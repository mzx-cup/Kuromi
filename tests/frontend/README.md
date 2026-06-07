# 星识 Star-Learn 前端自动化测试体系

## 目录

1. [测试金字塔 — 为什么需要分层测试](#1-测试金字塔)
2. [第一层：单元测试 (Unit Tests)](#2-第一层单元测试)
3. [第二层：冒烟测试 (Smoke Tests)](#3-第二层冒烟测试)
4. [第三层：无障碍测试 (Accessibility Tests)](#4-第三层无障碍测试)
5. [第四层：视觉回归测试 (Visual Regression)](#5-第四层视觉回归测试)
6. [CI/CD 集成](#6-cicd-集成)
7. [日常开发工作流](#7-日常开发工作流)

---

## 1. 测试金字塔

```
            ╱ 视觉回归 ╲          ← 少量，慢，检测像素级变化
           ╱  无障碍审计 ╲         ← 中量，检测 WCAG 合规
          ╱    冒烟测试    ╲        ← 覆盖全部页面，验证可加载
         ╱     单元测试      ╲       ← 大量，快，验证 JS 逻辑正确性
        ─────────────────────────
```

**核心原则：**
- **越底层的测试越多、越快、越频繁运行**
- **越上层的测试越少、越慢，但覆盖真实用户场景**
- **每一层保护不同类型的问题，不可互相替代**

---

## 2. 第一层：单元测试

### 测什么？
纯 JavaScript 逻辑，不依赖 DOM/网络/浏览器 API。本项目覆盖：
- `toast.js` — 通知系统的创建、关闭、XSS 防护、定时器
- `auth.js` — Token 管理、登录态验证、角色判断

### 为什么不测 DOM 交互？
DOM 交互应在上层 E2E 中测试——单元测试用 `jsdom` 模拟 DOM，但模拟 ≠ 真实浏览器。单元测试专注于**输入→输出的纯逻辑验证**。

### 用什么工具？
**Vitest** — 兼容 Jest API，原生 ESM 支持，内置覆盖率。

### 关键测试用例设计思路

**Toast 测试 (15 个用例):**

| 用例 | 验证什么 | 为什么重要 |
|------|----------|------------|
| API 存在性 | `window.Toast` 挂载了所有方法 | 确保模块加载正确 |
| show() 创建 DOM | toast 元素挂载到 `.app-toast-container` | 验证核心渲染路径 |
| 五种类型 | info/success/error/warning/mascot 各异 | 类型决定视觉表现 |
| 自动关闭 | 3 秒后添加 `.app-toast--removing` 类 | 定时器逻辑不能有内存泄漏 |
| duration:0 | 不自动关闭 | 持久通知的边界条件 |
| dismiss() | 手动关闭触发移除动画 | 用户交互路径 |
| XSS 防护 | `<script>` 标签被转义 | **安全关键路径** |
| 操作按钮 | 回调触发 + toast 关闭 | 交互式通知 |
| 容器复用 | 多个 toast 共享一个容器 | DOM 结构正确性 |
| transitionend 移除 | 动画结束后从 DOM 删除 | 清理逻辑的两种路径 |
| 400ms fallback | transitionend 不触发时的兜底 | 防御性编程 |

**Auth 测试 (13 个用例):**

| 用例 | 验证什么 |
|------|----------|
| getToken/setToken | localStorage 读写 |
| isTokenValid 过期 | JWT exp 解析和比较 |
| isTokenValid 损坏 | 非法 token 不崩溃 |
| fetchMe 401 | 过期 token 自动清除 |
| 角色判断 | teacher/student 布尔值 |
| logout | 清除状态 + 跳转 |
| data-auth-role | DOM 元素按角色显示/隐藏 |

### 运行命令

```bash
# 安装依赖
npm install

# 运行所有单元测试
npm run test:unit

# 持续监听模式（开发时使用）
npm run test:unit:watch

# 生成覆盖率报告
npm run test:unit:coverage
# 报告位置: coverage/index.html
```

### 覆盖率目标

```
js/toast.js   → ≥ 90% (安全关键，每个分支都要覆盖)
js/auth.js    → ≥ 85% (核心认证逻辑)
js/theme.js   → ≥ 60% (大量 DOM 操作，建议在 E2E 中测试)
```

---

## 3. 第二层：冒烟测试

### 测什么？
**所有 30 个页面**是否都能正常加载，会不会报 JS 错误。

### 为什么重要？
29 个页面共享同一套 CSS/JS 基础层。修改 `tokens.css` 或 `components.css` 时，你可能只手动验证了 2-3 个页面，但实际可能让其他页面因 CSS 变量缺失而布局崩溃。**冒烟测试 30 秒跑完所有页面，立即发现破坏性变更。**

### 每页面验证项：
1. **HTTP 加载成功** — 页面可访问（不是 404）
2. **无 JS 异常** — 页面级 `pageerror` 事件和 `console.error` 都被捕获
3. **Toast 系统可用** — `window.Toast` 对象存在
4. **body 存在** — 最基础的 DOM 结构完整

### 专项验证：
- login.html 的 `app-form-card` 类已正确应用
- hub.html 的 `data-bg-unified="true"` 标记
- stellar-showcase.html 没有重复的 `data-layer.js`
- pixel-pet-game.html 保留了 `data-bg-preserve` 豁免

### 运行命令

```bash
# 启动开发服务器后运行
npm run test:e2e:smoke

# 或让 Playwright 自动启动服务器
npx playwright test tests/frontend/e2e/smoke.spec.js
```

---

## 4. 第三层：无障碍测试

### 测什么？
使用 **axe-core** 引擎对 5 个核心页面进行 WCAG 2.1 AA 级别自动化审计。

### 检测规则（axe-core 内置 100+ 条规则）：

| 规则类别 | 示例检测项 |
|----------|-----------|
| **颜色对比度** | 文字颜色与背景色的对比度 ≥ 4.5:1 (AA) |
| **键盘可访问** | 所有交互元素可通过 Tab 键到达 |
| **ARIA 属性** | role/aria-label 使用正确 |
| **表单标签** | 每个 input 有关联的 label |
| **图片 alt** | 所有 img 有 alt 文本 |
| **标题层级** | h1 → h2 → h3 不跳级 |
| **文档语言** | html 标签有 lang 属性 |
| **焦点指示** | 键盘焦点时有可见的 focus ring |
| **frame 标题** | iframe 有 title 属性 |
| **列表结构** | li 元素在 ul/ol 内 |

### 为什么 CI 中不阻塞非 critical 违规？
- 项目使用第三方组件（Alpine.js、Tailwind CDN），部分违规来自外部
- 暗色主题下的对比度问题是逐步修复的
- **只阻塞 `critical` 和 `serious` 级别的违规**，`moderate`/`minor` 记录日志但不失败

### 运行命令

```bash
npm run test:a11y
```

---

## 5. 第四层：视觉回归测试

### 原理
```
首次运行 (--update-snapshots)
  → 截图保存为基准 (tests/frontend/screenshots/*.png)

后续运行
  → 重新截图
  → 与基准逐像素对比
  → 差异像素 > 阈值 → 测试失败，生成差异图
```

### 测什么？
| 页面 | 截取方式 | 说明 |
|------|---------|------|
| login | 视口 | 关键 UI：表单卡片 + 星座背景 |
| hub | 整页 | 内容最丰富的页面，卡片最多 |
| settings | 视口 | 主题弹窗交互验证 |
| stellar-showcase | 整页 | 徽章网格，stagger 动画后状态 |

### 主题切换验证
- hub.html 在 4 种主题下各截一张图
- 验证**主题切换不会导致布局偏移**（元素不移动/不重叠）
- 验证**暗色主题文字仍可读**

### 为什么需要视觉回归？
CSS 是全局的。修改一个 `.app-card` 的 padding 可能影响 29 个页面中的 200+ 个卡片实例。**人的眼睛不可能每次改动都手动检查所有页面。**视觉回归用像素对比做到这一点，而且是自动的。

### 运行命令

```bash
# 首次：生成基准截图（需要人工确认截图正确后提交到 git）
npm run test:e2e:visual:update

# 后续：与基准对比
npm run test:e2e:visual
```

---

## 6. CI/CD 集成

### GitHub Actions 示例（概念配置）

```yaml
# .github/workflows/test.yml
name: Frontend Tests
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run test:unit -- --reporter=junit
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-coverage
          path: coverage/

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npm run test:e2e:smoke
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-screenshots
          path: tests/frontend/reports/

  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npm run test:a11y
```

### 提交前检查 (Pre-commit Hook)

```bash
# .git/hooks/pre-commit (手动安装或通过 husky)
npm run test:unit        # 30 秒内完成
npm run test:e2e:smoke   # 2 分钟内完成
```

---

## 7. 日常开发工作流

### 修改 CSS 变量时
```bash
# 1. 改 tokens.css
# 2. 跑冒烟测试验证所有页面
npm run test:e2e:smoke
# 3. 如果测试失败 → 检查具体页面 → 修复
# 4. 更新视觉回归基准
npm run test:e2e:visual:update
```

### 修改 JS 模块时
```bash
# 1. 先写/改单元测试
# 2. 跑单元测试确认失败/通过
npm run test:unit:watch
# 3. 改代码
# 4. 确认测试通过
# 5. 跑冒烟确认没有影响其他页面
npm run test:e2e:smoke
```

### 添加新页面时
```bash
# 1. 在 smoke.spec.js 的 ALL_PAGES 列表中加入新页面
# 2. 跑冒烟测试确认新页面正常
# 3. 加入视觉回归（如果是核心页面）
```

---

## 快速开始

```bash
# 1. 安装依赖（仅首次）
npm install
npx playwright install chromium

# 2. 跑所有测试
npm run test:all

# 3. 查看报告
npx playwright show-report tests/frontend/reports/playwright-html
npx vitest run --coverage && open coverage/index.html
```

---

## 文件结构

```
tests/frontend/
├── unit/
│   ├── toast.test.js        # Toast 通知系统 15 个测试用例
│   └── auth.test.js         # JWT 认证模块 13 个测试用例
├── e2e/
│   ├── smoke.spec.js        # 30 页面冒烟测试
│   └── visual.spec.js       # 视觉回归测试（4 核心页 + 4 主题变体）
├── a11y/
│   └── a11y.spec.js         # WCAG 2.1 AA 无障碍审计（5 核心页）
├── screenshots/             # 视觉回归基准截图 (git 追踪)
└── reports/                 # 测试报告 (gitignore)
```
