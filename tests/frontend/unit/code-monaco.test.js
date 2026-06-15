import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('CodeMonaco.load', () => {
  beforeEach(() => {
    delete window.require;
    delete window.monaco;
    document.querySelectorAll('script[data-monaco-loader]').forEach(s => s.remove());
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
});
