"""
Course service layer - CRUD for Subject / Course / Chapter / SubChapter.
Uses async SQLAlchemy sessions.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_sessionmaker
from app.models.course import Subject, Course, Chapter, SubChapter


async def _get_session():
    """Yield an async session."""
    async with get_sessionmaker()() as session:
        yield session


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

async def list_subjects() -> list[Subject]:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            select(Subject)
            .options(
                selectinload(Subject.courses)
                .selectinload(Course.chapters)
                .selectinload(Chapter.subchapters)
            )
            .order_by(Subject.sort_order)
        )
        return result.scalars().all()


async def get_subject(subject_id: str) -> Subject | None:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            select(Subject)
            .where(Subject.id == subject_id)
            .options(selectinload(Subject.courses))
        )
        return result.scalar_one_or_none()


async def create_subject(data: dict[str, Any]) -> Subject:
    async with get_sessionmaker()() as session:
        subject = Subject(
            id=data.get("id") or f"subj_{uuid.uuid4().hex[:8]}",
            name=data["name"],
            slug=data.get("slug") or data["name"],
            icon=data.get("icon", "default"),
            visible=data.get("visible", True),
            sort_order=data.get("sort_order", 0),
        )
        session.add(subject)
        await session.commit()
        await session.refresh(subject)
        return subject


async def update_subject(subject_id: str, data: dict[str, Any]) -> Subject | None:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            select(Subject).where(Subject.id == subject_id)
        )
        subject = result.scalar_one_or_none()
        if not subject:
            return None
        for key, value in data.items():
            if hasattr(subject, key) and value is not None:
                setattr(subject, key, value)
        await session.commit()
        await session.refresh(subject)
        return subject


async def delete_subject(subject_id: str) -> bool:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            delete(Subject).where(Subject.id == subject_id)
        )
        await session.commit()
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

async def get_course(course_id: str) -> Course | None:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(
                selectinload(Course.chapters).selectinload(Chapter.subchapters)
            )
        )
        return result.scalar_one_or_none()


async def create_course(data: dict[str, Any]) -> Course:
    async with get_sessionmaker()() as session:
        course = Course(
            id=data.get("id") or f"course_{uuid.uuid4().hex[:8]}",
            subject_id=data.get("subject_id", ""),
            title=data["title"],
            description=data.get("description", ""),
            bvid=data.get("bvid", ""),
            playlist_url=data.get("playlist_url", ""),
            cover_url=data.get("cover_url", ""),
            author_name=data.get("author_name", ""),
            total_lessons=data.get("total_lessons", 0),
            total_duration=data.get("total_duration", 0),
            progress=data.get("progress", 0.0),
            visible=data.get("visible", True),
            sort_order=data.get("sort_order", 0),
            student_id=data.get("student_id", ""),
            status=data.get("status", "draft"),
        )
        session.add(course)
        await session.commit()
        await session.refresh(course)
        return course


async def update_course(course_id: str, data: dict[str, Any]) -> Course | None:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            select(Course).where(Course.id == course_id)
        )
        course = result.scalar_one_or_none()
        if not course:
            return None
        for key, value in data.items():
            if hasattr(course, key) and value is not None:
                setattr(course, key, value)
        await session.commit()
        await session.refresh(course)
        return course


async def delete_course(course_id: str) -> bool:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            delete(Course).where(Course.id == course_id)
        )
        await session.commit()
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------

async def create_chapter(data: dict[str, Any]) -> Chapter:
    async with get_sessionmaker()() as session:
        chapter = Chapter(
            id=data.get("id") or f"ch_{uuid.uuid4().hex[:8]}",
            course_id=data["course_id"],
            title=data["title"],
            description=data.get("description", ""),
            sort_order=data.get("sort_order", 0),
        )
        session.add(chapter)
        await session.commit()
        await session.refresh(chapter)
        return chapter


async def delete_chapter(chapter_id: str) -> bool:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            delete(Chapter).where(Chapter.id == chapter_id)
        )
        await session.commit()
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# SubChapter
# ---------------------------------------------------------------------------

async def create_subchapter(data: dict[str, Any]) -> SubChapter:
    async with get_sessionmaker()() as session:
        sub = SubChapter(
            id=data.get("id") or f"sc_{uuid.uuid4().hex[:8]}",
            chapter_id=data["chapter_id"],
            title=data["title"],
            description=data.get("description", ""),
            bvid=data.get("bvid", ""),
            cid=data.get("cid", 0),
            page=data.get("page", 1),
            duration=data.get("duration", 0),
            type=data.get("type", "video"),
            sort_order=data.get("sort_order", 0),
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub


async def delete_subchapter(subchapter_id: str) -> bool:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            delete(SubChapter).where(SubChapter.id == subchapter_id)
        )
        await session.commit()
        return result.rowcount > 0
