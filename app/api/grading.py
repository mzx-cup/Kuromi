# -*- coding: utf-8 -*-
"""
智能评分 API 端点

POST /api/v2/grade  — 评分并持久化到 MySQL quiz_records 表
POST /api/v2/grade/evaluate — 仅评分（不持久化），用于实时课堂反馈

对应 OpenMAIC app/api/quiz-grade/route.ts
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.teacher.grading import Grader, GradeResult, get_grader

logger = logging.getLogger("starlearn.api.grading")

router = APIRouter(prefix="/grade", tags=["grading"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class GradeRequest(BaseModel):
    """评分请求"""
    question: str = Field(..., description="题目内容")
    standard_answer: str = Field(default="", description="标准答案（简答题）")
    user_answer: str = Field(..., description="学生答案")
    question_type: str = Field(default="short_answer", description="题型: short_answer | choice")
    total_points: float = Field(default=10.0, description="满分值")
    key_points: list[str] = Field(default_factory=list, description="评分要点（简答题用）")
    options: list[str] = Field(default_factory=list, description="选项列表（选择题用）")
    correct_option: str = Field(default="", description="正确选项（选择题用）")

    # 用于持久化
    student_id: str = Field(default="", description="学生ID")
    classroom_id: str = Field(default="", description="课堂ID")
    quiz_id: str = Field(default="", description="测验ID")
    persist: bool = Field(default=True, description="是否持久化到数据库")


class GradeResponse(BaseModel):
    """评分响应"""
    is_correct: bool
    score: float
    total_points: float
    feedback: str
    correct_answer: str = ""
    key_points_hit: list[str] = Field(default_factory=list)
    key_points_missed: list[str] = Field(default_factory=list)
    saved: bool = False  # 是否已持久化


# =============================================================================
# API 端点
# =============================================================================

@router.post("", response_model=GradeResponse)
async def grade_and_save(req: GradeRequest):
    """
    评分并持久化到 MySQL quiz_records 表。

    适用于：课堂测验提交、作业批改等需要记录的评分场景。
    """
    return await _do_grade(req, persist=req.persist)


@router.post("/evaluate", response_model=GradeResponse)
async def grade_only(req: GradeRequest):
    """
    仅评分不持久化。适用于：实时课堂互动中的即时反馈。
    """
    return await _do_grade(req, persist=False)


# =============================================================================
# 核心逻辑
# =============================================================================

async def _do_grade(req: GradeRequest, persist: bool = True) -> GradeResponse:
    grader = get_grader()

    try:
        result: GradeResult = await grader.grade(
            question=req.question,
            standard_answer=req.standard_answer,
            user_answer=req.user_answer,
            question_type=req.question_type,
            total_points=req.total_points,
            key_points=req.key_points,
            options=req.options,
            correct_option=req.correct_option,
        )
    except Exception as e:
        logger.error("Grading failed: %s", e)
        raise HTTPException(status_code=500, detail=f"评分失败: {e}")

    resp = GradeResponse(
        is_correct=result.is_correct,
        score=result.score,
        total_points=result.total_points,
        feedback=result.feedback,
        correct_answer=result.correct_answer,
        key_points_hit=result.key_points_hit,
        key_points_missed=result.key_points_missed,
    )

    # 持久化
    if persist and req.student_id:
        try:
            await _save_to_db(req, result)
            resp.saved = True
            logger.info(
                "Quiz result saved: student=%s, quiz=%s, score=%.1f/%.1f, correct=%s",
                req.student_id, req.quiz_id, result.score, result.total_points, result.is_correct,
            )
        except Exception as e:
            logger.error("Failed to persist quiz result: %s", e)
            # 持久化失败不影响评分返回
            resp.saved = False

    return resp


async def _save_to_db(req: GradeRequest, result: GradeResult):
    """将评分结果写入 MySQL quiz_records 表"""
    quiz_id = req.quiz_id or f"quiz_{uuid.uuid4().hex[:12]}"

    try:
        # 尝试使用 SQLAlchemy async ORM
        from app.core.database import get_sessionmaker
        from app.models.classroom import QuizRecord

        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            record = QuizRecord(
                classroom_id=req.classroom_id or "",
                student_id=req.student_id,
                quiz_id=quiz_id,
                score=result.score,
                total=int(result.total_points),
                passed=result.is_correct,
                answers={
                    "user_answer": req.user_answer,
                    "question": req.question,
                    "question_type": req.question_type,
                },
                feedback={
                    "text": result.feedback,
                    "correct_answer": result.correct_answer,
                    "key_points_hit": result.key_points_hit,
                    "key_points_missed": result.key_points_missed,
                },
            )
            session.add(record)
            await session.commit()
    except Exception as e:
        # 如果 async ORM 不可用，回退到 db.py 的同步方式
        logger.warning("Async ORM save failed, falling back to db.py: %s", e)
        try:
            import json
            from db import get_db

            with get_db() as db:
                db.execute(
                    """INSERT INTO quiz_records
                       (classroom_id, student_id, quiz_id, score, total, passed, answers, feedback, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        req.classroom_id or "",
                        req.student_id,
                        quiz_id,
                        result.score,
                        int(result.total_points),
                        result.is_correct,
                        json.dumps({
                            "user_answer": req.user_answer,
                            "question": req.question,
                            "question_type": req.question_type,
                        }, ensure_ascii=False),
                        json.dumps({
                            "text": result.feedback,
                            "correct_answer": result.correct_answer,
                            "key_points_hit": result.key_points_hit,
                            "key_points_missed": result.key_points_missed,
                        }, ensure_ascii=False),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
        except Exception as e2:
            logger.error("DB fallback also failed: %s", e2)
            raise


# =============================================================================
# 旧的 quiz_grade 端点增强 — 在 main.py 中通过 monkeypatch 注入
# =============================================================================

async def enhanced_grade_quiz(questions: list[dict], student_answers: list[dict]) -> dict:
    """
    增强版批量评分函数，供 main.py 中 /api/v2/course/quiz/grade 使用。

    与旧版 course_generator.grade_quiz_answers() 接口兼容，
    但使用新的 Grader 引擎，返回更丰富的反馈。
    """
    grader = get_grader()
    results = []

    for i, (q, a) in enumerate(zip(questions, student_answers)):
        q_type = q.get("type", "short_answer")
        total = float(q.get("points", 10))

        try:
            result = await grader.grade(
                question=q.get("question", q.get("title", "")),
                standard_answer=q.get("answer", q.get("standard_answer", "")),
                user_answer=a.get("answer", a.get("selected_key", "")),
                question_type="choice" if q_type in ("choice", "quiz") else "short_answer",
                total_points=total,
                key_points=q.get("key_points", []),
                options=[f"{opt.get('key','')}. {opt.get('text','')}" for opt in q.get("options", [])],
                correct_option=q.get("correct_key", q.get("answer", "")),
            )
        except Exception:
            result = GradeResult(
                is_correct=False, score=0, total_points=total,
                feedback="评分出错，请重试",
            )

        results.append({
            "quiz_id": q.get("quiz_id", q.get("id", "")),
            "is_correct": result.is_correct,
            "score": result.score,
            "total": result.total_points,
            "feedback": result.feedback,
            "key_points_hit": result.key_points_hit,
            "key_points_missed": result.key_points_missed,
        })

    total_score = sum(r["score"] for r in results)
    total_possible = sum(r["total"] for r in results)

    return {
        "results": results,
        "total_score": total_score,
        "total_possible": total_possible,
        "pass_rate": (total_score / total_possible * 100) if total_possible > 0 else 0,
        "graded_count": len(results),
    }
