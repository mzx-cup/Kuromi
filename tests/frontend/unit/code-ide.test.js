import { describe, it, expect, beforeAll, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { CodeIDE } from '../../../js/code-ide.js';

const CSS_PATH = path.resolve(__dirname, '../../../css/code-ide.css');

describe('code-ide.css', () => {
  let cssText = '';

  beforeAll(() => {
    cssText = fs.readFileSync(CSS_PATH, 'utf-8');
    const style = document.createElement('style');
    style.setAttribute('data-test', 'code-ide');
    style.textContent = cssText;
    document.head.appendChild(style);
  });

  it('活动栏选择器存在', () => {
    const styleEl = document.querySelector('style[data-test="code-ide"]');
    expect(styleEl, 'style element must be injected').toBeTruthy();
    // jsdom does parse the CSS into a CSSStyleSheet on the <style> element
    const sheet = styleEl.sheet;
    expect(sheet, 'sheet must be parsed').toBeTruthy();
    const rules = [...sheet.cssRules].map(r => r.selectorText).filter(Boolean);
    expect(rules).toContain('.ide-activity-bar');
    expect(rules).toContain('.ide-activity-icon');
  });
});

describe('CodeIDE', () => {
  beforeEach(() => {
    // 隔离：清空 DOM 与 localStorage，避免用例间相互污染
    document.body.innerHTML = '';
    localStorage.clear();
  });

  afterEach(() => {
    // 收尾：再次清理，防止监听器/节点残留
    document.body.innerHTML = '';
    localStorage.clear();
  });

  function buildShell() {
    document.body.insertAdjacentHTML('beforeend', `
      <div class="ide-shell">
        <aside class="ide-activity-bar">
          <button class="ide-activity-icon" data-panel="task">T</button>
          <button class="ide-activity-icon" data-panel="notes">N</button>
        </aside>
      </div>
    `);
    return document.querySelector('.ide-shell');
  }

  it('activate 切换活动栏图标激活态', () => {
    const ide = new CodeIDE(buildShell());
    ide.activate('task');
    expect(document.querySelector('[data-panel="task"]').dataset.active).toBe('true');
    expect(document.querySelector('[data-panel="notes"]').dataset.active).toBe('false');
    ide.activate('notes');
    expect(document.querySelector('[data-panel="notes"]').dataset.active).toBe('true');
  });

  it('click 活动栏图标触发激活', () => {
    const ide = new CodeIDE(buildShell());
    const taskBtn = document.querySelector('[data-panel="task"]');
    taskBtn.click();
    expect(taskBtn.dataset.active).toBe('true');
    expect(ide.activePanel).toBe('task');
    expect(document.querySelector('[data-panel="notes"]').dataset.active).toBe('false');
  });

  it('activate 派发 codeide:panel-change CustomEvent', () => {
    const shell = buildShell();
    const ide = new CodeIDE(shell);
    const handler = makeSpy();
    document.addEventListener('codeide:panel-change', handler);
    ide.activate('task');
    expect(handler.calls.length).toBe(1);
    expect(handler.calls[0].detail).toEqual({ panel: 'task' });
    document.removeEventListener('codeide:panel-change', handler);
  });

  it('persistLayout 写入 localStorage', () => {
    const ide = new CodeIDE(buildShell());
    ide.activate('task');
    const raw = localStorage.getItem('code_ide_layout');
    expect(raw, 'localStorage entry must exist').toBeTruthy();
    const parsed = JSON.parse(raw);
    expect(parsed.activePanel).toBe('task');
  });
});

// 轻量 helper：构造一个可断言的间谍函数，避免在测试文件里再 import vi
function makeSpy() {
  const fn = (event) => {
    fn.calls.push(event);
  };
  fn.calls = [];
  return fn;
}
