import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('mountOutputTabs', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('创建 4 个 Tab + 第一个 Tab 接收初始内容', async () => {
    document.body.insertAdjacentHTML('beforeend', `
      <div class="output-panel">
        <div class="output-header"><span>运行结果</span></div>
        <div class="output-content" id="out">initial stdout</div>
      </div>
    `);
    const { mountOutputTabs } = await import('../../../js/code-output-tabs.js');
    mountOutputTabs(document.querySelector('.output-panel'));
    const tabs = document.querySelectorAll('.output-tab');
    expect(tabs.length).toBe(4);
    expect(tabs[0].textContent).toContain('运行');
    expect(tabs[0].dataset.active).toBe('true');
    expect(document.getElementById('out').textContent).toBe('initial stdout');
  });
});
