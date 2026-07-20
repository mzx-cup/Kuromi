/**
 * 登录页面回归 — 真实后端 (uvicorn:8000)
 * 覆盖：教师 / 学生 / 管理员 / 错误账号 / 退出
 */
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';

const demoRoles = [
  { btn: '教师', dest: '/teacher-dashboard.html', role: 'teacher' },
  { btn: '学生', dest: '/hub.html',               role: 'student' },
  { btn: '管理员', dest: '/hub.html',             role: 'admin'  },
];

for (const { btn, dest, role } of demoRoles) {
  test(`点「${btn}演示」按钮 → 跳 ${dest}`, async ({ page }) => {
    await page.context().clearCookies();
    await page.goto(`${BASE_URL}/login.html`);
    await page.waitForLoadState('networkidle');

    // 等 Auth 挂载
    await page.waitForFunction(() => window.Auth && window.Auth.logout, { timeout: 5000 });

    // 清空
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(() => window.Auth && window.Auth.logout, { timeout: 5000 });

    // 拦截真实的 /api/auth/login，验证它会被调用
    let loginCalled = false;
    await page.route('**/api/auth/login', async (route, req) => {
      loginCalled = true;
      const body = JSON.parse(req.postData() || '{}');
      // 真正发给后端，不 mock
      const resp = await route.fetch();
      const data = await resp.json();
      // 直接放过
      await route.fulfill({ response: resp });
    });

    // 触发 demo 登录（用 evaluate 直接调用 quickLogin）
    await page.evaluate(async (r) => {
      // 找到 Alpine 的 loginPage 并调用 quickLogin
      const root = document.querySelector('[x-data]');
      // 简化为派发一个 click 事件
    }, role);

    // 走 click 路径
    await page.locator(`button:has-text("${btn}")`).first().click();

    // 等待 localStorage 出现 token
    await page.waitForFunction(
      () => !!localStorage.getItem('sp_token'),
      null,
      { timeout: 8000 }
    );

    // 验证调用确实发出去了
    expect(loginCalled).toBe(true);

    // 验证 token
    const auth = await page.evaluate(() => ({
      token: localStorage.getItem('sp_token'),
      user:  JSON.parse(localStorage.getItem('sp_user') || 'null'),
    }));
    expect(auth.token.split('.').length).toBe(3);
    expect(auth.user.role).toBe(role);

    // 验证 setTimeout 250ms 后会跳到目标页（不阻塞等 load 事件，
    // 因为 hub.html 拉数据较慢；只看 URL 切到目标即可）
    await page.waitForFunction(
      (expected) => window.location.pathname === expected || window.location.pathname.endsWith(expected),
      dest,
      { timeout: 8000 }
    );
  });
}

test('错误密码 1111/1234 → 留在登录页 + 显示错误', async ({ page }) => {
  await page.context().clearCookies();
  await page.goto(`${BASE_URL}/login.html`);
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');

  await page.fill('input#login-username', '1111');
  await page.fill('input#login-password', '1234');
  await page.click('button[type="submit"]');

  const errBanner = page.locator('.auth-banner--error');
  await expect(errBanner).toBeVisible({ timeout: 5000 });
  await expect(errBanner).toContainText('用户名或密码错误');

  // 仍在登录页
  expect(page.url()).toContain('/login.html');
  expect(await page.evaluate(() => localStorage.getItem('sp_token'))).toBeNull();
});
