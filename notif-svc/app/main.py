import logging
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from . import models, schemas
from .database import Base, engine, get_db

logger = logging.getLogger("notif-svc")
logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="notif-svc")

from .consul_registration import deregister, register  # agregar al import existente

@app.on_event("startup")
def on_startup():
    register()


@app.on_event("shutdown")
def on_shutdown():
    deregister()


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


@app.post("/notifications", response_model=schemas.NotificationOut, status_code=201)
def send_notification(payload: schemas.NotificationCreate, db: Session = Depends(get_db)):
    logger.info("notificación para user_id=%s: %s", payload.user_id, payload.message)

    notification = models.Notification(user_id=payload.user_id, message=payload.message)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@app.get("/notifications/{user_id}", response_model=list[schemas.NotificationOut])
def get_history(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )
