# Hub Section Separation Redesign

**Date:** 2026-08-06
**Status:** Approved
**Scope:** `css/hub-chrome.css` (and packaging mirror)

## Problem

Hub 页面用 `--chrome-border`（暗色 `rgba(255,255,255,0.10)`、亮色 `rgba(15,23,42,0.10)`）作为顶部导航栏、左侧栏、右侧面板三块之间的边界线。这些 1px 硬白线在深空背景上很突兀，破坏玻璃质感。

## Goal

替换硬边线为柔和玻璃感的悬浮面板效果，让功能板块通过阴影、内反光、背景色差三重组合自然区分，不出现任何硬直线。

## Design

### 顶部导航栏 (`.hub-navbar`)

**暗色主题**：
```css
box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
```

**亮色主题**：
```css
box-shadow:
    0 4px 20px rgba(15, 23, 42, 0.10),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
```

- 下方投影让导航栏"浮起"
- 顶部 1px 内反光模拟玻璃边沿高光

### 左侧侧边栏 (`.hub-sidebar`)

- 背景：比主区略深的玻璃色（`background: rgba(255, 255, 255, 0.03)` 暗色 / `rgba(15, 23, 42, 0.025)` 亮色）
- 右侧内边缘高光替代原 `border-right`：

**暗色**：
```css
box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.05);
```

**亮色**：
```css
box-shadow: inset -1px 0 0 rgba(15, 23, 42, 0.06);
```

### 右侧面板 (`.hub-right-panel`)

- 与侧边栏对称，背景略深
- 左侧内边缘高光替代原 `border-left`：

**暗色**：
```css
box-shadow: inset 1px 0 0 rgba(255, 255, 255, 0.05);
```

**亮色**：
```css
box-shadow: inset 1px 0 0 rgba(15, 23, 42, 0.06);
```

### 顺手清理

- `--chrome-border` 和 `--chrome-border-2` 变量移除（已无人引用）
- `backdrop-filter` / 卡片样式不动

## 实现

只改两处文件：
- `css/hub-chrome.css`
- `packaging/app_payload/css/hub-chrome.css`

## 验收

- 顶部导航栏下方有柔和阴影，与内容区明显分层
- 侧边栏和右侧面板通过内反光区分，无硬边线
- 暗色和亮色主题下效果一致
- 其他卡片样式无视觉变化