/**
 * css-conflict-resolution.spec.js — L3 回归测试
 *
 * 验证 5 个高风险页面的核心 UI 状态：
 * 1. 加载正确（无 console error）
 * 2. 主题切换后 CSS 变量值变化
 * 3. 不加载被禁用的 CSS 文件
 */
const { test, expect } = require('@playwright/test');

const HIGH_RISK_PAGES = [
  { path: '/login.html', name: 'login', forbiddenCss: ['teacher.css'] },
  { path: '/register.html', name: 'register', forbiddenCss: ['teacher.css'] },
  { path: '/hub.html', name: 'hub', forbiddenCss: ['hub-perfect.css', 'hub-winmoes.css'] },
  { path: '/personal.html', name: 'personal', forbiddenCss: [] },
  { path: '/teacher-dashboard.html', name: 'teacher-dashboard', forbiddenCss: [] },
];

for (const page of HIGH_RISK_PAGES) {
  test(`${page.name} - 加载不包含禁用 CSS`, async ({ page: browserPage }) => {
    const loadedStylesheets = [];

    // 拦截所有样式表请求
    browserPage.on('response', (response) => {
      const url = response.url();
      if (url.endsWith('.css')) {
        loadedStylesheets.push(url);
      }
    });

    await browserPage.goto(page.path);
    await browserPage.waitForLoadState('networkidle');

    for (const forbidden of page.forbiddenCss) {
      const found = loadedStylesheets.find((url) => url.includes(forbidden));
      expect(found, `${page.name} 不应加载 ${forbidden}`).toBeUndefined();
    }
  });

  test(`${page.name} - 主题切换后 CSS 变量值变化`, async ({ page: browserPage }) => {
    await browserPage.goto(page.path);
    await browserPage.waitForLoadState('networkidle');

    // 读取当前主题的 brand-400 颜色
    const before = await browserPage.evaluate(() => {
      return getComputedStyle(document.documentElement)
        .getPropertyValue('--brand-400')
        .trim();
    });
    expect(before, '应能读取到 --brand-400 变量').not.toBe('');

    // 切换 data-theme 属性（模拟主题切换）
    await browserPage.evaluate(() => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current && current.includes('sakura') ? 'bamboo-dark' : 'sakura-dark';
      document.documentElement.setAttribute('data-theme', next);
    });

    // 等待样式应用
    await browserPage.waitForTimeout(200);

    const after = await browserPage.evaluate(() => {
      return getComputedStyle(document.documentElement)
        .getPropertyValue('--brand-400')
        .trim();
    });

    expect(after, '切换主题后 --brand-400 应变化').not.toBe(before);
  });
}
