import json
import os

from mcp import ClientSession
from mcp.client.sse import sse_client

# fitflow-mcp expone sus herramientas por SSE. Los agentes A2A actúan como
# clientes MCP de ese servidor -- así ejecutan las acciones reales sobre
# FitFlow, tal como indica la guía: "Internamente usa el MCP Server de
# FitFlow para ejecutar las acciones reales."
FITFLOW_MCP_URL = os.getenv("FITFLOW_MCP_URL", "http://fitflow-mcp:8000/sse")


async def call_mcp_tool(tool_name: str, arguments: dict):
    """Abre una sesión MCP contra fitflow-mcp, llama a una herramienta, y
    devuelve el resultado ya parseado (dict o list)."""
    async with sse_client(FITFLOW_MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            if result.isError:
                error_text = "".join(
                    getattr(block, "text", "") for block in result.content
                )
                raise RuntimeError(f"MCP tool '{tool_name}' error: {error_text}")

            text_blocks = [
                block.text for block in result.content if hasattr(block, "text")
            ]
            if not text_blocks:
                return None
            
            parsed_blocks = []
            for raw in text_blocks:
                try:
                    parsed_blocks.append(json.loads(raw))
                except json.JSONDecodeError:
                    parsed_blocks.append(raw)

            return parsed_blocks[0] if len(parsed_blocks) == 1 else parsed_blocks
