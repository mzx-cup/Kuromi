"""
Bilibili API client - video metadata, search, playlist, subtitles.
Uses httpx to call B站 official APIs, with page-scrape fallback.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse, parse_qs

import httpx

logger = logging.getLogger("starlearn.bilibili")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REFERER = "https://www.bilibili.com"

TIMEOUT = httpx.Timeout(15.0, connect=10.0)

# WBI signing — cached keys and mix table
_wbi_keys: tuple[str, str] | None = None
_WBI_MIX = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


def _fetch_wbi_keys(cli: httpx.Client) -> tuple[str, str]:
    """Fetch img_key and sub_key from B站 nav endpoint."""
    global _wbi_keys
    if _wbi_keys is not None:
        return _wbi_keys
    try:
        r = cli.get("https://api.bilibili.com/x/web-interface/nav")
        if r.status_code == 200:
            data = r.json().get("data", {})
            wbi = data.get("wbi_img", {})
            img_url = wbi.get("img_url", "")
            sub_url = wbi.get("sub_url", "")
            if img_url and sub_url:
                img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
                sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
                _wbi_keys = (img_key, sub_key)
                return _wbi_keys
    except Exception:
        pass
    return ("", "")


def _wbi_sign(params: dict[str, Any], cli: httpx.Client) -> dict[str, Any]:
    """Add wts and w_rid WBI signing params."""
    img_key, sub_key = _fetch_wbi_keys(cli)
    if not img_key or not sub_key:
        return params
    mixin = img_key + sub_key
    mixin_key = "".join(mixin[_WBI_MIX[i]] for i in range(32))
    wts = int(time.time())
    params["wts"] = wts
    sorted_keys = sorted(params.keys())
    query = "&".join(f"{k}={params[k]}" for k in sorted_keys)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = w_rid
    return params


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Referer": REFERER},
        timeout=TIMEOUT,
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def extract_bvid(url: str) -> str | None:
    m = re.search(r"BV[a-zA-Z0-9]{10}", url)
    return m.group(0) if m else None


def _is_json(content_type: str | None) -> bool:
    return bool(content_type and "json" in content_type)


# ---------------------------------------------------------------------------
# parse single video
# ---------------------------------------------------------------------------

def parse_video(url: str) -> dict[str, Any] | None:
    bvid = extract_bvid(url)
    if not bvid:
        return None

    with _client() as cli:
        # try official API first
        r = cli.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0 and data.get("data"):
                return _normalize_video(data["data"])

        # fallback: scrape page for __INITIAL_STATE__
        r2 = cli.get(f"https://www.bilibili.com/video/{bvid}")
        return _scrape_video_page(r2.text, bvid)


def _normalize_video(api_data: dict) -> dict:
    stat = api_data.get("stat", {})
    owner = api_data.get("owner", {})
    pages = api_data.get("pages", [])
    first_page = pages[0] if pages else {}
    cid = first_page.get("cid", api_data.get("cid", 0))

    ugc_season = api_data.get("ugc_season") or {}
    return {
        "bvid": api_data.get("bvid", ""),
        "title": api_data.get("title", ""),
        "description": api_data.get("desc", ""),
        "duration": api_data.get("duration", 0),
        "coverUrl": api_data.get("pic", ""),
        "authorName": owner.get("name", ""),
        "playCount": stat.get("view", 0),
        "tags": _extract_tags(api_data),
        "cid": cid,
        "pages": [
            {"page": p.get("page", 1), "partTitle": p.get("part", ""), "cid": p.get("cid", 0), "duration": p.get("duration", 0)}
            for p in pages
        ],
        "ugcSeasonId": ugc_season.get("id"),
        "ugcSeasonTitle": ugc_season.get("title", ""),
        "ugcSeasonCount": ugc_season.get("ep_count", 0),
        "ugcSeasonMid": ugc_season.get("mid") or owner.get("mid"),
    }


def _extract_tags(api_data: dict) -> list[str]:
    tags = []
    raw = api_data.get("tname", "")
    if raw:
        tags.append(raw)
    for t in api_data.get("tag", []) or []:
        if isinstance(t, dict):
            tags.append(t.get("tag_name", ""))
        elif isinstance(t, str):
            tags.append(t)
    return [t for t in tags if t]


def _scrape_video_page(html: str, bvid: str) -> dict | None:
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});\s*\(function", html, re.DOTALL)
    if not m:
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});", html, re.DOTALL)
    if not m:
        return None

    try:
        state = json.loads(m.group(1))
        vd = state.get("videoData", {})
        if not vd:
            return None
        ugc = vd.get("ugc_season") or {}
        owner = vd.get("owner") or {}
        return {
            "bvid": vd.get("bvid", bvid),
            "title": vd.get("title", ""),
            "description": vd.get("desc", ""),
            "duration": vd.get("duration", 0),
            "coverUrl": vd.get("pic", ""),
            "authorName": owner.get("name", ""),
            "playCount": (vd.get("stat") or {}).get("view", 0),
            "tags": [],
            "cid": vd.get("cid", 0),
            "pages": [
                {"page": p.get("page", 1), "partTitle": p.get("part", ""), "cid": p.get("cid", 0), "duration": p.get("duration", 0)}
                for p in (vd.get("pages") or [])
            ],
            "ugcSeasonId": ugc.get("id"),
            "ugcSeasonTitle": ugc.get("title", ""),
            "ugcSeasonCount": ugc.get("ep_count", 0),
            "ugcSeasonMid": ugc.get("mid") or owner.get("mid"),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def search_videos(keyword: str, page: int = 1, page_size: int = 10) -> dict[str, Any]:
    with _client() as cli:
        params = _wbi_sign({
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
        }, cli)
        r = cli.get(
            "https://api.bilibili.com/x/web-interface/wbi/search/type",
            params=params,
        )
        if r.status_code != 200:
            return {"items": [], "total": 0}

        try:
            data = r.json()
        except Exception:
            return {"items": [], "total": 0}
        if data.get("code") != 0:
            return {"items": [], "total": 0}

        result = data.get("data", {}).get("result", []) or []
        items = []
        for v in result:
            items.append({
                "bvid": v.get("bvid", ""),
                "title": re.sub(r'<.*?>', '', v.get("title", "")),
                "description": v.get("description", ""),
                "duration": _parse_duration(v.get("duration", "")),
                "coverUrl": (v.get("pic") or "").replace("http:", "https:"),
                "authorName": v.get("author", ""),
                "playCount": v.get("play", 0),
                "tags": [v.get("tag", "")] if v.get("tag") else [],
            })

        return {"items": items, "total": data.get("data", {}).get("numResults", len(items))}


def _parse_duration(dur_str: str) -> int:
    """Parse 'MM:SS' or 'HH:MM:SS' to seconds."""
    parts = dur_str.strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


# ---------------------------------------------------------------------------
# playlist / collection / series
# ---------------------------------------------------------------------------

def parse_playlist(url: str) -> list[dict]:
    bvid = extract_bvid(url)
    parsed = urlparse(url)

    with _client() as cli:
        # series (channel/seriesdetail)
        if "seriesdetail" in url or "series" in parsed.path:
            qs = parse_qs(parsed.query)
            sid = (qs.get("sid") or [None])[0]
            series_id = (qs.get("series_id") or [None])[0]
            sid = sid or series_id

            if sid:
                items = _fetch_series(cli, sid)
                if items:
                    return items

        # collection
        if "collectiondetail" in url:
            qs = parse_qs(parsed.query)
            col_id = (qs.get("sid") or qs.get("id") or [None])[0]
            if col_id:
                items = _fetch_collection(cli, col_id)
                if items:
                    return items

        # fallback: multi-page video (multiple "P" within a single BV)
        # also checks ugc_season (B站合集) — video may belong to a collection
        if bvid:
            info = parse_video(url)
            if info:
                if len(info.get("pages", [])) > 1:
                    return [
                        {
                            "bvid": bvid,
                            "title": p["partTitle"] or info["title"],
                            "duration": p.get("duration", 0),
                            "coverUrl": info.get("coverUrl", ""),
                            "authorName": info.get("authorName", ""),
                        }
                        for p in info["pages"]
                    ]

                if info.get("ugcSeasonId"):
                    mid = info.get("ugcSeasonMid")
                    items = _fetch_collection(cli, str(info["ugcSeasonId"]), mid)
                    if items:
                        return items

        # fallback: try space channel (scrape page HTML for embedded episode list)
        if bvid:
            items = _try_space_channel(cli, url)
            if items:
                return items

    return []


def _fetch_series(cli: httpx.Client, series_id: str) -> list[dict]:
    params = _wbi_sign({"series_id": series_id, "pn": 1, "ps": 100}, cli)
    r = cli.get(
        "https://api.bilibili.com/x/series/archives",
        params=params,
    )
    if r.status_code != 200:
        return []
    data = r.json()
    if data.get("code") != 0:
        return []
    archives = data.get("data", {}).get("archives", []) or []
    return [
        {
            "bvid": a.get("bvid", ""),
            "title": a.get("title", ""),
            "duration": a.get("duration", 0),
            "coverUrl": (a.get("pic") or "").replace("http:", "https:"),
            "authorName": (a.get("owner") or {}).get("name", ""),
            "playCount": (a.get("stat") or {}).get("view", 0),
        }
        for a in archives
    ]


def _fetch_collection(cli: httpx.Client, col_id: str, mid: int | None = None, page: int = 1) -> list[dict]:
    api_params: dict[str, Any] = {"season_id": col_id, "page_num": page, "page_size": 30}
    if mid:
        api_params["mid"] = mid
    params = _wbi_sign(api_params, cli)
    r = cli.get(
        "https://api.bilibili.com/x/polymer/space/seasons_archives_list",
        params=params,
    )
    if r.status_code != 200:
        return []
    data = r.json()
    if data.get("code") != 0:
        return []
    archives = data.get("data", {}).get("archives", []) or []
    items = [
        {
            "bvid": a.get("bvid", ""),
            "title": a.get("title", ""),
            "duration": a.get("duration", 0),
            "coverUrl": (a.get("pic") or "").replace("http:", "https:"),
            "authorName": (a.get("owner") or {}).get("name", ""),
        }
        for a in archives
    ]

    total = data.get("data", {}).get("page", {}).get("total", 0)
    if len(items) < total:
        for p in range(2, (total // 30) + 2):
            more = _fetch_collection(cli, col_id, mid, p)
            if more:
                items.extend(more)
            else:
                break
    return items


def _try_space_channel(cli: httpx.Client, url: str) -> list[dict]:
    r = cli.get(url)
    if r.status_code != 200:
        return []
    text = r.text
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});\s*\(function", text, re.DOTALL)
    if not m:
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});", text, re.DOTALL)
    if not m:
        return []
    try:
        state = json.loads(m.group(1))
        section = state.get("sectionEpisodes") or state.get("episodes") or []
        return [
            {
                "bvid": ep.get("bvid", ""),
                "title": ep.get("title", ""),
                "duration": ep.get("duration", 0),
                "coverUrl": (ep.get("cover") or ep.get("pic") or "").replace("http:", "https:"),
                "authorName": "",
            }
            for ep in section
        ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# subtitles
# ---------------------------------------------------------------------------

def fetch_subtitles(bvid: str) -> list[dict]:
    """Fetch CC subtitles for a video. Returns [{lang, url, content: [{from, to, content}]}]."""
    with _client() as cli:
        r = cli.get(f"https://api.bilibili.com/x/player/v2?bvid={bvid}")
        if r.status_code != 200:
            return []

        data = r.json()
        if data.get("code") != 0:
            return []

        subtitle_info = data.get("data", {}).get("subtitle", {}).get("subtitles", []) or []
        results = []
        for sub in subtitle_info:
            sub_url = sub.get("subtitle_url", "")
            if sub_url and sub_url.startswith("//"):
                sub_url = "https:" + sub_url

            content = []
            if sub_url:
                try:
                    r2 = cli.get(sub_url)
                    if r2.status_code == 200:
                        body = r2.json().get("body", [])
                        content = [
                            {
                                "from": item.get("from", 0),
                                "to": item.get("to", 0),
                                "content": item.get("content", ""),
                            }
                            for item in body
                        ]
                except Exception:
                    pass

            results.append({
                "lang": sub.get("lan_doc", sub.get("lan", "")),
                "url": sub_url,
                "content": content,
            })
        return results
