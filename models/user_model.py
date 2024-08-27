# app/models/user_model.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Administrator(Base):
    __tablename__ = "admin_tb"
    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, index=True)
    user_email = Column(String, unique=True, index=True)
    user_password = Column(String)


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(32), unique=True, index=True)
    name = Column(String(32))
    email = Column(String(255), unique=True, index=True)
    avatar = Column(String(255))
    introduction = Column(Text)
    hashed_password = Column(String(255))
    create_datetime = Column(DateTime, default=datetime.utcnow)
    update_datetime = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean)
