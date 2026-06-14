# -*- coding: utf-8 -*-
"""Agent 编排控制塔 API - catalog / execute / status."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["agent-orchestration"])

from agents import AgentStepLog, create_default_controller
from app.schemas.agent_orchestration import PipelineRequest
from app.services.agent_log_adapter import agent_log_to_envelope
from app.services.portrait_aggregator import aggregate_portrait_snapshot
from state import LearningPortrait


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


# ---- Execute (SSE) ----

def _sse_format(event: str, data: dict[str, Any]) -> str:
    """Serialize event to SSE wire format."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/api/agents/execute")
async def execute_pipeline(req: PipelineRequest, request: Request):
    """启动流水线，返回 SSE 流（前端 agent-sse-client 订阅）."""
    trace_id = req.trace_id or str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    async def on_step(log: AgentStepLog) -> None:
        env = agent_log_to_envelope(log, trace_id=trace_id)
        await queue.put(("agent_step", env))
        # 关键节点（画像/评估/规划）追加 profile_updated 事件
        if log.agent_role in ("画像分析", "评估", "路径规划"):
            # 注: plan 用 StudentState + profile=LearningPortrait, 实际
            # StudentState.profile 是 LearningProfile(legacy), LearningPortrait 是独立模型.
            # aggregator v2 直接接受 LearningPortrait 参数 (Task 3 deviation).
            snap = aggregate_portrait_snapshot(LearningPortrait())
            await queue.put(("profile_updated", {
                "trace_id": trace_id,
                "radar": snap["radar"],
                "panel": snap["panel"],
            }))

    async def event_gen():
        yield _sse_format("heartbeat", {
            "trace_id": trace_id, "ts": int(time.time() * 1000),
        })
        controller = create_default_controller()

        async def run_controller():
            # 注: StudentState 字段是 student_id (不是 user_id), profile 是 LearningProfile.
            from state import StudentState
            state = StudentState(student_id=req.student_id)
            try:
                await controller.execute(state, on_step_complete=on_step)
            except Exception as e:
                await queue.put(("error", {
                    "message": str(e), "agent": "controller",
                }))
            finally:
                await queue.put(("pipeline_complete", {
                    "trace_id": trace_id, "status": "complete", "assets": [],
                }))
                await queue.put(None)  # sentinel

        runner = asyncio.create_task(run_controller())
        try:
            while True:
                if await request.is_disconnected():
                    runner.cancel()
                    break
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield _sse_format(event, data)
        finally:
            if not runner.done():
                runner.cancel()

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })