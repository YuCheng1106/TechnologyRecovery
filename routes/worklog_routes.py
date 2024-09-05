import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from services import worklog_service
from services import user_service
from services.database import get_db_session
from schemas.worklog_schemas import WorkLogCreate, WorkLogUpdate, WorkLogResponse, WorkLogSubmit
from schemas.group_schema import GroupResponse
from models.group_model import Group
from dependencies import get_current_user
from formatter import process_and_store_log
from fastapi.templating import Jinja2Templates
from services import usergroup_service
from sqlalchemy.future import select
router = APIRouter()

templates = Jinja2Templates(directory="templates")


def split_text_by_double_newlines(text):
    """按双换行符分割文本"""
    parts = []
    current_part = []

    for line in text.splitlines():
        if line.strip() == '' and current_part:
            if any(line.strip() for line in current_part):
                parts.append('\n'.join(current_part))
            current_part = []
        else:
            current_part.append(line)

    if current_part and any(line.strip() for line in current_part):
        parts.append('\n'.join(current_part))

    return parts


def parse_worklog_part(part: str, user_uuid: str) -> dict:
    # 将 part 字符串分割为多行
    lines = part.split('\n')
    worklog_data = {
        "姓名": user_uuid,
        "工作日志": None,
        "effect": None
    }

    for line in lines:
        if line.startswith("解决问题："):
            worklog_data["工作日志"] = line.replace("解决问题：", "").strip()
        elif line.startswith("解决效果："):
            worklog_data["effect"] = line.replace("解决效果：", "").strip()

    return worklog_data


@router.post('/worklogs/submit', status_code=status.HTTP_201_CREATED)
async def submit_log(worklog: WorkLogSubmit, db: AsyncSession = Depends(get_db_session), uid=Depends(get_current_user)):
    processed_result = await process_and_store_log(worklog.text)
    parts = split_text_by_double_newlines(processed_result)

    for i, part in enumerate(parts, start=1):
        retries = 0
        max_retries = 2

        # 解析 part 字符串
        worklog_data = parse_worklog_part(part, uid)

        while retries <= max_retries:
            try:
                await worklog_service.create_worklog(db, worklog_data)
                break  # 如果成功插入，则跳出重试循环
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    print(f"插入部分{i}数据失败: {e}")
                else:
                    await asyncio.sleep(1)  # 等待1秒后重试

    return {"message": "Work logs successfully submitted"}


@router.get('/worklogs/add', status_code=status.HTTP_200_OK)
async def addlogs(request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
    # 获取 token 并验证用户身份
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # 解析 token 并获取 user_uuid
        try:
            token = token.split(" ")[1]
        except IndexError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format")

        user_uuid = await get_current_user(token, db)
        if not user_uuid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        # 获取当前用户信息
        user = await user_service.get_user_by_uuid(db, user_uuid)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # 获取该用户加入的所有群组
        usergroups = await usergroup_service.get_all_groups_for_user(db, user_uuid)

        # 优化获取群组信息
        group_uuids = [usergroup.group_uuid for usergroup in usergroups]
        groups = []
        if group_uuids:
            group_query = select(Group).where(Group.uuid.in_(group_uuids))
            result = await db.execute(group_query)
            group_objects = result.scalars().all()

            # 将每个群组对象转为 GroupResponse
            groups = [GroupResponse.from_orm(group).json() for group in group_objects]

        # 返回模板响应
        return templates.TemplateResponse('addlogs.html', {"request": request, "username": user.name, "groups": groups})

    except HTTPException as http_exc:
        raise http_exc  # 重新抛出已知 HTTP 异常

    except Exception as e:
        # 打印异常信息并返回通用错误
        print(f"Error retrieving worklogs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve add logs.")


@router.get('/worklogs/show', status_code=status.HTTP_200_OK)
async def show_worklogs(request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        # 获取 token 并验证用户身份
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # 解析 token 并获取 user_uuid
        try:
            token = token.split(" ")[1]
        except IndexError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format")

        user_uuid = await get_current_user(token, db)
        if not user_uuid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        # 获取当前用户的所有工作日志
        results = await worklog_service.get_all_user_worklogs(db, user_uuid)
        if not results:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No worklogs found")

        # 构建响应数据，包括每条日志对应的用户名
        logs = []
        for result in results:
            log_data = WorkLogResponse.from_orm(result).dict()
            user = await user_service.get_user_by_uuid(db, result.user_uuid)
            if user:
                log_data['user_name'] = user.name
            else:
                log_data['user_name'] = "Unknown User"  # 如果用户不存在，使用默认值
            logs.append(log_data)

        return templates.TemplateResponse('showlogs.html', {"request": request, "logs": logs})

    except HTTPException as http_exc:
        raise http_exc  # 重新抛出已知 HTTP 异常

    except Exception as e:
        # 打印异常信息并返回通用错误
        print(f"Error retrieving worklogs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve work logs.")


# Create WorkLog
@router.post("/worklogs/", response_model=WorkLogResponse, status_code=status.HTTP_201_CREATED)
async def create_worklog(worklog: WorkLogCreate, db: AsyncSession = Depends(get_db_session)):
    return await worklog_service.create_worklog(db, worklog.model_dump())


# Get WorkLog by ID
@router.get("/worklogs/by-id/{worklog_id}", response_model=WorkLogResponse)
async def get_worklog_by_id(worklog_id: int, db: AsyncSession = Depends(get_db_session), _: None = Depends(get_current_user)):
    db_worklog = await worklog_service.get_worklog_by_id(db, worklog_id)
    if db_worklog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkLog not found")
    return db_worklog


# Get WorkLog by UUID
@router.get("/worklogs/by-uuid/{worklog_uuid}", response_model=WorkLogResponse)
async def get_worklog_by_uuid(worklog_uuid: str, db: AsyncSession = Depends(get_db_session), _: None = Depends(get_current_user)):
    db_worklog = await worklog_service.get_worklog_by_uuid(db, worklog_uuid)
    if db_worklog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkLog not found")
    return db_worklog


# Edit WorkLog by UUID
@router.put("/worklogs/by-uuid/{worklog_uuid}", response_model=WorkLogResponse)
async def edit_worklog_by_uuid(worklog_uuid: str, update_data: WorkLogUpdate, db: AsyncSession = Depends(get_db_session), _: None = Depends(get_current_user)):
    worklog = await worklog_service.edit_worklog_by_uuid(db, worklog_uuid, update_data.model_dump())
    if worklog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkLog not found")
    return worklog


# Get All WorkLogs
@router.get("/worklogs/", response_model=list[WorkLogResponse])
async def get_all_worklogs(db: AsyncSession = Depends(get_db_session), _: None = Depends(get_current_user)):
    return await worklog_service.get_all_worklogs(db)
