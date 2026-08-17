class LearningMonitor {
    constructor(config = {}) {
        this.enabled = config.enabled !== false;
        this.studentId = config.studentId || 'anonymous';
        this.courseId = config.courseId || 'bigdata';
        this.apiEndpoint = config.apiEndpoint || `${window.location.origin}/api/v2/telemetry`;
        this.reportInterval = config.reportInterval || 60000;
        this.dataWindowMs = config.dataWindowMs || 180000;

        this.watchZones = config.watchZones || [
            { selector: '#chat-container', name: 'chat_area', type: 'content' },
            { selector: '#code-editor', name: 'code_editor', type: 'code' },
            { selector: '#radar-chart', name: 'radar_chart', type: 'chart' },
            { selector: '#task-input', name: 'task_area', type: 'exercise' },
            { selector: '#path-container', name: 'path_area', type: 'navigation' },
        ];

        this.thresholds = {
            fastScrollSpeed: config.fastScrollSpeed || 300,
            deepReadSpeed: config.deepReadSpeed || 100,
            overloadThreshold: config.overloadThreshold || 75,
            criticalOverload: config.criticalOverload || 90,
            overloadDurationMs: config.overloadDurationMs || 5000,
            mouseDebounceMs: config.mouseDebounceMs || 300,
            scrollThrottleMs: config.scrollThrottleMs || 200,
        };

        this._dwellTimes = {};
        this._scrollEvents = [];
        this._mouseEvents = [];
        this._zoneEnterTimes = {};
        this._zoneDwellTimes = {};
        this._overloadScore = 0;
        this._overloadStartTime = null;
        this._overloadTriggered = false;
        this._lastScrollY = window.scrollY;
        this._lastScrollTime = Date.now();
        this._lastMouseX = 0;
        this._lastMouseY = 0;
        this._mousePathEntropy = 0;
        this._mousePositions = [];
        this._reportTimer = null;
        this._gcTimer = null;
        this._boundHandlers = {};
        this._started = false;
        this._fpsFrames = 0;
        this._fpsLastTime = performance.now();
        this._currentFps = 60;

        // ── 新增遥测状态 ──
        this._codeEditorFocusTime = 0;
        this._codeEditorFocusStart = null;
        this._codeRunCount = 0;
        this._codeRunHistory = [];
        this._errorViewStart = null;
        this._errorViewDuration = 0;
        this._pasteEvents = [];
        this._tabSwitchCount = 0;
        this._tabSwitchStart = null;
        this._consecutiveWrongCount = 0;
        this._lastQuizCorrect = true;
        this._deprecatedApiDetected = [];
        this._keyboardEvents = [];

        this.onOverload = config.onOverload || null;
        this.onDeepRead = config.onDeepRead || null;
        this.onFastBrowse = config.onFastBrowse || null;
    }

    start() {
        if (!this.enabled || this._started) return;
        this._started = true;

        this._boundHandlers = {
            scroll: this._throttle(this._onScroll.bind(this), this.thresholds.scrollThrottleMs),
            mousemove: this._debounce(this._onMouseMove.bind(this), this.thresholds.mouseDebounceMs),
            visibilitychange: this._onVisibilityChange.bind(this),
            beforeunload: this._onBeforeUnload.bind(this),
            paste: this._onPaste.bind(this),
            blur: this._onWindowBlur.bind(this),
            focus: this._onWindowFocus.bind(this),
        };

        window.addEventListener('scroll', this._boundHandlers.scroll, { passive: true });
        document.addEventListener('mousemove', this._boundHandlers.mousemove, { passive: true });
        document.addEventListener('visibilitychange', this._boundHandlers.visibilitychange);
        window.addEventListener('beforeunload', this._boundHandlers.beforeunload);

        // ── 新增事件监听 ──
        document.addEventListener('paste', this._boundHandlers.paste);
        window.addEventListener('blur', this._boundHandlers.blur);
        window.addEventListener('focus', this._boundHandlers.focus);
        this._initCodeEditorTracking();
        this._initCodeRunTracking();
        this._initErrorViewTracking();
        this._initDeprecatedApiScan();
        this._initQuizTracking();

        this._initZoneTracking();
        this._startFPSMonitor();
        this._reportTimer = setInterval(() => this._aggregateAndReport(), this.reportInterval);
        this._gcTimer = setInterval(() => this._garbageCollect(), 30000);
    }

    stop() {
        if (!this._started) return;
        this._started = false;

        window.removeEventListener('scroll', this._boundHandlers.scroll);
        document.removeEventListener('mousemove', this._boundHandlers.mousemove);
        document.removeEventListener('visibilitychange', this._boundHandlers.visibilitychange);
        window.removeEventListener('beforeunload', this._boundHandlers.beforeunload);
        document.removeEventListener('paste', this._boundHandlers.paste);
        window.removeEventListener('blur', this._boundHandlers.blur);
        window.removeEventListener('focus', this._boundHandlers.focus);

        if (this._reportTimer) clearInterval(this._reportTimer);
        if (this._gcTimer) clearInterval(this._gcTimer);

        this._aggregateAndReport();
        this._cleanupZoneTracking();
    }

    destroy() {
        this.stop();
        this._dwellTimes = {};
        this._scrollEvents = [];
        this._mouseEvents = [];
        this._zoneEnterTimes = {};
        this._zoneDwellTimes = {};
        this._mousePositions = [];
        this._boundHandlers = {};
    }

    getOverloadScore() {
        return this._overloadScore;
    }

    getMetrics() {
        return {
            pageDwellTime: this._getPageDwellTime(),
            zoneDwellTimes: { ...this._zoneDwellTimes },
            scrollSpeed: this._getAverageScrollSpeed(),
            mouseEntropy: this._mousePathEntropy,
            overloadScore: this._overloadScore,
            fps: this._currentFps,
        };
    }

    _initZoneTracking() {
        this.watchZones.forEach(zone => {
            const el = document.querySelector(zone.selector);
            if (!el) return;
            this._zoneDwellTimes[zone.name] = 0;

            const enterHandler = () => {
                this._zoneEnterTimes[zone.name] = Date.now();
            };
            const leaveHandler = () => {
                const enterTime = this._zoneEnterTimes[zone.name];
                if (enterTime) {
                    const dwell = (Date.now() - enterTime) / 1000;
                    this._zoneDwellTimes[zone.name] = (this._zoneDwellTimes[zone.name] || 0) + dwell;
                    delete this._zoneEnterTimes[zone.name];
                }
            };

            el.addEventListener('mouseenter', enterHandler);
            el.addEventListener('mouseleave', leaveHandler);
            el.addEventListener('focus', enterHandler);
            el.addEventListener('blur', leaveHandler);

            zone._enterHandler = enterHandler;
            zone._leaveHandler = leaveHandler;
            zone._element = el;
        });
    }

    _cleanupZoneTracking() {
        this.watchZones.forEach(zone => {
            if (zone._element) {
                zone._element.removeEventListener('mouseenter', zone._enterHandler);
                zone._element.removeEventListener('mouseleave', zone._leaveHandler);
                zone._element.removeEventListener('focus', zone._enterHandler);
                zone._element.removeEventListener('blur', zone._leaveHandler);
            }
        });
    }

    _onScroll() {
        const now = Date.now();
        const deltaY = Math.abs(window.scrollY - this._lastScrollY);
        const deltaTime = (now - this._lastScrollTime) / 1000;
        const speed = deltaTime > 0 ? deltaY / deltaTime : 0;
        const direction = window.scrollY > this._lastScrollY ? 'down' : 'up';

        this._scrollEvents.push({
            timestamp: now,
            speed: Math.round(speed),
            direction,
            position: window.scrollY,
        });

        if (speed > this.thresholds.fastScrollSpeed && this.onFastBrowse) {
            this.onFastBrowse({ speed, direction });
        }
        if (speed < this.thresholds.deepReadSpeed && speed > 0 && this.onDeepRead) {
            this.onDeepRead({ speed, direction });
        }

        this._lastScrollY = window.scrollY;
        this._lastScrollTime = now;
        this._updateOverloadScore();
    }

    _onMouseMove(event) {
        const now = Date.now();
        const dx = event.clientX - this._lastMouseX;
        const dy = event.clientY - this._lastMouseY;

        this._mousePositions.push({
            x: event.clientX,
            y: event.clientY,
            t: now,
        });

        if (this._mousePositions.length > 60) {
            this._mousePositions = this._mousePositions.slice(-60);
        }

        this._mousePathEntropy = this._calculateMouseEntropy();
        this._lastMouseX = event.clientX;
        this._lastMouseY = event.clientY;

        this._mouseEvents.push({
            timestamp: now,
            x: event.clientX,
            y: event.clientY,
            entropy: this._mousePathEntropy,
        });

        this._updateOverloadScore();
    }

    _calculateMouseEntropy() {
        if (this._mousePositions.length < 5) return 0;

        const positions = this._mousePositions.slice(-30);
        let directionChanges = 0;
        let totalDistance = 0;

        for (let i = 1; i < positions.length; i++) {
            const dx = positions[i].x - positions[i - 1].x;
            const dy = positions[i].y - positions[i - 1].y;
            totalDistance += Math.sqrt(dx * dx + dy * dy);

            if (i >= 2) {
                const prevDx = positions[i - 1].x - positions[i - 2].x;
                const prevDy = positions[i - 1].y - positions[i - 2].y;
                const cross = dx * prevDy - dy * prevDx;
                if (Math.abs(cross) > 50) directionChanges++;
            }
        }

        const avgDistance = totalDistance / Math.max(1, positions.length - 1);
        const changeRatio = directionChanges / Math.max(1, positions.length - 2);
        const entropy = Math.min(100, (changeRatio * 60 + Math.min(avgDistance / 5, 40)));

        return Math.round(entropy);
    }

    _updateOverloadScore() {
        const zoneDwellScore = this._calculateZoneDwellScore();
        const mouseEntropyScore = this._mousePathEntropy;
        const scrollAnomalyScore = this._calculateScrollAnomalyScore();

        this._overloadScore = Math.round(
            zoneDwellScore * 0.40 +
            mouseEntropyScore * 0.35 +
            scrollAnomalyScore * 0.25
        );

        this._overloadScore = Math.min(100, Math.max(0, this._overloadScore));

        const now = Date.now();

        if (this._overloadScore >= this.thresholds.criticalOverload) {
            this._triggerOverload('critical');
        } else if (this._overloadScore >= this.thresholds.overloadThreshold) {
            if (!this._overloadStartTime) {
                this._overloadStartTime = now;
            }
            if (now - this._overloadStartTime >= this.thresholds.overloadDurationMs) {
                this._triggerOverload('sustained');
            }
        } else {
            this._overloadStartTime = null;
            this._overloadTriggered = false;
        }
    }

    _calculateZoneDwellScore() {
        const totalDwell = Object.values(this._zoneDwellTimes).reduce((a, b) => a + b, 0);
        if (totalDwell < 5) return 0;
        if (totalDwell < 30) return totalDwell * 1.5;
        if (totalDwell < 120) return 45 + (totalDwell - 30) * 0.3;
        return Math.min(100, 69 + (totalDwell - 120) * 0.1);
    }

    _calculateScrollAnomalyScore() {
        const recent = this._scrollEvents.filter(
            e => Date.now() - e.timestamp < 30000
        );
        if (recent.length < 3) return 0;

        const speeds = recent.map(e => e.speed);
        const avg = speeds.reduce((a, b) => a + b, 0) / speeds.length;
        const variance = speeds.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / speeds.length;
        const stdDev = Math.sqrt(variance);

        const directionChanges = recent.filter((e, i) =>
            i > 0 && e.direction !== recent[i - 1].direction
        ).length;
        const directionChangeRatio = directionChanges / Math.max(1, recent.length - 1);

        return Math.min(100, Math.round(stdDev / 3 + directionChangeRatio * 70));
    }

    _triggerOverload(type) {
        if (this._overloadTriggered && type === 'sustained') return;
        this._overloadTriggered = true;

        if (this.onOverload) {
            this.onOverload({
                type,
                score: this._overloadScore,
                metrics: this.getMetrics(),
                timestamp: Date.now(),
            });
        }

        this._aggregateAndReport();
    }

    _getPageDwellTime() {
        if (!this._dwellTimes._pageStart) return 0;
        return (Date.now() - this._dwellTimes._pageStart) / 1000;
    }

    _getAverageScrollSpeed() {
        const recent = this._scrollEvents.filter(e => Date.now() - e.timestamp < 30000);
        if (recent.length === 0) return 0;
        return Math.round(recent.reduce((a, b) => a + b.speed, 0) / recent.length);
    }

    _onVisibilityChange() {
        if (document.hidden) {
            this._dwellTimes._hiddenAt = Date.now();
        } else if (this._dwellTimes._hiddenAt) {
            delete this._dwellTimes._hiddenAt;
        }
    }

    _onBeforeUnload() {
        this._aggregateAndReport(true);
    }

    // ── 代码编辑器焦点追踪 ──
    _initCodeEditorTracking() {
        const editor = document.querySelector('#code-editor, .code-editor, [data-role="code-editor"]');
        if (!editor) return;

        editor.addEventListener('focus', () => {
            this._codeEditorFocusStart = Date.now();
        });
        editor.addEventListener('blur', () => {
            if (this._codeEditorFocusStart) {
                const duration = (Date.now() - this._codeEditorFocusStart) / 1000;
                this._codeEditorFocusTime += duration;
                this._codeEditorFocusStart = null;
            }
        });
    }

    // ── 代码运行按钮点击追踪 ──
    _initCodeRunTracking() {
        const runBtn = document.querySelector('#run-btn, #execute-btn, [data-action="run-code"], .run-button');
        if (!runBtn) return;

        runBtn.addEventListener('click', () => {
            this._codeRunCount++;
            this._codeRunHistory.push({
                timestamp: Date.now(),
                source: 'button_click',
            });
            // 每次运行后上报一次实时事件
            this._reportEvent('code_run_event', {
                run_count: this._codeRunCount,
                timestamp: Date.now(),
            });
        });
    }

    // ── 报错查看时长追踪 ──
    _initErrorViewTracking() {
        // 监听错误面板的显示/隐藏
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                const errorPanel = document.querySelector('#error-panel, .error-output, .compile-error, [data-role="error-display"]');
                if (!errorPanel) return;
                const isVisible = errorPanel.offsetParent !== null;
                if (isVisible && !this._errorViewStart) {
                    this._errorViewStart = Date.now();
                } else if (!isVisible && this._errorViewStart) {
                    const duration = (Date.now() - this._errorViewStart) / 1000;
                    this._errorViewDuration += duration;
                    this._errorViewStart = null;
                }
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // ── 复制粘贴检测 ──
    _onPaste(event) {
        const target = event.target;
        const isCodeEditor = target.matches('#code-editor, .code-editor, textarea, [contenteditable="true"]');
        this._pasteEvents.push({
            timestamp: Date.now(),
            in_code_editor: isCodeEditor,
            target_tag: target.tagName,
        });
        this._reportEvent('clipboard_paste_event', {
            in_code_editor: isCodeEditor,
            timestamp: Date.now(),
        });
    }

    // ── 窗口焦点切换（标签页切换） ──
    _onWindowBlur() {
        this._tabSwitchStart = Date.now();
    }

    _onWindowFocus() {
        if (this._tabSwitchStart) {
            const awayTime = (Date.now() - this._tabSwitchStart) / 1000;
            // 离开超过 3 秒才算一次有意义的切换
            if (awayTime > 3) {
                this._tabSwitchCount++;
            }
            this._tabSwitchStart = null;
        }
    }

    // ── 过时代码扫描 ──
    _initDeprecatedApiScan() {
        const deprecatedPatterns = [
            { pattern: /var\s+\w+/g, name: 'var_declaration', suggest: 'let/const' },
            { pattern: /eval\s*\(/g, name: 'eval_usage', suggest: '避免使用 eval' },
            { pattern: /document\.write\s*\(/g, name: 'document_write', suggest: 'DOM 操作' },
            { pattern: /new\s+ActiveXObject/g, name: 'activex_object', suggest: '现代 API' },
            { pattern: /__proto__/g, name: 'proto_direct_access', suggest: 'Object.getPrototypeOf' },
            { pattern: /alert\s*\(/g, name: 'alert_usage', suggest: '自定义弹窗' },
        ];

        const scanCode = () => {
            const editor = document.querySelector('#code-editor, .code-editor, textarea');
            if (!editor) return;
            const code = editor.value || editor.textContent || '';
            this._deprecatedApiDetected = [];
            deprecatedPatterns.forEach(({ pattern, name, suggest }) => {
                const matches = code.match(pattern);
                if (matches && matches.length > 0) {
                    this._deprecatedApiDetected.push({
                        api: name,
                        count: matches.length,
                        suggest: suggest,
                    });
                }
            });
        };

        // 延迟扫描，等待编辑器内容加载
        setTimeout(scanCode, 2000);
        // 监听代码变化（如果有 CodeMirror 或 Monaco 等编辑器）
        const editor = document.querySelector('#code-editor, .code-editor');
        if (editor) {
            editor.addEventListener('input', this._debounce(scanCode, 2000));
        }
    }

    // ── 测验答题追踪 ──
    _initQuizTracking() {
        // 监听提交按钮或 quiz 相关事件
        document.addEventListener('quiz_submitted', (e) => {
            const detail = e.detail || {};
            const isCorrect = detail.correct || detail.passed || false;
            if (!isCorrect) {
                this._consecutiveWrongCount++;
            } else {
                this._consecutiveWrongCount = 0;
                this._lastQuizCorrect = true;
            }
            this._lastQuizCorrect = isCorrect;
            this._reportEvent('quiz_answered', {
                correct: isCorrect,
                consecutive_wrong: this._consecutiveWrongCount,
                timestamp: Date.now(),
            });
        });
    }

    // ── 实时事件上报 ──
    async _reportEvent(eventType, data) {
        const payload = {
            student_id: this.studentId,
            course_id: this.courseId,
            timestamp: Date.now(),
            event_type: eventType,
            data: data,
        };
        await this._sendWithRetry(payload, 1);
    }

    _startFPSMonitor() {
        const measureFPS = () => {
            if (!this._started) return;
            this._fpsFrames++;
            const now = performance.now();
            if (now - this._fpsLastTime >= 1000) {
                this._currentFps = Math.round(this._fpsFrames * 1000 / (now - this._fpsLastTime));
                this._fpsFrames = 0;
                this._fpsLastTime = now;
            }
            requestAnimationFrame(measureFPS);
        };
        requestAnimationFrame(measureFPS);
    }

    _garbageCollect() {
        const cutoff = Date.now() - this.dataWindowMs;
        this._scrollEvents = this._scrollEvents.filter(e => e.timestamp > cutoff);
        this._mouseEvents = this._mouseEvents.filter(e => e.timestamp > cutoff);
        this._codeRunHistory = this._codeRunHistory.filter(e => e.timestamp > cutoff);
        this._pasteEvents = this._pasteEvents.filter(e => e.timestamp > cutoff);
        if (this._mouseEvents.length > 500) {
            this._mouseEvents = this._mouseEvents.slice(-300);
        }
        if (this._scrollEvents.length > 200) {
            this._scrollEvents = this._scrollEvents.slice(-150);
        }
    }

    async _aggregateAndReport(useBeacon = false) {
        const payload = this._buildPayload();
        if (useBeacon && navigator.sendBeacon) {
            navigator.sendBeacon(
                this.apiEndpoint,
                JSON.stringify(payload)
            );
            return;
        }
        await this._sendWithRetry(payload);
    }

    _buildPayload() {
        const now = Date.now();
        // 计算当前代码编辑器焦点时长（如果仍在焦点中）
        let currentCodeFocus = this._codeEditorFocusTime;
        if (this._codeEditorFocusStart) {
            currentCodeFocus += (Date.now() - this._codeEditorFocusStart) / 1000;
        }
        // 计算当前报错查看时长（如果仍在查看中）
        let currentErrorView = this._errorViewDuration;
        if (this._errorViewStart) {
            currentErrorView += (Date.now() - this._errorViewStart) / 1000;
        }

        return {
            student_id: this.studentId,
            course_id: this.courseId,
            timestamp: now,
            session_duration: this._getPageDwellTime(),
            zone_dwell_times: { ...this._zoneDwellTimes },
            scroll_metrics: {
                avg_speed: this._getAverageScrollSpeed(),
                recent_events: this._scrollEvents.slice(-20),
            },
            mouse_metrics: {
                path_entropy: this._mousePathEntropy,
                recent_entropy_values: this._mouseEvents.slice(-20).map(e => e.entropy),
            },
            overload: {
                current_score: this._overloadScore,
                triggered: this._overloadTriggered,
            },
            performance: {
                fps: this._currentFps,
            },
            // ── 新增遥测数据 ──
            code_editor: {
                focus_time_seconds: Math.round(currentCodeFocus),
                currently_focused: !!this._codeEditorFocusStart,
            },
            code_execution: {
                run_count: this._codeRunCount,
                recent_runs: this._codeRunHistory.slice(-5),
            },
            error_behavior: {
                view_duration_seconds: Math.round(currentErrorView),
                currently_viewing: !!this._errorViewStart,
            },
            paste_events: {
                total_count: this._pasteEvents.length,
                recent_in_editor: this._pasteEvents
                    .filter(e => e.in_code_editor)
                    .slice(-5),
            },
            tab_switching: {
                switch_count: this._tabSwitchCount,
            },
            quiz_performance: {
                consecutive_wrong_count: this._consecutiveWrongCount,
                last_answer_correct: this._lastQuizCorrect,
            },
            deprecated_api: {
                detected: this._deprecatedApiDetected.length > 0,
                details: this._deprecatedApiDetected,
            },
        };
    }

    async _sendWithRetry(payload, maxRetries = 3) {
        for (let attempt = 0; attempt < maxRetries; attempt++) {
            try {
                const res = await fetch(this.apiEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    keepalive: true,
                });
                if (res.ok) return;
                console.warn(`[Telemetry] 上报失败: HTTP ${res.status} (attempt ${attempt + 1}/${maxRetries})`);
            } catch (err) {
                console.warn(`[Telemetry] 请求异常: ${err.message || err} (attempt ${attempt + 1}/${maxRetries})`);
            }
            const delay = Math.pow(2, attempt) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
        }
        console.error('[Telemetry] 上报最终失败，已重试', maxRetries, '次');
    }

    _debounce(fn, delay) {
        let timer = null;
        return function (...args) {
            if (timer) clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    _throttle(fn, interval) {
        let lastTime = 0;
        return function (...args) {
            const now = Date.now();
            if (now - lastTime >= interval) {
                lastTime = now;
                fn.apply(this, args);
            }
        };
    }
}

window.LearningMonitor = LearningMonitor;
