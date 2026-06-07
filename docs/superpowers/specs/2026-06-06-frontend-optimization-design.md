# Frontend Display Optimization Design

**Date:** 2026-06-06
**Status:** Approved
**Scope:** All pages except index.html and classroom.html (AI chat pages excluded)

## Overview

Systematic enhancement of the Star-Learn frontend across six systems: design tokens, component library, animation system, base layer, auth/intercept, and theme system. The project already has ~70% design maturity — this work is "last mile" integration, not a rewrite.

**Strategy:** Foundation → Showcase → Rollout (Approach C). Foundation hits all pages at once; showcase pages (5 key pages) validate patterns; remaining ~19 pages batch-migrated in 3 waves.

---

## Section 1: Foundation Layer

### 1A. Extended Design Tokens (tokens.css)

Add to existing 3-layer token system. No breaking changes.

**New spacing tokens:**
- `--space-3xl: 80px`
- `--space-section: 48px` (between sections)
- `--space-gutter: 24px` (page gutter)
- `--gap-xs/sm/md/lg` (flex/grid gaps)

**New z-index scale:**
- `--z-base: 0`, `--z-dropdown: 100`, `--z-sticky: 200`, `--z-overlay: 500`, `--z-modal: 1000`, `--z-toast: 1100`, `--z-tooltip: 1200`

**New semantic tokens:**
- `--surface-raised`, `--surface-sunken`, `--separator`, `--overlay-dim`, `--focus-ring`, `--font-mono`, `--radius-pill: 9999px`

**Refined shadows:**
- `--shadow-inset`, `--shadow-glow`, `--shadow-card-hover`, `--shadow-modal`, `--shadow-toast`
- All derived from `--_shadow-strength`

**Files changed:** `css/tokens.css` (+~40 lines)

### 1B. Unified Base Layer (app-base.css + app-bg.css)

- Firefox scrollbar support
- Focus-visible ring for keyboard a11y
- `.sr-only` screen-reader utility
- `@media (prefers-reduced-motion)` support
- Smooth background transition (0.6s crossfade between themes)
- Grid background pattern option for light themes
- Dark mode: shooting star animation
- Utility classes: `.app-container`, `.app-grid-2/3/4`, `.app-flex-row/col`, `.app-gap-xs/sm/md/lg/xl`, `.truncate/.truncate-2`, `.sr-only`, `.no-scrollbar`

**Files changed:** `css/app-base.css` (+~60 lines), `css/app-bg.css` (+~30 lines)

### 1C. Enhanced Animation System (animations.css)

**New entry animations:** slide-down, slide-left, slide-right, grow-in, fade-up

**New attention animations:** gentle-shake (error feedback), glow-pulse (CTA highlight), breathing (subtle scale loop), draw-attention (bounce + glow)

**Stagger system:** `.stagger > *` auto-delays children via `--stagger-delay: 60ms` and `--stagger-count: 10`

**Utility classes:** `.animate-once`, `.animate-infinite`, `.animate-delay-100/200/300/500`, `.duration-fast/normal/slow`

**Accessibility:** `@media (prefers-reduced-motion)` disables all animations.

**Files changed:** `css/animations.css` (from 98 → ~180 lines)

---

## Section 2: Component Library — Unified Card System

### 2A. Mascot/Kanban

Existing system is complete (mascot-core.js, mascot-panel.js, mascot.css, kanban.js). **Only change:** replace hardcoded colors in mascot.css with tokens.css variables for theme-aware rendering. No JS changes.

### 2B. Five Core Card Prototypes

All cards share `.app-card` base. Five prototypes cover all 29 pages:

| Prototype | Class | Structure | Covers (old classes) |
|-----------|-------|-----------|---------------------|
| **Stat** | `.app-stat-card` | icon + value + label + delta | stat-card, dd-stat, metric-panel, summary-card, cockpit-stat-card, hub-stat, progress-stat, dashboard-stat, teacher-stat, calendar-stat, flow-stat, quantum-metric |
| **Content** | `.app-content-card` | thumb + body(title+desc+meta) + actions | content-card, resource-card, class-card, exam-card, video-info-panel, player-shell, plant-info-panel |
| **Action** | `.app-action-card` | icon + title + desc | feature-card, func-card, overview-action-card, compact-card, pref-card, brief-card, dimension-card, option-btn |
| **Form** | `.app-form-card` | header + body(form fields) + footer | auth-card-inner, form-card, setting-card, modal-content (non-modal usage) |
| **Chart** | `.app-chart-card` | header + chart-body(canvas/svg) | chart-card, td-chart-box, flow-card, badge-card, plant-detail-card, main-card |

### 2C. Composable Variants

Each prototype accepts these modifiers: `.glass` (frosted), `.ghost` (transparent), `.interactive` (clickable + hover), `.prism` (corner decoration via clip-path), `.compact` (reduced padding).

Compatibility mapping layer in components.css maps all 30+ legacy class names to the new unified classes.

**Files changed:** `css/components.css` (+~300 lines, includes 5 card prototypes + variants + compatibility map)

### 2D. Button/Modal/Form Enhancements

**Button:** Add `.app-btn-outline`, `.app-btn-glass`, `.app-btn-link`, `.app-btn-loading`, `.app-btn-block`
**Modal:** Add `.app-modal-slide-up`, `.app-modal-fullscreen`, ESC close, focus trap, body scroll lock
**Form:** Add `.app-checkbox/.app-radio`, `.app-input-group` (prefix/suffix), `.app-input-password` (show/hide toggle), `.app-form-row`

---

## Section 3: Auth + Theme + Animation + Toast

### 3A. Auth Enhancements (auth.js)

- `data-auth-role="teacher|student|admin|guest|user"` attribute — auto show/hide elements by role
- `Auth.isTokenValid()` — decode JWT exp field, check expiration
- `Auth.onExpire(callback)` — register expiration callback
- On page load, if token expires within 5 min, attempt fetchMe() refresh; on failure redirect to login

**Files changed:** `js/auth.js` (+~40 lines)

### 3B. Theme Enhancements (theme.js)

**Import/Export:** `StarTheme.exportTheme(themeId)` downloads JSON; `StarTheme.importTheme(jsonFile)` imports with dedup. Buttons in theme modal.

**Custom Token Editor:** Expandable panel in theme modal with H/C/L sliders for brand color, semantic color previews, shadow strength slider. Real-time preview as sliders move. "Save as custom theme" button.

**Theme transition animation:** `data-theme-transitioning` attribute on `<html>` triggers 0.4s crossfade on color/background/border/shadow properties. Auto-cleared after transitionend.

**Files changed:** `js/theme.js` (+~150 lines)

### 3C. Animation Enhancements (animations.css)

See Section 1C. From 98 → ~180 lines total.

**Files changed:** `css/animations.css` (+~80 lines)

### 3D. Unified Toast System (toast.js)

Extract toast logic from mascot-core.js into standalone `js/toast.js`. Single engine, two call styles:

- `Toast.show(msg, 'success')` / `Toast.error(msg)` / `Toast.warning(msg)` / `Toast.info(msg)` — general business use
- `Toast.mascot(title, content)` — mascot-style notifications (preserves character icon and bubble style)

CSS: `.app-toast` base class + type variants + `.app-toast--mascot` for mascot visual identity.

mascot-core.js delegates to `window.Toast.mascot()` instead of its own inline toast code.

**Files changed:** `js/toast.js` (new, ~100 lines), `js/mascot-core.js` (-30 lines), `css/components.css` (+60 lines)

---

## Section 4: Showcase Pages

Five key pages transformed first to establish gold-standard patterns.

### 4A. Login

- `.auth-card-inner` → `.app-form-card`
- Form fields → `.app-input` + `.app-label`
- Login button → `.app-btn-primary.app-btn-block`
- Register link → `.app-btn-link`
- Card entry → `.scale-in` animation
- Error feedback → `Toast.error()`

**Changes:** ~30 lines HTML, 0 JS

### 4B. Hub (most complex page)

All five card prototypes used:
- Stats area → `.app-stat-card.glass` with stagger fade-up
- Feature nav (8 cards) → `.app-action-card.interactive` with stagger scale-in
- Course cards → `.app-content-card.glass.interactive` with stagger slide-up
- Charts → `.app-chart-card.glass` with fade-in
- Prism corners → `.app-card-prism` modifier

**Changes:** ~80 lines HTML, ~20 lines CSS, 0 JS

### 4C. Personal (cockpit)

- Top stats → `.app-stat-card.glass` horizontal row
- Progress chart → `.app-chart-card`
- Preference cards → `.app-action-card.compact`
- Data panels → `.app-content-card`
- Layout → `.app-grid-3` utility
- Number-counting animation on stat values

**Changes:** ~50 lines HTML, +15 lines JS

### 4D. Teacher Dashboard (Prism validation)

- Dashboard stats → `.app-stat-card.prism`
- Class cards → `.app-content-card.prism`
- Exam/resource cards → `.app-content-card.prism.compact`
- Charts → `.app-chart-card.prism`
- Quick actions → `.app-action-card.prism.interactive`
- Prism clip-path moved from inline to components.css

**Changes:** ~60 lines HTML, ~30 lines CSS, 0 JS

### 4E. Settings

- Setting groups → `.app-form-card` sections
- Toggles → `.app-toggle` (existing component)
- Input groups → `.app-input-group` (prefix/suffix)
- Token editor panel → embedded from theme.js
- Import/Export buttons → `.app-btn-outline`

**Changes:** ~40 lines HTML, +80 lines JS (theme.js panel)

---

## Section 5: Rollout Plan

After showcase validation, remaining ~19 pages batched in 3 waves.

### Wave 1 — Lightweight (6 pages)
Register, Courses, Calendar, Progress, Assessment, Video
Mostly class name swaps + entry animations.

### Wave 2 — Medium (7 pages)
Code, Socratic, Data-dashboard, Flow-meter, Plant, Teacher-class, Teacher-resources
Class swaps + preserve special containers (editor, chat area, canvas, ECharts).

### Wave 3 — Remaining + Cleanup (~6 pages)
Gen-preview, Teacher-exams, Course-detail, remaining pages, mascot.css token adaptation.

### Per-Page Checklist
1. Class name replacement (per Section 2 mapping table)
2. Add animation (stagger container + child entry animations)
3. Replace inline layout with utility classes (`.app-grid-*`, `.app-flex-*`)
4. Verify: light/dark mode, theme switch, mobile responsive

---

## Implementation Order

| Phase | Content | Files | Est. Lines |
|-------|---------|-------|------------|
| Foundation | tokens + base + bg + animations | 4 | +150 |
| Components | 5 card prototypes + variants + toast + button/modal/form | 1 | +300 |
| JS Enhance | auth + theme + toast + mascot token | 5 | +400 |
| Showcase | Login, Hub, Personal, Teacher-dashboard, Settings | 5 | +400 |
| Wave 1 | Register, Courses, Calendar, Progress, Assessment, Video | 6 | +180 |
| Wave 2 | Code, Socratic, Data-dashboard, Flow-meter, Plant, Teacher-class, Teacher-resources | 7 | +210 |
| Wave 3 | Gen-preview, Teacher-exams, Course-detail, rest, mascot token | ~6 | +150 |

**Total:** ~34 files, ~1,800 lines. All additive, no JS business logic changes.

---

## Exclusions

- `index.html` and `classroom.html` (AI chat pages) — not in scope
- No Live2D SDK changes
- No backend API changes
- No new dependencies
- No refresh token mechanism (backend not ready)
