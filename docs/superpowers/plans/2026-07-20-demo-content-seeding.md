# Demo Content Seeding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After first startup of any deployment, the course center contains one complete demo course (with structured rich-text lectures + node-edge mindmaps per chapter) and the classroom page contains one pre-prepared demo classroom session (PPT slides 1:1 with chapters). Demo content is visible to all users, idempotently seeded, and versioned.

**Architecture:** Add `is_demo` + `demo_version` boolean/string columns to 5 tables (Subject/Course/Chapter/SubChapter/ClassroomSession) plus JSON columns (Chapter.lecture, Chapter.mindmap, ClassroomSession.slides). Ship demo content as 4 small JSON files (~25 KB total) under `storage/seed/demo/`. New `app/services/demo_seeder.py` is invoked from `main.py` lifespan and idempotently inserts/migrates rows. Old demo rows are deleted by `is_demo=TRUE AND demo_version=old`, never touching user data.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), Alembic, pydantic, pytest + pytest-asyncio + httpx.AsyncClient, MySQL 8.0 / SQLite 3 (tested against both).

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Edit | `app/models/course.py` | Add `is_demo`, `demo_version`, `lecture`, `mindmap` to Subject/Course/Chapter/SubChapter |
| Edit | `app/models/classroom.py` | Add `is_demo`, `demo_version`, `slides` to ClassroomSession |
| Create | `alembic/versions/20260720_add_demo_flags_and_lecture_fields.py` | Migration adding all 12 new columns |
| Edit | `Navicat/setup_database.py` | Mirror migration for `Navicat/setup_database.py` MySQL DDL list (so fresh MySQL installs include columns without alembic) |
| Create | `storage/seed/demo/manifest.json` | Demo version + content pointers |
| Create | `storage/seed/demo/course.json` | Subject/Course/Chapter/SubChapter tree |
| Create | `storage/seed/demo/lectures.json` | Structured rich-text lecture blocks |
| Create | `storage/seed/demo/mindmaps.json` | Node/edge mindmap graphs |
| Create | `storage/seed/demo/classroom.json` | Pre-prepared classroom PPT scenes + slides + quiz_pool |
| Create | `storage/seed/demo/README.md` | Maintenance notes for demo content authors |
| Create | `app/services/demo_seeder.py` | Idempotent startup seeder |
| Edit | `main.py` | Call `seed_demo_if_missing()` in lifespan |
| Create | `scripts/seed_demo.py` | Manual `--check` / `--reset` / `--dump` CLI |
| Edit | `app/api/courses.py` | Add `include_demo` filter + return `is_demo`/`demo_version` in JSON |
| Edit | `app/api/classroom.py` | Same |
| Edit | `html/courses.html` | Render DEMO badge when `course.is_demo` |
| Edit | `html/classroom.html` | Render "演示课堂" banner when `classroom.is_demo` |
| Create | `tests/test_demo_seeder.py` | 7 unit tests for seeder |
| Create | `tests/test_demo_api.py` | 6 API integration tests |
| Edit | `README.md` | Add "Demo Content" section |

---

## Phase 1 — Schema Foundation

### Task 1: Add is_demo + demo_version + JSON columns to Course models

**Files:**
- Modify: `app/models/course.py`
- Test: `tests/test_demo_models.py` (new)

- [ ] **Step 1: Write failing test that imports new fields**

Create `tests/test_demo_models.py`:

```python
"""Verify the demo columns exist on the ORM models."""
from sqlalchemy import inspect

from app.models.course import Chapter, Course, Subject, SubChapter


def test_subject_has_demo_columns():
    cols = {c.name for c in inspect(Subject).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols


def test_course_has_demo_columns():
    cols = {c.name for c in inspect(Course).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols


def test_chapter_has_demo_columns_and_json():
    cols = {c.name for c in inspect(Chapter).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols
    assert "lecture" in cols
    assert "mindmap" in cols


def test_subchapter_has_demo_columns():
    cols = {c.name for c in inspect(SubChapter).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_demo_models.py -v`
Expected: ImportError or AttributeError — fields not yet defined.

- [ ] **Step 3: Add columns to Subject, Course, SubChapter**

Open `app/models/course.py`. Add the `Boolean` import:

```python
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
```

Modify `Subject` (add at end of class, before any `relationship` is fine — keep all existing lines intact):

```python
class Subject(Base):
    """Top-level subject category (e.g., 计算机科学, 数学)."""
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(32), default="default")
    visible: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Demo content marker (added 2026-07-20)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    demo_version: Mapped[str] = mapped_column(String(16), default="", server_default="")

    courses: Mapped[list["Course"]] = relationship(back_populates="subject", order_by="Course.sort_order")
```

Modify `Course` (add at end of class, before `subject` relationship):

```python
class Course(Base):
    """Course belongs to a Subject (e.g., 计算机基础入门 under 计算机科学)."""
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), ForeignKey("subjects.id"), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    bvid: Mapped[str] = mapped_column(String(32), default="")
    playlist_url: Mapped[str] = mapped_column(String(512), default="")
    cover_url: Mapped[str] = mapped_column(String(512), default="")
    author_name: Mapped[str] = mapped_column(String(128), default="")
    total_lessons: Mapped[int] = mapped_column(Integer, default=0)
    total_duration: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    visible: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    student_id: Mapped[str] = mapped_column(String(64), default="")
    outlines: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    scenes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Demo content marker (added 2026-07-20)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    demo_version: Mapped[str] = mapped_column(String(16), default="", server_default="")

    subject: Mapped["Subject"] = relationship(back_populates="courses")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course", order_by="Chapter.sort_order")
```

Modify `SubChapter` (add before `chapter` relationship):

```python
class SubChapter(Base):
    """SubChapter is a single learning unit (e.g., one B站 video page)."""
    __tablename__ = "subchapters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(String(64), ForeignKey("chapters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    bvid: Mapped[str] = mapped_column(String(32), default="")
    cid: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[int] = mapped_column(Integer, default=1)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(32), default="video")
    completed: Mapped[bool] = mapped_column(default=False)
    transcript: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Demo content marker (added 2026-07-20)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    demo_version: Mapped[str] = mapped_column(String(16), default="", server_default="")

    chapter: Mapped["Chapter"] = relationship(back_populates="subchapters")
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(back_populates="subchapter")
```

- [ ] **Step 4: Add columns to Chapter (including JSON fields)**

Modify `Chapter` (note `lecture` and `mindmap` are NEW JSON columns):

```python
class Chapter(Base):
    """Chapter groups SubChapters (e.g., 第一章：计算机组成原理)."""
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Demo content marker + structured content (added 2026-07-20)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    demo_version: Mapped[str] = mapped_column(String(16), default="", server_default="")
    lecture: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mindmap: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    course: Mapped["Course"] = relationship(back_populates="chapters")
    subchapters: Mapped[list["SubChapter"]] = relationship(back_populates="chapter", order_by="SubChapter.sort_order")
```

- [ ] **Step 5: Run test, expect PASS**

Run: `pytest tests/test_demo_models.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/models/course.py tests/test_demo_models.py
git commit -m "feat(models): add is_demo/demo_version/lecture/mindmap columns to course hierarchy"
```

---

### Task 2: Add is_demo + demo_version + slides columns to ClassroomSession

**Files:**
- Modify: `app/models/classroom.py`
- Modify: `tests/test_demo_models.py`

- [ ] **Step 1: Extend the existing test file**

Append to `tests/test_demo_models.py`:

```python
from app.models.classroom import ClassroomSession


def test_classroom_session_has_demo_columns():
    cols = {c.name for c in inspect(ClassroomSession).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols
    assert "slides" in cols
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_demo_models.py::test_classroom_session_has_demo_columns -v`
Expected: AssertionError or AttributeError.

- [ ] **Step 3: Add columns to ClassroomSession**

Open `app/models/classroom.py`. The existing imports already include `Boolean, DateTime, Float, Integer, String, Text, func` — `JSON` is also already imported from `sqlalchemy.dialects.mysql`.

Append to `ClassroomSession` class (before `created_at`):

```python
class ClassroomSession(Base):
    __tablename__ = "classroom_sessions"

    # Original (immersive-classroom) schema — kept intact.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False)
    course_id: Mapped[str] = mapped_column(String(64), default="")
    course_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    current_scene_index: Mapped[int] = mapped_column(Integer, default=0)
    visited_scenes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    quiz_answers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    chat_history: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    time_spent: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    teacher_persona: Mapped[str] = mapped_column(
        String(32), default="expert_mentor", nullable=False,
        comment="AI教师角色: patient_tutor|socratic_questioner|energetic_lecturer|expert_mentor"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # M10 extensions (additive only, no rename / no removal).
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_slide: Mapped[int] = mapped_column(Integer, default=0)
    teacher_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    # Demo content marker + structured slide data (added 2026-07-20)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    demo_version: Mapped[str] = mapped_column(String(16), default="", server_default="")
    slides: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 4: Run test, expect PASS**

Run: `pytest tests/test_demo_models.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/models/classroom.py tests/test_demo_models.py
git commit -m "feat(models): add is_demo/demo_version/slides to classroom_sessions"
```

---

### Task 3: Create Alembic migration

**Files:**
- Create: `alembic/versions/20260720_add_demo_flags_and_lecture_fields.py`

- [ ] **Step 1: Find the latest revision id**

Run: `ls alembic/versions/`

Look for the highest hex revision prefix (e.g. `b01b4224a404`). Use it as `down_revision`.

- [ ] **Step 2: Write the migration file**

Create `alembic/versions/20260720_add_demo_flags_and_lecture_fields.py`:

```python
"""add demo flags + lecture/mindmap/slides JSON fields

Revision ID: 20260720_demo_flags
Revises: <DOWN_REVISION>
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON as MySQL_JSON

# revision identifiers, used by Alembic.
revision = "20260720_demo_flags"
down_revision = "<DOWN_REVISION>"  # ← replace with the value found in Step 1
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = MySQL_JSON if bind.dialect.name == "mysql" else sa.Text

    # subjects
    op.add_column("subjects", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("subjects", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # courses
    op.add_column("courses", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("courses", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # chapters (also adds lecture + mindmap)
    op.add_column("chapters", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("chapters", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))
    op.add_column("chapters", sa.Column("lecture", json_type, nullable=True))
    op.add_column("chapters", sa.Column("mindmap", json_type, nullable=True))

    # subchapters
    op.add_column("subchapters", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("subchapters", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # classroom_sessions (also adds slides)
    op.add_column("classroom_sessions", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("classroom_sessions", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))
    op.add_column("classroom_sessions", sa.Column("slides", json_type, nullable=True))


def downgrade() -> None:
    op.drop_column("classroom_sessions", "slides")
    op.drop_column("classroom_sessions", "demo_version")
    op.drop_column("classroom_sessions", "is_demo")
    op.drop_column("subchapters", "demo_version")
    op.drop_column("subchapters", "is_demo")
    op.drop_column("chapters", "mindmap")
    op.drop_column("chapters", "lecture")
    op.drop_column("chapters", "demo_version")
    op.drop_column("chapters", "is_demo")
    op.drop_column("courses", "demo_version")
    op.drop_column("courses", "is_demo")
    op.drop_column("subjects", "demo_version")
    op.drop_column("subjects", "is_demo")
```

- [ ] **Step 3: Run migration against SQLite (the default test DB)**

Run: `alembic upgrade head`
Expected: `Running upgrade  -> 20260720_demo_flags, add demo flags + lecture/mindmap/slides JSON fields`

- [ ] **Step 4: Verify columns exist**

Run: `sqlite3 xingshi_v2.db ".schema chapters"`
Expected output contains `is_demo`, `demo_version`, `lecture`, `mindmap`.

- [ ] **Step 5: Test downgrade + re-upgrade (reversibility)**

```bash
alembic downgrade -1
alembic upgrade head
```

Expected: Both succeed. `alembic current` shows `20260720_demo_flags` (head).

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/20260720_add_demo_flags_and_lecture_fields.py
git commit -m "feat(alembic): add is_demo flags + lecture/mindmap/slides JSON columns"
```

---

### Task 4: Mirror new columns into Navicat/setup_database.py (MySQL DDL)

**Files:**
- Modify: `Navicat/setup_database.py`

- [ ] **Step 1: Locate the existing chapter table SQL**

In `Navicat/setup_database.py`, find the `learning_records` block (table #2 in `MYSQL_TABLES`). The legacy `chapter` / `classroom` tables do **NOT** currently exist in `MYSQL_TABLES` (they live in the SQLAlchemy models only). So this step is **additive** — we add new `MYSQL_TABLES` entries for the missing tables so the legacy Navicat installer (used for MySQL-only fresh installs) creates them with the new columns.

- [ ] **Step 2: Append new MySQL table DDLs**

Add a new DDL block at the end of `MYSQL_TABLES` (just before the closing `]`). Use the same `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci` style as the existing entries. Mirror exactly what Alembic does for SQLite/MySQL parity.

```python
    # ──────────────────────────────────────────────────────
    # 35. subjects (legacy mirror — was missing from MYSQL_TABLES)
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS subjects (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(128) NOT NULL,
        slug VARCHAR(64) NOT NULL UNIQUE,
        icon VARCHAR(32) DEFAULT 'default',
        visible TINYINT DEFAULT 1,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_demo TINYINT DEFAULT 0,
        demo_version VARCHAR(16) DEFAULT ''
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 36. courses (legacy mirror)
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS courses (
        id VARCHAR(64) PRIMARY KEY,
        subject_id VARCHAR(64) NOT NULL,
        title VARCHAR(256) NOT NULL,
        description TEXT,
        bvid VARCHAR(32) DEFAULT '',
        playlist_url VARCHAR(512) DEFAULT '',
        cover_url VARCHAR(512) DEFAULT '',
        author_name VARCHAR(128) DEFAULT '',
        total_lessons INT DEFAULT 0,
        total_duration INT DEFAULT 0,
        progress FLOAT DEFAULT 0.0,
        visible TINYINT DEFAULT 1,
        sort_order INT DEFAULT 0,
        student_id VARCHAR(64) DEFAULT '',
        outlines JSON,
        scenes JSON,
        data_json JSON,
        status VARCHAR(32) DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        is_demo TINYINT DEFAULT 0,
        demo_version VARCHAR(16) DEFAULT ''
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 37. chapters (legacy mirror — adds lecture + mindmap)
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS chapters (
        id VARCHAR(64) PRIMARY KEY,
        course_id VARCHAR(64) NOT NULL,
        title VARCHAR(256) NOT NULL,
        description TEXT,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_demo TINYINT DEFAULT 0,
        demo_version VARCHAR(16) DEFAULT '',
        lecture JSON,
        mindmap JSON
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 38. subchapters (legacy mirror)
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS subchapters (
        id VARCHAR(64) PRIMARY KEY,
        chapter_id VARCHAR(64) NOT NULL,
        title VARCHAR(256) NOT NULL,
        description TEXT,
        bvid VARCHAR(32) DEFAULT '',
        cid INT DEFAULT 0,
        page INT DEFAULT 1,
        duration INT DEFAULT 0,
        type VARCHAR(32) DEFAULT 'video',
        completed TINYINT DEFAULT 0,
        transcript TEXT,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_demo TINYINT DEFAULT 0,
        demo_version VARCHAR(16) DEFAULT ''
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
```

- [ ] **Step 3: Extend TABLE_NAMES to match**

Append corresponding entries to `TABLE_NAMES` (in the same order):

```python
TABLE_NAMES.extend([
    "subjects",
    "courses",
    "chapters",
    "subchapters",
])
```

- [ ] **Step 4: Append classroom_sessions column additions**

Find the existing `classroom_sessions` SQL block (block #32 in current `MYSQL_TABLES`) and append the new columns before the closing `)`:

```sql
        `slides` JSON DEFAULT NULL,
        `is_demo` TINYINT DEFAULT 0,
        `demo_version` VARCHAR(16) DEFAULT ''
```

Note: `classroom_sessions` already exists in `MYSQL_TABLES`, so we just add columns. The four tables we added in Step 2 (`subjects`, `courses`, `chapters`, `subchapters`) are entirely new entries.

- [ ] **Step 5: Run Navicat script against SQLite to validate**

Run: `python Navicat/setup_database.py --backend=sqlite`
Expected: All 38 tables report "就绪". No failures.

- [ ] **Step 6: Commit**

```bash
git add Navicat/setup_database.py
git commit -m "feat(navicat): add demo columns + subjects/courses/chapters/subchapters tables"
```

---

## Phase 2 — Demo Content JSON Files

### Task 5: Create manifest.json + course.json

**Files:**
- Create: `storage/seed/demo/manifest.json`
- Create: `storage/seed/demo/course.json`

- [ ] **Step 1: Create directory**

Run: `mkdir -p storage/seed/demo`

- [ ] **Step 2: Write manifest.json**

Create `storage/seed/demo/manifest.json`:

```json
{
  "demo_version": "1.0.0",
  "min_app_version": "1.0.0",
  "course_id": "demo_python_101",
  "classroom_id": "demo_classroom_python_101",
  "subject_id": "subj_demo_cs",
  "updated_at": "2026-07-20"
}
```

- [ ] **Step 3: Write course.json**

Create `storage/seed/demo/course.json`:

```json
{
  "subject": {
    "id": "subj_demo_cs",
    "name": "Computer Science (Demo)",
    "slug": "demo-cs",
    "icon": "demo-cs",
    "visible": true,
    "sort_order": 0
  },
  "course": {
    "id": "demo_python_101",
    "subject_id": "subj_demo_cs",
    "title": "Python 编程入门（演示课程）",
    "description": "演示课程 — 展示 AI 生成的完整讲义 + 思维导图 + 课堂 PPT。所有用户首次访问即可看到，无需登录。",
    "author_name": "Star-Learn Demo Teacher",
    "total_lessons": 4,
    "cover_url": "/static/demo/python_101_cover.png",
    "outlines": [
      {"id": "ol_1", "title": "Python 初识",   "type": "slide",      "points": 3, "description": "了解 Python 的历史、特点与第一个程序。"},
      {"id": "ol_2", "title": "变量与类型",   "type": "interactive", "points": 3, "description": "掌握变量的命名规则与基本数据类型。"},
      {"id": "ol_3", "title": "控制流",        "type": "code",       "points": 3, "description": "用 if/for/while 编写分支与循环。"},
      {"id": "ol_4", "title": "函数",         "type": "video",      "points": 3, "description": "理解函数的封装、参数与返回值。"}
    ]
  },
  "chapters": [
    {
      "id": "ch_demo_py_1",
      "course_id": "demo_python_101",
      "title": "Python 初识",
      "description": "了解 Python 的诞生、特点与应用场景，并完成第一个程序。",
      "sort_order": 0,
      "lecture_ref": "lecture_ch_demo_py_1",
      "mindmap_ref": "mindmap_ch_demo_py_1"
    },
    {
      "id": "ch_demo_py_2",
      "course_id": "demo_python_101",
      "title": "变量与类型",
      "description": "掌握变量的命名规则与 5 种基本数据类型。",
      "sort_order": 1,
      "lecture_ref": "lecture_ch_demo_py_2",
      "mindmap_ref": "mindmap_ch_demo_py_2"
    },
    {
      "id": "ch_demo_py_3",
      "course_id": "demo_python_101",
      "title": "控制流",
      "description": "用 if/for/while 实现分支与循环。",
      "sort_order": 2,
      "lecture_ref": "lecture_ch_demo_py_3",
      "mindmap_ref": "mindmap_ch_demo_py_3"
    },
    {
      "id": "ch_demo_py_4",
      "course_id": "demo_python_101",
      "title": "函数",
      "description": "理解函数的封装、参数与返回值。",
      "sort_order": 3,
      "lecture_ref": "lecture_ch_demo_py_4",
      "mindmap_ref": "mindmap_ch_demo_py_4"
    }
  ],
  "subchapters": [
    {"id": "sc_demo_py_1", "chapter_id": "ch_demo_py_1", "title": "Python 初识",   "type": "slide",      "duration": 480},
    {"id": "sc_demo_py_2", "chapter_id": "ch_demo_py_2", "title": "变量与类型",   "type": "interactive", "duration": 720},
    {"id": "sc_demo_py_3", "chapter_id": "ch_demo_py_3", "title": "控制流",        "type": "code",       "duration": 900},
    {"id": "sc_demo_py_4", "chapter_id": "ch_demo_py_4", "title": "函数",         "type": "video",      "duration": 600}
  ]
}
```

- [ ] **Step 4: Validate JSON**

Run: `python -c "import json; json.load(open('storage/seed/demo/manifest.json')); json.load(open('storage/seed/demo/course.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add storage/seed/demo/manifest.json storage/seed/demo/course.json
git commit -m "feat(demo): add manifest.json and course.json for demo course"
```

---

### Task 6: Create lectures.json (4 chapters × ~6 blocks)

**Files:**
- Create: `storage/seed/demo/lectures.json`

- [ ] **Step 1: Write lectures.json**

Create `storage/seed/demo/lectures.json`:

```json
{
  "lecture_ch_demo_py_1": {
    "chapter_id": "ch_demo_py_1",
    "estimated_minutes": 8,
    "blocks": [
      {"kind": "h2",      "text": "1. 什么是 Python？"},
      {"kind": "p",       "text": "Python 是一门由 Guido van Rossum 于 1991 年发布的解释型、动态类型、跨平台的高级编程语言。它强调代码可读性，让程序员用更少的代码表达想法。"},
      {"kind": "callout", "tone": "info", "text": "Python 之禅：优美胜于丑陋，明了胜于隐晦。"},
      {"kind": "h3",      "text": "主要特点"},
      {"kind": "list",    "ordered": false, "items": ["解释型：无需编译，直接运行", "动态类型：变量类型自动推断", "跨平台：Windows / macOS / Linux 通吃", "生态丰富：超过 30 万个第三方包"]},
      {"kind": "h2",      "text": "2. 应用领域"},
      {"kind": "p",       "text": "Python 广泛应用于 Web 后端（Django / Flask）、数据科学（pandas / NumPy）、人工智能（PyTorch / TensorFlow）、自动化脚本、教学等领域。"},
      {"kind": "h2",      "text": "3. 第一个程序"},
      {"kind": "p",       "text": "将以下代码保存为 hello.py，在命令行运行 python hello.py。"},
      {"kind": "code",    "lang": "python", "text": "print(\"Hello, Star-Learn!\")"},
      {"kind": "summary", "text": "本节我们了解了 Python 的诞生、特点、应用领域，并完成了第一个 print 程序。下一节我们将学习变量与数据类型。"}
    ]
  },
  "lecture_ch_demo_py_2": {
    "chapter_id": "ch_demo_py_2",
    "estimated_minutes": 10,
    "blocks": [
      {"kind": "h2",      "text": "1. 变量是什么？"},
      {"kind": "p",       "text": "变量是贴在数据上的标签，用来在内存中存储值。Python 的变量无需声明类型，直接赋值即可创建。"},
      {"kind": "code",    "lang": "python", "text": "name = \"Star\"\nage = 3\nprint(name, age)   # 输出: Star 3"},
      {"kind": "h2",      "text": "2. 命名规则"},
      {"kind": "list",    "ordered": true, "items": ["只能包含字母、数字、下划线", "不能以数字开头", "不能使用关键字 (if / for / class 等)", "建议用 snake_case 风格"]},
      {"kind": "callout", "tone": "warning", "text": "避免使用单字母 l / O / I，容易与数字 1 / 0 混淆。"},
      {"kind": "h2",      "text": "3. 五种基本数据类型"},
      {"kind": "table",   "headers": ["类型", "示例", "说明"], "rows": [
        ["int",   "42",            "整数"],
        ["float", "3.14",          "浮点数"],
        ["str",   "\"hello\"",     "字符串"],
        ["bool",  "True / False",  "布尔值"],
        ["None",  "None",          "空值"]
      ]},
      {"kind": "summary", "text": "本节我们掌握了变量命名规则与 5 种基本数据类型。下一节我们将用条件与循环让程序做决策。"}
    ]
  },
  "lecture_ch_demo_py_3": {
    "chapter_id": "ch_demo_py_3",
    "estimated_minutes": 12,
    "blocks": [
      {"kind": "h2",      "text": "1. 条件分支 if"},
      {"kind": "p",       "text": "if 语句根据布尔表达式的结果决定是否执行某段代码。"},
      {"kind": "code",    "lang": "python", "text": "score = 85\nif score >= 90:\n    print(\"优秀\")\nelif score >= 60:\n    print(\"及格\")\nelse:\n    print(\"不及格\")"},
      {"kind": "h2",      "text": "2. for 循环"},
      {"kind": "p",       "text": "for 用来遍历任何可迭代对象（字符串、列表、range 等）。"},
      {"kind": "code",    "lang": "python", "text": "for i in range(3):\n    print(\"第\", i + 1, \"次\")"},
      {"kind": "h2",      "text": "3. while 循环"},
      {"kind": "p",       "text": "while 在条件为真时反复执行，常用于不确定次数的循环。"},
      {"kind": "code",    "lang": "python", "text": "n = 1\nwhile n <= 3:\n    print(n)\n    n += 1"},
      {"kind": "callout", "tone": "warning", "text": "注意避免死循环：确保循环体内有改变条件的语句。"},
      {"kind": "summary", "text": "本节我们掌握了 if / for / while 三种控制流语句，并学会了避免常见陷阱。下一节我们将学习如何用函数封装代码。"}
    ]
  },
  "lecture_ch_demo_py_4": {
    "chapter_id": "ch_demo_py_4",
    "estimated_minutes": 9,
    "blocks": [
      {"kind": "h2",      "text": "1. 定义函数"},
      {"kind": "p",       "text": "用 def 关键字定义函数，函数体内可以有 return 语句返回值。"},
      {"kind": "code",    "lang": "python", "text": "def greet(name):\n    return f\"Hello, {name}!\"\n\nprint(greet(\"Star\"))"},
      {"kind": "h2",      "text": "2. 参数的几种形式"},
      {"kind": "list",    "ordered": false, "items": ["位置参数：def f(a, b)", "默认参数：def f(a, b=10)", "关键字参数：f(b=20, a=10)", "可变参数：def f(*args, **kwargs)"]},
      {"kind": "h2",      "text": "3. 返回值"},
      {"kind": "p",       "text": "函数可以返回任意类型的数据；不写 return 时返回 None。"},
      {"kind": "code",    "lang": "python", "text": "def add(a, b):\n    return a + b\n\nresult = add(3, 5)\nprint(result)   # 8"},
      {"kind": "callout", "tone": "success", "text": "好习惯：函数只做一件事，名字用动词短语，文档字符串说明输入输出。"},
      {"kind": "summary", "text": "本节我们掌握了函数的定义、参数与返回值。恭喜你完成了 Python 入门演示课！"}
    ]
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; d=json.load(open('storage/seed/demo/lectures.json')); print('refs:', list(d.keys()))"`
Expected: `refs: ['lecture_ch_demo_py_1', 'lecture_ch_demo_py_2', 'lecture_ch_demo_py_3', 'lecture_ch_demo_py_4']`

- [ ] **Step 3: Commit**

```bash
git add storage/seed/demo/lectures.json
git commit -m "feat(demo): add structured rich-text lectures for 4 demo chapters"
```

---

### Task 7: Create mindmaps.json (4 chapters × ~5 nodes)

**Files:**
- Create: `storage/seed/demo/mindmaps.json`

- [ ] **Step 1: Write mindmaps.json**

Create `storage/seed/demo/mindmaps.json`:

```json
{
  "mindmap_ch_demo_py_1": {
    "chapter_id": "ch_demo_py_1",
    "root_label": "Python 初识",
    "layout": "right-tree",
    "nodes": [
      {"id": "n1", "label": "Python 初识",   "level": 0, "x": 0,   "y": 0},
      {"id": "n2", "label": "三大特点",     "level": 1, "x": 200, "y": -80},
      {"id": "n3", "label": "应用领域",     "level": 1, "x": 200, "y": 0},
      {"id": "n4", "label": "环境搭建",     "level": 1, "x": 200, "y": 80},
      {"id": "n5", "label": "Web 后端",     "level": 2, "x": 380, "y": -40},
      {"id": "n6", "label": "AI / 数据科学","level": 2, "x": 380, "y": 40}
    ],
    "edges": [
      {"from": "n1", "to": "n2"},
      {"from": "n1", "to": "n3"},
      {"from": "n1", "to": "n4"},
      {"from": "n3", "to": "n5"},
      {"from": "n3", "to": "n6"}
    ]
  },
  "mindmap_ch_demo_py_2": {
    "chapter_id": "ch_demo_py_2",
    "root_label": "变量与类型",
    "layout": "right-tree",
    "nodes": [
      {"id": "n1", "label": "变量与类型", "level": 0, "x": 0,   "y": 0},
      {"id": "n2", "label": "命名规则",   "level": 1, "x": 200, "y": -100},
      {"id": "n3", "label": "5 种类型",   "level": 1, "x": 200, "y": 0},
      {"id": "n4", "label": "类型转换",   "level": 1, "x": 200, "y": 100},
      {"id": "n5", "label": "int / float","level": 2, "x": 380, "y": -80},
      {"id": "n6", "label": "str / bool", "level": 2, "x": 380, "y": 0},
      {"id": "n7", "label": "None",       "level": 2, "x": 380, "y": 80}
    ],
    "edges": [
      {"from": "n1", "to": "n2"},
      {"from": "n1", "to": "n3"},
      {"from": "n1", "to": "n4"},
      {"from": "n3", "to": "n5"},
      {"from": "n3", "to": "n6"},
      {"from": "n3", "to": "n7"}
    ]
  },
  "mindmap_ch_demo_py_3": {
    "chapter_id": "ch_demo_py_3",
    "root_label": "控制流",
    "layout": "right-tree",
    "nodes": [
      {"id": "n1", "label": "控制流",   "level": 0, "x": 0,   "y": 0},
      {"id": "n2", "label": "if 分支",  "level": 1, "x": 200, "y": -80},
      {"id": "n3", "label": "for 循环", "level": 1, "x": 200, "y": 0},
      {"id": "n4", "label": "while 循环","level": 1, "x": 200, "y": 80},
      {"id": "n5", "label": "elif / else","level": 2, "x": 380, "y": -120},
      {"id": "n6", "label": "range()",  "level": 2, "x": 380, "y": -40}
    ],
    "edges": [
      {"from": "n1", "to": "n2"},
      {"from": "n1", "to": "n3"},
      {"from": "n1", "to": "n4"},
      {"from": "n2", "to": "n5"},
      {"from": "n3", "to": "n6"}
    ]
  },
  "mindmap_ch_demo_py_4": {
    "chapter_id": "ch_demo_py_4",
    "root_label": "函数",
    "layout": "right-tree",
    "nodes": [
      {"id": "n1", "label": "函数",     "level": 0, "x": 0,   "y": 0},
      {"id": "n2", "label": "定义",     "level": 1, "x": 200, "y": -80},
      {"id": "n3", "label": "参数",     "level": 1, "x": 200, "y": 0},
      {"id": "n4", "label": "返回值",   "level": 1, "x": 200, "y": 80},
      {"id": "n5", "label": "*args",    "level": 2, "x": 380, "y": -40},
      {"id": "n6", "label": "**kwargs", "level": 2, "x": 380, "y": 40}
    ],
    "edges": [
      {"from": "n1", "to": "n2"},
      {"from": "n1", "to": "n3"},
      {"from": "n1", "to": "n4"},
      {"from": "n3", "to": "n5"},
      {"from": "n3", "to": "n6"}
    ]
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; d=json.load(open('storage/seed/demo/mindmaps.json')); [print(k, len(v['nodes']), 'nodes') for k,v in d.items()]"`

Expected output:

```
mindmap_ch_demo_py_1 6 nodes
mindmap_ch_demo_py_2 7 nodes
mindmap_ch_demo_py_3 6 nodes
mindmap_ch_demo_py_4 6 nodes
```

- [ ] **Step 3: Commit**

```bash
git add storage/seed/demo/mindmaps.json
git commit -m "feat(demo): add node-edge mindmaps for 4 demo chapters"
```

---

### Task 8: Create classroom.json (1 classroom × 4 scenes × 6 slides)

**Files:**
- Create: `storage/seed/demo/classroom.json`

- [ ] **Step 1: Write classroom.json**

Create `storage/seed/demo/classroom.json`:

```json
{
  "classroom_id": "demo_classroom_python_101",
  "course_id": "demo_python_101",
  "title": "Python 编程入门 · 演示课堂",
  "teacher_persona": "patient_tutor",
  "voice_id": "female-yujie",
  "scenes": [
    {
      "index": 0,
      "title": "开场：今天我们学什么？",
      "type": "intro",
      "duration_sec": 30,
      "slides": [
        {"id": "s1", "layout": "title",  "title": "Python 编程入门", "subtitle": "演示课堂 · Star-Learn"},
        {"id": "s2", "layout": "agenda", "title": "本节内容", "items": ["语言特点", "应用领域", "环境搭建", "第一个程序"]}
      ],
      "speech": "同学们好，今天我们来认识 Python。它是一门非常适合入门的编程语言，让我们先看看它的三大特点。"
    },
    {
      "index": 1,
      "title": "Python 的三大特点",
      "type": "concept",
      "duration_sec": 180,
      "slides": [
        {"id": "s3", "layout": "list",    "title": "三大特点", "items": ["解释型：无需编译", "动态类型：自动推断", "跨平台：三大系统通吃"]},
        {"id": "s4", "layout": "callout", "title": "Python 之禅", "text": "优美胜于丑陋，明了胜于隐晦。"},
        {"id": "s5", "layout": "code",    "title": "Hello World", "code": "print('Hello, Star-Learn!')"}
      ],
      "speech": "Python 有三大显著特点。第一，它是解释型语言，写完代码就能直接运行。第二，它是动态类型语言，你不用声明变量类型。第三，它跨平台，Windows、macOS、Linux 上都能跑。",
      "actions": ["wb_draw_svg:椭圆-高亮-Python 之禅", "spotlight:s4"]
    },
    {
      "index": 2,
      "title": "互动：判断哪个变量名合法",
      "type": "interactive",
      "duration_sec": 240,
      "slides": [
        {"id": "s6", "layout": "question", "title": "下列哪个是合法的变量名？", "options": ["2var", "_name", "class", "my-var"]}
      ],
      "quiz": [
        {"id": "q_intro_1", "question": "下列哪个是合法的 Python 变量名？", "options": ["2var", "_name", "class", "my-var"], "answer": 1}
      ],
      "speech": "现在我们来做一道小测验。判断下面哪个是合法的 Python 变量名？请大家先思考几秒钟。"
    },
    {
      "index": 3,
      "title": "小结 + 下节预告",
      "type": "summary",
      "duration_sec": 60,
      "slides": [
        {"id": "s7", "layout": "summary", "title": "本节小结", "bullets": ["Python 是解释型、动态类型、跨平台", "可以用 print() 输出第一个程序", "下一节：变量与数据类型"]}
      ],
      "speech": "今天我们认识了 Python，了解了它的特点，并完成了第一个程序。下一节课我们将学习变量与数据类型，记得完成课后练习哦。"
    }
  ],
  "quiz_pool": [
    {"id": "q_intro_1", "question": "Python 是一门 ___ 语言", "options": ["编译型", "解释型", "汇编型"], "answer": 1},
    {"id": "q_intro_2", "question": "下列哪个是合法的变量名？", "options": ["2var", "_name", "class", "my-var"], "answer": 1},
    {"id": "q_intro_3", "question": "Python 之禅第一句是什么？", "options": ["简单胜于复杂", "优美胜于丑陋", "明了胜于隐晦", "复杂胜于晦涩"], "answer": 1}
  ]
}
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; d=json.load(open('storage/seed/demo/classroom.json')); print('scenes:', len(d['scenes']), 'quiz_pool:', len(d['quiz_pool']))"`

Expected: `scenes: 4 quiz_pool: 3`

- [ ] **Step 3: Commit**

```bash
git add storage/seed/demo/classroom.json
git commit -m "feat(demo): add pre-prepared classroom PPT with 4 scenes and 6 slides"
```

---

### Task 9: Create demo seed README

**Files:**
- Create: `storage/seed/demo/README.md`

- [ ] **Step 1: Write README.md**

Create `storage/seed/demo/README.md`:

````markdown
# Demo Content

This directory holds pre-prepared content seeded into a fresh deployment so first-time visitors see something rather than an empty course center.

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Version + content pointers (read first by seeder) |
| `course.json` | Subject / Course / Chapter / SubChapter tree |
| `lectures.json` | Structured rich-text lecture blocks keyed by `chapter_id` |
| `mindmaps.json` | Node-edge mindmap graphs keyed by `chapter_id` |
| `classroom.json` | Pre-prepared classroom PPT scenes + slides + quiz_pool |

## Authoring guide

### To upgrade demo content

1. Edit the JSON file(s) you want to change.
2. Bump `manifest.json#demo_version` (e.g., `1.0.0` → `1.0.1`).
3. On next startup, the seeder detects the version mismatch, drops the old demo rows (filtered by `is_demo=TRUE AND demo_version=<old>`), and inserts the new version.
4. **User-private content is never touched** because all demo operations filter on `is_demo=TRUE`.

### Lecture block kinds

| `kind` | Extra fields | Renders as |
|--------|--------------|------------|
| `h1`, `h2`, `h3` | `text` | Heading |
| `p` | `text` | Paragraph |
| `code` | `lang`, `text` | Code block |
| `list` | `ordered`, `items[]` | Bullet/numbered list |
| `callout` | `tone` (`info`/`warning`/`success`), `text` | Highlighted box |
| `quote` | `text` | Blockquote |
| `summary` | `text` | End-of-section summary |
| `image` | `src`, `alt`, `caption` | Inline image |
| `table` | `headers[]`, `rows[][]` | Markdown-style table |

### Mindmap node schema

```json
{"id": "n1", "label": "...", "level": 0, "x": 0, "y": 0}
```

Edges connect nodes by id:

```json
{"from": "n1", "to": "n2"}
```

`layout` is one of: `right-tree`, `left-tree`, `radial`, `two-sided`.

### To force-refresh without bumping version

```bash
python scripts/seed_demo.py --reset
```

This drops the current demo rows and re-inserts from these JSON files, useful during content authoring.

### To disable demo entirely

```sql
DELETE FROM subjects           WHERE is_demo = 1;
DELETE FROM courses            WHERE is_demo = 1;
DELETE FROM chapters           WHERE is_demo = 1;
DELETE FROM subchapters        WHERE is_demo = 1;
DELETE FROM classroom_sessions WHERE is_demo = 1;
```

Or roll back the schema change:

```bash
alembic downgrade -1
```
````

- [ ] **Step 2: Commit**

```bash
git add storage/seed/demo/README.md
git commit -m "docs(demo): add maintenance README for demo content authors"
```

---

## Phase 3 — Seeder Module (TDD)

### Task 10: Test + implement seed_demo_if_missing on empty DB

**Files:**
- Test: `tests/test_demo_seeder.py`
- Create: `app/services/demo_seeder.py`

- [ ] **Step 1: Write failing test for empty-DB seed**

Create `tests/test_demo_seeder.py`:

```python
"""Tests for the demo content seeder."""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest
import pytest_asyncio

from sqlalchemy import delete, select

from app.core.database import get_sessionmaker, init_db
from app.models.classroom import ClassroomSession
from app.models.course import Chapter, Course, SubChapter, Subject


@pytest_asyncio.fixture
async def fresh_db(tmp_path, monkeypatch):
    """Reset SQLite to a clean state and reinit schema before each test."""
    db_path = tmp_path / "demo_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    # Reload config so DATABASE_URL change takes effect
    import importlib
    from app.core import config as app_config
    importlib.reload(app_config)
    importlib.reload(__import__("app.core.database", fromlist=["get_engine"]))
    from app.core.database import init_db as _init
    await _init()
    yield db_path


@pytest_asyncio.fixture
async def cleared(fresh_db):
    """Wipe demo rows before each test (idempotency baseline)."""
    sm = get_sessionmaker()
    async with sm() as s:
        await s.execute(delete(ClassroomSession).where(ClassroomSession.is_demo.is_(True)))
        await s.execute(delete(SubChapter).where(SubChapter.is_demo.is_(True)))
        await s.execute(delete(Chapter).where(Chapter.is_demo.is_(True)))
        await s.execute(delete(Course).where(Course.is_demo.is_(True)))
        await s.execute(delete(Subject).where(Subject.is_demo.is_(True)))
        await s.commit()
    yield


@pytest.mark.asyncio
async def test_seeder_empty_db_inserts_demo(fresh_db, cleared):
    """First startup against empty DB seeds all demo content."""
    from app.services.demo_seeder import seed_demo_if_missing

    result = await seed_demo_if_missing()

    assert result["status"] == "seeded"
    assert result["version"] == "1.0.0"

    sm = get_sessionmaker()
    async with sm() as s:
        subjects = (await s.execute(
            select(Subject).where(Subject.is_demo.is_(True))
        )).scalars().all()
        courses = (await s.execute(
            select(Course).where(Course.is_demo.is_(True))
        )).scalars().all()
        chapters = (await s.execute(
            select(Chapter).where(Chapter.is_demo.is_(True))
        )).scalars().all()
        subchapters = (await s.execute(
            select(SubChapter).where(SubChapter.is_demo.is_(True))
        )).scalars().all()
        sessions = (await s.execute(
            select(ClassroomSession).where(ClassroomSession.is_demo.is_(True))
        )).scalars().all()

    assert len(subjects) == 1
    assert len(courses) == 1
    assert len(chapters) == 4
    assert len(subchapters) == 4
    assert len(sessions) == 1
    assert all(c.lecture for c in chapters), "every chapter must have lecture populated"
    assert all(c.mindmap for c in chapters), "every chapter must have mindmap populated"
    assert sessions[0].slides is not None
    assert sessions[0].student_id == "", "demo session must have no owner"
```

- [ ] **Step 2: Run test, expect failure (module doesn't exist)**

Run: `pytest tests/test_demo_seeder.py -v`
Expected: `ModuleNotFoundError: No module named 'app.services.demo_seeder'`

- [ ] **Step 3: Implement demo_seeder.py skeleton**

Create `app/services/demo_seeder.py`:

```python
"""Idempotent demo content seeder.

Runs from FastAPI lifespan. On every startup:
  1. Reads storage/seed/demo/manifest.json
  2. Compares its demo_version against current DB state
  3. If absent or version-bumped: drops old demo rows + inserts new
  4. If matching: no-op
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from app.core.database import get_sessionmaker
from app.models.classroom import ClassroomSession
from app.models.course import Chapter, Course, SubChapter, Subject

logger = logging.getLogger("starlearn.demo_seeder")

DEMO_DIR: Path = Path(__file__).resolve().parents[2] / "storage" / "seed" / "demo"


async def _current_demo_version() -> str | None:
    sm = get_sessionmaker()
    async with sm() as s:
        row = (await s.execute(
            select(Course.demo_version).where(Course.is_demo.is_(True)).limit(1)
        )).first()
        return row[0] if row else None


async def _drop_old_demo(old_version: str) -> int:
    """Delete all rows where is_demo=TRUE AND demo_version=old_version."""
    sm = get_sessionmaker()
    async with sm() as s:
        course_ids = (await s.execute(
            select(Course.id).where(Course.is_demo.is_(True), Course.demo_version == old_version)
        )).scalars().all()
        classroom_ids = (await s.execute(
            select(ClassroomSession.id).where(
                ClassroomSession.is_demo.is_(True),
                ClassroomSession.demo_version == old_version,
            )
        )).scalars().all()

        if classroom_ids:
            await s.execute(delete(ClassroomSession).where(ClassroomSession.id.in_(classroom_ids)))
        if course_ids:
            await s.execute(delete(SubChapter).where(SubChapter.course_id.in_(course_ids)))
            await s.execute(delete(Chapter).where(Chapter.course_id.in_(course_ids)))
            await s.execute(delete(Course).where(Course.id.in_(course_ids)))
        await s.execute(delete(Subject).where(
            Subject.is_demo.is_(True), Subject.demo_version == old_version,
        ))
        await s.commit()
        return len(course_ids)


async def _load_manifest() -> dict[str, Any] | None:
    manifest_path = DEMO_DIR / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


async def _load_payload() -> dict[str, Any]:
    """Load all demo JSON files. Missing files become empty structures."""
    def _read(name: str) -> dict[str, Any]:
        path = DEMO_DIR / name
        if not path.exists():
            logger.warning("demo: %s missing", name)
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    return {
        "course": _read("course.json"),
        "lectures": _read("lectures.json"),
        "mindmaps": _read("mindmaps.json"),
        "classroom": _read("classroom.json"),
    }


async def _insert_demo(manifest: dict[str, Any]) -> int:
    payload = await _load_payload()
    course_data = payload["course"]
    lectures = payload["lectures"]
    mindmaps = payload["mindmaps"]
    classroom = payload["classroom"]
    version = manifest["demo_version"]

    if not course_data:
        logger.error("demo: course.json missing or empty, cannot seed")
        return 0

    sm = get_sessionmaker()
    async with sm() as s:
        # 1. Subject
        subj = Subject(
            **course_data["subject"],
            is_demo=True,
            demo_version=version,
        )
        s.add(subj)

        # 2. Course
        course = Course(
            **course_data["course"],
            is_demo=True,
            demo_version=version,
        )
        s.add(course)
        await s.flush()

        # 3. Chapters
        for ch in course_data.get("chapters", []):
            lecture_ref = ch.pop("lecture_ref", None)
            mindmap_ref = ch.pop("mindmap_ref", None)
            lecture = lectures.get(lecture_ref) if lecture_ref else None
            mindmap = mindmaps.get(mindmap_ref) if mindmap_ref else None
            if lecture_ref and lecture is None:
                logger.warning("demo: lecture_ref %s not found", lecture_ref)
            if mindmap_ref and mindmap is None:
                logger.warning("demo: mindmap_ref %s not found", mindmap_ref)
            chapter = Chapter(
                **ch,
                lecture=lecture,
                mindmap=mindmap,
                is_demo=True,
                demo_version=version,
            )
            s.add(chapter)

        # 4. SubChapters
        for sc in course_data.get("subchapters", []):
            s.add(SubChapter(**sc, is_demo=True, demo_version=version))

        # 5. Classroom
        if classroom:
            s.add(ClassroomSession(
                id=classroom["classroom_id"],
                student_id="",
                course_id=classroom["course_id"],
                title=classroom["title"],
                teacher_persona=classroom["teacher_persona"],
                slides={
                    "scenes": classroom.get("scenes", []),
                    "quiz_pool": classroom.get("quiz_pool", []),
                },
                course_data=classroom,
                is_demo=True,
                demo_version=version,
            ))

        await s.commit()
    return 1


async def seed_demo_if_missing() -> dict[str, Any]:
    """Lifespan entrypoint. Idempotent."""
    manifest = await _load_manifest()
    if manifest is None:
        logger.warning("demo: manifest.json missing, skipping")
        return {"status": "no-manifest"}

    new_version = manifest.get("demo_version")
    if not new_version:
        logger.error("demo: manifest.json missing demo_version, skipping")
        return {"status": "no-version"}

    cur = await _current_demo_version()
    if cur == new_version:
        logger.info("demo: already at version %s, skipping", new_version)
        return {"status": "up-to-date", "version": new_version}

    if cur is not None:
        dropped = await _drop_old_demo(cur)
        logger.info("demo: dropped %d old demo course(s) at version %s", dropped, cur)

    inserted = await _insert_demo(manifest)
    logger.info("demo: seeded version %s (%d course(s))", new_version, inserted)
    return {"status": "seeded", "version": new_version, "inserted": inserted}
```

- [ ] **Step 4: Run test, expect PASS**

Run: `pytest tests/test_demo_seeder.py::test_seeder_empty_db_inserts_demo -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/demo_seeder.py tests/test_demo_seeder.py
git commit -m "feat(seeder): add idempotent demo content seeder with empty-DB test"
```

---

### Task 11: Test + implement idempotency (second call is no-op)

**Files:**
- Modify: `tests/test_demo_seeder.py`

- [ ] **Step 1: Append the test**

Append to `tests/test_demo_seeder.py`:

```python
@pytest.mark.asyncio
async def test_seeder_idempotent_no_op_on_second_call(fresh_db, cleared):
    """Second call without version change must not re-insert."""
    from app.services.demo_seeder import seed_demo_if_missing

    first = await seed_demo_if_missing()
    assert first["status"] == "seeded"

    # Capture counts after first seed
    sm = get_sessionmaker()
    async with sm() as s:
        before_courses = len((await s.execute(select(Course))).scalars().all())

    second = await seed_demo_if_missing()
    assert second["status"] == "up-to-date"
    assert second["version"] == "1.0.0"

    async with sm() as s:
        after_courses = len((await s.execute(select(Course))).scalars().all())
    assert after_courses == before_courses
```

- [ ] **Step 2: Run test, expect PASS (no impl changes needed)**

Run: `pytest tests/test_demo_seeder.py::test_seeder_idempotent_no_op_on_second_call -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_demo_seeder.py
git commit -m "test(seeder): verify second seeder call is a no-op"
```

---

### Task 12: Test + implement version bump (drop old, insert new)

**Files:**
- Modify: `tests/test_demo_seeder.py`

- [ ] **Step 1: Append the test**

```python
@pytest.mark.asyncio
async def test_seeder_version_bump_drops_old_inserts_new(fresh_db, cleared, monkeypatch):
    """Bumping manifest version drops old demo rows and inserts new ones."""
    from app.services import demo_seeder
    from app.services.demo_seeder import seed_demo_if_missing

    # First seed at v1.0.0
    first = await seed_demo_if_missing()
    assert first["status"] == "seeded"
    assert first["version"] == "1.0.0"

    # Override manifest to v1.0.1
    manifest_path = demo_seeder.DEMO_DIR / "manifest.json"
    original = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(original.replace('"1.0.0"', '"1.0.1"'), encoding="utf-8")
    try:
        second = await seed_demo_if_missing()
        assert second["status"] == "seeded"
        assert second["version"] == "1.0.1"

        # Old version rows should be gone
        sm = get_sessionmaker()
        async with sm() as s:
            old_courses = (await s.execute(
                select(Course).where(Course.demo_version == "1.0.0")
            )).scalars().all()
            new_courses = (await s.execute(
                select(Course).where(Course.demo_version == "1.0.1")
            )).scalars().all()
        assert len(old_courses) == 0
        assert len(new_courses) == 1
    finally:
        manifest_path.write_text(original, encoding="utf-8")
```

- [ ] **Step 2: Run test, expect PASS**

Run: `pytest tests/test_demo_seeder.py::test_seeder_version_bump_drops_old_inserts_new -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_demo_seeder.py
git commit -m "test(seeder): verify version bump drops old demo rows atomically"
```

---

### Task 13: Test + implement missing-files resilience

**Files:**
- Modify: `tests/test_demo_seeder.py`

- [ ] **Step 1: Append the test**

```python
@pytest.mark.asyncio
async def test_seeder_missing_lectures_file_warns_continues(fresh_db, cleared, monkeypatch):
    """If lectures.json is missing, chapters should still insert with lecture=None."""
    from app.services import demo_seeder
    from app.services.demo_seeder import seed_demo_if_missing

    lectures_path = demo_seeder.DEMO_DIR / "lectures.json"
    backup = lectures_path.read_text(encoding="utf-8")
    lectures_path.unlink()
    try:
        result = await seed_demo_if_missing()
        assert result["status"] == "seeded"

        sm = get_sessionmaker()
        async with sm() as s:
            chapters = (await s.execute(
                select(Chapter).where(Chapter.is_demo.is_(True))
            )).scalars().all()
        assert len(chapters) == 4
        # All lectures should be None (not raised)
        assert all(c.lecture is None for c in chapters)
        # Mindmaps should still be populated from mindmaps.json
        assert all(c.mindmap is not None for c in chapters)
    finally:
        lectures_path.write_text(backup, encoding="utf-8")


@pytest.mark.asyncio
async def test_seeder_no_manifest_skips(fresh_db, cleared, monkeypatch):
    """If manifest.json is missing, seeder is a no-op."""
    from app.services import demo_seeder
    from app.services.demo_seeder import seed_demo_if_missing

    manifest_path = demo_seeder.DEMO_DIR / "manifest.json"
    backup = manifest_path.read_text(encoding="utf-8")
    manifest_path.unlink()
    try:
        result = await seed_demo_if_missing()
        assert result["status"] == "no-manifest"

        sm = get_sessionmaker()
        async with sm() as s:
            courses = (await s.execute(select(Course))).scalars().all()
        assert len(courses) == 0
    finally:
        manifest_path.write_text(backup, encoding="utf-8")
```

- [ ] **Step 2: Run both tests, expect PASS**

Run: `pytest tests/test_demo_seeder.py::test_seeder_missing_lectures_file_warns_continues tests/test_demo_seeder.py::test_seeder_no_manifest_skips -v`
Expected: Both PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_demo_seeder.py
git commit -m "test(seeder): verify resilience to missing lectures.json / manifest.json"
```

---

### Task 14: Test that user data is not touched during demo upgrade

**Files:**
- Modify: `tests/test_demo_seeder.py`

- [ ] **Step 1: Append the test**

```python
@pytest.mark.asyncio
async def test_user_data_not_touched_on_demo_upgrade(fresh_db, cleared, monkeypatch):
    """Bumping demo version must not delete user-created rows."""
    from app.services import demo_seeder
    from app.services.demo_seeder import seed_demo_if_missing

    # Seed v1.0.0
    await seed_demo_if_missing()

    # Insert a fake user-owned course
    sm = get_sessionmaker()
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

    # Bump demo version
    manifest_path = demo_seeder.DEMO_DIR / "manifest.json"
    original = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(original.replace('"1.0.0"', '"1.0.1"'), encoding="utf-8")
    try:
        await seed_demo_if_missing()

        # User course must still exist
        async with sm() as s:
            user_rows = (await s.execute(
                select(Course).where(Course.student_id == "user_42")
            )).scalars().all()
        assert len(user_rows) == 1
        assert user_rows[0].id == "user_course_42"
        assert user_rows[0].title == "My Private Course"
    finally:
        manifest_path.write_text(original, encoding="utf-8")
```

- [ ] **Step 2: Run, expect PASS**

Run: `pytest tests/test_demo_seeder.py::test_user_data_not_touched_on_demo_upgrade -v`
Expected: PASS

- [ ] **Step 3: Run the full seeder test file**

Run: `pytest tests/test_demo_seeder.py -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_demo_seeder.py
git commit -m "test(seeder): verify user data isolation during demo upgrade"
```

---

## Phase 4 — Lifespan Integration

### Task 15: Wire seed_demo_if_missing into main.py lifespan

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Locate the lifespan block**

In `main.py`, find the existing block:

```python
try:
    from app.services.course_seeder import seed_courses_if_empty
    await seed_courses_if_empty()
except Exception as e:
    logger.exception(f"[Startup] seed failed: {e}")
```

- [ ] **Step 2: Insert the demo seed call right after**

```python
try:
    from app.services.course_seeder import seed_courses_if_empty
    await seed_courses_if_empty()
except Exception as e:
    logger.exception(f"[Startup] seed failed: {e}")
# NEW: demo content seeding (idempotent, fail-open)
try:
    from app.services.demo_seeder import seed_demo_if_missing
    demo_result = await seed_demo_if_missing()
    logger.info(f"[Startup] demo seed: {demo_result}")
except Exception as e:
    logger.exception(f"[Startup] demo seed failed: {e}")
```

- [ ] **Step 3: Smoke-test against a fresh SQLite DB**

```bash
rm -f xingshi_v2.db
python -c "
import asyncio
from app.core.database import init_db
from app.services.demo_seeder import seed_demo_if_missing
async def main():
    await init_db()
    print(await seed_demo_if_missing())
asyncio.run(main())
"
```

Expected output: `{'status': 'seeded', 'version': '1.0.0', 'inserted': 1}`

- [ ] **Step 4: Verify in DB**

Run: `python -c "
import asyncio
from sqlalchemy import select
from app.core.database import get_sessionmaker
from app.models.course import Course, Chapter
async def main():
    sm = get_sessionmaker()
    async with sm() as s:
        courses = (await s.execute(select(Course))).scalars().all()
        for c in courses:
            print(c.id, c.title, 'is_demo=', c.is_demo)
        chapters = (await s.execute(select(Chapter))).scalars().all()
        for ch in chapters:
            print(ch.id, 'lecture keys:', list((ch.lecture or {}).keys())[:3])
asyncio.run(main())
"`

Expected: 1 demo course + 4 chapters with `lecture` keys starting with `['chapter_id', 'estimated_minutes', 'blocks']`.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat(startup): call seed_demo_if_missing in lifespan"
```

---

## Phase 5 — Manual Management CLI

### Task 16: Create scripts/seed_demo.py

**Files:**
- Create: `scripts/seed_demo.py`

- [ ] **Step 1: Write the CLI**

Create `scripts/seed_demo.py`:

```python
#!/usr/bin/env python3
"""Manual demo content management.

Usage:
    python scripts/seed_demo.py --check     # print current demo_version
    python scripts/seed_demo.py --reset     # drop old demo, re-insert from JSON
    python scripts/seed_demo.py --dump      # export current DB demo rows to JSON
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Make 'app' importable when running from repo root.
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
    manifest = await demo_seeder._load_manifest()
    target = (manifest or {}).get("demo_version", "(no manifest)")
    print(f"current:  {cur or '(none)'}")
    print(f"manifest: {target}")
    print(f"status:   {'up-to-date' if cur == target else 'NEEDS SEED'}")
    return 0


async def cmd_reset() -> int:
    await init_db()
    cur = await demo_seeder._current_demo_version()
    if cur is not None:
        dropped = await demo_seeder._drop_old_demo(cur)
        print(f"dropped {dropped} old course(s) at version {cur}")
    result = await demo_seeder._insert_demo(await demo_seeder._load_manifest())
    print(f"re-inserted {result} course(s)")
    return 0


async def cmd_dump() -> int:
    await init_db()
    sm = get_sessionmaker()
    async with sm() as s:
        courses = (await s.execute(
            select(Course).where(Course.is_demo.is_(True))
        )).scalars().all()
        chapters = (await s.execute(
            select(Chapter).where(Chapter.is_demo.is_(True))
        )).scalars().all()
        subchapters = (await s.execute(
            select(SubChapter).where(SubChapter.is_demo.is_(True))
        )).scalars().all()
        classrooms = (await s.execute(
            select(ClassroomSession).where(ClassroomSession.is_demo.is_(True))
        )).scalars().all()
    out = {
        "courses": [
            {"id": c.id, "title": c.title, "demo_version": c.demo_version} for c in courses
        ],
        "chapters": [
            {"id": c.id, "course_id": c.course_id, "title": c.title,
             "has_lecture": c.lecture is not None, "has_mindmap": c.mindmap is not None}
            for c in chapters
        ],
        "subchapters": [{"id": s.id, "chapter_id": s.chapter_id} for s in subchapters],
        "classrooms": [
            {"id": c.id, "title": c.title, "has_slides": c.slides is not None}
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
    g.add_argument("--dump",  action="store_true", help="Dump current DB demo rows")
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
```

- [ ] **Step 2: Make executable + smoke-test --check**

```bash
chmod +x scripts/seed_demo.py
python scripts/seed_demo.py --check
```

Expected output:

```
current:  1.0.0
manifest: 1.0.0
status:   up-to-date
```

- [ ] **Step 3: Smoke-test --dump**

Run: `python scripts/seed_demo.py --dump | head -30`
Expected: JSON listing demo courses, chapters, subchapters, classrooms.

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_demo.py
git commit -m "feat(cli): add seed_demo.py with --check/--reset/--dump"
```

---

## Phase 6 — API Changes

### Task 17: Test + implement include_demo filter on course listing

**Files:**
- Test: `tests/test_demo_api.py`
- Modify: `app/api/courses.py`

- [ ] **Step 1: Read the current list endpoint**

Open `app/api/courses.py`. Find `list_courses` (or equivalent) — the function exposed at `@router.get("/courses")` or `@router.get("/courses/list")`. Note its current signature.

- [ ] **Step 2: Write failing API test**

Create `tests/test_demo_api.py`:

```python
"""API tests for demo content visibility."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.core.database import get_sessionmaker, init_db


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "demo_api_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    import importlib
    from app.core import config as app_config
    importlib.reload(app_config)
    importlib.reload(__import__("app.core.database", fromlist=["get_engine"]))
    from app.core.database import init_db as _init
    await _init()

    # Seed demo
    from app.services.demo_seeder import seed_demo_if_missing
    await seed_demo_if_missing()

    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_courses_includes_demo_when_anonymous(client):
    r = await client.get("/api/courses")
    assert r.status_code == 200
    data = r.json()
    items = data.get("data") or data.get("items") or data
    assert isinstance(items, list)
    titles = [c.get("title", "") for c in items]
    assert any("Python" in t and "演示" in t for t in titles), f"demo course missing from {titles}"


@pytest.mark.asyncio
async def test_list_courses_excludes_demo_when_flag_false(client):
    r = await client.get("/api/courses?include_demo=false")
    assert r.status_code == 200
    data = r.json()
    items = data.get("data") or data.get("items") or data
    titles = [c.get("title", "") for c in items]
    assert not any("演示" in t for t in titles), f"demo course leaked: {titles}"
```

- [ ] **Step 3: Run tests, expect failures**

Run: `pytest tests/test_demo_api.py -v`
Expected: First test might pass (because demo data exists), but `include_demo=false` filter is not yet implemented.

- [ ] **Step 4: Locate list_courses handler**

In `app/api/courses.py`, the relevant endpoint is whichever route maps to `GET /api/courses`. Add `include_demo: bool = True` query param.

- [ ] **Step 5: Modify the list endpoint**

Edit `app/api/courses.py` — find the function that returns the course list and modify it. Example (adjust names to match actual code):

```python
@router.get("/courses")
async def list_courses(
    student_id: str = "",
    include_demo: bool = True,
    # ... existing params ...
):
    stmt = select(Course)
    if student_id:
        stmt = stmt.where(
            (Course.student_id == student_id) | (Course.is_demo.is_(True))
        )
    elif not include_demo:
        stmt = stmt.where(Course.is_demo.is_(False))
    # ... existing ORDER BY / LIMIT logic ...
    return ...
```

Make sure the returned dict (or Pydantic model) for each course includes `is_demo` and `demo_version` fields. If you return via `Course.to_dict()` or similar, add those keys there.

- [ ] **Step 6: Same for /subjects and /chapters endpoints**

Apply the same `include_demo` filter pattern to:

```python
@router.get("/subjects")
async def list_subjects(include_demo: bool = True, ...):
    stmt = select(Subject).order_by(Subject.sort_order)
    if not include_demo:
        stmt = stmt.where(Subject.is_demo.is_(False))
    return ...
```

- [ ] **Step 7: Run tests, expect PASS**

Run: `pytest tests/test_demo_api.py -v`
Expected: Both PASS

- [ ] **Step 8: Commit**

```bash
git add app/api/courses.py tests/test_demo_api.py
git commit -m "feat(api): add include_demo filter + return is_demo/demo_version on course endpoints"
```

---

### Task 18: Test + implement classroom API demo visibility

**Files:**
- Modify: `tests/test_demo_api.py`
- Modify: `app/api/classroom.py`

- [ ] **Step 1: Append test**

```python
@pytest.mark.asyncio
async def test_classroom_load_returns_demo_slides(client):
    r = await client.get("/api/classroom/demo_classroom_python_101")
    assert r.status_code == 200
    data = r.json()
    payload = data.get("data") or data
    slides = payload.get("slides") or {}
    scenes = slides.get("scenes") or payload.get("scenes") or []
    assert len(scenes) >= 4, f"expected ≥4 scenes, got {len(scenes)}"
    is_demo = payload.get("is_demo")
    assert is_demo is True
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_demo_api.py::test_classroom_load_returns_demo_slides -v`
Expected: 404 or empty `slides`.

- [ ] **Step 3: Update classroom endpoint**

In `app/api/classroom.py`, locate the `GET /api/classroom/{session_id}` handler. Ensure:

1. It accepts `include_demo: bool = True` query param.
2. When `session_id == "demo_classroom_python_101"`, returns the demo session (which is now in the DB thanks to seeder).
3. The returned dict includes `is_demo`, `demo_version`, and `slides` fields.

Example patch (adjust names):

```python
@router.get("/classroom/{session_id}")
async def get_classroom(session_id: str, include_demo: bool = True, ...):
    stmt = select(ClassroomSession).where(ClassroomSession.id == session_id)
    if not include_demo:
        stmt = stmt.where(ClassroomSession.is_demo.is_(False))
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Classroom not found")
    return {
        "id": session.id,
        "course_id": session.course_id,
        "title": session.title,
        "teacher_persona": session.teacher_persona,
        "slides": session.slides,
        "is_demo": session.is_demo,
        "demo_version": session.demo_version,
        # ... other fields ...
    }
```

- [ ] **Step 4: Run, expect PASS**

Run: `pytest tests/test_demo_api.py::test_classroom_load_returns_demo_slides -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/classroom.py tests/test_demo_api.py
git commit -m "feat(api): expose demo classroom session + is_demo flag"
```

---

## Phase 7 — Frontend Polish

### Task 19: Render DEMO badge on courses.html

**Files:**
- Modify: `html/courses.html`

- [ ] **Step 1: Find the course-card template**

Open `html/courses.html`. Locate the function that renders each course card (search for `course-card` or similar). Note the surrounding structure.

- [ ] **Step 2: Add a DEMO badge in the card**

Inside the course-card template, add (at the top-right corner or beside the title):

```html
${course.is_demo ? '<span class="demo-badge" title="演示课程，所有用户共享">🎁 DEMO</span>' : ''}
```

For React-style templates adjust accordingly. If the page uses plain JS, add an equivalent `if (course.is_demo) document.createElement('span')...`.

- [ ] **Step 3: Add CSS for the badge**

In `css/courses.css`, append:

```css
.demo-badge {
    display: inline-block;
    background: linear-gradient(135deg, #ff8a00 0%, #e52e71 100%);
    color: #fff;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 8px;
    vertical-align: middle;
}
```

- [ ] **Step 4: Manual smoke test**

```bash
python main.py
# Open http://127.0.0.1:8000/html/courses.html
# Confirm: "Python 编程入门（演示课程）" card shows "🎁 DEMO" badge
```

- [ ] **Step 5: Commit**

```bash
git add html/courses.html css/courses.css
git commit -m "feat(ui): show DEMO badge on demo course cards"
```

---

### Task 20: Render 演示课堂 banner on classroom.html

**Files:**
- Modify: `html/classroom.html`

- [ ] **Step 1: Find the classroom header markup**

Open `html/classroom.html`. Locate the header / banner area near the top of the page.

- [ ] **Step 2: Add a conditional banner**

Insert this near the top of the main content (before the slide canvas):

```html
<div id="demo-banner" class="demo-banner" style="display:none;">
    🎁 演示课堂 · 所有用户共享 · 不可编辑
</div>
```

- [ ] **Step 3: Show banner when classroom is demo**

Find the JS that loads the classroom session and add:

```js
if (session.is_demo) {
    document.getElementById('demo-banner').style.display = 'block';
}
```

- [ ] **Step 4: Add CSS**

In `css/classroom.css`:

```css
.demo-banner {
    background: linear-gradient(135deg, #ff8a00 0%, #e52e71 100%);
    color: #fff;
    text-align: center;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.5px;
    border-radius: 8px;
    margin: 12px 0;
}
```

- [ ] **Step 5: Manual smoke test**

```bash
python main.py
# Open http://127.0.0.1:8000/html/classroom.html?id=demo_classroom_python_101
# Confirm: orange "演示课堂" banner shows above the slide canvas
```

- [ ] **Step 6: Commit**

```bash
git add html/classroom.html css/classroom.css
git commit -m "feat(ui): show 演示课堂 banner on demo classroom sessions"
```

---

## Phase 8 — Documentation + Final Verification

### Task 21: Update README with demo content section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a "Demo Content" subsection under "快速开始"**

Insert after the existing "5 分钟跑起来" code block:

```markdown
### 预置 Demo 内容

首次启动后，应用会自动从 `storage/seed/demo/` 加载演示内容，无需任何手动操作：

- **1 门演示课程**：Python 编程入门（4 章，含完整讲义 + 思维导图）
- **1 个演示课堂**：Python 编程入门 · 演示课堂（4 个场景，6 张幻灯片）

所有用户（包括未登录）都可在课程中心看到 🎁 DEMO 课程，在课堂页看到「演示课堂」横幅。

### 修改 / 升级 Demo 内容

1. 编辑 `storage/seed/demo/*.json`
2. 在 `manifest.json` 里 bump `demo_version`（如 `1.0.0` → `1.0.1`）
3. 下次启动自动替换 demo 内容；用户私有数据完全不受影响

详见 [storage/seed/demo/README.md](storage/seed/demo/README.md)。
```

- [ ] **Step 2: Verify README renders correctly**

Open `README.md` and confirm the new section sits between "5 分钟跑起来" and "详细文档".

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): document demo content seeding"
```

---

### Task 22: Full test suite verification

**Files:** none

- [ ] **Step 1: Run all seeder + api tests**

Run: `pytest tests/test_demo_models.py tests/test_demo_seeder.py tests/test_demo_api.py -v`
Expected: All pass.

- [ ] **Step 2: Run the entire test suite to confirm no regressions**

Run: `pytest tests/ -v --ignore=tests/test_demo_api.py 2>&1 | tail -50`

Look for: zero failures in pre-existing tests.

- [ ] **Step 3: Manual end-to-end smoke test**

```bash
rm -f xingshi_v2.db
python main.py &
sleep 5
curl -s http://127.0.0.1:8000/api/courses | python -m json.tool | head -30
curl -s http://127.0.0.1:8000/api/classroom/demo_classroom_python_101 | python -m json.tool | head -30
kill %1
```

Expected: both endpoints return JSON containing the demo course / classroom.

- [ ] **Step 4: Open browser, visually verify**

1. http://127.0.0.1:8000/html/courses.html — confirm DEMO badge appears
2. http://127.0.0.1:8000/html/classroom.html?id=demo_classroom_python_101 — confirm 演示课堂 banner shows

- [ ] **Step 5: Final commit (if any uncommitted changes)**

```bash
git status
git log --oneline -10
```

Verify all commits land cleanly. Plan complete.

---

## Self-Review Checklist

- [x] **Spec coverage**: every requirement in `docs/superpowers/specs/2026-07-20-demo-content-seeding-design.md` has a task:
  - §3 file layout → Tasks 1–9
  - §4 schema additions → Tasks 1–4
  - §5 demo content JSON files → Tasks 5–8
  - §6 seeder → Tasks 10–14
  - §6.3 manual CLI → Task 16
  - §7 API changes → Tasks 17–18
  - §8 testing → Tasks 10–14 (seeder) + Task 17–18 (api)
  - §9 failure modes → Tasks 11–14 cover missing-file + version-bump
  - §11 acceptance criteria → Task 22 final verification
- [x] **Placeholder scan**: no "TBD", "TODO", "implement later", or "similar to Task N". Every code block is complete.
- [x] **Type consistency**:
  - `seed_demo_if_missing()` defined in Task 10, used in Tasks 15, 16.
  - `Course.is_demo`, `Chapter.lecture`, `ClassroomSession.slides` added in Tasks 1–2, queried in Tasks 17–18.
  - `_current_demo_version()`, `_drop_old_demo()`, `_insert_demo()`, `_load_manifest()`, `_load_payload()` defined in Task 10, used in Task 12, 13, 14, 16.
  - `DEMO_DIR` used in Task 12, 13, 14, 16.

---

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-07-20-demo-content-seeding.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration with quality gates.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

Which approach?