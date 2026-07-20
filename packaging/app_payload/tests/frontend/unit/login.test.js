/**
 * Login page quickLogin — 演示账号登录 (Phase 1.4)
 *
 * Verifies the frontend "快速演示登录" buttons now call
 * /api/auth/demo-login (with role query param) instead of the old
 * /api/login/guest endpoint.
 *
 * Strategy: login.js declares functions at top-level, which in a regular
 * <script> tag attach to window but in vitest's ES-module context do not.
 * We read the source and inspect it for the new URL + 403 handling.
 *
 * 运行: npx vitest run tests/frontend/unit/login.test.js
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const LOGIN_JS = resolve(__dirname, '../../../js/login.js');

let loginSource;
let quickLoginSource;

beforeEach(() => {
  loginSource = readFileSync(LOGIN_JS, 'utf-8');
  quickLoginSource = loginSource.match(
    /async function quickLogin\(name\) \{[\s\S]*?(?=\ndocument\.getElementById)/
  )?.[0] || '';
});

describe('login.js — quickLogin URL routing', () => {
  it('应调用 /api/auth/demo-login 而非 /api/login/guest', () => {
    expect(quickLoginSource).toMatch(/\/api\/auth\/demo-login/);
    expect(quickLoginSource).not.toMatch(/\/api\/login\/guest/);
  });

  it('应使用 role 查询参数传递教师/学生/管理员', () => {
    expect(quickLoginSource).toMatch(
      /fetch\(`\$\{API_URL\}\/auth\/demo-login\?role=\$\{encodeURIComponent\(name\)\}`/
    );
  });

  it('应先处理 403 响应并提示演示登录已禁用', () => {
    expect(quickLoginSource).toMatch(
      /if\s*\(res\.status\s*===\s*403\)\s*\{[\s\S]*?ALLOW_DEMO_LOGIN=true[\s\S]*?return;[\s\S]*?\}\s*if\s*\(!res\.ok\)/
    );
    expect(quickLoginSource).toMatch(/演示账号登录已禁用/);
  });

  it('应在响应中保存 isDemo 标记到 localStorage', () => {
    expect(quickLoginSource).toMatch(
      /if\s*\(data\.isDemo\)\s*\{\s*localStorage\.setItem\(['"]starlearn_is_demo['"],\s*['"]true['"]\);\s*\}/
    );
  });

  it('网络失败时不应回退到绕过开关的本地演示账号', () => {
    const catchBlock = quickLoginSource.match(/catch\s*\(e\)\s*\{([\s\S]*?)\n\s*\}/)?.[1] || '';

    expect(catchBlock).toMatch(/ALLOW_DEMO_LOGIN=true/);
    expect(catchBlock).toMatch(/return;/);
    expect(catchBlock).not.toMatch(/dicebear|starlearn_user/);
  });

  it('应在成功后跳转 /index.html', () => {
    expect(quickLoginSource).toMatch(
      /catch\s*\(e\)\s*\{[\s\S]*?return;[\s\S]*?\}\s*window\.location\.href\s*=\s*['"]\/index\.html['"];/
    );
  });
});