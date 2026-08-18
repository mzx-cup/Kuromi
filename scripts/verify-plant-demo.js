// Verify demo fake data renders correctly on plant.html
// 通过 DOM 断言验证假数据渲染（不依赖截图可读性）
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();

  // 未登录（无 sp_token / 无 user） + 清空真实植物数据 → 应当自动进入演示模式
  const initScript = () => {
    localStorage.removeItem('sp_token');
    localStorage.removeItem('sp_user');
    localStorage.removeItem('starlearn_user');
    localStorage.removeItem('starlearn_plants');
    localStorage.removeItem('starlearn_plant_demo_mode');
    localStorage.removeItem('starlearn_plant_demo_state');
  };

  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(initScript);
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push('PAGEERROR: ' + err.message));

  await page.goto('http://localhost:8000/plant.html', { waitUntil: 'networkidle', timeout: 25000 });
  await page.waitForTimeout(1800);

  const result = await page.evaluate(() => {
    const slotItems = [...document.querySelectorAll('.plant-pot-wrapper')].map(w => ({
      slot: w.dataset.slot,
      emoji: w.querySelector('.plant-in-pot')?.textContent?.trim(),
      stage: w.querySelector('.plant-in-pot')?.className.match(/stage-(\d)/)?.[1],
      selected: w.classList.contains('selected'),
    }));
    const ownedCount = document.getElementById('owned-count')?.textContent;
    const seedNav = document.getElementById('seed-count-nav')?.textContent;
    const weatherTemp = document.getElementById('weather-temp')?.textContent;
    const weatherCity = document.getElementById('weather-city')?.textContent;
    const weatherIcon = document.getElementById('weather-icon')?.textContent;
    const ownedItems = [...document.querySelectorAll('.plant-collection-item.owned')].length;
    const badge = !!document.getElementById('demo-data-badge');
    const tipText = document.getElementById('plant-tip')?.textContent?.trim();
    // 选中第一个槽位（sakura 已成熟）
    const selectedPot = document.querySelector('.plant-pot-wrapper.selected');
    return {
      slots: slotItems,
      ownedCount,
      seedNav,
      weather: { temp: weatherTemp, city: weatherCity, icon: weatherIcon },
      ownedItemsInCollection: ownedItems,
      badge,
      tipText,
      hasSelectedPot: !!selectedPot,
      // demo 标记应当被设置
      demoFlag: localStorage.getItem('starlearn_plant_demo_mode'),
      demoDataSaved: !!localStorage.getItem('starlearn_plant_demo_state'),
      realDataUntouched: localStorage.getItem('starlearn_plants') === null,
    };
  });

  console.log('=== plant.html (演示模式) ===');
  console.log(JSON.stringify(result, null, 2));
  console.log('\nConsole errors:', errors.length ? errors.join('\n') : 'none');

  // 断言
  const fails = [];
  if (result.ownedCount !== '24') fails.push(`owned-count 期望 24，实得 ${result.ownedCount}`);
  if (result.seedNav !== '18') fails.push(`seed-count-nav 期望 18，实得 ${result.seedNav}`);
  if (result.demoFlag !== '1') fails.push(`demo flag 未设置: ${result.demoFlag}`);
  if (!result.demoDataSaved) fails.push('demo 数据未持久化');
  if (!result.realDataUntouched) fails.push('真实数据 key 被污染');
  if (!result.badge) fails.push('未显示演示数据角标');
  if (result.slots.length !== 3) fails.push(`期望 3 个槽位，实得 ${result.slots.length}`);
  if (result.slots[0].emoji !== '🌸') fails.push(`槽位 1 emoji 期望 🌸（已成熟樱花），实得 ${result.slots[0].emoji}`);
  if (result.slots[0].stage !== '3') fails.push(`槽位 1 stage 期望 3，实得 ${result.slots[0].stage}`);
  if (result.slots[2].emoji !== '🌱') fails.push(`槽位 3 应当为空（🌱），实得 ${result.slots[2].emoji}`);
  if (!result.weather.city?.includes('演示城市')) fails.push(`天气城市应包含「演示城市」，实得 ${result.weather.city}`);

  // 点击槽位 2（成长期彩虹玫瑰）→ 验证主面板切换
  await page.click('.plant-pot-wrapper[data-slot="1"]');
  await page.waitForTimeout(500);
  const slot2View = await page.evaluate(() => ({
    name: document.getElementById('plant-name')?.textContent,
    stage: document.getElementById('plant-stage')?.textContent,
    water: document.getElementById('water-value')?.textContent,
    nutrient: document.getElementById('nutrient-value')?.textContent,
    timer: document.getElementById('plant-timer')?.textContent,
  }));
  console.log('\n=== 点击槽位 2 后的主面板 ===');
  console.log(JSON.stringify(slot2View, null, 2));
  if (!slot2View.name?.includes('彩虹玫瑰')) fails.push(`槽位 2 名称应包含「彩虹玫瑰」，实得 ${slot2View.name}`);
  if (slot2View.timer === '--:--:--') fails.push('槽位 2 应当显示剩余时间');

  if (fails.length) {
    console.log('\n❌ FAIL:', fails.length, '处问题：');
    fails.forEach(f => console.log('  -', f));
    process.exit(1);
  } else {
    console.log('\n✅ 全部断言通过');
  }

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });