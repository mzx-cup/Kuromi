// @ts-check
const { test, expect } = require('@playwright/test');

const THEMES = ['dawn', 'forest', 'sakura', 'midnight', 'nebula', 'cyber'];

for (const theme of THEMES) {
  test(`code.html 在 ${theme} 主题下布局无破版`, async ({ page }) => {
    await page.addInitScript((t) => {
      localStorage.setItem('starlearn_theme', t);
    }, theme);
    await page.goto('/code.html');
    await page.waitForSelector('.ide-shell');
    await expect(page.locator('.ide-shell')).toBeVisible();
    const shellBox = await page.locator('.ide-shell').boundingBox();
    expect(shellBox.width).toBeGreaterThan(800);
    await expect(page.locator('.ide-activity-bar')).toBeVisible();
    await expect(page.locator('.ide-status-bar')).toBeVisible();
    await expect(page.locator('.ide-coach').first()).toBeAttached();
    await page.screenshot({ path: `tests/frontend/e2e/__screenshots__/code-ide-${theme}.png`, fullPage: false });
  });
}
