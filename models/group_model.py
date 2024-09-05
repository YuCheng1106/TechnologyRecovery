from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class GroupModel(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    worklog_standard = Column(String)

    # 定义与管理员和用户的关系
    admins = relationship(
        "UserModel",
        primaryjoin="and_(GroupModel.id==UserModel.group_id, UserModel.role=='admin')",
        back_populates="group",
        viewonly=True
    )
    users = relationship(
        "UserModel",
        primaryjoin="and_(GroupModel.id==UserModel.group_id, UserModel.role=='user')",
        back_populates="group",
        viewonly=True
    )


class UserModel(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String)
    group_id = Column(Integer, ForeignKey('groups.id'))

    # 设置反向关系，viewonly=True 避免循环关系的问题
    group = relationship("GroupModel", back_populates="admins", viewonly=True)
