/**
 * 视觉回归测试 (Visual Regression Tests)
 *
 * 对核心页面进行截图对比，检测 UI 变更是否引入了意外的样式变化。
 *
 * 原理：
 *   1. 首次运行 → 生成基准截图 (baseline) 存入 tests/frontend/screenshots/
 *   2. 后续运行 → 将当前截图与基准截图逐像素对比
 *   3. 差异像素超过阈值 → 测试失败，生成差异图
 *
 * 运行:
 *   # 首次：生成基准截图
 *   npx playwright test tests/frontend/e2e/visual.spec.js --update-snapshots
 *
 *   # 后续：与基准对比
 *   npx playwright test tests/frontend/e2e/visual.spec.js
 *
 * 配置说明：
 *   - maxDiffPixels: 允许的最大差异像素数（0 = 完全不允许差异）
 *   - 建议对动画页面放宽到 ~500 像素
 *   - fullPage: 截取整页而非仅视口
 */

const { test, expect } = require('@playwright/test');

// 需要视觉回归覆盖的核心页面
const VISUAL_PAGES = [
  { name: 'login', path: '/html/login.html', fullPage: false },
  { name: 'hub', path: '/html/hub.html', fullPage: true, maxDiff: 2000 },
  { name: 'settings', path: '/html/settings.html', fullPage: false },
  { name: 'stellar-showcase', path: '/html/stellar-showcase.html', fullPage: true, maxDiff: 500 },
];

VISUAL_PAGES.forEach(({ name, path, fullPage, maxDiff }) => {
  test(`视觉回归: ${name}`, async ({ page }) => {
    await page.goto(path, { waitUntil: 'networkidle', timeout: 30000 });

    // 等待所有入场动画完成
    await page.waitForTimeout(1000);

    // 截图对比
    await expect(page).toHaveScreenshot(`${name}.png`, {
      fullPage: fullPage || false,
      maxDiffPixels: maxDiff || 100,
      // 允许的差异比例 (0-1)
      maxDiffPixelRatio: 0.01,
    });
  });
});

// 主题切换视觉回归
test.describe('主题切换 — 视觉一致性', () => {
  const THEMES = ['warm-morning', 'study-night', 'ocean-glass', 'starry-night'];

  THEMES.forEach((theme) => {
    test(`hub.html — 主题 ${theme} 不应有布局偏移`, async ({ page }) => {
      // 设置主题
      await page.addInitScript((t) => {
        document.documentElement.setAttribute('data-theme', t);
      }, theme);

      await page.goto('/html/hub.html', { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(1500);

      await expect(page).toHaveScreenshot(`hub-${theme}.png`, {
        fullPage: true,
        maxDiffPixels: 2000,
      });
    });
  });

  test('settings.html — 主题弹窗打开后应正常显示', async ({ page }) => {
    await page.goto('/html/settings.html', { waitUntil: 'networkidle' });

    // 点击主题设置按钮
    const fab = page.locator('#app-theme-fab');
    if (await fab.isVisible()) {
      await fab.click();
      await page.waitForTimeout(500);

      const modal = page.locator('#theme-settings-modal');
      await expect(modal).toBeVisible();

      await expect(page).toHaveScreenshot('settings-theme-modal.png', {
        maxDiffPixels: 200,
      });
    }
  });
});
