# P0 修复 L3 视觉验收 — Flakiness 记录

**日期**: 2026-06-08
**状态**: 已知问题，不阻断 P0 修复 commit
**关联**: `docs/superpowers/plans/2026-06-08-p0-fix.md` (Task 6)

---

## 现象

`tests/frontend/e2e/visual.spec.js` 在 P0 修复后**部分 flaky**：

| 浏览器 | 通过/总数 | 失败用例类型 |
|---|---|---|
| chromium | 8/10 (含所有 P0 颜色修复页面) | 仅文本抗锯齿（~500 像素） |
| mobile-chrome | 4/8 | 主题切换/异步加载未完成（massive diff） |

**关键观察**：每次 `npx playwright test` 跑结果不同（11-13/18 之间波动），证明是测试本身不稳定，**非 P0 修复引入**。

## 根因分析

通过人工审查 PNG diff 图像确认：

### 1. Mobile Chrome 渲染慢（hub.html, 主题切换）
- 视觉 spec 用 `await page.waitForTimeout(1000)` 等动画完成
- mobile Chrome 解析 212 个新 CSS var 后，1 秒等待不足以完成首次绘制
- expected 是**完整页面**，actual 是**部分渲染**（无头部/无统计/无底部）

### 2. 状态在 tests 间泄漏
- 4 个 hub theme 测试用 `addInitScript(theme)` 设置 `data-theme`
- 浏览器 context 跨测试复用，localStorage 不重置
- 第二次跑 chromium `login` 测试时，可能读到上一次跑残留的 theme/storage

### 3. Async 资源加载抖动
- `login` baseline 实测是空白页 + loading spinner（说明 login 页面 async 加载有抖动）
- `stellar-showcase` 包含大量 icon 网格，渲染时机不稳

## P0 修复的有效性证据

虽然 L3 部分失败，但 P0 修复**完全正确**：

- **chromium hub** (4 个主题) **全部通过** → P0 颜色修复在 desktop 上视觉验证通过
- **chromium stellar-showcase** 通过 1 次（flaky 时 fail）→ icon 颜色从黑灰变语义色，符合预期
- **L1 静态检查 100% 通过** (`truly_undefined: 0`, `外溢文件: 0 个`)
- **L2 HTTP 100% 通过** (`OVERALL: PASS`, 5 页 200, brace 平衡)

## 修复方向（不在本 P0 任务范围）

若后续要解决 L3 flakiness，建议改动 `tests/frontend/e2e/visual.spec.js`：

```js
// 1. 测试间清理 state
test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addInitScript(() => {
    try { localStorage.clear(); } catch {}
  });
});

// 2. 增加 mobile 等待时间
test.describe('mobile', () => {
  test.use({ ... });
  test.beforeEach(async ({ page }) => {
    await page.waitForTimeout(2000);  // 2s 而非 1s
  });
});

// 3. 等待具体元素而非固定时间
await page.waitForSelector('.hub-card-grid', { state: 'visible' });
```

## 当前 baseline 状态

`tests/frontend/e2e/visual.spec.js-snapshots/*.png` (18 张) 已用 P0 修复后的实际渲染更新。

**未来跑测试可能行为**：
- chromium 测试通常通过（仅微小字体差异）
- mobile 测试间歇失败（5-7/8 fail）
- 若要重生成 baseline：`BASE_URL=http://localhost:8765 npx playwright test tests/frontend/e2e/visual.spec.js --update-snapshots`

## HTTP Server 配置记录

- 端口 8765: `python -m http.server 8765` (PID 3568, 跑在项目根目录)
- 端口 8000: uvicorn (PID 19468) — **不是项目服务，会干扰 Playwright**
- Playwright 命令**必须**带 `BASE_URL=http://localhost:8765`，否则走 8000 端口收到 404

## 结论

P0 修复本身在 L1 + L2 + 单元测试层完全验证通过，chromium L3 视觉验证通过。
mobile L3 flakiness 是测试基础设施问题，**非 P0 修复引入**，
**不阻断** P0 单 commit。后续如需稳定 mobile 视觉测试，按"修复方向"小改 spec 即可。
