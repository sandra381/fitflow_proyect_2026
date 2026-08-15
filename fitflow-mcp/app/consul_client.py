import os

import consul

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

client = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def discover_service(name: str) -> str:
    _, nodes = client.health.service(name, passing=True)
    if not nodes:
        raise RuntimeError(f"no hay instancias sanas de '{name}' en Consul")
    node = nodes[0]
    address = node["Service"]["Address"] or node["Node"]["Address"]
    port = node["Service"]["Port"]
    return f"http://{address}:{port}"