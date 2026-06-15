import { describe, it, expect, beforeAll } from 'vitest';
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
  it('activate 切换活动栏图标激活态', () => {
    document.body.insertAdjacentHTML('beforeend', `
      <div class="ide-shell">
        <aside class="ide-activity-bar">
          <button class="ide-activity-icon" data-panel="task">T</button>
          <button class="ide-activity-icon" data-panel="notes">N</button>
        </aside>
      </div>
    `);
    const ide = new CodeIDE(document.querySelector('.ide-shell'));
    ide.activate('task');
    expect(document.querySelector('[data-panel="task"]').dataset.active).toBe('true');
    expect(document.querySelector('[data-panel="notes"]').dataset.active).toBe('false');
    ide.activate('notes');
    expect(document.querySelector('[data-panel="notes"]').dataset.active).toBe('true');
  });
});
