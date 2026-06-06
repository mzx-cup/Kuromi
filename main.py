from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, Union
import requests
import json
import re
import os
import subprocess
import tempfile
import hashlib
import bcrypt
import uvicorn
import logging
from datetime import datetime, timedelta
import time
import httpx
import numpy as np
from urllib.parse import quote
import db as database
import pymysql
from db import (
    save_classroom_record,
    get_classroom_records,
    get_classroom_record,
    update_classroom_record,
    delete_classroom_record,
    save_course_generation_status,
    get_course_generation_status,
    update_course_generation_status,
)
import asyncio
from contextlib import asynccontextmanager

from state import ChatRequestV2, ChatResponseV2, StudentState, StreamChatRequest, CognitiveStyle, DialogueRole, DebateRequest, LearningPortrait, CourseGenerationRequest, CourseData, SceneOutline, Slide, SlideContent, SlideElement, TeacherInfo, GenerateImageRequest, GenerateImageResponse, GenerateTTSRequest, GenerateTTSResponse, CourseSaveRequest, CourseListResponse, CourseChatRequest, InteractiveScene, TextCardComponent, QuizComponent, CodeEditorComponent, SimulationComponent, QuizOption, QuizGradeRequest, QuizGradeResponse, RunCodeRequest, RunCodeResponse, parse_interactive_scene
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
from llm_stream import (
    call_llm_stream, call_llm_stream_with_log, call_llm_async, close_http_client,
    call_llm_stream_with_log_messages,
)
from task_manager import get_task_manager, dispatch_resource_tasks, TaskStatus
from config import settings
from app.services.teacher.personas import get_persona_manager
from app.api.learning_path import generate_path_for_user

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, "html")
CSS_DIR = os.path.join(BASE_DIR, "css")
JS_DIR = os.path.join(BASE_DIR, "js")
STATIC_DIR = os.path.join(BASE_DIR, "static")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
VIDEO_DIR = os.path.join(BASE_DIR, "video")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用启动/关闭的生命周期事件。"""
    # Startup
    all_paths = [r.path for r in app.routes if hasattr(r, 'path')]
    v2_paths = [p for p in all_paths if 'v2' in p or 'textbook' in p]
    logger.info(f"[Startup] Total routes: {len(all_paths)}, v2/textbook: {len(v2_paths)}")
    yield
    # Shutdown
    await close_http_client()

app = FastAPI(lifespan=lifespan)

# ── 学习路径实时刷新防抖 ──
_path_refresh_debounce: dict[int, float] = {}

async def trigger_learning_path_refresh(user_id: int, trigger_source: str = "unknown"):
    """异步触发学习路径刷新（带5分钟防抖）。"""
    import time
    now = time.time()
    last = _path_refresh_debounce.get(user_id, 0)
    if now - last < 300:  # 5分钟内不重复触发
        print(f"[LearningPathRefresh] 跳过刷新 (user_id={user_id}, source={trigger_source}, 冷却中)")
        return
    _path_refresh_debounce[user_id] = now
    print(f"[LearningPathRefresh] 触发刷新 (user_id={user_id}, source={trigger_source})")
    try:
        await generate_path_for_user(user_id, force_refresh=False)
        print(f"[LearningPathRefresh] 刷新完成 (user_id={user_id})")
    except Exception as e:
        print(f"[LearningPathRefresh] 刷新失败 (user_id={user_id}): {e}")

def _safe_trigger_learning_path_refresh(user_id: int, trigger_source: str = "unknown"):
    """在同步上下文中安全地异步触发学习路径刷新（无事件循环时自动创建）。"""
    import asyncio, threading
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(trigger_learning_path_refresh(user_id, trigger_source))
    except RuntimeError:
        def _trigger():
            try:
                asyncio.run(trigger_learning_path_refresh(user_id, trigger_source))
            except Exception:
                pass
        threading.Thread(target=_trigger, daemon=True).start()

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

# ---- Static files (专注音乐 MP3 等资源) ----
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# ---- V2 API routes (Star-Learn 2.0) ----
from app.api import router as v2_router
app.include_router(v2_router)

# ---- Learning Path API (实时学情驱动路径生成) ----
from app.api.learning_path import router as learning_path_router
app.include_router(learning_path_router, prefix="/api/learning-path")

# ---- Memory API (用户长期记忆) ----
from app.api.memory import router as memory_router
app.include_router(memory_router, prefix="/api")

# ---- Profile API (用户画像) ----
from app.api.profile import router as profile_router
app.include_router(profile_router, prefix="/api")

# ---- Evaluation API (评估指标) ----
from app.api.evaluation import router as evaluation_router
app.include_router(evaluation_router, prefix="/api")

# ---- Bilibili Import API (B站视频导入) ----
from app.api.bilibili import router as bilibili_router
app.include_router(bilibili_router)
# ---- Courses API (课程中心) ----
from app.api.courses import router as courses_router
app.include_router(courses_router)

# ---- Mascot API (小星 AI 助手) ----
from app.api.mascot import router as mascot_router
app.include_router(mascot_router, prefix="/api")

# ---- Auth API (用户认证) ----
from app.api.auth import router as auth_router
app.include_router(auth_router)

# ---- Teacher API (教师端) ----
from app.api.teacher import router as teacher_router
app.include_router(teacher_router)

# ---- Datacenter API (数据仪表盘) ----
from app.api.datacenter import router as datacenter_router
app.include_router(datacenter_router)


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
    sessionId: str = ""           # 会话ID，用于关联对话历史
    userId: int = 0               # 用户ID，用于保存消息到数据库

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
    """使用 bcrypt 哈希密码（新注册/修改密码时调用）。"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """验证密码，兼容旧的 SHA256 和新的 bcrypt。
    若匹配旧 SHA256 格式，仍返回 True（建议用户尽快修改密码以升级）。
    """
    if hashed.startswith('$2b$') or hashed.startswith('$2a$'):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    # 兼容旧 SHA256（64 位十六进制）
    if len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed):
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == hashed
    return False

def get_login_request_meta(request: Request) -> tuple[str, str]:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else ""
    if not ip_address and request.client:
        ip_address = request.client.host or ""
    user_agent = request.headers.get("user-agent", "")
    return ip_address, user_agent

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
    """调用 MiniMax-Text-01 大模型生成内容（已完全切换自讯飞）"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.minimax_api_key}",
    }
    payload = {
        "model": settings.minimax_model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 8192,
    }
    try:
        response = requests.post(
            f"{settings.minimax_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
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


def call_llm_with_messages(messages: list[dict], temperature=0.3):
    """调用 MiniMax-Text-01，支持完整 messages 数组（含历史上下文）。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.minimax_api_key}",
    }
    payload = {
        "model": settings.minimax_model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 8192,
    }
    try:
        response = requests.post(
            f"{settings.minimax_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
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

@app.get("/pixel-pet-game.html")
def serve_pixel_pet_game():
    game_path = os.path.join(HTML_DIR, "pixel-pet-game.html")
    if os.path.exists(game_path):
        return FileResponse(game_path)
    raise HTTPException(status_code=404, detail="像素宠物游戏页面未找到")

@app.get("/register.html")
def serve_register():
    register_path = os.path.join(HTML_DIR, "register.html")
    if os.path.exists(register_path):
        return FileResponse(register_path)
    raise HTTPException(status_code=404, detail="注册页面未找到")


@app.get("/struggle_test.html")
def serve_struggle_test():
    """Serve the local struggle_test.html to allow browser-based testing (avoids file:// origin issues)."""
    struggle_path = os.path.join(HTML_DIR, "struggle_test.html")
    if os.path.exists(struggle_path):
        return FileResponse(struggle_path)
    raise HTTPException(status_code=404, detail="struggle_test.html 未找到")

@app.get("/css/{filename:path}")
def serve_css(filename: str):
    file_path = os.path.join(CSS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/css; charset=utf-8")
    raise HTTPException(status_code=404, detail="CSS文件未找到")

@app.get("/js/{filename:path}")
def serve_js(filename: str):
    file_path = os.path.join(JS_DIR, filename)
    logger.info(f"[serve_js] requested: {filename} -> resolved: {file_path} | exists: {os.path.exists(file_path)}")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript; charset=utf-8")
    raise HTTPException(status_code=404, detail=f"JS文件未找到: {filename}")

@app.get("/audio/{filename}")
def serve_audio(filename: str):
    audio_dir = os.path.join(BASE_DIR, "audio")
    file_path = os.path.join(audio_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="音频文件未找到")

@app.get("/video/{filename}")
def serve_video(filename: str):
    video_ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".m4v": "video/mp4",
    }
    media_type = media_types.get(video_ext)
    if media_type is None:
        raise HTTPException(status_code=404, detail="视频文件未找到")
    file_path = os.path.join(VIDEO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type=media_type)
    raise HTTPException(status_code=404, detail="视频文件未找到")

@app.get("/api/local-videos")
def list_local_videos():
    video_exts = {".mp4", ".webm", ".mov", ".m4v"}
    if not os.path.isdir(VIDEO_DIR):
        return {"videos": []}

    def natural_sort_key(filename: str):
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", filename)
        ]

    def clean_video_title(filename: str):
        title = os.path.splitext(filename)[0]
        title = re.sub(r"\(Av[^)]*\)", "", title).strip()
        title = re.sub(r"^\d+(?:\.\d+)*\.?", "", title).strip()
        return title or os.path.splitext(filename)[0]

    videos = []
    for filename in sorted(os.listdir(VIDEO_DIR), key=natural_sort_key):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in video_exts:
            continue
        videos.append({
            "id": hashlib.md5(filename.encode("utf-8")).hexdigest()[:12],
            "filename": filename,
            "title": clean_video_title(filename),
            "src": f"/video/{quote(filename)}",
        })
    return {"videos": videos}


# ============ 视频课程库 API ============

@app.get("/api/video-courses")
def list_video_courses(source_type: str = ""):
    courses = database.get_all_video_courses(source_type=source_type or None)
    for c in courses:
        for json_field in ("ai_timeline", "ai_questions"):
            val = c.get(json_field, "[]")
            if isinstance(val, str):
                try:
                    c[json_field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    c[json_field] = [] if json_field != "ai_timeline" else []
    return {"courses": courses}


@app.get("/api/video-courses/{course_id}")
def get_video_course_api(course_id: int):
    course = database.get_video_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    for json_field in ("ai_timeline", "ai_questions"):
        val = course.get(json_field, "[]")
        if isinstance(val, str):
            try:
                course[json_field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                course[json_field] = []
    return {"course": course}


class VideoCourseCreate(BaseModel):
    title: str
    source_type: str = "bilibili"
    subtitle: str = ""
    bvid: str = ""
    page: int = 1
    local_path: str = ""
    duration_label: str = "--:--"
    ai_summary: str = ""
    ai_timeline: list = []
    ai_questions: list = []
    ai_suggestion: str = ""
    created_by: str = ""


@app.post("/api/video-courses")
def create_video_course_api(req: VideoCourseCreate):
    course_id = database.create_video_course(
        title=req.title,
        source_type=req.source_type,
        subtitle=req.subtitle,
        bvid=req.bvid,
        page=req.page,
        local_path=req.local_path,
        duration_label=req.duration_label,
        ai_summary=req.ai_summary,
        ai_timeline=json.dumps(req.ai_timeline, ensure_ascii=False),
        ai_questions=json.dumps(req.ai_questions, ensure_ascii=False),
        ai_suggestion=req.ai_suggestion,
        created_by=req.created_by,
    )
    if course_id is None:
        raise HTTPException(status_code=500, detail="创建课程失败")
    return {"id": course_id, "message": "课程已创建"}


class VideoCourseUpdate(BaseModel):
    title: str = None
    source_type: str = None
    subtitle: str = None
    bvid: str = None
    page: int = None
    local_path: str = None
    duration_label: str = None
    ai_summary: str = None
    ai_timeline: list = None
    ai_questions: list = None
    ai_suggestion: str = None


@app.put("/api/video-courses/{course_id}")
def update_video_course_api(course_id: int, req: VideoCourseUpdate):
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="无更新字段")
    if "ai_timeline" in updates:
        updates["ai_timeline"] = json.dumps(updates["ai_timeline"], ensure_ascii=False)
    if "ai_questions" in updates:
        updates["ai_questions"] = json.dumps(updates["ai_questions"], ensure_ascii=False)
    ok = database.update_video_course(course_id, **updates)
    if not ok:
        raise HTTPException(status_code=404, detail="课程不存在或更新失败")
    return {"message": "课程已更新"}


@app.delete("/api/video-courses/{course_id}")
def delete_video_course_api(course_id: int):
    ok = database.delete_video_course(course_id)
    if not ok:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"message": "课程已删除"}


# ============ 播放列表 API ============

class PlaylistCreate(BaseModel):
    user_id: str
    name: str = "默认列表"


class PlaylistRename(BaseModel):
    name: str


@app.get("/api/video-playlists")
def list_playlists(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id 参数")
    playlists = database.get_user_playlists(user_id)
    for pl in playlists:
        for v in pl.get("videos", []):
            for json_field in ("ai_timeline", "ai_questions"):
                val = v.get(json_field, "[]")
                if isinstance(val, str):
                    try:
                        v[json_field] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        v[json_field] = []
    return {"playlists": playlists}


@app.post("/api/video-playlists")
def create_playlist_api(req: PlaylistCreate):
    pl_id = database.create_playlist(req.user_id, req.name)
    if pl_id is None:
        raise HTTPException(status_code=500, detail="创建播放列表失败")
    return {"id": pl_id, "message": "播放列表已创建"}


@app.put("/api/video-playlists/{playlist_id}")
def rename_playlist_api(playlist_id: int, req: PlaylistRename):
    ok = database.rename_playlist(playlist_id, req.name)
    if not ok:
        raise HTTPException(status_code=404, detail="播放列表不存在")
    return {"message": "播放列表已重命名"}


@app.delete("/api/video-playlists/{playlist_id}")
def delete_playlist_api(playlist_id: int):
    ok = database.delete_playlist(playlist_id)
    if not ok:
        raise HTTPException(status_code=404, detail="播放列表不存在")
    return {"message": "播放列表已删除"}


class PlaylistVideoAdd(BaseModel):
    playlist_id: int
    course_id: int
    position: int = None


class PlaylistVideoReorder(BaseModel):
    items: list


@app.post("/api/playlist-videos")
def add_playlist_video_api(req: PlaylistVideoAdd):
    pv_id = database.add_video_to_playlist(req.playlist_id, req.course_id, req.position)
    if pv_id is None:
        raise HTTPException(status_code=500, detail="添加视频失败")
    return {"id": pv_id, "message": "视频已添加到列表"}


@app.delete("/api/playlist-videos/{pv_id}")
def remove_playlist_video_api(pv_id: int):
    ok = database.remove_video_from_playlist(pv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="条目不存在")
    return {"message": "视频已从列表移除"}


@app.put("/api/playlist-videos/reorder")
def reorder_playlist_videos_api(req: PlaylistVideoReorder):
    ok = database.reorder_playlist_videos(req.items)
    if not ok:
        raise HTTPException(status_code=500, detail="排序失败")
    return {"message": "排序已保存"}


# ============ B站 视频信息代理 ============

@app.get("/api/bilibili/info")
def bilibili_video_info(bvid: str = ""):
    if not bvid:
        raise HTTPException(status_code=400, detail="缺少 bvid 参数")
    try:
        import urllib.request
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        req = urllib.request.Request(api_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            raise HTTPException(status_code=404, detail="B站视频不存在")
        video_data = data["data"]
        return {
            "bvid": bvid,
            "title": video_data.get("title", ""),
            "cover": video_data.get("pic", ""),
            "duration": video_data.get("duration", 0),
            "duration_label": f"{video_data.get('duration', 0) // 60}:{video_data.get('duration', 0) % 60:02d}",
            "owner": video_data.get("owner", {}).get("name", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取B站视频信息失败: {str(e)}")


@app.get("/api/bilibili/playurl")
async def bilibili_play_url(bvid: str = "", page: int = 1):
    """Fetch B站 video stream URL for native playback."""
    if not bvid:
        raise HTTPException(status_code=400, detail="缺少 bvid 参数")
    try:
        async with httpx.AsyncClient() as client:
            bili_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
            }
            # Step 1: Get video info (need cid for the page)
            info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            info_resp = await client.get(info_url, headers=bili_headers, timeout=15.0)
            info_data = info_resp.json()
            logging.info(f"[B站playurl] view API response: code={info_data.get('code')}, bvid={bvid}")
            if info_data.get("code") != 0:
                msg = info_data.get("message", "B站视频不存在")
                raise HTTPException(status_code=404, detail=f"B站API返回: {msg} (code={info_data.get('code')})")

            video_data = info_data["data"]
            pages = video_data.get("pages", [])
            cid = None
            if pages:
                for p in pages:
                    if p.get("page") == page:
                        cid = p["cid"]
                        break
                if cid is None:
                    cid = pages[0]["cid"]
            else:
                cid = video_data.get("cid", 0)

            if not cid:
                raise HTTPException(status_code=502, detail="无法获取视频 cid")

            # Step 2: Get play URL (fnval=0 for FLV, fnval=1 for DASH)
            for fnval in (0, 1):
                play_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval={fnval}&fourk=1"
                play_resp = await client.get(play_url, headers=bili_headers, timeout=15.0)
                play_data = play_resp.json()
                if play_data.get("code") != 0:
                    continue
                durl = play_data["data"].get("durl", [])
                if durl and durl[0].get("url"):
                    return {
                        "bvid": bvid,
                        "cid": cid,
                        "url": durl[0]["url"],
                        "backup_urls": durl[0].get("backup_url", []),
                        "quality": play_data["data"].get("quality", 0),
                        "format": play_data["data"].get("format", ""),
                        "duration": video_data.get("duration", 0),
                        "title": video_data.get("title", ""),
                    }
                # If fnval=1, check dash field
                dash = play_data["data"].get("dash")
                if dash:
                    videos = dash.get("video", [])
                    audios = dash.get("audio", [])
                    if videos:
                        return {
                            "bvid": bvid,
                            "cid": cid,
                            "dash_video_url": videos[0].get("baseUrl") or videos[0].get("base_url", ""),
                            "dash_audio_url": audios[0].get("baseUrl") or audios[0].get("base_url", "") if audios else "",
                            "quality": play_data["data"].get("quality", 0),
                            "format": "dash",
                            "duration": video_data.get("duration", 0),
                            "title": video_data.get("title", ""),
                        }
            raise HTTPException(status_code=502, detail="无可用的视频流")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取播放地址失败: {str(e)}")


@app.get("/api/bilibili/stream")
async def bilibili_stream(request: Request, url: str = ""):
    """Proxy B站 video stream with proper Referer header."""
    from urllib.parse import unquote
    url = unquote(url)
    if not url:
        raise HTTPException(status_code=400, detail="缺少 url 参数")

    range_header = request.headers.get("range", "")
    req_headers = {
        "Referer": "https://www.bilibili.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if range_header:
        req_headers["Range"] = range_header

    client = httpx.AsyncClient()
    cm = client.stream("GET", url, headers=req_headers, timeout=120.0)
    upstream = await cm.__aenter__()
    upstream_headers = upstream.headers
    status_code = upstream.status_code
    content_type = upstream_headers.get("content-type", "video/mp4")

    resp_headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
    }
    content_length = upstream_headers.get("content-length")
    if content_length:
        resp_headers["Content-Length"] = content_length
    content_range = upstream_headers.get("content-range")
    if content_range:
        resp_headers["Content-Range"] = content_range

    async def stream_video():
        try:
            async for chunk in upstream.aiter_bytes(chunk_size=1024 * 1024):
                yield chunk
            await cm.__aexit__(None, None, None)
        finally:
            await client.aclose()

    return StreamingResponse(
        stream_video(),
        media_type=content_type,
        status_code=status_code,
        headers=resp_headers
    )


WHITEBOARD_DRAW_SYSTEM_PROMPT = """你是一位精通教学可视化的白板绘图专家。请根据用户的描述，生成一系列白板绘图动作，以JSON数组格式输出。

## 输出格式要求
必须输出纯JSON数组，不要包含任何markdown代码块标记或额外解释。每个元素格式：
{
  "type": "动作类型",
  "params": { 参数对象 }
}

## 可用动作类型
- wb_draw_text: 写文字。params: {content, x, y, fontSize(可选,默认20), color(可选,默认#333)}
- wb_draw_shape: 几何图形。params: {shape: "rectangle|circle|triangle", x, y, width, height, fillColor(可选), strokeColor(可选,默认#333)}
- wb_draw_svg: SVG矢量图。params: {svg: "SVG字符串(不含<svg>外层标签)", x, y, width, height}
- wb_draw_latex: LaTeX公式。params: {latex, x, y, width(可选,默认400), color(可选)}
- wb_draw_chart: 图表。params: {chartType: "bar|line|pie|radar", data: {labels, legends, series}, x, y, width, height}
- wb_draw_table: 表格。params: {data: [["表头1",...],["行1数据",...]], x, y, width, height}
- wb_draw_line: 线条/箭头。params: {startX, startY, endX, endY, color(可选), width(可选), style(可选, "solid|dashed"), points(可选, ["","arrow"])}
- wb_draw_code: 代码块。params: {language, code, x, y, width(可选,默认500), height(可选,默认300), fileName(可选)}

## SVG 规范 (使用 wb_draw_svg 时)
- 必须简洁，使用 stroke 为主，fill="none" 或浅色半透明填充
- 坐标空间 viewBox="0 0 400 300"，所有坐标在此范围内
- 颜色使用深色描边 (#333, #2563eb, #dc2626)
- 文字标注用 <text> 元素，font-size="12"-"16"
- 一个SVG最多10-15个元素，简洁优先
- 不使用 <foreignObject>、外部CSS、JS

## 布局约束 (CRITICAL)
- 白板尺寸: 宽1000 x 高562.5
- 元素之间保持 ≥ 30px 间距，严禁重叠
- 内容从左上角开始排列，合理分布
- 文字颜色 #333，背景色不用设置
- 坐标取整数

## 设计原则
- 根据描述选择最合适的可视化方式：流程图用svg、公式用latex、数据用chart/table、几何用shape
- 如果是数学/物理概念，优先用svg绘制示意图配合latex标注公式
- 如果是数据结构/算法，用shape画框、line画箭头、text写标注
- 如果是代码讲解，用code块
- 每个action独立表达一个视觉元素，逐步构建完整画面
"""


class WhiteboardDrawRequest(BaseModel):
    description: str
    course_id: Optional[str] = ""
    scene_title: Optional[str] = ""
    auto_mode: Optional[bool] = False
    is_custom_prompt: Optional[bool] = False


@app.post("/api/whiteboard/draw")
async def whiteboard_draw(request: WhiteboardDrawRequest):
    """AI 白板智能绘图"""
    description = request.description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="描述不能为空")

    # 构建 user prompt
    user_prompt = f"用户想绘制以下内容：\n{description}\n\n"
    if request.scene_title:
        user_prompt += f"场景标题：{request.scene_title}\n"
    if request.auto_mode:
        user_prompt += "这是课程自动生成的白板内容，请确保绘图具有教学性和准确性。\n"
    if request.is_custom_prompt:
        user_prompt += "这是用户的自定义绘图请求，请尽可能满足用户的具体要求。\n"
    user_prompt += "请直接输出JSON动作数组，不要有任何额外解释。"

    try:
        llm_response = await call_llm_async(
            system_prompt=WHITEBOARD_DRAW_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
        )
    except Exception as e:
        print(f"[whiteboard_draw] LLM call failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI 绘图请求失败: {str(e)}")

    # 提取 JSON 数组
    actions = None
    try:
        # 尝试从响应中提取 JSON 数组
        text = llm_response.strip()
        # 去掉 markdown 代码块
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        actions = json.loads(text)
        if not isinstance(actions, list):
            # 有些模型可能返回 {"actions": [...]} 格式
            if isinstance(actions, dict) and "actions" in actions:
                actions = actions["actions"]
            else:
                actions = [actions] if isinstance(actions, dict) else None
    except Exception as e:
        print(f"[whiteboard_draw] JSON parse failed: {e}, raw={llm_response[:500]}")
        # 尝试用正则提取数组
        try:
            match = re.search(r'\[.*\]', llm_response.replace('\n', ''), re.DOTALL)
            if match:
                actions = json.loads(match.group())
        except Exception as e2:
            print(f"[whiteboard_draw] Regex extract failed: {e2}")

    if not actions or not isinstance(actions, list):
        raise HTTPException(status_code=500, detail="AI 未能生成有效的绘图指令")

    # 过滤并规范化 actions
    valid_types = {
        "wb_draw_text", "wb_draw_shape", "wb_draw_svg", "wb_draw_latex",
        "wb_draw_chart", "wb_draw_table", "wb_draw_line", "wb_draw_code",
        "wb_clear", "wb_delete", "wb_open", "wb_close",
    }
    normalized = []
    for act in actions:
        if not isinstance(act, dict):
            continue
        t = act.get("type") or act.get("name")
        if t not in valid_types:
            continue
        params = act.get("params") or act.get("parameters") or {}
        if not isinstance(params, dict):
            params = {}
        normalized.append({"type": t, "params": params})

    if not normalized:
        raise HTTPException(status_code=500, detail="AI 生成的绘图指令为空或格式不正确")

    return {"success": True, "actions": normalized}


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
def login(body: LoginRequest, http_request: Request):
    ip_address, user_agent = get_login_request_meta(http_request)
    if not body.username or not body.password:
        database.record_login_event(None, body.username, False, "用户名和密码不能为空", ip_address, user_agent)
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    user = database.get_user_by_username(body.username)
    if not user:
        database.record_login_event(None, body.username, False, "用户不存在", ip_address, user_agent)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(body.password, user['password']):
        database.record_login_event(user.get('id'), body.username, False, "密码错误", ip_address, user_agent)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    database.update_last_login(user['id'])
    database.record_login_event(user['id'], user['username'], True, "", ip_address, user_agent)
    avatar = user['avatar'] or f"https://api.dicebear.com/7.x/adventurer/svg?seed={body.username}&backgroundColor=b6e3f4"
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
        "preferences": get_user_preferences_internal(user['id']),
        "themePrefs": database.get_user_theme_prefs(user['id'])
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

class ThemeSyncRequest(BaseModel):
    userId: int = None
    mode: str = "light"
    theme: str = "warm-morning"
    wallpaper: dict = {}
    customThemes: list = []

@app.post("/api/user/theme/sync")
def sync_theme_to_server(request: ThemeSyncRequest):
    """Save user theme preferences to server."""
    try:
        if not request.userId:
            return {"ok": False, "reason": "not_logged_in"}
        prefs = {
            "mode": request.mode,
            "theme": request.theme,
            "wallpaper": request.wallpaper,
            "customThemes": request.customThemes
        }
        database.save_user_theme_prefs(request.userId, prefs)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}

@app.get("/api/user/theme/sync")
def get_theme_from_server(user_id: int = None):
    """Load user theme preferences from server."""
    try:
        if not user_id:
            return {"theme": None}
        prefs = database.get_user_theme_prefs(user_id)
        if prefs:
            return prefs
        return {"theme": None}
    except:
        return {"theme": None}

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
        profile_json = json.dumps(request.profile, ensure_ascii=False)
        grade_record = request.lastGradeRecord

        database.save_user_profile(user_id, profile_json, evaluation_json, grade_record)
        # 注意：学习路径不再通过 /api/progress/save 保存。
        # 路径结构由后端 LLM 在 /api/learning-path/generate 中生成并持久化到 learning_path 表。
        # 节点状态由规则引擎/LLM 分析器写入 learning_path_nodes 表。
        # 前端只读取，不直接修改路径结构。

        # 同时保存到 learning_records 和 user_evaluations
        ev = request.evaluation or {}
        try:
            database.save_learning_record(
                user_id=user_id,
                interaction_count=ev.get("interactionCount", 0),
                code_practice_time=ev.get("codePracticeTime", 0),
                socratic_pass_rate=ev.get("socraticPassRate", 0.0),
                difficulty_level=ev.get("difficultyLevel", "basic"),
                profile_json=evaluation_json,
            )
        except Exception as e:
            print(f"[ProgressSave] learning_records 保存失败（非阻塞）: {e}")

        try:
            database.save_user_evaluation(user_id, ev)
        except Exception as e:
            print(f"[ProgressSave] user_evaluations 保存失败（非阻塞）: {e}")

        # 异步触发学习路径刷新（不阻塞响应）
        _safe_trigger_learning_path_refresh(user_id, "progress_save")

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

@app.get("/course-learn.html")
def serve_course_learn():
    course_learn_path = os.path.join(HTML_DIR, "course-learn.html")
    if os.path.exists(course_learn_path):
        return FileResponse(course_learn_path)
    raise HTTPException(status_code=404, detail="课程学习页面未找到")

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

@app.get("/html/concept-analyzer.html")
def serve_concept_analyzer():
    path = os.path.join(HTML_DIR, "concept-analyzer.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="概念拆解仪页面未找到")

@app.get("/html/ai-pair-programming.html")
def serve_ai_pair_programming():
    return RedirectResponse(url="/code.html?mode=fix&source=pair", status_code=307)

@app.get("/html/architecture-blueprint.html")
def serve_architecture_blueprint():
    path = os.path.join(HTML_DIR, "architecture-blueprint.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="架构蓝图页面未找到")

@app.get("/generation-preview.html")
def serve_generation_preview():
    path = os.path.join(HTML_DIR, "generation-preview.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="课程生成预览页面未找到")

@app.get("/classroom.html")
def serve_classroom():
    path = os.path.join(HTML_DIR, "classroom.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="课堂页面未找到")

# ---- Teacher pages ----
@app.get("/teacher-dashboard.html")
def serve_teacher_dashboard():
    path = os.path.join(HTML_DIR, "teacher-dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="教师仪表盘页面未找到")

@app.get("/teacher-class.html")
def serve_teacher_class():
    path = os.path.join(HTML_DIR, "teacher-class.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="班级管理页面未找到")

@app.get("/teacher-manage.html")
def serve_teacher_manage():
    path = os.path.join(HTML_DIR, "teacher-manage.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="学生管理页面未找到")

@app.get("/teacher-exam.html")
def serve_teacher_exam():
    path = os.path.join(HTML_DIR, "teacher-exam.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="考试管理页面未找到")

@app.get("/teacher-content.html")
def serve_teacher_content():
    path = os.path.join(HTML_DIR, "teacher-content.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="内容管理页面未找到")

@app.get("/data-dashboard.html")
def serve_data_dashboard():
    path = os.path.join(HTML_DIR, "data-dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="数据仪表盘页面未找到")

# ========== Socratic AI API ==========

class SocraticRoleRequest(BaseModel):
    role: str = Field(default="teacher", description="角色类型: teacher 或 interviewer")
    user_id: Optional[int] = Field(default=None, description="用户ID")


class SocraticQuestionRequest(BaseModel):
    role: str = Field(default="teacher", description="角色类型: teacher 或 interviewer")
    user_id: Optional[int] = Field(default=None, description="用户ID")


class SocraticScoreRequest(BaseModel):
    role: str = Field(default="teacher", description="角色类型: teacher 或 interviewer")
    question: str = Field(description="问题内容")
    answer: str = Field(description="用户回答")
    user_id: Optional[int] = Field(default=None, description="用户ID")


class SocraticTTSRequest(BaseModel):
    text: str = Field(description="要转换的文本")
    voice_id: int = Field(default=0, ge=0, le=4, description="音色ID: 0-4")


class SocraticTTSResponse(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    error: Optional[str] = None


class SocraticCheckpointRequest(BaseModel):
    topic: str = Field(default="", description="检查点主题/知识盲区")
    understood: bool = Field(description="用户是否理解")
    message_timestamp: Union[int, str] = Field(default=0, description="消息时间戳")
    course_id: Optional[str] = Field(default=None, description="课程ID")


# 音色配置 (MiniMax speech-2.8-hd 模型)
VOICE_CONFIGS = [
    {"name": "晓雅", "id": "female-tianmei", "description": "女声，甜美清脆"},
    {"name": "云起", "id": "male-qn-qingse", "description": "男声，青年清朗"},
    {"name": "雨辰", "id": "male-qn-jingying", "description": "男声，青年精英"},
    {"name": "苏格拉底", "id": "female-tianmei", "description": "女声，甜美清脆"},
    {"name": "雅典娜", "id": "female-chengshu", "description": "女声，成熟知性"},
]


def get_user_profile_for_socratic(user_id: int = None) -> dict:
    """获取用户画像用于生成个性化问题"""
    if user_id:
        profile = database.get_user_profile(user_id)
        if profile and profile.get("profile_json"):
            try:
                return json.loads(profile["profile_json"])
            except (json.JSONDecodeError, TypeError):
                pass
    return {}


def generate_socratic_question(role: str, user_profile: dict = None) -> dict:
    """使用 AI 生成苏格拉底问题"""
    profile_context = ""
    if user_profile:
        learning_direction = user_profile.get("learningDirection", "编程与技术")
        languages = user_profile.get("languages", ["Python"])
        code_skill = user_profile.get("codeSkill", "intermediate")
        profile_context = f"用户学习方向: {learning_direction}，擅长语言: {', '.join(languages)}，代码水平: {code_skill}。"

    if role == "interviewer":
        system_prompt = f"""你是一位专业的技术面试官。你需要根据用户的背景生成一个合适的技术面试问题。

{profile_context}

要求：
1. 问题应该考察用户对核心概念的理解，而非死记硬背
2. 问题应该有深度，能引发思考和讨论
3. 同时给出一个简短的提示，帮助用户组织答案
4. 返回格式：{{"question": "问题", "hint": "提示"}}

请生成一个面试问题："""
    else:
        system_prompt = f"""你是一位循循善诱的老师。你需要根据用户的背景生成一个苏格拉底式的问题，通过提问引导用户深入理解知识点。

{profile_context}

要求：
1. 问题应该从简单到复杂，逐步引导
2. 问题应该联系实际应用场景
3. 同时给出一个简短的提示，帮助用户思考
4. 返回格式：{{"question": "问题", "hint": "提示"}}

请生成一个问题："""

    try:
        question_text = asyncio.run(call_llm_async(system_prompt, "请生成一个问题", temperature=0.7))
        import re
        match = re.search(r'"question":\s*"([^"]+)"', question_text)
        hint_match = re.search(r'"hint":\s*"([^"]+)"', question_text)
        if match and hint_match:
            return {
                "question": match.group(1),
                "hint": hint_match.group(1)
            }
    except Exception as e:
        logger.error(f"生成苏格拉底问题失败: {e}")

    return {
        "question": "请解释一下你对这个主题的理解？",
        "hint": "可以从定义、原理、应用场景三个方面来回答"
    }


def score_socratic_answer(role: str, question: str, answer: str, user_profile: dict = None) -> dict:
    """使用 AI 对用户回答进行评分和反馈（直接使用 MiniMax API 避免编码问题）"""
    profile_context = ""
    if user_profile:
        learning_direction = user_profile.get("learningDirection", "编程与技术")
        languages = user_profile.get("languages", ["Python"])
        profile_context = f"用户学习方向: {learning_direction}，擅长语言: {', '.join(languages)}。"

    if role == "interviewer":
        system_prompt = f"""你是一位专业的技术面试官，正在评估候选人的回答。

背景：{profile_context}
问题：{question}
用户回答：{answer}

请评估用户回答的质量，从以下几个方面打分（满分100）：
1. 答案准确性 (0-30)
2. 回答深度 (0-30)
3. 表达清晰度 (0-20)
4. 思考逻辑性 (0-20)

同时给出简短的反馈和建议。

返回格式：
{{"score": 分数, "feedback": "反馈内容"}}
"""
    else:
        system_prompt = f"""你是一位循循善诱的老师，正在评估学生的回答。

背景：{profile_context}
问题：{question}
学生回答：{answer}

请评估学生回答的质量，从以下几个方面打分（满分100）：
1. 理解准确性 (0-30)
2. 思考深度 (0-30)
3. 表达清晰度 (0-20)
4. 联系实际 (0-20)

同时给出简短的鼓励和建议。

返回格式：
{{"score": 分数, "feedback": "反馈内容"}}
"""

    try:
        result_text = call_llm(system_prompt, "请评估回答", temperature=0.3)

        import re
        score_match = re.search(r'"score":\s*(\d+)', result_text)
        feedback_match = re.search(r'"feedback":\s*"([^"]+)"', result_text)
        if score_match and feedback_match:
            return {
                "score": int(score_match.group(1)),
                "feedback": feedback_match.group(1)
            }
    except Exception as e:
        logger.error(f"评分失败: {e}")

    return {
        "score": 75,
        "feedback": "回答已记录，感谢你的参与！"
    }


@app.post("/api/socratic/role")
def set_socratic_role(request: SocraticRoleRequest):
    """设置AI角色并返回第一个问题"""
    try:
        role = request.role if request.role in ["teacher", "interviewer"] else "teacher"
        user_profile = get_user_profile_for_socratic(request.user_id)
        question_data = generate_socratic_question(role, user_profile)

        return {
            "success": True,
            "role": role,
            "question": {
                "number": "Q1",
                "text": question_data["question"],
                "hint": question_data["hint"]
            }
        }
    except Exception as e:
        logger.error(f"设置角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置角色失败: {str(e)}")


@app.post("/api/socratic/question")
def get_socratic_question(request: SocraticQuestionRequest):
    """获取新的苏格拉底问题"""
    try:
        role = request.role if request.role in ["teacher", "interviewer"] else "teacher"
        user_profile = get_user_profile_for_socratic(request.user_id)
        question_data = generate_socratic_question(role, user_profile)

        return {
            "success": True,
            "question": {
                "number": "Q1",
                "text": question_data["question"],
                "hint": question_data["hint"]
            }
        }
    except Exception as e:
        logger.error(f"获取问题失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取问题失败: {str(e)}")


@app.post("/api/socratic/score")
def score_answer(request: SocraticScoreRequest):
    """对用户回答进行评分"""
    try:
        role = request.role if request.role in ["teacher", "interviewer"] else "teacher"
        user_profile = get_user_profile_for_socratic(request.user_id)
        result = score_socratic_answer(role, request.question, request.answer, user_profile)

        return {
            "success": True,
            "score": result["score"],
            "feedback": result["feedback"]
        }
    except Exception as e:
        logger.error(f"评分失败: {e}")
        raise HTTPException(status_code=500, detail=f"评分失败: {str(e)}")


@app.post("/api/socratic/checkpoint")
def socratic_checkpoint(request: SocraticCheckpointRequest):
    """记录苏格拉底交互确认点的用户反馈"""
    try:
        # 这里可以接入知识掌握度追踪系统
        # 简单实现：打印日志并返回成功
        logger.info(
            f"[SocraticCheckpoint] topic={request.topic}, understood={request.understood}, "
            f"course={request.course_id}, ts={request.message_timestamp}"
        )

        # TODO: 接入实际的知识掌握度数据库
        # 例如：更新用户在该知识点上的掌握度评分
        # update_knowledge_mastery(user_id, request.topic, request.understood)

        return {
            "success": True,
            "understood": request.understood,
            "topic": request.topic,
            "message": "已记录" if request.understood else "进入苏格拉底深度诊断模式"
        }
    except Exception as e:
        logger.error(f"苏格拉底检查点记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"记录失败: {str(e)}")


@app.post("/api/socratic/tts")
def text_to_speech(request: SocraticTTSRequest) -> SocraticTTSResponse:
    """使用 MiniMax TTS 将文本转换为语音"""
    try:
        # 验证文本不为空
        if not request.text or not request.text.strip():
            logger.error("TTS 请求文本为空")
            return SocraticTTSResponse(
                success=False,
                error="请求文本不能为空"
            )

        voice_id = max(0, min(4, request.voice_id))
        voice = VOICE_CONFIGS[voice_id]
        logger.info(f"TTS 请求: text长度={len(request.text)}, voice_id={voice_id}, voice.id={voice['id']}")

        # 使用 t2a_v2 接口，speech-2.8-hd 模型，group_id 作为 URL 参数
        tts_url = f"{settings.minimax_api_url}/t2a_v2?GroupId={settings.minimax_group_id}"

        headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # MiniMax TTS API v2 格式（form-data）
        data = {
            "model": "speech-2.8-hd",
            "text": request.text.strip(),
            "voice_id": voice["id"],
            "output_format": "hex",
            "sample_rate": 32000,
            "speed": 1.0,
            "volume": 1.0,
            "pitch": 0
        }

        logger.info(f"TTS 完整data: {data}")
        client = httpx.Client(timeout=30.0)
        response = client.post(tts_url, headers=headers, data=data)

        if response.status_code != 200:
            logger.error(f"TTS API 返回错误: {response.status_code}, body: {response.text[:500]}")
            return SocraticTTSResponse(
                success=False,
                error=f"TTS API 返回错误: {response.status_code}, {response.text[:200]}"
            )

        # 判断响应格式：application/json 为 JSON 格式，否则为二进制音频
        content_type = response.headers.get("content-type", "")
        logger.info(f"TTS 响应类型: {content_type}, 内容长度: {len(response.content)}")
        result = response.json()
        logger.info(f"TTS JSON响应: {result}")

        # 检查 API 错误
        if result.get("base_resp", {}).get("status_code") != 0:
            err_msg = result.get("base_resp", {}).get("status_msg", "TTS API 错误")
            logger.error(f"TTS API错误: {err_msg}, 完整响应: {result}")
            return SocraticTTSResponse(
                success=False,
                error=f"TTS API错误: {err_msg}"
            )

        # 获取音频数据（hex 格式）
        audio_hex = result.get("data", {}).get("audio", "")
        if not audio_hex:
            logger.error(f"TTS API未返回audio字段, 响应: {result}")
            return SocraticTTSResponse(
                success=False,
                error="TTS API 未返回音频数据"
            )

        # 解码 hex 音频数据
        import binascii
        try:
            audio_bytes = binascii.unhexlify(audio_hex)
        except Exception as e:
            logger.error(f"音频 hex 解码失败: {e}")
            return SocraticTTSResponse(
                success=False,
                error=f"音频解码失败"
            )

        # 保存音频文件
        audio_dir = os.path.join(BASE_DIR, "audio")
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)

        filename = f"tts_{int(time.time())}_{voice_id}.mp3"
        audio_path = os.path.join(audio_dir, filename)

        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        return SocraticTTSResponse(
            success=True,
            audio_url=f"/audio/{filename}"
        )

    except Exception as e:
        logger.error(f"TTS 生成失败: {e}")
        return SocraticTTSResponse(
            success=False,
            error=f"TTS 生成失败: {str(e)}"
        )


@app.post("/api/socratic/asr")
async def speech_to_text(request: Request):
    """使用百度语音识别将音频转换为文字"""
    try:
        # 获取上传的音频文件
        form_data = await request.form()
        audio_file = form_data.get("audio")

        if not audio_file:
            return {"success": False, "error": "未找到音频文件"}

        # 读取音频数据
        audio_data = await audio_file.read()
        if not audio_data:
            return {"success": False, "error": "音频数据为空"}

        # 检查百度 ASR 配置
        if not settings.baidu_asr_api_key or not settings.baidu_asr_secret_key:
            logger.error("百度 ASR API 密钥未配置")
            return {"success": False, "error": "语音识别服务未配置"}

        # 保存临时文件
        import tempfile
        import uuid
        import subprocess

        temp_dir = tempfile.gettempdir()
        input_file = os.path.join(temp_dir, f"asr_input_{uuid.uuid4().hex}")
        output_file = os.path.join(temp_dir, f"asr_output_{uuid.uuid4().hex}.wav")

        # 根据文件头判断格式
        file_sig = audio_data[:12]
        is_wav = b'RIFF' in audio_data[:12] and b'WAVE' in audio_data[:12]
        is_webm = b'\x1A\x45\xDF\xA3' in audio_data[:4] or b'webm' in audio_data[:12]

        ext = '.wav' if is_wav else '.webm'
        input_file = input_file + ext

        with open(input_file, "wb") as f:
            f.write(audio_data)

        try:
            # 获取百度 access token
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            token_params = {
                "grant_type": "client_credentials",
                "client_id": settings.baidu_asr_api_key,
                "client_secret": settings.baidu_asr_secret_key
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                token_response = await client.post(token_url, data=token_params)
                token_result = token_response.json()
                access_token = token_result.get("access_token")

                if not access_token:
                    logger.error(f"获取百度 access token 失败: {token_result}")
                    return {"success": False, "error": "获取访问令牌失败"}

                # 尝试转换音频格式
                pcm_data = None

                if is_wav:
                    # WAV 文件：尝试直接读取并重采样
                    try:
                        from scipy.io import wavfile
                        from scipy import signal
                        sample_rate, wav_data = wavfile.read(input_file)
                        # 重采样到 16kHz
                        if sample_rate != 16000:
                            num_samples = int(len(wav_data) * 16000 / sample_rate)
                            wav_data = signal.resample(wav_data, num_samples)
                        # 转换为单声道 16bit PCM
                        if len(wav_data.shape) > 1:
                            wav_data = wav_data[:, 0]
                        wav_data = wav_data.astype(np.int16)
                        pcm_data = wav_data.tobytes()
                        logger.info(f"WAV 转换成功: 采样率=16000, 长度={len(pcm_data)}")
                    except Exception as e:
                        logger.error(f"WAV 处理失败: {e}")

                # 如果 pcm_data 为空，尝试用 ffmpeg 转换
                if pcm_data is None:
                    # 查找 ffmpeg
                    ffmpeg_paths = ['ffmpeg', 'ffmpeg.exe',
                                   r"C:\Apps\Anaconda3\Library\bin\ffmpeg.exe",
                                   r"C:\Apps\ffmpeg\bin\ffmpeg.exe",
                                   os.path.join(os.path.dirname(__file__), "ffmpeg.exe")]
                    ffmpeg_cmd = None
                    for fp in ffmpeg_paths:
                        if os.path.exists(fp) or fp == 'ffmpeg' or fp == 'ffmpeg.exe':
                            try:
                                result = subprocess.run([fp, '-version'], capture_output=True, timeout=5)
                                if result.returncode == 0:
                                    ffmpeg_cmd = fp
                                    break
                            except:
                                pass

                    if ffmpeg_cmd:
                        # 使用 ffmpeg 转换
                        cmd = [ffmpeg_cmd, "-y", "-i", input_file,
                               "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
                               "-f", "s16le", "pipe:1"]
                        result = subprocess.run(cmd, capture_output=True, timeout=60)
                        if result.returncode == 0:
                            pcm_data = result.stdout
                            logger.info(f"ffmpeg 转换成功: 长度={len(pcm_data)}")
                        else:
                            logger.error(f"ffmpeg 转换失败: {result.stderr.decode()}")
                    else:
                        logger.error("未找到 ffmpeg，无法转换音频格式")
                        return {"success": False, "error": "音频格式转换工具未安装（请安装 ffmpeg）"}

                if not pcm_data:
                    return {"success": False, "error": "音频转换失败"}

                # 调用百度 ASR
                asr_url = f"https://vop.baidu.com/server_api?dev_pid=1537&token={access_token}"
                asr_response = await client.post(
                    asr_url,
                    data=pcm_data,
                    params={"dev_pid": 1537},
                    headers={"Content-Type": "audio/pcm; rate=16000"}
                )

                asr_result = asr_response.json()
                logger.info(f"百度 ASR 响应: {asr_result}")

                if asr_result.get("err_no") == 0:
                    result_list = asr_result.get("result", [])
                    if result_list:
                        text = result_list[0]
                        return {"success": True, "text": text}
                    else:
                        return {"success": True, "text": ""}
                else:
                    err_msg = asr_result.get("err_msg", "语音识别失败")
                    logger.error(f"百度 ASR 错误: {err_msg}")
                    return {"success": False, "error": err_msg}

        finally:
            # 清理临时文件
            if os.path.exists(input_file):
                os.remove(input_file)
            if os.path.exists(output_file):
                os.remove(output_file)

    except Exception as e:
        logger.error(f"ASR 处理失败: {e}")
        return {"success": False, "error": f"语音识别失败: {str(e)}"}


@app.get("/api/socratic/voices")
def get_voice_list():
    """获取音色列表"""
    return {
        "success": True,
        "voices": [
            {"id": i, "name": v["name"], "description": v["description"]}
            for i, v in enumerate(VOICE_CONFIGS)
        ]
    }


# ============================================================
# 学生画像 API（6维度）
# ============================================================

class PortraitUpdateRequest(BaseModel):
    user_id: int
    source: str = "socratic"  # socratic, code, chat, index, other
    interaction_data: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/profile/portrait/update")
def update_portrait(request: PortraitUpdateRequest):
    """基于交互数据更新学生的6维画像"""
    try:
        existing_portrait = database.get_student_portrait(request.user_id)

        if existing_portrait is None:
            existing_portrait = {
                "knowledge_mastery": {"topics": [], "overall": 0.0},
                "code_skill": {"level": "beginner", "strong_areas": [], "weak_areas": [], "last_updated": ""},
                "cognitive_style": {"type": "实践型", "confidence": 0.0, "last_updated": ""},
                "learning_goal": {"current": "", "target_positions": [], "timeframe": "", "last_updated": ""},
                "weakness": {"areas": [], "last_detected": "", "last_updated": ""},
                "focus_level": {"current": "中等专注", "trend": "stable", "last_updated": ""},
                "last_synced": ""
            }

        system_prompt = """你是一个教育数据分析智能体。分析学生交互数据，更新6维动态画像。
当前画像：{existing_portrait}
交互数据：{interaction_data}
交互来源：{source}

只输出纯JSON格式的更新内容，不要任何其他文字。输出格式：
{{"knowledge_mastery": {{"topics": [{{"name": "知识点名", "level": 0.0-1.0, "last_updated": "日期"}}], "overall": 0.0-1.0}}, "code_skill": {{"level": "beginner/intermediate/advanced", "strong_areas": [], "weak_areas": [], "last_updated": "日期"}}, "cognitive_style": {{"type": "视觉型/文字型/实践型", "confidence": 0.0-1.0, "last_updated": "日期"}}, "learning_goal": {{"current": "目标", "target_positions": [], "timeframe": "", "last_updated": "日期"}}, "weakness": {{"areas": [], "last_detected": "日期", "last_updated": "日期"}}, "focus_level": {{"current": "高专注/中等专注/需要引导", "trend": "stable/improving/declining", "last_updated": "日期"}}}}"""

        user_prompt = f"当前画像：{json.dumps(existing_portrait, ensure_ascii=False)}\n交互数据：{json.dumps(request.interaction_data, ensure_ascii=False)}\n交互来源：{request.source}"

        try:
            llm_response = call_llm(system_prompt, user_prompt, temperature=0.3)
            updated_portrait = extract_json(llm_response)
            if not updated_portrait:
                return {"success": False, "error": "AI解析失败"}
        except Exception as e:
            logger.error(f"画像更新失败: {e}")
            return {"success": False, "error": str(e)}

        database.save_student_portrait(request.user_id, updated_portrait)
        return {"success": True, "portrait": updated_portrait}

    except Exception as e:
        logger.error(f"画像更新异常: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/profile/portrait/{user_id}")
def get_portrait(user_id: int):
    """获取学生的6维画像"""
    try:
        portrait = database.get_student_portrait(user_id)
        if portrait is None:
            return {"success": True, "portrait": None, "message": "暂无画像数据"}
        return {"success": True, "portrait": portrait}
    except Exception as e:
        logger.error(f"获取画像失败: {e}")
        return {"success": False, "error": str(e)}


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

        # 从 learning_records 和 user_evaluations 补充/覆盖更实时的指标
        try:
            lr = database.get_learning_record(user_id)
            if lr:
                ev = result.get("evaluation") or {}
                ev["interactionCount"] = ev.get("interactionCount") or lr.get("interaction_count", 0)
                ev["socraticPassRate"] = ev.get("socraticPassRate") or lr.get("socratic_pass_rate", 0.0)
                ev["difficultyLevel"] = ev.get("difficultyLevel") or lr.get("difficulty_level", "basic")
                ev["codePracticeTime"] = ev.get("codePracticeTime") or lr.get("code_practice_time", 0)
                # profile_json 中可能存了 focus_time_today 等
                if lr.get("profile_json"):
                    try:
                        lr_profile = json.loads(lr["profile_json"]) if isinstance(lr["profile_json"], str) else lr["profile_json"]
                        if isinstance(lr_profile, dict):
                            ev["focusTimeToday"] = ev.get("focusTimeToday") or lr_profile.get("focus_time_today", 0)
                            ev["flashcardsStudied"] = ev.get("flashcardsStudied") or lr_profile.get("flashcards_studied", 0)
                            ev["streakDays"] = ev.get("streakDays") or lr_profile.get("streak_days", 0)
                    except Exception:
                        pass
                result["evaluation"] = ev
        except Exception as e:
            print(f"[ProgressLoad] learning_records 读取失败（非阻塞）: {e}")

        # 从 user_evaluations（今日）补充更实时的指标
        try:
            from datetime import date
            ue = database.get_user_evaluation(user_id, record_date=date.today().isoformat())
            if ue:
                ev = result.get("evaluation") or {}
                if ue.get("interaction_count") is not None:
                    ev["interactionCount"] = ue["interaction_count"]
                if ue.get("socratic_pass_rate") is not None:
                    ev["socraticPassRate"] = ue["socratic_pass_rate"]
                if ue.get("difficulty_level"):
                    ev["difficultyLevel"] = ue["difficulty_level"]
                if ue.get("code_practice_time") is not None:
                    ev["codePracticeTime"] = ue["code_practice_time"]
                if ue.get("focus_time_today") is not None:
                    ev["focusTimeToday"] = ue["focus_time_today"]
                if ue.get("flashcards_studied") is not None:
                    ev["flashcardsStudied"] = ue["flashcards_studied"]
                if ue.get("streak_days") is not None:
                    ev["streakDays"] = ue["streak_days"]
                # eval_json 中可能包含 interactionHistory / lastStudyDate
                if ue.get("eval_json"):
                    try:
                        ej = json.loads(ue["eval_json"]) if isinstance(ue["eval_json"], str) else ue["eval_json"]
                        if isinstance(ej, dict):
                            if ej.get("lastStudyDate") and not ev.get("lastStudyDate"):
                                ev["lastStudyDate"] = ej["lastStudyDate"]
                            if ej.get("interactionHistory") and not ev.get("interactionHistory"):
                                ev["interactionHistory"] = ej["interactionHistory"]
                    except Exception:
                        pass
                result["evaluation"] = ev
        except Exception as e:
            print(f"[ProgressLoad] user_evaluations 读取失败（非阻塞）: {e}")

        if path_data:
            result["currentPath"] = coerce_learning_path(path_data.get("path_json"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")

@app.get("/api/progress/summary/{user_id}")
def get_progress_summary(user_id: int, range: str = "month"):
    """前端 progress.js 调用的学习进度汇总接口。"""
    try:
        profile_data = database.get_user_profile(user_id)
        path_data = database.get_learning_path(user_id)
        lr = database.get_learning_record(user_id)

        total_hours = 0.0
        if lr and lr.get("code_practice_time"):
            total_hours += lr["code_practice_time"] / 60.0

        streak_days = 0
        completed_courses = 0
        if profile_data and profile_data.get("evaluation_json"):
            try:
                ev = json.loads(profile_data["evaluation_json"]) if isinstance(profile_data["evaluation_json"], str) else profile_data["evaluation_json"]
                if isinstance(ev, dict):
                    streak_days = ev.get("streakDays", ev.get("streak_days", 0))
                    completed_courses = ev.get("completedCourses", 0)
            except Exception:
                pass

        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekly_activity = [{"day": days[i], "hours": round(total_hours / 7, 1), "minutes": int(total_hours * 60 / 7)} for i in range(7)]

        course_progress = []
        if path_data and path_data.get("path_json"):
            try:
                path = json.loads(path_data["path_json"]) if isinstance(path_data["path_json"], str) else path_data["path_json"]
                if isinstance(path, dict) and "courses" in path:
                    for idx, c in enumerate(path["courses"]):
                        course_progress.append({
                            "name": c.get("name", "未命名课程"),
                            "progress": c.get("progress", 0),
                            "icon": c.get("icon", ["📚", "💻", "🔢", "🗄️", "🌐"][idx % 5]),
                        })
            except Exception:
                pass

        timeline = []
        if lr:
            timeline.append({
                "title": "代码练习",
                "time": "最近",
                "desc": f"累计练习 {lr.get('code_practice_time', 0)} 分钟",
                "status": "completed",
            })

        summary = {
            "total_hours": round(total_hours, 1),
            "completed_courses": completed_courses,
            "current_streak": streak_days,
            "avg_daily_hours": round(total_hours / 30, 1) if total_hours > 0 else 0.0,
            "weekly_activity": weekly_activity,
            "course_progress": course_progress,
            "timeline": timeline,
        }
        return {"success": True, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载进度汇总失败: {str(e)}")

def _build_chat_messages(system_prompt: str, history: list, current_user_text: str, max_history: int = 10) -> list:
    """构建带历史上下文的 messages 数组。"""
    messages = [{"role": "system", "content": system_prompt}]
    # 加入历史消息（只取最近 N 条，避免超出上下文窗口）
    for msg in history[-max_history:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant", "system") and content:
            messages.append({"role": role, "content": content})
    # 当前用户输入
    messages.append({"role": "user", "content": current_user_text})
    return messages


@app.post("/api/chat")
def multi_agent_workflow(request: ChatRequest):
    workflow_logs = []
    session_id = request.sessionId or f"sess_{request.userId}_{int(time.time())}"
    student_id = request.userId or 0
    
    try:
        # ===== 记忆系统：保存用户消息 + 加载历史 =====
        try:
            from db import save_message, get_conversation_messages
            save_message(session_id, student_id, "user", request.userText, message_type="text")
            chat_history = get_conversation_messages(session_id, student_id, limit=20)
            workflow_logs.append(f"[Memory] 已加载 {len(chat_history)} 条历史消息 | 会话: {session_id[:20]}...")
        except Exception as mem_e:
            chat_history = []
            workflow_logs.append(f"[Memory] 历史消息加载失败（非阻塞）: {mem_e}")
        
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
        # 使用新的学情驱动路径生成服务（异步触发，不阻塞聊天响应）
        _safe_trigger_learning_path_refresh(request.userId or 0, "chat_interaction")
        # 保留原有的简单路径生成作为即时回退
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

        # ===== 长期记忆检索 =====
        long_term_memory_text = ""
        try:
            from app.services.memory_retriever import retrieve_relevant_memories_sync, format_memories_for_prompt
            relevant_memories = retrieve_relevant_memories_sync(
                str(student_id), request.userText, limit=6, min_confidence=0.5
            )
            if relevant_memories:
                long_term_memory_text = format_memories_for_prompt(relevant_memories)
                workflow_logs.append(f"[Memory] 检索到 {len(relevant_memories)} 条长期记忆")
            else:
                workflow_logs.append("[Memory] 暂无相关长期记忆")
        except Exception as mem_e:
            workflow_logs.append(f"[Memory] 长期记忆检索失败（非阻塞）: {mem_e}")

        # 轻量级即时特征检测（让用户在本轮就感知到"被记住"）
        detected_traits_text = ""
        try:
            from agents import ProfilerAgent
            _profiler = ProfilerAgent()
            traits = _profiler._detect_user_traits(request.userText)
            if traits:
                trait_lines = []
                for trait in traits:
                    label = {"background": "背景", "preference": "偏好", "knowledge": "知识", "interest": "兴趣", "goal": "目标", "emotion": "情感"}.get(trait.get("type", ""), "特征")
                    trait_lines.append(f"  [{label}] {trait.get('content', '')}")
                detected_traits_text = "\n【本轮对话中检测到的用户新特征（请在本轮回答中引用）】:\n" + "\n".join(trait_lines) + "\n"
                workflow_logs.append(f"[Profiler] 即时特征检测: 发现 {len(traits)} 条新特征")
        except Exception:
            pass

        # ===== Agent 5-8: 多模态生成智能体群组 (Generator Agents) =====
        if dispatch_strategy == "socratic":
            # ===== Agent: 苏格拉底诊断智能体 (Socratic Evaluator) =====
            workflow_logs.append("[Socratic Evaluator] 正在启动启发式诊断，引导学生自主思考...")
            socratic_sys = f"""你是一位苏格拉底式教学导师。学生目前处于困惑状态，你的任务不是直接给出答案，而是通过启发式反问引导学生自主思考。

【学生画像】: {json.dumps(new_profile, ensure_ascii=False)}
【教材参考】:
{context}
{long_term_memory_text}
{detected_traits_text}

【规则】：
1. 绝不直接给出完整答案
2. 通过2-3个层层递进的引导性问题，帮助学生自己发现答案
3. 每个问题后给出提示方向（而非答案本身）
4. 最后给出一个"思考锚点"——即如果学生能回答最后一个问题，就说明已经理解了核心
5. 用 [Doc_Ref: xxx] 标注引用来源
6. 语气温和鼓励，像一位耐心的导师

【记忆提示】：如果以下历史对话中有与当前问题相关的上下文，请自然地引用或关联。"""
            messages = _build_chat_messages(socratic_sys, chat_history, request.userText, max_history=10)
            final_answer = call_llm_with_messages(messages, temperature=0.5)
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
{visual_instruction}
{long_term_memory_text}
{detected_traits_text}

【记忆提示】：以下是你和这位学生的历史对话记录。请在回答中自然地关联之前讨论过的内容，让学生感受到你记得TA说过什么。如果历史记录与当前问题无关，则忽略。"""

            messages = _build_chat_messages(tutor_sys, chat_history, request.userText, max_history=10)
            final_answer = call_llm_with_messages(messages, temperature=0.6)
            workflow_logs.append("[Generator Agents] 多模态内容生成完毕。")

        # ===== 记忆系统：保存 AI 回复 =====
        try:
            from db import save_message
            save_message(session_id, student_id, "assistant", final_answer, message_type="text")
            workflow_logs.append("[Memory] AI 回复已保存到对话历史")
        except Exception as mem_e:
            workflow_logs.append(f"[Memory] 保存AI回复失败（非阻塞）: {mem_e}")

        # ===== 长期记忆：异步提取新记忆 =====
        workflow_logs.append("[Memory] 启动异步记忆分析...")

        def _extract_long_term_memory():
            try:
                import asyncio
                from app.services.memory_extractor import extract_memories_from_conversation, deduplicate_memories, save_extracted_memories
                from db import get_user_memories

                async def _do_extract():
                    all_memories = get_user_memories(student_id)
                    recent_history = chat_history[-6:] + [{"role": "user", "content": request.userText}, {"role": "assistant", "content": final_answer}]
                    new_memories = await extract_memories_from_conversation(
                        str(student_id), recent_history, existing_memories=all_memories
                    )
                    if new_memories:
                        type_names = {"background": "背景", "preference": "偏好", "knowledge": "知识", "interest": "兴趣", "goal": "目标", "emotion": "情感", "fact": "事实"}
                        for mem in new_memories:
                            label = type_names.get(mem.get("memory_type", "fact"), "特征")
                            print(f"[MemoryExtractor] 发现新特征：[{label}] {mem.get('content', '')}")
                        deduped = deduplicate_memories(new_memories, all_memories)
                        if deduped:
                            saved = await save_extracted_memories(str(student_id), deduped)
                            print(f"[MemoryExtractor] 已记住 {len(saved)} 条新特征")
                        else:
                            print("[MemoryExtractor] 新特征与已有记忆重复，无需重复记录")
                    else:
                        print("[MemoryExtractor] 本次对话未发现新的用户特征")

                # Reset global httpx client to avoid "Event loop is closed" in background thread
                import llm_stream
                llm_stream._http_client = None
                
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_do_extract())
                finally:
                    loop.close()
            except Exception as e:
                print(f"[MemoryExtractor] 异步记忆提取失败: {e}")

        import threading
        threading.Thread(target=_extract_long_term_memory, daemon=True).start()

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
            },
            "sessionId": session_id,
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

    # ===== 记忆系统：初始化会话 + 保存用户消息 + 加载历史 =====
    session_id = body.session_id or f"sess_{body.student_id}_{int(time.time())}"
    student_id = body.student_id or ""
    chat_history = []
    try:
        from db import save_message, get_conversation_messages
        save_message(session_id, student_id, "user", body.user_input, message_type="text")
        chat_history = get_conversation_messages(session_id, student_id, limit=20)
        logger.info(f"[Memory] 已加载 {len(chat_history)} 条历史消息 | 会话: {session_id}")
    except Exception as mem_e:
        logger.warning(f"[Memory] 历史消息加载失败（非阻塞）: {mem_e}")

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

            # 强制苏格拉底模式：前端用户点击"不太懂"时触发
            if body.force_socratic:
                state.metadata["dialogue_type"] = "confusion"
                state.metadata["force_socratic"] = True
                await push_agent_log("profiler", "用户主动请求苏格拉底深度诊断，跳过常规分析")

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

            # ===== 长期记忆检索 =====
            long_term_memory_text = ""
            try:
                from app.services.memory_retriever import retrieve_relevant_memories, format_memories_for_prompt
                relevant_memories = await retrieve_relevant_memories(
                    str(student_id), body.user_input, limit=6, min_confidence=0.5
                )
                if relevant_memories:
                    long_term_memory_text = format_memories_for_prompt(relevant_memories)
                    await push_agent_log("memory", f"检索到 {len(relevant_memories)} 条长期记忆")
                else:
                    await push_agent_log("memory", "暂无相关长期记忆")
            except Exception as mem_e:
                await push_agent_log("memory", f"长期记忆检索失败（非阻塞）: {mem_e}")

            recommended_links = []

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
                    # 从苏格拉底响应中提取链接
                    recommended_links = _extract_links_from_text(socratic_response)
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

                # 根据 agent/persona 动态构建角色设定
                # 优先使用 persona（无论当前学科是什么），因为用户通过 persona chip 主动选择了性格身份
                if body.persona:
                    try:
                        mgr = get_persona_manager()
                        persona_obj = mgr.get(body.persona)
                        identity_prompt = (
                            f"{persona_obj.identity}\n\n"
                            f"教学策略：\n{persona_obj.teaching_strategy}\n\n"
                            f"语气要求：\n{persona_obj.tone}\n\n"
                            f"行为准则：\n" + "\n".join(f"- {r}" for r in persona_obj.behavior_rules)
                        )
                        await push_agent_log("persona_loader", f"已加载身份: {persona_obj.name} ({body.persona})")
                    except Exception as e:
                        logger.warning(f"[Persona] 加载失败: {e}, fallback 到 agent_system_prompt")
                        identity_prompt = body.agent_system_prompt or "你是一位专业的大数据与AI高校导师。"
                elif body.agent_system_prompt:
                    identity_prompt = body.agent_system_prompt
                else:
                    identity_prompt = "你是一位专业的大数据与AI高校导师。"

                blind_spots = state.metadata.get("blind_spots", [])
                blind_spots_text = "、".join(blind_spots) if blind_spots else "暂无明确盲区"
                socratic_embed_rule = """【苏格拉底穿插规则】
在回答过程中，当你解释完一个关键概念后，请自然地插入一个简短的启发式问题，引导学生主动思考。
格式要求：用 [SocraticQ] 和 [/SocraticQ] 包裹问题，例如：
"HDFS 的 NameNode 负责管理元数据。[SocraticQ]那你能猜一下，如果 NameNode 宕机，DataNode 上的数据还能被访问吗？[/SocraticQ]"
约束：
1. 每个回答最多插入 2 个苏格拉底问题
2. 问题必须简短（不超过 25 字），与上下文自然衔接
3. 只在涉及抽象概念或容易混淆的地方插入
4. 禁止在代码块、Mermaid 图表、JSON 内部插入"""
                if blind_spots:
                    socratic_embed_rule += f"\n\n【用户可能的知识盲区】：{blind_spots_text}\n请针对以上盲区优先设计苏格拉底问题。"

                # ProfilerAgent 同步检测到的即时特征（本轮即可引用）
                detected_traits = state.metadata.get("detected_traits", [])
                detected_traits_text = ""
                if detected_traits:
                    trait_lines = []
                    for trait in detected_traits:
                        label = {"background": "背景", "preference": "偏好", "knowledge": "知识", "interest": "兴趣", "goal": "目标", "emotion": "情感"}.get(trait.get("type", ""), "特征")
                        trait_lines.append(f"  [{label}] {trait.get('content', '')}")
                    detected_traits_text = "\n【本轮对话中检测到的用户新特征（请在本轮回答中引用）】:\n" + "\n".join(trait_lines) + "\n"

                sys_prompt = f"""{identity_prompt}

【必须遵守规则】：
1. 基于[教材参考]回答并标注引用。
[教材参考开始]
{context}
[教材参考结束]
2. 根据画像 {json.dumps(state.profile.model_dump(mode='json'), ensure_ascii=False)} 调整难度和表达方式。
3. 如果学生基础薄弱，避免底层源码解析，用生动比喻和可视化替代。
{instruction}
{socratic_embed_rule}
{long_term_memory_text}
{detected_traits_text}

【记忆提示】：以下是你和这位学生的历史对话记录。请在回答中自然地关联之前讨论过的内容，让学生感受到你记得TA说过什么。如果历史记录与当前问题无关，则忽略。

【苏格拉底穿插规则】
在回答过程中，当你解释完一个关键概念后，请自然地插入一个简短的启发式问题，引导学生主动思考。
格式要求：用 [SocraticQ] 和 [/SocraticQ] 包裹问题，例如：
"HDFS 的 NameNode 负责管理元数据。[SocraticQ]那你能猜一下，如果 NameNode 宕机，DataNode 上的数据还能被访问吗？[/SocraticQ]"

约束：
1. 每个回答最多插入 2 个苏格拉底问题
2. 问题必须简短（不超过 25 字），与上下文自然衔接
3. 只在涉及抽象概念或容易混淆的地方插入
4. 禁止在代码块、Mermaid 图表、JSON 内部插入

【用户可能的知识盲区】：{blind_spots_text}
请针对以上盲区优先设计苏格拉底问题。

【学习链接推荐规则】（可选）
在回复内容之后，你可以选择性附加 `<links>[...]</links>` 标记，为学生推荐与当前话题直接相关的学习资源：
- 仅当问题涉及具体知识点、概念或技能时才推荐
- 每个链接必须与学生当前学习的内容直接相关
- 站内链接：`{{"type": "internal", "title": "...", "url": "/classroom.html?course_id=xxx", "description": "...", "icon": "emoji"}}`
- 站外链接：`{{"type": "external", "title": "...", "url": "https://...", "description": "...", "icon": "🔗"}}`
- 最多推荐 3 个链接，优先站内资源
- 如果问题不涉及具体知识点，不要输出 <links> 标记"""

                agent_label = f"generator_{dispatch_strategy}"
                await push_agent_log(agent_label, "正在调用大模型流式生成...")

                # 构建带历史上下文的 messages 数组
                messages = [{"role": "system", "content": sys_prompt}]
                for msg in chat_history[-10:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ("user", "assistant", "system") and content:
                        messages.append({"role": role, "content": content})
                messages.append({"role": "user", "content": body.user_input})

                async for event in call_llm_stream_with_log_messages(
                    messages, agent_name=agent_label, temperature=0.3
                ):
                    if disconnected.is_set():
                        break
                    if event["type"] == "content_chunk":
                        await push_content_chunk(event["content"])
                    elif event["type"] == "text":
                        await push_content_chunk(event["content"])
                    elif event["type"] == "log":
                        await push_agent_log(agent_label, event.get("message", ""))
                    elif event["type"] == "done":
                        elapsed = event.get("elapsed_ms", "?")
                        char_count = len(event.get("full_text", ""))
                        await push_agent_log(agent_label, f"生成完毕 | 共 {char_count} 字 | 耗时 {elapsed}ms")

                # 从 LLM 完整输出中提取学习链接
                full_response_text = event.get("full_text", "")
                recommended_links = _extract_links_from_text(full_response_text)
                if recommended_links:
                    await push_agent_log("resource_dispatcher", f"检测到 {len(recommended_links)} 个推荐学习链接")

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

            # ===== 记忆系统：保存 AI 回复 =====
            try:
                from db import save_message
                if dispatch_strategy == "socratic":
                    ai_response = state.metadata.get("socratic_response", "")
                else:
                    ai_response = full_response_text
                if ai_response:
                    save_message(session_id, student_id, "assistant", ai_response, message_type="text")
                    await push_agent_log("memory", "AI 回复已保存到对话历史")
            except Exception as mem_e:
                await push_agent_log("memory", f"保存AI回复失败（非阻塞）: {mem_e}")

            # ===== 长期记忆：异步提取新记忆 =====
            try:
                from app.services.memory_extractor import extract_memories_from_conversation, deduplicate_memories, save_extracted_memories
                from db import get_user_memories

                await push_agent_log("memory", "正在分析对话中的用户新特征...")
                all_memories = get_user_memories(student_id)
                recent_history = chat_history[-6:] + [
                    {"role": "user", "content": body.user_input},
                    {"role": "assistant", "content": ai_response},
                ]
                new_memories = await extract_memories_from_conversation(
                    str(student_id), recent_history, existing_memories=all_memories
                )
                if new_memories:
                    type_names = {"background": "背景", "preference": "偏好", "knowledge": "知识", "interest": "兴趣", "goal": "目标", "emotion": "情感", "fact": "事实"}
                    for mem in new_memories:
                        label = type_names.get(mem.get("memory_type", "fact"), "特征")
                        await push_agent_log("memory", f"发现新特征：[{label}] {mem.get('content', '')}")
                    deduped = deduplicate_memories(new_memories, all_memories)
                    if deduped:
                        saved = await save_extracted_memories(str(student_id), deduped)
                        await push_agent_log("memory", f"已记住 {len(saved)} 条新特征，下次会主动引用")
                    else:
                        await push_agent_log("memory", "新特征与已有记忆重复，无需重复记录")
                else:
                    await push_agent_log("memory", "本次对话未发现新的用户特征")
            except Exception as mem_e:
                await push_agent_log("memory", f"记忆分析失败（非阻塞）: {mem_e}")
                logger.warning(f"[MemoryExtractor] 流式聊天记忆提取失败: {mem_e}")

            # ===== 苏格拉底交互确认点判断 =====
            socratic_checkpoint = False
            checkpoint_topic = ""
            if dispatch_strategy != "socratic":
                response_len = len(full_response_text) if 'full_response_text' in locals() else 0
                has_blind_spots = bool(state.metadata.get("blind_spots", []))
                low_pass_rate = state.profile.socratic_pass_rate < 0.5
                if response_len > 300 and (has_blind_spots or low_pass_rate):
                    socratic_checkpoint = True
                    checkpoint_topic = state.metadata.get("blind_spots", ["当前内容"])[0] if has_blind_spots else "当前内容"
                    await push_agent_log("master_controller", f"苏格拉底交互确认点触发 | 主题: {checkpoint_topic}")

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
                "links": recommended_links,
                "sessionId": session_id,
                "socraticCheckpoint": socratic_checkpoint,
                "checkpointTopic": checkpoint_topic,
                "triggerMemoryRefresh": True,
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


@app.get("/api/chat/history")
def get_chat_history(sessionId: str, userId: str = ""):
    """获取指定会话的聊天记录，用于前端页面刷新后恢复显示。"""
    try:
        from db import get_conversation_messages
        history = get_conversation_messages(sessionId, student_id=userId or None, limit=50)
        # 精简字段，只返回前端渲染所需的数据
        messages = []
        for msg in history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
                "created_at": str(msg.get("created_at", "")) if msg.get("created_at") else None,
            })
        return {"success": True, "count": len(messages), "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取聊天记录失败: {e}")


# ========== AI 结对编程 - 题目生成API ==========

class ProblemGenerationRequest(BaseModel):
    """题目生成请求"""
    student_id: str = ""
    course_id: str = "bigdata"
    chapter: str = "ch1"  # 章节ID
    topic: str = ""  # 知识点
    difficulty: str = "medium"  # 难度: easy, medium, hard
    weak_topics: list[str] = Field(default_factory=list)  # 薄弱知识点列表
    learning_history: list[dict[str, Any]] = Field(default_factory=list)  # 学习历史
    current_mastery: int = 0  # 当前掌握度 0-100


def sse_event(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_data(data: Any) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def extract_json_object(text: str) -> dict[str, Any]:
    json_match = re.search(r'\{[\s\S]*\}', text or "")
    if not json_match:
        raise ValueError("未从大模型响应中解析到 JSON")
    return json.loads(json_match.group())


def strip_spoiler_comments(code: str) -> str:
    return re.sub(
        r'\s+#\s*(错误|錯誤|error|bug|这里写错|此处写错|写错了)\d*[:：]?.*',
        '',
        code or '',
        flags=re.IGNORECASE,
    ).strip()


def extract_fenced_section(markdown: str, label: str) -> str:
    pattern = rf'{label}\s*:?\s*```(?:python)?\s*(.*?)\s*```'
    match = re.search(pattern, markdown or "", flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_labeled_line(markdown: str, label: str) -> str:
    match = re.search(rf'^{label}\s*:\s*(.+)$', markdown or "", flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_links_from_text(text: str) -> list[dict]:
    """从 LLM 输出中提取 <links> 标记中的学习链接数组"""
    if not text:
        return []

    match = re.search(r'<links>([\s\S]*?)</links>', text, re.DOTALL)
    if not match:
        return []

    links_text = match.group(1).strip()
    if links_text.startswith("```"):
        links_text = re.sub(r"^```\w*\s*", "", links_text)
        links_text = re.sub(r"\s*```$", "", links_text)

    try:
        links = json.loads(links_text)
        if isinstance(links, list) and len(links) > 0:
            normalized = []
            for link in links:
                if not isinstance(link, dict):
                    continue
                if not link.get("title") or not link.get("url"):
                    continue
                normalized.append({
                    "id": link.get("id") or f"link_{len(normalized)}",
                    "type": link.get("type", "internal"),
                    "title": link["title"],
                    "url": link["url"],
                    "description": link.get("description", ""),
                    "icon": link.get("icon", "📚" if link.get("type") == "internal" else "🔗"),
                    "style": link.get("style", "card"),
                    "metadata": link.get("metadata", {}),
                })
            return normalized
    except json.JSONDecodeError:
        pass
    return []


def extract_starter_code_progress(markdown: str) -> tuple[str, bool]:
    """Return the currently available starter code and whether its fence is closed."""
    text = markdown or ""
    marker = re.search(r'STARTER_CODE\s*:?', text, flags=re.IGNORECASE)
    search_start = marker.end() if marker else 0
    fence = re.search(r'```(?:python)?\s*\n?', text[search_start:], flags=re.IGNORECASE)
    if not fence:
        return "", False

    code_start = search_start + fence.end()
    rest = text[code_start:]
    close_match = re.search(r'\n?```', rest)
    if close_match:
        return rest[:close_match.start()], True

    # Avoid briefly rendering a partial closing fence if it arrives split across chunks.
    partial = rest
    for suffix in ("\n``", "\n`", "``", "`"):
        if partial.endswith(suffix):
            partial = partial[: -len(suffix)]
            break
    return partial, False


def parse_markdown_problem(markdown: str, body: ProblemGenerationRequest) -> dict[str, Any]:
    starter_code = strip_spoiler_comments(extract_fenced_section(markdown, "STARTER_CODE"))
    if not starter_code:
        raise ValueError("未解析到 STARTER_CODE 代码块")

    solution_code = extract_fenced_section(markdown, "SOLUTION_CODE")
    title = extract_labeled_line(markdown, "TITLE") or f"{body.topic or 'Python'} 调试任务"
    description = extract_labeled_line(markdown, "DESCRIPTION") or (
        f"这道题聚焦「{body.topic or 'Python'}」，代码中预计包含 2-3 处隐蔽错误，请阅读代码并运行排查。"
    )
    known_issue = extract_labeled_line(markdown, "KNOWN_ISSUE") or "第一次运行通常会暴露最靠前的运行时错误，请从 traceback 最底部开始定位。"
    error_clue = extract_labeled_line(markdown, "ERROR_CLUE") or "建议关注变量命名、边界条件和数据结构是否与调用处保持一致。"

    return {
        "id": int(time.time() * 1000) % 1000000,
        "chapter": body.chapter,
        "topic": body.topic,
        "language": "python",
        "difficulty": body.difficulty,
        "task_info": {
            "title": title,
            "description": description,
        },
        "starter_code": starter_code,
        "solution_code": solution_code,
        "ui_hints": {
            "known_issue": known_issue,
            "error_clue": error_clue,
        },
    }


def build_problem_generation_prompt(body: ProblemGenerationRequest) -> tuple[str, str]:
    topic_descriptions = {
        "ch1": "变量与数据类型、运算符、控制流程",
        "ch2": "列表List、字典Dict、集合Set、元组Tuple",
        "ch3": "函数定义、参数传递、返回值、作用域",
        "ch4": "类与对象、继承、封装、多态",
        "ch5": "文件读写、异常处理、上下文管理器",
        "ch6": "导入模块、标准库、第三方包",
        "ch7": "排序算法、查找算法、递归、动态规划",
        "ch8": "SQL基础、数据库连接、CRUD操作",
    }
    error_types_for_weak = {
        "变量与数据类型": ["TypeError", "NameError", "SyntaxError"],
        "列表List": ["IndexError", "TypeError"],
        "字典Dict": ["KeyError", "TypeError"],
        "函数": ["TypeError", "UnboundLocalError"],
        "类与对象": ["AttributeError", "TypeError"],
        "异常处理": ["RuntimeError", "AttributeError"],
        "文件读写": ["FileNotFoundError", "PermissionError"],
        "排序算法": ["RecursionError", "IndexError"],
    }
    weak_errors: list[str] = []
    for weak_topic in body.weak_topics:
        weak_errors.extend(error_types_for_weak.get(weak_topic, []))
    weak_errors = list(set(weak_errors))[:3]

    if body.difficulty == "easy":
        difficulty_instruction = "题目应该简单，包含2处相对明显但不在代码注释中剧透的错误，适合初学者"
    elif body.difficulty == "hard":
        difficulty_instruction = "题目应该困难，包含3处隐蔽错误，需要深入理解运行结果和数据流"
    else:
        difficulty_instruction = "题目难度适中，包含2-3处常见但需要运行定位的错误"

    chapter_desc = topic_descriptions.get(body.chapter, "Python基础")
    system_prompt = "你是严谨的大学计算机实验课导师。生成 Debug 题时必须先输出学生可见的 STARTER_CODE Markdown 代码块，禁止输出 JSON，禁止在代码注释中剧透错误。"
    user_prompt = f"""你是「玄武·AI结对编程舱」的题目生成专家。

【任务】
根据以下学情信息，生成一道适合学生的 Python Debug 实操题。

【学生学情】
- 当前学习章节：{body.chapter}
- 章节知识点：{chapter_desc}
- 目标知识点：{body.topic}
- 当前掌握度：{body.current_mastery}%
- 薄弱知识点：{', '.join(body.weak_topics) if body.weak_topics else '无记录'}
- 推荐错误类型：{', '.join(weak_errors) if weak_errors else '根据知识点常见错误'}

【生成要求 - 重要】
{difficulty_instruction}
1. 题目必须是一个完整的 Python 代码片段（40-90行）。
2. starter_code 必须包含2-3处真实开发中常见的语法、运行时或逻辑错误。
3. starter_code 中严禁出现任何揭示错误的注释，尤其禁止 "# 错误1"、"# 这里写错了"、"# bug"、"# fix me" 等剧透字样。
4. 如果代码需要注释，只能写自然的业务说明，不能暗示错误位置、变量名修复方式或正确答案。
5. 至少第一处错误应能通过点击“运行代码”在终端中暴露。
6. solution_code 必须是修复后的完整正确代码，仅供后台判定使用，不要在 starter_code 中泄露。

【输出协议 - 必须按顺序输出，禁止 JSON】
第一段必须立刻输出学生可见的初始代码，不能先解释：
STARTER_CODE:
```python
# 这里放完整初始代码。代码可包含自然业务注释，但严禁写“错误1/这里写错/bug/fix me”等剧透注释。
```

第二段输出页面元信息：
TASK_INFO:
TITLE: 学生成绩排序与统计系统
DESCRIPTION: 这道题聚焦「{body.topic}」，代码中预计包含 2-3 处隐蔽错误，请阅读代码并运行排查。
KNOWN_ISSUE: 第一次运行通常会在第 XX 行附近触发某类报错，请检查上下文变量或数据结构是否一致。
ERROR_CLUE: 建议关注变量作用域、排序 key 或边界条件，不要直接给出答案。

第三段输出后台参考答案，供系统判定使用，不会展示给学生：
SOLUTION_CODE:
```python
# 这里放修复后的完整正确代码
```"""
    return system_prompt, user_prompt


@app.post("/api/v2/coding-problem/generate")
async def generate_coding_problem(body: ProblemGenerationRequest):
    """根据学生学情实时生成编程题目"""
    logger.info(f"Generating problem for student={body.student_id}, chapter={body.chapter}, topic={body.topic}")

    # 构建生成题目的提示词
    topic_descriptions = {
        "ch1": "变量与数据类型、运算符、控制流程",
        "ch2": "列表List、字典Dict、集合Set、元组Tuple",
        "ch3": "函数定义、参数传递、返回值、作用域",
        "ch4": "类与对象、继承、封装、多态",
        "ch5": "文件读写、异常处理、上下文管理器",
        "ch6": "导入模块、标准库、第三方包",
        "ch7": "排序算法、查找算法、递归、动态规划",
        "ch8": "SQL基础、数据库连接、CRUD操作"
    }

    chapter_desc = topic_descriptions.get(body.chapter, "Python基础")

    # 根据薄弱知识点调整题目难度和错误类型
    error_types_for_weak = {
        "变量与数据类型": ["TypeError", "NameError", "SyntaxError"],
        "列表List": ["IndexError", "TypeError"],
        "字典Dict": ["KeyError", "TypeError"],
        "函数": ["TypeError", "UnboundLocalError"],
        "类与对象": ["AttributeError", "TypeError"],
        "异常处理": ["RuntimeError", "AttributeError"],
        "文件读写": ["FileNotFoundError", "PermissionError"],
        "排序算法": ["RecursionError", "IndexError"]
    }

    weak_errors = []
    for wt in body.weak_topics:
        if wt in error_types_for_weak:
            weak_errors.extend(error_types_for_weak[wt])

    # 去重
    weak_errors = list(set(weak_errors))[:3]

    difficulty_instruction = ""
    if body.difficulty == "easy":
        difficulty_instruction = "题目应该简单，包含2处相对明显但不在代码注释中剧透的错误，适合初学者"
    elif body.difficulty == "hard":
        difficulty_instruction = "题目应该困难，包含3处隐蔽错误，需要深入理解运行结果和数据流"
    else:
        difficulty_instruction = "题目难度适中，包含2-3处常见但需要运行定位的错误"

    prompt = f"""你是「玄武·AI结对编程舱」的题目生成专家。

【任务】
根据以下学情信息，生成一道适合学生的Python编程题目。

【学生学情】
- 当前学习章节：{body.chapter}
- 章节知识点：{chapter_desc}
- 目标知识点：{body.topic}
- 当前掌握度：{body.current_mastery}%
- 薄弱知识点：{', '.join(body.weak_topics) if body.weak_topics else '无记录'}
- 推荐错误类型：{', '.join(weak_errors) if weak_errors else '根据知识点常见错误'}

【生成要求 - 重要】
{difficulty_instruction}
1. 题目必须是一个完整的Python代码片段（40-90行）
2. starter_code 必须包含2-3处真实开发中常见的语法、运行时或逻辑错误
3. 【绝对禁令】starter_code 中严禁出现任何揭示错误的注释，尤其禁止 "# 错误1"、"# 这里写错了"、"# bug"、"# fix me" 等剧透字样
4. 如果代码需要注释，只能写自然的业务说明，不能暗示错误位置、变量名修复方式或正确答案
5. 错误应该符合目标知识点的特点，且错误类型要多样化
6. 代码应该有实际的业务场景（如学生成绩排序系统、数据处理、电商订单等）
7. 结尾必须包含一个执行入口（if __name__ == "__main__":）
8. 至少第一处错误应能通过点击“运行代码”在终端中暴露，后续错误可以是运行时错误或需要进一步验证的逻辑错误
9. solution_code 必须是修复后的完整正确代码，仅供后台判定使用，不要在 starter_code 中泄露

【输出格式】
请严格按照以下 JSON 格式输出，不要包含任何其他内容。最终返回必须是可直接 json.loads 解析的合法 JSON，不能出现 Markdown、注释或未加引号的占位符：
{{
    "id": 123456,
    "chapter": "{body.chapter}",
    "topic": "{body.topic}",
    "language": "python",
    "difficulty": "{body.difficulty}",
    "task_info": {{
        "title": "学生成绩排序与统计系统",
        "description": "这道题聚焦「{body.topic}」，代码中预计包含 2-3 处隐蔽错误，请阅读代码并运行排查。"
    }},
    "starter_code": "完整 Python 初始代码字符串。包含隐蔽错误，但严禁在注释中指出错误位置和原因。",
    "solution_code": "修复后的完整正确 Python 代码字符串。仅供后台对比判定使用，不对学生展示。",
    "ui_hints": {{
        "known_issue": "已知现象。例如：第一次运行通常会在第 XX 行附近触发 NameError，请检查上下文的变量声明是否一致。",
        "error_clue": "方向性报错线索。例如：建议关注变量作用域、排序 key 或边界条件，不要直接给出答案。"
    }}
}}

请生成题目："""

    try:
        from llm_stream import call_llm_async

        # 调用 LLM 生成题目
        result = await call_llm_async(
            system_prompt="你是严谨的大学计算机实验课导师。生成 Debug 题时，starter_code 内绝对禁止用注释剧透错误位置或原因；启发式线索只能写入 ui_hints。",
            user_prompt=prompt,
            temperature=0.7
        )

        # 解析 LLM 返回的 JSON
        import json
        import re

        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            problem_data = json.loads(json_match.group())
            if problem_data.get("starter_code"):
                problem_data["starter_code"] = re.sub(
                    r'\s+#\s*(错误|錯誤|error|bug|这里写错|此处写错|写错了)\d*[:：]?.*',
                    '',
                    problem_data["starter_code"],
                    flags=re.IGNORECASE,
                ).strip()
            title = problem_data.get("task_info", {}).get("title") or problem_data.get("title", "unknown")
            logger.info(f"Problem generated successfully: {title}")
            return {"success": True, "problem": problem_data}
        else:
            logger.error(f"Failed to parse problem JSON: {result[:200]}")
            return {"success": False, "error": "题目生成失败，请稍后再试"}

    except Exception as e:
        logger.error(f"Problem generation error: {str(e)}", exc_info=True)
        return {"success": False, "error": f"生成出错: {str(e)}"}


@app.post("/api/v2/coding-problem/generate/stream")
async def generate_coding_problem_stream(raw_request: Request, body: ProblemGenerationRequest):
    """SSE 流式生成 Debug 题：先实时推 starter code，再返回结构化结果。"""
    logger.info(f"Streaming problem generation: student={body.student_id}, chapter={body.chapter}, topic={body.topic}")

    system_prompt, user_prompt = build_problem_generation_prompt(body)

    async def event_generator():
        full_text = ""
        emitted_code_len = 0
        code_started = False
        code_completed = False
        try:
            yield sse_event("status", {"msg": "正在读取学情画像..."})
            await asyncio.sleep(0)
            yield sse_event("status", {"msg": "正在请求大模型流式生成代码..."})

            async for chunk in call_llm_stream(system_prompt, user_prompt, temperature=0.7):
                if await raw_request.is_disconnected():
                    logger.info(f"Problem generation stream disconnected: student={body.student_id}")
                    return
                full_text += chunk

                current_code, is_code_complete = extract_starter_code_progress(full_text)
                if current_code and not code_started:
                    code_started = True
                    yield sse_event("code_start", {"msg": "代码流已建立"})

                if len(current_code) > emitted_code_len:
                    delta = current_code[emitted_code_len:]
                    emitted_code_len = len(current_code)
                    yield sse_event("code_chunk", {"chunk": delta})

                if is_code_complete and not code_completed:
                    code_completed = True
                    yield sse_event("code_complete", {"msg": "初始代码生成完成，正在整理题目信息..."})

            yield sse_event("status", {"msg": "正在解析 Markdown 题目协议..."})
            problem_data = parse_markdown_problem(full_text, body)
            title = problem_data.get("task_info", {}).get("title") or problem_data.get("title", "unknown")
            logger.info(f"Streaming problem generated successfully: {title}")
            yield sse_event("result", {"success": True, "problem": problem_data})
        except Exception as exc:
            logger.error(f"Streaming problem generation error: {str(exc)}", exc_info=True)
            yield sse_event("error", {"message": f"题目生成失败: {str(exc)}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/v2/coding-problem/generate-batch")
async def generate_coding_problems_batch(body: ProblemGenerationRequest):
    """批量生成编程题目（一次生成3道）"""
    logger.info(f"Generating batch problems for student={body.student_id}")

    results = []
    for i in range(3):
        # 每次生成一道题
        req = ProblemGenerationRequest(
            student_id=body.student_id,
            course_id=body.course_id,
            chapter=body.chapter,
            topic=body.topic,
            difficulty=body.difficulty,
            weak_topics=body.weak_topics[:2] if body.weak_topics else [],
            learning_history=body.learning_history,
            current_mastery=body.current_mastery
        )

        result = await generate_coding_problem(req)
        if result.get("success"):
            # 修改ID避免重复
            problem = result["problem"]
            problem["id"] = problem["id"] + i * 100
            results.append(problem)

    return {"success": True, "problems": results}


# ========== AI 代码批阅API ==========

class CodeReviewRequest(BaseModel):
    """代码批阅请求"""
    student_id: str = ""
    original_code: str = ""
    solution_code: str = ""
    user_code: str = ""
    problem_id: Any = None
    topic: str = ""
    difficulty: str = "medium"


def build_code_review_prompt(body: CodeReviewRequest) -> tuple[str, str]:
    system_prompt = "你是一个专业的 Python 代码批阅专家，擅长对比参考答案、定位代码问题，并输出严格 JSON。"
    user_prompt = f"""你是「玄武·AI结对编程舱」的代码批阅专家。

【任务】
对比原始题目代码、后台参考答案和用户修改后的代码，判断用户是否完成修复。

【原始题目代码】
```python
{body.original_code}
```

【后台参考答案】
```python
{body.solution_code or "本题未提供参考答案，请主要依据原始代码与用户代码进行审阅。"}
```

【用户修改后的代码】
```python
{body.user_code}
```

【输出要求】
只输出合法 JSON，不要输出 Markdown：
{{
    "correct_items": [
        {{"line": 1, "description": "用户修复了某个问题"}}
    ],
    "wrong_items": [
        {{"line": 1, "description": "仍存在的问题", "suggestion": "方向性建议，不要直接整段代写"}}
    ],
    "summary": {{
        "correct_count": 0,
        "wrong_count": 0,
        "passed": false
    }}
}}"""
    return system_prompt, user_prompt


@app.post("/api/v2/code/review")
async def review_user_code(body: CodeReviewRequest):
    """AI 批阅用户修改后的代码"""
    logger.info(f"Code review for student={body.student_id}, problem={body.problem_id}")

    prompt = f"""你是「玄武·AI结对编程舱」的代码批阅专家。

【任务】
对比原始题目代码和用户修改后的代码，找出：
1. 用户改正了哪些错误
2. 用户还有哪些错误没有改正

【原始题目代码】
```python
{body.original_code}
```

【后台参考答案（仅用于判定，不对学生展示）】
```python
{body.solution_code or "本题未提供参考答案，请主要依据原始代码与用户代码进行审阅。"}
```

【用户修改后的代码】
```python
{body.user_code}
```

【输出要求】
请仔细对比两份代码，找出：
1. 原本代码中的每个错误，以及用户是否改正了它
2. 用户是否引入了新的错误

请严格按照以下JSON格式输出：
{{
    "correct_items": [
        {{"line": 行号, "description": "用户改正了xxx错误"}}
    ],
    "wrong_items": [
        {{"line": 行号, "description": "错误描述", "suggestion": "修改建议"}}
    ],
    "summary": {{
        "correct_count": 改正数量,
        "wrong_count": 错误数量,
        "passed": 是否全部改正 (true/false)
    }}
}}

请进行批阅："""

    try:
        from llm_stream import call_llm_async

        result = await call_llm_async(
            system_prompt="你是一个专业的Python代码批阅专家，擅长找出代码中的错误并给出修改建议。",
            user_prompt=prompt,
            temperature=0.3
        )
        

        import re
        import json

        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            report_data = json.loads(json_match.group())
            logger.info(f"Review completed: correct={report_data.get('summary', {}).get('correct_count', 0)}, wrong={report_data.get('summary', {}).get('wrong_count', 0)}")
            return {"success": True, "report": report_data}
        else:
            logger.error(f"Failed to parse review JSON: {result[:200]}")
            return {"success": False, "error": "批阅解析失败"}

    except Exception as e:
        logger.error(f"Code review error: {str(e)}", exc_info=True)
        return {"success": False, "error": f"批阅出错: {str(e)}"}


@app.post("/api/v2/code/review/stream")
async def review_user_code_stream(raw_request: Request, body: CodeReviewRequest):
    """SSE 流式批阅：先推分析状态，最后推结构化 JSON 结果。"""
    logger.info(f"Streaming code review: student={body.student_id}, problem={body.problem_id}")
    system_prompt, user_prompt = build_code_review_prompt(body)

    async def event_generator():
        full_text = ""
        try:
            yield sse_event("status", {"msg": "正在分析代码语法..."})
            await asyncio.sleep(0.12)
            yield sse_event("status", {"msg": "正在对比参考答案..."})

            chunk_count = 0
            async for chunk in call_llm_stream(system_prompt, user_prompt, temperature=0.3):
                if await raw_request.is_disconnected():
                    logger.info(f"Code review stream disconnected: student={body.student_id}")
                    return
                full_text += chunk
                chunk_count += 1
                if chunk_count == 8:
                    yield sse_event("status", {"msg": "正在检测逻辑漏洞..."})
                elif chunk_count == 18:
                    yield sse_event("status", {"msg": "正在整理修复建议..."})
                yield sse_event("content", {"chunk": chunk})

            yield sse_event("status", {"msg": "正在生成结构化批阅报告..."})
            report = extract_json_object(full_text)
            yield sse_event("result", {"success": True, "report": report})
        except Exception as exc:
            logger.error(f"Streaming code review error: {str(exc)}", exc_info=True)
            yield sse_event("error", {"message": f"批阅失败: {str(exc)}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ========== 辩论模式API ==========

DEBATE_TIMEOUT_FIRST_ROUND = 120  # 第一轮超时(秒)
DEBATE_TIMEOUT_COMMENT = 60       # 评论轮超时
DEBATE_TIMEOUT_JUDGE = 90         # 裁判超时


async def run_debate_agent_turn(
    agent_id: str,
    agent_name: str,
    system_prompt: str,
    user_input: str,
    context: str,
    round_num: int,
    push_event,
    timeout: int = DEBATE_TIMEOUT_FIRST_ROUND,
    agent_color: str = "#6366f1"
) -> str:
    """运行单个AI身份的辩论回合"""

    await push_event({
        "type": "agent_start",
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agent_color": agent_color,
        "round": round_num
    })

    # 构建身份隔离的系统提示词
    isolated_prompt = f"""你是「{agent_name}」，一个具有独特视角的AI导师。

【身份边界】
- 你必须始终以「{agent_name}」的身份回答问题
- 你的专业领域和思考方式由你的角色决定
- 绝对不要模仿或引用其他AI身份的观点
- 用你自己独特的风格和专业视角来分析问题

【核心专长】
{system_prompt}

【回答要求】
1. 从你的专业角度出发，给出独特见解
2. 回答要有深度，但要简洁（控制在300字以内）
3. 如果其他身份可能持有不同观点，简要说明你的立场差异
4. 使用你独特的语言风格和表达方式

{"【其他身份的观点参考】" + context if context else "这是第一轮回答，请给出你的独立见解。"}
"""

    full_response = ""
    try:
        async for chunk in call_llm_stream(isolated_prompt, user_input, temperature=0.5):
            full_response += chunk
            await push_event({
                "type": "agent_chunk",
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_color": agent_color,
                "content": chunk
            })

        await push_event({
            "type": "agent_complete",
            "agent_id": agent_id,
            "agent_name": agent_name,
            "full_response": full_response
        })

        return full_response

    except asyncio.TimeoutError:
        await push_event({
            "type": "agent_error",
            "agent_id": agent_id,
            "message": "响应超时"
        })
        return ""
    except Exception as e:
        await push_event({
            "type": "agent_error",
            "agent_id": agent_id,
            "message": str(e)
        })
        raise


async def run_debate_cross_comment(
    agent_id: str,
    agent_name: str,
    user_input: str,
    other_responses: dict[str, str],
    push_event,
    timeout: int = DEBATE_TIMEOUT_COMMENT
) -> str:
    """运行交叉评论"""

    await push_event({
        "type": "comment_start",
        "agent_id": agent_id,
        "agent_name": agent_name
    })

    # 构建其他身份观点摘要
    other_views = "\n\n".join([
        f"【{aid}的观点】\n{resp[:500]}{'...' if len(resp) > 500 else ''}"
        for aid, resp in other_responses.items()
    ])

    comment_prompt = f"""你是「{agent_name}」，现在进入辩论的第二轮。

【原始问题】
{user_input}

【其他AI身份的观点】
{other_views}

【你的任务】
1. 简要评论其他身份的观点（选择1-2个最有价值的观点进行讨论）
2. 指出你认同或不认同的地方
3. 补充你认为被遗漏的重要视角
4. 保持你的身份特色，不要改变立场

请用100-200字进行评论。"""

    full_comment = ""
    try:
        async for chunk in call_llm_stream(comment_prompt, "", temperature=0.4):
            full_comment += chunk
            await push_event({
                "type": "comment_chunk",
                "agent_id": agent_id,
                "content": chunk
            })

        await push_event({
            "type": "comment_complete",
            "agent_id": agent_id,
            "comment": full_comment
        })

        return full_comment

    except Exception as e:
        logger.error(f"Cross comment error for {agent_id}: {e}")
        return ""


async def run_judge_synthesis(
    user_input: str,
    agent_responses: dict[str, str],
    cross_comments: dict[str, str],
    push_event,
    timeout: int = DEBATE_TIMEOUT_JUDGE
) -> str:
    """裁判综合判定"""

    await push_event({"type": "judge_start"})

    # 汇总所有观点
    all_views = "\n\n".join([
        f"【{aid}】\n回答：{resp}\n评论：{cross_comments.get(aid, '无')}"
        for aid, resp in agent_responses.items()
    ])

    judge_prompt = f"""你是一位公正的学术裁判，负责综合多位AI导师的观点。

【原始问题】
{user_input}

【多身份辩论记录】
{all_views}

【裁判任务】
1. 分析各身份观点的核心价值
2. 找出共识点和分歧点
3. 综合各方观点，形成最终答案
4. 指出学生应该关注的关键要点

【输出格式】
## 综合判定

### 核心共识
（列出各身份一致认同的要点）

### 观点分歧
（列出有价值的分歧视角）

### 最终答案
（综合各身份观点，给出完整解答）

### 学习建议
（对学生后续学习的建议）"""

    full_answer = ""
    try:
        async for chunk in call_llm_stream(judge_prompt, "", temperature=0.3):
            full_answer += chunk
            await push_event({
                "type": "judge_chunk",
                "content": chunk
            })

        await push_event({
            "type": "judge_complete",
            "final_answer": full_answer
        })

        return full_answer

    except Exception as e:
        logger.error(f"Judge synthesis error: {e}")
        return "裁判综合判定失败，请参考各身份的独立回答。"


@app.post("/api/v2/debate/stream")
async def debate_stream(raw_request: Request, body: DebateRequest):
    """多身份辩论模式流式API"""
    logger.info(f"Debate stream started: student={body.student_id}, input={body.user_input[:50]}")

    event_queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=2048)
    disconnected = asyncio.Event()

    async def push_event(event: dict):
        if not disconnected.is_set():
            await event_queue.put(event)

    async def run_debate():
        try:
            await push_event({"type": "debate_start", "message": "辩论开始"})

            # 第一阶段：各身份独立回答 (并发)
            tasks = []
            for agent in body.agents:
                task = asyncio.create_task(
                    asyncio.wait_for(
                        run_debate_agent_turn(
                            agent_id=agent.id,
                            agent_name=agent.name,
                            system_prompt=agent.systemPrompt,
                            user_input=body.user_input,
                            context="",
                            round_num=1,
                            push_event=push_event,
                            agent_color=agent.themeColor
                        ),
                        timeout=DEBATE_TIMEOUT_FIRST_ROUND
                    )
                )
                tasks.append((agent.id, task))

            agent_responses = {}
            for agent_id, task in tasks:
                try:
                    result = await task
                    agent_responses[agent_id] = result
                except Exception as e:
                    logger.error(f"Agent {agent_id} failed: {e}")
                    await push_event({
                        "type": "agent_error",
                        "agent_id": agent_id,
                        "message": str(e)
                    })

            await push_event({
                "type": "debate_round_complete",
                "round": 1,
                "message": "第一轮完成"
            })

            # 第二阶段：交叉评论 (可选)
            cross_comments = {}
            if len(agent_responses) > 1:
                comment_tasks = []
                for agent in body.agents:
                    if agent.id not in agent_responses:
                        continue
                    other_responses = {
                        aid: resp for aid, resp in agent_responses.items()
                        if aid != agent.id
                    }
                    if not other_responses:
                        continue

                    task = asyncio.create_task(
                        asyncio.wait_for(
                            run_debate_cross_comment(
                                agent_id=agent.id,
                                agent_name=agent.name,
                                user_input=body.user_input,
                                other_responses=other_responses,
                                push_event=push_event
                            ),
                            timeout=DEBATE_TIMEOUT_COMMENT
                        )
                    )
                    comment_tasks.append((agent.id, task))

                for agent_id, task in comment_tasks:
                    try:
                        result = await task
                        cross_comments[agent_id] = result
                    except Exception as e:
                        logger.error(f"Comment {agent_id} failed: {e}")

            # 第三阶段：裁判综合判定
            final_answer = await asyncio.wait_for(
                run_judge_synthesis(
                    user_input=body.user_input,
                    agent_responses=agent_responses,
                    cross_comments=cross_comments,
                    push_event=push_event
                ),
                timeout=DEBATE_TIMEOUT_JUDGE
            )

            # 完成
            await push_event({
                "type": "debate_complete",
                "final_answer": final_answer,
                "agent_responses": agent_responses
            })

        except Exception as e:
            logger.error(f"Debate workflow error: {e}", exc_info=True)
            await push_event({"type": "error", "message": str(e)})
        finally:
            await event_queue.put(None)

    task = asyncio.create_task(run_debate())

    async def event_generator():
        try:
            while not disconnected.is_set():
                if await raw_request.is_disconnected():
                    disconnected.set()
                    break

                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    break

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info(f"Debate stream closed: student={body.student_id}")

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


@app.api_route("/api/v2/event/struggle", methods=["POST", "OPTIONS"])
async def report_struggle(request: Request):
    """Accept flexible struggle event payloads and return clearer validation errors.
    Accepts both snake_case and camelCase keys and handles preflight OPTIONS to avoid 405 for browser requests.
    """
    if request.method == "OPTIONS":
        # Return explicit CORS preflight headers to satisfy strict clients when middleware isn't applied
        return Response(status_code=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600",
        })

    try:
        payload = await request.json()
    except Exception as e:
        req_logger.warning(f"Struggle event: invalid JSON body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # normalize common camelCase -> snake_case keys
    if isinstance(payload, dict):
        if 'userId' in payload and 'user_id' not in payload:
            payload['user_id'] = payload.pop('userId')
        if 'sessionId' in payload and 'session_id' not in payload:
            payload['session_id'] = payload.pop('sessionId')
        if 'currentContentId' in payload and 'current_content_id' not in payload:
            payload['current_content_id'] = payload.pop('currentContentId')
        if 'struggleMetrics' in payload and 'struggle_metrics' not in payload:
            payload['struggle_metrics'] = payload.pop('struggleMetrics')

    # Validate using Pydantic and give actionable errors
    try:
        # pydantic v2 validation
        try:
            event = StruggleEvent.model_validate(payload)
        except AttributeError:
            # fallback for pydantic v1
            event = StruggleEvent(**payload)
    except Exception as ve:
        # Log the validation error for debugging
        req_logger.warning(f"Struggle event validation failed: {ve}")
        # Provide readable detail to client
        raise HTTPException(status_code=422, detail=f"Invalid struggle event payload: {ve}")

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


class FlashcardProgressRequest(BaseModel):
    user_id: int
    card_hash: str
    course_id: str = "bigdata"
    chapter_name: str = ""
    front: str = ""
    back: str = ""
    hint: str = ""
    is_mastered: int = 0
    is_favorite: int = 0
    difficulty: str = "medium"
    user_note: str = ""
    review_count: int = 0


class FlashcardSessionRequest(BaseModel):
    user_id: int
    course_id: str = "bigdata"
    chapter_name: str = ""
    cards_total: int = 0
    cards_answered: int = 0
    cards_mastered: int = 0
    cards_favorited: int = 0
    duration_seconds: int = 0
    session_json: str = ""


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


@app.post("/api/v2/flashcard/progress")
async def save_flashcard_progress_api(req: FlashcardProgressRequest):
    try:
        database.save_flashcard_progress(req.user_id, req.dict())
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v2/flashcard/progress")
async def get_flashcard_progress_api(user_id: int, course_id: str = "bigdata"):
    try:
        progress = database.get_flashcard_progress(user_id, course_id)
        return {"success": True, "data": progress}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/v2/flashcard/session")
async def save_flashcard_session_api(req: FlashcardSessionRequest):
    try:
        database.save_flashcard_session(req.user_id, req.dict())
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v2/flashcard/stats")
async def get_flashcard_stats_api(user_id: int):
    try:
        stats = database.get_flashcard_stats(user_id)
        return {"success": True, "data": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


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


@app.get("/api/news/today")
async def get_today_news():
    """
    获取今日要闻，覆盖多个领域：AI科技、民生、生活、国际形势等
    通过抓取国内新闻源获取实时新闻
    """
    import httpx
    from bs4 import BeautifulSoup
    import re

    today = datetime.now().strftime("%Y年%m月%d日")

    # 默认降级新闻数据
    fallback_news = [
        {"title": "AI大模型技术持续突破，应用场景不断拓展", "category": "AI科技", "description": "大模型应用深入发展，技术赋能千行百业", "source": "AI前哨", "timestamp": "今日"},
        {"title": "神舟飞船成功着陆，航天员平安归来", "category": "国际形势", "description": "中国航天事业取得重大突破，太空探索再创佳绩", "source": "人民日报", "timestamp": "今日"},
        {"title": "就业政策再加力，青年群体获重点帮扶", "category": "民生", "description": "多项就业扶持政策出台，助力青年高质量就业", "source": "新华社", "timestamp": "今日"},
        {"title": "春季旅游市场火热，文化消费持续升温", "category": "生活", "description": "文旅融合深入发展，居民文化消费需求旺盛", "source": "经济日报", "timestamp": "今日"},
        {"title": "人工智能掀起新一轮科技革命浪潮", "category": "AI科技", "description": "生成式AI快速发展，各行业加速智能化转型", "source": "科技日报", "timestamp": "今日"},
        {"title": "全球数字经济蓬勃发展，合作共赢成主流", "category": "国际形势", "description": "数字经济成为全球经济增长新引擎", "source": "光明日报", "timestamp": "今日"},
        {"title": "教育公平持续推进，优质资源下沉基层", "category": "民生", "description": "教育资源均衡配置，更多孩子享受优质教育", "source": "中国教育报", "timestamp": "今日"},
        {"title": "健康生活方式受追捧，健身运动成新时尚", "category": "生活", "description": "全民健身热情高涨，健康意识不断增强", "source": "健康时报", "timestamp": "今日"}
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    collected_news = []

    # 国内新闻源列表（只需1个可靠的源）
    NEWS_SOURCES = [
        ("https://36kr.com/feed", "36氪", "AI科技"),
    ]

    async with httpx.AsyncClient(timeout=1.5, follow_redirects=True) as client:
        for url, source_name, default_category in NEWS_SOURCES:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    continue

                content = resp.text
                soup = BeautifulSoup(content, 'html.parser')

                items = soup.find_all('item')
                if not items:
                    items = soup.find_all('entry')

                for item in items[:15]:
                    title = item.find('title')
                    title = title.get_text(strip=True) if title else ''
                    desc = item.find('description') or item.find('summary') or item.find('content')
                    desc = desc.get_text(strip=True)[:80] if desc else ''

                    if title and len(title) > 5:
                        category = default_category
                        title_lower = title.lower()
                        if any(k in title_lower for k in ['ai', '人工智能', '模型', '科技', '技术', '大模型', 'chatgpt', 'gpt', '软件', '互联网']):
                            category = "AI科技"
                        elif any(k in title_lower for k in ['经济', '股市', '就业', '民生', '政策', '社会', '企业', '商业']):
                            category = "民生"
                        elif any(k in title_lower for k in ['文化', '体育', '娱乐', '生活', '健康', '旅游']):
                            category = "生活"
                        elif any(k in title_lower for k in ['国际', '美国', '欧洲', '外交', '全球', '世界', '国家']):
                            category = "国际形势"

                        collected_news.append({
                            "title": title[:40],
                            "category": category,
                            "description": desc[:80] if desc else '点击查看详情',
                            "source": source_name,
                            "timestamp": "今日"
                        })
            except Exception as e:
                logger.warning(f"[get_today_news] Fetch error for {source_name}: {e}")
                continue

    # 按类别分组返回
    if len(collected_news) >= 4:
        category_groups = {"AI科技": [], "民生": [], "生活": [], "国际形势": []}
        for n in collected_news[:20]:
            cat = n['category']
            if cat in category_groups:
                category_groups[cat].append(n)

        selected = []
        for cat in ["AI科技", "民生", "生活", "国际形势"]:
            selected.extend(category_groups.get(cat, [])[:3])

        remaining = [n for n in collected_news[:20] if n not in selected]
        while len(selected) < 8 and remaining:
            selected.append(remaining.pop(0))

        if len(selected) >= 4:
            return {"success": True, "date": today, "news": selected[:8]}

    return {"success": True, "date": today, "news": fallback_news}


# ============================================
# 今日航线 API - AI 智能学习计划生成
# ============================================

DAILY_ROUTE_CACHE_KEY = 'starlearn_daily_route'
DAILY_ROUTE_CACHE_DURATION = 12 * 60 * 60 * 1000  # 12小时

class DailyRouteRequest(BaseModel):
    userId: Optional[int] = None

def call_llm_for_daily_route(system_prompt: str, user_prompt: str, temperature=0.3):
    """复用统一的 call_llm() 封装，避免重复实现 MiniMax 调用逻辑。"""
    try:
        return call_llm(system_prompt, user_prompt, temperature)
    except Exception as e:
        print(f"[call_llm_for_daily_route] Exception: {e}")
        return None


@app.post("/api/daily-route/generate")
def generate_daily_route(request: DailyRouteRequest):
    """
    根据学生画像生成专属的今日学习计划
    """
    try:
        user_id = request.userId
        today = datetime.now().strftime("%Y年%m月%d日")
        today_key = datetime.now().strftime("%Y-%m-%d")

        default_tasks = [
            {"id": 1, "title": "英语单词记忆", "description": "背诵20个核心词汇", "type": "study", "duration": 20, "subject": "英语", "difficulty": "easy", "taskUrl": "/html/courses.html"},
            {"id": 2, "title": "高数专项练习", "description": "完成5道极限练习题", "type": "practice", "duration": 30, "subject": "数学", "difficulty": "medium", "taskUrl": "/html/courses.html"},
            {"id": 3, "title": "错题回顾", "description": "复习本周典型错题", "type": "review", "duration": 25, "subject": "通用", "difficulty": "medium", "taskUrl": "/html/courses.html"},
            {"id": 4, "title": "算法挑战", "description": "完成2道简单算法题", "type": "practice", "duration": 30, "subject": "编程", "difficulty": "medium", "taskUrl": "/html/courses.html"},
            {"id": 5, "title": "喂养星宝", "description": "放松一下，照顾虚拟宠物", "type": "relax", "duration": 10, "subject": "休闲", "difficulty": "easy", "taskUrl": "/html/pet.html"},
        ]

        if not user_id:
            return {"success": False, "error": "用户未登录"}

        print(f"[generate_daily_route] Starting for user_id: {user_id}")

        profile_data = {}
        try:
            user_profile = database.get_user_profile(user_id)
            if user_profile:
                if isinstance(user_profile, dict):
                    profile_json = user_profile.get('profile_json', {})
                    if isinstance(profile_json, str):
                        profile_data = json.loads(profile_json)
                    else:
                        profile_data = profile_json
                elif isinstance(user_profile, str):
                    profile_data = json.loads(user_profile)
            print(f"[generate_daily_route] Profile: {profile_data}")
        except Exception as e:
            print(f"[generate_daily_route] Failed to get profile: {e}")

        learning_records = []
        try:
            learning_record = database.get_learning_record(user_id)
            if learning_record:
                learning_records = [learning_record]
            storage = database.load_local_storage()
            all_records = storage.get('learning_records', [])
            user_records = [r for r in all_records if r.get('user_id') == user_id]
            if user_records:
                learning_records = user_records
            print(f"[generate_daily_route] Got {len(learning_records)} learning records")
        except Exception as e:
            print(f"[generate_daily_route] Failed to get records: {e}")

        knowledge_mastery = profile_data.get('knowledgeMastery', [])
        cognitive_level = profile_data.get('cognitiveLevel', 'basic')
        learning_style = profile_data.get('learningStyle', 'pragmatic')
        learning_goals = profile_data.get('learningGoals', ['应对考试'])

        total_interactions = 0
        total_practice_time = 0
        pass_rates = []
        for r in learning_records:
            if isinstance(r, dict):
                total_interactions += r.get('interaction_count', 0)
                total_practice_time += r.get('code_practice_time', 0)
                pr = r.get('socratic_pass_rate', 0)
                if pr > 0:
                    pass_rates.append(pr)
        avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0

        system_prompt = """你是一个专业的AI学习规划师，专门为学生生成每日的个性化学习计划。
你的任务是分析学生的学习画像，生成最适合他们的今日学习任务。

## 学生画像分析维度：
1. 知识掌握情况 - 哪些知识点已掌握，哪些薄弱
2. 认知水平 - 基础/进阶/高级
3. 学习风格 - 理论型/实践型/混合型
4. 学习目标 - 应对考试/兴趣学习/技能提升

## 任务设计原则：
1. 难度适中，既有挑战又不至于无法完成
2. 结合学生的薄弱点和目标
3. 任务类型多样化（阅读、练习、复习、实践等）
4. 总时长控制在2-4小时
5. 包含一个轻松的任务（如喂养虚拟宠物、放松活动）

## 返回格式：
请返回JSON数组，每个任务包含：
- id: 任务ID（数字）
- title: 任务标题（15字以内，简短有力）
- description: 任务描述（30字以内，说明具体做什么）
- type: 任务类型（study/practice/review/relax）
- duration: 预计时长（分钟）
- subject: 学科领域
- difficulty: 难度（easy/medium/hard）
- taskUrl: 点击后跳转的页面路径，必须是以下之一：
  - courses.html （课程学习：视频课程、知识点学习）
  - code.html （编程练习：代码编写、调试、算法训练）
  - flow-meter.html （专注计时：番茄钟、专注力训练）
  - calendar.html （日历计划：制定学习计划、查看日程）
  - pixel-pet-game.html （休闲游戏：虚拟宠物、放松娱乐）
  - progress.html （学习进度：查看学习统计、成长记录）
  - socratic-ai.html （AI问答：苏格拉底式AI辅导）
  - plant.html （植物养成：种植、收获、图鉴收集）
  - stellar-showcase.html （星座展示：天文知识学习）
  - concept-analyzer.html （概念分析：概念梳理、知识图谱）
  - architecture-blueprint.html （架构蓝图：系统设计学习）
  - ai-pair-programming.html （AI结对编程：AI辅助编程）
  - video-player.html （视频学习：视频课程播放）
  - assessment.html （能力评估：测评答题）

请生成5-7个任务，确保：
1. 至少3个是针对当前薄弱环节的专项练习
2. 任务描述要具体（如"完成5道一元二次方程练习题"而不是"数学练习"）
3. 合理分配taskUrl（编程相关用/code.html，记忆背诵用/courses.html，等）
4. 总时长控制在2-3小时
5. 包含一个放松任务（taskUrl用/pixel-pet-game.html或/plant.html）

只返回JSON数组，不要包含任何其他说明文字。"""

        user_prompt = f"""请为以下学生生成今日学习计划：

## 学生基本信息
- 日期：{today}
- 学习目标：{', '.join(learning_goals)}
- 认知水平：{cognitive_level}
- 学习风格：{learning_style}

## 学习数据统计
- 累计学习交互：{total_interactions} 次
- 编程练习时长：{total_practice_time} 分钟
- 苏格拉底问答通过率：{avg_pass_rate:.1%}

## 知识掌握情况
"""

        if knowledge_mastery:
            for k in knowledge_mastery[:10]:
                name = k.get('name', k.get('topic', '未知'))
                mastery = k.get('mastery', k.get('level', '未知'))
                user_prompt += f"- {name}：{mastery}\n"
        else:
            user_prompt += "暂无详细数据\n"

        user_prompt += "\n请生成专属的今日学习计划："

        print("[generate_daily_route] Calling LLM...")
        tasks = default_tasks
        llm_used = False

        try:
            llm_response = call_llm_for_daily_route(system_prompt, user_prompt, temperature=0.3)
            print(f"[generate_daily_route] LLM response: {str(llm_response)[:300] if llm_response else 'None'}")

            if llm_response:
                json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
                if json_match:
                    parsed_tasks = json.loads(json_match.group())
                    if isinstance(parsed_tasks, list) and len(parsed_tasks) > 0:
                        tasks = parsed_tasks
                        llm_used = True
                        print(f"[generate_daily_route] Successfully parsed {len(tasks)} tasks from LLM")
        except json.JSONDecodeError as e:
            print(f"[generate_daily_route] JSON decode error: {e}")
        except Exception as e:
            print(f"[generate_daily_route] LLM processing error: {e}")

        for i, task in enumerate(tasks):
            if 'id' not in task:
                task['id'] = i + 1
            if 'taskUrl' not in task:
                task['taskUrl'] = '/html/courses.html'

        try:
            cache_data = {
                'tasks': tasks,
                'date': today_key,
                'completed': [],
                'generated_at': datetime.now().isoformat()
            }
            save_daily_route_cache(user_id, cache_data)
            print(f"[generate_daily_route] Cached {len(tasks)} tasks")
        except Exception as e:
            print(f"[generate_daily_route] Failed to cache: {e}")

        result = {
            "success": True,
            "date": today,
            "tasks": tasks,
            "llmUsed": llm_used,
            "profile": {
                "cognitiveLevel": cognitive_level,
                "learningStyle": learning_style,
                "totalInteractions": total_interactions,
                "practiceTime": total_practice_time,
                "passRate": avg_pass_rate
            }
        }
        print(f"[generate_daily_route] Returning {len(tasks)} tasks")
        return result
    except Exception as e:
        print(f"[generate_daily_route] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def save_daily_route_cache(user_id, cache_data):
    """保存今日航线缓存"""
    storage = database.load_local_storage()
    if 'daily_routes' not in storage:
        storage['daily_routes'] = []
    # 移除同一天的数据
    today_key = datetime.now().strftime("%Y-%m-%d")
    storage['daily_routes'] = [r for r in storage['daily_routes'] if r.get('date') != today_key]
    # 添加新数据
    cache_data['user_id'] = user_id
    storage['daily_routes'].append(cache_data)
    # 只保留最近30天的数据
    storage['daily_routes'] = storage['daily_routes'][-30:]
    database.save_local_storage(storage)


@app.post("/api/daily-route/complete")
async def complete_daily_task(request: dict):
    """
    标记任务完成
    """
    user_id = request.get('userId')
    task_id = request.get('taskId')

    if not user_id or task_id is None:
        return {"success": False, "error": "参数错误"}

    today_key = datetime.now().strftime("%Y-%m-%d")
    storage = database.load_local_storage()

    # 查找今日航线
    daily_routes = storage.get('daily_routes', [])
    today_route = None
    for route in reversed(daily_routes):
        if route.get('user_id') == user_id and route.get('date') == today_key:
            today_route = route
            break

    if not today_route:
        return {"success": False, "error": "今日航线未生成"}

    # 标记完成
    if task_id not in today_route.get('completed', []):
        if 'completed' not in today_route:
            today_route['completed'] = []
        today_route['completed'].append(task_id)

    # 更新存储
    storage['daily_routes'] = daily_routes
    database.save_local_storage(storage)

    # 获取任务信息用于通知
    task = next((t for t in today_route.get('tasks', []) if t.get('id') == task_id), None)

    # 异步触发学习路径刷新（任务完成意味着学情变化）
    _safe_trigger_learning_path_refresh(user_id, "daily_task_complete")

    return {
        "success": True,
        "completedCount": len(today_route.get('completed', [])),
        "totalCount": len(today_route.get('tasks', [])),
        "task": task
    }


@app.get("/api/daily-route/status")
async def get_daily_route_status(userId: int):
    """
    获取今日航线状态
    """
    if not userId:
        return {"success": False, "error": "用户未登录"}

    today_key = datetime.now().strftime("%Y-%m-%d")
    storage = database.load_local_storage()

    daily_routes = storage.get('daily_routes', [])
    today_route = None
    for route in reversed(daily_routes):
        if route.get('user_id') == userId and route.get('date') == today_key:
            today_route = route
            break

    if not today_route:
        return {
            "success": True,
            "generated": False,
            "tasks": [],
            "completed": [],
            "progress": 0
        }

    completed = today_route.get('completed', [])
    tasks = today_route.get('tasks', [])
    progress = len(completed) / len(tasks) * 100 if tasks else 0

    return {
        "success": True,
        "generated": True,
        "tasks": tasks,
        "completed": completed,
        "progress": progress,
        "date": today_route.get('date')
    }


@app.get("/api/news/more")
async def get_more_news():
    """
    获取更多新闻，支持按分类筛选
    使用并发请求 + 缓存优化加载速度
    """
    import feedparser
    from bs4 import BeautifulSoup
    import re
    import asyncio
    import aiohttp

    today = datetime.now().strftime("%Y年%m月%d日")

    # 内存缓存（进程内缓存，减少重复请求）
    global _more_news_cache, _more_news_cache_time
    cache_duration = 10 * 60  # 10分钟缓存
    if '_more_news_cache' not in globals():
        globals()['_more_news_cache'] = None
        globals()['_more_news_cache_time'] = 0

    # 检查缓存是否有效
    if (_more_news_cache is not None and
        (datetime.now() - _more_news_cache_time).total_seconds() < cache_duration):
        return {"success": True, "news": _more_news_cache, "cached": True}

    # 使用国内可访问的新闻源
    RSS_SOURCES = [
        ("https://36kr.com/feed", "36氪", "AI科技"),
        ("https://www.zhihu.com/api/v4/act/topic/19550347/items?limit=20", "知乎", "民生"),
        ("https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2517&k=&num=20&page=1", "新浪", "民生"),
    ]

    collected_news = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # 并发获取所有 RSS 源
    async def fetch_single_feed(session, rss_url, source_name, default_category):
        try:
            timeout = aiohttp.ClientTimeout(total=2)  # 减少超时到2秒
            async with session.get(rss_url, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()

            feed = feedparser.parse(text)
            results = []
            for entry in feed.entries[:8]:
                title = getattr(entry, 'title', '') or ''
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
                published = getattr(entry, 'published', '') or getattr(entry, 'updated', '') or ''
                link = getattr(entry, 'link', '') or ''

                if summary:
                    soup = BeautifulSoup(summary, 'html.parser')
                    summary = soup.get_text(separator=' ', strip=True)[:200]

                if title and len(title) > 5:
                    category = default_category
                    title_lower = title.lower()
                    if any(k in title_lower for k in ['ai', 'artificial', 'tech', 'technology', 'digital', 'software', 'app', 'robot', 'openai', 'google', 'microsoft', 'apple', '模型', '科技']):
                        category = "AI科技"
                    elif any(k in title_lower for k in ['economy', 'market', 'business', 'stock', 'trade', 'finance', 'bank', 'economy', '就业', '民生', 'health', '医疗', '教育', '房价']):
                        category = "民生"
                    elif any(k in title_lower for k in ['sport', 'movie', 'music', 'entertainment', 'culture', 'life', 'food', 'travel', '文化', '体育', '娱乐']):
                        category = "生活"

                    # 解析时间
                    timestamp = "今日"
                    if published:
                        try:
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(published)
                            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
                            diff = (now - dt).total_seconds()
                            if diff < 3600:
                                timestamp = f"{int(diff/60)}分钟前"
                            elif diff < 86400:
                                timestamp = f"{int(diff/3600)}小时前"
                            else:
                                timestamp = dt.strftime("%m月%d日")
                        except:
                            timestamp = "今日"

                    results.append({
                        "title": re.sub(r'[^\w\s一-鿿]', '', title)[:50],
                        "category": category,
                        "description": summary[:100] if summary else '点击查看详情',
                        "source": source_name,
                        "timestamp": timestamp,
                        "link": link
                    })
            return results
        except asyncio.TimeoutError:
            logger.warning(f"[get_more_news] Timeout fetching {source_name}")
            return []
        except Exception as e:
            logger.warning(f"[get_more_news] Error fetching {source_name}: {e}")
            return []

    async def fetch_zhihu_feed(session, url, source_name, default_category):
        """获取知乎热榜"""
        try:
            timeout = aiohttp.ClientTimeout(total=2)
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

            results = []
            for item in data.get('data', [])[:15]:
                title = item.get('target', {}).get('title', '') or item.get('title', '')
                if title and len(title) > 5:
                    results.append({
                        "title": title[:50],
                        "category": "民生",
                        "description": "知乎热榜话题",
                        "source": "知乎",
                        "timestamp": "今日",
                        "link": item.get('target', {}).get('url', '') or ''
                    })
            return results
        except Exception as e:
            logger.warning(f"[get_more_news] Zhihu fetch error: {e}")
            return []

    # 使用 aiohttp 并发请求所有源
    connector = aiohttp.TCPConnector(limit=10, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for url, name, cat in RSS_SOURCES:
            if 'zhihu' in url and 'api' in url:
                tasks.append(fetch_zhihu_feed(session, url, name, cat))
            else:
                tasks.append(fetch_single_feed(session, url, name, cat))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            collected_news.extend(result)

    # 去重
    unique_news = []
    seen_titles = set()
    for news in collected_news:
        title_key = news['title'].lower()[:25]
        is_duplicate = False
        for seen in seen_titles:
            if sum(c1 == c2 for c1, c2 in zip(title_key, seen)) > len(seen) * 0.65:
                is_duplicate = True
                break
        if not is_duplicate:
            seen_titles.add(title_key)
            unique_news.append(news)
        if len(unique_news) >= 30:
            break

    # 如果抓取到的新闻太少，使用 LLM 生成新闻
    if len(unique_news) < 5:
        logger.warning(f"[get_more_news] Only got {len(unique_news)} news, trying LLM fallback")
        llm_fallback = await generate_llm_news(today)
        if llm_fallback:
            _more_news_cache = llm_fallback
            _more_news_cache_time = datetime.now()
            return {"success": True, "news": llm_fallback}

    # 最终降级数据
    if len(unique_news) < 3:
        unique_news = [
            {"title": "AI大模型技术持续突破，应用场景不断拓展", "category": "AI科技", "description": "各大科技公司纷纷布局AI领域，大模型技术日新月异", "source": "AI前哨", "timestamp": "今日", "link": ""},
            {"title": "教育改革深入推进，素质教育受重视", "category": "民生", "description": "教育部门出台新政策，促进学生全面发展", "source": "教育报", "timestamp": "今日", "link": ""},
            {"title": "全球数字经济蓬勃发展，数字化转型加速", "category": "国际形势", "description": "数字经济成为全球经济增长新引擎", "source": "经济参考报", "timestamp": "今日", "link": ""},
            {"title": "健康生活方式受追捧，健身行业快速增长", "category": "生活", "description": "全民健身意识增强，健康产业迎来发展机遇", "source": "健康时报", "timestamp": "今日", "link": ""},
            {"title": "新能源汽车销量持续增长，绿色出行成趋势", "category": "民生", "description": "新能源汽车市场火爆，充电设施建设加速", "source": "汽车时报", "timestamp": "今日", "link": ""},
        ]

    # 更新缓存
    _more_news_cache = unique_news[:30]
    _more_news_cache_time = datetime.now()

    return {"success": True, "news": _more_news_cache}


async def generate_llm_news(today):
    """使用 LLM 生成新闻（当 RSS 抓取失败时）"""
    import re

    system_prompt = """你是一个新闻资讯聚合助手，专门为用户提供当日重点新闻摘要。
你的任务是根据当前日期，生成当日最重要的新闻资讯，涵盖以下领域：
1. AI科技 - 人工智能、大模型、互联网技术等
2. 民生 - 就业、收入、教育、医疗、住房等民生热点
3. 生活 - 消费、文化、娱乐、体育等生活资讯
4. 国际形势 - 国际政治、经济、外交等重大事件

请以JSON数组格式返回，每条新闻包含以下字段：
- title: 新闻标题（简洁有力，25字以内）
- category: 分类（AI科技/民生/生活/国际形势）
- description: 简短描述（40字以内）
- source: 新闻来源（可以是通用来源如：AI前哨、财经观察等）
- timestamp: 发布时间描述（统一使用"今日"）

请返回6-8条最重要的新闻，确保涵盖至少3个不同领域。
只返回JSON数组，不要包含任何其他文字说明。"""

    user_prompt = f"请列出{today}今日最值得关注的重点新闻，涵盖AI科技、民生、生活、国际形势等多个领域。"

    try:
        news_content = call_llm(system_prompt, user_prompt, temperature=0.3)
        if news_content and isinstance(news_content, str):
            json_match = re.search(r'\[.*\]', news_content, re.DOTALL)
            if json_match:
                news_list = json.loads(json_match.group())
                if isinstance(news_list, list) and len(news_list) > 0:
                    return news_list
    except Exception as e:
        logger.warning(f"[generate_llm_news] LLM news generation failed: {e}")

    return None


# ============================================================
# 数据库全面接入 - Pydantic 模型
# ============================================================

class GardenSaveRequest(BaseModel):
    userId: int
    seeds: int = 0
    gardenData: dict = {}

class PetSaveRequest(BaseModel):
    userId: int
    petData: Optional[dict] = None
    petGameData: Optional[dict] = None

class AchievementsSaveRequest(BaseModel):
    userId: int
    achievementsData: dict = {}

class StatsSaveRequest(BaseModel):
    userId: int
    statsData: dict = {}

class NotificationsSaveRequest(BaseModel):
    userId: int
    notificationsData: list = []
    lastUpdateTime: Optional[int] = None

class SettingsSaveRequest(BaseModel):
    userId: int
    settingsData: Optional[dict] = None
    weatherCity: Optional[str] = None
    floatingAlarmX: Optional[int] = None
    floatingAlarmY: Optional[int] = None
    hubTheme: Optional[str] = None

class CodingStateSaveRequest(BaseModel):
    userId: int
    codingStateData: dict = {}

class WeatherSaveRequest(BaseModel):
    userId: int
    weatherData: dict = {}

class FocusSaveRequest(BaseModel):
    userId: int
    focusData: list = []

class EcoSaveRequest(BaseModel):
    userId: int
    ecoData: dict = {}

class ProjectsSaveRequest(BaseModel):
    userId: int
    projectsData: list = []

class CalendarEventsSaveRequest(BaseModel):
    userId: int
    eventsData: dict = {}

class UserMetaUpdateRequest(BaseModel):
    userId: int
    preferredLanguage: Optional[str] = None
    theme: Optional[str] = None
    lastAgentId: Optional[str] = None


# ============================================================
# 数据库全面接入 - API 端点
# ============================================================

# ── 用户状态批量加载 ──

@app.get("/api/user/state/{user_id}")
def get_user_full_state(user_id: int):
    """一次性加载用户所有数据"""
    try:
        state = database.get_full_user_state(user_id)
        if state.get('user') is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"success": True, **state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载用户数据失败: {str(e)}")


# ── 用户元数据更新（语言、主题、代理） ──

@app.post("/api/user/meta")
def update_user_meta(request: UserMetaUpdateRequest):
    try:
        database.update_user_meta(
            request.userId,
            preferred_language=request.preferredLanguage,
            theme=request.theme,
            last_agent_id=request.lastAgentId,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


# ── 花园 / 植物 ──

@app.post("/api/garden/save")
def save_garden(request: GardenSaveRequest):
    try:
        database.save_user_garden(request.userId, request.seeds, request.gardenData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存花园失败: {str(e)}")


@app.get("/api/garden/load/{user_id}")
def load_garden(user_id: int):
    try:
        garden = database.get_user_garden(user_id)
        if garden:
            return {"success": True, "seeds": garden.get('seeds', 3), "gardenData": garden.get('garden_data', garden.get('garden_json', {}))}
        return {"success": True, "seeds": 3, "gardenData": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载花园失败: {str(e)}")


# ── 宠物 ──

@app.post("/api/pet/save")
def save_pet(request: PetSaveRequest):
    try:
        database.save_user_pet(
            request.userId,
            pet_data=request.petData,
            pet_game_data=request.petGameData,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存宠物失败: {str(e)}")


@app.get("/api/pet/load/{user_id}")
def load_pet(user_id: int):
    try:
        pet = database.get_user_pet(user_id)
        if pet:
            return {"success": True, "petData": pet.get('pet', {}), "petGameData": pet.get('pet_game', {})}
        return {"success": True, "petData": {}, "petGameData": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载宠物失败: {str(e)}")


# ── 成就 ──

@app.post("/api/achievements/save")
def save_achievements(request: AchievementsSaveRequest):
    try:
        database.save_user_achievements(request.userId, request.achievementsData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存成就失败: {str(e)}")


@app.get("/api/achievements/load/{user_id}")
def load_achievements(user_id: int):
    try:
        achievements = database.get_user_achievements(user_id)
        return {"success": True, "achievementsData": achievements if achievements else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载成就失败: {str(e)}")


# ── 统计数据 ──

@app.post("/api/stats/save")
def save_stats(request: StatsSaveRequest):
    try:
        database.save_user_stats(request.userId, request.statsData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存统计失败: {str(e)}")


@app.get("/api/stats/load/{user_id}")
def load_stats(user_id: int):
    try:
        stats = database.get_user_stats(user_id)
        return {"success": True, "statsData": stats if stats else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载统计失败: {str(e)}")


# ── 学习驾驶舱实时分析 ──

class CockpitAnalysisRequest(BaseModel):
    userId: int
    minutes: Optional[int] = 1  # 本次学习分钟数
    hour: Optional[int] = None  # 当前小时 (0-23)

@app.get("/api/cockpit/analysis/{user_id}")
async def get_cockpit_analysis(user_id: int):
    """
    返回全息"智理"学习驾驶舱所需的所有实时分析数据
    包括：思维深度、概念掌握、专注度、学习动能、交互统计等
    """
    try:
        stats = database.get_user_stats(user_id)
        prefs = database.get_user_preferences(user_id)
        coding = database.get_user_coding_state(user_id) if hasattr(database, 'get_user_coding_state') else {}
        eco = database.get_user_eco_data(user_id) if hasattr(database, 'get_user_eco_data') else {}
        garden = database.get_user_garden(user_id) or {}
        pet = database.get_user_pet(user_id) or {}

        # 从统计中提取数据
        interaction_count = stats.get('interactionCount', 0) if stats else 0
        learning_minutes = stats.get('codePracticeTime', 0) if stats else 0
        completed_tasks = stats.get('completedTasks', 0) if stats else 0
        focus_sessions = stats.get('focusSessions', 0) if stats else 0

        # 计算指标
        # 思维深度：基于交互次数和学习时长
        thinking_depth = min(95, 45 + (interaction_count % 50))
        if learning_minutes > 300:
            thinking_depth = min(95, thinking_depth + 15)
        elif learning_minutes > 100:
            thinking_depth = min(95, thinking_depth + 8)

        # 概念掌握率：基于完成任务数和交互次数
        concept_mastery = min(95, 50 + (completed_tasks % 40))
        if interaction_count > 50:
            concept_mastery = min(95, concept_mastery + 10)

        # 专注休息比
        total_minutes = max(1, learning_minutes)
        focus_ratio = min(95, 60 + (focus_sessions * 5))
        rest_ratio = 100 - focus_ratio if focus_ratio < 95 else 5

        # 学习动能
        momentum = min(98, 40 + (interaction_count % 50) + (completed_tasks % 20))
        if learning_minutes > 200:
            momentum = min(98, momentum + 10)

        # 认知评估等级
        if thinking_depth >= 85:
            cognitive_level = "L4·专家级"
        elif thinking_depth >= 70:
            cognitive_level = "L3·进阶级"
        elif thinking_depth >= 55:
            cognitive_level = "L2·基础级"
        else:
            cognitive_level = "L1·入门级"

        # 学习建议
        suggestions = []
        if concept_mastery < 60:
            suggestions.append("建议复习Hadoop基础概念，巩固知识体系")
        if focus_ratio > 85:
            suggestions.append("专注时间较长，建议休息15分钟恢复认知资源")
        if momentum > 80:
            suggestions.append("当前学习状态极佳，可适当挑战高难度内容")
        if completed_tasks > 0 and interaction_count > 0:
            suggestions.append(f"已完成{completed_tasks}个任务，继续保持节奏")

        # 最近学习领域分析
        recent_topics = stats.get('recentTopics', []) if stats else []
        if not recent_topics:
            # 从编码状态推断
            recent_code = coding.get('currentFile', '') if coding else ''
            recent_topics = ['Python核心', '数据结构', 'Hadoop基础', '数据挖掘'][:max(1, interaction_count % 3 + 1)]

        return {
            "success": True,
            "analysis": {
                "thinking_depth": thinking_depth,
                "concept_mastery": concept_mastery,
                "focus_ratio": focus_ratio,
                "rest_ratio": rest_ratio,
                "learning_momentum": momentum,
                "cognitive_level": cognitive_level,
                "interaction_count": interaction_count,
                "learning_minutes": learning_minutes,
                "completed_tasks": completed_tasks,
                "focus_sessions": focus_sessions,
                "recent_topics": recent_topics,
                "suggestions": suggestions[:3],
            },
            "eco": {
                "harvest_count": stats.get('harvestCount', 0) if stats else 0,
                "companion_hours": eco.get('companionHours', 0) if eco else 0,
                "pet_level": eco.get('petLevel', 1) if eco else 1,
                "garden_seeds": garden.get('seeds', 3) if garden else 3,
                "plant_count": len(garden.get('garden_data', {})) if garden else 0,
            },
            "stats": {
                "interactions": interaction_count,
                "minutes": learning_minutes,
                "tasks": completed_tasks,
                "focus_sessions": focus_sessions,
            }
        }
    except Exception as e:
        # 降级：返回合理默认值
        return {
            "success": True,
            "analysis": {
                "thinking_depth": 78,
                "concept_mastery": 85,
                "focus_ratio": 80,
                "rest_ratio": 20,
                "learning_momentum": 88,
                "cognitive_level": "L3·进阶级",
                "interaction_count": 0,
                "learning_minutes": 0,
                "completed_tasks": 0,
                "focus_sessions": 0,
                "recent_topics": ["Python核心", "数据挖掘"],
                "suggestions": ["开始学习以获取实时分析数据"],
            },
            "eco": {
                "harvest_count": 0,
                "companion_hours": 0,
                "pet_level": 1,
                "garden_seeds": 3,
                "plant_count": 0,
            },
            "stats": {
                "interactions": 0,
                "minutes": 0,
                "tasks": 0,
                "focus_sessions": 0,
            }
        }


@app.post("/api/cockpit/stats/sync")
async def sync_cockpit_stats(request: CockpitAnalysisRequest):
    """
    同步驾驶舱统计数据到数据库
    """
    try:
        stats = database.get_user_stats(request.userId)
        if not stats:
            stats = {}

        # 更新交互计数
        stats['interactionCount'] = stats.get('interactionCount', 0) + 1
        stats['lastInteractionTime'] = datetime.now().isoformat()

        database.save_user_stats(request.userId, stats)
        return {"success": True, "interactionCount": stats['interactionCount']}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/cockpit/learning-time")
async def update_learning_time(request: CockpitAnalysisRequest):
    """
    更新学习时长（每分钟调用一次）
    同时记录每日分钟数用于趋势图
    """
    try:
        stats = database.get_user_stats(request.userId)
        if not stats:
            stats = {"daily_minutes": {}, "hourly_minutes": {}}

        today = datetime.now().strftime('%Y-%m-%d')
        current_hour = request.hour if request.hour is not None else datetime.now().hour

        # 初始化 daily_minutes 结构
        if 'daily_minutes' not in stats:
            stats['daily_minutes'] = {}
        if 'hourly_minutes' not in stats:
            stats['hourly_minutes'] = {}
        if today not in stats['hourly_minutes']:
            stats['hourly_minutes'][today] = {}

        # 更新每日分钟数（使用传入的分钟数）
        minutes_to_add = request.minutes if request.minutes else 1
        stats['daily_minutes'][today] = stats['daily_minutes'].get(today, 0) + minutes_to_add

        # 更新小时分钟数
        stats['hourly_minutes'][today][str(current_hour)] = stats['hourly_minutes'][today].get(str(current_hour), 0) + minutes_to_add

        # 更新累计分钟数
        stats['codePracticeTime'] = stats.get('codePracticeTime', 0) + minutes_to_add

        database.save_user_stats(request.userId, stats)
        return {
            "success": True,
            "minutes": stats['codePracticeTime'],
            "today_minutes": stats['daily_minutes'].get(today, 0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 学习概览 API ──

class StudySessionRequest(BaseModel):
    userId: int
    session_date: str
    duration_minutes: int = 0
    start_time: str = ""
    end_time: str = ""
    subject: str = ""
    node_id: str = ""


class LearningGoalRequest(BaseModel):
    userId: int
    goal_type: str = "daily"
    title: str = ""
    target_value: int = 60
    current_value: int = 0
    unit: str = "minutes"
    start_date: str = ""
    end_date: str = ""


class GoalUpdateRequest(BaseModel):
    goal_id: int
    current_value: int


@app.get("/api/study/sessions/{user_id}")
def get_study_sessions(user_id: int, start_date: str = None, end_date: str = None):
    """获取学习时段记录"""
    try:
        sessions = database.get_study_sessions(user_id, start_date, end_date)
        return {"success": True, "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学习时段失败: {str(e)}")


@app.post("/api/study/sessions")
def create_study_session(request: StudySessionRequest):
    """记录学习时段"""
    try:
        session_data = {
            'session_date': request.session_date,
            'duration_minutes': request.duration_minutes,
            'start_time': request.start_time,
            'end_time': request.end_time,
            'subject': request.subject,
            'node_id': request.node_id,
        }
        database.save_study_session(request.userId, session_data)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存学习时段失败: {str(e)}")


@app.get("/api/study/total/{user_id}")
def get_total_study_time(user_id: int, start_date: str = None, end_date: str = None):
    """获取总学习时长"""
    try:
        total = database.get_total_study_minutes(user_id, start_date, end_date)
        return {"success": True, "total_minutes": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学习时长失败: {str(e)}")


@app.get("/api/goals/{user_id}")
def get_goals(user_id: int, active_only: bool = True):
    """获取学习目标"""
    try:
        goals = database.get_learning_goals(user_id, active_only)
        return {"success": True, "goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学习目标失败: {str(e)}")


@app.post("/api/goals")
def create_goal(request: LearningGoalRequest):
    """创建学习目标"""
    try:
        goal_data = {
            'goal_type': request.goal_type,
            'title': request.title,
            'target_value': request.target_value,
            'current_value': request.current_value,
            'unit': request.unit,
            'start_date': request.start_date,
            'end_date': request.end_date,
        }
        database.save_learning_goal(request.userId, goal_data)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建学习目标失败: {str(e)}")


@app.put("/api/goals")
def update_goal(request: GoalUpdateRequest):
    """更新目标进度"""
    try:
        database.update_learning_goal(request.goal_id, request.current_value)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新目标失败: {str(e)}")


@app.delete("/api/goals/{goal_id}")
def delete_goal(goal_id: int):
    """停用学习目标"""
    try:
        database.deactivate_learning_goal(goal_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停用目标失败: {str(e)}")


@app.get("/api/stats/overview/{user_id}")
def get_stats_overview(user_id: int):
    """获取学习概览数据"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')

        # 从 user_stats 读取数据
        stats = database.get_user_stats(user_id)
        daily_minutes = stats.get('daily_minutes', {}) if stats else {}

        # 今日学习分钟数
        today_minutes = daily_minutes.get(today, 0)

        # 计算本周总学习时长
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
        week_minutes = 0
        current = datetime.now()
        for i in range(7):
            date = current - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            if date_str >= week_start:
                week_minutes += daily_minutes.get(date_str, 0)

        # 计算上周总学习时长（用于趋势计算）
        last_week_end = week_start
        last_week_start = (datetime.strptime(week_start, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        last_week_minutes = 0
        for date_str, minutes in daily_minutes.items():
            if last_week_start <= date_str < last_week_end:
                last_week_minutes += minutes

        # 计算周同比趋势百分比
        if last_week_minutes > 0:
            week_trend = round(((week_minutes - last_week_minutes) / last_week_minutes) * 100)
        else:
            week_trend = 100 if week_minutes > 0 else 0

        # 获取活跃目标
        goals = database.get_learning_goals(user_id, active_only=True)

        # 获取知识点掌握度
        mastery = database.get_user_knowledge_mastery(user_id)
        avg_mastery = sum(m['mastery'] for m in mastery) / len(mastery) if mastery else 0

        return {
            "success": True,
            "overview": {
                "today_minutes": today_minutes,
                "week_minutes": week_minutes,
                "week_trend": week_trend,
                "total_goals": len(goals),
                "active_goals": [dict(g) if not isinstance(g, dict) else g for g in goals],
                "knowledge_count": len(mastery),
                "avg_mastery": int(avg_mastery),
            }
        }
    except Exception as e:
        return {
            "success": True,
            "overview": {
                "today_minutes": 0,
                "week_minutes": 0,
                "week_trend": 0,
                "total_goals": 0,
                "active_goals": [],
                "knowledge_count": 0,
                "avg_mastery": 0,
            }
        }


@app.get("/api/stats/heatmap/{user_id}")
def get_heatmap_data(user_id: int, weeks: int = 4):
    """获取热力图数据"""
    try:
        stats = database.get_user_stats(user_id)
        daily_minutes = stats.get('daily_minutes', {}) if stats else {}

        today = datetime.now()
        heatmap_data = []

        for i in range(weeks * 7):
            date = today - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            total_minutes = daily_minutes.get(date_str, 0)

            heatmap_data.append({
                'date': date_str,
                'day_of_week': date.strftime('%a'),
                'minutes': total_minutes,
                'level': 0 if total_minutes == 0 else (1 if total_minutes < 30 else (2 if total_minutes < 60 else (3 if total_minutes < 120 else 4)))
            })

        heatmap_data.reverse()
        return {"success": True, "heatmap": heatmap_data}
    except Exception as e:
        return {"success": True, "heatmap": []}


@app.get("/api/stats/mastery/{user_id}")
def get_mastery_data(user_id: int):
    """获取知识点掌握度"""
    try:
        mastery = database.get_user_knowledge_mastery(user_id)
        return {"success": True, "mastery": mastery}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取掌握度失败: {str(e)}")


@app.get("/api/stats/trend/{user_id}")
def get_trend_data(user_id: int, days: int = 7):
    """获取学习趋势数据"""
    try:
        stats = database.get_user_stats(user_id)
        daily_minutes = stats.get('daily_minutes', {}) if stats else {}

        today = datetime.now()
        trend_data = []

        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            minutes = daily_minutes.get(date_str, 0)

            trend_data.append({
                'date': date_str,
                'day': date.strftime('%m/%d'),
                'weekday': date.strftime('%a'),
                'minutes': minutes,
            })

        trend_data.reverse()
        return {"success": True, "trend": trend_data}
    except Exception as e:
        return {"success": True, "trend": []}


# ── 通知 ──

@app.post("/api/notifications/save")
def save_notifications(request: NotificationsSaveRequest):
    try:
        database.save_user_notifications(
            request.userId,
            request.notificationsData,
            last_update_time=request.lastUpdateTime,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存通知失败: {str(e)}")


@app.get("/api/notifications/load/{user_id}")
def load_notifications(user_id: int):
    try:
        data = database.get_user_notifications(user_id)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载通知失败: {str(e)}")


# ── 综合设置 ──

@app.post("/api/settings/save")
def save_settings(request: SettingsSaveRequest):
    try:
        database.save_user_settings(
            request.userId,
            settings_data=request.settingsData,
            weather_city=request.weatherCity,
            floating_alarm_x=request.floatingAlarmX,
            floating_alarm_y=request.floatingAlarmY,
            hub_theme=request.hubTheme,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")


@app.get("/api/settings/load/{user_id}")
def load_settings(user_id: int):
    try:
        settings = database.get_user_settings(user_id)
        return {"success": True, **settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载设置失败: {str(e)}")


# ── 编程状态 ──

@app.post("/api/coding-state/save")
def save_coding_state(request: CodingStateSaveRequest):
    try:
        database.save_user_coding_state(request.userId, request.codingStateData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存编程状态失败: {str(e)}")


@app.get("/api/coding-state/load/{user_id}")
def load_coding_state(user_id: int):
    try:
        state = database.get_user_coding_state(user_id)
        return {"success": True, "codingStateData": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载编程状态失败: {str(e)}")


# ── 天气缓存 ──

@app.post("/api/weather/save")
def save_weather(request: WeatherSaveRequest):
    try:
        database.save_user_weather_cache(request.userId, request.weatherData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存天气失败: {str(e)}")


@app.get("/api/weather/load/{user_id}")
def load_weather(user_id: int):
    try:
        weather = database.get_user_weather_cache(user_id)
        return {"success": True, "weatherData": weather}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载天气失败: {str(e)}")


@app.delete("/api/weather/clear/{user_id}")
def clear_weather(user_id: int):
    try:
        database.delete_user_weather_cache(user_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除天气失败: {str(e)}")


# ── 专注历史 ──

@app.post("/api/focus/save")
def save_focus(request: FocusSaveRequest):
    try:
        database.save_user_focus_history(request.userId, request.focusData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存专注历史失败: {str(e)}")


@app.get("/api/focus/load/{user_id}")
def load_focus(user_id: int):
    try:
        focus = database.get_user_focus_history(user_id)
        return {"success": True, "focusData": focus if focus else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载专注历史失败: {str(e)}")


class FocusRecordRequest(BaseModel):
    userId: int
    studyMinutes: int = 0
    focusMinutes: int = 0
    pageSwitches: int = 0
    completedFocus: bool = False
    source: str = "activity"
    timestamp: str = ""


@app.post("/api/focus/record")
def record_focus(request: FocusRecordRequest):
    """前端 focus-sync.js 调用的专注记录接口，将单条记录追加到用户专注历史中。"""
    try:
        existing = database.get_user_focus_history(request.userId)
        history = existing if isinstance(existing, list) else []
        if not isinstance(history, list):
            history = []
        history.append({
            "studyMinutes": request.studyMinutes,
            "focusMinutes": request.focusMinutes,
            "pageSwitches": request.pageSwitches,
            "completedFocus": request.completedFocus,
            "source": request.source,
            "timestamp": request.timestamp or datetime.now().isoformat(),
        })
        database.save_user_focus_history(request.userId, history)
        summary = {
            "todayStudyMinutes": sum(h.get("studyMinutes", 0) for h in history[-7:]),
            "todayFocusMinutes": sum(h.get("focusMinutes", 0) for h in history[-7:]),
            "totalRecords": len(history),
        }
        return {"success": True, "focusSummary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录专注历史失败: {str(e)}")


# ── 生态数据 ──

@app.post("/api/eco/save")
def save_eco(request: EcoSaveRequest):
    try:
        database.save_user_eco_data(request.userId, request.ecoData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存生态数据失败: {str(e)}")


@app.get("/api/eco/load/{user_id}")
def load_eco(user_id: int):
    try:
        eco = database.get_user_eco_data(user_id)
        return {"success": True, "ecoData": eco if eco else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载生态数据失败: {str(e)}")


# ── 知识节点 ──

@app.get("/api/knowledge/nodes/{user_id}")
def get_nodes(user_id: int, active: bool = False):
    """获取用户的知识节点
    - active=true: 只返回已激活的节点（根据学习记录过滤）
    - active=false: 返回所有节点
    """
    try:
        if active:
            nodes = database.get_active_knowledge_nodes(user_id)
        else:
            nodes = database.get_knowledge_nodes(user_id)
        return {"success": True, "nodes": nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识节点失败: {str(e)}")


@app.post("/api/knowledge/nodes")
def save_node(request: Request):
    """创建或更新知识节点"""
    try:
        data = request.json()
        user_id = data.get('user_id')
        node_data = data.get('node')
        if not user_id or not node_data:
            raise HTTPException(status_code=400, detail="缺少user_id或node数据")

        database.save_knowledge_node(user_id, node_data)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存知识节点失败: {str(e)}")


@app.post("/api/knowledge/review")
def submit_review(request: Request):
    """提交复习结果并更新SM2数据"""
    try:
        data = request.json()
        user_id = data.get('user_id')
        node_id = data.get('node_id')
        quality = data.get('quality', 0)
        response_time = data.get('response_time', 0)

        if not user_id or not node_id:
            raise HTTPException(status_code=400, detail="缺少user_id或node_id")

        result = database.add_review_record(user_id, node_id, quality, response_time)
        if result is None:
            raise HTTPException(status_code=404, detail="知识节点不存在")

        return {"success": True, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交复习失败: {str(e)}")


@app.get("/api/knowledge/pending/{user_id}")
def get_pending(user_id: int):
    """获取需要复习的节点列表"""
    try:
        pending = database.get_pending_reviews(user_id)
        return {"success": True, "pending": pending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取待复习列表失败: {str(e)}")


@app.get("/api/knowledge/records/{user_id}")
def get_records(user_id: int, node_id: str = None):
    """获取复习记录"""
    try:
        records = database.get_review_records(user_id, node_id)
        return {"success": True, "records": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取复习记录失败: {str(e)}")


# ── AI课程关联分析 ──

COURSE_RELATION_SYSTEM_PROMPT = """你是一个学习路径规划专家，专门分析课程之间的前置知识和关联性。
请分析用户激活的课程列表，输出每对课程的关系。

关系类型：
- prerequisite: 前置知识（A是B的前置，必须先学A才能学B）
- related: 相关知识（A和B有关联，学A对理解B有帮助）
- none: 无关

输出格式：严格JSON数组，每项包含 source, target, relationship_type, strength(0-1)
示例：[{"source":"数学基础","target":"机器学习","relationship_type":"prerequisite","strength":0.9}]

只返回JSON数组，不要其他内容。"""


@app.post("/api/knowledge/analyze-relations")
async def analyze_course_relations(request: Request):
    """AI分析课程之间的关联性

    分析用户已激活的知识节点，调用AI识别课程间的前置知识和关联关系
    """
    try:
        import json as json_mod
        from datetime import datetime
        from llm_stream import call_llm_async

        data = await request.json()
        user_id = data.get('user_id')

        if not user_id:
            raise HTTPException(status_code=400, detail="缺少user_id")

        # 获取用户已激活的知识节点
        active_nodes = database.get_active_knowledge_nodes(user_id)

        if not active_nodes:
            return {"success": True, "relations": [], "message": "没有激活的课程"}

        if len(active_nodes) < 2:
            return {"success": True, "relations": [], "message": "课程数量不足，无法分析关联"}

        # 构建课程列表
        courses = []
        for node in active_nodes:
            courses.append({
                'node_id': node.get('node_id'),
                'name': node.get('name'),
                'level': node.get('level', 'leaf'),
                'subject': node.get('subject', '')
            })

        # 构建AI提示词
        course_list = "\n".join([f"- {c['name']} ({c['level']}, {c['subject']})" for c in courses])

        user_prompt = f"""请分析以下课程的关联性：

{course_list}

只返回JSON数组，不要其他内容。"""

        # 调用AI分析
        try:
            ai_response = await call_llm_async(
                system_prompt=COURSE_RELATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3
            )

            # 解析AI响应
            relations = []
            try:
                # 尝试直接解析
                relations = json_mod.loads(ai_response)
            except json_mod.JSONDecodeError:
                # 尝试提取JSON部分
                import re
                json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
                if json_match:
                    relations = json_mod.loads(json_match.group())

            if not isinstance(relations, list):
                relations = []

            # 保存分析结果到各节点
            now = datetime.now().isoformat()

            # 构建 node_id -> relations 映射
            relations_by_node = {}
            for rel in relations:
                source = rel.get('source')
                target = rel.get('target')
                if not source or not target:
                    continue
                if source not in relations_by_node:
                    relations_by_node[source] = []
                relations_by_node[source].append({
                    'node_id': target,
                    'type': rel.get('relationship_type', 'related'),
                    'strength': rel.get('strength', 0.5)
                })
                # 双向保存
                if target not in relations_by_node:
                    relations_by_node[target] = []
                # 不双向保存，避免重复

            # 更新每个节点的关系数据
            for node in active_nodes:
                node_id = node.get('node_id')
                related = relations_by_node.get(node_id, [])

                # 更新到数据库
                database.update_node_relations(user_id, node_id, related, now)

            return {
                "success": True,
                "relations": relations,
                "analyzed_at": now,
                "node_count": len(active_nodes)
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"课程关联分析失败: {str(e)}")


# ── 架构项目 ──

@app.post("/api/projects/save")
def save_projects(request: ProjectsSaveRequest):
    try:
        database.save_user_projects(request.userId, request.projectsData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存项目失败: {str(e)}")


@app.get("/api/projects/load/{user_id}")
def load_projects(user_id: int):
    try:
        projects = database.get_user_projects(user_id)
        return {"success": True, "projectsData": projects if projects else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载项目失败: {str(e)}")


# ── 日历事件 ──

@app.post("/api/calendar-events/save")
def save_calendar_events(request: CalendarEventsSaveRequest):
    try:
        database.save_user_calendar_events(request.userId, request.eventsData)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存日历事件失败: {str(e)}")


@app.get("/api/calendar-events/load/{user_id}")
def load_calendar_events(user_id: int):
    try:
        events = database.get_user_calendar_events(user_id)
        return {"success": True, "eventsData": events if events else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载日历事件失败: {str(e)}")


# ── 每日路线 ──

class DailyRouteSaveRequest(BaseModel):
    userId: int
    routeDate: str
    tasks: list = []
    completed: list = []


@app.post("/api/daily-route/save-db")
def save_daily_route_db(request: DailyRouteSaveRequest):
    """保存每日学习路线到数据库"""
    try:
        database.save_daily_route(
            request.userId, request.routeDate,
            request.tasks, request.completed,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存路线失败: {str(e)}")


@app.get("/api/daily-route/load-db/{user_id}/{route_date}")
def load_daily_route_db(user_id: int, route_date: str):
    try:
        route = database.get_daily_route(user_id, route_date)
        if route:
            return {"success": True, "route": route}
        return {"success": True, "route": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载路线失败: {str(e)}")


# ── 游客登录 ──

@app.post("/api/login/guest")
def guest_login(http_request: Request):
    """游客快速登录 - 生成临时账号"""
    ip_address, user_agent = get_login_request_meta(http_request)
    import random
    import string
    guest_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    guest_username = f"guest_{guest_id}"
    guest_password = hashlib.md5(guest_username.encode()).hexdigest()
    avatar = f"https://api.dicebear.com/7.x/adventurer/svg?seed={guest_username}&backgroundColor=b6e3f4"

    existing = database.get_user_by_username(guest_username)
    if existing:
        user_id = existing.get('id')
    else:
        hashed = hash_password(guest_password)
        user_id = database.create_user(guest_username, hashed, avatar, f"游客_{guest_id[:4]}")

    database.update_last_login(user_id)
    database.record_login_event(user_id, guest_username, True, "访客登录", ip_address, user_agent)
    return {
        "success": True,
        "userId": user_id,
        "username": guest_username,
        "nickname": f"游客_{guest_id[:4]}",
        "avatar": avatar,
        "currentTask": "大数据导论",
        "hasCompletedAssessment": False,
        "preferences": get_user_preferences_internal(user_id),
    }


# ============================================================
# 修改已有 /api/login 端点（增强版：返回完整状态）
# ============================================================

# 原始 login 端点已存在，这里提供一个增强版 login-v2，
# 返回完整用户状态，省去前端再请求一次 /api/user/state

class LoginRequestV2(BaseModel):
    username: str
    password: str


@app.post("/api/login-v2")
def login_v2(body: LoginRequestV2, http_request: Request):
    """增强版登录：返回完整用户状态 + 认证信息"""
    ip_address, user_agent = get_login_request_meta(http_request)
    if not body.username or not body.password:
        database.record_login_event(None, body.username, False, "用户名和密码不能为空", ip_address, user_agent)
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    user = database.get_user_by_username(body.username)
    if not user:
        database.record_login_event(None, body.username, False, "用户不存在", ip_address, user_agent)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(body.password, user['password']):
        database.record_login_event(user.get('id'), body.username, False, "密码错误", ip_address, user_agent)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    database.update_last_login(user['id'])
    database.record_login_event(user['id'], user['username'], True, "", ip_address, user_agent)
    avatar = user['avatar'] or f"https://api.dicebear.com/7.x/adventurer/svg?seed={body.username}&backgroundColor=b6e3f4"
    nickname = user['nickname'] or (user['username'] + "同学")
    profile = database.get_user_profile(user['id'])
    has_completed_assessment = profile is not None and profile.get('profile_json') is not None

    # 加载完整状态
    full_state = database.get_full_user_state(user['id'])

    return {
        "success": True,
        "userId": user['id'],
        "username": user['username'],
        "nickname": nickname,
        "avatar": avatar,
        "currentTask": user['current_task'],
        "hasCompletedAssessment": has_completed_assessment,
        "preferences": full_state.get('preferences', {}),
        "garden": full_state.get('garden', {}),
        "pet": full_state.get('pet', {}),
        "achievements": full_state.get('achievements', {}),
        "stats": full_state.get('stats', {}),
        "notifications": full_state.get('notifications', {}),
        "settings": full_state.get('settings', {}),
        "codingState": full_state.get('coding_state'),
        "weatherCache": full_state.get('weather_cache'),
        "focusHistory": full_state.get('focus_history', []),
        "ecoData": full_state.get('eco_data', {}),
        "projects": full_state.get('projects', []),
        "calendarEvents": full_state.get('calendar_events', {}),
        "learningProfile": full_state.get('learning_profile'),
        "learningPath": full_state.get('learning_path'),
        "learningRecord": full_state.get('learning_record'),
    }


# ============================================================
# 课程生成API (OpenMAIC风格)
# ============================================================

@app.post("/api/v2/course/generate/stream")
async def generate_course_stream(request: CourseGenerationRequest):
    """
    流式生成课程（LLM驱动版）
    使用 CourseGenerator 进行真实的大模型调用，通过SSE返回进度
    """
    from course_generator import get_course_generator
    generator = get_course_generator()

    queue = asyncio.Queue(maxsize=500)

    async def background_generate():
        try:
            async for event in generator.generate_course(
                requirement=request.requirement,
                student_id=request.student_id or "",
                enable_image=request.enable_image,
                enable_tts=request.enable_tts,
                enable_video=request.enable_video,
                voice_id=request.voice_id,
                agent_mode=request.agent_mode,
                interactive_mode=request.interactive_mode,
                enable_pdf_upload=request.enable_pdf_upload,
                pdf_text=request.pdf_text,
                enable_web_search=request.enable_web_search,
                enable_minimax_ppt=request.enable_minimax_ppt,
                minimax_ppt_ratio=request.minimax_ppt_ratio,
                teacher_name=request.teacher_name,
                teacher_avatar=request.teacher_avatar,
                teacher_profession=request.teacher_profession,
                teacher_personality=request.teacher_personality,
                teacher_teaching_style=request.teacher_teaching_style,
                teacher_icon=request.teacher_icon,
                teacher_system_prompt=request.teacher_system_prompt,
                teacher_greeting=request.teacher_greeting,
            ):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # 丢弃最旧的事件，保留最新的
                    try:
                        queue.get_nowait()
                        queue.put_nowait(event)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        pass
        except Exception as e:
            logger.exception("Background generation error")
            try:
                queue.put_nowait({
                    "type": "error",
                    "error": str(e),
                    "progress": 0,
                })
            except asyncio.QueueFull:
                pass
        finally:
            # 发送结束标记
            try:
                queue.put_nowait({"type": "__done__"})
            except asyncio.QueueFull:
                pass

    # 启动后台生成任务（不跟随SSE连接生命周期）
    asyncio.create_task(background_generate())

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # 发送心跳防止超时断开
                    yield sse_event("status", {"progress": 0, "data": {"msg": "生成中..."}})
                    continue

                if event.get("type") == "__done__":
                    break

                event_type = event.pop("type", "message")
                yield sse_event(event_type, event)
        except asyncio.CancelledError:
            # 客户端断开连接，不要取消后台任务
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/v2/course/export/pptx")
async def export_course_pptx(data: dict[str, Any] = {}):
    """
    导出课程为PPTX文件
    接收前端传过来的 CourseData JSON，返回 .pptx 文件
    """
    try:
        from pptx_export import PPTXExporter
        course_data = CourseData(**data)
        exporter = PPTXExporter()
        pptx_bytes = exporter.export(course_data)
        filename = f"{course_data.title or '课程'}.pptx"
        encoded_filename = requests.utils.quote(filename)

        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPTX导出失败: {str(e)}")


@app.post("/api/v2/course/extract-pdf-text")
async def extract_pdf_text(request: Request):
    """
    提取PDF文本内容
    接收base64编码的PDF内容或文件路径，返回提取的文本
    """
    import base64
    import pdfplumber
    import tempfile
    import os

    try:
        body = await request.json()
        pdf_content = body.get("pdf_content")  # base64 encoded PDF
        pdf_url = body.get("pdf_url")  # or URL to download
        filename = body.get("filename", "document.pdf")

        text_content = ""

        if pdf_content:
            # Decode base64 PDF
            pdf_bytes = base64.b64decode(pdf_content)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name
        elif pdf_url:
            # Download from URL
            resp = requests.get(pdf_url, timeout=30)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
        else:
            raise HTTPException(status_code=400, detail="未提供PDF内容或URL")

        # Extract text using pdfplumber
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n\n"

        # Cleanup temp file
        os.unlink(tmp_path)

        if not text_content.strip():
            return {"success": True, "text": "", "message": "PDF未提取到文本内容"}

        # Truncate if too long (LLM context limit)
        max_chars = 50000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "\n\n[内容已截断...]"

        return {
            "success": True,
            "text": text_content,
            "filename": filename,
            "char_count": len(text_content)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF解析失败: {str(e)}")


# ============================================================
# 课堂聊天 API (基于当前课程上下文)
# ============================================================


async def _sse_event_chat(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/v2/course/chat")
async def course_chat(request: CourseChatRequest):
    """课堂内AI问答（基于当前课程上下文，支持多教师角色）"""
    from llm_stream import call_llm_async
    from prompts import build_prompt

    # 尝试构建完整的课程上下文
    agent_role = getattr(request, 'agent_role', 'AI助教') if hasattr(request, 'agent_role') else 'AI助教'
    course_title = request.course_id  # fallback

    # 网络搜索：检测问题是否超出课程范围，必要时调用 Tavily
    web_context = ""
    if getattr(request, 'enable_web_search', False):
        try:
            from app.services.teacher.web_search import search_web, format_as_context
            # 检测问题是否涉及课程外知识（最新、现在、新闻、动态等关键词）
            beyond_keywords = ["最新", "现在", "新闻", "动态", "最近", "202", "如何", "怎么"]
            needs_search = (
                len(request.slide_content) < 100 or
                any(kw in request.user_input for kw in beyond_keywords)
            )
            if needs_search:
                search_resp = await search_web(request.user_input)
                if search_resp and search_resp.source_count > 0:
                    web_context = format_as_context(search_resp)
                    logger.info(f"[course_chat] Tavily搜索成功，结果数={search_resp.source_count}")
        except Exception as e:
            logger.warning(f"[course_chat] Tavily搜索失败: {e}")

    # 加载课程数据以获取更多上下文
    filepath = _get_course_path(request.course_id)
    course_context = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                course = json.load(f)
            course_title = course.get("title", request.course_id)
            # 构建课程大纲摘要
            outlines = course.get("outlines", [])
            if outlines:
                course_context = "\n".join(
                    f"  - {o.get('title', '')} ({o.get('type', 'slide')})"
                    for o in outlines[:8]
                )
            # 获取教师团队
            agent_team = course.get("agent_team", [])
            if agent_team and not hasattr(request, 'agent_role'):
                agent_role = agent_team[0].get("role", "课程导师") if isinstance(agent_team[0], dict) else "课程导师"
        except Exception:
            pass

    # 使用增强提示词模板
    try:
        if hasattr(request, 'agent_role') and request.agent_role:
            persona = getattr(request, 'persona', '专业、耐心') if hasattr(request, 'persona') else '专业、耐心'
            system_prompt = build_prompt(
                "classroom_chat_contextual",
                course_title=course_title,
                agent_role=agent_role,
                persona=persona,
                scene_title=request.slide_title,
                scene_content=request.slide_content[:500],
                speech=request.speech[:300],
                course_context=course_context[:500],
                user_input=request.user_input,
            )
            user_prompt = request.user_input
        else:
            system_prompt = f"""你是一个课堂AI助教，正在辅助学生学习课程。

当前课程: {course_title}
当前幻灯片: {request.slide_title}
幻灯片内容: {request.slide_content[:500]}
教师台词: {request.speech[:300]}
课程大纲: {course_context[:500]}
{web_context}

请基于以上课程上下文回答学生的问题。回答要简洁、准确、有教育意义。"""

            history_str = "\n".join(
                f"{'学生' if m.get('role') == 'user' else '教师'}: {m.get('content', '')}"
                for m in request.history[-6:]
            )
            user_prompt = f"历史对话：\n{history_str}\n\n学生提问：{request.user_input}"
    except Exception:
        system_prompt = f"""你是课堂AI助教。当前课程: {course_title}
当前讲解: {request.slide_title}
{web_context}
请回答学生问题，简洁有教育意义。"""
        user_prompt = request.user_input

    try:
        result = await call_llm_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
        )
        return {"success": True, "content": result.strip()}
    except Exception as e:
        return {"success": False, "content": "抱歉，我暂时无法回答这个问题。"}


@app.post("/api/v2/course/chat/stream")
async def course_chat_stream(request: CourseChatRequest):
    """课堂内AI问答（流式SSE）"""
    from llm_stream import call_llm_stream

    # 网络搜索
    web_context = ""
    if getattr(request, 'enable_web_search', False):
        try:
            from app.services.teacher.web_search import search_web, format_as_context
            beyond_keywords = ["最新", "现在", "新闻", "动态", "最近", "202", "如何", "怎么"]
            needs_search = (
                len(request.slide_content) < 100 or
                any(kw in request.user_input for kw in beyond_keywords)
            )
            if needs_search:
                search_resp = await search_web(request.user_input)
                if search_resp and search_resp.source_count > 0:
                    web_context = format_as_context(search_resp)
        except Exception:
            pass

    system_prompt = f"""你是一个课堂AI助教，正在辅助学生学习课程。

当前课程: {request.course_id}
当前幻灯片: {request.slide_title}
幻灯片内容: {request.slide_content[:500]}
教师台词: {request.speech[:300]}
{web_context}

请基于以上课程上下文回答学生的问题。回答要简洁、准确、有教育意义。"""

    history_str = "\n".join(
        f"{'学生' if m.get('role') == 'user' else '教师'}: {m.get('content', '')}"
        for m in request.history[-6:]
    )
    user_prompt = f"历史对话：\n{history_str}\n\n学生提问：{request.user_input}"

    async def event_generator():
        full_content = ""
        async for chunk in call_llm_stream(system_prompt, user_prompt):
            if chunk:
                full_content += chunk
                yield _sse_event_chat("chat_chunk", {"content": chunk})
        yield _sse_event_chat("chat_done", {"content": full_content})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/v2/course/discussion/stream")
async def course_discussion_stream(request: Request):
    """AI同学多智能体讨论流式API"""
    from state import CourseDiscussionRequest
    from app.services.teacher.discussion_roles import (
        get_discussion_roles_manager,
        build_discussion_prompt,
        get_all_participants,
    )

    try:
        body = await request.json()
        req = CourseDiscussionRequest(**body)
    except Exception as e:
        logger.error(f"Discussion request parse error: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)

    logger.info(f"Discussion stream started: course={req.course_id}")

    event_queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=2048)
    disconnected = asyncio.Event()

    async def push_event(event: dict):
        if not disconnected.is_set():
            await event_queue.put(event)

    async def run_discussion():
        try:
            await push_event({"type": "discussion_start", "message": "讨论开始"})

            # 使用预设的多角色系统
            roles_manager = get_discussion_roles_manager()

            # 生成讨论话题
            topic = req.slide_topic or req.slide_content[:200] if req.slide_content else "当前课程内容"
            user_input = req.user_message or f"关于「{topic}」，请各位AI同学发表看法"

            # 获取参与者列表
            # 如果前端传入了特定的agent_ids，使用课程中的agent；否则使用预设角色
            if req.agent_ids and len(req.agent_ids) > 0:
                # 使用课程中的agent（兼容旧逻辑）
                filepath = _get_course_path(req.course_id)
                if not os.path.exists(filepath):
                    await push_event({"type": "error", "message": "课程不存在"})
                    return

                with open(filepath, "r", encoding="utf-8") as f:
                    course_data = json.load(f)

                agent_team = course_data.get("agent_team", [])
                if not agent_team:
                    await push_event({"type": "error", "message": "没有可用的AI同学"})
                    return

                active_agents = [a for a in agent_team if a.get("id") in req.agent_ids]
                if not active_agents:
                    active_agents = agent_team

                # 构建agent的讨论提示词
                for agent in active_agents:
                    agent["system_prompt"] = agent.get("persona", f"你是{agent.get('name', 'AI')}，一个活泼的AI同学。")
                    agent["role"] = agent.get("role", "agent")
            else:
                # 使用预设的多角色系统（老师3人 + 学生随机3人）
                participants = get_all_participants()
                active_agents = [
                    {
                        "id": p.role_id,
                        "name": p.name,
                        "role": p.role_id,
                        "color": p.color,
                        "avatar_bg": p.avatar_bg,
                        "system_prompt": build_discussion_prompt(p, topic, req.slide_content or ""),
                    }
                    for p in participants
                ]

                logger.info(f"Using discussion roles: {[a['name'] for a in active_agents]}")

            # 第一阶段：各身份独立发言 (并发)
            tasks = []
            for agent in active_agents:
                task = asyncio.create_task(
                    asyncio.wait_for(
                        run_debate_agent_turn(
                            agent_id=agent.get("id", ""),
                            agent_name=agent.get("name", "AI同学"),
                            system_prompt=agent.get("system_prompt", f"你是{agent.get('name', 'AI')}，一个活泼的AI同学。"),
                            user_input=user_input,
                            context=req.slide_content or "",
                            round_num=1,
                            push_event=push_event,
                            agent_color=agent.get("color", "#6366f1")
                        ),
                        timeout=DEBATE_TIMEOUT_FIRST_ROUND
                    )
                )
                tasks.append((agent.get("id", ""), task))

            agent_responses = {}
            for agent_id, task in tasks:
                try:
                    result = await task
                    agent_responses[agent_id] = result
                except Exception as e:
                    logger.error(f"Agent {agent_id} failed: {e}")

            await push_event({
                "type": "discussion_round_complete",
                "round": 1,
                "message": "第一轮发言完成"
            })

            # 第二阶段：交叉评论
            cross_comments = {}
            if len(agent_responses) > 1:
                comment_tasks = []
                for agent in active_agents:
                    if agent.get("id") not in agent_responses:
                        continue
                    other_responses = {
                        aid: resp for aid, resp in agent_responses.items()
                        if aid != agent.get("id")
                    }
                    if not other_responses:
                        continue

                    task = asyncio.create_task(
                        asyncio.wait_for(
                            run_debate_cross_comment(
                                agent_id=agent.get("id", ""),
                                agent_name=agent.get("name", "AI同学"),
                                user_input=user_input,
                                other_responses=other_responses,
                                push_event=push_event
                            ),
                            timeout=DEBATE_TIMEOUT_COMMENT
                        )
                    )
                    comment_tasks.append((agent.get("id", ""), task))

                for agent_id, task in comment_tasks:
                    try:
                        result = await task
                        cross_comments[agent_id] = result
                    except Exception as e:
                        logger.error(f"Comment {agent_id} failed: {e}")

            # 第三阶段：裁判总结
            final_answer = await asyncio.wait_for(
                run_judge_synthesis(
                    user_input=user_input,
                    agent_responses=agent_responses,
                    cross_comments=cross_comments,
                    push_event=push_event
                ),
                timeout=DEBATE_TIMEOUT_JUDGE
            )

            await push_event({
                "type": "discussion_complete",
                "final_answer": final_answer,
                "agent_responses": agent_responses
            })

        except Exception as e:
            logger.error(f"Discussion workflow error: {e}", exc_info=True)
            await push_event({"type": "error", "message": str(e)})
        finally:
            await event_queue.put(None)

    task = asyncio.create_task(run_discussion())

    async def event_generator():
        try:
            while not disconnected.is_set():
                if await request.is_disconnected():
                    disconnected.set()
                    break

                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    break

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info(f"Discussion stream closed: course={req.course_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 媒体生成 API (OpenMAIC风格)
# ============================================================


@app.post("/api/v2/generate/image")
async def generate_image_api(request: GenerateImageRequest):
    """调用 MiniMax image-01 生成图片"""
    from media_generation import generate_image
    try:
        url = await generate_image(request.prompt, request.aspect_ratio)
        return GenerateImageResponse(url=url)
    except Exception as e:
        return GenerateImageResponse(success=False, error=str(e))


@app.post("/api/v2/generate/tts")
async def generate_tts_api(request: GenerateTTSRequest):
    """调用 MiniMax speech-02 TTS 生成语音，保存为MP3文件"""
    from media_generation import generate_tts
    import uuid
    try:
        audio_bytes = await generate_tts(request.text, request.voice_id, request.speed)

        audio_dir = os.path.join(STORAGE_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        filename = f"tts_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(audio_dir, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        url = f"/storage/audio/{filename}"
        return GenerateTTSResponse(url=url)
    except Exception as e:
        return GenerateTTSResponse(success=False, error=str(e))


# Serve generated audio files
@app.get("/storage/audio/{filename}")
async def serve_audio(filename: str):
    filepath = os.path.join(STORAGE_DIR, "audio", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(filepath, media_type="audio/mpeg")


# ============================================================
# 课程持久化 API (服务端存储)
# ============================================================


def _get_course_path(course_id: str) -> str:
    courses_dir = os.path.join(STORAGE_DIR, "courses")
    os.makedirs(courses_dir, exist_ok=True)
    return os.path.join(courses_dir, f"{course_id}.json")


@app.post("/api/v2/course/save")
async def save_course(request: CourseSaveRequest):
    """保存课程数据到服务端"""
    course = request.course_data
    # 兼容前端的 course_id / courseId 写法
    course_id = course.courseId or getattr(course, 'course_id', '') or ''
    if not course_id:
        course_id = f"course_{int(time.time())}_{os.urandom(4).hex()}"
        course.courseId = course_id

    if request.student_id:
        course.metadata["student_id"] = request.student_id
    filepath = _get_course_path(course_id)

    # 保存到JSON文件
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(course.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    # 同步到数据库
    user_id = 0
    if request.student_id:
        try:
            user_id = int(request.student_id)
        except ValueError:
            print(f"警告: student_id '{request.student_id}' 不是有效数字，无法保存到数据库课堂记录")

    if course_id:
        try:
            full_data = json.dumps(course.model_dump(mode="json"), ensure_ascii=False)
            ppt_pages = request.ppt_pages if request.ppt_pages else (
                len(course.slides_v2) if course.slides_v2 else (
                    len(course.slides) if course.slides else 0
                )
            )
            save_classroom_record(user_id, course_id, course.title, full_data, ppt_pages)
        except Exception as e:
            print(f"数据库保存失败（非致命）: {e}")

    return {"success": True, "course_id": course_id}


@app.get("/api/v2/course/{course_id}")
async def get_course(course_id: str):
    """获取指定课程"""
    filepath = _get_course_path(course_id)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Course not found")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/v2/course/{course_id}/slides/pending")
async def get_pending_slides(course_id: str):
    """获取课程待生成的幻灯片（用于后台增量生成）"""
    status = get_course_generation_status(course_id)
    if not status:
        # 如果数据库中没有记录，说明生成状态尚未保存或已清理，返回 is_complete=False 让前端继续轮询
        # 同时检查本地存储中是否有该课程的文件作为后备判断
        courses_dir = os.path.join(STORAGE_DIR, "courses")
        course_file = os.path.join(courses_dir, f"{course_id}.json")
        has_local_file = os.path.exists(course_file)
        return {
            "pending_slides": [],
            "pending_slides_v2": [],
            "pending_quiz_data": [],
            "pending_exercise_data": [],
            "generated_count": 0,
            "total_outlines": 0,
            "is_complete": has_local_file  # 只有本地文件存在时才认为已完成
        }
    return {
        "pending_slides": [],
        "pending_slides_v2": status.get("pending_slides_v2", []),
        "pending_quiz_data": status.get("pending_quiz_data", []),
        "pending_exercise_data": status.get("pending_exercise_data", []),
        "generated_count": status.get("generated_count", 0),
        "total_outlines": status.get("total_outlines", 0),
        "is_complete": status.get("is_complete", False)
    }


@app.post("/api/v2/course/{course_id}/slides/consume")
async def consume_pending_slides(course_id: str, request: Request):
    """前端消费 pending slides 后调用，清空已消费的 slides"""
    try:
        body = await request.json()
        consumed_slide_titles = body.get("consumed_slide_titles", [])
    except Exception:
        consumed_slide_titles = []

    status = get_course_generation_status(course_id)
    if not status:
        return {"success": True, "message": "No status found"}

    pending_v2 = status.get("pending_slides_v2", [])
    if consumed_slide_titles:
        # 根据 title 移除已消费的 slides
        new_pending_v2 = [s for s in pending_v2 if s.get("title") not in consumed_slide_titles]
    else:
        # 如果没有提供具体消费的 titles，清空全部 pending（前端已自行合并）
        new_pending_v2 = []

    try:
        update_course_generation_status(
            course_id=course_id,
            pending_slides_v2=new_pending_v2
        )
        return {"success": True, "removed_count": len(pending_v2) - len(new_pending_v2)}
    except Exception as e:
        logger.error(f"Failed to consume pending slides for {course_id}: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/v2/course/list/{student_id}")
async def list_courses(student_id: str):
    """列出学生的课程列表，按时间倒序"""
    courses_dir = os.path.join(STORAGE_DIR, "courses")
    courses = []
    if os.path.exists(courses_dir):
        for fname in sorted(os.listdir(courses_dir), reverse=True):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(courses_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("metadata", {})
                if meta.get("student_id") == student_id or not student_id:
                    courses.append(data)
            except Exception:
                continue
    return CourseListResponse(courses=courses)


@app.delete("/api/v2/course/{course_id}")
async def delete_course(course_id: str):
    """删除指定课程"""
    filepath = _get_course_path(course_id)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Course not found")
    os.remove(filepath)
    return {"success": True}


# ============================================================
# 新增: AI教师团队生成 API
# ============================================================

@app.post("/api/v2/course/generate/agent-team")
async def generate_agent_team(data: dict[str, Any] = {}):
    """生成AI教师团队（自动模式）"""
    from course_generator import get_course_generator
    from llm_stream import call_llm_async
    from prompts import build_prompt

    generator = get_course_generator()
    course_title = data.get("course_title", "")
    outlines = data.get("outlines", [])
    requirement = data.get("requirement", "")

    try:
        agent_team = await generator._generate_agent_team(
            course_title, outlines, requirement
        )
        return {"success": True, "agents": agent_team}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 新增: Quiz 评分 API
# ============================================================

@app.post("/api/v2/course/quiz/grade")
async def grade_quiz(data: dict[str, Any] = {}):
    """批改Quiz答案"""
    from course_generator import get_course_generator

    generator = get_course_generator()
    questions = data.get("questions", [])
    student_answers = data.get("student_answers", [])

    try:
        result = await generator.grade_quiz_answers(questions, student_answers)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 新增: 课程完成 API
# ============================================================

@app.post("/api/v2/course/complete")
async def complete_course(data: dict[str, Any] = {}):
    """课堂完成总结"""
    from course_generator import CourseGenerator
    from prompts import build_prompt

    course_id = data.get("course_id", "")
    quiz_score = data.get("quiz_score", 0)
    time_spent = data.get("time_spent", 0)
    scenes_visited = data.get("scenes_visited", [])
    total_scenes = data.get("total_scenes", 0)

    # 加载课程数据
    course_data = None
    filepath = _get_course_path(course_id)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            course_data = json.load(f)

    course_title = course_data.get("title", "课程") if course_data else "课程"
    outlines = course_data.get("outlines", []) if course_data else []

    try:
        # 使用规则生成 + LLM生成个性化总结
        badges: list[str] = []
        if quiz_score >= 90:
            badges.append("知识达人")
        if quiz_score >= 70:
            badges.append("学有所成")
        if len(scenes_visited) >= total_scenes:
            badges.append("全勤学霸")
        if time_spent > 1800:
            badges.append("专注之星")
        badges.append("课堂参与者")

        next_steps: list[str] = [
            "回顾课程重点内容，巩固所学知识",
            "尝试相关练习，提升实践能力",
            "探索更深层次的相关主题",
        ]

        summary_text = f"你完成了《{course_title}》的{len(scenes_visited)}个学习场景"

        # 尝试使用LLM生成更个性化的总结
        try:
            from llm_stream import call_llm_async
            outlines_summary = json.dumps(
                [{"title": o.get("title", ""), "type": o.get("type", "slide")}
                 for o in outlines[:5]],
                ensure_ascii=False,
            )
            prompt = build_prompt(
                "completion_summary",
                course_title=course_title,
                total_scenes=str(total_scenes),
                completed_scenes=str(len(scenes_visited)),
                quiz_score=str(quiz_score),
                time_spent=str(time_spent // 60),
                outlines_summary=outlines_summary,
            )
            llm_raw = await call_llm_async(
                "你是一位学习总结专家，严格按JSON格式输出。",
                prompt,
                temperature=0.5,
            )
            from course_generator import CourseGenerator
            llm_data = CourseGenerator._extract_json(llm_raw)
            if isinstance(llm_data, dict):
                if llm_data.get("summary"):
                    summary_text = llm_data["summary"]
                if llm_data.get("badges"):
                    badges = llm_data["badges"]
                if llm_data.get("next_steps"):
                    next_steps = llm_data["next_steps"]
        except Exception:
            pass

        return {
            "success": True,
            "total_scenes": total_scenes,
            "completed_scenes": len(scenes_visited),
            "quiz_score": quiz_score,
            "time_spent": time_spent,
            "badges": badges,
            "next_steps": next_steps,
            "summary": summary_text,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 新增: 视频生成 API
# ============================================================

@app.post("/api/v2/generate/video")
async def generate_video_endpoint(data: dict[str, Any] = {}):
    """视频生成（MiniMax video-01）"""
    from media_generation import generate_video

    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="缺少prompt参数")

    duration = data.get("duration", 5)
    resolution = data.get("resolution", "720p")

    try:
        video_url = await generate_video(
            prompt=prompt,
            duration=duration,
            resolution=resolution,
        )
        return {"success": True, "url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 新增: 所有课程列表 (首页课堂网格)
# ============================================================

@app.get("/api/v2/course/list/all")
async def list_all_courses():
    """列出所有课程（按时间倒序，最多返回20个）"""
    courses_dir = os.path.join(STORAGE_DIR, "courses")
    courses = []
    if os.path.exists(courses_dir):
        for fname in sorted(os.listdir(courses_dir), reverse=True)[:20]:
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(courses_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                courses.append(data)
            except Exception:
                continue
    return {"courses": courses}


# ============================================================
# 新增: 重命名课程
# ============================================================

@app.put("/api/v2/course/{course_id}/rename")
async def rename_course(course_id: str, data: dict[str, Any] = {}):
    """重命名课程"""
    filepath = _get_course_path(course_id)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Course not found")

    new_title = data.get("title", "")
    if not new_title:
        raise HTTPException(status_code=400, detail="缺少title参数")

    with open(filepath, "r", encoding="utf-8") as f:
        course = json.load(f)
    course["title"] = new_title
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(course, f, ensure_ascii=False, indent=2)

    return {"success": True, "course_id": course_id, "title": new_title}


# ============================================================
# V2.0 SSE 课堂流式端点（必须在 {course_id} 前注册，避免路径冲突）
# ============================================================

from app.core.sse import sse_event, sse_done, sse_heartbeat
from app.api.classroom import classroom_stream, StreamRequest


@app.post("/api/v2/classroom/stream")
async def v2_classroom_stream(req: StreamRequest):
    return await classroom_stream(req)


# ============================================================
# 课堂记录 CRUD API（数据库）
# ============================================================

@app.get("/api/v2/classroom/list/{user_id}")
async def get_classrooms(user_id: int):
    """获取指定学生的所有课堂记录列表"""
    records = get_classroom_records(user_id)
    return {"success": True, "records": records}


@app.get("/api/v2/classroom/{course_id}")
async def get_classroom(course_id: str):
    """获取单个课堂的完整数据"""
    record = get_classroom_record(course_id)
    if not record:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return {"success": True, "record": record}


@app.put("/api/v2/classroom/{course_id}")
async def update_classroom(course_id: str, data: dict[str, Any]):
    """更新课堂标题"""
    title = data.get("title", "")
    if not title:
        raise HTTPException(status_code=400, detail="缺少title参数")

    success = update_classroom_record(course_id, title)
    if not success:
        raise HTTPException(status_code=404, detail="Classroom not found")

    return {"success": True, "course_id": course_id, "title": title}


# ============================================================
# 沉浸式互动教学引擎 API
# ============================================================

@app.post("/api/run_code")
async def run_code(request: RunCodeRequest):
    """安全的代码执行接口（支持比对预期输出）"""
    if request.language == "python":
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(request.code)
                tmp_path = f.name
            try:
                result = subprocess.run(
                    ["python", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd="/tmp",
                    env={"PATH": "/usr/bin"}
                )
                actual = result.stdout.strip()
            except subprocess.TimeoutExpired:
                return RunCodeResponse(success=False, passed=False, error="执行超时（5秒）", actual_output="")
            finally:
                os.unlink(tmp_path)

            passed = actual == request.expected_output.strip() if request.expected_output else False
            return RunCodeResponse(
                success=True,
                passed=passed,
                actual_output=actual,
                error=result.stderr if result.stderr else ""
            )

        except Exception as e:
            return RunCodeResponse(success=False, passed=False, error=str(e), actual_output="")

    elif request.language in ("html", "javascript"):
        return RunCodeResponse(
            success=True,
            passed=False,
            actual_output="[前端语言请在浏览器运行]",
            error=""
        )

    else:
        return RunCodeResponse(success=False, passed=False, error=f"不支持的语言: {request.language}", actual_output="")


@app.post("/api/quiz/grade")
async def quiz_grade(request: QuizGradeRequest):
    """Quiz 安全评分接口（安全设计：答案仅在后端比对，不暴露给前端）

    前端发送: quiz_id, selected_key, question(题干), options(不含is_correct)
    后端返回: is_correct, explanation, correct_key（提交后）
    """
    correct_key = ""
    explanation = ""

    # 尝试从课程数据中查找正确答案（通过 quiz_id）
    # 注意：实际项目中需要根据 quiz_id 加载课程数据
    try:
        # 这里需要根据 quiz_id 查询课程数据获取正确答案
        # 暂时使用简化实现：如果 options 中有 is_correct 字段（容错）
        for opt in request.options:
            # 容错：如果 options 意外包含 is_correct
            if hasattr(opt, 'is_correct') and opt.is_correct:
                correct_key = opt.key
                explanation = request.question + "。" if request.question else ""
                break
    except Exception as e:
        logger.error(f"Quiz grade lookup error: {e}")

    # 比对结果
    is_correct = (request.selected_key == correct_key) if correct_key else False

    return QuizGradeResponse(
        is_correct=is_correct,
        explanation=explanation if is_correct else "答案错误，请再思考一下",
        correct_key=correct_key  # 提交后才返回正确答案
    )


class GradeBatchRequest(BaseModel):
    questions: list[dict[str, Any]]
    answers: dict[str, Any]
    quiz_id: str = ""


@app.post("/api/v2/grade/batch")
def grade_batch(request: GradeBatchRequest):
    """前端 classroom.js 调用的批量阅卷接口（支持选择+简答混合）。"""
    results = []
    total_score = 0
    total_points = 0

    for idx, q in enumerate(request.questions):
        q_type = q.get("type", "single")
        points = q.get("points", 10)
        total_points += points
        correct_answer = q.get("correct_answer", "")
        user_answer = request.answers.get(str(idx), "")

        if q_type in ("single", "multiple"):
            is_correct = str(user_answer).strip().upper() == str(correct_answer).strip().upper()
            score = points if is_correct else 0
        elif q_type == "short_answer":
            ua = str(user_answer).strip()
            ca = str(correct_answer).strip()
            if ua and len(ua) >= 10 and ca and len(ca) >= 5:
                keywords = [k.strip() for k in ca.split() if len(k.strip()) > 1]
                matched = sum(1 for k in keywords if k in ua)
                ratio = matched / len(keywords) if keywords else 0
                score = int(points * (0.6 + 0.4 * ratio))
            elif ua and len(ua) >= 5:
                score = int(points * 0.3)
            else:
                score = 0
            is_correct = score >= points * 0.6
        else:
            is_correct = False
            score = 0

        total_score += score
        results.append({
            "question_index": idx,
            "question_type": q_type,
            "is_correct": is_correct,
            "score": score,
            "max_score": points,
            "correct_answer": correct_answer,
            "user_answer": user_answer,
            "explanation": q.get("explanation", "") or ("回答正确！" if is_correct else "请再思考一下。"),
            "graded_by": "batch",
        })

    percentage = round(total_score / total_points * 100) if total_points > 0 else 0
    return {
        "results": results,
        "total_score": total_score,
        "total_points": total_points,
        "percentage": percentage,
        "passed": percentage >= 60,
    }


@app.delete("/api/v2/classroom/{course_id}")
async def delete_classroom(course_id: str):
    """删除课堂记录"""
    success = delete_classroom_record(course_id)

    # 同时删除JSON文件
    filepath = _get_course_path(course_id)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

    if not success:
        raise HTTPException(status_code=404, detail="Classroom not found")

    return {"success": True, "course_id": course_id}


if __name__ == "__main__":
    print("\n" + "="*50)
    print("星识 (Star-Learn) 伴学系统正在启动...")
    print("请直接在浏览器打开链接: http://localhost:8000/login.html")
    print("="*50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
