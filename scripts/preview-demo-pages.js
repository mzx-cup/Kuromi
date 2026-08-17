// Quick visual preview of the demo fake data on progress.html / calendar.html
// 验证 demo-data.js 注入的假数据渲染效果（无需登录、无需后端数据）
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const outDir = path.resolve(__dirname, '..', 'artifacts', 'demo', 'pages');
  fs.mkdirSync(outDir, { recursive: true });

  // 未登录（无 starlearn_user）+ 已完成新手引导（避免引导遮罩）
  const initScript = () => {
    localStorage.removeItem('starlearn_user');
    localStorage.setItem('starlearn_onboarding_completed', '1');
  };

  // ---------- progress.html ----------
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(initScript);
    const page = await ctx.newPage();
    const errors = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('pageerror', err => errors.push('PAGEERROR: ' + err.stack));

    await page.goto('http://localhost:8000/progress.html', { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(2200); // 等待数字与柱状图动画

    // 视口截图（避免全页图过高无法预览）+ 滚到中段与底部各截一张
    const f1 = path.join(outDir, 'progress-demo-top.jpg');
    await page.screenshot({ path: f1, type: 'jpeg', quality: 85 });
    console.log('Saved:', f1);

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.5));
    await page.waitForTimeout(300);
    const f2 = path.join(outDir, 'progress-demo-mid.jpg');
    await page.screenshot({ path: f2, type: 'jpeg', quality: 85 });
    console.log('Saved:', f2);

    // 切换时间范围「全部」
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.click('.time-range-btn[data-range="all"]');
    await page.waitForTimeout(1200);
    const f3 = path.join(outDir, 'progress-demo-all-top.jpg');
    await page.screenshot({ path: f3, type: 'jpeg', quality: 85 });
    console.log('Saved:', f3);

    console.log('progress.html console errors:', errors.length ? errors.join('\n') : 'none');
    await ctx.close();
  }

  // ---------- calendar.html ----------
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(initScript);
    const page = await ctx.newPage();
    const errors = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('pageerror', err => errors.push('PAGEERROR: ' + err.stack));

    // Tailwind CDN 脚本会长时间保持连接拖慢 load 事件，直接拦截；页面样式由 calendar.css 提供
    await page.route('https://cdn.tailwindcss.com/**', route => route.abort());
    await page.goto('http://localhost:8000/calendar.html', { waitUntil: 'load', timeout: 20000 });
    await page.waitForTimeout(2200);

    const f1 = path.join(outDir, 'calendar-demo-top.jpg');
    await page.screenshot({ path: f1, type: 'jpeg', quality: 85 });
    console.log('Saved:', f1);

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.55));
    await page.waitForTimeout(300);
    const f2 = path.join(outDir, 'calendar-demo-mid.jpg');
    await page.screenshot({ path: f2, type: 'jpeg', quality: 85 });
    console.log('Saved:', f2);

    console.log('calendar.html console errors:', errors.length ? errors.join('\n') : 'none');
    await ctx.close();
  }

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
