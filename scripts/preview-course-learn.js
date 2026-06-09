// Preview of course-learn.html — 课程学习页 v2 重构
// 用法: node scripts/preview-course-learn.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2
  });
  const page = await ctx.newPage();

  // Mock 后端 API
  const demoCourse = {
    id: 'BV1GJ411x7h7',
    title: '计算机基础入门',
    bvid: 'BV1GJ411x7h7',
    total_lessons: 79,
    total_duration: 12000,
    progress: 19,
    cover_url: '',
    chapters: [
      {
        id: 'ch-1', title: '计算机的发展',
        subchapters: [
          { id: 'sub-1', title: '1-01 计算机的发展-古代的计算工具', duration: 393, cid: 1, page: 1, bvid: 'BV1GJ411x7h7', completed: true },
          { id: 'sub-2', title: '1-02 计算机的发展-机械时代', duration: 358, cid: 1, page: 2, bvid: 'BV1GJ411x7h7', completed: true },
          { id: 'sub-3', title: '1-03 计算机的发展-电子时代', duration: 343, cid: 1, page: 3, bvid: 'BV1GJ411x7h7', completed: false },
          { id: 'sub-4', title: '1-04 计算机的发展-近代计算机', duration: 951, cid: 1, page: 4, bvid: 'BV1GJ411x7h7', completed: false },
          { id: 'sub-5', title: '1-05 计算机的发展-未来计算机', duration: 89, cid: 1, page: 5, bvid: 'BV1GJ411x7h7', completed: false }
        ]
      },
      {
        id: 'ch-2', title: '计算机硬件',
        subchapters: [
          { id: 'sub-6', title: '2-01 计算机硬件-分类', duration: 104, cid: 1, page: 6, bvid: 'BV1GJ411x7h7', completed: false },
          { id: 'sub-7', title: '2-02 计算机硬件-CPU 生成器', duration: 627, cid: 1, page: 7, bvid: 'BV1GJ411x7h7', completed: false },
          { id: 'sub-8', title: '2-03 计算机硬件-CPU 参数', duration: 856, cid: 1, page: 8, bvid: 'BV1GJ411x7h7', completed: false }
        ]
      },
      {
        id: 'ch-3', title: '计算机软件',
        subchapters: [
          { id: 'sub-9', title: '3-01 计算机软件', duration: 204, cid: 1, page: 9, bvid: 'BV1GJ411x7h7', completed: false }
        ]
      }
    ]
  };

  const demoBilibili = {
    code: 200,
    data: {
      title: '计算机基础入门',
      cid: 1,
      duration: 12000,
      pages: demoCourse.chapters.flatMap(c => c.subchapters.map(s => ({
        page: parseInt(String(s.page)),
        partTitle: s.title,
        duration: s.duration,
        cid: s.cid
      })))
    }
  };

  await page.route('**/api/courses/courses/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, data: demoCourse }) });
  });
  await page.route('**/api/bilibili/parse', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(demoBilibili) });
  });
  await page.route('**/api/bilibili/subtitles', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, data: [] }) });
  });

  // 屏蔽 B 站 embed, 用占位符更干净
  await page.route('**/player.bilibili.com/**', async (route) => {
    await route.abort('blockedbyclient');
  });

  const url = 'http://localhost:8765/html/course-learn.html?courseId=BV1GJ411x7h7';
  await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(1500);

  const outDir = path.resolve(__dirname, '..', 'demo-results', 'course-learn-rebuild');
  fs.mkdirSync(outDir, { recursive: true });

  // 1. 整体首屏 (深色)
  await page.screenshot({ path: path.join(outDir, '01-overview.png'), fullPage: false });
  console.log('✓ 01-overview.png saved');

  // 2. 全页截图
  await page.screenshot({ path: path.join(outDir, '02-full-page.png'), fullPage: true });
  console.log('✓ 02-full-page.png saved');

  // 3. 切换到字幕步骤
  await page.click('.cl-step[data-step="subtitles"]');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(outDir, '03-step-subtitles.png'), fullPage: false });
  console.log('✓ 03-step-subtitles.png saved');

  // 4. 切换到笔记步骤 (先切换再填字)
  await page.click('.cl-step[data-step="notes"]');
  await page.waitForTimeout(800);
  await page.fill('#cl-notes-editor', '本节重点:\n1. 古代计算工具的发展: 结绳 → 算筹 → 算盘\n2. 机械计算器: 帕斯卡加法器、莱布尼茨步进计算器\n3. 程序存储思想: 巴贝奇分析机\n4. 冯·诺依曼架构: 五大部件, 沿用至今\n\n[时间戳 12:30] 这里的例子很关键, 记一下');
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(outDir, '04-step-notes.png'), fullPage: false });
  console.log('✓ 04-step-notes.png saved');

  // 5. 切换到关键概念步骤
  await page.click('.cl-step[data-step="concepts"]');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(outDir, '05-step-concepts.png'), fullPage: false });
  console.log('✓ 05-step-concepts.png saved');

  // 6. 切换到思维导图步骤 (滚动到面板 + 等布局稳定)
  await page.click('.cl-step[data-step="mindmap"]');
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    document.querySelector('.cl-step-panel[data-panel="mindmap"]').scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(1200);
  // 单独截 viewport 区域
  const mmViewport = await page.$('#cl-mindmap-viewport');
  if (mmViewport) {
    await mmViewport.screenshot({ path: path.join(outDir, '06-step-mindmap.png') });
  } else {
    await page.screenshot({ path: path.join(outDir, '06-step-mindmap.png'), fullPage: true });
  }
  console.log('✓ 06-step-mindmap.png saved');

  // 7. 切换到练习步骤并答题
  await page.click('.cl-step[data-step="exercises"]');
  await page.waitForTimeout(800);
  // 答第 1 题
  const firstOpt = await page.$('.cl-exercise-item[data-idx="0"] .cl-exercise-option[data-opt="3"]');
  if (firstOpt) await firstOpt.click();
  await page.waitForTimeout(400);
  // 答第 2 题
  const secondOpt = await page.$('.cl-exercise-item[data-idx="1"] .cl-exercise-option[data-opt="2"]');
  if (secondOpt) await secondOpt.click();
  await page.waitForTimeout(400);
  // 答第 3 题 (判断)
  const thirdOpt = await page.$('.cl-exercise-item[data-idx="2"] .cl-exercise-option[data-bool="false"]');
  if (thirdOpt) await thirdOpt.click();
  await page.waitForTimeout(400);
  // 答第 4 题 (填空)
  const fillInput = await page.$('.cl-exercise-item[data-idx="3"] input');
  if (fillInput) {
    await fillInput.fill('周易');
    const submitBtn = await page.$('[data-fill-submit="3"]');
    if (submitBtn) await submitBtn.click();
  }
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(outDir, '07-step-exercises.png'), fullPage: false });
  console.log('✓ 07-step-exercises.png saved');

  // 8. 切换 subtab 到 AI 讲义
  await page.click('.cl-step[data-step="subtitles"]');
  await page.waitForTimeout(400);
  await page.click('.cl-subtab[data-subtab="transcript"]');
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '08-transcript.png'), fullPage: false });
  console.log('✓ 08-transcript.png saved');

  // 9. 测试侧边栏折叠
  await page.click('.cl-sidebar-toggle');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(outDir, '09-sidebar-collapsed.png'), fullPage: false });
  console.log('✓ 09-sidebar-collapsed.png saved');

  await browser.close();
  console.log('\nAll screenshots saved to:', outDir);
})();
