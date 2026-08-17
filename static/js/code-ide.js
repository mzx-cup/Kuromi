/**
 * CodeIDE — IDE 工作台控制器
 * 管理活动栏路由、面板激活状态与布局持久化。
 * 调用方自行决定是否实例化为单例（既支持 ESM 命名导入，也通过 window.CodeIDE 暴露全局）。
 *
 * 后续任务预告：
 * - Task 3：新增 resizer 拖拽逻辑
 * - Task 4：新增面板宽度/折叠持久化
 */
const RESIZER_HANDLES = new WeakSet();

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

  /**
   * 激活指定面板，更新活动栏图标激活态（默认还会持久化并派发事件）。
   * @param {string} panelKey - 面板标识
   * @param {{silent?: boolean}} [opts] - silent=true 时跳过持久化与事件派发（用于恢复布局）
   */
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

  /**
   * 将当前布局状态写入 localStorage。
   * panelWidths / panelCollapsed 使用浅合并，实例值优先于已存储值，
   * 保证其他代码路径写入的字段不会被整体覆盖。
   */
  persistLayout() {
    try {
      const raw = localStorage.getItem(this.options.storageKey);
      const data = raw ? JSON.parse(raw) : {};
      data.activePanel = this.activePanel;
      data.panelWidths = { ...(data.panelWidths || {}), ...(this.panelWidths || {}) };
      data.panelCollapsed = { ...(data.panelCollapsed || {}), ...(this.panelCollapsed || {}) };
      localStorage.setItem(this.options.storageKey, JSON.stringify(data));
    } catch {}
  }

  /**
   * 设置面板宽度（持久化到 localStorage）。
   * @param {string} panelKey - 面板标识
   * @param {number} width - 像素值；非有限数字（NaN/Infinity/负数/0）将被忽略
   */
  setPanelWidth(panelKey, width) {
    if (!Number.isFinite(width) || width <= 0) return;
    this.panelWidths = this.panelWidths || {};
    this.panelWidths[panelKey] = width;
    this.persistLayout();
  }

  /**
   * 设置面板折叠状态（持久化到 localStorage 并派发 codeide:panel-collapse 事件）。
   * @param {string} panelKey - 面板标识
   * @param {boolean} collapsed - true = 折叠，false = 展开
   */
  setPanelCollapsed(panelKey, collapsed) {
    const value = Boolean(collapsed);
    this.panelCollapsed = this.panelCollapsed || {};
    this.panelCollapsed[panelKey] = value;
    this.persistLayout();
    document.dispatchEvent(new CustomEvent('codeide:panel-collapse', {
      detail: { panel: panelKey, collapsed: value }
    }));
  }

  /**
   * 从 localStorage 恢复布局状态（面板宽度 / 折叠态 / 当前激活面板）。
   * panelWidths 与 panelCollapsed 独立恢复，不依赖 activePanel 是否存在；
   * activePanel 使用过期面板防御性检查，避免激活已下线的面板。
   */
  restoreLayout() {
    try {
      const raw = localStorage.getItem(this.options.storageKey);
      if (!raw) return;
      const data = JSON.parse(raw);
      // Restore widths/collapsed (independent of activePanel)
      if (data.panelWidths && typeof data.panelWidths === 'object') {
        this.panelWidths = { ...data.panelWidths };
      }
      if (data.panelCollapsed && typeof data.panelCollapsed === 'object') {
        this.panelCollapsed = { ...data.panelCollapsed };
      }
      // Restore activePanel (with stale-panel guard)
      if (data.activePanel) {
        const iconStillExists = this.activityIcons.some(b => b.dataset.panel === data.activePanel);
        if (iconStillExists) {
          this.activate(data.activePanel, { silent: true });
        } else {
          localStorage.removeItem(this.options.storageKey);
        }
      }
    } catch {}
  }

  /**
   * 绑定 resizer 拖拽手柄。同一个 handleEl 二次调用为 no-op（防止重复挂载）。
   * @param {HTMLElement} handleEl - 拖拽手柄 DOM（需带 data-target 与可选 data-panel）
   * @param {number} minWidth - 最小宽度（像素）
   * @param {number} maxWidth - 最大宽度（像素）
   * @param {(width: number) => void} onResize - 拖拽过程中回调，传入夹紧后的宽度
   */
  attachResizer(handleEl, minWidth, maxWidth, onResize) {
    if (RESIZER_HANDLES.has(handleEl)) return;
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
      if (!targetEl) return;
      // 持久化：找到该 resizer 关联的 panel key
      const panelKey = handleEl.dataset.panel || 'coach';
      this.setPanelWidth(panelKey, parseFloat(targetEl.style.width));
    };
    handleEl.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startX = e.clientX;
      startWidth = targetEl ? targetEl.getBoundingClientRect().width : 0;
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
    RESIZER_HANDLES.add(handleEl);
  }

  detachResizer(handleEl) {
    // Future Task 14 will use this for teardown. For now, just clear the guard.
    // The actual removeEventListener needs a stored reference — defer until Task 14.
    RESIZER_HANDLES.delete(handleEl);
  }
}

if (typeof window !== 'undefined') {
  window.CodeIDE = CodeIDE;
}
