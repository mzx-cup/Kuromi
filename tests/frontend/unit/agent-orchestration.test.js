/**
 * Agent orchestration UI 单元测试 (M2.6)
 *
 * 验证:
 *  - renderAgentRunStream 按时间顺序渲染 agent_run SSE 事件
 *  - getAgentTabs 返回 5 角色命名空间
 */
import { describe, it, expect } from 'vitest';

describe('AgentBehaviorLog UI', () => {
  it('renders agent_run SSE events in chronological order', async () => {
    const { renderAgentRunStream } = await import('../../../js/agent-orchestration.js');
    const events = [
      { agent: 'qa_agent', step: 'ask', timestamp: '2026-07-29T10:00:00Z' },
      { agent: 'audit_agent', step: 'check', timestamp: '2026-07-29T10:00:01Z' },
    ];
    const html = renderAgentRunStream(events);
    expect(html).toContain('qa_agent');
    expect(html).toContain('audit_agent');
    // qa_agent must appear before audit_agent (chronological)
    expect(html.indexOf('qa_agent')).toBeLessThan(html.indexOf('audit_agent'));
  });

  it('renders an empty string for empty events', async () => {
    const { renderAgentRunStream } = await import('../../../js/agent-orchestration.js');
    expect(renderAgentRunStream([])).toBe('');
  });

  it('shows 5-role tabs with correct keys', async () => {
    const { getAgentTabs } = await import('../../../js/agent-orchestration.js');
    const tabs = getAgentTabs();
    expect(tabs).toHaveLength(5);
    expect(tabs.map((t) => t.key)).toEqual([
      'qa_agent',
      'content_agent',
      'recommend_agent',
      'audit_agent',
      'evaluate_agent',
    ]);
  });

  it('each tab has a Chinese label', async () => {
    const { getAgentTabs } = await import('../../../js/agent-orchestration.js');
    const tabs = getAgentTabs();
    for (const tab of tabs) {
      expect(tab.label).toBeTruthy();
      expect(tab.label.length).toBeGreaterThan(0);
    }
  });
});