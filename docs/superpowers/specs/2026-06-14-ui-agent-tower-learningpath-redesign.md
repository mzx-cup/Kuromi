# UI Redesign: 6D Radar, Agent Control Tower 2.0, Learning Path

## Overview

Three interconnected UI improvements to transform the Hachiware learning experience:
1. **6D Knowledge Radar** — visual refresh to glassmorphism style
2. **Agent Control Tower 2.0** — from read-only monitor to interactive console
3. **Learning Path** — card-based layout restructure

All three share a unified design language: glassmorphism, blue-to-purple gradient accents, light shadows, and clear visual hierarchy.

---

## 1. 6D Knowledge Radar — Glassmorphism Refresh

### Current Problems
- Canvas rendering is functional but visually dated (flat colors, no glass effect)
- Tooltip-based dimension details are undiscoverable
- No way to interact with individual dimensions

### Design
- **Glassmorphism container**: `.glass-radar-wrap` gets enhanced with `backdrop-filter: blur(20px)`, subtle border, and semi-transparent background
- **Canvas rendering upgrade**:
  - Softer gradient fill (blue→purple at 15% opacity)
  - Glow effect on data polygon edges
  - Dimension labels styled to match glass theme
- **Dimension list below radar**: Each of the 6 dimensions rendered as a row with:
  - Dimension name + score percentage
  - Mini progress bar (gradient fill)
  - Click to expand AI-generated short insight
- **Smooth transitions**: Score changes animate with 0.6s ease-out

### Data Source
- Existing `towerRadarSnapshot.radar` (from SSE `profile_updated` events)
- Fallback: legacy `profile` object → `mapProfileToScore()`

### Files to Modify
- `css/index.css` — `.glass-radar-wrap` styles, new dimension list styles
- `js/index.js` — `renderRadarChart()` visual upgrades, new `renderRadarDimensionList()`
- `css/tokens.css` — potential new glass-effect tokens

---

## 2. Agent Control Tower 2.0 — Interactive Console

### Core Philosophy
Transform from passive monitor (user can only watch) to active control console (user can direct). Every UI element must have a real backend effect.

### Layout
- Default: **hidden**, right-side floating trigger button (`#tower-float-btn`)
- Click trigger: slides in `#track-a-container` from right (400px wide, full height)
- Three-tab structure: [实时学情] [教学调控] [任务编排]
- Close button or click outside to dismiss

### Tab 1: 实时学情 (Real-time Learning Status)

**Purpose**: Make AI's analysis visible and actionable.

| UI Element | Visual | Backend Action |
|-----------|--------|----------------|
| Current status cards | Focus %, study time, current topic, mastery bar | Reads from `towerRadarSnapshot` + `localStorage` study minutes |
| Mini 6D radar | Small canvas radar (reuse `renderRadarChart`) | Same data as main radar |
| Weakness alerts | List of weak points with action buttons | Reads from portrait API `weakness` field |
| "标记为已掌握" button | Button on each weakness | `POST /api/profile/portrait/update` — sets topic mastery higher |
| "生成专项练习" button | Button on each weakness | Sends tailored prompt to `/api/v2/chat/stream` |
| "换个方式讲解" button | Button on each weakness | Switches teacher persona in current session |

### Tab 2: 教学调控 (Teaching Control)

**Purpose**: Let user control how AI teaches.

| UI Element | Visual | Backend Action |
|-----------|--------|----------------|
| Teacher persona selector | 4 avatar cards: 陈默/林文/周然/严正 | Writes to `localStorage` + `POST /api/memories` (type: preference) |
| Difficulty slider | Range slider: 简单 ←●→ 困难 | `POST /api/profile/portrait/update` → `difficulty_pref` field |
| Teaching strategy | 4 pills: 自动/讲解/练习/苏格拉底 | Changes LLM system prompt template for next call |
| Knowledge injector | Input field + [注入] button | `POST /api/memories` (type: interest/goal), ProfilerAgent reads it |
| Injected tags list | Removable tag pills | Delete from localStorage + memories API |

**Real effect flow**: When user changes teacher persona to "林文", the next `/api/v2/chat/stream` call injects Lin Wen's socratic system prompt. When difficulty slider moves, PlannerAgent uses the stored `difficulty_pref` to select content level.

### Tab 3: 任务编排 (Task Planning)

**Purpose**: Goal-driven learning with AI breakdown.

| UI Element | Visual | Backend Action |
|-----------|--------|----------------|
| Goal input | Text input + [AI 自动拆解] button | `POST /api/learning-path/generate` with goal context |
| Task list | Card per day/node with status icon and progress bar | Reads from `GET /api/learning-path/current` |
| "继续学习" button | Per-task action | Navigates chat context to that topic |
| "标记已完成" button | Per-task action | `POST /api/learning-path/nodes/evaluate` |
| "调整日期" button | Per-task action | Simple date picker → update node metadata |
| Overall progress bar | Gradient bar with percentage | Computed from node completion status |
| "重新规划" button | Bottom action | Force-refresh `POST /api/learning-path/generate` |

### States & Edge Cases

| State | Behavior |
|-------|----------|
| **Loading** | Skeleton shimmer for each tab content area |
| **Empty** (no data yet) | Friendly empty state: "开始学习后，AI 会自动分析你的学情" |
| **Error** (API failure) | Retry button + "数据加载失败" message |
| **Offline** | Use last cached data from localStorage |
| **Tab switch** | Preserve state, no re-fetch unless data is stale (>30s) |
| **Tower hidden** | Stop auto-refresh intervals; resume on open |

### Files to Modify/Create
- `css/agent-tower.css` — complete rewrite for tab layout
- `html/index.html` — restructure `#track-a-container` with tab markup
- `js/index.js` — tower-related functions, new tab logic
- `js/agent-bus.js` — may need new event types for control actions

### API: New Endpoint Needed
- `POST /api/learning-path/goal` — `{ userId, goal: string }` → generates path from a free-text goal (extends existing `generate` logic)

---

## 3. Learning Path — Card-Based Layout Restructure

### Current Problems
- Dense text, poor visual hierarchy
- Node status not immediately scannable
- Capability analysis is a plain list
- Overall cramped feel

### Design
- **Node cards** replace existing `path-analysis-goals` list:
  - Each node is a card with: status badge (🟢/🟡/⚪), topic name, progress bar, mastery %, action button
  - Completed nodes: muted style with checkmark
  - In-progress node: highlighted with primary color left border
  - Locked nodes: greyed out with lock icon
  - Cards have hover lift effect (translateY -2px, subtle shadow)
- **Capability grid**: 3×2 card grid replacing the dimension list
  - Each card: icon + label + short analysis text
  - Hover: accent left border
- **Progress section**: Full-width gradient bar with clear stat labels
- **Spacing**: increased padding/margins, more breathing room
- **Responsive**: stacked layout on narrow screens

### No Data Logic Changes
- Same data structures (`currentPath`, `capabilityAnalysis`)
- Same API calls (`GET /api/learning-path/current`, `POST /api/learning-path/generate`)
- Pure CSS/HTML restructuring

### Files to Modify
- `css/index.css` — rewrite `.path-analysis-*` classes for card layout
- `html/index.html` — update learning path section markup
- `js/index.js` — `renderPathTree()` modifications for new card HTML

---

## Implementation Order

1. **Learning Path UI** (pure CSS/HTML — lowest risk, quickest win)
2. **6D Radar** (canvas + CSS — moderate)
3. **Control Tower 2.0** (new functionality — highest complexity)

---

## Verification

1. **Learning Path**: Visual check — cards render correctly, status colors accurate, progress bar animates
2. **6D Radar**: Canvas renders with new style, dimension list shows correct scores, click expands insight
3. **Control Tower**:
   - Tab switching works
   - Each control action produces correct API call (verify via network tab)
   - Default hidden state works
   - Loading/empty/error states render
   - Teacher persona change reflects in next chat response
   - Goal input → path generation flows end-to-end
