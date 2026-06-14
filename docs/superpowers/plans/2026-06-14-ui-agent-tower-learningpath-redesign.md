# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign 6D knowledge radar (glassmorphism), transform Agent Control Tower into interactive 3-tab console, restructure Learning Path to card-based layout, with all controls wired to real backend APIs.

**Architecture:** All changes are frontend-only (CSS + JS restructure) except one new API endpoint. Existing data pipelines (SSE profile_updated, learning path API, portrait API, memories API) are reused. Control tower controls write to existing backend endpoints.

**Tech Stack:** Vanilla JS, CSS custom properties (glassmorphism theme), Canvas 2D (radar), SSE (real-time data)

---

## File Structure

| File | Responsibility | Change Type |
|------|---------------|-------------|
| `html/index.html` | Radar section, tower container, learning path container markup | Modify |
| `css/index.css` | Radar styles, learning path card styles, tower container styles | Modify |
| `css/agent-tower.css` | Tower tab layout, tab content styles, float button styles | Rewrite |
| `js/index.js` | Radar rendering upgrades, tower tab logic, learning path card HTML, all interactive controls | Modify |
| `js/agent-bus.js` | Possibly new event types for control actions | Maybe modify |
| `app/api/agent_orchestration.py` or new | New `POST /api/learning-path/goal` endpoint | Create |

---

### Task 1: Learning Path — Card-Based Layout Restructure

**Files:**
- Modify: `css/index.css` (`.path-analysis-*` section, lines 2784-3200)
- Modify: `js/index.js` (`renderPathTree()` function, lines 5982-6137)

- [ ] **Step 1: Rewrite CSS for card-based learning path layout**

Replace the `.path-analysis-*` CSS block in `css/index.css` (starting at line 2784) with glassmorphism card styles:

```css
/* ── AI 学习路径分析视图 (Card Layout) ── */
.path-analysis-root {
    font-size: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

/* Banner card */
.path-analysis-banner {
    background: linear-gradient(135deg, var(--accent-bg) 0%, rgba(59,130,246,0.04) 100%);
    border: 1px solid var(--accent-border);
    border-radius: 14px;
    padding: 14px 16px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
    backdrop-filter: blur(8px);
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

/* Status cards per node */
.path-analysis-node-card {
    background: var(--glass-bg);
    border: 1px solid var(--border-glass);
    border-radius: 12px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: all 0.25s ease;
    position: relative;
}
.path-analysis-node-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}
.path-analysis-node-card.is-completed {
    opacity: 0.75;
}
.path-analysis-node-card.is-completed::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(34,197,94,0.04), transparent);
    pointer-events: none;
}
.path-analysis-node-card.is-in-progress {
    border-left: 3px solid var(--primary-light);
    background: linear-gradient(135deg, var(--glass-bg), rgba(59,130,246,0.03));
}
.path-analysis-node-card.is-locked {
    opacity: 0.5;
}
.path-analysis-node-card .node-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}
.path-analysis-node-card .node-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 0;
}
.path-analysis-node-card .node-status-icon {
    font-size: 16px;
    flex-shrink: 0;
}
.path-analysis-node-card .node-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.path-analysis-node-card .node-action-btn {
    flex-shrink: 0;
    font-size: 10px;
    padding: 3px 10px;
    border-radius: 9999px;
    border: 1px solid var(--accent-border);
    background: var(--accent-bg);
    color: var(--primary-light);
    cursor: pointer;
    transition: all 0.2s;
}
.path-analysis-node-card .node-action-btn:hover {
    background: var(--primary-light);
    color: #fff;
}
.path-analysis-node-card .node-mastery-row {
    display: flex;
    align-items: center;
    gap: 8px;
}
.path-analysis-node-card .node-mastery-bar-bg {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: rgba(255,255,255,0.06);
    overflow: hidden;
}
.path-analysis-node-card .node-mastery-bar-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--primary-light), var(--accent));
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.path-analysis-node-card .node-mastery-text {
    font-size: 10px;
    color: var(--text-tertiary);
    white-space: nowrap;
}
.path-analysis-node-card .node-prereq {
    font-size: 9px;
    color: var(--text-tertiary);
}

/* Capability grid */
.path-analysis-dim-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}
.path-analysis-dim-item {
    background: var(--glass-bg);
    border: 1px solid var(--border-glass);
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    gap: 8px;
    align-items: flex-start;
    transition: all 0.2s;
    cursor: default;
}
.path-analysis-dim-item:hover {
    border-left: 2px solid var(--accent);
    transform: translateX(2px);
}
.path-analysis-dim-icon {
    font-size: 16px;
    flex-shrink: 0;
    margin-top: 1px;
}
.path-analysis-dim-body {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
}
.path-analysis-dim-label {
    font-size: 9px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.path-analysis-dim-value {
    font-size: 10.5px;
    color: var(--text-secondary);
    line-height: 1.4;
    word-break: break-word;
}

/* Node goals list */
.path-analysis-goals-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.path-analysis-goal-item {
    background: var(--glass-bg);
    border: 1px solid var(--border-glass);
    border-radius: 10px;
    padding: 10px 12px;
    transition: all 0.2s;
}

/* Progress bar */
.path-analysis-progress {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.path-analysis-progress-bar-bg {
    height: 6px;
    border-radius: 3px;
    background: rgba(255,255,255,0.06);
    overflow: hidden;
}
.path-analysis-progress-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--primary-light), var(--accent));
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.path-analysis-progress-stats {
    display: flex;
    gap: 12px;
    font-size: 10px;
}
.path-analysis-stat.completed { color: var(--success); }
.path-analysis-stat.inprogress { color: var(--primary-light); }
.path-analysis-stat.locked { color: var(--text-tertiary); }
```

- [ ] **Step 2: Rewrite `renderPathTree()` JS to use card layout**

Replace the `renderPathTree()` function body in `js/index.js` (lines 5982-6137) with:

```js
function renderPathTree() {
    const container = document.getElementById('path-tree-container');
    if (!container) return;

    if (!currentPath || currentPath.length === 0) {
        container.innerHTML = '<div class="text-xs py-4 text-center" style="color: var(--text-tertiary);">暂无学习路径</div>';
        return;
    }

    const totalNodes = currentPath.length;
    const completedNodes = currentPath.filter(n => n.status === 'completed').length;
    const inProgressNodes = currentPath.filter(n => n.status === 'in_progress').length;
    const progressPercent = Math.round(((completedNodes + inProgressNodes * 0.5) / totalNodes) * 100);
    const current = currentPath.find(n => n.status === 'in_progress');
    const next = currentPath.find(n => n.status === 'locked');

    // Banner
    let html = `<div class="path-analysis-root">`;
    const now = new Date();
    const timestamp = now.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });

    let bannerParts = [];
    bannerParts.push(`🧠 星识认知引擎根据你近期的学习行为，生成了包含 <strong>${totalNodes}</strong> 个节点的专属学习路径。`);
    if (current) {
        bannerParts.push(`📌 <strong>当前学习</strong>：<span class="path-analysis-highlight">${escapeHtml(current.topic || '当前任务')}</span>`);
        if (current.description) bannerParts.push(`<span class="path-analysis-desc">${escapeHtml(current.description)}</span>`);
    }

    html += `<div class="path-analysis-banner">
        <span class="path-analysis-icon">🧙‍♂️</span>
        <div class="path-analysis-text">${bannerParts.map(p => `<div class="path-analysis-line">${p}</div>`).join('')}</div>
    </div>`;

    // Node cards
    html += `<div class="path-analysis-goals-list">`;
    for (const node of currentPath) {
        const nodeName = node.topic || node.name || node.title || '学习节点';
        const status = node.status || 'locked';
        const mastery = node.mastery_score != null ? Math.round(node.mastery_score * 100) : null;
        const prereqText = (node.prerequisites && node.prerequisites.length > 0) ? `前置: ${node.prerequisites.join(', ')}` : '';

        let statusIcon, statusClass, actionBtn;
        if (status === 'completed') {
            statusIcon = '✅'; statusClass = 'is-completed';
            actionBtn = `<button class="node-action-btn" onclick="alert('回顾功能')">回顾</button>`;
        } else if (status === 'in_progress') {
            statusIcon = '🟡'; statusClass = 'is-in-progress';
            actionBtn = `<button class="node-action-btn">继续学习</button>`;
        } else {
            statusIcon = '⚪'; statusClass = 'is-locked';
            actionBtn = '';
        }

        html += `<div class="path-analysis-node-card ${statusClass}">
            <div class="node-header">
                <div class="node-title-row">
                    <span class="node-status-icon">${statusIcon}</span>
                    <span class="node-name">${escapeHtml(nodeName)}</span>
                </div>
                ${actionBtn}
            </div>`;

        if (mastery !== null) {
            html += `<div class="node-mastery-row">
                <div class="node-mastery-bar-bg">
                    <div class="node-mastery-bar-fill" style="width:${mastery}%"></div>
                </div>
                <span class="node-mastery-text">${mastery}%</span>
            </div>`;
        }

        if (prereqText) {
            html += `<div class="node-prereq">${prereqText}</div>`;
        }

        html += `</div>`;
    }
    html += `</div>`;

    // Capability grid
    const dimConfig = [
        { key: 'knowledge_base_assessment', icon: '📚', label: '知识适配' },
        { key: 'learning_goal_alignment', icon: '🎯', label: '目标对齐' },
        { key: 'cognitive_style_adaptation', icon: '🧠', label: '认知适配' },
        { key: 'weakness_reinforcement', icon: '⚡', label: '短板强化' },
        { key: 'learning_pace', icon: '📊', label: '节奏建议' },
    ];
    const hasCapability = capabilityAnalysis && Object.keys(capabilityAnalysis).length > 0;

    if (hasCapability) {
        html += `<div class="path-analysis-dimensions">
            <div class="path-analysis-dim-title">🎯 多维能力规划</div>
            <div class="path-analysis-dim-grid">`;
        for (const cfg of dimConfig) {
            const val = capabilityAnalysis[cfg.key];
            if (val) {
                html += `<div class="path-analysis-dim-item">
                    <span class="path-analysis-dim-icon">${cfg.icon}</span>
                    <div class="path-analysis-dim-body">
                        <span class="path-analysis-dim-label">${cfg.label}</span>
                        <span class="path-analysis-dim-value">${escapeHtml(val)}</span>
                    </div>
                </div>`;
            }
        }
        html += `</div></div>`;
    }

    // Progress bar
    html += `<div class="path-analysis-progress">
        <div class="path-analysis-progress-bar-bg">
            <div class="path-analysis-progress-bar-fill" style="width: ${progressPercent}%;"></div>
        </div>
        <div class="path-analysis-progress-stats">
            <span class="path-analysis-stat completed">${completedNodes} 已完成</span>
            <span class="path-analysis-stat inprogress">${inProgressNodes} 进行中</span>
            <span class="path-analysis-stat locked">${totalNodes - completedNodes - inProgressNodes} 待解锁</span>
        </div>
    </div>`;

    // Footer
    html += `<div class="path-analysis-footer"><span class="path-analysis-time">🕐 ${timestamp}</span></div>`;
    html += `</div>`;
    container.innerHTML = html;
}
```

- [ ] **Step 3: Test visually in browser**

Run: Start the dev server and open index.html. Verify:
- Node cards render with correct status colors
- Progress bar animates on page load
- Capability grid shows 2 columns
- Empty state ("暂无学习路径") renders when no data

- [ ] **Step 4: Commit**

```bash
git add css/index.css js/index.js
git commit -m "refactor(learning-path): card-based layout with glassmorphism styling"
```

---

### Task 2: 6D Knowledge Radar — Glassmorphism Visual Refresh

**Files:**
- Modify: `css/index.css` (`.glass-radar-wrap` styles at lines 3413-3559)
- Modify: `js/index.js` (`renderRadarChart()` at lines 3288-3554, add dimension list)

- [ ] **Step 1: Add radar dimension list CSS**

At the end of `.glass-radar-wrap` CSS block in `css/index.css` (after line 3559), add:

```css
/* radar dimension list below canvas */
.radar-dim-list {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.radar-dim-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 6px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
}
.radar-dim-item:hover {
    background: rgba(255,255,255,0.04);
}
.radar-dim-label {
    font-size: 10px;
    color: var(--text-secondary);
    min-width: 42px;
    flex-shrink: 0;
}
.radar-dim-bar-bg {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: rgba(255,255,255,0.06);
    overflow: hidden;
}
.radar-dim-bar-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--primary-light), var(--accent));
    transition: width 0.6s ease;
}
.radar-dim-value {
    font-size: 10px;
    color: var(--text-tertiary);
    min-width: 24px;
    text-align: right;
}
.radar-dim-insight {
    display: none;
    font-size: 9.5px;
    color: var(--text-tertiary);
    padding: 4px 8px;
    margin-top: 2px;
    background: rgba(0,0,0,0.1);
    border-radius: 6px;
    line-height: 1.4;
}
.radar-dim-insight.is-visible {
    display: block;
}
```

- [ ] **Step 2: Add dimension list generation to radar render flow**

In `js/index.js`, after the canvas element in the radar section, add a container for the dimension list. Modify the `renderRadarChart()` call to also call `renderRadarDimensionList()`. Add this new function after `renderRadarChart()`:

```js
/**
 * Render the dimension detail list below the radar canvas.
 * Shows per-dimension progress bars with click-to-expand insights.
 */
function renderRadarDimensionList() {
    const wrap = document.querySelector('.glass-radar-wrap');
    if (!wrap) return;

    let listEl = wrap.querySelector('.radar-dim-list');
    if (!listEl) {
        listEl = document.createElement('div');
        listEl.className = 'radar-dim-list';
        wrap.appendChild(listEl);
    }

    let dims, values, descs;
    if (typeof towerRadarSnapshot !== 'undefined' && towerRadarSnapshot && towerRadarSnapshot.radar) {
        const RADAR_DIMENSIONS = {
            knowledge_mastery: { label: '知识掌握', desc: '知识体系的掌握程度' },
            code_skill: { label: '编程能力', desc: '编程实践能力水平' },
            cognitive_style: { label: '认知风格', desc: '信息处理与学习偏好' },
            learning_goal: { label: '学习目标', desc: '目标明确性与方向感' },
            weakness: { label: '知识短板', desc: '薄弱环节严重度' },
            focus_level: { label: '专注度', desc: '学习注意力维持能力' },
        };
        dims = [];
        values = [];
        descs = [];
        for (const [key, cfg] of Object.entries(RADAR_DIMENSIONS)) {
            const val = towerRadarSnapshot.radar[key];
            if (val != null) {
                dims.push(cfg.label);
                values.push(val);
                descs.push(cfg.desc);
            }
        }
    } else {
        dims = ['方向', '基础', '编程', '认知', '短板', '专注'];
        values = [50, 50, 50, 50, 50, 50];
        descs = ['', '', '', '', '', ''];
    }

    let html = '';
    for (let i = 0; i < dims.length; i++) {
        const val = Math.min(100, Math.max(0, values[i]));
        const insightKey = 'radar-insight-' + i;
        html += `<div class="radar-dim-item" onclick="toggleRadarInsight(${i})">
            <span class="radar-dim-label">${dims[i]}</span>
            <div class="radar-dim-bar-bg">
                <div class="radar-dim-bar-fill" style="width:${val}%"></div>
            </div>
            <span class="radar-dim-value">${val}</span>
        </div>
        <div class="radar-dim-insight" id="${insightKey}">${descs[i] || '暂无分析'}</div>`;
    }
    listEl.innerHTML = html;
}

function toggleRadarInsight(idx) {
    const el = document.getElementById('radar-insight-' + idx);
    if (el) el.classList.toggle('is-visible');
}
```

Update the render callsite (somewhere after `renderRadarChart()` is called) to also call `renderRadarDimensionList()`.

- [ ] **Step 3: Enhance canvas rendering with glassmorphism visuals**

In `js/index.js`, modify `renderRadarChart()` at the gradient fill section (around line 3346) to use softer glow effect:

Find the centerGlow section and replace:
```js
const centerGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
centerGlow.addColorStop(0, radarColorWithAlpha(radarGlow, 0.06));
centerGlow.addColorStop(0.5, radarColorWithAlpha(radarFillStart, 0.03));
centerGlow.addColorStop(1, 'transparent');
```

Replace with enhanced glow:
```js
const centerGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.2);
centerGlow.addColorStop(0, radarColorWithAlpha(radarFillEnd, 0.15));
const midGlow = ctx.createRadialGradient(cx, cy, R * 0.1, cx, cy, R);
midGlow.addColorStop(0, radarColorWithAlpha(radarGlow, 0.08));
midGlow.addColorStop(0.5, radarColorWithAlpha(radarFillStart, 0.04));
midGlow.addColorStop(1, 'transparent');
ctx.fillStyle = midGlow;
ctx.fillRect(0, 0, W, H);
```

- [ ] **Step 4: Reduce aspect-ratio constraint on radar wrap**

Change `css/index.css` line 3428 from `aspect-ratio: 1 / 1` to `aspect-ratio: auto` so the wrap naturally fits canvas + dimension list height.

- [ ] **Step 5: Test visually**

Verify:
- Canvas renders with enhanced glow
- Dimension list shows below the canvas with progress bars
- Clicking a dimension expands/collapses insight text
- No regressions on existing radar functionality

- [ ] **Step 6: Commit**

```bash
git add css/index.css js/index.js
git commit -m "feat(radar): glassmorphism refresh + dimension detail list"
```

---

### Task 3: Agent Control Tower — Default Hidden + Float Button

**Files:**
- Modify: `html/index.html` (tower section markup)
- Modify: `css/index.css` (tower container + float button styles)
- Modify: `js/index.js` (tower init: default collapse)

- [ ] **Step 1: Add float trigger button to HTML**

In `html/index.html`, just before `#track-a-container`, add a floating trigger button:

```html
<!-- Floating tower trigger button -->
<button id="tower-float-btn" class="tower-float-btn" onclick="toggleTowerPanel()" title="打开 AI 控制塔">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
    <span class="float-btn-label">控制塔</span>
</button>
```

- [ ] **Step 2: Make tower default collapsed**

In `js/index.js`, in `initAgentTower()` or the DOMContentLoaded block, add:

```js
// Default: tower starts collapsed
const towerContainer = document.getElementById('track-a-container');
if (towerContainer) {
    towerContainer.classList.add('collapsed');
}
```

Remove the `collapsed` class from any server-rendered markup (if present).

- [ ] **Step 3: Add float button CSS**

In `css/index.css`, after the `#track-a-container.collapsed` block (around line 2049), add:

```css
/* Floating tower trigger button */
.tower-float-btn {
    position: fixed;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 100;
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
    border: 1px solid rgba(255,255,255,0.15);
    color: #fff;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    opacity: 0;
    pointer-events: none;
}
.tower-float-btn.is-visible {
    opacity: 1;
    pointer-events: auto;
}
.tower-float-btn:hover {
    transform: translateY(-50%) scale(1.08);
    box-shadow: 0 6px 24px rgba(0,0,0,0.4);
}
.tower-float-btn .float-btn-label {
    font-size: 6px;
    font-weight: 700;
    letter-spacing: 0.05em;
    line-height: 1;
}
```

- [ ] **Step 4: Wire toggle function + float button visibility**

In `js/index.js`, add:

```js
function toggleTowerPanel() {
    const container = document.getElementById('track-a-container');
    const floatBtn = document.getElementById('tower-float-btn');
    if (!container) return;
    const isCollapsed = container.classList.contains('collapsed');
    if (isCollapsed) {
        container.classList.remove('collapsed');
        if (floatBtn) floatBtn.classList.remove('is-visible');
    } else {
        container.classList.add('collapsed');
        if (floatBtn) floatBtn.classList.add('is-visible');
    }
    window.dispatchEvent(new Event('resize'));
}

// Show float button when tower is collapsed
function updateTowerFloatBtn() {
    const container = document.getElementById('track-a-container');
    const floatBtn = document.getElementById('tower-float-btn');
    if (!container || !floatBtn) return;
    floatBtn.classList.toggle('is-visible', container.classList.contains('collapsed'));
}
```

Call `updateTowerFloatBtn()` after init. Also add a resize observer or event listener on the tower toggle to call `updateTowerFloatBtn()`.

- [ ] **Step 5: Test visually**

Verify:
- Tower starts collapsed on page load
- Float button is visible when tower is collapsed
- Clicking float button opens the tower
- Clicking toggle inside tower collapses it and shows float button again

- [ ] **Step 6: Commit**

```bash
git add html/index.html css/index.css js/index.js
git commit -m "feat(tower): default hidden with float trigger button"
```

---

### Task 4: Agent Control Tower — 3-Tab Layout Restructure

**Files:**
- Rewrite: `css/agent-tower.css` (full rewrite for tab layout)
- Modify: `html/index.html` (replace tower content with tab structure)
- Modify: `js/index.js` (add tab switching, tab content renderers)

- [ ] **Step 1: Replace tower HTML with tab structure**

In `html/index.html` (lines 187-209), replace the tower content with:

```html
<div id="track-a" class="track-sandbox flex flex-col h-[35vh] md:h-full">
    <!-- Tower Header -->
    <div class="tower-header">
        <h2><span id="tower-status-dot" class="tower-status-dot"></span> AI 控制塔</h2>
        <div class="tower-actions">
            <button class="tower-btn" id="tower-toggle" title="收起控制塔" onclick="toggleTowerPanel()">✕</button>
        </div>
    </div>
    <!-- Tab Navigation -->
    <div class="tower-tabs">
        <button class="tower-tab is-active" data-tab="status" onclick="switchTowerTab('status', this)">📊 实时学情</button>
        <button class="tower-tab" data-tab="control" onclick="switchTowerTab('control', this)">🎛 教学调控</button>
        <button class="tower-tab" data-tab="plan" onclick="switchTowerTab('plan', this)">🎯 任务编排</button>
    </div>
    <!-- Tab Content -->
    <div class="tower-content">
        <div class="tower-tab-content is-active" id="tower-tab-status">
            <div id="tower-status-content" class="tower-scroll-area">
                <div class="tower-loading">加载学情数据...</div>
            </div>
        </div>
        <div class="tower-tab-content" id="tower-tab-control">
            <div id="tower-control-content" class="tower-scroll-area">
                <div class="tower-loading">加载控制面板...</div>
            </div>
        </div>
        <div class="tower-tab-content" id="tower-tab-plan">
            <div id="tower-plan-content" class="tower-scroll-area">
                <div class="tower-loading">加载任务编排...</div>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 2: Rewrite `css/agent-tower.css`**

Replace the entire file with tab layout styles:

```css
/* css/agent-tower.css — Agent Control Tower 2.0 */

/* Header */
.tower-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border-glass);
    flex-shrink: 0;
}
.tower-header h2 {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 6px;
}
.tower-actions {
    display: flex;
    gap: 6px;
}
.tower-btn {
    background: var(--surface-glass);
    border: 1px solid var(--border-glass);
    border-radius: 8px;
    padding: 4px 10px;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
}
.tower-btn:hover {
    background: var(--surface-glass-2);
}

/* Tab Navigation */
.tower-tabs {
    display: flex;
    border-bottom: 1px solid var(--border-glass);
    flex-shrink: 0;
    background: rgba(0,0,0,0.02);
}
.tower-tab {
    flex: 1;
    padding: 8px 6px;
    font-size: 10px;
    font-weight: 600;
    color: var(--text-tertiary);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
}
.tower-tab:hover {
    color: var(--text-secondary);
    background: rgba(255,255,255,0.02);
}
.tower-tab.is-active {
    color: var(--primary-light);
    border-bottom-color: var(--primary-light);
}

/* Tab Content */
.tower-content {
    flex: 1;
    min-height: 0;
    position: relative;
}
.tower-tab-content {
    display: none;
    height: 100%;
    overflow: hidden;
}
.tower-tab-content.is-active {
    display: block;
}
.tower-scroll-area {
    height: 100%;
    overflow-y: auto;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

/* Loading / Empty / Error states */
.tower-loading {
    text-align: center;
    color: var(--text-tertiary);
    font-size: 11px;
    padding: 20px;
}
.tower-empty {
    text-align: center;
    color: var(--text-tertiary);
    font-size: 11px;
    padding: 20px;
    line-height: 1.6;
}
.tower-error {
    text-align: center;
    color: var(--danger);
    font-size: 11px;
    padding: 16px;
}
.tower-error-retry {
    margin-top: 8px;
    padding: 4px 14px;
    border-radius: 9999px;
    background: var(--surface-glass);
    border: 1px solid var(--border-glass);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 10px;
}

/* Status Cards (Tab 1) */
.tower-status-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.tower-status-card {
    background: var(--glass-bg);
    border: 1px solid var(--border-glass);
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.tower-status-card .tsc-icon {
    font-size: 18px;
    flex-shrink: 0;
}
.tower-status-card .tsc-body {
    flex: 1;
    min-width: 0;
}
.tower-status-card .tsc-label {
    font-size: 9px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.tower-status-card .tsc-value {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-primary);
}
.tower-status-card .tsc-sub {
    font-size: 10px;
    color: var(--text-secondary);
}

/* Weakness items with actions */
.tower-weakness-item {
    background: var(--glass-bg);
    border: 1px solid rgba(239,68,68,0.15);
    border-radius: 10px;
    padding: 10px 12px;
}
.tower-weakness-item .twi-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}
.tower-weakness-item .twi-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
}
.tower-weakness-item .twi-actions {
    display: flex;
    gap: 4px;
}
.tower-action-btn {
    font-size: 9px;
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid var(--accent-border);
    background: var(--accent-bg);
    color: var(--primary-light);
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
}
.tower-action-btn:hover {
    background: var(--primary-light);
    color: #fff;
}
.tower-action-btn.is-danger {
    border-color: rgba(239,68,68,0.3);
    background: rgba(239,68,68,0.08);
    color: var(--danger);
}
.tower-weakness-item .twi-detail {
    font-size: 10px;
    color: var(--text-tertiary);
}

/* Pipeline status (compact, inside status tab) */
.tower-mini-pipeline {
    background: var(--glass-bg);
    border: 1px solid var(--border-glass);
    border-radius: 10px;
    padding: 10px 12px;
}
.tower-mini-pipeline .tmp-header {
    font-size: 9px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 6px;
}
.tower-mini-pipeline .tmp-flow {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}
.tmp-node {
    font-size: 9px;
    padding: 2px 6px;
    border-radius: 4px;
    background: var(--surface-glass);
    border: 1px solid var(--border-glass);
    color: var(--text-tertiary);
}
.tmp-node.is-busy { color: var(--agent-busy); border-color: var(--agent-busy); }
.tmp-node.is-success { color: var(--agent-success); border-color: var(--agent-success); }
.tmp-node.is-failed { color: var(--agent-failed); border-color: var(--agent-failed); }

/* Control Panel (Tab 2) */
.tower-control-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.tower-control-group {
    background: var(--glass-bg);
    border: 1px solid var(--border-glass);
    border-radius: 10px;
    padding: 12px;
}
.tower-control-group .tcg-title {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 8px;
}
.tcg-persona-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
}
.tcg-persona-card {
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid var(--border-glass);
    background: var(--surface-glass);
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
}
.tcg-persona-card:hover {
    border-color: var(--primary-light);
    background: rgba(59,130,246,0.06);
}
.tcg-persona-card.is-active {
    border-color: var(--primary-light);
    background: rgba(59,130,246,0.1);
    box-shadow: 0 0 8px rgba(59,130,246,0.15);
}
.tcg-persona-card .tpc-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
}
.tcg-persona-card .tpc-desc {
    font-size: 9px;
    color: var(--text-tertiary);
    margin-top: 2px;
}
.tcg-strategy-pills {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}
.tcg-strategy-pill {
    font-size: 10px;
    padding: 4px 12px;
    border-radius: 9999px;
    border: 1px solid var(--border-glass);
    background: var(--surface-glass);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
}
.tcg-strategy-pill:hover {
    border-color: var(--accent-border);
    color: var(--text-primary);
}
.tcg-strategy-pill.is-active {
    border-color: var(--primary-light);
    background: var(--accent-bg);
    color: var(--primary-light);
}
.tcg-slider-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
}
.tcg-slider-wrap input[type="range"] {
    flex: 1;
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    border-radius: 2px;
    background: rgba(255,255,255,0.1);
    outline: none;
}
.tcg-slider-wrap input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--primary-light), var(--accent));
    cursor: pointer;
    border: 2px solid rgba(255,255,255,0.15);
}
.tcg-slider-label {
    font-size: 10px;
    color: var(--text-tertiary);
    min-width: 24px;
    text-align: center;
}
.tcg-inject-input {
    display: flex;
    gap: 6px;
}
.tcg-inject-input input {
    flex: 1;
    font-size: 11px;
    padding: 6px 10px;
    border-radius: 8px;
    border: 1px solid var(--border-glass);
    background: var(--surface-glass);
    color: var(--text-primary);
    outline: none;
}
.tcg-inject-input input:focus {
    border-color: var(--primary-light);
}
.tcg-inject-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;
}
.tcg-inject-tag {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 9999px;
    background: var(--accent-bg);
    border: 1px solid var(--accent-border);
    color: var(--primary-light);
    display: flex;
    align-items: center;
    gap: 4px;
}
.tcg-inject-tag .tcg-tag-remove {
    cursor: pointer;
    opacity: 0.6;
    font-size: 12px;
    line-height: 1;
}
.tcg-inject-tag .tcg-tag-remove:hover {
    opacity: 1;
}

/* Plan Tab (Tab 3) */
.tower-plan-goal-input {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.tower-plan-goal-input input {
    width: 100%;
    font-size: 12px;
    padding: 8px 12px;
    border-radius: 10px;
    border: 1px solid var(--border-glass);
    background: var(--glass-bg);
    color: var(--text-primary);
    outline: none;
    box-sizing: border-box;
}
.tower-plan-goal-input input:focus {
    border-color: var(--primary-light);
}
.tower-plan-goal-input .tpg-actions {
    display: flex;
    gap: 6px;
}
.tower-plan-task-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.tower-plan-task {
    background: var(--glass-bg);
    border: 1px solid var(--border-glass);
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: all 0.2s;
}
.tower-plan-task .tpt-icon {
    font-size: 16px;
    flex-shrink: 0;
}
.tower-plan-task .tpt-body {
    flex: 1;
    min-width: 0;
}
.tower-plan-task .tpt-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
}
.tower-plan-task .tpt-detail {
    font-size: 9px;
    color: var(--text-tertiary);
    margin-top: 1px;
}
.tower-plan-task .tpt-action {
    font-size: 9px;
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid var(--accent-border);
    background: var(--accent-bg);
    color: var(--primary-light);
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s;
}
.tower-plan-task .tpt-action:hover {
    background: var(--primary-light);
    color: #fff;
}
.tower-plan-progress {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.tower-plan-progress .tpp-bar-bg {
    height: 6px;
    border-radius: 3px;
    background: rgba(255,255,255,0.06);
    overflow: hidden;
}
.tower-plan-progress .tpp-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--primary-light), var(--accent));
    transition: width 0.6s ease;
}
.tower-plan-progress .tpp-stats {
    font-size: 10px;
    color: var(--text-tertiary);
}
```

- [ ] **Step 3: Add tab switching logic in JS**

In `js/index.js`, add:

```js
/** Tab switching for control tower */
function switchTowerTab(tabName, btnEl) {
    // Update tab buttons
    document.querySelectorAll('.tower-tab').forEach(t => t.classList.remove('is-active'));
    if (btnEl) btnEl.classList.add('is-active');
    // Update tab content
    document.querySelectorAll('.tower-tab-content').forEach(tc => tc.classList.remove('is-active'));
    const target = document.getElementById('tower-tab-' + tabName);
    if (target) target.classList.add('is-active');
    // Load tab content if not yet loaded
    if (tabName === 'status') renderTowerStatusTab();
    else if (tabName === 'control') renderTowerControlTab();
    else if (tabName === 'plan') renderTowerPlanTab();
}
```

- [ ] **Step 4: Render functions for each tab**

Add three new functions in `js/index.js`:

```js
/** Tab 1: Real-time learning status */
function renderTowerStatusTab() {
    const container = document.getElementById('tower-status-content');
    if (!container) return;

    let html = '';

    // Status cards
    const focusLevel = towerRadarSnapshot?.radar?.focus_level ?? '--';
    const mastery = towerRadarSnapshot?.radar?.knowledge_mastery ?? '--';
    html += `<div class="tower-status-grid">
        <div class="tower-status-card">
            <span class="tsc-icon">🎯</span>
            <div class="tsc-body">
                <div class="tsc-label">当前专注度</div>
                <div class="tsc-value">${focusLevel}%</div>
            </div>
        </div>
        <div class="tower-status-card">
            <span class="tsc-icon">📚</span>
            <div class="tsc-body">
                <div class="tsc-label">知识掌握</div>
                <div class="tsc-value">${mastery}%</div>
            </div>
        </div>
        <div class="tower-status-card">
            <span class="tsc-icon">⏱</span>
            <div class="tsc-body">
                <div class="tsc-label">学习时长</div>
                <div class="tsc-value">${localStorage.getItem('starlearn_study') || 0} min</div>
            </div>
        </div>
    </div>`;

    // Weakness alerts
    if (towerRadarSnapshot?.radar?.weakness > 50) {
        html += `<div class="tower-weakness-item">
            <div class="twi-header">
                <span class="twi-label">⚠️ 薄弱环节提醒</span>
                <div class="twi-actions">
                    <button class="tower-action-btn" onclick="requestWeaknessPractice()">生成专项练习</button>
                    <button class="tower-action-btn" onclick="switchTeacherPersona('socratic_questioner')">换个方式讲解</button>
                </div>
            </div>
            <div class="twi-detail">短板维度评分 ${towerRadarSnapshot.radar.weakness}/100，建议加强针对性训练</div>
        </div>`;
    }

    // Mini pipeline status
    html += `<div class="tower-mini-pipeline">
        <div class="tmp-header">Agent 流水线状态</div>
        <div class="tmp-flow" id="tmp-flow"></div>
    </div>`;

    container.innerHTML = html;

    // Fill mini pipeline agents
    const tmpFlow = document.getElementById('tmp-flow');
    if (tmpFlow && agentCatalog) {
        const allAgents = _towerFlattenAgents();
        tmpFlow.innerHTML = allAgents.map(a =>
            `<span class="tmp-node ${towerAgentStatus[a.id] || 'idle'}">${a.name}</span>`
        ).join('');
    }
}

/** Tab 2: Teaching control panel */
function renderTowerControlTab() {
    const container = document.getElementById('tower-control-content');
    if (!container) return;

    const currentPersona = localStorage.getItem('starlearn_persona') || 'patient_tutor';
    const currentStrategy = localStorage.getItem('starlearn_strategy') || 'auto';
    const currentDifficulty = localStorage.getItem('starlearn_difficulty') || 50;
    const injectedTopics = JSON.parse(localStorage.getItem('starlearn_injected_topics') || '[]');

    const personas = [
        { id: 'patient_tutor', name: '陈默', desc: '耐心引导型', icon: '🧑‍🏫' },
        { id: 'socratic_questioner', name: '林文', desc: '苏格拉底追问', icon: '🤔' },
        { id: 'energetic_lecturer', name: '周然', desc: '激情讲解型', icon: '🔥' },
        { id: 'expert_mentor', name: '严正', desc: '严谨教授型', icon: '🎓' },
    ];
    const strategies = [
        { id: 'auto', label: '自动' },
        { id: 'lecture', label: '讲解' },
        { id: 'practice', label: '练习' },
        { id: 'socratic', label: '苏格拉底' },
    ];

    let html = `<div class="tower-control-section">`;

    // Teacher persona
    html += `<div class="tower-control-group">
        <div class="tcg-title">👤 教学风格</div>
        <div class="tcg-persona-grid">`;
    for (const p of personas) {
        const active = p.id === currentPersona ? 'is-active' : '';
        html += `<div class="tcg-persona-card ${active}" onclick="selectPersona('${p.id}', this)">
            <div class="tpc-name">${p.icon} ${p.name}</div>
            <div class="tpc-desc">${p.desc}</div>
        </div>`;
    }
    html += `</div></div>`;

    // Strategy
    html += `<div class="tower-control-group">
        <div class="tcg-title">📋 教学策略</div>
        <div class="tcg-strategy-pills">`;
    for (const s of strategies) {
        const active = s.id === currentStrategy ? 'is-active' : '';
        html += `<span class="tcg-strategy-pill ${active}" onclick="selectStrategy('${s.id}', this)">${s.label}</span>`;
    }
    html += `</div></div>`;

    // Difficulty
    html += `<div class="tower-control-group">
        <div class="tcg-title">📈 难度调节</div>
        <div class="tcg-slider-wrap">
            <span class="tcg-slider-label" style="color:var(--success)">简单</span>
            <input type="range" min="0" max="100" value="${currentDifficulty}" oninput="setDifficulty(this.value)" onchange="saveDifficulty(this.value)">
            <span class="tcg-slider-label" style="color:var(--danger)">困难</span>
        </div>
    </div>`;

    // Knowledge inject
    html += `<div class="tower-control-group">
        <div class="tcg-title">💉 知识注入</div>
        <div class="tcg-inject-input">
            <input type="text" id="tcg-inject-input" placeholder="输入你想重点学习的知识点..." onkeydown="if(event.key==='Enter') injectTopic()">
            <button class="tower-action-btn" onclick="injectTopic()">注入</button>
        </div>
        <div class="tcg-inject-tags" id="tcg-inject-tags">`;
    for (const t of injectedTopics) {
        html += `<span class="tcg-inject-tag">${t} <span class="tcg-tag-remove" onclick="removeInjectedTopic('${t}')">×</span></span>`;
    }
    html += `</div></div>`;
    html += `</div>`;
    container.innerHTML = html;
}

/** Tab 3: Task planning */
function renderTowerPlanTab() {
    const container = document.getElementById('tower-plan-content');
    if (!container) return;

    if (!currentPath || currentPath.length === 0) {
        container.innerHTML = `<div class="tower-control-section">
            <div class="tower-plan-goal-input">
                <input type="text" id="tpg-goal-input" placeholder="设定一个学习目标，例如「两周学会 Python 基础」..." onkeydown="if(event.key==='Enter') planGoalFromInput()">
                <div class="tpg-actions"><button class="tower-action-btn" onclick="planGoalFromInput()">AI 自动拆解</button></div>
            </div>
            <div class="tower-empty">🎯 设定学习目标，AI 将自动为你规划学习路径</div>
        </div>`;
        return;
    }

    const totalNodes = currentPath.length;
    const completedNodes = currentPath.filter(n => n.status === 'completed').length;
    const inProgressNodes = currentPath.filter(n => n.status === 'in_progress').length;
    const progressPercent = Math.round(((completedNodes + inProgressNodes * 0.5) / totalNodes) * 100);

    let html = `<div class="tower-control-section">
        <div class="tower-plan-goal-input">
            <input type="text" id="tpg-goal-input" placeholder="调整学习目标..." onkeydown="if(event.key==='Enter') planGoalFromInput()">
            <div class="tpg-actions">
                <button class="tower-action-btn" onclick="planGoalFromInput()">AI 重新规划</button>
            </div>
        </div>
        <div class="tower-plan-task-list">`;

    for (const node of currentPath) {
        const nodeName = node.topic || node.name || node.title || '任务';
        const status = node.status || 'locked';
        const statusMap = {
            completed: { icon: '✅', cls: '' },
            in_progress: { icon: '🟡', cls: '' },
            locked: { icon: '⚪', cls: '' },
        };
        const s = statusMap[status] || statusMap.locked;
        const actionLabel = status === 'completed' ? '回顾' : (status === 'in_progress' ? '继续学习' : '');
        html += `<div class="tower-plan-task">
            <span class="tpt-icon">${s.icon}</span>
            <div class="tpt-body">
                <div class="tpt-name">${escapeHtml(nodeName)}</div>
                <div class="tpt-detail">${status === 'completed' ? '已完成' : (status === 'in_progress' ? '进行中' : '待解锁')}</div>
            </div>
            ${actionLabel ? `<button class="tpt-action">${actionLabel}</button>` : ''}
        </div>`;
    }

    html += `</div>
        <div class="tower-plan-progress">
            <div class="tpp-bar-bg"><div class="tpp-bar-fill" style="width:${progressPercent}%"></div></div>
            <div class="tpp-stats">${completedNodes}/${totalNodes} 完成 · ${progressPercent}%</div>
        </div>
    </div>`;
    container.innerHTML = html;
}
```

- [ ] **Step 5: Wire up control actions to real APIs**

In `js/index.js`, add the handler functions for all control actions:

```js
/** Teacher persona selection — writes to localStorage + memories API */
function selectPersona(personaId, btnEl) {
    document.querySelectorAll('.tcg-persona-card').forEach(c => c.classList.remove('is-active'));
    if (btnEl) btnEl.classList.add('is-active');
    localStorage.setItem('starlearn_persona', personaId);
    // Persist to backend memories
    savePersonaPreference(personaId);
}
async function savePersonaPreference(personaId) {
    const user = currentUser;
    if (!user || !user.id) return;
    try {
        await fetch('/api/memories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                type: 'preference',
                content: { preferred_persona: personaId }
            })
        });
    } catch (e) { console.warn('[ControlTower] save persona failed', e); }
}

/** Teaching strategy selection */
function selectStrategy(strategyId, el) {
    document.querySelectorAll('.tcg-strategy-pill').forEach(p => p.classList.remove('is-active'));
    if (el) el.classList.add('is-active');
    localStorage.setItem('starlearn_strategy', strategyId);
}

/** Difficulty slider */
function setDifficulty(val) {
    // Real-time visual feedback
}
async function saveDifficulty(val) {
    localStorage.setItem('starlearn_difficulty', val);
    const user = currentUser;
    if (!user || !user.id) return;
    try {
        await fetch('/api/profile/portrait/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                difficulty_pref: parseInt(val)
            })
        });
    } catch (e) { console.warn('[ControlTower] save difficulty failed', e); }
}

/** Knowledge injection */
function injectTopic() {
    const input = document.getElementById('tcg-inject-input');
    if (!input || !input.value.trim()) return;
    const topic = input.value.trim();
    const existing = JSON.parse(localStorage.getItem('starlearn_injected_topics') || '[]');
    if (existing.includes(topic)) return;
    existing.push(topic);
    localStorage.setItem('starlearn_injected_topics', JSON.stringify(existing));
    input.value = '';
    // Re-render and persist
    renderTowerControlTab();
    saveInjectedTopics(existing);
}
function removeInjectedTopic(topic) {
    let existing = JSON.parse(localStorage.getItem('starlearn_injected_topics') || '[]');
    existing = existing.filter(t => t !== topic);
    localStorage.setItem('starlearn_injected_topics', JSON.stringify(existing));
    renderTowerControlTab();
    saveInjectedTopics(existing);
}
async function saveInjectedTopics(topics) {
    const user = currentUser;
    if (!user || !user.id || topics.length === 0) return;
    try {
        await fetch('/api/memories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                type: 'interest',
                content: { topics }
            })
        });
    } catch (e) { console.warn('[ControlTower] save topics failed', e); }
}

/** Weakness: generate practice */
function requestWeaknessPractice() {
    // Send a special message to the chat to generate practice exercises
    const chatInput = document.getElementById('notion-input');
    if (chatInput) {
        chatInput.textContent = '请针对我的薄弱环节生成一些专项练习题';
        // Trigger send
        const sendBtn = document.getElementById('tool_submit');
        if (sendBtn) sendBtn.click();
    }
}

/** Goal planning from input */
async function planGoalFromInput() {
    const input = document.getElementById('tpg-goal-input');
    if (!input || !input.value.trim()) return;
    const goal = input.value.trim();
    input.value = '';
    // Show loading
    const container = document.getElementById('tower-plan-content');
    if (container) container.innerHTML = '<div class="tower-loading">AI 正在分析目标并规划路径...</div>';
    // Call API
    try {
        const res = await fetch('/api/learning-path/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: currentUser?.id, forceRefresh: true, goal })
        });
        if (res.ok) {
            await refreshLearningPath(true);
            renderTowerPlanTab();
        } else {
            if (container) container.innerHTML = '<div class="tower-error">规划失败，请重试 <button class="tower-error-retry" onclick="renderTowerPlanTab()">重试</button></div>';
        }
    } catch (e) {
        if (container) container.innerHTML = '<div class="tower-error">网络错误，请重试 <button class="tower-error-retry" onclick="renderTowerPlanTab()">重试</button></div>';
    }
}
```

- [ ] **Step 6: Wire pipeline status updates to mini pipeline**

In the existing `subscribeToAgentBus()` function (around line 5227), add updates for the mini pipeline:

```js
// In the agent_step handler, also update mini pipeline
const tmpFlow = document.getElementById('tmp-flow');
if (tmpFlow && agentCatalog) {
    const allAgents = _towerFlattenAgents();
    tmpFlow.innerHTML = allAgents.map(a =>
        `<span class="tmp-node ${towerAgentStatus[a.id] || 'idle'}">${a.name}</span>`
    ).join('');
}
```

- [ ] **Step 7: Test all tabs**

Verify:
- Tab 1 renders status cards and weakness alerts (based on radarSnapshot data)
- Tab 2 shows persona grid, strategy pills, slider, injector
- Tab 3 shows goal input + existing path tasks
- Clicking persona card writes to localStorage
- Clicking inject writes to localStorage
- Tab switching preserves state
- Empty state renders when no learning path data
- Loading state shows spinner text
- Error state shows retry button

- [ ] **Step 8: Commit**

```bash
git add css/agent-tower.css html/index.html js/index.js
git commit -m "feat(tower): 3-tab interactive control tower with real API wiring"
```

---

### Task 5: Inline Tower Pipeline Visual (Compact) in Status Tab

**Files:**
- Modify: `js/index.js` (event-driven update of mini pipeline)

- [ ] **Step 1: Add live updates**

In `subscribeToAgentBus()`, for the `agent_step` handler, refresh the mini pipeline nodes:

```js
function updateMiniPipeline() {
    const tmpFlow = document.getElementById('tmp-flow');
    if (!tmpFlow || !agentCatalog) return;
    const allAgents = _towerFlattenAgents();
    tmpFlow.innerHTML = allAgents.map(a =>
        `<span class="tmp-node ${towerAgentStatus[a.id] || ''}">${a.name}</span>`
    ).join('');
}
```

Call `updateMiniPipeline()` from the agent_step subscriber and also from `initAgentTower()`.

- [ ] **Step 2: Commit**

```bash
git add js/index.js
git commit -m "feat(tower): live mini pipeline in status tab"
```

---

### Task 6: New API — POST /api/learning-path/goal

**Files:**
- Create: `app/api/learning_path_goal.py` (or modify existing learning_path router)

- [ ] **Step 1: Add the goal-based path generation endpoint**

If using the existing `app/api/learning_path.py`, add this route:

```python
@router.post('/goal')
async def generate_path_from_goal(
    request: GoalPathRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a learning path from a free-text user goal.
    Uses the same LLM pipeline as the regular path generation,
    but seeds the prompt with the user's specific goal.
    """
    analytics = await build_student_analytics(request.user_id, db)
    path_data = await generate_path_for_user(
        request.user_id, analytics, db,
        force_refresh=True,
        user_goal=request.goal  # injected into LLM prompt
    )
    return path_data
```

Add the request model:
```python
class GoalPathRequest(BaseModel):
    user_id: int
    goal: str
```

Update the backend `generate_path_for_user` to accept an optional `user_goal` parameter and inject it into the LLM prompt.

- [ ] **Step 2: Frontend update — use new endpoint in planGoalFromInput**

Modify `planGoalFromInput()` to use the new endpoint:

```js
async function planGoalFromInput() {
    const input = document.getElementById('tpg-goal-input');
    if (!input || !input.value.trim()) return;
    const goal = input.value.trim();
    input.value = '';
    const container = document.getElementById('tower-plan-content');
    if (container) container.innerHTML = '<div class="tower-loading">AI 正在分析目标并规划路径...</div>';
    try {
        const res = await fetch('/api/learning-path/goal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser?.id, goal })
        });
        if (res.ok) {
            await refreshLearningPath(true);
            renderTowerPlanTab();
        } else {
            if (container) container.innerHTML = '<div class="tower-error">规划失败 <button class="tower-error-retry" onclick="renderTowerPlanTab()">重试</button></div>';
        }
    } catch (e) {
        if (container) container.innerHTML = '<div class="tower-error">网络错误 <button class="tower-error-retry" onclick="renderTowerPlanTab()">重试</button></div>';
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add app/api/learning_path.py js/index.js
git commit -m "feat(api): POST /api/learning-path/goal for goal-based path generation"
```

---

## Verification

1. **End-to-end test**: Start the dev server, open index.html
2. **Radar**: Canvas renders with enhanced glassmorphism glow effect, dimension list shows below with progress bars, click dimension to expand insight
3. **Tower**: Starts collapsed with float button visible, click opens 3-tab panel, each tab renders correct content, control actions persist to localStorage + API
4. **Learning Path**: Node cards render with correct status colors, progress bar animates, capability grid shows in 2 columns, empty state renders when no data
5. **API**: `POST /api/learning-path/goal` accepts goal text and returns path data
6. **No regressions**: Chat still works, profile still loads, agent pipeline still runs
