import logging

import httpx

from .consul_client import discover_service

logger = logging.getLogger("orchestrator-agent")


async def get_agent_card(consul_name: str) -> dict:
    """Descubre DÓNDE está el agente via Consul, y luego le pregunta a él
    mismo QUÉ sabe hacer leyendo su Agent Card en /.well-known/agent.json.
    Esto es el mecanismo de descubrimiento de A2A."""
    base_url = discover_service(consul_name)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/.well-known/agent.json", timeout=5.0)
        resp.raise_for_status()
        card = resp.json()

    logger.info(
        "[A2A] agente descubierto -- name=%s skills=%s",
        card["name"],
        [s["id"] for s in card["skills"]],
    )
    return card


async def delegate_task(consul_name: str, skill: str, input_data: dict) -> dict:
    """Le delega una tarea a otro agente (protocolo A2A simplificado: un
    POST /tasks con el skill e input). El agente destino la ejecuta usando
    MCP internamente y devuelve el resultado."""
    base_url = discover_service(consul_name)
    logger.info("[A2A] delegando -- to=%s skill=%s input=%s", consul_name, skill, input_data)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}/tasks",
            json={"skill": skill, "input": input_data},
            timeout=15.0,
        )
        resp.raise_for_status()
        result = resp.json()

    logger.info("[A2A] resultado recibido -- from=%s skill=%s status=%s", consul_name, skill, result.get("status"))
    return result
