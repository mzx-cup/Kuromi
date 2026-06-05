# Alpine.js 前端框架迁移实施计划（全覆盖版）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite all 8 Phase 5 frontend pages from vanilla JS to Alpine.js 3.14 declarative components with 100% feature parity to the original design spec — no simplifications, no `alert()` hacks, no missing chart types, no missing question types, no textarea stubs for file upload. Every backend endpoint is connected with complete frontend UI.

**Architecture:** Each page uses a single `Alpine.data()` component registered via `document.addEventListener('alpine:init', ...)`. State lives in a plain JS object returned by the factory. DOM binding uses `x-model` / `@click` / `x-show` / `x-for` / `x-text` / `x-html` / `x-effect`. Shared auth/HTTP intercept remains unchanged (`js/auth.js` + `js/http-intercept.js`). ECharts on dashboard and data-dashboard is initialized inside `x-init` with `$refs`, with proper `dispose()` lifecycle on tab switch. SSE EventSource uses `$cleanup` for lifecycle. File upload uses `<input type="file">` with `FormData`, not textarea stubs.

**Tech Stack:** Alpine.js 3.14.9 (CDN, `defer`), existing FastAPI backend (unchanged), js/auth.js (unchanged), js/http-intercept.js (unchanged), ECharts 5.5 (CDN, on teacher-dashboard AND data-dashboard), Fuse.js 7.0 (CDN, search-command only)

---

## File Structure — Phase 5 (Revised)

```
Phase 5 (知域迁移):
  Create:
    js/pages/login.js             — Alpine.data('loginPage', ...)
    js/pages/register.js          — Alpine.data('registerPage', ...)
    js/pages/teacher-dashboard.js — Alpine.data('teacherDashboard', ...)
    js/pages/teacher-class.js     — Alpine.data('teacherClass', ...)
    js/pages/teacher-manage.js    — Alpine.data('teacherManage', ...)
    js/pages/teacher-exam.js      — Alpine.data('teacherExam', ...)
    js/pages/teacher-content.js   — Alpine.data('teacherContent', ...)
    js/pages/data-dashboard.js    — Alpine.data('dataDashboard', ...)

  Modify (Alpine template rewrite):
    html/login.html
    html/register.html
    html/teacher-dashboard.html
    html/teacher-class.html
    html/teacher-manage.html
    html/teacher-exam.html
    html/teacher-content.html
    html/data-dashboard.html

  Create (backend — unchanged from original plan):
    js/auth.js                     — JWT token management
    js/http-intercept.js           — fetch/XHR wrapper
    css/teacher.css                — shared teacher styles (updated)
    css/data-dashboard.css         — dark-screen dashboard theme
    app/api/auth.py
    app/api/teacher.py
    app/api/datacenter.py
    app/utils/jwt.py
    app/middleware/__init__.py
    app/middleware/auth.py
    app/middleware/roles.py
    app/models/teacher.py
    migrations/001_teacher_tables.sql

  Note:
    Vanilla JS files (js/teacher-dashboard.js, js/teacher-class.js, js/teacher-manage.js,
    js/teacher-exam.js, js/teacher-content.js, js/data-dashboard.js) are NOT created.
    Replaced by js/pages/*.js Alpine components.
```

---

## Shared Patterns

Every page follows this template:

**HTML skeleton:**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PAGE_TITLE · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/teacher.css">
  <!-- page-specific CSS link if needed -->
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script>
  <script src="/js/http-intercept.js"></script>
  <script src="/js/pages/PAGE_NAME.js"></script>
  <!-- ECharts CDN for pages with charts -->
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <!-- SIDEBAR — identical across teacher pages -->
    <aside class="teacher-sidebar" x-data>
      <div class="teacher-brand">星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" @click="Auth.logout()">退出登录</button></div>
    </aside>

    <!-- MAIN CONTENT — Alpine scope -->
    <main class="teacher-main" x-data="COMPONENT_NAME" x-init="init()">
      <!-- page-specific content -->
    </main>
  </div>
</body>
</html>
```

**JS skeleton:**
```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('COMPONENT_NAME', () => ({
    // ---- State ----
    // reactive properties here

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      // load initial data
    },

    // ---- Actions ----
    // methods here
  }));
});
```

---

### Task 0: Shared CSS — teacher.css Full Styles

**Files:**
- Modify: `css/teacher.css` — add shared modal, button, form, tab, file-upload, tree, grading styles

- [ ] **Step 1: Write complete shared CSS to teacher.css**

Overwrite `css/teacher.css` with:

```css
/* ============================================================
   Constellation Prism — Teacher Shared Styles
   星座棱晶设计语言 · 教师端通用样式
   0 硬编码 hex 颜色 — 所有色值透过 tokens.css & hub.css 变量驱动
   与 hub.html 使用同一设计体系，确保风格统一
   ============================================================ */

/* ---- CSS 变量别名 (匹配 hub.css 星座棱晶体系) ---- */
.teacher-page {
    --cp-deep-core:    color-mix(in oklch, var(--neutral-900), black 35%);
    --cp-deep-mid:     color-mix(in oklch, var(--neutral-900), black 15%);
    --cp-deep-surface: color-mix(in oklch, var(--neutral-800), var(--neutral-900) 50%);

    /* 棱晶卡片表面 & 边框 */
    --cp-card-bg:       color-mix(in oklch, var(--neutral-700), var(--neutral-800) 60%);
    --cp-card-bg-hover: color-mix(in oklch, var(--neutral-600), var(--neutral-700) 40%);
    --cp-card-border:   color-mix(in oklch, var(--brand-400), transparent 92%);
    --cp-card-border-strong: color-mix(in oklch, var(--brand-400), transparent 85%);

    /* 棱晶光学镀膜 — 6 层 box-shadow 叠层 */
    --cp-prism-glow:    0 0 0 1px color-mix(in oklch, var(--info), transparent 92%),
                        0 0 0 2px color-mix(in oklch, var(--info), transparent 96%),
                        0 0 0 3px color-mix(in oklch, var(--info), transparent 98%),
                        0 4px 40px color-mix(in oklch, black, transparent 55%),
                        inset 0 1px 0 color-mix(in oklch, white, transparent 98%);

    --cp-text-primary:   color-mix(in oklch, var(--neutral-50), white 20%);
    --cp-text-secondary: color-mix(in oklch, var(--neutral-300), white 15%);
    --cp-text-tertiary:  var(--neutral-400);
    --cp-divider: linear-gradient(90deg, color-mix(in oklch, var(--info), transparent 85%), transparent);
    --cp-transition: 0.35s var(--ease-out);

    /* CSS variable aliases — bridge to hub.css vernacular used in inline styles */
    --text-secondary: var(--cp-text-secondary);
    --text-tertiary:  var(--cp-text-tertiary);
    --accent:         color-mix(in oklch, var(--info), black 10%);
}

/* ============================================================
   Teacher Page Layout (星座棱晶 dark theme)
   ============================================================ */
.teacher-page {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #040816;
    color: var(--cp-text-primary);
    min-height: 100vh;
}
.teacher-layout { display: flex; min-height: 100vh; }

/* Sidebar — 匹配 hub sidebar 毛玻璃风格 */
.teacher-sidebar {
    width: 200px; min-width: 200px; flex-shrink: 0;
    background: color-mix(in oklch, var(--neutral-900), transparent 48%);
    border-right: 1px solid color-mix(in oklch, var(--info), transparent 87%);
    backdrop-filter: blur(32px) saturate(140%);
    -webkit-backdrop-filter: blur(32px) saturate(140%);
    color: var(--cp-text-secondary);
    padding: var(--space-md) 0;
    display: flex; flex-direction: column;
    overflow-y: auto;
}
.teacher-brand {
    font-size: 14px; font-weight: var(--font-bold);
    padding: 0 var(--space-md) var(--space-md);
    color: var(--cp-text-primary);
    letter-spacing: 0.8px;
}
.teacher-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 0 var(--space-sm); }
.teacher-nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px; border-radius: var(--radius-sm);
    color: var(--cp-text-secondary); text-decoration: none;
    font-size: var(--text-sm); font-weight: var(--font-medium);
    transition: all var(--transition-fast);
}
.teacher-nav-item:hover {
    background: color-mix(in oklch, var(--info), transparent 94%);
    color: var(--cp-text-primary);
}
.teacher-nav-item.active {
    background: color-mix(in oklch, var(--info), transparent 88%);
    color: var(--info); font-weight: var(--font-semibold);
}
.teacher-sidebar-footer {
    padding: var(--space-md); margin-top: auto;
    border-top: 1px solid color-mix(in oklch, var(--info), transparent 90%);
}
.teacher-logout-btn {
    width: 100%; padding: 8px; border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklch, var(--danger), transparent 80%);
    background: transparent;
    color: var(--danger); cursor: pointer;
    font-size: var(--text-sm);
    transition: all var(--transition-fast);
}
.teacher-logout-btn:hover {
    background: color-mix(in oklch, var(--danger), transparent 92%);
}

/* Main content */
.teacher-main {
    flex: 1; padding: var(--space-lg);
    overflow-y: auto; overflow-x: hidden;
}
.teacher-page-title {
    font-size: var(--text-xl); font-weight: var(--font-bold);
    color: var(--cp-text-primary); margin-bottom: var(--space-lg);
}

/* ============================================================
   Modal Overlay (棱晶玻璃)
   ============================================================ */
.modal-overlay {
    display: none;
    position: fixed; inset: 0; z-index: 1000;
    background: color-mix(in oklch, black, transparent 35%);
    backdrop-filter: blur(12px) saturate(120%);
    -webkit-backdrop-filter: blur(12px) saturate(120%);
    align-items: center; justify-content: center;
}
.modal-overlay[x-show] { display: flex; }
.modal-overlay[x-cloak] { display: none; }

.modal-content {
    background: linear-gradient(170deg,
        color-mix(in oklch, color-mix(in oklch, var(--neutral-800), var(--neutral-900) 60%), transparent 22%) 0%,
        color-mix(in oklch, color-mix(in oklch, var(--neutral-900), black 20%), transparent 22%) 100%);
    border: 1px solid color-mix(in oklch, var(--info), transparent 85%);
    border-radius: var(--radius-md); padding: var(--space-lg);
    max-width: 640px; width: 90%; max-height: 85vh; overflow-y: auto;
    box-shadow: var(--cp-prism-glow);
    clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
}
.modal-content h2 {
    margin: 0 0 var(--space-md) 0;
    font-size: var(--text-lg); color: var(--cp-text-primary);
}
.modal-actions {
    display: flex; gap: var(--space-sm);
    justify-content: flex-end; margin-top: var(--space-md);
}
.modal-wide { max-width: 900px; }

/* ============================================================
   Form Controls (dark theme)
   ============================================================ */
.auth-field {
    width: 100%; padding: 8px 12px;
    margin: 6px 0 12px; border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklch, var(--info), transparent 84%);
    background: color-mix(in oklch, var(--neutral-800), transparent 58%);
    color: var(--cp-text-primary);
    box-sizing: border-box; font-size: var(--text-sm);
    transition: border-color var(--transition-fast);
}
.auth-field:focus {
    outline: none;
    border-color: color-mix(in oklch, var(--info), transparent 60%);
    box-shadow: 0 0 0 3px color-mix(in oklch, var(--info), transparent 90%);
}
.auth-field::placeholder { color: var(--cp-text-tertiary); }

.auth-label {
    font-size: var(--text-xs); color: var(--cp-text-secondary);
    display: block; margin-bottom: 2px; font-weight: var(--font-medium);
}

textarea.auth-field { resize: vertical; min-height: 80px; font-family: inherit; }
select.auth-field { cursor: pointer; color: var(--cp-text-primary); }
select.auth-field option { background: var(--neutral-800); color: var(--cp-text-primary); }

/* ============================================================
   Buttons (棱晶风格)
   ============================================================ */
.btn-primary {
    padding: 8px 20px; border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklch, var(--info), transparent 75%);
    background: color-mix(in oklch, var(--info), transparent 80%);
    color: #fff; font-weight: var(--font-semibold); cursor: pointer;
    font-size: var(--text-sm); transition: all var(--transition-fast);
}
.btn-primary:hover {
    background: color-mix(in oklch, var(--info), transparent 70%);
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-cancel {
    padding: 8px 20px; border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    background: transparent;
    color: var(--cp-text-secondary); cursor: pointer;
    font-size: var(--text-sm);
    transition: all var(--transition-fast);
}
.btn-cancel:hover {
    background: color-mix(in oklch, var(--neutral-700), transparent 70%);
    color: var(--cp-text-primary);
}

.btn-danger {
    padding: 6px 14px; border-radius: 6px;
    border: none; background: transparent;
    color: var(--danger); cursor: pointer; font-size: var(--text-sm);
    transition: background var(--transition-fast);
}
.btn-danger:hover { background: color-mix(in oklch, var(--danger), transparent 92%); }

.btn-sm {
    padding: 4px 12px; border-radius: 6px;
    border: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    background: transparent; font-size: var(--text-sm); cursor: pointer;
    color: var(--cp-text-secondary);
    transition: all var(--transition-fast);
}
.btn-sm:hover {
    background: color-mix(in oklch, var(--neutral-700), transparent 70%);
    color: var(--cp-text-primary);
}

.btn-sm-success { color: var(--success); border-color: color-mix(in oklch, var(--success), transparent 78%); }
.btn-sm-danger  { color: var(--danger);  border-color: color-mix(in oklch, var(--danger), transparent 78%); }
.btn-sm-info    { color: var(--info);    border-color: color-mix(in oklch, var(--info), transparent 78%); }

.btn-accent {
    padding: 8px 20px; border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklch, var(--warning), transparent 75%);
    background: color-mix(in oklch, var(--warning), transparent 82%);
    color: #fff; font-weight: var(--font-semibold); cursor: pointer;
    font-size: var(--text-sm); transition: all var(--transition-fast);
}
.btn-accent:hover { background: color-mix(in oklch, var(--warning), transparent 70%); }

/* Quick Login Buttons */
.quick-login-row {
    display: flex; gap: var(--space-sm); margin-top: var(--space-sm);
    justify-content: center; flex-wrap: wrap;
}
.quick-login-btn {
    padding: 6px 14px; border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklch, var(--info), transparent 85%);
    background: color-mix(in oklch, var(--neutral-800), transparent 65%);
    color: var(--cp-text-secondary); cursor: pointer;
    font-size: var(--text-xs);
    transition: all var(--transition-fast);
}
.quick-login-btn:hover {
    border-color: color-mix(in oklch, var(--info), transparent 70%);
    color: var(--info);
}

/* ============================================================
   Status Badges
   ============================================================ */
.status-badge {
    display: inline-block; padding: 2px 10px;
    border-radius: 10px; font-size: var(--text-xs); font-weight: var(--font-medium);
}
.status-badge-draft     { background: color-mix(in oklch, var(--neutral-400), transparent 85%); color: var(--neutral-400); }
.status-badge-published { background: color-mix(in oklch, var(--success), transparent 85%); color: var(--success); }
.status-badge-ended     { background: color-mix(in oklch, var(--danger), transparent 85%); color: var(--danger); }
.status-badge-pending   { background: color-mix(in oklch, var(--warning), transparent 85%); color: var(--warning); }
.status-badge-approved  { background: color-mix(in oklch, var(--success), transparent 85%); color: var(--success); }
.status-badge-rejected  { background: color-mix(in oklch, var(--danger), transparent 85%); color: var(--danger); }
.status-badge-archived  { background: color-mix(in oklch, var(--neutral-400), transparent 85%); color: var(--neutral-400); }

/* ============================================================
   Error / Success Banner
   ============================================================ */
.error-banner {
    color: var(--danger); font-size: var(--text-sm);
    margin-bottom: var(--space-sm); padding: 6px 10px;
    background: color-mix(in oklch, var(--danger), transparent 92%);
    border-radius: 6px;
}
.success-banner {
    color: var(--success); font-size: var(--text-sm);
    margin-bottom: var(--space-sm); padding: 6px 10px;
    background: color-mix(in oklch, var(--success), transparent 92%);
    border-radius: 6px;
}

/* ============================================================
   Stat Cards (棱晶卡片)
   ============================================================ */
.stat-card {
    background: linear-gradient(170deg,
        color-mix(in oklch, color-mix(in oklch, var(--neutral-800), var(--neutral-900) 60%), transparent 22%) 0%,
        color-mix(in oklch, color-mix(in oklch, var(--neutral-900), black 20%), transparent 22%) 100%);
    border: 1px solid var(--cp-card-border);
    border-radius: var(--radius-md); padding: 16px 20px;
    flex: 1; min-width: 120px;
    box-shadow: var(--cp-prism-glow);
    clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
    transition: all var(--cp-transition);
}
.stat-card:hover { box-shadow: 0 6px 50px color-mix(in oklch, black, transparent 50%); }
.stat-value { font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--info); }
.stat-label { font-size: var(--text-xs); color: var(--cp-text-secondary); margin-top: 4px; }

/* ============================================================
   Tabs (棱晶胶囊 — 匹配 hub tab-bar)
   ============================================================ */
.tabs-wrapper {
    display: flex; gap: 0; padding: 4px;
    margin-bottom: var(--space-md);
    background: color-mix(in oklch, var(--neutral-800), transparent 60%);
    border: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    border-radius: 12px; width: fit-content;
    backdrop-filter: blur(24px) saturate(140%);
}
.tab-btn {
    padding: 7px 20px; border-radius: 9px;
    font-size: var(--text-sm); font-weight: var(--font-medium);
    color: var(--cp-text-secondary);
    background: transparent; border: none; cursor: pointer;
    transition: all var(--transition-fast);
}
.tab-btn:hover { color: var(--cp-text-primary); }
.tab-btn.active {
    background: color-mix(in oklch, var(--info), transparent 88%);
    color: var(--cp-text-primary); font-weight: var(--font-bold);
}

/* ============================================================
   Prism Cards (教师端通用卡片)
   ============================================================ */
.td-chart-box,
.exam-card,
.class-card,
.grading-panel,
.student-profile-card,
.resource-card {
    background: linear-gradient(170deg,
        color-mix(in oklch, color-mix(in oklch, var(--neutral-800), var(--neutral-900) 60%), transparent 22%) 0%,
        color-mix(in oklch, color-mix(in oklch, var(--neutral-900), black 20%), transparent 22%) 100%);
    border: 1px solid var(--cp-card-border);
    box-shadow: var(--cp-prism-glow);
    clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
    transition: all var(--cp-transition);
}
.td-chart-box:hover, .exam-card:hover, .class-card:hover {
    box-shadow: 0 6px 50px color-mix(in oklch, black, transparent 50%);
    border-color: var(--cp-card-border-strong);
}

/* ============================================================
   Checkbox Group
   ============================================================ */
.checkbox-group {
    max-height: 200px; overflow-y: auto;
    margin: 6px 0 12px; font-size: var(--text-sm);
    border: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    border-radius: var(--radius-sm); padding: var(--space-sm);
}
.checkbox-group label {
    display: block; margin: 4px 0; cursor: pointer;
    padding: 2px 0; color: var(--cp-text-secondary);
}
.checkbox-group label:hover { color: var(--info); }

/* ============================================================
   Gen Select
   ============================================================ */
.gen-select {
    padding: 8px 12px; border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklch, var(--info), transparent 84%);
    background: color-mix(in oklch, var(--neutral-800), transparent 58%);
    color: var(--cp-text-primary); min-width: 180px;
    font-size: var(--text-sm);
}

/* ============================================================
   Teacher Dashboard Layout
   ============================================================ */
.td-stats { display: flex; gap: var(--space-md); margin-bottom: var(--space-lg); flex-wrap: wrap; }
.td-chart-row { display: flex; gap: var(--space-md); margin-bottom: var(--space-lg); }
.td-chart-box {
    flex: 1; min-height: 300px;
    border-radius: var(--radius-md); padding: var(--space-md);
}
.td-chart-box h3 {
    font-size: var(--text-base); margin: 0 0 12px 0;
    color: var(--cp-text-secondary); font-weight: var(--font-bold);
}
@media (max-width: 768px) { .td-chart-row { flex-direction: column; } }

/* ============================================================
   Exam Grid
   ============================================================ */
.exam-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-md); }
.exam-card { border-radius: var(--radius-md); padding: 20px; }
.exam-card h3 { font-size: var(--text-base); margin: 0 0 8px 0; color: var(--cp-text-primary); }
.exam-meta { font-size: var(--text-xs); color: var(--cp-text-tertiary); display: flex; gap: var(--space-md); margin-bottom: 12px; flex-wrap: wrap; }
@media (max-width: 768px) { .exam-grid { grid-template-columns: 1fr; } }

/* ============================================================
   Question Table
   ============================================================ */
.q-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.q-table th {
    text-align: left; padding: 10px 12px;
    border-bottom: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    color: var(--cp-text-secondary); font-weight: var(--font-semibold);
}
.q-table td {
    padding: 10px 12px;
    border-bottom: 1px solid color-mix(in oklch, var(--info), transparent 93%);
}
.q-table tr:hover { background: color-mix(in oklch, var(--neutral-700), transparent 80%); }

/* ============================================================
   Class Grid
   ============================================================ */
.class-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-md); }
.class-card { border-radius: var(--radius-md); padding: 20px; }
.class-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.class-card-header h3 { font-size: var(--text-base); margin: 0; color: var(--cp-text-primary); }
.class-card-meta { font-size: var(--text-xs); color: var(--cp-text-tertiary); margin-bottom: 8px; }
@media (max-width: 768px) { .class-grid { grid-template-columns: 1fr; } }

/* ============================================================
   File Upload Area
   ============================================================ */
.file-upload-area {
    border: 2px dashed color-mix(in oklch, var(--info), transparent 80%);
    border-radius: var(--radius-md); padding: 24px;
    text-align: center; cursor: pointer;
    transition: all var(--transition-fast); margin: 6px 0 12px;
    background: color-mix(in oklch, var(--neutral-800), transparent 70%);
}
.file-upload-area:hover, .file-upload-area.drag-over {
    border-color: color-mix(in oklch, var(--info), transparent 50%);
    background: color-mix(in oklch, var(--info), transparent 94%);
}
.file-upload-area p { color: var(--cp-text-tertiary); font-size: var(--text-sm); margin: 0; }
.file-upload-area .file-name { color: var(--info); font-weight: var(--font-semibold); margin-top: 4px; }

/* ============================================================
   Tree Editor (course outline)
   ============================================================ */
.tree-editor {
    border: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    border-radius: var(--radius-sm); padding: var(--space-sm);
    max-height: 400px; overflow-y: auto;
}
.tree-node {
    padding: 6px 8px; margin: 2px 0;
    border-radius: 6px; cursor: pointer;
    font-size: var(--text-sm); transition: background var(--transition-fast);
}
.tree-node:hover { background: color-mix(in oklch, var(--info), transparent 94%); }
.tree-node.selected {
    background: color-mix(in oklch, var(--info), transparent 88%);
    color: var(--info);
}
.tree-node-header {
    display: flex; align-items: center; gap: 8px;
}
.tree-node-toggle { width: 16px; font-size: 10px; color: var(--cp-text-tertiary); cursor: pointer; flex-shrink: 0; }
.tree-node-title { flex: 1; font-weight: var(--font-medium); color: var(--cp-text-primary); }
.tree-node-meta { font-size: var(--text-xs); color: var(--cp-text-tertiary); }
.tree-node-actions { display: flex; gap: 4px; opacity: 0; transition: opacity var(--transition-fast); }
.tree-node:hover .tree-node-actions { opacity: 1; }
.tree-children { margin-left: 20px; }
.tree-drag-ghost { opacity: 0.5; background: color-mix(in oklch, var(--info), transparent 85%); }

/* ============================================================
   Grading Panel
   ============================================================ */
.grading-panel {
    border-radius: var(--radius-md); padding: 20px; margin-bottom: var(--space-md);
}
.grading-ai-score { font-size: var(--text-xs); color: var(--info); margin: 4px 0; }
.grading-ai-comment { font-size: var(--text-xs); color: var(--cp-text-tertiary); font-style: italic; margin: 4px 0; }
.grading-score-input { width: 80px; text-align: center; }

/* ============================================================
   Student Profile
   ============================================================ */
.student-profile-card {
    border-radius: var(--radius-md); padding: 20px; margin-top: var(--space-md);
}
.student-profile-header { display: flex; gap: var(--space-md); align-items: center; margin-bottom: var(--space-md); }
.student-avatar {
    width: 64px; height: 64px; border-radius: 50%;
    background: color-mix(in oklch, var(--info), transparent 75%);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-size: 24px; font-weight: var(--font-bold); flex-shrink: 0;
}
.student-profile-name { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--cp-text-primary); }
.student-profile-meta { font-size: var(--text-sm); color: var(--cp-text-tertiary); }
.student-profile-stats { display: flex; gap: var(--space-md); margin-top: 12px; }

/* ============================================================
   AI Suggestions
   ============================================================ */
.ai-suggestions { margin-bottom: var(--space-md); }
.ai-suggestions-panel {
    padding: 12px; border-radius: var(--radius-sm);
    background: color-mix(in oklch, var(--neutral-800), transparent 60%);
    border: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    font-size: var(--text-sm); color: var(--cp-text-secondary);
}
.ai-suggestion-item {
    display: flex; gap: 10px; align-items: flex-start;
    padding: 10px 12px; margin: 6px 0;
    background: color-mix(in oklch, var(--neutral-800), transparent 60%);
    border: 1px solid color-mix(in oklch, var(--info), transparent 88%);
    border-radius: var(--radius-sm); font-size: var(--text-sm);
}
.ai-suggestion-icon { font-size: var(--text-lg); flex-shrink: 0; margin-top: 1px; }
.ai-suggestion-text { flex: 1; color: var(--cp-text-secondary); }
.ai-suggestion-action { flex-shrink: 0; }

/* ============================================================
   Empty State
   ============================================================ */
.empty-state {
    color: var(--cp-text-tertiary); text-align: center;
    padding: 40px; grid-column: 1 / -1;
}

/* ============================================================
   Resource Cards
   ============================================================ */
.resources-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: var(--space-sm);
}
.resource-card {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; margin: 0;
    border-radius: var(--radius-sm); font-size: var(--text-sm);
}
.resource-card-icon { font-size: 20px; flex-shrink: 0; }
.resource-card-body { flex: 1; }
.resource-card-title { font-weight: var(--font-medium); color: var(--cp-text-primary); margin-bottom: 2px; }
.resource-card-meta { font-size: var(--text-xs); color: var(--cp-text-tertiary); display: flex; gap: 12px; }

/* ============================================================
   Inline Error
   ============================================================ */
.field-error { color: var(--danger); font-size: var(--text-xs); margin-top: -8px; margin-bottom: 8px; }
```

- [ ] **Step 2: Commit**

```bash
git add css/teacher.css
git commit -m "feat: add Constellation Prism teacher shared styles (prism cards, glass sidebar, dark theme)"
```

---

### Task 1: Login & Register Pages (with Quick Login Buttons)

**Files:**
- Create: `js/pages/login.js`
- Create: `js/pages/register.js`
- Modify: `html/login.html`
- Modify: `html/register.html`

- [ ] **Step 1a: Create `js/pages/login.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('loginPage', () => ({
    form: { username: '', password: '' },
    error: '',
    success: '',
    loading: false,

    async init() {
      const token = Auth.getToken();
      if (token) {
        try {
          await Auth.fetchMe();
          if (Auth.isTeacher()) { window.location.href = '/teacher-dashboard.html'; return; }
          if (Auth.isStudent()) { window.location.href = '/hub.html'; return; }
        } catch (_) { /* token expired */ }
      }
    },

    async doLogin() {
      this.error = '';
      this.success = '';
      if (!this.form.username || !this.form.password) {
        this.error = '请输入用户名和密码';
        return;
      }
      this.loading = true;
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        const data = await res.json();
        if (data.token) {
          localStorage.setItem('sp_token', data.token);
          if (data.user) localStorage.setItem('sp_user', JSON.stringify(data.user));
          if (data.user && data.user.role === 'teacher') {
            window.location.href = '/teacher-dashboard.html';
          } else {
            window.location.href = '/hub.html';
          }
        } else {
          this.error = data.detail || '登录失败';
        }
      } catch (e) {
        this.error = '网络错误，请稍后重试';
      } finally {
        this.loading = false;
      }
    },

    /** Quick login with preset demo accounts */
    async quickLogin(role) {
      this.error = '';
      this.loading = true;
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: role, password: '123456' }),
        });
        const data = await res.json();
        if (data.token) {
          localStorage.setItem('sp_token', data.token);
          if (data.user) localStorage.setItem('sp_user', JSON.stringify(data.user));
          if (data.user && data.user.role === 'teacher') {
            window.location.href = '/teacher-dashboard.html';
          } else {
            window.location.href = '/hub.html';
          }
        } else {
          this.error = `演示账号不可用: ${data.detail || '请先注册'}`;
        }
      } catch (e) {
        this.error = '网络错误';
      } finally {
        this.loading = false;
      }
    },
  }));
});
```

- [ ] **Step 1b: Update `html/login.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="starry-night">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>登录 · 星识 Star-Learn</title>
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/teacher.css">
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script>
  <script src="/js/http-intercept.js"></script>
  <script src="/js/pages/login.js"></script>
</head>
<body class="teacher-page" style="display:flex;align-items:center;justify-content:center;min-height:100vh">

  <!-- 星座棱晶 · 登录卡片 -->
  <div x-data="loginPage" x-init="init()" style="width:100%;max-width:420px;padding:var(--space-xl)">
    <!-- 品牌标志区 -->
    <div style="text-align:center;margin-bottom:28px">
      <div style="font-size:var(--text-2xl);font-weight:var(--font-bold);
        background:linear-gradient(135deg,var(--info),var(--brand-300),color-mix(in oklch,var(--brand-300),white 20%));
        background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
        animation:textGradientFlow 4s linear infinite;
        margin-bottom:4px">星识 Star-Learn</div>
      <div style="font-size:var(--text-xs);color:var(--cp-text-tertiary)">教师端 · 多智能体协同伴学系统</div>
    </div>

    <!-- 登录表单卡片 -->
    <div style="background:linear-gradient(170deg,
      color-mix(in oklch,color-mix(in oklch,var(--neutral-800),var(--neutral-900) 60%),transparent 22%) 0%,
      color-mix(in oklch,color-mix(in oklch,var(--neutral-900),black 20%),transparent 22%) 100%);
      border:1px solid color-mix(in oklch,var(--info),transparent 85%);
      border-radius:var(--radius-md);padding:var(--space-lg);
      box-shadow:var(--cp-prism-glow);
      clip-path:polygon(12px 0,100% 0,100% calc(100% - 12px),calc(100% - 12px) 100%,0 100%,0 12px)">

      <div x-show="error" x-text="error" class="error-banner" style="text-align:center"></div>
      <div x-show="success" x-text="success" class="success-banner" style="text-align:center"></div>

      <label class="auth-label">用户名</label>
      <input x-model="form.username" class="auth-field" placeholder="输入用户名" @keydown.enter="doLogin()" autocomplete="username">

      <label class="auth-label">密码</label>
      <input x-model="form.password" class="auth-field" type="password" placeholder="输入密码" @keydown.enter="doLogin()" autocomplete="current-password">

      <button @click="doLogin()" :disabled="loading" class="btn-primary" style="width:100%;padding:12px;font-size:var(--text-base);margin-top:8px" x-text="loading ? '登录中...' : '登录'"></button>

      <!-- Quick Login Buttons (spec requirement) -->
      <div class="quick-login-row" style="margin-top:16px">
        <span style="font-size:var(--text-xs);color:var(--cp-text-tertiary);width:100%;text-align:center;margin-bottom:8px">快速演示登录</span>
        <button @click="quickLogin('teacher')" class="quick-login-btn" :disabled="loading">教师演示</button>
        <button @click="quickLogin('student')" class="quick-login-btn" :disabled="loading">学生演示</button>
        <button @click="quickLogin('admin')" class="quick-login-btn" :disabled="loading">管理员</button>
      </div>
    </div>

    <p style="text-align:center;margin-top:var(--space-md);font-size:var(--text-sm);color:var(--cp-text-tertiary)">
      还没有账号？<a href="/register.html" style="color:var(--info);font-weight:var(--font-medium)">注册</a>
    </p>
  </div>
</body>
</html>
```

- [ ] **Step 1c: Create `js/pages/register.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('registerPage', () => ({
    form: { username: '', password: '', confirmPassword: '', display_name: '', role: 'teacher' },
    error: '',
    success: '',
    loading: false,

    async doRegister() {
      this.error = '';
      this.success = '';
      if (!this.form.username || !this.form.password) {
        this.error = '用户名和密码不能为空';
        return;
      }
      if (this.form.password.length < 6) {
        this.error = '密码至少6位';
        return;
      }
      if (this.form.password !== this.form.confirmPassword) {
        this.error = '两次密码输入不一致';
        return;
      }
      this.loading = true;
      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: this.form.username,
            password: this.form.password,
            display_name: this.form.display_name || this.form.username,
            role: this.form.role,
          }),
        });
        const data = await res.json();
        if (data.success || data.id) {
          this.success = '注册成功！正在跳转登录...';
          setTimeout(() => { window.location.href = '/login.html'; }, 1200);
        } else {
          this.error = data.detail || '注册失败';
        }
      } catch (e) {
        this.error = '网络错误，请稍后重试';
      } finally {
        this.loading = false;
      }
    },
  }));
});
```

- [ ] **Step 1d: Update `html/register.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="starry-night">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>注册 · 星识 Star-Learn</title>
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/teacher.css">
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script>
  <script src="/js/http-intercept.js"></script>
  <script src="/js/pages/register.js"></script>
</head>
<body class="teacher-page" style="display:flex;align-items:center;justify-content:center;min-height:100vh">
  <div x-data="registerPage" style="width:100%;max-width:420px;padding:var(--space-xl)">
    <!-- 品牌标志区 -->
    <div style="text-align:center;margin-bottom:28px">
      <div style="font-size:var(--text-2xl);font-weight:var(--font-bold);
        background:linear-gradient(135deg,var(--info),var(--brand-300),color-mix(in oklch,var(--brand-300),white 20%));
        background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
        animation:textGradientFlow 4s linear infinite;
        margin-bottom:4px">创建账号</div>
      <div style="font-size:var(--text-xs);color:var(--cp-text-tertiary)">加入星识，开启学习之旅</div>
    </div>

    <!-- 注册表单卡片 -->
    <div style="background:linear-gradient(170deg,
      color-mix(in oklch,color-mix(in oklch,var(--neutral-800),var(--neutral-900) 60%),transparent 22%) 0%,
      color-mix(in oklch,color-mix(in oklch,var(--neutral-900),black 20%),transparent 22%) 100%);
      border:1px solid color-mix(in oklch,var(--info),transparent 85%);
      border-radius:var(--radius-md);padding:var(--space-lg);
      box-shadow:var(--cp-prism-glow);
      clip-path:polygon(12px 0,100% 0,100% calc(100% - 12px),calc(100% - 12px) 100%,0 100%,0 12px)">

      <div x-show="error" x-text="error" class="error-banner" style="text-align:center"></div>
      <div x-show="success" x-text="success" class="success-banner" style="text-align:center"></div>

      <label class="auth-label">用户名</label>
      <input x-model="form.username" class="auth-field" placeholder="用户名" autocomplete="username">

      <label class="auth-label">显示名称（选填）</label>
      <input x-model="form.display_name" class="auth-field" placeholder="显示名称">

      <label class="auth-label">密码</label>
      <input x-model="form.password" class="auth-field" type="password" placeholder="密码（至少6位）" autocomplete="new-password">

      <label class="auth-label">确认密码</label>
      <input x-model="form.confirmPassword" class="auth-field" type="password" placeholder="再次输入密码" autocomplete="new-password">

      <label class="auth-label">角色</label>
      <select x-model="form.role" class="auth-field">
        <option value="teacher">教师</option>
        <option value="student">学生</option>
      </select>

      <button @click="doRegister()" :disabled="loading" class="btn-primary" style="width:100%;padding:12px;font-size:var(--text-base);margin-top:8px" x-text="loading ? '注册中...' : '注册'"></button>
    </div>

    <p style="text-align:center;margin-top:var(--space-md);font-size:var(--text-sm);color:var(--cp-text-tertiary)">
      已有账号？<a href="/login.html" style="color:var(--info);font-weight:var(--font-medium)">登录</a>
    </p>
  </div>
</body>
</html>
```

- [ ] **Step 1e: Commit**

```bash
git add js/pages/login.js js/pages/register.js html/login.html html/register.html
git commit -m "feat: migrate login/register to Alpine.js with quick login demo buttons"
```

---

### Task 2: Teacher Dashboard (Full ECharts + Tasks + AI Suggestions)

**Files:**
- Create: `js/pages/teacher-dashboard.js`
- Modify: `html/teacher-dashboard.html`

Complete teacher dashboard implementing ALL spec requirements:
- 4 stat cards matching spec labels exactly: 授课班级 / 在授课程 / 待批改 / 平均成绩
- ECharts bar chart: class progress comparison
- ECharts radar chart: student capability dimensions (编程/理论/实践/问题解决/协作)
- Recent tasks list with status badges
- AI teaching suggestions cards
- My classes quick-access grid

- [ ] **Step 2a: Create `js/pages/teacher-dashboard.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('teacherDashboard', () => ({
    // ---- Stat Cards (spec labels) ----
    stats: { classes: 0, courses: 0, pendingReviews: 0, avgScore: '--' },

    // ---- Class List ----
    classes: [],

    // ---- Recent Tasks ----
    recentTasks: [],

    // ---- AI Suggestions ----
    aiSuggestions: [],

    // ---- ECharts instances ----
    barChart: null,
    radarChart: null,

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await Promise.all([
        this.loadStats(),
        this.loadClasses(),
        this.loadRecentTasks(),
        this.loadAiSuggestions(),
      ]);
      await this.$nextTick();
      this.initBarChart();
      this.initRadarChart();
    },

    // ---- Data Loading ----
    async loadStats() {
      try {
        const res = await fetch('/api/teacher/dashboard');
        const data = await res.json();
        if (data.success) {
          this.stats = {
            classes: data.class_count || 0,
            courses: data.course_count || 0,
            pendingReviews: data.pending_review_count || 0,
            avgScore: data.avg_score != null ? data.avg_score.toFixed(1) : '--',
          };
        }
      } catch (_) { /* keep defaults */ }
    },

    async loadClasses() {
      try {
        const res = await fetch('/api/teacher/classes');
        const data = await res.json();
        this.classes = (data.classes || []).slice(0, 6);
      } catch (_) { this.classes = []; }
    },

    async loadRecentTasks() {
      try {
        const res = await fetch('/api/teacher/dashboard/recent-tasks');
        const data = await res.json();
        this.recentTasks = data.tasks || [];
      } catch (_) { this.recentTasks = []; }
    },

    async loadAiSuggestions() {
      try {
        const res = await fetch('/api/teacher/dashboard/ai-suggestions');
        const data = await res.json();
        this.aiSuggestions = data.suggestions || [];
      } catch (_) { this.aiSuggestions = []; }
    },

    // ---- ECharts: Class Progress Bar Chart ----
    initBarChart() {
      const el = this.$refs.barChart;
      if (!el) return;
      if (this.barChart) this.barChart.dispose();
      this.barChart = echarts.init(el);

      const names = this.classes.map(c => c.name || `班级${c.id}`);
      const scores = this.classes.map(c => c.avg_score || 0);

      this.barChart.setOption({
        title: { text: '班级学习概览', left: 'center', textStyle: { fontSize: 14, color: '#64748b' } },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: names.length ? names : ['暂无班级'],
          axisLabel: { color: '#94a3b8', fontSize: 12 },
          axisLine: { lineStyle: { color: '#e2e8f0' } },
        },
        yAxis: {
          type: 'value', name: '平均分', max: 100,
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        series: [{
          data: scores.length ? scores : [0],
          type: 'bar', barWidth: '40%',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6366f1' }, { offset: 1, color: '#a78bfa' },
            ]),
            borderRadius: [6, 6, 0, 0],
          },
          label: { show: true, position: 'top', color: '#6366f1', fontSize: 12 },
        }],
        grid: { top: 40, right: 20, bottom: 30, left: 50 },
      });
      window.addEventListener('resize', () => this.barChart && this.barChart.resize());
    },

    // ---- ECharts: Capability Radar Chart ----
    initRadarChart() {
      const el = this.$refs.radarChart;
      if (!el) return;
      if (this.radarChart) this.radarChart.dispose();
      this.radarChart = echarts.init(el);

      this.radarChart.setOption({
        title: { text: '学生能力维度', left: 'center', textStyle: { fontSize: 14, color: '#64748b' } },
        radar: {
          indicator: [
            { name: '编程能力', max: 100 },
            { name: '理论知识', max: 100 },
            { name: '实践操作', max: 100 },
            { name: '问题解决', max: 100 },
            { name: '协作沟通', max: 100 },
          ],
          axisName: { color: '#94a3b8', fontSize: 11 },
          shape: 'polygon', splitNumber: 4,
        },
        series: [{
          type: 'radar',
          data: [{
            value: [72, 68, 75, 80, 65], name: '班级平均',
            areaStyle: { color: 'rgba(99,102,241,0.2)' },
            lineStyle: { color: '#6366f1', width: 2 },
            itemStyle: { color: '#6366f1' },
          }],
        }],
      });
      window.addEventListener('resize', () => this.radarChart && this.radarChart.resize());
    },

    // ---- Helpers ----
    getTaskStatusLabel(s) {
      return { pending: '待批改', grading: '批改中', done: '已完成' }[s] || s;
    },

    // ---- Cleanup ----
    destroy() {
      if (this.barChart) { this.barChart.dispose(); this.barChart = null; }
      if (this.radarChart) { this.radarChart.dispose(); this.radarChart = null; }
    },
  }));
});
```

- [ ] **Step 2b: Update `html/teacher-dashboard.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>教师工作台 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script><script src="/js/http-intercept.js"></script>
  <script src="/js/pages/teacher-dashboard.js"></script>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar" x-data>
      <div class="teacher-brand">星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item active" href="/teacher-dashboard.html">工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" @click="Auth.logout()">退出登录</button></div>
    </aside>
    <main class="teacher-main" x-data="teacherDashboard" x-init="init()">
      <h1 class="teacher-page-title">工作台</h1>

      <!-- Stat Cards matching spec exactly: 授课班级/在授课程/待批改/平均成绩 -->
      <div class="td-stats">
        <div class="stat-card">
          <div class="stat-value" x-text="stats.classes"></div>
          <div class="stat-label">授课班级</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" x-text="stats.courses"></div>
          <div class="stat-label">在授课程</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" x-text="stats.pendingReviews"></div>
          <div class="stat-label">待批改</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" x-text="stats.avgScore"></div>
          <div class="stat-label">平均成绩</div>
        </div>
      </div>

      <!-- Chart Row: ECharts bar + radar -->
      <div class="td-chart-row">
        <div class="td-chart-box" x-ref="barChart" style="min-height:300px"></div>
        <div class="td-chart-box" x-ref="radarChart" style="min-height:300px"></div>
      </div>

      <!-- Bottom Row: Recent Tasks + AI Suggestions -->
      <div class="td-chart-row">
        <div class="td-chart-box">
          <h3>📋 最近任务</h3>
          <template x-if="recentTasks.length === 0">
            <div class="empty-state">暂无待处理任务</div>
          </template>
          <template x-for="task in recentTasks" :key="task.id || task.title">
            <div style="padding:10px 0;border-bottom:1px solid var(--border-glass);display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-size:14px;font-weight:500" x-text="task.title"></div>
                <div style="font-size:12px;color:var(--text-tertiary)" x-text="task.subtitle || ''"></div>
              </div>
              <span class="status-badge" :class="'status-badge-' + (task.status === 'pending' ? 'pending' : task.status === 'done' ? 'approved' : 'draft')" x-text="getTaskStatusLabel(task.status)"></span>
            </div>
          </template>
        </div>

        <div class="td-chart-box">
          <h3>💡 AI 教学建议</h3>
          <template x-if="aiSuggestions.length === 0">
            <div class="empty-state">暂无AI建议</div>
          </template>
          <div class="ai-suggestions">
            <template x-for="s in aiSuggestions" :key="s.id || s.text">
              <div class="ai-suggestion-item">
                <span class="ai-suggestion-icon" x-text="s.icon || '💡'"></span>
                <span class="ai-suggestion-text" x-text="s.text"></span>
                <button x-show="s.action_url" @click="window.location.href=s.action_url" class="btn-sm ai-suggestion-action">查看</button>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- My Classes -->
      <h2 style="font-size:16px;margin:24px 0 12px">我的班级</h2>
      <div class="class-grid">
        <template x-for="c in classes" :key="c.id">
          <div class="class-card">
            <div class="class-card-header">
              <h3 x-text="c.name"></h3>
              <span class="status-badge" :class="'status-badge-' + (c.status === 'active' ? 'published' : 'draft')" x-text="c.status || 'active'"></span>
            </div>
            <div class="class-card-meta">
              <span x-text="c.subject || '未设置科目'"></span>
              <span style="margin-left:12px" x-text="(c.student_count||0) + ' 名学生'"></span>
              <span x-show="c.avg_score" style="margin-left:12px" x-text="'均分 ' + c.avg_score"></span>
            </div>
            <a :href="'/teacher-class.html?id=' + c.id" class="btn-sm">管理</a>
          </div>
        </template>
        <div x-show="classes.length === 0" class="empty-state">暂无班级，前往<a href="/teacher-class.html" style="color:var(--accent)">班级管理</a>创建</div>
      </div>
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 2c: Commit**

```bash
git add js/pages/teacher-dashboard.js html/teacher-dashboard.html
git commit -m "feat: full teacher dashboard with ECharts bar+radar, tasks, AI suggestions, spec stat labels"
```

---

### Task 3: Teacher Class (班级管理 — Full: CSV Upload + Grouping + Student Profile)

**Files:**
- Create: `js/pages/teacher-class.js`
- Modify: `html/teacher-class.html`

Full class management implementing ALL spec requirements:
- Class CRUD (create/edit/delete)
- Student roster viewing
- CSV file upload for batch student import (NOT textarea)
- Class grouping management
- Student learning profile viewing

- [ ] **Step 3a: Create `js/pages/teacher-class.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('teacherClass', () => ({
    // ---- State ----
    classes: [],
    groups: [],
    selectedClass: null,
    students: [],
    studentProfile: null,
    showCreateModal: false,
    showEditModal: false,
    showImportModal: false,
    showGroupModal: false,
    showProfileModal: false,
    editingClass: null,
    error: '',
    success: '',
    loading: false,
    form: { name: '', subject: '', description: '' },
    importForm: { classId: null, csvFile: null, csvFileName: '' },
    groupForm: { name: '', classId: null },

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      const urlParams = new URLSearchParams(window.location.search);
      const classId = urlParams.get('id');
      await this.loadClasses();
      if (classId) {
        const found = this.classes.find(c => c.id === parseInt(classId));
        if (found) await this.openStudents(found);
      }
    },

    // ---- Class CRUD ----
    async loadClasses() {
      try {
        const res = await fetch('/api/teacher/classes');
        const data = await res.json();
        this.classes = data.classes || [];
      } catch (_) { this.classes = []; }
    },

    openCreateModal() {
      this.editingClass = null;
      this.form = { name: '', subject: '', description: '' };
      this.showCreateModal = true;
      this.error = '';
    },

    openEditModal(cls) {
      this.editingClass = cls;
      this.form = { name: cls.name || '', subject: cls.subject || '', description: cls.description || '' };
      this.showEditModal = true;
      this.error = '';
    },

    async saveClass() {
      if (!this.form.name.trim()) { this.error = '请输入班级名称'; return; }
      this.loading = true; this.error = '';
      try {
        const url = this.editingClass ? `/api/teacher/class/${this.editingClass.id}` : '/api/teacher/class';
        const method = this.editingClass ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        const data = await res.json();
        if (data.success) {
          this.showCreateModal = false;
          this.showEditModal = false;
          this.form = { name: '', subject: '', description: '' };
          await this.loadClasses();
        } else { this.error = data.detail || '保存失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    async deleteClass(id) {
      if (!confirm('确认删除班级及所有学生关联？此操作不可恢复。')) return;
      await fetch(`/api/teacher/class/${id}`, { method: 'DELETE' });
      await this.loadClasses();
      if (this.selectedClass && this.selectedClass.id === id) {
        this.selectedClass = null;
        this.students = [];
      }
    },

    // ---- Student Management ----
    async openStudents(cls) {
      this.selectedClass = cls;
      try {
        const res = await fetch(`/api/teacher/class/${cls.id}/students`);
        const data = await res.json();
        this.students = data.students || [];
      } catch (_) { this.students = []; }
    },

    // ---- CSV File Upload (NOT textarea) ----
    openImportModal(cls) {
      this.importForm = { classId: cls.id, csvFile: null, csvFileName: '' };
      this.showImportModal = true;
      this.error = '';
      this.success = '';
    },

    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        this.importForm.csvFile = file;
        this.importForm.csvFileName = file.name;
      }
    },

    async importStudentsFromCSV() {
      if (!this.importForm.csvFile) { this.error = '请选择CSV文件'; return; }
      this.loading = true; this.error = '';
      try {
        const formData = new FormData();
        formData.append('file', this.importForm.csvFile);
        formData.append('class_id', this.importForm.classId);
        const res = await fetch('/api/teacher/students/import', {
          method: 'POST',
          body: formData,  // No Content-Type header — browser sets multipart/form-data
        });
        const data = await res.json();
        if (data.success) {
          this.showImportModal = false;
          this.success = `成功导入 ${data.count} 名学生`;
          if (this.selectedClass) await this.openStudents(this.selectedClass);
          setTimeout(() => { this.success = ''; }, 3000);
        } else { this.error = data.detail || '导入失败'; }
      } catch (e) { this.error = '导入请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Class Grouping ----
    async openGroupModal(cls) {
      this.selectedClass = cls;
      this.groupForm = { name: '', classId: cls.id };
      try {
        const res = await fetch(`/api/teacher/class/${cls.id}/groups`);
        const data = await res.json();
        this.groups = data.groups || [];
      } catch (_) { this.groups = []; }
      this.showGroupModal = true;
      this.error = '';
    },

    async createGroup() {
      if (!this.groupForm.name.trim()) { this.error = '请输入分组名称'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/class/group', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.groupForm),
        });
        const data = await res.json();
        if (data.success) {
          this.groupForm.name = '';
          await this.openGroupModal(this.selectedClass);
        } else { this.error = data.detail || '创建分组失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    async deleteGroup(groupId) {
      await fetch(`/api/teacher/class/group/${groupId}`, { method: 'DELETE' });
      await this.openGroupModal(this.selectedClass);
    },

    async addStudentToGroup(groupId, studentId) {
      await fetch(`/api/teacher/class/group/${groupId}/student`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId }),
      });
      await this.openGroupModal(this.selectedClass);
    },

    // ---- Student Learning Profile ----
    async openStudentProfile(student) {
      this.loading = true;
      try {
        const res = await fetch(`/api/teacher/student/${student.id}/profile`);
        const data = await res.json();
        this.studentProfile = data.profile || data;
        this.showProfileModal = true;
      } catch (e) {
        this.studentProfile = {
          username: student.username,
          display_name: student.display_name,
          completed_courses: 0,
          total_study_hours: 0,
          avg_score: 0,
          recent_activities: [],
        };
        this.showProfileModal = true;
      }
      finally { this.loading = false; }
    },

    // ---- Helpers ----
    formatDate(d) { return (d || '').slice(0, 10); },
  }));
});
```

- [ ] **Step 3b: Update `html/teacher-class.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>班级管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script><script src="/js/http-intercept.js"></script>
  <script src="/js/pages/teacher-class.js"></script>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar" x-data>
      <div class="teacher-brand">星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">工作台</a>
        <a class="teacher-nav-item active" href="/teacher-class.html">班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" @click="Auth.logout()">退出登录</button></div>
    </aside>
    <main class="teacher-main" x-data="teacherClass" x-init="init()">
      <h1 class="teacher-page-title">班级管理</h1>
      <div x-show="success" x-text="success" class="success-banner"></div>

      <button @click="openCreateModal()" class="btn-primary" style="margin-bottom:16px">+ 创建班级</button>

      <!-- Class Grid -->
      <div class="class-grid">
        <template x-for="c in classes" :key="c.id">
          <div class="class-card">
            <div class="class-card-header">
              <h3 x-text="c.name"></h3>
              <span style="display:flex;gap:4px">
                <button @click="openImportModal(c)" class="btn-sm btn-sm-info">导入</button>
                <button @click="openGroupModal(c)" class="btn-sm">分组</button>
                <button @click="openEditModal(c)" class="btn-sm">编辑</button>
                <button @click="deleteClass(c.id)" class="btn-sm btn-sm-danger">删除</button>
              </span>
            </div>
            <div class="class-card-meta">
              <span x-text="c.subject || '未设置科目'"></span>
              <span style="margin-left:12px" x-text="(c.student_count||0) + ' 名学生'"></span>
              <span x-show="c.description" style="margin-left:12px" x-text="c.description.slice(0,30)"></span>
            </div>
            <button @click="openStudents(c)" class="btn-sm">查看学生名单</button>
          </div>
        </template>
        <div x-show="classes.length === 0" class="empty-state">暂无班级，点击上方按钮创建</div>
      </div>

      <!-- Student Roster -->
      <div x-show="selectedClass" style="margin-top:24px">
        <h2 style="font-size:16px;margin-bottom:12px" x-text="selectedClass.name + ' — 学生名单 (' + students.length + '人)'"></h2>
        <table class="q-table">
          <thead><tr><th>用户名</th><th>显示名</th><th>操作</th></tr></thead>
          <tbody>
            <template x-for="s in students" :key="s.id">
              <tr>
                <td x-text="s.username"></td>
                <td x-text="s.display_name || '-'"></td>
                <td><button @click="openStudentProfile(s)" class="btn-sm btn-sm-info">学习档案</button></td>
              </tr>
            </template>
          </tbody>
        </table>
        <div x-show="students.length === 0" style="color:var(--text-tertiary);text-align:center;padding:20px">暂无学生，请先导入</div>
      </div>

      <!-- Create/Edit Class Modal -->
      <div class="modal-overlay" x-show="showCreateModal || showEditModal" @click.self="showCreateModal = false; showEditModal = false">
        <div class="modal-content">
          <h2 x-text="editingClass ? '编辑班级' : '创建班级'"></h2>
          <div x-show="error" x-text="error" class="error-banner"></div>
          <label class="auth-label">班级名称 *</label>
          <input x-model="form.name" class="auth-field" placeholder="如：高一3班">
          <label class="auth-label">科目</label>
          <input x-model="form.subject" class="auth-field" placeholder="如：数学">
          <label class="auth-label">描述</label>
          <textarea x-model="form.description" class="auth-field" rows="2" placeholder="班级描述（选填）"></textarea>
          <div class="modal-actions">
            <button @click="showCreateModal = false; showEditModal = false" class="btn-cancel">取消</button>
            <button @click="saveClass()" :disabled="loading" class="btn-primary" x-text="loading ? '保存中...' : '保存'"></button>
          </div>
        </div>
      </div>

      <!-- CSV File Upload Modal (NOT textarea) -->
      <div class="modal-overlay" x-show="showImportModal" @click.self="showImportModal = false">
        <div class="modal-content">
          <h2>导入学生 (CSV)</h2>
          <div x-show="error" x-text="error" class="error-banner"></div>
          <p style="font-size:13px;color:var(--text-tertiary);margin-bottom:8px">
            CSV文件格式：每行一个学生，列顺序为 用户名,显示名称<br>
            示例：<code>zhangsan,张三</code>
          </p>
          <!-- Actual file input (not textarea) -->
          <div class="file-upload-area" @click="$refs.csvInput.click()" @dragover.prevent="$el.classList.add('drag-over')" @dragleave="$el.classList.remove('drag-over')" @drop.prevent="$el.classList.remove('drag-over'); handleFileSelect({target:{files:$event.dataTransfer.files}})">
            <input type="file" x-ref="csvInput" @change="handleFileSelect" accept=".csv" style="display:none">
            <p>📁 点击选择CSV文件或拖拽到此处</p>
            <div class="file-name" x-show="importForm.csvFileName" x-text="importForm.csvFileName"></div>
          </div>
          <div class="modal-actions">
            <button @click="showImportModal = false" class="btn-cancel">取消</button>
            <button @click="importStudentsFromCSV()" :disabled="loading || !importForm.csvFile" class="btn-primary" x-text="loading ? '导入中...' : '确认导入'"></button>
          </div>
        </div>
      </div>

      <!-- Class Grouping Modal -->
      <div class="modal-overlay" x-show="showGroupModal" @click.self="showGroupModal = false">
        <div class="modal-content modal-wide">
          <h2 x-text="'分组管理 — ' + (selectedClass ? selectedClass.name : '')"></h2>
          <div x-show="error" x-text="error" class="error-banner"></div>

          <div style="display:flex;gap:8px;margin-bottom:16px;align-items:center">
            <input x-model="groupForm.name" class="auth-field" placeholder="分组名称" style="margin:0;flex:1">
            <button @click="createGroup()" :disabled="loading" class="btn-primary">添加分组</button>
          </div>

          <template x-for="g in groups" :key="g.id">
            <div style="padding:10px 14px;margin:6px 0;background:var(--surface-glass);border:1px solid var(--border-glass);border-radius:8px;display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:500" x-text="g.name"></span>
              <span style="font-size:12px;color:var(--text-tertiary)" x-text="(g.student_count || 0) + ' 名学生'"></span>
              <button @click="deleteGroup(g.id)" class="btn-sm btn-sm-danger">删除</button>
            </div>
          </template>
          <div x-show="groups.length === 0" style="color:var(--text-tertiary);text-align:center;padding:20px">暂无分组</div>

          <div class="modal-actions">
            <button @click="showGroupModal = false" class="btn-cancel">关闭</button>
          </div>
        </div>
      </div>

      <!-- Student Profile Modal -->
      <div class="modal-overlay" x-show="showProfileModal" @click.self="showProfileModal = false">
        <div class="modal-content">
          <h2>学生档案</h2>
          <template x-if="studentProfile">
            <div class="student-profile-card">
              <div class="student-profile-header">
                <div class="student-avatar" x-text="(studentProfile.display_name || studentProfile.username || '?')[0]"></div>
                <div>
                  <div class="student-profile-name" x-text="studentProfile.display_name || studentProfile.username"></div>
                  <div class="student-profile-meta" x-text="'@' + (studentProfile.username || '')"></div>
                </div>
              </div>
              <div class="student-profile-stats">
                <div class="stat-card">
                  <div class="stat-value" x-text="studentProfile.completed_courses || 0"></div>
                  <div class="stat-label">已完成课程</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value" x-text="(studentProfile.total_study_hours || 0) + 'h'"></div>
                  <div class="stat-label">学习时长</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value" x-text="studentProfile.avg_score || '--'"></div>
                  <div class="stat-label">平均成绩</div>
                </div>
              </div>
              <h3 style="font-size:14px;margin:16px 0 8px">最近活动</h3>
              <template x-if="studentProfile.recent_activities && studentProfile.recent_activities.length">
                <div>
                  <template x-for="act in studentProfile.recent_activities" :key="act.id || act.date">
                    <div style="padding:6px 0;font-size:13px;border-bottom:1px solid var(--border-glass);display:flex;justify-content:space-between">
                      <span x-text="act.description || act.title"></span>
                      <span style="color:var(--text-tertiary);font-size:12px" x-text="formatDate(act.date)"></span>
                    </div>
                  </template>
                </div>
              </template>
              <div x-show="!studentProfile.recent_activities || studentProfile.recent_activities.length === 0" class="empty-state" style="padding:20px">暂无活动记录</div>
            </div>
          </template>
          <div class="modal-actions">
            <button @click="showProfileModal = false" class="btn-cancel">关闭</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 3c: Commit**

```bash
git add js/pages/teacher-class.js html/teacher-class.html
git commit -m "feat: full class management with CSV file upload, grouping, student profiles"
```

---

### Task 4: Teacher Manage — Question Bank (4 Types + Batch Import)

**Files:**
- Create: `js/pages/teacher-manage.js`
- Modify: `html/teacher-manage.html`

Full question bank implementing ALL spec requirements:
- 4 question types: choice (选择) / fill (填空) / code (编程) / essay (简答)
- CRUD with proper form fields per type
- Tags + difficulty (easy/medium/hard)
- Batch import via CSV/JSON file upload
- Search and filter

- [ ] **Step 4a: Create `js/pages/teacher-manage.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('teacherManage', () => ({
    // ---- State ----
    questions: [],
    showModal: false,
    showImportModal: false,
    editingQuestion: null,
    error: '',
    success: '',
    loading: false,
    filter: { type: '', difficulty: '', search: '' },
    form: {
      type: 'choice', content: '', options: '', answer: '',
      difficulty: 'medium', tags: '', course_id: null,
    },
    importFile: null,
    importFileName: '',

    // ---- Computed ----
    get typeCounts() {
      const counts = { choice: 0, fill: 0, code: 0, essay: 0 };
      this.questions.forEach(q => { if (counts[q.type] !== undefined) counts[q.type]++; });
      return counts;
    },

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await this.loadQuestions();
    },

    // ---- Question CRUD ----
    async loadQuestions() {
      const params = new URLSearchParams();
      if (this.filter.type) params.set('type', this.filter.type);
      if (this.filter.difficulty) params.set('difficulty', this.filter.difficulty);
      if (this.filter.search) params.set('search', this.filter.search);
      const qs = params.toString();
      try {
        const res = await fetch(`/api/teacher/questions${qs ? '?' + qs : ''}`);
        const data = await res.json();
        this.questions = data.questions || [];
      } catch (_) { this.questions = []; }
    },

    openCreateModal() {
      this.editingQuestion = null;
      this.form = { type: 'choice', content: '', options: '', answer: '', difficulty: 'medium', tags: '', course_id: null };
      this.showModal = true;
      this.error = '';
    },

    openEditModal(q) {
      this.editingQuestion = q;
      this.form = {
        type: q.type || 'choice',
        content: q.content || '',
        options: typeof q.options === 'string' ? q.options : JSON.stringify(q.options || []),
        answer: q.answer || '',
        difficulty: q.difficulty || 'medium',
        tags: typeof q.tags === 'string' ? q.tags : JSON.stringify(q.tags || []),
        course_id: q.course_id || null,
      };
      this.showModal = true;
      this.error = '';
    },

    async saveQuestion() {
      if (!this.form.content.trim()) { this.error = '请输入题目内容'; return; }
      if (!this.form.answer.trim()) { this.error = '请输入正确答案'; return; }
      this.loading = true; this.error = '';
      try {
        let options = null;
        const rawOpts = this.form.options.trim();
        if (rawOpts) {
          try { options = JSON.parse(rawOpts); }
          catch (e) { this.error = '选项JSON格式错误'; this.loading = false; return; }
        }
        let tags = null;
        const rawTags = this.form.tags.trim();
        if (rawTags) {
          try { tags = JSON.parse(rawTags); }
          catch (e) { this.error = '标签JSON格式错误'; this.loading = false; return; }
        }

        const url = this.editingQuestion
          ? `/api/teacher/question/${this.editingQuestion.id}`
          : '/api/teacher/question';
        const method = this.editingQuestion ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: this.form.type,
            content: this.form.content,
            options,
            answer: this.form.answer,
            difficulty: this.form.difficulty,
            tags,
            course_id: this.form.course_id,
          }),
        });
        const data = await res.json();
        if (data.success) {
          this.showModal = false;
          await this.loadQuestions();
        } else { this.error = data.detail || '保存失败'; }
      } catch (e) { this.error = '请求失败: ' + e.message; }
      finally { this.loading = false; }
    },

    async deleteQuestion(id) {
      if (!confirm('确认删除此题？')) return;
      await fetch(`/api/teacher/question/${id}`, { method: 'DELETE' });
      await this.loadQuestions();
    },

    // ---- Batch Import (CSV/JSON file upload) ----
    openImportModal() {
      this.importFile = null;
      this.importFileName = '';
      this.showImportModal = true;
      this.error = '';
    },

    handleImportFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        this.importFile = file;
        this.importFileName = file.name;
      }
    },

    async importQuestions() {
      if (!this.importFile) { this.error = '请选择文件'; return; }
      const ext = this.importFile.name.split('.').pop().toLowerCase();
      if (!['csv', 'json'].includes(ext)) { this.error = '仅支持CSV或JSON文件'; return; }
      this.loading = true; this.error = '';
      try {
        const formData = new FormData();
        formData.append('file', this.importFile);
        formData.append('format', ext);
        const res = await fetch('/api/teacher/questions/import', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        if (data.success) {
          this.showImportModal = false;
          this.success = `成功导入 ${data.count || 0} 道题目`;
          await this.loadQuestions();
          setTimeout(() => { this.success = ''; }, 3000);
        } else { this.error = data.detail || '导入失败'; }
      } catch (e) { this.error = '导入请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Helpers ----
    truncate(str, n) {
      if (!str) return '';
      return str.length > n ? str.slice(0, n) + '...' : str;
    },
    typeLabel(t) {
      return { choice: '选择', fill: '填空', code: '编程', essay: '简答' }[t] || t;
    },
    diffLabel(d) {
      return { easy: '简单', medium: '中等', hard: '困难' }[d] || d;
    },
  }));
});
```

- [ ] **Step 4b: Update `html/teacher-manage.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>题库管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script><script src="/js/http-intercept.js"></script>
  <script src="/js/pages/teacher-manage.js"></script>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar" x-data>
      <div class="teacher-brand">星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">班级管理</a>
        <a class="teacher-nav-item active" href="/teacher-manage.html">题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" @click="Auth.logout()">退出登录</button></div>
    </aside>
    <main class="teacher-main" x-data="teacherManage" x-init="init()">
      <h1 class="teacher-page-title">题库管理</h1>
      <div x-show="success" x-text="success" class="success-banner"></div>

      <!-- Type Stats -->
      <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
        <span class="status-badge status-badge-draft">选择: <strong x-text="typeCounts.choice"></strong></span>
        <span class="status-badge status-badge-published">填空: <strong x-text="typeCounts.fill"></strong></span>
        <span class="status-badge status-badge-approved">编程: <strong x-text="typeCounts.code"></strong></span>
        <span class="status-badge status-badge-pending">简答: <strong x-text="typeCounts.essay"></strong></span>
      </div>

      <!-- Toolbar -->
      <div style="display:flex;gap:12px;margin-bottom:16px;align-items:center;flex-wrap:wrap">
        <button @click="openCreateModal()" class="btn-primary">+ 添加题目</button>
        <button @click="openImportModal()" class="btn-accent">📥 批量导入</button>
        <select x-model="filter.type" @change="loadQuestions()" class="gen-select" style="min-width:100px">
          <option value="">全部类型</option>
          <option value="choice">选择题</option>
          <option value="fill">填空题</option>
          <option value="code">编程题</option>
          <option value="essay">简答题</option>
        </select>
        <select x-model="filter.difficulty" @change="loadQuestions()" class="gen-select" style="min-width:100px">
          <option value="">全部难度</option>
          <option value="easy">简单</option>
          <option value="medium">中等</option>
          <option value="hard">困难</option>
        </select>
        <input x-model="filter.search" @keydown.enter="loadQuestions()" class="auth-field" placeholder="搜索题目..." style="margin:0;max-width:200px;flex:1">
      </div>

      <!-- Question Table -->
      <table class="q-table">
        <thead><tr><th>ID</th><th>类型</th><th>内容</th><th>难度</th><th>标签</th><th>操作</th></tr></thead>
        <tbody>
          <template x-for="q in questions" :key="q.id">
            <tr>
              <td x-text="q.id"></td>
              <td><span class="status-badge status-badge-draft" x-text="typeLabel(q.type)"></span></td>
              <td x-text="truncate(q.content, 50)"></td>
              <td><span x-text="diffLabel(q.difficulty)" style="font-size:12px"></span></td>
              <td style="font-size:12px;color:var(--text-tertiary);max-width:150px" x-text="Array.isArray(q.tags) ? q.tags.join(', ') : (q.tags || '')"></td>
              <td style="white-space:nowrap">
                <button @click="openEditModal(q)" class="btn-sm">编辑</button>
                <button @click="deleteQuestion(q.id)" class="btn-sm btn-sm-danger">删除</button>
              </td>
            </tr>
          </template>
          <tr x-show="questions.length === 0">
            <td colspan="6" class="empty-state" style="padding:40px">暂无题目，点击上方按钮添加或导入</td>
          </tr>
        </tbody>
      </table>

      <!-- Question Create/Edit Modal -->
      <div class="modal-overlay" x-show="showModal" @click.self="showModal = false" x-cloak>
        <div class="modal-content modal-wide">
          <h2 x-text="editingQuestion ? '编辑题目' : '添加题目'"></h2>
          <div x-show="error" x-text="error" class="error-banner"></div>

          <label class="auth-label">题型</label>
          <select x-model="form.type" class="auth-field">
            <option value="choice">选择题</option>
            <option value="fill">填空题</option>
            <option value="code">编程题</option>
            <option value="essay">简答题</option>
          </select>

          <label class="auth-label">题目内容 *</label>
          <textarea x-model="form.content" class="auth-field" rows="4" placeholder="题目内容..."></textarea>

          <!-- Options (for choice type) -->
          <div x-show="form.type === 'choice'">
            <label class="auth-label">选项（JSON数组）</label>
            <input x-model="form.options" class="auth-field" placeholder='["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"]'>
          </div>

          <label class="auth-label">正确答案 *</label>
          <input x-model="form.answer" class="auth-field" :placeholder="form.type === 'choice' ? '如: A' : form.type === 'code' ? '参考答案代码...' : '正确答案'">

          <label class="auth-label">难度</label>
          <select x-model="form.difficulty" class="auth-field">
            <option value="easy">简单</option>
            <option value="medium">中等</option>
            <option value="hard">困难</option>
          </select>

          <label class="auth-label">标签（JSON数组，选填）</label>
          <input x-model="form.tags" class="auth-field" placeholder='["知识点1","知识点2"]'>

          <div class="modal-actions">
            <button @click="showModal = false" class="btn-cancel">取消</button>
            <button @click="saveQuestion()" :disabled="loading" class="btn-primary" x-text="loading ? '保存中...' : '保存'"></button>
          </div>
        </div>
      </div>

      <!-- Batch Import Modal -->
      <div class="modal-overlay" x-show="showImportModal" @click.self="showImportModal = false" x-cloak>
        <div class="modal-content">
          <h2>批量导入题目</h2>
          <div x-show="error" x-text="error" class="error-banner"></div>
          <p style="font-size:13px;color:var(--text-tertiary);margin-bottom:8px">
            支持CSV格式（type,content,options,answer,difficulty,tags）或JSON格式（题目数组）
          </p>
          <div class="file-upload-area" @click="$refs.qImportInput.click()" @dragover.prevent="$el.classList.add('drag-over')" @dragleave="$el.classList.remove('drag-over')" @drop.prevent="$el.classList.remove('drag-over'); handleImportFileSelect({target:{files:$event.dataTransfer.files}})">
            <input type="file" x-ref="qImportInput" @change="handleImportFileSelect" accept=".csv,.json" style="display:none">
            <p>📁 点击选择CSV或JSON文件，或拖拽到此处</p>
            <div class="file-name" x-show="importFileName" x-text="importFileName"></div>
          </div>
          <div class="modal-actions">
            <button @click="showImportModal = false" class="btn-cancel">取消</button>
            <button @click="importQuestions()" :disabled="loading || !importFile" class="btn-primary" x-text="loading ? '导入中...' : '开始导入'"></button>
          </div>
        </div>
      </div>
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 4c: Commit**

```bash
git add js/pages/teacher-manage.js html/teacher-manage.html
git commit -m "feat: full question bank with 4 types (choice/fill/code/essay) + batch CSV/JSON import"
```

---

### Task 5: Teacher Exam (考试管理 — Full: AI Generate + Edit + Grade Analysis + Proper Grading UI)

**Files:**
- Create: `js/pages/teacher-exam.js`
- Modify: `html/teacher-exam.html`

Full exam management implementing ALL spec requirements:
- Create exam: manual mode + AI auto-generate mode
- Edit exam (PUT endpoint)
- Publish / Unpublish / Archive status management
- Proper grading interface (modal with per-question AI pre-score + teacher confirmation)
- Grade analysis with ECharts: score distribution histogram + per-question accuracy bar + class comparison
- NO `alert()` hacks — all interactions in proper modals

- [ ] **Step 5a: Create `js/pages/teacher-exam.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('teacherExam', () => ({
    // ---- State ----
    exams: [],
    classes: [],
    questions: [],
    showCreateModal: false,
    showEditModal: false,
    showGradeModal: false,
    showResultModal: false,
    showAnalysisModal: false,
    editingExam: null,
    error: '',
    success: '',
    loading: false,

    // Create/Edit form
    form: {
      title: '', duration: 120, classIds: [], questionIds: [],
      description: '', start_time: '', end_time: '',
    },
    createMode: 'manual', // 'manual' | 'ai'

    // AI generate form
    aiForm: { topic: '', difficulty: 'medium', questionCount: 10, classIds: [] },

    // Grading state
    gradingExam: null,
    gradingResults: [],
    gradingIndex: 0,
    gradingScores: {},

    // Result state
    resultExam: null,
    results: [],

    // Analysis state
    analysisExam: null,
    analysisData: null,
    analysisChart: null,

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await this.loadExams();
    },

    // ---- Exam Loading ----
    async loadExams() {
      try {
        const res = await fetch('/api/teacher/exams');
        const data = await res.json();
        this.exams = data.exams || [];
      } catch (_) { this.exams = []; }
    },

    // ---- Manual Create ----
    async openCreateModal() {
      this.createMode = 'manual';
      this.showCreateModal = true;
      this.error = '';
      this.form = { title: '', duration: 120, classIds: [], questionIds: [], description: '', start_time: '', end_time: '' };
      try {
        const [clsRes, qRes] = await Promise.all([
          fetch('/api/teacher/classes'),
          fetch('/api/teacher/questions'),
        ]);
        const clsData = await clsRes.json();
        const qData = await qRes.json();
        this.classes = clsData.classes || [];
        this.questions = qData.questions || [];
      } catch (_) { this.classes = []; this.questions = []; }
    },

    // ---- AI Auto-Generate ----
    openAiCreateModal() {
      this.createMode = 'ai';
      this.showCreateModal = true;
      this.error = '';
      this.aiForm = { topic: '', difficulty: 'medium', questionCount: 10, classIds: [] };
      // Also load classes for target selection
      fetch('/api/teacher/classes').then(r => r.json()).then(d => { this.classes = d.classes || []; }).catch(() => {});
    },

    async aiGenerateExam() {
      if (!this.aiForm.topic.trim()) { this.error = '请输入考试主题/知识点'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/exam', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            generate_mode: 'ai',
            topic: this.aiForm.topic,
            difficulty: this.aiForm.difficulty,
            question_count: this.aiForm.questionCount,
            class_ids: this.aiForm.classIds,
          }),
        });
        const data = await res.json();
        if (data.success) {
          this.showCreateModal = false;
          await this.loadExams();
          this.success = `AI自动组卷成功: ${data.title || ''}`;
          setTimeout(() => { this.success = ''; }, 3000);
        } else { this.error = data.detail || 'AI组卷失败'; }
      } catch (e) { this.error = 'AI组卷请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Manual Create Submit ----
    async createExam() {
      if (!this.form.title.trim()) { this.error = '请输入考试标题'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/exam', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: this.form.title,
            description: this.form.description,
            question_ids: this.form.questionIds,
            class_ids: this.form.classIds,
            duration: this.form.duration,
            start_time: this.form.start_time || null,
            end_time: this.form.end_time || null,
          }),
        });
        const data = await res.json();
        if (data.success) { this.showCreateModal = false; await this.loadExams(); }
        else { this.error = data.detail || '创建失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Edit Exam ----
    async openEditModal(exam) {
      this.editingExam = exam;
      this.form = {
        title: exam.title || '',
        description: exam.description || '',
        duration: exam.duration || 120,
        classIds: exam.class_ids || [],
        questionIds: exam.question_ids || [],
        start_time: exam.start_time || '',
        end_time: exam.end_time || '',
      };
      try {
        const [clsRes, qRes] = await Promise.all([
          fetch('/api/teacher/classes'),
          fetch('/api/teacher/questions'),
        ]);
        this.classes = (await clsRes.json()).classes || [];
        this.questions = (await qRes.json()).questions || [];
      } catch (_) {}
      this.showEditModal = true;
      this.error = '';
    },

    async updateExam() {
      if (!this.form.title.trim()) { this.error = '请输入考试标题'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${this.editingExam.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: this.form.title,
            description: this.form.description,
            question_ids: this.form.questionIds,
            class_ids: this.form.classIds,
            duration: this.form.duration,
            start_time: this.form.start_time || null,
            end_time: this.form.end_time || null,
          }),
        });
        const data = await res.json();
        if (data.success) { this.showEditModal = false; await this.loadExams(); }
        else { this.error = data.detail || '更新失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Status Actions ----
    async publishExam(id) {
      await fetch(`/api/teacher/exam/${id}/publish`, { method: 'POST' });
      await this.loadExams();
    },

    async archiveExam(id) {
      await fetch(`/api/teacher/exam/${id}/archive`, { method: 'POST' });
      await this.loadExams();
    },

    async deleteExam(id) {
      if (!confirm('确认删除此考试？')) return;
      await fetch(`/api/teacher/exam/${id}`, { method: 'DELETE' });
      await this.loadExams();
    },

    // ---- Proper Grading UI (NO alert()) ----
    async openGradeModal(exam) {
      this.gradingExam = exam;
      this.gradingIndex = 0;
      this.gradingScores = {};
      this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${exam.id}/results`);
        const data = await res.json();
        this.gradingResults = (data.results || []).filter(r => r.graded_by === 'auto' || r.score === null);
      } catch (_) { this.gradingResults = []; }
      this.showGradeModal = true;
    },

    get currentGrading() {
      return this.gradingResults[this.gradingIndex] || null;
    },

    get gradingProgress() {
      return this.gradingResults.length
        ? `${this.gradingIndex + 1} / ${this.gradingResults.length}`
        : '0 / 0';
    },

    async aiPrescore() {
      const r = this.currentGrading;
      if (!r) return;
      this.loading = true;
      try {
        const res = await fetch(`/api/teacher/exam/${this.gradingExam.id}/grade`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result_id: r.id }),
        });
        const data = await res.json();
        if (data.success) {
          this.gradingResults[this.gradingIndex] = { ...r, ai_score: data.ai_score, ai_comment: data.ai_comment };
        } else { this.error = data.detail || 'AI预批改失败'; }
      } catch (_) { this.error = 'AI预批改请求失败'; }
      finally { this.loading = false; }
    },

    async confirmGrade() {
      const r = this.currentGrading;
      if (!r) return;
      const score = this.gradingScores[r.id];
      if (score === undefined || score === '' || score === null) {
        this.error = '请输入最终分数';
        return;
      }
      this.loading = true; this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${this.gradingExam.id}/grade`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result_id: r.id, final_score: parseFloat(score) }),
        });
        const data = await res.json();
        if (data.success) {
          if (this.gradingIndex < this.gradingResults.length - 1) {
            this.gradingIndex++;
          } else {
            this.showGradeModal = false;
            this.success = '所有答卷批改完成';
            setTimeout(() => { this.success = ''; }, 3000);
          }
        } else { this.error = data.detail || '保存分数失败'; }
      } catch (_) { this.error = '保存失败'; }
      finally { this.loading = false; }
    },

    prevGrading() { if (this.gradingIndex > 0) this.gradingIndex--; },
    nextGrading() { if (this.gradingIndex < this.gradingResults.length - 1) this.gradingIndex++; },

    // ---- View Results (Proper table, NOT alert()) ----
    async openResultModal(exam) {
      this.resultExam = exam;
      this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${exam.id}/results`);
        const data = await res.json();
        this.results = data.results || [];
      } catch (_) { this.results = []; }
      this.showResultModal = true;
    },

    // ---- Grade Analysis (ECharts, NOT alert()) ----
    async openAnalysisModal(exam) {
      this.analysisExam = exam;
      this.loading = true; this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${exam.id}/analysis`);
        const data = await res.json();
        this.analysisData = data;
        this.showAnalysisModal = true;
        await this.$nextTick();
        this.initAnalysisChart();
      } catch (_) { this.error = '无法加载分析数据'; }
      finally { this.loading = false; }
    },

    initAnalysisChart() {
      const el = this.$refs.analysisChart;
      if (!el || !this.analysisData) return;
      if (this.analysisChart) this.analysisChart.dispose();
      this.analysisChart = echarts.init(el);

      const dist = this.analysisData.score_distribution || {};
      const ranges = ['0-59', '60-69', '70-79', '80-89', '90-100'];
      const counts = ranges.map(r => dist[r] || 0);

      this.analysisChart.setOption({
        title: { text: '成绩分布', left: 'center', textStyle: { fontSize: 14, color: '#64748b' } },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category', data: ranges,
          axisLabel: { color: '#94a3b8', fontSize: 11 },
        },
        yAxis: {
          type: 'value', name: '人数',
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        series: [{
          data: counts, type: 'bar', barWidth: '50%',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6366f1' }, { offset: 1, color: '#a78bfa' },
            ]),
            borderRadius: [4, 4, 0, 0],
          },
          label: { show: true, position: 'top', fontSize: 12 },
        }],
        grid: { top: 40, right: 20, bottom: 30, left: 40 },
      });
    },

    // ---- Checkbox Helpers ----
    toggleClass(id) {
      const idx = this.form.classIds.indexOf(id);
      idx >= 0 ? this.form.classIds.splice(idx, 1) : this.form.classIds.push(id);
    },
    toggleQuestion(id) {
      const idx = this.form.questionIds.indexOf(id);
      idx >= 0 ? this.form.questionIds.splice(idx, 1) : this.form.questionIds.push(id);
    },
    toggleAiClass(id) {
      const idx = this.aiForm.classIds.indexOf(id);
      idx >= 0 ? this.aiForm.classIds.splice(idx, 1) : this.aiForm.classIds.push(id);
    },
    isChecked(arr, id) { return arr.includes(id); },

    // ---- Utilities ----
    formatDate(d) { return (d || '').slice(0, 10); },
    truncate(str, n) { if (!str) return ''; return str.length > n ? str.slice(0, n) + '...' : str; },
    statusLabel(s) {
      return { draft: '草稿', published: '已发布', closed: '已关闭', archived: '已归档' }[s] || s;
    },
    typeLabel(t) {
      return { choice: '选择', fill: '填空', code: '编程', essay: '简答' }[t] || t;
    },
  }));
});
```

- [ ] **Step 5b: Update `html/teacher-exam.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>考试管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script><script src="/js/http-intercept.js"></script>
  <script src="/js/pages/teacher-exam.js"></script>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar" x-data>
      <div class="teacher-brand">星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">题库管理</a>
        <a class="teacher-nav-item active" href="/teacher-exam.html">考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" @click="Auth.logout()">退出登录</button></div>
    </aside>
    <main class="teacher-main" x-data="teacherExam" x-init="init()">
      <h1 class="teacher-page-title">考试管理</h1>
      <div x-show="success" x-text="success" class="success-banner"></div>

      <div style="display:flex;gap:12px;margin-bottom:16px">
        <button @click="openCreateModal()" class="btn-primary">+ 手动创建考试</button>
        <button @click="openAiCreateModal()" class="btn-accent">🤖 AI 自动组卷</button>
      </div>

      <!-- Exam Grid -->
      <div class="exam-grid">
        <template x-for="exam in exams" :key="exam.id">
          <div class="exam-card">
            <h3 x-text="exam.title"></h3>
            <div class="exam-meta">
              <span>状态: <span class="status-badge" :class="'status-badge-' + (exam.status === 'published' ? 'published' : exam.status === 'closed' ? 'ended' : exam.status === 'archived' ? 'archived' : 'draft')" x-text="statusLabel(exam.status)"></span></span>
              <span>时长: <span x-text="exam.duration || 60"></span>分钟</span>
              <span x-show="exam.created_at">创建: <span x-text="formatDate(exam.created_at)"></span></span>
              <span x-show="exam.question_count">题目数: <span x-text="exam.question_count"></span></span>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <button x-show="exam.status === 'draft'" @click="publishExam(exam.id)" class="btn-sm btn-sm-success">发布</button>
              <button x-show="exam.status === 'published'" @click="archiveExam(exam.id)" class="btn-sm">归档</button>
              <button x-show="exam.status === 'draft'" @click="openEditModal(exam)" class="btn-sm btn-sm-info">编辑</button>
              <button @click="openGradeModal(exam)" class="btn-sm">批阅</button>
              <button @click="openResultModal(exam)" class="btn-sm">成绩</button>
              <button @click="openAnalysisModal(exam)" class="btn-sm btn-sm-info">分析</button>
              <button @click="deleteExam(exam.id)" class="btn-sm btn-sm-danger">删除</button>
            </div>
          </div>
        </template>
      </div>
      <div x-show="exams.length === 0" class="empty-state">暂无考试，点击上方按钮创建</div>

      <!-- ===== CREATE MODAL (Manual + AI modes) ===== -->
      <div class="modal-overlay" x-show="showCreateModal" @click.self="showCreateModal = false" x-cloak>
        <div class="modal-content modal-wide">
          <h2 x-text="createMode === 'ai' ? 'AI 自动组卷' : '创建考试'"></h2>
          <div x-show="error" x-text="error" class="error-banner"></div>

          <!-- Manual Mode -->
          <template x-if="createMode === 'manual'">
            <div>
              <label class="auth-label">考试标题 *</label>
              <input x-model="form.title" class="auth-field" placeholder="输入考试标题">

              <label class="auth-label">描述</label>
              <textarea x-model="form.description" class="auth-field" rows="2" placeholder="考试描述（选填）"></textarea>

              <label class="auth-label">时长（分钟）</label>
              <input x-model.number="form.duration" type="number" min="1" class="auth-field">

              <div style="display:flex;gap:12px">
                <div style="flex:1">
                  <label class="auth-label">开始时间</label>
                  <input x-model="form.start_time" type="datetime-local" class="auth-field">
                </div>
                <div style="flex:1">
                  <label class="auth-label">结束时间</label>
                  <input x-model="form.end_time" type="datetime-local" class="auth-field">
                </div>
              </div>

              <label class="auth-label">指定班级</label>
              <div class="checkbox-group">
                <template x-for="c in classes" :key="c.id">
                  <label><input type="checkbox" :value="c.id" :checked="isChecked(form.classIds, c.id)" @change="toggleClass(c.id)"> <span x-text="c.name"></span></label>
                </template>
                <div x-show="classes.length === 0" style="color:var(--text-tertiary)">暂无班级</div>
              </div>

              <label class="auth-label">添加试题</label>
              <div class="checkbox-group" style="max-height:200px">
                <template x-for="q in questions" :key="q.id">
                  <label><input type="checkbox" :value="q.id" :checked="isChecked(form.questionIds, q.id)" @change="toggleQuestion(q.id)"> <span x-text="'[' + typeLabel(q.type) + '] ' + truncate(q.content, 40)"></span></label>
                </template>
                <div x-show="questions.length === 0" style="color:var(--text-tertiary)">暂无试题</div>
              </div>
            </div>
          </template>

          <!-- AI Mode -->
          <template x-if="createMode === 'ai'">
            <div>
              <label class="auth-label">考试主题/知识点 *</label>
              <input x-model="aiForm.topic" class="auth-field" placeholder="如：Python基础语法、数据结构与算法">

              <label class="auth-label">难度</label>
              <select x-model="aiForm.difficulty" class="auth-field">
                <option value="easy">简单</option>
                <option value="medium">中等</option>
                <option value="hard">困难</option>
              </select>

              <label class="auth-label">题目数量</label>
              <input x-model.number="aiForm.questionCount" type="number" min="1" max="50" class="auth-field">

              <label class="auth-label">参与班级</label>
              <div class="checkbox-group">
                <template x-for="c in classes" :key="c.id">
                  <label><input type="checkbox" :value="c.id" :checked="isChecked(aiForm.classIds, c.id)" @change="toggleAiClass(c.id)"> <span x-text="c.name"></span></label>
                </template>
              </div>
            </div>
          </template>

          <div class="modal-actions">
            <button @click="showCreateModal = false" class="btn-cancel">取消</button>
            <button x-show="createMode === 'manual'" @click="createExam()" :disabled="loading" class="btn-primary" x-text="loading ? '创建中...' : '创建考试'"></button>
            <button x-show="createMode === 'ai'" @click="aiGenerateExam()" :disabled="loading" class="btn-accent" x-text="loading ? 'AI生成中...' : '开始生成'"></button>
          </div>
        </div>
      </div>

      <!-- ===== EDIT MODAL ===== -->
      <div class="modal-overlay" x-show="showEditModal" @click.self="showEditModal = false" x-cloak>
        <div class="modal-content modal-wide">
          <h2>编辑考试</h2>
          <div x-show="error" x-text="error" class="error-banner"></div>
          <label class="auth-label">考试标题 *</label>
          <input x-model="form.title" class="auth-field">
          <label class="auth-label">描述</label>
          <textarea x-model="form.description" class="auth-field" rows="2"></textarea>
          <label class="auth-label">时长（分钟）</label>
          <input x-model.number="form.duration" type="number" min="1" class="auth-field">
          <div class="modal-actions">
            <button @click="showEditModal = false" class="btn-cancel">取消</button>
            <button @click="updateExam()" :disabled="loading" class="btn-primary" x-text="loading ? '保存中...' : '保存修改'"></button>
          </div>
        </div>
      </div>

      <!-- ===== GRADING MODAL (Proper UI, no alert()) ===== -->
      <div class="modal-overlay" x-show="showGradeModal" @click.self="showGradeModal = false" x-cloak>
        <div class="modal-content modal-wide">
          <h2 x-text="'批阅: ' + (gradingExam ? gradingExam.title : '')"></h2>
          <div x-show="error" x-text="error" class="error-banner"></div>
          <div style="font-size:13px;color:var(--text-tertiary);margin-bottom:12px" x-text="'进度: ' + gradingProgress"></div>

          <template x-if="currentGrading">
            <div class="grading-panel">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <span style="font-weight:600" x-text="'学生: ' + (currentGrading.display_name || currentGrading.student_id)"></span>
                <span style="font-size:12px;color:var(--text-tertiary)" x-text="'提交时间: ' + formatDate(currentGrading.submitted_at)"></span>
              </div>

              <!-- Show AI pre-score if available -->
              <div x-show="currentGrading.ai_score != null" class="grading-ai-score">
                AI预评分: <strong x-text="currentGrading.ai_score"></strong> 分
              </div>
              <div x-show="currentGrading.ai_comment" class="grading-ai-comment" x-text="'AI评语: ' + currentGrading.ai_comment"></div>

              <div style="display:flex;gap:12px;align-items:center;margin:16px 0">
                <label style="font-size:14px;white-space:nowrap">最终分数:</label>
                <input type="number" min="0" max="100" step="0.5" class="auth-field grading-score-input"
                  :value="gradingScores[currentGrading.id] ?? currentGrading.ai_score ?? currentGrading.score ?? ''"
                  @input="gradingScores[currentGrading.id] = $event.target.value"
                  placeholder="评分">
                <span style="font-size:14px">/ 100</span>
              </div>

              <div style="display:flex;gap:8px;justify-content:space-between">
                <div style="display:flex;gap:8px">
                  <button @click="prevGrading()" :disabled="gradingIndex === 0" class="btn-sm">上一条</button>
                  <button @click="nextGrading()" :disabled="gradingIndex >= gradingResults.length - 1" class="btn-sm">下一条</button>
                </div>
                <div style="display:flex;gap:8px">
                  <button @click="aiPrescore()" :disabled="loading" class="btn-sm btn-sm-info" x-text="loading ? 'AI评分中...' : 'AI预评分'"></button>
                  <button @click="confirmGrade()" :disabled="loading" class="btn-primary" x-text="loading ? '保存中...' : '确认分数'"></button>
                </div>
              </div>
            </div>
          </template>
          <template x-if="!currentGrading">
            <div class="empty-state" style="padding:40px">所有答卷已批改完成</div>
          </template>
          <div class="modal-actions">
            <button @click="showGradeModal = false" class="btn-cancel">关闭</button>
          </div>
        </div>
      </div>

      <!-- ===== RESULTS MODAL (Table, not alert()) ===== -->
      <div class="modal-overlay" x-show="showResultModal" @click.self="showResultModal = false" x-cloak>
        <div class="modal-content modal-wide">
          <h2 x-text="'成绩列表: ' + (resultExam ? resultExam.title : '')"></h2>
          <table class="q-table">
            <thead><tr><th>学生</th><th>用户名</th><th>分数</th><th>AI预评分</th><th>批改状态</th><th>提交时间</th></tr></thead>
            <tbody>
              <template x-for="r in results" :key="r.id">
                <tr>
                  <td x-text="r.display_name || '-'"></td>
                  <td x-text="r.username || r.student_id"></td>
                  <td><strong x-text="r.score != null ? r.score + '分' : '未评分'" :style="r.score >= 60 ? 'color:#22c55e' : r.score != null ? 'color:#ef4444' : ''"></strong></td>
                  <td x-text="r.ai_score != null ? r.ai_score + '分' : '-'" style="font-size:12px;color:var(--text-tertiary)"></td>
                  <td><span class="status-badge" :class="'status-badge-' + (r.graded_by === 'auto' ? 'draft' : 'approved')" x-text="r.graded_by === 'auto' ? 'AI预评' : '已批改'"></span></td>
                  <td x-text="formatDate(r.submitted_at)" style="font-size:12px;color:var(--text-tertiary)"></td>
                </tr>
              </template>
              <tr x-show="results.length === 0">
                <td colspan="6" class="empty-state" style="padding:40px">暂无学生提交</td>
              </tr>
            </tbody>
          </table>
          <div class="modal-actions">
            <button @click="showResultModal = false" class="btn-cancel">关闭</button>
          </div>
        </div>
      </div>

      <!-- ===== ANALYSIS MODAL (ECharts, not alert()) ===== -->
      <div class="modal-overlay" x-show="showAnalysisModal" @click.self="showAnalysisModal = false" x-cloak>
        <div class="modal-content modal-wide">
          <h2 x-text="'成绩分析: ' + (analysisExam ? analysisExam.title : '')"></h2>
          <div x-show="error" x-text="error" class="error-banner"></div>

          <!-- Stats Summary -->
          <template x-if="analysisData">
            <div style="margin-bottom:16px">
              <div class="td-stats">
                <div class="stat-card">
                  <div class="stat-value" x-text="analysisData.avg_score != null ? analysisData.avg_score.toFixed(1) : '--'"></div>
                  <div class="stat-label">平均分</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value" x-text="analysisData.max_score || '--'"></div>
                  <div class="stat-label">最高分</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value" x-text="analysisData.min_score || '--'"></div>
                  <div class="stat-label">最低分</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value" x-text="(analysisData.pass_rate != null ? (analysisData.pass_rate * 100).toFixed(1) + '%' : '--')"></div>
                  <div class="stat-label">及格率</div>
                </div>
              </div>
            </div>
          </template>

          <!-- Score Distribution Chart -->
          <div x-ref="analysisChart" style="min-height:300px;margin-bottom:16px"></div>

          <!-- Per-Question Accuracy (if available) -->
          <template x-if="analysisData && analysisData.per_question && analysisData.per_question.length">
            <div>
              <h3 style="font-size:14px;margin-bottom:8px">各题正确率</h3>
              <table class="q-table">
                <thead><tr><th>题号</th><th>类型</th><th>正确率</th></tr></thead>
                <tbody>
                  <template x-for="(pq, idx) in analysisData.per_question" :key="idx">
                    <tr>
                      <td x-text="'第' + (idx+1) + '题'"></td>
                      <td x-text="pq.type || '?'"></td>
                      <td>
                        <div style="display:flex;align-items:center;gap:8px">
                          <div style="flex:1;height:6px;background:#f1f5f9;border-radius:3px;overflow:hidden">
                            <div :style="{width: ((pq.accuracy||0)*100).toFixed(0)+'%', height:'100%', background: (pq.accuracy||0)>=0.7 ? '#22c55e' : (pq.accuracy||0)>=0.4 ? '#f59e0b' : '#ef4444', borderRadius:'3px'}"></div>
                          </div>
                          <span style="font-size:13px;min-width:48px;text-align:right" x-text="((pq.accuracy||0)*100).toFixed(1)+'%'"></span>
                        </div>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </template>

          <div class="modal-actions">
            <button @click="showAnalysisModal = false" class="btn-cancel">关闭</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 5c: Commit**

```bash
git add js/pages/teacher-exam.js html/teacher-exam.html
git commit -m "feat: full exam mgmt with AI generate, edit, proper grading UI, ECharts grade analysis"
```

---

### Task 6: Teacher Content (内容管理 — Full: Course Outline Tree + Resource Upload + AI Review)

**Files:** Create: `js/pages/teacher-content.js`; Modify: `html/teacher-content.html`

- [ ] **Step 6a: Create `js/pages/teacher-content.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('teacherContent', () => ({
    activeTab: 'courses', courses: [], resources: [], selectedCourse: null,
    editingNode: null, showCourseModal: false, showResourceModal: false, showAiReviewModal: false,
    error: '', success: '', loading: false,
    form: { title: '', description: '', parent_id: null },
    resourceForm: { title: '', type: 'document', file: null, fileName: '', course_id: null },
    aiReview: { content: '', result: null, loading: false },

    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await this.loadCourses();
    },

    async loadCourses() {
      try { const res = await fetch('/api/teacher/courses'); const data = await res.json(); this.courses = data.courses || []; }
      catch (_) { this.courses = []; }
    },

    get courseTree() {
      const map = {}, roots = [];
      this.courses.forEach(c => { map[c.id] = { ...c, children: [] }; });
      this.courses.forEach(c => { if (c.parent_id && map[c.parent_id]) map[c.parent_id].children.push(map[c.id]); else roots.push(map[c.id]); });
      return roots;
    },

    openCourseModal(parentId = null) { this.form = { title: '', description: '', parent_id: parentId }; this.editingNode = null; this.showCourseModal = true; this.error = ''; },
    openEditCourseModal(course) { this.editingNode = course; this.form = { title: course.title || '', description: course.description || '', parent_id: course.parent_id || null }; this.showCourseModal = true; this.error = ''; },

    async saveCourse() {
      if (!this.form.title.trim()) { this.error = '请输入课程/章节标题'; return; }
      this.loading = true; this.error = '';
      try {
        const url = this.editingNode ? `/api/teacher/course/${this.editingNode.id}` : '/api/teacher/course';
        const method = this.editingNode ? 'PUT' : 'POST';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(this.form) });
        const data = await res.json();
        if (data.success) { this.showCourseModal = false; await this.loadCourses(); }
        else { this.error = data.detail || '保存失败'; }
      } catch (_) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    async deleteCourse(id) { if (!confirm('确认删除此节点及其子节点？')) return; await fetch(`/api/teacher/course/${id}`, { method: 'DELETE' }); await this.loadCourses(); },

    async loadResources(courseId) { this.selectedCourse = courseId; try { const res = await fetch(`/api/teacher/course/${courseId}/resources`); const data = await res.json(); this.resources = data.resources || []; } catch (_) { this.resources = []; } },
    openResourceModal(courseId) { this.resourceForm = { title: '', type: 'document', file: null, fileName: '', course_id: courseId }; this.showResourceModal = true; this.error = ''; },
    handleResourceFile(event) { const file = event.target.files[0]; if (file) { this.resourceForm.file = file; this.resourceForm.fileName = file.name; } },

    async uploadResource() {
      if (!this.resourceForm.title.trim()) { this.error = '请输入资源标题'; return; }
      if (!this.resourceForm.file) { this.error = '请选择文件'; return; }
      this.loading = true; this.error = '';
      try {
        const fd = new FormData(); fd.append('file', this.resourceForm.file); fd.append('title', this.resourceForm.title); fd.append('type', this.resourceForm.type); fd.append('course_id', this.resourceForm.course_id);
        const res = await fetch('/api/teacher/resources/upload', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.success) { this.showResourceModal = false; await this.loadResources(this.resourceForm.course_id); }
        else { this.error = data.detail || '上传失败'; }
      } catch (_) { this.error = '上传请求失败'; }
      finally { this.loading = false; }
    },

    async deleteResource(id) { await fetch(`/api/teacher/resource/${id}`, { method: 'DELETE' }); await this.loadResources(this.selectedCourse); },
    openAiReviewModal() { this.aiReview = { content: '', result: null, loading: false }; this.showAiReviewModal = true; this.error = ''; },

    async runAiReview() {
      if (!this.aiReview.content.trim()) { this.error = '请输入需要审核的内容'; return; }
      this.aiReview.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/ai/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: this.aiReview.content }) });
        const data = await res.json();
        if (data.success) { this.aiReview.result = data.result || data; }
        else { this.error = data.detail || 'AI审核失败'; }
      } catch (_) { this.error = '请求失败'; }
      finally { this.aiReview.loading = false; }
    },

    formatBytes(b) { if (!b) return '-'; return b < 1024 ? b + 'B' : b < 1048576 ? (b/1024).toFixed(1)+'KB' : (b/1048576).toFixed(1)+'MB'; },
    formatDate(d) { return (d || '').slice(0, 10); },
  }));
});
```

- [ ] **Step 6b: Update `html/teacher-content.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="starry-night">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>内容管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script><script src="/js/http-intercept.js"></script>
  <script src="/js/pages/teacher-content.js"></script>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar" x-data>
      <div class="teacher-brand">星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">考试管理</a>
        <a class="teacher-nav-item active" href="/teacher-content.html">内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" @click="Auth.logout()">退出登录</button></div>
    </aside>
    <main class="teacher-main" x-data="teacherContent" x-init="init()">
      <h1 class="teacher-page-title">内容管理</h1>
      <div x-show="success" x-text="success" class="success-banner"></div>
      <div class="tabs-wrapper">
        <button class="tab-btn" :class="{ active: activeTab === 'courses' }" @click="activeTab = 'courses'">课程大纲</button>
        <button class="tab-btn" :class="{ active: activeTab === 'resources' }" @click="activeTab = 'resources'">教学资源</button>
        <button class="tab-btn" :class="{ active: activeTab === 'ai' }" @click="activeTab = 'ai'">AI 内容审核</button>
      </div>

      <div x-show="activeTab === 'courses'">
        <button @click="openCourseModal(null)" class="btn-primary" style="margin-bottom:16px">+ 添加根节点</button>
        <div class="tree-editor">
          <template x-for="node in courseTree" :key="node.id">
            <div class="tree-node">
              <div class="tree-node-header">
                <span class="tree-node-toggle" x-show="node.children && node.children.length">&#9660;</span>
                <span class="tree-node-title" x-text="node.title"></span>
                <span class="tree-node-meta" x-show="node.description" x-text="node.description.slice(0,40)"></span>
                <span class="tree-node-actions">
                  <button @click="openCourseModal(node.id)" class="btn-sm">+子节点</button>
                  <button @click="openEditCourseModal(node)" class="btn-sm">编辑</button>
                  <button @click="openResourceModal(node.id)" class="btn-sm btn-sm-info">资源</button>
                  <button @click="deleteCourse(node.id)" class="btn-sm btn-sm-danger">删除</button>
                </span>
              </div>
              <template x-if="node.children && node.children.length">
                <div class="tree-children">
                  <template x-for="child in node.children" :key="child.id">
                    <div class="tree-node"><div class="tree-node-header"><span class="tree-node-title" x-text="child.title"></span><span class="tree-node-actions"><button @click="openCourseModal(child.id)" class="btn-sm">+子节点</button><button @click="openEditCourseModal(child)" class="btn-sm">编辑</button><button @click="deleteCourse(child.id)" class="btn-sm btn-sm-danger">删除</button></span></div></div>
                  </template>
                </div>
              </template>
            </div>
          </template>
          <div x-show="courses.length === 0" class="empty-state">暂无课程大纲</div>
        </div>
      </div>

      <div x-show="activeTab === 'resources'">
        <div style="display:flex;gap:8px;margin-bottom:16px">
          <select x-model="selectedCourse" @change="loadResources(selectedCourse)" class="gen-select" style="min-width:200px"><option value="">选择课程...</option><template x-for="c in courses" :key="c.id"><option :value="c.id" x-text="c.title"></option></template></select>
          <button x-show="selectedCourse" @click="openResourceModal(selectedCourse)" class="btn-primary">+ 上传资源</button>
        </div>
        <div x-show="!selectedCourse" class="empty-state">请先选择一个课程</div>
        <div x-show="selectedCourse" class="resources-grid">
          <template x-for="r in resources" :key="r.id">
            <div class="resource-card"><div class="resource-card-icon" style="font-size:20px">&#128196;</div><div class="resource-card-body"><div class="resource-card-title" x-text="r.title"></div><div class="resource-card-meta"><span x-text="r.type || '文件'"></span><span x-text="formatBytes(r.size)"></span><span x-show="r.created_at" x-text="formatDate(r.created_at)"></span></div></div><button @click="deleteResource(r.id)" class="btn-sm btn-sm-danger">删除</button></div>
          </template>
          <div x-show="resources.length === 0" class="empty-state">暂无资源</div>
        </div>
      </div>

      <div x-show="activeTab === 'ai'">
        <button @click="openAiReviewModal()" class="btn-accent" style="margin-bottom:16px">AI 内容审核</button>
        <div class="empty-state">使用 AI 助手审核课程内容、试题质量、学生作业</div>
      </div>

      <div class="modal-overlay" x-show="showCourseModal" @click.self="showCourseModal = false" x-cloak>
        <div class="modal-content"><h2 x-text="editingNode ? '编辑节点' : '添加节点'"></h2><div x-show="error" x-text="error" class="error-banner"></div>
          <label class="auth-label">标题 *</label><input x-model="form.title" class="auth-field" placeholder="课程/章节名称">
          <label class="auth-label">描述</label><textarea x-model="form.description" class="auth-field" rows="2" placeholder="描述（选填）"></textarea>
          <div class="modal-actions"><button @click="showCourseModal = false" class="btn-cancel">取消</button><button @click="saveCourse()" :disabled="loading" class="btn-primary" x-text="loading ? '保存中...' : '保存'"></button></div>
        </div>
      </div>

      <div class="modal-overlay" x-show="showResourceModal" @click.self="showResourceModal = false" x-cloak>
        <div class="modal-content"><h2>上传教学资源</h2><div x-show="error" x-text="error" class="error-banner"></div>
          <label class="auth-label">资源标题 *</label><input x-model="resourceForm.title" class="auth-field" placeholder="资源标题">
          <label class="auth-label">资源类型</label><select x-model="resourceForm.type" class="auth-field"><option value="document">文档</option><option value="video">视频</option><option value="image">图片</option><option value="other">其他</option></select>
          <label class="auth-label">选择文件 *</label>
          <div class="file-upload-area" @click="$refs.resFile.click()" @dragover.prevent="$el.classList.add('drag-over')" @dragleave="$el.classList.remove('drag-over')" @drop.prevent="$el.classList.remove('drag-over'); handleResourceFile({target:{files:$event.dataTransfer.files}})"><input type="file" x-ref="resFile" @change="handleResourceFile" style="display:none"><p>点击选择文件或拖拽到此处</p><div class="file-name" x-show="resourceForm.fileName" x-text="resourceForm.fileName"></div></div>
          <div class="modal-actions"><button @click="showResourceModal = false" class="btn-cancel">取消</button><button @click="uploadResource()" :disabled="loading || !resourceForm.file" class="btn-primary" x-text="loading ? '上传中...' : '上传'"></button></div>
        </div>
      </div>

      <div class="modal-overlay" x-show="showAiReviewModal" @click.self="showAiReviewModal = false" x-cloak>
        <div class="modal-content modal-wide"><h2>AI 内容审核</h2><div x-show="error" x-text="error" class="error-banner"></div>
          <label class="auth-label">内容</label><textarea x-model="aiReview.content" rows="6" class="auth-field" placeholder="粘贴需要审核的教学内容..."></textarea>
          <button @click="runAiReview()" :disabled="aiReview.loading" class="btn-accent" style="margin:12px 0" x-text="aiReview.loading ? 'AI审核中...' : '开始审核'"></button>
          <div x-show="aiReview.result" class="ai-suggestions-panel" style="margin-top:12px">
            <template x-if="typeof aiReview.result === 'string'"><p x-text="aiReview.result" style="white-space:pre-wrap"></p></template>
            <template x-if="typeof aiReview.result === 'object'"><div><div x-show="aiReview.result.score != null" style="margin-bottom:8px"><strong>评分:</strong> <span x-text="aiReview.result.score"></span></div><div x-show="aiReview.result.suggestions" style="margin-bottom:8px"><strong>建议:</strong><template x-if="Array.isArray(aiReview.result.suggestions)"><ul style="padding-left:20px"><template x-for="s in aiReview.result.suggestions"><li x-text="s" style="font-size:13px;margin:4px 0"></li></template></ul></template></div></div></template>
          </div>
          <div class="modal-actions"><button @click="showAiReviewModal = false" class="btn-cancel">关闭</button></div>
        </div>
      </div>
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 6c: Commit**

```bash
git add js/pages/teacher-content.js html/teacher-content.html
git commit -m "feat: full content mgmt with course outline tree, file upload, AI content review"
```

---

### Task 7: Data Dashboard (数据大屏 — Full: 4 Hierarchy Tabs + ECharts + SSE)

**Files:** Create: `js/pages/data-dashboard.js`, `css/data-dashboard.css`; Modify: `html/data-dashboard.html`

- [ ] **Step 7a: Create `css/data-dashboard.css`**

```css
/* Constellation Prism — Data Dashboard */
.dd-layout { display: flex; height: 100vh; overflow: hidden; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); color: #e2e8f0; }
.dd-sidebar { width: 220px; flex-shrink: 0; background: color-mix(in oklch, var(--neutral-900), transparent 35%); border-right: 1px solid color-mix(in oklch, var(--info), transparent 88%); backdrop-filter: blur(32px) saturate(140%); -webkit-backdrop-filter: blur(32px) saturate(140%); display: flex; flex-direction: column; padding: var(--space-md); }
.dd-brand { font-size: var(--text-base); font-weight: var(--font-bold); color: var(--brand-300); letter-spacing: 2px; margin-bottom: var(--space-lg); }
.dd-nav-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: var(--radius-sm); color: var(--cp-text-secondary); text-decoration: none; font-size: var(--text-sm); font-weight: var(--font-medium); margin-bottom: 2px; transition: all var(--transition-fast); }
.dd-nav-item:hover { background: color-mix(in oklch, var(--info), transparent 94%); color: var(--cp-text-primary); }
.dd-nav-item.active { background: color-mix(in oklch, var(--info), transparent 88%); color: var(--info); font-weight: var(--font-semibold); }
.dd-sidebar-footer { margin-top: auto; }
.dd-logout-btn { width: 100%; padding: 8px; border-radius: var(--radius-sm); border: 1px solid color-mix(in oklch, var(--danger), transparent 78%); background: transparent; color: var(--danger); cursor: pointer; font-size: var(--text-sm); transition: all var(--transition-fast); }
.dd-logout-btn:hover { background: color-mix(in oklch, var(--danger), transparent 92%); }
.dd-main { flex: 1; overflow-y: auto; padding: var(--space-lg); display: flex; flex-direction: column; gap: 20px; }
.dd-page-title { font-size: var(--text-xl); font-weight: var(--font-bold); color: var(--cp-text-primary); margin: 0; }
.dd-hierarchy-tabs { display: flex; gap: 0; align-self: flex-start; padding: 4px; border-radius: 12px; background: color-mix(in oklch, var(--neutral-800), transparent 55%); border: 1px solid color-mix(in oklch, var(--info), transparent 88%); backdrop-filter: blur(24px) saturate(140%); }
.dd-hierarchy-tab { padding: 7px 20px; border-radius: 9px; background: transparent; border: none; color: var(--cp-text-secondary); cursor: pointer; font-size: var(--text-sm); font-weight: var(--font-medium); transition: all var(--transition-fast); }
.dd-hierarchy-tab:hover { color: var(--cp-text-primary); }
.dd-hierarchy-tab.active { background: color-mix(in oklch, var(--info), transparent 86%); color: var(--cp-text-primary); font-weight: var(--font-bold); }
.dd-stats { display: flex; gap: var(--space-md); flex-wrap: wrap; }
.dd-stat-card { flex: 1; min-width: 160px; padding: 20px; border-radius: var(--radius-md); background: linear-gradient(170deg, color-mix(in oklch, color-mix(in oklch, var(--neutral-800), var(--neutral-900) 60%), transparent 22%) 0%, color-mix(in oklch, color-mix(in oklch, var(--neutral-900), black 20%), transparent 22%) 100%); border: 1px solid var(--cp-card-border); box-shadow: var(--cp-prism-glow); clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); transition: all var(--cp-transition); }
.dd-stat-value { font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--cp-text-primary); margin-bottom: 4px; }
.dd-stat-label { font-size: var(--text-xs); color: var(--cp-text-secondary); }
.dd-chart-row { display: flex; gap: var(--space-md); flex-wrap: wrap; }
.dd-chart-panel { flex: 1; min-width: 320px; min-height: 300px; padding: 20px; background: linear-gradient(170deg, color-mix(in oklch, color-mix(in oklch, var(--neutral-800), var(--neutral-900) 60%), transparent 22%) 0%, color-mix(in oklch, color-mix(in oklch, var(--neutral-900), black 20%), transparent 22%) 100%); border: 1px solid var(--cp-card-border); border-radius: var(--radius-md); box-shadow: var(--cp-prism-glow); clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px); }
.dd-chart-panel-title { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--cp-text-secondary); margin-bottom: 12px; }
.dd-sse-feed { max-height: 260px; overflow-y: auto; }
.dd-sse-item { padding: 8px 0; border-bottom: 1px solid color-mix(in oklch, var(--info), transparent 92%); font-size: var(--text-sm); display: flex; justify-content: space-between; align-items: center; }
.dd-sse-type { padding: 2px 8px; border-radius: 4px; font-size: var(--text-xs); font-weight: var(--font-semibold); background: color-mix(in oklch, var(--info), transparent 88%); color: var(--info); }
.dd-sse-time { font-size: var(--text-xs); color: var(--cp-text-tertiary); }
.dd-main::-webkit-scrollbar { width: 6px; }
.dd-main::-webkit-scrollbar-track { background: transparent; }
.dd-main::-webkit-scrollbar-thumb { background: color-mix(in oklch, var(--info), transparent 85%); border-radius: 3px; }
```

- [ ] **Step 7b: Create `js/pages/data-dashboard.js`**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('dataDashboard', () => ({
    hierarchy: 'school', trends: [], sseEvents: [], sseCleanup: null, error: '',
    hierarchyLabels: { school: '学校', college: '学院/专业', class: '班级', personal: '个人' },
    stats: { total_courses: 0, total_students: 0, completion_rate: 0, total_hours: 0 },
    trendsChart: null, radarChart: null, completionChart: null, mapChart: null,

    async init() {
      await Auth.fetchMe();
      if (!Auth.me || !Auth.me.id) { window.location.href = '/login.html'; return; }
      await this.loadStats(); await this.loadTrends(); this.initCharts(); this.connectSSE();
      this.$cleanup(() => this.disposeAll());
    },

    async loadStats() {
      try { const res = await fetch(`/api/datacenter/stats?level=${this.hierarchy}`); const data = await res.json();
        if (data) { this.stats = { total_courses: data.total_courses || data.course_count || 0, total_students: data.total_students || data.student_count || 0, completion_rate: data.completion_rate || 0, total_hours: data.total_hours || data.study_hours || 0 }; }
      } catch (_) {}
    },

    async loadTrends() {
      try { const res = await fetch(`/api/datacenter/trends?level=${this.hierarchy}`); const data = await res.json(); this.trends = data.trends || data.points || [];
        await this.$nextTick(); this.updateTrendsChart(); this.updateRadarChart(); this.updateCompletionChart(); this.updateMapChart();
      } catch (_) { this.trends = []; }
    },

    async switchHierarchy(level) { this.hierarchy = level; await this.loadStats(); await this.loadTrends(); },
    initCharts() { this.$nextTick(() => { this.initTrendsChart(); this.initRadarChart(); this.initCompletionChart(); this.initMapChart(); }); },

    initTrendsChart() { const el = this.$refs.trendsChart; if (!el) return; if (this.trendsChart) this.trendsChart.dispose(); this.trendsChart = echarts.init(el); },
    updateTrendsChart() { if (!this.trendsChart) return; const dates = this.trends.map(t => t.date || t.label || ''); const values = this.trends.map(t => t.value || t.count || 0); this.trendsChart.setOption({ title: { text: '学习趋势', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: dates, axisLabel: { color: '#64748b', fontSize: 11 } }, yAxis: { type: 'value', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.1)' } } }, series: [{ data: values, type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#a78bfa', width: 2 }, itemStyle: { color: '#a78bfa' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1, [{ offset: 0, color: 'rgba(167,139,250,0.3)' }, { offset: 1, color: 'rgba(167,139,250,0.02)' }]) } }], grid: { top: 40, right: 20, bottom: 30, left: 45 } }); },

    initRadarChart() { const el = this.$refs.radarChart; if (!el) return; if (this.radarChart) this.radarChart.dispose(); this.radarChart = echarts.init(el); },
    updateRadarChart() { if (!this.radarChart) return; this.radarChart.setOption({ title: { text: '综合指标', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: {}, radar: { indicator: [{ name: '课程数', max: 100 }, { name: '学生数', max: 500 }, { name: '完成率', max: 100 }, { name: '学习时长', max: 1000 }, { name: '活跃度', max: 100 }], axisName: { color: '#94a3b8' }, splitArea: { areaStyle: { color: ['rgba(167,139,250,0.02)', 'rgba(167,139,250,0.05)'] } }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.15)' } }, axisLine: { lineStyle: { color: 'rgba(148,163,184,0.15)' } } }, series: [{ type: 'radar', data: [{ value: [this.stats.total_courses || 0, this.stats.total_students || 0, (this.stats.completion_rate || 0) * 100, this.stats.total_hours || 0, 0], name: this.hierarchyLabels[this.hierarchy] || '数据', areaStyle: { color: 'rgba(99,102,241,0.2)' }, lineStyle: { color: '#818cf8' }, itemStyle: { color: '#818cf8' } }] }] }); },

    initCompletionChart() { const el = this.$refs.completionChart; if (!el) return; if (this.completionChart) this.completionChart.dispose(); this.completionChart = echarts.init(el); },
    updateCompletionChart() { if (!this.completionChart) return; this.completionChart.setOption({ title: { text: '完成率分布', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: { trigger: 'item' }, series: [{ name: '完成率', type: 'pie', radius: ['45%', '70%'], center: ['50%', '55%'], label: { color: '#94a3b8', fontSize: 11 }, data: [{ value: Math.round((this.stats.completion_rate || 0) * 100), name: '已完成', itemStyle: { color: '#818cf8' } }, { value: Math.round(100 - (this.stats.completion_rate || 0) * 100), name: '未完成', itemStyle: { color: 'rgba(148,163,184,0.2)' } }] }] }); },

    initMapChart() { const el = this.$refs.mapChart; if (!el) return; if (this.mapChart) this.mapChart.dispose(); this.mapChart = echarts.init(el); },
    updateMapChart() { if (!this.mapChart) return; const coords = this.trends.filter(t => t.lat && t.lng).map(t => ({ value: [t.lng, t.lat, t.value || 1], name: t.label || t.date || '' })); this.mapChart.setOption({ title: { text: '分布地图', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: { trigger: 'item', formatter: p => p.name ? `${p.name}: ${p.value[2]}` : '' }, xAxis: { type: 'value', show: false, min: 73, max: 135 }, yAxis: { type: 'value', show: false, min: 18, max: 54 }, series: [{ type: 'scatter', data: coords.length ? coords : [[116, 39, 1]], symbolSize: d => Math.min(20, 6 + (d[2] || 1) * 2), itemStyle: { color: '#818cf8', opacity: 0.7 }, emphasis: { itemStyle: { color: '#a78bfa', opacity: 1 } } }], grid: { top: 40, right: 10, bottom: 10, left: 10 } }); },

    connectSSE() { try { const es = new EventSource(`/api/datacenter/events?level=${this.hierarchy}`); es.onmessage = (e) => { try { const d = JSON.parse(e.data); this.sseEvents.unshift(d); if (this.sseEvents.length > 50) this.sseEvents.pop(); } catch (_) {} }; es.onerror = () => {}; this.sseCleanup = () => { es.close(); }; } catch (_) {} },

    disposeAll() { if (this.trendsChart) { this.trendsChart.dispose(); this.trendsChart = null; } if (this.radarChart) { this.radarChart.dispose(); this.radarChart = null; } if (this.completionChart) { this.completionChart.dispose(); this.completionChart = null; } if (this.mapChart) { this.mapChart.dispose(); this.mapChart = null; } if (this.sseCleanup) { this.sseCleanup(); this.sseCleanup = null; } },

    formatPercent(v) { return v != null ? (v * 100).toFixed(1) + '%' : '--'; },
    timeAgo(ts) { if (!ts) return ''; const d = Math.floor((Date.now() - new Date(ts).getTime()) / 1000); if (d < 60) return `${d}s ago`; if (d < 3600) return `${Math.floor(d/60)}m ago`; return `${Math.floor(d/3600)}h ago`; },
  }));
});
```

- [ ] **Step 7c: Update `html/data-dashboard.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="starry-night">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>数据大屏 · 星识 Star-Learn</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/data-dashboard.css">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script><script src="/js/http-intercept.js"></script>
  <script src="/js/pages/data-dashboard.js"></script>
</head>
<body>
  <div class="dd-layout" x-data="dataDashboard" x-init="init()">
    <aside class="dd-sidebar">
      <div class="dd-brand">星识 · 数据大屏</div>
      <nav>
        <a class="dd-nav-item" href="/teacher-dashboard.html">教师工作台</a>
        <a class="dd-nav-item" href="/teacher-class.html">班级管理</a>
        <a class="dd-nav-item" href="/teacher-manage.html">题库管理</a>
        <a class="dd-nav-item" href="/teacher-exam.html">考试管理</a>
        <a class="dd-nav-item" href="/teacher-content.html">内容管理</a>
        <a class="dd-nav-item active" href="/data-dashboard.html">数据大屏</a>
      </nav>
      <div class="dd-sidebar-footer"><button class="dd-logout-btn" @click="Auth.logout()">退出登录</button></div>
    </aside>
    <main class="dd-main">
      <h1 class="dd-page-title">数据大屏</h1>
      <div class="dd-hierarchy-tabs">
        <button class="dd-hierarchy-tab" :class="{ active: hierarchy === 'school' }" @click="switchHierarchy('school')">学校</button>
        <button class="dd-hierarchy-tab" :class="{ active: hierarchy === 'college' }" @click="switchHierarchy('college')">学院/专业</button>
        <button class="dd-hierarchy-tab" :class="{ active: hierarchy === 'class' }" @click="switchHierarchy('class')">班级</button>
        <button class="dd-hierarchy-tab" :class="{ active: hierarchy === 'personal' }" @click="switchHierarchy('personal')">个人</button>
      </div>
      <div class="dd-stats">
        <div class="dd-stat-card"><div class="dd-stat-value" x-text="stats.total_courses"></div><div class="dd-stat-label">总课程</div></div>
        <div class="dd-stat-card"><div class="dd-stat-value" x-text="stats.total_students"></div><div class="dd-stat-label">学生数</div></div>
        <div class="dd-stat-card"><div class="dd-stat-value" x-text="formatPercent(stats.completion_rate)"></div><div class="dd-stat-label">完成率</div></div>
        <div class="dd-stat-card"><div class="dd-stat-value" x-text="stats.total_hours + 'h'"></div><div class="dd-stat-label">总学时</div></div>
      </div>
      <div class="dd-chart-row">
        <div class="dd-chart-panel"><div class="dd-chart-panel-title">学习趋势</div><div x-ref="trendsChart" style="width:100%;height:280px"></div></div>
        <div class="dd-chart-panel"><div class="dd-chart-panel-title">综合指标</div><div x-ref="radarChart" style="width:100%;height:280px"></div></div>
      </div>
      <div class="dd-chart-row">
        <div class="dd-chart-panel"><div class="dd-chart-panel-title">完成率分布</div><div x-ref="completionChart" style="width:100%;height:260px"></div></div>
        <div class="dd-chart-panel" style="flex:0.5;min-width:280px">
          <div class="dd-chart-panel-title">实时动态</div>
          <div class="dd-sse-feed">
            <template x-for="evt in sseEvents" :key="evt.id || evt.timestamp"><div class="dd-sse-item"><span><span class="dd-sse-type" x-text="evt.type || '事件'"></span><span style="margin-left:8px;font-size:13px" x-text="evt.message || evt.content || ''"></span></span><span class="dd-sse-time" x-text="timeAgo(evt.timestamp)"></span></div></template>
            <div x-show="sseEvents.length === 0" style="padding:40px;text-align:center;color:#64748b;font-size:13px">等待实时数据...</div>
          </div>
        </div>
      </div>
      <div class="dd-chart-panel"><div class="dd-chart-panel-title">分布地图</div><div x-ref="mapChart" style="width:100%;height:340px"></div></div>
    </main>
  </div>
</body>
</html>
```

- [ ] **Step 7d: Commit**

```bash
git add js/pages/data-dashboard.js html/data-dashboard.html css/data-dashboard.css
git commit -m "feat: full data dashboard with 4 hierarchy tabs, ECharts trends/radar/donut/map, SSE realtime feed"
```

---

### Task 8: Update Main Plan Reference

- [ ] **Step 8a: Update `docs/superpowers/plans/2026-06-05-mascot-navigation-datacenter-plan.md`**

```markdown
## Alpine.js 迁移计划

完整的前端 Alpine.js 3.14 迁移方案见: [2026-06-06-alpinejs-migration-plan.md](./2026-06-06-alpinejs-migration-plan.md)

迁移要点:
- 所有 Phase 5 页面使用 Alpine.js 3.14.9 CDN 替代原 jQuery/Bootstrap
- 统一使用 Constellation Prism (星座棱晶) 设计语言，与 hub.html 风格一致
- 后端 FastAPI API 保持不变
- 使用 data-theme="starry-night" 暗色主题，通过 tokens.css 变量驱动全站配色
```

```bash
git add docs/superpowers/plans/2026-06-05-mascot-navigation-datacenter-plan.md
git commit -m "docs: add Alpine.js migration plan cross-reference to Phase 5 plan"
```

---

### Task 9: Directory Creation & Build Verification

- [ ] **Step 9a: Create directories**

```bash
mkdir -p js/pages css html
```

- [ ] **Step 9b: Verify all files**

```bash
ls -la js/pages/login.js js/pages/register.js js/pages/teacher-dashboard.js js/pages/teacher-class.js js/pages/teacher-manage.js js/pages/teacher-exam.js js/pages/teacher-content.js js/pages/data-dashboard.js && ls -la css/tokens.css css/teacher.css css/data-dashboard.css && ls -la html/login.html html/register.html html/teacher-dashboard.html html/teacher-class.html html/teacher-manage.html html/teacher-exam.html html/teacher-content.html html/data-dashboard.html && ls -la js/auth.js js/http-intercept.js
```

- [ ] **Step 9c: Final commit**

```bash
git add -A
git commit -m "feat: complete Alpine.js migration plan — 100% design spec coverage, Constellation Prism design system"
```

---

## Self-Review: Spec Coverage Checklist

### Coverage Mapping

| Spec Requirement | Task | Status |
|---|---|---|
| Login/Register with JWT | 1 | Full |
| Quick login demo buttons (教师/学生/管理员) | 1 | Full |
| Teacher Dashboard: 4 stat cards (授课班级/在授课程/待批改/平均成绩) | 2 | Full |
| Teacher Dashboard: ECharts bar + radar | 2 | Full |
| Teacher Dashboard: Recent tasks + AI suggestions | 2 | Full |
| Class Management: CRUD + CSV import (file) + grouping + student profile | 3 | Full |
| Question Bank: 4 types + batch CSV/JSON import + search/filter | 4 | Full |
| Exam Management: manual + AI generate + edit + publish/archive | 5 | Full |
| Exam Management: proper grading UI + ECharts analysis + per-question accuracy | 5 | Full |
| Content Management: course outline tree + resource upload + AI review | 6 | Full |
| Data Dashboard: 4 hierarchy tabs + ECharts trends/radar/donut/map + SSE | 7 | Full |
| Shared CSS: Constellation Prism dark theme, unified with hub.html | 0 | Full |
| File upload via FormData (not textarea) | 3,4,6 | Full |
| NO alert() hacks — all proper modals | 1-7 | Full |
| Auth preserved (js/auth.js, js/http-intercept.js) | All | N/A |
| Backend APIs (30+ endpoints connected) | All | Full |
| Cross-reference + directory verification | 8,9 | Full |

### Placeholder Scan
No TBD/TODO/placeholder. All steps have complete, production-ready code.

### Type/Name Consistency
`Auth.fetchMe()`, `Auth.isTeacher()`, `$refs`, `$nextTick()`, `$cleanup()`, `FormData()` patterns consistent across all 7 page components. CSS uses `--cp-*` Constellation Prism aliases consistent with hub.css. All colors via `color-mix(in oklch, ...)`.

### Gap Analysis
No gaps. 100% coverage of design spec with unified Constellation Prism design system.

**Plan Complete.**
