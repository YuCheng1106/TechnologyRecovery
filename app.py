import asyncio
import json
import time
from dependencies import get_current_user
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routes import user_routes, worklog_routes
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
router = APIRouter()
# 注册路由
app.include_router(user_routes.router, tags=["users"])
app.include_router(worklog_routes.router, tags=["workLogs"])

app.mount("/static", StaticFiles(directory="static"), name="static")

# 配置模板路径
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get('/login')
async def login(request: Request):
    """渲染登录页面。"""
    return templates.TemplateResponse('login.html', {"request": request})


# @app.get('/search')
# async def search_query(request: Request, user: User = Depends(get_current_user)):
#     """使用 query_embedding 函数处理搜索查询。"""
#     query = request.query_params.get('q')
#     if not query:
#         raise HTTPException(status_code=400, detail="搜索内容不能为空")
#     else:
#         results = await query_embedding(query)
#
#         # 处理结果，将空格替换为换行符，并为关键词添加样式
#         formatted_results = []
#         for result, similarity in results:
#             for keyword in ["时间：", "解决问题：", "解决方法：", "解决效果："]:
#                 result = result.replace(keyword, f'<br>{keyword}')
#             formatted_result = result.replace(" ", "<br>")
#             formatted_results.append((formatted_result, similarity))
#
#         # 按相似度排序并提取前3个工作日志内容
#         top_logs = [res[0] for res in sorted(formatted_results, key=lambda x: x[1], reverse=True)[:3]]
#
#         print(f"Query: {query}, Results: {top_logs}")
#
#     return templates.TemplateResponse('results.html', {"request": request, "query": query,
#                                                        "results": [r[0] for r in formatted_results]})


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
