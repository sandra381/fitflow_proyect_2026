import datetime

from pydantic import BaseModel


class NotificationCreate(BaseModel):
    user_id: int
    message: str


class NotificationOut(BaseModel):
    id: int
    user_id: int
    message: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
