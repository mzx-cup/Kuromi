import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('CodeMonaco.load', () => {
  beforeEach(() => {
    delete window.require;
    delete window.monaco;
    document.querySelectorAll('script[data-monaco-loader]').forEach(s => s.remove());
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it('加载后挂载 window.monaco 并返回 promise', async () => {
    // mock require — 模拟 Monaco AMD loader 行为：调用 cb 之前先把 monaco 挂到 window 上
    // （这是 Monaco 真实行为：editor.main 执行后会写 window.monaco）
    const requireMock = vi.fn((deps, cb) => {
      window.monaco = { editor: {}, languages: {} };
      cb({ editor: {}, languages: {} });
    });
    window.require = requireMock;
    // mock the loader script append
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = document.createElementNS('http://www.w3.org/1999/xhtml', tag);
      if (tag === 'script') {
        el.setAttribute('data-monaco-loader', 'true');
        setTimeout(() => el.onload && el.onload(), 0);
      }
      return el;
    });

    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const m = await CodeMonaco.load();
    expect(m).toBeTruthy();
    expect(window.monaco).toBeTruthy();
  });

  it('window.monaco 已存在时直接返回缓存', async () => {
    const cached = { editor: { create: () => {} }, languages: {} };
    window.monaco = cached;
    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const m = await CodeMonaco.load();
    expect(m).toBe(cached);
  });

  it('并发调用返回同一个 Promise', async () => {
    window.monaco = undefined;
    let scriptLoadTriggered = 0;
    const requireMock = vi.fn((deps, cb) => {
      window.monaco = { editor: {}, languages: {} };
      cb(window.monaco);
    });
    window.require = requireMock;
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = document.createElementNS('http://www.w3.org/1999/xhtml', tag);
      if (tag === 'script') {
        el.setAttribute('data-monaco-loader', 'true');
        if (scriptLoadTriggered++ === 0) {
          setTimeout(() => el.onload && el.onload(), 0);
        }
        // 第二次 mock 调用直接拒绝（不该发生）
      }
      return el;
    });

    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const [m1, m2, m3] = await Promise.all([
      CodeMonaco.load(),
      CodeMonaco.load(),
      CodeMonaco.load(),
    ]);
    expect(m1).toBe(m2);
    expect(m2).toBe(m3);
    expect(scriptLoadTriggered).toBe(1);  // 只创建了 1 个 script 标签
  });

  it('onerror 还原 pre-existing window.require', async () => {
    const preExistingRequire = vi.fn();  // 假装页面已有 require.js 之类
    window.require = preExistingRequire;
    delete window.monaco;

    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = document.createElementNS('http://www.w3.org/1999/xhtml', tag);
      if (tag === 'script') {
        el.setAttribute('data-monaco-loader', 'true');
        setTimeout(() => el.onerror && el.onerror(), 0);  // 触发失败路径
      }
      return el;
    });

    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    await expect(CodeMonaco.load()).rejects.toThrow('Monaco loader failed');
    expect(window.require).toBe(preExistingRequire);  // 还原成功
  });
});
