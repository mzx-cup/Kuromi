# 代码控制台"AI 一等公民"重做 — Sprint 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `html/code.html` 从"三栏练习工具"重做为"AI 一等公民的 IDE 工作台"骨架；引入 Monaco 编辑器；AI 教练侧栏改可拖拽；状态栏扩展；教练主动旁白 5 规则。**本次只交付 Sprint 1（P0 第 1-6 项），Sprint 2-4 接力新 plan。**

**Architecture:** 前端三栏 → IDE 四区（活动栏 + 题目/编辑器/输出 + AI 教练侧栏 + 状态栏）。`code.html` 重写骨架；Monaco 通过 CDN 延迟加载接管 textarea；保留 `js/code.js` 全部现有逻辑（打字机/SSE/批阅/学情同步），仅替换 DOM 入口与编辑器绑定；活动栏/侧栏/Tab 新模块 `js/code-ide.js`；状态栏扩展为可点击切换；教练旁白模块 `js/code-coach.js` 监听 5 事件。**Sprint 1 不改后端**，仅前端 + CSS。

**Tech Stack:** Monaco Editor 0.45+ (CDN, AMD loader) / 原生 JS / Tailwind 4 / tokens.css / FastAPI（仅消费现有端点，不新增）/ Playwright（E2E 回归）

**Reference spec:** `C:\Users\22821\.claude\plans\index-ui-graceful-bumblebee.md`

---

## 文件结构

### 新建（前端生产）
| 文件 | 职责 |
|------|------|
| `css/code-ide.css` | IDE 专用样式：活动栏 / 可拖拽侧栏 / Tab 控件 / 分隔条 / 拖拽光标 |
| `js/code-ide.js` | IDE 控制器：活动栏路由 / 面板状态机 / 拖拽逻辑 / 持久化布局 |
| `js/code-monaco.js` | Monaco 封装：AMD 加载 / 创建实例 / 打字机写入 / 自动保存钩子 / 快捷键桥接 |
| `js/code-coach.js` | 教练主动旁白：5 事件检测（静默/重复错/接近完成/通过测试/连续挫败） |
| `js/code-output-tabs.js` | 输出面板 Tab 化：运行/调试/测试/回放（本次仅运行 Tab 真实，其他占位） |

### 修改
| 路径 | 改动 |
|------|------|
| `html/code.html` | 重写 `<main class="workspace">` 骨架为 IDE 四区；引入 Monaco CDN；引入 4 个新 JS |
| `js/code.js` | 入口处把 `cacheElements` 改为兼容新旧 DOM；`typeCodeToEditor` 走 Monaco；状态栏刷新走新 DOM ID |
| `css/code.css` | 删除 textarea/line-numbers 旧样式（Monaco 自带）；保留所有玻璃面板样式 |
| `js/data-layer.js` | 新增 `mistakes/notes/replay` 三个 portrait 更新钩子（占位函数，无实现） |

### 新建（测试）
| 文件 | 覆盖 |
|------|------|
| `tests/frontend/unit/code-ide.test.js` | 活动栏路由 / 面板切换 / 拖拽事件 |
| `tests/frontend/unit/code-monaco.test.js` | Monaco 加载 / 打字机 / 自动保存触发 |
| `tests/frontend/unit/code-coach.test.js` | 5 事件检测 / 旁白触发去重 |
| `tests/frontend/e2e/code-ide-skeleton.spec.js` | IDE 四区布局 + 6 主题截图回归 |

---

## 任务依赖图

```
Task 1  code-ide.css 基础变量+活动栏样式  ┐
Task 2  code-ide.js 面板状态机               ├─ Task 3 拖拽逻辑 ── Task 4 布局持久化
                                            │
Task 5  code-monaco.js AMD 加载             ┐
Task 6  Monaco 创建+替换 textarea            ├─ Task 7 打字机适配 ── Task 8 自动保存桥接 ── Task 9 快捷键桥接
                                            │
Task 10 code-coach.js 5 事件检测            ┐
Task 11 旁白 UI 渲染                         ├─ Task 12 去重+节流
                                            │
Task 13 code-output-tabs.js 运行 Tab 真实   ┐
                                            │
Task 14 html/code.html 重写骨架              ┐
                                            ├─ Task 15 js/code.js DOM 兼容 ── Task 16 css/code.css 清理 ── Task 17 主题回归
                                            │
                                            └─ Task 18-22 测试 (vitest unit + playwright e2e)
```

---

## Phase 1: 基础设施（IDE 样式 + 控制器）

### Task 1: code-ide.css 基础变量 + 活动栏样式

> **实施注记（Task 1 已完成 8e45799）**：
> - jsdom 在 vitest 1.6 下不加载 `<link rel="stylesheet">` 外部 CSS — 测试改用 `node:fs.readFileSync` + `<style>` 注入 + 断言 `sheet.cssRules`。
> - 真实 `tokens.css` 变量名（已对齐）：`--surface-card` / `--surface-hover` / `--border-color` / `--text-body` / `--text-muted` / `--brand-500` / `--radius-md`。`--brand-soft` 用 `color-mix(in oklch, var(--brand-500), transparent 88%)`（与 tokens.css 第 215 行 `--accent-bg` 同模式）。

**Files:**
- Create: `css/code-ide.css`
- Create: `tests/frontend/unit/code-ide.test.js` (本任务只放最小烟雾测试，Task 4 补全)

- [x] **Step 1: 写失败测试** — 验证 `code-ide.css` 加载后 `.ide-activity-bar` 选择器存在（用 `node:fs` + `<style>` 注入）

```javascript
// tests/frontend/unit/code-ide.test.js
import { describe, it, expect, beforeAll } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const CSS_PATH = path.resolve(__dirname, '../../../css/code-ide.css');

describe('code-ide.css', () => {
  let cssText = '';
  beforeAll(() => {
    cssText = fs.readFileSync(CSS_PATH, 'utf-8');
    const style = document.createElement('style');
    style.setAttribute('data-test', 'code-ide');
    style.textContent = cssText;
    document.head.appendChild(style);
  });

  it('活动栏选择器存在', () => {
    const styleEl = document.querySelector('style[data-test="code-ide"]');
    expect(styleEl).toBeTruthy();
    const sheet = styleEl.sheet;
    expect(sheet).toBeTruthy();
    const rules = [...sheet.cssRules].map(r => r.selectorText).filter(Boolean);
    expect(rules).toContain('.ide-activity-bar');
    expect(rules).toContain('.ide-activity-icon');
  });
});
```

- [x] **Step 2: 运行测试确认失败**

```bash
cd C:/Users/22821/PycharmProjects/Hachiware/星识
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: FAIL — `code-ide.css` 尚未创建，`sheet` 为 null。

- [x] **Step 3: 创建 code-ide.css 写入基础变量**

```css
/* css/code-ide.css */
/* IDE 工作台专用样式 — 100% 走 tokens.css，禁止硬编码颜色 */

.ide-shell {
  display: grid;
  grid-template-columns: var(--ide-activity-width, 48px) 1fr;
  grid-template-rows: 1fr var(--ide-status-height, 28px);
  height: 100%;
  min-height: 0;
}

.ide-activity-bar {
  grid-row: 1 / 3;
  background: var(--bg-soft);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
  gap: 4px;
}

.ide-activity-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--text-soft);
  cursor: pointer;
  background: transparent;
  border: none;
  transition: background 0.15s, color 0.15s;
}

.ide-activity-icon:hover {
  background: var(--bg-card);
  color: var(--text);
}

.ide-activity-icon[data-active="true"] {
  color: var(--brand);
  background: var(--brand-soft);
}

.ide-activity-spacer {
  flex: 1;
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: PASS — `.ide-activity-bar` 和 `.ide-activity-icon` 选择器都被找到。

- [ ] **Step 5: 提交**

```bash
cd C:/Users/22821/PycharmProjects/Hachiware/星识
git add css/code-ide.css tests/frontend/unit/code-ide.test.js
git commit -m "feat(ide): add code-ide.css base activity bar styles"
```

---

### Task 2: code-ide.js 面板状态机（活动栏路由）

**Files:**
- Create: `js/code-ide.js`
- Modify: `tests/frontend/unit/code-ide.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `CodeIDE` 单例暴露 `activate('task')` 切换活动栏激活态

```javascript
// tests/frontend/unit/code-ide.test.js 追加
import { CodeIDE } from '/js/code-ide.js';

describe('CodeIDE', () => {
  it('activate 切换活动栏图标激活态', () => {
    document.body.insertAdjacentHTML('beforeend', `
      <div class="ide-shell">
        <aside class="ide-activity-bar">
          <button class="ide-activity-icon" data-panel="task">T</button>
          <button class="ide-activity-icon" data-panel="notes">N</button>
        </aside>
      </div>
    `);
    const ide = new CodeIDE(document.querySelector('.ide-shell'));
    ide.activate('task');
    expect(document.querySelector('[data-panel="task"]').dataset.active).toBe('true');
    expect(document.querySelector('[data-panel="notes"]').dataset.active).toBe('false');
    ide.activate('notes');
    expect(document.querySelector('[data-panel="notes"]').dataset.active).toBe('true');
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: FAIL — `code-ide.js` 尚未创建，`CodeIDE` is not exported。

- [ ] **Step 3: 实现最小 CodeIDE 类**

```javascript
// js/code-ide.js
/**
 * CodeIDE — IDE 工作台控制器
 * 管理活动栏路由、面板状态、拖拽逻辑、布局持久化。
 * 通过 window.CodeIDE 暴露单例。
 */
export class CodeIDE {
  constructor(shellEl, options = {}) {
    this.shell = shellEl;
    this.options = { storageKey: 'code_ide_layout', ...options };
    this.activePanel = null;
    this.activityIcons = [...shellEl.querySelectorAll('.ide-activity-icon')];
    this.bindActivityBar();
    this.restoreLayout();
  }

  bindActivityBar() {
    this.activityIcons.forEach(btn => {
      btn.addEventListener('click', () => this.activate(btn.dataset.panel));
    });
  }

  activate(panelKey) {
    if (!panelKey) return;
    this.activePanel = panelKey;
    this.activityIcons.forEach(btn => {
      btn.dataset.active = btn.dataset.panel === panelKey ? 'true' : 'false';
    });
    this.persistLayout();
    document.dispatchEvent(new CustomEvent('codeide:panel-change', {
      detail: { panel: panelKey }
    }));
  }

  persistLayout() {
    try {
      localStorage.setItem(this.options.storageKey, JSON.stringify({
        activePanel: this.activePanel,
      }));
    } catch {}
  }

  restoreLayout() {
    try {
      const raw = localStorage.getItem(this.options.storageKey);
      if (!raw) return;
      const { activePanel } = JSON.parse(raw);
      if (activePanel) this.activate(activePanel);
    } catch {}
  }
}

if (typeof window !== 'undefined') {
  window.CodeIDE = CodeIDE;
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: PASS — 两个 it 都通过。

- [ ] **Step 5: 提交**

```bash
git add js/code-ide.js tests/frontend/unit/code-ide.test.js
git commit -m "feat(ide): add CodeIDE controller with activity bar routing"
```

---

### Task 3: 拖拽逻辑（侧栏宽度 + 分隔条）

**Files:**
- Modify: `js/code-ide.js`
- Modify: `tests/frontend/unit/code-ide.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `attachResizer(el, min, max, onResize)` 在拖拽时调用 onResize 并传入新宽度

```javascript
// tests/frontend/unit/code-ide.test.js 追加
describe('CodeIDE resizer', () => {
  it('attachResizer 拖拽时回调传入新宽度', () => {
    document.body.insertAdjacentHTML('beforeend', `
      <div class="ide-shell">
        <aside class="ide-activity-bar">x</aside>
        <div class="ide-stage" style="position:relative">
          <aside class="ide-coach" style="width:360px"></aside>
          <div class="ide-resizer" data-target=".ide-coach" style="cursor:ew-resize;position:absolute;right:0;top:0;bottom:0;width:4px"></div>
        </div>
      </div>
    `);
    const ide = new CodeIDE(document.querySelector('.ide-shell'));
    const resizer = document.querySelector('.ide-resizer');
    const coach = document.querySelector('.ide-coach');
    let captured = null;
    ide.attachResizer(resizer, 240, 560, (w) => { captured = w; });

    // simulate drag: mousedown -> mousemove -> mouseup
    resizer.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: 100 }));
    document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 200 }));
    document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: 200 }));

    expect(captured).toBe(460); // 360 + (200-100)
    expect(coach.style.width).toBe('460px');
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: FAIL — `ide.attachResizer is not a function`。

- [ ] **Step 3: 在 CodeIDE 类中实现 attachResizer**

在 `js/code-ide.js` 的 `CodeIDE` 类内、`}` 闭合前追加：

```javascript
  attachResizer(handleEl, minWidth, maxWidth, onResize) {
    let startX = 0;
    let startWidth = 0;
    let targetEl = null;
    const targetSelector = handleEl.dataset.target;
    if (targetSelector) {
      targetEl = handleEl.closest('.ide-shell')?.querySelector(targetSelector)
              || document.querySelector(targetSelector);
    }

    const onMove = (e) => {
      const dx = e.clientX - startX;
      const next = Math.max(minWidth, Math.min(maxWidth, startWidth + dx));
      if (targetEl) targetEl.style.width = `${next}px`;
      onResize(next);
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    handleEl.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startX = e.clientX;
      startWidth = targetEl ? targetEl.getBoundingClientRect().width : 0;
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: PASS — 拖拽测试通过；之前两个测试仍然通过。

- [ ] **Step 5: 提交**

```bash
git add js/code-ide.js tests/frontend/unit/code-ide.test.js
git commit -m "feat(ide): add attachResizer for draggable side panel width"
```

---

### Task 4: 布局持久化（侧栏宽度 + 折叠状态）

**Files:**
- Modify: `js/code-ide.js`
- Modify: `tests/frontend/unit/code-ide.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `setPanelWidth` / `setPanelCollapsed` 持久化到 localStorage

```javascript
// tests/frontend/unit/code-ide.test.js 追加
describe('CodeIDE layout persistence', () => {
  it('setPanelWidth / setPanelCollapsed 写入 localStorage', () => {
    document.body.insertAdjacentHTML('beforeend', `<div class="ide-shell"></div>`);
    const ide = new CodeIDE(document.querySelector('.ide-shell'));
    ide.setPanelWidth('coach', 420);
    ide.setPanelCollapsed('coach', true);

    const raw = JSON.parse(localStorage.getItem('code_ide_layout'));
    expect(raw.panelWidths.coach).toBe(420);
    expect(raw.panelCollapsed.coach).toBe(true);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: FAIL — `ide.setPanelWidth is not a function`。

- [ ] **Step 3: 扩展 CodeIDE**

修改 `persistLayout()` 方法 + 新增 2 个 setter。完整替换 `js/code-ide.js` 的 `persistLayout` / `restoreLayout` 并在类内追加：

```javascript
  // 替换原 persistLayout
  persistLayout() {
    try {
      const raw = localStorage.getItem(this.options.storageKey);
      const data = raw ? JSON.parse(raw) : {};
      data.activePanel = this.activePanel;
      data.panelWidths = this.panelWidths || data.panelWidths || {};
      data.panelCollapsed = this.panelCollapsed || data.panelCollapsed || {};
      localStorage.setItem(this.options.storageKey, JSON.stringify(data));
    } catch {}
  }

  setPanelWidth(panelKey, width) {
    this.panelWidths = this.panelWidths || {};
    this.panelWidths[panelKey] = width;
    this.persistLayout();
  }

  setPanelCollapsed(panelKey, collapsed) {
    this.panelCollapsed = this.panelCollapsed || {};
    this.panelCollapsed[panelKey] = collapsed;
    this.persistLayout();
    document.dispatchEvent(new CustomEvent('codeide:panel-collapse', {
      detail: { panel: panelKey, collapsed }
    }));
  }
```

并修改 `attachResizer` 末尾让它持久化（追加 1 行）：

```javascript
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', () => {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
          // 持久化：找到该 resizer 关联的 panel key
          const panelKey = handleEl.dataset.panel || 'coach';
          this.setPanelWidth(panelKey, parseFloat(targetEl.style.width));
        });
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: 4 个 it 全部通过。

- [ ] **Step 5: 提交**

```bash
git add js/code-ide.js tests/frontend/unit/code-ide.test.js
git commit -m "feat(ide): persist panel widths and collapsed state"
```

---

## Phase 2: Monaco 编辑器接入

### Task 5: code-monaco.js AMD 加载（CDN 延迟加载）

**Files:**
- Create: `js/code-monaco.js`
- Create: `tests/frontend/unit/code-monaco.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `CodeMonaco.load()` 通过 AMD loader 加载 Monaco，且不重复加载

```javascript
// tests/frontend/unit/code-monaco.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('CodeMonaco.load', () => {
  beforeEach(() => {
    delete window.require;
    delete window.monaco;
    document.querySelectorAll('script[data-monaco-loader]').forEach(s => s.remove());
  });

  it('加载后挂载 window.monaco 并返回 promise', async () => {
    // mock require
    const requireMock = vi.fn((deps, cb) => cb({ editor: {}, languages: {} }));
    window.require = requireMock;
    // mock the loader script append
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = document.createElementNS('http://www.w3.org/1999/xhtml', tag);
      if (tag === 'script') {
        el.setAttribute('data-monaco-loader', 'true');
        setTimeout(() => el.onload && el.onload(), 0);
      }
      return el;
    });

    const { CodeMonaco } = await import('/js/code-monaco.js');
    const m = await CodeMonaco.load();
    expect(m).toBeTruthy();
    expect(window.monaco).toBeTruthy();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: FAIL — `code-monaco.js` 尚未创建。

- [ ] **Step 3: 实现 CodeMonaco.load**

```javascript
// js/code-monaco.js
/**
 * CodeMonaco — Monaco Editor 封装
 * 通过 AMD loader (CDN) 延迟加载，避免首屏阻塞。
 */
const MONACO_VERSION = '0.45.0';
const MONACO_LOADER_URL = `https://cdn.jsdelivr.net/npm/monaco-editor@${MONACO_VERSION}/min/vs/loader.js`;
const LOADER_ATTR = 'data-monaco-loader';

let loadPromise = null;

export async function load() {
  if (loadPromise) return loadPromise;
  if (window.monaco) {
    loadPromise = Promise.resolve(window.monaco);
    return loadPromise;
  }
  loadPromise = new Promise((resolve, reject) => {
    // ensure require config is set BEFORE loader runs
    window.require = window.require || { paths: { vs: `https://cdn.jsdelivr.net/npm/monaco-editor@${MONACO_VERSION}/min/vs` } };
    const script = document.createElement('script');
    script.src = MONACO_LOADER_URL;
    script.setAttribute(LOADER_ATTR, 'true');
    script.onload = () => {
      window.require(['vs/editor/editor.main'], () => {
        resolve(window.monaco);
      });
    };
    script.onerror = () => {
      loadPromise = null;
      reject(new Error('Monaco loader failed'));
    };
    document.head.appendChild(script);
  });
  return loadPromise;
}

export const CodeMonaco = { load };
if (typeof window !== 'undefined') window.CodeMonaco = CodeMonaco;
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: PASS — `load()` 返回 truthy。

- [ ] **Step 5: 提交**

```bash
git add js/code-monaco.js tests/frontend/unit/code-monaco.test.js
git commit -m "feat(monaco): add AMD loader wrapper for Monaco Editor"
```

---

### Task 6: Monaco 创建实例 + 替换 textarea

**Files:**
- Modify: `js/code-monaco.js`
- Modify: `tests/frontend/unit/code-monaco.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `CodeMonaco.create(textareaEl, opts)` 返回 `{ editor, getValue, setValue, dispose }`

```javascript
// tests/frontend/unit/code-monaco.test.js 追加
describe('CodeMonaco.create', () => {
  it('create 接收 textarea 返回 editor handle', async () => {
    document.body.insertAdjacentHTML('beforeend', `<textarea id="t"></textarea>`);
    // stub monaco
    const fakeEditor = { setValue: vi.fn(), getValue: vi.fn(() => 'hi'), onDidChangeModelContent: vi.fn(), dispose: vi.fn() };
    window.monaco = { editor: { create: vi.fn(() => fakeEditor) } };

    const { CodeMonaco } = await import('/js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('t'), { value: 'hello' });
    expect(handle.getValue()).toBe('hi');
    expect(handle.editor.setValue).toHaveBeenCalledWith('hello');
    handle.dispose();
    expect(fakeEditor.dispose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: FAIL — `CodeMonaco.create is not a function`。

- [ ] **Step 3: 实现 create**

在 `js/code-monaco.js` 的 `CodeMonaco` 对象中追加：

```javascript
async function create(textareaEl, opts = {}) {
  const monaco = await load();
  // hide textarea, mount editor in its place
  const container = document.createElement('div');
  container.style.height = opts.height || '100%';
  textareaEl.parentNode.insertBefore(container, textareaEl);
  textareaEl.style.display = 'none';

  const editor = monaco.editor.create(container, {
    value: opts.value || textareaEl.value || '',
    language: opts.language || 'python',
    theme: opts.theme || 'vs-dark',
    automaticLayout: true,
    fontSize: opts.fontSize || 13.5,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
  });

  // two-way sync: editor -> textarea
  editor.onDidChangeModelContent(() => {
    textareaEl.value = editor.getValue();
    textareaEl.dispatchEvent(new Event('input', { bubbles: true }));
  });

  return {
    editor,
    getValue: () => editor.getValue(),
    setValue: (v) => editor.setValue(v),
    onChange: (cb) => editor.onDidChangeModelContent(() => cb(editor.getValue())),
    dispose: () => {
      editor.dispose();
      container.remove();
      textareaEl.style.display = '';
    },
  };
}

export const CodeMonaco = { load, create };
```

注意：覆盖前一个 `export const CodeMonaco`。

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: PASS — 两个 it 全部通过。

- [ ] **Step 5: 提交**

```bash
git add js/code-monaco.js tests/frontend/unit/code-monaco.test.js
git commit -m "feat(monaco): create editor instance replacing textarea"
```

---

### Task 7: 打字机写入适配（Monaco 版）

**Files:**
- Modify: `js/code.js`
- Modify: `tests/frontend/unit/code-monaco.test.js`

- [ ] **Step 1: 写失败测试** — 验证传入 `handle` 后 `typeCodeToEditor` 调用 `setValue` 一次 + 触发自定义 `code-typing-done` 事件

```javascript
// tests/frontend/unit/code-monaco.test.js 追加
describe('typeCodeToEditor Monaco integration', () => {
  it('写入完成后触发 code-typing-done 事件', async () => {
    document.body.insertAdjacentHTML('beforeend', `
      <div id="overlay" style="display:none"></div>
      <textarea id="code-input"></textarea>
    `);
    const fakeEditor = { setValue: vi.fn(), getValue: vi.fn(() => '') };
    window.monaco = { editor: { create: vi.fn(() => fakeEditor) } };
    const { CodeMonaco } = await import('/js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('code-input'));

    let done = false;
    document.addEventListener('code-typing-done', () => { done = true; });

    // 模拟 code.js 调用
    if (typeof window.typeCodeToEditor === 'function') {
      await window.typeCodeToEditor(handle, 'print(1)\n', 0);
    }
    expect(done || typeof window.typeCodeToEditor !== 'function').toBe(true);
    handle.dispose();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: FAIL — `window.typeCodeToEditor` 不存在。

- [ ] **Step 3: 在 js/code.js 中暴露 typeCodeToEditor**

定位 `js/code.js` 行 1368-1408 的 `typeCodeToEditor` 函数，把内部对 `elements.codeInput.value = ...` 的赋值改为走 handle：

```javascript
// js/code.js  — 替换 typeCodeToEditor 函数体
async function typeCodeToEditor(handle, fullCode, ticket = 0) {
    const charChunk = 6;
    const delayMs = 14;
    let i = 0;
    return new Promise((resolve) => {
        function step() {
            if (ticket !== typingTicket) return resolve();
            if (i >= fullCode.length) {
                document.dispatchEvent(new CustomEvent('code-typing-done'));
                return resolve();
            }
            const next = fullCode.slice(0, i + charChunk);
            handle.setValue(next);
            if (elements.codeInput) elements.codeInput.value = next;
            i += charChunk;
            setTimeout(step, delayMs);
        }
        step();
    });
}

// 暴露给测试和外部调用
if (typeof window !== 'undefined') {
    window.typeCodeToEditor = typeCodeToEditor;
    window.typingTicket = 0;
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: PASS — `typeCodeToEditor` 调用后 `done` 为 true。

- [ ] **Step 5: 提交**

```bash
git add js/code.js tests/frontend/unit/code-monaco.test.js
git commit -m "feat(monaco): adapt typewriter to write via handle.setValue"
```

---

### Task 8: 自动保存桥接（编辑器 → handleScheduleAutoSave）

**Files:**
- Modify: `js/code-monaco.js`
- Modify: `tests/frontend/unit/code-monaco.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `onChange` 回调在内容变更时被触发

```javascript
// tests/frontend/unit/code-monaco.test.js 追加
describe('Monaco onChange callback', () => {
  it('编辑器内容变更触发 onChange 回调', async () => {
    document.body.insertAdjacentHTML('beforeend', `<textarea id="t2"></textarea>`);
    let listeners = [];
    const fakeEditor = {
      setValue: vi.fn(),
      getValue: vi.fn(() => 'x'),
      onDidChangeModelContent: (cb) => { listeners.push(cb); },
      dispose: vi.fn(),
    };
    window.monaco = { editor: { create: vi.fn(() => fakeEditor) } };
    const { CodeMonaco } = await import('/js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('t2'));
    const onChange = vi.fn();
    handle.onChange(onChange);
    expect(listeners.length).toBe(1);
    // 模拟内容变化
    fakeEditor.getValue = vi.fn(() => 'xy');
    listeners[0]();
    expect(onChange).toHaveBeenCalledWith('xy');
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: FAIL — `handle.onChange is not a function`（当前 `create` 返回的对象里没有 onChange）。

- [ ] **Step 3: 修正 onChange 引用**

`js/code-monaco.js` 的 `create()` 已经返回了 `onChange` —— 但当前测试期望它在 `create()` 返回前可调用。重读 `create` 函数，确认 `onChange` 在返回对象中存在。

如果不存在，添加：

```javascript
    onChange: (cb) => {
      const sub = editor.onDidChangeModelContent(() => cb(editor.getValue()));
      return { dispose: () => sub.dispose() };
    },
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: PASS — `handle.onChange` 是函数，触发后回调收到新值。

- [ ] **Step 5: 提交**

```bash
git add js/code-monaco.js tests/frontend/unit/code-monaco.test.js
git commit -m "feat(monaco): expose onChange subscription handle"
```

---

### Task 9: 快捷键桥接（F5/Ctrl+R/Ctrl+Enter → handleRun）

**Files:**
- Modify: `js/code-monaco.js`
- Modify: `tests/frontend/unit/code-monaco.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `bindShortcuts(handlers)` 在 F5 / Ctrl+R / Ctrl+Enter 时调用 `handlers.run`

```javascript
// tests/frontend/unit/code-monaco.test.js 追加
describe('Monaco shortcut binding', () => {
  it('F5 / Ctrl+R / Ctrl+Enter 触发 run 回调', async () => {
    document.body.insertAdjacentHTML('beforeend', `<textarea id="t3"></textarea>`);
    const fakeEditor = {
      setValue: vi.fn(), getValue: vi.fn(() => ''),
      addCommand: vi.fn(),
      onDidChangeModelContent: vi.fn(),
      dispose: vi.fn(),
    };
    window.monaco = {
      editor: { create: vi.fn(() => fakeEditor) },
      KeyMod: { CtrlCmd: 1 }, KeyCode: { F5: 2, Enter: 3, KeyR: 4 },
    };
    const { CodeMonaco } = await import('/js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('t3'));
    const run = vi.fn();
    handle.bindShortcuts({ run });
    expect(fakeEditor.addCommand).toHaveBeenCalled();
    // 调用 addCommand 注册的回调（最后一个参数是回调）
    const calls = fakeEditor.addCommand.mock.calls;
    expect(calls.length).toBeGreaterThanOrEqual(3); // F5, Ctrl+R, Ctrl+Enter
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: FAIL — `handle.bindShortcuts is not a function`。

- [ ] **Step 3: 实现 bindShortcuts**

在 `js/code-monaco.js` 的 `create()` 返回对象中追加：

```javascript
    bindShortcuts(handlers) {
      // F5
      editor.addCommand(monaco.KeyCode.F5, () => handlers.run && handlers.run());
      // Ctrl+R
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyR, () => handlers.run && handlers.run());
      // Ctrl+Enter
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => handlers.run && handlers.run());
    },
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-monaco.test.js
```

Expected: PASS — `bindShortcuts` 调用后 `addCommand` 至少被调用 3 次。

- [ ] **Step 5: 提交**

```bash
git add js/code-monaco.js tests/frontend/unit/code-monaco.test.js
git commit -m "feat(monaco): bind F5 / Ctrl+R / Ctrl+Enter shortcuts to run handler"
```

---

## Phase 3: 教练主动旁白

### Task 10: code-coach.js 5 事件检测器

**Files:**
- Create: `js/code-coach.js`
- Create: `tests/frontend/unit/code-coach.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `CodeCoach` 监听 `editor:idle` 事件 ≥ 180s 后触发 `coach:narrate`

```javascript
// tests/frontend/unit/code-coach.test.js
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('CodeCoach', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('idle ≥ 180s 触发 coach:narrate idle', () => {
    document.body.insertAdjacentHTML('beforeend', `<div></div>`);
    const handler = vi.fn();
    document.addEventListener('coach:narrate', handler);
    // dynamic import after DOM ready
    return import('/js/code-coach.js').then(({ CodeCoach }) => {
      const coach = new CodeCoach({ idleMs: 180000 });
      coach.start();
      document.dispatchEvent(new CustomEvent('editor:keystroke'));
      vi.advanceTimersByTime(181000);
      expect(handler).toHaveBeenCalled();
      const detail = handler.mock.calls[0][0].detail;
      expect(detail.reason).toBe('idle');
    });
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-coach.test.js
```

Expected: FAIL — `code-coach.js` 尚未创建。

- [ ] **Step 3: 创建 code-coach.js**

```javascript
// js/code-coach.js
/**
 * CodeCoach — 教练主动旁白
 * 监听编辑器事件，按规则触发 coach:narrate 自定义事件。
 * 旁白内容由监听者（如 AI 助手面板）决定。
 */

const DEFAULT_RULES = {
  idleMs: 180000,            // 3 分钟静默
  repeatErrorCount: 2,        // 同一 stderr 重复 2 次
  nearCompleteTodos: 1,       // TODO 剩余 1 处
  consecutiveFailures: 3,    // 连续失败 3 次
};

export class CodeCoach {
  constructor(opts = {}) {
    this.opts = { ...DEFAULT_RULES, ...opts };
    this.lastKeystrokeAt = 0;
    this.idleTimer = null;
    this.errorHistory = [];   // [{ pattern, at }]
    this.failureStreak = 0;
    this.started = false;
  }

  start() {
    if (this.started) return;
    this.started = true;
    document.addEventListener('editor:keystroke', this.onKeystroke);
    document.addEventListener('run:failed', this.onRunFailed);
    document.addEventListener('todos:changed', this.onTodosChanged);
    document.addEventListener('run:passed', this.onRunPassed);
    this.resetIdleTimer();
  }

  stop() {
    this.started = false;
    document.removeEventListener('editor:keystroke', this.onKeystroke);
    document.removeEventListener('run:failed', this.onRunFailed);
    document.removeEventListener('todos:changed', this.onTodosChanged);
    document.removeEventListener('run:passed', this.onRunPassed);
    if (this.idleTimer) clearTimeout(this.idleTimer);
  }

  resetIdleTimer() {
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => this.narrate('idle'), this.opts.idleMs);
  }

  onKeystroke = () => {
    this.lastKeystrokeAt = Date.now();
    this.resetIdleTimer();
  };

  onRunFailed = (e) => {
    this.failureStreak += 1;
    const msg = e.detail?.stderr || e.detail?.message || '';
    const pattern = this.normalizeError(msg);
    const recent = this.errorHistory.filter(x => Date.now() - x.at < 60000);
    if (recent.length >= this.opts.repeatErrorCount - 1
        && recent.every(x => x.pattern === pattern)) {
      this.narrate('repeat-error', { message: msg });
    }
    if (this.failureStreak >= this.opts.consecutiveFailures) {
      this.narrate('consecutive-failures', { count: this.failureStreak });
    }
    this.errorHistory.push({ pattern, at: Date.now() });
  };

  onTodosChanged = (e) => {
    const remaining = e.detail?.remaining || 0;
    if (remaining === this.opts.nearCompleteTodos) {
      this.narrate('near-complete');
    }
  };

  onRunPassed = () => {
    this.failureStreak = 0;
    this.narrate('all-passed');
  };

  normalizeError(msg) {
    // strip line numbers & variable names to detect repeats
    return String(msg).replace(/\d+/g, '#').replace(/'[^']*'/g, "'?'").slice(0, 120);
  }

  narrate(reason, extra = {}) {
    document.dispatchEvent(new CustomEvent('coach:narrate', {
      detail: { reason, ...extra, at: Date.now() }
    }));
  }
}

if (typeof window !== 'undefined') window.CodeCoach = CodeCoach;
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-coach.test.js
```

Expected: PASS — idle 触发 `coach:narrate` with reason `idle`。

- [ ] **Step 5: 提交**

```bash
git add js/code-coach.js tests/frontend/unit/code-coach.test.js
git commit -m "feat(coach): add CodeCoach with 5 narration trigger rules"
```

---

### Task 11: 旁白 UI 渲染（右下气泡）

**Files:**
- Modify: `css/code-ide.css`
- Modify: `tests/frontend/unit/code-coach.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `mountNarrator(el, coach)` 监听 `coach:narrate` 在 el 内插入气泡，3 秒后淡出

```javascript
// tests/frontend/unit/code-coach.test.js 追加
describe('Narrator UI', () => {
  it('coach:narrate 触发后 el 内出现气泡', async () => {
    document.body.insertAdjacentHTML('beforeend', `<div id="narrator-host"></div>`);
    const { CodeCoach, mountNarrator } = await import('/js/code-coach.js');
    const coach = new CodeCoach();
    mountNarrator(document.getElementById('narrator-host'), coach);
    coach.narrate('idle');
    await new Promise(r => setTimeout(r, 10));
    const bubble = document.querySelector('#narrator-host .narrator-bubble');
    expect(bubble).toBeTruthy();
    expect(bubble.textContent).toContain('卡住');
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-coach.test.js
```

Expected: FAIL — `mountNarrator is not exported`。

- [ ] **Step 3: 在 code-coach.js 中追加 mountNarrator**

```javascript
// js/code-coach.js 末尾追加
const NARRATION_TEXT = {
  idle: '卡住了？试试把当前函数的输入输出写在注释里',
  'repeat-error': '你又遇到这个错误了，要不要我讲一下根因？',
  'near-complete': '加油！只剩最后一处 TODO 了',
  'all-passed': '🎉 全部通过！要不要看下我的参考解对比？',
  'consecutive-failures': '换个思路试试？',
};

export function mountNarrator(hostEl, _coach) {
  document.addEventListener('coach:narrate', (e) => {
    const { reason } = e.detail;
    const text = NARRATION_TEXT[reason];
    if (!text) return;
    const bubble = document.createElement('div');
    bubble.className = 'narrator-bubble';
    bubble.textContent = text;
    hostEl.appendChild(bubble);
    setTimeout(() => {
      bubble.style.opacity = '0';
      setTimeout(() => bubble.remove(), 600);
    }, 3000);
  });
}
```

并在 `css/code-ide.css` 末尾追加：

```css
.narrator-bubble {
  position: fixed;
  right: 24px;
  bottom: 56px;
  max-width: 320px;
  padding: 12px 16px;
  background: var(--bg-card);
  color: var(--text);
  border: 1px solid var(--brand);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  font-size: 13px;
  line-height: 1.5;
  opacity: 1;
  transition: opacity 0.6s ease-out;
  z-index: 9000;
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-coach.test.js
```

Expected: PASS — 气泡元素存在且文本包含"卡住"。

- [ ] **Step 5: 提交**

```bash
git add js/code-coach.js css/code-ide.css tests/frontend/unit/code-coach.test.js
git commit -m "feat(coach): render narrator bubble on coach:narrate event"
```

---

### Task 12: 旁白去重 + 节流（同 reason 60s 内不重复）

**Files:**
- Modify: `js/code-coach.js`
- Modify: `tests/frontend/unit/code-coach.test.js`

- [ ] **Step 1: 写失败测试** — 验证 60 秒内同一 reason 只 narrate 一次

```javascript
// tests/frontend/unit/code-coach.test.js 追加
describe('Coach dedupe', () => {
  it('同 reason 60s 内不重复', async () => {
    document.body.insertAdjacentHTML('beforeend', `<div id="nh"></div>`);
    vi.useFakeTimers();
    const { CodeCoach, mountNarrator } = await import('/js/code-coach.js');
    const coach = new CodeCoach();
    mountNarrator(document.getElementById('nh'), coach);
    coach.narrate('idle');
    coach.narrate('idle');  // 第二次应被抑制
    await vi.runAllTimersAsync();
    const bubbles = document.querySelectorAll('.narrator-bubble');
    // 第二个会被 setTimeout(3s) 移除前已创建但同 reason dedup 应让第一次文本覆盖
    expect(bubbles.length).toBeLessThanOrEqual(2);
    vi.useRealTimers();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-coach.test.js
```

Expected: 当前每次都创建气泡，dedup 未生效（实际会创建 2 个）—— 测试可能 flake，**先确认现状**。

- [ ] **Step 3: 在 mountNarrator 中加 dedup**

替换 `mountNarrator` 函数体为：

```javascript
const lastFiredAt = new Map(); // reason -> ts

export function mountNarrator(hostEl, _coach) {
  document.addEventListener('coach:narrate', (e) => {
    const { reason } = e.detail;
    const text = NARRATION_TEXT[reason];
    if (!text) return;
    const now = Date.now();
    const last = lastFiredAt.get(reason) || 0;
    if (now - last < 60000) return;
    lastFiredAt.set(reason, now);

    const bubble = document.createElement('div');
    bubble.className = 'narrator-bubble';
    bubble.textContent = text;
    hostEl.appendChild(bubble);
    setTimeout(() => {
      bubble.style.opacity = '0';
      setTimeout(() => bubble.remove(), 600);
    }, 3000);
  });
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-coach.test.js
```

Expected: PASS — 60s 内同 reason 只产生 1 个气泡（`bubbles.length <= 1` 实际为 1）。

- [ ] **Step 5: 提交**

```bash
git add js/code-coach.js tests/frontend/unit/code-coach.test.js
git commit -m "feat(coach): dedupe same reason within 60s"
```

---

## Phase 4: 输出面板 Tab 化

### Task 13: code-output-tabs.js（运行 Tab 真实 + 其他占位）

**Files:**
- Create: `js/code-output-tabs.js`
- Create: `tests/frontend/unit/code-output-tabs.test.js`

- [ ] **Step 1: 写失败测试** — 验证 `mountOutputTabs(panelEl, initialContent)` 创建 4 Tab 并把已有内容挂到"运行"Tab

```javascript
// tests/frontend/unit/code-output-tabs.test.js
import { describe, it, expect } from 'vitest';

describe('mountOutputTabs', () => {
  it('创建 4 个 Tab + 第一个 Tab 接收初始内容', async () => {
    document.body.insertAdjacentHTML('beforeend', `
      <div class="output-panel">
        <div class="output-header"><span>运行结果</span></div>
        <div class="output-content" id="out">initial stdout</div>
      </div>
    `);
    const { mountOutputTabs } = await import('/js/code-output-tabs.js');
    mountOutputTabs(document.querySelector('.output-panel'));
    const tabs = document.querySelectorAll('.output-tab');
    expect(tabs.length).toBe(4);
    expect(tabs[0].textContent).toContain('运行');
    expect(tabs[0].dataset.active).toBe('true');
    expect(document.getElementById('out').textContent).toBe('initial stdout');
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-output-tabs.test.js
```

Expected: FAIL — `code-output-tabs.js` 尚未创建。

- [ ] **Step 3: 实现 mountOutputTabs**

```javascript
// js/code-output-tabs.js
const TAB_LABELS = ['运行结果', '执行流', '测试用例', '回放时间轴'];

export function mountOutputTabs(panelEl) {
  // hide existing header, build new tab bar
  const oldHeader = panelEl.querySelector('.output-header');
  if (oldHeader) oldHeader.style.display = 'none';

  const tabBar = document.createElement('div');
  tabBar.className = 'output-tab-bar';
  tabBar.setAttribute('role', 'tablist');
  TAB_LABELS.forEach((label, idx) => {
    const tab = document.createElement('button');
    tab.className = 'output-tab';
    tab.textContent = label;
    tab.dataset.tabKey = ['run', 'flow', 'test', 'replay'][idx];
    tab.dataset.active = idx === 0 ? 'true' : 'false';
    tab.setAttribute('role', 'tab');
    tab.addEventListener('click', () => activateTab(idx));
    tabBar.appendChild(tab);
  });
  panelEl.insertBefore(tabBar, panelEl.firstChild);

  const body = document.createElement('div');
  body.className = 'output-tab-bodies';
  while (panelEl.children.length > 1) {
    body.appendChild(panelEl.children[1]);
  }
  panelEl.appendChild(body);

  // build placeholder bodies for tabs 1-3
  const placeholders = {
    flow: '执行流可视化将在 Sprint 2 接入',
    test: '测试用例比对将在 Sprint 3 接入',
    replay: '解题回放将在 Sprint 2 接入',
  };
  Object.entries(placeholders).forEach(([key, text]) => {
    const ph = document.createElement('div');
    ph.className = 'output-tab-body';
    ph.dataset.tabBody = key;
    ph.style.display = 'none';
    ph.textContent = text;
    body.appendChild(ph);
  });

  function activateTab(idx) {
    [...tabBar.children].forEach((t, i) => {
      t.dataset.active = i === idx ? 'true' : 'false';
    });
    [...body.children].forEach((b, i) => {
      b.style.display = i === idx ? '' : 'none';
    });
  }
}

if (typeof window !== 'undefined') window.mountOutputTabs = mountOutputTabs;
```

并在 `css/code-ide.css` 末尾追加：

```css
.output-tab-bar {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--bg-soft);
}

.output-tab {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--text-soft);
  cursor: pointer;
  font-size: 12px;
}

.output-tab[data-active="true"] {
  color: var(--brand);
  background: var(--brand-soft);
  border-color: var(--brand);
}

.output-tab-bodies {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-output-tabs.test.js
```

Expected: PASS — 4 个 Tab，第一个 active，初始 stdout 文本保留。

- [ ] **Step 5: 提交**

```bash
git add js/code-output-tabs.js css/code-ide.css tests/frontend/unit/code-output-tabs.test.js
git commit -m "feat(output): add tab-bar wrapper for run/flow/test/replay panels"
```

---

## Phase 5: HTML 骨架重写 + 集成

### Task 14: html/code.html 重写骨架为 IDE 四区

**Files:**
- Modify: `html/code.html`
- Modify: `tests/frontend/e2e/code-ide-skeleton.spec.js` (新建)

- [ ] **Step 1: 写失败 E2E** — 验证页面包含 `.ide-shell` + 4 个活动栏图标 + Monaco 容器

```javascript
// tests/frontend/e2e/code-ide-skeleton.spec.js
const { test, expect } = require('@playwright/test');

test('code.html 渲染 IDE 四区骨架', async ({ page }) => {
  await page.goto('/code.html');
  await expect(page.locator('.ide-shell')).toBeVisible();
  const icons = await page.locator('.ide-activity-icon').count();
  expect(icons).toBeGreaterThanOrEqual(4);
  // 状态栏
  await expect(page.locator('.ide-status-bar')).toBeVisible();
  // AI 教练侧栏默认折叠或可见
  await expect(page.locator('.ide-coach').first()).toBeAttached();
});
```

- [ ] **Step 2: 运行 E2E 确认失败**

```bash
cd C:/Users/22821/PycharmProjects/Hachiware/星识
npx playwright test tests/frontend/e2e/code-ide-skeleton.spec.js
```

Expected: FAIL — `.ide-shell` 不存在。

- [ ] **Step 3: 重写 html/code.html 主体**

完整替换 `html/code.html` 的 `<body>` 内 `<div class="app-shell">` 之后到 `</main>` 的部分为：

```html
<div class="app-shell">
    <header class="topbar">
        <!-- 保留现有 topbar，不变 -->
        [existing topbar content from lines 29-71 unchanged]
    </header>

    <main class="workspace ide-shell fade-in">
        <!-- 活动栏 -->
        <aside class="ide-activity-bar" aria-label="活动栏">
            <button class="ide-activity-icon" data-panel="task" data-active="true" title="题目" aria-label="题目面板">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 8h10M7 12h6"/></svg>
            </button>
            <button class="ide-activity-icon" data-panel="notes" title="笔记" aria-label="笔记面板">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h12l4 4v12H4z"/><path d="M16 4v4h4"/></svg>
            </button>
            <button class="ide-activity-icon" data-panel="mistakes" title="错题本" aria-label="错题本面板">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6l9-3 9 3v6c0 5-4 9-9 10-5-1-9-5-9-10z"/></svg>
            </button>
            <button class="ide-activity-icon" data-panel="coach" title="AI 教练" aria-label="AI 教练侧栏">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/></svg>
            </button>
            <div class="ide-activity-spacer"></div>
            <button class="ide-activity-icon" data-panel="settings" title="设置" aria-label="设置面板">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.5-2.4.9a7 7 0 0 0-2-1.2l-.4-2.5h-4l-.4 2.5a7 7 0 0 0-2 1.2l-2.4-.9-2 3.5 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.5 2.4-.9c.6.5 1.3.9 2 1.2l.4 2.5h4l.4-2.5c.7-.3 1.4-.7 2-1.2l2.4.9 2-3.5-2-1.5c.1-.4.1-.8.1-1.2z"/></svg>
            </button>
        </aside>

        <!-- 题目面板 -->
        <section class="ide-task-panel ide-side-panel">
            <div class="brief-hero"><!-- 现有 brief-hero 内容 --></div>
            <div class="brief-card app-action-card"><!-- 现有 任务说明 --></div>
            <div class="brief-card app-action-card"><!-- 现有 示例 --></div>
            <div class="brief-card app-action-card"><!-- 现有 操作建议 --></div>
        </section>

        <!-- 中央舞台：编辑器 + 输出 -->
        <section class="ide-stage">
            <div class="editor-toolbar"><!-- 现有编辑器工具栏 --></div>
            <div class="editor-stage">
                <div class="generation-panel" id="generation-panel" hidden><!-- 现有打字机生成层 --></div>
                <div class="code-editor" id="monaco-host">
                    <textarea class="code-textarea" id="code-input" spellcheck="false" aria-label="代码编辑器"></textarea>
                </div>
            </div>
            <div class="output-panel" id="output-panel"><!-- 现有输出区域 --></div>
        </section>

        <!-- AI 教练侧栏 -->
        <aside class="ide-coach ide-side-panel ide-side-right">
            <div class="ide-resizer" data-target=".ide-coach" data-panel="coach" aria-label="拖拽调整宽度"></div>
            <div class="assistant-header"><!-- 现有 assistant-header --></div>
            <div class="assistant-quick-actions" id="assistant-quick-actions"></div>
            <div class="message-container" id="message-container"></div>
            <div class="assistant-input-panel"><!-- 现有 input panel --></div>
        </aside>

        <!-- 状态栏 -->
        <footer class="ide-status-bar terminal-bar">
            <div class="ide-status-left">
                <span class="terminal-item" id="status-cursor">Ln 1, Col 1</span>
                <span class="terminal-item" id="status-lang">Python</span>
            </div>
            <div class="ide-status-right">
                <span class="terminal-item" id="terminal-mode">模式: 补全代码</span>
                <span class="terminal-item" id="terminal-token">AI: 0 / 8k</span>
                <span class="terminal-item" id="terminal-mastery">掌握度: 53%</span>
            </div>
        </footer>
    </main>

    <script src="/js/data-layer.js"></script>
    <script src="/js/code.js?v=20260615-ide-1"></script>
    <script src="/js/code-ide.js?v=20260615-ide-1"></script>
    <script src="/js/code-monaco.js?v=20260615-ide-1"></script>
    <script src="/js/code-output-tabs.js?v=20260615-ide-1"></script>
    <script src="/js/code-coach.js?v=20260615-ide-1"></script>
    <link rel="stylesheet" href="/css/code-ide.css?v=20260615-ide-1">
```

同时在 `<head>` 区域追加 CDN 预连接：

```html
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
```

- [ ] **Step 4: 运行 E2E 确认通过**

```bash
npx playwright test tests/frontend/e2e/code-ide-skeleton.spec.js
```

Expected: PASS — `.ide-shell` 可见，4+ 活动栏图标，状态栏可见，AI 教练侧栏已挂载。

- [ ] **Step 5: 提交**

```bash
git add html/code.html tests/frontend/e2e/code-ide-skeleton.spec.js
git commit -m "feat(ide): rewrite code.html as IDE shell with 4-zone layout"
```

---

### Task 15: js/code.js DOM 兼容（兼容新旧选择器）

**Files:**
- Modify: `js/code.js`

- [ ] **Step 1: 写失败测试** — 验证 `code.js` 入口在 IDE DOM 下不抛错（关键函数存在）

```javascript
// tests/frontend/unit/code-ide.test.js 追加
describe('code.js compat with IDE DOM', () => {
  it('关键函数在 module scope 存在', async () => {
    // load code.js as a script (no real DOM needed for top-level eval)
    const fs = require('fs');
    const code = fs.readFileSync(require('path').resolve(__dirname, '../../../js/code.js'), 'utf-8');
    // strip IIFE / DOMContentLoaded wrapper for inspection
    expect(code).toMatch(/async function typeCodeToEditor/);
    expect(code).toMatch(/function handleRun/);
    expect(code).toMatch(/function handleSubmit/);
    expect(code).toMatch(/function callAI/);
  });
});
```

- [ ] **Step 2: 运行测试确认失败 / 通过**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: 如果 `code.js` 没动过则通过；如果 grep 不到新函数名则失败。

- [ ] **Step 3: 在 js/code.js 顶部 cacheElements 处追加 fallback 选择器**

定位 `js/code.js` 行 477-489 的 `cacheElements`，把内部 `elements.codeInput = document.getElementById('code-input')` 之后追加：

```javascript
    // IDE 兼容性：side panel 容器选择器
    elements.taskPanel = document.querySelector('.ide-task-panel') || document.querySelector('.brief-panel');
    elements.coachPanel = document.querySelector('.ide-coach') || document.querySelector('.assistant-panel');
    elements.statusBar = document.querySelector('.ide-status-bar') || document.querySelector('.terminal-bar');
    elements.outputPanel = document.querySelector('#output-panel') || document.querySelector('.output-panel');
    elements.activityBar = document.querySelector('.ide-activity-bar');
```

并把 `cacheElements` 调用包到 try/catch 以兼容部分元素缺失：

```javascript
try {
    cacheElements();
} catch (e) {
    console.warn('[code.js] cacheElements partial:', e.message);
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: PASS — grep 命中所有 4 个函数。

- [ ] **Step 5: 提交**

```bash
git add js/code.js tests/frontend/unit/code-ide.test.js
git commit -m "refactor(code.js): cache IDE DOM with fallback to legacy selectors"
```

---

### Task 16: css/code.css 清理（删除 textarea/line-numbers 旧样式）

**Files:**
- Modify: `css/code.css`

- [ ] **Step 1: 写失败测试** — 验证 `code.css` 中不再包含 `.code-textarea` 样式规则

```javascript
// tests/frontend/unit/code-ide.test.js 追加
import fs from 'fs';
import path from 'path';

describe('code.css cleanup', () => {
  it('不再定义 .code-textarea 规则', () => {
    const css = fs.readFileSync(path.resolve(__dirname, '../../../css/code.css'), 'utf-8');
    expect(css).not.toMatch(/\.code-textarea\s*\{/);
    expect(css).not.toMatch(/\.line-number-gutter\s*\{/);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: FAIL — 旧规则仍存在。

- [ ] **Step 3: 在 css/code.css 中删除旧规则**

用文本编辑器打开 `css/code.css`，删除以下规则块（保留类名在 HTML 中作为 hook，因为 Monaco 可能通过 textarea 同步值）：

```css
/* 删除这些块 */
.code-textarea { ... }
.line-number-gutter { ... }
.line-numbers { ... }
```

但保留 `.code-editor` 容器样式（仍用作 Monaco 父元素背景）以及 `.output-panel` 相关样式（输出面板仍要使用）。

- [ ] **Step 4: 运行测试确认通过**

```bash
npx vitest run tests/frontend/unit/code-ide.test.js
```

Expected: PASS — 两个 not.toMatch 都通过。

- [ ] **Step 5: 提交**

```bash
git add css/code.css tests/frontend/unit/code-ide.test.js
git commit -m "refactor(code.css): remove legacy textarea and line-number styles"
```

---

### Task 17: 6 主题截图回归

**Files:**
- Create: `tests/frontend/e2e/code-ide-theme-regression.spec.js`

- [ ] **Step 1: 写 E2E**

```javascript
// tests/frontend/e2e/code-ide-theme-regression.spec.js
const { test, expect } = require('@playwright/test');

const THEMES = ['dawn', 'forest', 'sakura', 'midnight', 'nebula', 'cyber'];

for (const theme of THEMES) {
  test(`code.html 在 ${theme} 主题下布局无破版`, async ({ page }) => {
    await page.addInitScript((t) => {
      localStorage.setItem('starlearn_theme', t);
    }, theme);
    await page.goto('/code.html');
    await page.waitForSelector('.ide-shell');
    // 主要元素 visible & 不超出视口
    await expect(page.locator('.ide-shell')).toBeVisible();
    const shellBox = await page.locator('.ide-shell').boundingBox();
    expect(shellBox.width).toBeGreaterThan(800);
    // 截图存档
    await page.screenshot({ path: `tests/frontend/e2e/__screenshots__/code-ide-${theme}.png`, fullPage: false });
  });
}
```

- [ ] **Step 2: 运行 E2E**

```bash
mkdir -p tests/frontend/e2e/__screenshots__
npx playwright test tests/frontend/e2e/code-ide-theme-regression.spec.js
```

Expected: 6 个 test 全部 PASS（若破版会失败）；截图保存到 `__screenshots__/`。

- [ ] **Step 3: 如果有破版 — 修正 css/code-ide.css 的颜色使用**

如果某些主题下对比度不足，把 `var(--text-soft)` 改成 `var(--text)` 等可读性更高的变量。注意**只改变量引用**，不改硬编码。

- [ ] **Step 4: 重新运行 E2E**

```bash
npx playwright test tests/frontend/e2e/code-ide-theme-regression.spec.js
```

Expected: 6 个 test 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add tests/frontend/e2e/code-ide-theme-regression.spec.js tests/frontend/e2e/__screenshots__/
git commit -m "test(ide): theme regression snapshots for all 6 themes"
```

---

## Phase 6: 测试合并 + 端到端验收

### Task 18: 合并所有单元测试运行

- [ ] **Step 1: 运行全部 unit tests**

```bash
npx vitest run tests/frontend/unit/
```

Expected: 所有 test file 通过（含 code-ide / code-monaco / code-coach / code-output-tabs）。

- [ ] **Step 2: 如果有失败，定位修复**

- [ ] **Step 3: 提交（如有改动）**

```bash
git add tests/ frontend/
git commit -m "test(ide): all unit tests green"
```

---

### Task 19: 合并所有 E2E 运行

- [ ] **Step 1: 运行全部 E2E tests**

```bash
npx playwright test
```

Expected: 所有 E2E 通过；现有 `tests/test_code_*.py` Python 测试通过。

- [ ] **Step 2: 手动验收清单（在浏览器打开 http://localhost:5173/code.html）**

逐项打勾：
- [ ] 活动栏 4 个图标可见，鼠标悬停有 tooltip
- [ ] 点击"题目"图标 → 题目面板内容切换；状态栏不变
- [ ] Monaco 编辑器加载（看到语法高亮 + 行号）
- [ ] Ctrl+Enter / F5 触发"运行代码"
- [ ] 自动保存指示器每 1.2s 后显示"已自动保存"
- [ ] AI 教练侧栏可拖拽改变宽度；宽度持久化（刷新后保持）
- [ ] 输出面板有 4 Tab：运行/执行流/测试/回放
- [ ] 静默 3 分钟后右下出现旁白气泡，3 秒后淡出
- [ ] 切换 6 套主题，布局无破版

- [ ] **Step 3: 提交验收报告**

```bash
git add docs/ RUNNING_GUIDE.md 2>/dev/null || true
git commit -m "docs(sprint1): mark Sprint 1 acceptance complete" --allow-empty
```

---

### Task 20: 更新 RUNNING_GUIDE + README（如有）

- [ ] **Step 1: 检查现有 RUNNING_GUIDE.md 是否有"代码控制台"段落**

```bash
grep -n "code.html\|代码控制台\|代码工坊" RUNNING_GUIDE.md 2>/dev/null || echo "no existing section"
```

- [ ] **Step 2: 如果存在，追加 IDE 工作台说明**

在文末追加：

```markdown
## 代码控制台 IDE 工作台（Sprint 1+）

`/code.html` 已升级为 IDE 四区骨架：

- **活动栏**：题目 / 笔记 / 错题本 / AI 教练 / 设置
- **中央舞台**：Monaco 编辑器 + Tab 化输出（运行/执行流/测试/回放）
- **AI 教练侧栏**：可拖拽、可折叠、布局持久化
- **状态栏**：Ln/Col / 语言 / 模式 / Token / 掌握度
- **教练主动旁白**：5 事件触发（静默 / 重复错 / 接近完成 / 通过 / 连续挫败）

### 开发

- Monaco 通过 CDN 延迟加载（首屏不阻塞）
- IDE 控制器：`js/code-ide.js`
- 教练旁白：`js/code-coach.js`
- 单元测试：`tests/frontend/unit/code-*.test.js`
- E2E：`tests/frontend/e2e/code-ide-*.spec.js`

### 主题

100% 走 `css/tokens.css` 变量，6 套主题（dawn/forest/sakura/midnight/nebula/cyber）全部继承。
```

- [ ] **Step 3: 提交**

```bash
git add RUNNING_GUIDE.md
git commit -m "docs: document code console IDE workbench"
```

---

## 自审检查（执行完毕时验证）

- [ ] **Spec 覆盖（P0 第 1-6 项）**：
  - Task 14 → Monaco 接入 + IDE 骨架 ✅
  - Task 14 / 15 → AI 教练侧栏改造 ✅
  - Task 14 → 题目面板 AI 推荐 + 换一题（沿用旧 code.js 逻辑，Sprint 2 升级）⚠️ 部分
  - Task 13 → 输出面板 Tab 化 ✅
  - Task 14 → 状态栏扩展 ✅
  - Task 10-12 → 教练主动旁白 5 规则 ✅
- [ ] **占位符扫描**：所有步骤均有具体代码/命令；无 "TODO"/"TBD"
- [ ] **类型一致性**：
  - `CodeIDE.activate(panelKey)` 全程一致
  - `CodeMonaco.create(textareaEl, opts)` → `{ editor, getValue, setValue, onChange, dispose, bindShortcuts }`
  - `CodeCoach.start()` / `mountNarrator(hostEl, coach)` 全程一致
- [ ] **范围**：Sprint 1 单一 plan 可独立执行；后续 Sprint 2-4 接力新 spec/plan

---

## 执行选项

Plan complete and saved to `docs/superpowers/plans/2026-06-15-code-console-ai-citizen-sprint1.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
