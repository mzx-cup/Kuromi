"""Demo content seeder — reads storage/seed/demo/ JSON files and inserts
Subject / Course / Chapter / SubChapter / ClassroomSession with is_demo=TRUE.

Public API:
    seed_demo_if_missing() -> dict with {status, version, inserted/dropped}

Idempotent: detects demo_version in manifest.json, drops old demo rows on version
bump, and is a no-op when the version already matches.

User-private content is never touched (all operations filter on is_demo=TRUE).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from app.core.database import get_sessionmaker
from app.models.classroom import ClassroomSession
from app.models.course import Chapter, Course, SubChapter, Subject

logger = logging.getLogger("starlearn.demo_seeder")

DEMO_DIR: Path = Path(__file__).resolve().parents[2] / "storage" / "seed" / "demo"

# Backward-compat alias.
SEED_DIR = DEMO_DIR


def _read_json(filename: str) -> dict[str, Any]:
    path = DEMO_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


async def _current_demo_version() -> str | None:
    sm = get_sessionmaker()
    async with sm() as session:
        row = (await session.execute(
            select(Course.demo_version).where(Course.is_demo.is_(True)).limit(1)
        )).first()
        return row[0] if row else None


async def _drop_all_demo_rows() -> int:
    """Remove all existing demo rows from all tables. Returns courses deleted."""
    sm = get_sessionmaker()
    async with sm() as session:
        course_ids = (await session.execute(
            select(Course.id).where(Course.is_demo.is_(True))
        )).scalars().all()
        chapter_ids = (await session.execute(
            select(Chapter.id).where(Chapter.is_demo.is_(True))
        )).scalars().all()
        classroom_ids = (await session.execute(
            select(ClassroomSession.id).where(ClassroomSession.is_demo.is_(True))
        )).scalars().all()
        if classroom_ids:
            await session.execute(delete(ClassroomSession).where(ClassroomSession.id.in_(classroom_ids)))
        if chapter_ids:
            await session.execute(delete(SubChapter).where(SubChapter.chapter_id.in_(chapter_ids)))
            await session.execute(delete(Chapter).where(Chapter.id.in_(chapter_ids)))
        if course_ids:
            await session.execute(delete(Course).where(Course.id.in_(course_ids)))
        await session.execute(delete(Subject).where(Subject.is_demo.is_(True)))
        await session.commit()
        return len(course_ids)


async def _insert_subject(subj_data: dict[str, Any], version: str) -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        existing = (await session.execute(
            select(Subject).where(Subject.id == subj_data["id"])
        )).scalar_one_or_none()
        if existing is not None:
            return
        session.add(Subject(
            id=subj_data["id"],
            name=subj_data["name"],
            slug=subj_data.get("slug", subj_data["id"]),
            icon=subj_data.get("icon", "default"),
            visible=subj_data.get("visible", True),
            sort_order=subj_data.get("sort_order", 0),
            is_demo=True,
            demo_version=version,
        ))
        await session.commit()


async def _insert_course(crs_data: dict[str, Any], subject_id: str, version: str) -> str:
    sm = get_sessionmaker()
    async with sm() as session:
        existing = (await session.execute(
            select(Course).where(Course.id == crs_data["id"])
        )).scalar_one_or_none()
        if existing is not None:
            return existing.id
        outlines = crs_data.get("outlines", [])
        session.add(Course(
            id=crs_data["id"],
            subject_id=subject_id,
            title=crs_data["title"][:256],
            description=crs_data.get("description", "")[:1024],
            bvid=crs_data.get("bvid", ""),
            playlist_url=crs_data.get("playlist_url", ""),
            cover_url=crs_data.get("cover_url", ""),
            author_name=crs_data.get("author_name", "Star-Learn Demo")[:128],
            total_lessons=len(outlines) or crs_data.get("total_lessons", 0),
            total_duration=crs_data.get("total_duration", 0),
            progress=0.0,
            visible=True,
            sort_order=crs_data.get("sort_order", 0),
            student_id="",
            outlines={"items": outlines} if outlines else None,
            status="published",
            is_demo=True,
            demo_version=version,
        ))
        await session.commit()
        return crs_data["id"]


async def _insert_chapters(
    chapters: list[dict[str, Any]],
    course_id: str,
    version: str,
    lectures: dict[str, Any],
    mindmaps: dict[str, Any],
) -> int:
    sm = get_sessionmaker()
    count = 0
    async with sm() as session:
        for ch in chapters:
            ch_id = ch.get("id") or ch.get("chapter_id")
            if not ch_id:
                continue
            existing = (await session.execute(
                select(Chapter).where(Chapter.id == ch_id)
            )).scalar_one_or_none()
            if existing is not None:
                continue
            lecture_ref = ch.get("lecture_ref", "")
            mindmap_ref = ch.get("mindmap_ref", "")
            session.add(Chapter(
                id=ch_id,
                course_id=ch.get("course_id") or course_id,
                title=ch.get("title", ch_id)[:256],
                description=ch.get("description", "")[:1024],
                sort_order=ch.get("sort_order", 0),
                is_demo=True,
                demo_version=version,
                lecture=lectures.get(lecture_ref) if lecture_ref else None,
                mindmap=mindmaps.get(mindmap_ref) if mindmap_ref else None,
            ))
            count += 1
        await session.commit()
    return count


async def _insert_subchapters(subs: list[dict[str, Any]], version: str) -> int:
    sm = get_sessionmaker()
    count = 0
    async with sm() as session:
        for sc in subs:
            if not sc.get("id"):
                continue
            existing = (await session.execute(
                select(SubChapter).where(SubChapter.id == sc["id"])
            )).scalar_one_or_none()
            if existing is not None:
                continue
            session.add(SubChapter(
                id=sc["id"],
                chapter_id=sc.get("chapter_id", ""),
                title=sc.get("title", sc["id"])[:256],
                description=sc.get("description", "")[:1024],
                bvid=sc.get("bvid", ""),
                cid=sc.get("cid", 0),
                page=sc.get("page", 1),
                duration=sc.get("duration", 0),
                type=sc.get("type", "slide")[:32],
                completed=False,
                transcript=sc.get("transcript", ""),
                sort_order=sc.get("sort_order", 0),
                is_demo=True,
                demo_version=version,
            ))
            count += 1
        await session.commit()
    return count


async def _insert_classroom(cr_data: dict[str, Any], version: str) -> int:
    sm = get_sessionmaker()
    async with sm() as session:
        existing = (await session.execute(
            select(ClassroomSession).where(ClassroomSession.id == cr_data["classroom_id"])
        )).scalar_one_or_none()
        if existing is not None:
            return 0
        scenes = cr_data.get("scenes", [])
        session.add(ClassroomSession(
            id=cr_data["classroom_id"],
            student_id="",  # demo: no owner
            course_id=cr_data.get("course_id", ""),
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
            demo_version=version,
            slides={"scenes": scenes, "quiz_pool": cr_data.get("quiz_pool", [])},
        ))
        await session.commit()
    return 1


async def _insert_demo_payload(version: str) -> dict[str, int]:
    """Read all demo JSON files and insert rows.

    Canonical schema (single subject + single course + single classroom):
        course.json:    {subject, course, chapters, subchapters}
        lectures.json:  {lecture_<ch_id>: {...}, ...}
        mindmaps.json:  {mindmap_<ch_id>: {...}, ...}
        classroom.json: {classroom_id, course_id, scenes, quiz_pool}

    Optional additive extension files (auto-detected if present):
        extra_courses.json:    {subjects[], courses[], chapters[], subchapters[]}
        extra_lectures.json:   merged over lectures.json on key conflict
        extra_mindmaps.json:   merged over mindmaps.json on key conflict
        classrooms/*.json:     one file per classroom under SEED_DIR/classrooms/
    """
    course_data = _read_json("course.json")
    lectures = _read_json("lectures.json")
    mindmaps = _read_json("mindmaps.json")
    classroom_data = _read_json("classroom.json")
    extra_courses = _read_json("extra_courses.json")
    extra_lectures = _read_json("extra_lectures.json")
    extra_mindmaps = _read_json("extra_mindmaps.json")

    # Merge lecture / mindmap sources (extra_* overrides base).
    lectures = {**lectures, **extra_lectures}
    mindmaps = {**mindmaps, **extra_mindmaps}

    stats = {"subjects": 0, "courses": 0, "chapters": 0, "subchapters": 0, "classrooms": 0}

    # 1) Subjects: prefer multi (extra_courses.json) then single (course.json)
    if extra_courses and extra_courses.get("subjects"):
        for s in extra_courses["subjects"]:
            await _insert_subject(s, version)
            stats["subjects"] += 1
    elif course_data.get("subject"):
        await _insert_subject(course_data["subject"], version)
        stats["subjects"] = 1

    # 2) Courses
    if extra_courses and extra_courses.get("courses"):
        for c in extra_courses["courses"]:
            await _insert_course(c, c.get("subject_id", ""), version)
            stats["courses"] += 1
    elif course_data.get("course"):
        course_id = await _insert_course(
            course_data["course"], course_data["course"].get("subject_id", ""), version
        )
        stats["courses"] = 1

    # 3) Chapters: extra then legacy (legacy backfills course_id)
    if extra_courses and extra_courses.get("chapters"):
        stats["chapters"] = await _insert_chapters(
            extra_courses["chapters"], "", version, lectures, mindmaps,
        )
    legacy_chapters = course_data.get("chapters", []) if course_data else []
    if legacy_chapters and course_data.get("course"):
        cid = course_data["course"]["id"]
        for ch in legacy_chapters:
            ch.setdefault("course_id", cid)
        stats["chapters"] += await _insert_chapters(
            legacy_chapters, cid, version, lectures, mindmaps,
        )

    # 4) Subchapters
    all_subs: list[dict[str, Any]] = []
    if extra_courses and extra_courses.get("subchapters"):
        all_subs.extend(extra_courses["subchapters"])
    if course_data.get("subchapters"):
        all_subs.extend(course_data["subchapters"])
    stats["subchapters"] = await _insert_subchapters(all_subs, version)

    # 5) Classrooms: single from classroom.json + one per file in classrooms/
    classrooms_list: list[dict[str, Any]] = []
    if classroom_data.get("classroom_id"):
        classrooms_list.append(classroom_data)
    cr_dir = SEED_DIR / "classrooms"
    if cr_dir.exists() and cr_dir.is_dir():
        for path in sorted(cr_dir.glob("*.json")):
            try:
                classrooms_list.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception as exc:
                logger.warning("demo_seeder: failed to read %s: %s", path.name, exc)
    for c_data in classrooms_list:
        stats["classrooms"] += await _insert_classroom(c_data, version)

    logger.info(
        "demo_seeder: seeded %d subjects, %d courses, %d chapters, %d subchapters, %d classrooms",
        stats["subjects"], stats["courses"], stats["chapters"],
        stats["subchapters"], stats["classrooms"],
    )
    return stats


async def seed_demo_if_missing() -> dict[str, Any]:
    """Lifespan entrypoint. Idempotent."""
    manifest = _read_json("manifest.json")
    if not manifest:
        return {"status": "no-manifest"}

    new_version = manifest.get("demo_version")
    if not new_version:
        return {"status": "no-version"}

    cur = await _current_demo_version()
    if cur == new_version:
        return {"status": "up-to-date", "version": new_version}

    dropped = 0
    if cur is not None:
        dropped = await _drop_all_demo_rows()

    stats = await _insert_demo_payload(new_version)
    inserted = stats.get("courses", 0) + stats.get("classrooms", 0)
    return {
        "status": "seeded",
        "version": new_version,
        "inserted": inserted,
        "dropped": dropped,
    }


# Convenience shim used by scripts/seed_demo.py — accept force=True to drop+reinsert.
async def seed_demo_content(force: bool = False) -> dict[str, Any]:
    if force:
        cur = await _current_demo_version()
        if cur is not None:
            await _drop_all_demo_rows()
    return await seed_demo_if_missing()
