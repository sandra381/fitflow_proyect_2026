import datetime
import threading
import time

import httpx
import pybreaker
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from . import models, schemas
from .auth import get_current_user_id
from .consul_registration import deregister, discover_service, register
from .database import Base, SessionLocal, engine, get_db
from .observability import CorrelationIdMiddleware, get_correlation_id, logger
from .resilience import notif_breaker

Base.metadata.create_all(bind=engine)

app = FastAPI(title="booking-svc")
app.add_middleware(CorrelationIdMiddleware)


@app.on_event("startup")
def on_startup_register():
    register()


@app.on_event("shutdown")
def on_shutdown():
    deregister()


@app.on_event("startup")
def start_outbox_worker():
    """Hilo en segundo plano que reintenta notificaciones pendientes cada
    15s -- el 'outbox pattern' que procesa lo que quedó pendiente cuando
    notif-svc estaba caído."""
    thread = threading.Thread(target=_outbox_worker_loop, daemon=True)
    thread.start()


SEED_CLASSES = [
    {"name": "Yoga", "instructor": "Ana Lopez", "offset_days": 1, "capacity": 15},
    {"name": "Spinning", "instructor": "Carlos Ruiz", "offset_days": 2, "capacity": 20},
    {"name": "CrossFit", "instructor": "Maria Gomez", "offset_days": 3, "capacity": 12},
    {"name": "Pilates", "instructor": "Luis Perez", "offset_days": 4, "capacity": 15},
]


@app.on_event("startup")
def seed_classes():
    db: Session = SessionLocal()
    try:
        if db.query(models.FitnessClass).count() == 0:
            now = datetime.datetime.now(datetime.timezone.utc)
            for c in SEED_CLASSES:
                db.add(
                    models.FitnessClass(
                        name=c["name"],
                        instructor=c["instructor"],
                        scheduled_at=now + datetime.timedelta(days=c["offset_days"]),
                        capacity=c["capacity"],
                    )
                )
            db.commit()
    finally:
        db.close()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="database not ready")


@app.get("/circuit-status")
def circuit_status():
    """Expone el estado actual del circuit breaker hacia notif-svc -- útil
    para la demo del Task 3 (mostrar cuándo está abierto/cerrado)."""
    return {
        "breaker": notif_breaker.name,
        "state": str(notif_breaker.current_state),
        "fail_counter": notif_breaker.fail_counter,
    }


@app.get("/classes", response_model=list[schemas.ClassOut])
def list_classes(db: Session = Depends(get_db)):
    return db.query(models.FitnessClass).order_by(models.FitnessClass.scheduled_at).all()


# --- Resiliencia: timeout + retries con backoff/jitter + circuit breaker ---

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2) + wait_random(0, 0.3),
    retry=retry_if_exception_type((httpx.HTTPError, RuntimeError)),
    reraise=True,
)
def _post_notification(user_id: int, message: str):
    """Un intento (con reintentos internos) de avisarle a notif-svc.
    Timeout de 2s por intento. Reintenta hasta 3 veces con backoff
    exponencial (0.5s, 1s, 2s) + jitter aleatorio."""
    notif_url = discover_service("notif-svc")
    correlation_id = get_correlation_id()
    headers = {"x-correlation-id": correlation_id} if correlation_id else {}

    resp = httpx.post(
        f"{notif_url}/notifications",
        json={"user_id": user_id, "message": message},
        headers=headers,
        timeout=2.0,
    )
    resp.raise_for_status()
    return resp


@notif_breaker
def _post_notification_guarded(user_id: int, message: str):
    """Misma llamada, pero protegida por el circuit breaker: si notif-svc
    falló 3 veces seguidas (cada una ya con sus reintentos agotados), el
    breaker se abre y esta función falla instantáneamente sin ni siquiera
    intentar la llamada, durante 30s."""
    return _post_notification(user_id, message)


def _save_pending_notification(user_id: int, message: str):
    db = SessionLocal()
    try:
        db.add(models.PendingNotification(user_id=user_id, message=message))
        db.commit()
    finally:
        db.close()


def _notify(user_id: int, message: str):
    """Le avisa a notif-svc que algo pasó. Si falla (timeout, servicio
    caído, o circuit breaker abierto), la reserva NO se pierde -- se guarda
    como notificación pendiente (outbox pattern) para reintentar después."""
    try:
        _post_notification_guarded(user_id, message)
    except pybreaker.CircuitBreakerError:
        logger.warning("notification_skipped_circuit_open", user_id=user_id)
        _save_pending_notification(user_id, message)
    except Exception as exc:
        logger.warning("notification_failed_after_retries", user_id=user_id, error=str(exc))
        _save_pending_notification(user_id, message)


def _flush_pending_notifications():
    """Intenta reenviar las notificaciones pendientes. Si la primera falla
    (breaker sigue abierto o notif-svc sigue caído), se detiene en vez de
    seguir intentando todas -- espera al siguiente ciclo."""
    db = SessionLocal()
    try:
        pending = (
            db.query(models.PendingNotification)
            .filter_by(sent=False)
            .order_by(models.PendingNotification.created_at)
            .all()
        )
        for item in pending:
            try:
                _post_notification_guarded(item.user_id, item.message)
            except Exception:
                logger.info("outbox_flush_paused", remaining=len(pending))
                break
            item.sent = True
            db.commit()
            logger.info("outbox_notification_sent", notification_id=item.id)
    finally:
        db.close()


def _outbox_worker_loop():
    while True:
        time.sleep(15)
        try:
            _flush_pending_notifications()
        except Exception as exc:
            logger.warning("outbox_worker_error", error=str(exc))


@app.post("/bookings", response_model=schemas.BookingOut, status_code=201)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    fitness_class = db.query(models.FitnessClass).filter(
        models.FitnessClass.id == payload.class_id
    ).first()
    if not fitness_class:
        raise HTTPException(status_code=404, detail="class not found")

    booking = models.Booking(
        user_id=user_id,
        class_id=fitness_class.id,
        class_name=fitness_class.name,
        status="confirmed",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    logger.info("booking_created", booking_id=booking.id, user_id=user_id, class_id=fitness_class.id)
    _notify(user_id, f"Tu reserva para {fitness_class.name} fue confirmada")

    return booking


@app.get("/bookings/{booking_id}", response_model=schemas.BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="booking not found")
    return booking


@app.delete("/bookings/{booking_id}", response_model=schemas.BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="not your booking")

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking
