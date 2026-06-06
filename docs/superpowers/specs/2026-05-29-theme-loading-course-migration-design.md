# 主题系统、加载动画、课程中心移植设计

从 Java "知域" 项目向 Python "星识" 项目移植三个独立模块。

---

## 模块一：主题系统（壁纸 + 液态玻璃统一主题）

### 入口

顶栏深色/浅色切换按钮改为"主题设置"按钮，点击弹出液态玻璃 Modal。（前端没有做好，点击没有Modal弹出）
┌─────────────────────────────────────────┐
  │  主题设置                          [X]  │
  ├─────────────────────────────────────────┤
  │  外观模式    [浅色 / 深色] 切换        │
  │                                         │
  │  壁纸                                     │
  │  ┌──默认──┐ ┌─书房夜晚─┐ ┌─安逸舒适─┐  │
  │  │        │ │         │ │         │  │
  │  └────────┘ └─────────┘ └─────────┘  │
  │  ┌海洋女孩─┐ ┌航天女孩▷┐ ┌尼尔纪元▷┐  │
  │  │        │ │         │ │         │  │
  │  └────────┘ └─────────┘ └─────────┘  │
  │                                         │
  │  壁纸亮度    ───●───────  85%           │
  │  壁纸模糊    ──●────────   5px          │
  │                                         │
  │  [恢复默认]              [取消] [确认]  │
  └─────────────────────────────────────────┘

### Modal 内容

- 外观模式：浅色/深色切换（保留现有功能）
- 壁纸选择：5 张壁纸缩略图网格
  - 默认星图（无壁纸、无液态玻璃）
  - 书房夜晚（静态）
  - 安逸舒适（静态）
  - 海洋女孩（静态）
  - 向往航天的女孩（动态 webm）
  - 尼尔：机械纪元 团队（动态 webm）
- 壁纸亮度滑块（40%-150%）
- 壁纸模糊滑块（0-20px）
- 恢复默认 / 取消 / 确认按钮

### 行为

- 选择任一壁纸（非"默认星图"）→ 自动启用全局液态玻璃：`<body data-glass="true">`
- 选择"默认星图" → 无壁纸背景，无液态玻璃：`<body data-glass="false">`
- 动态壁纸通过 `<video autoplay loop muted>` 渲染在背景层
- CSS 变量：`--bg-image`、`--bg-brightness`、`--bg-blur`、`--bg-type`（static/dynamic）
- 液态玻璃变量：`--glass-opacity`、`--glass-blur` 在 `data-glass="true"` 时生效
- 设置持久化 localStorage + 服务端同步

### 资源

从 Java 项目复制壁纸到 `static/wallpaper/`：
- `static/书房夜晚/image.png` + `image-pre.webp`
- `static/安逸舒适/image.png` + `image-pre.webp`
- `static/海洋女孩/image.png` + `image-pre.webp`
- `dynamic/向往航天的女孩/Toy-Aeroplane.webm` + `Toy-Aeroplane-pre.webm`
- `dynamic/尼尔：机械纪元 团队/video.webm` + `video-pre.webm`

### 涉及文件

| 文件 | 操作 |
|------|------|
| `js/theme.js` | 重写：新增壁纸状态管理、液态玻璃自动切换、CSS 变量应用 |
| `html/hub.html` | 修改：顶栏按钮改为主题设置入口，新增 Modal 结构 |
| `css/hub.css` | 修改：Modal 液态玻璃样式、壁纸网格样式、滑块样式 |
| `css/index.css` | 修改：全局液态玻璃变量、`[data-glass]` 选择器规则 |
| `static/wallpaper/` | 新增：复制 Java 项目壁纸资源 |

---

## 模块二：全局加载动画（三层架构）

### 第一层：状态控制

```javascript
let isLoading = true;  // 初始显示加载画面

// 预加载：头像 + 页面卡片图片 + 背景壁纸/视频
// 2.5s 超时兜底
// 全部加载完成后 500ms 延迟 → isLoading = false
```

预加载策略：
- 收集页面所有 `<img>` 的 src
- 添加头像图片（若已登录）
- 添加当前壁纸（若已设置）
- `Promise.all` 并行加载，`Promise.race` 2.5s 超时
- `isLoading = false` 前等待 500ms 视觉稳定

### 第二层：3D 旋转 Spinner

```html
<div class="spinner"></div>
```

单个 `<div>` + 两个伪元素实现双层交叉旋转：

| 属性 | `::before` | `::after` |
|------|-----------|----------|
| 背景图 | `loader.svg` | `loader.svg` |
| 旋转轴角度 | `rotateX(60deg)` | `rotateX(240deg)` |
| 旋转方向 | 正向 | 反向 |
| 动画周期 | 750ms 无限 | 750ms 无限 |

```css
.spinner {
  width: 80px; height: 80px;
  position: relative;
  transform-style: preserve-3d;
  perspective: 340px;
}
.spinner::before,
.spinner::after {
  content: '';
  position: absolute; inset: 0;
  background: url('/static/loader.svg') center/contain no-repeat;
  animation: spin-layer 750ms linear infinite;
}
.spinner::after { animation-direction: reverse; }
@keyframes spin-layer {
  to { transform: rotateZ(360deg); }
}
```

### loader.svg 图形

- 中心：旋转地球（CSS 通过 SVG 自转动画实现）
- 45°倾斜椭圆轨道环（半透明蓝色）
- 黄色四角星 `#fbbf24`（4 个三角形拼成）
- 尾迹：星星后方 4-5 个渐隐小星点，沿轨道方向依次缩小+透明
- 加载完成：星星缩小并向中心位移跳入地球，地球短暂白色闪光

### 第三层：淡出过渡

```css
.loading-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: #282c34;
  transition: opacity 0.8s ease;
}
.loading-overlay.fade-out {
  opacity: 0;
  pointer-events: none;
}
```

### 涉及文件

| 文件 | 操作 |
|------|------|
| `css/loading.css` | 新增：Spinner 3D 样式、Overlay 淡出、动画关键帧 |
| `js/loading.js` | 新增：预加载逻辑、状态控制、超时兜底 |
| `static/loader.svg` | 新增：地球+轨道+四角星+尾迹矢量图 |

---

## 模块三：课程中心（可汗学院风格重建）

### 3a. 学科/课程列表页（重写 courses.html）

#### 布局
 ┌──────────────────────────────────────────┐
  │  [返回中枢]    课程中心    [编辑课程 🔧]  │
  ├──────────────────────────────────────────┤
  │                                          │
  │  ▎计算机科学                             │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
  │  │ 计算机   │ │ 数据     │ │ 操作     │ │
  │  │ 基础入门 │ │ 结构入门 │ │ 系统入门 │ │
  │  │ 32课时→ │ │ 48课时→ │ │ 28课时→ │ │
  │  └──────────┘ └──────────┘ └──────────┘ │
  │                                          │
  │  ▎数学                                   │
  │  ┌──────────┐ ┌──────────┐              │
  │  │ 线性代数 │ │ 概率统计 │              │
  │  │ 入门     │ │ 入门     │              │
  │  └──────────┘ └──────────┘              │
  │                                          │
  │  ▎物理学                                 │
  │  ...                                     │
  └──────────────────────────────────────────┘
- 顶部导航：返回中枢链接 + 标题"课程中心" + 编辑课程按钮
- 内容区：按科目分组，每个科目区块包含标题 + 课程卡片横排网格
- 课程卡片：封面色块 + 课程名称 + 课时数 + 进度环/操作按钮

#### 编辑课程面板（液态玻璃 Modal）
 ┌─────────────────────────────────────────┐
  │  编辑课程                          [X]  │
  ├─────────────────────────────────────────┤
  │  ☑ 计算机科学    [显示/隐藏]  [B站导入]│
  │    ☑ 计算机基础入门          [移除]    │
  │    ☐ 数据结构入门            [移除]    │
  │    ☑ 操作系统入门            [移除]    │
  │                                         │
  │  ☑ 数学            [显示/隐藏]  [B站导入]│
  │    ☑ 线性代数入门            [移除]    │
  │    ...                                  │
  │                                         │
  │  [+ 添加科目]                  [完成]    │
  └─────────────────────────────────────────┘
- 每个科目行：显示/隐藏开关 + B站导入按钮
- 展开科目显示课程列表：每个课程有显示/隐藏开关 + 移除按钮
- "+ 添加科目" 按钮（输入科目名称创建空科目）
- "完成" 按钮关闭面板

#### B站导入 Modal（液态玻璃面板）

三个 Tab：
- **粘贴链接**：textarea 粘贴 B站 URL → 解析 → 预览卡片 → 导入
- **搜索视频**：关键词搜索 → 多选结果 → 导入
- **合集导入**：粘贴合集 URL → 解析视频列表 → 指定课程名 → 导入

### 3b. 课程学习页（新建 course-learn.html）

#### 双栏布局
┌──────────────────────────────────────────────┐
  │  [返回]  计算机基础入门 / 二进制与数据表示   │
  ├──────────────┬───────────────────────────────┤
  │  目录        │  视频                         │
  │              │  ┌─────────────────────────┐  │
  │  第1章       │  │ B站 iframe 嵌入         │  │
  │    1.1  [✓] │  │ sandbox 禁止跳转        │  │
  │    1.2  [●] │  └─────────────────────────┘  │
  │    1.3       │                               │
  │  第2章       │  [讲义] [字幕] [文字转述]     │
  │    2.1       │  ──────────────────────── │
  │    2.2       │                              │
  │              │  点击字幕时间戳 → 视频跳转    │
  │              │  当前播放位置 → 字幕高亮      │
  │              │                              │
  │              │  [上一个]          [下一个]   │
  └──────────────┴──────────────────────────────┘
- **左侧**（约 280px）：章节目录树，章节可折叠，已完成打勾，当前高亮
- **右侧**：
  - 视频区：B站 iframe 嵌入，`sandbox="allow-scripts allow-same-origin"` 禁止点击跳转
  - 内容 Tab：[讲义] [字幕] [文字转述]
  - 字幕区：时间轴文本，点击时间戳 → 视频 seek，播放位置 → 字幕高亮
  - 底部：上一个/下一个课时导航按钮

#### 视频播放器

- 使用 Java 项目的 `bilibiliEmbedUrl()` 方法：`//player.bilibili.com/player.html?bvid=BVxxx&page=N&high_quality=1`
- iframe 添加 `sandbox="allow-scripts allow-same-origin"` 禁止跳转B站链接
- 字幕 API：`api.bilibili.com/x/player/v2?bvid=BVxxx` → 获取 cid → 下载字幕 JSON → 时间轴展示

### 初始数据

B站合集 `BV1YA411871j`（"真小白福利，完全从零带你掌握计算机与程序员基础知识"）作为"计算机科学"科目下"计算机基础入门"课程的初始内容。

### 后端新增

| 文件 | 用途 |
|------|------|
| `app/api/bilibili.py` | FastAPI 路由：`POST /api/bilibili/parse`、`/search`、`/playlist`、`/import`、`/subtitles` |
| `app/services/bilibili.py` | B站 API 封装（httpx）：视频元数据解析、搜索、合集解析、字幕获取 |
| `app/services/course_import.py` | 课程导入编排：B站视频 → AI 分类/章节生成 → 数据入库 |

数据模型调整：`app/models/course.py` 支持学科(Subject) → 课程(Course) → 章节(Chapter) → 子章节(SubChapter) → 知识点(KnowledgePoint) 五级结构。

### 涉及前端文件

| 文件 | 操作 |
|------|------|
| `html/courses.html` | 重写：学科分组布局 + 编辑课程 Modal + B站导入 Modal |
| `js/courses.js` | 重写：课程数据加载、学科/课程显示切换、Modal 交互 |
| `css/courses.css` | 重写：可汗学院风格布局、液态玻璃 Modal 样式 |
| `html/course-learn.html` | 新建：双栏课程学习页 |
| `js/course-learn.js` | 新建：章节导航、B站播放器控制、字幕同步、Tab 切换 |
| `css/course-learn.css` | 新建：双栏布局、视频播放器容器、字幕时间轴样式 |
| `js/bilibili-import.js` | 新建：B站导入三 Tab 交互逻辑 |
| `css/bilibili-import.css` | 新建：B站导入 Modal 样式 |

---

## 模块间关系

```
模块一 (主题系统)    独立
模块二 (加载动画)    独立，可与模块一并行
模块三 (课程中心)    依赖模块一（液态玻璃 Modal），依赖后端 B站 API
```

## 不使用的图标

所有新增代码不使用 emoji 图标（不使用类似 🐍 ☕ 🧮 🌐 🤖 📊 🗄️ ⚡ 等字符），改用 SVG 图标。
