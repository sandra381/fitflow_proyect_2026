# FitFlow

Plataforma de reservas de clases fitness con arquitectura de microservicios.
Postgrado en Diseño y Desarrollo de Software — Universidad Galileo, FISICC.

> **Estado:** Task 1 completado (microservicios + Docker).

## Arquitectura (Task 1)

Tres servicios independientes, cada uno con su propia base de datos MySQL.
Ningún servicio accede a la base de datos de otro directamente.
users-svc (:8003) ─┐
booking-svc (:8001)─┼─ cada uno con su propia MySQL
notif-svc (:8002) ──┘

booking-svc ── HTTP ──► notif-svc (al crear una reserva)

## Servicios

| Servicio | Puerto | Endpoints principales |
|---|---|---|
| `users-svc` | 8003 | `POST /register`, `POST /login`, `GET /users/{id}` |
| `booking-svc` | 8001 | `GET /classes`, `POST /bookings`, `DELETE /bookings/{id}` |
| `notif-svc` | 8002 | `POST /notifications`, `GET /notifications/{user_id}` |

Todos exponen `/healthz` y `/readyz`. `POST /bookings` y `DELETE /bookings/{id}`
requieren JWT (`Authorization: Bearer <token>`).

## Stack

Python + FastAPI · MySQL 8 (una instancia por servicio) · SQLAlchemy ·
JWT (PyJWT + bcrypt) · Docker + Docker Compose

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

## Próximos pasos

- [ ] Task 2: Consul + servidor MCP
- [ ] Task 3: Resiliencia + logs estructurados
- [ ] Task 4: Seguridad + demo grabada
- [ ] Task 5: Agent-to-Agent (A2A)