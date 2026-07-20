# Demo Content Seeding — Design Spec

| | |
|---|---|
| **Date** | 2026-07-20 |
| **Status** | Approved (brainstorming complete) |
| **Author** | Brainstorming session |
| **Affects** | `app/models/course.py`, `app/models/classroom.py`, `app/api/courses.py`, `app/api/classroom.py`, `app/services/demo_seeder.py` (new), `storage/seed/demo/` (new), `scripts/seed_demo.py` (new), `tests/test_demo_seeder.py` (new), `tests/test_demo_api.py` (new), `main.py` lifespan, `html/courses.html`, `html/classroom.html` |

---

## 1. Problem

A fresh deployment of Star-Learn leaves new users staring at empty course centers and no classroom demo. They must generate their first course through LLM-driven flow before they see any content — bad first impression, especially in evaluation contexts.

**Goal**: After first startup, every deployment contains:

1. **One complete demo course** in the course center (Subject → Course → Chapter × N → SubChapter × N), with **structured rich-text lectures** and **node-edge mindmaps** per chapter.
2. **One pre-prepared classroom session** (a.k.a. "课堂演示 PPT") that maps 1:1 to the demo course chapters — anyone opening it gets a full, scrollable slide flow without waiting on the LLM.

**Non-goals**:
- We are not generating fresh demo content via LLM at deploy time. Demo content is **committed JSON** (deterministic, offline-deployable, no API key required).
- We are not changing existing user-data ownership semantics — private user data still goes through `student_id`.

---

## 2. Decisions (locked from brainstorming)

| # | Decision |
|---|----------|
| D1 | Lecture & mindmap content is **structured rich-text JSON + node/edge graph**, not Markdown blobs / Mermaid source. |
| D2 | Classroom PPT and demo course are **two views of the same course** — slides are 1:1 mapped to chapters. |
| D3 | Demo content has **no owner** — visible to all users. Implemented via an `is_demo: Boolean` flag (orthogonal to `student_id`). |
| D4 | Demo content is **checked on every startup** and missing pieces are re-inserted (idempotent). |
| D5 | Demo content lives as **JSON files in `storage/seed/demo/`**, loaded by an idempotent seeder on startup (mirrors existing `course_seeder.py` pattern). |
| D6 | A demo-content **versioning scheme** (`demo_version` semver) lets us upgrade content without writing `UPDATE` SQL. Old version is **dropped** + new version **inserted** on upgrade. |
| D7 | User private content is **never touched** by demo operations — all DELETE/INSERT are filtered by `is_demo=TRUE`. |

---

## 3. Architecture

### 3.1 File layout

```
Kuromi-main/
├── app/
│   ├── models/
│   │   ├── course.py                 # EDIT: add is_demo, demo_version, lecture, mindmap
│   │   └── classroom.py              # EDIT: add is_demo, demo_version, slides
│   ├── api/
│   │   ├── courses.py                # EDIT: include_demo filter on list endpoints
│   │   └── classroom.py              # EDIT: same
│   └── services/
│       └── demo_seeder.py            # NEW: idempotent demo content seeder
├── storage/
│   └── seed/
│       └── demo/                     # NEW
│           ├── README.md
│           ├── manifest.json
│           ├── course.json
│           ├── lectures.json
│           ├── mindmaps.json
│           └── classroom.json
├── scripts/
│   └── seed_demo.py                  # NEW: --check / --reset / --dump
├── tests/
│   ├── test_demo_seeder.py           # NEW
│   └── test_demo_api.py              # NEW
├── alembic/
│   └── versions/
│       └── 20260720_add_demo_flags_and_lecture_fields.py   # NEW
├── main.py                           # EDIT: lifespan calls seed_demo_if_missing()
└── html/
    ├── courses.html                  # EDIT: show DEMO badge when is_demo=true
    └── classroom.html                # EDIT: show "演示课堂" banner when is_demo=true
```

### 3.2 Runtime data flow

```
startup
  └── lifespan()
       ├── init_db()                  # existing — creates base tables
       ├── seed_courses_if_empty()    # existing — seeds from storage/courses/*.json
       ├── seed_demo_if_missing()     # NEW — checks manifest version, drops old demo, inserts new
       └── HealthWorker / schedulers  # existing
            │
            ▼
       app starts serving on :8000
            │
            ▼
       GET /api/courses
            │
       SQL: SELECT * FROM courses WHERE is_demo=TRUE OR student_id=?
            │
            ▼
       returns JSON with is_demo field, frontend renders DEMO badge
```

### 3.3 Isolation guarantees

- **No leakage between user data and demo data**: every demo SQL statement filters on `is_demo=TRUE`; every user-data API filters on `student_id=<user>`. The OR clause that joins them is opt-in (`include_demo=true`).
- **Demo upgrade is atomic**: either all old demo rows are dropped + new rows inserted, or nothing changes. No "half-migrated" state survives a crash because the seeder runs inside one transaction.
- **Startup is fail-open**: if `seed_demo_if_missing()` raises, only a log line is emitted; the rest of lifespan continues. App still starts (degraded demo, working private content).

---

## 4. Data Model

### 4.1 Schema additions

| Table | New column | Type | Default | Notes |
|-------|-----------|------|---------|-------|
| `subjects` | `is_demo` | BOOLEAN | 0 | Indexed (composite with `student_id` not needed; `is_demo` is small and selective) |
| `subjects` | `demo_version` | VARCHAR(16) | `''` | semver, only meaningful when `is_demo=TRUE` |
| `courses` | `is_demo` | BOOLEAN | 0 | |
| `courses` | `demo_version` | VARCHAR(16) | `''` | |
| `chapters` | `is_demo` | BOOLEAN | 0 | |
| `chapters` | `demo_version` | VARCHAR(16) | `''` | |
| `chapters` | `lecture` | JSON (MySQL) / TEXT (SQLite) | NULL | Structured rich-text blocks |
| `chapters` | `mindmap` | JSON (MySQL) / TEXT (SQLite) | NULL | `{nodes, edges}` graph |
| `subchapters` | `is_demo` | BOOLEAN | 0 | |
| `subchapters` | `demo_version` | VARCHAR(16) | `''` | |
| `classroom_sessions` | `is_demo` | BOOLEAN | 0 | |
| `classroom_sessions` | `demo_version` | VARCHAR(16) | `''` | |
| `classroom_sessions` | `slides` | JSON / TEXT | NULL | Holds demo slide flow |

All fields are nullable / default-safe so existing rows keep working unchanged. Migration only `ADD COLUMN`, never `DROP COLUMN` of pre-existing fields.

### 4.2 Migration

File: `alembic/versions/20260720_add_demo_flags_and_lecture_fields.py`

```python
"""add demo flags + lecture/mindmap/slides JSON fields."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON as MySQL_JSON

def upgrade():
    bind = op.get_bind()
    json_type = MySQL_JSON if bind.dialect.name == "mysql" else sa.Text

    # subjects
    op.add_column("subjects", sa.Column("is_demo", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("subjects", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # courses
    op.add_column("courses", sa.Column("is_demo", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("courses", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # chapters — also adds lecture + mindmap JSON columns
    op.add_column("chapters", sa.Column("is_demo", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("chapters", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))
    op.add_column("chapters", sa.Column("lecture", json_type, nullable=True))
    op.add_column("chapters", sa.Column("mindmap", json_type, nullable=True))

    # subchapters
    op.add_column("subchapters", sa.Column("is_demo", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("subchapters", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # classroom_sessions — also adds slides JSON column
    op.add_column("classroom_sessions", sa.Column("is_demo", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("classroom_sessions", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))
    op.add_column("classroom_sessions", sa.Column("slides", json_type, nullable=True))

def downgrade():
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

`json_type` choice: MySQL gets `JSON` (validated + binary), SQLite gets `TEXT` (validated by app layer). All new columns are nullable (where JSON) or have safe defaults (where BOOLEAN / VARCHAR) so existing rows are unaffected.

---

## 5. Demo Content Spec

### 5.1 `manifest.json`

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

### 5.2 `course.json`

Contains four sub-objects: `subject`, `course`, `chapters`, `subchapters`. Each chapter has `lecture_ref` and `mindmap_ref` keys — these are **not** stored in the DB column; the seeder resolves them against `lectures.json` and `mindmaps.json` before insert.

### 5.3 `lectures.json`

Map keyed by `lecture_ref`. Each value:

```json
{
  "chapter_id": "ch_demo_py_1",
  "estimated_minutes": 8,
  "blocks": [
    {"kind": "h2",      "text": "Section title"},
    {"kind": "p",       "text": "Body paragraph"},
    {"kind": "callout", "tone": "info|warning|success", "text": "..."},
    {"kind": "code",    "lang": "python", "text": "print(1)"},
    {"kind": "list",    "ordered": false, "items": ["..."]},
    {"kind": "quote",   "text": "..."},
    {"kind": "summary", "text": "Wrap-up line"}
  ]
}
```

`kind` enum (closed set, frontend renders each differently): `h1, h2, h3, p, code, list, callout, quote, image, summary, table`.

### 5.4 `mindmaps.json`

Map keyed by `mindmap_ref`. Each value:

```json
{
  "chapter_id": "ch_demo_py_1",
  "root_label": "Python 初识",
  "layout": "right-tree",
  "nodes": [{"id": "n1", "label": "Python 初识", "level": 0, "x": 0, "y": 0}],
  "edges": [{"from": "n1", "to": "n2"}]
}
```

`layout` enum: `right-tree, left-tree, radial, two-sided`.

### 5.5 `classroom.json`

A single classroom session blob:

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
      "title": "开场",
      "type": "intro",
      "duration_sec": 30,
      "slides": [{"id": "s1", "layout": "title", "title": "..."}],
      "speech": "..."
    }
  ],
  "quiz_pool": [{"id": "q_intro_1", "question": "...", "options": [], "answer": 0}]
}
```

`scene.type` enum: `intro, concept, interactive, code, summary`.
`slide.layout` enum: `title, agenda, list, callout, code, summary`.

### 5.6 v1.0.0 content scope

| Item | Count | Notes |
|------|-------|-------|
| Subjects | 1 | `Computer Science (Demo)` |
| Courses | 1 | `Python 编程入门（演示课程）` |
| Chapters | 4 | 初识 / 变量与类型 / 控制流 / 函数 |
| SubChapters | 4 | 1:1 with chapters |
| Lectures | 4 | One per chapter, 5–7 blocks each |
| Mindmaps | 4 | One per chapter, 4–6 nodes each |
| Classroom sessions | 1 | 4 scenes, 6 slides, 1 quiz |
| Total JSON footprint | ~25 KB | Fits comfortably in Git |

---

## 6. Seeder

### 6.1 Public API

```python
# app/services/demo_seeder.py
async def seed_demo_if_missing() -> dict[str, Any]:
    """Returns {status, version, inserted/dropped} for logging."""
```

### 6.2 Behavior matrix

| Current DB | manifest | Action |
|-----------|---------|--------|
| No demo rows | any | INSERT v_new |
| `is_demo=TRUE` rows exist, version == manifest | match | skip (idempotent) |
| `is_demo=TRUE` rows exist, version != manifest | bumped | DELETE all rows where `is_demo=TRUE AND demo_version=old`, including the `Subject`. Then INSERT v_new |
| `manifest.json` missing | — | log warning, return `{status: "no-manifest"}` |
| `course.json` corrupt | — | log error, skip that file, continue with rest |
| `lecture_ref` not found in `lectures.json` | — | log warning, Chapter.lecture=NULL |
| `mindmap_ref` not found | — | log warning, Chapter.mindmap=NULL |
| Any DB write failure | — | transaction rollback, raise, lifespan logs and swallows |

**Subjects are always re-created along with their courses**: a demo Subject (`is_demo=TRUE`) only exists to host demo courses. When dropping an old demo version we delete the Subject too (filtered by `is_demo=TRUE AND demo_version=old`). If a user happens to also own a Subject with the same `id`, that user's Subject is filtered out by `is_demo=FALSE` so it is **never touched**.

**Demo `ClassroomSession.student_id` is set to `""` (empty string)**, NOT a sentinel user id. This is intentional: empty `student_id` is the "no owner" semantic throughout the codebase. The `is_demo=TRUE` flag is the *primary* identifier — list queries filter on `is_demo=TRUE`, not on `student_id=""`. Empty `student_id` is also explicit at the data layer so that any future query like `WHERE student_id=?` will not accidentally match demo rows.

### 6.3 `main.py` lifespan integration

```python
try:
    from app.services.demo_seeder import seed_demo_if_missing
    result = await seed_demo_if_missing()
    logger.info(f"[Startup] demo seed: {result}")
except Exception as e:
    logger.exception(f"[Startup] demo seed failed: {e}")
```

Placed after `seed_courses_if_empty()`, before scheduler startup. Order matters: regular courses seed first → demo subjects/courses don't collide on slug.

### 6.4 Manual management: `scripts/seed_demo.py`

```
python scripts/seed_demo.py --check    # print current demo_version
python scripts/seed_demo.py --reset    # drop old demo, re-insert from JSON
python scripts/seed_demo.py --dump     # export current DB demo rows back to JSON (debug)
```

`--reset` is the operational escape hatch when content authors want to force-refresh without bumping manifest version.

---

## 7. API changes

### 7.1 Listing endpoints

```python
# app/api/courses.py
@router.get("/subjects")
async def list_subjects(include_demo: bool = True, ...):
    stmt = select(Subject).order_by(Subject.sort_order)
    if not include_demo:
        stmt = stmt.where(Subject.is_demo.is_(False))
    return ...

@router.get("/courses")
async def list_courses(student_id: str = "", include_demo: bool = True, ...):
    stmt = select(Course)
    if student_id:
        stmt = stmt.where((Course.student_id == student_id) | (Course.is_demo.is_(True)))
    elif not include_demo:
        stmt = stmt.where(Course.is_demo.is_(False))
    return ...
```

Same pattern for `classroom_sessions`.

### 7.2 Returned JSON

`is_demo` and `demo_version` are **always present** in JSON responses. Frontend logic:

```js
if (course.is_demo) renderBadge('🎁 DEMO');
if (classroom.is_demo) renderBanner('演示课堂，所有用户共享');
```

No behavioural change for non-demo content.

---

## 8. Testing

### 8.1 Unit tests (`tests/test_demo_seeder.py`)

| Test | Setup | Assertion |
|------|-------|-----------|
| `test_seeder_empty_db` | wipe demo rows, call seeder | status="seeded", exactly 1 subject / 1 course / 4 chapters / 4 subchapters / 1 classroom inserted |
| `test_seeder_idempotent` | call seeder twice | 2nd call status="up-to-date", no row count change |
| `test_seeder_version_bump` | call seeder, bump manifest to 1.1.0, call again | 2nd call drops v1.0.0 rows, inserts v1.1.0; old row count is 0 |
| `test_seeder_missing_lectures_file` | delete `lectures.json`, call seeder | status="seeded", chapters inserted with lecture=NULL, log warning present |
| `test_seeder_no_manifest` | delete `manifest.json`, call seeder | status="no-manifest", no rows inserted |
| `test_seeder_corrupt_json` | corrupt `course.json`, call seeder | exception caught at boundary, lifespan logs and continues |
| `test_user_data_not_touched_on_demo_upgrade` | seed user data + demo v1.0.0, bump to v1.1.0 | user rows unchanged, demo rows swapped |

### 8.2 API tests (`tests/test_demo_api.py`)

| Test | Setup | Assertion |
|------|-------|-----------|
| `test_list_courses_includes_demo_when_anonymous` | empty DB after seed | GET /api/courses returns demo course |
| `test_list_courses_excludes_demo_when_flag_false` | same | `?include_demo=false` hides demo course |
| `test_chapter_returns_lecture_blocks` | seed | GET /api/chapters/{ch_demo_py_1}.lecture.blocks has ≥4 items |
| `test_chapter_returns_mindmap_nodes` | seed | GET /api/chapters/{ch_demo_py_1}.mindmap.nodes length ≥4 |
| `test_classroom_load_returns_slides` | seed | GET /api/classroom/demo_classroom_python_101 returns 4 scenes |
| `test_demo_does_not_appear_in_user_course_list` | register user X, list X's courses | demo course absent unless `include_demo=true` |

### 8.3 Manual smoke test

```bash
# Fresh DB
rm -f xingshi_v2.db
python main.py
# Browser: http://127.0.0.1:8000 → 课程中心 → see "Python 编程入门（演示课程）"
# Click into it → see 4 chapters with lecture + mindmap rendered
# Open 课堂 → click "演示课堂" → see slide flow
```

---

## 9. Failure modes & rollback

### 9.1 Failure modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Migration not run | `OperationalError: Unknown column 'is_demo'` | lifespan logs, app starts (degraded). Run `alembic upgrade head`, restart. |
| `storage/seed/demo/` missing | `DEMO_DIR.exists()` False | seeder early-returns with warning. No DB change. |
| JSON file corrupt | `json.JSONDecodeError` | log error, skip file, other files still seed. |
| `manifest.demo_version` missing | `KeyError` | log error, skip entire batch. |
| Lecture/mindmap ref unresolved | `dict.get()` returns None | field NULL on that row, log warning. |
| DB write fails mid-insert | exception | full transaction rollback; retry on next startup. |
| Demo content quality complaint | — | bump `demo_version`, edit JSONs, deploy. |

### 9.2 Rollback playbook

| Want to roll back | How |
|-------------------|-----|
| Bad demo content | `python scripts/seed_demo.py --reset` |
| Disable demo entirely | `DELETE FROM subjects WHERE is_demo=1; DELETE FROM courses WHERE is_demo=1; DELETE FROM chapters WHERE is_demo=1; DELETE FROM subchapters WHERE is_demo=1; DELETE FROM classroom_sessions WHERE is_demo=1;` |
| Revert schema | `alembic downgrade -1` |
| Revert to old demo content | revert manifest + JSONs, then `alembic downgrade -1 && alembic upgrade head` then restart |

---

## 10. Out of scope (YAGNI)

- Auto-generating fresh demo content via LLM at deploy time — defeats determinism + offline deployability.
- Multi-language demo content — single Chinese demo course is sufficient for v1.
- Per-user demo customization — all users share.
- Demo analytics — same as regular content.
- Demo content editor UI — keep authoring in `storage/seed/demo/*.json`.
- Migration for demo content itself — content lives in JSON files, version is a string.

---

## 11. Acceptance criteria

- [ ] `alembic upgrade head` adds the new columns on both MySQL and SQLite without errors.
- [ ] First startup against an empty DB seeds exactly: 1 subject, 1 course, 4 chapters, 4 subchapters, 1 classroom session. All `is_demo=TRUE`, `demo_version="1.0.0"`.
- [ ] Second startup is a no-op (logs "up-to-date").
- [ ] After bumping manifest to `1.0.1`, third startup swaps demo rows atomically. User-private rows are untouched.
- [ ] `GET /api/courses` (anonymous) returns the demo course. `GET /api/courses?include_demo=false` does not.
- [ ] `GET /api/chapters/{ch_demo_py_1}` returns `lecture.blocks` length ≥ 4 and `mindmap.nodes` length ≥ 4.
- [ ] `GET /api/classroom/demo_classroom_python_101` returns 4 scenes with ≥ 6 slides total.
- [ ] `html/courses.html` renders the demo course with a "🎁 DEMO" badge.
- [ ] `html/classroom.html` renders the demo classroom with a "演示课堂" banner.
- [ ] All tests in §8 pass on both MySQL 8.0 and SQLite 3.
- [ ] If `storage/seed/demo/` is deleted entirely, the app starts and serves an empty course center without errors.