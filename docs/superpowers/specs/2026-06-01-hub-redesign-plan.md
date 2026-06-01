# Hub 页面重设计 — 实现计划

**日期**: 2026-06-01
**依赖**: [设计文档](./2026-06-01-hub-redesign-design.md)

---

## 实施顺序

分 5 个阶段，每个阶段可独立验证。

### 阶段 1：清理与准备
**目标**: 修复已知 bug，删除死代码，建立干净的起点

1. **hub.html 添加 tokens.css 引用** — 在 `<head>` 中 `<link>` 加载 tokens.css（这是主题失效的根本原因）
2. **删除不存在的 CSS 引用** — 移除 `hub-perfect.css` 和 `hub-winmoes.css` 的 `<link>` 标签
3. **备份现有文件** — `git mv css/hub-refined.css css/hub-refined.css.bak`（暂留作参考）

**验证**: 打开 hub.html，确认 tokens.css 已加载（DevTools > Elements > Computed 能看到 `--brand-500` 等变量）

### 阶段 2：重写 HTML 骨架
**目标**: 新布局结构，保留所有模块 DOM

1. **重写 `html/hub.html`**：
   - `<head>`: 仅加载 tailwind CDN → tokens.css → loading.css → hub.css → components.css
   - `<body class="hub-body">`:
     ```
     <!-- 背景层 -->
     <div id="global-bg-layer"><video id="global-bg-video"></video></div>
     <div id="hub-bg"></div>

     <!-- 顶部导航 -->
     <nav class="hub-navbar">
       logo · 搜索框 · 心流分数 · 主题按钮 · 通知 · 头像
     </nav>

     <!-- 通知面板 -->
     <div id="notification-panel">...</div>

     <!-- 左侧图标栏 48px -->
     <aside class="hub-sidebar">
       <icon-nav data-tab="overview">首页</icon-nav>
       <icon-nav data-tab="learn">学习</icon-nav>
       <icon-nav data-tab="tools">工具</icon-nav>
       <icon-nav data-tab="data">数据</icon-nav>
       <icon-nav>设置</icon-nav>
     </aside>

     <!-- 主内容区 -->
     <main class="hub-main">
       <!-- 标签导航 -->
       <nav class="tab-bar">
         <button class="tab-btn active" data-tab="overview">总览</button>
         <button class="tab-btn" data-tab="learn">学习</button>
         <button class="tab-btn" data-tab="tools">工具</button>
         <button class="tab-btn" data-tab="data">数据</button>
       </nav>

       <!-- 总览标签 -->
       <section class="tab-panel active" id="tab-overview">
         <!-- 欢迎卡片 -->
         <section id="hero-welcome">问候语 + 日期 + 心流环</section>
         <!-- 快捷操作 -->
         <div id="quick-actions">4 个按钮</div>
         <!-- 功能卡片 2x3 网格 -->
         <div id="feature-grid">6 张卡片</div>
         <!-- 每日路线 + 心流条 -->
         <div id="daily-route-section">...</div>
       </section>

       <!-- 学习标签 -->
       <section class="tab-panel" id="tab-learn">
         <div id="knowledge-eco">知识生态系统</div>
         <div id="flow-resonance">心流共振</div>
         <div id="focus-timer">专注计时器</div>
         <div id="course-progress">课程进度</div>
       </section>

       <!-- 工具标签 -->
       <section class="tab-panel" id="tab-tools">
         <div id="study-hall">自习室</div>
         <div id="kanban">看板</div>
         <div id="task-manager">任务</div>
         <div id="quick-notes">笔记</div>
       </section>

       <!-- 数据标签 -->
       <section class="tab-panel" id="tab-data">
         <canvas id="trendChart">趋势图</canvas>
         <div id="heatmap">热力图</div>
         <div id="stats-overview">统计</div>
         <div id="weekly-report">周报</div>
       </section>
     </main>

     <!-- 右侧面板 200px -->
     <aside class="hub-right-panel">
       <div id="mini-calendar">日历</div>
       <div id="task-list">待办</div>
       <div id="tags-cloud">标签</div>
       <div id="news-feed">新闻</div>
     </aside>

     <!-- 弹窗层 -->
     <div id="news-modal">...</div>
     <div id="review-modal">...</div>
     <div id="kanban-mascot">...</div>
     ```

   - **关键原则**：每个现有模块的 DOM 结构保留（ID、data 属性不变），只改外层容器布局

**验证**: 页面加载无 404，所有模块 DOM 节点存在于 DevTools Elements 面板

### 阶段 3：重写 CSS
**目标**: 单一 hub.css（<2500 行），0 硬编码颜色

1. **CSS 架构（自上而下）**:
   ```
   hub.css (~2500 lines)
   ├── 1. CSS 变量映射（~50 行）
   │   └── 将 tokens.css 变量映射为组件便捷变量
   ├── 2. 布局系统（~200 行）
   │   ├── .hub-body (全屏 flex 容器)
   │   ├── .hub-sidebar (48px 图标栏)
   │   ├── .hub-main (弹性主区)
   │   ├── .hub-right-panel (200px 右侧)
   │   └── .tab-bar + .tab-panel
   ├── 3. 组件样式（~1500 行）
   │   ├── Navbar (~200 行)
   │   ├── Cards — 混合风格 (~200 行)
   │   ├── Feature Grid (~100 行)
   │   ├── Quick Actions (~80 行)
   │   ├── Hero Welcome (~120 行)
   │   ├── Daily Route (~150 行)
   │   ├── Knowledge Ecosystem (~250 行)
   │   ├── Flow Resonance (~120 行)
   │   ├── Focus Timer (~80 行)
   │   ├── Study Hall (~100 行)
   │   ├── Kanban (~80 行)
   │   ├── Task List (~80 行)
   │   ├── Calendar (~60 行)
   │   ├── Tags Cloud (~40 行)
   │   ├── Trend Chart (~50 行)
   │   ├── Heatmap (~80 行)
   │   ├── News Feed (~80 行)
   │   └── Notifications (~80 行)
   ├── 4. 弹窗层 (~150 行)
   │   ├── News Modal
   │   ├── Review Modal
   │   └── Theme Modal (从 components.css 复用)
   └── 5. 响应式 (~300 行)
       ├── ≥1400px — 完整三栏
       ├── ≥1024px — 右侧折叠
       ├── ≥768px — 左侧折叠
       └── <768px — 单栏
   ```

2. **卡片混合风格实现**:
   ```css
   .hub-card {
     background: var(--surface-glass);
     border: 1px solid var(--border-glass);
     border-radius: var(--radius-md);
     box-shadow: var(--shadow-sm);
     padding: var(--space-lg);
     transition: var(--transition-base);
   }
   .hub-card:hover {
     background: var(--surface-glass-hover);
     border-color: var(--border-glass-hover);
     box-shadow: var(--shadow-md);
     transform: translateY(-2px);
   }
   ```

3. **从 hub-refined.css 迁移必要的颜色覆盖到 hub.css**（约 20% 的内容）

**验证**: 视觉检查 — 所有卡片统一风格，切换 6 个主题颜色生效，4 个断点布局正确

### 阶段 4：重写 JavaScript
**目标**: 模块化 hub.js，类结构清晰，保持所有功能

1. **新建文件** `js/hub.js`，模块化结构:
   ```javascript
   // hub.js — 入口文件（~250 行）
   class HubApp {
     constructor() {
       this.tabs = new TabManager();
       this.cards = new CardRenderer();
       this.charts = new ChartRenderer();
       this.flow = new FlowTracker();
       this.kanban = new KanbanManager();
       this.studyHall = new StudyHall();
       this.knowledge = new KnowledgeEco();
       this.toast = new Toast();
       this.news = new NewsManager();
       this.theme = new ThemeManager();
     }
     async init() {
       // 按依赖顺序初始化
       await this.theme.init();
       this.tabs.init();
       this.flow.init();
       // ... 其他模块并行初始化
     }
   }
   document.addEventListener('DOMContentLoaded', () => {
     window.hubApp = new HubApp();
     window.hubApp.init();
   });
   ```

2. **模块功能迁移**（从现有 hub.js 复制逻辑，改写为类）:
   - `TabManager` — 标签切换，URL hash 同步（`#overview`/`#learn`/`#tools`/`#data`）
   - `CardRenderer` — 动态卡片生成
   - `ChartRenderer` — Canvas 趋势图 + 热力图
   - `FlowTracker` — 心流分数 + 专注计时（保留 localStorage `page_visits`）
   - `KanbanManager` — 看板拖拽（保留 kanban.js 交互逻辑）
   - `StudyHall` — 自习室配对
   - `KnowledgeEco` — SM2 算法 + 全息树（保留 `calculateSM2()`）
   - `Toast` — 通知系统
   - `NewsManager` — 新闻加载 + 缓存
   - `ThemeManager` — 主题切换（委托给 StarTheme 或直接操作 data-theme）
   - `NotificationManager` — 通知面板 + 红点
   - `DataSync` — 跨标签同步
   - `DailyRoute` — 每日路线生成

3. **保留所有 localStorage key**:
   - `starlearn_user`, `starlearn_study`, `starlearn_learning_update`, `starlearn_focus_update`
   - `starlearn_daily_news`, `starlearn_notifications`, `starlearn_notifications_last_update`
   - `hub-theme`, `page_visits`

4. **保留所有 API 端点调用**:
   - `/api/daily-route/status`, `/generate`, `/complete`
   - `/api/stats/overview/`, `/trend/`, `/heatmap/`
   - `/api/knowledge/nodes/`, `/review`, `/pending/`
   - `/api/news/today`, `/more`
   - `/api/goals/`, `/api/cockpit/learning-time`

**验证**: 所有功能可交互 — 标签切换、图表渲染、路线生成、知识树、日历、任务、新闻加载均正常

### 阶段 5：集成验证与清理
**目标**: 端到端验证，删除旧文件

1. **删除 `css/hub-refined.css`**（内容已迁移到 hub.css）
2. **端到端测试**:
   - 6 个主题逐一切换，确认所有区域变色
   - 4 个标签页切换，确认内容加载
   - 4 个响应式断点，确认布局自适应
   - localStorage 数据兼容性检查
   - 心流分数计算正常
   - 每日路线生成正常
   - 知识生态系统正常
3. **提交**: 单次 commit 包含所有变更

---

## 风险控制

| 风险 | 缓解 |
|------|------|
| JS 模块化时遗漏功能 | 以现有 hub.js 的 init 函数列表为 checklist，逐项核对 |
| 主题颜色不如预期 | tokens.css 未修改，只改 hub.css 的变量引用方式 |
| 响应式断点遗漏 | 4 个断点各写测试用例 |
| localStorage 数据丢失 | 不改 key 名称，保持数据结构兼容 |
| API 调用格式不兼容 | 保持现有 fetch 参数格式不变 |

## 时间估计

- 阶段 1（清理）: 10 分钟
- 阶段 2（HTML）: 30 分钟
- 阶段 3（CSS）: 1 小时
- 阶段 4（JS）: 1.5 小时
- 阶段 5（验证）: 20 分钟
