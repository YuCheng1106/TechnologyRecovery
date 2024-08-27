from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class WorkLogSubmit(BaseModel):
    text: str


class WorkLogCreate(BaseModel):
    user_uuid: str
    task: Optional[str] = None
    solution: Optional[str] = None
    effect: Optional[str] = None


class WorkLogUpdate(BaseModel):
    task: Optional[str] = None
    solution: Optional[str] = None
    effect: Optional[str] = None
    active: Optional[bool] = None
    update_datetime: Optional[datetime] = None


class WorkLogResponse(BaseModel):
    id: int
    uuid: str
    user_uuid: str
    task: Optional[str] = None
    solution: Optional[str] = None
    effect: Optional[str] = None
    create_datetime: datetime
    update_datetime: datetime
    active: Optional[bool] = True

    class Config:
        orm_mode = True
        from_attributes = True
