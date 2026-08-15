from sqlalchemy import Column, DateTime, Integer, String
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
