/**
 * CodeIDE — IDE 工作台控制器
 * 管理活动栏路由、面板状态、拖拽逻辑、布局持久化。
 * 通过 window.CodeIDE 暴露单例。
 */
export class CodeIDE {
  constructor(shellEl, options = {}) {
    this.shell = shellEl;
    this.options = { storageKey: 'code_ide_layout', ...options };
    this.activePanel = null;
    this.activityIcons = [...shellEl.querySelectorAll('.ide-activity-icon')];
    this.bindActivityBar();
    this.restoreLayout();
  }

  bindActivityBar() {
    this.activityIcons.forEach(btn => {
      btn.addEventListener('click', () => this.activate(btn.dataset.panel));
    });
  }

  activate(panelKey) {
    if (!panelKey) return;
    this.activePanel = panelKey;
    this.activityIcons.forEach(btn => {
      btn.dataset.active = btn.dataset.panel === panelKey ? 'true' : 'false';
    });
    this.persistLayout();
    document.dispatchEvent(new CustomEvent('codeide:panel-change', {
      detail: { panel: panelKey }
    }));
  }

  persistLayout() {
    try {
      localStorage.setItem(this.options.storageKey, JSON.stringify({
        activePanel: this.activePanel,
      }));
    } catch {}
  }

  restoreLayout() {
    try {
      const raw = localStorage.getItem(this.options.storageKey);
      if (!raw) return;
      const { activePanel } = JSON.parse(raw);
      if (activePanel) this.activate(activePanel);
    } catch {}
  }
}

if (typeof window !== 'undefined') {
  window.CodeIDE = CodeIDE;
}
