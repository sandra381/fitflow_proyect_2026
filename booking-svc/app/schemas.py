import datetime

from pydantic import BaseModel


class ClassOut(BaseModel):
    id: int
    name: str
    instructor: str
    scheduled_at: datetime.datetime
    capacity: int

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    class_id: int


class BookingOut(BaseModel):
    id: int
    user_id: int
    class_id: int
    class_name: str
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
