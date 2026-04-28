# 学习概览卡片排版重设计计划

## Context

用户反馈当前"学习概览"（Learning Dashboard）的卡片排版存在以下问题：
1. **排版不人性化** - 现有的左右分栏布局不够直观
2. **廉价卡片感** - `glass-card` 样式过于普通，缺乏设计感
3. **图表单调** - 现有的环形图和柱状图比较基础

设计目标：
- 采用更人性化的信息层级设计
- 重新设计卡片样式，提升质感
- 重绘学习数据可视化图表
- **不影响其他功能模块**

---

## 设计理念

### 信息层级重构

采用 **"一眼可见 → 重点关注 → 细节可探"** 的信息架构：

```
┌──────────────────────────────────────────────────────────────┐
│  学习概览 · 今天                                              │
│  2026年4月27日 星期一                                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  今日学习状态卡 (Hero Card)                           │     │
│  │  ┌─────┐  主标题  副标题                             │     │
│  │  │图标 │  数据指标  趋势箭头                         │     │
│  │  └─────┘                                          │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │
│  │ 专注时长卡片  │  │ 完成任务卡片  │  │ 连续天数卡片  │    │
│  └───────────────┘  └───────────────┘  └───────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  学习趋势图 (流光风格)                               │     │
│  │  ～～～～～～～～～～～～～～～～～～～              │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────┐  ┌────────────────────────┐     │
│  │ 本周学习热力图          │  │ 专注任务列表           │     │
│  │ ░░▒▒▓▓██░░▒▒         │  │ · 任务1 ✓            │     │
│  │                      │  │ · 任务2 ●             │     │
│  └────────────────────────┘  └────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 设计风格

### 配色方案 (沿用现有变量)

```css
--neon-purple: #a855f7;
--neon-blue: #3b82f6;
--neon-green: #10b981;
--neon-orange: #f97316;
--neon-pink: #ec4899;
--neon-cyan: #06b6d4;
```

### 新卡片样式

**1. Hero 状态卡**
- 大尺寸渐变背景 + 微光动画
- 左侧图标 + 右侧数据
- 顶部有装饰性光效条

**2. 指标卡 (Stat Cards)**
- 玻璃拟态 + 细边框
- 顶部彩色光效条
- 悬浮时有上浮 + 光晕效果

**3. 图表卡**
- 标题区 + 图表区分离
- 图表区有渐变填充
- 支持深色/浅色主题

### 新图表设计

**学习趋势图 (替代原有 SVG)**
- 流光曲线 + 渐变填充
- 网格背景
- 悬停显示具体数值

**本周学习热力图 (新增)**
- 7x24 网格显示每日学习时段
- 颜色深浅表示学习强度

---

## 实现方案

### Phase 1: HTML 结构改造

**文件**: `html/hub.html`

修改 `dashboard-section` 结构：

```html
<section class="dashboard-section" id="section-dashboard">
    <!-- 概览头部 -->
    <div class="overview-header">
        <div class="overview-title-row">
            <span class="overview-icon">📊</span>
            <h2 class="overview-title">学习概览</h2>
        </div>
        <div class="overview-meta">
            <span class="overview-date" id="overview-date"></span>
        </div>
    </div>

    <!-- Hero 状态卡 -->
    <div class="hero-status-card" id="hero-status-card">
        <div class="hero-glow"></div>
        <div class="hero-content">
            <div class="hero-icon-wrapper">
                <span class="hero-icon">🚀</span>
            </div>
            <div class="hero-info">
                <h3 class="hero-title">今日学习进行中</h3>
                <p class="hero-subtitle">已专注 45 分钟，继续保持！</p>
            </div>
            <div class="hero-stats">
                <div class="hero-stat">
                    <span class="hero-stat-value">5.2</span>
                    <span class="hero-stat-label">小时</span>
                </div>
                <div class="hero-stat-trend up">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"/>
                    </svg>
                    <span>+12%</span>
                </div>
            </div>
        </div>
    </div>

    <!-- 指标卡片网格 -->
    <div class="stat-cards-grid">
        <div class="stat-card">
            <div class="stat-card-accent purple"></div>
            <div class="stat-card-icon">
                <svg>...</svg>
            </div>
            <div class="stat-card-content">
                <span class="stat-card-value">207</span>
                <span class="stat-card-unit">小时</span>
            </div>
            <span class="stat-card-label">累计学习</span>
        </div>
        <!-- 类似结构... -->
    </div>

    <!-- 趋势 + 热力图 -->
    <div class="dashboard-charts-row">
        <div class="chart-card trend-chart-card">
            <div class="chart-header">
                <h4>学习趋势</h4>
                <span class="chart-badge">近7天</span>
            </div>
            <div class="trend-chart-wrapper">
                <canvas id="trendChart"></canvas>
            </div>
        </div>
        <div class="chart-card heatmap-card">
            <div class="chart-header">
                <h4>学习时段</h4>
                <span class="chart-badge">本周</span>
            </div>
            <div class="heatmap-wrapper" id="heatmap-wrapper"></div>
        </div>
    </div>

    <!-- 任务 + 日历 -->
    <div class="dashboard-bottom-row">
        <div class="task-list-card">
            <!-- 任务列表 -->
        </div>
        <div class="mini-calendar-card">
            <!-- 专注日历 -->
        </div>
        <div class="tags-card">
            <!-- 学习标签 -->
        </div>
    </div>
</section>
```

### Phase 2: CSS 样式重写

**文件**: `css/hub.css`

重写以下样式：

1. `.dashboard-section` → `.overview-section` (避免冲突)
2. 新增 Hero Card 样式
3. 新增 Stat Cards 样式
4. 新增 Chart Card 样式
5. 新增 Heatmap 样式
6. 新增 Animations

### Phase 3: JavaScript 图表

**文件**: `js/hub.js`

1. 趋势图：使用 Canvas 绑定真实数据
2. 热力图：动态生成 7x24 网格
3. 数据从 `data-layer.js` 获取

---

## Critical Files

| 文件 | 修改内容 |
|------|----------|
| `html/hub.html` | 重写 `dashboard-section` HTML 结构 |
| `css/hub.css` | 新增/重写 dashboard 相关样式 |
| `js/hub.js` | 图表初始化和数据绑定 |

---

## 不影响范围

以下模块**保持不变**：
- `daily-highlights-section` (今日要闻) ✅
- `daily-route-section` (今日航线) ✅
- `module-section` (心流共振、星际自习等) ✅
- `holo-tree` (全息知识树) ✅

---

## Verification

1. **视觉检查**: 打开 hub 页面，确认学习概览区域已更新
2. **功能检查**: 确认其他模块（今日要闻、航线、知识树等）功能正常
3. **主题检查**: 深色/浅色主题切换正常
4. **响应式检查**: 不同分辨率下布局正常
