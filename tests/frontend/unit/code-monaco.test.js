import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

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

describe('CodeMonaco.create', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it('create 接收 textarea 返回 editor handle', async () => {
    document.body.insertAdjacentHTML('beforeend', `<textarea id="t"></textarea>`);
    // stub monaco
    const fakeEditor = {
      setValue: vi.fn(),
      getValue: vi.fn(() => 'hi'),
      onDidChangeModelContent: vi.fn(() => ({ dispose: vi.fn() })),
      dispose: vi.fn(),
    };
    window.monaco = { editor: { create: vi.fn(() => fakeEditor) } };

    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('t'), { value: 'hello' });
    expect(handle.getValue()).toBe('hi');
    expect(handle.editor.setValue).toHaveBeenCalledWith('hello');
    handle.dispose();
    expect(fakeEditor.dispose).toHaveBeenCalled();
  });

  it('dispose 双调用安全（不抛错）', async () => {
    document.body.insertAdjacentHTML('beforeend', `<textarea id="t"></textarea>`);
    const fakeEditor = {
      setValue: vi.fn(),
      getValue: vi.fn(() => ''),
      onDidChangeModelContent: vi.fn(() => ({ dispose: vi.fn() })),
      dispose: vi.fn(),
    };
    window.monaco = { editor: { create: vi.fn(() => fakeEditor) } };
    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('t'));
    handle.dispose();
    expect(() => handle.dispose()).not.toThrow();
    expect(fakeEditor.dispose).toHaveBeenCalledTimes(1);
  });

  it('window.monaco 缺失时抛错', async () => {
    document.body.insertAdjacentHTML('beforeend', `<textarea id="t"></textarea>`);
    window.monaco = undefined;
    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    expect(() => CodeMonaco.create(document.getElementById('t')))
      .toThrow(/monaco not loaded/);
  });

  it('textarea 未挂载到 DOM 时抛错', async () => {
    window.monaco = { editor: { create: vi.fn(() => ({
      setValue: vi.fn(), getValue: vi.fn(() => ''),
      onDidChangeModelContent: vi.fn(() => ({ dispose: vi.fn() })),
      dispose: vi.fn(),
    })) } };
    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const detached = document.createElement('textarea');
    expect(() => CodeMonaco.create(detached)).toThrow(/must be attached/);
  });
});

describe('typeCodeToEditor Monaco integration', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it('传入 handle 时,完成打字后触发 code-typing-done 事件 + 同步 setValue', async () => {
    document.body.insertAdjacentHTML('beforeend', `
      <div id="overlay" style="display:none"></div>
      <textarea id="code-input"></textarea>
      <div id="line-numbers"></div>
      <div id="output-content"></div>
      <div id="status-lines"></div>
      <div id="status-chars"></div>
      <div id="status-todos"></div>
      <div id="status-cursor"></div>
      <div id="status-font"></div>
      <div id="save-indicator"></div>
      <div id="editor-status-bar"></div>
      <div id="output-meta"></div>
      <div id="assistant-subtitle"></div>
      <div id="status-badge"></div>
      <div id="status-text"></div>
      <div id="assistant-quick-actions"></div>
      <div id="message-container"></div>
      <div id="assistant-input"></div>
      <div id="send-btn"></div>
      <div id="terminal-state"><span></span><span></span></div>
      <div id="terminal-runtime"></div>
      <div id="terminal-mode"></div>
      <div id="terminal-token"></div>
      <div id="terminal-cpu"></div>
    `);
    const setValueCalls = [];
    const fakeEditor = {
      setValue: (v) => setValueCalls.push(v),
      getValue: () => '',
      onDidChangeModelContent: () => ({ dispose: () => {} }),
      dispose: () => {},
    };
    window.monaco = { editor: { create: () => fakeEditor } };
    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('code-input'));

    // 加载 js/code.js 到当前 jsdom 中，使 window.typeCodeToEditor 可用。
    // code.js 是纯脚本（非 ESM），jsdom 默认不执行 appendChild 注入的 <script>，
    // 且 code.js 依赖 DOMContentLoaded 才执行 cacheElements()。
    // 这里用 vm.runInContext 模拟脚本执行，并手动调用 cacheElements()。
    // vm context 需要补齐 code.js 引用的全局（CustomEvent / Event 等），
    // 这些在真实浏览器中由 window 提供。
    const codeSrc = fs.readFileSync(
      path.resolve(__dirname, '../../../js/code.js'),
      'utf8',
    );
    const ctx = {
      window,
      document,
      console,
      setTimeout,
      clearTimeout,
      setInterval,
      clearInterval,
      CustomEvent,
      Event,
      requestAnimationFrame: window.requestAnimationFrame || ((cb) => setTimeout(cb, 0)),
    };
    ctx.window.document = document;
    ctx.window.console = console;
    vm.createContext(ctx);
    vm.runInContext(codeSrc, ctx);
    // 真实页面在 DOMContentLoaded 时调用 cacheElements()，
    // jsdom 不会自动 fire DOMContentLoaded，所以手动调用。
    vm.runInContext('cacheElements()', ctx);

    expect(typeof window.typeCodeToEditor).toBe('function');

    let done = false;
    let doneDetail = null;
    document.addEventListener('code-typing-done', (e) => {
      done = true;
      doneDetail = e.detail;
    });

    await window.typeCodeToEditor('print(1)\n', { handle });

    expect(done).toBe(true);
    expect(doneDetail).toBeTruthy();
    expect(doneDetail.code).toBe('print(1)\n');
    expect(setValueCalls.length).toBeGreaterThan(0);
    // 最后一次 setValue 应包含完整代码（打字结束时的状态）
    expect(setValueCalls[setValueCalls.length - 1]).toBe('print(1)\n');

    handle.dispose();
  });

  it('被取消时（typingTicket 不一致）不触发 code-typing-done', async () => {
    // 锁定契约：js/code.js:1386-1388 的早返回会抑制事件。
    // 任何把 dispatch 移到循环守卫上方的重构都会让本测试失败。
    //
    // 实现要点：
    // - 复用上一个测试的 DOM + vm.runInContext 装载方式。
    // - chunkSize = 8（live=false, 长度 < 900），'a\n' × 20 = 40 字符，
    //   至少需要 4-5 个 chunk，每个之间 await sleep(4)，给取消留出窗口。
    // - state 是 vm context 中的模块私有变量；在 vm context 内修改它
    //   会被 typeCodeToEditor 通过闭包看到。
    // - 不可在 host window 上直接取消（cancelTypingAnimation 未挂到 window），
    //   所以走 vm.runInContext('state.typingTicket += 1', ctx) 后门。
    document.body.insertAdjacentHTML('beforeend', `
      <div id="overlay" style="display:none"></div>
      <textarea id="code-input"></textarea>
      <div id="line-numbers"></div>
      <div id="output-content"></div>
      <div id="status-lines"></div>
      <div id="status-chars"></div>
      <div id="status-todos"></div>
      <div id="status-cursor"></div>
      <div id="status-font"></div>
      <div id="save-indicator"></div>
      <div id="editor-status-bar"></div>
      <div id="output-meta"></div>
      <div id="assistant-subtitle"></div>
      <div id="status-badge"></div>
      <div id="status-text"></div>
      <div id="assistant-quick-actions"></div>
      <div id="message-container"></div>
      <div id="assistant-input"></div>
      <div id="send-btn"></div>
      <div id="terminal-state"><span></span><span></span></div>
      <div id="terminal-runtime"></div>
      <div id="terminal-mode"></div>
      <div id="terminal-token"></div>
      <div id="terminal-cpu"></div>
    `);
    const setValueCalls = [];
    const fakeEditor = {
      setValue: (v) => setValueCalls.push(v),
      getValue: () => '',
      onDidChangeModelContent: () => ({ dispose: () => {} }),
      dispose: () => {},
    };
    window.monaco = { editor: { create: () => fakeEditor } };
    const { CodeMonaco } = await import('../../../js/code-monaco.js');
    const handle = CodeMonaco.create(document.getElementById('code-input'));

    const codeSrc = fs.readFileSync(
      path.resolve(__dirname, '../../../js/code.js'),
      'utf8',
    );
    const ctx = {
      window,
      document,
      console,
      setTimeout,
      clearTimeout,
      setInterval,
      clearInterval,
      CustomEvent,
      Event,
      requestAnimationFrame: window.requestAnimationFrame || ((cb) => setTimeout(cb, 0)),
    };
    ctx.window.document = document;
    ctx.window.console = console;
    vm.createContext(ctx);
    vm.runInContext(codeSrc, ctx);
    vm.runInContext('cacheElements()', ctx);

    expect(typeof window.typeCodeToEditor).toBe('function');

    let done = false;
    let doneDetail = null;
    document.addEventListener('code-typing-done', (e) => {
      done = true;
      doneDetail = e.detail;
    });

    const code = 'a\n'.repeat(20); // 40 chars, ~5 chunks of 8
    // 不 await —— fire and forget；我们要中途取消。
    const typingPromise = window.typeCodeToEditor(code, { handle });

    // 等几毫秒让至少 1-2 个 chunk 完成（每次 await sleep(4)）。
    await new Promise((resolve) => setTimeout(resolve, 8));

    // 通过 vm context 后门使 typingTicket 失配，模拟 cancelTypingAnimation() 行为。
    vm.runInContext('state.typingTicket += 1', ctx);

    // 现在 typeCodeToEditor 应在下一次循环守卫检查时早返回 false。
    const result = await typingPromise;

    expect(result).toBe(false);
    expect(done).toBe(false);
    expect(doneDetail).toBe(null);
    // 部分写入：setValue 被调用过，但少于完整 5 个 chunk。
    expect(setValueCalls.length).toBeGreaterThan(0);
    expect(setValueCalls.length).toBeLessThan(5);
    // 最后一次 setValue 不应等于完整 code —— 证明事件触发前被打断。
    expect(setValueCalls[setValueCalls.length - 1]).not.toBe(code);

    handle.dispose();
  });
});
