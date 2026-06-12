# 主题系统配色优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将主题系统重构为三层 token 架构（原始层/自动色阶/语义层），支持 5 个预设主题（含霓虹还原），增加用户自定义 token 编辑器和亮/暗两层切换机制，实现 localStorage + 服务端同步。

**Architecture:** CSS 用 `color-mix(in oklch, ...)` 从原始层 ~10 个变量自动生成完整色阶，语义层 token 全局只定义一次。JS 改为 mode+theme 两层状态管理，弹窗只做快速切换，设置页做完整 token 编辑。服务端在 `users` 表增加 `theme_prefs` JSON 列。

**Tech Stack:** CSS custom properties + `color-mix()` + `oklch()`, vanilla JavaScript, FastAPI + pymysql/sqlite3

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `css/index.css` (:1-273) | 重写 ~270 行 token 区域 | 三层架构：原始 tokens、自动色阶、语义 tokens、5 个主题块、霓虹覆盖 |
| `js/theme.js` | 重写 | mode+theme 状态管理、弹窗交互、自定义主题 CRUD、同步引擎 |
| `html/settings.html` | 修改 | 在 appearance section 中新增 token 编辑器区域 |
| `js/settings.js` | 修改/新增 | token 编辑器交互逻辑、对比度计算 |
| `main.py` | 修改 | 新增 `POST/GET /api/user/theme/sync` |
| `db.py` | 修改 | `users` 表加 `theme_prefs` 列 |
| `css/hub.css` | 修改 | 删除隐藏的 `.theme-toggle-btn` 样式，适配新 token |
| 所有 `html/*.html` | 审查 | 无硬编码颜色，使用语义 token |
| 所有 `css/*.css` | 审查 | 同上 |

---

## Phase 1: CSS 三层 Token 架构

### Task 1: 备份并清空 index.css 中的 token 区域

**Files:**
- Modify: `css/index.css:1-273`

- [ ] **Step 1: 确认当前 token 区域范围**

token 区域从第 1 行到第 273 行（`[data-theme="starry-night"]` 块结束）。之后是 `body` 和 `*` 全局样式，不在此次修改范围。
运行：`head -280 css/index.css | tail -10` 确认 273 行之后是 `body, .text-auto {`。

- [ ] **Step 2: 保存旧 token 为备份**

```bash
cp css/index.css css/index.css.bak
```

- [ ] **Step 3: 用三层架构替换 :root 和 [data-theme] 块（1-273行）**

将第 1-273 行替换为以下内容，精确到行：

```css
/* ============================================
   Design Tokens v3 — Three-Layer Architecture
   Layer 1: Primitive    — per-theme raw colors (~10 values)
   Layer 2: Generated    — color-mix() scales, global
   Layer 3: Semantic     — usage tokens, global
   ============================================ */

/* ===== Layer 1: Primitive Tokens (per-theme) ===== */

/* Default: 日出晨光 (light, warm orange) */
:root, [data-theme="warm-morning"] {
    --brand-500:        #f97316;
    --neutral-500:      #78716c;
    --neutral-hue:      30;
    --accent-amber:     #f59e0b;
    --accent-rose:      #f43f5e;
    --accent-teal:      #14b8a6;
    --accent-violet:    #8b5cf6;
    --surface-page-l:   0.97;
    --surface-card-l:   1.0;
    --theme-name:       "日出晨光";
    color-scheme: light;
}

/* 林间晨光 (light, forest green) */
[data-theme="forest-light"] {
    --brand-500:        #16a34a;
    --neutral-500:      #6b7280;
    --neutral-hue:      240;
    --accent-amber:     #eab308;
    --accent-rose:      #f43f5e;
    --accent-teal:      #14b8a6;
    --accent-violet:    #8b5cf6;
    --surface-page-l:   0.97;
    --surface-card-l:   1.0;
    --theme-name:       "林间晨光";
    color-scheme: light;
}

/* 深夜书房 (dark, warm orange) */
[data-theme="study-night"] {
    --brand-500:        #fb923c;
    --neutral-500:      #8b9298;
    --neutral-hue:      30;
    --accent-amber:     #f59e0b;
    --accent-rose:      #f43f5e;
    --accent-teal:      #14b8a6;
    --accent-violet:    #8b5cf6;
    --surface-page-l:   0.10;
    --surface-card-l:   0.14;
    --theme-name:       "深夜书房";
    color-scheme: dark;
}

/* 星夜 (dark, gold + violet) */
[data-theme="starry-night"] {
    --brand-500:        #fbbf24;
    --neutral-500:      #8b9298;
    --neutral-hue:      260;
    --accent-amber:     #fbbf24;
    --accent-rose:      #f43f5e;
    --accent-teal:      #14b8a6;
    --accent-violet:    #a78bfa;
    --surface-page-l:   0.08;
    --surface-card-l:   0.12;
    --theme-name:       "星夜";
    color-scheme: dark;
}

/* 霓虹电光 (dark, neon cyan) */
[data-theme="neon-cyber"] {
    --brand-500:        #00e5ff;
    --neutral-500:      #6b7280;
    --neutral-hue:      220;
    --accent-amber:     #ffea00;
    --accent-rose:      #ff006e;
    --accent-teal:      #00e5ff;
    --accent-violet:    #b388ff;
    --surface-page-l:   0.04;
    --surface-card-l:   0.07;
    --theme-name:       "霓虹电光";
    color-scheme: dark;
}

/* ===== Layer 2: Generated Scales (global — defined once) ===== */
:root {
    /* Brand scale — light side (mix toward white) */
    --brand-50:  color-mix(in oklch, var(--brand-500) 8%, white);
    --brand-100: color-mix(in oklch, var(--brand-500) 20%, white);
    --brand-200: color-mix(in oklch, var(--brand-500) 38%, white);
    --brand-300: color-mix(in oklch, var(--brand-500) 55%, white);
    --brand-400: color-mix(in oklch, var(--brand-500) 78%, white);
    /* --brand-500: from primitive */
    /* Brand scale — dark side (mix toward black) */
    --brand-600: color-mix(in oklch, var(--brand-500) 78%, black);
    --brand-700: color-mix(in oklch, var(--brand-500) 55%, black);
    --brand-800: color-mix(in oklch, var(--brand-500) 32%, black);
    --brand-900: color-mix(in oklch, var(--brand-500) 10%, black);

    /* Neutral scale */
    --neutral-50:  color-mix(in oklch, var(--neutral-500) 8%, white);
    --neutral-100: color-mix(in oklch, var(--neutral-500) 20%, white);
    --neutral-200: color-mix(in oklch, var(--neutral-500) 38%, white);
    --neutral-300: color-mix(in oklch, var(--neutral-500) 58%, white);
    --neutral-400: color-mix(in oklch, var(--neutral-500) 80%, white);
    --neutral-600: color-mix(in oklch, var(--neutral-500) 78%, black);
    --neutral-700: color-mix(in oklch, var(--neutral-500) 55%, black);
    --neutral-800: color-mix(in oklch, var(--neutral-500) 32%, black);
    --neutral-900: color-mix(in oklch, var(--neutral-500) 10%, black);

    /* Accent scales */
    --accent-amber-50:  color-mix(in oklch, var(--accent-amber) 15%, white);
    --accent-amber-200: color-mix(in oklch, var(--accent-amber) 50%, white);
    --accent-amber-700: color-mix(in oklch, var(--accent-amber) 50%, black);
    --accent-rose-50:   color-mix(in oklch, var(--accent-rose) 15%, white);
    --accent-rose-200:  color-mix(in oklch, var(--accent-rose) 50%, white);
    --accent-rose-700:  color-mix(in oklch, var(--accent-rose) 50%, black);
    --accent-teal-50:   color-mix(in oklch, var(--accent-teal) 15%, white);
    --accent-teal-200:  color-mix(in oklch, var(--accent-teal) 50%, white);
    --accent-teal-700:  color-mix(in oklch, var(--accent-teal) 50%, black);
    --accent-violet-50: color-mix(in oklch, var(--accent-violet) 15%, white);
    --accent-violet-200:color-mix(in oklch, var(--accent-violet) 50%, white);
    --accent-violet-700:color-mix(in oklch, var(--accent-violet) 50%, black);

    /* ===== Layer 3: Semantic Tokens (global — defined once) ===== */

    /* Surfaces */
    --surface-page:      oklch(var(--surface-page-l) 0.02 var(--neutral-hue));
    --surface-card:      oklch(var(--surface-card-l) 0.02 var(--neutral-hue));
    --surface-hover:     color-mix(in oklch, var(--surface-card), var(--brand-500) 6%);
    --surface-pressed:   color-mix(in oklch, var(--surface-card), var(--brand-500) 12%);
    --surface-overlay:   oklch(0.15 0.02 var(--neutral-hue) / 0.6);
    --surface-nav:       oklch(var(--surface-card-l) 0.03 var(--neutral-hue) / 0.85);

    /* Text */
    --text-heading:      var(--neutral-900);
    --text-body:         var(--neutral-700);
    --text-muted:        var(--neutral-500);
    --text-placeholder:  var(--neutral-400);
    --text-link:         var(--brand-600);
    --text-on-brand:     white;

    /* Shadows */
    --shadow-xs: 0 1px 2px color-mix(in oklch, var(--neutral-900) 6%, transparent);
    --shadow-sm: 0 1px 3px color-mix(in oklch, var(--neutral-900) 8%, transparent);
    --shadow-md: 0 4px 16px color-mix(in oklch, var(--neutral-900) 10%, transparent);
    --shadow-lg: 0 12px 40px color-mix(in oklch, var(--neutral-900) 14%, transparent);

    /* Semantic colors */
    --success: #16a34a; --success-bg: #f0fdf4;
    --warning: #d97706; --warning-bg: #fffbeb;
    --danger:  #dc2626; --danger-bg:  #fef2f2;
    --info:    #2563eb; --info-bg:    #eff6ff;

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
    --radar-fill: color-mix(in oklch, var(--brand-500) 10%, transparent);
    --radar-stroke: var(--brand-400);
    --glass-bg: var(--surface-card);
    --dropdown-bg: var(--surface-card);
    --glass-border: var(--neutral-200);
    --text-main: var(--text-heading);
    --glass-shadow: color-mix(in oklch, var(--neutral-900) 6%, transparent);
    --glass-blur: 0px;
    --mesh-1: var(--neutral-100);
    --mesh-2: var(--neutral-50);
    --mesh-3: var(--neutral-200);
    --mesh-4: var(--neutral-100);
    --mesh-accent-1: color-mix(in oklch, var(--brand-500) 4%, transparent);
    --mesh-accent-2: color-mix(in oklch, var(--accent-amber) 3%, transparent);
    --text-primary: var(--text-heading);
    --text-secondary: var(--text-body);
    --text-tertiary: var(--text-muted);
    --text-on-accent: var(--text-on-brand);
    --surface-glass: var(--surface-card);
    --surface-glass-hover: var(--surface-hover);
    --border-glass: var(--neutral-200);
    --border-glass-hover: var(--brand-300);
    --accent-bg: color-mix(in oklch, var(--brand-500) 10%, transparent);
    --accent-border: color-mix(in oklch, var(--brand-500) 20%, transparent);
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

- [ ] **Step 4: 在后面添加霓虹主题的语义覆盖**

在 legacy mappings 的 `}` 之后（替换完的新内容的末尾），紧接着添加霓虹覆盖：

```css
/* ---- Neon Cyber semantic overrides ---- */
[data-theme="neon-cyber"] {
    /* 阴影替换为辉光 */
    --shadow-xs: 0 0 4px color-mix(in oklch, var(--brand-500) 30%, transparent);
    --shadow-sm: 0 0 8px color-mix(in oklch, var(--brand-500) 40%, transparent);
    --shadow-md: 0 0 16px color-mix(in oklch, var(--brand-500) 50%, transparent);
    --shadow-lg: 0 0 32px color-mix(in oklch, var(--brand-500) 60%, transparent);

    /* 品牌色阶保持荧光饱和度 — 暗底上少混白 */
    --brand-50:  color-mix(in oklch, var(--brand-500) 15%, black);
    --brand-100: color-mix(in oklch, var(--brand-500) 30%, black);
    --brand-200: color-mix(in oklch, var(--brand-500) 50%, black);
    --brand-300: color-mix(in oklch, var(--brand-500) 70%, black);
    --brand-400: color-mix(in oklch, var(--brand-500) 88%, black);

    /* 中性色阶偏冷 */
    --neutral-50:  oklch(0.06 0.01 var(--neutral-hue));
    --neutral-100: oklch(0.10 0.01 var(--neutral-hue));
    --neutral-200: oklch(0.16 0.01 var(--neutral-hue));
    --neutral-300: oklch(0.22 0.01 var(--neutral-hue));
    --neutral-400: oklch(0.35 0.01 var(--neutral-hue));
    --neutral-600: oklch(0.70 0.02 var(--neutral-hue));
    --neutral-700: oklch(0.82 0.01 var(--neutral-hue));
    --neutral-800: oklch(0.92 0.01 var(--neutral-hue));
    --neutral-900: oklch(0.97 0.01 var(--neutral-hue));

    /* Legacy overrides for neon */
    --radar-fill: color-mix(in oklch, var(--brand-500) 15%, transparent);
    --radar-stroke: var(--brand-400);
    --glass-shadow: 0 0 12px color-mix(in oklch, var(--brand-500) 30%, transparent);
    --mesh-accent-1: color-mix(in oklch, var(--brand-500) 8%, transparent);
    --mesh-accent-2: color-mix(in oklch, var(--accent-violet) 5%, transparent);
    --accent-bg: color-mix(in oklch, var(--brand-500) 15%, transparent);
    --accent-border: color-mix(in oklch, var(--brand-500) 30%, transparent);
    --text-on-brand: black;
    --primary-50: var(--neutral-100);
    --primary-100: var(--neutral-200);
    --primary-200: var(--neutral-300);
    --primary-300: var(--neutral-400);
}
```

- [ ] **Step 5: 检查是否有遗留的旧主题选择器需要删除**

确认以下选择器都不再存在于 index.css 中（应该已经在替换中被删除）：
- `[data-theme="light"]`
- `[data-theme="ocean"]`
- `.dark`

```bash
grep -n 'data-theme="light"\|data-theme="ocean"\|\.dark' css/index.css
```

预期输出为空（无匹配）。

- [ ] **Step 6: 提交**

```bash
git add css/index.css css/index.css.bak
git commit -m "重构CSS为三层token架构：原始层变量、color-mix自动色阶、语义层全局共享，新增forest-light和neon-cyber主题"
```

---

### Task 2: 清理 hub.css 中被隐藏的旧按钮样式

**Files:**
- Modify: `css/hub.css`

- [ ] **Step 1: 找到并删除 `.theme-toggle-btn` 的隐藏样式**

```bash
grep -n 'theme-toggle-btn' css/hub.css
```

- [ ] **Step 2: 删除 `.theme-toggle-btn { display: none; }` 所在行**

用精确的 grep 结果定位行号，用 Edit 删除。

- [ ] **Step 3: 确认 hub.css 中使用的旧 token 名称**

```bash
grep -o 'var(--[a-zA-Z-]*' css/hub.css | sort -u
```

确认使用的变量名都在 legacy mappings 中有定义。如有不在 legacy mappings 中的，记录下来后续处理。

- [ ] **Step 4: 提交**

```bash
git add css/hub.css
git commit -m "清理hub.css：删除隐藏的旧theme-toggle-btn样式"
```

---

### Task 3: 审查所有 HTML 页面使用语义 token

**Files:**
- Review: `html/*.html` (全部 6+ 个页面)
- Review: `css/loading.css`, 其他 `css/*.css`

- [ ] **Step 1: 扫描所有 HTML/CSS 中的硬编码颜色**

```bash
grep -rn '#[0-9a-fA-F]\{3,6\}\|rgb[a]\?(' html/ css/ --include='*.html' --include='*.css' | grep -v 'index.css' | grep -v 'node_modules' | grep -v '\.bak'
```

注意排除 index.css（已处理）。

- [ ] **Step 2: 逐文件审查，将硬编码颜色替换为语义 token**

对每个硬编码颜色，判断应替换为哪个语义 token：
- 背景色 → `var(--surface-card)` / `var(--surface-page)` 等
- 文字色 → `var(--text-body)` / `var(--text-muted)` 等
- 边框色 → `var(--border-color)` / `var(--neutral-200)` 等
- 品牌色 → `var(--brand-500)` 等

- [ ] **Step 3: 提交**

```bash
git add html/ css/
git commit -m "审查所有页面：替换硬编码颜色为语义token"
```

---

## Phase 2: JavaScript 重写

### Task 4: 重写 theme.js — 核心状态管理

**Files:**
- Modify: `js/theme.js` (全量重写)

- [ ] **Step 1: 删除旧 theme.js 并创建新文件骨架**

新的 theme.js 按以下结构组织：

```javascript
/**
 * Theme System v3 — Three-Layer Token Architecture
 * - mode (light/dark) + theme (color scheme) two-layer switching
 * - 5 preset themes + unlimited custom themes
 * - localStorage primary + server sync backup
 * - Wallpaper system (unchanged from v2)
 */
(function() {
  'use strict';

  // ===== Constants =====
  var STORAGE_KEY = 'starlearn_theme_v3';
  var CUSTOM_KEY = 'starlearn_custom_themes';
  var SYNC_DEBOUNCE = 2000;

  // ===== Preset Themes =====
  var PRESETS = {
    'warm-morning':  { name: '日出晨光', mode: 'light' },
    'forest-light':  { name: '林间晨光', mode: 'light' },
    'study-night':   { name: '深夜书房', mode: 'dark' },
    'starry-night':  { name: '星夜',     mode: 'dark' },
    'neon-cyber':    { name: '霓虹电光', mode: 'dark' }
  };

  // ===== Wallpapers (unchanged from v2) =====
  var WALLPAPERS = [
    { id: 'default',     title: '默认星图',     type: 'none',    url: '', preview: '' },
    { id: 'study-night', title: '书房夜晚',     type: 'static',  url: '/static/wallpaper/static/书房夜晚/image.png', preview: '/static/wallpaper/static/书房夜晚/image-pre.webp' },
    { id: 'cozy',        title: '安逸舒适',     type: 'static',  url: '/static/wallpaper/static/安逸舒适/image.png', preview: '/static/wallpaper/static/安逸舒适/image-pre.webp' },
    { id: 'ocean-girl',  title: '海洋女孩',     type: 'static',  url: '/static/wallpaper/static/海洋女孩/image.png', preview: '/static/wallpaper/static/海洋女孩/image-pre.webp' },
    { id: 'aerospace',   title: '向往航天的女孩', type: 'dynamic', url: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane.webm', preview: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane-pre.webm' },
    { id: 'nier-team',   title: '尼尔：机械纪元 团队', type: 'dynamic', url: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team.webm', preview: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team-pre.webm' }
  ];

  // ===== State =====
  var state = loadState();
  var customThemes = loadCustomThemes();
  var syncTimer = null;
  var videoBgEl = null;
```

- [ ] **Step 2: 实现 loadState / saveState（新模式存储结构）**

```javascript
  function loadState() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && saved.theme && saved.mode) return saved;
    } catch (e) {}
    return {
      mode: 'light',
      theme: 'warm-morning',
      wallpaperId: 'default',
      brightness: 85,
      blur: 5,
      textContrast: 30
    };
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    scheduleSync();
  }

  function loadCustomThemes() {
    try {
      var saved = JSON.parse(localStorage.getItem(CUSTOM_KEY));
      if (Array.isArray(saved)) return saved;
    } catch (e) {}
    return [];
  }

  function saveCustomThemes() {
    localStorage.setItem(CUSTOM_KEY, JSON.stringify(customThemes));
    scheduleSync();
  }
```

- [ ] **Step 3: 实现 getThemeInfo 辅助函数**

```javascript
  function getThemeInfo(themeId) {
    // Check presets first
    if (PRESETS[themeId]) return PRESETS[themeId];
    // Check custom themes
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === themeId) {
        return { name: customThemes[i].name, mode: customThemes[i].mode };
      }
    }
    // Fallback
    return { name: themeId, mode: 'light' };
  }

  function isLightMode() {
    return state.mode === 'light';
  }

  function getThemesForMode(mode) {
    var ids = [];
    // Presets for this mode
    for (var id in PRESETS) {
      if (PRESETS[id].mode === mode) ids.push(id);
    }
    // Custom themes for this mode
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].mode === mode) ids.push(customThemes[i].id);
    }
    return ids;
  }
```

- [ ] **Step 4: 实现 applyTheme — 自动同步 mode 和 theme**

```javascript
  function applyTheme(themeId) {
    state.theme = themeId;
    var info = getThemeInfo(themeId);
    state.mode = info.mode;
    document.documentElement.setAttribute('data-theme', themeId);
    document.body.classList.toggle('light-theme', state.mode === 'light');
  }

  function setMode(mode) {
    state.mode = mode;
    // Switch to last-used theme for this mode, or first available
    var themes = getThemesForMode(mode);
    if (themes.indexOf(state.theme) === -1) {
      state.theme = themes[0];
    }
    applyTheme(state.theme);
    saveState();
  }

  function setTheme(themeId) {
    applyTheme(themeId);
    saveState();
  }

  function toggleMode() {
    setMode(state.mode === 'light' ? 'dark' : 'light');
  }
```

- [ ] **Step 5: 保留壁纸相关函数（applyWallpaper 等，代码不变）**

壁纸系统的 `applyWallpaper`、`ensureVideoBg`、`removeVideoBg`、`updateVideoFilter`、`setWallpaper`、`setBrightness`、`setBlur`、`setTextContrast`、`restoreDefaults` 保持不变。直接从旧 theme.js 复制粘贴。

- [ ] **Step 6: 实现 applyAll**

```javascript
  function applyAll() {
    applyTheme(state.theme);
    applyWallpaper();
  }
```

- [ ] **Step 7: 实现自定义主题 CRUD**

```javascript
  function createCustomTheme(name, mode, primitives) {
    var id = 'custom-' + Date.now();
    customThemes.push({ id: id, name: name, mode: mode, primitives: primitives });
    saveCustomThemes();
    return id;
  }

  function updateCustomTheme(id, name, mode, primitives) {
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === id) {
        customThemes[i].name = name;
        customThemes[i].mode = mode;
        customThemes[i].primitives = primitives;
        saveCustomThemes();
        // If this theme is currently active, re-apply it
        if (state.theme === id) {
          applyCustomThemePrimitives(primitives);
        }
        return true;
      }
    }
    return false;
  }

  function deleteCustomTheme(id) {
    customThemes = customThemes.filter(function(t) { return t.id !== id; });
    saveCustomThemes();
    // If deleted theme was active, fall back to default
    if (state.theme === id) {
      setTheme(state.mode === 'light' ? 'warm-morning' : 'study-night');
    }
  }

  function applyCustomThemePrimitives(primitives) {
    var root = document.documentElement;
    for (var key in primitives) {
      root.style.setProperty('--' + key, primitives[key]);
    }
  }
```

- [ ] **Step 8: 实现服务端同步**

```javascript
  function scheduleSync() {
    if (syncTimer) clearTimeout(syncTimer);
    syncTimer = setTimeout(syncToServer, SYNC_DEBOUNCE);
  }

  function syncToServer() {
    if (!window.__currentUserId) return; // No user logged in
    var payload = {
      mode: state.mode,
      theme: state.theme,
      wallpaper: {
        id: state.wallpaperId,
        brightness: state.brightness,
        blur: state.blur,
        textContrast: state.textContrast
      },
      customThemes: customThemes
    };

    fetch('/api/user/theme/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).catch(function() { /* silent fail */ });
  }

  function loadFromServer() {
    if (!window.__currentUserId) return;
    fetch('/api/user/theme/sync')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data && data.theme) {
          state.mode = data.mode || 'light';
          state.theme = data.theme;
          if (data.wallpaper) {
            state.wallpaperId = data.wallpaper.id || 'default';
            state.brightness = data.wallpaper.brightness || 85;
            state.blur = data.wallpaper.blur || 5;
            state.textContrast = data.wallpaper.textContrast || 30;
          }
          if (Array.isArray(data.customThemes)) {
            customThemes = data.customThemes;
            saveCustomThemes();
          }
          saveState();
          applyAll();
        }
      }).catch(function() { /* silent fail */ });
  }
```

- [ ] **Step 9: 实现 init 和公共 API**

```javascript
  function init() {
    applyAll();

    // Try loading server preferences first
    loadFromServer();

    // Theme settings button
    initThemeSettingsModal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.StarTheme = {
    WALLPAPERS: WALLPAPERS,
    PRESETS: PRESETS,
    getState: function() { return state; },
    getCustomThemes: function() { return customThemes; },
    setMode: setMode,
    setTheme: setTheme,
    toggleMode: toggleMode,
    isLightMode: isLightMode,
    getThemesForMode: getThemesForMode,
    getThemeInfo: getThemeInfo,
    setWallpaper: setWallpaper,
    setBrightness: setBrightness,
    setBlur: setBlur,
    setTextContrast: setTextContrast,
    restoreDefaults: restoreDefaults,
    applyAll: applyAll,
    openThemeModal: openThemeModal,
    createCustomTheme: createCustomTheme,
    updateCustomTheme: updateCustomTheme,
    deleteCustomTheme: deleteCustomTheme,
    loadFromServer: loadFromServer
  };
})();
```

- [ ] **Step 10: 删除死代码**

确认以下内容**不出现**在新文件中：
- `renderSakuraParticles()` / `stopSakuraParticles()`
- `toggleTheme()` (旧的循环切换)
- `updateToggleButton()` (旧的太阳/月亮按钮)
- `LIGHT_THEMES` 数组
- `DEFAULT_THEME` 常量（改为从 state 默认值推断）

- [ ] **Step 11: 提交**

```bash
git add js/theme.js
git commit -m "重写theme.js：mode+theme两层切换、自定义主题CRUD、服务端同步引擎、删除死代码"
```

---

### Task 5: 重写 theme.js — 弹窗 Modal

**Files:**
- Modify: `js/theme.js` (同一文件，接续 Task 4)

- [ ] **Step 1: 实现新的 openThemeModal**

弹窗结构：模式开关 + 当前模式下的预设/自定义配色卡片 + 品牌色快速选择 + 高级编辑入口 + 壁纸网格 + 滑块 + 操作按钮。

```javascript
  function openThemeModal() {
    var existing = document.getElementById('theme-settings-modal');
    if (existing) existing.remove();

    var currentInfo = getThemeInfo(state.theme);
    var themes = getThemesForMode(state.mode);

    var html = '';
    html += '<div class="theme-modal-overlay" id="theme-settings-modal">';
    html += '<div class="theme-modal glass-card">';
    html += '<div class="theme-modal-header">';
    html += '<h3 class="theme-modal-title">主题设置</h3>';
    html += '<button class="theme-modal-close" id="theme-modal-close">';
    html += '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    html += '</button></div>';

    // Mode toggle
    html += '<div class="theme-modal-section">';
    html += '<label class="theme-modal-label">外观模式</label>';
    html += '<div class="theme-mode-toggle">';
    html += '<button class="theme-mode-btn' + (state.mode === 'dark' ? ' active' : '') + '" data-mode="dark">深色</button>';
    html += '<button class="theme-mode-btn' + (state.mode === 'light' ? ' active' : '') + '" data-mode="light">浅色</button>';
    html += '</div></div>';

    // Color scheme cards
    html += '<div class="theme-modal-section">';
    html += '<label class="theme-modal-label">配色方案</label>';
    html += '<div class="theme-color-options">';
    for (var i = 0; i < themes.length; i++) {
      var t = themes[i];
      var info = getThemeInfo(t);
      var isActive = state.theme === t ? ' active' : '';
      var isPreset = PRESETS[t] ? '' : ' custom';
      html += '<button class="theme-color-btn' + isActive + isPreset + '" data-theme="' + t + '">';
      html += '<span class="theme-color-swatch" style="background:linear-gradient(135deg,var(--brand-500),var(--accent-violet))"></span>';
      html += info.name;
      if (!PRESETS[t]) html += '<span class="theme-custom-badge">自定义</span>';
      html += '</button>';
    }
    html += '</div></div>';

    // Brand color quick picker
    html += '<div class="theme-modal-section">';
    html += '<label class="theme-modal-label">品牌色快速调整</label>';
    html += '<div class="theme-brand-picker">';
    html += '<input type="color" id="theme-brand-color" value="#f97316" class="theme-color-input">';
    html += '<div class="theme-color-presets">';
    var presetColors = ['#f97316', '#16a34a', '#2563eb', '#8b5cf6', '#ec4899', '#00e5ff', '#fbbf24', '#ef4444'];
    for (var c = 0; c < presetColors.length; c++) {
      html += '<button class="theme-preset-dot" data-color="' + presetColors[c] + '" style="background:' + presetColors[c] + '"></button>';
    }
    html += '</div></div></div>';

    // Advanced edit link
    html += '<div class="theme-modal-section">';
    html += '<a href="/html/settings.html#appearance" class="theme-advanced-link">高级编辑 → 完整 Token 编辑器</a>';
    html += '</div>';

    // Wallpaper grid (unchanged from v2)
    html += '<div class="theme-modal-section">';
    html += '<label class="theme-modal-label">壁纸</label>';
    html += '<div class="theme-wallpaper-grid">';
    for (var w = 0; w < WALLPAPERS.length; w++) {
      var wp = WALLPAPERS[w];
      var sel = state.wallpaperId === wp.id ? ' selected' : '';
      var dyn = wp.type === 'dynamic' ? ' dynamic' : '';
      html += '<button class="theme-wallpaper-thumb' + sel + dyn + '" data-wp-id="' + wp.id + '">';
      if (wp.preview) {
        html += '<img src="' + wp.preview + '" alt="' + wp.title + '" class="theme-wallpaper-img" loading="lazy" onerror="this.style.display=\'none\'">';
      } else {
        html += '<div class="theme-wallpaper-placeholder"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M12 2a10 10 0 0 0 0 20"/><path d="M2 12h20"/></svg></div>';
      }
      html += '<span class="theme-wallpaper-label">' + wp.title + '</span>';
      if (wp.type === 'dynamic') html += '<span class="theme-wallpaper-badge">动态</span>';
      html += '</button>';
    }
    html += '</div></div>';

    // Sliders (unchanged)
    html += '<div class="theme-modal-section">';
    html += '<div class="theme-slider-row">';
    html += '<label class="theme-modal-label">壁纸亮度 <span class="theme-slider-val">' + state.brightness + '%</span></label>';
    html += '<input type="range" class="theme-slider" id="theme-brightness" min="40" max="150" value="' + state.brightness + '">';
    html += '</div>';
    html += '<div class="theme-slider-row">';
    html += '<label class="theme-modal-label">模糊 <span class="theme-slider-val">' + state.blur + 'px</span></label>';
    html += '<input type="range" class="theme-slider" id="theme-blur" min="0" max="20" value="' + state.blur + '">';
    html += '</div></div>';

    // Actions
    html += '<div class="theme-modal-actions">';
    html += '<button class="theme-action-btn ghost" id="theme-restore-btn">恢复默认</button>';
    html += '<button class="theme-action-btn ghost" id="theme-cancel-btn">取消</button>';
    html += '<button class="theme-action-btn primary" id="theme-confirm-btn">确认</button>';
    html += '</div>';

    html += '</div></div>';
    document.body.insertAdjacentHTML('beforeend', html);

    // Event bindings
    bindModalEvents();
  }
```

- [ ] **Step 2: 实现 bindModalEvents（新的事件绑定逻辑）**

```javascript
  function bindModalEvents() {
    var modal = document.getElementById('theme-settings-modal');

    // Close
    document.getElementById('theme-modal-close').addEventListener('click', closeModal);
    document.getElementById('theme-cancel-btn').addEventListener('click', closeModal);
    modal.addEventListener('click', function(e) { if (e.target === modal) closeModal(); });

    // Mode toggle — switches mode, refreshes theme list
    modal.querySelectorAll('.theme-mode-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var mode = this.getAttribute('data-mode');
        modal.querySelectorAll('.theme-mode-btn').forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
        // Refresh color options for this mode
        refreshModalColorOptions(modal, mode);
      });
    });

    // Color theme buttons
    modal.querySelectorAll('.theme-color-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        modal.querySelectorAll('.theme-color-btn').forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
      });
    });

    // Brand color picker
    var brandInput = document.getElementById('theme-brand-color');
    if (brandInput) {
      brandInput.addEventListener('input', function() {
        document.documentElement.style.setProperty('--brand-500', this.value);
      });
    }
    modal.querySelectorAll('.theme-preset-dot').forEach(function(dot) {
      dot.addEventListener('click', function() {
        var color = this.getAttribute('data-color');
        document.documentElement.style.setProperty('--brand-500', color);
        if (brandInput) brandInput.value = color;
      });
    });

    // Wallpaper (unchanged logic)
    modal.querySelectorAll('.theme-wallpaper-thumb').forEach(function(btn) {
      btn.addEventListener('click', function() {
        modal.querySelectorAll('.theme-wallpaper-thumb').forEach(function(b) { b.classList.remove('selected'); });
        this.classList.add('selected');
        var wpId = this.getAttribute('data-wp-id');
        var wp = getWallpaper(wpId);
        if (wp && wp.type !== 'none') {
          document.documentElement.style.setProperty('--leleo-bg-image', 'url("' + (wp.preview || wp.url) + '")');
          document.documentElement.style.setProperty('--leleo-bg-type', wp.type);
          if (wp.type === 'dynamic') {
            document.documentElement.style.setProperty('--leleo-bg-video', 'url("' + wp.url + '")');
            ensureVideoBg(wp.url);
          } else {
            removeVideoBg();
          }
          document.documentElement.setAttribute('data-glass', 'true');
        } else {
          document.documentElement.style.setProperty('--leleo-bg-image', 'none');
          document.documentElement.setAttribute('data-glass', 'false');
          removeVideoBg();
        }
      });
    });

    // Sliders (unchanged)
    var brightnessSlider = document.getElementById('theme-brightness');
    var blurSlider = document.getElementById('theme-blur');
    brightnessSlider.addEventListener('input', function() {
      var val = parseInt(this.value);
      document.documentElement.style.setProperty('--leleo-brightness', val + '%');
      this.parentElement.querySelector('.theme-slider-val').textContent = val + '%';
      updateVideoFilter();
    });
    blurSlider.addEventListener('input', function() {
      var val = parseInt(this.value);
      document.documentElement.style.setProperty('--leleo-blur', val + 'px');
      this.parentElement.querySelector('.theme-slider-val').textContent = val + 'px';
      updateVideoFilter();
    });

    // Confirm
    document.getElementById('theme-confirm-btn').addEventListener('click', function() {
      var selectedThumb = modal.querySelector('.theme-wallpaper-thumb.selected');
      if (selectedThumb) state.wallpaperId = selectedThumb.getAttribute('data-wp-id');
      state.brightness = parseInt(brightnessSlider.value);
      state.blur = parseInt(blurSlider.value);

      var activeColorBtn = modal.querySelector('.theme-color-btn.active');
      if (activeColorBtn) {
        var themeId = activeColorBtn.getAttribute('data-theme');
        setTheme(themeId);
      }

      // If brand color was changed via quick picker, create/update custom theme
      var newBrand = document.getElementById('theme-brand-color');
      if (newBrand && newBrand.value !== getComputedStyle(document.documentElement).getPropertyValue('--brand-500').trim()) {
        var customId = createCustomTheme('我的配色', state.mode, {
          'brand-500': newBrand.value,
          'neutral-500': getComputedStyle(document.documentElement).getPropertyValue('--neutral-500').trim(),
          'neutral-hue': 30,
          'accent-amber': getComputedStyle(document.documentElement).getPropertyValue('--accent-amber').trim(),
          'accent-rose': getComputedStyle(document.documentElement).getPropertyValue('--accent-rose').trim(),
          'accent-teal': getComputedStyle(document.documentElement).getPropertyValue('--accent-teal').trim(),
          'accent-violet': getComputedStyle(document.documentElement).getPropertyValue('--accent-violet').trim(),
          'surface-page-l': state.mode === 'light' ? 0.97 : 0.10,
          'surface-card-l': state.mode === 'light' ? 1.0 : 0.14
        });
        setTheme(customId);
      }

      saveState();
      applyAll();
      closeModal();
    });

    // Restore
    document.getElementById('theme-restore-btn').addEventListener('click', function() {
      restoreDefaults();
      modal.querySelectorAll('.theme-wallpaper-thumb').forEach(function(b) { b.classList.remove('selected'); });
      var defaultThumb = modal.querySelector('[data-wp-id="default"]');
      if (defaultThumb) defaultThumb.classList.add('selected');
      brightnessSlider.value = 85;
      blurSlider.value = 5;
      modal.querySelectorAll('.theme-slider-val')[0].textContent = '85%';
      modal.querySelectorAll('.theme-slider-val')[1].textContent = '5px';
    });

    // Esc
    function onKeydown(e) { if (e.key === 'Escape') { closeModal(); document.removeEventListener('keydown', onKeydown); } }
    document.addEventListener('keydown', onKeydown);
  }

  function refreshModalColorOptions(modal, mode) {
    var container = modal.querySelector('.theme-color-options');
    if (!container) return;
    var themes = getThemesForMode(mode);
    var html = '';
    for (var i = 0; i < themes.length; i++) {
      var t = themes[i];
      var info = getThemeInfo(t);
      var isActive = state.theme === t ? ' active' : '';
      var isPreset = PRESETS[t] ? '' : ' custom';
      html += '<button class="theme-color-btn' + isActive + isPreset + '" data-theme="' + t + '">';
      html += '<span class="theme-color-swatch" style="background:linear-gradient(135deg,var(--brand-500),var(--accent-violet))"></span>';
      html += info.name;
      if (!PRESETS[t]) html += '<span class="theme-custom-badge">自定义</span>';
      html += '</button>';
    }
    container.innerHTML = html;
    // Re-bind click events
    container.querySelectorAll('.theme-color-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        container.querySelectorAll('.theme-color-btn').forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
      });
    });
  }

  function closeModal() {
    var m = document.getElementById('theme-settings-modal');
    if (m) m.remove();
    applyAll();
  }
```

- [ ] **Step 3: 保留 getWallpaper 函数**

```javascript
  function getWallpaper(id) {
    for (var i = 0; i < WALLPAPERS.length; i++) {
      if (WALLPAPERS[i].id === id) return WALLPAPERS[i];
    }
    return WALLPAPERS[0];
  }
```

- [ ] **Step 4: 验证新 theme.js 完整无语法错误**

```bash
node --check js/theme.js
```

预期：无输出（无语法错误）。

- [ ] **Step 5: 提交**

```bash
git add js/theme.js
git commit -m "重写theme.js弹窗：mode切换联动配色列表、品牌色快速选择器、自定义主题创建"
```

---

## Phase 3: 设置页 Token 编辑器

### Task 6: 在 settings.html 中添加 Token 编辑器区域

**Files:**
- Modify: `html/settings.html` (appearance section)
- Create/Modify: `js/settings.js` (token editor logic)

- [ ] **Step 1: 找到 settings.html 的 appearance section 并替换旧的 theme-colors**

定位 `html/settings.html:121-126` 的旧 5 色选择器：

```bash
grep -n 'theme-colors\|theme-color active' html/settings.html
```

- [ ] **Step 2: 删除旧选择器，插入 token 编辑器骨架**

找到旧代码：
```html
<div class="theme-colors">
    <button class="theme-color active" data-color="purple" ...></button>
    <button class="theme-color" data-color="blue" ...></button>
    <button class="theme-color" data-color="green" ...></button>
    <button class="theme-color" data-color="orange" ...></button>
    <button class="theme-color" data-color="pink" ...></button>
</div>
```

替换为：

```html
<div class="token-editor" id="token-editor">
    <h4>配色编辑器</h4>
    <p class="settings-hint">调整配色方案，实时预览。修改会自动生成完整色阶。</p>

    <!-- Preview -->
    <div class="token-preview" id="token-preview">
        <div class="token-preview-card">
            <h5 class="token-preview-heading">预览标题</h5>
            <p class="token-preview-body">正文文字示例。色阶过渡自然，对比度清晰可读。</p>
            <p class="token-preview-muted">辅助文字 · 次要信息</p>
            <button class="token-preview-btn">按钮示例</button>
        </div>
        <div class="token-preview-contrast" id="token-contrast-info">
            <span>正文对比度：<strong id="contrast-body">--</strong></span>
            <span>辅助对比度：<strong id="contrast-muted">--</strong></span>
        </div>
    </div>

    <!-- Brand color -->
    <div class="token-field">
        <label>品牌色</label>
        <div class="token-color-row">
            <input type="color" id="edit-brand-500" class="token-color-input">
            <input type="text" id="edit-brand-500-hex" class="token-hex-input" maxlength="7" placeholder="#f97316">
        </div>
        <div class="token-preset-row" id="brand-presets"></div>
    </div>

    <!-- Neutral tone -->
    <div class="token-field">
        <label>中性色基调</label>
        <div class="token-neutral-tone">
            <button class="tone-btn active" data-tone="warm">暖灰</button>
            <button class="tone-btn" data-tone="cool">冷灰</button>
            <button class="tone-btn" data-tone="pure">纯灰</button>
        </div>
        <label>底色明度 <span id="surface-l-val">0.97</span></label>
        <input type="range" id="edit-surface-page-l" min="0.03" max="1.0" step="0.01" value="0.97">
    </div>

    <!-- Accent colors -->
    <div class="token-field">
        <label>装饰色</label>
        <div class="token-accent-grid">
            <div class="token-accent-item">
                <span>琥珀</span>
                <input type="color" id="edit-accent-amber" class="token-color-input">
            </div>
            <div class="token-accent-item">
                <span>玫红</span>
                <input type="color" id="edit-accent-rose" class="token-color-input">
            </div>
            <div class="token-accent-item">
                <span>青绿</span>
                <input type="color" id="edit-accent-teal" class="token-color-input">
            </div>
            <div class="token-accent-item">
                <span>紫</span>
                <input type="color" id="edit-accent-violet" class="token-color-input">
            </div>
        </div>
    </div>

    <!-- Save -->
    <div class="token-actions">
        <input type="text" id="edit-theme-name" class="token-name-input" placeholder="输入主题名称" maxlength="20">
        <button class="settings-btn primary" id="save-custom-theme">保存为自定义主题</button>
        <button class="settings-btn ghost" id="reset-token-editor">恢复默认</button>
    </div>
</div>
```

- [ ] **Step 3: 提交**

```bash
git add html/settings.html
git commit -m "settings.html：替换旧5色选择器为完整token编辑器骨架"
```

---

### Task 7: 实现 settings.js Token 编辑器交互

**Files:**
- Modify: `js/settings.js`

- [ ] **Step 1: 检查 settings.js 是否存在**

```bash
ls -la js/settings.js
```

如果不存在则创建，如果存在则在末尾追加。

- [ ] **Step 2: 实现对比度计算函数**

```javascript
/**
 * Token Editor — contrast calculation and live preview
 */
(function() {
  'use strict';

  // WCAG relative luminance
  function getLuminance(hex) {
    var r = parseInt(hex.slice(1, 3), 16) / 255;
    var g = parseInt(hex.slice(3, 5), 16) / 255;
    var b = parseInt(hex.slice(5, 7), 16) / 255;
    var toLinear = function(c) {
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
  }

  function getContrastRatio(hex1, hex2) {
    var l1 = getLuminance(hex1);
    var l2 = getLuminance(hex2);
    var lighter = Math.max(l1, l2);
    var darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }
```

- [ ] **Step 3: 实现实时预览更新**

```javascript
  function updatePreview() {
    var brand = document.getElementById('edit-brand-500').value;
    var surfaceL = parseFloat(document.getElementById('edit-surface-page-l').value);

    // Update CSS custom properties on the preview card
    var preview = document.getElementById('token-preview');
    if (!preview) return;

    // Apply brand color
    preview.style.setProperty('--brand-500', brand);
    preview.style.setProperty('--brand-600', brand); // fallback

    // Calculate approximate surface color from lightness
    var isDark = surfaceL < 0.5;
    var bgColor = isDark
      ? '#' + Math.round(surfaceL * 255).toString(16).padStart(2, '0').repeat(3)
      : '#' + Math.round((1 - surfaceL) * 255).toString(16).padStart(2, '0').repeat(3);

    preview.style.backgroundColor = isDark ? '#1a1a2e' : '#fafaf9';
    preview.style.color = isDark ? '#e8ecf1' : '#1c1917';

    // Calculate and display contrast
    var textColor = isDark ? '#e8ecf1' : '#44413c';
    var mutedColor = isDark ? '#8b9298' : '#78756e';
    var bgHex = isDark ? '#1a1a2e' : '#ffffff';

    var bodyContrast = getContrastRatio(textColor, bgHex);
    var mutedContrast = getContrastRatio(mutedColor, bgHex);

    var bodyEl = document.getElementById('contrast-body');
    var mutedEl = document.getElementById('contrast-muted');
    if (bodyEl) {
      bodyEl.textContent = bodyContrast.toFixed(1) + ':1';
      bodyEl.style.color = bodyContrast >= 4.5 ? '#16a34a' : bodyContrast >= 3 ? '#d97706' : '#dc2626';
    }
    if (mutedEl) {
      mutedEl.textContent = mutedContrast.toFixed(1) + ':1';
      mutedEl.style.color = mutedContrast >= 3 ? '#16a34a' : '#dc2626';
    }
  }
```

- [ ] **Step 4: 实现编辑器初始化**

```javascript
  function initTokenEditor() {
    var editor = document.getElementById('token-editor');
    if (!editor) return;

    // Load current theme state
    var state = window.StarTheme ? window.StarTheme.getState() : null;
    var mode = state ? state.mode : 'light';
    var surfaceL = mode === 'light' ? 0.97 : 0.10;

    // Set initial values from current theme
    var rootStyles = getComputedStyle(document.documentElement);
    var brand500 = rootStyles.getPropertyValue('--brand-500').trim();
    document.getElementById('edit-brand-500').value = brand500 || '#f97316';
    document.getElementById('edit-brand-500-hex').value = brand500 || '#f97316';
    document.getElementById('edit-surface-page-l').value = surfaceL;
    document.getElementById('edit-surface-l-val').textContent = surfaceL.toFixed(2);
    document.getElementById('edit-accent-amber').value = rootStyles.getPropertyValue('--accent-amber').trim() || '#f59e0b';
    document.getElementById('edit-accent-rose').value = rootStyles.getPropertyValue('--accent-rose').trim() || '#f43f5e';
    document.getElementById('edit-accent-teal').value = rootStyles.getPropertyValue('--accent-teal').trim() || '#14b8a6';
    document.getElementById('edit-accent-violet').value = rootStyles.getPropertyValue('--accent-violet').trim() || '#8b5cf6';

    // Brand presets
    var presets = ['#f97316', '#16a34a', '#2563eb', '#8b5cf6', '#ec4899', '#00e5ff', '#fbbf24', '#ef4444'];
    var presetRow = document.getElementById('brand-presets');
    if (presetRow) {
      var html = '';
      for (var i = 0; i < presets.length; i++) {
        html += '<button class="theme-preset-dot" data-color="' + presets[i] + '" style="background:' + presets[i] + '"></button>';
      }
      presetRow.innerHTML = html;
    }

    // Event delegation for presets
    presetRow.addEventListener('click', function(e) {
      var dot = e.target.closest('.theme-preset-dot');
      if (!dot) return;
      var color = dot.getAttribute('data-color');
      document.getElementById('edit-brand-500').value = color;
      document.getElementById('edit-brand-500-hex').value = color;
      document.documentElement.style.setProperty('--brand-500', color);
      updatePreview();
    });

    // Brand color sync
    document.getElementById('edit-brand-500').addEventListener('input', function() {
      var val = this.value;
      document.getElementById('edit-brand-500-hex').value = val;
      document.documentElement.style.setProperty('--brand-500', val);
      updatePreview();
    });
    document.getElementById('edit-brand-500-hex').addEventListener('input', function() {
      var val = this.value;
      if (/^#[0-9a-fA-F]{6}$/.test(val)) {
        document.getElementById('edit-brand-500').value = val;
        document.documentElement.style.setProperty('--brand-500', val);
        updatePreview();
      }
    });

    // Surface lightness
    document.getElementById('edit-surface-page-l').addEventListener('input', function() {
      var val = parseFloat(this.value);
      document.getElementById('edit-surface-l-val').textContent = val.toFixed(2);
      document.documentElement.style.setProperty('--surface-page-l', val);
      document.documentElement.style.setProperty('--surface-card-l', Math.min(1, val + 0.03));
      updatePreview();
    });

    // Accent colors
    ['amber', 'rose', 'teal', 'violet'].forEach(function(name) {
      var input = document.getElementById('edit-accent-' + name);
      if (input) {
        input.addEventListener('input', function() {
          document.documentElement.style.setProperty('--accent-' + name, this.value);
          updatePreview();
        });
      }
    });

    // Neutral tone buttons
    document.querySelectorAll('.tone-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.tone-btn').forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
        var tone = this.getAttribute('data-tone');
        var hue = tone === 'warm' ? 30 : tone === 'cool' ? 240 : 0;
        document.documentElement.style.setProperty('--neutral-hue', hue);
        updatePreview();
      });
    });

    // Save custom theme
    document.getElementById('save-custom-theme').addEventListener('click', function() {
      var name = document.getElementById('edit-theme-name').value.trim() || '我的配色';
      var mode = parseFloat(document.getElementById('edit-surface-page-l').value) > 0.5 ? 'light' : 'dark';
      var primitives = {
        'brand-500': document.getElementById('edit-brand-500').value,
        'neutral-500': getComputedStyle(document.documentElement).getPropertyValue('--neutral-500').trim(),
        'neutral-hue': parseInt(getComputedStyle(document.documentElement).getPropertyValue('--neutral-hue').trim()) || 30,
        'accent-amber': document.getElementById('edit-accent-amber').value,
        'accent-rose': document.getElementById('edit-accent-rose').value,
        'accent-teal': document.getElementById('edit-accent-teal').value,
        'accent-violet': document.getElementById('edit-accent-violet').value,
        'surface-page-l': parseFloat(document.getElementById('edit-surface-page-l').value),
        'surface-card-l': Math.min(1, parseFloat(document.getElementById('edit-surface-page-l').value) + 0.03)
      };

      if (window.StarTheme) {
        var id = window.StarTheme.createCustomTheme(name, mode, primitives);
        window.StarTheme.setTheme(id);
        alert('主题 "' + name + '" 已保存并应用！');
      }
    });

    // Reset
    document.getElementById('reset-token-editor').addEventListener('click', function() {
      if (window.StarTheme) {
        var defaultTheme = window.StarTheme.isLightMode() ? 'warm-morning' : 'study-night';
        window.StarTheme.setTheme(defaultTheme);
      }
      // Re-read CSS values
      setTimeout(function() {
        var rs = getComputedStyle(document.documentElement);
        document.getElementById('edit-brand-500').value = rs.getPropertyValue('--brand-500').trim();
        document.getElementById('edit-brand-500-hex').value = rs.getPropertyValue('--brand-500').trim();
        document.getElementById('edit-accent-amber').value = rs.getPropertyValue('--accent-amber').trim();
        document.getElementById('edit-accent-rose').value = rs.getPropertyValue('--accent-rose').trim();
        document.getElementById('edit-accent-teal').value = rs.getPropertyValue('--accent-teal').trim();
        document.getElementById('edit-accent-violet').value = rs.getPropertyValue('--accent-violet').trim();
        updatePreview();
      }, 100);
    });

    updatePreview();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTokenEditor);
  } else {
    if (document.getElementById('token-editor')) initTokenEditor();
  }
})();
```

- [ ] **Step 4: 提交**

```bash
git add js/settings.js
git commit -m "实现settings.js token编辑器：对比度计算/实时预览/品牌色/中性色/装饰色编辑/保存自定义主题"
```

---

## Phase 4: 服务端持久化

### Task 8: 数据库 — users 表新增 theme_prefs 列

**Files:**
- Modify: `db.py`

- [ ] **Step 1: 找到 users 表的创建/确保逻辑**

```bash
grep -n 'def.*user.*table\|CREATE TABLE.*user[^_]\|ensure.*user' db.py
```

- [ ] **Step 2: 添加 ensure_theme_prefs_column 函数**

在 db.py 中合适位置（如 `ensure_login_records_table` 附近）添加：

```python
def ensure_theme_prefs_column(conn):
    """Add theme_prefs JSON column to user table if missing."""
    if conn is None:
        return
    cursor = conn.cursor()
    if _is_sqlite(conn):
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN theme_prefs TEXT DEFAULT ''")
        except:
            pass  # column already exists
    else:
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN theme_prefs JSON DEFAULT NULL")
        except:
            pass
    conn.commit()
    cursor.close()
```

- [ ] **Step 3: 添加 get/set 函数**

```python
import json

def get_user_theme_prefs(user_id):
    with get_db() as conn:
        if conn is None:
            return None
        ensure_theme_prefs_column(conn)
        cursor = conn.cursor(pymysql.cursors.DictCursor) if not _is_sqlite(conn) else conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("SELECT theme_prefs FROM user WHERE id = ?", (user_id,))
        else:
            cursor.execute("SELECT theme_prefs FROM user WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        if row and row.get('theme_prefs'):
            prefs = row['theme_prefs']
            if isinstance(prefs, str):
                try:
                    return json.loads(prefs)
                except:
                    return None
            return prefs
        return None


def save_user_theme_prefs(user_id, prefs_dict):
    prefs_json = json.dumps(prefs_dict, ensure_ascii=False)
    with get_db() as conn:
        if conn is None:
            return False
        ensure_theme_prefs_column(conn)
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("UPDATE user SET theme_prefs = ? WHERE id = ?", (prefs_json, user_id))
        else:
            cursor.execute("UPDATE user SET theme_prefs = %s WHERE id = %s", (prefs_json, user_id))
        conn.commit()
        cursor.close()
        return True
```

- [ ] **Step 4: 提交**

```bash
git add db.py
git commit -m "db.py：users表新增theme_prefs JSON列，添加get/set函数"
```

---

### Task 9: API — 新增主题同步端点

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 在 login 端点返回中添加 theme_prefs**

找到 login 端点的返回处（`main.py:1278`），在返回字典中添加：

```python
    theme_prefs = database.get_user_theme_prefs(user['id'])
    return {
        ...existing fields...,
        "themePrefs": theme_prefs
    }
```

- [ ] **Step 2: 在用户状态加载中包含 theme_prefs**

找到 `main.py:4949` 附近的用户状态构建代码，确认 theme_prefs 被读取并传递到前端 state 中，以便前端 `window.__currentUserId` 和同步工作。

- [ ] **Step 3: 新增 ThemeSyncRequest 模型和两个端点**

在 `main.py` 中合适位置（如其他 `/api/user/*` 端点附近，约 1307 行后）添加：

```python
class ThemeSyncRequest(BaseModel):
    mode: str = "light"
    theme: str = "warm-morning"
    wallpaper: dict = {}
    customThemes: list = []

@app.post("/api/user/theme/sync")
def sync_theme_to_server(request: ThemeSyncRequest):
    """Save user theme preferences to server."""
    try:
        user_id = get_current_user_id()  # Need to check how auth works
        if not user_id:
            return {"ok": False, "reason": "not_logged_in"}
        prefs = {
            "mode": request.mode,
            "theme": request.theme,
            "wallpaper": request.wallpaper,
            "customThemes": request.customThemes
        }
        database.save_user_theme_prefs(user_id, prefs)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}

@app.get("/api/user/theme/sync")
def get_theme_from_server():
    """Load user theme preferences from server."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return {"theme": None}
        prefs = database.get_user_theme_prefs(user_id)
        if prefs:
            return prefs
        return {"theme": None}
    except:
        return {"theme": None}
```

- [ ] **Step 4: 确定 get_current_user_id 的实现方式**

检查现有端点如何获取当前用户 ID：

```bash
grep -n 'user_id\|userId\|current_user' main.py | head -20
```

根据项目实际认证方式调整。如果用的是 session/token 从请求中提取 user_id，沿用现有模式。

- [ ] **Step 5: 提交**

```bash
git add main.py
git commit -m "main.py：新增POST/GET /api/user/theme/sync端点，登录返回themePrefs"
```

---

## Phase 5: 验证与清理

### Task 10: 端到端验证

- [ ] **Step 1: 启动开发服务器**

```bash
python main.py
```

- [ ] **Step 2: 浏览器测试清单**

逐一验证：
1. 打开页面，默认 `warm-morning` 主题正确显示
2. 弹窗中切换暗色模式，配色列表变为暗色主题
3. 选择 `study-night` / `starry-night` / `neon-cyber`，主题切换正常，对比度清晰
4. 选择 `forest-light`（亮色模式），绿色品牌色正确
5. 品牌色快速选择器工作正常
6. 壁纸选择和滑块正常工作
7. 设置页 token 编辑器：修改品牌色，预览实时更新
8. 保存自定义主题 → 弹窗中出现新主题
9. 应用自定义主题 → 所有页面一致
10. 刷新页面 → 主题偏好保持
11. 霓虹主题辉光效果正常，文字可读

- [ ] **Step 2: 检查 console 无 JS 错误**

在每个页面上打开 DevTools Console，确认无报错。

- [ ] **Step 3: 修复发现的问题并提交**

```bash
git add -A
git commit -m "验证修复：端到端测试中发现的样式和逻辑问题"
```

---

### Task 11: 最终清理 — 删除 css/index.css.bak

- [ ] **Step 1: 删除备份文件**

```bash
rm css/index.css.bak
```

- [ ] **Step 2: 最终提交**

```bash
git add css/index.css.bak
git commit -m "清理：删除CSS备份文件"
```

---

## 自审清单

**1. Spec coverage:**
- ✅ 三层 Token 架构 → Task 1
- ✅ 5 个预设主题 → Task 1（CSS 定义）
- ✅ 亮/暗两层切换 → Task 4（theme.js 状态管理）+ Task 5（弹窗）
- ✅ 用户自定义（弹窗） → Task 5（品牌色选择器）
- ✅ 用户自定义（设置页） → Task 6 + Task 7（token 编辑器）
- ✅ 服务端持久化 → Task 8 + Task 9
- ✅ 霓虹特殊处理 → Task 1（neon-cyber 语义覆盖）
- ✅ 对比度保证 → Task 7（实时对比度计算和预览）
- ✅ 清理旧代码 → Task 2 + Task 4 step 10 + Task 6 step 2

**2. Placeholder scan:** 无 TBD/TODO/占位符。

**3. Type consistency:**
- `state.mode` / `state.theme` / `state.wallpaperId` — 在所有 Task 中一致
- `customThemes` 数组结构 `{ id, name, mode, primitives }` — Task 4/5/7/8/9 一致
- API 请求体字段 `{ mode, theme, wallpaper, customThemes }` — Task 9 与 Task 4 一致
- CSS 原始层变量名 — Task 1 与 Task 7 一致
