import os

import consul

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

SERVICE_NAME = "notif-svc"
SERVICE_PORT = 8002
SERVICE_ADDRESS = os.getenv("SERVICE_ADDRESS", "notif-svc")

_client = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def register():
    _client.agent.service.register(
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
    _client.agent.service.deregister(SERVICE_NAME)