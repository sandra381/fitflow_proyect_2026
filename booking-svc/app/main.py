import datetime
import logging
import os
import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from . import models, schemas
from .auth import get_current_user_id
from .database import Base, SessionLocal, engine, get_db

logger = logging.getLogger("booking-svc")
logging.basicConfig(level=logging.INFO)

NOTIF_SVC_URL = os.getenv("NOTIF_SVC_URL", "http://notif-svc:8002")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="booking-svc")


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


@app.get("/classes", response_model=list[schemas.ClassOut])
def list_classes(db: Session = Depends(get_db)):
    return db.query(models.FitnessClass).order_by(models.FitnessClass.scheduled_at).all()


def _notify(user_id: int, message: str):
    """Llamada best-effort a notif-svc. El Task 3 le agrega resiliencia real."""
    try:
        httpx.post(
            f"{NOTIF_SVC_URL}/notifications",
            json={"user_id": user_id, "message": message},
            timeout=2.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("no se pudo notificar a notif-svc: %s", exc)


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
