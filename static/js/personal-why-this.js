/**
 * personal-why-this.js — "为什么推这个" 解释卡片（M4.3）
 *
 * 与 js/personal.js 分离：原文件是 script (IIFE + globals)，新文件是 ESM 模块。
 * 通过 vitest 测试；生产侧可在 personal.html 里 <script type="module"> 引用。
 *
 * 导出:
 *   - renderWhyThisCard(recommendation) : 把 RecommendAgent 输出渲染成 HTML
 *   - isExpanded / toggleExpand        : 折叠卡片状态管理
 */
'use strict';

const _expandedCards = new Set();

export function renderWhyThisCard(recommendation) {
  const conf = Math.round((recommendation.confidence ?? 0) * 100);
  return `
    <div class="why-this-card" data-node-id="${escapeHtml(recommendation.node_id || '')}">
      <div class="why-this-header">
        <h4>${escapeHtml(recommendation.title || '')}</h4>
        <span class="confidence">${conf}%</span>
      </div>
      <div class="why-this-body" data-expanded="${isExpanded(recommendation.node_id) ? 'true' : 'false'}">
        <div class="reasoning">
          <strong>为什么？</strong> ${escapeHtml(recommendation.reasoning || '')}
        </div>
        <div class="goal-evidence">
          <strong>目标差距：</strong> ${escapeHtml(recommendation.goal_evidence || '')}
        </div>
        <div class="capability">
          <strong>匹配你的能力：</strong> ${escapeHtml(recommendation.capability_rationale || '')}
        </div>
      </div>
      <button class="toggle-btn" data-node-id="${escapeHtml(recommendation.node_id || '')}">
        ${isExpanded(recommendation.node_id) ? '收起' : '展开'}
      </button>
    </div>`;
}

export function isExpanded(cardId) {
  return _expandedCards.has(cardId);
}

export function toggleExpand(cardId) {
  if (_expandedCards.has(cardId)) {
    _expandedCards.delete(cardId);
  } else {
    _expandedCards.add(cardId);
  }
  return _expandedCards.has(cardId);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}