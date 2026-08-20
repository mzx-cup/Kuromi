# -*- coding: utf-8 -*-
"""Agent 编排控制塔 API - catalog / execute / status."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["agent-orchestration"])

from agents import AgentStepLog, create_default_controller
from app.schemas.agent_orchestration import PipelineRequest
from app.services.agent_log_adapter import agent_log_to_envelope
from app.services.portrait_aggregator import aggregate_portrait_snapshot
from state import LearningPortrait


# ---- profile_updated payload helpers (M1.1 / #7) ----

async def _load_user_portrait(student_id: str) -> LearningPortrait:
    """从 CapabilityRepository 加载学生真实画像 (失败时回退 LearningPortrait()).

    M1.1 / #7: 修复 line 103 传空 LearningPortrait() 导致 radar 全 0 的 bug.
    """
    if not student_id:
        return LearningPortrait()
    try:
        from app.core.repository_factory import get_repository_for_user
        from app.services.course_brainstorm import (
            _capability_to_learning_portrait,
            _portrait_to_learning_portrait,
        )
        repository = get_repository_for_user(student_id, repository_type="capability")
        profile = await repository.aggregate_profile(student_id)
        if isinstance(profile, dict) and profile:
            portrait_dict = _capability_to_learning_portrait(profile)
            portrait = _portrait_to_learning_portrait(portrait_dict)
            if portrait is not None:
                return portrait
    except Exception as exc:
        logging.warning(
            "_load_user_portrait failed for student_id=%s: %s; fallback to empty portrait.",
            student_id, exc,
        )
    return LearningPortrait()


def _build_profile_updated_payload(
    user_id: str, portrait: LearningPortrait
) -> dict[str, Any]:
    """构造 profile_updated SSE 事件载荷（避免传空 portrait）.

    与 aggregate_portrait_snapshot 输出的 radar/panel 一致, 前端 agent-sse-client
    按 radar 6 维渲染雷达图、按 panel 4 卡渲染画像卡.
    """
    snap = aggregate_portrait_snapshot(portrait)
    return {
        "user_id": user_id,
        "radar": snap["radar"],
        "panel": snap["panel"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/agents/catalog")
async def get_catalog():
    """返回 agent 目录与流水线定义（前端拿来渲染 flow-nodes）."""
    from agents import (
        ProfilerAgent, PlannerAgent, DocumentGeneratorAgent,
        MindmapGeneratorAgent, ExerciseGeneratorAgent, VideoContentAgent,
        ResourcePushAgent, EvaluationAgent, EchoAgent,
    )
    agents = [
        {"id": "echo", "name": "问候", "role": "回声智能体",
         "tools": ["登录问候"], "stage": "pre",
         "class": EchoAgent.__name__},
        {"id": "profiler", "name": "画像构建", "role": "画像分析智能体",
         "tools": ["6 维画像更新", "情绪识别", "盲区检测", "认知超载干预"],
         "memory_keys": ["student_profile", "blind_spots", "telemetry_data"],
         "stage": "main",
         "class": ProfilerAgent.__name__},
        {"id": "planner", "name": "路径规划", "role": "路径规划智能体",
         "tools": ["知识图谱", "内容类型路由", "难度梯度"], "stage": "main",
         "class": PlannerAgent.__name__},
        {"id": "document_generator", "name": "文档生成", "role": "文档生成智能体",
         "tools": ["Markdown 渲染", "章节拆分", "插图占位"], "stage": "parallel",
         "class": DocumentGeneratorAgent.__name__},
        {"id": "exercise_generator", "name": "题库生成", "role": "习题生成智能体",
         "tools": ["题目模板", "难度档位", "答案解析"], "stage": "parallel",
         "class": ExerciseGeneratorAgent.__name__},
        {"id": "mindmap_generator", "name": "导图生成", "role": "思维导图智能体",
         "tools": ["概念抽取", "层级归并", "SVG 渲染"], "stage": "parallel",
         "class": MindmapGeneratorAgent.__name__},
        {"id": "video_content", "name": "视频内容", "role": "视频内容智能体",
         "tools": ["B 站检索", "片段切片", "字幕校对"], "stage": "parallel",
         "class": VideoContentAgent.__name__},
        {"id": "resource_push", "name": "资源推送", "role": "资源推送智能体",
         "tools": ["用户偏好匹配", "推送时机", "去重"], "stage": "post",
         "class": ResourcePushAgent.__name__},
        {"id": "evaluator", "name": "评估", "role": "评估智能体",
         "tools": ["行为打分", "掌握度更新"], "stage": "post",
         "class": EvaluationAgent.__name__},
    ]
    pipeline = [
        {"stage": "pre", "agents": ["echo"]},
        {"stage": "main", "agents": ["profiler", "planner"]},
        {"stage": "parallel", "agents": [
            "document_generator", "exercise_generator",
            "mindmap_generator", "video_content",
        ], "max_concurrent": 4},
        {"stage": "post", "agents": ["resource_push", "evaluator"]},
    ]
    return {"agents": agents, "pipeline": pipeline}


# ---- Status (in-memory trace state) ----

_PIPELINE_STATUS: dict[str, dict] = {}


# ---- Execute (SSE) ----

def _sse_format(event: str, data: dict[str, Any]) -> str:
    """Serialize event to SSE wire format."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


# 与 main.py 聊天流的 _AGENT_DISPLAY 保持一致:
# 前端 (index.js TOWER_PRODUCT_DISPLAY / product_ready 订阅) 按这些字段渲染产物卡片
_AGENT_DISPLAY = {
    "document_generator": ("📄", "文档生成", "document"),
    "mindmap_generator": ("🧠", "导图生成", "mindmap"),
    "exercise_generator": ("✏️", "题库生成", "exercise"),
    "video_content": ("🎬", "视频推荐", "video"),
}


@router.post("/api/agents/execute")
async def execute_pipeline(req: PipelineRequest, request: Request):
    """启动流水线，返回 SSE 流（前端 agent-sse-client 订阅）."""
    trace_id = req.trace_id or str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    # 预加载学生真实画像（避免 line 103 传空 LearningPortrait() 导致 radar 全 0）
    real_portrait: LearningPortrait = await _load_user_portrait(req.student_id)

    async def on_step(log: AgentStepLog) -> None:
        env = agent_log_to_envelope(log, trace_id=trace_id)
        await queue.put(("agent_step", env))
        # 关键节点（画像/评估/规划）追加 profile_updated 事件
        if log.agent_role in ("画像分析", "评估", "路径规划"):
            # 注: 使用闭包捕获的 real_portrait（已从 CapabilityRepository 预加载）,
            # 不再传空 LearningPortrait(), radar/panel 反映真实画像数据.
            payload = _build_profile_updated_payload(req.student_id, real_portrait)
            payload["trace_id"] = trace_id  # 保持与 SSE envelope 一致
            await queue.put(("profile_updated", payload))

    async def on_product(agent_name: str, payload: dict[str, Any]) -> None:
        """generator 产物实时推送: 单独启动控制塔时, 产物同样要冒泡到聊天框.

        MasterController.execute 并行跑 4 个 generator, 谁先完成谁先回调,
        前端 runBackendPipeline 把 product_ready 路由到 agentBus -> 聊天框.
        """
        icon, label, content_type = _AGENT_DISPLAY.get(
            agent_name, ("✨", agent_name, "text")
        )
        await queue.put(("product_ready", {
            "agent_id": agent_name,
            "agent_label": label,
            "agent_icon": icon,
            "content_type": content_type,
            "payload": payload,
            "ts": int(time.time() * 1000),
            "trace_id": trace_id,
        }))

    async def event_gen():
        yield _sse_format("heartbeat", {
            "trace_id": trace_id, "ts": int(time.time() * 1000),
        })
        # B3: emit memory_card once at stream start (cross-layer context
        # snapshot the Socratic agent uses). Failures degrade gracefully —
        # the rest of the pipeline runs without a card.
        try:
            from app.services.agent.memory_card_loader import MemoryCardLoader
            _card = MemoryCardLoader().load(
                agent_id="socratic", user_id=req.student_id,
            )
            yield _sse_format("memory_card", {
                "trace_id": trace_id,
                "token_count": getattr(_card, "token_count", 0),
                "partial_fields": getattr(_card, "partial_fields", []),
            })
        except Exception as _card_exc:
            logging.warning("SSE memory_card emit failed (%s); skipping.", _card_exc)
        controller = create_default_controller()
        cancel_state = {"cancelled": False}

        async def run_controller():
            # 注: StudentState 字段是 student_id (不是 user_id), profile 是 LearningProfile.
            from state import StudentState
            state = StudentState(student_id=req.student_id)
            started_at = int(time.time() * 1000)
            agents_run: list[str] = []  # TODO: append from on_step callback when populating per-agent timing
            try:
                await controller.execute(
                    state, on_step_complete=on_step, on_product=on_product,
                )
                # Note: agent_role / agent_name is recorded via on_step callback, but for
                # simplicity we just track that pipeline completed. Future tasks can extend
                # to capture per-agent timing.
            except Exception as e:
                if not cancel_state["cancelled"]:
                    await queue.put(("error", {
                        "message": str(e), "agent": "controller",
                    }))
            finally:
                if not cancel_state["cancelled"]:
                    completed_at = int(time.time() * 1000)
                    _PIPELINE_STATUS[trace_id] = {
                        "trace_id": trace_id,
                        "status": "complete",
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "agents": agents_run,
                        "assets": [],
                    }
                    await queue.put(("pipeline_complete", {
                        "trace_id": trace_id, "status": "complete", "assets": [],
                    }))
                await queue.put(None)  # sentinel always emitted so stream terminates

        runner = asyncio.create_task(run_controller())
        try:
            while True:
                if await request.is_disconnected():
                    cancel_state["cancelled"] = True
                    runner.cancel()
                    break
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield _sse_format(event, data)
        finally:
            if not runner.done():
                cancel_state["cancelled"] = True
                runner.cancel()

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


# ---- Status (read-only lookup) ----

@router.get("/api/agents/status/{trace_id}")
async def get_status(trace_id: str):
    """查询某次流水线的执行状态（前端轮询或断线后回查）."""
    info = _PIPELINE_STATUS.get(trace_id)
    if not info:
        raise HTTPException(status_code=404, detail="trace not found")
    return info
