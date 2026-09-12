import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .consul_registration import deregister, register
from .mcp_client import call_mcp_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("booking-agent")

app = FastAPI(title="FitFlow Booking Agent")

AGENT_CARD = {
    "name": "FitFlow Booking Agent",
    "description": "Gestiona reservas de clases fitness en FitFlow",
    "url": "http://booking-agent:9001",
    "skills": [
        {
            "id": "get_available_classes",
            "name": "Listar clases disponibles",
            "description": "Devuelve las clases fitness disponibles en FitFlow",
        },
        {
            "id": "create_booking",
            "name": "Crear reserva",
            "description": "Reserva una clase para el usuario, dado su class_id",
        },
        {
            "id": "cancel_booking",
            "name": "Cancelar reserva",
            "description": "Cancela una reserva existente, dado su booking_id",
        },
    ],
}

# Cada skill del Agent Card mapea a una herramienta real del servidor MCP de
# FitFlow. El agente no tiene lógica de negocio propia -- solo traduce una
# "tarea A2A" en una llamada MCP real.
SKILL_TO_MCP_TOOL = {
    "get_available_classes": "get_available_classes",
    "create_booking": "create_booking",
    "cancel_booking": "cancel_booking",
}


class TaskRequest(BaseModel):
    skill: str
    input: dict = {}


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


@app.post("/tasks")
async def handle_task(task: TaskRequest):
    """Endpoint A2A simplificado: recibe una tarea con un `skill` (debe
    coincidir con uno publicado en el Agent Card) y su `input`, la ejecuta
    llamando a la herramienta MCP correspondiente, y devuelve el resultado.
    """
    tool_name = SKILL_TO_MCP_TOOL.get(task.skill)
    if not tool_name:
        raise HTTPException(status_code=400, detail=f"unknown skill '{task.skill}'")

    logger.info(
        "[A2A] tarea recibida -- skill=%s input=%s", task.skill, task.input
    )

    try:
        result = await call_mcp_tool(tool_name, task.input)
    except Exception as exc:
        logger.warning("[A2A] tarea fallida -- skill=%s error=%s", task.skill, exc)
        raise HTTPException(status_code=502, detail=f"error ejecutando '{task.skill}': {exc}")

    logger.info("[A2A] tarea completada -- skill=%s", task.skill)
    return {"status": "completed", "skill": task.skill, "output": result}