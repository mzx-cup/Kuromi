# -*- coding: utf-8 -*-
"""Agent 编排控制塔 API - catalog / execute / status."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["agent-orchestration"])


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