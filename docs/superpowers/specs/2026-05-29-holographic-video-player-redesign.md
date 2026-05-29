# 全息视界播放器重设计

日期: 2026-05-29 | 状态: 已确认

## 概述

重写全息视界页面播放器，支持 B站嵌入 + 本地视频双模式，统一控制栏体验。后端新增视频课程库和播放列表 API。

## 架构

```
                    ┌─────────────────┐
                    │   控制栏 UI      │
                    │ 播放/暂停 进度条  │
                    │ 倍速 音量 全屏   │
                    └───────┬─────────┘
                            │
              ┌─────────────┴─────────────┐
              │    videoController        │
              │    (source_type 路由)      │
              └─────────────┬─────────────┘
                            │
         ┌──────────────────┼──────────────────┐
    source=bilibili    source=local       空状态
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│ BilibiliDriver  │  │ LocalDriver     │
│ postMessage API │  │ <video> DOM API │
└─────────────────┘  └─────────────────┘
```

### 设计原则

- 控制栏 UI 统一，底层驱动按 source_type 切换
- B站 iframe 保留 sandbox（allow-scripts allow-same-origin allow-presentation），不放开 allow-top-navigation
- 页面不出现 "B站视频学习驾驶舱" / "B站 已接入" 品牌标语，仅在空状态和添加表单中保留操作指引

## 数据模型

新增三张表，按现有项目多后端模式（MySQL/SQLite/JSON fallback）实现。

### video_courses — 统一视频课程库

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO | 自增主键 |
| title | VARCHAR(256) | 课程标题 |
| subtitle | VARCHAR(512) | 副标题 |
| source_type | VARCHAR(16) | `bilibili` 或 `local` |
| bvid | VARCHAR(32) | B站 BV 号 |
| page | INT DEFAULT 1 | B站分P |
| local_path | VARCHAR(512) | 本地文件路径 |
| duration_label | VARCHAR(16) | 时长展示 |
| ai_summary | TEXT | AI 摘要 |
| ai_timeline | JSON | 时间戳笔记 [{time, title, desc}] |
| ai_questions | JSON | 重点问题 [string] |
| ai_suggestion | TEXT | 学习建议 |
| created_by | VARCHAR(64) | 创建者 user_id |
| created_at | DATETIME | 创建时间 |

### video_playlists — 用户播放列表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO | 自增主键 |
| user_id | VARCHAR(64) | 所属用户 |
| name | VARCHAR(128) | 列表名称 |
| position | INT DEFAULT 0 | 排序 |
| created_at | DATETIME | 创建时间 |

### playlist_videos — 列表内视频

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO | 自增主键 |
| playlist_id | INT FK | 关联播放列表 |
| course_id | INT FK | 关联 video_courses |
| position | INT DEFAULT 0 | 播放顺序 |
| added_at | DATETIME | 添加时间 |

## 后端 API

### 课程库

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/video-courses` | 获取全部课程，支持 `?source_type=` 过滤 |
| GET | `/api/video-courses/{id}` | 单个课程详情 |
| POST | `/api/video-courses` | 添加课程 |
| PUT | `/api/video-courses/{id}` | 编辑课程 |
| DELETE | `/api/video-courses/{id}` | 删除课程 |

### 播放列表

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/video-playlists?user_id=` | 获取用户播放列表（含视频条目） |
| POST | `/api/video-playlists` | 创建播放列表 |
| PUT | `/api/video-playlists/{id}` | 重命名 |
| DELETE | `/api/video-playlists/{id}` | 删除列表 |
| POST | `/api/playlist-videos` | 添加视频到列表 |
| DELETE | `/api/playlist-videos/{id}` | 从列表移除 |
| PUT | `/api/playlist-videos/reorder` | 拖拽排序 |

### 已有路由（沿用）

| 路由 | 说明 |
|------|------|
| `/video/{filename}` | 本地视频文件服务 |
| `/api/local-videos` | 扫描 video/ 目录 |

### 新增辅助路由

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/bilibili/info?bvid=` | 服务端代理获取 B站视频标题/封面/时长 |

## 前端页面（基于现有布局微调）

### 布局结构

沿用现有 `.bili-theater` 两栏布局：左侧播放器列 + 右侧侧边面板。

### 调整点

**1. iframe 裁剪 B站控件**
- iframe 高度设为 `calc(100% + 50px)`，容器 `overflow: hidden`，B站内置控件被裁掉
- 统一控制栏覆盖在容器底部（现有 `.player-controls` 位置）

**2. 侧栏 Tab 扩展为 3 个**
- Tab 1 "课程库" — 全部可用课程，搜索过滤，来源标签（本地/B站），点击添加到播放列表
- Tab 2 "我的列表" — 播放列表中的视频，拖拽排序/删除，点击播放，当前播放项高亮
- Tab 3 "AI伴学笔记" — 摘要、可点击时间戳笔记、重点问题、学习建议、我的笔记

**3. 控制栏统一化**
- 恢复倍速按钮和音量按钮
- B站模式通过 postMessage 发送 seek/play/pause/setPlaybackRate，本地模式操作 `<video>` DOM
- 全屏按钮操作整个 `.video-player` 容器

**4. 导航栏精简**
- 去掉副标题文字，状态指示精简为 `● 就绪`
- 标题保持 "全息视界"

**5. 视频信息面板**
- 在现有信息面板中增加来源标识（B站/本地 + BV号或文件名）

### 播放器双驱动逻辑

```
事件 → videoController
         ├─ source=bilibili → BilibiliDriver (iframe.contentWindow.postMessage)
         │   - 播放/暂停/跳转/倍速 通过 postMessage 发送
         │   - 进度通过 500ms 轮询 getCurrentTime
         │   - 时间戳笔记点击 → postMessage seek
         └─ source=local → LocalDriver (<video> DOM API)
             - 直接操作 video.play()/pause()/currentTime/playbackRate
             - 进度通过 timeupdate 事件获取
             - 时间戳笔记点击 → video.currentTime = time
```

### 错误处理

| 场景 | 处理 |
|------|------|
| B站视频加载失败 | 空状态 "B站视频加载失败，请检查 BV 号或网络" |
| 本地视频文件缺失 | 空状态 "请在 video/ 目录放入视频文件" |
| 添加重复课程 | 后端去重检查 |
| 网络中断 | 课程库/播放列表使用本地缓存兜底 |

### 空状态文案

- 播放列表为空: "添加你的第一个学习视频"
- 操作指引: "支持 bilibili.com 的 BV 号或 av 号，也可指定本地 video/ 目录中的视频文件"

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `html/video-player.html` | 改 | iframe 裁剪、三 tab、控制栏恢复、去品牌化 |
| `js/video-player.js` | 重写 | videoController + BilibiliDriver + LocalDriver 双驱动 |
| `css/video-player.css` | 改 | iframe 溢出裁剪、三 tab 适配 |
| `main.py` | 改 | 新增 API 路由 |
| `db.py` | 改 | 新增三张表的数据访问函数 |
| `tests/test_video_player_links.py` | 改 | 适配新布局 |

## 不在范围内

- AI 自动生成笔记（当前为静态数据，后续接入 LLM）
- 弹幕服务端持久化（仍用 localStorage）
- 视频上传功能
- 用户间课程分享
