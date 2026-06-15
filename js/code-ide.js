/**
 * CodeIDE — IDE 工作台控制器
 * 管理活动栏路由、面板激活状态与布局持久化。
 * 调用方自行决定是否实例化为单例（既支持 ESM 命名导入，也通过 window.CodeIDE 暴露全局）。
 *
 * 后续任务预告：
 * - Task 3：新增 resizer 拖拽逻辑
 * - Task 4：新增面板宽度/折叠持久化
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

  activate(panelKey, { silent = false } = {}) {
    if (!panelKey) return;
    this.activePanel = panelKey;
    this.activityIcons.forEach(btn => {
      btn.dataset.active = btn.dataset.panel === panelKey ? 'true' : 'false';
    });
    if (silent) return;
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
      if (!activePanel) return;
      // 防御性：localStorage 中可能保存了已下线的面板（如 'old-feature'），
      // 此时若直接 activate 会清空所有图标的激活态但仍抛出 panel-change 事件。
      // 仅当对应的活动栏图标仍然存在时才恢复，否则丢弃过期值。
      const iconStillExists = this.activityIcons.some(b => b.dataset.panel === activePanel);
      if (iconStillExists) {
        this.activate(activePanel, { silent: true });
      } else {
        localStorage.removeItem(this.options.storageKey);
      }
    } catch {}
  }

  attachResizer(handleEl, minWidth, maxWidth, onResize) {
    let startX = 0;
    let startWidth = 0;
    let targetEl = null;
    const targetSelector = handleEl.dataset.target;
    if (targetSelector) {
      targetEl = handleEl.closest('.ide-shell')?.querySelector(targetSelector)
              || document.querySelector(targetSelector);
    }

    const onMove = (e) => {
      const dx = e.clientX - startX;
      const next = Math.max(minWidth, Math.min(maxWidth, startWidth + dx));
      if (targetEl) targetEl.style.width = `${next}px`;
      onResize(next);
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    handleEl.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startX = e.clientX;
      startWidth = targetEl ? targetEl.getBoundingClientRect().width : 0;
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }
}

if (typeof window !== 'undefined') {
  window.CodeIDE = CodeIDE;
}
