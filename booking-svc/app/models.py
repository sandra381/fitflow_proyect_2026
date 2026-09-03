from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from .database import Base


class FitnessClass(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    instructor = Column(String(255), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    capacity = Column(Integer, nullable=False, default=20)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    class_id = Column(Integer, nullable=False, index=True)
    class_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="confirmed")  # confirmed | cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PendingNotification(Base):
    """Outbox pattern: cuando notif-svc no responde (circuit breaker abierto
    o reintentos agotados), la notificación se guarda aquí en vez de
    perderse. Un worker en segundo plano la reintenta cuando notif-svc
    vuelve a estar disponible."""

    __tablename__ = "pending_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    message = Column(String(500), nullable=False)
    sent = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
