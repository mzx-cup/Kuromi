// @ts-check
const { test, expect } = require('@playwright/test');

test('code.html 渲染 IDE 四区骨架', async ({ page }) => {
  await page.goto('/code.html');
  await expect(page.locator('.ide-shell')).toBeVisible();
  const icons = await page.locator('.ide-activity-icon').count();
  expect(icons).toBeGreaterThanOrEqual(4);
  // 状态栏
  await expect(page.locator('.ide-status-bar')).toBeVisible();
  // AI 教练侧栏
  await expect(page.locator('.ide-coach').first()).toBeAttached();
});
