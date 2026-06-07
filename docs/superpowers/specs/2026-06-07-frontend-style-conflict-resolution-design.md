# 前端样式冲突解决方案 — 设计

**日期**: 2026-06-07
**作者**: Claude (brainstorming)
**状态**: 待用户审阅
**范围**: 前端 CSS/HTML 加载层面的样式冲突

---

## 1. 背景与目标

在审视 [Kuromi](c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main) 项目前端代码时，发现若干明确可重现的样式冲突来源：

1. 登录 / 注册页错误加载 `teacher.css`，会把教师页的 37KB 组件样式下放到认证页
2. 13 个 HTML 用 Tailwind CDN 运行时，1 个用本地编译版，加载方式不统一
3. 至少 11 个 CSS 文件重复定义 `body { }`，6+ 个重复定义 `* { }`，靠"加载顺序"决定样式属于脆弱设计
4. 4 个孤儿 CSS 文件（2 个 hub 变体 + 2 个 .backup），共约 270KB 死代码

**目标**：用"三层职责 + 加载顺序单一来源"重整 CSS 加载，消除"靠先后顺序决定样式"的脆弱性，并清理历史残留。

**不在范围**（后续专项处理）：
- 把所有硬编码颜色统一替换为 `oklch` / `color-mix`（[css/index.css](css/index.css) 有 980 处）
- 全部组件类加 `app-` 前缀（属于"组件清理"里程碑）
- 新功能开发

---

## 2. 总体架构

### 2.1 三层职责划分

| 层级 | 职责 | 允许内容 | 禁止内容 |
|---|---|---|---|
| **基础层** | token、全局重置、字体、滚动条、背景层 | `:root`、`html`、`body`、`*` | 组件类、页面类 |
| **组件层** | 可复用的 UI 组件（按钮、卡片、表单、模态框） | `.app-btn` / `.app-card` / `.app-form-card` 等 | 页面专属类、`:root` |
| **页面层** | 单页专用样式 | `.page-*` / 页面语义化类（`hub-card`） | 全局选择器（`body` / `*` / `html`） |

### 2.2 加载顺序约定（所有 HTML 必须按此顺序）

```
1. tokens.css          →  设计 token (颜色变量、字体变量、间距)
2. tailwind.css         →  Tailwind 基础 + 工具类 (本地编译)
3. app-base.css         →  html/body/全局重置、字体、滚动条
4. app-bg.css           →  全局背景层 (.app-bg-layer、星星、星云)
5. components.css       →  核心组件: .app-btn / .app-input / .app-card / .app-form-card / .app-modal
6. components-*.css     →  细分组件 (cards / forms / glass / kanban / navbar / toast / ...)
7. animations.css       →  动画 keyframes 和 .fade-in / .stagger-*
8. <页面专属 CSS>       →  只能定义 .page-* 或页面语义化类
9. (按需) theme.css scheme-*.css
```

### 2.3 关键规则

1. 页面级 CSS（如 `hub.css`、`personal.css`）禁止再出现 `body {}` / `* {}` / `html {}`
2. 组件类应加 `app-` 前缀（已有体系：`app-form-card` / `app-input` / `app-btn` / `app-stat-card`）；本次范围内不要求所有现存非前缀类都迁移，迁移工作作为单独里程碑
3. 登录 / 注册页不加载 `teacher.css`（这是 page CSS，不该在 auth 页加载）
4. 加载顺序在任何 HTML 中必须保持一致，由静态检查脚本强制

---

## 3. 修复动作

按风险从低到高排列，每步独立 commit，便于回滚。

### 3.1 动作 1 · 删除孤儿 CSS 文件（零风险）

**目标文件**：

- [css/hub-perfect.css](css/hub-perfect.css)
- [css/hub-winmoes.css](css/hub-winmoes.css)
- [css/hub.css.backup](css/hub.css.backup)（204KB）
- [css/hub-refined.css.backup](css/hub-refined.css.backup)（64KB）

**验证**：执行 `grep -rn "hub-perfect\|hub-winmoes" --include="*.html" --include="*.js"`，确认无 HTML/JS 引用。注意 [js/hub.js:3974](js/hub.js#L3974) 中的 `hub-perfect-animations` 只是动态注入 `<style>` 标签的 ID 属性，不是文件依赖。

**Commit 粒度**：4 个文件可分 1-2 个 commit，message 用 `chore(cleanup): 删除 hub 相关孤儿 CSS 文件`。

### 3.2 动作 2 · 修正错误加载（低风险）

**修改**：

- [html/login.html:6](html/login.html#L6) 删掉 `<link rel="stylesheet" href="/css/teacher.css">`
- [html/register.html:6](html/register.html#L6) 删掉 `<link rel="stylesheet" href="/css/teacher.css">`
- 将 `tokens.css` 链接移到 `teacher.css` 之前（如果当前是反着的）

**验证**：

1. 刷新登录 / 注册页，确认按钮、输入框、卡片样式正常
2. 用浏览器 DevTools 检查没有未定义样式引用
3. 在 light / dark 主题间切换验证

**Commit message**：`fix(auth): 移除登录/注册页误加载的 teacher.css`

### 3.3 动作 3 · 统一 Tailwind 加载方式（中风险）

**问题**：13 个 HTML 用 `https://cdn.tailwindcss.com`（运行时 JIT，~2MB JS），1 个用本地 `/css/tailwind.css`，不一致。

**步骤**：

1. **审计**：在 14 个 HTML 中 grep Tailwind 工具类使用模式：
   ```bash
   grep -rhoE 'class="[^"]*\b(flex|grid|p-[0-9]|m-[0-9]|text-(xs|sm|base|lg|xl)|bg-[a-z]+-[0-9]+)\b[^"]*"' html/ | sort -u | head -50
   ```
2. **决策**：
   - 如果使用范围小（< 30 个独立类）：直接切本地 `/css/tailwind.css`
   - 如果使用范围大：保留 CDN 但改 `defer` 异步加载
3. **实施**：对每个 HTML 文件做相应修改
4. **验证**：用 [tests/](tests/) 下的 Playwright 测试登录 + Hub 页面布局无 regression

**Commit message**：`refactor(perf): 统一 Tailwind 加载方式为本地编译版` 或 `refactor(perf): Tailwind CDN 改为 defer 异步加载`

### 3.4 动作 4 · 审计全局选择器重复（中风险）

**问题**：11 个 CSS 文件含 `body { }`、6+ 个含 `* { }`、部分含 `html { }`，靠加载顺序决定样式。

**步骤**：

1. **盘点**：列出所有包含 `body { }` / `* { }` / `html { }` 的文件
   ```bash
   grep -lnE "^\s*(body|html|\*)\s*\{" css/*.css
   ```
2. **职责切分**：
   - `html` 的 `color-scheme` 保留在 [app-base.css:11](css/app-base.css#L11)
   - `body` 的 `margin/padding/font-family` 保留在 [app-base.css:15](css/app-base.css#L15)
   - `*` 的滚动条样式保留在 [app-base.css:144](css/app-base.css#L144)
3. **逐文件清理**：从其他 14+ 文件里删除这些全局选择器
4. **试点**：先在 1-2 个文件做试点（建议先改 [css/hub.css](css/hub.css)），验证主题切换、字体、滚动条无 regression
5. **推广**：试点通过后批量推广到其他文件
6. **验证**：所有 5 个高风险页面（login / register / hub / personal / teacher-dashboard）切换 light/dark 主题 + 3 种主题色

**涉及文件**（初判）：hub.css、personal.css、index.css、classroom.css、calendar.css、code.css、concept-analyzer.css、ai-pair-programming.css、architecture-blueprint.css、flow-meter.css、generation-preview.css、plant.css、components-glass.css 等。

**Commit message**：`refactor(css): 移除页面级 CSS 重复的全局选择器，统一到 app-base.css`

### 3.5 动作 5 · 组件类加 `app-` 前缀（高风险，单独里程碑）

**范围**：审计所有非前缀组件类（`.btn` / `.card` / `.input` / `.modal` / `.btn-primary` / `.card-title` 等），加 `app-` 前缀，配合现有 `app-form-card` / `app-input` / `app-btn` / `app-stat-card` 体系。

**不在本次范围**：本设计仅做"明确样式冲突"修复；`app-` 前缀清理属于后续"组件清理"专项，本次不实施。

---

## 4. 验证策略

### 4.1 L1 · 静态检查（每个 PR 必过）

**CSS 变量引用完整性**：

```bash
# 提取所有引用的变量
grep -rhoE 'var\(--[a-z0-9-]+' css/ | sed 's/var(//' | sort -u > /tmp/used.txt
# 提取所有定义的变量
grep -hoE '^\s*--[a-z0-9-]+' css/tokens.css | sed 's/^\s*--//' | sed 's/:.*//' | sort -u > /tmp/defined.txt
# 输出未定义引用
comm -23 /tmp/used.txt /tmp/defined.txt
```

期望输出为空。

**禁止页面级 CSS 出现全局选择器**：

```bash
grep -nE "^\s*(body|html|\*)\s*\{" css/hub.css css/personal.css css/index.css \
  css/classroom.css css/calendar.css css/code.css css/concept-analyzer.css \
  css/ai-pair-programming.css css/architecture-blueprint.css css/flow-meter.css \
  css/generation-preview.css css/plant.css css/components-glass.css
```

期望输出为空。

**HTML 加载顺序验证**：写一个 Python 脚本 ([scripts/verify_css_load_order.py](scripts/verify_css_load_order.py) 新建)，遍历所有 HTML，验证 `<link rel="stylesheet">` 顺序符合 2.2 节约定。

### 4.2 L2 · 渲染验证（动作 2/3 必做）

打开浏览器手动检查 5 个高风险页面：

- [html/login.html](html/login.html)、[html/register.html](html/register.html)
- [html/hub.html](html/hub.html)、[html/personal.html](html/personal.html)
- [html/teacher-dashboard.html](html/teacher-dashboard.html)

对每个页面：

1. 切换 light / dark 主题，验证颜色都跟随
2. 切换 3 种主题色（sakura / bamboo / star），验证 token 全部生效
3. 检查浏览器 console 无样式相关错误
4. 检查 [html/login.html](html/login.html) 上的 `Toast.show(...)` 通知样式无错位

### 4.3 L3 · 回归测试

- 复用 [tests/](tests/) 目录下的 Playwright 配置（[playwright.config.js](playwright.config.js)）
- 给 5 个高风险页面的核心 UI 状态各写一个 snapshot 测试：
  - 按钮颜色
  - 卡片背景
  - 主题切换后颜色变化
- 命名为 `tests/e2e/css-conflict-resolution.spec.ts`（新文件）

### 4.4 回滚预案

- 每个动作单独 commit，commit message 用 `refactor(cleanup): ...` 前缀
- 动作 1-3 风险低，失败可立即 `git revert <commit-sha>`
- 动作 4 风险中等，先在 1-2 个文件做试点再推广
- 动作 5 风险最高，单独里程碑推进

---

## 5. 范围外（明确不做）

为避免 scope creep，以下工作**不在本次设计范围**：

1. 全部硬编码颜色 → `oklch` / `color-mix` 替换
2. 全部组件类加 `app-` 前缀
3. 删除 [html/index.html](html/index.html) 和 [html/classroom.html](html/classroom.html) 之外的 legacy class（已有 [docs/superpowers/plans/2026-06-06-frontend-optimization-plan.md](docs/superpowers/plans/2026-06-06-frontend-optimization-plan.md) 在跟进）
4. 新功能开发

这些项目可作为后续 spec 单独规划。

---

## 6. 风险评估

| 动作 | 风险 | 影响范围 | 回滚难度 |
|---|---|---|---|
| 1 · 删孤儿文件 | 极低 | 无运行时影响 | 极简单（git revert） |
| 2 · 改 login/register | 低 | 2 个页面 | 简单（git revert） |
| 3 · Tailwind 统一 | 中 | 14 个页面 | 中等（需回退所有 HTML） |
| 4 · 全局选择器审计 | 中 | 14+ 个 CSS 文件 | 中等（commit 大但已分文件） |
| 5 · `app-` 前缀 | 高 | 全前端 | 高（涉及全部组件调用方） |

---

## 7. 验收标准

本次设计完成的标志：

- [ ] 4 个孤儿 CSS 文件已删除
- [ ] 登录 / 注册页不再加载 `teacher.css`
- [ ] Tailwind 加载方式统一（CDN 或本地，二选一）
- [ ] 所有页面级 CSS 文件不再含 `body { }` / `* { }` / `html { }`
- [ ] L1 静态检查全部通过
- [ ] L2 5 个高风险页面渲染验证通过
- [ ] L3 至少 1 个 Playwright snapshot 测试通过

---

## 8. 实施计划指针

完整实施计划将由 `writing-plans` skill 单独生成（在用户批准本 spec 后）。本 spec 仅定义设计。

---
