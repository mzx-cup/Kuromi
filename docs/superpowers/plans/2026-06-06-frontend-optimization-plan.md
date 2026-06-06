# Frontend Display Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Systematic enhancement of Star-Learn frontend across 6 systems (tokens, components, animations, base layer, auth/theme, pages) on all pages except index.html and classroom.html.

**Architecture:** Foundation-first approach — extend CSS tokens/base/animations, then build unified card components on top, then enhance JS systems (auth/theme/toast), then transform 5 showcase pages, then batch-migrate remaining 19 pages in 3 waves. All changes are additive; no JS business logic rewrites.

**Tech Stack:** Vanilla HTML/CSS/JS + Alpine.js 3.14 + OKLCH color space + CSS custom properties

---

### Task 1: Extend tokens.css — Spacing, Z-Index, Semantic Tokens

**Files:**
- Modify: `css/tokens.css`

- [ ] **Step 1: Add spacing tokens after existing space tokens**

Open `css/tokens.css`. Find the line `--space-2xl: 64px;` (or last space token). Add after it:

```css
--space-3xl: 80px;
--space-section: 48px;
--space-gutter: 24px;
--gap-xs: 4px;
--gap-sm: 8px;
--gap-md: 16px;
--gap-lg: 24px;
--gap-xl: 32px;
```

- [ ] **Step 2: Add z-index scale before the first `@media` or `data-theme` block**

```css
/* ===== Z-Index Scale ===== */
--z-base: 0;
--z-dropdown: 100;
--z-sticky: 200;
--z-overlay: 500;
--z-modal: 1000;
--z-toast: 1100;
--z-tooltip: 1200;
```

- [ ] **Step 3: Add semantic surface tokens in the semantic tokens section**

Find the section with `--surface-card` and add after:

```css
--surface-raised: color-mix(in oklch, var(--surface-card), white 5%);
--surface-sunken: color-mix(in oklch, var(--surface-card), black 5%);
--separator: color-mix(in oklch, var(--border-color), transparent 50%);
--overlay-dim: rgba(0, 0, 0, 0.5);
--focus-ring: 0 0 0 3px color-mix(in oklch, var(--brand-400), transparent 60%);
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
--radius-pill: 9999px;
```

- [ ] **Step 4: Add refined shadow tokens near existing shadow tokens**

```css
--shadow-inset: inset 0 2px 4px rgba(0,0,0, calc(var(--_shadow-strength) * 0.5));
--shadow-glow: 0 0 20px color-mix(in oklch, var(--brand-400), transparent 60%);
--shadow-card-hover: 0 8px 30px rgba(0,0,0, calc(var(--_shadow-strength) * 1.2));
--shadow-modal: 0 20px 60px rgba(0,0,0, calc(var(--_shadow-strength) * 1.5));
--shadow-toast: 0 4px 20px rgba(0,0,0, calc(var(--_shadow-strength) * 1));
```

- [ ] **Step 5: Commit**

```bash
git add css/tokens.css
git commit -m "feat: extend design tokens — spacing, z-index, semantic, shadow tokens"
```

---

### Task 2: Enhance app-base.css — A11y, Utilities, Motion

**Files:**
- Modify: `css/app-base.css`

- [ ] **Step 1: Add screen-reader and scrollbar utility classes**

At the end of `css/app-base.css`, append:

```css
/* Screen reader only */
.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}

/* Firefox scrollbar */
* {
  scrollbar-width: thin;
  scrollbar-color: var(--border-color) transparent;
}

/* Hide scrollbar */
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
.no-scrollbar::-webkit-scrollbar { display: none; }

/* Focus visible ring for keyboard a11y */
:focus-visible {
  outline: 2px solid var(--brand-400);
  outline-offset: 2px;
}

/* Text truncation */
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.truncate-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
```

- [ ] **Step 2: Add responsive grid and flex utility classes**

```css
/* Grid utilities */
.app-container { max-width: 1400px; margin: 0 auto; padding: 0 var(--space-gutter); }
.app-grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--gap-md); }
.app-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--gap-md); }
.app-grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--gap-md); }
@media (max-width: 768px) {
  .app-grid-2, .app-grid-3, .app-grid-4 { grid-template-columns: 1fr; }
}

/* Flex utilities */
.app-flex-row { display: flex; flex-direction: row; }
.app-flex-col { display: flex; flex-direction: column; }
.app-gap-xs { gap: var(--gap-xs); } .app-gap-sm { gap: var(--gap-sm); }
.app-gap-md { gap: var(--gap-md); } .app-gap-lg { gap: var(--gap-lg); }
.app-gap-xl { gap: var(--gap-xl); }
```

- [ ] **Step 3: Add reduced-motion media query**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}
```

- [ ] **Step 4: Commit**

```bash
git add css/app-base.css
git commit -m "feat: enhance base layer — a11y, grid/flex utilities, reduced-motion"
```

---

### Task 3: Enhance app-bg.css — Theme Transition Crossfade

**Files:**
- Modify: `css/app-bg.css`

- [ ] **Step 1: Add smooth background transition**

At the top of `css/app-bg.css`, add:

```css
/* Smooth crossfade between themes */
.app-bg-layer { transition: opacity 0.6s ease; }
```

- [ ] **Step 2: Add grid pattern option for light themes**

At the end of the file, append:

```css
/* Grid pattern for light themes */
[data-theme-transitioning] .app-bg-layer { opacity: 0.5; }

.light-theme .app-bg-layer::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.5;
}
```

- [ ] **Step 3: Commit**

```bash
git add css/app-bg.css
git commit -m "feat: enhance background layer — theme crossfade, light grid pattern"
```

---

### Task 4: Expand animations.css — Entry, Attention, Stagger

**Files:**
- Modify: `css/animations.css`

- [ ] **Step 1: Add entry animations after existing keyframes**

Open `css/animations.css`. After the `.bounce` block (line 58), add:

```css
/* ---------- 从上方滑入 ---------- */
@keyframes slide-down {
  from { opacity: 0; transform: translateY(-16px); }
  to   { opacity: 1; transform: translateY(0); }
}
.slide-down { animation: slide-down 0.35s var(--ease-out) forwards; }

/* ---------- 从右侧滑入 ---------- */
@keyframes slide-left {
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: translateX(0); }
}
.slide-left { animation: slide-left 0.35s var(--ease-out) forwards; }

/* ---------- 从左侧滑入 ---------- */
@keyframes slide-right {
  from { opacity: 0; transform: translateX(-16px); }
  to   { opacity: 1; transform: translateX(0); }
}
.slide-right { animation: slide-right 0.35s var(--ease-out) forwards; }

/* ---------- 淡入 + 上移 ---------- */
@keyframes fade-up {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fade-up { animation: fade-up 0.4s var(--ease-out) forwards; }

/* ---------- 弹出 ---------- */
@keyframes grow-in {
  from { opacity: 0; transform: scale(0); }
  to   { opacity: 1; transform: scale(1); }
}
.grow-in { animation: grow-in 0.3s var(--ease-out) forwards; }
```

- [ ] **Step 2: Add attention animations**

```css
/* ---------- 错误抖动 ---------- */
@keyframes gentle-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-4px); }
  40% { transform: translateX(4px); }
  60% { transform: translateX(-4px); }
  80% { transform: translateX(4px); }
}
.gentle-shake { animation: gentle-shake 0.4s ease; }

/* ---------- 发光脉冲 ---------- */
@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 0 0 color-mix(in oklch, var(--brand-400), transparent 60%); }
  50%      { box-shadow: 0 0 0 8px color-mix(in oklch, var(--brand-400), transparent 90%); }
}
.glow-pulse { animation: glow-pulse 2s ease-in-out infinite; }

/* ---------- 呼吸 ---------- */
@keyframes breathing {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.02); }
}
.breathing { animation: breathing 3s ease-in-out infinite; }

/* ---------- 吸引注意 ---------- */
@keyframes draw-attention {
  0% { transform: scale(1) translateY(0); box-shadow: var(--shadow-md); }
  10% { transform: scale(1.05) translateY(-4px); box-shadow: var(--shadow-glow); }
  20% { transform: scale(1) translateY(0); box-shadow: var(--shadow-md); }
  100% { transform: scale(1) translateY(0); box-shadow: var(--shadow-md); }
}
.draw-attention { animation: draw-attention 2s ease-in-out infinite; }
```

- [ ] **Step 3: Add stagger system and animation utility classes**

```css
/* ---------- Stagger 延迟系统 ---------- */
.stagger > * { animation-delay: calc(var(--stagger-index, 0) * var(--stagger-delay, 60ms)); }
.stagger > *:nth-child(1) { --stagger-index: 0; }
.stagger > *:nth-child(2) { --stagger-index: 1; }
.stagger > *:nth-child(3) { --stagger-index: 2; }
.stagger > *:nth-child(4) { --stagger-index: 3; }
.stagger > *:nth-child(5) { --stagger-index: 4; }
.stagger > *:nth-child(6) { --stagger-index: 5; }
.stagger > *:nth-child(7) { --stagger-index: 6; }
.stagger > *:nth-child(8) { --stagger-index: 7; }
.stagger > *:nth-child(9) { --stagger-index: 8; }
.stagger > *:nth-child(10) { --stagger-index: 9; }

/* ---------- 动画控制工具类 ---------- */
.animate-once { animation-iteration-count: 1; }
.animate-infinite { animation-iteration-count: infinite; }
.animate-delay-100 { animation-delay: 100ms; }
.animate-delay-200 { animation-delay: 200ms; }
.animate-delay-300 { animation-delay: 300ms; }
.animate-delay-500 { animation-delay: 500ms; }
.duration-fast { animation-duration: 0.15s; }
.duration-normal { animation-duration: 0.3s; }
.duration-slow { animation-duration: 0.6s; }

@media (prefers-reduced-motion: reduce) {
  .stagger > * { animation-delay: 0ms !important; }
  .animate-infinite { animation-iteration-count: 1 !important; }
}
```

- [ ] **Step 4: Commit**

```bash
git add css/animations.css
git commit -m "feat: expand animations — entry, attention, stagger system, a11y"
```

---

### Task 5: Add 5 Card Prototypes + Variants to components.css

**Files:**
- Modify: `css/components.css`

- [ ] **Step 1: Add base .app-card foundation**

Find the existing `.app-card` style (or the card section). Ensure this base exists or add it:

```css
/* ===== Unified Card System ===== */
.app-card {
  background: var(--surface-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

/* ===== Card Variants ===== */
.app-card-glass {
  background: color-mix(in oklch, var(--surface-card), transparent 30%);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.app-card-ghost { background: transparent; border-color: transparent; box-shadow: none; }
.app-card-interactive { cursor: pointer; transition: transform 0.2s ease, box-shadow 0.2s ease; }
.app-card-interactive:hover { transform: translateY(-2px); box-shadow: var(--shadow-card-hover); }
.app-card-compact { padding: var(--space-sm); }
```

- [ ] **Step 2: Add .app-stat-card prototype**

```css
/* ---------- Stat Card ---------- */
.app-stat-card {
  display: flex; flex-direction: column; gap: 4px; padding: var(--space-md);
  background: var(--surface-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
}
.app-stat-card .app-stat-icon { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-md); }
.app-stat-card .app-stat-value { font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-heading); line-height: 1.2; }
.app-stat-card .app-stat-label { font-size: var(--text-xs); color: var(--text-muted); }
.app-stat-card .app-stat-delta { font-size: var(--text-xs); display: flex; align-items: center; gap: 4px; }
.app-stat-card .app-stat-delta.up { color: var(--success); }
.app-stat-card .app-stat-delta.down { color: var(--danger); }
```

- [ ] **Step 3: Add .app-content-card prototype**

```css
/* ---------- Content Card ---------- */
.app-content-card {
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--surface-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); transition: box-shadow 0.2s ease;
}
.app-content-card .app-card-thumb {
  width: 100%; height: 160px; object-fit: cover; background: var(--surface-hover);
  display: flex; align-items: center; justify-content: center;
}
.app-content-card .app-card-body { padding: var(--space-md); display: flex; flex-direction: column; gap: 6px; flex: 1; }
.app-content-card .app-card-title { font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-heading); }
.app-content-card .app-card-desc { font-size: var(--text-sm); color: var(--text-muted); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.app-content-card .app-card-meta { font-size: var(--text-xs); color: var(--text-muted); display: flex; gap: 12px; }
.app-content-card .app-card-actions { padding: 0 var(--space-md) var(--space-md); display: flex; gap: 8px; }
```

- [ ] **Step 4: Add .app-action-card prototype**

```css
/* ---------- Action Card ---------- */
.app-action-card {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: var(--space-lg); text-align: center; cursor: pointer;
  background: var(--surface-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  text-decoration: none;
}
.app-action-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-card-hover); }
.app-action-card .app-card-icon { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-md); }
.app-action-card .app-card-title { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--text-heading); }
.app-action-card .app-card-desc { font-size: var(--text-xs); color: var(--text-muted); }
```

- [ ] **Step 5: Add .app-form-card prototype**

```css
/* ---------- Form Card ---------- */
.app-form-card {
  background: var(--surface-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-md); padding: var(--space-lg);
}
.app-form-card .app-card-header { margin-bottom: var(--space-md); }
.app-form-card .app-card-header h2 { font-size: var(--text-xl); font-weight: var(--font-bold); color: var(--text-heading); }
.app-form-card .app-card-footer { margin-top: var(--space-md); display: flex; justify-content: flex-end; gap: 8px; }
```

- [ ] **Step 6: Add .app-chart-card prototype**

```css
/* ---------- Chart Card ---------- */
.app-chart-card {
  background: var(--surface-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--space-md); overflow: hidden;
}
.app-chart-card .app-card-header { margin-bottom: var(--space-sm); font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--text-heading); }
.app-chart-card .app-chart-body { width: 100%; min-height: 200px; }
```

- [ ] **Step 7: Add Prism corner modifier**

```css
/* ---------- Prism Corner Decor ---------- */
.app-card-prism { position: relative; overflow: hidden; }
.app-card-prism::before {
  content: ''; position: absolute; top: 0; right: 0;
  width: 0; height: 0;
  border-style: solid;
  border-width: 0 24px 24px 0;
  border-color: transparent var(--brand-300) transparent transparent;
  opacity: 0.4; transition: opacity 0.3s ease;
}
.app-card-prism:hover::before { opacity: 0.7; }
```

- [ ] **Step 8: Add compatibility mapping for legacy class names**

```css
/* ===== Legacy Class Name Compatibility ===== */
.stat-card, .dd-stat, .metric-panel, .summary-card,
.hub-stat, .progress-stat, .dashboard-stat, .teacher-stat,
.calendar-stat, .flow-stat, .quantum-metric, .cockpit-stat-card {
  /* Inherits from .app-stat-card via JS or page migration */
}

.content-card, .resource-card, .class-card, .exam-card,
.video-info-panel, .player-shell, .plant-info-panel {
  /* Inherits from .app-content-card */
}

.feature-card, .func-card, .overview-action-card, .compact-card,
.pref-card, .brief-card, .dimension-card, .option-btn {
  /* Inherits from .app-action-card */
}

.auth-card-inner, .form-card, .setting-card {
  /* Inherits from .app-form-card */
}

.chart-card, .td-chart-box, .flow-card, .badge-card,
.plant-detail-card, .main-card {
  /* Inherits from .app-chart-card */
}
```

- [ ] **Step 9: Commit**

```bash
git add css/components.css
git commit -m "feat: add 5 unified card prototypes, variants, prism modifier, legacy compat map"
```

---

### Task 6: Add Button/Modal/Form Enhancement Styles to components.css

**Files:**
- Modify: `css/components.css`

- [ ] **Step 1: Add button variants after existing .app-btn styles**

```css
/* Button — outline variant */
.app-btn-outline {
  background: transparent; border: 1.5px solid var(--brand-400);
  color: var(--brand-400);
}
.app-btn-outline:hover { background: var(--brand-400); color: white; }

/* Button — glass variant */
.app-btn-glass {
  background: color-mix(in oklch, var(--surface-card), transparent 40%);
  backdrop-filter: blur(8px); border: 1px solid color-mix(in oklch, var(--border-color), transparent 50%);
}

/* Button — link variant */
.app-btn-link {
  background: transparent; border: none; color: var(--brand-400);
  padding: 0; text-decoration: underline; text-underline-offset: 2px;
}
.app-btn-link:hover { color: var(--brand-500); }

/* Button — loading state */
.app-btn-loading { position: relative; color: transparent !important; pointer-events: none; }
.app-btn-loading::after {
  content: ''; position: absolute; inset: 0; margin: auto;
  width: 16px; height: 16px; border: 2px solid transparent;
  border-top-color: currentColor; border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* Button — block (full width) */
.app-btn-block { width: 100%; display: flex; justify-content: center; }
```

- [ ] **Step 2: Add form enhancements**

```css
/* Checkbox & Radio — custom styled */
.app-checkbox, .app-radio { appearance: none; width: 18px; height: 18px; border: 2px solid var(--border-color); border-radius: var(--radius-sm); cursor: pointer; position: relative; transition: all 0.2s ease; }
.app-checkbox:checked { background: var(--brand-400); border-color: var(--brand-400); }
.app-checkbox:checked::after { content: ''; position: absolute; left: 5px; top: 2px; width: 5px; height: 9px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.app-radio { border-radius: 50%; }
.app-radio:checked { border-color: var(--brand-400); }
.app-radio:checked::after { content: ''; position: absolute; inset: 3px; background: var(--brand-400); border-radius: 50%; }

/* Input group — prefix/suffix */
.app-input-group { display: flex; align-items: stretch; }
.app-input-group .app-input { flex: 1; border-radius: 0; }
.app-input-group .app-input:first-child { border-radius: var(--radius-md) 0 0 var(--radius-md); }
.app-input-group .app-input:last-child { border-radius: 0 var(--radius-md) var(--radius-md) 0; }
.app-input-group .app-input-prefix,
.app-input-group .app-input-suffix {
  display: flex; align-items: center; padding: 0 12px;
  background: var(--surface-hover); border: 1px solid var(--border-color);
  font-size: var(--text-sm); color: var(--text-muted);
}
.app-input-group .app-input-prefix { border-radius: var(--radius-md) 0 0 var(--radius-md); border-right: none; }
.app-input-group .app-input-suffix { border-radius: 0 var(--radius-md) var(--radius-md) 0; border-left: none; }

/* Password input — show/hide toggle */
.app-input-password { position: relative; }
.app-input-password .app-input { padding-right: 40px; }
.app-input-password .password-toggle {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: none; border: none; cursor: pointer; color: var(--text-muted); padding: 4px;
}

/* Form row — side-by-side fields */
.app-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap-md); }
```

- [ ] **Step 3: Commit**

```bash
git add css/components.css
git commit -m "feat: add button variants, form enhancements (checkbox/radio/input-group/password)"
```

---

### Task 7: Add .app-toast Styles to components.css

**Files:**
- Modify: `css/components.css`

- [ ] **Step 1: Add toast notification styles**

```css
/* ===== Toast Notification ===== */
.app-toast-container {
  position: fixed; top: 16px; right: 16px; z-index: var(--z-toast);
  display: flex; flex-direction: column; gap: 8px; pointer-events: none;
}
.app-toast {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 16px; border-radius: var(--radius-md);
  background: var(--surface-raised); border: 1px solid var(--border-color);
  box-shadow: var(--shadow-toast); min-width: 280px; max-width: 420px;
  pointer-events: auto; animation: slide-left 0.3s var(--ease-out) forwards;
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.app-toast--removing { opacity: 0; transform: translateX(100%); }
.app-toast-icon { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.app-toast-body { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.app-toast-title { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--text-heading); }
.app-toast-content { font-size: var(--text-xs); color: var(--text-muted); }
.app-toast-action {
  font-size: var(--text-xs); font-weight: var(--font-semibold); color: var(--brand-400);
  background: none; border: none; cursor: pointer; padding: 2px 8px; flex-shrink: 0;
}
.app-toast-close {
  background: none; border: none; cursor: pointer; color: var(--text-muted);
  font-size: 16px; padding: 0; line-height: 1; flex-shrink: 0;
}

/* Toast — mascot variant */
.app-toast--mascot {
  background: linear-gradient(135deg, var(--surface-raised), color-mix(in oklch, var(--brand-100), transparent 70%));
  border-color: color-mix(in oklch, var(--brand-300), transparent 50%);
}
.app-toast--mascot .app-toast-icon { font-size: 22px; }

/* Toast — type variants */
.app-toast--success { border-left: 3px solid var(--success); }
.app-toast--error { border-left: 3px solid var(--danger); }
.app-toast--warning { border-left: 3px solid var(--warning); }
.app-toast--info { border-left: 3px solid var(--info); }
```

- [ ] **Step 2: Commit**

```bash
git add css/components.css
git commit -m "feat: add .app-toast styles with type and mascot variants"
```

---

### Task 8: Create toast.js — Unified Toast System

**Files:**
- Create: `js/toast.js`

- [ ] **Step 1: Write toast.js**

```javascript
/**
 * Toast — 全局通知系统
 * 统一业务通知和看板娘通知，共用底层引擎。
 *
 * Usage:
 *   Toast.show('保存成功', 'success')
 *   Toast.error('操作失败')
 *   Toast.mascot('小星提醒', '该休息啦~')
 */
const Toast = (() => {
  'use strict';

  let container = null;

  function ensureContainer() {
    if (!container || !container.parentNode) {
      container = document.createElement('div');
      container.className = 'app-toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  function createToast(title, content, opts = {}) {
    const { duration = 3000, actionLabel, actionCallback, type = 'info', variant = '' } = opts;
    const iconMap = { info: 'ℹ️', warning: '⚠️', success: '✅', error: '❌', tip: '💡' };

    const toast = document.createElement('div');
    toast.className = `app-toast app-toast--${type}${variant ? ' app-toast--' + variant : ''}`;

    toast.innerHTML = `
      <span class="app-toast-icon">${iconMap[type] || '💬'}</span>
      <div class="app-toast-body">
        <div class="app-toast-title">${escapeHTML(title)}</div>
        ${content ? `<div class="app-toast-content">${escapeHTML(content)}</div>` : ''}
      </div>
      ${actionLabel ? `<button class="app-toast-action">${escapeHTML(actionLabel)}</button>` : ''}
      <button class="app-toast-close">&times;</button>
    `;

    toast.querySelector('.app-toast-close').onclick = () => dismiss(toast);
    if (actionLabel && actionCallback) {
      toast.querySelector('.app-toast-action').onclick = () => { actionCallback(); dismiss(toast); };
    }

    ensureContainer().appendChild(toast);

    if (duration > 0) {
      toast._timer = setTimeout(() => dismiss(toast), duration);
    }

    return toast;
  }

  function dismiss(toast) {
    if (toast._timer) clearTimeout(toast._timer);
    toast.classList.add('app-toast--removing');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 400);
  }

  function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  // ---- Public API ----

  function show(title, type = 'info', opts = {}) {
    return createToast(title, '', { ...opts, type });
  }

  function info(title, opts = {}) { return show(title, 'info', opts); }
  function ok(title, opts = {}) { return show(title, 'success', opts); }
  function error(title, opts = {}) { return show(title, 'error', opts); }
  function warning(title, opts = {}) { return show(title, 'warning', opts); }

  function mascot(title, content, opts = {}) {
    return createToast(title, content, { ...opts, type: 'info', variant: 'mascot', duration: 5000 });
  }

  window.Toast = { show, info, error, warning, ok, mascot, dismiss };
  return window.Toast;
})();
```

- [ ] **Step 2: Commit**

```bash
git add js/toast.js
git commit -m "feat: add unified toast system — Toast.show/toast.error/toast.mascot"
```

---

### Task 9: Update mascot-core.js — Delegate to window.Toast

**Files:**
- Modify: `js/mascot-core.js`

- [ ] **Step 1: Replace inline toast code with Toast.mascot() calls**

In `js/mascot-core.js`, find the `showToast` function (lines 41-78). Replace the entire `showToast` and `dismissToast` functions with:

```javascript
  function showToast(title, content, opts = {}) {
    return window.Toast.mascot(title, content, opts);
  }

  function dismissToast(toast) {
    window.Toast.dismiss(toast);
  }
```

Also remove the `escapeHTML` function (lines 87-91) since it's now in toast.js.

- [ ] **Step 2: Commit**

```bash
git add js/mascot-core.js
git commit -m "refactor: delegate mascot toast to unified window.Toast.mascot()"
```

---

### Task 10: Enhance auth.js — Role Visibility + JWT Expiry Check

**Files:**
- Modify: `js/auth.js`

- [ ] **Step 1: Add JWT expiry check and role visibility scanner**

At the end of `js/auth.js` (before the final `return window.Auth;`), add:

```javascript
  /** Decode JWT payload to check expiration */
  function isTokenValid() {
    const token = getToken();
    if (!token) return false;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (!payload.exp) return true; // no exp claim, assume valid
      return Date.now() < payload.exp * 1000;
    } catch (e) {
      return false;
    }
  }

  /** Check token on load — if expiring soon, try refresh */
  function checkTokenOnLoad() {
    const token = getToken();
    if (!token) return;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp && (payload.exp * 1000 - Date.now()) < 5 * 60 * 1000) {
        fetchMe().catch(() => {}); // silent attempt to refresh
      }
    } catch (e) {}
  }

  /** Scan DOM for data-auth-role and show/hide elements */
  function applyRoleVisibility() {
    const role = me ? me.role : 'guest';
    document.querySelectorAll('[data-auth-role]').forEach(el => {
      const required = el.getAttribute('data-auth-role');
      if (required === 'user') {
        el.style.display = role !== 'guest' ? '' : 'none';
      } else if (required === 'guest') {
        el.style.display = role === 'guest' ? '' : 'none';
      } else {
        el.style.display = role === required ? '' : 'none';
      }
    });
  }

  // Apply role visibility after fetchMe completes
  const originalFetchMe = fetchMe;
  fetchMe = async function() {
    const result = await originalFetchMe();
    applyRoleVisibility();
    return result;
  };

  // Run on page load
  checkTokenOnLoad();
  applyRoleVisibility();
```

Update the public API object to include the new methods:

```javascript
  window.Auth = {
    get me() { return me; },
    getToken,
    setToken,
    fetchMe,
    logout,
    isTeacher,
    isStudent,
    isAdmin,
    isTokenValid,
    applyRoleVisibility,
  };
```

- [ ] **Step 2: Commit**

```bash
git add js/auth.js
git commit -m "feat: add JWT expiry check and data-auth-role visibility system"
```

---

### Task 11: Enhance theme.js — Import/Export + Token Editor + Transition

**Files:**
- Modify: `js/theme.js`

- [ ] **Step 1: Add theme JSON export function**

Inside theme.js, add to the public API (before the closing `window.StarTheme = {`):

```javascript
  function exportTheme(themeId) {
    var info = getThemeInfo(themeId);
    var primitives = {};
    if (PRESETS[themeId]) {
      // For presets, capture current computed primitives
      var root = document.documentElement;
      for (var i = 0; i < PRIMITIVE_KEYS.length; i++) {
        var k = PRIMITIVE_KEYS[i];
        var val = getComputedStyle(root).getPropertyValue('--' + k).trim();
        if (val) primitives[k] = val;
      }
    } else {
      for (var i = 0; i < customThemes.length; i++) {
        if (customThemes[i].id === themeId) {
          primitives = customThemes[i].primitives;
          break;
        }
      }
    }
    var exportData = {
      version: 1,
      type: 'starlearn-theme',
      theme: { name: info.name, mode: info.mode, primitives: primitives }
    };
    var blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'starlearn-theme-' + themeId + '.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  function importTheme(fileInput) {
    var file = fileInput.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
      try {
        var data = JSON.parse(e.target.result);
        if (data.type !== 'starlearn-theme' || !data.theme || !data.theme.primitives) {
          window.Toast && Toast.error('无效的主题文件格式');
          return;
        }
        // Dedup by name
        var exists = customThemes.some(function(t) { return t.name === data.theme.name; });
        if (exists) {
          window.Toast && Toast.warning('同名主题已存在，跳过导入');
          return;
        }
        var id = createCustomTheme(data.theme.name, data.theme.mode, data.theme.primitives);
        window.Toast && Toast.ok('主题 "' + data.theme.name + '" 导入成功');
      } catch (err) {
        window.Toast && Toast.error('主题文件解析失败');
      }
    };
    reader.readAsText(file);
  }
```

- [ ] **Step 2: Add theme transition animation support**

In the `applyTheme` function, add transition attribute before setting theme:

```javascript
  function applyTheme(themeId) {
    // Trigger crossfade
    document.documentElement.setAttribute('data-theme-transitioning', 'true');
    document.documentElement.addEventListener('transitionend', function onEnd() {
      document.documentElement.removeAttribute('data-theme-transitioning');
      document.documentElement.removeEventListener('transitionend', onEnd);
    }, { once: true });
    // Fallback: remove after 500ms if no transitionend
    setTimeout(function() {
      document.documentElement.removeAttribute('data-theme-transitioning');
    }, 500);

    state.theme = themeId;
    var info = getThemeInfo(themeId);
    state.mode = info.mode;
    document.documentElement.setAttribute('data-theme', themeId);
    document.body.classList.toggle('light-theme', state.mode === 'light');

    if (!PRESETS[themeId]) {
      for (var i = 0; i < customThemes.length; i++) {
        if (customThemes[i].id === themeId) {
          applyCustomThemePrimitives(customThemes[i].primitives);
          break;
        }
      }
    } else {
      clearCustomThemePrimitives();
    }
  }
```

- [ ] **Step 3: Add import/export buttons to the theme modal**

In `openThemeModal()`, find the actions section (around line 730). After the `advancedLink` element, add:

```javascript
    // Import button
    var importInput = document.createElement('input');
    importInput.type = 'file';
    importInput.accept = '.json';
    importInput.style.display = 'none';
    importInput.addEventListener('change', function() { importTheme(importInput); });

    var importBtn = document.createElement('button');
    importBtn.className = 'tsm-restore-btn';
    importBtn.textContent = '导入主题 ↑';
    importBtn.style.marginLeft = '8px';
    importBtn.addEventListener('click', function() { importInput.click(); });

    var exportBtn = document.createElement('button');
    exportBtn.className = 'tsm-restore-btn';
    exportBtn.textContent = '导出当前主题 ↓';
    exportBtn.style.marginLeft = '8px';
    exportBtn.addEventListener('click', function() { exportTheme(state.theme); });

    actions.appendChild(importBtn);
    actions.appendChild(exportBtn);
    actions.appendChild(importInput);
```

- [ ] **Step 4: Update public API with new methods**

```javascript
  window.StarTheme = {
    // ... existing methods ...
    exportTheme: exportTheme,
    importTheme: importTheme,
    // ... rest of existing methods ...
  };
```

- [ ] **Step 5: Commit**

```bash
git add js/theme.js
git commit -m "feat: add theme JSON import/export, crossfade transition, public API extensions"
```

---

### Task 12: Adapt mascot.css — Replace Hardcoded Colors with Tokens

**Files:**
- Modify: `css/mascot.css`

- [ ] **Step 1: Find and replace hardcoded colors**

Read `css/mascot.css`. Search for hardcoded colors like `#a78bfa`, `rgba(139,92,246,0.4)`, and similar purple/pink hex values that should follow the theme. Replace them:

- `#a78bfa` → `var(--brand-400)`
- `rgba(139,92,246,0.4)` → `color-mix(in oklch, var(--brand-400), transparent 60%)`
- Any `#8b5cf6` or similar → `var(--brand-500)`

Run a grep first to identify all hardcoded colors, then replace each instance.

- [ ] **Step 2: Commit**

```bash
git add css/mascot.css
git commit -m "refactor: replace hardcoded colors in mascot.css with design tokens"
```

---

### Task 13: Showcase — Login Page Transformation

**Files:**
- Modify: `html/login.html`

- [ ] **Step 1: Replace auth-card-inner with app-form-card**

In `html/login.html`, find `<div class="auth-card-inner animate-fade-in-up animate-delay-1" style="position:relative">` (line 226). Replace with:

```html
<div class="app-form-card scale-in" style="position:relative; max-width:420px; margin:0 auto;">
```

- [ ] **Step 2: Update form fields to use app-input**

Replace `<input x-model="form.username" class="auth-field" ...>` with:

```html
<input x-model="form.username" class="app-input" style="width:100%;margin-bottom:12px"
       placeholder="输入用户名" @keydown.enter="doLogin()"
       autocomplete="username">
```

Replace `<input x-model="form.password" class="auth-field" type="password" ...>` with:

```html
<input x-model="form.password" class="app-input" type="password" style="width:100%;margin-bottom:16px"
       placeholder="输入密码" @keydown.enter="doLogin()"
       autocomplete="current-password">
```

- [ ] **Step 3: Update button to app-btn-primary.app-btn-block**

Replace `<button @click="doLogin()" :disabled="loading" class="btn-primary-auth" ...>` with:

```html
<button @click="doLogin()" :disabled="loading"
        class="app-btn-primary app-btn-block"
        x-text="loading ? '登录中...' : '登 录'">
  登 录
</button>
```

- [ ] **Step 4: Update footer link to app-btn-link**

Replace `<a href="/register.html">注册新账号</a>` with:

```html
<a href="/register.html" class="app-btn-link">注册新账号</a>
```

- [ ] **Step 5: Add toast.js include in <head>**

After the theme.js script tag, add:

```html
<script src="/js/toast.js"></script>
```

- [ ] **Step 6: Use Toast.error for login errors**

In `js/pages/login.js`, find where `error` is set and add parallel Toast call. In the `doLogin` function's error handler, add:

```javascript
window.Toast && Toast.error(this.error || '登录失败');
```

- [ ] **Step 7: Commit**

```bash
git add html/login.html js/pages/login.js
git commit -m "refactor: migrate login page to app-form-card, app-input, toast error"
```

---

### Task 14: Showcase — Hub Page Card Migration

**Files:**
- Modify: `html/hub.html`

- [ ] **Step 1: Add toast.js script include**

After the theme.js script tag in `<head>`, add:

```html
<script src="/js/toast.js"></script>
```

- [ ] **Step 2: Add stagger animation classes to feature grid**

Find `<div class="feature-grid" id="feature-grid">` (line 645). Change to:

```html
<div class="feature-grid stagger" id="feature-grid" style="--stagger-delay:60ms;">
```

Add `fade-up` class to each `feature-card`:

Each `<a href="..." class="feature-card hub-card func-card" ...>` should become:

```html
<a href="/index.html" class="feature-card hub-card func-card app-action-card fade-up" data-category="core">
```

Repeat for all 8 feature cards.

- [ ] **Step 3: Add stagger to hero stat capsules**

Find `<div class="hero-stats-row" id="hero-stats">` (line 554). Change to:

```html
<div class="hero-stats-row stagger" id="hero-stats" style="--stagger-delay:100ms;">
```

Add `fade-up` class to each `hero-stat-capsule`:

```html
<div class="hero-stat-capsule study fade-up">...
<div class="hero-stat-capsule streak fade-up">...
<div class="hero-stat-capsule mastery fade-up">...
<div class="hero-stat-capsule level fade-up">...
```

- [ ] **Step 4: Add stagger to content grid**

Find `<div class="content-grid" id="content-grid">` (line 874). Change to:

```html
<div class="content-grid stagger" id="content-grid" style="--stagger-delay:80ms;">
```

Add `slide-up` class to each `content-card`:

```html
<a href="/courses.html" class="content-card hub-card content-card-compact app-content-card slide-up">
```

Repeat for all content cards in the grid.

- [ ] **Step 5: Add fade-in to section entries**

For each `<section class="overview-section">` or `<section class="panel-section">`, add `fade-in` class to the first child card.

- [ ] **Step 6: Commit**

```bash
git add html/hub.html
git commit -m "refactor: add stagger animations and card classes to Hub page"
```

---

### Task 15: Showcase — Personal Page Transformation

**Files:**
- Modify: `html/personal.html`

- [ ] **Step 1: Add toast.js script include**

After theme.js in `<head>`, add:

```html
<script src="/js/toast.js"></script>
```

- [ ] **Step 2: Migrate stat cards**

Find all `stat-card` or `metric-panel` or `cockpit-stat-card` elements. For each, add `app-stat-card glass` class alongside or replacing the old class.

- [ ] **Step 3: Migrate chart containers**

Find all `chart-card` elements. Add `app-chart-card glass` class.

- [ ] **Step 4: Replace custom grid with app-grid-3**

Find the main stat row and add `app-grid-3 app-gap-md` to the container.

- [ ] **Step 5: Add number counting animation**

Add this small script at the bottom of the page (before `</body>`):

```javascript
<script>
// Number counting animation for stat values
document.querySelectorAll('.app-stat-value[data-count]').forEach(el => {
  const target = parseInt(el.getAttribute('data-count'));
  const duration = 800;
  const start = performance.now();
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    el.textContent = Math.round(target * eased).toLocaleString();
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
});
</script>
```

- [ ] **Step 6: Commit**

```bash
git add html/personal.html
git commit -m "refactor: migrate Personal page — stat cards, chart cards, number animation"
```

---

### Task 16: Showcase — Teacher Dashboard Transformation

**Files:**
- Modify: `html/teacher-dashboard.html`

- [ ] **Step 1: Add toast.js script include**

After theme.js in `<head>`, add:

```html
<script src="/js/toast.js"></script>
```

- [ ] **Step 2: Migrate stat cards with prism variant**

Find all `teacher-stat` or `dashboard-stat` elements. Add class `app-stat-card prism`.

Example: if original is `<div class="teacher-stat">`, change to `<div class="teacher-stat app-stat-card prism">`.

- [ ] **Step 3: Migrate content cards with prism variant**

Find all `class-card` or `exam-card` or `resource-card` elements. Add `app-content-card prism` class.

- [ ] **Step 4: Migrate chart cards with prism variant**

Find all `chart-card` elements. Add `app-chart-card prism` class.

- [ ] **Step 5: Migrate action cards**

Find quick action buttons/cards. Add `app-action-card prism interactive` class.

- [ ] **Step 6: Ensure Prism CSS is in components.css**

Verify that the `.app-card-prism::before` clip-path rule from Task 5 Step 7 is present. If not, add it.

- [ ] **Step 7: Commit**

```bash
git add html/teacher-dashboard.html
git commit -m "refactor: migrate Teacher Dashboard — prism card variants, unified classes"
```

---

### Task 17: Showcase — Settings Page Transformation

**Files:**
- Modify: `html/settings.html`

- [ ] **Step 1: Add toast.js script include**

After theme.js in `<head>`, add:

```html
<script src="/js/toast.js"></script>
```

- [ ] **Step 2: Wrap setting groups in app-form-card**

Find each major settings section and wrap in:

```html
<div class="app-form-card">
  <div class="app-card-header"><h2>分组标题</h2></div>
  <!-- existing settings content -->
</div>
```

- [ ] **Step 3: Replace custom toggles with app-toggle**

Ensure toggle switches use the existing `.app-toggle` class from components.css.

- [ ] **Step 4: Add import/export theme buttons**

Add to the theme settings section:

```html
<button class="app-btn-outline" onclick="StarTheme.exportTheme(StarTheme.getState().theme)">导出当前主题 ↓</button>
<button class="app-btn-outline" onclick="document.getElementById('importFileInput').click()">导入主题 ↑</button>
<input type="file" id="importFileInput" accept=".json" style="display:none" onchange="StarTheme.importTheme(this)">
```

- [ ] **Step 5: Commit**

```bash
git add html/settings.html
git commit -m "refactor: migrate Settings page — form cards, toggle, import/export buttons"
```

---

### Task 18: Wave 1 Rollout — Register, Courses, Calendar, Progress, Assessment, Video

**Files:**
- Modify: `html/register.html`, `html/courses.html`, `html/calendar.html`, `html/progress.html`, `html/assessment.html`, `html/video-player.html`

- [ ] **Step 1: Register page — mirror Login changes**

Apply the same `app-form-card` + `app-input` + `app-btn-primary.app-btn-block` pattern as in Task 13. Add toast.js include.

- [ ] **Step 2: Courses page — class name swap + stagger**

Add toast.js include. Change all `content-card`, `resource-card` to `app-content-card`. Add `stagger` container + `slide-up` or `fade-up` on children.

- [ ] **Step 3: Calendar page — class name swap**

Add toast.js include. Change `calendar-stat` to `app-stat-card`. Change `badge-card` to `app-chart-card`. Add `fade-in` on sections.

- [ ] **Step 4: Progress page — class name swap**

Add toast.js include. Change `progress-stat` to `app-stat-card`. Change `chart-card` to `app-chart-card`. Add `stagger fade-up` on stat row.

- [ ] **Step 5: Assessment page — class name swap**

Add toast.js include. Change `dimension-card` to `app-action-card`. Change `form-card` to `app-form-card`. Add `fade-in` on sections.

- [ ] **Step 6: Video page — class name swap**

Add toast.js include. Change `video-info-panel` and `player-shell` to `app-content-card`. Add `slide-up` on info panel.

- [ ] **Step 7: Commit**

```bash
git add html/register.html html/courses.html html/calendar.html html/progress.html html/assessment.html html/video-player.html
git commit -m "refactor: Wave 1 rollout — 6 pages class migration + stagger animations"
```

---

### Task 19: Wave 2 Rollout — Code, Socratic, Data-dashboard, Flow-meter, Plant, Teacher-class, Teacher-resources

**Files:**
- Modify: `html/code.html`, `html/socratic-ai.html`, `html/data-dashboard.html`, `html/flow-meter.html`, `html/plant.html`, `html/teacher-class.html`, `html/teacher-resources.html`

- [ ] **Step 1: Code page**

Add toast.js include. Change `brief-card`, `compact-card` to `app-action-card.compact`. Preserve editor container. Add `fade-in` on panels.

- [ ] **Step 2: Socratic page**

Add toast.js include. Change `content-card` to `app-content-card`. Preserve chat dialogue area. Add `fade-in` on sections.

- [ ] **Step 3: Data-dashboard page**

Add toast.js include. Change `dashboard-stat` to `app-stat-card.glass`. Change all `chart-card` (7 variants) to `app-chart-card`. Preserve ECharts containers. Add `stagger fade-up` on stat row.

- [ ] **Step 4: Flow-meter page**

Add toast.js include. Change `flow-stat` to `app-stat-card`. Change `flow-card` to `app-chart-card`. Preserve canvas waveform. Add `fade-in`.

- [ ] **Step 5: Plant page**

Add toast.js include. Change `plant-info-panel` to `app-content-card`. Change `plant-detail-card` to `app-chart-card`. Preserve care animations. Add `slide-up`.

- [ ] **Step 6: Teacher-class page**

Add toast.js include. Change `class-card`, `exam-card` to `app-content-card.prism`. Add stagger animation on card lists.

- [ ] **Step 7: Teacher-resources page**

Add toast.js include. Change `resource-card` to `app-content-card`. Add `stagger slide-up`.

- [ ] **Step 8: Commit**

```bash
git add html/code.html html/socratic-ai.html html/data-dashboard.html html/flow-meter.html html/plant.html html/teacher-class.html html/teacher-resources.html
git commit -m "refactor: Wave 2 rollout — 7 pages class migration, preserve special containers"
```

---

### Task 20: Wave 3 Rollout — Remaining Pages + Mascot Token Finish

**Files:**
- Modify: `html/gen-preview.html`, `html/teacher-exams.html`, `html/course-detail.html`, plus any remaining pages that aren't excluded
- Modify: `css/mascot.css` (final pass)

- [ ] **Step 1: Gen-preview, Teacher-exams, Course-detail**

Add toast.js include to each. Apply class name swaps per the mapping table:
- `main-card` → `app-chart-card`
- `exam-card` → `app-content-card.prism`
- `content-card` → `app-content-card`

Add `fade-in` or `slide-up` as appropriate.

- [ ] **Step 2: Any remaining pages**

Grep for any other .html files not yet processed (excluding index.html and classroom.html). Apply:
1. Add `<script src="/js/toast.js"></script>` after theme.js
2. Swap legacy class names per the mapping table
3. Add at least one entry animation class
4. Replace inline grid/flex with `.app-grid-*` / `.app-flex-*` utilities where applicable

- [ ] **Step 3: Final mascot.css token pass**

Verify all hardcoded colors in mascot.css have been replaced. Run:

```bash
grep -nE '#[0-9a-fA-F]{3,6}|rgba?\([0-9,.\s]+\)' css/mascot.css
```

Replace any remaining hardcoded non-SVG colors with token references.

- [ ] **Step 4: Commit**

```bash
git add html/gen-preview.html html/teacher-exams.html html/course-detail.html css/mascot.css
git commit -m "refactor: Wave 3 rollout — remaining pages + final mascot token pass"
```

---

### Task 21: Final Verification

**Files:**
- All modified files

- [ ] **Step 1: Verify no broken CSS variable references**

```bash
grep -rn 'var(--' css/ | grep -v 'tokens.css' | head -30
```

Ensure all referenced variables exist in tokens.css.

- [ ] **Step 2: Verify toast.js loaded on all pages**

```bash
grep -l 'toast.js' html/*.html | wc -l
```

Compare against total page count (excluding index.html, classroom.html).

- [ ] **Step 3: Test light/dark mode on 3 key pages**

Open Login, Hub, and Teacher-dashboard in browser. Toggle light/dark mode. Verify:
- Colors change smoothly
- No "flash of wrong theme"
- Cards remain readable

- [ ] **Step 4: Test theme switch**

On Hub page, open theme modal (gear icon). Switch between 3 different themes. Verify:
- Crossfade transition works (0.4s)
- All cards respect new theme
- No layout shifts

- [ ] **Step 5: Test toast notifications**

On any page, open browser console and run:

```javascript
Toast.show('测试成功消息', 'success')
Toast.error('测试错误消息')
Toast.warning('测试警告消息')
Toast.mascot('小星', '该休息啦~')
```

Verify all 4 toasts appear stacked, auto-dismiss, and mascot variant has bubble style.

- [ ] **Step 6: Test role visibility**

On a page with `data-auth-role` attributes, log in as different roles and verify elements show/hide correctly.

- [ ] **Step 7: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final verification fixes"
```
