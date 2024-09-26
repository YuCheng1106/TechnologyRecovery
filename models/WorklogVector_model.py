from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class WorklogVector(Base):
    __tablename__ = 'worklog_vector'

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(255), nullable=False)
    vector = Column(JSON, nullable=False)  # 假设vector存储为JSON格式
