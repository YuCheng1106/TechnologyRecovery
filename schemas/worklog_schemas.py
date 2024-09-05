from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WorkLogSubmit(BaseModel):
    text: str


class WorkLogCreate(BaseModel):
    姓名: str
    工作日志: Optional[str] = None
    向量: Optional[bytes] = None
    active: Optional[bool] = None


class WorkLogUpdate(BaseModel):
    工作日志: Optional[str] = None
    向量: Optional[bytes] = None
    active: Optional[bool] = None
    update_datetime: Optional[datetime] = None


class WorkLogResponse(BaseModel):
    id: int
    uuid: str
    姓名: str
    工作日志: Optional[str] = None
    向量: Optional[bytes] = None
    create_datetime: datetime
    update_datetime: datetime
    active: Optional[bool] = True

    class Config:
        orm_mode = True
        from_attributes = True
