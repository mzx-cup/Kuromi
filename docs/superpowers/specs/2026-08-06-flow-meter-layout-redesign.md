---
title: Flow-Meter Layout Redesign
status: draft
date: 2026-08-06
---

# Flow-Meter 页面布局重设计

## 1. 背景

`html/flow-meter.html` 是「心流共振仪」页面，向用户呈现当日专注度分析。当前布局存在三个问题：

1. **首屏不可读**：4 个 KPI 卡（深度率/累计专注/切屏/心流指数）等宽并排，每个 ~325px，但其中累计专注、深度率、心流指数是首屏最该看到的指标，被淹没在 4 项里。
2. **装饰大于数据**：Hero 横幅里 72px 的旋转状态球占据显著位置，但状态只有 3 个离散值（深度/轻度/分心），是装饰重于信息密度。
3. **冗余字段**：会话卡片里「学习内容」「目标时长」是静态占位文本（`Python 数据结构` / `60 分钟`），没接真实数据，却占据 50% 卡片面积。

后端 `/api/focus/analysis/{user_id}` 已稳定返回完整 payload（`score`, `deepRatio`, `today.*`, `timeOfDay.*`, `timeline`, `trend`, `tips`），数据足够支撑首屏 KPI 设计。

## 2. 目标

- **首屏一眼可见三个核心 KPI**：今日专注分钟、心流指数、深度专注率。
- **信息密度提升**：去掉冗余/装饰元素后，单屏可见数据量增加。
- **保留可读性与美感**：沿用现有的玻璃质感、ECharts 动效、token 色彩体系，不推倒重做。

## 3. 非目标

- 不改后端 API 协议、不改数据库 schema、不改 `FocusAnalysis` 模块。
- 不引入新依赖。
- 不重做 mascot、AI 助手等周边元素。
- 不重写 ECharts 图表逻辑（`flow-meter.js` 中的 `renderWaveformChart` / `renderTimeOfDayChart` / `renderHistoryChart` 保持不变）。

## 4. 布局结构

```
┌──────────────────────────────────────────────────────────┐
│  顶部条：返回 + 心流共振仪标题 + 实时监测标签 + 日期时间     │
├──────────────────────────────────────────────────────────┤
│  Row 1 · KPI 大数字带横向进度条（3 等宽卡）                  │
│  ┌──────────────┬──────────────┬──────────────┐           │
│  │ ⏱  45:30     │ ✦  78        │ ⚡  82%       │           │
│  │ 今日专注     │ 心流指数     │ 深度专注率   │           │
│  │ ▰▰▰▰▰▱▱▱ 60% │ ▰▰▰▰▰▰▱ 75% │ ▰▰▰▰▰▰▰ 82%  │           │
│  │ 目标 60 分钟  │ ↑ +12 vs 3d │ 本周均值 65% │           │
│  └──────────────┴──────────────┴──────────────┘           │
├──────────────────────────────────────────────────────────┤
│  Row 2 · 主图区                                              │
│  ┌────────────────────────────┬──────────────┐            │
│  │ 📈 实时心流波形（2/3 宽）   │ ⏰ 时段分布(1/3)│            │
│  │ [深度/轻度/走神状态切换曲线]  │ [4 时段柱状]    │           │
│  └────────────────────────────┴──────────────┘            │
├──────────────────────────────────────────────────────────┤
│  Row 3 · 会话（精简）+ 建议                                   │
│  ┌─────────────────────┬──────────────────┐               │
│  │ 📅 本次会话           │ 💡 专注建议         │               │
│  │ 开始  14:00:00        │ • 近期分心多       │               │
│  │ 剩余  14:30           │ • 深度率优秀       │               │
│  │ ▰▰▰▰▰▰▱ 75% 完成     │ • 最佳时段：下午   │               │
│  └─────────────────────┴──────────────────┘               │
├──────────────────────────────────────────────────────────┤
│  Row 4 · 历史趋势（全宽，filter 右上）                       │
└──────────────────────────────────────────────────────────┘
```

## 5. 组件细节

### 5.1 KPI 大数字卡（Row 1）

每个卡片：

- **顶部行**：图标徽章（48×48 圆角块，配色取自 `--ic`） + 右上角趋势徽章（`↑ +12` 用 success 色，`↓ -3` 用 danger 色，`—` 用 muted）
- **中段**：超大数字，用 `clamp(2.25rem, 4vw, 3.5rem)`，颜色 `--text-heading`，字重 700。数字下方紧跟一行 13px 中等字重的中文标签
- **进度条**：12px 高，圆角 pill，背景 `--border-glass`；填充色随主题（info/brand/success）。心流指数和深度率用满色填充，学习分钟用 vs 目标（默认 60 分钟）的比例
- **进度条下方**：13px 小辅助行（muted 色）

**三卡字段映射**：

| 卡片 | 图标 | 数据源 | 进度条填充率 | 辅助行 |
|---|---|---|---|---|
| 今日专注 | `clock-4` | `today.studyMinutes` | `studyMinutes / 60` | "目标 60 分钟" |
| 心流指数 | `activity` | `score` | `score / 100` | `trend.direction` + `trend.change` 文案 |
| 深度专注率 | `zap` | `deepRatio` | `deepRatio / 100` | "本周均值 X%" 取 `recentHistory` 中本周时间戳样本的 `score` 平均 |

"本周"定义为本周一 00:00 至今。`recentHistory` 是后端 `_compute_focus_analysis` 返回的最近 48 条历史样本（`main.py` L8330），按 `timestamp` 字段 ISO 字符串前缀 `YYYY-MM-DD` 过滤到本周范围取均值。如果本周样本为空，辅助行显示"—"。

### 5.2 实时心流波形（Row 2 左，2/3 宽）

保持现有 `renderWaveformChart` 实现不变。ECharts 容器最小高度 280px。状态图例 pill（深度/轻度/分心）放在卡片头部右侧。

### 5.3 时段专注分布（Row 2 右，1/3 宽）

保持现有 `renderTimeOfDayChart` 实现不变。ECharts 容器最小高度 280px。

### 5.4 本次会话卡（Row 3 左，精简）

字段精简为两个：

- 开始时间：取 `today.firstSessionTime`
- 剩余时间：取 `max(0, studyMinutes - focusMinutes)`，按 "时:分" 格式

下方一条进度条：宽度按 `focusRatio`（today.focusRatio）。保留 `fm-progress-fill` 的光带流动动画（`fm-bar-stripe` keyframes）。

去掉「学习内容」「目标时长」两个静态占位字段。

### 5.5 专注建议卡（Row 3 右）

保留现有 `tips-list` 渲染逻辑。最多显示 4 条（与后端 `_compute_focus_analysis` 已经限制为 4 条一致）。保留左侧强调条 + 图标 + 文本结构。

### 5.6 历史趋势卡（Row 4，全宽）

保持现有 `renderHistoryChart` 实现不变。filter pills（今日/本周/本月）保持在卡片头部右侧。

## 6. 数据流

HTML 标记（结构层）→ `flow-meter.js` 监听 `FocusAnalysis` 的 `analysis-updated` 事件 → 调用 `updateAllCards(data)` → `updateStatsPanel` / `updateSessionPanel` / `updateTips` / `updateCharts` 分别更新各区域。

新增的 KPI 卡：复用现有 `updateStatsPanel` 的绑定（`#focus-time` / `#flow-score` / `#deep-value`）即可，不需要新写 JS。但 KPI 卡的进度条和辅助行需要新增渲染函数 `updateKpiCards(data)`，从 `data.today.*`、`data.score`、`data.deepRatio`、`data.trend` 读取并写到 DOM。

具体新增 DOM 锚点：

- `#kpi-focus-fill` / `#kpi-focus-hint`（今日专注进度条 + 辅助文字）
- `#kpi-score-fill` / `#kpi-score-hint`（心流指数进度条 + trend 文案）
- `#kpi-deep-fill` / `#kpi-deep-hint`（深度率进度条 + 本周均值）

`focus-sync.js` / `focus-analysis.js` / `main.py` 后端接口全部保持不变。

## 7. 文件改动范围

| 文件 | 改动 |
|---|---|
| `html/flow-meter.html` | 改写 `<section class="fm-bento-stats">`（4 卡 → 3 卡，新结构）；删除 `.fm-hero` 文章块；改写 `<section class="fm-bento-info">` 的 `.fm-card-session` 部分（去掉两个占位字段）；保留 `<section class="fm-bento-charts">` 和 `<section class="fm-bento-history">` |
| `css/flow-meter.css` | 删除 `.fm-hero`、`@keyframes fm-pulse/orb-rotate/grad-flow/state-underline/chip-shine/grad-underline/draw` 中只服务于 hero 的部分；新增 `.fm-kpi-card` / `.fm-kpi-value` / `.fm-kpi-fill` / `.fm-kpi-hint` 等样式；调整 `.fm-bento-stats` 为 3 列；调整 `.fm-card-session` 为单列 2 字段布局；调整 `.fm-card-waveform` / `.fm-card-timeofday` 的 `min-height`；调整响应式断点 |
| `js/flow-meter.js` | 在 `updateStatsPanel` 内或新增 `updateKpiCards(data)` 函数中渲染进度条宽度和辅助文字；保留所有现有 ECharts 渲染函数 |
| `packaging/app_payload/html/flow-meter.html` | 字节级同步 |
| `packaging/app_payload/css/flow-meter.css` | 字节级同步 |
| `packaging/app_payload/js/flow-meter.js` | 字节级同步 |

后端代码（`main.py`、`app/models/focus.py`、`app/repositories/orm/focus.py`、`db.py`）不在此次改动范围内。

## 8. 风险与对策

- **CSS 注释里的 CJK 字符容易导致 Edit 失败**：之前在 `flow-meter.css` 调整 chart height 时遇到过 `/* Chart heights (覆盖默认 dd-chart) */` 的中英文标点差异。处理方法：每次 Edit 前先 Read 精确文本，避免凭记忆。
- **ECharts 容器尺寸**：Row 2 主图区从 50/50 改为 2/3 + 1/3 后，1/3 的时段分布柱状图在窄屏上可能挤压坐标轴标签。处理方法：设置 `grid.containLabel: true` 并把 `grid.left` 调到 32px。
- **响应式中段塌缩**：768-1199px 时 Row 2 改为单列堆叠。处理方法：在媒体查询里直接改 `grid-template-columns: 1fr`，避免 grid 单元过窄。
- **进度条从数据派生**：`studyMinutes / 60` 用 60 作为默认目标。如果未来要从设置读取目标时长，需要单独处理，但本次不做。

## 9. 验收

- 首屏（不滚动）能看到三个 KPI 大数字 + 实时波形 + 时段分布。
- KPI 进度条宽度 = 数据比例，趋势徽章正确反映 `trend.direction`。
- 会话卡只剩"开始时间"和"剩余时间"两个字段 + 进度条。
- `curling http://localhost:8000/api/focus/analysis/1?range=7d` 返回的数据能驱动新布局正常显示。
- 三个响应式断点下无横向滚动条、无元素溢出。
- 镜像 `packaging/app_payload/{html,css,js}/flow-meter.*` 字节级同步。

## 10. 不在范围

- 后端 schema 迁移
- 目标时长接入用户设置
- 本周均值接入后端 API（暂时在前端从 `recentHistory` 计算）
- 移动端 PWA 适配（已存在的响应式断点足够）