# Hub 页面重设计 — 星座棱晶 · Constellation Prism

**日期**: 2026-06-03
**状态**: 已确认
**最终效果参考**: `.superpowers/brainstorm/939-1780452206/content/ultimate-refinement.html`
**前身**: 2026-06-01-hub-redesign-design.md（已被本方案取代）

---

## 设计方向

**星座棱晶（Constellation Prism）** — 以星图为骨架、棱晶折射为细节的深色奢华学习仪表盘。

融合两种美学基因：
- **星座图（Constellation Map）**：深靛蓝夜空 + 精密星座网格连线 + 星点节点标记 + 天文坐标装饰
- **棱晶折射（Crystalline Prism）**：卡片切角 clip-path + 角落七彩棱镜微光 + 彩虹渐变色彩系统

---

## 色彩系统（参考色值 → tokens.css 变量映射）

| tokens.css 变量 | 参考色值 | 用途 |
|-----------------|---------|------|
| `--brand-500` (调整 hue) | `#7098d8` | 主色-靛蓝：交互、节点、边框 |
| `--info` | `#68c0c8` | 辅色-青：计时、进度、链接 |
| `--brand-300` | `#b8a0e0` | 辅色-紫：知识生态、学习卡 |
| `--warning` | `#d8b070` | 辅色-金：统计、成就、强调 |
| 页面底色 | `#040816` | body background |
| `--surface-glass` | `rgba(8,14,32,0.85)` | 卡片背景 |
| `--neutral-900` (亮主题) / `--neutral-50` (暗主题) | `#dce4f4` | 文字-主：标题 |
| `--neutral-600` (亮) / `--neutral-400` (暗) | `#5580a8` | 文字-次：正文 |
| `--neutral-500` (亮) / `--neutral-500` (暗) | `#507098` | 文字-弱：注释 |

彩虹渐变序列（用于进度环/棱镜折射/渐变文字）：
```
靛蓝 → 青 → 紫 → 金
#7098d8 → #68c0c8 → #b8a0e0 → #d8b070
```

---

## 页面背景系统 — CSS 实现

### HTML 结构
```html
<body>
  <!-- 背景层容器 -->
  <div class="hub-bg">
    <!-- Layer 1+4: 深空渐变 + 星云光斑（CSS radial-gradient） -->
    <div class="hub-bg-nebula"></div>
    <!-- Layer 2+3: 星场 + 星座网格（SVG） -->
    <svg class="hub-bg-stars" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
      <!-- 星点散布 -->
      <!-- 星座连线 -->
    </svg>
  </div>
  <!-- 页面内容 -->
  <div class="hub-app">...</div>
</body>
```

### CSS 代码
```css
/* Layer 1+4: 深空渐变 + 星云光斑 */
.hub-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: #040816;
}

.hub-bg-nebula {
  position: absolute;
  inset: 0;
  background:
    /* 左上靛蓝光斑 */
    radial-gradient(ellipse at 25% 30%, rgba(20,35,80,0.5) 0%, transparent 60%),
    /* 右下紫光斑 */
    radial-gradient(ellipse at 70% 60%, rgba(30,20,60,0.4) 0%, transparent 55%),
    /* 右上青光斑 */
    radial-gradient(ellipse at 85% 20%, rgba(15,40,60,0.3) 0%, transparent 50%);
}

/* Layer 2+3: 星场 + 星座网格 */
.hub-bg-stars {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.30;
}
```

### SVG 星场内容（hub-bg-stars 内）
- 散布 20–30 个 `<circle>` 星点，半径 0.4–1.2px，颜色 `#8098c0` 到 `#d0d8f0` 不等
- 2–3 颗亮星（半径 1.0–1.2px）带十字星芒：
  ```html
  <g transform="translate(x,y)">
    <line x1="-3" y1="0" x2="3" y2="0" stroke="#d0d8f0" stroke-width="0.3"/>
    <line x1="0" y1="-3" x2="0" y2="3" stroke="#d0d8f0" stroke-width="0.3"/>
  </g>
  ```

### SVG 星座网格内容（hub-bg-stars 内）
- 6–10 条连线，使用 `<line>` + `<linearGradient>` 实现淡入淡出：
  ```html
  <defs>
    <linearGradient id="cg1">
      <stop offset="0%" stop-color="#6088c0" stop-opacity="0"/>
      <stop offset="50%" stop-color="#6088c0" stop-opacity="1"/>
      <stop offset="100%" stop-color="#6088c0" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <line x1="60" y1="80" x2="380" y2="100" stroke="url(#cg1)" stroke-width="0.5"/>
  ```
- 交汇处节点圆点：6–8 个 `<circle>`，半径 2–3.5px，颜色 `#6088c0`–`#8098d8`

### Layer 4 补充：大尺寸星云光斑（CSS）
```css
.hub-bg-orb-1 {
  position: absolute;
  top: 15%;
  left: 50%;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle,
    rgba(100,160,220,0.03) 0%,
    rgba(140,120,210,0.02) 40%,
    transparent 70%);
  pointer-events: none;
}
.hub-bg-orb-2 {
  position: absolute;
  bottom: 10%;
  right: 20%;
  width: 250px;
  height: 250px;
  border-radius: 50%;
  background: radial-gradient(circle,
    rgba(200,160,100,0.02) 0%,
    rgba(160,130,210,0.02) 50%,
    transparent 75%);
  pointer-events: none;
}
```

---

## 卡片系统 — 完整 CSS

### 通用卡片基类 `.card-prism`

```css
.card-prism {
  /* 背景 */
  background: linear-gradient(170deg,
    rgba(10,16,36,0.90) 0%,
    rgba(6,12,28,0.92) 100%);

  /* 切角形状 — 12px */
  clip-path: polygon(
    12px 0,
    100% 0,
    100% calc(100% - 12px),
    calc(100% - 12px) 100%,
    0 100%,
    0 12px
  );

  /* 六层 box-shadow 光学镀膜边框 */
  box-shadow:
    0 0 0 1px rgba(70,110,170,0.08),   /* 第1层-微光边框 */
    0 0 0 2px rgba(70,110,170,0.04),   /* 第2层-扩散 */
    0 0 0 3px rgba(70,110,170,0.02),   /* 第3层-晕染 */
    0 4px 40px rgba(0,0,0,0.45),       /* 第4层-投影 */
    inset 0 1px 0 rgba(255,255,255,0.015); /* 第5层-顶光 */

  /* 内层微光边框（clip-path 裁切后） */
  position: relative;
  padding: 22px;

  /* 过渡 */
  transition: transform 0.3s var(--ease-out),
              box-shadow 0.3s var(--ease-out);
}

.card-prism:hover {
  transform: translateY(-2px);
  box-shadow:
    0 0 0 1px rgba(70,110,170,0.14),
    0 0 0 2px rgba(70,110,170,0.08),
    0 0 0 3px rgba(70,110,170,0.04),
    0 8px 48px rgba(0,0,0,0.50),
    inset 0 1px 0 rgba(255,255,255,0.025);
}
```

### 四类卡片配色变体

```css
/* 学习路线 — 靛蓝色调 */
.card-prism-route {
  /* box-shadow 第一层使用靛蓝 */
  --card-accent: 70,110,170;      /* rgba 基础值 */
  --card-node: #80a8e0;
  --card-label: #6088b8;
}

/* 专注计时 — 青色调 */
.card-prism-focus {
  --card-accent: 80,150,180;
  --card-node: #68c0c8;
  --card-label: #58a8b8;
}

/* 知识生态 — 紫色调 */
.card-prism-eco {
  --card-accent: 120,90,180;
  --card-node: #a898e0;
  --card-label: #8878b8;
}

/* 统计数据 — 金色调 */
.card-prism-stats {
  --card-accent: 180,140,90;
  --card-node: #d8b070;
  --card-label: #b89858;
}
```

### 棱镜折射角 — HTML + CSS

每个卡片 1–2 个角落放置折射光。以卡片左上角为例：

```html
<div class="card-prism card-prism-route">
  <!-- 左上角棱镜折射 -->
  <div class="prism-corner prism-corner-tl">
    <div class="prism-corner-inner"></div>
    <div class="prism-corner-outer"></div>
  </div>
  <!-- 右下角棱镜折射 -->
  <div class="prism-corner prism-corner-br">
    <div class="prism-corner-inner"></div>
  </div>
  <!-- 卡片内容 -->
  ...
</div>
```

```css
/* 棱镜折射角 — 基础容器 */
.prism-corner {
  position: absolute;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

/* 左上角 — 90×90px */
.prism-corner-tl {
  top: -1px;
  left: -1px;
  width: 90px;
  height: 90px;
}

/* 右下角 — 70×70px */
.prism-corner-br {
  bottom: -1px;
  right: -1px;
  width: 70px;
  height: 70px;
}

/* 内层折射光（浓） */
.prism-corner-tl .prism-corner-inner {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  /* 以学习路线卡为例：蓝→青→紫 */
  background: linear-gradient(135deg,
    rgba(120,160,220,0.15) 0%,
    rgba(140,180,240,0.06) 25%,
    rgba(170,130,230,0.08) 55%,
    transparent 75%);
  clip-path: polygon(0 0, 90px 0, 0 90px);
}

/* 外层折射光（淡） */
.prism-corner-tl .prism-corner-outer {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: linear-gradient(135deg,
    transparent 20%,
    rgba(180,210,250,0.04) 40%,
    transparent 60%);
  clip-path: polygon(0 0, 60px 0, 0 60px);
}

/* 右下角折射光 */
.prism-corner-br .prism-corner-inner {
  position: absolute;
  bottom: 0; right: 0;
  width: 100%; height: 100%;
  background: linear-gradient(315deg,
    rgba(100,190,210,0.10) 0%,
    rgba(200,170,100,0.06) 35%,
    transparent 65%);
  clip-path: polygon(100% 100%, 0 100%, 100% 0);
}
```

### 棱镜折射配色表（四类卡片的 linear-gradient 参数）

| 卡片 | 角落位置 | 内层渐变（浓） | 外层渐变（淡） |
|------|---------|--------------|--------------|
| 学习路线 | TL | `135deg, rgba(120,160,220,0.15)→rgba(140,180,240,0.06)→rgba(170,130,230,0.08)→transparent` | `135deg, transparent 20%→rgba(180,210,250,0.04) 40%→transparent` |
| 学习路线 | BR | `315deg, rgba(100,190,210,0.10)→rgba(200,170,100,0.06)→transparent` | — |
| 专注计时 | TR | `225deg, rgba(90,190,200,0.12)→rgba(120,210,220,0.05)→rgba(160,140,220,0.06)→transparent` | — |
| 知识生态 | BL | `45deg, rgba(150,110,210,0.10)→rgba(180,150,230,0.05)→transparent` | — |
| 统计数据 | TR | `225deg, rgba(210,180,100,0.12)→rgba(230,200,130,0.05)→rgba(180,150,210,0.04)→transparent` | — |

---

## 组件级代码规范

### 1. 顶部导航栏

```html
<header class="hub-navbar">
  <div class="hub-navbar-left">
    <!-- SVG 八角星 Logo -->
    <svg class="hub-logo" width="24" height="24" viewBox="0 0 24 24">
      <polygon points="12,0 15,8 24,12 15,16 12,24 9,16 0,12 9,8"
               fill="#80a8e0" opacity="0.9"/>
      <circle cx="12" cy="12" r="3" fill="#c0d8f8" opacity="0.6"/>
    </svg>
    <span class="hub-brand">星识 Star-Learn</span>
  </div>
  <div class="hub-navbar-right">
    <span class="hub-version-tag">STAR MAP v2.4</span>
  </div>
</header>
```

```css
.hub-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: rgba(6,12,28,0.80);
  border: 1px solid rgba(70,100,160,0.10);
  border-radius: 14px;
  backdrop-filter: blur(30px);
}

.hub-brand {
  font-size: 14px;
  font-weight: 700;
  color: #c8d8f0;
  letter-spacing: 0.8px;
}

.hub-version-tag {
  font-size: 9px;
  color: #5080a8;
  font-weight: 700;
  letter-spacing: 2px;
}
```

### 2. 左侧图标导航（48px）

```css
.hub-sidebar {
  width: 48px;
  background: rgba(8,12,30,0.6);
  border-right: 1px solid rgba(80,110,180,0.10);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 16px;
  gap: 6px;
}

.hub-sidebar-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 图标使用 SVG，线条色 #506890，stroke-width 1.2 */
}

.hub-sidebar-icon.active {
  background: rgba(100,140,220,0.12);
  /* 图标色变为 #8eb8f0 */
}
```

### 3. 标签页栏

```html
<nav class="hub-tabs">
  <button class="hub-tab active">总览</button>
  <button class="hub-tab">学习</button>
  <button class="hub-tab">工具</button>
  <button class="hub-tab">数据</button>
</nav>
```

```css
.hub-tabs {
  display: flex;
  gap: 0;
  background: rgba(8,14,32,0.50);
  border: 1px solid rgba(70,100,160,0.08);
  border-radius: 12px;
  padding: 4px;
  width: fit-content;
}

.hub-tab {
  padding: 7px 20px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 500;
  color: #607898;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.hub-tab.active {
  font-weight: 700;
  color: #c0d0e8;
  background: rgba(80,120,200,0.12);
}

.hub-tab:hover:not(.active) {
  color: #8098b8;
}
```

### 4. 星座节点标记

这是每个卡片 header 左上角的装饰图案——多层同心环 + 星点。

```html
<!-- 节点标记 HTML -->
<div class="node-marker">
  <svg width="22" height="22" viewBox="0 0 22 22">
    <!-- 外环 -->
    <circle cx="11" cy="11" r="9" fill="none"
            stroke="rgba(100,150,210,0.15)" stroke-width="0.8"/>
    <!-- 虚线刻度环 -->
    <circle cx="11" cy="11" r="6" fill="none"
            stroke="rgba(100,150,210,0.10)" stroke-width="0.5"
            stroke-dasharray="2,3"/>
    <!-- 内环 -->
    <circle cx="11" cy="11" r="3" fill="none"
            stroke="rgba(120,170,220,0.20)" stroke-width="0.8"/>
    <!-- 中心星点 -->
    <circle cx="11" cy="11" r="1.5" fill="#80a8e0"/>
  </svg>
  <!-- 卫星光点 -->
  <div class="node-satellite"></div>
</div>
```

```css
.node-marker {
  position: relative;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-satellite {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c0d8f0;
  box-shadow: 0 0 4px #80a8e0;
}
```

### 5. 卡片 Header 完整结构

每张功能卡片的 header 统一结构：

```html
<div class="card-header">
  <!-- 节点标记 -->
  <div class="node-marker">...</div>
  <div class="card-header-info">
    <span class="card-node-label">NODE α · 01</span>
    <span class="card-coords">RA 12h 34m · Dec +56° 12'</span>
  </div>
  <span class="card-status">进行中</span>
</div>
<h3 class="card-title">每日学习路线</h3>
<p class="card-desc">今天有 3 个学习节点等待探索 · 预计用时 2.5 小时</p>

<!-- 渐变分割线（带星点） -->
<div class="card-sep">
  <div class="card-sep-star"></div>
</div>

<div class="card-footer">
  <!-- 标签 pills + 操作 -->
</div>
```

```css
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.card-node-label {
  font-size: 9px;
  color: var(--card-label); /* 随卡片类型变化 */
  font-weight: 700;
  letter-spacing: 1.8px;
}

.card-coords {
  font-size: 8px;
  color: #406890;
}

.card-status {
  margin-left: auto;
  font-size: 10px;
  color: #7098d8;
  font-weight: 600;
  background: rgba(100,150,210,0.08);
  padding: 3px 10px;
  border-radius: 4px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #dce6f4;
  letter-spacing: -0.2px;
  margin-bottom: 3px;
}

.card-desc {
  font-size: 11px;
  color: #507098;
  line-height: 1.6;
}

/* 渐变分割线 + 星点 */
.card-sep {
  height: 1px;
  margin: 13px 0;
  background: linear-gradient(90deg,
    rgba(90,140,210,0.15) 0%,
    rgba(90,140,210,0.06) 40%,
    transparent 60%);
  position: relative;
}

.card-sep-star {
  position: absolute;
  right: 30%;
  top: -3px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #7098d8;
  box-shadow: 0 0 4px rgba(100,150,210,0.3);
}

/* 卡片 footer */
.card-footer {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
```

### 6. 标签 Pill

```html
<span class="tag-pill tag-blue">复变函数</span>
<span class="tag-pill tag-purple">英语阅读</span>
```

```css
.tag-pill {
  padding: 4px 12px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue {
  background: rgba(80,130,200,0.08);
  border: 1px solid rgba(80,130,200,0.18);
  color: #78a8e0;
}

.tag-purple {
  background: rgba(140,110,200,0.06);
  border: 1px solid rgba(140,110,200,0.15);
  color: #a898d8;
}
```

### 7. "展开详情" 按钮

卡片右下角的操作入口：

```html
<span class="card-expand">
  <svg width="10" height="10" viewBox="0 0 10 10">
    <circle cx="5" cy="5" r="4" fill="none" stroke="#7098d8" stroke-width="1"/>
    <line x1="5" y1="2" x2="5" y2="8" stroke="#7098d8" stroke-width="1"/>
    <line x1="2" y1="5" x2="8" y2="5" stroke="#7098d8" stroke-width="1"/>
  </svg>
  展开星图
</span>
```

```css
.card-expand {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #7098d8;
  font-weight: 600;
  cursor: pointer;
}
```

---

### 8. 专注计时器卡片 — 完整规格

```html
<div class="card-prism card-prism-focus" style="text-align:center;">

  <!-- 右上角棱镜折射 -->
  <div class="prism-corner prism-corner-tr">...</div>

  <!-- 倾斜轨道环装饰（左上角） -->
  <div class="orbit-rings">
    <div class="orbit-ring orbit-ring-1"></div>
    <div class="orbit-ring orbit-ring-2"></div>
    <div class="orbit-ring orbit-ring-3"></div>
    <div class="orbit-dot"></div>
  </div>

  <!-- Header -->
  <div class="card-header" style="justify-content:center;">
    <svg width="12" height="12" viewBox="0 0 12 12">
      <circle cx="6" cy="6" r="5" fill="none"
              stroke="rgba(100,180,200,0.20)" stroke-width="0.8"/>
      <circle cx="6" cy="6" r="2" fill="none"
              stroke="#68c0c8" stroke-width="1"/>
      <circle cx="6" cy="6" r="1" fill="#68c0c8"/>
    </svg>
    <span class="card-node-label">FOCUS NODE · β</span>
  </div>

  <h3 class="card-title" style="font-size:14px;">专注计时器</h3>

  <!-- 三层天文环计时器 -->
  <div class="timer-astronomical">
    <!-- Ring 1: 外层光晕虚线环 -->
    <svg class="timer-ring timer-ring-outer" viewBox="0 0 96 96">
      <circle cx="48" cy="48" r="44" fill="none"
              stroke="rgba(100,190,200,0.06)" stroke-width="0.5"/>
      <circle cx="48" cy="48" r="42" fill="none"
              stroke="rgba(100,190,200,0.04)" stroke-width="0.3"
              stroke-dasharray="4,12"/>
    </svg>

    <!-- Ring 2: 中层天文标记环（NESW 四方位） -->
    <svg class="timer-ring timer-ring-mid" viewBox="0 0 96 96">
      <circle cx="48" cy="48" r="36" fill="none"
              stroke="rgba(120,140,210,0.06)" stroke-width="0.6"/>
      <circle cx="48" cy="48" r="36" fill="none"
              stroke="rgba(120,140,210,0.08)" stroke-width="0.4"
              stroke-dasharray="1,18"/>
      <!-- NESW 标记点 -->
      <circle cx="48" cy="12" r="1.5" fill="rgba(140,180,220,0.30)"/>
      <circle cx="84" cy="48" r="1.5" fill="rgba(140,180,220,0.30)"/>
      <circle cx="48" cy="84" r="1.5" fill="rgba(140,180,220,0.30)"/>
      <circle cx="12" cy="48" r="1.5" fill="rgba(140,180,220,0.30)"/>
    </svg>

    <!-- Ring 3: 彩虹渐变进度环 -->
    <svg class="timer-ring timer-ring-progress" viewBox="0 0 96 96">
      <defs>
        <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#7098d8"/>
          <stop offset="30%" stop-color="#68c0c8"/>
          <stop offset="65%" stop-color="#b8a0e0"/>
          <stop offset="100%" stop-color="#d8b070"/>
        </linearGradient>
      </defs>
      <!-- 底环 -->
      <circle cx="48" cy="48" r="32" fill="none"
              stroke="rgba(255,255,255,0.025)" stroke-width="3"/>
      <!-- 进度弧 — 201 为总周长(r=32), dashoffset=50 表示约75% -->
      <circle cx="48" cy="48" r="32" fill="none"
              stroke="url(#ringGrad)" stroke-width="2.5"
              stroke-dasharray="201" stroke-dashoffset="50"
              stroke-linecap="round"
              transform="rotate(-90 48 48)"/>
    </svg>

    <!-- 中心数字 -->
    <div class="timer-center">
      <span class="timer-number">25</span>
      <span class="timer-unit">分钟</span>
    </div>
  </div>

  <!-- 底部统计行 -->
  <div class="timer-stats">
    <div class="timer-stat">
      <div class="timer-stat-value">3</div>
      <div class="timer-stat-label">完成</div>
    </div>
    <div class="timer-stat-sep"></div>
    <div class="timer-stat">
      <div class="timer-stat-value">45<span>m</span></div>
      <div class="timer-stat-label">今日</div>
    </div>
    <div class="timer-stat-sep"></div>
    <div class="timer-stat">
      <div class="timer-stat-value accent">87<span>%</span></div>
      <div class="timer-stat-label">专注率</div>
    </div>
  </div>
</div>
```

```css
/* 轨道环装饰 */
.orbit-rings {
  position: absolute;
  top: 14px;
  left: 16px;
  pointer-events: none;
}

.orbit-ring {
  position: absolute;
  border-radius: 50%;
  border: 0.8px solid rgba(100,180,200,0.08);
}

.orbit-ring-1 {
  width: 42px; height: 42px;
  transform: rotateX(65deg) rotateY(15deg);
}

.orbit-ring-2 {
  width: 30px; height: 30px;
  top: 6px; left: 6px;
  border-width: 0.6px;
  border-color: rgba(100,180,200,0.06);
  transform: rotateX(55deg) rotateY(-10deg);
}

.orbit-ring-3 {
  width: 18px; height: 18px;
  top: 12px; left: 12px;
  border-width: 0.5px;
  border-color: rgba(100,180,200,0.10);
  transform: rotateX(45deg);
}

.orbit-dot {
  position: absolute;
  top: 8px; left: 28px;
  width: 3px; height: 3px;
  border-radius: 50%;
  background: #90d8e0;
  box-shadow: 0 0 6px rgba(100,200,210,0.5);
}

/* 计时器容器 */
.timer-astronomical {
  position: relative;
  width: 96px;
  height: 96px;
  margin: 12px auto 10px;
}

.timer-ring {
  position: absolute;
  top: 0; left: 0;
  width: 96px;
  height: 96px;
}

.timer-ring-outer { opacity: 0.30; }

.timer-center {
  position: absolute;
  inset: 20px;
  border-radius: 50%;
  background: rgba(5,10,26,0.92);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02);
}

.timer-number {
  font-size: 24px;
  font-weight: 800;
  color: #e8eef6;
  line-height: 1;
}

.timer-unit {
  font-size: 9px;
  color: #507898;
  font-weight: 500;
}

/* 底部统计 */
.timer-stats {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 4px;
}

.timer-stat-value {
  font-size: 14px;
  font-weight: 700;
  color: #d0d8e8;
}

.timer-stat-value.accent { color: #68c0c8; }

.timer-stat-value span {
  font-size: 9px;
  color: #507898;
}

.timer-stat-label {
  font-size: 9px;
  color: #507898;
}

.timer-stat-sep {
  width: 1px;
  background: rgba(100,150,200,0.10);
}
```

---

### 9. 知识生态卡片 — 完整规格

```html
<div class="card-prism card-prism-eco">

  <!-- 左下角棱镜折射 -->
  <div class="prism-corner prism-corner-bl">...</div>

  <!-- 右上角微型星座图装饰 -->
  <div class="mini-constellation">
    <svg width="60" height="60" viewBox="0 0 60 60" opacity="0.12">
      <line x1="10" y1="30" x2="30" y2="10" stroke="#a898e0" stroke-width="0.5"/>
      <line x1="30" y1="10" x2="50" y2="30" stroke="#a898e0" stroke-width="0.5"/>
      <line x1="50" y1="30" x2="30" y2="50" stroke="#a898e0" stroke-width="0.5"/>
      <line x1="30" y1="50" x2="10" y2="30" stroke="#a898e0" stroke-width="0.5"/>
      <line x1="30" y1="10" x2="30" y2="50" stroke="#a898e0" stroke-width="0.3"/>
      <line x1="10" y1="30" x2="50" y2="30" stroke="#a898e0" stroke-width="0.3"/>
      <circle cx="10" cy="30" r="2" fill="#b8a0e8"/>
      <circle cx="30" cy="10" r="2.5" fill="#b8a0e8"/>
      <circle cx="50" cy="30" r="2" fill="#b8a0e8"/>
      <circle cx="30" cy="50" r="2" fill="#b8a0e8"/>
    </svg>
  </div>

  <!-- Header -->
  <div class="card-header">
    <div class="node-marker">...</div>
    <span class="card-node-label">ECO NODE · γ</span>
    <span class="card-status">活跃</span>
  </div>

  <h3 class="card-title">知识生态系统</h3>
  <p class="card-desc">18 个知识节点构成星座网络 · 7 个节点等待复习巩固</p>

  <div class="card-sep"></div>

  <!-- 知识柱状图 -->
  <div class="knowledge-bars">
    <!-- 7 根柱子，每根结构： -->
    <div class="kbar">
      <div class="kbar-fill" style="height:16px; --bar-color:rgba(150,120,210,0.30)">
        <!-- 顶部星点（高柱才有） -->
      </div>
      <span class="kbar-label">数</span>
    </div>
    <div class="kbar">
      <div class="kbar-fill" style="height:24px; --bar-color:rgba(130,150,210,0.35)"></div>
      <span class="kbar-label">物</span>
    </div>
    <div class="kbar">
      <div class="kbar-fill has-star" style="height:32px; --bar-color:rgba(140,160,220,0.45)">
        <div class="kbar-star"></div>
      </div>
      <span class="kbar-label">英</span>
    </div>
    <div class="kbar">
      <div class="kbar-fill" style="height:20px; --bar-color:rgba(100,180,200,0.28)"></div>
      <span class="kbar-label">计</span>
    </div>
    <div class="kbar">
      <div class="kbar-fill has-star" style="height:36px; --bar-color:rgba(160,140,220,0.50)">
        <div class="kbar-star"></div>
      </div>
      <span class="kbar-label">语</span>
    </div>
    <div class="kbar">
      <div class="kbar-fill" style="height:28px; --bar-color:rgba(200,160,100,0.32)"></div>
      <span class="kbar-label">政</span>
    </div>
    <div class="kbar">
      <div class="kbar-fill has-star" style="height:38px; --bar-color:rgba(210,180,120,0.48)">
        <div class="kbar-star"></div>
      </div>
      <span class="kbar-label">专</span>
    </div>
  </div>

  <!-- 图例 -->
  <div class="knowledge-legend">
    <span class="legend-item"><span class="legend-dot" style="background:#80a8e0;"></span>已掌握 11</span>
    <span class="legend-item"><span class="legend-dot" style="background:#a0d8e0;"></span>学习中 4</span>
    <span class="legend-item"><span class="legend-dot" style="background:#d8b070;"></span>待复习 3</span>
  </div>
</div>
```

```css
.knowledge-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 40px;
  margin-bottom: 10px;
}

.kbar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.kbar-fill {
  width: 100%;
  background: linear-gradient(180deg,
    var(--bar-color) 0%,
    color-mix(in srgb, var(--bar-color), black 30%) 100%);
  border-radius: 3px 3px 0 0;
  position: relative;
}

.kbar-star {
  position: absolute;
  top: -7px;
  left: 50%;
  transform: translateX(-50%);
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #80a8e0;
  box-shadow: 0 0 6px rgba(100,150,210,0.5);
}

.kbar-label {
  font-size: 7px;
  color: #505878;
}

.knowledge-legend {
  display: flex;
  gap: 14px;
  font-size: 9px;
  color: #507098;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
```

---

### 10. 统计卡片 — 完整规格

```html
<div class="card-prism card-prism-stats">

  <!-- 右上角金调棱镜折射 -->
  <div class="prism-corner prism-corner-tr">...</div>

  <!-- Header -->
  <div class="card-header">
    <svg width="12" height="12" viewBox="0 0 12 12">
      <polygon points="6,0 8,4 12,6 8,8 6,12 4,8 0,6 4,4"
               fill="none" stroke="#d8b070" stroke-width="0.8"/>
      <circle cx="6" cy="6" r="1.2" fill="#d8b070"/>
    </svg>
    <span class="card-node-label">STELLAR STATS · δ</span>
  </div>

  <!-- 彩虹渐变大数字 -->
  <div class="stats-big-number">
    <span class="stats-number-gradient">12</span><span class="stats-unit"> h</span>
  </div>
  <div class="stats-subtitle">本周累计学习时长</div>

  <div class="card-sep"></div>

  <!-- 指标网格 -->
  <div class="stats-grid">
    <div class="stats-cell">
      <div class="stats-cell-value">87<span>%</span></div>
      <div class="stats-cell-label">完成率</div>
    </div>
    <div class="stats-cell">
      <div class="stats-cell-value accent-cyan">12</div>
      <div class="stats-cell-label">连续天数</div>
    </div>
    <div class="stats-cell">
      <div class="stats-cell-value accent-purple">3.2<span>h</span></div>
      <div class="stats-cell-label">日均</div>
    </div>
  </div>
</div>
```

```css
.stats-big-number {
  font-size: 38px;
  font-weight: 800;
  letter-spacing: -1.5px;
  line-height: 1;
  margin: 4px 0;
}

.stats-number-gradient {
  background: linear-gradient(135deg,
    #80a8e0 0%, #68c0c8 35%, #b8a0e0 65%, #d8b070 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stats-unit {
  font-size: 18px;
  -webkit-text-fill-color: #4a7090;
}

.stats-subtitle {
  font-size: 10px;
  color: #507098;
  letter-spacing: 0.5px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.stats-cell {
  text-align: center;
  background: rgba(255,255,255,0.01);
  border-radius: 8px;
  padding: 8px 4px;
}

.stats-cell-value {
  font-size: 18px;
  font-weight: 700;
  color: #d0d8e8;
}

.stats-cell-value.accent-cyan { color: #68c0c8; }
.stats-cell-value.accent-purple { color: #b8a0e0; }

.stats-cell-value span {
  font-size: 10px;
  color: #507898;
}

.stats-cell-label {
  font-size: 9px;
  color: #507098;
}
```

---

### 11. 趋势迷你图（SVG polyline）

用于数据 Tab 或统计卡片内的 7 日趋势图。

```html
<svg width="100%" height="56" viewBox="0 0 200 56">
  <!-- 网格参考线 -->
  <line x1="0" y1="14" x2="200" y2="14"
        stroke="rgba(100,140,200,0.06)" stroke-width="0.5"/>
  <line x1="0" y1="28" x2="200" y2="28"
        stroke="rgba(100,140,200,0.06)" stroke-width="0.5"/>
  <line x1="0" y1="42" x2="200" y2="42"
        stroke="rgba(100,140,200,0.06)" stroke-width="0.5"/>

  <!-- 折线 -->
  <polyline points="10,35 40,28 70,38 100,20 130,24 160,12 190,8"
    fill="none" stroke="url(#trendGrad)" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round"/>

  <!-- 数据点 -->
  <circle cx="10" cy="35" r="3" fill="#7098d8"/>
  <circle cx="40" cy="28" r="2.5" fill="#68c0c8"/>
  <circle cx="70" cy="38" r="2.5" fill="#80a8d8"/>
  <circle cx="100" cy="20" r="2.5" fill="#a0c0e0"/>
  <circle cx="130" cy="24" r="2.5" fill="#90b8d8"/>
  <circle cx="160" cy="12" r="3" fill="#b8a0e0"/>
  <circle cx="190" cy="8" r="3.5" fill="#d8b070"/> <!-- 今日-金色强调 -->

  <defs>
    <linearGradient id="trendGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#7098d8"/>
      <stop offset="50%" stop-color="#68c0c8"/>
      <stop offset="100%" stop-color="#d8b070"/>
    </linearGradient>
  </defs>
</svg>

<!-- 底部星期标签 -->
<div class="trend-labels">
  <span>周一</span><span>周二</span><span>周三</span><span>周四</span>
  <span>周五</span><span>周六</span><span class="today">今日</span>
</div>
```

```css
.trend-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 2px;
  font-size: 9px;
  color: #506890;
}

.trend-labels .today {
  color: #d8b070;
}
```

---

### 12. 欢迎区（Hero）

```html
<div class="hero">
  <div class="hero-title-row">
    <h1 class="hero-title">下午好，继续探索星图</h1>
    <span class="hero-coords">坐标 N22°33' · E114°08'</span>
  </div>
  <div class="hero-meta">
    <span>今日完成 3/5 学习节点</span>
    <span class="hero-sep"></span>
    <span class="hero-accent-cyan">连续 12 天</span>
    <span class="hero-sep"></span>
    <span class="hero-accent-purple">心流指数 78</span>
  </div>
</div>
```

```css
.hero {
  margin-bottom: 16px;
}

.hero-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.hero-title {
  font-size: 22px;
  font-weight: 800;
  color: #dce4f4;
  letter-spacing: -0.3px;
}

.hero-coords {
  font-size: 9px;
  color: #5078a0;
  font-weight: 600;
  letter-spacing: 1px;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 3px;
  font-size: 11px;
  color: #5580a8;
}

.hero-sep {
  width: 1px;
  height: 10px;
  background: rgba(100,140,200,0.15);
}

.hero-accent-cyan { color: #68c0c8; font-weight: 600; }
.hero-accent-purple { color: #b8a0e0; }
```

---

### 13. 右侧面板

```html
<aside class="right-panel">
  <div class="panel-section">
    <h4 class="panel-label">星历日历</h4>
    <div class="panel-calendar">
      <div class="cal-date-label">6月3日</div>
      <div class="cal-date-number">3</div>
      <div class="cal-date-info">4 个学习节点</div>
    </div>
  </div>
  <div class="panel-section">
    <h4 class="panel-label">星讯</h4>
    <p class="panel-news-item">新课程"深度学习"已上线</p>
    <span class="panel-news-time">2 小时前</span>
  </div>
</aside>
```

```css
.right-panel {
  width: 180px;
  background: rgba(8,12,28,0.50);
  border-left: 1px solid rgba(80,110,180,0.10);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-label {
  font-size: 10px;
  color: #506890;
  font-weight: 700;
  letter-spacing: 1px;
}

.panel-calendar {
  background: rgba(10,16,36,0.60);
  border: 1px solid rgba(80,110,180,0.12);
  border-radius: 10px;
  padding: 12px;
  text-align: center;
}

.cal-date-label { font-size: 10px; color: #6080a8; }
.cal-date-number { font-size: 26px; font-weight: 800; color: #c0d0e8; margin: 2px 0; }
.cal-date-info { font-size: 9px; color: #7098d8; }

.panel-news-item { font-size: 11px; color: #8098b8; line-height: 1.5; }
.panel-news-time { font-size: 10px; color: #506890; }
```

---

## 排版层级

| 层级 | 字号 | 字重 | 颜色 | letter-spacing | 用途 |
|------|------|------|------|----------------|------|
| H1 | 22px | 800 | `#dce4f4` | -0.3px | 页面大标题 |
| H2 | 16px | 700 | `#dce6f4` | -0.2px | 卡片标题 |
| H3 | 14px | 600 | `#bcc8d8` | 0.4px | 组件标题 |
| Body | 11px | 400 | `#5580a8` | 0 | 正文 |
| Caption | 9–10px | 500–600 | `#507098` | 0 | 注释/坐标 |
| Label | 9px | 700 | 跟随卡片 | 1.5–2px | 英文标注 |
| 大数字 | 38px | 800 | 渐变色 | -1.5px | 统计数据 |
| 计时数字 | 24px | 800 | `#e8eef6` | 0 | 计时器 |

---

## 装饰元素完整清单

| 元素 | 实现方式 | 使用位置 |
|------|---------|---------|
| 星座节点标记 | SVG 多层同心环 + CSS 卫星光点 | 每张功能卡片 header |
| 天文坐标文字 | `<span>` RA/Dec 格式 | 节点标记下方 |
| 棱镜折射角 | `linear-gradient` + `clip-path` 三角形 | 每张卡片 1–2 个角落 |
| 轨道环 | `div` + `border-radius:50%` + `transform:rotateX/Y` | 计时器卡片左上 |
| 轨道环光点 | `div` 小圆点 + `box-shadow` 发光 | 轨道环上 |
| 星芒十字 | SVG `line` 交叉 | 背景亮星 |
| 微型星座图 | SVG `line` + `circle` 多边形连线 | 知识生态卡片右上 |
| 渐变分割线 | `linear-gradient` 横线 | 卡片内容区之间 |
| 分割线星点 | `div` 圆点 + `box-shadow` | 分割线上 |
| 彩虹渐变环 | SVG `circle` + `linearGradient` stroke | 计时器进度环 |
| 彩虹渐变文字 | `-webkit-background-clip: text` | 统计大数字 |
| 星云光斑 | `radial-gradient` 椭圆 | 页面四角背景 |

---

## 布局结构

```
┌──────────────────────────────────────────────────────┐
│  顶部导航栏 (logo · 搜索 · 心流 · 通知 · 用户)        │
├────┬────────────────────────────────────┬─────────────┤
│    │  [总览] [学习] [工具] [数据]       │             │
│ 左 │                                   │  右侧面板   │
│ 侧 │  Hero 欢迎区                       │  · 星历日历 │
│ 导 │                                   │  · 星讯     │
│ 航 │  ┌──────────┐ ┌──────────┐       │  · 快捷入口 │
│ 48 │  │ 学习路线  │ │ 专注计时  │       │             │
│ px │  └──────────┘ └──────────┘       │             │
│    │  ┌──────────┐ ┌──────────┐       │             │
│    │  │ 知识生态  │ │ 星图统计  │       │             │
│    │  └──────────┘ └──────────┘       │             │
│    │                                   │             │
├────┴────────────────────────────────────┴─────────────┤
│  响应式: ≥1400 三栏 / ≥1024 右侧折叠 / ≥768 左侧折叠  │
└──────────────────────────────────────────────────────┘
```

---

## 技术方案

### CSS
- 单一文件 `css/hub.css`，完全重写
- 目标 < 2500 行
- 0 硬编码颜色值 — 使用 tokens.css CSS 变量，参考色值用于查找对应变量
- CSS Grid 做卡片网格布局，Flexbox 做组件内部布局
- `clip-path: polygon()` 切角
- `box-shadow` 堆叠模拟多层边框
- 棱镜折射角用 `linear-gradient` + `clip-path` 三角形

### HTML
- 语义化结构
- 所有内联 style 颜色通过 CSS class 管理
- 保留现有 data-* 属性体系

### 现有特效保留
保留并适配新配色：
- 数据粒子（data particles）
- 光标光晕（cursor glow）
- 涟漪效果（ripple）
- 卡片 shimmer 扫光（光泽色改为靛蓝系）
- 3D 倾斜（3D tilt）
- 浮动微尘（floating dust）
- 卡片呼吸光（breath glow）

### JavaScript
- 保留全部现有模块（FocusTracker、DailyRoute、StudyHall、Kanban、KnowledgeEco、Toast 等）
- localStorage 数据持久化
- Canvas 图表（趋势图、热力图）配色适配新系统

---

## 响应式断点
- `≥1400px` — 完整三栏
- `≥1024px` — 右侧面板折叠为底部抽屉
- `≥768px` — 左侧导航折叠为顶部标签
- `<768px` — 单栏

---

## 文件变更

| 操作 | 文件 |
|------|------|
| 重写 | `html/hub.html` |
| 重写 | `css/hub.css` |
| 更新 | `js/hub.js`（图表配色适配） |
| 保留 | `css/tokens.css`（无需修改） |
| 保留 | 其他所有页面和功能 |

---

## 功能保留清单（22 项）

1. 顶部导航栏 2. 左侧图标导航 3. 欢迎区 4. 快捷操作按钮组
5. 功能卡片网格 6. 每日路线 7. 心流分数显示 8. 知识生态系统
9. 心流共振面板 10. 专注计时器 11. 自习室同伴匹配 12. 看板
13. 任务管理列表 14. 日历 15. 标签云 16. 学习趋势图
17. 热力图 18. 课程进度 19. 新闻/动态 20. 主题切换（6 套）
21. 统计概览 22. 搜索功能

---

## 不做的事
- 不新增功能模块
- 不修改 tokens.css
- 不修改后端 API
- 不影响其他页面
- 不使用 emoji 图标
