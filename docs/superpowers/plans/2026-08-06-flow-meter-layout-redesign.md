# Flow-Meter Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `flow-meter.html` so three core KPIs (today focus minutes, flow score, deep focus rate) are visible above the fold, by removing the decorative hero orb, simplifying the session card, and tightening the bento grid.

**Architecture:** Pure HTML/CSS/JS markup change. No backend, no schema, no new dependencies. Three concerns: (1) HTML structure, (2) CSS layout/styles, (3) JS data binding. Each task delivers one concern and syncs byte-for-byte to `packaging/app_payload/`.

**Tech Stack:** HTML, CSS (with `oklch` color tokens), vanilla JS, ECharts. No build step.

---

## File Structure

| File | Responsibility |
|---|---|
| `html/flow-meter.html` | Page markup: KPI 3-card structure, simplified session card, hero removal |
| `css/flow-meter.css` | Layout: 3-column bento stats, KPI card styles, hero-only CSS deletion, responsive |
| `js/flow-meter.js` | New `updateKpiCards(data)` function reading `today.*` / `score` / `deepRatio` / `trend` / `recentHistory` |
| `packaging/app_payload/html/flow-meter.html` | Mirror of source |
| `packaging/app_payload/css/flow-meter.css` | Mirror of source |
| `packaging/app_payload/js/flow-meter.js` | Mirror of source |

---

## Task 1: Replace 4-card stats with 3 KPI cards in HTML

**Files:**
- Modify: `html/flow-meter.html:92-142` (the `<section class="fm-bento-stats">` block)

- [ ] **Step 1: Read the exact current markup**

Run: Read `html/flow-meter.html` lines 92-142.

- [ ] **Step 2: Replace the stats section**

In `html/flow-meter.html`, replace the entire `<section class="fm-bento-stats">…</section>` block (currently 4 cards: deep, focus, switch, score) with the new 3-card structure below.

Replacement block:

```html
        <!-- ===== Bento Grid ===== -->
        <div class="dd-bento">

            <!-- ROW A: 3 KPI cards -->
            <section class="fm-bento-stats">

                <article class="app-stat-card fm-kpi-card" data-key="focus" style="--ic: var(--info);">
                    <div class="dd-stat-head">
                        <div class="dd-stat-icon"><i data-lucide="clock-4"></i></div>
                        <div class="dd-stat-trend" id="kpi-focus-trend">—</div>
                    </div>
                    <div class="fm-kpi-value" id="kpi-focus-value">--:--</div>
                    <div class="fm-kpi-label">今日专注</div>
                    <div class="fm-kpi-bar">
                        <div class="fm-kpi-bar-fill" id="kpi-focus-fill" style="width: 0%;"></div>
                    </div>
                    <div class="fm-kpi-hint" id="kpi-focus-hint">目标 60 分钟</div>
                </article>

                <article class="app-stat-card fm-kpi-card" data-key="score" style="--ic: var(--brand-500);">
                    <div class="dd-stat-head">
                        <div class="dd-stat-icon"><i data-lucide="activity"></i></div>
                        <div class="dd-stat-trend" id="kpi-score-trend">—</div>
                    </div>
                    <div class="fm-kpi-value" id="kpi-score-value">0</div>
                    <div class="fm-kpi-label">心流指数</div>
                    <div class="fm-kpi-bar">
                        <div class="fm-kpi-bar-fill" id="kpi-score-fill" style="width: 0%;"></div>
                    </div>
                    <div class="fm-kpi-hint" id="kpi-score-hint">vs 近3天</div>
                </article>

                <article class="app-stat-card fm-kpi-card" data-key="deep" style="--ic: var(--success);">
                    <div class="dd-stat-head">
                        <div class="dd-stat-icon"><i data-lucide="zap"></i></div>
                        <div class="dd-stat-trend" id="kpi-deep-trend">—</div>
                    </div>
                    <div class="fm-kpi-value" id="kpi-deep-value">0%</div>
                    <div class="fm-kpi-label">深度专注率</div>
                    <div class="fm-kpi-bar">
                        <div class="fm-kpi-bar-fill" id="kpi-deep-fill" style="width: 0%;"></div>
                    </div>
                    <div class="fm-kpi-hint" id="kpi-deep-hint">本周均值 —</div>
                </article>

            </section>
```

- [ ] **Step 3: Verify the file parses**

Run: Open `html/flow-meter.html` in a text editor (or `head -150 html/flow-meter.html` in bash) and confirm:
- Line 92 area starts with `<!-- ===== Bento Grid ===== -->` followed by the new `<section class="fm-bento-stats">`.
- The new section has exactly 3 `<article class="fm-kpi-card">` elements.
- No leftover old IDs (`#deep-value`, `#focus-time`, `#switch-count`, `#flow-score`, `#trend-*`).

- [ ] **Step 4: Sync to packaging mirror**

Run:
```bash
cp html/flow-meter.html packaging/app_payload/html/flow-meter.html
diff -q html/flow-meter.html packaging/app_payload/html/flow-meter.html
```
Expected output: no diff (silent).

---

## Task 2: Simplify the session card in HTML

**Files:**
- Modify: `html/flow-meter.html:174-202` (the `.fm-card-session` block)

- [ ] **Step 1: Read the exact current session card markup**

Run: Read `html/flow-meter.html` lines 174-202.

- [ ] **Step 2: Replace the session card body**

Replace only the contents of `<article class="app-card dd-card fm-card-session">` (keep the article wrapper and the `<header class="dd-card-head">` with `<h3 class="dd-card-title">📅 本次会话</h3>`).

The `<div class="fm-session-grid">` should keep only two cells (开始时间 and 剩余时间). Use this exact replacement for the grid:

```html
                    <div class="fm-session-grid">
                        <div class="fm-session-cell">
                            <span class="fm-session-label">开始时间</span>
                            <span class="fm-session-value" id="session-start">--:--:--</span>
                        </div>
                        <div class="fm-session-cell">
                            <span class="fm-session-label">剩余时间</span>
                            <span class="fm-session-value fm-highlight" id="remaining-time">--:--</span>
                        </div>
                    </div>
```

The progress block (`<div class="fm-progress">…</div>`) and the `id="session-progress"` / `id="progress-label"` spans stay as-is.

- [ ] **Step 3: Verify no leftover placeholders**

Run: `grep -n "Python 数据结构\|目标时长\|学习内容" html/flow-meter.html`

Expected output: empty (no matches).

- [ ] **Step 4: Sync to packaging mirror**

Run:
```bash
cp html/flow-meter.html packaging/app_payload/html/flow-meter.html
diff -q html/flow-meter.html packaging/app_payload/html/flow-meter.html
```
Expected: no diff.

---

## Task 3: Remove hero article block from HTML

**Files:**
- Modify: `html/flow-meter.html:66-87` (the `<article class="app-chart-card fm-hero">` block)

- [ ] **Step 1: Read the exact hero block**

Run: Read `html/flow-meter.html` lines 65-90.

- [ ] **Step 2: Delete the hero block**

Delete from the `<!-- ===== Hero State Banner ===== -->` comment line (currently around line 65) through the closing `</article>` tag of the hero (currently around line 87). Do not touch any other surrounding markup.

Verify that the line immediately after the deleted block is `<!-- ===== Bento Grid ===== -->` (currently around line 89).

- [ ] **Step 3: Sync to packaging mirror**

Run:
```bash
cp html/flow-meter.html packaging/app_payload/html/flow-meter.html
diff -q html/flow-meter.html packaging/app_payload/html/flow-meter.html
```
Expected: no diff.

---

## Task 4: Add KPI card CSS and adjust bento stats to 3 columns

**Files:**
- Modify: `css/flow-meter.css:523-550` (the bento grid section block)

- [ ] **Step 1: Read the exact bento section CSS**

Run: Read `css/flow-meter.css` lines 523-560.

- [ ] **Step 2: Replace `.fm-bento-stats` grid columns from 4 to 3**

Find the existing `.fm-bento-stats { … grid-template-columns: repeat(4, 1fr); … }` block and change `repeat(4, 1fr)` to `repeat(3, 1fr)`. Keep `gap: 12px` and `margin-bottom: var(--space-md)`.

The `.fm-bento-charts`, `.fm-bento-info`, `.fm-bento-history` blocks below stay as-is (they remain 2-column / single-column).

- [ ] **Step 3: Add new KPI card styles**

Append the following block immediately after the existing `.fm-bento-history { … }` block (after line ~550):

```css
/* ============================================================
   KPI Card — Row 1 (3 large metric cards)
   ============================================================ */
.fm-kpi-card {
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 18px 22px 20px;
    min-height: 168px;
}
.fm-kpi-value {
    font-size: clamp(2.25rem, 4vw, 3.5rem);
    line-height: 1;
    font-weight: var(--font-bold);
    color: var(--text-heading);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
}
.fm-kpi-label {
    font-size: 13px;
    font-weight: var(--font-medium);
    color: var(--text-body);
    margin-top: -2px;
}
.fm-kpi-bar {
    height: 12px;
    background: color-mix(in oklch, var(--border-glass), transparent 30%);
    border-radius: var(--radius-pill);
    overflow: hidden;
    position: relative;
}
.fm-kpi-bar-fill {
    height: 100%;
    border-radius: var(--radius-pill);
    background: linear-gradient(90deg,
        color-mix(in oklch, var(--ic, var(--info)), transparent 20%),
        var(--ic, var(--info)));
    transition: width 1s var(--ease-out);
    box-shadow: 0 0 12px color-mix(in oklch, var(--ic, var(--info)), transparent 70%);
}
.fm-kpi-hint {
    font-size: 13px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
}
.fm-kpi-card .dd-stat-head {
    margin-bottom: 4px;
}
```

- [ ] **Step 4: Sync to packaging mirror**

Run:
```bash
cp css/flow-meter.css packaging/app_payload/css/flow-meter.css
diff -q css/flow-meter.css packaging/app_payload/css/flow-meter.css
```
Expected: no diff.

---

## Task 5: Delete hero-only CSS

**Files:**
- Modify: `css/flow-meter.css`

- [ ] **Step 1: Delete `.fm-hero` styles block**

Find the comment line `/* ============================================================` followed by `Hero State Banner — 当前专注状态大卡` (currently around line 339) and delete from that comment header through the closing `}` of the `.fm-hero` related rules.

Specifically delete the entire block from:
```
/* ============================================================
   Hero State Banner — 当前专注状态大卡
   ============================================================ */
.fm-hero {
   ...
}
.fm-hero::before {
   ...
}
… (everything up to and including the last .fm-hero* rule before the `/* Bento grid sections */` comment)
```

Do NOT delete `.fm-hero-bar` (it's the colored progress bar inside hero — it should also go). Delete every selector whose name starts with `.fm-hero` or `.hero-orb`. Verify by grepping after:

Run: `grep -n "\.fm-hero\|\.hero-orb" css/flow-meter.css`

Expected: no matches.

- [ ] **Step 2: Delete hero-only keyframes**

The hero orb uses these keyframes: `fm-pulse`, `fm-breathe`, `fm-orb-rotate`, `fm-orb-rotate-reverse`, `fm-state-underline`, `fm-grad-flow`, `fm-grad-underline`, `fm-chip-shine`. They are also referenced by other selectors (e.g. `.dd-status-dot` uses `fm-pulse`, `.dd-title-grad` uses `fm-grad-flow`, `.dd-eyebrow-chip` uses `fm-chip-shine`, etc.).

DO NOT delete keyframes that are referenced outside the hero. After deleting the hero rules, run:

Run: `grep -n "fm-pulse\|fm-breathe\|fm-orb-rotate\|fm-state-underline\|fm-grad-flow\|fm-grad-underline\|fm-chip-shine\|fm-bar-stripe\|fm-empty\|fm-tip-enter\|fm-draw" css/flow-meter.css | head -40`

For each keyframe, check if it's still referenced outside `.fm-hero*`/`.hero-orb*` selectors. Specifically:
- `fm-pulse` — still used by `.dd-status-dot` and `.fm-session-value.fm-highlight::before` — KEEP
- `fm-grad-flow` — used by `.dd-title-grad` — KEEP
- `fm-grad-underline` — used by `.dd-title-grad::after` — KEEP
- `fm-chip-shine` — used by `.dd-eyebrow-chip::before` — KEEP
- `fm-breathe`, `fm-orb-rotate`, `fm-orb-rotate-reverse`, `fm-state-underline` — only used by hero — DELETE

Delete the keyframes blocks for `fm-breathe`, `fm-orb-rotate`, `fm-orb-rotate-reverse`, `fm-state-underline`.

After deletion, run:
Run: `grep -n "fm-breathe\|fm-orb-rotate\|fm-state-underline" css/flow-meter.css`

Expected: no matches.

- [ ] **Step 3: Sync to packaging mirror**

Run:
```bash
cp css/flow-meter.css packaging/app_payload/css/flow-meter.css
diff -q css/flow-meter.css packaging/app_payload/css/flow-meter.css
```
Expected: no diff.

---

## Task 6: Adjust responsive breakpoints for 3-column stats and 2/3 + 1/3 charts

**Files:**
- Modify: `css/flow-meter.css` (the responsive section near the bottom)

- [ ] **Step 1: Read the current responsive media queries**

Run: Read `css/flow-meter.css` from the `/* ============================================================` followed by `Responsive` comment through the end of the file (around line 1080-1128).

- [ ] **Step 2: Update the 1100px breakpoint**

Find:
```css
@media (max-width: 1100px) {
    .fm-bento-stats { grid-template-columns: repeat(2, 1fr); }
    .fm-bento-charts { grid-template-columns: 1fr; }
    .fm-bento-info   { grid-template-columns: 1fr; }
    .fm-hero {
        grid-template-columns: auto 1fr;
        gap: 20px;
    }
    .fm-hero-bar-wrap {
        grid-column: 1 / -1;
    }
}
```

Replace the `.fm-hero` and `.fm-hero-bar-wrap` lines inside this block — they reference deleted styles. Since hero is gone, replace the whole block with:

```css
@media (max-width: 1100px) {
    .fm-bento-stats { grid-template-columns: repeat(3, 1fr); }
    .fm-bento-charts { grid-template-columns: 1fr; }
    .fm-bento-info   { grid-template-columns: 1fr; }
}
```

(KPI cards stay 3-column down to 1100px; charts stack vertically earlier to give the chart more horizontal room.)

- [ ] **Step 3: Update the 767px breakpoint**

Find:
```css
@media (max-width: 767px) {
    .fm-bento-stats { grid-template-columns: 1fr 1fr; }
    .fm-hero {
        padding: 18px;
        gap: 14px;
    }
    .fm-hero-orb {
        width: 56px;
        height: 56px;
    }
    .fm-session-grid {
        gap: 10px 14px;
    }
    .fm-stat {
        min-height: 120px;
        padding: 12px 14px;
    }
```

Replace the `.fm-hero*` references with nothing (they're deleted). Also update `.fm-bento-stats` to be 2-column so three KPI cards become a 2+1 wrap, and replace `.fm-stat` (no longer used) with `.fm-kpi-card`:

```css
@media (max-width: 767px) {
    .fm-bento-stats { grid-template-columns: 1fr 1fr; }
    .fm-session-grid {
        gap: 10px 14px;
    }
    .fm-kpi-card {
        min-height: 144px;
        padding: 14px 16px 16px;
    }
}
```

The last `.fm-bento-stats > article:nth-child(3)` would wrap alone on its own row (CSS grid auto-flow). Visually acceptable; no special rule needed.

- [ ] **Step 4: Verify no stale references**

Run: `grep -n "fm-hero\|hero-orb" css/flow-meter.css`

Expected: no matches.

- [ ] **Step 5: Sync to packaging mirror**

Run:
```bash
cp css/flow-meter.css packaging/app_payload/css/flow-meter.css
diff -q css/flow-meter.css packaging/app_payload/css/flow-meter.css
```
Expected: no diff.

---

## Task 7: Add updateKpiCards data binding

**Files:**
- Modify: `js/flow-meter.js`

- [ ] **Step 1: Read the existing updateStatsPanel**

Run: Read `js/flow-meter.js` lines 640-705 (the `updateStatsPanel` and `updateSessionPanel` functions).

- [ ] **Step 2: Add the new updateKpiCards function**

In `js/flow-meter.js`, insert the following new function immediately before the `function updateCharts()` function (currently around line 776). Find the line `// ============ chart refresh ============` and insert above it:

```javascript
// ============ KPI cards (Row 1) ============

function fmtStudyHM(mins) {
    var m = Math.max(0, parseInt(mins, 10) || 0);
    var h = Math.floor(m / 60);
    var r = m % 60;
    return h > 0
        ? h + ':' + String(r).padStart(2, '0')
        : String(r).padStart(2, '0') + ':00';
}

function trendBadgeText(trend) {
    if (!trend) return '—';
    if (trend.direction === 'up')   return '↑ +' + trend.change;
    if (trend.direction === 'down') return '↓ ' + trend.change;
    return '—';
}

function trendBadgeColor(trend) {
    if (!trend) return '';
    if (trend.direction === 'up')   return 'var(--success)';
    if (trend.direction === 'down') return 'var(--danger)';
    return '';
}

function weekStartIso() {
    var now = new Date();
    var day = now.getDay() || 7; // 0 = Sunday → 7
    var monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (day - 1));
    return monday.toISOString().slice(0, 10);
}

function weeklyAvgScore(analysis) {
    if (!analysis || !Array.isArray(analysis.recentHistory)) return null;
    var cutoff = weekStartIso();
    var samples = analysis.recentHistory.filter(function (it) {
        return it && typeof it.timestamp === 'string' && it.timestamp.slice(0, 10) >= cutoff;
    });
    if (!samples.length) return null;
    var sum = 0;
    for (var i = 0; i < samples.length; i++) {
        sum += parseInt(samples[i].score, 10) || 0;
    }
    return Math.round(sum / samples.length);
}

function updateKpiCards(data) {
    if (!data) return;
    var today = data.today || {};
    var study = parseInt(today.studyMinutes, 10) || 0;

    // 1) 今日专注
    var focusVal = document.getElementById('kpi-focus-value');
    if (focusVal) focusVal.textContent = fmtStudyHM(study);
    var focusFill = document.getElementById('kpi-focus-fill');
    if (focusFill) {
        var pct = Math.min(100, Math.round((study / 60) * 100));
        focusFill.style.width = pct + '%';
    }
    var focusHint = document.getElementById('kpi-focus-hint');
    if (focusHint) focusHint.textContent = '目标 60 分钟';

    // 2) 心流指数
    var scoreVal = document.getElementById('kpi-score-value');
    var score = parseInt(data.score, 10) || 0;
    if (scoreVal) scoreVal.textContent = score;
    var scoreFill = document.getElementById('kpi-score-fill');
    if (scoreFill) {
        scoreFill.style.width = Math.min(100, Math.max(0, score)) + '%';
    }
    // 心流指数辅助行 = 趋势徽章文字 (在右上 trend 徽章里已显示), 下方 hint 用近3天均值对照
    var scoreHint = document.getElementById('kpi-score-hint');
    if (scoreHint) {
        var t = data.trend;
        scoreHint.textContent = t
            ? ('近3天均值 ' + (t.previousPeriodScore || 0) + ' / 当前 ' + (t.currentPeriodScore || 0))
            : '—';
    }
    var scoreTrend = document.getElementById('kpi-score-trend');
    if (scoreTrend) {
        scoreTrend.textContent = trendBadgeText(data.trend);
        scoreTrend.style.color = trendBadgeColor(data.trend);
    }

    // 3) 深度专注率
    var deep = parseFloat(data.deepRatio) || 0;
    var deepVal = document.getElementById('kpi-deep-value');
    if (deepVal) deepVal.textContent = Math.round(deep) + '%';
    var deepFill = document.getElementById('kpi-deep-fill');
    if (deepFill) {
        deepFill.style.width = Math.min(100, Math.max(0, Math.round(deep))) + '%';
    }
    var deepHint = document.getElementById('kpi-deep-hint');
    if (deepHint) {
        var avg = weeklyAvgScore(data);
        deepHint.textContent = avg === null ? '本周均值 —' : ('本周均值 ' + avg + '%');
    }
    var deepTrend = document.getElementById('kpi-deep-trend');
    if (deepTrend) deepTrend.textContent = '—';
}
```

- [ ] **Step 3: Wire it into updateAllCards**

Find the existing `function updateAllCards(data)` (currently around line 788):

```javascript
function updateAllCards(data) {
    if (!data) { return; }
    updateStatsPanel(data);
    updateSessionPanel(data);
    updateStateIndicator(window.FocusAnalysis.getRealtimeState());
    updateCharts();
    updateTips(data.tips);
}
```

Replace with:

```javascript
function updateAllCards(data) {
    if (!data) { return; }
    updateStatsPanel(data);
    updateKpiCards(data);
    updateSessionPanel(data);
    updateStateIndicator(window.FocusAnalysis.getRealtimeState());
    updateCharts();
    updateTips(data.tips);
}
```

Keep `updateStatsPanel(data)` call as-is — it still updates the `#deep-value` ring, `#focus-time`, `#switch-count`, `#flow-score` (which the new HTML no longer has IDs for). Since these DOM nodes are gone, `updateStatsPanel` will silently no-op for those, which is fine. We can leave the function intact (it's small and defensive).

Actually — since the HTML no longer has those IDs, `updateStatsPanel` does nothing useful. To keep the file clean, replace the `updateStatsPanel(data);` line with `// updateStatsPanel removed: HTML IDs are gone in the new layout`.

Final replacement for `updateAllCards`:

```javascript
function updateAllCards(data) {
    if (!data) { return; }
    updateKpiCards(data);
    updateSessionPanel(data);
    updateStateIndicator(window.FocusAnalysis.getRealtimeState());
    updateCharts();
    updateTips(data.tips);
}
```

- [ ] **Step 4: Remove or leave the now-orphan updateStatsPanel function**

The `updateStatsPanel` function is no longer called by `updateAllCards`. Leave it in place (defensive; harmless). Do not delete — small risk of breaking if other code (e.g. tests, devtools) calls it.

- [ ] **Step 5: Sync to packaging mirror**

Run:
```bash
cp js/flow-meter.js packaging/app_payload/js/flow-meter.js
diff -q js/flow-meter.js packaging/app_payload/js/flow-meter.js
```
Expected: no diff.

---

## Task 8: Manual smoke test in browser

**Files:**
- (No file changes; verification only)

- [ ] **Step 1: Confirm backend is reachable**

Run: `curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/focus/analysis/1?range=7d`

Expected: `200`

If not 200, do not proceed — the user's running dev server is unreachable.

- [ ] **Step 2: Confirm the page loads**

Open `http://localhost:8000/html/flow-meter.html` in a browser. Confirm:

- [ ] No JavaScript errors in browser console (DevTools → Console).
- [ ] Three KPI cards render side-by-side above the fold.
- [ ] Each KPI shows: icon + trend badge at top, large number, label, progress bar, hint.
- [ ] Heart-flow waveform + time-of-day chart appear in Row 2 below the KPIs.
- [ ] Session card shows only "开始时间" and "剩余时间" + progress bar.
- [ ] Tips card shows up to 4 tips.
- [ ] History chart shows full-width with filter pills (今日/本周/本月).

- [ ] **Step 3: Verify KPI binding**

After ~3 seconds (the polling interval), the KPI numbers should reflect the API payload. Confirm:

- 今日专注: format `H:MM` or `MM:SS`, progress bar fills proportional to `studyMinutes / 60`.
- 心流指数: integer 0-100, progress bar matches the integer percentage.
- 深度专注率: integer percent, progress bar matches.

- [ ] **Step 4: Verify responsive**

In DevTools, toggle device toolbar:

- Width 1400px: 3 KPIs in row, charts in 2/3 + 1/3.
- Width 900px: 3 KPIs in row (still), charts stack vertically.
- Width 500px: KPIs wrap to 2-column (third wraps alone), everything single-column.

No horizontal scroll bars at any width.

- [ ] **Step 5: Verify mirror parity**

Run:
```bash
diff -q html/flow-meter.html packaging/app_payload/html/flow-meter.html
diff -q css/flow-meter.css packaging/app_payload/css/flow-meter.css
diff -q js/flow-meter.js packaging/app_payload/js/flow-meter.js
```
Expected: all three commands silent (no diff).