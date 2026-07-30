/**
 * Teacher AI Suggestions UI 单元测试 (M4.2)
 *
 * 验证:
 *  - renderSuggestionCard 输出含必要字段 + 三个动作按钮
 */
import { describe, it, expect } from 'vitest';

describe('Teacher AI Suggestions UI', () => {
  it('renders suggestion cards with action buttons', async () => {
    const { renderSuggestionCard } = await import('../../../js/teacher-dashboard.js');
    const html = renderSuggestionCard({
      id: 'sg_1',
      student_id: 's_1',
      type: 'low_engagement',
      priority: 'high',
      payload: { message: '3 days inactive' },
      status: 'pending',
    });
    expect(html).toContain('sg_1');
    expect(html).toContain('low_engagement');
    expect(html).toContain('一键发送');
    expect(html).toContain('修改');
    expect(html).toContain('取消');
    expect(html).toContain('high');
  });

  it('escapes XSS in suggestion payload', async () => {
    const { renderSuggestionCard } = await import('../../../js/teacher-dashboard.js');
    const html = renderSuggestionCard({
      id: 'sg_xss',
      student_id: 's_2',
      type: 'weakness',
      priority: 'medium',
      payload: { message: '<script>alert("xss")</script>' },
      status: 'pending',
    });
    expect(html).not.toContain('<script>alert');
    expect(html).toContain('&lt;script&gt;');
  });

  it('renders suggestions list with all items', async () => {
    const { renderSuggestionsList } = await import('../../../js/teacher-dashboard.js');
    const items = [
      { id: 'sg_1', student_id: 's_1', type: 'low_engagement', priority: 'high', payload: { message: 'm1' }, status: 'pending' },
      { id: 'sg_2', student_id: 's_2', type: 'weakness', priority: 'medium', payload: { message: 'm2' }, status: 'pending' },
    ];
    const html = renderSuggestionsList(items);
    expect(html).toContain('sg_1');
    expect(html).toContain('sg_2');
  });
});