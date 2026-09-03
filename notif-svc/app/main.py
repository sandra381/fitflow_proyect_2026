from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models, schemas
from .consul_registration import deregister, register
from .database import Base, engine, get_db
from .observability import CorrelationIdMiddleware, logger

Base.metadata.create_all(bind=engine)

app = FastAPI(title="notif-svc")
app.add_middleware(CorrelationIdMiddleware)


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
    # Por ahora "enviar" es solo loguear + guardar. Se puede reemplazar por
    # email/SMS real más adelante sin tocar a booking-svc.
    logger.info("notification_received", user_id=payload.user_id, message=payload.message)

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
