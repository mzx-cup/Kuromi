from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except Exception:
        return None


def _date_key(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


def _range_start(today: datetime, range_key: str) -> datetime | None:
    if range_key == "week":
        return today - timedelta(days=today.weekday())
    if range_key == "month":
        return today.replace(day=1)
    if range_key == "year":
        return today.replace(month=1, day=1)
    return None


def _minutes_from_stats(stats: dict[str, Any] | None) -> dict[str, int]:
    daily = (stats or {}).get("daily_minutes", {}) or {}
    result = {}
    for date, minutes in daily.items():
        try:
            result[str(date)] = int(minutes or 0)
        except Exception:
            result[str(date)] = 0
    return result


def _filter_daily_minutes(daily_minutes: dict[str, int], today: datetime, range_key: str) -> dict[str, int]:
    start = _range_start(today, range_key)
    if start is None:
        return dict(daily_minutes)
    today_key = _date_key(today)
    start_key = _date_key(start)
    return {date: minutes for date, minutes in daily_minutes.items() if start_key <= date <= today_key}


def _merge_session_minutes(daily_minutes: dict[str, int], sessions: list[dict[str, Any]]) -> dict[str, int]:
    merged = dict(daily_minutes)
    session_daily: dict[str, int] = defaultdict(int)
    for session in sessions:
        date = str(session.get("session_date") or "")[:10]
        if not date:
            continue
        session_daily[date] += int(session.get("duration_minutes") or 0)
    for date, minutes in session_daily.items():
        merged[date] = max(merged.get(date, 0), minutes)
    return merged


def _safe_percent(current: Any, target: Any) -> int:
    try:
        current_value = float(current or 0)
        target_value = float(target or 0)
    except Exception:
        return 0
    if target_value <= 0:
        return 0
    return max(0, min(100, round(current_value / target_value * 100)))


def _round_half_up(value: float) -> int:
    return int(value + 0.5)


def _current_streak(daily_minutes: dict[str, int], today: datetime) -> int:
    streak = 0
    cursor = today
    while True:
        if daily_minutes.get(_date_key(cursor), 0) <= 0:
            break
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _weekly_activity(daily_minutes: dict[str, int], today: datetime) -> list[dict[str, Any]]:
    start = today - timedelta(days=today.weekday())
    labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return [
        {
            "date": _date_key(start + timedelta(days=i)),
            "day": labels[i],
            "minutes": daily_minutes.get(_date_key(start + timedelta(days=i)), 0),
            "hours": round(daily_minutes.get(_date_key(start + timedelta(days=i)), 0) / 60, 1),
        }
        for i in range(7)
    ]


def _course_progress(sessions: list[dict[str, Any]], mastery: list[dict[str, Any]], goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    subject_minutes: dict[str, int] = defaultdict(int)
    for session in sessions:
        subject = session.get("subject") or session.get("course") or "未分类"
        subject_minutes[str(subject)] += int(session.get("duration_minutes") or 0)

    mastery_by_subject: dict[str, list[int]] = defaultdict(list)
    for item in mastery:
        subject = item.get("subject") or item.get("name") or item.get("node_id") or "知识点"
        mastery_by_subject[str(subject)].append(int(item.get("mastery") or 0))

    rows = []
    for subject, minutes in subject_minutes.items():
        mastery_values = mastery_by_subject.get(subject, [])
        progress_sources = []
        if mastery_values:
            progress_sources.append(sum(mastery_values) / len(mastery_values))
        related_goal_progress = [
            _safe_percent(goal.get("current_value"), goal.get("target_value"))
            for goal in goals
            if subject in str(goal.get("title") or goal.get("goal_type") or "")
        ]
        progress_sources.extend(related_goal_progress)
        progress = _round_half_up(sum(progress_sources) / len(progress_sources)) if progress_sources else min(100, round(minutes / 120 * 100))
        rows.append({
            "name": subject,
            "icon": _subject_icon(subject),
            "minutes": minutes,
            "progress": progress,
        })

    for goal in goals:
        name = goal.get("title") or goal.get("goal_type") or "学习目标"
        if any(row["name"] == name for row in rows):
            continue
        rows.append({
            "name": name,
            "icon": "🎯",
            "minutes": 0,
            "progress": _safe_percent(goal.get("current_value"), goal.get("target_value")),
        })

    if not rows:
        for item in mastery[:6]:
            rows.append({
                "name": item.get("name") or item.get("node_id") or "知识点",
                "icon": item.get("icon") or "📚",
                "minutes": 0,
                "progress": int(item.get("mastery") or 0),
            })

    return sorted(rows, key=lambda row: (row["progress"], row["minutes"]), reverse=True)[:8]


def _subject_icon(subject: str) -> str:
    text = subject.lower()
    if "python" in text:
        return "🐍"
    if "算法" in subject or "algorithm" in text:
        return "🧮"
    if "数据库" in subject or "sql" in text or "mysql" in text:
        return "🗄️"
    if "web" in text or "前端" in subject:
        return "🌐"
    if "ai" in text or "机器学习" in subject:
        return "🤖"
    if "数学" in subject:
        return "📊"
    return "📚"


def build_progress_summary(
    user_id: int,
    range_key: str,
    today: str | None,
    stats: dict[str, Any] | None,
    sessions: list[dict[str, Any]],
    goals: list[dict[str, Any]],
    mastery: list[dict[str, Any]],
) -> dict[str, Any]:
    today_dt = _parse_date(today) or datetime.now()
    all_daily = _merge_session_minutes(_minutes_from_stats(stats), sessions)
    ranged_daily = _filter_daily_minutes(all_daily, today_dt, range_key)
    total_minutes = sum(ranged_daily.values())
    study_days = sum(1 for minutes in ranged_daily.values() if minutes > 0)
    completed_goals = sum(1 for goal in goals if _safe_percent(goal.get("current_value"), goal.get("target_value")) >= 100)
    avg_daily = round(total_minutes / study_days / 60, 1) if study_days else 0

    return {
        "user_id": user_id,
        "range": range_key,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 1),
        "study_days": study_days,
        "completed_courses": completed_goals,
        "current_streak": _current_streak(all_daily, today_dt),
        "avg_daily_hours": avg_daily,
        "weekly_activity": _weekly_activity(all_daily, today_dt),
        "course_progress": _course_progress(sessions, mastery, goals),
        "timeline": _timeline_from_sessions(sessions),
    }


def _timeline_from_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(sessions, key=lambda s: (str(s.get("session_date") or ""), str(s.get("end_time") or "")), reverse=True)
    return [
        {
            "title": f"学习「{session.get('subject') or '未分类'}」",
            "time": session.get("session_date") or "",
            "desc": f"{session.get('duration_minutes') or 0} 分钟",
            "status": "completed",
        }
        for session in rows[:8]
    ]


def build_calendar_payload(events_data: dict[str, Any] | None, sessions: list[dict[str, Any]], today: str | None = None) -> dict[str, Any]:
    events_data = events_data or {}
    days: dict[str, dict[str, Any]] = {}

    for date, events in events_data.items():
        normalized = _normalize_events(events)
        if normalized:
            done_count = sum(1 for event in normalized if event.get("done"))
            status = "completed" if done_count == len(normalized) else "scheduled"
            days[date] = {
                "status": status,
                "tasks": normalized,
                "study_minutes": 0,
            }

    for session in sessions:
        date = str(session.get("session_date") or "")[:10]
        if not date:
            continue
        day = days.setdefault(date, {"status": "empty", "tasks": [], "study_minutes": 0})
        minutes = int(session.get("duration_minutes") or 0)
        day["study_minutes"] += minutes
        day["tasks"].append({
            "name": session.get("subject") or "学习记录",
            "duration": f"{minutes}分钟",
            "done": True,
            "category": "study",
        })
        day["status"] = "partial" if any(not task.get("done") for task in day["tasks"]) else "completed"

    today_dt = _parse_date(today) or datetime.now()
    month_prefix = today_dt.strftime("%Y-%m")
    month_days = {date: day for date, day in days.items() if date.startswith(month_prefix)}
    return {
        "days": days,
        "month_summary": {
            "study_days": sum(1 for day in month_days.values() if day.get("study_minutes", 0) > 0),
            "total_minutes": sum(day.get("study_minutes", 0) for day in month_days.values()),
            "completed_tasks": sum(1 for day in month_days.values() for task in day.get("tasks", []) if task.get("done")),
        },
        "upcoming": _upcoming_events(days, today_dt),
    }


def _normalize_events(events: Any) -> list[dict[str, Any]]:
    if isinstance(events, dict):
        events = events.get("tasks") or events.get("events") or []
    if not isinstance(events, list):
        return []
    return [
        {
            "name": event.get("name") or event.get("title") or "学习计划",
            "duration": event.get("duration") or "1h",
            "done": bool(event.get("done", False)),
            "category": event.get("category") or "study",
            "desc": event.get("desc") or event.get("description") or "",
        }
        for event in events
        if isinstance(event, dict)
    ]


def _upcoming_events(days: dict[str, dict[str, Any]], today: datetime) -> list[dict[str, Any]]:
    today_key = _date_key(today)
    rows = []
    for date, day in days.items():
        if date < today_key:
            continue
        for task in day.get("tasks", []):
            if task.get("done"):
                continue
            rows.append({"date": date, **task})
    return sorted(rows, key=lambda row: row["date"])[:6]


def build_focus_payload(focus_history: list[Any] | None, fallback_score: int = 0) -> dict[str, Any]:
    history = [item for item in (focus_history or []) if isinstance(item, dict)]
    if not history:
        return {
            "score": int(fallback_score or 0),
            "timeline": [],
            "segments": {"deep": 0, "shallow": 0, "warning": 0},
        }

    scores = []
    segments = {"deep": 0, "shallow": 0, "warning": 0}
    timeline = []
    for item in history[-24:]:
        score = int(item.get("score") or item.get("value") or 0)
        if score:
            scores.append(score)
        kind = item.get("type") or ("deep" if score >= 75 else "warning" if score < 55 else "shallow")
        if kind not in segments:
            kind = "shallow"
        segments[kind] += 1
        timeline.append({
            "score": score,
            "type": kind,
            "timestamp": item.get("timestamp") or item.get("time") or "",
        })

    score = _round_half_up(sum(scores) / len(scores)) if scores else int(fallback_score or 0)
    return {
        "score": score,
        "timeline": timeline,
        "segments": segments,
    }


def build_focus_event(
    study_minutes: int = 0,
    focus_minutes: int = 0,
    page_switches: int = 0,
    completed_focus: bool = False,
    timestamp: str | None = None,
    source: str = "activity",
) -> dict[str, Any]:
    study = max(0, int(study_minutes or 0))
    focus = max(0, int(focus_minutes or 0))
    switches = max(0, int(page_switches or 0))

    score = 68
    score += min(18, study * 2)
    score += min(16, focus)
    if completed_focus:
        score += 10
    score -= min(36, switches * 6)
    score = max(10, min(100, score))

    if score >= 75:
        kind = "deep"
    elif score < 55:
        kind = "warning"
    else:
        kind = "shallow"

    return {
        "score": score,
        "type": kind,
        "timestamp": timestamp or datetime.now().isoformat(),
        "source": source,
        "study_minutes": study,
        "focus_minutes": focus,
        "page_switches": switches,
        "completed_focus": bool(completed_focus),
    }
