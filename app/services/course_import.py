"""
Course import orchestration: Bilibili video / playlist -> Course hierarchy.

Uses app.services.bilibili to fetch metadata, then creates:
  Subject -> Course -> Chapter -> SubChapter
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.services.bilibili import parse_video, parse_playlist
from app.services.course_service import (
    create_course,
    create_chapter,
    create_subchapter,
    create_subject,
    get_subject,
)

logger = logging.getLogger("starlearn.course_import")

# Mapping: subject_id -> name, slug
_DEFAULT_SUBJECTS = {
    "cs": ("计算机科学", "cs"),
    "math": ("数学", "math"),
    "physics": ("物理学", "physics"),
}


async def _ensure_subject(subject_id: str):
    """Ensure a subject exists in the database, creating it if necessary."""
    subj = await get_subject(subject_id)
    if subj is not None:
        return subj
    name, slug = _DEFAULT_SUBJECTS.get(subject_id, (subject_id, subject_id))
    return await create_subject({"id": subject_id, "name": name, "slug": slug})


async def import_bilibili_video(
    bvid: str,
    subject_id: str,
    course_title: str | None = None,
) -> dict[str, Any] | None:
    """Import a single Bilibili video as a course with one chapter and one subchapter."""
    info = parse_video(f"https://www.bilibili.com/video/{bvid}")
    if not info:
        return None

    await _ensure_subject(subject_id)

    title = course_title or info.get("title", "未命名课程")
    course = await create_course({
        "subject_id": subject_id,
        "title": title,
        "description": info.get("description", ""),
        "bvid": bvid,
        "cover_url": info.get("coverUrl", ""),
        "author_name": info.get("authorName", ""),
        "total_duration": info.get("duration", 0),
        "total_lessons": 1,
        "status": "published",
    })

    chapter = await create_chapter({
        "course_id": course.id,
        "title": "第1章",
        "sort_order": 0,
    })

    pages = info.get("pages", [])
    if pages:
        for idx, page in enumerate(pages):
            await create_subchapter({
                "chapter_id": chapter.id,
                "title": page.get("partTitle") or f"课时 {idx + 1}",
                "bvid": bvid,
                "cid": page.get("cid", 0),
                "page": page.get("page", idx + 1),
                "duration": page.get("duration", 0),
                "sort_order": idx,
            })
    else:
        await create_subchapter({
            "chapter_id": chapter.id,
            "title": info.get("title", "视频"),
            "bvid": bvid,
            "cid": info.get("cid", 0),
            "page": 1,
            "duration": info.get("duration", 0),
            "sort_order": 0,
        })

    return {
        "courseId": course.id,
        "title": course.title,
        "bvid": bvid,
        "lessons": len(pages) or 1,
    }


async def import_bilibili_playlist(
    playlist_url: str,
    subject_id: str,
    course_name: str,
) -> dict[str, Any] | None:
    """Import a Bilibili playlist/series/collection as a course."""
    items = parse_playlist(playlist_url)
    if not items:
        return None

    await _ensure_subject(subject_id)

    course = await create_course({
        "subject_id": subject_id,
        "title": course_name,
        "description": f"从B站合集导入，共 {len(items)} 个视频",
        "playlist_url": playlist_url,
        "cover_url": items[0].get("coverUrl", ""),
        "author_name": items[0].get("authorName", ""),
        "total_lessons": len(items),
        "status": "published",
    })

    chapter = await create_chapter({
        "course_id": course.id,
        "title": "第1章",
        "sort_order": 0,
    })

    for idx, item in enumerate(items):
        bvid = item.get("bvid", "")
        cid = 0
        if bvid:
            try:
                info = parse_video(f"https://www.bilibili.com/video/{bvid}")
                if info:
                    cid = info.get("cid", 0)
            except Exception:
                pass

        await create_subchapter({
            "chapter_id": chapter.id,
            "title": item.get("title", f"课时 {idx + 1}"),
            "bvid": bvid,
            "cid": cid,
            "page": idx + 1,
            "duration": item.get("duration", 0),
            "sort_order": idx,
        })

    return {
        "courseId": course.id,
        "title": course.title,
        "lessons": len(items),
    }
