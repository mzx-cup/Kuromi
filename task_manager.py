import asyncio
import json
import os
import re
import time
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

import db as database

if TYPE_CHECKING:
    from state import StudentState

logger = logging.getLogger("starlearn.task_manager")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SubTaskInfo(BaseModel):
    agent_name: str
    display_name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubTaskInfo":
        return cls.model_validate(data)


class AsyncTaskState(BaseModel):
    context_id: str
    student_id: str = ""
    overall_status: TaskStatus = TaskStatus.PENDING
    overall_progress: int = 0
    subtasks: dict[str, SubTaskInfo] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AsyncTaskState":
        return cls.model_validate(data)


RESOURCE_AGENTS = {
    "document_generator": "知识文档生成",
    "mindmap_generator": "思维导图生成",
    "exercise_generator": "实操练习生成",
    "video_content": "视频内容推荐",
}

MAX_RETRIES = 2
RETRY_DELAY = 1.0

TASK_STORAGE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "storage", "task_storage"
)


class TaskStateManager:
    def __init__(self) -> None:
        self._tasks: dict[str, AsyncTaskState] = {}
        self._lock = asyncio.Lock()
        os.makedirs(TASK_STORAGE_PATH, exist_ok=True)
        self._ensure_db_table()
        self._recover_from_db()

    def _ensure_db_table(self) -> None:
        with database.get_db() as conn:
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS async_task_state (
                            context_id VARCHAR(64) PRIMARY KEY,
                            student_id VARCHAR(64) DEFAULT '',
                            overall_status VARCHAR(20) DEFAULT 'pending',
                            overall_progress INT DEFAULT 0,
                            state_json TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """)
                    conn.commit()
                    cursor.close()
                    logger.info("async_task_state table ensured")
                except Exception as e:
                    logger.warning(f"Failed to create async_task_state table: {e}")

    def _recover_from_db(self) -> None:
        with database.get_db() as conn:
            if conn:
                try:
                    # ``db.py`` 不在模块顶层导入 pymysql(所有导入都在函数内),
                    # 所以 ``database.pymysql`` 永远是 ``AttributeError``.
                    # 而且 sqlite3 的 ``Connection.cursor()`` 不接受参数.
                    # 用 backend-aware cursor 选择 — 与 ``db._get_video_cursor``
                    # 保持一致.
                    if database._is_sqlite(conn):  # noqa: SLF001
                        cursor = conn.cursor()
                    else:
                        import pymysql  # 局部导入,与 db.py 其他位置一致
                        cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT context_id, state_json FROM async_task_state WHERE overall_status IN ('pending', 'running')"
                    )
                    rows = cursor.fetchall()
                    cursor.close()
                    # MySQL pymysql.DictCursor 返回 dict, sqlite3.Row 也支持
                    # 键访问 (row["col"]) — 统一当作 dict 即可.
                    for row in rows:
                        try:
                            state_data = json.loads(row["state_json"])
                            task_state = AsyncTaskState.from_dict(state_data)
                            if task_state.overall_status == TaskStatus.RUNNING:
                                task_state.overall_status = TaskStatus.PENDING
                                for st in task_state.subtasks.values():
                                    if st.status == TaskStatus.RUNNING:
                                        st.status = TaskStatus.PENDING
                                        st.progress = 0
                            self._tasks[row["context_id"]] = task_state
                            logger.info(f"Recovered task: {row['context_id']}")
                        except Exception as e:
                            logger.warning(f"Failed to recover task {row['context_id']}: {e}")
                except Exception as e:
                    logger.warning(f"DB recovery query failed: {e}")

        for fname in os.listdir(TASK_STORAGE_PATH):
            if fname.endswith(".json"):
                cid = fname[:-5]
                if cid not in self._tasks:
                    try:
                        with open(os.path.join(TASK_STORAGE_PATH, fname), "r", encoding="utf-8") as f:
                            state_data = json.load(f)
                        task_state = AsyncTaskState.from_dict(state_data)
                        if task_state.overall_status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                            self._tasks[cid] = task_state
                    except Exception:
                        pass

    async def create_task(self, context_id: str, student_id: str = "") -> AsyncTaskState:
        async with self._lock:
            subtasks = {}
            for agent_name, display_name in RESOURCE_AGENTS.items():
                subtasks[agent_name] = SubTaskInfo(
                    agent_name=agent_name,
                    display_name=display_name,
                )
            task = AsyncTaskState(
                context_id=context_id,
                student_id=student_id,
                overall_status=TaskStatus.PENDING,
                overall_progress=0,
                subtasks=subtasks,
            )
            self._tasks[context_id] = task
            self._persist(task)
            return task

    async def update_subtask(
        self,
        context_id: str,
        agent_name: str,
        status: TaskStatus | None = None,
        progress: int | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            task = self._tasks.get(context_id)
            if not task:
                return
            st = task.subtasks.get(agent_name)
            if not st:
                return
            if status is not None:
                st.status = status
            if progress is not None:
                st.progress = min(100, max(0, progress))
            if result is not None:
                st.result = result
            if error is not None:
                st.error = error
            if status == TaskStatus.RUNNING and st.started_at is None:
                st.started_at = time.time()
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                st.completed_at = time.time()
                st.progress = 100 if status == TaskStatus.COMPLETED else st.progress

            task.overall_progress = self._calc_overall_progress(task)
            task.overall_status = self._calc_overall_status(task)
            task.updated_at = time.time()
            self._persist(task)

    async def get_task(self, context_id: str) -> AsyncTaskState | None:
        async with self._lock:
            return self._tasks.get(context_id)

    async def get_task_status_response(self, context_id: str) -> dict[str, Any]:
        task = await self.get_task(context_id)
        if not task:
            return {"error": "Task not found", "context_id": context_id}

        subtask_list = []
        for agent_name, st in task.subtasks.items():
            entry: dict[str, Any] = {
                "agent": agent_name,
                "displayName": st.display_name,
                "status": st.status.value,
                "progress": st.progress,
            }
            if st.result is not None:
                entry["result"] = st.result
            if st.error is not None:
                entry["error"] = st.error
            if st.started_at is not None:
                elapsed = (st.completed_at or time.time()) - st.started_at
                entry["elapsedMs"] = int(elapsed * 1000)
            if st.retry_count > 0:
                entry["retryCount"] = st.retry_count
            subtask_list.append(entry)

        return {
            "contextId": task.context_id,
            "studentId": task.student_id,
            "overallStatus": task.overall_status.value,
            "overallProgress": task.overall_progress,
            "subtasks": subtask_list,
            "createdAt": datetime.fromtimestamp(task.created_at).isoformat(),
            "updatedAt": datetime.fromtimestamp(task.updated_at).isoformat(),
        }

    def _calc_overall_progress(self, task: AsyncTaskState) -> int:
        if not task.subtasks:
            return 0
        total = sum(st.progress for st in task.subtasks.values())
        return total // len(task.subtasks)

    def _calc_overall_status(self, task: AsyncTaskState) -> TaskStatus:
        statuses = [st.status for st in task.subtasks.values()]
        if all(s == TaskStatus.COMPLETED for s in statuses):
            return TaskStatus.COMPLETED
        if any(s == TaskStatus.FAILED for s in statuses):
            non_failed = [s for s in statuses if s != TaskStatus.FAILED]
            if all(s == TaskStatus.COMPLETED for s in non_failed):
                return TaskStatus.FAILED
            return TaskStatus.RUNNING
        if any(s == TaskStatus.RUNNING for s in statuses):
            return TaskStatus.RUNNING
        return TaskStatus.PENDING

    def _persist(self, task: AsyncTaskState) -> None:
        try:
            path = os.path.join(TASK_STORAGE_PATH, f"{task.context_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(task.to_dict(), f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"File persist failed for {task.context_id}: {e}")

        with database.get_db() as conn:
            if conn:
                try:
                    cursor = conn.cursor()
                    state_json = json.dumps(task.to_dict(), ensure_ascii=False)
                    cursor.execute(
                        """INSERT INTO async_task_state (context_id, student_id, overall_status, overall_progress, state_json)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                           student_id=%s, overall_status=%s, overall_progress=%s, state_json=%s""",
                        (
                            task.context_id, task.student_id, task.overall_status.value,
                            task.overall_progress, state_json,
                            task.student_id, task.overall_status.value,
                            task.overall_progress, state_json,
                        ),
                    )
                    conn.commit()
                    cursor.close()
                except Exception as e:
                    logger.warning(f"DB persist failed for {task.context_id}: {e}")

    async def increment_retry(self, context_id: str, agent_name: str) -> int:
        async with self._lock:
            task = self._tasks.get(context_id)
            if not task:
                return 0
            st = task.subtasks.get(agent_name)
            if not st:
                return 0
            st.retry_count += 1
            st.status = TaskStatus.PENDING
            st.progress = 0
            st.error = None
            task.updated_at = time.time()
            self._persist(task)
            return st.retry_count


_manager_instance: TaskStateManager | None = None


def get_task_manager() -> TaskStateManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = TaskStateManager()
    return _manager_instance


async def run_agent_with_retry(
    agent: Any,
    state: "StudentState",
    context_id: str,
    manager: TaskStateManager,
) -> "StudentState":
    from agents import BaseAgent

    agent_name = agent.name if isinstance(agent, BaseAgent) else str(agent)
    retry_count = 0

    while retry_count <= MAX_RETRIES:
        try:
            await manager.update_subtask(
                context_id, agent_name,
                status=TaskStatus.RUNNING, progress=25,
            )

            result_state = await agent.run(state)

            await manager.update_subtask(
                context_id, agent_name,
                status=TaskStatus.COMPLETED, progress=100,
            )

            output_key_map = {
                "document_generator": "document_output",
                "mindmap_generator": "mindmap_output",
                "exercise_generator": "exercise_output",
            }
            output_key = output_key_map.get(agent_name, f"{agent_name}_output")
            output_data = result_state.metadata.get(output_key)
            if output_data:
                await manager.update_subtask(
                    context_id, agent_name,
                    result=output_data if isinstance(output_data, dict) else {"data": output_data},
                )

            return result_state

        except Exception as e:
            retry_count += 1
            logger.error(
                f"Agent {agent_name} failed (attempt {retry_count}/{MAX_RETRIES + 1}): {e}",
                exc_info=True,
            )

            current_retries = await manager.increment_retry(context_id, agent_name)

            if current_retries > MAX_RETRIES:
                await manager.update_subtask(
                    context_id, agent_name,
                    status=TaskStatus.FAILED,
                    error=f"重试{MAX_RETRIES}次后仍失败: {str(e)}",
                )
                return state

            await asyncio.sleep(RETRY_DELAY * current_retries)

            await manager.update_subtask(
                context_id, agent_name,
                status=TaskStatus.PENDING, progress=0,
            )

    return state


async def _should_generate_resources(state: "StudentState") -> bool:
    """判断当前对话是否值得生成学习资源。"""
    messages = state.get_recent_messages(5)
    user_msgs = [m for m in messages if m.role.value == "student"]
    ai_msgs = [m for m in messages if m.role.value != "student"]

    if not user_msgs:
        return False

    user_question = user_msgs[-1].content
    ai_answer = ai_msgs[-1].content if ai_msgs else ""

    # 简单启发式过滤（无需 LLM，节省成本）
    trivial_patterns = [
        r"中午吃什么", r"晚上吃什么", r"你好", r"在吗", r"谢谢", r"再见",
        r"^(hi|hello|hey)\b", r"^\d+$",
        r"天气", r"时间", r"几点",
    ]
    for p in trivial_patterns:
        if re.search(p, user_question, re.I):
            return False

    # 长度过滤：用户问题太短（< 5 字）且 AI 回答也短（< 100 字）
    if len(user_question) < 5 and len(ai_answer) < 100:
        return False

    # 如果启发式无法确定，调用轻量级 LLM 判断
    try:
        from llm_stream import call_llm_async
        prompt = f"""判断以下对话是否涉及知识学习/技术讨论/教育内容。如果是闲聊、问候、生活琐事，回答"否"。只回答"是"或"否"。

用户问题：{user_question[:200]}
AI回答摘要：{ai_answer[:300]}"""
        result = await call_llm_async(
            "你是一个内容分类器，只回答'是'或'否'。",
            prompt,
            temperature=0.1,
        )
        return "是" in result or "yes" in result.lower()
    except Exception:
        return True  # 默认生成，宁可多不可少


async def dispatch_resource_tasks(
    state: "StudentState",
    context_id: str,
    controller: Any,
    on_product: "Optional[Any]" = None,   # async def cb(agent_name: str, payload: dict) -> None
) -> None:
    """在后台异步运行资源生成 (document / mindmap / exercise / video)。

    每个 generator 完成后, 调用 on_product 回调 (若提供), 用于实时把产物推给前端。
    4 个 generator 现在使用 asyncio.gather 并行, 谁先完成谁先回调, 体验上呈"逐个跳出"。
    """
    from agents import DocumentGeneratorAgent, MindmapGeneratorAgent, ExerciseGeneratorAgent, VideoContentAgent

    manager = get_task_manager()

    task = await manager.create_task(context_id, state.student_id)

    # 相关性判断：闲聊类问题不触发资源生成
    should_generate = await _should_generate_resources(state)
    if not should_generate:
        for agent_name in RESOURCE_AGENTS:
            await manager.update_subtask(
                context_id, agent_name,
                status=TaskStatus.SKIPPED, progress=100,
            )
        logger.info(f"Resource generation skipped for context {context_id} (trivial chat)")
        return

    agents_to_run = []
    for agent_name in RESOURCE_AGENTS:
        agent = controller._generator_agents.get(agent_name)
        if agent is None:
            if agent_name == "document_generator":
                agent = DocumentGeneratorAgent()
            elif agent_name == "mindmap_generator":
                agent = MindmapGeneratorAgent()
            elif agent_name == "exercise_generator":
                agent = ExerciseGeneratorAgent()
            elif agent_name == "video_content":
                agent = VideoContentAgent()
        agents_to_run.append(agent)

    # 初始状态: 全部标记为 RUNNING
    for agent in agents_to_run:
        await manager.update_subtask(
            context_id, agent.name,
            status=TaskStatus.RUNNING, progress=10,
        )

    async def run_all():
        # 输出键映射 (video_content 没有特殊映射, 用 _output 后缀)
        output_key_map = {
            "document_generator": "document_output",
            "mindmap_generator": "mindmap_output",
            "exercise_generator": "exercise_output",
            "video_content": "video_output",
        }

        async def _run_one(agent):
            try:
                result_state = await run_agent_with_retry(
                    agent, state, context_id, manager,
                )
                output_key = output_key_map.get(agent.name, f"{agent.name}_output")
                if output_key in result_state.metadata:
                    state.metadata[output_key] = result_state.metadata[output_key]
                    payload = state.metadata[output_key]
                    if on_product is not None:
                        try:
                            await on_product(agent.name, payload)
                        except Exception as cb_e:
                            logger.warning(f"[dispatch] on_product callback error for {agent.name}: {cb_e}")
            except Exception as e:
                logger.error(f"Resource task dispatch error for {agent.name}: {e}", exc_info=True)
                await manager.update_subtask(
                    context_id, agent.name,
                    status=TaskStatus.FAILED,
                    error=str(e),
                )

        # 并行跑 4 个 generator, 谁先完成谁先 emit product_ready
        await asyncio.gather(*(_run_one(a) for a in agents_to_run))

        try:
            resource_push = controller._agents.get("resource_push")
            if resource_push:
                await resource_push.run(state)
        except Exception as e:
            logger.error(f"ResourcePush failed: {e}")

        try:
            from agent_utils import save_state
            save_state(state)
        except Exception as e:
            logger.warning(f"Failed to save state after resource tasks: {e}")

    # 关键: 返回 task 而非 fire-and-forget
    # 调用方 (chat_stream_v2.run_workflow) 需要 await 这个 task,
    # 才能保证所有 generator 跑完、所有 product_ready 都入队后, 再关闭 SSE 流.
    return asyncio.create_task(run_all())
