# 课堂记录持久化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在星识项目中实现学生课堂生成记录的数据库持久化存储，并提供完整的CRUD API。

**Architecture:** 复用现有 `user` 表，通过 `user_id` 关联学生与课堂记录。使用 `classroom_records` 表存储完整课程数据。API层保留与现有JSON文件存储的兼容性。

**Tech Stack:** Python (FastAPI/uvicorn), SQLite/MySQL, JSON文件备份

---

## 文件结构

```
星识/
├── Navicat/setup_database.py    # 添加 classroom_records 建表SQL
├── db.py                         # 添加 5 个数据库CRUD函数
├── main.py                       # 添加/修改 5 个API端点
└── state.py                      # (无需修改，仅确认Pydantic模型)
```

---

## Task 1: 添加 classroom_records 建表SQL

**Files:**
- Modify: `Navicat/setup_database.py`

- [ ] **Step 1: 在 setup_database.py 中添加建表SQL**

找到 `MYSQL_TABLES` 列表末尾，在 `weekly_summary` 表定义之后添加新的表：

```python
    # ──────────────────────────────────────────────────────
    # 25. classroom_records - 课堂记录
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS classroom_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        course_id VARCHAR(100) NOT NULL UNIQUE,
        title VARCHAR(255) NOT NULL DEFAULT '',
        full_data LONGTEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
        INDEX idx_user_id (user_id),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
```

同时在 `TABLE_NAMES` 列表末尾添加 `"classroom_records"`。

- [ ] **Step 2: 验证SQL语法正确**

检查新增的SQL语句是否有语法错误（括号匹配、引号等）。

- [ ] **Step 3: 提交**

```bash
cd 星识 && git add Navicat/setup_database.py && git commit -m "feat(db): add classroom_records table schema"
```

---

## Task 2: 添加数据库CRUD函数

**Files:**
- Modify: `db.py` (在文件末尾添加新函数)

- [ ] **Step 1: 添加 save_classroom_record 函数**

在 `db.py` 末尾添加：

```python
# ============================================================
# 课堂记录 CRUD
# ============================================================

def save_classroom_record(user_id: int, course_id: str, title: str, full_data: str) -> bool:
    """保存课堂记录到数据库"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO classroom_records (user_id, course_id, title, full_data)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(course_id) DO UPDATE SET
                            title=excluded.title,
                            full_data=excluded.full_data,
                            updated_at=datetime('now','localtime')
                    """, (user_id, course_id, title, full_data))
                else:
                    cursor.execute("""
                        INSERT INTO classroom_records (user_id, course_id, title, full_data)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            title=%s, full_data=%s
                    """, (user_id, course_id, title, full_data, title, full_data))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存课堂记录失败: {e}")

        # JSON fallback
        storage = load_local_storage()
        records = storage.get('classroom_records', [])
        for record in records:
            if record.get('course_id') == course_id:
                record.update({'user_id': user_id, 'title': title, 'full_data': full_data})
                save_local_storage(storage)
                return True
        records.append({
            'id': len(records) + 1,
            'user_id': user_id,
            'course_id': course_id,
            'title': title,
            'full_data': full_data,
            'created_at': 'local',
            'updated_at': 'local',
        })
        storage['classroom_records'] = records
        save_local_storage(storage)
        return True
```

- [ ] **Step 2: 添加 get_classroom_records 函数**

```python
def get_classroom_records(user_id: int) -> list:
    """获取指定学生的所有课堂记录（不含full_data）"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        SELECT id, user_id, course_id, title, created_at, updated_at
                        FROM classroom_records WHERE user_id = ?
                        ORDER BY created_at DESC
                    """, (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("""
                        SELECT id, user_id, course_id, title, created_at, updated_at
                        FROM classroom_records WHERE user_id = %s
                        ORDER BY created_at DESC
                    """, (user_id,))
                rows = cursor.fetchall()
                cursor.close()
                return [dict(row) for row in rows] if _is_sqlite(conn) else rows
            except Exception as e:
                print(f"查询课堂记录失败: {e}")

        storage = load_local_storage()
        records = storage.get('classroom_records', [])
        result = []
        for r in records:
            if r.get('user_id') == user_id:
                result.append({
                    'id': r.get('id'),
                    'user_id': r.get('user_id'),
                    'course_id': r.get('course_id'),
                    'title': r.get('title'),
                    'created_at': r.get('created_at'),
                    'updated_at': r.get('updated_at'),
                })
        return sorted(result, key=lambda x: x.get('created_at', ''), reverse=True)
```

- [ ] **Step 3: 添加 get_classroom_record 函数**

```python
def get_classroom_record(course_id: str) -> Optional[dict]:
    """获取单个课堂记录的完整数据"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM classroom_records WHERE course_id = ?", (course_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT * FROM classroom_records WHERE course_id = %s", (course_id,))
                row = cursor.fetchone()
                cursor.close()
                return dict(row) if row and _is_sqlite(conn) else row
            except Exception as e:
                print(f"查询课堂记录失败: {e}")

        storage = load_local_storage()
        for r in storage.get('classroom_records', []):
            if r.get('course_id') == course_id:
                return r
        return None
```

- [ ] **Step 4: 添加 update_classroom_record 函数**

```python
def update_classroom_record(course_id: str, title: str) -> bool:
    """更新课堂标题"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        UPDATE classroom_records SET title = ?,
                            updated_at = datetime('now','localtime')
                        WHERE course_id = ?
                    """, (title, course_id))
                else:
                    cursor.execute("""
                        UPDATE classroom_records SET title = %s
                        WHERE course_id = %s
                    """, (title, course_id))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"更新课堂记录失败: {e}")

        storage = load_local_storage()
        for r in storage.get('classroom_records', []):
            if r.get('course_id') == course_id:
                r['title'] = title
                r['updated_at'] = 'local'
                save_local_storage(storage)
                return True
        return False
```

- [ ] **Step 5: 添加 delete_classroom_record 函数**

```python
def delete_classroom_record(course_id: str) -> bool:
    """删除课堂记录"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM classroom_records WHERE course_id = ?", (course_id,))
                else:
                    cursor.execute("DELETE FROM classroom_records WHERE course_id = %s", (course_id,))
                conn.commit()
                affected = cursor.rowcount
                cursor.close()
                return affected > 0
            except Exception as e:
                print(f"删除课堂记录失败: {e}")

        storage = load_local_storage()
        original_len = len(storage.get('classroom_records', []))
        storage['classroom_records'] = [
            r for r in storage.get('classroom_records', [])
            if r.get('course_id') != course_id
        ]
        save_local_storage(storage)
        return len(storage['classroom_records']) < original_len
```

- [ ] **Step 6: 提交**

```bash
cd 星识 && git add db.py && git commit -m "feat(db): add classroom_records CRUD functions"
```

---

## Task 3: 添加/修改 API 端点

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 修改 save_course API，添加数据库存储**

找到现有的 `@app.post("/api/v2/course/save")` 端点（约5928行），在文件存储之后添加数据库保存逻辑：

```python
@app.post("/api/v2/course/save")
async def save_course(request: CourseSaveRequest):
    """保存课程数据到服务端"""
    course = request.course_data
    if request.student_id:
        course.metadata["student_id"] = request.student_id
    filepath = _get_course_path(course.courseId)

    # 保存到JSON文件
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(course.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    # 同步到数据库
    try:
        user_id = int(request.student_id) if request.student_id else 0
        if user_id and course.courseId:
            full_data = json.dumps(course.model_dump(mode="json"), ensure_ascii=False)
            save_classroom_record(user_id, course.courseId, course.title, full_data)
    except Exception as e:
        print(f"数据库保存失败（非致命）: {e}")

    return {"success": True, "course_id": course.courseId}
```

- [ ] **Step 2: 添加 get_classrooms API（列出学生课堂）**

在 `main.py` 中找一个合适位置添加：

```python
@app.get("/api/v2/classroom/list/{user_id}")
async def get_classrooms(user_id: int):
    """获取指定学生的所有课堂记录列表"""
    records = get_classroom_records(user_id)
    return {"success": True, "records": records}
```

- [ ] **Step 3: 添加 get_classroom API（获取单个课堂详情）**

```python
@app.get("/api/v2/classroom/{course_id}")
async def get_classroom(course_id: str):
    """获取单个课堂的完整数据"""
    record = get_classroom_record(course_id)
    if not record:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return {"success": True, "record": record}
```

- [ ] **Step 4: 添加 update_classroom API（更新标题）**

```python
@app.put("/api/v2/classroom/{course_id}")
async def update_classroom(course_id: str, data: dict[str, Any]):
    """更新课堂标题"""
    title = data.get("title", "")
    if not title:
        raise HTTPException(status_code=400, detail="缺少title参数")

    success = update_classroom_record(course_id, title)
    if not success:
        raise HTTPException(status_code=404, detail="Classroom not found")

    return {"success": True, "course_id": course_id, "title": title}
```

- [ ] **Step 5: 添加 delete_classroom API（删除课堂）**

```python
@app.delete("/api/v2/classroom/{course_id}")
async def delete_classroom(course_id: str):
    """删除课堂记录"""
    success = delete_classroom_record(course_id)

    # 同时删除JSON文件
    filepath = _get_course_path(course_id)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

    if not success:
        raise HTTPException(status_code=404, detail="Classroom not found")

    return {"success": True, "course_id": course_id}
```

- [ ] **Step 6: 在 main.py 顶部添加函数导入**

确保文件顶部有（如果已有则跳过）：
```python
from db import (
    save_classroom_record,
    get_classroom_records,
    get_classroom_record,
    update_classroom_record,
    delete_classroom_record,
)
```

- [ ] **Step 7: 提交**

```bash
cd 星识 && git add main.py && git commit -m "feat(api): add classroom CRUD API endpoints"
```

---

## Task 4: 验证建表脚本

- [ ] **Step 1: 运行建表脚本**

```bash
cd 星识 && python Navicat/setup_database.py
```

预期输出应包含 `classroom_records` 表的创建成功信息。

---

## Task 5: 测试 API 功能

- [ ] **Step 1: 启动服务器**

```bash
cd 星识 && python main.py
```

- [ ] **Step 2: 测试保存课堂**

```bash
curl -X POST http://localhost:8000/api/v2/course/save \
  -H "Content-Type: application/json" \
  -d '{"course_data": {"courseId": "test_001", "title": "测试课堂"}, "student_id": "1"}'
```

- [ ] **Step 3: 测试列出课堂**

```bash
curl http://localhost:8000/api/v2/classroom/list/1
```

- [ ] **Step 4: 测试获取单个课堂**

```bash
curl http://localhost:8000/api/v2/classroom/test_001
```

- [ ] **Step 5: 测试更新标题**

```bash
curl -X PUT http://localhost:8000/api/v2/classroom/test_001 \
  -H "Content-Type: application/json" \
  -d '{"title": "新标题"}'
```

- [ ] **Step 6: 测试删除**

```bash
curl -X DELETE http://localhost:8000/api/v2/classroom/test_001
```

---

## 依赖关系

- Task 1 → Task 2（建表SQL完成后才能添加CRUD函数）
- Task 2 → Task 3（CRUD函数完成后才能添加API）
- Task 1, 2, 3 → Task 4, 5（需要全部完成才能测试）

---

## 验证清单

- [ ] `Navicat/setup_database.py` 包含 `classroom_records` 建表SQL
- [ ] `TABLE_NAMES` 列表包含 `"classroom_records"`
- [ ] `db.py` 包含 5 个课堂记录CRUD函数
- [ ] `main.py` 包含 4 个新API端点
- [ ] `save_course` API 同时保存到文件和数据库
- [ ] 运行 `python Navicat/setup_database.py` 无报错
- [ ] API 测试全部通过
