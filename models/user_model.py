# app/models/user_model.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, BLOB
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(32), unique=True, index=True)
    name = Column(String(32))
    hashed_password = Column(String(255))
    create_datetime = Column(DateTime, default=datetime.utcnow)
    update_datetime = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    role = Column(String(32))
    active = Column(Boolean)
