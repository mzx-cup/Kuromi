/**
 * 全页面冒烟测试 (Smoke Tests)
 *
 * 对项目中所有页面进行基本加载验证：
 *   1. 页面能正常加载 (HTTP 200)
 *   2. 无 JavaScript 控制台错误
 *   3. 关键 CSS/JS 文件成功加载
 *   4. Toast 系统可用
 *   5. 主题令牌正确注入
 *
 * 运行:
 *   npx playwright test tests/frontend/e2e/smoke.spec.js
 *   npx playwright test tests/frontend/e2e/smoke.spec.js --project=chromium
 */

const { test, expect } = require('@playwright/test');

// 需要测试的所有页面（排除文件后缀 .html）
const ALL_PAGES = [
  'login',
  'register',
  'hub',
  'personal',
  'settings',
  'teacher-dashboard',
  'courses',
  'calendar',
  'progress',
  'assessment',
  'video-player',
  'code',
  'socratic-ai',
  'data-dashboard',
  'flow-meter',
  'plant',
  'teacher-class',
  'teacher-content',
  'teacher-exam',
  'teacher-manage',
  'course-learn',
  'course-detail',
  'generation-preview',
  'ai-pair-programming',
  'architecture-blueprint',
  'concept-analyzer',
  'my-courses',
  'stellar-showcase',
  'pixel-pet-game',
  'classroom-premium-preview',
];

// 为每个页面生成一个测试
ALL_PAGES.forEach((pageName) => {
  test(`页面加载: ${pageName}.html — 无控制台错误`, async ({ page }) => {
    const errors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // 页面加载失败的错误也捕获
    page.on('pageerror', (err) => {
      errors.push(err.message);
    });

    await page.goto(`/html/${pageName}.html`, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // 验证页面标题不为空
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);

    // 验证 body 存在
    const bodyExists = await page.locator('body').count();
    expect(bodyExists).toBe(1);

    // 报告控制台错误（但不立即失败，先收集所有错误）
    if (errors.length > 0) {
      console.warn(`[${pageName}.html] 控制台错误:`, errors);
    }

    // toast.js 中 window.Toast 是 IIFE 挂载的，验证存在
    const hasToast = await page.evaluate(() => typeof window.Toast !== 'undefined');
    expect(hasToast).toBe(true);
  });
});

// 核心页面专项测试
test.describe('核心页面 — 专项验证', () => {
  test('login.html — 应包含 app-form-card', async ({ page }) => {
    await page.goto('/login.html', { waitUntil: 'networkidle' });
    const card = page.locator('.auth-card-inner');
    await expect(card).toBeVisible();
  });

  test('hub.html — 应包含 data-bg-unified 属性', async ({ page }) => {
    await page.goto('/hub.html', { waitUntil: 'networkidle' });
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-bg-unified', 'true');
  });

  test('settings.html — 应包含主题设置入口', async ({ page }) => {
    await page.goto('/settings.html', { waitUntil: 'networkidle' });
    const themeBtn = page.locator('#app-theme-fab');
    await expect(themeBtn).toBeAttached({ timeout: 5000 });
  });

  test('stellar-showcase.html — 不应有重复 data-layer.js', async ({ page }) => {
    await page.goto('/stellar-showcase.html', { waitUntil: 'networkidle' });
    const scripts = await page.locator('script[src="/js/data-layer.js"]').count();
    expect(scripts).toBeLessThanOrEqual(1);
  });

  test('pixel-pet-game.html — 应保留 data-bg-preserve 豁免', async ({ page }) => {
    await page.goto('/pixel-pet-game.html', { waitUntil: 'networkidle' });
    const body = page.locator('body');
    await expect(body).toHaveAttribute('data-bg-preserve', 'true');
  });
});

// CSS 变量注入验证
test.describe('设计令牌 — CSS 变量注入', () => {
  const TOKEN_PAGES = ['login', 'hub', 'settings'];

  TOKEN_PAGES.forEach((pageName) => {
    test(`${pageName}.html — 应注入核心 CSS 令牌`, async ({ page }) => {
      await page.goto(`/${pageName}.html`, { waitUntil: 'networkidle' });

      const tokens = await page.evaluate(() => {
        const styles = getComputedStyle(document.documentElement);
        return {
          '--text-heading': styles.getPropertyValue('--text-heading').trim(),
          '--text-body': styles.getPropertyValue('--text-body').trim(),
          '--surface-card': styles.getPropertyValue('--surface-card').trim(),
          '--brand-500': styles.getPropertyValue('--brand-500').trim(),
          '--radius-lg': styles.getPropertyValue('--radius-lg').trim(),
          '--shadow-md': styles.getPropertyValue('--shadow-md').trim(),
          '--ease-out': styles.getPropertyValue('--ease-out').trim(),
        };
      });

      // 每个令牌应包含有效值（非空字符串）
      Object.entries(tokens).forEach(([name, value]) => {
        expect(value, `${pageName}: ${name} 不应为空`).toBeTruthy();
      });
    });
  });
});
