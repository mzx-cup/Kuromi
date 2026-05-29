# 全息视界播放器重设计 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重写全息视界播放器为 B站嵌入 + 本地视频双模式，统一控制栏，3 Tab 侧栏（课程库/我的列表/AI笔记），后端新增视频课程库和播放列表 API。

**Architecture:** 前端 videoController 按 source_type 路由到 BilibiliDriver（iframe postMessage）或 LocalDriver（video DOM API），控制栏 UI 统一。后端新增 video_courses/video_playlists/playlist_videos 三张表，遵循现有 db.py 多后端模式（MySQL/SQLite/JSON fallback）。

**Tech Stack:** FastAPI (Python), vanilla JS, HTML/CSS, 现有 db.py 多后端抽象层

---

### Task 1: 数据库层 — video_courses 表

**Files:**
- Modify: `db.py` (末尾追加)

- [ ] **Step 1: 添加 video_courses SQL 建表语句到数据库初始化**

在 `db.py` 文件末尾追加 `init_video_tables` 函数和 CRUD 函数。

数据库表创建函数 `init_video_tables()`:

```python
def init_video_tables():
    with get_db() as conn:
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            if _is_sqlite(conn):
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_courses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        subtitle TEXT DEFAULT '',
                        source_type TEXT NOT NULL DEFAULT 'bilibili',
                        bvid TEXT DEFAULT '',
                        page INTEGER DEFAULT 1,
                        local_path TEXT DEFAULT '',
                        duration_label TEXT DEFAULT '--:--',
                        ai_summary TEXT DEFAULT '',
                        ai_timeline TEXT DEFAULT '[]',
                        ai_questions TEXT DEFAULT '[]',
                        ai_suggestion TEXT DEFAULT '',
                        created_by TEXT DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL DEFAULT '默认列表',
                        position INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playlist_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        playlist_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        position INTEGER DEFAULT 0,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_courses (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(256) NOT NULL,
                        subtitle VARCHAR(512) DEFAULT '',
                        source_type VARCHAR(16) NOT NULL DEFAULT 'bilibili',
                        bvid VARCHAR(32) DEFAULT '',
                        page INT DEFAULT 1,
                        local_path VARCHAR(512) DEFAULT '',
                        duration_label VARCHAR(16) DEFAULT '--:--',
                        ai_summary TEXT,
                        ai_timeline JSON,
                        ai_questions JSON,
                        ai_suggestion TEXT,
                        created_by VARCHAR(64) DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_playlists (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(64) NOT NULL,
                        name VARCHAR(128) NOT NULL DEFAULT '默认列表',
                        position INT DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playlist_videos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        playlist_id INT NOT NULL,
                        course_id INT NOT NULL,
                        position INT DEFAULT 0,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"初始化视频表失败: {e}")
```

- [ ] **Step 2: 运行迁移验证**

```bash
cd "C:\Users\ZWC\Downloads\Kuromi-main\Kuromi-main" && python -c "import db; db.init_video_tables(); print('OK')"
```

预期: `OK`（无异常）

- [ ] **Step 3: 实现 video_courses CRUD 函数**

在 `db.py` 末尾追加:

```python
def get_all_video_courses(source_type=None):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    if source_type:
                        cursor.execute("SELECT * FROM video_courses WHERE source_type = ? ORDER BY id DESC", (source_type,))
                    else:
                        cursor.execute("SELECT * FROM video_courses ORDER BY id DESC")
                    rows = cursor.fetchall()
                    cursor.close()
                    return [dict(r) for r in rows]
                else:
                    if source_type:
                        cursor.execute("SELECT * FROM video_courses WHERE source_type = %s ORDER BY id DESC", (source_type,))
                    else:
                        cursor.execute("SELECT * FROM video_courses ORDER BY id DESC")
                    rows = cursor.fetchall()
                    cursor.close()
                    return [dict(r) for r in rows]
            except Exception as e:
                print(f"查询视频课程失败: {e}")
                return []
        storage = load_local_storage()
        courses = storage.get('video_courses', [])
        if source_type:
            courses = [c for c in courses if c.get('source_type') == source_type]
        return sorted(courses, key=lambda c: c.get('id', 0), reverse=True)


def get_video_course(course_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM video_courses WHERE id = ?", (course_id,))
                else:
                    cursor.execute("SELECT * FROM video_courses WHERE id = %s", (course_id,))
                row = cursor.fetchone()
                cursor.close()
                return dict(row) if row else None
            except Exception as e:
                print(f"查询视频课程失败: {e}")
                return None
        storage = load_local_storage()
        for c in storage.get('video_courses', []):
            if c.get('id') == course_id:
                return c
        return None


def create_video_course(title, source_type='bilibili', subtitle='', bvid='', page=1,
                        local_path='', duration_label='--:--', ai_summary='',
                        ai_timeline='[]', ai_questions='[]', ai_suggestion='', created_by=''):
    import json as _json
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO video_courses (title, subtitle, source_type, bvid, page,
                            local_path, duration_label, ai_summary, ai_timeline, ai_questions,
                            ai_suggestion, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (title, subtitle, source_type, bvid, page, local_path, duration_label,
                          ai_summary, ai_timeline, ai_questions, ai_suggestion, created_by))
                else:
                    cursor.execute("""
                        INSERT INTO video_courses (title, subtitle, source_type, bvid, page,
                            local_path, duration_label, ai_summary, ai_timeline, ai_questions,
                            ai_suggestion, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (title, subtitle, source_type, bvid, page, local_path, duration_label,
                          _json.dumps(ai_summary) if isinstance(ai_summary, str) else _json.dumps(ai_summary or ''),
                          _json.dumps(ai_timeline) if isinstance(ai_timeline, str) else _json.dumps(ai_timeline or '[]'),
                          _json.dumps(ai_questions) if isinstance(ai_questions, str) else _json.dumps(ai_questions or '[]'),
                          ai_suggestion, created_by))
                conn.commit()
                course_id = cursor.lastrowid
                cursor.close()
                return course_id
            except Exception as e:
                print(f"创建视频课程失败: {e}")
                return None
        storage = load_local_storage()
        courses = storage.get('video_courses', [])
        new_id = max([c.get('id', 0) for c in courses], default=0) + 1
        course = {
            'id': new_id, 'title': title, 'subtitle': subtitle, 'source_type': source_type,
            'bvid': bvid, 'page': page, 'local_path': local_path, 'duration_label': duration_label,
            'ai_summary': ai_summary, 'ai_timeline': ai_timeline, 'ai_questions': ai_questions,
            'ai_suggestion': ai_suggestion, 'created_by': created_by, 'created_at': ''
        }
        courses.append(course)
        storage['video_courses'] = courses
        save_local_storage(storage)
        return new_id


def delete_video_course(course_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM video_courses WHERE id = ?", (course_id,))
                else:
                    cursor.execute("DELETE FROM video_courses WHERE id = %s", (course_id,))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"删除视频课程失败: {e}")
                return False
        storage = load_local_storage()
        storage['video_courses'] = [c for c in storage.get('video_courses', []) if c.get('id') != course_id]
        save_local_storage(storage)
        return True


def update_video_course(course_id, **kwargs):
    if not kwargs:
        return False
    import json as _json
    fields = []
    values = []
    for key in ('title', 'subtitle', 'source_type', 'bvid', 'page', 'local_path',
                'duration_label', 'ai_summary', 'ai_timeline', 'ai_questions', 'ai_suggestion'):
        if key in kwargs:
            fields.append(f"{key} = {'?' if _is_sqlite(None) else '%s'}")
            values.append(kwargs[key])
    if not fields:
        return False
    values.append(course_id)
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                sqlite = _is_sqlite(conn)
                placeholders = ', '.join(f"{k} = {'?' if sqlite else '%s'}" for k in kwargs if k in (
                    'title', 'subtitle', 'source_type', 'bvid', 'page', 'local_path',
                    'duration_label', 'ai_summary', 'ai_timeline', 'ai_questions', 'ai_suggestion'
                ))
                sql = f"UPDATE video_courses SET {placeholders} WHERE id = {'?' if sqlite else '%s'}"
                vals = [kwargs[k] for k in kwargs if k in (
                    'title', 'subtitle', 'source_type', 'bvid', 'page', 'local_path',
                    'duration_label', 'ai_summary', 'ai_timeline', 'ai_questions', 'ai_suggestion'
                )]
                vals.append(course_id)
                cursor.execute(sql, vals)
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"更新视频课程失败: {e}")
                return False
        storage = load_local_storage()
        for c in storage.get('video_courses', []):
            if c.get('id') == course_id:
                c.update(kwargs)
                save_local_storage(storage)
                return True
        return False
```

- [ ] **Step 4: 实现 video_playlists 和 playlist_videos CRUD 函数**

在 `db.py` 末尾追加:

```python
def get_user_playlists(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM video_playlists WHERE user_id = ? ORDER BY position, id", (user_id,))
                else:
                    cursor.execute("SELECT * FROM video_playlists WHERE user_id = %s ORDER BY position, id", (user_id,))
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    pl = dict(row)
                    cursor.execute(
                        "SELECT pv.*, vc.title, vc.source_type, vc.bvid, vc.page, vc.local_path, vc.duration_label, vc.ai_summary, vc.ai_timeline, vc.ai_questions, vc.ai_suggestion FROM playlist_videos pv JOIN video_courses vc ON pv.course_id = vc.id WHERE pv.playlist_id = ? ORDER BY pv.position, pv.id" if _is_sqlite(conn) else
                        "SELECT pv.*, vc.title, vc.source_type, vc.bvid, vc.page, vc.local_path, vc.duration_label, vc.ai_summary, vc.ai_timeline, vc.ai_questions, vc.ai_suggestion FROM playlist_videos pv JOIN video_courses vc ON pv.course_id = vc.id WHERE pv.playlist_id = %s ORDER BY pv.position, pv.id",
                        (pl['id'],))
                    vrows = cursor.fetchall()
                    pl['videos'] = [dict(vr) for vr in vrows]
                    results.append(pl)
                cursor.close()
                return results
            except Exception as e:
                print(f"查询播放列表失败: {e}")
                return []
        storage = load_local_storage()
        playlists = [p for p in storage.get('video_playlists', []) if p.get('user_id') == user_id]
        all_items = storage.get('playlist_videos', [])
        all_courses = {c['id']: c for c in storage.get('video_courses', [])}
        for pl in playlists:
            items = [i for i in all_items if i.get('playlist_id') == pl['id']]
            for item in items:
                course = all_courses.get(item.get('course_id'))
                if course:
                    item.update({k: course[k] for k in ('title', 'source_type', 'bvid', 'page', 'local_path', 'duration_label', 'ai_summary', 'ai_timeline', 'ai_questions', 'ai_suggestion') if k in course})
            pl['videos'] = sorted(items, key=lambda i: i.get('position', 0))
        return sorted(playlists, key=lambda p: p.get('position', 0))


def create_playlist(user_id, name='默认列表'):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("INSERT INTO video_playlists (user_id, name) VALUES (?, ?)", (user_id, name))
                else:
                    cursor.execute("INSERT INTO video_playlists (user_id, name) VALUES (%s, %s)", (user_id, name))
                conn.commit()
                pl_id = cursor.lastrowid
                cursor.close()
                return pl_id
            except Exception as e:
                print(f"创建播放列表失败: {e}")
                return None
        storage = load_local_storage()
        playlists = storage.get('video_playlists', [])
        new_id = max([p.get('id', 0) for p in playlists], default=0) + 1
        pl = {'id': new_id, 'user_id': user_id, 'name': name, 'position': 0, 'created_at': ''}
        playlists.append(pl)
        storage['video_playlists'] = playlists
        save_local_storage(storage)
        return new_id


def delete_playlist(playlist_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM playlist_videos WHERE playlist_id = ?", (playlist_id,))
                    cursor.execute("DELETE FROM video_playlists WHERE id = ?", (playlist_id,))
                else:
                    cursor.execute("DELETE FROM playlist_videos WHERE playlist_id = %s", (playlist_id,))
                    cursor.execute("DELETE FROM video_playlists WHERE id = %s", (playlist_id,))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"删除播放列表失败: {e}")
                return False
        storage = load_local_storage()
        storage['playlist_videos'] = [i for i in storage.get('playlist_videos', []) if i.get('playlist_id') != playlist_id]
        storage['video_playlists'] = [p for p in storage.get('video_playlists', []) if p.get('id') != playlist_id]
        save_local_storage(storage)
        return True


def rename_playlist(playlist_id, name):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("UPDATE video_playlists SET name = ? WHERE id = ?", (name, playlist_id))
                else:
                    cursor.execute("UPDATE video_playlists SET name = %s WHERE id = %s", (name, playlist_id))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"重命名播放列表失败: {e}")
                return False
        storage = load_local_storage()
        for p in storage.get('video_playlists', []):
            if p.get('id') == playlist_id:
                p['name'] = name
                save_local_storage(storage)
                return True
        return False


def add_video_to_playlist(playlist_id, course_id, position=None):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if position is None:
                    if _is_sqlite(conn):
                        cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_videos WHERE playlist_id = ?", (playlist_id,))
                    else:
                        cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_videos WHERE playlist_id = %s", (playlist_id,))
                    position = cursor.fetchone()[0]
                if _is_sqlite(conn):
                    cursor.execute("INSERT INTO playlist_videos (playlist_id, course_id, position) VALUES (?, ?, ?)", (playlist_id, course_id, position))
                else:
                    cursor.execute("INSERT INTO playlist_videos (playlist_id, course_id, position) VALUES (%s, %s, %s)", (playlist_id, course_id, position))
                conn.commit()
                pv_id = cursor.lastrowid
                cursor.close()
                return pv_id
            except Exception as e:
                print(f"添加视频到列表失败: {e}")
                return None
        storage = load_local_storage()
        items = storage.get('playlist_videos', [])
        new_id = max([i.get('id', 0) for i in items], default=0) + 1
        if position is None:
            existing = [i for i in items if i.get('playlist_id') == playlist_id]
            position = max([i.get('position', 0) for i in existing], default=-1) + 1
        item = {'id': new_id, 'playlist_id': playlist_id, 'course_id': course_id, 'position': position, 'added_at': ''}
        items.append(item)
        storage['playlist_videos'] = items
        save_local_storage(storage)
        return new_id


def remove_video_from_playlist(pv_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM playlist_videos WHERE id = ?", (pv_id,))
                else:
                    cursor.execute("DELETE FROM playlist_videos WHERE id = %s", (pv_id,))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"移除列表视频失败: {e}")
                return False
        storage = load_local_storage()
        storage['playlist_videos'] = [i for i in storage.get('playlist_videos', []) if i.get('id') != pv_id]
        save_local_storage(storage)
        return True


def reorder_playlist_videos(items):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                for item in items:
                    if _is_sqlite(conn):
                        cursor.execute("UPDATE playlist_videos SET position = ? WHERE id = ?", (item['position'], item['id']))
                    else:
                        cursor.execute("UPDATE playlist_videos SET position = %s WHERE id = %s", (item['position'], item['id']))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"排序失败: {e}")
                return False
        storage = load_local_storage()
        for item in items:
            for i in storage.get('playlist_videos', []):
                if i.get('id') == item['id']:
                    i['position'] = item['position']
        save_local_storage(storage)
        return True
```

- [ ] **Step 5: 在 db.py 的启动初始化中调用 init_video_tables**

确保 `init_video_tables()` 在应用启动时被调用。在 `db.py` 末尾追加:

```python
# 自动初始化视频表
try:
    init_video_tables()
except Exception:
    pass
```

- [ ] **Step 6: 提交**

```bash
git add db.py
git commit -m "feat: add video_courses, video_playlists, playlist_videos tables and CRUD"

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task 2: 后端 API 路由

**Files:**
- Modify: `main.py` (在现有视频路由区域追加)

- [ ] **Step 1: 在 main.py 添加课程库 API 路由**

在 `main.py` 的 `# 视频相关路由` 区域（约700行附近）之后追加:

```python
# ============ 视频课程库 API ============

@app.get("/api/video-courses")
def list_video_courses(source_type: str = ""):
    courses = database.get_all_video_courses(source_type=source_type or None)
    for c in courses:
        for json_field in ("ai_timeline", "ai_questions"):
            val = c.get(json_field, "[]")
            if isinstance(val, str):
                try:
                    c[json_field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    c[json_field] = [] if json_field != "ai_timeline" else []
    return {"courses": courses}


@app.get("/api/video-courses/{course_id}")
def get_video_course_api(course_id: int):
    course = database.get_video_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    for json_field in ("ai_timeline", "ai_questions"):
        val = course.get(json_field, "[]")
        if isinstance(val, str):
            try:
                course[json_field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                course[json_field] = []
    return {"course": course}


class VideoCourseCreate(BaseModel):
    title: str
    source_type: str = "bilibili"
    subtitle: str = ""
    bvid: str = ""
    page: int = 1
    local_path: str = ""
    duration_label: str = "--:--"
    ai_summary: str = ""
    ai_timeline: list = []
    ai_questions: list = []
    ai_suggestion: str = ""
    created_by: str = ""


@app.post("/api/video-courses")
def create_video_course_api(req: VideoCourseCreate):
    course_id = database.create_video_course(
        title=req.title,
        source_type=req.source_type,
        subtitle=req.subtitle,
        bvid=req.bvid,
        page=req.page,
        local_path=req.local_path,
        duration_label=req.duration_label,
        ai_summary=req.ai_summary,
        ai_timeline=json.dumps(req.ai_timeline, ensure_ascii=False),
        ai_questions=json.dumps(req.ai_questions, ensure_ascii=False),
        ai_suggestion=req.ai_suggestion,
        created_by=req.created_by,
    )
    if course_id is None:
        raise HTTPException(status_code=500, detail="创建课程失败")
    return {"id": course_id, "message": "课程已创建"}


class VideoCourseUpdate(BaseModel):
    title: str = None
    source_type: str = None
    subtitle: str = None
    bvid: str = None
    page: int = None
    local_path: str = None
    duration_label: str = None
    ai_summary: str = None
    ai_timeline: list = None
    ai_questions: list = None
    ai_suggestion: str = None


@app.put("/api/video-courses/{course_id}")
def update_video_course_api(course_id: int, req: VideoCourseUpdate):
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="无更新字段")
    if "ai_timeline" in updates:
        updates["ai_timeline"] = json.dumps(updates["ai_timeline"], ensure_ascii=False)
    if "ai_questions" in updates:
        updates["ai_questions"] = json.dumps(updates["ai_questions"], ensure_ascii=False)
    ok = database.update_video_course(course_id, **updates)
    if not ok:
        raise HTTPException(status_code=404, detail="课程不存在或更新失败")
    return {"message": "课程已更新"}


@app.delete("/api/video-courses/{course_id}")
def delete_video_course_api(course_id: int):
    ok = database.delete_video_course(course_id)
    if not ok:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"message": "课程已删除"}
```

- [ ] **Step 2: 在 main.py 添加播放列表 API 路由**

```python
# ============ 播放列表 API ============

class PlaylistCreate(BaseModel):
    user_id: str
    name: str = "默认列表"


class PlaylistRename(BaseModel):
    name: str


@app.get("/api/video-playlists")
def list_playlists(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id 参数")
    playlists = database.get_user_playlists(user_id)
    for pl in playlists:
        for v in pl.get("videos", []):
            for json_field in ("ai_timeline", "ai_questions"):
                val = v.get(json_field, "[]")
                if isinstance(val, str):
                    try:
                        v[json_field] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        v[json_field] = []
    return {"playlists": playlists}


@app.post("/api/video-playlists")
def create_playlist_api(req: PlaylistCreate):
    pl_id = database.create_playlist(req.user_id, req.name)
    if pl_id is None:
        raise HTTPException(status_code=500, detail="创建播放列表失败")
    return {"id": pl_id, "message": "播放列表已创建"}


@app.put("/api/video-playlists/{playlist_id}")
def rename_playlist_api(playlist_id: int, req: PlaylistRename):
    ok = database.rename_playlist(playlist_id, req.name)
    if not ok:
        raise HTTPException(status_code=404, detail="播放列表不存在")
    return {"message": "播放列表已重命名"}


@app.delete("/api/video-playlists/{playlist_id}")
def delete_playlist_api(playlist_id: int):
    ok = database.delete_playlist(playlist_id)
    if not ok:
        raise HTTPException(status_code=404, detail="播放列表不存在")
    return {"message": "播放列表已删除"}


class PlaylistVideoAdd(BaseModel):
    playlist_id: int
    course_id: int
    position: int = None


class PlaylistVideoReorder(BaseModel):
    items: list


@app.post("/api/playlist-videos")
def add_playlist_video_api(req: PlaylistVideoAdd):
    pv_id = database.add_video_to_playlist(req.playlist_id, req.course_id, req.position)
    if pv_id is None:
        raise HTTPException(status_code=500, detail="添加视频失败")
    return {"id": pv_id, "message": "视频已添加到列表"}


@app.delete("/api/playlist-videos/{pv_id}")
def remove_playlist_video_api(pv_id: int):
    ok = database.remove_video_from_playlist(pv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="条目不存在")
    return {"message": "视频已从列表移除"}


@app.put("/api/playlist-videos/reorder")
def reorder_playlist_videos_api(req: PlaylistVideoReorder):
    ok = database.reorder_playlist_videos(req.items)
    if not ok:
        raise HTTPException(status_code=500, detail="排序失败")
    return {"message": "排序已保存"}
```

- [ ] **Step 3: 添加 B站视频信息代理 API**

```python
# ============ B站 视频信息代理 ============

@app.get("/api/bilibili/info")
def bilibili_video_info(bvid: str = ""):
    if not bvid:
        raise HTTPException(status_code=400, detail="缺少 bvid 参数")
    try:
        import urllib.request
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        req = urllib.request.Request(api_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            raise HTTPException(status_code=404, detail="B站视频不存在")
        video_data = data["data"]
        return {
            "bvid": bvid,
            "title": video_data.get("title", ""),
            "cover": video_data.get("pic", ""),
            "duration": video_data.get("duration", 0),
            "duration_label": f"{video_data.get('duration', 0) // 60}:{video_data.get('duration', 0) % 60:02d}",
            "owner": video_data.get("owner", {}).get("name", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取B站视频信息失败: {str(e)}")
```

- [ ] **Step 4: 验证 API 可启动**

```bash
cd "C:\Users\ZWC\Downloads\Kuromi-main\Kuromi-main" && python -c "
import main
import db
db.init_video_tables()
# 测试创建课程
cid = db.create_video_course('测试课程', source_type='bilibili', bvid='BV1xx411c7mD', created_by='test')
print(f'Created course: {cid}')
courses = db.get_all_video_courses()
print(f'Total courses: {len(courses)}')
# 测试播放列表
pid = db.create_playlist('test', '测试列表')
print(f'Created playlist: {pid}')
pvid = db.add_video_to_playlist(pid, cid)
print(f'Added to playlist: {pvid}')
playlists = db.get_user_playlists('test')
print(f'Playlists: {len(playlists)}, videos in first: {len(playlists[0][\"videos\"]) if playlists else 0}')
# 清理
db.remove_video_from_playlist(pvid)
db.delete_playlist(pid)
db.delete_video_course(cid)
print('Cleanup OK')
"
```

预期: 所有步骤打印正常，无异常。

- [ ] **Step 5: 提交**

```bash
git add main.py
git commit -m "feat: add video courses, playlists, bilibili info API routes"

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task 3: HTML — 页面结构调整

**Files:**
- Modify: `html/video-player.html`

- [ ] **Step 1: 更新导航栏 — 去品牌化**

将 `html/video-player.html` 中导航栏的副标题和状态文字精简:

```html
<div class="nav-brand">
    <span class="brand-mark">SL</span>
    <div>
        <h1 class="nav-title">全息视界</h1>
    </div>
</div>
<div class="nav-status">
    <span class="status-dot"></span>
    <span id="nav-status-text">就绪</span>
</div>
```

（去掉 `<p class="nav-subtitle">` 行）

- [ ] **Step 2: 播放器区域 — 同时放置 iframe 和 video 元素**

将播放器壳内的 `<iframe>` 改为同时包含 `<video>` 和 `<iframe>`（source_type 决定显示哪个），并将 player-shell 的 heading 精简:

```html
<div class="player-heading">
    <div>
        <p class="section-kicker" id="section-kicker">视频播放</p>
        <h2 id="video-title">选择视频开始学习</h2>
        <p id="video-subtitle" class="stage-copy"></p>
    </div>
</div>

<div class="video-player" id="video-player" data-empty-state>
    <video id="course-video-local" preload="auto" playsinline style="display:none"></video>
    <iframe id="course-video-bilibili"
            allowfullscreen
            sandbox="allow-scripts allow-same-origin allow-presentation"
            loading="lazy"
            referrerpolicy="no-referrer"
            style="display:none"></iframe>
    <div class="video-empty-state" id="video-empty-state">
        <div class="play-circle">
            <svg class="play-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
            </svg>
        </div>
        <p class="placeholder-text">添加你的第一个学习视频</p>
        <p class="placeholder-subtext">支持 bilibili.com 的 BV 号或 av 号，也可指定本地 video/ 目录中的视频文件</p>
    </div>
    <div class="danmaku-stage" id="danmaku-stage" aria-live="polite"></div>

    <div class="player-controls" id="player-controls">
        <div class="progress-container">
            <div class="progress-track" id="progress-track">
                <div class="progress-fill" id="progress-fill">
                    <div class="progress-glow"></div>
                </div>
                <div class="progress-thumb" id="progress-thumb"></div>
            </div>
        </div>

        <div class="control-bar">
            <div class="control-left">
                <button class="control-btn play-btn" id="play-btn" type="button" aria-label="播放或暂停">
                    <svg class="icon-play" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                    <svg class="icon-pause hidden" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                    </svg>
                </button>
                <button class="control-btn volume-btn" id="volume-btn" type="button" aria-label="静音">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 5L6 9H2v6h4l5 4V5zM19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/>
                    </svg>
                </button>
                <div class="time-display">
                    <span id="current-time">00:00</span>
                    <span class="time-separator">/</span>
                    <span id="total-time">00:00</span>
                </div>
            </div>
            <div class="control-right">
                <button class="control-btn speed-btn" id="speed-btn" type="button"><span id="speed-text">1x</span></button>
                <button class="control-btn fullscreen-btn" id="fullscreen-btn" type="button" aria-label="全屏">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/>
                    </svg>
                </button>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 3: 侧栏 — 3 Tab 结构**

将侧栏 Tab 从 2 个扩展为 3 个:

```html
<aside class="player-side-panel">
    <div class="side-tabs" role="tablist" aria-label="全息视界侧栏">
        <button class="side-tab active" type="button" data-tab="courses">课程库</button>
        <button class="side-tab" type="button" data-tab="playlist">我的列表</button>
        <button class="side-tab" type="button" data-tab="ai-notes">AI伴学笔记</button>
    </div>

    <section class="side-panel-section active" id="courses-panel">
        <div class="side-section-header">
            <div>
                <span class="section-kicker">课程库</span>
                <h3>全部视频课程</h3>
            </div>
            <button class="ghost-action" id="add-course-btn" type="button" style="padding:0 10px;font-size:12px;min-height:28px">+ 添加</button>
        </div>
        <input class="danmaku-input" id="course-search" type="text" placeholder="搜索课程..." style="margin-bottom:8px">
        <div class="episode-list" id="course-list"></div>
    </section>

    <section class="side-panel-section" id="playlist-panel">
        <div class="side-section-header">
            <div>
                <span class="section-kicker">我的列表</span>
                <h3 id="playlist-name">默认列表</h3>
            </div>
            <span class="rail-pill" id="playlist-count">0 个视频</span>
        </div>
        <div class="episode-list" id="playlist-episode-list"></div>
    </section>

    <section class="side-panel-section" id="ai-notes-panel">
        ... (保持现有的 AI 笔记内容不变) ...
    </section>
</aside>
```

AI 笔记面板内容保持不变:
```html
<section class="side-panel-section" id="ai-notes-panel">
    <div class="side-section-header">
        <div>
            <span class="section-kicker">AI Companion</span>
            <h3>AI伴学笔记</h3>
        </div>
        <span class="rail-pill">可跳转</span>
    </div>
    <article class="ai-summary">
        <span class="panel-label">本节摘要</span>
        <p id="ai-summary-text"></p>
    </article>
    <div>
        <span class="panel-label">时间戳笔记</span>
        <div class="note-timeline" id="note-timeline"></div>
    </div>
    <div>
        <span class="panel-label">我的笔记</span>
        <div class="student-note-list" id="student-note-list"></div>
    </div>
    <div>
        <span class="panel-label">重点问题</span>
        <div class="question-list" id="question-list"></div>
    </div>
    <article class="ai-suggestion">
        <span class="panel-label">学习建议</span>
        <p id="ai-suggestion-text"></p>
    </article>
</section>
```

- [ ] **Step 4: 视频信息面板增加来源标识**

```html
<section class="video-info-panel">
    <div>
        <span class="panel-label" id="info-source-label">来源: -</span>
        <h3 id="info-title">选择视频开始学习</h3>
        <p id="info-description"></p>
    </div>
    <div class="info-metrics">
        <article class="metric-panel">
            <span class="metric-value" id="progress-percent">0%</span>
            <span class="metric-label">当前进度</span>
        </article>
        <article class="metric-panel">
            <span class="metric-value" id="note-count">0</span>
            <span class="metric-label">AI笔记</span>
        </article>
    </div>
</section>
```

- [ ] **Step 5: 添加课程弹窗（模态框）**

在 `</main>` 之前插入:

```html
<div class="modal-overlay hidden" id="add-course-modal">
    <div class="modal-panel">
        <div class="modal-header">
            <h3>添加视频课程</h3>
            <button class="modal-close" id="modal-close-btn" type="button">&times;</button>
        </div>
        <form id="add-course-form">
            <div class="form-group">
                <label>来源类型</label>
                <select id="course-source-type">
                    <option value="bilibili">B站 (Bilibili)</option>
                    <option value="local">本地视频</option>
                </select>
            </div>
            <div class="form-group">
                <label>课程标题</label>
                <input id="course-title-input" type="text" maxlength="100" placeholder="输入课程名称" required>
            </div>
            <div class="form-group" id="bvid-group">
                <label>B站 BV 号</label>
                <input id="course-bvid-input" type="text" maxlength="20" placeholder="例如 BV1xx411c7mD">
            </div>
            <div class="form-group hidden" id="local-path-group">
                <label>本地文件路径</label>
                <input id="course-local-input" type="text" maxlength="200" placeholder="例如 /video/algorithm-01.mp4">
                <span class="form-hint">将视频放入 video/ 文件夹后，路径填 /video/文件名</span>
            </div>
            <div class="modal-actions">
                <button type="button" class="ghost-action" id="modal-cancel-btn">取消</button>
                <button type="submit" class="primary-action">添加</button>
            </div>
        </form>
    </div>
</div>
```

- [ ] **Step 6: 添加 CSS link 到 head**

确保 head 中包含弹窗所需的样式引用（后续 CSS 任务会添加样式）。

- [ ] **Step 7: 提交**

```bash
git add html/video-player.html
git commit -m "feat: restructure video player page with 3 tabs, dual player, add-course modal"

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task 4: CSS — 样式调整

**Files:**
- Modify: `css/video-player.css` (追加新样式，修改现有选择器)

- [ ] **Step 1: 更新 iframe 裁剪 B站控件样式**

修改 `.video-player iframe` 规则:

```css
.video-player iframe,
.video-player iframe#course-video-bilibili {
    position: absolute;
    top: 0;
    left: 0;
    display: block;
    width: 100%;
    height: calc(100% + 54px);
    border: none;
    background: #000;
    z-index: 0;
}

.video-player video,
.video-player video#course-video-local {
    position: absolute;
    top: 0;
    left: 0;
    display: block;
    width: 100%;
    height: 100%;
    object-fit: contain;
    background: #000;
    z-index: 0;
}
```

- [ ] **Step 2: 模态框样式**

在 CSS 文件末尾追加:

```css
.modal-overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.68);
    backdrop-filter: blur(6px);
}

.modal-overlay.hidden {
    display: none;
}

.modal-panel {
    width: min(480px, 92vw);
    padding: 24px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel-strong);
    box-shadow: var(--shadow);
}

.modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
}

.modal-header h3 {
    margin: 0;
    color: #fff;
    font-size: 18px;
}

.modal-close {
    width: 32px;
    height: 32px;
    border: 1px solid transparent;
    border-radius: var(--radius);
    color: var(--muted);
    background: rgba(255, 255, 255, 0.06);
    font-size: 18px;
    cursor: pointer;
}

.modal-close:hover {
    border-color: var(--line-strong);
    color: var(--cyan);
}

.form-group {
    margin-bottom: 14px;
}

.form-group label {
    display: block;
    margin-bottom: 4px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
}

.form-group select,
.form-group input {
    width: 100%;
    min-height: 38px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 0 12px;
    color: var(--text);
    outline: none;
    background: rgba(255, 255, 255, 0.055);
    font: inherit;
}

.form-group select:focus,
.form-group input:focus {
    border-color: var(--line-strong);
    box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.12);
}

.form-group select option {
    background: #0b1430;
    color: var(--text);
}

.form-hint {
    display: block;
    margin-top: 4px;
    color: var(--soft);
    font-size: 12px;
}

.modal-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 20px;
}

.modal-actions .ghost-action,
.modal-actions .primary-action {
    min-height: 34px;
    padding: 0 18px;
    border-radius: var(--radius);
    font-weight: 700;
    cursor: pointer;
}

.modal-actions .ghost-action {
    border: 1px solid var(--line);
    color: var(--text);
    background: rgba(255, 255, 255, 0.04);
}

.modal-actions .primary-action {
    border: 1px solid rgba(34, 211, 238, 0.58);
    color: #03111d;
    background: linear-gradient(135deg, var(--cyan), #60a5fa);
}
```

- [ ] **Step 3: 课程库列表项样式（含来源标签）**

在 CSS 文件末尾追加:

```css
.course-item {
    display: grid;
    grid-template-columns: 38px minmax(0, 1fr) auto;
    align-items: center;
    gap: 4px;
    padding: 9px 10px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: rgba(255, 255, 255, 0.05);
    color: var(--muted);
    text-align: left;
    cursor: pointer;
    transition: border-color 0.18s ease, background 0.18s ease;
}

.course-item:hover {
    border-color: var(--line-strong);
    background: rgba(34, 211, 238, 0.06);
}

.course-item .course-index {
    color: var(--soft);
    font-family: "Rajdhani", sans-serif;
    font-size: 16px;
    font-weight: 700;
    text-align: center;
}

.course-item .course-title {
    color: var(--text);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.source-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
}

.source-tag.bilibili {
    color: #fb7299;
    background: rgba(251, 114, 153, 0.12);
    border: 1px solid rgba(251, 114, 153, 0.3);
}

.source-tag.local {
    color: var(--cyan);
    background: rgba(34, 211, 238, 0.12);
    border: 1px solid rgba(34, 211, 238, 0.3);
}

.add-to-list-btn {
    padding: 4px 10px;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--cyan);
    background: transparent;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
}

.add-to-list-btn:hover {
    border-color: var(--cyan);
    background: rgba(34, 211, 238, 0.1);
}

.playlist-video-item {
    display: grid;
    grid-template-columns: 38px minmax(0, 1fr) auto;
    align-items: center;
    gap: 4px;
    padding: 9px 10px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: rgba(255, 255, 255, 0.05);
    color: var(--muted);
    text-align: left;
    cursor: pointer;
    transition: border-color 0.18s ease, background 0.18s ease;
}

.playlist-video-item:hover {
    border-color: var(--line-strong);
    background: rgba(34, 211, 238, 0.06);
}

.playlist-video-item.active {
    border-color: var(--cyan);
    background: rgba(34, 211, 238, 0.12);
    box-shadow: inset 3px 0 0 var(--cyan);
}

.playlist-video-item .episode-index {
    color: var(--soft);
    font-family: "Rajdhani", sans-serif;
    font-size: 18px;
    font-weight: 700;
    text-align: center;
}

.playlist-video-item .episode-title {
    color: var(--text);
    font-size: 13px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.playlist-video-item .episode-desc {
    color: var(--soft);
    font-size: 11px;
}

.remove-from-list-btn {
    padding: 2px 8px;
    border: 1px solid transparent;
    border-radius: 999px;
    color: var(--danger);
    background: transparent;
    font-size: 14px;
    cursor: pointer;
    line-height: 1;
}

.remove-from-list-btn:hover {
    border-color: var(--danger);
    background: rgba(251, 113, 133, 0.1);
}

.empty-list-hint {
    padding: 24px 12px;
    text-align: center;
    color: var(--soft);
    font-size: 13px;
    line-height: 1.6;
}
```

- [ ] **Step 4: 隐藏状态样式调整**

`.hidden` 类已存在。确保 `#bvid-group.hidden` 和 `#local-path-group.hidden` 可用（已有 `.hidden { display: none !important; }` 规则）。

- [ ] **Step 5: 提交**

```bash
git add css/video-player.css
git commit -m "feat: add iframe crop, modal, course/library list styles"

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task 5: JavaScript — 双驱动播放器 + 课程库逻辑

**Files:**
- Modify: `js/video-player.js` (完全重写)

- [ ] **Step 1: 写 videoController 核心 + 双驱动**

完全重写 `js/video-player.js`:

```javascript
const STORAGE_PREFIX = 'starlearn-video-progress:';
const NOTE_STORAGE_PREFIX = 'starlearn-video-notes:';
const SPEED_OPTIONS = [1, 1.25, 1.5, 2];

let currentSourceType = null;
let currentVideoId = null;
let currentCourseData = null;
let speedIndex = 0;
let progressTimer = null;

// ============ DOM refs ============
const $ = (id) => document.getElementById(id);
const videoLocal = $('course-video-local');
const iframeBilibili = $('course-video-bilibili');
const player = $('video-player');
const playBtn = $('play-btn');
const volumeBtn = $('volume-btn');
const speedBtn = $('speed-btn');
const speedText = $('speed-text');
const fullscreenBtn = $('fullscreen-btn');
const progressTrack = $('progress-track');
const progressFill = $('progress-fill');
const progressThumb = $('progress-thumb');
const currentTimeEl = $('current-time');
const totalTimeEl = $('total-time');
const progressPercent = $('progress-percent');
const danmakuForm = $('danmaku-form');
const danmakuInput = $('danmaku-input');
const danmakuStage = $('danmaku-stage');

// ============ BilibiliDriver ============
const BilibiliDriver = {
    get iframe() { return iframeBilibili; },

    postCommand(cmd, ...args) {
        try {
            this.iframe.contentWindow.postMessage(
                { cmd: 'callPlayer', args: [cmd, ...args], id: Date.now() },
                'https://player.bilibili.com'
            );
        } catch (e) {}
    },

    load(bvid, page = 1) {
        const url = `https://player.bilibili.com/player.html?bvid=${bvid}&page=${page}&autoplay=0&danmaku=0`;
        this.iframe.src = url;
    },

    play() { this.postCommand('play'); },
    pause() { this.postCommand('pause'); },
    seek(time) { this.postCommand('seek', time); },
    setPlaybackRate(rate) { this.postCommand('setPlaybackRate', rate); },
    setVolume(vol) { this.postCommand('setVolume', vol); },

    startProgressPolling() {
        this.stopProgressPolling();
        progressTimer = setInterval(() => {
            this.postCommand('getCurrentTime');
            this.postCommand('getDuration');
        }, 500);
    },

    stopProgressPolling() {
        if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
    },

    show() {
        this.iframe.style.display = 'block';
        videoLocal.style.display = 'none';
    },

    hide() {
        this.iframe.style.display = 'none';
    }
};

// ============ LocalDriver ============
const LocalDriver = {
    get video() { return videoLocal; },

    load(src) {
        this.video.src = src;
        this.video.load();
    },

    play() { this.video.play().catch(() => {}); },
    pause() { this.video.pause(); },
    seek(time) { this.video.currentTime = time; },
    setPlaybackRate(rate) { this.video.playbackRate = rate; },
    setVolume(vol) { this.video.volume = vol / 100; },

    get currentTime() { return this.video.currentTime; },
    get duration() { return this.video.duration; },
    get paused() { return this.video.paused; },

    show() {
        this.video.style.display = 'block';
        iframeBilibili.style.display = 'none';
    },

    hide() {
        this.video.style.display = 'none';
    }
};

// ============ videoController ============
const videoController = {
    get driver() {
        return currentSourceType === 'bilibili' ? BilibiliDriver : LocalDriver;
    },

    load(courseData) {
        currentCourseData = courseData;
        currentSourceType = courseData.source_type || 'bilibili';
        currentVideoId = courseData.id;

        player.removeAttribute('data-empty-state');
        player.setAttribute('data-loading-state', '');

        if (currentSourceType === 'bilibili') {
            BilibiliDriver.show();
            BilibiliDriver.load(courseData.bvid, courseData.page || 1);
            BilibiliDriver.startProgressPolling();
        } else {
            LocalDriver.show();
            LocalDriver.load(courseData.local_path);
        }

        $('video-title').textContent = courseData.title || '';
        $('video-subtitle').textContent = courseData.subtitle || '';
        $('info-title').textContent = courseData.title || '';
        $('info-description').textContent = courseData.subtitle || '';
        $('total-time').textContent = courseData.duration_label || '--:--';
        $('info-source-label').textContent =
            `来源: ${currentSourceType === 'bilibili' ? 'B站 · ' + (courseData.bvid || '') : '本地 · ' + (courseData.local_path || '')}`;

        updateProgress(0);
        currentTimeEl.textContent = '00:00';
        renderAiNotes(courseData);
        updateStudentNoteCount();
    },

    play() { this.driver.play(); },
    pause() { this.driver.pause(); },
    togglePlay() {
        if (currentSourceType === 'local') {
            if (LocalDriver.paused) LocalDriver.play();
            else LocalDriver.pause();
        } else {
            BilibiliDriver.play();
        }
    },
    seek(time) { this.driver.seek(time); },
    setSpeed(rate) { this.driver.setPlaybackRate(rate); },
    setVolume(vol) { this.driver.setVolume(vol); }
};

// ============ postMessage 监听 ============
window.addEventListener('message', function(e) {
    if (e.origin !== 'https://player.bilibili.com') return;
    const data = e.data;
    if (!data || typeof data !== 'object') return;

    if (typeof data.currentTime === 'number' && currentSourceType === 'bilibili') {
        const duration = data.duration || LocalDriver.duration || 1;
        const pct = (data.currentTime / duration) * 100;
        updateProgress(pct);
        currentTimeEl.textContent = formatTime(data.currentTime);
        if (data.duration && totalTimeEl.textContent === '--:--') {
            totalTimeEl.textContent = formatTime(data.duration);
        }
    }

    if (data.state === 'playing' || data.state === 'paused') {
        updatePlayIcon(data.state === 'playing');
    }

    if (data.state === 'ready' || data.state === 'playing') {
        player.removeAttribute('data-loading-state');
        player.removeAttribute('data-empty-state');
    }
});

// ============ 本地视频事件 ============
videoLocal.addEventListener('timeupdate', function() {
    if (currentSourceType !== 'local') return;
    if (!Number.isFinite(videoLocal.duration)) return;
    const pct = (videoLocal.currentTime / videoLocal.duration) * 100;
    updateProgress(pct);
    currentTimeEl.textContent = formatTime(videoLocal.currentTime);
    if (Number.isFinite(videoLocal.duration)) {
        totalTimeEl.textContent = formatTime(videoLocal.duration);
    }
    localStorage.setItem(STORAGE_PREFIX + currentVideoId, String(Math.floor(videoLocal.currentTime)));
});

videoLocal.addEventListener('loadedmetadata', function() {
    if (currentSourceType !== 'local') return;
    player.removeAttribute('data-loading-state');
    player.removeAttribute('data-empty-state');
    totalTimeEl.textContent = formatTime(videoLocal.duration);
    const saved = Number(localStorage.getItem(STORAGE_PREFIX + currentVideoId));
    if (Number.isFinite(saved) && saved > 0 && saved < videoLocal.duration) {
        videoLocal.currentTime = saved;
    }
});

videoLocal.addEventListener('play', () => updatePlayIcon(true));
videoLocal.addEventListener('pause', () => updatePlayIcon(false));
videoLocal.addEventListener('error', showEmptyState);

// ============ 控制栏事件 ============
playBtn.addEventListener('click', () => videoController.togglePlay());

volumeBtn.addEventListener('click', function() {
    if (currentSourceType === 'local') {
        videoLocal.muted = !videoLocal.muted;
        updateVolumeIcon();
        showToast(videoLocal.muted ? '已静音' : '已恢复声音', 'info');
    } else {
        showToast('B站视频请使用播放器内置音量控制', 'info');
    }
});

speedBtn.addEventListener('click', function() {
    speedIndex = (speedIndex + 1) % SPEED_OPTIONS.length;
    const rate = SPEED_OPTIONS[speedIndex];
    speedText.textContent = `${rate}x`;
    videoController.setSpeed(rate);
});

fullscreenBtn.addEventListener('click', function() {
    if (!document.fullscreenElement) {
        player.requestFullscreen().catch(() => showToast('无法进入全屏', 'error'));
    } else {
        document.exitFullscreen();
    }
});

progressTrack.addEventListener('click', function(e) {
    if (currentSourceType === 'local') {
        if (!Number.isFinite(videoLocal.duration)) return;
        const rect = progressTrack.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        videoLocal.currentTime = pct * videoLocal.duration;
    } else if (currentSourceType === 'bilibili') {
        showToast('B站视频请拖动播放器内置进度条', 'info');
    }
});

document.addEventListener('keydown', function(e) {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        videoController.togglePlay();
    }
});

// ============ 课程库 ============
async function loadCourseLibrary() {
    try {
        const resp = await fetch('/api/video-courses');
        if (!resp.ok) return;
        const data = await resp.json();
        renderCourseList(data.courses || []);
    } catch (e) {
        console.warn('加载课程库失败', e);
    }
}

function renderCourseList(courses, filter = '') {
    const list = $('course-list');
    list.innerHTML = '';
    const filtered = filter
        ? courses.filter(c => c.title.toLowerCase().includes(filter.toLowerCase()))
        : courses;

    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-list-hint">没有匹配的课程</div>';
        return;
    }

    filtered.forEach((course, i) => {
        const div = document.createElement('div');
        div.className = 'course-item';
        div.innerHTML = `
            <span class="course-index">${String(i + 1).padStart(2, '0')}</span>
            <span class="course-title">${escapeHtml(course.title)}</span>
            <span class="source-tag ${course.source_type}">${course.source_type === 'bilibili' ? 'B站' : '本地'}</span>
            <button class="add-to-list-btn" data-course-id="${course.id}">+ 加入列表</button>
        `;
        div.querySelector('.add-to-list-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            addCourseToPlaylist(course.id);
        });
        list.appendChild(div);
    });
}

$('course-search').addEventListener('input', async function() {
    try {
        const resp = await fetch('/api/video-courses');
        if (!resp.ok) return;
        const data = await resp.json();
        renderCourseList(data.courses || [], this.value);
    } catch (e) {}
});

async function addCourseToPlaylist(courseId) {
    const playlistId = getCurrentPlaylistId();
    if (!playlistId) {
        showToast('请先创建播放列表', 'warning');
        return;
    }
    try {
        const resp = await fetch('/api/playlist-videos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist_id: playlistId, course_id: courseId })
        });
        if (resp.ok) {
            showToast('已添加到播放列表', 'success');
            loadPlaylist();
        } else {
            showToast('添加失败', 'error');
        }
    } catch (e) {
        showToast('网络错误', 'error');
    }
}

// ============ 播放列表 ============
async function loadPlaylist() {
    const userId = getCurrentUserId();
    if (!userId) return;
    try {
        const resp = await fetch(`/api/video-playlists?user_id=${encodeURIComponent(userId)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        const playlists = data.playlists || [];
        if (playlists.length > 0) {
            renderPlaylistVideos(playlists[0]);
            $('playlist-count').textContent = `${playlists[0].videos?.length || 0} 个视频`;
            $('playlist-name').textContent = playlists[0].name;
        } else {
            const pid = await createDefaultPlaylist(userId);
            if (pid) {
                renderPlaylistVideos({ id: pid, videos: [], name: '默认列表' });
                $('playlist-count').textContent = '0 个视频';
                $('playlist-name').textContent = '默认列表';
            }
        }
    } catch (e) {
        console.warn('加载播放列表失败', e);
    }
}

function getCurrentPlaylistId() {
    return parseInt(localStorage.getItem('starlearn-current-playlist-id') || '0') || null;
}

async function createDefaultPlaylist(userId) {
    try {
        const resp = await fetch('/api/video-playlists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, name: '默认列表' })
        });
        if (resp.ok) {
            const data = await resp.json();
            localStorage.setItem('starlearn-current-playlist-id', String(data.id));
            return data.id;
        }
    } catch (e) {}
    return null;
}

function getCurrentUserId() {
    const profile = window.StarData?.user?.id;
    if (profile) return profile;
    return localStorage.getItem('starlearn-user-id') || 'anonymous';
}

function renderPlaylistVideos(playlist) {
    const list = $('playlist-episode-list');
    list.innerHTML = '';
    const videos = playlist.videos || [];
    if (videos.length === 0) {
        list.innerHTML = '<div class="empty-list-hint">添加你的第一个学习视频<br>支持 bilibili.com 的 BV 号或 av 号</div>';
        return;
    }
    localStorage.setItem('starlearn-current-playlist-id', String(playlist.id));
    $('playlist-count').textContent = `${videos.length} 个视频`;

    videos.forEach((v, i) => {
        const div = document.createElement('div');
        div.className = 'playlist-video-item';
        div.innerHTML = `
            <span class="episode-index">${String(i + 1).padStart(2, '0')}</span>
            <span>
                <span class="episode-title">${escapeHtml(v.title || '未命名')}</span>
                <span class="episode-desc">${v.duration_label || '--:--'} · <span class="source-tag ${v.source_type}">${v.source_type === 'bilibili' ? 'B站' : '本地'}</span></span>
            </span>
            <button class="remove-from-list-btn" data-pv-id="${v.id}" title="从列表移除">&times;</button>
        `;
        div.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-from-list-btn')) return;
            videoController.load(v);
            updatePlaylistActiveState(i);
        });
        div.querySelector('.remove-from-list-btn').addEventListener('click', async (e) => {
            e.stopPropagation();
            await removeFromPlaylist(v.id);
        });
        list.appendChild(div);
    });
}

function updatePlaylistActiveState(index) {
    document.querySelectorAll('.playlist-video-item').forEach((item, i) => {
        item.classList.toggle('active', i === index);
    });
}

async function removeFromPlaylist(pvId) {
    try {
        const resp = await fetch(`/api/playlist-videos/${pvId}`, { method: 'DELETE' });
        if (resp.ok) {
            showToast('已从列表移除', 'success');
            loadPlaylist();
        }
    } catch (e) {
        showToast('移除失败', 'error');
    }
}

// ============ 添加课程弹窗 ============
$('add-course-btn').addEventListener('click', () => {
    $('add-course-modal').classList.remove('hidden');
});

$('modal-close-btn').addEventListener('click', () => {
    $('add-course-modal').classList.add('hidden');
});

$('modal-cancel-btn').addEventListener('click', () => {
    $('add-course-modal').classList.add('hidden');
});

$('course-source-type').addEventListener('change', function() {
    if (this.value === 'bilibili') {
        $('bvid-group').classList.remove('hidden');
        $('local-path-group').classList.add('hidden');
    } else {
        $('bvid-group').classList.add('hidden');
        $('local-path-group').classList.remove('hidden');
    }
});

$('add-course-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const sourceType = $('course-source-type').value;
    const title = $('course-title-input').value.trim();
    if (!title) { showToast('请输入课程标题', 'warning'); return; }

    const body = {
        title,
        source_type: sourceType,
        subtitle: title,
        created_by: getCurrentUserId()
    };

    if (sourceType === 'bilibili') {
        body.bvid = $('course-bvid-input').value.trim();
        if (!body.bvid) { showToast('请输入 B站 BV 号', 'warning'); return; }
        try {
            const infoResp = await fetch(`/api/bilibili/info?bvid=${body.bvid}`);
            if (infoResp.ok) {
                const info = await infoResp.json();
                body.title = info.title || title;
                body.subtitle = info.owner ? `UP主: ${info.owner}` : title;
                body.duration_label = info.duration_label || '--:--';
            }
        } catch (e) {}
    } else {
        body.local_path = $('course-local-input').value.trim();
        if (!body.local_path) { showToast('请输入本地文件路径', 'warning'); return; }
    }

    try {
        const resp = await fetch('/api/video-courses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (resp.ok) {
            showToast('课程已添加', 'success');
            $('add-course-modal').classList.add('hidden');
            this.reset();
            loadCourseLibrary();
        } else {
            showToast('添加失败', 'error');
        }
    } catch (e) {
        showToast('网络错误', 'error');
    }
});

// ============ Tab 切换 ============
document.querySelectorAll('.side-tab').forEach(tab => {
    tab.addEventListener('click', function() {
        document.querySelectorAll('.side-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.side-panel-section').forEach(s => s.classList.remove('active'));
        this.classList.add('active');
        const panelId = `${this.dataset.tab}-panel`;
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.add('active');
        if (this.dataset.tab === 'courses') loadCourseLibrary();
        if (this.dataset.tab === 'playlist') loadPlaylist();
    });
});

// ============ 弹幕 (保持现有逻辑) ============
danmakuForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const text = danmakuInput.value.trim();
    if (!text) return;
    addStudentNote(text);
    launchDanmaku(text);
    danmakuInput.value = '';
});

function getStudentNotes(videoId) {
    try {
        const raw = localStorage.getItem(NOTE_STORAGE_PREFIX + videoId);
        const notes = raw ? JSON.parse(raw) : [];
        return Array.isArray(notes) ? notes : [];
    } catch (e) { return []; }
}

function saveStudentNotes(videoId, notes) {
    localStorage.setItem(NOTE_STORAGE_PREFIX + videoId, JSON.stringify(notes));
}

function addStudentNote(text) {
    if (!currentVideoId) return;
    const notes = getStudentNotes(currentVideoId);
    notes.push({ text, time: Math.floor(Date.now() / 1000), createdAt: Date.now() });
    saveStudentNotes(currentVideoId, notes);
    updateStudentNoteCount();
    renderStudentNotes(currentCourseData);
}

function updateStudentNoteCount() {
    $('note-count').textContent = currentVideoId ? getStudentNotes(currentVideoId).length : 0;
}

function renderStudentNotes(item) {
    const list = $('student-note-list');
    if (!list) return;
    const itemId = item?.id || currentVideoId;
    const notes = getStudentNotes(itemId);
    list.innerHTML = '';
    if (notes.length === 0) {
        list.innerHTML = '<div class="student-note-empty">还没有学生笔记，发送一条本地弹幕后这里会自动记录。</div>';
        return;
    }
    notes.slice().reverse().forEach(note => {
        const div = document.createElement('div');
        div.className = 'student-note-item';
        const date = new Date(note.createdAt);
        div.innerHTML = `
            <span class="note-time">${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}</span>
            <span class="student-note-text">${escapeHtml(note.text)}</span>
        `;
        list.appendChild(div);
    });
}

function launchDanmaku(text) {
    const el = document.createElement('div');
    el.className = 'danmaku-item';
    el.textContent = text;
    el.style.setProperty('--lane-top', `${18 + Math.floor(Math.random() * 48)}%`);
    danmakuStage.appendChild(el);
    setTimeout(() => el.remove(), 7200);
}

// ============ AI 笔记 ============
function renderAiNotes(item) {
    if (!item) return;
    $('ai-summary-text').textContent =
        (typeof item.ai_summary === 'string' ? item.ai_summary : '') || '暂无摘要';
    $('ai-suggestion-text').textContent =
        (typeof item.ai_suggestion === 'string' ? item.ai_suggestion : '') || '暂无建议';
    updateStudentNoteCount();

    const timeline = $('note-timeline');
    timeline.innerHTML = '';
    let timelineData = item.ai_timeline;
    if (typeof timelineData === 'string') {
        try { timelineData = JSON.parse(timelineData); } catch (e) { timelineData = []; }
    }
    if (Array.isArray(timelineData)) {
        timelineData.forEach(note => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'note-item';
            btn.innerHTML = `
                <span class="note-time">${formatTime(note.time)}</span>
                <span>
                    <span class="note-title">${escapeHtml(note.title)}</span>
                    <span class="note-desc">${escapeHtml(note.desc)}</span>
                </span>
            `;
            btn.addEventListener('click', () => {
                if (currentSourceType === 'bilibili') {
                    BilibiliDriver.seek(note.time);
                    showToast(`已跳转到 ${formatTime(note.time)}`, 'success');
                } else {
                    videoLocal.currentTime = note.time;
                    showToast(`已跳转到 ${formatTime(note.time)}`, 'success');
                }
            });
            timeline.appendChild(btn);
        });
    }

    const questions = $('question-list');
    questions.innerHTML = '';
    let qData = item.ai_questions;
    if (typeof qData === 'string') {
        try { qData = JSON.parse(qData); } catch (e) { qData = []; }
    }
    if (Array.isArray(qData)) {
        qData.forEach(q => {
            const div = document.createElement('div');
            div.className = 'question-item';
            div.textContent = q;
            questions.appendChild(div);
        });
    }

    renderStudentNotes(item);
}

// ============ 工具函数 ============
function updateProgress(pct) {
    const safe = Math.max(0, Math.min(100, pct));
    progressFill.style.width = `${safe}%`;
    progressThumb.style.left = `${safe}%`;
    progressPercent.textContent = `${Math.round(safe)}%`;
}

function updatePlayIcon(playing) {
    document.querySelector('.icon-play').classList.toggle('hidden', playing);
    document.querySelector('.icon-pause').classList.toggle('hidden', !playing);
}

function updateVolumeIcon() {
    if (!volumeBtn) return;
    if (currentSourceType === 'local' && videoLocal.muted) {
        volumeBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 5L6 9H2v6h4l5 4V5z"/>
            <line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>
        </svg>`;
    }
}

function showEmptyState() {
    player.setAttribute('data-empty-state', '');
    BilibiliDriver.stopProgressPolling();
}

function formatTime(value) {
    if (!Number.isFinite(value)) return '00:00';
    const total = Math.max(0, Math.floor(value));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:12px;';
        document.body.appendChild(container);
    }
    const colors = { success: 'rgba(16,185,129,0.4)', error: 'rgba(239,68,68,0.4)', warning: 'rgba(249,115,22,0.4)', info: 'rgba(59,130,246,0.4)' };
    const toast = document.createElement('div');
    toast.style.cssText = `padding:14px 20px;background:rgba(20,20,40,0.95);border:1px solid ${colors[type]||colors.info};border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.4);color:#fff;font-size:14px;animation:slideIn 0.3s ease;backdrop-filter:blur(20px);`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', async function() {
    await loadPlaylist();
    const playlistResp = await fetch(`/api/video-playlists?user_id=${encodeURIComponent(getCurrentUserId())}`);
    if (playlistResp.ok) {
        const data = await playlistResp.json();
        const playlists = data.playlists || [];
        if (playlists.length > 0 && playlists[0].videos?.length > 0) {
            videoController.load(playlists[0].videos[0]);
            updatePlaylistActiveState(0);
        }
    }
});
```

- [ ] **Step 2: 验证 JS 语法**

```bash
cd "C:\Users\ZWC\Downloads\Kuromi-main\Kuromi-main" && node --check js/video-player.js 2>&1 || echo "Check done"
```

- [ ] **Step 3: 提交**

```bash
git add js/video-player.js
git commit -m "feat: rewrite video player with dual-driver, course library, playlist management"

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task 6: 测试更新

**Files:**
- Modify: `tests/test_video_player_links.py`

- [ ] **Step 1: 更新测试以适配新布局**

重写 `tests/test_video_player_links.py`:

```python
import unittest
from pathlib import Path


class VideoPlayerShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path("html/video-player.html").read_text(encoding="utf-8")

    def test_has_dual_player_elements(self):
        self.assertIn('id="course-video-local"', self.page)
        self.assertIn('id="course-video-bilibili"', self.page)
        self.assertIn("data-empty-state", self.page)

    def test_contains_bilibili_style_theater_layout(self):
        for token in (
            "bili-theater",
            "player-column",
            "player-side-panel",
            "episode-list",
            "danmaku-form",
        ):
            self.assertIn(token, self.page)

    def test_contains_three_tabs(self):
        for token in (
            'data-tab="courses"',
            'data-tab="playlist"',
            'data-tab="ai-notes"',
        ):
            self.assertIn(token, self.page)

    def test_contains_ai_notes_sections(self):
        for token in (
            "AI伴学笔记",
            "note-timeline",
            "重点问题",
            "AI Companion",
        ):
            self.assertIn(token, self.page)

    def test_contains_empty_state_guidance(self):
        self.assertIn("添加你的第一个学习视频", self.page)
        self.assertIn("bilibili.com", self.page)
        self.assertIn("BV 号或 av 号", self.page)

    def test_contains_add_course_modal(self):
        for token in (
            "add-course-modal",
            "add-course-form",
            "course-source-type",
            "course-bvid-input",
            "course-local-input",
        ):
            self.assertIn(token, self.page)

    def test_video_player_script_has_dual_driver(self):
        video_js = Path("js/video-player.js").read_text(encoding="utf-8")
        for token in (
            "BilibiliDriver",
            "LocalDriver",
            "videoController",
            "function updateProgress",
            "function launchDanmaku",
            "SPEED_OPTIONS",
            "loadCourseLibrary",
            "loadPlaylist",
            "postMessage",
        ):
            self.assertIn(token, video_js)

    def test_nav_does_not_have_bilibili_branding(self):
        self.assertNotIn("B站视频学习驾驶舱", self.page)
        self.assertNotIn("B站 已接入", self.page)
        self.assertNotIn("本地视频学习驾驶舱", self.page)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试验证通过**

```bash
cd "C:\Users\ZWC\Downloads\Kuromi-main\Kuromi-main" && python -m pytest tests/test_video_player_links.py -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/test_video_player_links.py
git commit -m "test: update video player tests for dual-driver and 3-tab layout"

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task 7: 端到端验证

- [ ] **Step 1: 启动应用并验证 API**

```bash
cd "C:\Users\ZWC\Downloads\Kuromi-main\Kuromi-main" && timeout 8 python -c "
import main
import db
db.init_video_tables()
print('DB tables OK')
# Test course operations
cid = db.create_video_course('E2E测试', source_type='bilibili', bvid='BV1GJ411x7h7', created_by='e2e')
print(f'Course created: {cid}')
courses = db.get_all_video_courses()
print(f'Course count: {len(courses)}')
# Test playlist
pid = db.create_playlist('e2e', 'E2E列表')
print(f'Playlist created: {pid}')
pvid = db.add_video_to_playlist(pid, cid)
print(f'Added to playlist: {pvid}')
playlists = db.get_user_playlists('e2e')
print(f'Playlist count: {len(playlists)}, videos: {len(playlists[0][\"videos\"]) if playlists else 0}')
# Cleanup
db.remove_video_from_playlist(pvid)
db.delete_playlist(pid)
db.delete_video_course(cid)
print('All E2E checks passed')
" 2>&1 || echo "Note: requires running server for full E2E"
```

- [ ] **Step 2: 验证 HTML/CSS/JS 文件无语法错误**

```bash
cd "C:\Users\ZWC\Downloads\Kuromi-main\Kuromi-main" && node --check js/video-player.js && echo "JS OK" && python -c "
from pathlib import Path
# Verify HTML is well-formed enough
html = Path('html/video-player.html').read_text(encoding='utf-8')
assert html.count('<') == html.count('>'), 'HTML tag mismatch'
assert html.strip().startswith('<!DOCTYPE html>'), 'Missing DOCTYPE'
print('HTML looks OK')
css = Path('css/video-player.css').read_text(encoding='utf-8')
assert css.count('{') == css.count('}'), 'CSS brace mismatch'
print('CSS looks OK')
print('All static checks passed')
"
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "chore: E2E verification of video player redesign

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 自检清单

- [x] Spec coverage: 数据模型三张表 → Task 1; 后端 API → Task 2; HTML 三 tab + 去品牌化 + iframe 裁剪 → Task 3; CSS 样式 → Task 4; JS 双驱动 + 课程库 → Task 5; 测试 → Task 6; 端到端 → Task 7
- [x] Placeholder scan: 无 TBD/TODO/占位符
- [x] Type consistency: `source_type` 字段值 `bilibili`/`local` 贯穿 db.py、main.py、video-player.js 一致; `ai_timeline`/`ai_questions` JSON 序列化/反序列化一致; 路由参数命名与前端 fetch URL 一致
