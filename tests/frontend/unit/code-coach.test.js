import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('CodeCoach', () => {
  let handler;
  // Track all handlers added across tests so we can clear them between runs
  // (jsdom doesn't provide a way to enumerate listeners, so we maintain our own list).
  const allHandlers = [];
  beforeEach(() => {
    vi.useFakeTimers();
    // Clear all previously-registered handlers to prevent cross-test contamination.
    while (allHandlers.length) {
      const h = allHandlers.pop();
      document.removeEventListener('coach:narrate', h);
    }
    handler = vi.fn();
    allHandlers.push(handler);
    document.addEventListener('coach:narrate', handler);
  });
  afterEach(() => {
    vi.useRealTimers();
    document.removeEventListener('coach:narrate', handler);
    const idx = allHandlers.indexOf(handler);
    if (idx >= 0) allHandlers.splice(idx, 1);
  });

  it('idle ≥ idleMs 后触发 coach:narrate { reason: "idle" }', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach({ idleMs: 180000 });
    coach.start();
    document.dispatchEvent(new CustomEvent('editor:keystroke'));
    vi.advanceTimersByTime(181000);
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.reason).toBe('idle');
    coach.stop();
  });

  it('keystroke 在 idleMs 内重置计时器（不触发）', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach({ idleMs: 1000 });
    coach.start();
    document.dispatchEvent(new CustomEvent('editor:keystroke'));
    vi.advanceTimersByTime(500);
    document.dispatchEvent(new CustomEvent('editor:keystroke'));  // 重置
    vi.advanceTimersByTime(500);
    expect(handler).not.toHaveBeenCalled();
    vi.advanceTimersByTime(600);
    expect(handler).toHaveBeenCalled();
    coach.stop();
  });

  it('run:failed 触发后,相同 stderr 第二次出现时触发 repeat-error', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach({ repeatErrorCount: 2 });
    coach.start();
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'NameError: x not defined' } }));
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'NameError: y not defined' } }));  // same pattern (variable name stripped)
    const calls = handler.mock.calls.filter(c => c[0].detail.reason === 'repeat-error');
    expect(calls.length).toBe(1);
    coach.stop();
  });

  it('run:failed 连续 3 次触发 consecutive-failures', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach({ consecutiveFailures: 3 });
    coach.start();
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'error A' } }));
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'error B' } }));
    expect(handler).not.toHaveBeenCalledWith(expect.objectContaining({ detail: expect.objectContaining({ reason: 'consecutive-failures' }) }));
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'error C' } }));
    const calls = handler.mock.calls.filter(c => c[0].detail.reason === 'consecutive-failures');
    expect(calls.length).toBe(1);
    expect(handler.mock.calls[handler.mock.calls.length - 1][0].detail.count).toBe(3);
    coach.stop();
  });

  it('run:passed 重置 failureStreak', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach({ consecutiveFailures: 3 });
    coach.start();
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'err1' } }));
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'err2' } }));
    document.dispatchEvent(new CustomEvent('run:passed'));  // reset streak
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'err3' } }));
    document.dispatchEvent(new CustomEvent('run:failed', { detail: { stderr: 'err4' } }));
    // streak was reset, so 3 failures total since the pass shouldn't trigger consecutive-failures
    const calls = handler.mock.calls.filter(c => c[0].detail.reason === 'consecutive-failures');
    expect(calls.length).toBe(0);
    coach.stop();
  });

  it('todos:changed 当 remaining === nearCompleteTodos (1) 触发 near-complete', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach({ nearCompleteTodos: 1 });
    coach.start();
    document.dispatchEvent(new CustomEvent('todos:changed', { detail: { remaining: 3 } }));
    expect(handler).not.toHaveBeenCalled();
    document.dispatchEvent(new CustomEvent('todos:changed', { detail: { remaining: 1 } }));
    const calls = handler.mock.calls.filter(c => c[0].detail.reason === 'near-complete');
    expect(calls.length).toBe(1);
    coach.stop();
  });

  it('run:passed 触发 all-passed', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach();
    coach.start();
    document.dispatchEvent(new CustomEvent('run:passed'));
    const calls = handler.mock.calls.filter(c => c[0].detail.reason === 'all-passed');
    expect(calls.length).toBe(1);
    coach.stop();
  });

  it('start 双调用安全（no-op）', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach();
    coach.start();
    coach.start();  // 二次调用应 no-op
    document.dispatchEvent(new CustomEvent('run:passed'));
    const calls = handler.mock.calls.filter(c => c[0].detail.reason === 'all-passed');
    expect(calls.length).toBe(1);
    coach.stop();
  });

  it('stop 后不再监听事件', async () => {
    const { CodeCoach } = await import('../../../js/code-coach.js');
    const coach = new CodeCoach();
    coach.start();
    coach.stop();
    document.dispatchEvent(new CustomEvent('run:passed'));
    expect(handler).not.toHaveBeenCalled();
  });
});
