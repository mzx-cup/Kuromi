"""One-shot seeder: reads storage/courses/*.json and creates
Subject / Course / Chapter / SubChapter rows. Idempotent.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.core.database import get_sessionmaker
from app.models.course import Chapter, Course, SubChapter, Subject

logger = logging.getLogger("starlearn.course_seeder")

STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "courses"

SUBJECT_DISPLAY: dict[str, tuple[str, str]] = {
    "cs":       ("Computer Science", "cs"),
    "math":     ("Math", "math"),
    "physics":  ("Physics", "physics"),
    "language": ("Language", "language"),
    "default":  ("General", "default"),
}

SUBJECT_RULES: list[tuple[str, list[str]]] = [
    ("cs", [
        "python", "c language", "java", "javascript", "programming",
        "algorithm", "data structure", "data structures", "code", "coding",
        "development", "frontend", "backend", "vue", "react", "go ",
        "rust", "computer", "software", "git", "linux", "sql",
        "html", "css", "php", "c++", "scala", "kotlin", "swift",
        "html5", "css3", "node", "django", "flask",
    ]),
    ("math", [
        "math", "calculus", "linear algebra", "probability", "statistics",
        "function", "algebra", "geometry", "trigonometry", "equation",
        "quadratic", "derivative", "integral", "matrix", "vector",
    ]),
    ("physics", [
        "physics", "mechanics", "electromagnetism", "optics",
        "thermodynamics", "quantum", "relativity", "circuit",
        "fourier", "wave", "electromagnetic",
    ]),
    ("language", [
        "english", "chinese", "japanese", "korean", "french", "german",
        "ielts", "toefl", "speaking", "listening", "reading", "writing",
        "vocabulary", "grammar", "vocab", "language", "spanish",
    ]),
]


def _slug_for(title: str, requirement: str) -> str:
    hay = (str(title or "") + " " + str(requirement or "") + " ").lower()
    for slug, keywords in SUBJECT_RULES:
        for kw in keywords:
            if kw.lower() in hay:
                return slug
    return "default"


def _stable_id(raw: str, prefix: str) -> str:
    safe = "".join(c if (c.isalnum() or c == "_") else "_" for c in str(raw))[:24]
    if not safe:
        safe = uuid.uuid4().hex[:8]
    return f"{prefix}_{safe}"


async def _ensure_default_subjects() -> dict[str, str]:
    sm = get_sessionmaker()
    async with sm() as session:
        existing = (await session.execute(select(Subject))).scalars().all()
        by_slug: dict[str, str] = {s.slug: s.id for s in existing}

        for slug, (name, s_slug) in SUBJECT_DISPLAY.items():
            if s_slug in by_slug:
                continue
            subj = Subject(
                id=f"subj_{s_slug}",
                name=name,
                slug=s_slug,
                icon=s_slug,
                visible=True,
                sort_order=list(SUBJECT_DISPLAY.keys()).index(slug) * 10,
            )
            session.add(subj)
            await session.flush()
            by_slug[s_slug] = subj.id
        await session.commit()
        return by_slug


async def _is_empty() -> bool:
    sm = get_sessionmaker()
    async with sm() as session:
        n = (await session.execute(select(func.count(Course.id)))).scalar_one()
        return n == 0


async def _seed_one(payload: dict[str, Any], slug_to_id: dict[str, str]) -> str | None:
    title = (payload.get("title") or "").strip() or "(untitled)"
    meta = payload.get("metadata") or {}
    requirement = (meta.get("requirement") or "").strip()
    slug = _slug_for(title, requirement)

    raw_id = payload.get("courseId") or meta.get("session_id") or uuid.uuid4().hex
    course_id = _stable_id(raw_id, "course")
    subject_id = slug_to_id.get(slug) or slug_to_id["default"]

    outlines = payload.get("outlines") or []
    slides = payload.get("slides_v2") or payload.get("slides") or []
    teacher = payload.get("teacher") or {}

    sm = get_sessionmaker()
    async with sm() as session:
        existing = (
            await session.execute(select(Course).where(Course.id == course_id))
        ).scalar_one_or_none()
        if existing:
            return None

        course = Course(
            id=course_id,
            subject_id=subject_id,
            title=title[:256],
            description=(f"Learning goal: {requirement}" if requirement else "")[:1024],
            bvid="",
            playlist_url="",
            cover_url="",
            author_name=(teacher.get("name") or "Star-Learn Teacher")[:128],
            total_lessons=len(slides) or len(outlines),
            total_duration=0,
            progress=0.0,
            visible=True,
            sort_order=0,
            student_id=str(meta.get("student_id") or "")[:64],
            outlines={"items": outlines},
            scenes={"items": slides},
            data_json={
                "requirement": requirement,
                "session_id": meta.get("session_id"),
                "agent_mode": meta.get("agent_mode"),
                "voice_id": meta.get("voice_id"),
            },
            status="published",
        )
        session.add(course)
        await session.flush()

        chapter_list = outlines if outlines else [{"title": "Course content"}]
        stem_part = course_id.replace("course_", "")[:16]
        for idx, ch in enumerate(chapter_list):
            chapter_id = f"ch_{stem_part}_{idx}"[:64]
            chapter = Chapter(
                id=chapter_id,
                course_id=course_id,
                title=(ch.get("title") or f"Chapter {idx + 1}")[:256],
                description=(ch.get("description") or "")[:1024],
                sort_order=idx,
            )
            session.add(chapter)
            await session.flush()

            sc_id = f"sc_{stem_part}_{idx}"[:64]
            sc = SubChapter(
                id=sc_id,
                chapter_id=chapter.id,
                title=chapter.title,
                description="",
                bvid="",
                cid=0,
                page=1,
                duration=0,
                type=(ch.get("type") or "slide")[:32],
                completed=False,
                sort_order=0,
            )
            session.add(sc)

        await session.commit()
        return course_id


async def seed_courses_if_empty() -> int:
    if not STORAGE_DIR.exists():
        logger.warning("seed: %s missing, skipping", STORAGE_DIR)
        return 0
    if not await _is_empty():
        logger.info("seed: courses table not empty, skipping")
        return 0

    slug_to_id = await _ensure_default_subjects()
    json_files = sorted(STORAGE_DIR.glob("*.json"))
    inserted = 0
    for path in json_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = await _seed_one(payload, slug_to_id)
            if result:
                inserted += 1
        except Exception as e:
            logger.exception("seed: failed %s: %s", path.name, e)
    logger.info("seed: inserted %d / %d courses", inserted, len(json_files))
    return inserted
