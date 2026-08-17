/**
 * FocusAnalysis — 心流分析共享模块
 *
 * 供 hub.js 和 flow-meter.js 共用：
 *   - 轮询 /api/focus/analysis/{userId}
 *   - localStorage 缓存（TTL 15s）
 *   - 客户端实时状态检测（页面切换频率 + 可见性）
 *   - 事件通知机制
 */
(function () {
    'use strict';

    var CACHE_KEY = 'starlearn_focus_analysis_cache';
    var CACHE_TTL = 15000;
    var STORAGE_KEY = 'starlearn_focus_update';

    var _analysis = null;
    var _pollTimer = null;
    var _pollInterval = 5000;
    var _realtimeTimer = null;
    var _listeners = {};
    var _realtime = {
        state: 'focused',
        switchFrequency: 0,
        lastActivitySec: 0,
        confidence: 1.0
    };

    // ============ helpers ============

    function safeGetJSON(key, fallback) {
        fallback = fallback || {};
        try {
            var v = localStorage.getItem(key);
            return v ? JSON.parse(v) : fallback;
        } catch (e) { return fallback; }
    }

    function getUserId() {
        var user = safeGetJSON('starlearn_user', {});
        return user.id || null;
    }

    function cacheGet() {
        var entry = safeGetJSON(CACHE_KEY, null);
        if (entry && entry.ts && (Date.now() - entry.ts) < CACHE_TTL) {
            return entry.data;
        }
        return null;
    }

    function cacheSet(data) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: data }));
        } catch (e) { /* quota exceeded, ignore */ }
    }

    // ============ event system ============

    function _emit(event, payload) {
        var cbs = _listeners[event] || [];
        for (var i = 0; i < cbs.length; i++) {
            try { cbs[i](payload); } catch (e) { /* ignore */ }
        }
    }

    function on(event, cb) {
        if (!_listeners[event]) _listeners[event] = [];
        _listeners[event].push(cb);
    }

    function off(event, cb) {
        if (!_listeners[event]) return;
        _listeners[event] = _listeners[event].filter(function (f) { return f !== cb; });
    }

    // ============ API ============

    function fetchAnalysis() {
        var userId = getUserId();
        if (!userId) return Promise.resolve(null);

        return fetch('/api/focus/analysis/' + userId + '?range=7d')
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function (data) {
                if (data.success === false) throw new Error(data.detail || 'API error');
                _analysis = data;
                cacheSet(data);
                _emit('analysis-updated', data);
                return data;
            })
            .catch(function (err) {
                console.warn('[FocusAnalysis] fetch failed:', err.message);
                // 返回缓存作为回退
                var cached = cacheGet();
                if (cached) {
                    _analysis = cached;
                    _emit('analysis-updated', cached);
                }
                return null;
            });
    }

    // ============ real-time detection ============

    function _detectRealtimeState() {
        var now = Date.now();
        var pageVisits = [];
        try {
            pageVisits = JSON.parse(localStorage.getItem('page_visits') || '[]');
        } catch (e) { pageVisits = []; }

        // 60秒窗口内的页面切换次数
        var cutoff = now - 60000;
        var recentSwitches = pageVisits.filter(function (t) { return t > cutoff; });
        var switchFreq = recentSwitches.length;

        // 距离最后一次活动的时间
        var lastActivity = 0;
        if (recentSwitches.length > 0) {
            lastActivity = Math.round((now - recentSwitches[recentSwitches.length - 1]) / 1000);
        }

        // 可见性
        var hidden = document.hidden || !document.hasFocus();

        var state;
        if (hidden) {
            state = 'distracted';
        } else if (switchFreq <= 1) {
            state = 'focused';
        } else if (switchFreq <= 3) {
            state = 'lightly';
        } else {
            state = 'distracted';
        }

        var confidence = hidden ? 1.0 : Math.max(0.2, 1.0 - switchFreq * 0.15);

        return {
            state: state,
            switchFrequency: switchFreq,
            lastActivitySec: lastActivity,
            confidence: Math.round(confidence * 100) / 100,
            isHidden: hidden,
            timestamp: now
        };
    }

    function _realtimeTick() {
        var newState = _detectRealtimeState();
        var changed =
            newState.state !== _realtime.state ||
            newState.switchFrequency !== _realtime.switchFrequency;

        _realtime = newState;

        if (changed) {
            _emit('realtime-changed', newState);
        }
    }

    function getRealtimeState() {
        return _realtime;
    }

    // ============ polling ============

    function startPolling(intervalMs) {
        stopPolling();
        if (intervalMs) _pollInterval = intervalMs;

        // 立即拉取一次
        fetchAnalysis();

        // 定时拉取
        _pollTimer = setInterval(function () {
            if (!document.hidden) {
                fetchAnalysis();
            }
        }, _pollInterval);

        // 实时状态检测（每秒）
        if (!_realtimeTimer) {
            _realtimeTimer = setInterval(_realtimeTick, 1000);
        }

        // 从隐藏恢复时立即拉取
        document.addEventListener('visibilitychange', function () {
            if (!document.hidden) {
                fetchAnalysis();
                _realtimeTick();
            }
        });
    }

    function stopPolling() {
        if (_pollTimer) {
            clearInterval(_pollTimer);
            _pollTimer = null;
        }
    }

    function getAnalysis() {
        return _analysis;
    }

    // ============ init ============

    function init() {
        // 从缓存加载
        var cached = cacheGet();
        if (cached) {
            _analysis = cached;
        }

        // 监听 focus-sync 的更新事件
        window.addEventListener('starlearn:focus-updated', function () {
            fetchAnalysis();
        });

        // 跨标签页同步
        window.addEventListener('storage', function (e) {
            if (e.key === STORAGE_KEY) {
                fetchAnalysis();
            }
            if (e.key === CACHE_KEY) {
                var cached = cacheGet();
                if (cached) {
                    _analysis = cached;
                    _emit('analysis-updated', cached);
                }
            }
        });

        // 页面可见性变化
        document.addEventListener('visibilitychange', function () {
            _realtimeTick();
        });
        window.addEventListener('blur', function () { _realtimeTick(); });
        window.addEventListener('focus', function () { _realtimeTick(); });

        // 立即检测一次实时状态
        _realtime = _detectRealtimeState();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.FocusAnalysis = {
        fetchAnalysis: fetchAnalysis,
        startPolling: startPolling,
        stopPolling: stopPolling,
        getAnalysis: getAnalysis,
        getRealtimeState: getRealtimeState,
        on: on,
        off: off,
        _detectRealtimeState: _detectRealtimeState  // exposed for testing
    };
})();
