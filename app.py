import asyncio
import json
import time

import aiomysql
import mysql.connector
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routes import user_routes, worklog_routes
from dataembedding import process_logs
from formatter import process_and_store_log
from search import query_embedding
from utils import initialize_model

# 加载 .env 文件中的所有变量
load_dotenv()

app = FastAPI()

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头部
)

# 注册路由
app.include_router(user_routes.router, tags=["users"])
app.include_router(worklog_routes.router, tags=["workLogs"])

app.mount("/static", StaticFiles(directory="static"), name="static")
# 配置模板路径
templates = Jinja2Templates(directory="templates")

# 数据库连接参数
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'techsearch',
    'db': 'logdb',
    'charset': 'utf8mb4',
    'autocommit': True
}

@app.on_event("startup")
async def startup():
    """在应用程序启动时加载模型"""
    await initialize_model()

@app.get('/')
async def home(request: Request):
    """渲染主页。"""
    return templates.TemplateResponse('index.html', {"request": request})

@app.get('/login')
async def login(request: Request):
    """渲染登录页面。"""
    return templates.TemplateResponse('login.html', {"request": request})

@app.get('/search')
async def search_query(request: Request):
    """使用 query_embedding 函数处理搜索查询。"""
    query = request.query_params.get('q')
    if not query:
        results = []
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

    return templates.TemplateResponse('results.html', {"request": request, "query": query, "results": [r[0] for r in formatted_results]})

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
async def showlogs(request: Request):
    """获取数据库中的日志数据并返回。"""
    db, cursor = await c1onnect_to_db()
    if not db or not cursor:
        raise HTTPException(status_code=500, detail="无法连接到数据库")

    try:
        query = "SELECT * FROM logs2"
        await cursor.execute(query)
        results = await cursor.fetchall()

        logs = [dict(result) for result in results]
        return templates.TemplateResponse('showlogs.html', {"request": request, "logs": logs})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await cursor.close()
        db.close()

@app.get('/addlogs')
async def addlogs(request: Request):
    """渲染添加日志页面。"""
    name = "张三"
    return templates.TemplateResponse('addlogs.html', {"request": request, "username": name})

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

    parts = split_text_by_double_newlines(text)

    for i, part in enumerate(parts, start=1):
        retries = 0
        max_retries = 2

        while retries <= max_retries:
            try:
                query = "INSERT INTO logs2 (工作日志) VALUES (%s)"
                cursor.execute(query, (part,))
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
async def submit_log(request: Request):
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
        "bot_id": "7400423003794227254",
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
