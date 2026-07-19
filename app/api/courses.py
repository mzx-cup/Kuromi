"""
Course Center API routes.

GET    /api/courses/subjects          -> list subjects with nested courses
POST   /api/courses/subjects          -> create subject
PATCH  /api/courses/subjects/{id}     -> update subject
DELETE /api/courses/subjects/{id}     -> delete subject

GET    /api/courses/courses/{id}      -> get course detail with nested chapters
POST   /api/courses/courses           -> create course
PATCH  /api/courses/courses/{id}      -> update course
DELETE /api/courses/courses/{id}     -> delete course

POST   /api/courses/import-bilibili   -> import Bilibili video as course
POST   /api/courses/import-playlist   -> import Bilibili playlist as course
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.course_service import (
    list_subjects,
    get_subject,
    create_subject,
    update_subject,
    delete_subject,
    get_course,
    create_course,
    update_course,
    delete_course,
)
from app.services.course_import import (
    import_bilibili_video,
    import_bilibili_playlist,
)

logger = logging.getLogger("starlearn.courses_api")
router = APIRouter(prefix="/api/courses")


# ── request / response models ──

class SubjectCreateRequest(BaseModel):
    name: str
    slug: str | None = None
    icon: str = "default"
    visible: bool = True
    sort_order: int = 0


class SubjectUpdateRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    icon: str | None = None
    visible: bool | None = None
    sort_order: int | None = None


class CourseCreateRequest(BaseModel):
    subject_id: str
    title: str
    description: str = ""
    bvid: str = ""
    cover_url: str = ""
    author_name: str = ""
    total_lessons: int = 0
    visible: bool = True
    sort_order: int = 0


class CourseUpdateRequest(BaseModel):
    subject_id: str | None = None
    title: str | None = None
    description: str | None = None
    bvid: str | None = None
    cover_url: str | None = None
    author_name: str | None = None
    total_lessons: int | None = None
    visible: bool | None = None
    sort_order: int | None = None
    progress: float | None = None
    status: str | None = None


class ImportBilibiliRequest(BaseModel):
    bvid: str
    subject_id: str
    course_title: str | None = None


class ImportPlaylistRequest(BaseModel):
    playlist_url: str
    subject_id: str
    course_name: str


# ── helpers ──

def _subject_to_dict(subject) -> dict[str, Any]:
    return {
        "id": subject.id,
        "name": subject.name,
        "slug": subject.slug,
        "icon": subject.icon,
        "visible": subject.visible,
        "sort_order": subject.sort_order,
        "courses": [_course_to_dict(c) for c in subject.courses],
    }


def _course_to_dict(course) -> dict[str, Any]:
    return {
        "id": course.id,
        "subject_id": course.subject_id,
        "title": course.title,
        "description": course.description,
        "bvid": course.bvid,
        "playlist_url": course.playlist_url,
        "cover_url": course.cover_url,
        "author_name": course.author_name,
        "total_lessons": course.total_lessons,
        "total_duration": course.total_duration,
        "progress": course.progress,
        "visible": course.visible,
        "sort_order": course.sort_order,
        "status": course.status,
        "chapters": [_chapter_to_dict(ch) for ch in getattr(course, "chapters", [])],
    }


def _chapter_to_dict(chapter) -> dict[str, Any]:
    return {
        "id": chapter.id,
        "course_id": chapter.course_id,
        "title": chapter.title,
        "description": chapter.description,
        "sort_order": chapter.sort_order,
        "subchapters": [_subchapter_to_dict(sc) for sc in getattr(chapter, "subchapters", [])],
    }


def _subchapter_to_dict(sc) -> dict[str, Any]:
    return {
        "id": sc.id,
        "chapter_id": sc.chapter_id,
        "title": sc.title,
        "bvid": sc.bvid,
        "cid": sc.cid,
        "page": sc.page,
        "duration": sc.duration,
        "type": sc.type,
        "completed": sc.completed,
        "sort_order": sc.sort_order,
    }


# ── routes: subjects ──

@router.get("/subjects")
async def list_subjects_api():
    try:
        subjects = await list_subjects()
        return {"code": 200, "data": [_subject_to_dict(s) for s in subjects]}
    except Exception as e:
        err_str = str(e).lower()
        if "no such table" in err_str or "undefinedtable" in err_str or "no module named 'aiosqlite'" in err_str:
            return {"code": 200, "data": []}
        logger.error(f"[courses] list_subjects failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subjects")
async def create_subject_api(req: SubjectCreateRequest):
    subject = await create_subject(req.model_dump(exclude_unset=True))
    return {"code": 200, "data": _subject_to_dict(subject)}


@router.patch("/subjects/{subject_id}")
async def update_subject_api(subject_id: str, req: SubjectUpdateRequest):
    subject = await update_subject(subject_id, req.model_dump(exclude_unset=True))
    if not subject:
        raise HTTPException(status_code=404, detail="学科不存在")
    return {"code": 200, "data": _subject_to_dict(subject)}


@router.delete("/subjects/{subject_id}")
async def delete_subject_api(subject_id: str):
    ok = await delete_subject(subject_id)
    if not ok:
        raise HTTPException(status_code=404, detail="学科不存在")
    return {"code": 200, "message": "已删除"}


# ── routes: courses ──

@router.get("/courses/{course_id}")
async def get_course_api(course_id: str):
    course = await get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"code": 200, "data": _course_to_dict(course)}


@router.post("/courses")
async def create_course_api(req: CourseCreateRequest):
    course = await create_course(req.model_dump(exclude_unset=True))
    return {"code": 200, "data": _course_to_dict(course)}


@router.patch("/courses/{course_id}")
async def update_course_api(course_id: str, req: CourseUpdateRequest):
    course = await update_course(course_id, req.model_dump(exclude_unset=True))
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"code": 200, "data": _course_to_dict(course)}


@router.delete("/courses/{course_id}")
async def delete_course_api(course_id: str):
    ok = await delete_course(course_id)
    if not ok:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"code": 200, "message": "已删除"}


# ── routes: import ──

@router.post("/import-bilibili")
async def import_bilibili_api(req: ImportBilibiliRequest):
    result = await import_bilibili_video(req.bvid, req.subject_id, req.course_title)
    if not result:
        raise HTTPException(status_code=400, detail="无法解析B站视频")
    return {"code": 200, "data": result}


@router.post("/import-playlist")
async def import_playlist_api(req: ImportPlaylistRequest):
    result = await import_bilibili_playlist(req.playlist_url, req.subject_id, req.course_name)
    if not result:
        raise HTTPException(status_code=400, detail="无法解析B站合集")
    return {"code": 200, "data": result}
