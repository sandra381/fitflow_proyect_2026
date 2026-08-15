import os

import consul

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

SERVICE_NAME = "booking-svc"
SERVICE_PORT = 8001
SERVICE_ADDRESS = os.getenv("SERVICE_ADDRESS", "booking-svc")

client = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def register():
    client.agent.service.register(
        name=SERVICE_NAME,
        service_id=SERVICE_NAME,
        address=SERVICE_ADDRESS,
        port=SERVICE_PORT,
        check=consul.Check.http(
            url=f"http://{SERVICE_ADDRESS}:{SERVICE_PORT}/healthz",
            interval="10s",
            timeout="5s",
            deregister="30s",
        ),
    )


def deregister():
    client.agent.service.deregister(SERVICE_NAME)


def discover_service(name: str) -> str:
    """Le pregunta a Consul dónde está una instancia sana de `name` ahora
    mismo, y devuelve su URL base."""
    _, nodes = client.health.service(name, passing=True)
    if not nodes:
        raise RuntimeError(f"no hay instancias sanas de '{name}' en Consul")
    node = nodes[0]
    address = node["Service"]["Address"] or node["Node"]["Address"]
    port = node["Service"]["Port"]
    return f"http://{address}:{port}"