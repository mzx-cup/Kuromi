import asyncio
import json
import time
import logging
import heapq
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from enum import IntEnum

logger = logging.getLogger("starlearn.proactive")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)


class ProactiveMessageType(str):
    GREETING = "greeting"
    STRUGGLE_INTERVENTION = "struggle_intervention"
    REVIEW_REMINDER = "review_reminder"
    ACHIEVEMENT = "achievement"
    TIP = "tip"
    SYSTEM = "system"


class MessagePriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class ProactiveMessage(BaseModel):
    msg_type: str = ProactiveMessageType.SYSTEM
    priority: int = MessagePriority.NORMAL
    timestamp: float = Field(default_factory=time.time)
    msg_id: str = ""
    student_id: str = ""
    title: str = ""
    content: str = ""
    action_label: str = ""
    action_payload: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)

    def to_sse_data(self) -> str:
        return json.dumps({
            "envelope": {
                "type": "proactive",
                "msg_type": self.msg_type,
                "priority": self.priority,
                "timestamp": self.timestamp,
                "msg_id": self.msg_id,
                "student_id": self.student_id,
            },
            "payload": {
                "title": self.title,
                "content": self.content,
                "action_label": self.action_label,
                "action_payload": self.action_payload,
                "meta": self.meta,
            }
        }, ensure_ascii=False)


class StruggleEvent(BaseModel):
    user_id: str
    session_id: str = ""
    current_content_id: str = ""
    struggle_metrics: dict = Field(default_factory=dict)


class SSEConnection:
    def __init__(self, student_id: str, device_id: str, queue: asyncio.Queue):
        self.student_id = student_id
        self.device_id = device_id
        self.queue: asyncio.Queue = queue
        self.connected_at: float = time.time()
        self.last_active: float = time.time()
        self.last_msg_id: str = ""
        self._closed = False

    async def send(self, message: ProactiveMessage) -> bool:
        if self._closed:
            return False
        try:
            self.queue.put_nowait(message)
            self.last_active = time.time()
            self.last_msg_id = message.msg_id
            return True
        except asyncio.QueueFull:
            logger.warning(f"Queue full for {self.student_id}/{self.device_id}, dropping msg {message.msg_id}")
            return False

    def close(self):
        self._closed = True


class ConnectionManager:
    def __init__(self, max_connections: int = 1000, max_per_user: int = 5):
        self._connections: dict[str, dict[str, SSEConnection]] = {}
        self._msg_buffer: dict[str, list[ProactiveMessage]] = {}
        self._buffer_size = 50
        self._max_connections = max_connections
        self._max_per_user = max_per_user
        self._lock = asyncio.Lock()
        self._total_connections = 0
        self._rate_limiters: dict[str, list[float]] = {}
        self._rate_window = 60.0
        self._rate_max_messages = 20

    async def connect(self, student_id: str, device_id: str) -> asyncio.Queue:
        async with self._lock:
            if self._total_connections >= self._max_connections:
                raise ConnectionRefusedError("Max connections reached")
            user_devices = self._connections.setdefault(student_id, {})
            if len(user_devices) >= self._max_per_user:
                oldest_dev = min(user_devices.values(), key=lambda c: c.connected_at)
                await self.disconnect(student_id, oldest_dev.device_id)
            queue: asyncio.Queue = asyncio.Queue(maxsize=256)
            conn = SSEConnection(student_id, device_id, queue)
            user_devices[device_id] = conn
            self._total_connections += 1
            logger.info(f"SSE connected: {student_id}/{device_id} (total: {self._total_connections})")
            return queue

    async def disconnect(self, student_id: str, device_id: str):
        async with self._lock:
            user_devices = self._connections.get(student_id)
            if user_devices and device_id in user_devices:
                user_devices[device_id].close()
                del user_devices[device_id]
                self._total_connections -= 1
                if not user_devices:
                    del self._connections[student_id]
                logger.info(f"SSE disconnected: {student_id}/{device_id} (total: {self._total_connections})")

    async def disconnect_all(self, student_id: str):
        async with self._lock:
            user_devices = self._connections.pop(student_id, {})
            for conn in user_devices.values():
                conn.close()
                self._total_connections -= 1
            logger.info(f"SSE disconnected all devices for {student_id}")

    def get_connection(self, student_id: str, device_id: str) -> Optional[SSEConnection]:
        user_devices = self._connections.get(student_id)
        if user_devices:
            return user_devices.get(device_id)
        return None

    def get_user_connections(self, student_id: str) -> list[SSEConnection]:
        return list(self._connections.get(student_id, {}).values())

    async def push_to_user(self, student_id: str, message: ProactiveMessage) -> int:
        if not self._check_rate_limit(student_id):
            logger.warning(f"Rate limited for {student_id}")
            return 0
        self._buffer_message(student_id, message)
        conns = self.get_user_connections(student_id)
        delivered = 0
        for conn in conns:
            if await conn.send(message):
                delivered += 1
        if delivered > 0:
            logger.info(f"Pushed {message.msg_type} to {student_id} ({delivered} devices)")
        return delivered

    async def push_to_all(self, message: ProactiveMessage) -> int:
        total = 0
        for student_id in list(self._connections.keys()):
            total += await self.push_to_user(student_id, message)
        return total

    def _buffer_message(self, student_id: str, message: ProactiveMessage):
        if student_id not in self._msg_buffer:
            self._msg_buffer[student_id] = []
        buf = self._msg_buffer[student_id]
        buf.append(message)
        if len(buf) > self._buffer_size:
            buf.pop(0)

    def get_missed_messages(self, student_id: str, after_msg_id: str = "") -> list[ProactiveMessage]:
        buf = self._msg_buffer.get(student_id, [])
        if not after_msg_id:
            return buf[-10:]
        for i, msg in enumerate(buf):
            if msg.msg_id == after_msg_id:
                return buf[i + 1:]
        return buf[-10:]

    def _check_rate_limit(self, student_id: str) -> bool:
        now = time.time()
        if student_id not in self._rate_limiters:
            self._rate_limiters[student_id] = []
        timestamps = self._rate_limiters[student_id]
        cutoff = now - self._rate_window
        self._rate_limiters[student_id] = [t for t in timestamps if t > cutoff]
        if len(self._rate_limiters[student_id]) >= self._rate_max_messages:
            return False
        self._rate_limiters[student_id].append(now)
        return True

    def get_stats(self) -> dict:
        return {
            "total_connections": self._total_connections,
            "unique_users": len(self._connections),
            "max_connections": self._max_connections,
            "buffered_users": len(self._msg_buffer),
        }


_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


class ProactiveTutor:
    def __init__(self, manager: ConnectionManager):
        self._manager = manager
        self._msg_counter = 0

    def _next_msg_id(self) -> str:
        self._msg_counter += 1
        return f"proactive-{int(time.time())}-{self._msg_counter}"

    async def on_login(self, student_id: str, course_id: str = "bigdata"):
        logger.info(f"ProactiveTutor: on_login for {student_id}")
        stale_knowledge = await self._query_stale_knowledge(student_id, course_id)
        if stale_knowledge:
            topic = stale_knowledge[0]
            days = topic.get("days_since_review", 2)
            kp_name = topic.get("knowledge_point", "上次学习的内容")
            greeting = self._build_greeting(kp_name, days)
            msg = ProactiveMessage(
                msg_type=ProactiveMessageType.GREETING,
                priority=MessagePriority.HIGH,
                msg_id=self._next_msg_id(),
                student_id=student_id,
                title="学习提醒",
                content=greeting,
                action_label="开始快问快答",
                action_payload={"type": "socratic_quick", "knowledge_point": kp_name, "course_id": course_id},
                meta={"days_since_review": days, "knowledge_point": kp_name},
            )
            await self._manager.push_to_user(student_id, msg)
        else:
            hour = datetime.now().hour
            if hour < 12:
                period = "上午好"
            elif hour < 18:
                period = "下午好"
            else:
                period = "晚上好"
            msg = ProactiveMessage(
                msg_type=ProactiveMessageType.GREETING,
                priority=MessagePriority.LOW,
                msg_id=self._next_msg_id(),
                student_id=student_id,
                title="欢迎回来",
                content=f"{period}！准备好今天的学习了吗？",
                action_label="开始学习",
                action_payload={"type": "start_session", "course_id": course_id},
            )
            await self._manager.push_to_user(student_id, msg)

    async def on_struggle(self, event: StruggleEvent):
        logger.info(f"ProactiveTutor: struggle detected for {event.user_id} on {event.current_content_id}")
        intervention = await self._generate_struggle_intervention(event)
        msg = ProactiveMessage(
            msg_type=ProactiveMessageType.STRUGGLE_INTERVENTION,
            priority=MessagePriority.CRITICAL,
            msg_id=self._next_msg_id(),
            student_id=event.user_id,
            title="看起来遇到了困难",
            content=intervention,
            action_label="获取提示",
            action_payload={
                "type": "socratic_hint",
                "content_id": event.current_content_id,
                "session_id": event.session_id,
            },
            meta={"struggle_metrics": event.struggle_metrics, "content_id": event.current_content_id},
        )
        await self._manager.push_to_user(event.user_id, msg)

    async def on_review_reminder(self, student_id: str, knowledge_points: list[dict]):
        if not knowledge_points:
            return
        kp_names = ", ".join(kp.get("knowledge_point", "") for kp in knowledge_points[:3])
        msg = ProactiveMessage(
            msg_type=ProactiveMessageType.REVIEW_REMINDER,
            priority=MessagePriority.HIGH,
            msg_id=self._next_msg_id(),
            student_id=student_id,
            title="复习提醒",
            content=f"以下知识点需要复习：{kp_names}。定期复习能有效巩固记忆！",
            action_label="开始复习",
            action_payload={"type": "review_session", "knowledge_points": knowledge_points},
        )
        await self._manager.push_to_user(student_id, msg)

    def _build_greeting(self, knowledge_point: str, days: int) -> str:
        hour = datetime.now().hour
        if hour < 12:
            period = "上午好"
        elif hour < 18:
            period = "下午好"
        else:
            period = "晚上好"
        return f"{period}！距离上次学习「{knowledge_point}」已经过去{days}天了，要不要先花3分钟玩个快问快答热热身？"

    async def _query_stale_knowledge(self, student_id: str, course_id: str) -> list[dict]:
        stale = []
        try:
            from db import get_db
            with get_db() as conn:
                if conn is None:
                    return self._fallback_stale_query(student_id)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id, profile_json, created_at "
                    "FROM learning_records WHERE user_id = %s ORDER BY created_at ASC LIMIT 10",
                    (student_id,)
                )
                rows = cursor.fetchall()
                now = datetime.now()
                for row in rows:
                    last_reviewed = row[2]
                    profile_json = row[1] or "{}"
                    try:
                        profile = json.loads(profile_json) if isinstance(profile_json, str) else {}
                    except (json.JSONDecodeError, TypeError):
                        profile = {}
                    knowledge_points = profile.get("knowledge_mastery", {})
                    if last_reviewed:
                        if isinstance(last_reviewed, str):
                            last_reviewed = datetime.fromisoformat(last_reviewed.replace("Z", "+00:00").replace("+08:00", ""))
                        days_diff = (now - last_reviewed).days
                        if days_diff >= 2:
                            for kp_name, mastery in knowledge_points.items():
                                stale.append({
                                    "knowledge_point": kp_name,
                                    "mastery_level": mastery if isinstance(mastery, (int, float)) else 0,
                                    "days_since_review": days_diff,
                                })
                            if not knowledge_points:
                                stale.append({
                                    "knowledge_point": "上次学习的内容",
                                    "mastery_level": 0,
                                    "days_since_review": days_diff,
                                })
        except Exception as e:
            logger.warning(f"DB query failed for stale knowledge: {e}")
            stale = self._fallback_stale_query(student_id)
        return stale

    def _fallback_stale_query(self, student_id: str) -> list[dict]:
        import json as _json
        try:
            with open("local_storage.json", "r", encoding="utf-8") as f:
                data = _json.load(f)
            # local_storage.json 中 learning_records 是 list，每个元素含 user_id
            records = data.get("learning_records", [])
            if not isinstance(records, list):
                records = []
            now = datetime.now()
            stale = []
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                if str(rec.get("user_id", "")) != str(student_id):
                    continue
                lr = rec.get("last_reviewed_at", "")
                if lr:
                    try:
                        dt = datetime.fromisoformat(lr.replace("Z", "+00:00"))
                        days = (now - dt).days
                        if days >= 2:
                            stale.append({
                                "knowledge_point": rec.get("knowledge_point", "未知知识点"),
                                "days_since_review": days,
                                "mastery_level": rec.get("mastery_level", 0),
                            })
                    except (ValueError, TypeError):
                        pass
            return stale[:5]
        except (FileNotFoundError, _json.JSONDecodeError):
            return []

    async def _generate_struggle_intervention(self, event: StruggleEvent) -> str:
        content_id = event.current_content_id or "当前内容"
        metrics = event.struggle_metrics
        if metrics:
            idle_time = metrics.get("idle_seconds", 0)
            error_count = metrics.get("error_count", 0)
            if idle_time > 120:
                return f"我注意到你在「{content_id}」上停留了一段时间。要不要换个角度思考？试试把问题拆解成更小的步骤。"
            if error_count > 3:
                return f"在「{content_id}」上反复遇到问题是很正常的。让我用苏格拉底式提问引导你找到答案吧！"
        return f"看起来在「{content_id}」上遇到了一些困难。别担心，让我用几个问题帮你理清思路。"


_tutor: Optional[ProactiveTutor] = None


def get_proactive_tutor() -> ProactiveTutor:
    global _tutor
    if _tutor is None:
        _tutor = ProactiveTutor(get_connection_manager())
    return _tutor
