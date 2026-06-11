// Preview of video-player.html
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Mock API responses
  const demoCourses = {
    courses: [
      { id: 1, title: '抽错必后悔！星铁4.3~4.4卡池抽取推荐！', source_type: 'bilibili', bvid: 'BV1H9V76TEPM', subtitle: '千劫刃 姬子启行 远坂凛 吉尔伽美什卡 虚照 真珠应该抽谁？', duration_label: '03:17' },
      { id: 2, title: 'Python 数据结构精讲', source_type: 'bilibili', bvid: 'BV1oi4y1L7yA', subtitle: '从零到精通，10 大经典结构', duration_label: '24:36' },
      { id: 3, title: '高等数学上册', source_type: 'local', local_path: '/video/math-01.mp4', subtitle: '极限与连续专题', duration_label: '45:12' },
      { id: 4, title: 'C++ 模板元编程', source_type: 'bilibili', bvid: 'BV1Ab411c7mD', subtitle: '类型体操实战', duration_label: '38:00' },
      { id: 5, title: '机器学习导论', source_type: 'local', local_path: '/video/ml-01.mp4', subtitle: '从线性回归到神经网络', duration_label: '52:48' },
    ],
  };

  const demoPlaylists = {
    playlists: [
      {
        id: 1, name: '默认列表',
        videos: [demoCourses.courses[0], demoCourses.courses[1]],
      },
    ],
  };

  await page.route('**/api/video-courses', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(demoCourses) });
  });
  await page.route('**/api/video-playlists**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(demoPlaylists) });
  });
  await page.route('**/api/bilibili/**', async (route) => {
    await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'mock - 不实际播放' }) });
  });

  const url = 'http://localhost:8001/video-player.html';
  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(1200);

  const outDir = path.resolve(__dirname, '..', 'demo-results', 'video-player-rebuild');
  fs.mkdirSync(outDir, { recursive: true });

  // Screenshot 1: 默认主题（与 hub 一致）
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'pink-dark'));
  await page.waitForTimeout(500);
  const f1 = path.join(outDir, 'vp-pink-dark.png');
  await page.screenshot({ path: f1, fullPage: true });
  console.log('Saved:', f1);

  // Screenshot 2: 亮色
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'ocean-glass'));
  await page.waitForTimeout(500);
  const f2 = path.join(outDir, 'vp-ocean-light.png');
  await page.screenshot({ path: f2, fullPage: true });
  console.log('Saved:', f2);

  // Screenshot 3: 暗色金靛
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'star-vault'));
  await page.waitForTimeout(500);
  const f3 = path.join(outDir, 'vp-star-vault.png');
  await page.screenshot({ path: f3, fullPage: true });
  console.log('Saved:', f3);

  // Screenshot 4: 默认主题 + 打开 AI 笔记 Tab
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'pink-dark'));
  await page.waitForTimeout(300);
  await page.click('.side-tab[data-tab="ai-notes"]');
  await page.waitForTimeout(500);
  const f4 = path.join(outDir, 'vp-ai-notes.png');
  await page.screenshot({ path: f4, fullPage: true });
  console.log('Saved:', f4);

  // Screenshot 5: 弹窗
  await page.click('.side-tab[data-tab="courses"]');
  await page.waitForTimeout(300);
  await page.click('#add-course-btn');
  await page.waitForTimeout(400);
  const f5 = path.join(outDir, 'vp-add-modal.png');
  await page.screenshot({ path: f5, fullPage: true });
  console.log('Saved:', f5);

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
