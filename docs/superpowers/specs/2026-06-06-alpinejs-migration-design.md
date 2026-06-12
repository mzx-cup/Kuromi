# Alpine.js 前端框架迁移设计文档

> **日期**: 2026-06-06
> **状态**: 设计提案 — 待审批
> **范围**: Phase 5 全部新增前端页面 + Phase 3/4 可受益页面

---

## 1. 动机

第 9 次综合审计发现了 41 个问题，其中 **8 个 Critical/High 问题源于 vanilla JS 原生模式**：

| 问题类别 | 审计 ID | 根因 |
|----------|---------|------|
| inline onclick 调用 IIFE 局部函数 | C6, H2, H3 | `onclick="loadExams()"` 但函数在闭包内 |
| DOM 元素 ID 不一致 | H4, M7 | `#realtime-feed` vs `#data-flow-panel` |
| 字段名不一致（`q.title` vs `q.content`）| H1, M15 | 无类型检查的字符串拼接 |
| 类型不匹配（string → list）| C7, M14 | `input.value` 永远是字符串，无自动转换 |
| auth.js 在非登录页崩溃 | C1 | 无声明式条件绑定 |
| EventSource 无清理 | H10 | 手动生命周期管理 |
| `.auth-submit` 样式缺失 | C8, H5 | 不同页面 CSS 引用不一致 |
| innerHTML 拼接的模板与数据不一致 | H1 | 无编译期/运行期验证 |

**根本原因**：Vanilla JS 依赖字符串拼接、手动 DOM 操作、全局作用域调用，AI 生成代码时极容易出错。

## 2. 方案选择：Alpine.js

### 2.1 为什么不选 HTMX

| 需求 | HTMX | Alpine.js |
|------|------|-----------|
| 弹窗/模态框 | 需要扩展（hyperscript） | 原生 `x-show` |
| 条件渲染 | 需服务端返回不同 HTML | 声明式 `x-if`/`x-show` |
| 表单双向绑定 | 无 | `x-model` |
| 列表渲染 | 需服务端返回 HTML 片段 | `x-for` 客户端渲染 |
| 不增加后端端点 | 每个交互需要一个 SSR 端点 | 零后端改动 |

当前 5 个 teacher 页面大量使用弹窗、条件渲染、客户端表单验证 — HTMX 不适合。

### 2.2 Alpine.js 核心优势

- **零构建**：CDN `<script>` 标签，不需要 npm/vite/webpack
- **体积小**：~15KB gzipped
- **渐进式**：与现有 vanilla JS 页面完全共存
- **声明式 + 响应式**：消除 DOM 查询、innerHTML 拼接、手动事件绑定
- **AI 友好**：逻辑是普通 JS 对象 `() => ({ ... })`，模板是 HTML 属性，AI 几乎不会写错

### 2.3 CDN 版本

```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
```

添加到每个页面的 `<head>`，替代 `DOMContentLoaded` 初始化模式。

## 3. 模式迁移对照表

每个 vanilla JS 痛点对应一个 Alpine.js 解决方案：

### 3.1 DOM 查询 → 响应式状态

**Before (vanilla JS):**
```javascript
document.getElementById('stat-pending').textContent = reviews.filter(r => r.status === 'pending').length;
document.getElementById('exam-grid').innerHTML = data.map(e => `<div>${e.title}</div>`).join('');
const title = document.getElementById('exam-title-input').value;
```

**After (Alpine.js):**
```html
<span x-text="reviews.filter(r => r.status === 'pending').length"></span>
<template x-for="e in exams" :key="e.id">
  <div x-text="e.title"></div>
</template>
<input x-model="form.title">
```

### 3.2 事件绑定 → 声明式指令

**Before (vanilla JS):**
```javascript
document.getElementById('btn-create-exam').addEventListener('click', () => { ... });
document.getElementById('btn-cancel-exam')?.addEventListener('click', hideCreateModal);
```

**After (Alpine.js):**
```html
<button @click="showModal = true">+ 创建考试</button>
<button @click="showModal = false">取消</button>
```

### 3.3 条件显示 → `x-show`

**Before (vanilla JS):**
```javascript
modal.style.display = 'flex';   // show
modal.style.display = 'none';   // hide
```

**After (Alpine.js):**
```html
<div class="modal-overlay" x-show="showModal" @click.self="showModal = false">
```

### 3.4 初始化 → `x-init`

**Before (vanilla JS):**
```javascript
(function() {
  'use strict';
  async function init() { ... }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
```

**After (Alpine.js):**
```html
<div x-data="pageComponent()" x-init="init()">
```
```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('pageComponent', () => ({
    // state
    async init() { ... },
  }));
});
```

### 3.5 inline onclick 作用域 → `@click`

**Before (vanilla JS) — BROKEN:**
```html
<button onclick="fetch('...').then(() => loadExams())">  <!-- ReferenceError! -->
```

**After (Alpine.js):**
```html
<button @click="publishExam(exam.id)">发布</button>
```

### 3.6 表单提交 → `@submit.prevent`

**Before (vanilla JS):**
```javascript
document.getElementById('btn-save-exam')?.addEventListener('click', async () => {
  const title = document.getElementById('exam-title-input').value.trim();
  const duration = parseInt(document.getElementById('exam-duration-input').value) || 120;
  // ...
});
```

**After (Alpine.js):**
```javascript
async saveExam() {
  if (!this.form.title.trim()) { this.error = '请输入标题'; return; }
  const res = await fetch('/api/teacher/exam', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: this.form.title, duration: this.form.duration, ... }),
  });
  if (res.ok) { this.showModal = false; await this.loadExams(); }
}
```

### 3.7 EventSource 生命周期 → `x-effect` + `$cleanup`

**Before (vanilla JS):**
```javascript
const es = new EventSource(url);  // never closed, leaks on page unload
```

**After (Alpine.js):**
```javascript
this.es = new EventSource(url);
this.es.onmessage = (e) => { this.events.push(JSON.parse(e.data)); };
// Alpine auto-calls $cleanup on component destroy
this.$cleanup(() => this.es.close());
```

## 4. 组件拆分

### 4.1 全局组件（Alpine.data 注册）

每个页面用 `Alpine.data('name', () => ({ ... }))` 注册一个全局组件。放在各页面的 `<script>` 中（或提取到共享的 `js/alpine-components.js`）。

```
js/alpine-components.js            — 共享 Alpine.data 注册（可选，按需提取）
  ├── teacherFormMixin()            — 弹窗打开/关闭、loading、error 通用逻辑
  ├── fetchWithAuth(url, opts)      — 复用 http-intercept.js 的 fetch 包装
  └── useEventSource(url)           — SSE 生命周期管理
```

### 4.2 页面级组件

每个页面用一个 `Alpine.data()` 注册：

| 页面 | Alpine.data 名称 | 核心状态 |
|------|-----------------|----------|
| `login.html` | `loginPage` | `{form:{username,password}, error, loading}` |
| `register.html` | `registerPage` | `{form:{username,password,display_name,role}, error}` |
| `teacher-dashboard.html` | `teacherDashboard` | `{stats:{}, chartData:{}}` |
| `teacher-class.html` | `teacherClass` | `{classes:[], showModal, form:{name,subject}, students:[]}` |
| `teacher-manage.html` | `teacherManage` | `{questions:[], showModal, form:{type,content,options,answer,...}}` |
| `teacher-exam.html` | `teacherExam` | `{exams:[], showModal, form:{title,duration,classIds:[],questionIds:[]}}` |
| `teacher-content.html` | `teacherContent` | `{reviews:[], lessons:[], genForm:{lessonId,model}, genStatus}` |
| `data-dashboard.html` | `dataDashboard` | `{stats:{}, charts:{}, realtime:[], activeTab:'overview'}` |

### 4.3 组件模板

**teacherExam 示例 (完整):**

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('teacherExam', () => ({
    // ---- State ----
    exams: [],
    classes: [],
    questions: [],
    showModal: false,
    loading: false,
    error: '',
    form: {
      title: '',
      duration: 120,
      classIds: [],
      questionIds: [],
    },

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await this.loadExams();
    },

    // ---- Actions ----
    async loadExams() {
      const res = await fetch('/api/teacher/exams');
      const data = await res.json();
      this.exams = data.exams || [];
    },

    async openCreateModal() {
      this.showModal = true;
      this.form = { title: '', duration: 120, classIds: [], questionIds: [] };
      // 并行加载班级和试题
      const [clsRes, qRes] = await Promise.all([
        fetch('/api/teacher/classes'),
        fetch('/api/teacher/questions'),
      ]);
      const clsData = await clsRes.json();
      const qData = await qRes.json();
      this.classes = clsData.classes || [];
      this.questions = qData.questions || [];
    },

    async createExam() {
      if (!this.form.title.trim()) { this.error = '请输入考试标题'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/exam', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: this.form.title,
            question_ids: this.form.questionIds,
            class_ids: this.form.classIds,
            duration: this.form.duration,
          }),
        });
        const data = await res.json();
        if (data.success) {
          this.showModal = false;
          await this.loadExams();
        } else {
          this.error = data.detail || '创建失败';
        }
      } catch (e) {
        this.error = '请求失败: ' + e.message;
      } finally {
        this.loading = false;
      }
    },

    async publishExam(id) {
      await fetch(`/api/teacher/exam/${id}/publish`, { method: 'POST' });
      await this.loadExams();
    },

    async deleteExam(id) {
      if (!confirm('确认删除？')) return;
      await fetch(`/api/teacher/exam/${id}`, { method: 'DELETE' });
      await this.loadExams();
    },

    async gradeExam(id) {
      const res = await fetch(`/api/teacher/exam/${id}/grade`, { method: 'POST' });
      const data = await res.json();
      alert('待批阅: ' + data.count + ' 份答卷');
    },

    async viewResults(id) {
      const res = await fetch(`/api/teacher/exam/${id}/results`);
      const data = await res.json();
      const lines = (data.results || []).map(r => `学生${r.display_name || r.student_id}: ${r.score || '未评分'}分`).join('\n');
      alert('成绩列表:\n' + (lines || '暂无提交'));
    },

    toggleClassId(id) {
      const idx = this.form.classIds.indexOf(id);
      if (idx >= 0) this.form.classIds.splice(idx, 1);
      else this.form.classIds.push(id);
    },

    toggleQuestionId(id) {
      const idx = this.form.questionIds.indexOf(id);
      if (idx >= 0) this.form.questionIds.splice(idx, 1);
      else this.form.questionIds.push(id);
    },
  }));
});
```

**对应 HTML:**

```html
<div x-data="teacherExam" x-init="init()">
  <button @click="openCreateModal()" class="auth-submit">+ 创建考试</button>

  <!-- 列表 -->
  <template x-if="exams.length === 0">
    <p style="color:var(--text-tertiary)">暂无考试</p>
  </template>
  <div class="exam-grid">
    <template x-for="exam in exams" :key="exam.id">
      <div class="exam-card">
        <h3 x-text="exam.title"></h3>
        <div class="exam-meta">
          <span>状态: <span x-text="exam.status" :class="'exam-status exam-status-' + exam.status"></span></span>
          <span>时长: <span x-text="exam.duration"></span>分钟</span>
        </div>
        <div style="margin-top:12px;display:flex;gap:8px">
          <button x-show="exam.status === 'draft'" @click="publishExam(exam.id)">发布</button>
          <button @click="viewResults(exam.id)">查看成绩</button>
          <button @click="gradeExam(exam.id)">开始批阅</button>
          <button @click="deleteExam(exam.id)" style="color:#ef4444">删除</button>
        </div>
      </div>
    </template>
  </div>

  <!-- 弹窗 -->
  <div class="modal-overlay" x-show="showModal" @click.self="showModal = false">
    <div class="modal-content">
      <h2>创建考试</h2>
      <div x-show="error" x-text="error" style="color:#ef4444;font-size:13px;margin-bottom:8px"></div>

      <label>标题</label>
      <input x-model="form.title" class="auth-field" placeholder="考试标题">

      <label>时长（分钟）</label>
      <input x-model.number="form.duration" type="number" min="1" class="auth-field">

      <label>班级</label>
      <div class="checkbox-group">
        <template x-for="c in classes" :key="c.id">
          <label>
            <input type="checkbox" :value="c.id" @change="toggleClassId(c.id)">
            <span x-text="c.name"></span>
          </label>
        </template>
      </div>

      <label>试题</label>
      <div class="checkbox-group">
        <template x-for="q in questions" :key="q.id">
          <label>
            <input type="checkbox" :value="q.id" @change="toggleQuestionId(q.id)">
            <span x-text="'[' + (q.type||'?') + '] ' + (q.content||'').slice(0, 40)"></span>
          </label>
        </template>
      </div>

      <div class="modal-actions">
        <button @click="showModal = false" class="btn-cancel">取消</button>
        <button @click="createExam()" :disabled="loading" x-text="loading ? '创建中...' : '创建考试'"></button>
      </div>
    </div>
  </div>
</div>
```

### 4.4 对比：代码量变化

| 页面 | Vanilla JS 行数 | Alpine.js 行数 | 减少 |
|------|----------------|---------------|------|
| teacher-exam | ~70 行 JS + 内联 onclick | ~65 行 JS (Alpine.data) | DOM 操作代码全部消除 |
| teacher-manage | ~45 行 JS + 内联 onclick | ~50 行 JS (Alpine.data) | 消除 innerHTML 拼接 + onclick 作用域问题 |
| teacher-content | ~40 行 JS | ~45 行 JS | 消除 getElementById 级联 |
| teacher-class | ~55 行 JS + 内联 onclick | ~55 行 JS | 消除 DOM 查询链 |
| data-dashboard | ~120 行 JS | ~100 行 JS | ECharts 仍用 JS 操作，状态管理用 Alpine |
| teacher-dashboard | ~70 行 JS | ~65 行 JS | 消除 innerHTML 统计卡片 |

**关键变化不是行数，而是代码可靠性**：Alpine.js 版本消除了字符串拼接的 HTML 模板、手动 DOM 查询、全局 onclick 作用域问题。

## 5. 与现有代码的共存

### 5.1 不迁移的部分

以下文件保持 vanilla JS，不迁移：

| 文件 | 原因 |
|------|------|
| `js/auth.js` | 纯工具函数（`getToken`/`login`/`logout`/`fetchMe`），无 DOM 操作 |
| `js/http-intercept.js` | 全局 fetch/XHR 拦截器，独立于页面框架 |
| `js/mascot.js` | Live2D 控制器，大量 Canvas API + SSE + MediaRecorder，Alpine 无优势 |
| `js/kanban.js` | 已有代码，不在 Phase 5 范围 |
| `js/search-command.js` | ⌘K 弹窗，Fuse.js 搜索逻辑，可在 Phase 4 后单独评估 |
| `js/onboarding.js` | 引导流程，DOM 动画密集，可在 Phase 4 后单独评估 |
| `html/hub.html` | 已有复杂页面 |
| `html/index.html` | 已有复杂页面 |

### 5.2 共享基础设施

Alpine.js 页面与 vanilla JS 页面共享：
- `js/auth.js` — `Auth.getToken()` / `Auth.isTeacher()` / `Auth.fetchMe()`
- `js/http-intercept.js` — 自动注入 Bearer token
- `css/tokens.css` — CSS 变量
- `css/teacher.css` — 教师端共享样式（需补充 `.modal-overlay`/`.auth-submit` 样式）

### 5.3 页面 `<head>` 模板

```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>考试管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/teacher.css">
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
  <script src="/js/auth.js"></script>
  <script src="/js/http-intercept.js"></script>
  <!-- 页面 Alpine.data 注册 -->
  <script src="/js/pages/teacher-exam.js"></script>
</head>
```

注意顺序：`http-intercept.js` 必须在 `auth.js` 之后加载（它依赖 `Auth`），Alpine.js 用 `defer` 异步加载，页面组件脚本在 `<head>` 底部。

## 6. 文件结构变更

```
Phase 5 (知域迁移):
  新增:
    js/pages/teacher-dashboard.js   — Alpine.data('teacherDashboard', ...)
    js/pages/teacher-class.js       — Alpine.data('teacherClass', ...)
    js/pages/teacher-manage.js      — Alpine.data('teacherManage', ...)
    js/pages/teacher-exam.js        — Alpine.data('teacherExam', ...)
    js/pages/teacher-content.js     — Alpine.data('teacherContent', ...)
    js/pages/data-dashboard.js      — Alpine.data('dataDashboard', ...)
    js/pages/login.js               — Alpine.data('loginPage', ...) [替代 js/login.js]
    js/pages/register.js            — Alpine.data('registerPage', ...) [替代 js/register.js]

  不再创建:
    js/teacher-dashboard.js         — 迁移到 js/pages/
    js/teacher-class.js             — 迁移到 js/pages/
    js/teacher-manage.js            — 迁移到 js/pages/
    js/teacher-exam.js              — 迁移到 js/pages/
    js/teacher-content.js           — 迁移到 js/pages/
    js/data-dashboard.js            — 迁移到 js/pages/

  保留不变:
    js/auth.js                      — 工具函数，不迁移
    js/http-intercept.js            — 拦截器，不迁移

  需要更新:
    html/login.html                 — 引入 Alpine.js CDN + Alpine.data('loginPage')
    html/register.html              — 引入 Alpine.js CDN + Alpine.data('registerPage')
    html/teacher-*.html             — 全部改为 Alpine 模板语法
    html/data-dashboard.html        — 改为 Alpine 模板语法
    css/teacher.css                 — 补充 .modal-overlay, .modal-content, .auth-submit 等共享样式
```

## 7. 消除的审计问题类别

Alpine.js 迁移后，以下审计问题类别**从根本上不再可能发生**：

| 问题类别 | 审计 ID | Alpine.js 如何消除 |
|----------|---------|-------------------|
| inline onclick 作用域 | C6, H2, H3 | `@click="fn()"` 在 x-data 作用域内解析 |
| DOM ID 不存在 | H4, M7 | 不需要 `getElementById`，`x-show`/`x-for`/`x-text` 绑定到数据 |
| 字段名类型不匹配 | C7, M14, H1 | `x-model.number` / 无 innerHTML 拼接 |
| auth.js 崩溃 | C1 | `x-show` 条件渲染替代无条件 DOM 查询 |
| EventSource 泄漏 | H10 | `$cleanup` 自动清理 |
| innerHTML 模板不完整 | H1 | `x-for` 模板在 HTML 中，可见可验证 |
| CSS 类缺失跨页引用 | H8, M9 | 共享 modal 样式提取到 `teacher.css` |

## 8. 实施顺序

1. **基础设施**：在 `css/teacher.css` 中添加 `.modal-overlay`、`.modal-content`、`.auth-field`、`.auth-submit`、`.btn-cancel` 共享样式
2. **登录/注册页**：最小风险，2 个独立页面，验证 Alpine.js + auth.js 协作模式
3. **teacher-exam.html**：弹窗 + 列表 + 多选，模式最完整，作为模板
4. **其余 teacher 页面**：teacher-class, teacher-manage, teacher-content, teacher-dashboard
5. **data-dashboard.html**：最复杂页面（ECharts + SSE），最后迁移
6. **Plan 文档更新**：将 Phase 5 所有前端 task 重写为 Alpine.js 版本

---

## 9. 自审清单

- [x] 无 TBD/TODO 占位符
- [x] Alpine.js 版本锁定（3.14.9，当前最新稳定版）
- [x] 与现有 vanilla JS 页面的共存策略明确
- [x] 所有 8 个页面的 Alpine.data 名称和核心状态已指定
- [x] 文件路径明确（`js/pages/` 目录）
- [x] CDN 引入方式明确（`defer` 属性，版本号固定）
- [x] 与 `auth.js`/`http-intercept.js` 的依赖关系清晰
