# 视觉验证报告 (2026-06-08)

## 验证范围
5 个高风险页面，在重排 link 顺序后渲染验证。

- `html/login.html`
- `html/register.html`
- `html/hub.html`
- `html/personal.html`
- `html/teacher-dashboard.html`

## 验证方法
- HTTP 服务: `python -m http.server 8765`（项目根目录）
- 浏览器: **未使用浏览器**，仅做静态检查。原因：本环境没有可用的 headless
  浏览器自动化工具 —— `agent-browser` CLI 未安装、Python `playwright` 未安装、
  Node `playwright` 也未安装。任务说明中已规定此情形下回退到静态检查。

静态检查由 `scripts/visual_verify_static.py` 执行，包含：

1. 对每个 HTML 页面发起 HTTP 请求，确认 200。
2. 用正则提取 `<link rel="stylesheet">` 列表，并按文档顺序验证 5 个核心 CSS
   (`tokens` → `app-base` → `app-bg` → `components` → `animations`) 的相对
   顺序正确。
3. 对该 HTML 引用的每个 CSS 文件发起 HTTP 请求，确认 200，并做花括号配对
   平衡检查（开括号数 == 闭括号数）。
4. `components.css` 本身是 `@import` 索引（无规则体），额外 curl 确认其
   引用的 11 个子 CSS 全部 200。

## 结果

| 页面 | HTTP 200 | 5-核心 CSS 顺序 | 引用 CSS 全部可达 | CSS 语法 (花括号) | 浏览器渲染 | Console 错误 |
|---|---|---|---|---|---|---|
| login.html | ✓ | ✓ | ✓ | ✓ | N/A (回退) | N/A |
| register.html | ✓ | ✓ | ✓ | ✓ | N/A (回退) | N/A |
| hub.html | ✓ | ✓ | ✓ (10 个 CSS) | ✓ | N/A (回退) | N/A |
| personal.html | ✓ | ✓ | ✓ (11 个 CSS) | ✓ | N/A (回退) | N/A |
| teacher-dashboard.html | ✓ | ✓ | ✓ (6 个 CSS) | ✓ | N/A (回退) | N/A |

### 关键 CSS 可达性（任务 7 个核心）
- `tokens.css`: 200
- `app-base.css`: 200
- `app-bg.css`: 200
- `components.css`: 200（@import 索引，11 个子文件均 200）
- `hub.css`: 200
- `personal.css`: 200
- `teacher.css`: 200

### 各页面 `<link rel="stylesheet">` 实际顺序

**login.html** / **register.html** (相同):
1. /css/tokens.css
2. /css/app-base.css
3. /css/app-bg.css
4. /css/components.css
5. /css/animations.css

**hub.html**:
1. /css/tokens.css
2. /css/app-base.css
3. /css/app-bg.css
4. /css/components.css
5. /css/animations.css
6. /css/loading.css
7. /css/mascot.css
8. /css/search-command.css
9. /css/onboarding.css
10. /css/hub.css

**personal.html**:
1. /css/tokens.css
2. /css/tailwind.css
3. /css/app-base.css
4. /css/app-bg.css
5. /css/components.css
6. /css/animations.css
7. /css/loading.css
8. /css/hub.css
9. /css/personal.css
10. /css/notifications.css
11. /css/mascot.css

**teacher-dashboard.html**:
1. /css/tokens.css
2. /css/app-base.css
3. /css/app-bg.css
4. /css/components.css
5. /css/animations.css
6. /css/teacher.css

### 静态分析（脚本输出汇总）
所有 5 个页面的 `expected_core_ok` / `order_ok` / `css_all_ok` 均为 `True`，
脚本最终输出 `OVERALL: PASS`。

| CSS 文件 | 开括号 | 闭括号 | 平衡 |
|---|---|---|---|
| tokens.css | 23 | 23 | ✓ |
| app-base.css | 44 | 44 | ✓ |
| app-bg.css | 21 | 21 | ✓ |
| components.css | 0 (仅 @import) | 0 | ✓ |
| animations.css | 102 | 102 | ✓ |
| loading.css | 35 | 35 | ✓ |
| mascot.css | 285 | 285 | ✓ |
| search-command.css | 18 | 18 | ✓ |
| onboarding.css | 17 | 17 | ✓ |
| hub.css | 628 | 628 | ✓ |
| tailwind.css | 599 | 599 | ✓ |
| personal.css | 1047 | 1047 | ✓ |
| notifications.css | 0 (仅注释) | 0 | ✓ |
| teacher.css | 193 | 193 | ✓ |

`components.css` 是 import 索引、`notifications.css` 是占位注释文件
（样式已迁移至 `js/notifications.js`），都是预期行为，不算异常。

## 截图
无浏览器，因此无截图。

## 结论
**通过 (回退路径)** —— 5 个高风险页面的 CSS 链接顺序、引用完整性、目标 CSS
可达性、CSS 语法平衡性 全部通过。

**未覆盖的部分**：实际像素级渲染、字体加载、动画播放、动态样式（如 Alpine
x-data 初始化后的样式）未在浏览器中验证。建议后续在有 Playwright /
agent-browser 的环境补一次真正的视觉回归测试。

**未发现的问题**：
- 没有任何 404 CSS。
- 没有任何 CSS 文件花括号不配对。
- 5 个核心 CSS 在所有 5 个页面中保持预期顺序：
  `tokens` → `app-base` → `app-bg` → `components` → `animations`。

执行人: 实施此任务的 subagent
日期: 2026-06-08
