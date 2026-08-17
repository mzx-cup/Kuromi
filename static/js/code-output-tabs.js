/**
 * CodeOutputTabs — 输出面板 Tab 化
 * 将现有 .output-panel 改造为 4 Tab：运行结果 / 执行流 / 测试用例 / 回放时间轴。
 * 第一个 Tab（运行结果）接收面板现有内容，其余为占位。
 */
const TAB_LABELS = ['运行结果', '执行流', '测试用例', '回放时间轴'];

export function mountOutputTabs(panelEl) {
  const oldHeader = panelEl.querySelector('.output-header');
  if (oldHeader) oldHeader.style.display = 'none';

  const tabBar = document.createElement('div');
  tabBar.className = 'output-tab-bar';
  tabBar.setAttribute('role', 'tablist');
  TAB_LABELS.forEach((label, idx) => {
    const tab = document.createElement('button');
    tab.className = 'output-tab';
    tab.textContent = label;
    tab.dataset.tabKey = ['run', 'flow', 'test', 'replay'][idx];
    tab.dataset.active = idx === 0 ? 'true' : 'false';
    tab.setAttribute('role', 'tab');
    tab.addEventListener('click', () => activateTab(idx));
    tabBar.appendChild(tab);
  });
  panelEl.insertBefore(tabBar, panelEl.firstChild);

  const body = document.createElement('div');
  body.className = 'output-tab-bodies';
  while (panelEl.children.length > 1) {
    body.appendChild(panelEl.children[1]);
  }
  panelEl.appendChild(body);

  const placeholders = {
    flow: '执行流可视化将在 Sprint 2 接入',
    test: '测试用例比对将在 Sprint 3 接入',
    replay: '解题回放将在 Sprint 2 接入',
  };
  Object.entries(placeholders).forEach(([key, text]) => {
    const ph = document.createElement('div');
    ph.className = 'output-tab-body';
    ph.dataset.tabBody = key;
    ph.style.display = 'none';
    ph.textContent = text;
    body.appendChild(ph);
  });

  function activateTab(idx) {
    [...tabBar.children].forEach((t, i) => {
      t.dataset.active = i === idx ? 'true' : 'false';
    });
    [...body.children].forEach((b, i) => {
      b.style.display = i === idx ? '' : 'none';
    });
  }
}

if (typeof window !== 'undefined') window.mountOutputTabs = mountOutputTabs;
