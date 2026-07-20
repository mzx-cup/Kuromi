"""Demo content seeder — reads storage/seed/demo/ JSON files and inserts
Subject / Course / Chapter / SubChapter / ClassroomSession with is_demo=TRUE.
Idempotent: detects demo_version in manifest.json, drops old demo rows on version bump.
User-private content is never touched (all operations filter on is_demo=TRUE).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select

from app.core.database import get_sessionmaker
from app.models.classroom import ClassroomSession
from app.models.course import Chapter, Course, SubChapter, Subject

logger = logging.getLogger("starlearn.demo_seeder")

SEED_DIR = Path(__file__).resolve().parents[2] / "storage" / "seed" / "demo"


def _read_json(filename: str) -> dict[str, Any]:
    path = SEED_DIR / filename
    if not path.exists():
        logger.warning("demo_seeder: %s missing, skipping demo seed", path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


async def _get_current_demo_version() -> str | None:
    """Return the demo_version of the oldest demo row, or None if no demo data exists."""
    sm = get_sessionmaker()
    async with sm() as session:
        result = await session.execute(
            select(func.min(Subject.demo_version)).where(Subject.is_demo == True)
        )
        return result.scalar_one_or_none()


async def _drop_all_demo_rows():
    """Remove all existing demo rows from all tables."""
    sm = get_sessionmaker()
    async with sm() as session:
        # Order matters for FK constraints
        await session.execute(delete(ClassroomSession).where(ClassroomSession.is_demo == True))
        await session.execute(delete(SubChapter).where(SubChapter.is_demo == True))
        await session.execute(delete(Chapter).where(Chapter.is_demo == True))
        await session.execute(delete(Course).where(Course.is_demo == True))
        await session.execute(delete(Subject).where(Subject.is_demo == True))
        await session.commit()
        logger.info("demo_seeder: dropped all old demo rows")


async def _seed_subject(subject_data: dict[str, Any], demo_version: str) -> str:
    sm = get_sessionmaker()
    async with sm() as session:
        existing = await session.execute(
            select(Subject).where(Subject.id == subject_data["id"])
        )
        if existing.scalar_one_or_none():
            return subject_data["id"]

        subj = Subject(
            id=subject_data["id"],
            name=subject_data["name"],
            slug=subject_data.get("slug", "demo"),
            icon=subject_data.get("icon", "default"),
            visible=subject_data.get("visible", True),
            sort_order=subject_data.get("sort_order", 0),
            is_demo=True,
            demo_version=demo_version,
        )
        session.add(subj)
        await session.commit()
        logger.info("demo_seeder: seeded subject %s", subj.name)
        return subj.id


async def _seed_course(course_data: dict[str, Any], subject_id: str, demo_version: str) -> str:
    sm = get_sessionmaker()
    async with sm() as session:
        existing = await session.execute(
            select(Course).where(Course.id == course_data["id"])
        )
        if existing.scalar_one_or_none():
            return course_data["id"]

        outlines = course_data.get("outlines", [])
        total_lessons = len(outlines) or course_data.get("total_lessons", 0)

        course = Course(
            id=course_data["id"],
            subject_id=subject_id,
            title=course_data["title"][:256],
            description=course_data.get("description", "")[:1024],
            bvid=course_data.get("bvid", ""),
            playlist_url=course_data.get("playlist_url", ""),
            cover_url=course_data.get("cover_url", ""),
            author_name=course_data.get("author_name", "Star-Learn Demo")[:128],
            total_lessons=total_lessons,
            total_duration=course_data.get("total_duration", 0),
            progress=0.0,
            visible=True,
            sort_order=course_data.get("sort_order", 0),
            student_id="",
            outlines={"items": outlines} if outlines else None,
            scenes=course_data.get("scenes"),
            data_json=course_data.get("data_json"),
            status="published",
            is_demo=True,
            demo_version=demo_version,
        )
        session.add(course)
        await session.commit()
        logger.info("demo_seeder: seeded course %s", course.title)
        return course.id


async def _seed_chapters(
    chapters: list[dict[str, Any]],
    course_id: str,
    demo_version: str,
    lectures_data: dict[str, Any],
    mindmaps_data: dict[str, Any],
) -> int:
    sm = get_sessionmaker()
    count = 0
    async with sm() as session:
        for ch_data in chapters:
            existing = await session.execute(
                select(Chapter).where(Chapter.id == ch_data["id"])
            )
            if existing.scalar_one_or_none():
                continue

            lecture_ref = ch_data.get("lecture_ref", "")
            mindmap_ref = ch_data.get("mindmap_ref", "")

            chapter = Chapter(
                id=ch_data["id"],
                course_id=course_id,
                title=ch_data["title"][:256],
                description=ch_data.get("description", "")[:1024],
                sort_order=ch_data.get("sort_order", 0),
                is_demo=True,
                demo_version=demo_version,
                lecture=lectures_data.get(lecture_ref) if lecture_ref else None,
                mindmap=mindmaps_data.get(mindmap_ref) if mindmap_ref else None,
            )
            session.add(chapter)
            count += 1

        await session.commit()
    return count


async def _seed_subchapters(
    subchapters: list[dict[str, Any]],
    demo_version: str,
) -> int:
    sm = get_sessionmaker()
    count = 0
    async with sm() as session:
        for sc_data in subchapters:
            existing = await session.execute(
                select(SubChapter).where(SubChapter.id == sc_data["id"])
            )
            if existing.scalar_one_or_none():
                continue

            sc = SubChapter(
                id=sc_data["id"],
                chapter_id=sc_data["chapter_id"],
                title=sc_data["title"][:256],
                description=sc_data.get("description", "")[:1024],
                bvid=sc_data.get("bvid", ""),
                cid=sc_data.get("cid", 0),
                page=sc_data.get("page", 1),
                duration=sc_data.get("duration", 0),
                type=sc_data.get("type", "slide")[:32],
                completed=False,
                transcript=sc_data.get("transcript", ""),
                sort_order=sc_data.get("sort_order", 0),
                is_demo=True,
                demo_version=demo_version,
            )
            session.add(sc)
            count += 1

        await session.commit()
    return count


async def _seed_classroom_sessions(
    classrooms: list[dict[str, Any]],
    demo_version: str,
) -> int:
    sm = get_sessionmaker()
    count = 0
    async with sm() as session:
        for cr_data in classrooms:
            existing = await session.execute(
                select(ClassroomSession).where(
                    ClassroomSession.id == cr_data["classroom_id"]
                )
            )
            if existing.scalar_one_or_none():
                continue

            scenes = cr_data.get("scenes", [])
            cr = ClassroomSession(
                id=cr_data["classroom_id"],
                student_id="",  # demo: no owner
                course_id=cr_data["course_id"],
                course_data={
                    "title": cr_data.get("title", ""),
                    "teacher_persona": cr_data.get("teacher_persona", "patient_tutor"),
                    "voice_id": cr_data.get("voice_id", ""),
                },
                current_scene_index=0,
                visited_scenes={"visited": []},
                quiz_answers={"answers": {}},
                chat_history={"turns": []},
                time_spent=0,
                status="active",
                teacher_persona=cr_data.get("teacher_persona", "patient_tutor"),
                user_id=None,
                is_demo=True,
                demo_version=demo_version,
                slides={"scenes": scenes, "quiz_pool": cr_data.get("quiz_pool", [])},
            )
            session.add(cr)
            count += 1

        await session.commit()
    return count


async def seed_demo_content(force: bool = False) -> dict[str, int]:
    """Main entry point. Reads seed/demo/*.json and inserts demo data.

    Returns a dict with counts: {subjects, courses, chapters, subchapters, classrooms}
    """
    manifest = _read_json("manifest.json")
    if not manifest:
        logger.info("demo_seeder: no manifest.json, skipping")
        return {}

    new_version = manifest.get("demo_version", "0.0.0")
    current_version = await _get_current_demo_version()

    if not force and current_version == new_version:
        logger.info(
            "demo_seeder: demo version %s already seeded, skipping", new_version
        )
        return {}

    if current_version and current_version != new_version:
        logger.info(
            "demo_seeder: version bump %s -> %s, re-seeding",
            current_version,
            new_version,
        )
        await _drop_all_demo_rows()

    if force:
        logger.info("demo_seeder: force reset")
        await _drop_all_demo_rows()

    # Read all data files
    course_data = _read_json("course.json")
    lectures_data = _read_json("lectures.json")
    mindmaps_data = _read_json("mindmaps.json")
    classroom_data = _read_json("classroom.json")

    if not course_data:
        logger.warning("demo_seeder: course.json missing or empty, skipping")
        return {}

    stats: dict[str, int] = {
        "subjects": 0,
        "courses": 0,
        "chapters": 0,
        "subchapters": 0,
        "classrooms": 0,
    }

    # Courses array (multi-course support)
    courses_list: list[dict[str, Any]]
    if "courses" in course_data:
        # Multi-course format
        courses_list = course_data["courses"]
        subjects_list = course_data.get("subjects", [])
        all_chapters = course_data.get("chapters", [])
        all_subchapters = course_data.get("subchapters", [])
    else:
        # Single-course legacy format
        subject_entry = course_data.get("subject")
        subjects_list = [subject_entry] if subject_entry else []
        course_entry = course_data.get("course")
        courses_list = [course_entry] if course_entry else []
        all_chapters = course_data.get("chapters", [])
        all_subchapters = course_data.get("subchapters", [])

    # Seed subjects
    for subj_data in subjects_list:
        await _seed_subject(subj_data, new_version)
        stats["subjects"] += 1

    # Seed courses
    for crs_data in courses_list:
        await _seed_course(crs_data, crs_data.get("subject_id", ""), new_version)
        stats["courses"] += 1

    # Seed chapters
    stats["chapters"] = await _seed_chapters(
        all_chapters, "", new_version, lectures_data, mindmaps_data
    )

    # Seed subchapters
    stats["subchapters"] = await _seed_subchapters(all_subchapters, new_version)

    # Seed classroom sessions
    classrooms_list: list[dict[str, Any]]
    if "classrooms" in classroom_data:
        classrooms_list = classroom_data["classrooms"]
    else:
        classrooms_list = [classroom_data] if classroom_data.get("classroom_id") else []

    stats["classrooms"] = await _seed_classroom_sessions(
        classrooms_list, new_version
    )

    logger.info(
        "demo_seeder: seeded %d subjects, %d courses, %d chapters, %d subchapters, %d classrooms",
        stats["subjects"],
        stats["courses"],
        stats["chapters"],
        stats["subchapters"],
        stats["classrooms"],
    )
    return stats
