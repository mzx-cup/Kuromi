(function () {
    const STORAGE_KEY = 'starlearn_focus_pending';
    const LAST_SWITCH_KEY = 'starlearn_focus_last_switch';
    const FLUSH_INTERVAL = 120000;

    function getUserId() {
        try {
            if (window.StarData?.getUserId) return window.StarData.getUserId();
            const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
            return user.id || null;
        } catch (error) {
            return null;
        }
    }

    function readPending() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        } catch (error) {
            return {};
        }
    }

    function writePending(pending) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(pending || {}));
    }

    function resetPending() {
        writePending({
            studyMinutes: 0,
            focusMinutes: 0,
            pageSwitches: 0,
            completedFocus: false,
            source: 'activity',
            updatedAt: Date.now()
        });
    }

    async function postFocusRecord(payload) {
        const userId = getUserId();
        if (!userId) return false;
        const response = await fetch('/api/focus/record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId, ...payload })
        });
        if (!response.ok) throw new Error(`focus record failed: ${response.status}`);
        const data = await response.json();
        if (!data.success) throw new Error(data.detail || 'focus record failed');
        localStorage.setItem('starlearn_focus_update', String(Date.now()));
        window.dispatchEvent(new CustomEvent('starlearn:focus-updated', { detail: data.focusSummary || data }));
        return true;
    }

    async function flush(reason = 'activity') {
        const pending = readPending();
        const studyMinutes = Number(pending.studyMinutes) || 0;
        const focusMinutes = Number(pending.focusMinutes) || 0;
        const pageSwitches = Number(pending.pageSwitches) || 0;
        const completedFocus = Boolean(pending.completedFocus);
        if (!studyMinutes && !focusMinutes && !pageSwitches && !completedFocus) return false;

        try {
            await postFocusRecord({
                studyMinutes,
                focusMinutes,
                pageSwitches,
                completedFocus,
                source: reason || pending.source || 'activity',
                timestamp: new Date().toISOString()
            });
            resetPending();
            return true;
        } catch (error) {
            console.warn('[FocusSync] 保存心流记录失败:', error);
            return false;
        }
    }

    function bump(values, source) {
        const pending = readPending();
        const next = {
            studyMinutes: (Number(pending.studyMinutes) || 0) + (Number(values.studyMinutes) || 0),
            focusMinutes: (Number(pending.focusMinutes) || 0) + (Number(values.focusMinutes) || 0),
            pageSwitches: (Number(pending.pageSwitches) || 0) + (Number(values.pageSwitches) || 0),
            completedFocus: Boolean(pending.completedFocus || values.completedFocus),
            source: source || pending.source || 'activity',
            updatedAt: Date.now()
        };
        writePending(next);

        if (next.completedFocus || next.studyMinutes >= 5 || next.pageSwitches >= 3) {
            flush(next.source);
        }
    }

    function recordStudyMinute(minutes = 1) {
        bump({ studyMinutes: minutes }, 'study_minute');
    }

    function recordFocusComplete(minutes = 0) {
        bump({ focusMinutes: minutes, completedFocus: true }, 'focus_complete');
    }

    function recordPageSwitch() {
        const now = Date.now();
        const last = Number(localStorage.getItem(LAST_SWITCH_KEY) || 0);
        if (now - last < 3000) return;
        localStorage.setItem(LAST_SWITCH_KEY, String(now));
        bump({ pageSwitches: 1 }, 'page_switch');
    }

    function init() {
        if (!localStorage.getItem(STORAGE_KEY)) resetPending();
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) recordPageSwitch();
            else flush('return_to_page');
        });
        window.addEventListener('beforeunload', () => {
            const pending = readPending();
            if (!getUserId()) return;
            if (!pending.studyMinutes && !pending.focusMinutes && !pending.pageSwitches && !pending.completedFocus) return;
            const body = JSON.stringify({
                userId: getUserId(),
                studyMinutes: Number(pending.studyMinutes) || 0,
                focusMinutes: Number(pending.focusMinutes) || 0,
                pageSwitches: Number(pending.pageSwitches) || 0,
                completedFocus: Boolean(pending.completedFocus),
                source: pending.source || 'beforeunload',
                timestamp: new Date().toISOString()
            });
            navigator.sendBeacon?.('/api/focus/record', new Blob([body], { type: 'application/json' }));
        });
        setInterval(() => flush('interval'), FLUSH_INTERVAL);
    }

    window.StarFocusSync = {
        init,
        flush,
        recordStudyMinute,
        recordFocusComplete,
        recordPageSwitch
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
