"""
Teacher API — 教师端完整 API

Classes | Students | Groups | Courses | Resources | Dashboard | Questions | Exams

缺口4 改造:
  - POST /api/teacher/exam/{exam_id}/grade → 调用 EnsembleGrader 做 AI 预评分
  - PUT  /api/teacher/exam/{exam_id}/grade → 教师人工校准 + 4 维分数覆盖 + 审计日志
  - GET  /api/teacher/exam/{exam_id}/results → 真实数据(从 quiz_records 表)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request

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
async def grade_exam(exam_id: int, data: dict[str, Any], request: Request):
    """缺口4:AI 预评分(多 Agent 联合打分)。

    Body: {result_id: int}
    Returns: {success, ai_score, ai_comment, dimensions, arbitration}
    """
    from db import get_conn, _is_sqlite

    result_id = data.get("result_id")
    if not result_id:
        raise HTTPException(status_code=400, detail="result_id required")

    teacher_id = _extract_teacher_id(request)

    # 1. 从 quiz_records 读答卷
    conn = get_conn()
    try:
        cur = conn.cursor()
        if _is_sqlite(conn):
            cur.execute(
                "SELECT id, question, answer, max_score, classroom_id FROM quiz_records WHERE id=?",
                (result_id,),
            )
        else:
            cur.execute(
                "SELECT id, question, answer, max_score, classroom_id FROM quiz_records WHERE id=%s",
                (result_id,),
            )
        row = cur.fetchone()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if not row:
        raise HTTPException(status_code=404, detail="result not found")

    qr_id, question, answer, max_score, _classroom_id = (
        row[0], row[1] or "", row[2] or "", float(row[3] or 100), row[4],
    )

    # 2. 调用 EnsembleGrader
    from app.services.teacher.ensemble_grading import get_ensemble_grader
    grader = get_ensemble_grader()
    ens = await grader.grade(
        question=question,
        standard_answer="",       # 教师上传题目时维护标准答案(简化场景填空)
        user_answer=answer,
        question_type="short_answer",
        total_points=max_score,
    )

    # 3. 写回 ai_score / 4 维(独立字段,不影响最终 score)
    conn = get_conn()
    try:
        cur = conn.cursor()
        if _is_sqlite(conn):
            cur.execute(
                """UPDATE quiz_records SET
                    ai_score=?, ai_comment=?,
                    knowledge_score=?, ability_score=?, process_score=?, innovation_score=?,
                    graded_by='auto', graded_at=CURRENT_TIMESTAMP,
                    graded_by_user_id=?
                   WHERE id=?""",
                (
                    ens.score, ens.feedback,
                    ens.knowledge_dimension, ens.ability_dimension,
                    ens.process_dimension, ens.innovation_dimension,
                    teacher_id, qr_id,
                ),
            )
        else:
            cur.execute(
                """UPDATE quiz_records SET
                    ai_score=%s, ai_comment=%s,
                    knowledge_score=%s, ability_score=%s, process_score=%s, innovation_score=%s,
                    graded_by='auto', graded_at=NOW(),
                    graded_by_user_id=%s
                   WHERE id=%s""",
                (
                    ens.score, ens.feedback,
                    ens.knowledge_dimension, ens.ability_dimension,
                    ens.process_dimension, ens.innovation_dimension,
                    teacher_id, qr_id,
                ),
            )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {
        "success": True,
        "ai_score": ens.score,
        "ai_comment": ens.feedback,
        "dimensions": {
            "knowledge": ens.knowledge_dimension,
            "ability": ens.ability_dimension,
            "process": ens.process_dimension,
            "innovation": ens.innovation_dimension,
        },
        "arbitration": ens.arbitration,
        "source_count": len(ens.source_scores),
    }


@router.put("/exam/{exam_id}/grade")
async def override_grade(exam_id: int, data: dict[str, Any], request: Request):
    """缺口4:教师人工校准分数。

    Body: {result_id, final_score, teacher_comment?, rubric?, is_final?}
    Returns: {success, result, audit_log_entry}
    """
    from db import get_conn, _is_sqlite
    import json as _json

    result_id = data.get("result_id")
    final_score = data.get("final_score")
    teacher_comment = data.get("teacher_comment", "") or ""
    rubric = data.get("rubric")
    is_final = bool(data.get("is_final", True))

    if not result_id or final_score is None:
        raise HTTPException(status_code=400, detail="result_id and final_score required")

    teacher_id = _extract_teacher_id(request)

    conn = get_conn()
    try:
        cur = conn.cursor()
        # 1. 读旧值(审计)
        if _is_sqlite(conn):
            cur.execute(
                "SELECT score, override_count, graded_by FROM quiz_records WHERE id=?",
                (result_id,),
            )
        else:
            cur.execute(
                "SELECT score, override_count, graded_by FROM quiz_records WHERE id=%s",
                (result_id,),
            )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="result not found")
        old_score, old_override_count, old_graded_by = (
            row[0], row[1] or 0, row[2] or "auto",
        )

        new_override_count = (old_override_count or 0) + 1
        # graded_by:第一次教师覆盖 → 'teacher';后续 → 'modified'
        new_graded_by = "teacher" if new_override_count == 1 else "modified"

        rubric_json = _json.dumps(rubric, ensure_ascii=False) if rubric else None

        # 2. 写新值
        if _is_sqlite(conn):
            cur.execute(
                """UPDATE quiz_records SET
                    score=?, teacher_comment=?, rubric=?,
                    override_count=?, graded_by=?, graded_by_user_id=?, graded_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (
                    float(final_score), teacher_comment, rubric_json,
                    new_override_count, new_graded_by, teacher_id, result_id,
                ),
            )
        else:
            cur.execute(
                """UPDATE quiz_records SET
                    score=%s, teacher_comment=%s, rubric=%s,
                    override_count=%s, graded_by=%s, graded_by_user_id=%s, graded_at=NOW()
                   WHERE id=%s""",
                (
                    float(final_score), teacher_comment, rubric_json,
                    new_override_count, new_graded_by, teacher_id, result_id,
                ),
            )
        conn.commit()

        # 3. 构造审计日志条目(V2 暂存到 feedback JSON)
        audit_entry = {
            "at": datetime.utcnow().isoformat(),
            "by": f"teacher:{teacher_id}" if teacher_id else "teacher:unknown",
            "action": "override",
            "before_score": old_score,
            "after_score": float(final_score),
            "comment": teacher_comment,
            "is_final": is_final,
        }
        try:
            if _is_sqlite(conn):
                cur.execute("SELECT feedback FROM quiz_records WHERE id=?", (result_id,))
            else:
                cur.execute("SELECT feedback FROM quiz_records WHERE id=%s", (result_id,))
            fb_row = cur.fetchone()
            existing = {}
            if fb_row and fb_row[0]:
                try:
                    if isinstance(fb_row[0], (dict, list)):
                        existing = fb_row[0] if isinstance(fb_row[0], dict) else {"history": fb_row[0]}
                    else:
                        existing = _json.loads(fb_row[0])
                except Exception:
                    existing = {}
            history = existing.get("override_history", [])
            history.append(audit_entry)
            existing["override_history"] = history
            new_feedback_json = _json.dumps(existing, ensure_ascii=False)
            if _is_sqlite(conn):
                cur.execute("UPDATE quiz_records SET feedback=? WHERE id=?",
                            (new_feedback_json, result_id))
            else:
                cur.execute("UPDATE quiz_records SET feedback=%s WHERE id=%s",
                            (new_feedback_json, result_id))
            conn.commit()
        except Exception as audit_err:
            logger.warning(f"audit_log 写入失败(忽略): {audit_err}")

        # 4. 读回最新值返回
        if _is_sqlite(conn):
            cur.execute(
                """SELECT id, score, ai_score, knowledge_score, ability_score,
                          process_score, innovation_score, override_count,
                          graded_by, teacher_comment, graded_by_user_id, graded_at
                   FROM quiz_records WHERE id=?""",
                (result_id,),
            )
        else:
            cur.execute(
                """SELECT id, score, ai_score, knowledge_score, ability_score,
                          process_score, innovation_score, override_count,
                          graded_by, teacher_comment, graded_by_user_id, graded_at
                   FROM quiz_records WHERE id=%s""",
                (result_id,),
            )
        final = cur.fetchone()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if not final:
        raise HTTPException(status_code=500, detail="update succeeded but read failed")

    return {
        "success": True,
        "result": {
            "id": final[0],
            "score": final[1],
            "ai_score": final[2],
            "knowledge_score": final[3],
            "ability_score": final[4],
            "process_score": final[5],
            "innovation_score": final[6],
            "override_count": final[7],
            "graded_by": final[8],
            "teacher_comment": final[9] or "",
            "graded_by_user_id": final[10],
            "graded_at": str(final[11]) if final[11] else None,
        },
        "audit_log": audit_entry,
    }


def _extract_teacher_id(request: Request) -> str | None:
    """从 JWT 或 X-Teacher-Id header 提取教师 ID."""
    teacher_id = request.headers.get("X-Teacher-Id")
    if teacher_id:
        return teacher_id
    # fallback: 尝试解析 Authorization Bearer
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jwt
            payload = jwt.decode(auth[7:], options={"verify_signature": False})
            return str(payload.get("sub") or payload.get("user_id") or "")
        except Exception:
            return None
    return None


@router.get("/exam/{exam_id}/analysis")
def get_exam_analysis(exam_id: int):
    """获取考试分析。"""
    return {"analysis": {"avgScore": 0, "distribution": [], "items": []}}


# ============================================================
# P0 比赛模式: 班级实时观察 (Task 17)
# 路径: GET /api/teacher/dashboard/observation
# 设计: 演示用静态种子观察事件, 失败 fallback 永远结构正确.
#      前端每 5s 拉一次, 展示"班级实时观察"卡片.
# P1 Task 21: 加 require_teacher 守卫, 仅教师/管理员可读.
# ============================================================


@router.get("/dashboard/observation")
def get_dashboard_observation(request: Request):
    """返回最近的班级观察事件 (学生动作/AI 建议/教师行动).

    P1 Task 21: 仅教师/管理员 token 可访问.
    """
    from app.api.auth import require_teacher
    require_teacher(request)

    from datetime import datetime, timezone  # 局部 import, 避免启动期拉入.

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # 演示种子: 3 条观察, 时戳用同一 now, 前端按顺序展示.
    observations = [
        {
            "student_id": "demo_student_1",
            "event": "answered question on recursion",
            "ts": now,
            "level": "info",
        },
        {
            "student_id": "demo_student_2",
            "event": "asked for hint on induction",
            "ts": now,
            "level": "warn",
        },
        {
            "student_id": "demo_student_3",
            "event": "completed micro-exercise correctly",
            "ts": now,
            "level": "success",
        },
    ]
    return {"observations": observations, "fallback": False}

