import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agent_client import delegate_task, get_agent_card
from .consul_client import deregister, register
from .intent import parse_instruction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator-agent")

app = FastAPI(title="FitFlow Orchestrator Agent")

AGENT_CARD = {
    "name": "FitFlow Orchestrator Agent",
    "description": "Recibe la intención del usuario y coordina a los agentes especializados de FitFlow",
    "url": "http://orchestrator-agent:9000",
    "skills": [
        {
            "id": "instruct",
            "name": "Procesar instrucción",
            "description": "Interpreta una instrucción en lenguaje natural y delega tareas a Booking Agent y Notification Agent",
        }
    ],
}


class InstructRequest(BaseModel):
    text: str


@app.on_event("startup")
def on_startup():
    register()


@app.on_event("shutdown")
def on_shutdown():
    deregister()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/.well-known/agent.json")
def agent_card():
    return AGENT_CARD


@app.post("/instruct")
async def instruct(payload: InstructRequest):
    """Punto de entrada único para el usuario. Ejemplo:
    'Reserva yoga para el viernes y avísame por notificación'.

    El orquestador NUNCA llama directamente a FitFlow -- todo pasa por los
    agentes especializados, descubiertos dinámicamente."""
    intent = parse_instruction(payload.text)
    trace = []

    logger.info("[A2A] instrucción recibida: '%s'", payload.text)

    if not intent["wants_booking"] or not intent["class_name"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "No pude identificar qué clase reservar. Prueba algo como "
                "'Reserva yoga y avísame por notificación'."
            ),
        )

    # 1. Descubrir al Booking Agent (Consul + su Agent Card)
    booking_card = await get_agent_card("booking-agent")
    trace.append({"step": "discover", "agent": booking_card["name"]})

    # 2. Delegarle que liste las clases, para resolver el nombre -> class_id
    classes_task = await delegate_task("booking-agent", "get_available_classes", {})
    classes = classes_task["output"]
    match = next(
        (c for c in classes if intent["class_name"] in c["name"].lower()), None
    )
    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"No encontré una clase que coincida con '{intent['class_name']}'",
        )
    trace.append({"step": "get_available_classes", "agent": booking_card["name"], "matched_class": match["name"]})

    # 3. Delegarle la creación de la reserva
    booking_task = await delegate_task("booking-agent", "create_booking", {"class_id": match["id"]})
    booking = booking_task["output"]
    trace.append({"step": "create_booking", "agent": booking_card["name"], "result": booking})

    notification = None
    if intent["wants_notification"]:
        # 4. Descubrir al Notification Agent y delegarle el aviso
        notif_card = await get_agent_card("notification-agent")
        trace.append({"step": "discover", "agent": notif_card["name"]})

        message = f"Tu reserva para {match['name']} fue confirmada"
        notif_task = await delegate_task(
            "notification-agent",
            "send_notification",
            {"user_id": booking["user_id"], "message": message},
        )
        notification = notif_task["output"]
        trace.append({"step": "send_notification", "agent": notif_card["name"], "result": notification})

    logger.info("[A2A] instrucción completada")

    return {
        "instruction": payload.text,
        "booking": booking,
        "notification": notification,
        "a2a_trace": trace,
    }
