/**
 * "为什么推这个" 卡片 单元测试 (M4.3)
 */
import { describe, it, expect, beforeEach } from 'vitest';

describe('Why This Recommendation Card', () => {
  it('renders reasoning + goal_evidence + capability_rationale', async () => {
    const { renderWhyThisCard } = await import('../../../js/personal-why-this.js');
    const html = renderWhyThisCard({
      node_id: 'n_1',
      title: '递归基础',
      reasoning: '因为你的"递归"薄弱点权重 0.8',
      goal_evidence: '距离目标"掌握 Python"还差 30%',
      capability_rationale: '视觉型学习者，适合图表讲解',
      confidence: 0.85,
    });
    expect(html).toContain('递归基础');
    expect(html).toContain('因为你的');
    expect(html).toContain('距离目标');
    expect(html).toContain('视觉型');
    expect(html).toContain('85%');
  });

  it('collapses/expands on click', async () => {
    const { isExpanded, toggleExpand } = await import('../../../js/personal-why-this.js');
    expect(isExpanded('card_1')).toBe(false);
    toggleExpand('card_1');
    expect(isExpanded('card_1')).toBe(true);
    toggleExpand('card_1');
    expect(isExpanded('card_1')).toBe(false);
  });

  it('escapes XSS in user-facing text', async () => {
    const { renderWhyThisCard } = await import('../../../js/personal-why-this.js');
    const html = renderWhyThisCard({
      node_id: 'n_xss',
      title: '<script>alert(1)</script>',
      reasoning: 'safe',
      goal_evidence: 'safe',
      capability_rationale: 'safe',
      confidence: 0.5,
    });
    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('&lt;script&gt;');
  });
});