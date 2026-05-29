# Frontend Design Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove AI-generated aesthetic from 6 core pages by rewriting design tokens, themes, and component styles with a warm academy look.

**Architecture:** Two-phase approach — (1) rewrite the token/theme layer in index.css + hub.css so all pages inherit new values, (2) page-by-page polish for component-specific hardcoded colors. `theme.js` updated for new theme names. All old neon/glass/spring variables removed.

**Tech Stack:** Vanilla CSS custom properties, vanilla JS theme system, Tailwind CDN (unchanged)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `css/index.css` | **Modify** lines 1-230 | Rewrite all 7 theme blocks → 3 themes (warm-morning, study-night, starry-night). Keep rest of file (10,900+ lines of component styles) — they reference variables that now have new values |
| `css/hub.css` | **Modify** lines 1-200 | Rewrite `:root` and `[data-theme="dark"]` blocks → new tokens + dark variant. Remove `--neon-*` and `--glow-*` variables |
| `js/theme.js` | **Modify** | Change default theme, update `LIGHT_THEMES`, add debug helper |
| `css/loading.css` | **Modify** | Simplify spinner (keep 3D for first-load path, add simple spinner for secondary loads) |
| `css/courses.css` | **Modify** | Replace hardcoded gradient/neon values with new tokens |
| `css/course-learn.css` | **Modify** | Replace hardcoded color values |
| `css/video-player.css` | **Modify** | Replace neon references |
| `css/personal.css` | **Modify** | Replace glass/neon references |
| `css/settings.css` | **Modify** | Replace glass/neon references |
| `html/index.html` | **Modify** | Update default `data-theme` |
| `html/personal.html` | **Modify** | Update default `data-theme` |

---

### Task 1: Rewrite index.css theme blocks — 3 new themes

**Files:**
- Modify: `css/index.css:1-230`

- [ ] **Step 1: Replace the entire theme block (lines 1-230)**

Delete all 7 old themes (`:root,[data-theme="ocean"]` through `[data-theme="ocean-light"]`) and replace with 3 new themes. The existing component styles from line ~231 onward are unchanged — they reference variables by name, the values just change.

Replace lines 1-230 with:

```css
/* ============================================
   Design Tokens v2 — Warm Academy
   ============================================ */

/* ---- Default Theme: 日出晨光 ---- */
:root, [data-theme="warm-morning"] {
    /* Brand — warm orange */
    --brand-50: #fff7ed; --brand-100: #ffedd5; --brand-200: #fed7aa;
    --brand-300: #fdba74; --brand-400: #fb923c; --brand-500: #f97316;
    --brand-600: #ea580c; --brand-700: #c2410c; --brand-800: #9a3412; --brand-900: #7c2d12;

    /* Neutral — warm gray */
    --neutral-50: #fafaf9; --neutral-100: #f5f4f0; --neutral-200: #e7e5e0;
    --neutral-300: #d6d3cc; --neutral-400: #a8a59e; --neutral-500: #78756e;
    --neutral-600: #57544e; --neutral-700: #44413c; --neutral-800: #292724; --neutral-900: #1c1917;

    /* Semantic */
    --success: #16a34a; --success-bg: #f0fdf4;
    --warning: #d97706; --warning-bg: #fffbeb;
    --danger: #dc2626;  --danger-bg: #fef2f2;
    --info: #2563eb;    --info-bg: #eff6ff;

    /* Accent — decoration only */
    --accent-amber: #f59e0b; --accent-rose: #f43f5e;
    --accent-teal: #14b8a6;  --accent-violet: #8b5cf6;

    /* Surfaces */
    --surface-page: #fafaf9; --surface-card: #ffffff;
    --surface-hover: #f5f4f0; --surface-pressed: #e7e5e0;
    --surface-overlay: rgba(28, 25, 23, 0.4);
    --surface-nav: rgba(250, 250, 249, 0.85);

    /* Shadows */
    --shadow-xs: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.08);
    --shadow-lg: 0 12px 40px rgba(0,0,0,0.12);

    /* Text */
    --text-heading: #1c1917; --text-body: #44413c;
    --text-muted: #78756e; --text-placeholder: #a8a59e;
    --text-link: #ea580c; --text-on-brand: #ffffff;

    /* Radius */
    --radius-sm: 8px; --radius-md: 14px; --radius-lg: 20px; --radius-full: 9999px;

    /* Spacing */
    --space-xs: 4px; --space-sm: 8px; --space-md: 16px; --space-lg: 24px; --space-xl: 40px;

    /* Easing */
    --ease-out: cubic-bezier(0, 0, 0.2, 1);
    --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
    --ease-standard: 0.15s ease;

    /* Typography */
    --text-xs: 11px; --text-sm: 13px; --text-base: 15px;
    --text-lg: 18px; --text-xl: 22px; --text-2xl: 28px; --text-3xl: 36px;
    --font-normal: 400; --font-medium: 500; --font-bold: 700;

    /* Theme name */
    --theme-name: "日出晨光";

    /* ===== LEGACY MAPPINGS — keep old var names working ===== */
    --primary: var(--brand-500);
    --primary-light: var(--brand-400);
    --primary-dark: var(--brand-600);
    --primary-50: var(--brand-50);
    --primary-100: var(--brand-100);
    --primary-200: var(--brand-200);
    --primary-300: var(--brand-300);
    --accent: var(--brand-400);
    --accent-hover: var(--brand-600);
    --sidebar-bg: var(--neutral-50);
    --sidebar-header: var(--neutral-100);
    --chat-bg: var(--surface-page);
    --msg-bot-bg: var(--surface-card);
    --msg-bot-border: var(--neutral-200);
    --radar-fill: rgba(249, 115, 22, 0.1);
    --radar-stroke: var(--brand-400);
    --glass-bg: var(--surface-card);
    --dropdown-bg: var(--surface-card);
    --glass-border: var(--neutral-200);
    --text-main: var(--text-heading);
    --glass-shadow: rgba(0,0,0,0.04);
    --glass-blur: 0px;
    --mesh-1: var(--neutral-100);
    --mesh-2: var(--neutral-50);
    --mesh-3: var(--neutral-200);
    --mesh-4: var(--neutral-100);
    --mesh-accent-1: rgba(249, 115, 22, 0.04);
    --mesh-accent-2: rgba(245, 158, 11, 0.03);
    --text-primary: var(--text-heading);
    --text-secondary: var(--text-body);
    --text-tertiary: var(--text-muted);
    --text-on-accent: var(--text-on-brand);
    --surface-glass: var(--surface-card);
    --surface-glass-hover: var(--surface-hover);
    --border-glass: var(--neutral-200);
    --border-glass-hover: var(--brand-300);
    --accent-bg: rgba(249, 115, 22, 0.1);
    --accent-border: rgba(249, 115, 22, 0.2);
    --bg-card: var(--surface-card);
    --border-color: var(--neutral-200);
    --hover-bg: var(--surface-hover);
    --input-bg: var(--neutral-100);
    --btn-secondary-bg: var(--neutral-100);
    --btn-secondary-hover: var(--neutral-200);
    --transition-fast: var(--ease-standard);
    --transition-base: 0.25s var(--ease-out);
    --transition-slow: 0.4s var(--ease-out);
    --transition-spring: 0.3s var(--ease-out);
    --shadow-glass: var(--shadow-xs);
}

/* ---- Dark Theme: 深夜书房 ---- */
[data-theme="study-night"] {
    --neutral-50: #1a1d23; --neutral-100: #21252b; --neutral-200: #2c313a;
    --neutral-300: #3a3f4a; --neutral-400: #5c6370; --neutral-500: #8b9298;
    --neutral-600: #b4bcc4; --neutral-700: #d1d7de; --neutral-800: #e8ecf1; --neutral-900: #f5f7fa;

    --brand-500: #fb923c; --brand-600: #fdba74;

    --surface-page: #1a1d23; --surface-card: #21252b;
    --surface-hover: #2c313a; --surface-pressed: #3a3f4a;
    --surface-overlay: rgba(0, 0, 0, 0.6);
    --surface-nav: rgba(26, 29, 35, 0.85);

    --shadow-xs: 0 1px 2px rgba(0,0,0,0.2);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.4);
    --shadow-lg: 0 12px 40px rgba(0,0,0,0.5);

    --text-heading: #e8ecf1; --text-body: #d1d7de;
    --text-muted: #8b9298; --text-placeholder: #5c6370;
    --text-link: #fb923c; --text-on-brand: #1c1917;

    --theme-name: "深夜书房";

    /* Legacy mappings — dark values */
    --primary: var(--brand-500);
    --primary-light: var(--brand-400);
    --primary-dark: var(--brand-600);
    --primary-50: var(--neutral-100);
    --primary-100: var(--neutral-200);
    --primary-200: var(--neutral-300);
    --primary-300: var(--neutral-400);
    --accent: var(--brand-400);
    --accent-hover: var(--brand-600);
    --sidebar-bg: var(--neutral-50);
    --sidebar-header: var(--neutral-100);
    --chat-bg: var(--surface-page);
    --msg-bot-bg: var(--surface-card);
    --msg-bot-border: var(--neutral-200);
    --radar-fill: rgba(251, 146, 60, 0.1);
    --radar-stroke: var(--brand-400);
    --glass-bg: var(--surface-card);
    --dropdown-bg: var(--surface-card);
    --glass-border: var(--neutral-200);
    --text-main: var(--text-heading);
    --glass-shadow: rgba(0,0,0,0.2);
    --glass-blur: 0px;
    --mesh-1: var(--neutral-50);
    --mesh-2: var(--neutral-100);
    --mesh-3: var(--neutral-50);
    --mesh-4: var(--neutral-100);
    --mesh-accent-1: rgba(251, 146, 60, 0.06);
    --mesh-accent-2: rgba(245, 158, 11, 0.04);
    --text-primary: var(--text-heading);
    --text-secondary: var(--text-body);
    --text-tertiary: var(--text-muted);
    --text-on-accent: var(--text-on-brand);
    --surface-glass: var(--surface-card);
    --surface-glass-hover: var(--surface-hover);
    --border-glass: var(--neutral-200);
    --border-glass-hover: var(--brand-300);
    --accent-bg: rgba(251, 146, 60, 0.1);
    --accent-border: rgba(251, 146, 60, 0.2);
    --bg-card: var(--surface-card);
    --border-color: var(--neutral-200);
    --hover-bg: var(--surface-hover);
    --input-bg: var(--neutral-100);
    --btn-secondary-bg: var(--neutral-100);
    --btn-secondary-hover: var(--neutral-200);
    --transition-fast: var(--ease-standard);
    --transition-base: 0.25s var(--ease-out);
    --transition-slow: 0.4s var(--ease-out);
    --transition-spring: 0.3s var(--ease-out);
    --shadow-glass: var(--shadow-xs);
}

/* ---- Dark Theme: 星夜 (gold + violet accents) ---- */
[data-theme="starry-night"] {
    --neutral-50: #0f1117; --neutral-100: #161922; --neutral-200: #1e2230;
    --neutral-300: #2a2f3d; --neutral-400: #5c6370; --neutral-500: #8b9298;
    --neutral-600: #b4bcc4; --neutral-700: #d1d7de; --neutral-800: #e8ecf1; --neutral-900: #f5f7fa;

    --brand-500: #fbbf24; --brand-600: #fcd34d;

    --accent-amber: #fbbf24; --accent-violet: #a78bfa;

    --surface-page: #0f1117; --surface-card: #161922;
    --surface-hover: #1e2230; --surface-pressed: #2a2f3d;
    --surface-overlay: rgba(0, 0, 0, 0.7);
    --surface-nav: rgba(15, 17, 23, 0.85);

    --shadow-xs: 0 1px 2px rgba(0,0,0,0.3);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.4);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.5);
    --shadow-lg: 0 12px 40px rgba(0,0,0,0.6);

    --text-heading: #f5f7fa; --text-body: #d1d7de;
    --text-muted: #8b9298; --text-placeholder: #5c6370;
    --text-link: #fbbf24; --text-on-brand: #0f1117;

    --theme-name: "星夜";

    /* Legacy mappings */
    --primary: var(--brand-500);
    --primary-light: var(--brand-400);
    --primary-dark: var(--brand-600);
    --primary-50: var(--neutral-100);
    --primary-100: var(--neutral-200);
    --primary-200: var(--neutral-300);
    --primary-300: var(--neutral-400);
    --accent: var(--brand-400);
    --accent-hover: var(--brand-600);
    --sidebar-bg: var(--neutral-50);
    --sidebar-header: var(--neutral-100);
    --chat-bg: var(--surface-page);
    --msg-bot-bg: var(--surface-card);
    --msg-bot-border: var(--neutral-200);
    --radar-fill: rgba(251, 191, 36, 0.08);
    --radar-stroke: var(--brand-400);
    --glass-bg: var(--surface-card);
    --dropdown-bg: var(--surface-card);
    --glass-border: var(--neutral-200);
    --text-main: var(--text-heading);
    --glass-shadow: rgba(0,0,0,0.3);
    --glass-blur: 0px;
    --mesh-1: var(--neutral-50);
    --mesh-2: var(--neutral-100);
    --mesh-3: var(--neutral-50);
    --mesh-4: var(--neutral-100);
    --mesh-accent-1: rgba(251, 191, 36, 0.04);
    --mesh-accent-2: rgba(167, 139, 250, 0.03);
    --text-primary: var(--text-heading);
    --text-secondary: var(--text-body);
    --text-tertiary: var(--text-muted);
    --text-on-accent: var(--text-on-brand);
    --surface-glass: var(--surface-card);
    --surface-glass-hover: var(--surface-hover);
    --border-glass: var(--neutral-200);
    --border-glass-hover: var(--brand-300);
    --accent-bg: rgba(251, 191, 36, 0.1);
    --accent-border: rgba(251, 191, 36, 0.2);
    --bg-card: var(--surface-card);
    --border-color: var(--neutral-200);
    --hover-bg: var(--surface-hover);
    --input-bg: var(--neutral-100);
    --btn-secondary-bg: var(--neutral-100);
    --btn-secondary-hover: var(--neutral-200);
    --transition-fast: var(--ease-standard);
    --transition-base: 0.25s var(--ease-out);
    --transition-slow: 0.4s var(--ease-out);
    --transition-spring: 0.3s var(--ease-out);
    --shadow-glass: var(--shadow-xs);
}
```

- [ ] **Step 2: Verify no compile errors — check that the CSS is valid**

Run: `python -c "with open('css/index.css') as f: content = f.read(); print(f'OK: {len(content)} chars, starts with: {content[:80]}')"`

- [ ] **Step 3: Commit**

```bash
git add css/index.css
git commit -m "feat: rewrite index.css theme blocks with warm academy design tokens"
```

---

### Task 2: Rewrite hub.css root variables — remove neon, unify with new tokens

**Files:**
- Modify: `css/hub.css:1-200`

- [ ] **Step 1: Replace hub.css `:root` block (lines 1-108)**

Delete all old `:root` variables (including `--neon-*`, `--glow-*`, `--gradient-*`, `--bg-card-gradient` etc.) and replace with a minimal block that reuses the index.css tokens via inheritance. The dark block (lines 110-174) also gets replaced.

Replace lines 1-174 with:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');

/* hub.css — inherits design tokens from index.css.
   Only defines hub-specific overrides and component styles. */

:root {
    /* Hub-specific surface aliases — maps to shared tokens */
    --bg-primary: var(--surface-page);
    --bg-secondary: var(--neutral-100);
    --bg-tertiary: var(--neutral-200);
    --bg-card: var(--surface-card);
    --bg-card-hover: var(--surface-hover);
    --bg-glass: var(--surface-card);
    --bg-glass-hover: var(--surface-hover);
    --bg-navbar: var(--surface-nav);
    --bg-sidebar: var(--neutral-50);
    --bg-overlay: var(--surface-overlay);

    /* Text */
    --text-primary: var(--text-heading);
    --text-secondary: var(--text-body);
    --text-tertiary: var(--text-muted);
    --text-inverse: #ffffff;

    /* Semantic */
    --color-success: var(--success);
    --color-success-bg: var(--success-bg);
    --color-warning: var(--warning);
    --color-warning-bg: var(--warning-bg);
    --color-danger: var(--danger);
    --color-danger-bg: var(--danger-bg);
    --color-info: var(--info);
    --color-info-bg: var(--info-bg);

    /* Contrast text */
    --text-on-primary: var(--text-heading);
    --text-on-secondary: var(--text-body);
    --text-on-accent: var(--text-on-brand);

    /* Borders */
    --border-primary: var(--neutral-300);
    --border-secondary: var(--neutral-200);
    --border-glass: var(--neutral-200);
    --border-accent: var(--brand-300);

    /* Shadows */
    --shadow-sm: var(--shadow-xs);
    --shadow-md: var(--shadow-sm);
    --shadow-lg: var(--shadow-md);
    --shadow-xl: var(--shadow-lg);

    /* Radius */
    --radius-sm: var(--radius-sm);
    --radius-md: var(--radius-md);
    --radius-lg: var(--radius-lg);
    --radius-xl: var(--radius-lg);
    --radius-full: var(--radius-full);

    /* Easing */
    --transition-fast: var(--ease-standard);
    --transition-normal: 0.3s var(--ease-out);
    --transition-slow: 0.5s var(--ease-out);

    /* Scrollbar */
    --scrollbar-thumb: var(--neutral-300);
    --scrollbar-thumb-hover: var(--neutral-400);
    --scrollbar-track: var(--neutral-100);

    /* Chart */
    --chart-grid: var(--neutral-200);
    --chart-axis: var(--neutral-500);
    --chart-label: var(--neutral-500);
    --chart-dot-fill: var(--surface-card);
    --chart-dot-stroke: var(--brand-500);

    /* Glass — nav only, all pages reference these */
    --glass-bg: var(--surface-nav);
    --glass-bg-hover: var(--surface-hover);
    --glass-border: var(--neutral-200);
    --glass-border-hover: var(--brand-300);
    --glass-highlight: rgba(255,255,255,0.1);
    --glass-shadow: rgba(0,0,0,0.04);
    --glass-blur: 12px;
    --glass-saturate: 100%;
    --ease-spring: var(--ease-out);
    --ease-smooth: var(--ease-out);
}

/* Dark overrides — when data-theme is study-night or starry-night */
[data-theme="study-night"] {
    --chart-dot-fill: var(--surface-card);
    --bg-primary: var(--surface-page);
    --bg-secondary: var(--neutral-100);
    --bg-card: var(--surface-card);
    --bg-navbar: var(--surface-nav);
    --border-glass: var(--neutral-200);
    --scrollbar-thumb: var(--neutral-400);
    --scrollbar-track: var(--neutral-100);
}

[data-theme="starry-night"] {
    --chart-dot-fill: var(--surface-card);
    --bg-primary: var(--surface-page);
    --bg-secondary: var(--neutral-100);
    --bg-card: var(--surface-card);
    --bg-navbar: var(--surface-nav);
    --border-glass: var(--neutral-200);
    --scrollbar-thumb: var(--neutral-400);
    --scrollbar-track: var(--neutral-100);
}
```

- [ ] **Step 2: Remove `--shadow-glow` references throughout hub.css**

Run grep to find remaining `--shadow-glow` and `--glow-` references:

```bash
grep -n 'shadow-glow\|glow-purple\|glow-blue\|glow-green\|glow-orange\|glow-pink\|neon-purple\|neon-blue\|neon-green\|neon-orange\|neon-pink\|neon-cyan\|gradient-primary\|bg-card-gradient\|bg-glass-gradient\|bg-accent-glow' css/hub.css
```

For each match found, replace inline with the equivalent new token:
- `var(--shadow-glow)` → `var(--shadow-md)`
- `var(--glow-purple)` → `rgba(249,115,22,0.1)` (warm orange glow instead of purple)
- `var(--glow-blue)` → `rgba(249,115,22,0.08)`
- `var(--glow-green)` → `rgba(20,184,166,0.08)`
- `var(--glow-orange)` → `rgba(249,115,22,0.1)`
- `var(--glow-pink)` → `rgba(244,63,94,0.08)`
- `var(--neon-purple)` → `var(--brand-500)`
- `var(--neon-blue)` → `var(--brand-400)`
- `var(--neon-green)` → `var(--accent-teal)`
- `var(--neon-orange)` → `var(--brand-500)`
- `var(--neon-pink)` → `var(--accent-rose)`
- `var(--neon-cyan)` → `var(--accent-teal)`
- `var(--gradient-primary)` → `linear-gradient(135deg, var(--brand-500), var(--accent-amber))`
- `var(--bg-card-gradient)` → `var(--surface-card)`
- `var(--bg-glass-gradient)` → `var(--surface-card)`
- `var(--bg-accent-glow)` → `none`

- [ ] **Step 3: Remove `--transition-spring` references in hub.css**

Run: `grep -n 'transition-spring\|ease-spring\|cubic-bezier(0.34, 1.56' css/hub.css`

Replace all occurrences:
- `var(--transition-spring)` → `var(--transition-normal)`
- `var(--ease-spring)` → `var(--ease-out)`
- `cubic-bezier(0.34, 1.56, 0.64, 1)` → `cubic-bezier(0, 0, 0.2, 1)`

- [ ] **Step 4: Commit**

```bash
git add css/hub.css
git commit -m "feat: rewrite hub.css tokens to inherit from index.css, remove neon/glow variables"
```

---

### Task 3: Update theme.js — new theme names, new default

**Files:**
- Modify: `js/theme.js`

- [ ] **Step 1: Change default theme and light themes list**

Edit `js/theme.js`:

Line 14: Change `DEFAULT_THEME`:
```js
var DEFAULT_THEME = 'warm-morning';
```

Line 26: Change `LIGHT_THEMES`:
```js
var LIGHT_THEMES = ['warm-morning'];
```

Line 128 (in `applyTheme`): Remove sakura check — sakura theme no longer exists:
```js
// Delete lines 127-131 (the sakura-falling check), replace with a no-op:
// (sakura particles removed — theme no longer exists)
```

Lines 144-148 (in `toggleTheme`): Update toggle logic:
```js
var current = state.theme;
var next;
if (current === 'warm-morning') {
  next = 'study-night';
} else if (current === 'study-night') {
  next = 'starry-night';
} else {
  next = 'warm-morning';
}
```

Lines 355-359 (in modal confirm): Update mode toggle logic:
```js
if (mode === 'light' && state.theme !== 'warm-morning') {
  state.theme = 'warm-morning';
} else if (mode === 'dark' && state.theme === 'warm-morning') {
  state.theme = 'study-night';
}
```

- [ ] **Step 2: Add theme list to theme modal for full theme switching**

In the modal HTML builder (after line 237, the appearance mode toggle), add a theme selector row:

```js
// Theme color selection
html += '<div class="theme-modal-section">';
html += '<label class="theme-modal-label">配色方案</label>';
html += '<div class="theme-color-options">';
html += '<button class="theme-color-btn' + (state.theme === 'warm-morning' ? ' active' : '') + '" data-theme="warm-morning"><span class="theme-color-swatch" style="background:linear-gradient(135deg,#f97316,#f59e0b)"></span>日出晨光</button>';
html += '<button class="theme-color-btn' + (state.theme === 'study-night' ? ' active' : '') + '" data-theme="study-night"><span class="theme-color-swatch" style="background:linear-gradient(135deg,#fb923c,#21252b)"></span>深夜书房</button>';
html += '<button class="theme-color-btn' + (state.theme === 'starry-night' ? ' active' : '') + '" data-theme="starry-night"><span class="theme-color-swatch" style="background:linear-gradient(135deg,#fbbf24,#a78bfa)"></span>星夜</button>';
html += '</div></div>';
```

Add event binding after mode toggle bindings:

```js
// Color theme buttons
modal.querySelectorAll('.theme-color-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    modal.querySelectorAll('.theme-color-btn').forEach(function(b) { b.classList.remove('active'); });
    this.classList.add('active');
  });
});
```

In confirm handler (after mode logic), add:

```js
var activeColorBtn = modal.querySelector('.theme-color-btn.active');
if (activeColorBtn) {
  state.theme = activeColorBtn.getAttribute('data-theme');
}
```

- [ ] **Step 3: Add CSS for the new theme color buttons**

Add to hub.css, after the modal styles:

```css
.theme-color-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.theme-color-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-glass);
  background: var(--bg-glass);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.theme-color-btn:hover { background: var(--bg-glass-hover); }
.theme-color-btn.active {
  border-color: var(--brand-500);
  background: rgba(249, 115, 22, 0.06);
}
.theme-color-swatch {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  flex-shrink: 0;
}
```

- [ ] **Step 4: Commit**

```bash
git add js/theme.js css/hub.css
git commit -m "feat: update theme.js for new warm academy themes, add theme color picker"
```

---

### Task 4: Simplify loading.css — keep 3D for first load only

**Files:**
- Modify: `css/loading.css`

- [ ] **Step 1: Add a simple spinner variant for secondary loads**

Add to `css/loading.css` after the existing `.loading-spinner` block:

```css
/* Simple spinner — for page-to-page transitions */
.loading-spinner.simple::before,
.loading-spinner.simple::after {
  content: none;
}

.loading-spinner.simple {
  width: 48px;
  height: 48px;
  border: 3px solid var(--neutral-200, #e7e5e0);
  border-top-color: var(--brand-500, #f97316);
  border-radius: 50%;
  animation: spin-simple 0.7s linear infinite;
}

@keyframes spin-simple {
  to { transform: rotate(360deg); }
}
```

- [ ] **Step 2: Update loading.js to handle simple vs full spinner**

The current `loading.js` creates a single overlay via `createOverlay()`, preloads images via `preloadImages()`, then finishes with a star-dive animation via `finish()`. Public API is `window.LoadingSystem` with `isLoading` and `finish`.

Add a `showSimple()` method that skips the star-dive effect and uses the simple spinner ring. Edit `js/loading.js`:

After line 106 (the `finish()` function closing brace), add:

```js
  function showSimple() {
    // Re-show the overlay with simple spinner (no star dive on finish)
    createOverlay();
    if (spinnerEl) spinnerEl.classList.add('simple');
    if (overlayEl) overlayEl.classList.remove('fade-out');
    isLoading = true;

    // Auto-hide after a brief delay
    setTimeout(function () {
      isLoading = false;
      if (overlayEl) {
        overlayEl.classList.add('fade-out');
        overlayEl.addEventListener('transitionend', function handler() {
          overlayEl.removeEventListener('transitionend', handler);
          if (overlayEl && overlayEl.parentNode) {
            overlayEl.parentNode.removeChild(overlayEl);
          }
          overlayEl = null;
          spinnerEl = null;
        });
      }
    }, 600);
  }

  function finishSimple() {
    // Clean finish without dive animation — for simple spinner
    if (!overlayEl) return;
    overlayEl.classList.add('fade-out');
    overlayEl.addEventListener('transitionend', function handler() {
      overlayEl.removeEventListener('transitionend', handler);
      if (overlayEl && overlayEl.parentNode) {
        overlayEl.parentNode.removeChild(overlayEl);
      }
      overlayEl = null;
      spinnerEl = null;
    });
  }
```

Update the public API export at the bottom of the file (replace line 132-136):

```js
  window.LoadingSystem = {
    get isLoading() { return isLoading; },
    finish: finish,
    showSimple: showSimple,
    finishSimple: finishSimple
  };
```

- [ ] **Step 3: Commit**

```bash
git add css/loading.css js/loading.js
git commit -m "feat: add simple spinner variant for secondary page loads"
```

---

### Task 5: Update HTML pages — change default theme attribute

**Files:**
- Modify: `html/index.html`
- Modify: `html/personal.html`

- [ ] **Step 1: Update index.html default theme**

Line 2: Change `data-theme="ocean"` to `data-theme="warm-morning"`

- [ ] **Step 2: Update personal.html default theme**

Line 2: Change `data-theme="ocean"` to `data-theme="warm-morning"`

- [ ] **Step 3: Remove inline neon/glass styles from index.html `<style>` block**

Read lines 18-168 of `html/index.html` (the inline `<style>` block). Replace hardcoded dark/glass colors:

- `background: rgba(15, 23, 42, 0.4)` → `background: var(--surface-hover)`
- `background: rgba(30, 41, 59, 0.5)` → `background: var(--surface-card)`
- `border: 1px solid rgba(99, 102, 241, 0.15)` → `border: 1px solid var(--border-glass)`
- `color: #94a3b8` → `color: var(--text-muted)`
- `color: #e2e8f0` → `color: var(--text-heading)`
- `color: #94a3b8` → `color: var(--text-muted)`
- Gradient `linear-gradient(to right, transparent, rgba(99, 102, 241, 0.3), transparent)` → `linear-gradient(to right, transparent, var(--brand-300), transparent)`
- `background: rgba(99, 102, 241, 0.12)` → `background: rgba(249, 115, 22, 0.08)`
- `box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(99, 102, 241, 0.1)` → `box-shadow: var(--shadow-sm)`
- `background: linear-gradient(135deg, #4f46e5, #7c3aed)` → `background: var(--brand-500)`
- `box-shadow: 0 2px 6px rgba(79, 70, 229, 0.4)` → `box-shadow: 0 2px 6px rgba(249, 115, 22, 0.2)`

Also remove the `transition-delay` rules (lines 99-103 — the staggered `.teacher-card:nth-child(...)` delays):
```css
/* DELETE lines 99-103 — sequential stagger animation delays */
```

And replace `cubic-bezier(0.34, 1.56, 0.64, 1)` with `var(--ease-out)` everywhere.

- [ ] **Step 4: Update index.html page title**

Line 6: Change `<title>星识 Star-Learn - 全息智控学习舱 V5.0</title>` to `<title>星识 Star-Learn - AI 智能学习助手</title>`

- [ ] **Step 5: Commit**

```bash
git add html/index.html html/personal.html
git commit -m "feat: switch default theme to warm-morning, clean inline styles"
```

---

### Task 6: Polish component CSS files — replace hardcoded values

**Files:**
- Modify: `css/courses.css`
- Modify: `css/course-learn.css`
- Modify: `css/video-player.css`
- Modify: `css/personal.css`
- Modify: `css/settings.css`

- [ ] **Step 1: Scan and fix courses.css**

Run grep across all 5 files for hardcoded values that need replacement:

```bash
grep -n '#3b82f6\|#2563eb\|#1d4ed8\|#a855f7\|#8b5cf6\|#6d28d9\|#ec4899\|#06b6d4\|rgba(59,130,246\|rgba(139,92,246\|rgba(168,85,247\|rgba(99,102,241' css/courses.css css/course-learn.css css/video-player.css css/personal.css css/settings.css
```

For courses.css, the key replacements (show actual line numbers from grep output):

Every `#3b82f6` → `var(--brand-500)`
Every `#2563eb` → `var(--brand-600)`
Every `rgba(59,130,246,0.4)` → `rgba(249,115,22,0.3)`
Every `rgba(59,130,246,0.2)` → `rgba(249,115,22,0.1)`
Every `rgba(59,130,246,0.15)` → `rgba(249,115,22,0.08)`
Every `#60a5fa` → `var(--brand-400)`
Every `rgba(10,15,30,0.96)` → `var(--surface-card)`
Every `rgba(255,255,255,0.12)` → `var(--border-glass)`
Every `rgba(255,255,255,0.06)` → `var(--border-glass)`
Every `rgba(255,255,255,0.9)` → `var(--text-heading)`
Every `rgba(255,255,255,0.8)` → `var(--text-body)`

- [ ] **Step 2: Scan and fix course-learn.css**

Same pattern — replace blue/purple hardcoded values with brand token references.

- [ ] **Step 3: Scan and fix video-player.css**

Same pattern — replace blue/purple/neon with brand token references.

- [ ] **Step 4: Scan and fix personal.css**

Same pattern — replace blue/purple/neon/glass with brand token references.

- [ ] **Step 5: Scan and fix settings.css**

Same pattern — replace blue/purple/neon/glass with brand token references.

- [ ] **Step 6: Spring animation cleanup across all 5 files**

```bash
grep -n 'cubic-bezier(0.34, 1.56\|transition-spring\|ease-spring' css/courses.css css/course-learn.css css/video-player.css css/personal.css css/settings.css
```

Replace all spring curve references with `var(--ease-out)` or `cubic-bezier(0, 0, 0.2, 1)`.

- [ ] **Step 7: Commit**

```bash
git add css/courses.css css/course-learn.css css/video-player.css css/personal.css css/settings.css
git commit -m "feat: replace hardcoded neon/glass colors with design tokens in page CSS files"
```

---

### Task 7: Verify — start app and visually check 6 pages

**Files:**
- None (verification only)

- [ ] **Step 1: Start the Python server**

```bash
cd C:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main
python main.py
```

Wait for server to start on port 8000.

- [ ] **Step 2: Check each page at these URLs**

Open each in browser and verify:
1. `http://localhost:8000/` or `/index.html` — chat page: warm orange accents, clean white cards, no purple glow
2. `http://localhost:8000/hub.html` — hub: warm welcome area, clean cards, hot-streak graph
3. `http://localhost:8000/courses.html` — courses: Khan-style cards, no neon
4. `http://localhost:8000/course-learn.html` — course learn: warm accents on sidebar
5. `http://localhost:8000/video-player.html` — video: warm progress bar
6. `http://localhost:8000/personal.html` — personal center: clean, no glass overload

- [ ] **Step 3: Test theme switching**

1. Click theme settings button → verify modal shows 3 themes
2. Switch to "深夜书房" → verify dark mode applies
3. Switch to "星夜" → verify gold+violet accents appear
4. Switch back to "日出晨光" → verify warm light mode returns
5. Test wallpaper selection + brightness/blur sliders

- [ ] **Step 4: Test loading states**

1. Hard refresh (Ctrl+Shift+R) → verify 3D spinner appears on first load
2. Navigate between pages → verify simple spinner appears briefly

- [ ] **Step 5: Fix any visual issues found during testing**

Any colors that look wrong → adjust the legacy mapping variables in Task 1's theme blocks.
Any layout breakage → the old CSS selectors may have depended on removed variables; add back a mapping.

- [ ] **Step 6: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: visual polish after theme testing"
```
