/**
 * Toast — 全局通知系统
 * 统一业务通知和看板娘通知，共用底层引擎。
 *
 * Usage:
 *   Toast.show('保存成功', 'success')
 *   Toast.error('操作失败')
 *   Toast.mascot('小星提醒', '该休息啦~')
 */
var Toast = (function() {
  'use strict';

  var container = null;

  function ensureContainer() {
    if (!container || !container.parentNode) {
      container = document.createElement('div');
      container.className = 'app-toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  function createToast(title, content, opts) {
    opts = opts || {};
    var duration = opts.duration !== undefined ? opts.duration : 3000;
    var actionLabel = opts.actionLabel;
    var actionCallback = opts.actionCallback;
    var type = opts.type || 'info';
    var variant = opts.variant || '';

    var iconMap = { info: '💬', warning: '⚠️', success: '✅', error: '❌', tip: '💡' };

    var toast = document.createElement('div');
    toast.className = 'app-toast app-toast--' + type + (variant ? ' app-toast--' + variant : '');

    toast.innerHTML =
      '<span class="app-toast-icon">' + (iconMap[type] || '💬') + '</span>' +
      '<div class="app-toast-body">' +
        '<div class="app-toast-title">' + escapeHTML(title) + '</div>' +
        (content ? '<div class="app-toast-content">' + escapeHTML(content) + '</div>' : '') +
      '</div>' +
      (actionLabel ? '<button class="app-toast-action">' + escapeHTML(actionLabel) + '</button>' : '') +
      '<button class="app-toast-close">&times;</button>';

    toast.querySelector('.app-toast-close').onclick = function() { dismiss(toast); };
    if (actionLabel && actionCallback) {
      toast.querySelector('.app-toast-action').onclick = function() { actionCallback(); dismiss(toast); };
    }

    ensureContainer().appendChild(toast);

    if (duration > 0) {
      toast._timer = setTimeout(function() { dismiss(toast); }, duration);
    }

    return toast;
  }

  function dismiss(toast) {
    if (toast._timer) clearTimeout(toast._timer);
    toast.classList.add('app-toast--removing');
    toast.addEventListener('transitionend', function() { toast.remove(); }, { once: true });
    setTimeout(function() { if (toast.parentNode) toast.remove(); }, 400);
  }

  function escapeHTML(str) {
    var div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  // ---- Public API ----

  function show(title, type, opts) {
    if (!type) type = 'info';
    if (!opts) opts = {};
    opts.type = type;
    return createToast(title, '', opts);
  }

  function info(title, opts) { return show(title, 'info', opts); }
  function ok(title, opts) { return show(title, 'success', opts); }
  function error(title, opts) { return show(title, 'error', opts); }
  function warning(title, opts) { return show(title, 'warning', opts); }

  function mascot(title, content, opts) {
    if (!opts) opts = {};
    opts.type = 'info';
    opts.variant = 'mascot';
    opts.duration = opts.duration || 5000;
    return createToast(title, content, opts);
  }

  window.Toast = { show: show, info: info, error: error, warning: warning, ok: ok, mascot: mascot, dismiss: dismiss };
  return window.Toast;
})();
