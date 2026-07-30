"""
Teacher API — 教师端完整 API

Classes | Students | Groups | Courses | Resources | Dashboard | Questions | Exams
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query

logger = logging.getLogger("starlearn.teacher")

router = APIRouter(prefix="/api/teacher")


# ─────────────────────────────────────────────
# M4.1: AI 教学建议（教师 workbench）
# ─────────────────────────────────────────────

@router.get("/ai-suggestions")
def get_ai_suggestions(
    teacher_id: str | None = Header(None, alias="X-Teacher-Id"),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    # FastAPI 直接调用时 Query 可能保留为对象；强制转 int
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10
    """获取 AI 给教师的干预建议列表（M4.1 / #5 part 1）。

    占位实现：返回 mock 数据（实际接 RuleEngine + ProfilerAgent）。
    每条 suggestion 包含：
      - id          : 唯一标识
      - student_id  : 目标学生
      - type        : 类型（low_engagement / deadline / weakness）
      - priority    : high / medium / low
      - payload     : 详情
      - status      : pending / acted / dismissed
    """
    items = [
        {
            "id": f"sg_{i}",
            "student_id": f"s_{i}",
            "type": ["low_engagement", "weakness", "deadline"][i % 3],
            "priority": ["high", "medium", "low"][i % 3],
            "payload": {
                "message": f"学生 s_{i} 需要关注",
                "topic": "勾股定理" if i % 2 == 0 else "一元二次方程",
            },
            "status": "pending",
        }
        for i in range(min(limit, 3))
    ]
    return {"suggestions": items, "teacher_id": teacher_id, "total": len(items)}


@router.post("/suggestion/{suggestion_id}/act")
def act_on_suggestion(
    suggestion_id: str,
    payload: dict[str, Any],
    teacher_id: str | None = Header(None, alias="X-Teacher-Id"),
) -> dict[str, Any]:
    """教师对 AI 建议一键下发 / 修改 / 取消（M4.1）。

    Args:
        suggestion_id: 建议 ID
        payload: {action: send_to_student|edit|cancel, message?: str}
        teacher_id: 教师 ID（来自 X-Teacher-Id header）
    """
    action = payload.get("action", "send_to_student")
    return {
        "suggestion_id": suggestion_id,
        "action": action,
        "acted_at": datetime.utcnow().isoformat(),
        "teacher_id": teacher_id,
        "status": "delivered" if action == "send_to_student" else action,
    }

# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard():
    """教师仪表盘概览数据。"""
    return {
        "stats": {
            "totalStudents": 0,
            "activeClasses": 0,
            "totalCourses": 0,
            "pendingGrading": 0,
            "avgScore": 0,
            "weeklyActivity": 0,
            "studentGrowth": 0,
        },
        "recentActivity": [],
        "upcomingTasks": [],
    }


@router.get("/dashboard/recent-tasks")
def get_recent_tasks():
    """教师最近的待办任务。"""
    return {"tasks": []}


@router.get("/dashboard/ai-suggestions")
def get_ai_suggestions():
    """AI 教学建议。"""
    return {"suggestions": []}


# ─────────────────────────────────────────────
# Classes (班级管理)
# ─────────────────────────────────────────────

@router.get("/classes")
def list_classes():
    """获取所有班级列表。"""
    return {"classes": []}


@router.post("/class")
def create_class(data: dict[str, Any]):
    """创建新班级。"""
    return {"success": True, "id": 1, **data}


@router.put("/class/{class_id}")
def update_class(class_id: int, data: dict[str, Any]):
    """更新班级信息。"""
    return {"success": True, "id": class_id, **data}


@router.delete("/class/{class_id}")
def delete_class(class_id: int):
    """删除班级。"""
    return {"success": True}


@router.get("/class/{class_id}/students")
def list_class_students(class_id: int):
    """获取班级学生列表。"""
    return {"students": []}


@router.post("/students/import")
def import_students(data: dict[str, Any]):
    """批量导入学生。"""
    return {"success": True, "imported": 0}


@router.get("/class/{class_id}/groups")
def list_class_groups(class_id: int):
    """获取班级小组列表。"""
    return {"groups": []}


@router.post("/class/group")
def create_group(data: dict[str, Any]):
    """创建小组。"""
    return {"success": True, "id": 1, **data}


@router.delete("/class/group/{group_id}")
def delete_group(group_id: int):
    """删除小组。"""
    return {"success": True}


@router.delete("/class/group/{group_id}/student")
def remove_student_from_group(group_id: int, data: dict[str, Any]):
    """从小组中移除学生。"""
    return {"success": True}


@router.get("/student/{student_id}/profile")
def get_student_profile(student_id: int):
    """获取学生详细画像。"""
    return {
        "profile": {
            "id": student_id,
            "username": f"student_{student_id}",
            "display_name": "",
            "avatar": "",
            "stats": {"avgScore": 0, "completedCourses": 0, "studyHours": 0},
            "evaluation": {},
        }
    }


# ─────────────────────────────────────────────
# Courses & Resources (课程内容管理)
# ─────────────────────────────────────────────

@router.get("/courses")
def list_teacher_courses():
    """获取教师的课程节点列表。"""
    return {"courses": []}


@router.post("/course")
def create_course_node(data: dict[str, Any]):
    """创建课程节点。"""
    return {"success": True, "id": 1, **data}


@router.put("/course/{course_id}")
def update_course_node(course_id: int, data: dict[str, Any]):
    """更新课程节点。"""
    return {"success": True, "id": course_id, **data}


@router.delete("/course/{course_id}")
def delete_course_node(course_id: int):
    """删除课程节点。"""
    return {"success": True}


@router.get("/course/{course_id}/resources")
def list_course_resources(course_id: int):
    """获取课程资源列表。"""
    return {"resources": []}


@router.post("/resources/upload")
def upload_resource(data: dict[str, Any]):
    """上传课程资源（FormData 由前端处理）。"""
    return {"success": True, "id": 1, "url": ""}


@router.delete("/resource/{resource_id}")
def delete_resource(resource_id: int):
    """删除课程资源。"""
    return {"success": True}


@router.post("/ai/review")
def ai_review_resource(data: dict[str, Any]):
    """AI 审查课程资源。"""
    return {"success": True, "review": {"score": 0, "feedback": ""}}


# ─────────────────────────────────────────────
# Questions (题库管理)
# ─────────────────────────────────────────────

@router.get("/questions")
def list_questions(
    type: str | None = Query(None),
    subject: str | None = Query(None),
    page: int = Query(1),
    pageSize: int = Query(20),
):
    """获取题目列表。"""
    return {"questions": [], "total": 0, "page": page, "pageSize": pageSize}


@router.post("/question")
def create_question(data: dict[str, Any]):
    """创建题目。"""
    return {"success": True, "id": 1, **data}


@router.put("/question/{question_id}")
def update_question(question_id: int, data: dict[str, Any]):
    """更新题目。"""
    return {"success": True, "id": question_id, **data}


@router.delete("/question/{question_id}")
def delete_question(question_id: int):
    """删除题目。"""
    return {"success": True}


@router.post("/questions/import")
def import_questions(data: dict[str, Any]):
    """批量导入题目。"""
    return {"success": True, "imported": 0}


# ─────────────────────────────────────────────
# Exams (考试管理)
# ─────────────────────────────────────────────

@router.get("/exams")
def list_exams():
    """获取考试列表。"""
    return {"exams": []}


@router.post("/exam")
def create_exam(data: dict[str, Any]):
    """创建考试。"""
    return {"success": True, "id": 1, **data}


@router.put("/exam/{exam_id}")
def update_exam(exam_id: int, data: dict[str, Any]):
    """更新考试。"""
    return {"success": True, "id": exam_id, **data}


@router.delete("/exam/{exam_id}")
def delete_exam(exam_id: int):
    """删除考试。"""
    return {"success": True}


@router.post("/exam/{exam_id}/publish")
def publish_exam(exam_id: int):
    """发布考试。"""
    return {"success": True}


@router.post("/exam/{exam_id}/archive")
def archive_exam(exam_id: int):
    """归档考试。"""
    return {"success": True}


@router.get("/exam/{exam_id}/results")
def get_exam_results(exam_id: int):
    """获取考试结果。"""
    return {"results": []}


@router.post("/exam/{exam_id}/grade")
def grade_exam(exam_id: int, data: dict[str, Any]):
    """批改考试。"""
    return {"success": True}


@router.get("/exam/{exam_id}/analysis")
def get_exam_analysis(exam_id: int):
    """获取考试分析。"""
    return {"analysis": {"avgScore": 0, "distribution": [], "items": []}}
