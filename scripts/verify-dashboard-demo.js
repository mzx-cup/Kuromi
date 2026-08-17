// Verify demo fake data renders correctly on data-dashboard.html (学习数据大屏)
// 通过 DOM 断言验证假数据渲染（不依赖截图可读性）
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(() => {
    localStorage.removeItem('starlearn_user');
    localStorage.setItem('starlearn_onboarding_completed', '1');
  });
  const page = await ctx.newPage();
  const apiRequests = [];
  page.on('request', req => {
    if (req.url().includes('/api/')) apiRequests.push(req.url());
  });

  // echarts/lucide 来自 CDN，等待 load 事件 + 数字动画完成
  await page.goto('http://localhost:8000/data-dashboard.html', { waitUntil: 'load', timeout: 30000 });
  await page.waitForFunction(() => {
    const el = document.getElementById('stat-total-hours');
    return el && el.getAttribute('data-counter') === '52.5' && document.getElementById('chart-daily-time')._echart_;
  }, null, { timeout: 20000 });
  await page.waitForTimeout(1400); // 等待数字滚动动画结束

  const overview = await page.evaluate(() => {
    const heat = [...document.querySelectorAll('#dd-heatmap .dd-heat-cell')];
    return {
      url: location.pathname,
      badge: !!document.getElementById('demo-data-badge'),
      stats: {
        hours: document.getElementById('stat-total-hours')?.textContent,
        courses: document.getElementById('stat-courses')?.textContent,
        exercises: document.getElementById('stat-exercises')?.textContent,
        streak: document.getElementById('stat-streak')?.textContent,
      },
      trends: {
        hours: document.getElementById('trend-hours')?.textContent,
        courses: document.getElementById('trend-courses')?.textContent,
        exercises: document.getElementById('trend-exercises')?.textContent,
        streak: document.getElementById('trend-streak')?.textContent,
      },
      dailyAvg: document.getElementById('daily-avg')?.textContent,
      heatmap: { cells: heat.length, active: heat.filter(c => !c.className.includes(' l0')).length, sample: heat.filter(c => !c.className.includes(' l0')).slice(0, 3).map(c => c.getAttribute('title')) },
      timeline: [...document.querySelectorAll('#dd-timeline .dd-timeline-item')].map(i => i.querySelector('.dd-tl-title')?.textContent),
      rings: [...document.querySelectorAll('.dd-ring .dd-ring-val')].map(r => r.textContent),
      goalFoot: document.getElementById('goal-foot')?.textContent,
      streakDots: document.querySelectorAll('[data-streak] span.on').length,
      charts: {
        daily: document.getElementById('chart-daily-time')._echart_ ? {
          x: document.getElementById('chart-daily-time')._echart_.getOption().xAxis[0].data,
          y: document.getElementById('chart-daily-time')._echart_.getOption().series[0].data,
        } : null,
        pie: document.getElementById('chart-subject-pie')._echart_
          ? document.getElementById('chart-subject-pie')._echart_.getOption().series[0].data.map(d => d.name)
          : null,
        weekly: document.getElementById('chart-weekly-bar')._echart_
          ? document.getElementById('chart-weekly-bar')._echart_.getOption().series.map(s => s.name)
          : null,
      },
    };
  });
  console.log('=== data-dashboard.html 概览 (默认 30d) ===');
  console.log(JSON.stringify(overview, null, 2));

  // ---------- 切换时间范围 ----------
  const rangeChecks = {};
  for (const r of ['7d', '90d']) {
    await page.click(`.dd-range-btn[data-range="${r}"]`);
    const expectedHours = r === '7d' ? '11.5' : '268.5';
    await page.waitForFunction(
      exp => document.getElementById('stat-total-hours')?.getAttribute('data-counter') === exp,
      expectedHours, { timeout: 10000 }
    );
    await page.waitForTimeout(1300);
    rangeChecks[r] = await page.evaluate(() => ({
      hours: document.getElementById('stat-total-hours')?.textContent,
      exercises: document.getElementById('stat-exercises')?.textContent,
      rings: [...document.querySelectorAll('.dd-ring .dd-ring-val')].map(r => r.textContent),
    }));
  }
  console.log('=== 时间范围切换 (7d / 90d) ===');
  console.log(JSON.stringify(rangeChecks, null, 2));

  // ---------- 能力雷达图 ----------
  await page.click('.dd-tab[data-tab="radar"]');
  await page.waitForFunction(() => document.getElementById('chart-radar')._echart_, null, { timeout: 10000 });
  await page.waitForTimeout(600);
  const radar = await page.evaluate(() => ({
    dims: [...document.querySelectorAll('#dim-list .dd-dim-item')].map(i => ({
      name: i.querySelector('.dd-dim-name')?.textContent,
      score: i.querySelector('.dd-dim-score')?.textContent,
    })),
    chart: document.getElementById('chart-radar')._echart_
      ? document.getElementById('chart-radar')._echart_.getOption().series[0].data[0].value
      : null,
    compare: document.getElementById('chart-radar-compare')._echart_
      ? document.getElementById('chart-radar-compare')._echart_.getOption().series.map(s => s.name)
      : null,
  }));
  console.log('=== 能力雷达图 ===');
  console.log(JSON.stringify(radar, null, 2));

  // ---------- 知识图谱 ----------
  await page.click('.dd-tab[data-tab="graph"]');
  await page.waitForFunction(() => document.getElementById('chart-graph')._echart_, null, { timeout: 10000 });
  await page.waitForTimeout(600);
  const graph = await page.evaluate(() => {
    const opt = document.getElementById('chart-graph')._echart_.getOption();
    return {
      nodes: opt.series[0].data.map(n => ({ name: n.name, cat: n.category })),
      links: opt.series[0].links.length,
      recommend: [...document.querySelectorAll('#graph-recommend .dd-path-item')].map(i => ({
        title: i.querySelector('.dd-path-title')?.textContent,
        meta: i.querySelector('.dd-path-meta')?.textContent,
      })),
    };
  });
  console.log('=== 知识图谱 ===');
  console.log(JSON.stringify(graph, null, 2));

  // ---------- 心流数据 ----------
  await page.click('.dd-tab[data-tab="flow"]');
  await page.waitForTimeout(800);
  const flow = await page.evaluate(() => ({
    focus: document.getElementById('flow-focus')?.textContent,
    study: document.getElementById('flow-study')?.textContent,
    switches: document.getElementById('flow-switches')?.textContent,
    score: document.getElementById('flow-score')?.textContent,
    loadingReplaced: !document.getElementById('flow-loading'),
  }));
  console.log('=== 心流数据 ===');
  console.log(JSON.stringify(flow, null, 2));

  console.log('=== /api/ 请求数（应为 0）===', apiRequests.length, apiRequests.length ? apiRequests : '');

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
