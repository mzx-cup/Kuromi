"""
Datacenter API — 数据仪表盘 API

GET  /api/datacenter/stats   — 统计数据
GET  /api/datacenter/trends  — 趋势数据
GET  /api/datacenter/events  — SSE 实时事件流
GET  /api/datacenter/dashboard/summary — 个人学习大屏数据
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from datetime import datetime, timedelta, date
from typing import Any

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import StreamingResponse

import jwt

logger = logging.getLogger("starlearn.datacenter")

router = APIRouter(prefix="/api/datacenter")

# JWT 配置 (同 auth.py)
JWT_SECRET = __import__('os').environ.get("JWT_SECRET", "starlearn-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"


def _get_user_id_from_request(request: Request) -> int:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效令牌")
    uid = payload.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="令牌无效")
    return int(uid)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except Exception:
        return None


def _date_key(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def _last_n_dates(n: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


# ── 仪表盘数据构建 ──

def _build_dashboard(user_id: int, range_key: str) -> dict[str, Any]:
    from app.services.datacenter_aggregator import build_full_user_state

    full_state = build_full_user_state(user_id)
    if not full_state or not full_state.get("user"):
        return _build_fallback_dashboard(user_id, range_key)

    stats = full_state.get("stats") or {}
    focus_history = full_state.get("focus_history") or []
    calendar_events = full_state.get("calendar_events") or {}
    learning_profile = full_state.get("learning_profile") or {}
    learning_record = full_state.get("learning_record") or {}

    profile_json = {}
    evaluation_json = {}
    if isinstance(learning_profile, dict):
        pj = learning_profile.get("profile_json")
        if isinstance(pj, str):
            try:
                profile_json = json.loads(pj)
            except Exception:
                pass
        elif isinstance(pj, dict):
            profile_json = pj
        ej = learning_profile.get("evaluation_json")
        if isinstance(ej, str):
            try:
                evaluation_json = json.loads(ej)
            except Exception:
                pass
        elif isinstance(ej, dict):
            evaluation_json = ej

    # -- 合并每日学习时长 (stats.daily_minutes + focus_history) --
    daily_minutes: dict[str, int] = {}
    raw_daily = stats.get("daily_minutes") or {}
    for k, v in raw_daily.items():
        try:
            daily_minutes[str(k)] = int(v or 0)
        except Exception:
            pass

    for fh in focus_history:
        if isinstance(fh, dict):
            ts = str(fh.get("timestamp") or "")[:10]
            if ts:
                daily_minutes[ts] = daily_minutes.get(ts, 0) + int(fh.get("studyMinutes") or 0)

    # -- 时间范围过滤 --
    today = date.today()
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    range_days = days_map.get(range_key, 30)
    cutoff = (today - timedelta(days=range_days)).isoformat()
    ranged_daily = {k: v for k, v in daily_minutes.items() if k >= cutoff}

    total_minutes = sum(ranged_daily.values())
    study_days = sum(1 for v in ranged_daily.values() if v > 0)

    # -- stats --
    streak = int(stats.get("streakDays") or 0)
    exercises = int(stats.get("completedTasks") or 0)
    completed_courses = int(stats.get("completedCourses") or len((learning_record.get("completed_json") or [])) if learning_record else 0)
    total_courses = len(profile_json.get("learningGoals") or []) or completed_courses + 5  # fallback

    # -- weekly activity --
    monday = today - timedelta(days=today.weekday())
    day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekly = []
    for i in range(7):
        d = (monday + timedelta(days=i)).isoformat()
        mins = daily_minutes.get(d, 0)
        weekly.append({
            "date": d,
            "day": day_labels[i],
            "minutes": mins,
            "hours": round(mins / 60, 1),
        })

    # -- course progress (from profile learning goals + mastery) --
    portrait = profile_json.get("learning_portrait") or {}
    k_mastery = portrait.get("knowledge_mastery") or {}
    topics = k_mastery.get("topics") or []
    course_progress = []
    if topics:
        for t in topics[:8]:
            course_progress.append({
                "name": t.get("name", "知识点"),
                "icon": _subject_icon(t.get("name", "")),
                "minutes": 0,
                "progress": int((t.get("level") or 0) * 100),
            })
    else:
        goals = profile_json.get("learningGoals") or []
        for g in goals[:8]:
            course_progress.append({
                "name": g if isinstance(g, str) else g.get("title", "目标"),
                "icon": "📚",
                "minutes": 0,
                "progress": 50,
            })
    if not course_progress:
        course_progress = [
            {"name": "Python 基础", "icon": "🐍", "minutes": 120, "progress": 75},
            {"name": "数据分析", "icon": "📊", "minutes": 80, "progress": 45},
            {"name": "机器学习", "icon": "🤖", "minutes": 30, "progress": 20},
        ]

    # -- timeline (from focus_history) --
    timeline = []
    for fh in sorted(focus_history, key=lambda x: str(x.get("timestamp") or ""), reverse=True)[:8]:
        timeline.append({
            "title": f"学习 {fh.get('studyMinutes', 0)} 分钟",
            "time": str(fh.get("timestamp") or "")[:19],
            "desc": f"专注 {fh.get('focusMinutes', 0)} 分钟",
            "status": "completed" if fh.get("completedFocus") else "active",
        })

    # -- radar dimensions (from student portrait) --
    code_skill = portrait.get("code_skill") or {}
    cognitive = portrait.get("cognitive_style") or {}
    focus = portrait.get("focus_level") or {}
    weakness = portrait.get("weakness") or {}
    learning_goal = portrait.get("learning_goal") or {}

    cs_level = code_skill.get("level", "beginner")
    cs_score = 80 if cs_level == "advanced" else 55 if cs_level == "intermediate" else 30

    cf_confidence = (cognitive.get("confidence") or 0) * 100
    cf_score = min(100, cf_confidence + 30 if cognitive.get("type") else 50)

    focus_current = focus.get("current", "中等专注")
    focus_score = 85 if "高" in str(focus_current) else 60 if "中等" in str(focus_current) else 35

    radar_dims = [
        {"name": "知识掌握", "icon": "🧠", "value": int((k_mastery.get("overall") or 0) * 100)},
        {"name": "代码能力", "icon": "💻", "value": cs_score},
        {"name": "认知分析", "icon": "🔍", "value": int(cf_score)},
        {"name": "专注水平", "icon": "🎯", "value": focus_score},
        {"name": "学习效率", "icon": "⏱️", "value": min(100, study_days * 2 + 30)},
        {"name": "持续力", "icon": "🔥", "value": min(100, streak * 3 + 20)},
    ]
    this_month = [d["value"] for d in radar_dims]
    last_month = [max(20, v - 10) for v in this_month]

    # -- focus payload --
    focus_summary = _build_focus_summary(focus_history)

    # -- heatmap (from daily_minutes) --
    heatmap_days = {}
    for i in range(min(84, range_days)):
        d = (today - timedelta(days=i)).isoformat()
        m = daily_minutes.get(d, 0)
        lvl = 0
        if total_minutes > 0 and m > 0:
            r = m / max(1, max(daily_minutes.values()))
            lvl = 4 if r > 0.75 else 3 if r > 0.5 else 2 if r > 0.25 else 1
        heatmap_days[d] = {"study_minutes": m, "level": lvl, "tasks": []}

    month_days = {k: v for k, v in heatmap_days.items() if k.startswith(today.strftime("%Y-%m"))}
    heatmap_month = {
        "study_days": sum(1 for v in month_days.values() if v["study_minutes"] > 0),
        "total_minutes": sum(v["study_minutes"] for v in month_days.values()),
        "completed_tasks": 0,
    }

    # -- goal rings --
    days_in_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    days_in_month = days_in_month.day
    days_passed = today.day
    target_hours = 40  # monthly target
    hours_goal = min(100, round(total_minutes / 60 / max(1, target_hours) * 100))
    ex_goal = min(100, round(exercises / 50 * 100)) if exercises > 0 else 0
    course_goal = min(100, round(completed_courses / max(1, total_courses) * 100))

    return {
        "success": True,
        "userId": user_id,
        "range": range_key,
        "stats": {
            "totalHours": round(total_minutes / 60, 1),
            "coursesCompleted": completed_courses,
            "coursesTotal": total_courses,
            "exercises": exercises,
            "streak": streak,
        },
        "dailyMinutes": ranged_daily,
        "weeklyActivity": weekly,
        "courseProgress": course_progress,
        "timeline": timeline,
        "radar": {
            "dimensions": radar_dims,
            "thisMonth": this_month,
            "lastMonth": last_month,
        },
        "focus": focus_summary,
        "heatmap": {
            "days": heatmap_days,
            "monthSummary": heatmap_month,
        },
        "goalRings": {
            "hoursGoal": hours_goal,
            "exGoal": ex_goal,
            "courseGoal": course_goal,
        },
    }


def _build_focus_summary(focus_history: list) -> dict[str, Any]:
    if not focus_history:
        return {
            "score": 0,
            "timeline": [],
            "segments": {"deep": 0, "shallow": 0, "warning": 0},
            "summary": {"focusMinutes": 0, "studyMinutes": 0, "pageSwitches": 0},
        }

    total_focus = 0
    total_study = 0
    total_switches = 0
    seg = {"deep": 0, "shallow": 0, "warning": 0}
    tl = []

    for fh in focus_history[-24:]:
        fm = int(fh.get("focusMinutes") or 0)
        sm = int(fh.get("studyMinutes") or 0)
        ps = int(fh.get("pageSwitches") or 0)
        total_focus += fm
        total_study += sm
        total_switches += ps

        # classify
        ratio = fm / max(1, sm) if sm > 0 else 0
        if ratio >= 0.7:
            kind = "deep"
        elif ratio < 0.3:
            kind = "warning"
        else:
            kind = "shallow"
        seg[kind] = seg.get(kind, 0) + 1

        tl.append({
            "score": min(100, int(ratio * 100)),
            "type": kind,
            "timestamp": str(fh.get("timestamp") or ""),
        })

    score = 0
    n = len(focus_history[-24:])
    if n > 0:
        avg_ratio = total_focus / max(1, total_study)
        score = min(100, int(avg_ratio * 80 + (total_focus / max(1, n)) * 2))

    return {
        "score": score,
        "timeline": tl,
        "segments": seg,
        "summary": {
            "focusMinutes": total_focus,
            "studyMinutes": total_study,
            "pageSwitches": total_switches,
        },
    }


def _build_fallback_dashboard(user_id: int, range_key: str) -> dict[str, Any]:
    """当数据库不可用或用户不存在时，返回演示数据。"""
    today = date.today()
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    range_days = days_map.get(range_key, 30)

    daily_minutes: dict[str, int] = {}
    for i in range(range_days):
        d = (today - timedelta(days=i)).isoformat()
        daily_minutes[d] = (hash(f"{user_id}{d}") % 120)

    total_minutes = sum(daily_minutes.values())
    study_days = sum(1 for v in daily_minutes.values() if v > 0)
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    monday = today - timedelta(days=today.weekday())

    ranged_daily = {k: v for k, v in daily_minutes.items() if k >= (today - timedelta(days=range_days)).isoformat()}

    weekly = []
    for i in range(7):
        d = (monday + timedelta(days=i)).isoformat()
        mins = daily_minutes.get(d, (hash(d) % 60))
        weekly.append({"date": d, "day": weekdays[i], "minutes": mins, "hours": round(mins / 60, 1)})

    demos = [
        {"name": "Python 基础", "icon": "🐍", "minutes": 120, "progress": 78},
        {"name": "数据分析", "icon": "📊", "minutes": 90, "progress": 52},
        {"name": "机器学习", "icon": "🤖", "minutes": 30, "progress": 18},
        {"name": "数据结构", "icon": "🧮", "minutes": 60, "progress": 35},
    ]

    radar_dims = [
        {"name": "知识掌握", "icon": "🧠", "value": 68},
        {"name": "代码能力", "icon": "💻", "value": 55},
        {"name": "认知分析", "icon": "🔍", "value": 62},
        {"name": "专注水平", "icon": "🎯", "value": 45},
        {"name": "学习效率", "icon": "⏱️", "value": 58},
        {"name": "持续力", "icon": "🔥", "value": 72},
    ]

    heatmap_days = {}
    for i in range(min(84, range_days)):
        d = (today - timedelta(days=i)).isoformat()
        m = daily_minutes.get(d, 0)
        mx = max(daily_minutes.values()) if daily_minutes else 1
        r = m / max(1, mx)
        lvl = 4 if r > 0.75 else 3 if r > 0.5 else 2 if r > 0.25 else 1
        heatmap_days[d] = {"study_minutes": m, "level": lvl, "tasks": []}

    month_days = {k: v for k, v in heatmap_days.items() if k.startswith(today.strftime("%Y-%m"))}
    heatmap_month = {
        "study_days": sum(1 for v in month_days.values() if v["study_minutes"] > 0),
        "total_minutes": sum(v["study_minutes"] for v in month_days.values()),
        "completed_tasks": 0,
    }

    return {
        "success": True,
        "userId": user_id,
        "range": range_key,
        "stats": {
            "totalHours": round(total_minutes / 60, 1),
            "coursesCompleted": 2,
            "coursesTotal": 8,
            "exercises": 23,
            "streak": 5,
        },
        "dailyMinutes": ranged_daily,
        "weeklyActivity": weekly,
        "courseProgress": demos,
        "timeline": [
            {"title": "学习 Python 数据清洗", "time": today.isoformat() + "T10:30:00", "desc": "45 分钟", "status": "completed"},
            {"title": "完成数据分析练习", "time": (today - timedelta(days=1)).isoformat() + "T14:20:00", "desc": "30 分钟", "status": "completed"},
            {"title": "机器学习入门", "time": (today - timedelta(days=2)).isoformat() + "T09:00:00", "desc": "20 分钟", "status": "completed"},
        ],
        "radar": {"dimensions": radar_dims, "thisMonth": [d["value"] for d in radar_dims], "lastMonth": [max(20, d["value"] - 10) for d in radar_dims]},
        "focus": {"score": 62, "timeline": [], "segments": {"deep": 3, "shallow": 5, "warning": 2}, "summary": {"focusMinutes": 85, "studyMinutes": 140, "pageSwitches": 5}},
        "heatmap": {"days": heatmap_days, "monthSummary": heatmap_month},
        "goalRings": {"hoursGoal": 42, "exGoal": 46, "courseGoal": 25},
        "_fallback": True,
    }


def _subject_icon(name: str) -> str:
    text = str(name).lower()
    if "python" in text: return "🐍"
    if "算法" in text or "algorithm" in text: return "🧮"
    if "数据库" in text or "sql" in text or "mysql" in text: return "🗄️"
    if "web" in text or "前端" in text: return "🌐"
    if "ai" in text or "机器学习" in text or "深度学习" in text: return "🤖"
    if "数学" in text: return "📊"
    if "数据" in text: return "📈"
    return "📚"


# ── API Endpoints ──

@router.get("/stats")
def get_stats(level: str = Query("school")):
    """获取数据仪表盘统计数据。"""
    now = datetime.now().isoformat()
    return {
        "stats": {
            "totalStudents": 0,
            "activeStudents": 0,
            "totalClasses": 0,
            "totalCourses": 0,
            "avgEngagement": 0,
            "avgScore": 0,
            "completionRate": 0,
            "updatedAt": now,
        }
    }


@router.get("/trends")
def get_trends(level: str = Query("school")):
    """获取趋势数据。"""
    return {
        "trends": [],
        "points": [],
        "updatedAt": datetime.now().isoformat(),
    }


@router.get("/events")
async def datacenter_events(request: Request, level: str = Query("school")):
    """SSE 端点 — 推送数据仪表盘的实时事件。"""
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                event_data = {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/dashboard/summary")
def dashboard_summary(request: Request, range: str = Query("30d")):
    """个人学习数据大屏 — 聚合接口。

    Args:
        range: 时间范围 (7d / 30d / 90d)
    """
    if range not in ("7d", "30d", "90d"):
        range = "30d"
    user_id = _get_user_id_from_request(request)
    return _build_dashboard(user_id, range)
