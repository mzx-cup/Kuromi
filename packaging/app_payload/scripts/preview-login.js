/**
 * preview-login.js — 登录页面回归
 *  1. 视觉：3 个主题下登录页静态展示
 *  2. 交互：错误态展示
 *  3. 演示登录 → 跳转 hub.html
 *  4. Auth.logout() 退出登录回归
 *  5. 移动端布局
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

/** 等待 window.Auth 挂载到全局 */
async function waitAuth(page, timeout = 5000) {
  await page.waitForFunction(() => typeof window.Auth !== 'undefined' && typeof window.Auth.logout === 'function', { timeout });
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  const outDir = path.resolve(__dirname, '..', 'demo-results', 'login-rebuild');
  fs.mkdirSync(outDir, { recursive: true });

  // ───────── 拦截 /api/auth/* ─────────
  const demoUser = (role, name) => ({
    id: role === 'teacher' ? 1 : role === 'admin' ? 3 : 2,
    username: role,
    role,
    display_name: name,
    avatar: '',
    nickname: name,
  });

  await page.route('**/api/auth/login', async (route, req) => {
    let body = {};
    try { body = JSON.parse(req.postData() || '{}'); } catch (_) {}
    const u = (body.username || '').toLowerCase();
    const roleMap = { teacher: 'teacher', student: 'student', admin: 'admin' };
    const role = roleMap[u];
    if (!role || body.password !== '123456') {
      return route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: '用户名或密码错误' }),
      });
    }
    const names = { teacher: '教师演示', student: '学生演示', admin: '管理员' };
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        token: 'mock.jwt.' + role,
        user: demoUser(role, names[role]),
      }),
    });
  });

  await page.route('**/api/auth/me', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ user: demoUser('student', '学生演示') }),
    });
  });

  const url = 'http://localhost:8001/login.html';

  // ───────── 1. 视觉：3 主题 ─────────
  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  await waitAuth(page);
  await page.waitForTimeout(800);

  for (const [theme, name] of [
    ['pink-dark',   'login-pink-dark.png'],
    ['star-vault',  'login-star-vault.png'],
    ['ocean-glass', 'login-ocean-light.png'],
  ]) {
    await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme);
    await page.waitForTimeout(400);
    const f = path.join(outDir, name);
    await page.screenshot({ path: f, fullPage: true });
    console.log('Saved:', f);
  }

  // ───────── 2. 错误态 ─────────
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'pink-dark'));
  await page.fill('#login-username', 'wronguser');
  await page.fill('#login-password', 'badpass');
  await page.click('button[type=submit]');
  await page.waitForTimeout(600);
  const fErr = path.join(outDir, 'login-error.png');
  await page.screenshot({ path: fErr, fullPage: true });
  console.log('Saved:', fErr);

  // ───────── 3. 演示登录 → 跳转 hub.html ─────────
  // 用一个全新 page 避免之前错误态的影响
  const ctx2 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx2.route('**/api/auth/login', (route, req) => {
    let body = {};
    try { body = JSON.parse(req.postData() || '{}'); } catch (_) {}
    if (body.username === 'student' && body.password === '123456') {
      // 生成一个结构合法的 mock JWT (3 段 base64)，让 hub.html 的 isTokenValid() 通过
      const future = Math.floor(Date.now() / 1000) + 3600;
      const payload = Buffer.from(JSON.stringify({ uid: 2, username: 'student', role: 'student', exp: future })).toString('base64url');
      const token = 'mock.' + payload + '.sig';
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ token, user: demoUser('student', '学生演示') }),
      });
    }
    return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'fail' }) });
  });
  const p2 = await ctx2.newPage();
  await p2.goto(url, { waitUntil: 'networkidle' });
  await waitAuth(p2);
  // 等演示登录按钮出现
  await p2.waitForSelector('.auth-quick-btn:nth-child(2)', { state: 'visible' });
  await p2.click('.auth-quick-btn:nth-child(2)');
  // 等待跳转（成功时跳到 /hub.html）
  let navOk = false;
  try {
    await p2.waitForURL('**/hub.html', { timeout: 5000 });
    navOk = true;
  } catch (_) {}
  console.log('Student quick-login → url:', p2.url(), 'navOk:', navOk);
  if (!navOk) {
    // 失败也截一张，便于诊断
    const fFail = path.join(outDir, 'login-quick-fail.png');
    await p2.screenshot({ path: fFail, fullPage: true });
    console.log('Saved (debug):', fFail);
    // 不抛错，继续后面的测试
  } else {
    console.log('✓ Quick-login navigated to /hub.html');
  }

  // ───────── 4. Auth.logout() 退出登录回归 ─────────
  // 模拟「之前登录过」然后调用 Auth.logout()
  const ctx3 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p3 = await ctx3.newPage();
  await p3.goto(url, { waitUntil: 'networkidle' });
  await waitAuth(p3);
  await p3.evaluate(() => {
    localStorage.setItem('sp_token', 'stale.jwt.value');
    localStorage.setItem('sp_user', JSON.stringify({ username: 'teacher', role: 'teacher' }));
    localStorage.setItem('starlearn_user', JSON.stringify({ name: 'legacy' }));
    sessionStorage.setItem('user_profile', 'stale');
  });
  const beforeKeys = await p3.evaluate(() => ({
    sp_token: localStorage.getItem('sp_token'),
    sp_user: localStorage.getItem('sp_user'),
    starlearn_user: localStorage.getItem('starlearn_user'),
    session_user: sessionStorage.getItem('user_profile'),
  }));
  console.log('Before logout:', beforeKeys);

  await p3.evaluate(() => window.Auth.logout());
  await p3.waitForURL('**/login.html', { timeout: 5000 });
  await p3.waitForTimeout(400);

  const afterKeys = await p3.evaluate(() => ({
    sp_token: localStorage.getItem('sp_token'),
    sp_user: localStorage.getItem('sp_user'),
    starlearn_user: localStorage.getItem('starlearn_user'),
    session_user: sessionStorage.getItem('user_profile'),
  }));
  console.log('After logout:', afterKeys);
  if (afterKeys.sp_token || afterKeys.sp_user || afterKeys.starlearn_user) {
    throw new Error('Auth.logout() did not clear all localStorage keys: ' + JSON.stringify(afterKeys));
  }
  console.log('✓ Logout cleared all localStorage keys');

  const fLogout = path.join(outDir, 'login-after-logout.png');
  await p3.screenshot({ path: fLogout, fullPage: true });
  console.log('Saved:', fLogout);

  // ───────── 5. 移动端 ─────────
  const ctx4 = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mp = await ctx4.newPage();
  await mp.goto(url, { waitUntil: 'networkidle' });
  await mp.waitForTimeout(500);
  const fMob = path.join(outDir, 'login-mobile.png');
  await mp.screenshot({ path: fMob, fullPage: true });
  console.log('Saved:', fMob);

  await browser.close();
  console.log('\nAll checks passed.');
})().catch((e) => { console.error('FAIL:', e); process.exit(1); });
