/**
 * Visual verification for the 知识生态 tree-root layout on hub.html.
 * Runs without the backend — serves the static html/css/js dirs over a local
 * http server, opens the page, switches to the "学习" tab, and screenshots the
 * #section-knowledge-tree element.
 *
 * Usage: node scripts/verify-knowledge-tree.js
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const PORT = 8766;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.json': 'application/json',
  '.woff2': 'font/woff2',
};

function serve() {
  return http.createServer((req, res) => {
    let urlPath = decodeURIComponent(req.url.split('?')[0]);
    if (urlPath === '/' ) urlPath = '/hub.html';
    const filePath = path.join(ROOT, urlPath);

    // Stub /api/* endpoints with a "no data" response so the JS falls into the
    // static tree branch (drawTreeConnections), which is the exact code path
    // shown in the screenshot bug.
    if (urlPath.startsWith('/api/')) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, nodes: [] }));
      return;
    }

    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('Not found: ' + filePath);
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      res.end(data);
    });
  }).listen(PORT);
}

(async () => {
  const server = serve();
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') console.log('[browser error]', msg.text());
  });

  // Seed a fake user so loadKnowledgeNodes doesn't bail before fetch
  await page.addInitScript(() => {
    localStorage.setItem('starlearn_user', JSON.stringify({
      id: 'demo-user', name: '李同学', hasCompletedAssessment: true,
    }));
    localStorage.setItem('starlearn_onboarding_completed', '1');
    localStorage.setItem('hub_onboarding_completed', '1');
  });

  await page.goto(`http://localhost:${PORT}/hub.html`, { waitUntil: 'networkidle' });

  // Switch to the 学习 tab where the knowledge ecosystem lives
  await page.evaluate(() => {
    // Dismiss onboarding tour & any overlays first
    document.querySelectorAll('.onboarding-overlay, .onboarding-tour, .driver-overlay, .modal-overlay').forEach(el => el.remove());
    localStorage.setItem('starlearn_onboarding_completed', '1');
    localStorage.setItem('hub_onboarding_completed', '1');

    const btn = document.querySelector('[data-tab="learn"], .tab-btn[data-target="tab-learn"]');
    if (btn) btn.click();
    const panel = document.getElementById('tab-learn');
    if (panel) {
      panel.style.display = 'block';
      panel.classList.add('active');
    }
    // Also hide tab-overview if it shares the same visibility model
    document.querySelectorAll('.tab-panel').forEach(p => {
      if (p.id !== 'tab-learn') p.style.display = 'none';
    });
  });

  await page.waitForTimeout(800);

  const section = await page.locator('#section-knowledge-tree');
  await section.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);

  // Sanity: read the rendered node positions
  const report = await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll('#holoNodes .holo-node'));
    const c = document.getElementById('holoNodes').getBoundingClientRect();
    return {
      container: { w: Math.round(c.width), h: Math.round(c.height) },
      nodes: nodes.map(n => {
        const r = n.getBoundingClientRect();
        return {
          id: n.dataset.id,
          x: Math.round(r.left - c.left + r.width / 2),
          y: Math.round(r.top - c.top + r.height / 2),
        };
      }),
      svgPaths: document.querySelectorAll('#holoConnections path').length,
    };
  });
  console.log('--- layout report ---');
  console.log(JSON.stringify(report, null, 2));

  const outDir = path.join(ROOT, 'test-results');
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, 'knowledge-tree-verify.png');
  await section.screenshot({ path: out });
  console.log('Screenshot:', out);

  await browser.close();
  server.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
