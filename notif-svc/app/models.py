from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from .database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
