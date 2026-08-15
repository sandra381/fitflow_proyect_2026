import logging

import httpx
from mcp.server.fastmcp import FastMCP

from .auth_client import get_token
from .consul_client import discover_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fitflow-mcp")

mcp = FastMCP("fitflow-mcp", host="0.0.0.0", port=8000)


@mcp.tool()
def get_available_classes() -> list[dict]:
    """Lista las clases fitness disponibles en FitFlow."""
    booking_url = discover_service("booking-svc")
    resp = httpx.get(f"{booking_url}/classes", timeout=5.0)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def create_booking(class_id: int) -> dict:
    """Crea una reserva para el usuario en la clase indicada por su class_id."""
    booking_url = discover_service("booking-svc")
    token = get_token()
    resp = httpx.post(
        f"{booking_url}/bookings",
        json={"class_id": class_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=5.0,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def cancel_booking(booking_id: int) -> dict:
    """Cancela una reserva existente del usuario dado su booking_id."""
    booking_url = discover_service("booking-svc")
    token = get_token()
    resp = httpx.delete(
        f"{booking_url}/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5.0,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    mcp.run(transport="sse")