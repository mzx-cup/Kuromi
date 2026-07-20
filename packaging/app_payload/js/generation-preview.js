/**
 * Generation Preview Page — Phase 2 流程宿主
 *
 * 职责:
 *  1. 读取 requirement (URL ?q= 或 sessionStorage.generationSession)
 *  2. 未带 requirement → 显示输入卡, 用户输入后启动脑暴
 *  3. 已带 requirement → 立刻启动 3 轮脑暴
 *  4. 脑暴完成后渲染大纲确认 + 9 件套进度 (走 brainstorm.js 暴露的 4 个全局函数)
 *  5. 完成后落盘 + 跳到 classroom (与原逻辑一致)
 */
(function () {
    'use strict';

    const _ = function (id) { return document.getElementById(id); };

    // 工具
    function _readQuery() {
        const u = new URL(window.location.href);
        return (u.searchParams.get('q') || u.searchParams.get('requirement') || '').trim();
    }

    function _readSession() {
        try {
            const raw = sessionStorage.getItem('generationSession');
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (e) { return null; }
    }

    function _setReadout(text) {
        const el = _('gp-requirement-readout');
        if (el) el.textContent = text ? ('课程主题: ' + text) : '';
    }

    function _show(id) {
        const el = _(id);
        if (el) el.classList.remove('hidden');
    }
    function _hide(id) {
        const el = _(id);
        if (el) el.classList.add('hidden');
    }

    function init() {
        const backBtn = _('back-btn');
        if (backBtn) backBtn.addEventListener('click', goBack);

        // 1) 解析入参
        const queryReq = _readQuery();
        let session = _readSession();
        const sessionReq = session && (session.requirement || (session.requirements && session.requirements.requirement) || '');

        const requirement = queryReq || sessionReq || '';

        if (requirement) {
            _setReadout(requirement);
            _hide('gp-requirement-card');
            // 启动脑暴
            if (typeof window.xsStartBrainstorm === 'function') {
                window.xsStartBrainstorm(requirement);
            } else {
                console.error('[generation-preview] brainstorm.js 未加载');
                alert('脑暴模块未就绪, 请刷新重试');
            }
        } else {
            // 显示输入卡
            _hide('xs-bs-panel');
            _hide('xs-confirm-panel');
            _hide('xs-bundle-panel');
            _show('gp-requirement-card');
            const startBtn = _('gp-requirement-start');
            const inputEl = _('gp-requirement-input');
            if (startBtn) {
                startBtn.addEventListener('click', function () {
                    const v = inputEl ? inputEl.value.trim() : '';
                    if (!v) { alert('请输入课程主题'); return; }
                    _setReadout(v);
                    _hide('gp-requirement-card');
                    if (typeof window.xsStartBrainstorm === 'function') {
                        window.xsStartBrainstorm(v);
                    } else {
                        alert('脑暴模块未就绪, 请刷新重试');
                    }
                });
            }
            if (inputEl) {
                inputEl.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault();
                        startBtn && startBtn.click();
                    }
                });
            }
        }
    }

    function goBack() {
        sessionStorage.removeItem('generationSession');
        window.location.href = '/';
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
