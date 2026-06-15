/**
 * CodeCoach — 教练主动旁白事件检测器
 * 监听 4 类编辑器事件，按 5 条规则触发 coach:narrate CustomEvent。
 * 旁白文本由 Task 11 的 mountNarrator 决定，本模块只负责"什么时候说什么理由"。
 */

const DEFAULT_RULES = {
  idleMs: 180000,            // 3 分钟静默
  repeatErrorCount: 2,        // 同一 stderr pattern 重复次数
  repeatErrorWindowMs: 60000, // 错误窗口
  nearCompleteTodos: 1,       // TODO 剩余阈值
  consecutiveFailures: 3,    // 连续失败次数
};

export class CodeCoach {
  constructor(opts = {}) {
    this.opts = { ...DEFAULT_RULES, ...opts };
    this.lastKeystrokeAt = 0;
    this.idleTimer = null;
    this.errorHistory = [];
    this.failureStreak = 0;
    this.started = false;
  }

  start() {
    if (this.started) return;
    this.started = true;
    document.addEventListener('editor:keystroke', this._onKeystroke);
    document.addEventListener('run:failed', this._onRunFailed);
    document.addEventListener('todos:changed', this._onTodosChanged);
    document.addEventListener('run:passed', this._onRunPassed);
    this.resetIdleTimer();
  }

  stop() {
    if (!this.started) return;
    this.started = false;
    document.removeEventListener('editor:keystroke', this._onKeystroke);
    document.removeEventListener('run:failed', this._onRunFailed);
    document.removeEventListener('todos:changed', this._onTodosChanged);
    document.removeEventListener('run:passed', this._onRunPassed);
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
  }

  resetIdleTimer() {
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => this.narrate('idle'), this.opts.idleMs);
  }

  _onKeystroke = () => {
    this.lastKeystrokeAt = Date.now();
    this.resetIdleTimer();
  };

  _onRunFailed = (e) => {
    this.failureStreak += 1;
    const msg = (e && e.detail && (e.detail.stderr || e.detail.message)) || '';
    const pattern = this._normalizeError(msg);
    const now = Date.now();
    this.errorHistory = this.errorHistory.filter(x => now - x.at < this.opts.repeatErrorWindowMs);
    if (this.errorHistory.length >= this.opts.repeatErrorCount - 1
        && this.errorHistory.every(x => x.pattern === pattern)) {
      this.narrate('repeat-error', { message: msg });
    }
    if (this.failureStreak >= this.opts.consecutiveFailures) {
      this.narrate('consecutive-failures', { count: this.failureStreak });
    }
    this.errorHistory.push({ pattern, at: now });
  };

  _onTodosChanged = (e) => {
    const remaining = (e && e.detail && e.detail.remaining) || 0;
    if (remaining === this.opts.nearCompleteTodos) {
      this.narrate('near-complete', { remaining });
    }
  };

  _onRunPassed = () => {
    this.failureStreak = 0;
    this.errorHistory = [];
    this.narrate('all-passed');
  };

  _normalizeError(msg) {
    // Strip digits, quoted strings, and bare identifiers that look like variable names
    // (lowercase word after ": " or after "(" before "not defined/is not defined"). This
    // lets "NameError: x not defined" and "NameError: y not defined" collide so the
    // repeat-error rule fires on the second occurrence of the same class of error.
    return String(msg)
      .replace(/\d+/g, '#')
      .replace(/'[^']*'/g, "'?'")
      .replace(/(?<=:\s)[A-Za-z_][A-Za-z_0-9]*(?=\s+(?:not |is ))/g, '?')
      .slice(0, 120);
  }

  narrate(reason, extra = {}) {
    document.dispatchEvent(new CustomEvent('coach:narrate', {
      detail: { reason, ...extra, at: Date.now() }
    }));
  }
}

if (typeof window !== 'undefined') window.CodeCoach = CodeCoach;
