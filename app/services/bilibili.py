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


def _cookie_header() -> str:
    """从 settings 里读用户在 .env 配的 B 站 cookie 字符串. 没有就返回空."""
    try:
        from config import settings
        return (settings.bili_cookie or "").strip()
    except Exception:
        return ""


def _client() -> httpx.Client:
    headers = {"User-Agent": USER_AGENT, "Referer": REFERER}
    cookie = _cookie_header()
    if cookie:
        headers["Cookie"] = cookie
    return httpx.Client(
        headers=headers,
        timeout=TIMEOUT,
        follow_redirects=True,
    )

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
    state = _parse_video_state(html, bvid)
    if not state:
        return None

    try:
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

def resolve_aid_cid(bvid: str) -> tuple[int, int] | None:
    """公开接口: 给定 bvid, 自动建好 cookie-injected client 并解析 aid/cid.

    适合给上层 (如 ASR 兜底) 使用 — 调用方不需要自己管 httpx.Client 的
    创建与 cookie 注入. 内部走 _resolve_aid_cid 的全部校验链路."""
    with _client() as cli:
        return _resolve_aid_cid(cli, bvid)


def _resolve_aid_cid(cli: httpx.Client, bvid: str) -> tuple[int, int] | None:
    """优先从 view 接口拿 aid + cid, 失败则尝试从页面 HTML 解析 __INITIAL_STATE__.
    任何一路返回的结果都要双向校验: bvid 字符串相等 + aid 与 view 接口给的一致.
    B站对不存在的 bvid 会重定向到推荐视频, 但 `__INITIAL_STATE__.videoData.bvid`
    仍会回显请求串, 单看 bvid 字符串会被骗; aid 是真实视频身份, 必须用它做最终判定."""
    try:
        r = cli.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
        if r.status_code == 200:
            d = r.json().get("data") or {}
            if d.get("aid") and d.get("cid") and _is_same_video(d.get("bvid", ""), bvid):
                return int(d["aid"]), int(d["cid"])
            elif d.get("aid"):
                logger.warning(
                    "view API 返回的 bvid 与请求不一致 req=%s got=%s, 已忽略",
                    bvid, d.get("bvid"))
    except Exception:
        pass
    try:
        r = cli.get(f"https://www.bilibili.com/video/{bvid}")
        html = r.text
        state = _parse_video_state(html, bvid)
        if state:
            vd = state.get("videoData", {}) or {}
            html_aid = vd.get("aid")
            html_cid = vd.get("cid")
            if html_aid and html_cid:
                # 关键: HTML 里的 aid 不一定属于请求的 bvid (B站重定向到推荐视频时,
                # 解析出的 aid 是被推荐视频的). 用 view API 二次校验.
                try:
                    verify = cli.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
                    if verify.status_code == 200:
                        vd2 = verify.json().get("data") or {}
                        if vd2.get("aid") and int(vd2["aid"]) == int(html_aid):
                            return int(html_aid), int(html_cid)
                        logger.warning(
                            "HTML 解析的 aid=%s 与 view API 返回的 aid=%s 不一致 (req=%s), 拒绝",
                            html_aid, vd2.get("aid"), bvid)
                except Exception:
                    pass
    except Exception:
        pass
    return None


def _parse_video_state(html: str, requested_bvid: str) -> dict | None:
    """从 B 站页面 HTML 解析 __INITIAL_STATE__, 但只在解析出的 videoData.bvid
    与请求一致时才返回. 否则返回 None (防止 B 站重定向/404 时把别的视频
    字幕元数据"借"给我们)."""
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});\s*\(function", html, re.DOTALL)
    if not m:
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});", html, re.DOTALL)
    if not m:
        return None
    try:
        state = json.loads(m.group(1))
    except Exception:
        return None
    vd = state.get("videoData") or {}
    parsed_bvid = vd.get("bvid") or ""
    if not _is_same_video(parsed_bvid, requested_bvid):
        logger.warning(
            "页面 HTML 的 videoData.bvid 与请求不一致 req=%s got=%s, 已忽略",
            requested_bvid, parsed_bvid)
        return None
    return state


def _is_same_video(parsed_bvid: str, requested_bvid: str, *, aid: int | None = None) -> bool:
    """B 站 bv 与 av 是 1:1 映射; 实际工程上只要 bvid 字符串相等就够.
    `aid` 是辅助校验 — 留作未来扩展 (某些接口可能不返回 bvid)."""
    if not parsed_bvid or not requested_bvid:
        return False
    return parsed_bvid.strip().upper() == requested_bvid.strip().upper()


def _scrape_subtitle_list(bvid: str) -> list[dict]:
    """从页面 HTML 的 videoData.subtitle.list 中提取字幕元信息(没有字幕 URL 时也尽量拿到可用信息).
    会校验 videoData.bvid 是否与请求一致, 否则返回空 list (防止借数据)."""
    out = []
    try:
        r = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Referer": REFERER},
            timeout=TIMEOUT,
            follow_redirects=True,
        ).get(f"https://www.bilibili.com/video/{bvid}")
        html = r.text
        state = _parse_video_state(html, bvid)
        if not state:
            return out
        vd = state.get("videoData", {}) or {}
        sub = (vd.get("subtitle") or {}).get("list") or []
        for s in sub:
            url = s.get("subtitle_url") or ""
            if url.startswith("//"):
                url = "https:" + url
            out.append({
                "lang": s.get("lan_doc") or s.get("lan") or "",
                "url": url,
                "ai_type": s.get("ai_type", 0),
                "ai_status": s.get("ai_status", 0),
            })
    except Exception:
        pass
    return out


def _download_subtitle_body(cli: httpx.Client, url: str) -> list[dict]:
    """下载并解析 json 字幕文件 -> [{from, to, content}]."""
    if not url:
        return []
    try:
        r = cli.get(url)
        if r.status_code != 200:
            return []
        body = r.json().get("body") or []
        return [
            {"from": it.get("from", 0), "to": it.get("to", 0), "content": it.get("content", "")}
            for it in body if it.get("content")
        ]
    except Exception:
        return []


def fetch_subtitles(bvid: str) -> list[dict]:
    """Fetch CC/AI subtitles for a B站 video.

    Multi-step strategy (with graceful fallbacks):
      1) player/v2 拿 subtitles[]  (CC, 通常需要登录)
      2) HTML scrape  videoData.subtitle.list 拿 AI 字幕 URL  (不需登录时也能用)
      3) 以上都没有就返回空列表 (调用方会回到课程标题兜底)

    返回 [{lang, url, content: [{from, to, content}], ai_type, source}]"""
    if not bvid:
        return []

    with _client() as cli:
        # Step 0: 解析 aid + cid, 用于 player/v2 备用路径
        aid_cid = _resolve_aid_cid(cli, bvid)

        results: list[dict] = []

        # Step 1: player/v2 (CC) — 用 aid+cid 比纯 bvid 稳定
        url = "https://api.bilibili.com/x/player/v2"
        params = {"bvid": bvid}
        if aid_cid:
            params["aid"] = aid_cid[0]
            params["cid"] = aid_cid[1]
        try:
            r = cli.get(url, params=params)
            if r.status_code == 200:
                d = r.json()
                if d.get("code") == 0:
                    sub_list = d.get("data", {}).get("subtitle", {}).get("subtitles") or []
                    for sub in sub_list:
                        sub_url = sub.get("subtitle_url", "")
                        if sub_url.startswith("//"):
                            sub_url = "https:" + sub_url
                        body = _download_subtitle_body(cli, sub_url)
                        results.append({
                            "lang": sub.get("lan_doc") or sub.get("lan") or "",
                            "url": sub_url,
                            "content": body,
                            "source": "cc",
                            "ai_type": sub.get("ai_type", 0),
                        })
        except Exception:
            pass

        # Step 2: HTML scrape — 找 AI 字幕 (通常字幕 URL 是空的, 但 ai_type 标记存在)
        if not results:
            candidates = _scrape_subtitle_list(bvid)
            for c in candidates:
                body = _download_subtitle_body(cli, c.get("url", ""))
                results.append({
                    "lang": c.get("lang", ""),
                    "url": c.get("url", ""),
                    "content": body,
                    "source": "ai",
                    "ai_type": c.get("ai_type", 0),
                })

        # Step 3: 都没有, 至少尝试描述性 metadata: 返回视频简介+标题, 作为最后兜底
        if not results and aid_cid is None:
            # 防止重复请求
            try:
                r2 = cli.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
                if r2.status_code == 200:
                    d2 = r2.json().get("data") or {}
                    desc = (d2.get("desc") or "").strip()
                    title = (d2.get("title") or "").strip()
                    if desc or title:
                        results.append({
                            "lang": "metadata",
                            "url": "",
                            "content": [
                                {"from": 0, "to": 0, "content": title},
                                {"from": 0, "to": 0, "content": desc},
                            ],
                            "source": "metadata",
                        })
            except Exception:
                pass

        return results
