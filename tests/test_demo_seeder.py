"""Tests for the demo content seeder.

Uses a single sequential test that exercises all behaviors in one session.
This sidesteps pytest-asyncio / SQLAlchemy engine-cache isolation issues that
plague multi-test fixtures in this codebase.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def isolated_demo_dir(tmp_path, monkeypatch):
    """Copy demo/ to a temp dir so test mutations don't pollute the source."""
    src = PROJECT_ROOT / "storage" / "seed" / "demo"
    dst = tmp_path / "demo"
    shutil.copytree(src, dst)
    # Patch DEMO_DIR in demo_seeder to point at the temp copy
    yield dst
    # No cleanup needed — tmp_path is wiped by pytest


def test_seeder_end_to_end(isolated_demo_dir, monkeypatch, tmp_path):
    db_path = tmp_path / "demo_e2e.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    # Reset cached engine + config.
    import app.core.database as db_mod
    import app.core.config as cfg_mod
    db_mod._engine = None
    db_mod._async_sessionmaker = None
    cfg_mod._config = None
    importlib.reload(cfg_mod)
    importlib.reload(db_mod)

    # Patch DEMO_DIR/SEED_DIR in the demo_seeder module.
    import app.services.demo_seeder as demo_seeder
    monkeypatch.setattr(demo_seeder, "DEMO_DIR", isolated_demo_dir)
    monkeypatch.setattr(demo_seeder, "SEED_DIR", isolated_demo_dir)

    from sqlalchemy import select

    from app.core.database import get_sessionmaker, init_db
    from app.models.classroom import ClassroomSession
    from app.models.course import Chapter, Course, SubChapter, Subject

    async def run():
        await init_db()

        # Discover current manifest version (it has been evolved by content authors).
        initial_version = json.loads((isolated_demo_dir / "manifest.json").read_text(encoding="utf-8"))["demo_version"]
        bumped_version = initial_version + "-test"

        # ── Phase 1: empty DB → seeder inserts all demo entities ──
        result = await demo_seeder.seed_demo_if_missing()
        assert result["status"] == "seeded", f"phase1: {result}"
        assert result["version"] == initial_version

        sm = get_sessionmaker()
        async with sm() as s:
            subjects = (await s.execute(select(Subject).where(Subject.is_demo.is_(True)))).scalars().all()
            courses = (await s.execute(select(Course).where(Course.is_demo.is_(True)))).scalars().all()
            chapters = (await s.execute(select(Chapter).where(Chapter.is_demo.is_(True)))).scalars().all()
            subchapters = (await s.execute(select(SubChapter).where(SubChapter.is_demo.is_(True)))).scalars().all()
            sessions = (await s.execute(select(ClassroomSession).where(ClassroomSession.is_demo.is_(True)))).scalars().all()

        assert len(subjects) >= 1, f"expected ≥1 subject, got {len(subjects)}"
        assert len(courses) >= 1, f"expected ≥1 course, got {len(courses)}"
        assert len(chapters) >= 4, f"expected ≥4 chapters, got {len(chapters)}"
        assert len(subchapters) >= 4, f"expected ≥4 subchapters, got {len(subchapters)}"
        assert len(sessions) >= 1, f"expected ≥1 session, got {len(sessions)}"
        assert all(c.lecture for c in chapters), "every chapter must have lecture populated"
        assert all(c.mindmap for c in chapters), "every chapter must have mindmap populated"
        assert sessions[0].slides is not None
        assert sessions[0].student_id == "", "demo session must have no owner"

        # ── Phase 2: idempotency — second call is no-op ──
        result = await demo_seeder.seed_demo_if_missing()
        assert result["status"] == "up-to-date", f"phase2: {result}"
        assert result["version"] == initial_version
        async with sm() as s:
            courses2 = (await s.execute(select(Course).where(Course.is_demo.is_(True)))).scalars().all()
        assert len(courses2) == len(courses)

        # ── Phase 3: insert user data, then version bump → must not touch user rows ──
        async with sm() as s:
            user_course = Course(
                id="user_course_42",
                subject_id="subj_demo_cs",
                title="My Private Course",
                student_id="user_42",
                is_demo=False,
                demo_version="",
            )
            s.add(user_course)
            await s.commit()

        manifest_path = isolated_demo_dir / "manifest.json"
        original = manifest_path.read_text(encoding="utf-8")
        manifest_path.write_text(original.replace(initial_version, bumped_version), encoding="utf-8")
        try:
            result = await demo_seeder.seed_demo_if_missing()
            assert result["status"] == "seeded", f"phase3: {result}"
            assert result["version"] == bumped_version
            async with sm() as s:
                old = (await s.execute(select(Course).where(Course.demo_version == initial_version))).scalars().all()
                new = (await s.execute(select(Course).where(Course.demo_version == bumped_version))).scalars().all()
                user_rows = (await s.execute(select(Course).where(Course.student_id == "user_42"))).scalars().all()
            assert len(old) == 0, f"phase3: old demo rows not dropped: {len(old)}"
            assert len(new) >= 1
            assert len(user_rows) == 1, "user data must NOT be touched"
            assert user_rows[0].id == "user_course_42"
        finally:
            manifest_path.write_text(original, encoding="utf-8")

        # ── Phase 4: missing manifest.json → no-manifest skip ──
        manifest_path = isolated_demo_dir / "manifest.json"
        original = manifest_path.read_text(encoding="utf-8")
        manifest_path.unlink()
        try:
            result = await demo_seeder.seed_demo_if_missing()
            assert result["status"] == "no-manifest", f"phase4: {result}"
        finally:
            manifest_path.write_text(original, encoding="utf-8")

    asyncio.run(run())
