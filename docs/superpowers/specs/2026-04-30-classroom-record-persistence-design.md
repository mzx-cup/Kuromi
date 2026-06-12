# 星识项目课堂记录持久化设计方案

## 1. 概述

**目标**：在星识项目中实现学生课堂生成记录的数据库持久化存储，并提供完整的CRUD API支持。

**现状**：
- 课程保存API（`/api/v2/course/save`）仅将数据存为JSON文件到 `storage/courses/`
- 数据库中没有课堂记录表

**方案**：复用现有 `user` 表，通过 `user_id` 关联学生与课堂记录。

---

## 2. 数据库设计

### 2.1 新建表：`classroom_records`

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 2.2 SQLite兼容

- `LONGTEXT` → `TEXT`
- 移除 `ENGINE=InnoDB` 等MySQL特有语法
- 外键在SQLite中通过建表后单独创建

---

## 3. API设计

### 3.1 保存课堂记录
- **POST** `/api/v2/classroom/save`
- **Body**: `CourseSaveRequest` (已有)
- **逻辑**：
  1. 从请求中获取 `student_id`（即 `user_id`）
  2. 生成或使用已有的 `course_id`
  3. 将完整课程数据序列化后存入 `full_data` 字段
  4. 保留原有的JSON文件存储作为备份

### 3.2 获取学生课堂列表
- **GET** `/api/v2/classroom/list/{user_id}`
- **返回**：该学生的所有课堂记录，按创建时间倒序
- **字段**：id, user_id, course_id, title, created_at, updated_at（不含full_data）

### 3.3 获取单个课堂详情
- **GET** `/api/v2/classroom/{course_id}`
- **返回**：完整课堂数据
- **逻辑**：优先从数据库读取，数据库无则回退到JSON文件

### 3.4 更新课堂标题
- **PUT** `/api/v2/classroom/{course_id}`
- **Body**: `{ "title": "新标题" }`
- **逻辑**：仅更新 title 和 updated_at 字段

### 3.5 删除课堂记录
- **DELETE** `/api/v2/classroom/{course_id}`
- **逻辑**：
  1. 删除数据库记录
  2. 删除对应的JSON文件（如果存在）

---

## 4. 实现文件

| 文件 | 改动 |
|------|------|
| `Navicat/setup_database.py` | 添加 `classroom_records` 建表SQL |
| `db.py` | 添加5个数据库函数 |
| `main.py` | 添加/修改5个API端点 |

---

## 5. 退化处理

- 数据库不可用时，继续使用现有的JSON文件存储
- API响应结构保持兼容：`{ "success": true, ... }`

---

## 6. 测试要点

1. 新用户创建课堂 → 数据库记录正确生成
2. 获取课堂列表 → 按时间倒序排列
3. 删除课堂 → 数据库和文件均删除
4. 数据库故障 → 静默回退到JSON文件存储
