/**
 * agent-orchestration.js — 5 角色命名空间前端渲染 (M2.6)
 *
 * 导出:
 *   - renderAgentRunStream(events) : 把 agent_run SSE 事件列表渲染成 HTML
 *   - getAgentTabs()                : 返回 5 角色 Tab 配置（key + 中文 label）
 *
 * 用法:
 *   import { renderAgentRunStream, getAgentTabs } from '/js/agent-orchestration.js';
 *   document.getElementById('agent-run-stream').innerHTML = renderAgentRunStream(events);
 */
'use strict';

/**
 * 把 agent_run SSE 事件列表渲染成 HTML（按时间顺序）。
 *
 * @param {Array<{agent: string, step: string, timestamp: string}>} events
 * @returns {string} HTML 片段
 */
export function renderAgentRunStream(events) {
  if (!Array.isArray(events) || events.length === 0) {
    return '';
  }
  return events
    .map(
      (e) => `
      <div class="agent-run-row" data-agent="${escapeHtml(e.agent || '')}">
        <span class="agent-name">${escapeHtml(e.agent || '')}</span>
        <span class="step">${escapeHtml(e.step || '')}</span>
        <time>${escapeHtml(e.timestamp || '')}</time>
      </div>`,
    )
    .join('');
}

/**
 * 返回 5 角色 Tab 配置（key + 中文 label）。
 *
 * @returns {Array<{key: string, label: string}>}
 */
export function getAgentTabs() {
  return [
    { key: 'qa_agent', label: '问答 Agent' },
    { key: 'content_agent', label: '内容 Agent' },
    { key: 'recommend_agent', label: '推荐 Agent' },
    { key: 'audit_agent', label: '审核 Agent' },
    { key: 'evaluate_agent', label: '评估 Agent' },
  ];
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}