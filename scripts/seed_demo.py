#!/usr/bin/env python3
"""Manual demo content management CLI.

Usage:
    python scripts/seed_demo.py --check             # print current demo_version vs manifest
    python scripts/seed_demo.py --reset             # drop + re-insert from JSON
    python scripts/seed_demo.py --reset --json      # drop + re-insert, output machine-readable JSON
    python scripts/seed_demo.py --dump              # export current DB demo rows to JSON
    python scripts/seed_demo.py --version           # print manifest version only (always JSON)

P0 (Task 9) 新增: --json 选项, 与 --reset 联用输出 {"version": ..., "counts": ...},
                 供验收脚本断言 version/counts 在两次 reset 之间一致.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import get_sessionmaker, init_db
from app.models.classroom import ClassroomSession
from app.models.course import Chapter, Course, SubChapter, Subject
from app.services import demo_seeder
from app.services.demo_seeder import DEMO_DIR


async def cmd_check(as_json: bool = False) -> int:
    await init_db()
    cur = await demo_seeder._current_demo_version()
    try:
        manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        manifest = {}
    target = manifest.get("demo_version", "(no manifest)")
    if as_json:
        print(json.dumps(
            {"current": cur, "manifest": target,
             "up_to_date": cur == target and target != "(no manifest)"},
            ensure_ascii=False,
        ))
    else:
        print(f"current:  {cur or '(none)'}")
        print(f"manifest: {target}")
        print(f"status:   {'up-to-date' if cur == target else 'NEEDS SEED'}")
    return 0


async def cmd_reset(as_json: bool = False) -> int:
    await init_db()
    cur = await demo_seeder._current_demo_version()

    # 读取 manifest 中的目标版本 (与 _drop_all_demo_rows 内部使用一致)
    try:
        manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        manifest = {}
    target_version = manifest.get("demo_version", "0.0.0")

    dropped = 0
    if cur is not None:
        dropped = await demo_seeder._drop_all_demo_rows()
    result = await demo_seeder._insert_demo_payload(target_version)

    if as_json:
        # result 可能是 {status, version, inserted/dropped} 或其他形状; 归一化 counts.
        counts: dict[str, int] = {}
        if isinstance(result, dict):
            for key in ("courses", "chapters", "subchapters", "classrooms"):
                v = result.get(key)
                if isinstance(v, list):
                    counts[key] = len(v)
                elif isinstance(v, int):
                    counts[key] = v
            # 兼容 demo_seeder 既有返回值
            if not counts and "inserted" in result and isinstance(result["inserted"], dict):
                counts = {k: len(v) if isinstance(v, list) else 0
                          for k, v in result["inserted"].items()}
        print(json.dumps(
            {"version": target_version, "dropped": dropped, "counts": counts},
            ensure_ascii=False,
        ))
    else:
        if dropped:
            print(f"dropped {dropped} old course(s) at version {cur}")
        print(f"re-inserted: {result}")
    return 0


async def cmd_dump() -> int:
    await init_db()
    sm = get_sessionmaker()
    async with sm() as s:
        courses = (await s.execute(select(Course).where(Course.is_demo.is_(True)))).scalars().all()
        chapters = (await s.execute(select(Chapter).where(Chapter.is_demo.is_(True)))).scalars().all()
        subchapters = (await s.execute(select(SubChapter).where(SubChapter.is_demo.is_(True)))).scalars().all()
        classrooms = (await s.execute(select(ClassroomSession).where(ClassroomSession.is_demo.is_(True)))).scalars().all()
    out = {
        "courses": [{"id": c.id, "title": c.title, "demo_version": c.demo_version} for c in courses],
        "chapters": [
            {"id": c.id, "course_id": c.course_id, "title": c.title,
             "has_lecture": c.lecture is not None, "has_mindmap": c.mindmap is not None}
            for c in chapters
        ],
        "subchapters": [{"id": s.id, "chapter_id": s.chapter_id} for s in subchapters],
        "classrooms": [
            {
                "id": c.id,
                "course_id": c.course_id,
                "title": (c.course_data or {}).get("title") if isinstance(c.course_data, dict) else "",
                "has_slides": c.slides is not None,
            }
            for c in classrooms
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


async def cmd_version() -> int:
    """仅输出 manifest 的 demo_version, 始终 JSON 格式."""
    try:
        manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        manifest = {}
    print(json.dumps({"version": manifest.get("demo_version", "(no manifest)")}, ensure_ascii=False))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Manage demo content")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="Check current demo version vs manifest")
    g.add_argument("--reset", action="store_true", help="Force re-insert demo from JSON files")
    g.add_argument("--dump", action="store_true", help="Dump current DB demo rows")
    g.add_argument("--version", action="store_true", help="Print manifest demo_version (always JSON)")
    p.add_argument("--json", action="store_true",
                   help="Machine-readable JSON output (with --check or --reset)")
    args = p.parse_args()

    if args.check:
        return asyncio.run(cmd_check(as_json=args.json))
    if args.reset:
        return asyncio.run(cmd_reset(as_json=args.json))
    if args.dump:
        return asyncio.run(cmd_dump())
    if args.version:
        return asyncio.run(cmd_version())
    return 1


if __name__ == "__main__":
    sys.exit(main())
