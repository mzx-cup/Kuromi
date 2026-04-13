from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import requests
import json
import re
import os
import subprocess
import tempfile
import hashlib
import uvicorn
import logging
from datetime import datetime
import time
import db as database
import pymysql
import asyncio

from state import ChatRequestV2, ChatResponseV2, StudentState, StreamChatRequest, CognitiveStyle, DialogueRole
from proactive_tutor import (
    get_connection_manager, get_proactive_tutor,
    ProactiveMessage, ProactiveMessageType, MessagePriority,
    StruggleEvent, ConnectionManager,
)
from agents import (
    MasterController, create_default_controller,
    ProfilerAgent, PlannerAgent, DocumentGeneratorAgent,
    MindmapGeneratorAgent, ExerciseGeneratorAgent, VideoContentAgent,
    ResourcePushAgent, EvaluationAgent, SocraticEvaluatorAgent, BaseAgent,
)
from agent_utils import (
    build_state_from_request, save_state, load_state,
    list_student_contexts, extract_final_content, extract_resources,
    extract_evaluation, format_workflow_logs, Timer,
)
from llm_stream import call_llm_stream, call_llm_stream_with_log, call_llm_async, close_http_client
from task_manager import get_task_manager, dispatch_resource_tasks, TaskStatus
from config import settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, "html")
CSS_DIR = os.path.join(BASE_DIR, "css")
JS_DIR = os.path.join(BASE_DIR, "js")
STATIC_DIR = os.path.join(BASE_DIR, "static")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

app = FastAPI()

logger = logging.getLogger("starlearn.stream")
req_logger = logging.getLogger("starlearn.request")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
if not req_logger.handlers:
    rh = logging.StreamHandler()
    rh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    req_logger.addHandler(rh)
    req_logger.setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    try:
        response = await call_next(request)
    except Exception as exc:
        req_logger.error(f"{request.method} {request.url.path} -> 500 (internal: {exc})")
        raise
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    if response.status_code >= 400:
        req_logger.warning(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.0f}ms)")
    else:
        req_logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.0f}ms)")
    return response


@app.on_event("startup")
async def startup_debug():
    all_paths = [r.path for r in app.routes if hasattr(r, 'path')]
    v2_paths = [p for p in all_paths if 'v2' in p or 'textbook' in p]
    logger.info(f"[Startup] Total routes: {len(all_paths)}, v2/textbook: {len(v2_paths)}")


@app.on_event("shutdown")
async def shutdown_event():
    await close_http_client()


def coerce_learning_path(value):
    """数据库 path_json 常为字符串；前端也可能误传对象。统一为 list[dict]。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        return []
    if isinstance(value, dict):
        return [value]
    return []


def coerce_profile_dict(value):
    if value is None or not isinstance(value, dict):
        return {}
    return value


class ChatRequest(BaseModel):
    userText: str
    currentProfile: dict = {}
    currentPath: list = []
    interactionCount: int = 0
    codePracticeTime: int = 0
    socraticPassRate: float = 0.0

    @field_validator("currentPath", mode="before")
    @classmethod
    def _path_must_be_list(cls, v):
        return coerce_learning_path(v)

    @field_validator("currentProfile", mode="before")
    @classmethod
    def _profile_must_be_dict(cls, v):
        return coerce_profile_dict(v)

class CodeRunRequest(BaseModel):
    code: str
    language: str = "python"

class CodeGradeRequest(BaseModel):
    code: str
    task: str
    language: str = "python"
    currentProfile: dict = {}

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UpdateProfileRequest(BaseModel):
    username: str = ""
    avatar: str = ""
    currentTask: str = ""
    nickname: str = ""

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

TEXTBOOK_DEEP_LINKS = {
    "大数据处理技术": {
        "platform": "hep",
        "baseUrl": "https://ebook.hep.com.cn",
        "bookId": "5d5f8a3e6d8f4a3c9c7b6e5d",
        "chapterUrl": "/reader?bookId={bookId}&chapterId={chapterId}&page={page}"
    },
    "实验指导书": {
        "platform": "zhishikoo",
        "baseUrl": "https://www.zhishikoo.com",
        "bookId": "exp-guide-2024",
        "chapterUrl": "/book/{bookId}/chapter/{chapterId}?page={page}"
    },
    "大数据导论": {
        "platform": "ucdrs",
        "baseUrl": "http://www.ucdrs.superlib.net",
        "bookId": "bigdata-intro-2024",
        "chapterUrl": "/search?sw={bookId}&page={page}"
    }
}

KNOWLEDGE_BASE = {
    "hadoop": {
        "content": "Hadoop的核心是HDFS和MapReduce。HDFS采用Master/Slave架构，NameNode负责管理文件系统的元数据（命名空间、数据块映射），DataNode负责实际存储数据块。MapReduce将计算分为Map阶段（数据切分与局部处理）和Reduce阶段（汇总聚合）。",
        "source": "《大数据处理技术》教材P12-P18",
        "keywords": ["hadoop", "hdfs", "mapreduce", "分布式", "namenode", "datanode"],
        "textbook": "大数据处理技术",
        "chapterId": "ch2-hadoop-overview",
        "startPage": 12,
        "endPage": 18
    },
    "hdfs": {
        "content": "HDFS（Hadoop Distributed File System）是Hadoop的分布式文件系统。写入流程：Client向NameNode请求上传→NameNode检查权限和目录→NameNode返回DataNode列表→Client建立Pipeline逐个传输数据包→DataNode确认后向NameNode汇报。读取流程：Client向NameNode获取数据块位置→直接从最近的DataNode读取。默认副本数为3。",
        "source": "《大数据处理技术》教材P15-P20",
        "keywords": ["hdfs", "文件系统", "写入", "读取", "副本", "数据块", "block"],
        "textbook": "大数据处理技术",
        "chapterId": "ch2-hdfs-detail",
        "startPage": 15,
        "endPage": 20
    },
    "mapreduce": {
        "content": "MapReduce编程模型：Map阶段将输入数据拆分为独立的数据块并行处理，输出<key,value>中间结果；Shuffle阶段按Key排序分组传输给Reducer；Reduce阶段对同一Key的所有Value执行聚合操作。核心思想：分而治之、数据本地化计算（移动计算而非移动数据）。",
        "source": "《大数据处理技术》教材P25-P32",
        "keywords": ["mapreduce", "map", "reduce", "shuffle", "分而治之", "键值对"],
        "textbook": "大数据处理技术",
        "chapterId": "ch3-mapreduce",
        "startPage": 25,
        "endPage": 32
    },
    "flink": {
        "content": "Flink是第三代分布式计算框架，核心优势是原生流处理（逐条处理而非微批）。Flink包含三种核心窗口：Tumbling Window(滚动窗口，无重叠)、Sliding Window(滑动窗口，有重叠)、Session Window(会话窗口，基于活跃度间隔)。Checkpoint机制保障Exactly-Once语义。",
        "source": "《大数据处理技术》教材P45-P52",
        "keywords": ["flink", "流处理", "窗口", "tumbling", "sliding", "session", "checkpoint"],
        "textbook": "大数据处理技术",
        "chapterId": "ch5-flink",
        "startPage": 45,
        "endPage": 52
    },
    "spark": {
        "content": "Spark基于RDD（弹性分布式数据集）的内存计算框架。RDD特性：不可变、分区、容错（Lineage血统机制）。Spark SQL提供DataFrame/Dataset API，Spark Streaming采用微批处理模型（DStream）。与MapReduce对比：Spark通过内存缓存减少磁盘IO，迭代计算性能提升10-100倍。",
        "source": "《大数据处理技术》教材P35-P44",
        "keywords": ["spark", "rdd", "内存计算", "dataframe", "streaming", "迭代"],
        "textbook": "大数据处理技术",
        "chapterId": "ch4-spark",
        "startPage": 35,
        "endPage": 44
    },
    "排序": {
        "content": "快速排序：平均O(n log n)，最坏O(n^2)，不稳定。归并排序：稳定，始终O(n log n)，需额外O(n)空间。堆排序：不稳定，O(n log n)，原地排序。在大数据场景中，外部排序（多路归并）是处理超大规模数据的核心方法。",
        "source": "《实验指导书》P8-P15",
        "keywords": ["排序", "快速排序", "归并排序", "堆排序", "时间复杂度"],
        "textbook": "实验指导书",
        "chapterId": "ch1-sorting",
        "startPage": 8,
        "endPage": 15
    },
    "nosql": {
        "content": "NoSQL数据库四大分类：键值存储(Redis)、列族存储(HBase)、文档存储(MongoDB)、图存储(Neo4j)。CAP定理：分布式系统最多同时满足一致性(C)、可用性(A)、分区容错性(P)中的两个。BASE理论是CAP的实践妥协：基本可用、软状态、最终一致性。",
        "source": "《大数据处理技术》教材P55-P62",
        "keywords": ["nosql", "redis", "hbase", "mongodb", "cap", "base", "键值", "列族"],
        "textbook": "大数据处理技术",
        "chapterId": "ch6-nosql",
        "startPage": 55,
        "endPage": 62
    },
    "zookeeper": {
        "content": "ZooKeeper是分布式协调服务，提供：命名服务、配置管理、集群管理、分布式锁。核心概念：ZNode（数据节点）、Watch机制（事件监听）、Leader选举（Paxos算法简化版ZAB协议）。HBase依赖ZooKeeper进行Master选举和Region定位。",
        "source": "《大数据处理技术》教材P22-P25",
        "keywords": ["zookeeper", "协调", "znode", "watch", "leader", "选举", "分布式锁"],
        "textbook": "大数据处理技术",
        "chapterId": "ch2-zookeeper",
        "startPage": 22,
        "endPage": 25
    }
}

def build_deep_link(textbook_name: str, chapter_id: str, page: int) -> str:
    link_config = TEXTBOOK_DEEP_LINKS.get(textbook_name)
    if not link_config:
        return "https://zh.hkr101.ru/"
    url = link_config["baseUrl"] + link_config["chapterUrl"].format(
        bookId=link_config["bookId"],
        chapterId=chapter_id,
        page=page
    )
    return url

def retrieve_knowledge(keywords: list):
    retrieved = []
    for kw in keywords:
        kw_lower = kw.lower()
        for key, doc in KNOWLEDGE_BASE.items():
            if key.lower() in kw_lower or any(k in kw_lower for k in doc["keywords"]):
                textbook_name = doc.get("textbook", "")
                chapter_id = doc.get("chapterId", "")
                start_page = doc.get("startPage", 1)
                deep_link = ""
                if textbook_name and chapter_id:
                    deep_link = build_deep_link(textbook_name, chapter_id, start_page)
                retrieved.append({
                    "content": doc["content"],
                    "source": doc["source"],
                    "deepLink": deep_link
                })
    if not retrieved:
        return "（教材库中未检索到特定内容，请依赖大模型自身知识储备）", [], []
    context = "\n\n".join([f"[Doc_Ref: {r['source']}] {r['content']}" for r in retrieved])
    sources = list(set([r["source"] for r in retrieved]))
    source_links = {}
    for r in retrieved:
        if r["source"] not in source_links and r["deepLink"]:
            source_links[r["source"]] = r["deepLink"]
    return context, sources, source_links

def call_llm(system_prompt: str, user_prompt: str, temperature=0.3):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.xunfei_api_key}"
    }
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }
    try:
        response = requests.post(settings.xunfei_api_url, headers=headers, json=payload, timeout=120)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="大模型接口请求超时，请稍后重试或检查网络")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"无法连接大模型接口: {str(e)}")

    if not response.ok:
        snippet = (response.text or "")[:800]
        raise HTTPException(
            status_code=502,
            detail=f"大模型接口返回 HTTP {response.status_code}。请检查 API Key、额度与网络。响应摘要: {snippet}",
        )

    try:
        body = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="大模型接口返回非 JSON，请检查服务地址与鉴权")

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        brief = json.dumps(body, ensure_ascii=False)[:600]
        raise HTTPException(status_code=502, detail=f"大模型响应格式异常（缺 choices/message），片段: {brief}")

def normalize_cognitive_style_for_routing(val):
    """画像里可能是中文（视觉型）或英文（visual），主控分发需要统一成英文码。"""
    if val is None:
        return "textual"
    s = str(val).strip().lower()
    if val in ("视觉型",) or "视觉" in str(val):
        return "visual"
    if val in ("实践型",) or "实践" in str(val) or s == "pragmatic":
        return "pragmatic"
    if val in ("文字型",) or "文字" in str(val) or s == "textual":
        return "textual"
    if s in ("visual", "pragmatic", "textual"):
        return s
    return "textual"


def extract_json(text, is_array=False):
    try:
        pattern = r'\[.*\]' if is_array else r'\{.*\}'
        match = re.search(pattern, text.replace('\n', ''), re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except:
        return _extract_json_truncated(text, is_array)


def _extract_json_truncated(text, is_array=False):
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 2:
            cleaned = parts[1].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    open_char = '[' if is_array else '{'
    close_char = ']' if is_array else '}'
    start = cleaned.find(open_char)
    if start == -1:
        return None

    depth = 0
    last_valid_close = -1
    for i in range(start, len(cleaned)):
        if cleaned[i] == open_char:
            depth += 1
        elif cleaned[i] == close_char:
            depth -= 1
            if depth == 0:
                last_valid_close = i
                break

    if last_valid_close > 0:
        try:
            return json.loads(cleaned[start:last_valid_close + 1])
        except json.JSONDecodeError:
            pass

    if depth > 0:
        for close_pos in range(len(cleaned) - 1, start, -1):
            if cleaned[close_pos] == close_char:
                candidate = cleaned[start:close_pos + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

        stacked = cleaned[start:]
        for _ in range(depth):
            stacked += close_char
        try:
            return json.loads(stacked)
        except json.JSONDecodeError:
            pass

        array_match = re.search(r'"flashcards"\s*:\s*\[', stacked)
        if array_match:
            arr_start = stacked.find('[', array_match.start())
            if arr_start != -1:
                arr_content = stacked[arr_start:]
                if not arr_content.rstrip().endswith(']'):
                    arr_content = arr_content.rstrip().rstrip(',')
                    if arr_content.endswith(','):
                        arr_content = arr_content[:-1]
                    arr_content += ']'
                try:
                    parsed = json.loads(arr_content)
                    return {"flashcards": parsed} if isinstance(parsed, list) else parsed
                except json.JSONDecodeError:
                    last_obj = 0
                    while True:
                        obj_start = arr_content.find('{', last_obj)
                        if obj_start == -1:
                            break
                        obj_end = arr_content.find('}', obj_start)
                        if obj_end == -1:
                            break
                        last_obj = obj_end + 1
                    if last_obj > 0:
                        fixed = arr_content[:last_obj] + ']'
                        try:
                            parsed = json.loads(fixed)
                            return {"flashcards": parsed} if isinstance(parsed, list) else parsed
                        except json.JSONDecodeError:
                            pass

    return None

@app.get("/")
def serve_frontend():
    index_path = os.path.join(HTML_DIR, "index.html")
    alt_path = os.path.join(HTML_DIR, "1.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    elif os.path.exists(alt_path):
        return FileResponse(alt_path)
    else:
        return {"error": "找不到前端网页文件！请确保 HTML 文件在 html/ 目录下。"}

@app.get("/favicon.ico")
def serve_favicon():
    favicon_path = os.path.join(BASE_DIR, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    from fastapi.responses import Response
    return Response(status_code=204)

@app.get("/index.html")
def serve_index_html():
    index_path = os.path.join(HTML_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="index.html 未找到")

@app.get("/login.html")
def serve_login():
    login_path = os.path.join(HTML_DIR, "login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)
    raise HTTPException(status_code=404, detail="登录页面未找到")

@app.get("/personal.html")
def serve_personal():
    personal_path = os.path.join(HTML_DIR, "personal.html")
    if os.path.exists(personal_path):
        return FileResponse(personal_path)
    raise HTTPException(status_code=404, detail="个人中心页面未找到")

@app.get("/register.html")
def serve_register():
    register_path = os.path.join(HTML_DIR, "register.html")
    if os.path.exists(register_path):
        return FileResponse(register_path)
    raise HTTPException(status_code=404, detail="注册页面未找到")

@app.get("/css/{filename}")
def serve_css(filename: str):
    file_path = os.path.join(CSS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS文件未找到")

@app.get("/js/{filename}")
def serve_js(filename: str):
    file_path = os.path.join(JS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS文件未找到")

@app.get("/audio/{filename}")
def serve_audio(filename: str):
    audio_dir = os.path.join(STATIC_DIR, "audio")
    file_path = os.path.join(audio_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="音频文件未找到")

@app.post("/api/register")
def register(request: RegisterRequest):
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(request.username) < 2 or len(request.username) > 20:
        raise HTTPException(status_code=400, detail="用户名长度需在2-20个字符之间")
    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="密码长度不能少于4个字符")
    existing = database.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail="该用户名已被注册")
    hashed = hash_password(request.password)
    avatar = f"https://api.dicebear.com/7.x/adventurer/svg?seed={request.username}&backgroundColor=b6e3f4"
    nickname = request.username + "同学"
    try:
        user_id = database.create_user(request.username, hashed, avatar, nickname)
        return {"success": True, "message": "注册成功", "userId": user_id, "username": request.username, "nickname": nickname, "avatar": avatar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")

@app.post("/api/login")
def login(request: LoginRequest):
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    user = database.get_user_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user['password'] != hash_password(request.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    database.update_last_login(user['id'])
    avatar = user['avatar'] or f"https://api.dicebear.com/7.x/adventurer/svg?seed={request.username}&backgroundColor=b6e3f4"
    nickname = user['nickname'] or (user['username'] + "同学")

    # 检查用户是否已完成评估
    profile = database.get_user_profile(user['id'])
    has_completed_assessment = profile is not None and profile.get('profile_json') is not None

    return {
        "success": True,
        "userId": user['id'],
        "username": user['username'],
        "nickname": nickname,
        "avatar": avatar,
        "currentTask": user['current_task'],
        "hasCompletedAssessment": has_completed_assessment,
        "preferences": get_user_preferences_internal(user['id'])
    }

def get_user_preferences_internal(user_id: int):
    try:
        with database.get_db() as conn:
            if conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT preferences_json FROM user_preferences WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    prefs = row['preferences_json']
                    if isinstance(prefs, str):
                        prefs = json.loads(prefs)
                    return prefs
        storage = database.load_local_storage()
        return storage.get('user_preferences', {}).get(str(user_id), {})
    except:
        return {}

@app.post("/api/user/update")
def update_user_profile(request: UpdateProfileRequest):
    try:
        if request.username:
            user = database.get_user_by_username(request.username)
            if user:
                if request.avatar:
                    database.update_user_avatar(user['id'], request.avatar)
                if request.currentTask:
                    database.update_user_task(user['id'], request.currentTask)
                if request.nickname:
                    database.update_user_nickname(user['id'], request.nickname)
                return {"success": True, "message": "更新成功"}
        raise HTTPException(status_code=400, detail="用户不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

class UserPreferencesRequest(BaseModel):
    userId: int
    preferences: dict = {}

@app.post("/api/user/preferences")
def save_user_preferences(request: UserPreferencesRequest):
    try:
        prefs_json = json.dumps(request.preferences, ensure_ascii=False)
        with database.get_db() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES LIKE 'user_preferences'")
                if not cursor.fetchone():
                    cursor.execute("""
                        CREATE TABLE user_preferences (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL UNIQUE,
                            preferences_json TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES user(id)
                        )
                    """)
                cursor.execute(
                    """INSERT INTO user_preferences (user_id, preferences_json) VALUES (%s, %s)
                       ON DUPLICATE KEY UPDATE preferences_json=%s""",
                    (request.userId, prefs_json, prefs_json)
                )
                conn.commit()
                cursor.close()
                return {"success": True, "message": "偏好设置已保存"}
        storage = database.load_local_storage()
        storage['user_preferences'] = storage.get('user_preferences', {})
        storage['user_preferences'][str(request.userId)] = request.preferences
        database.save_local_storage(storage)
        return {"success": True, "message": "偏好设置已保存到本地"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存偏好失败: {str(e)}")

@app.get("/api/user/preferences/{user_id}")
def get_user_preferences(user_id: int):
    try:
        with database.get_db() as conn:
            if conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT preferences_json FROM user_preferences WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    prefs = row['preferences_json']
                    if isinstance(prefs, str):
                        prefs = json.loads(prefs)
                    return {"success": True, "preferences": prefs}
        storage = database.load_local_storage()
        prefs = storage.get('user_preferences', {}).get(str(user_id), {})
        return {"success": True, "preferences": prefs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取偏好失败: {str(e)}")

class DeleteAccountRequest(BaseModel):
    userId: int

@app.delete("/api/user/delete")
def delete_user_account(request: DeleteAccountRequest):
    try:
        user_id = request.userId
        result = database.delete_user(user_id)
        if result:
            return {"success": True, "message": "账户已注销"}
        raise HTTPException(status_code=404, detail="用户不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"账户注销失败: {str(e)}")

class SaveProgressRequest(BaseModel):
    userId: int
    evaluation: dict = {}
    currentPath: list = []
    profile: dict = {}
    lastGradeRecord: Optional[dict] = None

    @field_validator("currentPath", mode="before")
    @classmethod
    def _save_path(cls, v):
        return coerce_learning_path(v)

    @field_validator("profile", "evaluation", mode="before")
    @classmethod
    def _save_dict(cls, v):
        return coerce_profile_dict(v) if v is not None else {}

@app.post("/api/progress/save")
def save_user_progress(request: SaveProgressRequest):
    try:
        user_id = request.userId
        evaluation_json = json.dumps(request.evaluation, ensure_ascii=False)
        path_json = json.dumps(request.currentPath, ensure_ascii=False)
        profile_json = json.dumps(request.profile, ensure_ascii=False)
        grade_record = request.lastGradeRecord

        database.save_user_profile(user_id, profile_json, evaluation_json, grade_record)
        database.save_learning_path(user_id, path_json)

        return {"success": True, "message": "进度保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

class LoadProgressRequest(BaseModel):
    userId: int

class AssessmentRequest(BaseModel):
    assessment: dict

@app.get("/assessment.html")
def serve_assessment():
    assessment_path = os.path.join(HTML_DIR, "assessment.html")
    if os.path.exists(assessment_path):
        return FileResponse(assessment_path)
    raise HTTPException(status_code=404, detail="评估页面未找到")

@app.get("/plant.html")
def serve_plant():
    plant_path = os.path.join(HTML_DIR, "plant.html")
    if os.path.exists(plant_path):
        return FileResponse(plant_path)
    raise HTTPException(status_code=404, detail="林场页面未找到")

@app.get("/hub.html")
def serve_hub():
    hub_path = os.path.join(HTML_DIR, "hub.html")
    if os.path.exists(hub_path):
        return FileResponse(hub_path)
    raise HTTPException(status_code=404, detail="中枢主页未找到")

@app.get("/courses.html")
def serve_courses():
    courses_path = os.path.join(HTML_DIR, "courses.html")
    if os.path.exists(courses_path):
        return FileResponse(courses_path)
    raise HTTPException(status_code=404, detail="课程中心页面未找到")

@app.get("/code.html")
def serve_code():
    code_path = os.path.join(HTML_DIR, "code.html")
    if os.path.exists(code_path):
        return FileResponse(code_path)
    raise HTTPException(status_code=404, detail="代码练习页面未找到")

@app.get("/progress.html")
def serve_progress():
    progress_path = os.path.join(HTML_DIR, "progress.html")
    if os.path.exists(progress_path):
        return FileResponse(progress_path)
    raise HTTPException(status_code=404, detail="学习进度页面未找到")

@app.get("/calendar.html")
def serve_calendar():
    calendar_path = os.path.join(HTML_DIR, "calendar.html")
    if os.path.exists(calendar_path):
        return FileResponse(calendar_path)
    raise HTTPException(status_code=404, detail="学习日历页面未找到")

@app.get("/settings.html")
def serve_settings():
    settings_path = os.path.join(HTML_DIR, "settings.html")
    if os.path.exists(settings_path):
        return FileResponse(settings_path)
    raise HTTPException(status_code=404, detail="设置页面未找到")

@app.get("/video-player.html")
def serve_video_player():
    video_player_path = os.path.join(HTML_DIR, "video-player.html")
    if os.path.exists(video_player_path):
        return FileResponse(video_player_path)
    raise HTTPException(status_code=404, detail="视频播放器页面未找到")

@app.get("/socratic-ai.html")
def serve_socratic_ai():
    socratic_ai_path = os.path.join(HTML_DIR, "socratic-ai.html")
    if os.path.exists(socratic_ai_path):
        return FileResponse(socratic_ai_path)
    raise HTTPException(status_code=404, detail="智脑苏格拉底页面未找到")

@app.get("/stellar-showcase.html")
def serve_stellar_showcase():
    stellar_showcase_path = os.path.join(HTML_DIR, "stellar-showcase.html")
    if os.path.exists(stellar_showcase_path):
        return FileResponse(stellar_showcase_path)
    raise HTTPException(status_code=404, detail="星云陈列室页面未找到")

@app.get("/flow-meter.html")
def serve_flow_meter():
    flow_meter_path = os.path.join(HTML_DIR, "flow-meter.html")
    if os.path.exists(flow_meter_path):
        return FileResponse(flow_meter_path)
    raise HTTPException(status_code=404, detail="心流共振仪页面未找到")

@app.post("/api/assessment/submit")
def submit_assessment(request: AssessmentRequest):
    """根据9维评估数据生成个性化学习计划"""
    try:
        assessment = request.assessment

        learning_direction = assessment.get('learningDirection', 'bigdata')
        languages = assessment.get('languages', ['python'])
        knowledge_base = assessment.get('knowledgeBase', 'zero')
        code_skill = assessment.get('codeSkill', 'beginner')
        learning_goal = assessment.get('learningGoal', 'interest')
        cognitive_style = assessment.get('cognitiveStyle', 'visual')
        study_time = assessment.get('studyTime', 'moderate')
        learning_pace = assessment.get('learningPace', 'normal')
        focus_level = assessment.get('focusLevel', 'medium')

        # 方向名称映射
        direction_names = {
            'bigdata': '大数据技术',
            'ai': '人工智能',
            'frontend': '前端开发',
            'backend': '后端开发',
            'algorithm': '算法与数据结构',
            'database': '数据库技术'
        }

        # 语言名称映射
        language_names = {
            'python': 'Python', 'java': 'Java', 'c': 'C语言', 'cpp': 'C++',
            'javascript': 'JavaScript', 'go': 'Go', 'sql': 'SQL', 'scala': 'Scala', 'rust': 'Rust'
        }

        # 根据学习方向和知识基础生成学习路径
        paths = {
            'bigdata': {
                'zero': [
                    {"topic": "计算机基础与Linux入门", "status": "current", "desc": "操作系统基础、Linux命令行"},
                    {"topic": "Python编程基础", "status": "locked", "desc": "Python语法、数据处理"},
                    {"topic": "大数据概论与环境搭建", "status": "locked", "desc": "Hadoop生态介绍、环境配置"},
                    {"topic": "Hadoop HDFS分布式存储", "status": "locked", "desc": "HDFS原理、读写流程"},
                    {"topic": "MapReduce分布式计算", "status": "locked", "desc": "MapReduce编程模型"},
                    {"topic": "Spark内存计算框架", "status": "locked", "desc": "Spark Core、SQL、Streaming"}
                ],
                'basic': [
                    {"topic": "编程基础巩固", "status": "completed", "desc": "已掌握基础编程"},
                    {"topic": "Hadoop HDFS深入", "status": "current", "desc": "HDFS架构、副本机制、读写优化"},
                    {"topic": "MapReduce编程实战", "status": "locked", "desc": "MapReduce开发、调优"},
                    {"topic": "Hive数据仓库", "status": "locked", "desc": "Hive SQL、分区、优化"},
                    {"topic": "Spark核心编程", "status": "locked", "desc": "RDD、DataFrame、Dataset"},
                    {"topic": "Flink流处理引擎", "status": "locked", "desc": "流式计算、窗口、CEP"}
                ],
                'intermediate': [
                    {"topic": "Hadoop生态体系", "status": "completed", "desc": "已掌握基础组件"},
                    {"topic": "Spark高级编程与调优", "status": "current", "desc": "Spark调优、SQL优化"},
                    {"topic": "Flink流处理引擎", "status": "locked", "desc": "实时计算、状态管理"},
                    {"topic": "NoSQL数据库", "status": "locked", "desc": "HBase、Redis、MongoDB"},
                    {"topic": "数据仓库建设", "status": "locked", "desc": "数仓建模、ETL流程"},
                    {"topic": "大数据项目实战", "status": "locked", "desc": "综合项目演练"}
                ],
                'advanced': [
                    {"topic": "大数据核心技术栈", "status": "completed", "desc": "已深入掌握"},
                    {"topic": "架构设计与优化", "status": "current", "desc": "企业级架构设计"},
                    {"topic": "大数据平台运维", "status": "locked", "desc": "集群监控、性能调优"},
                    {"topic": "实时数仓建设", "status": "locked", "desc": "Lambda/Kappa架构"},
                    {"topic": "机器学习平台", "status": "locked", "desc": "ML Pipeline构建"},
                    {"topic": "技术前沿探索", "status": "locked", "desc": "DataOps、Data Mesh"}
                ]
            },
            'ai': {
                'zero': [
                    {"topic": "Python编程基础", "status": "current", "desc": "Python语法、数据结构"},
                    {"topic": "数学基础", "status": "locked", "desc": "线性代数、概率统计、微积分"},
                    {"topic": "机器学习导论", "status": "locked", "desc": "ML基本概念、经典算法"},
                    {"topic": "深度学习基础", "status": "locked", "desc": "神经网络、反向传播"},
                    {"topic": "TensorFlow/PyTorch", "status": "locked", "desc": "深度学习框架实战"},
                    {"topic": "计算机视觉/NLP", "status": "locked", "desc": "CV或NLP方向深入"}
                ],
                'basic': [
                    {"topic": "Python编程", "status": "completed", "desc": "已掌握Python基础"},
                    {"topic": "机器学习算法", "status": "current", "desc": "监督学习、无监督学习"},
                    {"topic": "深度学习原理", "status": "locked", "desc": "CNN、RNN、Transformer"},
                    {"topic": "框架实战", "status": "locked", "desc": "PyTorch/TensorFlow项目"},
                    {"topic": "领域深入", "status": "locked", "desc": "CV/NLP/推荐系统"},
                    {"topic": "模型部署与优化", "status": "locked", "desc": "模型压缩、推理加速"}
                ],
                'intermediate': [
                    {"topic": "ML/DL基础", "status": "completed", "desc": "已掌握核心算法"},
                    {"topic": "领域专项突破", "status": "current", "desc": "CV/NLP/推荐深入"},
                    {"topic": "大模型技术", "status": "locked", "desc": "LLM、Prompt Engineering"},
                    {"topic": "MLOps实践", "status": "locked", "desc": "模型生命周期管理"},
                    {"topic": "研究论文复现", "status": "locked", "desc": "前沿论文阅读与实现"},
                    {"topic": "AI项目实战", "status": "locked", "desc": "端到端AI项目"}
                ],
                'advanced': [
                    {"topic": "AI核心技术", "status": "completed", "desc": "已深入掌握"},
                    {"topic": "前沿技术探索", "status": "current", "desc": "最新研究进展"},
                    {"topic": "系统架构设计", "status": "locked", "desc": "AI系统架构"},
                    {"topic": "团队技术管理", "status": "locked", "desc": "AI团队建设"},
                    {"topic": "论文发表", "status": "locked", "desc": "学术研究"},
                    {"topic": "技术影响力建设", "status": "locked", "desc": "开源、分享"}
                ]
            },
            'frontend': {
                'zero': [
                    {"topic": "HTML/CSS基础", "status": "current", "desc": "网页结构、样式设计"},
                    {"topic": "JavaScript入门", "status": "locked", "desc": "JS语法、DOM操作"},
                    {"topic": "ES6+与TypeScript", "status": "locked", "desc": "现代JS、类型系统"},
                    {"topic": "React/Vue框架", "status": "locked", "desc": "组件化开发"},
                    {"topic": "前端工程化", "status": "locked", "desc": "Webpack、Vite、CI/CD"},
                    {"topic": "项目实战", "status": "locked", "desc": "完整前端项目"}
                ],
                'basic': [
                    {"topic": "HTML/CSS/JS基础", "status": "completed", "desc": "已掌握前端基础"},
                    {"topic": "React/Vue深入", "status": "current", "desc": "框架原理、最佳实践"},
                    {"topic": "状态管理", "status": "locked", "desc": "Redux、Pinia、Zustand"},
                    {"topic": "前端工程化", "status": "locked", "desc": "构建工具、自动化"},
                    {"topic": "性能优化", "status": "locked", "desc": "加载优化、渲染优化"},
                    {"topic": "跨端开发", "status": "locked", "desc": "小程序、RN、Flutter"}
                ],
                'intermediate': [
                    {"topic": "前端框架", "status": "completed", "desc": "已熟练使用框架"},
                    {"topic": "架构设计", "status": "current", "desc": "前端架构、微前端"},
                    {"topic": "性能优化深入", "status": "locked", "desc": "极致性能优化"},
                    {"topic": "跨端技术", "status": "locked", "desc": "多端统一方案"},
                    {"topic": "前端智能化", "status": "locked", "desc": "低代码、AI辅助"},
                    {"topic": "技术团队管理", "status": "locked", "desc": "前端团队建设"}
                ],
                'advanced': [
                    {"topic": "前端全栈能力", "status": "completed", "desc": "已具备全栈能力"},
                    {"topic": "技术规划", "status": "current", "desc": "技术选型、架构演进"},
                    {"topic": "基础设施建设", "status": "locked", "desc": "研发平台、工具链"},
                    {"topic": "技术影响力", "status": "locked", "desc": "开源、技术分享"},
                    {"topic": "业务架构", "status": "locked", "desc": "业务与技术结合"},
                    {"topic": "团队成长", "status": "locked", "desc": "人才培养"}
                ]
            },
            'backend': {
                'zero': [
                    {"topic": "编程语言基础", "status": "current", "desc": "Java/Go/Python选一"},
                    {"topic": "数据结构与算法", "status": "locked", "desc": "基础算法、数据结构"},
                    {"topic": "数据库基础", "status": "locked", "desc": "MySQL、Redis入门"},
                    {"topic": "Web框架", "status": "locked", "desc": "Spring Boot/Gin/Django"},
                    {"topic": "微服务架构", "status": "locked", "desc": "服务拆分、RPC"},
                    {"topic": "分布式系统", "status": "locked", "desc": "分布式理论、实践"}
                ],
                'basic': [
                    {"topic": "编程语言", "status": "completed", "desc": "已掌握一门语言"},
                    {"topic": "数据库深入", "status": "current", "desc": "SQL优化、索引原理"},
                    {"topic": "Web框架实战", "status": "locked", "desc": "框架原理、最佳实践"},
                    {"topic": "微服务入门", "status": "locked", "desc": "Spring Cloud/微服务"},
                    {"topic": "消息队列", "status": "locked", "desc": "Kafka、RabbitMQ"},
                    {"topic": "分布式系统", "status": "locked", "desc": "CAP、分布式事务"}
                ],
                'intermediate': [
                    {"topic": "后端基础", "status": "completed", "desc": "已掌握后端开发"},
                    {"topic": "系统设计", "status": "current", "desc": "高并发、高可用设计"},
                    {"topic": "性能优化", "status": "locked", "desc": "JVM、数据库、缓存优化"},
                    {"topic": "分布式深入", "status": "locked", "desc": "分布式事务、一致性"},
                    {"topic": "容器化与云原生", "status": "locked", "desc": "Docker、K8s"},
                    {"topic": "架构演进", "status": "locked", "desc": "系统架构设计"}
                ],
                'advanced': [
                    {"topic": "后端核心技术", "status": "completed", "desc": "已深入掌握"},
                    {"topic": "架构设计", "status": "current", "desc": "大型系统架构"},
                    {"topic": "技术规划", "status": "locked", "desc": "技术选型、演进"},
                    {"topic": "团队管理", "status": "locked", "desc": "技术团队建设"},
                    {"topic": "技术影响力", "status": "locked", "desc": "开源、分享"},
                    {"topic": "业务架构", "status": "locked", "desc": "业务与技术融合"}
                ]
            },
            'algorithm': {
                'zero': [
                    {"topic": "编程语言基础", "status": "current", "desc": "C++/Python/Java"},
                    {"topic": "基础数据结构", "status": "locked", "desc": "数组、链表、栈、队列"},
                    {"topic": "基础算法", "status": "locked", "desc": "排序、二分、递归"},
                    {"topic": "进阶数据结构", "status": "locked", "desc": "树、图、哈希表"},
                    {"topic": "动态规划", "status": "locked", "desc": "DP思想、经典问题"},
                    {"topic": "竞赛算法", "status": "locked", "desc": "图论、数论、字符串"}
                ],
                'basic': [
                    {"topic": "基础算法", "status": "completed", "desc": "已掌握基础"},
                    {"topic": "数据结构深入", "status": "current", "desc": "高级数据结构"},
                    {"topic": "动态规划", "status": "locked", "desc": "DP专题训练"},
                    {"topic": "图论算法", "status": "locked", "desc": "BFS、DFS、最短路"},
                    {"topic": "刷题训练", "status": "locked", "desc": "LeetCode专项"},
                    {"topic": "竞赛模拟", "status": "locked", "desc": "模拟赛、真题"}
                ],
                'intermediate': [
                    {"topic": "基础算法", "status": "completed", "desc": "已熟练掌握"},
                    {"topic": "竞赛专题", "status": "current", "desc": "专项突破"},
                    {"topic": "高级算法", "status": "locked", "desc": "高级数据结构、算法"},
                    {"topic": "真题训练", "status": "locked", "desc": "历年真题"},
                    {"topic": "模拟赛", "status": "locked", "desc": "定期模拟"},
                    {"topic": "竞赛实战", "status": "locked", "desc": "参加比赛"}
                ],
                'advanced': [
                    {"topic": "算法能力", "status": "completed", "desc": "已具备竞赛水平"},
                    {"topic": "难题突破", "status": "current", "desc": "挑战难题"},
                    {"topic": "算法创新", "status": "locked", "desc": "算法优化、创新"},
                    {"topic": "竞赛指导", "status": "locked", "desc": "帮助他人提升"},
                    {"topic": "算法研究", "status": "locked", "desc": "算法理论研究"},
                    {"topic": "技术影响力", "status": "locked", "desc": "分享、开源"}
                ]
            },
            'database': {
                'zero': [
                    {"topic": "SQL基础", "status": "current", "desc": "SQL语法、基本查询"},
                    {"topic": "数据库设计", "status": "locked", "desc": "ER图、范式设计"},
                    {"topic": "MySQL深入", "status": "locked", "desc": "索引、事务、锁"},
                    {"topic": "Redis缓存", "status": "locked", "desc": "缓存设计、数据结构"},
                    {"topic": "MongoDB文档库", "status": "locked", "desc": "文档数据库"},
                    {"topic": "分布式数据库", "status": "locked", "desc": "分库分表、分布式事务"}
                ],
                'basic': [
                    {"topic": "SQL基础", "status": "completed", "desc": "已掌握SQL"},
                    {"topic": "MySQL深入", "status": "current", "desc": "存储引擎、索引优化"},
                    {"topic": "Redis实战", "status": "locked", "desc": "缓存架构、分布式锁"},
                    {"topic": "PostgreSQL", "status": "locked", "desc": "高级特性"},
                    {"topic": "NoSQL生态", "status": "locked", "desc": "MongoDB、ES"},
                    {"topic": "数据库运维", "status": "locked", "desc": "监控、备份、高可用"}
                ],
                'intermediate': [
                    {"topic": "数据库基础", "status": "completed", "desc": "已熟练使用"},
                    {"topic": "性能优化", "status": "current", "desc": "SQL优化、架构优化"},
                    {"topic": "高可用架构", "status": "locked", "desc": "主从、集群"},
                    {"topic": "分布式数据库", "status": "locked", "desc": "TiDB、OceanBase"},
                    {"topic": "数据架构", "status": "locked", "desc": "数据中台、数仓"},
                    {"topic": "数据库内核", "status": "locked", "desc": "源码分析"}
                ],
                'advanced': [
                    {"topic": "数据库技术", "status": "completed", "desc": "已深入掌握"},
                    {"topic": "架构设计", "status": "current", "desc": "数据架构规划"},
                    {"topic": "内核研究", "status": "locked", "desc": "数据库内核开发"},
                    {"topic": "技术规划", "status": "locked", "desc": "技术选型"},
                    {"topic": "团队建设", "status": "locked", "desc": "DBA团队管理"},
                    {"topic": "技术影响力", "status": "locked", "desc": "分享、开源"}
                ]
            }
        }

        # 获取对应路径
        path = paths.get(learning_direction, paths['bigdata']).get(knowledge_base, paths['bigdata']['zero'])

        # 生成个性化建议
        lang_str = '、'.join([language_names.get(l, l) for l in languages]) if languages else 'Python'
        dir_str = direction_names.get(learning_direction, '大数据技术')

        goal_names = {
            'exam': '应对考试', 'career': '职业发展', 'project': '项目实战',
            'interest': '兴趣探索', 'competition': '竞赛备战', 'research': '科研学术'
        }
        goal_str = goal_names.get(learning_goal, '学习提升')

        suggestion = f"你选择了{dir_str}方向，主要使用{lang_str}语言。目标是{goal_str}。"

        # 根据认知风格调整建议
        style_suggestions = {
            "visual": "根据你的视觉型学习偏好，我们会提供丰富的图表、流程图和可视化演示来帮助你理解。",
            "pragmatic": "根据你的实践型学习偏好，我们会提供大量代码示例和动手练习，让你在实践中掌握知识。",
            "textual": "根据你的文字型学习偏好，我们会提供详细的理论解释和文档资料，帮助你系统性地理解知识。"
        }
        suggestion += " " + style_suggestions.get(cognitive_style, "")

        # 根据学习时间调整建议
        time_suggestions = {
            "light": "考虑到你的学习时间有限，建议每天专注1-2个核心概念，循序渐进。",
            "immersive": "你的学习时间充裕，建议结合理论学习和项目实战，快速提升技能水平。"
        }
        suggestion += " " + time_suggestions.get(study_time, "")

        # 根据学习节奏调整建议
        pace_suggestions = {
            "slow": "建议你稳扎稳打，每个知识点都要彻底理解后再继续，打好坚实基础。",
            "fast": "建议快速过一遍核心内容，遇到问题再回头深入，效率优先。"
        }
        suggestion += " " + pace_suggestions.get(learning_pace, "")

        # 根据专注度调整建议
        if focus_level == 'low':
            suggestion += " 我们会通过互动问答、苏格拉底式引导等方式，帮助你保持学习专注度。"

        return {
            "success": True,
            "profile": assessment,
            "path": path,
            "suggestion": suggestion
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成学习计划失败: {str(e)}")

@app.post("/api/progress/load")
def load_user_progress(request: LoadProgressRequest):
    try:
        user_id = request.userId

        profile_data = database.get_user_profile(user_id)
        path_data = database.get_learning_path(user_id)

        result = {
            "success": True,
            "profile": None,
            "evaluation": None,
            "currentPath": None,
            "lastGradeRecord": None
        }

        if profile_data:
            pj = profile_data.get("profile_json", {})
            if isinstance(pj, str):
                try:
                    pj = json.loads(pj)
                except (json.JSONDecodeError, TypeError):
                    pj = {}
            result["profile"] = coerce_profile_dict(pj)
            ej = profile_data.get("evaluation_json", {})
            if isinstance(ej, str):
                try:
                    ej = json.loads(ej)
                except (json.JSONDecodeError, TypeError):
                    ej = {}
            result["evaluation"] = coerce_profile_dict(ej)
            result["lastGradeRecord"] = profile_data.get('last_grade_record')

        if path_data:
            result["currentPath"] = coerce_learning_path(path_data.get("path_json"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")

@app.post("/api/chat")
def multi_agent_workflow(request: ChatRequest):
    workflow_logs = []
    try:
        # ===== Agent 1: 画像分析智能体 (Profiler Agent) =====
        workflow_logs.append("[Profiler] 正在分析学生意图并进行6维学情切片...")
        profiler_sys = """你是一个教育数据分析智能体。分析学生输入，更新6维动态画像。必须输出纯JSON格式：
{"search_keywords": ["关键词1", "关键词2"], "profile_updates": {"knowledgeBase": "中文描述", "codeSkill": "中文描述", "learningGoal": "中文描述", "cognitiveStyle": "视觉型/文字型/实践型 之一", "weakness": "最新知识短板（中文短语，无则写 暂无）", "focusLevel": "高专注/中等专注/需要引导 之一"}, "dialogue_type": "question(提问)/confusion(困惑)/practice(练习)/chat(闲聊)"}

profile_updates 必须用简短中文，禁止输出 basic、exam、pragmatic、medium 等英文枚举键。

认知风格判定规则：
- 视觉型: 学生要求画图、看流程、可视化
- 实践型: 学生要求写代码、实操、运行
- 文字型: 学生偏好文字解释、理论推导
专注度判定规则：
- 高专注: 问题具体、有上下文
- 中等专注: 问题一般
- 需要引导: 问题模糊、敷衍"""
        profiler_reply = call_llm(profiler_sys, f"当前画像:{json.dumps(request.currentProfile, ensure_ascii=False)}\n用户输入:{request.userText}")
        analysis_data = extract_json(profiler_reply) or {"search_keywords": [request.userText], "profile_updates": {}, "dialogue_type": "question"}
        new_profile = {**request.currentProfile, **analysis_data.get("profile_updates", {})}
        keywords = analysis_data.get("search_keywords", [request.userText])
        dialogue_type = analysis_data.get("dialogue_type", "question")
        workflow_logs.append(f"[Profiler] 画像6维更新完毕 | 对话类型: {dialogue_type} | 认知风格: {new_profile.get('cognitiveStyle', '待测试')}")

        # ===== Agent 2: 教研规划智能体 (Planner Agent) =====
        workflow_logs.append("[Planner] 检测到学情变动，正在动态重组专属学习路径...")
        planner_sys = """你是一个大学教研规划智能体。根据画像规划路径。必须输出纯JSON数组：
[{"topic": "复习主题", "status": "completed"}, {"topic": "当前主题", "status": "current"}, {"topic": "进阶主题", "status": "locked"}]"""
        planner_reply = call_llm(planner_sys, f"最新画像:{json.dumps(new_profile, ensure_ascii=False)}\n用户输入:{request.userText}")
        new_path = coerce_learning_path(extract_json(planner_reply, is_array=True) or request.currentPath)
        workflow_logs.append("[Planner] 个性化学习路径树重构完成。")

        # ===== Agent 3: RAG 检索引擎 (RAG Retriever) =====
        workflow_logs.append("[RAG Retriever] 正在挂载高校内部课程知识库...")
        context, sources, source_links = retrieve_knowledge(keywords)
        confidence = min(95, 60 + len(sources) * 15) if sources else 30
        workflow_logs.append(f"[RAG Retriever] 检索完成 | 置信度: {confidence}% | 挂载{len(sources)}条教材引用")

        # ===== Agent 4: 主控中枢智能体 (Master Controller) =====
        cognitive_style = normalize_cognitive_style_for_routing(new_profile.get("cognitiveStyle", "textual"))
        workflow_logs.append(f"[Master Controller] 研判对话类型: {dialogue_type} | 认知模态: {cognitive_style} | 正在调度下游智能体网络...")

        dispatch_strategy = ""
        if dialogue_type == "confusion":
            dispatch_strategy = "socratic"
            workflow_logs.append("[Master Controller] 检测到学生困惑 -> 唤醒苏格拉底诊断智能体")
        elif cognitive_style == "visual":
            dispatch_strategy = "visual"
            workflow_logs.append("[Master Controller] 多模态分发策略: 高视觉权重 -> 导图Agent + 微课动画Agent")
        elif cognitive_style == "pragmatic":
            dispatch_strategy = "pragmatic"
            workflow_logs.append("[Master Controller] 多模态分发策略: 高实践权重 -> 实操Agent + 代码沙盒")
        else:
            dispatch_strategy = "textual"
            workflow_logs.append("[Master Controller] 多模态分发策略: 均衡模式 -> 文档Agent + 导图Agent")

        # ===== Agent 5-8: 多模态生成智能体群组 (Generator Agents) =====
        if dispatch_strategy == "socratic":
            # ===== Agent: 苏格拉底诊断智能体 (Socratic Evaluator) =====
            workflow_logs.append("[Socratic Evaluator] 正在启动启发式诊断，引导学生自主思考...")
            socratic_sys = f"""你是一位苏格拉底式教学导师。学生目前处于困惑状态，你的任务不是直接给出答案，而是通过启发式反问引导学生自主思考。

【学生画像】: {json.dumps(new_profile, ensure_ascii=False)}
【教材参考】:
{context}

【规则】：
1. 绝不直接给出完整答案
2. 通过2-3个层层递进的引导性问题，帮助学生自己发现答案
3. 每个问题后给出提示方向（而非答案本身）
4. 最后给出一个"思考锚点"——即如果学生能回答最后一个问题，就说明已经理解了核心
5. 用 [Doc_Ref: xxx] 标注引用来源
6. 语气温和鼓励，像一位耐心的导师"""
            final_answer = call_llm(socratic_sys, request.userText, temperature=0.5)
            workflow_logs.append("[Socratic Evaluator] 启发式诊断问题链生成完毕。")
        else:
            # ===== 多模态生成智能体群组 =====
            workflow_logs.append("[Generator Agents] 多模态教研组正在融合所有信息，生成讲解方案...")

            visual_instruction = ""
            if dispatch_strategy == "visual":
                visual_instruction = """【高视觉权重模式】：
1. 必须插入至少2个Mermaid图表（架构图/流程图/时序图），用 ```mermaid 包裹
2. 用生动的比喻解释抽象概念
3. 优先使用图示而非纯文字
4. 生成一个微课动画指令集，格式为 ```micro-course 包裹，内容为JSON：
{"title":"微课标题","scenes":[{"narration":"旁白文本","diagram":"mermaid图表代码(可选)","highlight":"需要高亮的关键词"}]}
5. 在关键概念处添加 [Doc_Ref: 引用来源] 标注"""
            elif dispatch_strategy == "pragmatic":
                visual_instruction = """【高实践权重模式】：
1. 提供可运行的Python代码示例，用 ```python 包裹
2. 代码注释详细解释每一步
3. 给出实际操作步骤
4. 插入1个Mermaid架构图说明代码逻辑，用 ```mermaid 包裹
5. 在关键概念处添加 [Doc_Ref: 引用来源] 标注"""
            else:
                visual_instruction = """【均衡模式】：
1. 提供清晰的文字解释，逻辑递进
2. 插入1个Mermaid思维导图或流程图，用 ```mermaid 包裹
3. 在关键概念处添加 [Doc_Ref: 引用来源] 标注
4. 适当使用类比帮助理解"""

            tutor_sys = f"""你是一位专业的大数据与AI高校导师。
【必须遵守规则】：
1. 基于[教材参考]回答并标注引用。
[教材参考开始]
{context}
[教材参考结束]
2. 根据画像 {json.dumps(new_profile, ensure_ascii=False)} 调整难度和表达方式。
3. 如果学生基础薄弱，避免底层源码解析，用生动比喻和可视化替代。
{visual_instruction}"""

            final_answer = call_llm(tutor_sys, request.userText, temperature=0.6)
            workflow_logs.append("[Generator Agents] 多模态内容生成完毕。")

        # ===== Agent: 评估智能体 (Evaluation Agent) =====
        interaction_count = request.interactionCount + 1
        socratic_pass_rate = request.socraticPassRate
        if dispatch_strategy == "socratic":
            socratic_pass_rate = min(1.0, socratic_pass_rate + 0.1)
        difficulty_level = "medium"
        if interaction_count > 10 and socratic_pass_rate > 0.7:
            difficulty_level = "advanced"
        elif interaction_count < 3 or socratic_pass_rate < 0.3:
            difficulty_level = "basic"
        workflow_logs.append(f"[Evaluator] 评估闭环 | 交互次数: {interaction_count} | 启发通关率: {socratic_pass_rate:.0%} | 下一阶段难度: {difficulty_level}")

        workflow_logs.append("[Master Controller] 十大智能体协同调度完毕。")

        return {
            "content": final_answer,
            "newProfile": new_profile,
            "newPath": new_path,
            "logs": workflow_logs,
            "sources": sources,
            "sourceLinks": source_links,
            "dispatchStrategy": dispatch_strategy,
            "evaluation": {
                "interactionCount": interaction_count,
                "socraticPassRate": socratic_pass_rate,
                "difficultyLevel": difficulty_level,
                "codePracticeTime": request.codePracticeTime
            }
        }
    except Exception as e:
        print(f"工作流中断: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/textbook-links/validate")
def validate_textbook_links():
    import urllib.request
    import urllib.error
    results = {}
    for textbook_name, link_config in TEXTBOOK_DEEP_LINKS.items():
        test_url = link_config["baseUrl"]
        try:
            req = urllib.request.Request(test_url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            urllib.request.urlopen(req, timeout=5)
            results[textbook_name] = {"status": "valid", "baseUrl": test_url}
        except Exception as e:
            results[textbook_name] = {"status": "invalid", "baseUrl": test_url, "error": str(e)}
    for key, doc in KNOWLEDGE_BASE.items():
        textbook_name = doc.get("textbook", "")
        chapter_id = doc.get("chapterId", "")
        start_page = doc.get("startPage", 1)
        if textbook_name and chapter_id:
            deep_link = build_deep_link(textbook_name, chapter_id, start_page)
            results[doc["source"]] = {"deepLink": deep_link, "textbook": textbook_name, "chapterId": chapter_id}
    return {"validationResults": results, "timestamp": datetime.now().isoformat()}

@app.get("/api/textbook-links/list")
def list_textbook_links():
    links = []
    for key, doc in KNOWLEDGE_BASE.items():
        textbook_name = doc.get("textbook", "")
        chapter_id = doc.get("chapterId", "")
        start_page = doc.get("startPage", 1)
        deep_link = ""
        if textbook_name and chapter_id:
            deep_link = build_deep_link(textbook_name, chapter_id, start_page)
        links.append({
            "key": key,
            "source": doc["source"],
            "textbook": textbook_name,
            "chapterId": chapter_id,
            "startPage": start_page,
            "endPage": doc.get("endPage", start_page),
            "deepLink": deep_link
        })
    return {"links": links, "platforms": TEXTBOOK_DEEP_LINKS}

@app.post("/api/run-code")
def run_code(request: CodeRunRequest):
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(request.code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=os.path.dirname(tmp_path)
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "程序运行超时（超过10秒），请检查是否存在死循环。", "returncode": -1}
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/grade-code")
def grade_code(request: CodeGradeRequest):
    try:
        grader_sys = f"""你是一位专业的编程教学批改智能体。你需要对学生提交的代码进行全方位批阅。

【学生画像】: {json.dumps(request.currentProfile, ensure_ascii=False) if request.currentProfile else '暂无'}

【批阅要求】：
1. 检查代码是否正确完成了题目要求
2. 检查代码逻辑、边界条件、异常处理
3. 评估代码风格和可读性
4. 给出具体的改进建议
5. 给出评分（0-100分）

【必须输出纯JSON格式】：
{{
  "score": 85,
  "correctness": "代码是否正确完成要求的评价",
  "logic_analysis": "逻辑分析",
  "style_analysis": "代码风格评价",
  "suggestions": ["改进建议1", "改进建议2"],
  "reference_answer": "参考答案代码（如果学生代码有误）",
  "encouragement": "根据学生画像给出的鼓励语"
}}"""

        user_prompt = f"""【编程题目】：
{request.task}

【学生提交的代码（{request.language}）】：
```{request.language}
{request.code}
```

请对以上代码进行详细批阅。"""

        reply = call_llm(grader_sys, user_prompt, temperature=0.3)
        grade_data = extract_json(reply)
        if not grade_data:
            grade_data = {
                "score": 0,
                "correctness": "批阅结果解析失败，请重试",
                "logic_analysis": reply,
                "style_analysis": "",
                "suggestions": [],
                "reference_answer": "",
                "encouragement": ""
            }
        return grade_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


_controller_instance: MasterController | None = None

def get_controller() -> MasterController:
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = create_default_controller()
    return _controller_instance


@app.post("/api/v2/chat")
async def chat_v2(request: ChatRequestV2, controller: MasterController = Depends(get_controller)):
    try:
        state = build_state_from_request(
            student_id=request.student_id,
            course_id=request.course_id,
            user_input=request.user_input,
            context_id=request.context_id,
            current_profile=request.current_profile,
            current_path=request.current_path,
            interaction_count=request.interaction_count,
            code_practice_time=request.code_practice_time,
            socratic_pass_rate=request.socratic_pass_rate,
        )

        state = await controller.execute(state)

        save_state(state)

        final_content = extract_final_content(state)
        resources = extract_resources(state)
        evaluation = extract_evaluation(state)
        workflow_logs = format_workflow_logs(state.workflow_logs)

        new_path = [node.model_dump(mode="json") for node in state.current_path]

        return ChatResponseV2(
            success=True,
            content=final_content,
            content_type=state.metadata.get("planner_output", {}).get("content_types", ["text"])[0] if state.metadata.get("planner_output") else "text",
            resources=resources,
            suggested_path=state.current_path,
            new_profile=state.profile.model_dump(mode="json"),
            new_path=new_path,
            workflow_logs=state.workflow_logs,
            sources=state.sources,
            source_links=state.source_links,
            dispatch_strategy=state.metadata.get("dialogue_type", "textual"),
            emotion=state.emotion,
            evaluation=evaluation,
            context_id=state.context_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)}")


@app.post("/api/v2/chat/stream")
async def chat_stream_v2(raw_request: Request, body: StreamChatRequest):
    logger.info(f"Stream connected: student={body.student_id}, input={body.user_input[:50]}")

    event_queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=1024)
    disconnected = asyncio.Event()

    state = build_state_from_request(
        student_id=body.student_id,
        course_id=body.course_id,
        user_input=body.user_input,
        context_id=body.context_id,
        current_profile=body.current_profile,
        current_path=body.current_path,
        interaction_count=body.interaction_count,
        code_practice_time=body.code_practice_time,
        socratic_pass_rate=body.socratic_pass_rate,
    )

    async def push_agent_log(agent_name: str, content: str):
        if not disconnected.is_set():
            await event_queue.put({"type": "agent_log", "agent": agent_name, "content": content})

    async def push_content_chunk(content: str):
        if not disconnected.is_set():
            await event_queue.put({"type": "content_chunk", "content": content})

    async def push_error(message: str):
        if not disconnected.is_set():
            await event_queue.put({"type": "error", "message": message})

    async def push_complete(data: dict):
        if not disconnected.is_set():
            await event_queue.put({"type": "complete", "data": data})

    async def push_new_logs(last_idx: int) -> int:
        for log in state.workflow_logs[last_idx:]:
            await push_agent_log(log.agent_name, log.output_summary)
        return len(state.workflow_logs)

    async def run_workflow():
        sources: list[str] = []
        source_links: dict[str, str] = {}
        context = ""
        dispatch_strategy = "textual"
        try:
            controller = get_controller()
            last_log_idx = 0

            await push_agent_log("system", "正在初始化多智能体工作流...")

            profiler = controller._agents.get("profiler") or ProfilerAgent()
            await profiler.run(state)
            last_log_idx = await push_new_logs(last_log_idx)

            overload_intervention = state.metadata.get("overload_intervention", "")
            if overload_intervention:
                await push_agent_log("profiler", f"认知超载干预: {overload_intervention}")

            planner = controller._agents.get("planner") or PlannerAgent()
            await planner.run(state)
            last_log_idx = await push_new_logs(last_log_idx)

            planner_data = state.metadata.get("planner_output", {})
            dialogue_type = state.metadata.get("dialogue_type", "question")
            cognitive_style = state.profile.learning_style
            if isinstance(cognitive_style, str):
                try:
                    cognitive_style = CognitiveStyle(cognitive_style)
                except ValueError:
                    cognitive_style = CognitiveStyle.PRAGMATIC

            await push_agent_log(
                "master_controller",
                f"路由决策: 对话类型={dialogue_type}, 认知风格={cognitive_style.value}",
            )

            context, sources, source_links = retrieve_knowledge(
                state.metadata.get("search_keywords", [])
            )

            if sources:
                await push_agent_log("rag_retriever", f"检索到 {len(sources)} 条教材引用 | 置信度: {min(95, 60 + len(sources) * 15)}%")

            if dialogue_type == "confusion":
                dispatch_strategy = "socratic"
            elif cognitive_style == CognitiveStyle.VISUAL:
                dispatch_strategy = "visual"
            elif cognitive_style == CognitiveStyle.PRAGMATIC:
                dispatch_strategy = "pragmatic"

            await push_agent_log("master_controller", f"分发策略: {dispatch_strategy}")

            if dispatch_strategy == "socratic":
                await push_agent_log("socratic_evaluator", "苏格拉底评估与辅导智能体启动...")
                socratic_agent = controller._agents.get("socratic_evaluator") or SocraticEvaluatorAgent()
                await socratic_agent.run(state)
                last_log_idx = await push_new_logs(last_log_idx)

                socratic_response = state.metadata.get("socratic_response", "")
                if socratic_response:
                    chunk_size = 80
                    for i in range(0, len(socratic_response), chunk_size):
                        if disconnected.is_set():
                            break
                        await push_content_chunk(socratic_response[i : i + chunk_size])
            else:
                visual_instruction = """【高视觉权重模式】：
1. 必须插入至少2个Mermaid图表（架构图/流程图/时序图），用 ```mermaid 包裹
2. 用生动的比喻解释抽象概念
3. 优先使用图示而非纯文字
4. 生成一个微课动画指令集，格式为 ```micro-course 包裹，内容为JSON：
{"title":"微课标题","scenes":[{"narration":"旁白文本","diagram":"mermaid图表代码(可选)","highlight":"需要高亮的关键词"}]}
5. 在关键概念处添加 [Doc_Ref: 引用来源] 标注"""
                pragmatic_instruction = """【高实践权重模式】：
1. 提供可运行的Python代码示例，用 ```python 包裹
2. 代码注释详细解释每一步
3. 给出实际操作步骤
4. 插入1个Mermaid架构图说明代码逻辑，用 ```mermaid 包裹
5. 在关键概念处添加 [Doc_Ref: 引用来源] 标注"""
                textual_instruction = """【均衡模式】：
1. 提供清晰的文字解释，逻辑递进
2. 插入1个Mermaid思维导图或流程图，用 ```mermaid 包裹
3. 在关键概念处添加 [Doc_Ref: 引用来源] 标注
4. 适当使用类比帮助理解"""

                if dispatch_strategy == "visual":
                    instruction = visual_instruction
                elif dispatch_strategy == "pragmatic":
                    instruction = pragmatic_instruction
                else:
                    instruction = textual_instruction

                sys_prompt = f"""你是一位专业的大数据与AI高校导师。
【必须遵守规则】：
1. 基于[教材参考]回答并标注引用。
[教材参考开始]
{context}
[教材参考结束]
2. 根据画像 {json.dumps(state.profile.model_dump(mode='json'), ensure_ascii=False)} 调整难度和表达方式。
3. 如果学生基础薄弱，避免底层源码解析，用生动比喻和可视化替代。
{instruction}"""

                agent_label = f"generator_{dispatch_strategy}"
                await push_agent_log(agent_label, "正在调用大模型流式生成...")

                async for event in call_llm_stream_with_log(
                    sys_prompt, body.user_input, agent_name=agent_label, temperature=0.3
                ):
                    if disconnected.is_set():
                        break
                    if event["type"] == "text":
                        await push_content_chunk(event["content"])
                    elif event["type"] == "log":
                        await push_agent_log(agent_label, event.get("message", ""))
                    elif event["type"] == "done":
                        elapsed = event.get("elapsed_ms", "?")
                        char_count = len(event.get("full_text", ""))
                        await push_agent_log(agent_label, f"生成完毕 | 共 {char_count} 字 | 耗时 {elapsed}ms")

            await push_agent_log("evaluator", "评估学情指标...")
            evaluator = controller._agents.get("evaluator") or EvaluationAgent()
            await evaluator.run(state)
            last_log_idx = await push_new_logs(last_log_idx)

            evaluation = extract_evaluation(state)
            state.sources = sources
            state.source_links = source_links
            save_state(state)

            new_path = [node.model_dump(mode="json") for node in state.current_path]

            await push_agent_log("master_controller", "多智能体协同调度完毕")

            await push_agent_log("resource_dispatcher", "正在分发异步资源生成任务...")

            await dispatch_resource_tasks(state, state.context_id, controller)

            await push_agent_log("resource_dispatcher", "思维导图/视频/练习已进入后台生成，可通过轮询接口查询进度")

            await push_complete({
                "newProfile": state.profile.model_dump(mode="json"),
                "newPath": new_path,
                "sources": sources,
                "sourceLinks": source_links,
                "dispatchStrategy": dispatch_strategy,
                "evaluation": evaluation,
                "emotion": state.emotion.model_dump(mode="json"),
                "contextId": state.context_id,
                "resourceTaskId": state.context_id,
            })

            logger.info(f"Stream workflow completed: student={body.student_id}, strategy={dispatch_strategy}")

        except Exception as e:
            logger.error(f"Stream workflow error: student={body.student_id}, error={str(e)}", exc_info=True)
            await push_error(f"工作流执行失败: {str(e)}")
        finally:
            await event_queue.put(None)

    task = asyncio.create_task(run_workflow())

    async def event_generator():
        try:
            while not disconnected.is_set():
                if await raw_request.is_disconnected():
                    logger.info(f"Client disconnected: student={body.student_id}")
                    disconnected.set()
                    break

                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    break

                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info(f"Stream closed: student={body.student_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v2/resource/status/{context_id}")
async def get_resource_status(context_id: str):
    manager = get_task_manager()
    result = await manager.get_task_status_response(context_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/v2/state/{student_id}/{context_id}")
async def get_state(student_id: str, context_id: str):
    state = load_state(student_id, context_id)
    if not state:
        raise HTTPException(status_code=404, detail="对话状态不存在")
    return state.to_persist_dict()


@app.get("/api/v2/state/{student_id}")
async def list_contexts(student_id: str):
    contexts = list_student_contexts(student_id)
    return {"student_id": student_id, "contexts": contexts}


@app.post("/api/v2/agents/register")
async def register_agent(agent_config: dict):
    try:
        agent_type = agent_config.get("type", "")
        agent_name = agent_config.get("name", "")

        controller = get_controller()

        type_map = {
            "profiler": ProfilerAgent,
            "planner": PlannerAgent,
            "document_generator": DocumentGeneratorAgent,
            "mindmap_generator": MindmapGeneratorAgent,
            "exercise_generator": ExerciseGeneratorAgent,
            "video_content": VideoContentAgent,
            "resource_push": ResourcePushAgent,
            "evaluator": EvaluationAgent,
        }

        if agent_type not in type_map:
            raise HTTPException(status_code=400, detail=f"未知的智能体类型: {agent_type}")

        new_agent = type_map[agent_type]()
        if agent_name:
            new_agent.name = agent_name

        if agent_type in ["document_generator", "mindmap_generator", "exercise_generator", "video_content"]:
            controller.register_generator(agent_type, new_agent)
        else:
            controller.register_agent(new_agent)

        return {"success": True, "message": f"智能体 {new_agent.name} ({new_agent.role}) 注册成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/agents/list")
async def list_agents(controller: MasterController = Depends(get_controller)):
    agents_info = []
    for name, agent in controller._agents.items():
        agents_info.append({
            "name": agent.name,
            "role": agent.role,
            "description": agent.description,
            "type": "generator" if name in controller._generator_agents else "pipeline",
        })
    return {"agents": agents_info}


@app.get("/api/v2/courses/list")
async def list_courses():
    courses = [
        {"id": "bigdata", "name": "大数据技术", "description": "Hadoop/Spark/Flink分布式计算", "chapters": 8},
        {"id": "clang", "name": "C语言程序设计", "description": "指针/内存管理/数据结构", "chapters": 12},
        {"id": "cpp", "name": "C++面向对象", "description": "类与对象/模板/STL", "chapters": 10},
        {"id": "python", "name": "Python编程", "description": "基础语法/数据分析/AI入门", "chapters": 10},
        {"id": "algorithm", "name": "算法与数据结构", "description": "排序/查找/图论/动态规划", "chapters": 14},
        {"id": "os", "name": "操作系统", "description": "进程管理/内存管理/文件系统", "chapters": 8},
    ]
    return {"courses": courses}


class TelemetryPayload(BaseModel):
    student_id: str = ""
    course_id: str = ""
    timestamp: int = 0
    session_duration: float = 0
    zone_dwell_times: dict = {}
    scroll_metrics: dict = {}
    mouse_metrics: dict = {}
    overload: dict = {}
    performance: dict = {}


@app.post("/api/v2/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    try:
        with database.get_db() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES LIKE 'telemetry_data'")
                if not cursor.fetchone():
                    cursor.execute("""
                        CREATE TABLE telemetry_data (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            student_id VARCHAR(100),
                            course_id VARCHAR(100),
                            timestamp BIGINT,
                            session_duration FLOAT,
                            zone_dwell_times JSON,
                            scroll_metrics JSON,
                            mouse_metrics JSON,
                            overload JSON,
                            performance JSON,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                cursor.execute(
                    """INSERT INTO telemetry_data
                       (student_id, course_id, timestamp, session_duration,
                        zone_dwell_times, scroll_metrics, mouse_metrics, overload, performance)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        payload.student_id,
                        payload.course_id,
                        payload.timestamp,
                        payload.session_duration,
                        json.dumps(payload.zone_dwell_times, ensure_ascii=False),
                        json.dumps(payload.scroll_metrics, ensure_ascii=False),
                        json.dumps(payload.mouse_metrics, ensure_ascii=False),
                        json.dumps(payload.overload, ensure_ascii=False),
                        json.dumps(payload.performance, ensure_ascii=False),
                    )
                )
                conn.commit()
                cursor.close()

            _update_student_telemetry(payload)

            return {"success": True, "message": "遥测数据已记录"}

        storage = database.load_local_storage()
        storage.setdefault("telemetry_data", []).append(payload.model_dump())
        database.save_local_storage(storage)

        _update_student_telemetry(payload)

        return {"success": True, "message": "遥测数据已记录到本地"}
    except Exception as e:
        return {"success": False, "message": f"记录失败: {str(e)}"}


def _update_student_telemetry(payload: TelemetryPayload) -> None:
    try:
        student_id = payload.student_id
        if not student_id or student_id == "anonymous":
            return

        contexts = list_student_contexts(student_id)
        if not contexts:
            return

        latest_ctx = contexts[0]
        state = load_state(student_id, latest_ctx)
        if not state:
            return

        state.update_telemetry({
            "session_duration": payload.session_duration,
            "zone_dwell_times": payload.zone_dwell_times,
            "scroll_metrics": payload.scroll_metrics,
            "mouse_metrics": payload.mouse_metrics,
            "overload": payload.overload,
            "performance": payload.performance,
            "last_telemetry_timestamp": payload.timestamp,
        })

        overload_data = payload.overload or {}
        overload_score = overload_data.get("current_score", 0)
        overload_triggered = overload_data.get("triggered", False)

        if overload_score >= 75 or overload_triggered:
            from state import EmotionType
            state.update_emotion(
                EmotionType.CONFUSED,
                intensity=min(1.0, overload_score / 100),
                trigger=f"认知超载检测: 得分={overload_score}"
            )
            state.metadata["cognitive_overload"] = True
            state.metadata["overload_score"] = overload_score

        save_state(state)
    except Exception:
        pass


@app.get("/api/v2/telemetry/{student_id}")
async def get_telemetry(student_id: str, limit: int = 20):
    try:
        with database.get_db() as conn:
            if conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(
                    "SELECT * FROM telemetry_data WHERE student_id = %s ORDER BY timestamp DESC LIMIT %s",
                    (student_id, limit),
                )
                rows = cursor.fetchall()
                cursor.close()
                for row in rows:
                    for key in ["zone_dwell_times", "scroll_metrics", "mouse_metrics", "overload", "performance"]:
                        if isinstance(row.get(key), str):
                            try:
                                row[key] = json.loads(row[key])
                            except (json.JSONDecodeError, TypeError):
                                pass
                return {"success": True, "data": rows}

        storage = database.load_local_storage()
        all_data = storage.get("telemetry_data", [])
        student_data = [d for d in all_data if d.get("student_id") == student_id][-limit:]
        return {"success": True, "data": student_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/vector-db/query")
async def query_vector_db(query: dict):
    return {
        "success": True,
        "message": "向量数据库接口预留，当前使用本地KNOWLEDGE_BASE",
        "results": [],
        "query": query.get("query", ""),
    }


@app.get("/api/v2/proactive/stream")
async def proactive_sse_stream(
    student_id: str = "",
    course_id: str = "bigdata",
    device_id: str = "default",
    last_msg_id: str = "",
    request: Request = None,
):
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    manager = get_connection_manager()
    try:
        queue = await manager.connect(student_id, device_id)
    except ConnectionRefusedError as e:
        raise HTTPException(status_code=503, detail=str(e))

    tutor = get_proactive_tutor()
    asyncio.create_task(tutor.on_login(student_id, course_id))

    if last_msg_id:
        missed = manager.get_missed_messages(student_id, last_msg_id)
        for msg in missed:
            queue.put_nowait(msg)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if isinstance(message, ProactiveMessage):
                    data = message.to_sse_data()
                    yield f"event: proactive\ndata: {data}\n\n"
                elif isinstance(message, dict):
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                elif message is None:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await manager.disconnect(student_id, device_id)
            logger.info(f"Proactive SSE closed: {student_id}/{device_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Student-ID": student_id,
        },
    )


@app.post("/api/v2/event/struggle")
async def report_struggle(event: StruggleEvent):
    if not event.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    tutor = get_proactive_tutor()
    asyncio.create_task(tutor.on_struggle(event))

    logger.info(f"Struggle event received: user={event.user_id}, content={event.current_content_id}")

    return {
        "success": True,
        "message": "Struggle event received, intervention dispatched",
        "user_id": event.user_id,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v2/proactive/status")
async def proactive_status():
    manager = get_connection_manager()
    return {
        "success": True,
        "stats": manager.get_stats(),
    }


@app.post("/api/v2/proactive/push")
async def manual_push(student_id: str, message: ProactiveMessage):
    manager = get_connection_manager()
    delivered = await manager.push_to_user(student_id, message)
    return {
        "success": True,
        "delivered_to": delivered,
        "student_id": student_id,
    }


class FlashcardRequest(BaseModel):
    student_id: str = ""
    course_id: str = "bigdata"
    chapter_name: str = ""
    chapter_content: str = Field("", min_length=1)


@app.post("/api/v2/flashcard/generate")
async def generate_flashcards(req: FlashcardRequest):
    from agents import FlashcardAgent
    agent = FlashcardAgent()
    state = StudentState(
        student_id=req.student_id,
        course_id=req.course_id,
        context_id=f"flashcard-{int(time.time())}",
    )
    state.metadata["current_chapter"] = req.chapter_name
    state.add_message(DialogueRole.STUDENT, req.chapter_content)
    state = await agent.run(state, chapter_content=req.chapter_content, chapter_name=req.chapter_name)
    result = state.metadata.get("flashcards", {"flashcards": []})
    return {"success": True, "data": result}


class TextbookChapterRequest(BaseModel):
    source: str = Field(..., min_length=1)
    keywords: str = ""


_textbook_chapter_cache = {}


@app.post("/api/v2/textbook/chapter")
async def get_textbook_chapter(req: TextbookChapterRequest):
    global _textbook_chapter_cache
    cache_key = f"{req.source}:{req.keywords}"
    if cache_key in _textbook_chapter_cache:
        return {"success": True, "data": _textbook_chapter_cache[cache_key]}

    context, sources, source_links = retrieve_knowledge([req.source, req.keywords])
    chapter_content = ""
    chapter_title = req.source
    sections = []

    if context and "未检索到" not in context:
        parts = context.split("\n\n")
        for part in parts:
            cleaned = part.strip()
            if not cleaned:
                continue
            if cleaned.startswith("[Doc_Ref:"):
                header_match = cleaned.split("]", 1)
                if len(header_match) > 1:
                    content_after = header_match[1].strip()
                    if content_after:
                        sections.append({
                            "title": header_match[0].replace("[Doc_Ref: ", "").replace("[Doc_Ref:", ""),
                            "content": content_after
                        })
            else:
                sections.append({"title": "", "content": cleaned})

        chapter_content = context
    else:
        chapter_content = f"未找到「{req.source}」的详细教材内容。请尝试与AI助手对话获取相关知识。"
        sections = [{"title": "提示", "content": chapter_content}]

    result = {
        "title": chapter_title,
        "sections": sections,
        "sources": sources,
        "sourceLinks": source_links,
    }
    if len(_textbook_chapter_cache) < 200:
        _textbook_chapter_cache[cache_key] = result
    return {"success": True, "data": result}


if __name__ == "__main__":
    print("\n" + "="*50)
    print("星识 (Star-Learn) 伴学系统正在启动...")
    print("请直接在浏览器打开链接: http://127.0.0.1:8000")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
