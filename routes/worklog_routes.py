import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from divide import insert_log_parts
from search import query_embedding
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
from utils import get_shared_state
from embedding import get_sentence_embedding
from search import Embeds
from sqlalchemy.ext.asyncio import AsyncSession
from divide import insert_log_parts
from sqlalchemy import insert
from models.WorklogVector_model import WorklogVector

router = APIRouter()

templates = Jinja2Templates(directory="templates")


def clean_part(part):
    """清理段落，删除姓名和时间，只保留有用的标签"""
    lines = part.splitlines()
    cleaned_lines = []
    has_valid_tag = False  # 标记是否包含有效标签

    # 遍历每一行，删除姓名和时间
    for line in lines:
        if line.startswith("姓名：") or line.startswith("时间："):
            continue
        elif line.startswith("解决问题：") or line.startswith("解决方法：") or line.startswith("解决效果："):
            # 处理“解决问题：”前的内容
            if "解决问题：" in line:
                line = line.split("解决问题：", 1)[1]
                cleaned_lines.append("解决问题：" + line)
                has_valid_tag = True
            elif "解决方法：" in line:
                line = line.split("解决方法：", 1)[1]
                cleaned_lines.append("解决方法：" + line)
                has_valid_tag = True
            elif "解决效果：" in line:
                line = line.split("解决效果：", 1)[1]
                cleaned_lines.append("解决效果：" + line)
                has_valid_tag = True

    # 只返回包含有效标签的段落
    return '\n'.join(cleaned_lines) if has_valid_tag else None



def split_text_by_double_newlines(text):
    """按双换行符分割文本，去除前后空白部分"""
    parts = []
    current_part = []

    for line in text.splitlines():
        if line.strip() == '' and current_part:
            cleaned_part = clean_part('\n'.join(current_part))

            if cleaned_part is not None:  # 检查cleaned_part是否为None
                # 删除“解决问题：”之前的内容
                if "解决问题：" in cleaned_part:
                    cleaned_part = cleaned_part.split("解决问题：", 1)[1]
                    cleaned_part = "解决问题：" + cleaned_part

                print(cleaned_part)
                parts.append(cleaned_part)
            current_part = []
        else:
            current_part.append(line)

    if current_part:
        cleaned_part = clean_part('\n'.join(current_part))

        if cleaned_part is not None:  # 检查cleaned_part是否为None
            # 删除“解决问题：”之前的内容
            if "解决问题：" in cleaned_part:
                cleaned_part = cleaned_part.split("解决问题：", 1)[1]
                cleaned_part = "解决问题：" + cleaned_part

            parts.append(cleaned_part)

    return parts



async def parse_worklog_part(part: str, user_uuid: str) -> dict:
    # 将 part 字符串分割为多行
    # lines = part.split('\n')
    worklog_data = {
        "user_uuid": user_uuid,
        "group_uuid": None,
        "content": part,
        "effect": None,
        "embedding": None
    }
    # print(worklog_data["content"])

    # for line in lines:
    #     if line.startswith("解决问题："):
    #         worklog_data["content"] = line.split("解决问题：")[1]
    #     elif line.startswith("解决效果："):
    #         worklog_data["effect"] = line.replace("解决效果：", "").strip()

    model = get_shared_state()
    embed = await get_sentence_embedding(part, model['embedding_model'])
    worklog_data["embedding"] = embed.tobytes()

    return worklog_data


async def divide(text):
    """分割并插入日志文本"""
    success = await insert_log_parts(text)
    return success


@router.post('/worklogs/submit', status_code=status.HTTP_201_CREATED)
async def submit_log(worklog: WorkLogSubmit, db: AsyncSession = Depends(get_db_session), uid=Depends(get_current_user)):
    processed_result = await process_and_store_log(worklog.text)
    print(processed_result)
    parts = split_text_by_double_newlines(processed_result)
    print(parts)
    # success = await divide(processed_result)
    # if not success:
    #     return;

    # parts = split_text_by_double_newlines(processed_result)
    for i, part in enumerate(parts, start=1):
        retries = 0
        max_retries = 2
        # 解析 part 字符/串
        worklog_data = await parse_worklog_part(part, uid)
        print(worklog_data)
        worklog_data["group_uuid"] = worklog.group_uuid
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
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        try:
            token = token.split(" ")[1]
        except IndexError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format")

        user_uuid = await get_current_user(token, db)
        if not user_uuid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        user = await user_service.get_user_by_uuid(db, user_uuid)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        usergroups = await usergroup_service.get_all_groups_for_user(db, user_uuid)

        group_uuids = [usergroup.group_uuid for usergroup in usergroups]
        groups = []
        if group_uuids:
            group_query = select(Group).where(Group.uuid.in_(group_uuids))
            result = await db.execute(group_query)
            group_objects = result.scalars().all()

            groups = []
            for group in group_objects:
                group_data = GroupResponse.from_orm(group).dict()
                if isinstance(group_data.get('create_datetime'), datetime):
                    group_data['create_datetime'] = group_data['create_datetime'].isoformat()
                if isinstance(group_data.get('update_datetime'), datetime):
                    group_data['update_datetime'] = group_data['update_datetime'].isoformat()

                groups.append(group_data)

        return templates.TemplateResponse('addlogs.html', {"request": request, "username": user.name, "groups": groups})

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
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

        usergroups = await usergroup_service.get_all_groups_for_user(db, user_uuid)

        # 优化获取群组信息
        group_uuids = [usergroup.group_uuid for usergroup in usergroups]
        groups = []
        if group_uuids:
            group_query = select(Group).where(Group.uuid.in_(group_uuids))
            result = await db.execute(group_query)
            group_objects = result.scalars().all()

            # 将每个群组对象转为 GroupResponse 并处理 datetime 对象
            groups = []
            for group in group_objects:
                group_data = GroupResponse.from_orm(group).dict()

                # 将 datetime 转换为 ISO 格式的字符串
                if isinstance(group_data.get('create_datetime'), datetime):
                    group_data['create_datetime'] = group_data['create_datetime'].isoformat()
                if isinstance(group_data.get('update_datetime'), datetime):
                    group_data['update_datetime'] = group_data['update_datetime'].isoformat()

                groups.append(group_data)

        # 获取用户信息
        user = await user_service.get_user_by_uuid(db, user_uuid)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # 根据用户角色选择获取工作日志的方法
        if user.role == 'admin':
            results = await worklog_service.get_all_worklogs(db)
        else:
            results = await worklog_service.get_all_user_worklogs(db, user_uuid)

        # 构建响应数据，包括每条日志对应的用户名
        logs = []
        for result in results:
            log_data = WorkLogResponse.from_orm(result).dict()

            # 从每条工作日志中获取 user_uuid
            user_uuid_for_log = log_data['user_uuid']  # 假设日志对象中有 user_uuid 字段

            # 获取用户信息
            user_for_log = await user_service.get_user_by_uuid(db, user_uuid_for_log)

            log_data['user_name'] = user_for_log.name if user_for_log else "Unknown User"  # 如果用户不存在则使用默认值

            # 格式化日期时间
            if isinstance(log_data.get('create_datetime'), datetime):
                log_data['create_datetime'] = log_data['create_datetime'].isoformat()
            if isinstance(log_data.get('update_datetime'), datetime):
                log_data['update_datetime'] = log_data['update_datetime'].isoformat()

            logs.append(log_data)

        return templates.TemplateResponse('showlogs.html',
                                          {"request": request, "logs": logs, "groups": groups, "user_uuid": user.uuid,
                                           "role": user.role})

    except HTTPException as http_exc:
        raise http_exc  # 重新抛出已知 HTTP 异常

    except Exception as e:
        # 打印异常信息并返回通用错误
        print(f"Error retrieving worklogs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve work logs.")


@router.get('/worklogs/search')
async def search_query(request: Request, db: AsyncSession = Depends(get_db_session)):
    results = await worklog_service.get_all_worklogs(db)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No worklogs found")

    # 构建响应数据，包括每条日志对应的用户名
    embeds = []
    for result in results:
        log_data = WorkLogResponse.from_orm(result).dict()
        user = await user_service.get_user_by_uuid(db, result.user_uuid)
        if user:
            log_data['user_name'] = user.name
        else:
            log_data['user_name'] = "Unknown User"  # 如果用户不存在，使用默认值
        if isinstance(log_data.get('create_datetime'), datetime):
            log_data['create_datetime'] = log_data['create_datetime'].isoformat()
        if isinstance(log_data.get('update_datetime'), datetime):
            log_data['update_datetime'] = log_data['update_datetime'].isoformat()
        embeds.append(Embeds(log_data, result.embedding, 0))

    query = request.query_params.get('q')
    if not query:
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    else:
        results = await query_embedding(query, embeds)

        # select_logs = [results[i].data for i in range(3)]
        select_logs = [results[i].data for i in range(min(3, len(results)))]

    return templates.TemplateResponse('results.html', {"request": request, "query": query, "logs": select_logs})


# Create WorkLog
@router.post("/worklogs/", response_model=WorkLogResponse, status_code=status.HTTP_201_CREATED)
async def create_worklog(worklog: WorkLogCreate, db: AsyncSession = Depends(get_db_session)):
    return await worklog_service.create_worklog(db, worklog.model_dump())


# Get WorkLog by ID
@router.get("/worklogs/by-id/{worklog_id}", response_model=WorkLogResponse)
async def get_worklog_by_id(worklog_id: int, db: AsyncSession = Depends(get_db_session),
                            _: None = Depends(get_current_user)):
    db_worklog = await worklog_service.get_worklog_by_id(db, worklog_id)
    if db_worklog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkLog not found")
    return db_worklog


# Get WorkLog by UUID
@router.get("/worklogs/by-uuid/{worklog_uuid}", response_model=WorkLogResponse)
async def get_worklog_by_uuid(worklog_uuid: str, db: AsyncSession = Depends(get_db_session),
                              _: None = Depends(get_current_user)):
    db_worklog = await worklog_service.get_worklog_by_uuid(db, worklog_uuid)
    if db_worklog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkLog not found")
    return db_worklog


# Edit WorkLog by UUID
@router.put("/worklogs/by-uuid/{worklog_uuid}", response_model=WorkLogResponse)
async def edit_worklog_by_uuid(worklog_uuid: str, update_data: WorkLogUpdate,
                               db: AsyncSession = Depends(get_db_session), _: None = Depends(get_current_user)):
    worklog = await worklog_service.edit_worklog_by_uuid(db, worklog_uuid, update_data.model_dump())
    if worklog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkLog not found")
    return worklog


# Get All WorkLogs
@router.get("/worklogs/", response_model=list[WorkLogResponse])
async def get_all_worklogs(db: AsyncSession = Depends(get_db_session), _: None = Depends(get_current_user)):
    return await worklog_service.get_all_worklogs(db)
