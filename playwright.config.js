/**
 * Playwright 配置 — E2E / 无障碍 / 视觉回归测试
 *
 * 运行:
 *   npx playwright test                                # 所有 E2E 测试
 *   npx playwright test --project=chromium             # 仅 Chrome
 *   npx playwright test tests/frontend/e2e/smoke.spec.js
 *   npx playwright test tests/frontend/a11y/a11y.spec.js
 *   npx playwright show-report                         # 查看 HTML 报告
 *
 * 首次使用:
 *   npx playwright install                             # 安装浏览器
 */

const { defineConfig, devices } = require('@playwright/test');

// 项目运行的开发服务器地址（根据实际情况修改）
const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

module.exports = defineConfig({
  testDir: './tests/frontend',

  // 每个测试超时 30 秒
  timeout: 30000,

  // 全局 expect 超时 10 秒
  expect: { timeout: 10000 },

  // 失败重试（CI 中启用）
  retries: process.env.CI ? 1 : 0,

  // 并行 worker 数
  workers: process.env.CI ? 2 : 4,

  // 报告器
  reporter: [
    ['html', { outputFolder: 'tests/frontend/reports/playwright-html' }],
    ['json', { outputFile: 'tests/frontend/reports/playwright.json' }],
    ['list'],
  ],

  use: {
    baseURL: BASE_URL,
    // 截图：仅在失败时
    screenshot: 'only-on-failure',
    // 视频：仅在失败时保留
    video: 'retain-on-failure',
    // 追踪：仅在首次重试时
    trace: 'on-first-retry',
    // 默认视口
    viewport: { width: 1440, height: 900 },
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // 可选：在多个浏览器中运行
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    // 移动端视口测试
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // 全局 setup：启动开发服务器
  webServer: {
    command: 'python -m http.server 8000 --directory .',
    url: 'http://localhost:8000',
    reuseExistingServer: !process.env.CI,
    timeout: 10000,
  },
});
