from fastapi import APIRouter, HTTPException, Depends
from pygments.lexer import default
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict
from pydantic import BaseModel
from dependencies import get_db_session
from services import group_service, user_service
from sqlalchemy.future import select
from models import User

router = APIRouter()


# 获取所有组信息
@router.get("/api/groups")
async def get_all_groups(db: AsyncSession = Depends(get_db_session)):
    groups = await group_service.get_all_groups(db)
    return {"groups": groups}


# 获取指定组的详细信息（包括管理员和用户组成员、工作日志标准）
@router.get("/api/groups/{group_id}")
async def get_group_info(group_id: int, db: AsyncSession = Depends(get_db_session)):
    group_info = await group_service.get_group_by_id(db, group_id)
    if not group_info:
        raise HTTPException(status_code=404, detail="Group not found")
    return group_info

@router.get("/api/groups/uuid/{group_uuid}")
async def get_group_by_uuid(group_uuid: str, db: AsyncSession = Depends(get_db_session)):
    group_info = await group_service.get_group_by_uuid(db, group_uuid)
    if not group_info:
        raise HTTPException(status_code=404, detail="Group not found")
    return group_info


# 更新工作日志标准
class WorklogStandardUpdate(BaseModel):
    worklog_standard: str


@router.put("/api/groups/{group_id}/worklog-standard")
async def update_worklog_standard(group_id: str, update: WorklogStandardUpdate,
                                  db: AsyncSession = Depends(get_db_session)):
    success = await group_service.update_worklog_standard(db, group_id, update.worklog_standard)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update worklog standard")
    return {"success": True}


# 获取所有用户，根据角色过滤
@router.get("/api/users")
async def get_users_by_role(role: str, db: AsyncSession = Depends(get_db_session)):
    users = await user_service.get_users_by_role(db, role)
    return {"users": users}

@router.get("/api/users/uuid/{user_uuid}")
async def get_user_by_uuid(user_uuid: str, db: AsyncSession = Depends(get_db_session)):
    db_user = await user_service.get_user_by_uuid(db, user_uuid)
    return db_user

# 添加组成员
class AddUsersRequest(BaseModel):
    role: str
    user_ids: List[int]



@router.post("/api/groups/{group_id}/add-users")
async def add_users_to_group(group_id: int, request: AddUsersRequest, db: AsyncSession = Depends(get_db_session)):
    success = await group_service.add_users_to_group(db, group_id, request.role, request.user_ids)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add users")
    return ({"success": True})

class RemoveUsersRequest(BaseModel):
    role: str
    user_ids: List[int]

@router.post("/api/groups/{group_id}/remove-users")
async def remove_users_from_group(group_id: int, request: RemoveUsersRequest, db: AsyncSession = Depends(get_db_session)):
    print(f"删除 {group_id}: {request.role}, {request.user_ids}")  # 调试信息
    success = await group_service.remove_users_from_group(db, group_id, request.role, request.user_ids)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove users")
    return {"success": True}



# 创建新组
class CreateGroupRequest(BaseModel):
    name: str
    worklog_standard: str


@router.post("/api/groups")
async def create_group(request: CreateGroupRequest, db: AsyncSession = Depends(get_db_session)):
    group_data = {
        'name': request.name,
        'worklog_standard': request.worklog_standard
    }
    group = await group_service.create_group(db, group_data)
    if not group:
        raise HTTPException(status_code=400, detail="Group creation failed")
    return {"success": True, "group_id": group.uuid}


@router.get("/api/users/{user_uuid}")
async def get_user_name(user_uuid: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(User).filter(User.uuid == user_uuid)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"name": user.name}

@router.get("/api/groups/search_admin_users_by_uuid/{user_uuid}")
async def search_admin_users_by_uuid(user_uuid: str, db: AsyncSession = Depends(get_db_session)):
    groups = await group_service.get_groups_by_admin_user_uuid(db, user_uuid)
    return {"group_uuids": [group.uuid for group in groups]}

@router.get("/api/groups/search_user_users_by_uuid/{user_uuid}")
async def search_user_users_by_uuid(user_uuid: str, db: AsyncSession = Depends(get_db_session)):
    groups = await group_service.get_groups_by_user_user_uuid(db, user_uuid)
    return {"group_uuids": [group.uuid for group in groups]}