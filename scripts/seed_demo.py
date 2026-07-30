#!/usr/bin/env python3
"""Manual demo content management CLI.

Usage:
    python scripts/seed_demo.py --check     # print current demo_version vs manifest
    python scripts/seed_demo.py --reset     # drop + re-insert from JSON
    python scripts/seed_demo.py --dump      # export current DB demo rows to JSON
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


async def cmd_check() -> int:
    await init_db()
    cur = await demo_seeder._current_demo_version()
    try:
        manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        manifest = {}
    target = manifest.get("demo_version", "(no manifest)")
    print(f"current:  {cur or '(none)'}")
    print(f"manifest: {target}")
    print(f"status:   {'up-to-date' if cur == target else 'NEEDS SEED'}")
    return 0


async def cmd_reset() -> int:
    await init_db()
    cur = await demo_seeder._current_demo_version()
    if cur is not None:
        dropped = await demo_seeder._drop_all_demo_rows()
        print(f"dropped {dropped} old course(s) at version {cur}")
    result = await demo_seeder._insert_demo_payload(await demo_seeder._current_demo_version() or "0.0.0")
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


def main() -> int:
    p = argparse.ArgumentParser(description="Manage demo content")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="Check current demo version vs manifest")
    g.add_argument("--reset", action="store_true", help="Force re-insert demo from JSON files")
    g.add_argument("--dump", action="store_true", help="Dump current DB demo rows")
    args = p.parse_args()

    if args.check:
        return asyncio.run(cmd_check())
    if args.reset:
        return asyncio.run(cmd_reset())
    if args.dump:
        return asyncio.run(cmd_dump())
    return 1


if __name__ == "__main__":
    sys.exit(main())
