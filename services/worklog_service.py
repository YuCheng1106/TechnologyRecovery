from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.worklog_model import WorkLog
from datetime import datetime
from common import id_generation


# 创建工作日志
async def create_worklog(db: AsyncSession, worklog_data: dict) -> WorkLog:
    uuid = 'workLog_{}'.format(id_generation.generate_id())
    while await get_worklog_by_uuid(db, uuid):
        uuid = 'workLog_{}'.format(id_generation.generate_id())

    db_worklog = WorkLog(**worklog_data, uuid=uuid, create_datetime=datetime.utcnow(), active=True)
    db.add(db_worklog)
    await db.commit()
    await db.refresh(db_worklog)
    return db_worklog


# 按 ID 编辑工作日志
async def edit_worklog_by_id(db: AsyncSession, worklog_id: int, update_data: dict) -> WorkLog:
    query = select(WorkLog).where(WorkLog.id == worklog_id)
    result = await db.execute(query)
    db_worklog = result.scalar_one_or_none()
    update_data = {k: v for k, v in update_data.items() if v is not None}  # 过滤掉 None 值
    if db_worklog is not None:
        for key, value in update_data.items():
            setattr(db_worklog, key, value)
        db_worklog.update_datetime = datetime.utcnow()
        await db.commit()
        await db.refresh(db_worklog)
        return db_worklog
    return None


# 按 UUID 编辑工作日志
async def edit_worklog_by_uuid(db: AsyncSession, worklog_uuid: str, update_data: dict) -> WorkLog:
    query = select(WorkLog).where(WorkLog.uuid == worklog_uuid)
    result = await db.execute(query)
    db_worklog = result.scalar_one_or_none()
    update_data = {k: v for k, v in update_data.items() if v is not None}  # 过滤掉 None 值
    if db_worklog is not None:
        for key, value in update_data.items():
            setattr(db_worklog, key, value)
        db_worklog.update_datetime = datetime.utcnow()
        await db.commit()
        await db.refresh(db_worklog)
        return db_worklog
    return None


# 按 ID 获取工作日志
async def get_worklog_by_id(db: AsyncSession, worklog_id: int) -> WorkLog:
    result = await db.execute(select(WorkLog).where(WorkLog.id == worklog_id))
    return result.scalar_one_or_none()


# 按 UUID 获取工作日志
async def get_worklog_by_uuid(db: AsyncSession, worklog_uuid: str) -> WorkLog:
    result = await db.execute(select(WorkLog).where(WorkLog.uuid == worklog_uuid))
    return result.scalar_one_or_none()


async def get_all_user_worklogs(db: AsyncSession, user_uuid: str) -> list[WorkLog]:
    result = await db.execute(
        select(WorkLog).where(WorkLog.user_uuid == user_uuid)
    )
    return result.scalars().all()


# 获取所有工作日志
async def get_all_worklogs(db: AsyncSession) -> list[WorkLog]:
    result = await db.execute(select(WorkLog))
    return result.scalars().all()
