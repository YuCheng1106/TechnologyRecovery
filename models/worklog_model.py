# app/models/user_model.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class WorkLog(Base):
    __tablename__ = "workLog"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(32), unique=True, index=True)
    user_uuid = Column(String(32))
    task = Column(Text)
    solution = Column(Text)
    effect = Column(Text)
    create_datetime = Column(DateTime, default=datetime.utcnow)
    update_datetime = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean)
