# FitFlow

Plataforma de reservas de clases fitness con arquitectura de microservicios.
Postgrado en Diseño y Desarrollo de Software — Universidad Galileo, FISICC.

> **Estado:** Task 1 y Task 2 completados (microservicios + Docker, Consul + MCP Server).

## Arquitectura (Task 1 + Task 2)

Tres servicios independientes, cada uno con su propia base de datos MySQL.
Ningún servicio accede a la base de datos de otro directamente. Todos se
registran en Consul al arrancar y se descubren dinámicamente entre sí.

```
users-svc (:8003) ─┐
booking-svc (:8001)─┼─ cada uno con su propia MySQL, registrado en Consul
notif-svc (:8002) ──┘

consul (:8500) ── service registry / health checks cada 10s

booking-svc ── descubre via Consul ──► notif-svc   (al crear una reserva)

fitflow-mcp (:8000) ── descubre via Consul ──► booking-svc, users-svc
       ▲
       │ protocolo MCP (SSE)
Claude Desktop
```

## Servicios

| Servicio | Puerto | Endpoints principales |
|---|---|---|
| `users-svc` | 8003 | `POST /register`, `POST /login`, `GET /users/{id}` |
| `booking-svc` | 8001 | `GET /classes`, `POST /bookings`, `DELETE /bookings/{id}` |
| `notif-svc` | 8002 | `POST /notifications`, `GET /notifications/{user_id}` |
| `consul` | 8500 | UI del service registry |
| `fitflow-mcp` | 8000 | Servidor MCP: `get_available_classes`, `create_booking`, `cancel_booking` |

Todos los servicios de aplicación exponen `/healthz` y `/readyz`.
`POST /bookings` y `DELETE /bookings/{id}` requieren JWT
(`Authorization: Bearer <token>`).

## Stack

Python + FastAPI · MySQL 8 (una instancia por servicio) · SQLAlchemy ·
JWT (PyJWT + bcrypt) · Docker + Docker Compose

## Cómo correr el proyecto

```bash
git clone <repo>
cd fitflow
cp .env .env   # completar valores
docker compose up --build
```

```bash
curl http://localhost:8003/healthz
curl http://localhost:8001/healthz
curl http://localhost:8002/healthz
```



## Consul + MCP Server (Task 2)

Abre `http://localhost:8500` para ver los 3 servicios registrados con sus
health checks en verde.

Para conectar Claude Desktop al servidor MCP (`fitflow-mcp`, puerto 8000),
agrega esto a tu `claude_desktop_config.json` (sección `mcpServers`):

```json
{
  "mcpServers": {
    "fitflow": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/sse", "--transport", "sse-only"]
    }
  }
}
```

Requiere Node.js instalado (usa `npx`). Antes de reservar vía MCP, registra
el usuario demo definido en `.env` (`DEMO_USER_EMAIL`/`DEMO_USER_PASSWORD`):

```bash
curl -X POST localhost:8003/register -H "Content-Type: application/json" \
  -d '{"email":"demo@fitflow.com","name":"Demo","password":"<tu-password>"}'
```

Luego, en el chat de Claude Desktop:
```
¿Qué clases hay disponibles en FitFlow?
Resérvame la clase de yoga
```

## Próximos pasos

- [x] Task 2: Consul + servidor MCP
- [ ] Task 3: Resiliencia + logs estructurados
- [ ] Task 4: Seguridad + demo grabada
- [ ] Task 5: Agent-to-Agent (A2A)
