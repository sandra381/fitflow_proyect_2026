# FitFlow

Plataforma de reservas de clases fitness con arquitectura de microservicios.
Postgrado en Diseño y Desarrollo de Software — Universidad Galileo, FISICC.

> **Estado:** Task 1, Task 2 y Task 3 completados (microservicios + Docker, Consul + MCP Server, resiliencia + logs estructurados).

## Arquitectura (Task 1 + Task 2 + Task 3)

Tres servicios independientes, cada uno con su propia base de datos MySQL.
Ningún servicio accede a la base de datos de otro directamente. Todos se
registran en Consul al arrancar y se descubren dinámicamente entre sí.

```
users-svc (:8003) ─┐
booking-svc (:8001)─┼─ cada uno con su propia MySQL, registrado en Consul
notif-svc (:8002) ──┘

consul (:8500) ── service registry / health checks cada 10s

booking-svc ── descubre via Consul ──► notif-svc   (al crear una reserva)
             (con timeout + retries + circuit breaker + outbox pattern)

fitflow-mcp (:8000) ── descubre via Consul ──► booking-svc, users-svc
       ▲
       │ protocolo MCP (SSE)
Claude Desktop
```

## Servicios

| Servicio | Puerto | Endpoints principales |
|---|---|---|
| `users-svc` | 8003 | `POST /register`, `POST /login`, `GET /users/{id}` |
| `booking-svc` | 8001 | `GET /classes`, `POST /bookings`, `DELETE /bookings/{id}`, `GET /circuit-status` |
| `notif-svc` | 8002 | `POST /notifications`, `GET /notifications/{user_id}` |
| `consul` | 8500 | UI del service registry |
| `fitflow-mcp` | 8000 | Servidor MCP: `get_available_classes`, `create_booking`, `cancel_booking` |

Todos los servicios de aplicación exponen `/healthz` y `/readyz`.
`POST /bookings` y `DELETE /bookings/{id}` requieren JWT
(`Authorization: Bearer <token>`).

## Stack

Python + FastAPI · MySQL 8 (una instancia por servicio) · SQLAlchemy ·
JWT (PyJWT + bcrypt) · Consul · MCP (protocolo, SDK oficial de Python) ·
tenacity + pybreaker (resiliencia) · structlog (logs JSON) ·
Docker + Docker Compose

## Cómo correr el proyecto

```bash
git clone <repo>
cd fitflow
cp .env.example .env   # completar valores
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

## Resiliencia + Logs estructurados (Task 3)

`booking-svc` no depende de que `notif-svc` esté siempre disponible:

- **Timeout** de 2s por llamada a `notif-svc`.
- **Retries con backoff exponencial + jitter**: hasta 3 intentos (0.5s, 1s, 2s + jitter).
- **Circuit breaker**: si falla varias veces seguidas, se abre por 30s y deja
  de intentar llamar (evita bloquear las reservas esperando a un servicio caído).
- **Outbox pattern**: mientras el circuito está abierto, la notificación se
  guarda como pendiente en la propia base de datos de `booking-svc`. Un
  hilo en segundo plano la reintenta cada 15s hasta que `notif-svc` vuelve.

Ver el estado del circuit breaker en vivo:
```bash
curl http://localhost:8001/circuit-status
```

Demo de resiliencia:
```bash
docker compose stop notif-svc
# ... hacer 3+ reservas, todas deben responder "confirmed", nunca 500 ...
curl http://localhost:8001/circuit-status   # -> "state":"open"
docker compose start notif-svc
# esperar ~40s
curl http://localhost:8001/circuit-status   # -> "state":"closed"
```

**Logs JSON con correlation-id:** cada request genera o propaga un
`x-correlation-id` (via header), y todos los logs de los 3 servicios
quedan en formato JSON con `correlation_id`, `service`, `event`, `level`
y `timestamp` — permite rastrear un mismo request a través de varios
servicios:
```bash
docker compose logs booking-svc | grep booking_created
docker compose logs notif-svc | grep notification_received
```

## Links a videos de entregas
- Checkpoint 1: https://drive.google.com/file/d/1ynJ5Y4whbLwhUsP3OgLkKPG_uF3HwyW-/view?usp=sharing
- Checkpoint 2:
- Checkpoint 3:

## Próximos pasos

- [x] Task 2: Consul + servidor MCP
- [x] Task 3: Resiliencia + logs estructurados
- [ ] Task 4: Seguridad + demo grabada
- [ ] Task 5: Agent-to-Agent (A2A)
