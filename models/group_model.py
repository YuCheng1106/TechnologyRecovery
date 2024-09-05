from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Group(Base):
    __tablename__ = "group"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(32), unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    create_datetime = Column(DateTime, default=datetime.utcnow)
    update_datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)

    # # Relationship to link with user_group
    # users = relationship('UserGroup', back_populates="group")
