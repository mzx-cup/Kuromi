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


# =============================================================================
# 批量评分 API — Phase 2 新增
# =============================================================================

class BatchGradeQuestion(BaseModel):
    """批量评分请求中的单道题目"""
    question_index: int = Field(..., description="题目序号（0-based）")
    question: str = Field(..., description="题目内容")
    question_type: str = Field(default="single", description="single | multiple | short_answer")
    options: list[str] = Field(default_factory=list, description="选项列表")
    correct_answer: int = Field(default=0, description="单选题正确答案索引")
    correct_answers: list[int] = Field(default_factory=list, description="多选题正确答案索引")
    answer: str = Field(default="", description="简答题参考答案")
    comment_prompt: str = Field(default="", description="简答题评分标准")
    points: float = Field(default=10.0, description="分值")
    key_points: list[str] = Field(default_factory=list, description="简答题评分要点")


class BatchGradeAnswer(BaseModel):
    """批量评分请求中的单道答案"""
    question_index: int = Field(..., description="题目序号（0-based）")
    answer_value: str = Field(default="", description="单选题: '0'; 多选题: '0,2'; 简答题: 文本")
    answer_values: list[int] = Field(default_factory=list, description="多选题选中索引列表")


class BatchGradeRequest(BaseModel):
    """批量评分请求"""
    questions: list[BatchGradeQuestion] = Field(..., min_length=1)
    answers: list[BatchGradeAnswer] = Field(default_factory=list)
    quiz_id: str = Field(default="", description="测验ID（可选，用于记录）")


class BatchGradeItem(BaseModel):
    """单题评分结果"""
    question_index: int
    is_correct: bool
    score: float
    total_points: float
    feedback: str = ""
    correct_answer: str = ""  # 简答题参考答案 / 选择题正确选项
    key_points_hit: list[str] = Field(default_factory=list)
    key_points_missed: list[str] = Field(default_factory=list)
    graded_by: str = "local"  # local | llm


class BatchGradeResponse(BaseModel):
    """批量评分响应"""
    results: list[BatchGradeItem]
    total_score: float
    total_points: float
    percentage: float
    passed: bool
    graded_count: int


@router.post("/batch", response_model=BatchGradeResponse)
async def grade_batch(req: BatchGradeRequest):
    """
    批量评分端点 — 支持单选题、多选题、简答题混合批改。

    - 单选: 本地精确匹配（correct_answer 索引比对）
    - 多选: 本地集合比对（correct_answers 集合比对，顺序无关）
    - 简答: LLM 评分（调用 Grader._grade_short_answer）
    """
    answers_by_index: dict[int, BatchGradeAnswer] = {
        a.question_index: a for a in req.answers
    }
    results: list[BatchGradeItem] = []

    for q in req.questions:
        ans = answers_by_index.get(q.question_index)
        idx = q.question_index

        if q.question_type == "single":
            results.append(_grade_single_choice(q, ans, idx))
        elif q.question_type == "multiple":
            results.append(_grade_multiple_choice(q, ans, idx))
        elif q.question_type == "short_answer":
            result = await _grade_short_answer_llm(q, ans, idx)
            results.append(result)
        else:
            # Fallback: treat unknown type as single choice
            results.append(_grade_single_choice(q, ans, idx))

    total_score = sum(r.score for r in results)
    total_points = sum(r.total_points for r in results)
    percentage = (total_score / total_points * 100) if total_points > 0 else 0

    return BatchGradeResponse(
        results=results,
        total_score=total_score,
        total_points=total_points,
        percentage=round(percentage, 1),
        passed=percentage >= 60,
        graded_count=len(results),
    )


# ---- 本地评分函数 ----

def _grade_single_choice(
    q: BatchGradeQuestion, ans: BatchGradeAnswer | None, idx: int
) -> BatchGradeItem:
    """评分单选题：精确匹配用户选择与正确答案索引"""
    correct_idx = q.correct_answer
    user_idx = int(ans.answer_value) if ans and ans.answer_value.isdigit() else -1
    is_correct = (user_idx == correct_idx) and user_idx >= 0

    correct_text = q.options[correct_idx] if 0 <= correct_idx < len(q.options) else str(correct_idx)
    user_text = q.options[user_idx] if 0 <= user_idx < len(q.options) else "未作答"

    score = q.points if is_correct else 0
    feedback = (
        f"回答正确！答案是 {chr(65 + correct_idx)}. {correct_text}"
        if is_correct
        else f"回答错误。正确答案是 {chr(65 + correct_idx)}. {correct_text}"
        if user_idx >= 0
        else f"未作答。正确答案是 {chr(65 + correct_idx)}. {correct_text}"
    )

    return BatchGradeItem(
        question_index=idx,
        is_correct=is_correct,
        score=score,
        total_points=q.points,
        feedback=feedback,
        correct_answer=correct_text,
        graded_by="local",
    )


def _grade_multiple_choice(
    q: BatchGradeQuestion, ans: BatchGradeAnswer | None, idx: int
) -> BatchGradeItem:
    """评分多选题：集合比对（顺序无关）"""
    correct_set = set(q.correct_answers)
    user_set = set(ans.answer_values) if ans else set()

    is_correct = (user_set == correct_set) and len(user_set) > 0

    correct_labels = ", ".join(
        chr(65 + i) for i in sorted(correct_set) if 0 <= i < len(q.options)
    )
    user_labels = ", ".join(
        chr(65 + i) for i in sorted(user_set) if 0 <= i < len(q.options)
    ) if user_set else "未作答"

    score = q.points if is_correct else 0

    if is_correct:
        feedback = f"回答正确！正确答案: {correct_labels}"
    elif not user_set:
        feedback = f"未作答。正确答案: {correct_labels}"
    else:
        feedback = f"回答不完整或有误。你的选择: {user_labels}，正确答案: {correct_labels}"

    return BatchGradeItem(
        question_index=idx,
        is_correct=is_correct,
        score=score,
        total_points=q.points,
        feedback=feedback,
        correct_answer=correct_labels,
        graded_by="local",
    )


async def _grade_short_answer_llm(
    q: BatchGradeQuestion, ans: BatchGradeAnswer | None, idx: int
) -> BatchGradeItem:
    """评分简答题：调用 LLM Grader"""
    user_text = ans.answer_value if ans else ""

    if not user_text.strip():
        return BatchGradeItem(
            question_index=idx,
            is_correct=False,
            score=0,
            total_points=q.points,
            feedback="未作答。请尝试写下你的理解，即使不完全正确也能获得部分分数。",
            correct_answer=q.answer,
            graded_by="local",
        )

    try:
        grader = get_grader()
        result: GradeResult = await grader._grade_short_answer(
            question=q.question,
            standard_answer=q.answer or q.comment_prompt,
            user_answer=user_text,
            total_points=q.points,
            key_points=q.key_points,
        )

        return BatchGradeItem(
            question_index=idx,
            is_correct=result.is_correct,
            score=result.score,
            total_points=result.total_points,
            feedback=result.feedback,
            correct_answer=q.answer,
            key_points_hit=result.key_points_hit,
            key_points_missed=result.key_points_missed,
            graded_by="llm",
        )
    except Exception as e:
        logger.error("Short answer LLM grading failed for question %d: %s", idx, e)
        return BatchGradeItem(
            question_index=idx,
            is_correct=False,
            score=q.points * 0.5,  # 50% fallback
            total_points=q.points,
            feedback="已收到你的答案，请参考标准答案进行对照学习。",
            correct_answer=q.answer,
            graded_by="local",
        )
