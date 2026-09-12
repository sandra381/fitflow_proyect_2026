import json
import os

from mcp import ClientSession
from mcp.client.sse import sse_client

FITFLOW_MCP_URL = os.getenv("FITFLOW_MCP_URL", "http://fitflow-mcp:8000/sse")


async def call_mcp_tool(tool_name: str, arguments: dict):
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

            # OJO: cuando una tool devuelve una lista (ej. get_notification_history),
            # FastMCP manda UN bloque de texto POR CADA ELEMENTO de la lista, no
            # un solo bloque con el array completo. Hay que juntarlos todos.
            parsed_blocks = []
            for raw in text_blocks:
                try:
                    parsed_blocks.append(json.loads(raw))
                except json.JSONDecodeError:
                    parsed_blocks.append(raw)

            return parsed_blocks[0] if len(parsed_blocks) == 1 else parsed_blocks
