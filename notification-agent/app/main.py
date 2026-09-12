import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .consul_registration import deregister, register
from .mcp_client import call_mcp_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-agent")

app = FastAPI(title="FitFlow Notification Agent")

AGENT_CARD = {
    "name": "FitFlow Notification Agent",
    "description": "Envía y consulta notificaciones de usuarios en FitFlow",
    "url": "http://notification-agent:9002",
    "skills": [
        {
            "id": "send_notification",
            "name": "Enviar notificación",
            "description": "Envía una notificación a un usuario, dado su user_id y un mensaje",
        },
        {
            "id": "get_history",
            "name": "Historial de notificaciones",
            "description": "Devuelve el historial de notificaciones de un usuario",
        },
    ],
}

SKILL_TO_MCP_TOOL = {
    "send_notification": "send_notification",
    "get_history": "get_notification_history",
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
    tool_name = SKILL_TO_MCP_TOOL.get(task.skill)
    if not tool_name:
        raise HTTPException(status_code=400, detail=f"unknown skill '{task.skill}'")

    logger.info("[A2A] tarea recibida -- skill=%s input=%s", task.skill, task.input)

    try:
        result = await call_mcp_tool(tool_name, task.input)
    except Exception as exc:
        logger.warning("[A2A] tarea fallida -- skill=%s error=%s", task.skill, exc)
        raise HTTPException(status_code=502, detail=f"error ejecutando '{task.skill}': {exc}")

    logger.info("[A2A] tarea completada -- skill=%s", task.skill)
    return {"status": "completed", "skill": task.skill, "output": result}
