/**
 * L3 集成测试 — 验证清点报告产物
 *
 * 由于本环境未装 Playwright 浏览器, 此测试在 CI 环境就绪后启用.
 * 验证内容:
 *   1. 报告文件存在
 *   2. 报告含 P0/P1/P2/P3 四个标题
 *   3. 报告含「报告遗留问题解决状态」块, 3 项全 [x]
 *   4. 报告含至少 1 个 P0 项的具体 file:line
 *
 * 运行 (环境就绪后):
 *   npx playwright test tests/frontend/e2e/tech-debt-inventory.spec.js
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '../../..');
const REPORT_PATH = path.join(
  PROJECT_ROOT,
  'docs/superpowers/notes/frontend-tech-debt-2026-06-08.md',
);

test.describe('Frontend Tech Debt Inventory Report', () => {
  test('report file exists', () => {
    expect(fs.existsSync(REPORT_PATH)).toBe(true);
  });

  test('report contains all priority sections', () => {
    const content = fs.readFileSync(REPORT_PATH, 'utf-8');
    expect(content).toMatch(/## P0 阻塞项/);
    expect(content).toMatch(/## P1 重要项/);
    expect(content).toMatch(/## P2 改进项/);
    expect(content).toMatch(/## P3 记录备查/);
  });

  test('report marks all 3 legacy issues resolved', () => {
    const content = fs.readFileSync(REPORT_PATH, 'utf-8');
    const matches = content.match(/\[x\] 报告遗留 \d/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(3);
  });

  test('P0 items have file:line references', () => {
    const content = fs.readFileSync(REPORT_PATH, 'utf-8');
    // 简易检查: P0 章节含 \d+:\d+ 形式
    const p0Section = content.split('## P0 阻塞项')[1]?.split('## P1')[0] || '';
    expect(p0Section).toMatch(/\d+:\d+/);
  });
});
