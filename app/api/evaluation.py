# -*- coding: utf-8 -*-
"""
评估指标(Evaluation) API

POST /api/evaluation/update           — 增量更新单个/多个指标
GET  /api/evaluation/{user_id}        — 获取用户当前评估指标
GET  /api/evaluation/history/{user_id} — 获取日线历史
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.repository_factory import get_repository_for_user

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class UpdateEvaluationRequest(BaseModel):
    userId: str | int  # 接受 string demo id 与 int 都行
    interactionCount: int | None = None
    socraticPassRate: float | None = None
    difficultyLevel: str | None = None
    codePracticeTime: int | None = None
    focusTimeToday: int | None = None
    flashcardsStudied: int | None = None
    streakDays: int | None = None
    evalJson: dict | None = None


def _coerce_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def _coerce_int(v, default=0):
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


@router.post("/update")
def update_evaluation(request: UpdateEvaluationRequest):
    """增量更新用户评估指标（按日期聚合）"""
    try:
        user_id = request.userId
        repository = get_repository_for_user(
            str(user_id), repository_type="learning"
        )

        # 获取今日已有记录（用于 eval_json 合并）
        today = date.today().isoformat()
        existing = repository.get_user_evaluation(user_id, record_date=today) or {}

        # 构建要保存的 evaluation_data 字典（只包含非 None 字段 + eval_json 合并）
        evaluation_data: dict[str, Any] = {}
        if request.interactionCount is not None:
            evaluation_data["interactionCount"] = request.interactionCount
        if request.socraticPassRate is not None:
            evaluation_data["socraticPassRate"] = request.socraticPassRate
        if request.difficultyLevel is not None:
            evaluation_data["difficultyLevel"] = request.difficultyLevel
        if request.codePracticeTime is not None:
            evaluation_data["codePracticeTime"] = request.codePracticeTime
        if request.focusTimeToday is not None:
            evaluation_data["focusTimeToday"] = request.focusTimeToday
        if request.flashcardsStudied is not None:
            evaluation_data["flashcardsStudied"] = request.flashcardsStudied
        if request.streakDays is not None:
            evaluation_data["streakDays"] = request.streakDays

        # eval_json 合并：将前端传入的 evalJson 与现有 eval_json 合并
        eval_json = dict(request.evalJson) if request.evalJson else {}
        if existing and existing.get("eval_json"):
            try:
                prev = (
                    json.loads(existing["eval_json"])
                    if isinstance(existing["eval_json"], str)
                    else existing["eval_json"]
                )
                if isinstance(prev, dict):
                    prev.update(eval_json)
                    eval_json = prev
            except Exception:
                pass
        if eval_json:
            evaluation_data.update(eval_json)

        # 保存到 user_evaluations（按日期聚合，增量合并）
        repository.save_user_evaluation(user_id, evaluation_data)

        # 同时更新 learning_records 作为实时快照（fallback 查询用）
        lr = repository.get_learning_record(user_id) or {}
        # 解析 learning_records 中已有的 profile_json
        lr_profile = {}
        if lr.get("profile_json"):
            try:
                lr_profile = json.loads(lr["profile_json"]) if isinstance(lr["profile_json"], str) else lr["profile_json"]
            except Exception:
                lr_profile = {}
        repository.save_learning_record(
            user_id,
            {
                "interaction_count": evaluation_data.get(
                    "interactionCount", _coerce_int(lr.get("interaction_count"))
                ),
                "code_practice_time": evaluation_data.get(
                    "codePracticeTime", _coerce_int(lr.get("code_practice_time"))
                ),
                "socratic_pass_rate": evaluation_data.get(
                    "socraticPassRate", _coerce_float(lr.get("socratic_pass_rate"))
                ),
                "difficulty_level": evaluation_data.get(
                    "difficultyLevel", lr.get("difficulty_level") or "basic"
                ),
                "profile_json": {
                    "focus_time_today": evaluation_data.get(
                        "focusTimeToday",
                        _coerce_int(lr_profile.get("focus_time_today")),
                    ),
                    "flashcards_studied": evaluation_data.get(
                        "flashcardsStudied",
                        _coerce_int(lr_profile.get("flashcards_studied")),
                    ),
                    "streak_days": evaluation_data.get(
                        "streakDays", _coerce_int(lr_profile.get("streak_days"))
                    ),
                },
            },
        )

        return {"success": True, "message": "评估指标更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新评估指标失败: {e}")


@router.get("/{user_id}")
def get_evaluation(user_id: str):
    """获取用户当前评估指标（合并今日 user_evaluations + learning_records）"""
    try:
        repository = get_repository_for_user(
            str(user_id), repository_type="learning"
        )
        today = date.today().isoformat()
        ev = repository.get_user_evaluation(user_id, record_date=today) or {}
        lr = repository.get_learning_record(user_id) or {}

        # 从 learning_records.profile_json 解析补充字段
        lr_profile = {}
        if lr.get("profile_json"):
            try:
                lr_profile = (
                    json.loads(lr["profile_json"])
                    if isinstance(lr["profile_json"], str)
                    else lr["profile_json"]
                )
            except Exception:
                lr_profile = {}

        # 从 user_evaluations.eval_json 解析补充字段
        ev_json = {}
        if ev.get("eval_json"):
            try:
                ev_json = (
                    json.loads(ev["eval_json"])
                    if isinstance(ev["eval_json"], str)
                    else ev["eval_json"]
                )
            except Exception:
                ev_json = {}

        # 合并优先级: user_evaluations > learning_records
        result = {
            "interactionCount": _coerce_int(
                ev.get("interaction_count") or lr.get("interaction_count")
            ),
            "socraticPassRate": _coerce_float(
                ev.get("socratic_pass_rate") or lr.get("socratic_pass_rate")
            ),
            "difficultyLevel": (
                ev.get("difficulty_level")
                or lr.get("difficulty_level")
                or "basic"
            ),
            "codePracticeTime": _coerce_int(
                ev.get("code_practice_time") or lr.get("code_practice_time")
            ),
            "focusTimeToday": _coerce_int(
                ev.get("focus_time_today") or lr_profile.get("focus_time_today")
            ),
            "flashcardsStudied": _coerce_int(
                ev.get("flashcards_studied") or lr_profile.get("flashcards_studied")
            ),
            "streakDays": _coerce_int(
                ev.get("streak_days") or lr_profile.get("streak_days")
            ),
            "lastStudyDate": ev_json.get("lastStudyDate") or lr_profile.get("lastStudyDate"),
            "interactionHistory": ev_json.get("interactionHistory") or lr_profile.get("interactionHistory"),
        }

        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取评估指标失败: {e}")


@router.get("/history/{user_id}")
def get_evaluation_history(user_id: str, days: int = 30):
    """获取用户最近 N 天的评估指标历史"""
    try:
        repository = get_repository_for_user(
            str(user_id), repository_type="learning"
        )
        history = repository.get_user_evaluation_history(user_id, days=days)
        return {"success": True, "count": len(history), "data": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取评估历史失败: {e}")
