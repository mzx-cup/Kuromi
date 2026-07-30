/**
 * teacher-dashboard.js — 教师 dashboard JS (M4.2 增量)
 *
 * 导出:
 *   - renderSuggestionCard(suggestion) : 把单条 AI 建议渲染成 HTML 卡片
 *   - renderSuggestionsList(items)     : 渲染整个建议列表
 *
 * 用法:
 *   import { renderSuggestionsList } from '/js/teacher-dashboard.js';
 *   document.getElementById('ai-suggestions-list').innerHTML =
 *     renderSuggestionsList(suggestions);
 */
'use strict';

export function renderSuggestionCard(suggestion) {
  const message = escapeHtml(suggestion.payload?.message || '');
  return `
    <div class="ai-suggestion-card" data-id="${escapeHtml(suggestion.id || '')}" data-priority="${escapeHtml(suggestion.priority || '')}">
      <div class="suggestion-header">
        <span class="type">${escapeHtml(suggestion.type || '')}</span>
        <span class="priority priority-${escapeHtml(suggestion.priority || '')}">${escapeHtml(suggestion.priority || '')}</span>
      </div>
      <div class="suggestion-body">${message}</div>
      <div class="suggestion-meta">
        学生：${escapeHtml(suggestion.student_id || '')} ·
        状态：${escapeHtml(suggestion.status || '')}
      </div>
      <div class="suggestion-actions">
        <button data-action="send_to_student" data-id="${escapeHtml(suggestion.id || '')}" class="btn-send">一键发送</button>
        <button data-action="edit" data-id="${escapeHtml(suggestion.id || '')}" class="btn-edit">修改</button>
        <button data-action="cancel" data-id="${escapeHtml(suggestion.id || '')}" class="btn-cancel">取消</button>
      </div>
    </div>`;
}

export function renderSuggestionsList(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return '<div class="empty">暂无 AI 建议</div>';
  }
  return items.map(renderSuggestionCard).join('');
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}