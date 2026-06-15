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

const NARRATION_TEXT = {
  idle: '卡住了？试试把当前函数的输入输出写在注释里',
  'repeat-error': '你又遇到这个错误了，要不要我讲一下根因？',
  'near-complete': '加油！只剩最后一处 TODO 了',
  'all-passed': '全部通过！要不要看下我的参考解对比？',
  'consecutive-failures': '换个思路试试？',
};

const lastFiredAt = new Map();

export function mountNarrator(hostEl, _coach) {
  document.addEventListener('coach:narrate', (e) => {
    const { reason } = e.detail;
    const text = NARRATION_TEXT[reason];
    if (!text) return;
    const now = Date.now();
    const last = lastFiredAt.get(reason) || 0;
    if (now - last < 60000) return;
    lastFiredAt.set(reason, now);

    const bubble = document.createElement('div');
    bubble.className = 'narrator-bubble';
    bubble.textContent = text;
    hostEl.appendChild(bubble);
    setTimeout(() => {
      bubble.style.opacity = '0';
      setTimeout(() => bubble.remove(), 600);
    }, 3000);
  });
}

if (typeof window !== 'undefined') {
  window.CodeCoach = CodeCoach;
  window.mountNarrator = mountNarrator;
}
