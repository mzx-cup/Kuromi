// Verify demo fake data renders correctly on progress.html / calendar.html
// 通过 DOM 断言验证假数据渲染（不依赖截图可读性）
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const initScript = () => {
    localStorage.removeItem('starlearn_user');
    localStorage.setItem('starlearn_onboarding_completed', '1');
  };

  // ---------- progress.html ----------
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(initScript);
    const page = await ctx.newPage();
    await page.goto('http://localhost:8000/progress.html', { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(2200);

    const result = await page.evaluate(() => {
      const stat = key => document.querySelector(`[data-stat="${key}"] [data-field="value"]`)?.textContent;
      const bars = [...document.querySelectorAll('#weekly-chart .bar-col')].map(c => ({
        label: c.querySelector('.bar-label')?.textContent,
        value: c.querySelector('.bar-value')?.textContent,
      }));
      const courses = [...document.querySelectorAll('#course-progress-list .progress-item')].map(i => ({
        name: i.querySelector('.progress-item-name-text')?.textContent,
        value: i.querySelector('.progress-item-value')?.textContent,
        barWidth: i.querySelector('.progress-bar-fill')?.style.width,
      }));
      const timeline = [...document.querySelectorAll('#learning-timeline .timeline-item')].map(i => i.querySelector('.timeline-title')?.textContent);
      const radarPoints = document.querySelectorAll('#radar-points .radar-point').length;
      const radarShape = document.getElementById('radar-shape')?.getAttribute('points');
      return {
        stat: { hours: stat('total-hours'), courses: stat('completed-courses'), streak: stat('current-streak'), avg: stat('avg-daily') },
        bars, courses, timeline, radarPoints, radarShape,
        unlocked: document.getElementById('unlocked-count')?.textContent,
        total: document.getElementById('total-count')?.textContent,
        badge: !!document.getElementById('demo-data-badge'),
      };
    });
    console.log('=== progress.html (本月) ===');
    console.log(JSON.stringify(result, null, 2));

    // 切换「全部」后再取统计
    await page.click('.time-range-btn[data-range="all"]');
    await page.waitForTimeout(1200);
    const allStats = await page.evaluate(() => ({
      hours: document.querySelector('[data-stat="total-hours"] [data-field="value"]')?.textContent,
      unlocked: document.getElementById('unlocked-count')?.textContent,
    }));
    console.log('=== progress.html (全部) 总时长/成就 ===', JSON.stringify(allStats));
    await ctx.close();
  }

  // ---------- calendar.html ----------
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(initScript);
    const page = await ctx.newPage();
    await page.route('https://cdn.tailwindcss.com/**', route => route.abort());
    await page.goto('http://localhost:8000/calendar.html', { waitUntil: 'load', timeout: 20000 });
    await page.waitForTimeout(2200);

    const result = await page.evaluate(() => {
      const dayCount = cls => document.querySelectorAll(`#calendar-grid .calendar-day.${cls}`).length;
      const days = [...document.querySelectorAll('#calendar-grid .calendar-day')].map(d => ({
        day: d.querySelector('.day-number')?.textContent,
        cls: d.className.replace('calendar-day', '').trim(),
        level: d.dataset.level,
      })).filter(d => d.cls && d.cls !== 'empty');
      return {
        kpi: {
          streak: document.getElementById('kpi-streak')?.textContent,
          todo: document.getElementById('kpi-todo-today')?.textContent,
          monthHours: document.getElementById('kpi-month-hours')?.textContent,
          weekRate: document.getElementById('kpi-week-rate')?.textContent,
        },
        monthTitle: document.getElementById('month-title')?.textContent,
        checkin: {
          percent: document.getElementById('checkin-percent')?.textContent,
          status: document.getElementById('checkin-status')?.textContent,
          btnText: document.getElementById('checkin-btn-text')?.textContent,
        },
        todayTasks: [...document.querySelectorAll('#today-tasks-list .task-item')].map(t => ({
          name: t.querySelector('.task-name')?.textContent,
          done: t.classList.contains('completed'),
        })),
        todayTasksCount: document.getElementById('today-tasks-count')?.textContent,
        heatmap: [...document.querySelectorAll('#heatmap-grid .heatmap-cell')].map(c => c.querySelector('.hm-value')?.textContent),
        heatmapTotal: document.getElementById('heatmap-total')?.textContent,
        upcoming: [...document.querySelectorAll('#events-list .event-item')].map(e => e.querySelector('.event-title')?.textContent),
        dayStates: {
          completed: dayCount('completed'), partial: dayCount('partial'),
          scheduled: dayCount('scheduled'), today: dayCount('today'),
        },
        badge: !!document.getElementById('demo-data-badge'),
      };
    });
    console.log('=== calendar.html ===');
    console.log(JSON.stringify(result, null, 2));
    await ctx.close();
  }

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
