"""
Bilibili import API routes.
POST /parse   - parse a single video URL
POST /search  - keyword search
POST /playlist - parse playlist/collection URL
POST /import  - import videos
POST /import-playlist - import playlist as course
POST /subtitles - fetch CC subtitles
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.bilibili import (
    parse_video,
    search_videos,
    parse_playlist,
    fetch_subtitles,
)

logger = logging.getLogger("starlearn.bilibili_api")
router = APIRouter(prefix="/api/bilibili")


# ── request / response models ──

class ParseRequest(BaseModel):
    url: str


class SearchRequest(BaseModel):
    keyword: str
    page: int = 1
    pageSize: int = 10


class PlaylistRequest(BaseModel):
    url: str


class ImportRequest(BaseModel):
    bvids: list[str]
    autoGenerate: bool = True


class ImportPlaylistRequest(BaseModel):
    bvids: list[str]
    courseName: str = ""
    autoGenerate: bool = True


class SubtitleRequest(BaseModel):
    bvid: str


# ── routes ──

@router.post("/parse")
def parse(req: ParseRequest):
    data = parse_video(req.url)
    if not data:
        return {"code": 404, "message": "无法解析视频", "data": None}
    return {"code": 200, "message": "ok", "data": data}


@router.post("/search")
def search(req: SearchRequest):
    result = search_videos(req.keyword, req.page, req.pageSize)
    return {"code": 200, "message": "ok", "data": result}


@router.post("/playlist")
def playlist(req: PlaylistRequest):
    items = parse_playlist(req.url)
    return {"code": 200, "message": "ok", "data": items}


@router.post("/import")
def import_videos(req: ImportRequest):
    """Import videos as standalone courses. Returns per-bvid results."""
    results = []
    for bvid in req.bvids:
        info = parse_video(f"https://www.bilibili.com/video/{bvid}")
        if info:
            results.append({
                "bvid": bvid,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "duration": info.get("duration", 0),
                "coverUrl": info.get("coverUrl", ""),
                "authorName": info.get("authorName", ""),
                "success": True,
            })
        else:
            results.append({"bvid": bvid, "success": False, "error": "解析失败"})

    return {"code": 200, "message": "ok", "data": {"results": results}}


@router.post("/import-playlist")
def import_playlist(req: ImportPlaylistRequest):
    """Import a playlist as a single course."""
    results = []
    for bvid in req.bvids:
        info = parse_video(f"https://www.bilibili.com/video/{bvid}")
        if info:
            results.append({
                "bvid": bvid,
                "title": info.get("title", ""),
                "duration": info.get("duration", 0),
                "success": True,
            })
        else:
            results.append({"bvid": bvid, "success": False, "error": "解析失败"})

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "courseName": req.courseName,
            "results": results,
        },
    }


@router.post("/subtitles")
def subtitles(req: SubtitleRequest):
    subs = fetch_subtitles(req.bvid)
    return {"code": 200, "message": "ok", "data": subs}
