# app/models/user_model.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text,BLOB
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class WorkLog(Base):
    __tablename__ = "workLog"
    id = Column(Integer, primary_key=True, index=True)
    姓名 = Column(Text)
    工作日志 = Column(Text)
    向量 = Column(BLOB)
    effect = Column(Text)
    active = Column(Boolean)
