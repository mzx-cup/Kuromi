// Quick visual preview of progress.html
// 拦截 fetch 调用，注入演示数据，避免对运行中后端的依赖
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // 拦截 /api/progress/summary
  await page.route('**/api/progress/summary/**', async (route) => {
    const demo = {
      success: true,
      summary: {
        total_hours: 42.5,
        completed_courses: 7,
        current_streak: 12,
        avg_daily_hours: 1.42,
        weekly_activity: [
          { day: '周一', hours: 1.2 },
          { day: '周二', hours: 0.8 },
          { day: '周三', hours: 2.1 },
          { day: '周四', hours: 1.5 },
          { day: '周五', hours: 0.4 },
          { day: '周六', hours: 3.2 },
          { day: '周日', hours: 2.8 },
        ],
        course_progress: [
          { name: 'Python 基础',    progress: 86, icon: '🐍' },
          { name: '算法与数据结构', progress: 64, icon: '🧮' },
          { name: 'Web 开发',       progress: 41, icon: '🌐' },
          { name: '数据库原理',     progress: 23, icon: '🗄️' },
          { name: '系统设计',       progress: 12, icon: '🏗️' },
        ],
        timeline: [
          { title: '完成《Python 基础》第七章', time: '今天 14:32', desc: '耗时 38 分钟，测试通过率 100%', status: 'completed' },
          { title: '算法练习：二叉树遍历',       time: '今天 10:15', desc: '中等难度，已通过 5/5 测试用例',   status: 'completed' },
          { title: '正在学习：Web 框架入门',     time: '昨天 21:08', desc: '已完成 41%，预计还需 3.2 小时',   status: 'in-progress' },
          { title: '提交项目：TODO 应用',         time: '昨天 16:40', desc: '代码已合并至 main 分支',          status: 'completed' },
          { title: '复习：高阶函数与闭包',        time: '前天 20:12', desc: '已添加 8 个知识卡片到复习计划',   status: 'completed' },
        ],
      },
    };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(demo) });
  });

  const url = 'http://localhost:8001/progress.html';
  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  // 等待数据动画
  await page.waitForTimeout(1500);

  const outDir = path.resolve(__dirname, '..', 'demo-results', 'progress-rebuild');
  fs.mkdirSync(outDir, { recursive: true });

  const file1 = path.join(outDir, 'progress-light.png');
  await page.screenshot({ path: file1, fullPage: true });
  console.log('Saved:', file1);

  // 默认主题（与 hub.html 一致：pink-dark）
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'pink-dark');
  });
  await page.waitForTimeout(500);
  const file2 = path.join(outDir, 'progress-pink-dark.png');
  await page.screenshot({ path: file2, fullPage: true });
  console.log('Saved:', file2);

  // 暗色主题
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'star-vault');
  });
  await page.waitForTimeout(500);
  const file3 = path.join(outDir, 'progress-star-vault.png');
  await page.screenshot({ path: file3, fullPage: true });
  console.log('Saved:', file3);

  // 亮色主题
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'ocean-glass');
  });
  await page.waitForTimeout(500);
  const file4 = path.join(outDir, 'progress-ocean-light.png');
  await page.screenshot({ path: file4, fullPage: true });
  console.log('Saved:', file4);

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
