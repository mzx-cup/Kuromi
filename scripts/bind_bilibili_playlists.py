# -*- coding: utf-8 -*-
"""Bind each 课程中心 course to the highest-played Bilibili playlist (合集).

Strategy
========

1. Read all rows from ``courses`` table (SQLite ``xingshi_v2.db``).
2. For each row whose title is non-empty and ``bvid`` is empty:
   - Extract a search keyword from the title (strip common suffixes like
     "入门" / "教程" / "实战" / "精讲" / "快速" / "零基础" / "速成" /
     "深度解析" / "核心").
   - Call ``bilibili.search_videos(keyword + " 合集")`` and pull the top
     ``SEARCH_PAGE_SIZE * SEARCH_PAGES`` results.
   - For each candidate, fetch its full video info via
     ``bilibili.parse_video(bvid)``.  Filter to candidates that
     belong to a ``ugc_season`` (合集) — that's the playlist marker.
   - Pick the candidate with the highest ``playCount``.
   - Write ``bvid, playlist_url, cover_url, author_name, total_lessons``
     to the courses table.

The script accepts a CLI ``--dry-run`` flag to preview without writing.
Re-running is idempotent: courses whose ``bvid`` is already filled are
skipped (use ``--force`` to re-bind).

CLI
===

    python scripts/bind_bilibili_playlists.py            # bind all
    python scripts/bind_bilibili_playlists.py --dry-run  # preview only
    python scripts/bind_bilibili_playlists.py --force    # re-bind existing
    python scripts/bind_bilibili_playlists.py --course-id course_xxx
                                                        # single course

Output
======

Each line:
    [OK ] course_xxx | Python快速入门 -> BV1xxxx | 播放 1.2M | 合集:《xxx》xx 集
    [SKIP] course_xxx | Python快速入门 | 已有 bvid
    [FAIL] course_xxx | 标题噪声(LLM中间输出) -> 跳过

A summary at the end:
    成功 N | 失败 M | 跳过 K | 已有 L
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

# 允许脚本单独运行（无需启动 uvicorn / fastapi）
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from app.services.bilibili import parse_video, search_videos  # noqa: E402

logger = logging.getLogger("bind_bili")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)

# 课程中心 SQLite — 默认与 ORM 同源
DEFAULT_DB_PATH = _PROJECT_ROOT / "xingshi_v2.db"

# 搜索配置
SEARCH_KEYWORD_SUFFIX = " 合集"     # 拼到搜索词后以偏向合集/系列
SEARCH_PAGE_SIZE = 10               # 每页条数（B站接口上限 50）
SEARCH_PAGES = 1                    # 拉 1 页 = 10 条候选（够挑最高播放了）
TOP_N_PARSE = 4                      # 候选里只解析前 N 条 video metadata

# 标题清洗：剔除 LLM 中间输出噪音、常见修饰词
TITLE_NOISE_RE = re.compile(
    r"<think>.*?</think>",            # LLM think tag
    flags=re.DOTALL,
)
# 通用修饰词 — 不论出现在标题哪个位置都剔除（避免 "Python快速" 这种残片）
MODIFIER_TOKENS = (
    "深度解析", "零基础", "速成课", "速成", "高清", "全集", "合集",
    "入门", "基础", "教程", "实战", "精讲", "精通", "核心",
    "从零", "快速", "一节课", "一集", "学习", "课",
    "掌握", "求职", "编程", "我想",
)

# 单独一个词容易撞到同名内容的关键词（如 Rust 游戏、Go 围棋）
# 搜索时补 "编程" 强制偏向编程内容
AMBIGUOUS_LANG = {"rust", "go", "golang", "c", "r"}

# 编程语境词 — 歧义词命中后还必须带上这些词之一，才算「编程内容」
PROGRAMMING_CONTEXT_RE = re.compile(
    r"(编程|教程|语言|入门|开发|实战|精通|基础|零基础|进阶|学习|讲解|程序员|代码)"
)
MODIFIER_RE = re.compile("|".join(MODIFIER_TOKENS))
PLACEHOLDER_TITLES = {
    "", "课程", "新课", "测试", "默认课程", "untitled",
}


def _clean_title(raw: str) -> str:
    """提取可搜索的关键词。

    - 去掉 ``<think>...</think>`` LLM 中间产物
    - 剔除通用修饰词（"入门"、"零基础"、"实战" 等，位置不限）
    - 截短到 8 字内（B站搜索接口对超长 query 会降权）

    Returns:
        干净的关键词字符串；若标题本身就是噪声（残留 LLM 文本 / 太短 /
        不可用），返回 ``""`` 表示应跳过。
    """
    if not raw:
        return ""
    cleaned = TITLE_NOISE_RE.sub("", raw).strip()
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    # 截短到 12 字（防止 LLM 残留长文本）
    cleaned = cleaned[:12]
    # 反复剔除修饰词（避免残留"Python快速"这种半截）
    while True:
        new_cleaned = MODIFIER_RE.sub("", cleaned).strip()
        if new_cleaned == cleaned:
            break
        cleaned = new_cleaned
    cleaned = cleaned[:8]
    if cleaned in PLACEHOLDER_TITLES:
        return ""
    # 残余的 think/用户提示/JSON 痕迹
    if any(t in cleaned for t in ("<think>", "用户要求", "需求是", "选项：", "生成")):
        return ""
    return cleaned


def _fetch_candidates(keyword: str) -> list[dict]:
    """调用 B 站搜索接口，拉多页并合并。"""
    candidates: list[dict] = []
    for page in range(1, SEARCH_PAGES + 1):
        result = search_videos(keyword, page=page, page_size=SEARCH_PAGE_SIZE)
        items = result.get("items", []) if isinstance(result, dict) else []
        candidates.extend(items)
        if not items:
            break
    return candidates


def _keyword_match(kw: str, text: str) -> bool:
    """关键词是否命中标题（纯 ASCII 短词按整词匹配，防 'C' 撞上一切）。"""
    if not text:
        return False
    if kw.isascii() and len(kw) <= 2:
        return re.search(rf"(?i)(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text) is not None
    return kw.lower() in text.lower()


def _pick_top_playlist(candidates: list[dict], keyword: str,
                       require_context: bool = False) -> dict | None:
    """从候选列表里挑出「播放量最高且属于合集」的视频。

    判定合集：
      - 调用 ``parse_video(bvid)``，检查 ``ugc_season.id`` 是否存在；
      - 否则检查 ``playCount`` 是否 ≥ 1k 且 ``authorName`` 与最高播放候选相同
        （兜底 — B 站搜索结果可能不直接给 ugc_season，但同 UP 主的多视频合集
        也算合集）。

    相关性：候选标题/合集名必须命中关键词，否则视为同名撞车（如 Rust 游戏）。
    ``require_context=True`` 时还必须带编程语境词（排除 Rust 生存游戏等）。
    """
    if not candidates:
        return None

    # 按 playCount 倒序，挨个查 ugc_season
    sorted_cands = sorted(
        candidates, key=lambda c: int(c.get("playCount") or 0), reverse=True,
    )

    def relevant(title: str) -> bool:
        if not _keyword_match(keyword, title):
            return False
        if require_context and not PROGRAMMING_CONTEXT_RE.search(title):
            return False
        return True

    parsed = []  # 收集解析成功且标题命中的候选
    for cand in sorted_cands[:TOP_N_PARSE]:  # 最多查前 N 个，限流 + 控制耗时
        bvid = cand.get("bvid", "")
        if not bvid:
            continue
        try:
            info = parse_video(f"https://www.bilibili.com/video/{bvid}")
        except Exception as e:
            logger.warning("parse_video(%s) failed: %s", bvid, e)
            continue

        if not info:
            continue

        # 相关性：标题或合集名必须命中关键词（+ 可选编程语境）
        if not (relevant(info.get("title", ""))
                or relevant(info.get("ugcSeasonTitle", ""))):
            continue

        parsed.append((cand, info))

    # 优先合集，其次单视频（都经过相关性过滤）
    for cand, info in parsed:
        ugc_id = info.get("ugcSeasonId")
        ugc_count = info.get("ugcSeasonCount", 0)
        if ugc_id and ugc_count and ugc_count >= 2:
            return {
                "bvid": info.get("bvid", cand.get("bvid", "")),
                "playCount": int(cand.get("playCount") or 0),
                "title": info.get("title", ""),
                "author": info.get("authorName", ""),
                "cover": info.get("coverUrl", ""),
                "ugc_season_id": ugc_id,
                "ugc_season_title": info.get("ugcSeasonTitle", ""),
                "ugc_season_count": ugc_count,
                "ugc_season_mid": info.get("ugcSeasonMid"),
            }

    if not parsed:
        return None
    top, info = parsed[0]
    return {
        "bvid": info.get("bvid", top.get("bvid", "")),
        "playCount": int(top.get("playCount") or 0),
        "title": info.get("title", ""),
        "author": info.get("authorName", ""),
        "cover": info.get("coverUrl", ""),
        "ugc_season_id": info.get("ugcSeasonId"),
        "ugc_season_title": info.get("ugcSeasonTitle", ""),
        "ugc_season_count": info.get("ugcSeasonCount", 0),
        "ugc_season_mid": info.get("ugcSeasonMid"),
    }


def _build_playlist_url(best: dict) -> str:
    """构造合集/单视频的播放页 URL。

    - 有 ugc_season_id → 指向 UP 主空间合集页（最贴近"课程合集"语义）
    - 否则 → 指向单视频页
    """
    sid = best.get("ugc_season_id")
    mid = best.get("ugc_season_mid")
    bvid = best.get("bvid", "")
    if sid and mid:
        return f"https://space.bilibili.com/{mid}/channel/collectiondetail?sid={sid}"
    if sid:
        return f"https://www.bilibili.com/video/{bvid}/?p=1"
    return f"https://www.bilibili.com/video/{bvid}"


def _format_count(n: int) -> str:
    """1234567 -> '1.2M'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def bind_one(
    conn: sqlite3.Connection,
    course_id: str,
    title: str,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> str:
    """绑一条课程，返回状态字符串。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT bvid, playlist_url, cover_url, author_name, total_lessons "
        "FROM courses WHERE id = ?",
        (course_id,),
    )
    row = cur.fetchone()
    if row is None:
        return f"[FAIL] {course_id} | 课程不存在"
    cur_bvid = row[0] or ""
    if cur_bvid and not force:
        return f"[SKIP] {course_id} | {title} | 已有 bvid={cur_bvid}"

    keyword = _clean_title(title)
    if not keyword:
        return f"[FAIL] {course_id} | {title[:30]}... | 标题噪声/LLM 中间输出"

    # 歧义词（Rust 游戏 / Go 围棋）优先搜「编程」，并要求候选带编程语境词
    ambiguous = keyword.lower() in AMBIGUOUS_LANG
    queries = [f"{keyword}{SEARCH_KEYWORD_SUFFIX}"]
    if ambiguous:
        queries.insert(0, f"{keyword} 编程")

    best = None
    for query in queries:
        logger.info("[%s] 搜索: %s", course_id, query)
        cands = _fetch_candidates(query)
        if not cands:
            continue
        best = _pick_top_playlist(cands, keyword, require_context=ambiguous)
        if best:
            break

    if not best:
        return f"[FAIL] {course_id} | {title} | 未解析到相关合集"

    bvid = best["bvid"]
    playlist_url = _build_playlist_url(best)
    cover_url = best.get("cover", "")
    author = best.get("author", "")
    total_lessons = best.get("ugc_season_count") or 1

    if not dry_run:
        cur.execute(
            "UPDATE courses SET "
            "bvid = ?, playlist_url = ?, cover_url = ?, author_name = ?, "
            "total_lessons = ?, total_duration = ?, status = 'ready', "
            "visible = 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (bvid, playlist_url, cover_url, author,
             total_lessons, 0, course_id),
        )
        conn.commit()

    play = _format_count(best["playCount"])
    if best.get("ugc_season_id"):
        ugc_label = (
            f"合集《{best['ugc_season_title'] or best['title']}》"
            f"{best['ugc_season_count']} 集"
        )
    else:
        ugc_label = "单视频（兜底）"
    status = "DRY " if dry_run else "OK  "
    return (
        f"[{status}] {course_id} | {title} -> {bvid} | "
        f"播放 {play} | {ugc_label}"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(DEFAULT_DB_PATH),
                    help=f"SQLite path (default: {DEFAULT_DB_PATH})")
    ap.add_argument("--dry-run", action="store_true",
                    help="预览绑定结果，不写入 DB")
    ap.add_argument("--force", action="store_true",
                    help="强制重绑已有 bvid 的课程")
    ap.add_argument("--course-id", default="",
                    help="只处理单个 course_id（用于单点调试）")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="每个课程处理后 sleep 秒数（防 B 站限流）")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        if args.course_id:
            cur.execute(
                "SELECT id, title FROM courses WHERE id = ?",
                (args.course_id,),
            )
            rows = cur.fetchall()
        else:
            cur.execute(
                "SELECT id, title FROM courses "
                "WHERE title IS NOT NULL AND TRIM(title) != '' "
                "ORDER BY id"
            )
            rows = cur.fetchall()

        if not rows:
            sys.exit("No courses to bind.")

        n_ok = n_skip = n_fail = 0
        for cid, title in rows:
            msg = bind_one(
                conn, cid, title,
                force=args.force, dry_run=args.dry_run,
            )
            print(msg, flush=True)
            if msg.startswith("[OK") or msg.startswith("[DRY"):
                n_ok += 1
            elif msg.startswith("[SKIP"):
                n_skip += 1
            else:
                n_fail += 1

            time.sleep(args.delay)

        print()
        print(
            f"汇总: 成功 {n_ok} | 失败 {n_fail} | 跳过 {n_skip} | "
            f"{'DRY-RUN' if args.dry_run else '已写入'}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()