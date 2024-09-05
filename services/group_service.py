from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Group
from datetime import datetime
from common import id_generation

# 创建群组
async def create_group(db: AsyncSession, group_data: dict) -> Group:
    uuid = 'group_{}'.format(id_generation.generate_id())
    while await get_group_by_uuid(db, uuid):
        uuid = 'group_{}'.format(id_generation.generate_id())

    db_group = Group(**group_data, uuid=uuid, create_datetime=datetime.utcnow(), active=True)
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group)
    return db_group


# 按 ID 编辑群组
async def edit_group_by_id(db: AsyncSession, group_id: int, update_data: dict) -> Group:
    query = select(Group).where(Group.id == group_id)
    result = await db.execute(query)
    db_group = result.scalar_one_or_none()
    update_data = {k: v for k, v in update_data.items() if v is not None}  # 过滤掉 None 值
    if db_group is not None:
        for key, value in update_data.items():
            setattr(db_group, key, value)
        db_group.update_datetime = datetime.utcnow()
        await db.commit()
        await db.refresh(db_group)
        return db_group
    return None


# 按 UUID 编辑群组
async def edit_group_by_uuid(db: AsyncSession, group_uuid: str, update_data: dict) -> Group:
    query = select(Group).where(Group.uuid == group_uuid)
    result = await db.execute(query)
    db_group = result.scalar_one_or_none()
    update_data = {k: v for k, v in update_data.items() if v is not None}  # 过滤掉 None 值
    if db_group is not None:
        for key, value in update_data.items():
            setattr(db_group, key, value)
        db_group.update_datetime = datetime.utcnow()
        await db.commit()
        await db.refresh(db_group)
        return db_group
    return None


# 按 ID 获取群组
async def get_group_by_id(db: AsyncSession, group_id: int) -> Group:
    result = await db.execute(select(Group).where(Group.id == group_id))
    return result.scalar_one_or_none()


# 按 UUID 获取群组
async def get_group_by_uuid(db: AsyncSession, group_uuid: str) -> Group:
    result = await db.execute(select(Group).where(Group.uuid == group_uuid))
    return result.scalar_one_or_none()


# 获取所有群组
async def get_all_groups(db: AsyncSession) -> list[Group]:
    result = await db.execute(select(Group))
    return result.scalars().all()
