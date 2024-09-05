import asyncio
import json
import time

import aiomysql
import mysql.connector
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends, status, Body, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from routes import user_routes, worklog_routes
from dataembedding import process_logs
from formatter import process_and_store_log
from search import query_embedding
from services.database import get_db_session
from models.user_model import User  # 如果你有 User 模型类
from schemas.user_schemas import TokenData  # 确保有 TokenData 定义在 schemas 中
from models.group_model import GroupModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import asyncmy

from utils import initialize_model
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# 加载 .env 文件中的所有变量
load_dotenv()

app = FastAPI()
DATABASE_URL = "mysql+asyncmy://root:liweiran@localhost/technologyrecovery"

SECRET_KEY = "your-secret-key"  # 替换为你的密钥
ALGORITHM = "HS256"
timetoday = datetime.today().strftime('%Y-%m-%d')
# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头部
)
router = APIRouter()
# 注册路由
app.include_router(user_routes.router, tags=["users"])
app.include_router(worklog_routes.router, tags=["workLogs"])
# app.mount("/static", StaticFiles(directory="static"), name="static")
# 配置模板路径
templates = Jinja2Templates(directory="templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 数据库连接参数
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'liweiran',
    'db': 'technologyrecovery',
    'charset': 'utf8mb4',
    'autocommit': True
}
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


@router.get("/groups/by-role")
def get_groups_by_role(role: str, db: Session = Depends(get_db_session)):
    if role == "admin":
        groups = db.query(Group).filter(Group.admin_group.isnot(None)).all()
    elif role == "user":
        groups = db.query(Group).filter(Group.user_group.isnot(None)).all()
    else:
        return []

    return [{"id": group.id, "name": group.name, "standard": group.standard} for group in groups]


async def get_user(username: str, db: AsyncSession):
    # 具体实现取决于你使用的 ORM，如 SQLAlchemy
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalar_one_or_none()


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    print(f"Decoded username from token: {username}")
    user = await get_user(username=token_data.username, db=db)
    if user is None:
        raise credentials_exception

    print(f"User found in database: {user.username}")
    return user


global_username = None


@app.post("/your-endpoint")
async def your_function(request: Request):
    form_data = await request.form()
    global_name = form_data.get("global_name")
    role = form_data.get("role")

    if not global_name or not role:
        raise HTTPException(status_code=400, detail="Missing user information")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 异步生成器函数
async def get_db_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


# 数据模型定义
class GroupModel(BaseModel):
    id: int
    name: str
    worklog_standard: str


class Group(BaseModel):
    id: int
    name: str
    worklog_standard: str
    admins: List[str]
    users: List[str]


@app.get("/manage_group", response_class=HTMLResponse)
async def manage_group_page(request: Request, db: AsyncSession = Depends(get_db_session)):
    # result = await db.execute(select(GroupModel))
    # groups = result.scalars().all()  # 从数据库中获取所有的组
    # return templates.TemplateResponse("manage_group.html", {"request": request, "groups": groups})
    return templates.TemplateResponse("manage_group.html", {"request": request})


@app.post("/manage_group/update", response_class=HTMLResponse)
async def update_group_standard(group_id: int, new_standard: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(GroupModel).filter(GroupModel.id == group_id))
    group = result.scalars().first()
    if group:
        group.worklog_standard = new_standard
        await db.commit()
    return RedirectResponse(url="/manage_group", status_code=303)


@app.get("/api/groups", response_model=List[Group])
async def get_groups(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(GroupModel))
    groups = result.scalars().all()
    return [{"id": g.id, "name": g.name} for g in groups]


@app.get("/api/groups/{group_id}", response_model=Group)
async def get_group(group_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(GroupModel).filter(GroupModel.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 这里需要根据实际的 `User` 模型来调整代码
    # result_admins = await db.execute(select(User).filter(User.role == 'admin', User.group_id == group_id))
    # admins = result_admins.scalars().all()
    #
    # result_users = await db.execute(select(User).filter(User.role == 'user', User.group_id == group_id))
    # users = result_users.scalars().all()

    admins = [admin.name for admin in group.admins]
    users = [user.name for user in group.users]

    return {
        "id": group.id,
        "name": group.name,
        "worklog_standard": group.worklog_standard,
        # "admins": [admin.name for admin in admins],
        # "users": [user.name for user in users]
        "admins": admins,
        "users": users
    }


@app.put("/api/groups/{group_id}/worklog-standard")
async def update_worklog_standard(group_id: int, worklog_standard: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(GroupModel).filter(GroupModel.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    group.worklog_standard = worklog_standard
    await db.commit()
    return {"message": "Worklog standard updated successfully"}


@app.post("/api/groups/{group_id}/add-users")
async def add_users_to_group(group_id: int, role: str, user_ids: List[int], db: AsyncSession = Depends(get_db_session)):
    # 确保组存在
    result = await db.execute(select(GroupModel).filter(GroupModel.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 更新用户的组关系
    if role in ['admin', 'user']:
        for user_id in user_ids:
            user_result = await db.execute(select(User).filter(User.id == user_id))
            user = user_result.scalars().first()
            if user:
                user.group_id = group_id
                user.role = role
        await db.commit()
    else:
        raise HTTPException(status_code=400, detail="Invalid role")

    return {"message": f"Users added to {role} group successfully"}


class Username(BaseModel):
    username: str


@app.get("/some-endpoint")
async def some_function(db: AsyncSession = Depends(get_db_session)):
    # 在这里使用 db 执行异步数据库操作
    user = await get_user("some_username", db)
    return user


@app.post("/users/store_username")
async def store_username(data: dict):
    global global_username
    global_username = data.get("username")
    print(f"Received username: {data.get('username')}")
    print(f"Global username stored: {global_username}")  # 添加日志
    return {"message": "用户名已存储"}


@app.on_event("startup")
async def startup():
    global timetoday
    timetoday = datetime.today().strftime('%Y-%m-%d')
    """在应用程序启动时加载模型"""
    await initialize_model()


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/users/login")
async def login(username: str, password: str):
    if username == "valid_username" and password == "valid_password":
        access_token = create_access_token(data={"sub": username})
        return {
            "token": {
                "access_token": access_token
            },
            "user": {
                "uuid": "user-uuid"
            }
        }
    raise HTTPException(status_code=400, detail="用户名或密码错误")


@app.get('/login')
async def login(request: Request):
    """渲染登录页面。"""
    return templates.TemplateResponse('login.html', {"request": request})


@app.get('/search')
async def search_query(request: Request, user: User = Depends(get_current_user)):
    """使用 query_embedding 函数处理搜索查询。"""
    query = request.query_params.get('q')
    if not query:
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    else:
        results = await query_embedding(query)

        # 处理结果，将空格替换为换行符，并为关键词添加样式
        formatted_results = []
        for result, similarity in results:
            for keyword in ["时间：", "解决问题：", "解决方法：", "解决效果："]:
                result = result.replace(keyword, f'<br>{keyword}')
            formatted_result = result.replace(" ", "<br>")
            formatted_results.append((formatted_result, similarity))

        # 按相似度排序并提取前3个工作日志内容
        top_logs = [res[0] for res in sorted(formatted_results, key=lambda x: x[1], reverse=True)[:3]]

        print(f"Query: {query}, Results: {top_logs}")

    return templates.TemplateResponse('results.html', {"request": request, "query": query,
                                                       "results": [r[0] for r in formatted_results]})


async def run_sync_task(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)


async def c1onnect_to_db():
    """异步连接到MySQL数据库"""
    try:
        connection = await aiomysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            db=DB_CONFIG['db'],
            charset=DB_CONFIG['charset'],
            autocommit=DB_CONFIG['autocommit']
        )
        cursor = await connection.cursor(aiomysql.DictCursor)
        print("成功连接到数据库")
        return connection, cursor
    except aiomysql.MySQLError as err:
        print(f"连接数据库失败: {err}")
        return None, None


@app.get('/showlogs')
async def showlogs(request: Request, role: str = Body(...), user: User = Depends(get_current_user)):
    """获取数据库中的日志数据并返回。"""
    db, cursor = await c1onnect_to_db()
    if not db or not cursor:
        raise HTTPException(status_code=500, detail="无法连接到数据库")

    try:
        query = "SELECT * FROM worklog WHERE role = %s"
        await cursor.execute(query, (user.role,))
        results = await cursor.fetchall()

        logs = [dict(result) for result in results]
        return templates.TemplateResponse('showlogs.html', {"request": request, "logs": logs, "user": user})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await cursor.close()
        db.close()


@app.get('/addlogs')
async def addlogs(request: Request, role: str = Body(...), user: User = Depends(get_current_user)):
    """渲染添加日志页面。"""
    if not user:
        return RedirectResponse(url='/login', status_code=302)  # 如果用户未登录，重定向到登录页面

    name = global_username
    return templates.TemplateResponse('addlogs.html',
                                      {"request": request, "username": name, "role": role, "user": user})


async def connect_to_db():
    """异步连接到MySQL数据库"""
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()
        print("成功连接到数据库")
        return db, cursor
    except mysql.connector.Error as err:
        print(f"连接数据库失败: {err}")
        return None, None


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


async def insert_log_parts(text):
    """将分割后的日志部分插入数据库"""
    db, cursor = await connect_to_db()
    if not db or not cursor:
        return False

        # 从 user 表中查找对应 global_username 的 uuid
    try:
        cursor.execute("SELECT uuid FROM user WHERE name = %s", (global_username,))
        result = cursor.fetchone()
        if result:
            user_uuid = result[0]  # 获取用户的 uuid
        else:
            print(f"未找到用户 {global_username} 的 uuid")
            cursor.close()
            db.close()
            return False
    except mysql.connector.Error as err:
        print(f"查询 uuid 失败: {err}")
        cursor.close()
        db.close()
        return False

    parts = split_text_by_double_newlines(text)

    for i, part in enumerate(parts, start=1):
        retries = 0
        max_retries = 2

        while retries <= max_retries:
            try:
                query = "INSERT INTO worklog (工作日志,姓名,时间, uuid) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (part, global_username,timetoday, user_uuid))
                db.commit()
                print(f"部分{i}日志数据已成功插入到数据库")
                break
            except mysql.connector.Error as err:
                retries += 1
                if retries > max_retries:
                    print(f"插入部分{i}数据失败: {err}")
                    break
                print(f"重试插入部分{i}数据...")
                await asyncio.sleep(5)

    cursor.close()
    db.close()
    return True


async def divide(text):
    """分割并插入日志文本"""
    success = await insert_log_parts(text)
    return success


async def process_and_divide_log(log_text):
    processed_result = process_and_store_log(log_text)
    success = await divide(processed_result)
    return success


async def dbembeddingrun():
    await process_logs()


@app.post('/submit_log')
async def submit_log(request: Request, current_user: str = Depends(get_current_user)):
    """处理日志提交请求"""
    data = await request.json()
    log_text = data.get('logData')

    if not log_text:
        raise HTTPException(status_code=400, detail="日志数据是必需的")

    try:
        success = await process_and_divide_log(log_text)
        await dbembeddingrun()

        if success:
            return JSONResponse({"success": "日志已提交并处理成功"}, status_code=200)
        else:
            return JSONResponse({"error": "日志处理失败"}, status_code=500)
    except HTTPException as e:
        return JSONResponse({"error": f"处理请求时发生错误: {str(e)}"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": f"处理请求时发生错误: {str(e)}"}, status_code=500)


def check(text: str):
    url = 'https://api.coze.cn/open_api/v2/chat'
    headers = {
        'Authorization': 'Bearer pat_J0kTR3d58Z8bWcFpUisvOMvrOToUDg6aVIk76yoraRCKapOt8jlHa6ghBbXO5a0h',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'api.coze.cn',
        'Connection': 'keep-alive'
    }

    data = {
        "conversation_id": "1234",
        "bot_id": "7410333069560905743",
        # "bot_id": "7400423003794227254",
        "user": "29032201862555",
        "query": text,
        "stream": False
    }

    for _ in range(3):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            response_data = response.json()
            messages = response_data.get("messages", [])
            for message in messages:
                if message.get("role") == "assistant" and message.get("type") == "answer":
                    return message.get("content")
            return None
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            time.sleep(5)

    raise ConnectionError("API请求失败: 超过最大重试次数")


@app.post('/check_text')
async def check_text(request: Request):
    try:
        data = await request.json()
        text = data.get('text')
        checked_text = await asyncio.to_thread(check, text)
        return JSONResponse({'checkedText': checked_text})
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@app.post('/api/ask')
async def api_ask(request: Request):
    """处理API请求并返回响应。"""
    data = await request.json()
    text = data.get('question')
    if not text:
        return JSONResponse({"error": "No query provided"}, status_code=400)

    top_logs = data.get('top_logs', [])
    background_text = "请以" + "、".join(
        [f"文本{i + 1}：" + log for i, log in enumerate(top_logs)]) + "为背景，回答“" + text + "”"

    url = 'https://api.coze.cn/open_api/v2/chat'
    headers = {
        'Authorization': 'Bearer pat_J0kTR3d58Z8bWcFpUisvOMvrOToUDg6aVIk76yoraRCKapOt8jlHa6ghBbXO5a0h',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'api.coze.cn',
        'Connection': 'keep-alive'
    }

    payload = {
        "conversation_id": "123",
        "bot_id": "7398757473089716261",
        "user": "29032201862555",
        "query": background_text,
        "stream": False
    }

    for _ in range(3):
        try:
            response = await asyncio.to_thread(requests.post, url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            response_data = response.json()
            messages = response_data.get("messages", [])
            for message in messages:
                if message.get("role") == "assistant" and message.get("type") == "answer":
                    return JSONResponse({"answer": message.get("content")})
            return JSONResponse({"error": "No valid response received"}, status_code=500)
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            await asyncio.sleep(5)

    return JSONResponse({"error": "API请求失败: 超过最大重试次数"}, status_code=500)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
