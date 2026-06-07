/**
 * 看板娘 核心桥接层 v3 — 小星角色 ↔ Alpine 面板
 *
 * 职责:
 *   1. 空闲检测 (5分钟无操作 → 触发问候)
 *   2. Toast 通知系统 (面板关闭时显示)
 *   3. 键盘快捷键 (Ctrl+Shift+K 切换面板)
 *   4. 暴露 window.MascotContext 给对话
 *   5. 面板状态 → 角色状态同步桥接
 *
 * 注意: 点击事件、角色表情、粒子特效现在由 kanban.js v3 直接管理。
 *       本文件专注于跨组件协调和通知基础设施。
 */
(function() {
  'use strict';

  const kanban = document.querySelector('.app-kanban');
  if (!kanban) return;

  // ═══════════════════════════════════════════
  // 1. 空闲检测
  // ═══════════════════════════════════════════
  let idleTimer = null;
  const IDLE_TIMEOUT = 5 * 60 * 1000; // 5分钟

  function resetIdleTimer() {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      window.dispatchEvent(new CustomEvent('mascot:idle-detected'));
    }, IDLE_TIMEOUT);
  }

  ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'].forEach(evt => {
    document.addEventListener(evt, resetIdleTimer, { passive: true });
  });
  resetIdleTimer();

  // ═══════════════════════════════════════════
  // 2. Toast 通知系统
  // ═══════════════════════════════════════════
  function showToast(title, content, opts = {}) {
    const { duration = 5000, actionLabel, actionCallback, type = 'info' } = opts;

    const toast = document.createElement('div');
    toast.className = `mascot-toast mascot-toast--${type}`;
    const iconMap = { info: '💬', warning: '⚠️', success: '✅', error: '❌', tip: '💡' };
    const icon = iconMap[type] || '💬';

    toast.innerHTML = `
      <span class="mascot-toast-icon">${icon}</span>
      <div class="mascot-toast-body">
        <div class="mascot-toast-title">${escapeHTML(title)}</div>
        <div class="mascot-toast-content">${escapeHTML(content)}</div>
      </div>
      ${actionLabel ? `<button class="mascot-toast-action">${escapeHTML(actionLabel)}</button>` : ''}
      <button class="mascot-toast-close">&times;</button>
    `;

    // 事件绑定
    toast.querySelector('.mascot-toast-close').onclick = () => dismissToast(toast);
    if (actionLabel && actionCallback) {
      toast.querySelector('.mascot-toast-action').onclick = () => {
        actionCallback();
        dismissToast(toast);
      };
    }

    document.body.appendChild(toast);

    // 入场动画
    requestAnimationFrame(() => toast.classList.add('mascot-toast--visible'));

    if (duration > 0) {
      toast._timer = setTimeout(() => dismissToast(toast), duration);
    }

    return toast;
  }

  function dismissToast(toast) {
    if (toast._timer) clearTimeout(toast._timer);
    toast.classList.remove('mascot-toast--visible');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 400);
  }

  function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // 监听 Toast 事件
  window.addEventListener('mascot:show-toast', (e) => {
    const { title, content, type, duration, actionLabel, actionCallback } = e.detail || {};
    showToast(title || '小星提醒', content || '', { type, duration, actionLabel, actionCallback });
  });

  // ═══════════════════════════════════════════
  // 3. 键盘快捷键
  // ═══════════════════════════════════════════
  document.addEventListener('keydown', (e) => {
    // Ctrl+Shift+K → 切换面板
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'K') {
      e.preventDefault();
      window.dispatchEvent(new CustomEvent('mascot:kanban-clicked'));
    }
  });

  // ═══════════════════════════════════════════
  // 4. 暴露上下文给对话
  // ═══════════════════════════════════════════
  window.MascotContext = {
    get pageContext() {
      return document.title || window.location.pathname;
    },
    get studentId() {
      return localStorage.getItem('starlearn_student_id') || 'default';
    },
    get pageType() {
      const path = window.location.pathname.toLowerCase();
      if (path.includes('hub')) return 'hub';
      if (path.includes('index')) return 'chat';
      if (path.includes('course')) return 'course';
      if (path.includes('code')) return 'code';
      if (path.includes('personal')) return 'personal';
      if (path.includes('socratic')) return 'socratic';
      if (path.includes('assessment')) return 'assessment';
      if (path.includes('video')) return 'video';
      if (path.includes('calendar')) return 'calendar';
      if (path.includes('progress')) return 'progress';
      return 'unknown';
    },
  };

  // ═══════════════════════════════════════════
  // 5. 面板状态 → 角色同步
  // ═══════════════════════════════════════════
  const MascotCore = window.MascotCore || {};

  // 扩展 showToast (如果 kanban.js 已经创建了 MascotCore，保留其方法)
  MascotCore.showToast = showToast;
  MascotCore.dismissToast = dismissToast;

  // 面板状态同步 — 被 mascot-panel.js 调用
  MascotCore.syncPanelState = function(state) {
    // 同步到角色
    window.dispatchEvent(new CustomEvent('mascot:update-state', {
      detail: state,
    }));
  };

  window.MascotCore = MascotCore;

  // ═══════════════════════════════════════════
  // 6. 面板关闭时的角色行为
  // ═══════════════════════════════════════════

  // 监听面板打开 (从面板发起)
  window.addEventListener('mascot:panel-opened', () => {
    // 重置空闲计时器
    resetIdleTimer();
    // 通知角色切换到思考状态
    window.dispatchEvent(new CustomEvent('mascot:update-state', {
      detail: { state: 'thinking', active: true },
    }));
  });

  // 监听面板关闭 (从面板发起)
  window.addEventListener('mascot:panel-closed', () => {
    // 清除思考状态
    window.dispatchEvent(new CustomEvent('mascot:update-state', {
      detail: { state: 'thinking', active: false },
    }));
    // 重置空闲计时
    resetIdleTimer();
  });

  console.log('[MascotCore v3] 桥接层就绪 — 通知/空闲检测/快捷键/状态同步已启用');
})();
