// 用真实 FastAPI 后端抓取 index.html 三个目标区域的真实渲染
// 手工运行: BASE_URL=http://127.0.0.1:8000 npx playwright test tests/frontend/e2e/ui-inspect.spec.js --project=chromium
// 默认 skip — 截图工具, 不参与 CI 套件
const { test } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SHOTS = path.resolve(__dirname, '../../../shots');
if (!fs.existsSync(SHOTS)) fs.mkdirSync(SHOTS, { recursive: true });

async function setup(page) {
  await page.addInitScript(() => {
    localStorage.setItem('starlearn_user', JSON.stringify({
      id: 'test_user', name: '测试用户', avatar: 'https://example.com/a.png',
    }));
    localStorage.setItem('starlearn_persona', 'patient_tutor');
  });
}

test.skip('Capture UI sections - real backend', async ({ page }) => {
  await setup(page);
  await page.setViewportSize({ width: 1920, height: 1600 });
  await page.goto('http://127.0.0.1:8000/index.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);

  // 强制让所有 sidebar 子节点可见
  await page.evaluate(() => {
    document.querySelectorAll('[id$="-section"], aside, .left-col, #profile-section, #radar-section').forEach(el => {
      el.style.cssText += '; width: auto !important; height: auto !important; overflow: visible !important; display: block !important; visibility: visible !important; opacity: 1 !important;';
    });
  });
  await page.waitForTimeout(500);

  await page.screenshot({ path: path.join(SHOTS, '01-full.png'), fullPage: true });

  // 抓 sidebar (整条)
  const sidebarHandle = await page.evaluateHandle(() => document.querySelector('aside'));
  if (sidebarHandle) {
    const el = sidebarHandle.asElement();
    if (el) await el.screenshot({ path: path.join(SHOTS, '02-sidebar.png') });
  }

  // 抓 profile section 单独 (8 tile)
  const profileHandle = await page.evaluateHandle(() => document.getElementById('profile-section'));
  if (profileHandle) {
    const el = profileHandle.asElement();
    if (el) await el.screenshot({ path: path.join(SHOTS, '03-profile.png') });
  }

  // 抓 radar section
  const radarHandle = await page.evaluateHandle(() => document.getElementById('radar-section'));
  if (radarHandle) {
    const el = radarHandle.asElement();
    if (el) await el.screenshot({ path: path.join(SHOTS, '04-radar.png') });
  }

  // 抓 control tower
  const towerHandle = await page.evaluateHandle(() => document.getElementById('track-a-container'));
  if (towerHandle) {
    const el = towerHandle.asElement();
    if (el) await el.screenshot({ path: path.join(SHOTS, '05-tower.png') });
  }

  // 关键状态
  const state = await page.evaluate(() => ({
    trackACollapsed: document.getElementById('track-a-container')?.classList.contains('collapsed'),
    trackAWidth: document.getElementById('track-a-container')?.getBoundingClientRect().width,
    radarCanvasVisible: !!document.getElementById('radar-chart') && document.getElementById('radar-chart').style.display !== 'none',
    profileContainerKids: document.getElementById('profile-container')?.children.length || 0,
    profileTileLabels: Array.from(document.querySelectorAll('#profile-container .profile-glass-tile')).map(el => el.textContent.trim().replace(/\s+/g, ' ')),
    agentSectionExists: !!document.getElementById('agent-section'),
    agentStatusCount: document.querySelectorAll('.agent-status-item').length,
    towerHeaderText: document.querySelector('.tower-header h2')?.textContent,
    towerHasContent: document.querySelectorAll('#track-a .flow-node, #tower-flow .flow-node, #tower-terminal').length,
    towerToggleBtnText: document.getElementById('tower-toggle')?.textContent,
    towerToggleBtnLabel: document.getElementById('tower-toggle')?.getAttribute('aria-label'),
  }));
  console.log('=== State:', JSON.stringify(state, null, 2));
});
