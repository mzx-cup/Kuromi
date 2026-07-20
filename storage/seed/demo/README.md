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
