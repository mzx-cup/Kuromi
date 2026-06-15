// ============================================================
// Phase 2 — 脑暴对话 + 9 件套生成前端状态机
//
// 暴露 4 个全局函数,index.js 调用:
//   - xsStartBrainstorm(requirement, opts)        启动 3 轮脑暴
//   - xsBsTurn({user_choice|user_text, skip})    推进 1 轮
//   - xsConfirmOutline({outline_edit, override})  锁定大纲
//   - xsStartBundle({...})                        9 件套生成 (SSE)
//
// 内部维护 _state = {id, turn, slots, totalTurns}
// 端点: /api/v2/course/brainstorm/{start,id/turn,id/confirm} + /bundle/generate/stream
// ============================================================
(function () {
    'use strict';

    const BRAINSTORM_START = '/api/v2/course/brainstorm/start';
    const BRAINSTORM_TURN = (id) => `/api/v2/course/brainstorm/${encodeURIComponent(id)}/turn`;
    const BRAINSTORM_CONFIRM = (id) => `/api/v2/course/brainstorm/${encodeURIComponent(id)}/confirm`;
    const BUNDLE_STREAM = '/api/v2/course/bundle/generate/stream';

    const SLOT_LABELS = {
        goal: '学习目标',
        base: '知识基础',
        path: '学习路径',
        case: '真实案例',
    };

    const COMPONENT_META = {
        outline:    { icon: '📋', name: '大纲' },
        plan:       { icon: '📝', name: '教案' },
        ppt:        { icon: '🎬', name: 'PPT' },
        graph:      { icon: '🕸', name: '图谱' },
        radar:      { icon: '📊', name: '雷达' },
        project:    { icon: '🛠', name: '项目' },
        case:       { icon: '📖', name: '案例' },
        exercises:  { icon: '✏️', name: '习题' },
        survey:     { icon: '📋', name: '问卷' },
    };

    const _state = {
        id: '',
        turn: 0,
        totalTurns: 3,
        slots: { goal: null, base: null, path: null, case: null },
        requirement: '',
        outline: null,
        obg_pbl_mode: 'obg',
        obg_pbl_rationale: '',
    };

    function _$(id) { return document.getElementById(id); }
    function _show(panel) { panel && panel.classList.remove('hidden'); }
    function _hide(panel) { panel && panel.classList.add('hidden'); }

    function _setBusy(btn, busy, text) {
        if (!btn) return;
        btn.disabled = !!busy;
        if (text != null) btn.textContent = text;
    }

    function _renderBsQuestion(payload) {
        const panel = _$('xs-bs-panel');
        if (!panel) return;
        _show(panel);
        const main = _$('openmaic-main');
        if (main) main.classList.add('xs-bs-active');

        const turn = payload.turn || 1;
        const total = payload.total_turns || 3;
        _state.turn = turn;
        _state.totalTurns = total;
        _state.id = payload.brainstorm_id;

        const turnLabel = _$('xs-bs-turn-label');
        const turnTotal = _$('xs-bs-turn-total');
        if (turnLabel) turnLabel.textContent = String(turn);
        if (turnTotal) turnTotal.textContent = String(total);

        const slot = payload.slot || 'goal';
        const slotBadge = _$('xs-bs-slot-badge');
        if (slotBadge) slotBadge.textContent = `${SLOT_LABELS[slot] || slot} (${turn}/${total})`;

        const qEl = _$('xs-bs-question');
        if (qEl) qEl.textContent = payload.question || '…';

        const optsEl = _$('xs-bs-options');
        if (optsEl) {
            optsEl.innerHTML = '';
            (payload.options || []).forEach((opt) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'xs-bs-option';
                btn.textContent = opt;
                btn.addEventListener('click', function () {
                    optsEl.querySelectorAll('.xs-bs-option.selected').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                });
                optsEl.appendChild(btn);
            });
        }
        const custom = _$('xs-bs-custom');
        if (custom) custom.value = '';

        _setBusy(_$('xs-bs-next'), false, turn >= total ? '生成大纲 →' : '下一题 →');
        _setBusy(_$('xs-bs-skip'), false);
    }

    function _readUserInput() {
        const custom = _$('xs-bs-custom');
        const customText = custom ? custom.value.trim() : '';
        if (customText) return { user_text: customText };
        const selected = document.querySelector('#xs-bs-options .xs-bs-option.selected');
        if (selected) return { user_choice: selected.textContent };
        return null;
    }

    async function xsStartBrainstorm(requirement, opts) {
        opts = opts || {};
        if (!requirement || !requirement.trim()) {
            console.warn('[xsStartBrainstorm] requirement empty');
            return;
        }
        _state.requirement = requirement.trim();

        const confirmPanel = _$('xs-confirm-panel');
        const bundlePanel = _$('xs-bundle-panel');
        _hide(confirmPanel); _hide(bundlePanel);

        try {
            const resp = await fetch(BRAINSTORM_START, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ requirement: _state.requirement, student_id: opts.student_id || '' }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: 'unknown' }));
                throw new Error(err.detail || `start failed (${resp.status})`);
            }
            const data = await resp.json();
            _renderBsQuestion(data);
            _bindBsActions();
        } catch (e) {
            console.error('[xsStartBrainstorm]', e);
            alert('启动脑暴失败: ' + e.message);
        }
    }

    function _bindBsActions() {
        const next = _$('xs-bs-next');
        const skip = _$('xs-bs-skip');
        const close = _$('xs-bs-close');
        if (next && !next._xsBound) {
            next._xsBound = true;
            next.addEventListener('click', async function () {
                const input = _readUserInput();
                if (!input) { alert('请选择一个选项,或在文本框中输入你的想法'); return; }
                _setBusy(next, true, '提交中…');
                _setBusy(skip, true);
                try {
                    await xsBsTurn(input);
                } finally {
                    _setBusy(next, false);
                    _setBusy(skip, false);
                }
            });
        }
        if (skip && !skip._xsBound) {
            skip._xsBound = true;
            skip.addEventListener('click', async function () {
                _setBusy(skip, true, '跳过中…');
                _setBusy(next, true);
                try {
                    await xsBsTurn({ skip: true });
                } finally {
                    _setBusy(skip, false);
                    _setBusy(next, false);
                }
            });
        }
        if (close && !close._xsBound) {
            close._xsBound = true;
            close.addEventListener('click', function () {
                if (confirm('确定要关闭脑暴吗? 已收集的进度会丢失。')) {
                    _resetAll();
                }
            });
        }
    }

    async function xsBsTurn(payload) {
        if (!_state.id) { console.warn('[xsBsTurn] no brainstorm_id'); return; }
        try {
            const resp = await fetch(BRAINSTORM_TURN(_state.id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    brainstorm_id: _state.id,
                    user_choice: payload.user_choice || null,
                    user_text: payload.user_text || null,
                    skip: !!payload.skip,
                }),
            });
            if (resp.status === 400) {
                const err = await resp.json().catch(() => ({}));
                alert(err.detail || '脑暴已完成或参数错误');
                return;
            }
            if (resp.status === 404) {
                alert('脑暴会话不存在,请重新开始');
                _resetAll();
                return;
            }
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `turn failed (${resp.status})`);
            }
            const data = await resp.json();

            if (!data.done) {
                _renderBsQuestion(data);
                return;
            }

            _state.obg_pbl_mode = data.obg_pbl_mode || 'obg';
            _state.obg_pbl_rationale = data.obg_pbl_rationale || '';
            _state.outline = data.outline || null;
            _renderConfirmPanel();
        } catch (e) {
            console.error('[xsBsTurn]', e);
            alert('提交答案失败: ' + e.message);
        }
    }

    function _renderConfirmPanel() {
        const panel = _$('xs-confirm-panel');
        if (!panel) return;
        _hide(_$('xs-bs-panel'));
        const main = _$('openmaic-main');
        if (main) main.classList.remove('xs-bs-active');
        _show(panel);

        const toggle = _$('xs-confirm-toggle');
        if (toggle) {
            toggle.dataset.mode = _state.obg_pbl_mode;
            toggle.textContent = _state.obg_pbl_mode === 'pbl' ? 'PBL · 项目制' : 'OBG · 目标驱动';
        }

        const rationale = _$('xs-confirm-rationale');
        if (rationale) rationale.textContent = _state.obg_pbl_rationale || 'LLM 已根据脑暴答案判定课程模式。';

        const ul = _$('xs-confirm-scenes');
        if (ul) {
            ul.innerHTML = '';
            const scenes = (_state.outline && _state.outline.scenes) || [];
            if (!scenes.length) {
                const li = document.createElement('li');
                li.textContent = '(未生成场景,请重试)';
                ul.appendChild(li);
            } else {
                scenes.forEach((s, i) => {
                    const li = document.createElement('li');
                    const title = (s && (s.title || s.name)) || `场景 ${i + 1}`;
                    const desc = (s && (s.description || s.summary || s.outcome)) || '';
                    li.innerHTML = `<strong>${i + 1}.</strong> ${_escapeHtml(title)}<br><span style="color:#94a3b8;font-size:12px">${_escapeHtml(desc)}</span>`;
                    ul.appendChild(li);
                });
            }
        }

        const go = _$('xs-confirm-go');
        if (go && !go._xsBound) {
            go._xsBound = true;
            go.addEventListener('click', async function () {
                const edit = {}; // 暂不提供 UI 编辑, 直接确认
                const override = _state.obg_pbl_mode;
                _setBusy(go, true, '锁定中…');
                try {
                    const ok = await xsConfirmOutline({ outline_edit: edit, obg_pbl_override: override });
                    if (ok) {
                        _renderBundlePanel();
                        await xsStartBundle({});
                    }
                } finally {
                    _setBusy(go, false, '开始生成 9 件套 →');
                }
            });
        }
        const back = _$('xs-confirm-back');
        if (back && !back._xsBound) {
            back._xsBound = true;
            back.addEventListener('click', function () {
                _hide(panel);
                _show(_$('xs-bs-panel'));
                if (main) main.classList.add('xs-bs-active');
            });
        }
        const toggle2 = _$('xs-confirm-toggle');
        if (toggle2 && !toggle2._xsBound) {
            toggle2._xsBound = true;
            toggle2.addEventListener('click', function () {
                _state.obg_pbl_mode = _state.obg_pbl_mode === 'pbl' ? 'obg' : 'pbl';
                toggle2.dataset.mode = _state.obg_pbl_mode;
                toggle2.textContent = _state.obg_pbl_mode === 'pbl' ? 'PBL · 项目制' : 'OBG · 目标驱动';
            });
        }
    }

    async function xsConfirmOutline({ outline_edit, obg_pbl_override }) {
        if (!_state.id) return false;
        try {
            const resp = await fetch(BRAINSTORM_CONFIRM(_state.id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    brainstorm_id: _state.id,
                    outline_edit: outline_edit || {},
                    obg_pbl_override: obg_pbl_override || '',
                }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `confirm failed (${resp.status})`);
            }
            const data = await resp.json();
            if (data.outline) _state.outline = data.outline;
            if (data.obg_pbl_mode) _state.obg_pbl_mode = data.obg_pbl_mode;
            return true;
        } catch (e) {
            console.error('[xsConfirmOutline]', e);
            alert('锁定大纲失败: ' + e.message);
            return false;
        }
    }

    function _renderBundlePanel() {
        const panel = _$('xs-bundle-panel');
        if (!panel) return;
        _hide(_$('xs-confirm-panel'));
        _show(panel);

        const grid = panel.querySelector('.xs-bundle-grid');
        if (grid) {
            grid.innerHTML = '';
            Object.keys(COMPONENT_META).forEach((name) => {
                const meta = COMPONENT_META[name];
                const div = document.createElement('div');
                div.className = 'xs-comp';
                div.dataset.name = name;
                div.dataset.state = 'pending';
                div.innerHTML = `
                    <div class="xs-comp-icon">${meta.icon}</div>
                    <div class="xs-comp-name">${meta.name}</div>
                    <div class="xs-comp-state">等待中</div>
                `;
                grid.appendChild(div);
            });
        }
    }

    function _setComponentState(name, state, label) {
        const el = document.querySelector(`#xs-bundle-panel .xs-comp[data-name="${name}"]`);
        if (!el) return;
        el.dataset.state = state;
        const stateEl = el.querySelector('.xs-comp-state');
        if (stateEl && label) stateEl.textContent = label;
    }

    async function xsStartBundle(opts) {
        opts = opts || {};
        const studentId = (() => {
            try { return (JSON.parse(localStorage.getItem('starlearn_user') || '{}') || {}).id || ''; }
            catch (e) { return ''; }
        })();

        const body = {
            requirement: _state.requirement,
            student_id: studentId,
            brainstorm_id: _state.id,
            enabled_components: opts.enabled_components || Object.keys(COMPONENT_META),
            obg_pbl_mode: _state.obg_pbl_mode,
            outline_override: opts.outline_override || (_state.outline || {}),
        };

        try {
            const resp = await fetch(BUNDLE_STREAM, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (resp.status === 400) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || '请求参数错误,请先完成脑暴');
            }
            if (resp.status === 404) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || '脑暴会话已过期,请重新开始');
            }
            if (!resp.ok || !resp.body) {
                throw new Error('bundle stream failed: ' + resp.status);
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buf = '';
            const seen = new Set();
            let finalBundle = null;

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buf += decoder.decode(value, { stream: true });

                let idx;
                while ((idx = buf.indexOf('\n\n')) >= 0) {
                    const raw = buf.slice(0, idx);
                    buf = buf.slice(idx + 2);
                    const ev = _parseSseEvent(raw);
                    if (!ev) continue;
                    if (ev.event === 'component_start') {
                        const name = ev.data && ev.data.name;
                        if (name) _setComponentState(name, 'running', '生成中…');
                    } else if (ev.event === 'component_ready') {
                        const name = ev.data && ev.data.name;
                        if (name) {
                            const status = (ev.data && ev.data.status) || 'ready';
                            const label = status === 'fallback' ? '占位生成' : '已生成';
                            _setComponentState(name, status, label);
                            seen.add(name);
                        }
                    } else if (ev.event === 'bundle_complete') {
                        finalBundle = (ev.data && ev.data.bundle) || ev.data;
                    } else if (ev.event === 'error' || (ev.data && ev.data.error)) {
                        console.warn('[xsStartBundle] SSE error event:', ev.data);
                    }
                }
            }

            const cancel = _$('xs-bundle-cancel');
            if (cancel) {
                cancel.style.display = 'none';
            }

            if (finalBundle) {
                // 反馈给 UI: 全部 9 件已就绪
                const titleEl = _$('xs-bundle-title');
                if (titleEl) titleEl.textContent = '9 件套生成完成, 正在保存到课程库…';
                try {
                    await _saveAndRedirect(finalBundle, studentId);
                } catch (e) {
                    console.error('[xsStartBundle] save+redirect failed', e);
                    const titleEl2 = _$('xs-bundle-title');
                    if (titleEl2) {
                        titleEl2.textContent = '保存失败: ' + e.message;
                        titleEl2.style.color = '#fca5a5';
                    }
                    // 兜底: 仍然把 bundle 写到 sessionStorage, 允许用户手动重试
                    try { sessionStorage.setItem('xs_course_bundle', JSON.stringify(finalBundle)); } catch (e2) { /* ignore quota */ }
                    if (typeof window.xsOnBundleComplete === 'function') {
                        try { window.xsOnBundleComplete({ bundle: finalBundle, seen: Array.from(seen), saved: false, error: e.message }); } catch (e2) { console.warn('[xsOnBundleComplete]', e2); }
                    }
                    alert('保存课程失败: ' + e.message + '\n请检查网络后刷新重试');
                }
            } else {
                console.warn('[xsStartBundle] bundle_complete 未收到, 9 件套生成可能不完整');
                const titleEl = _$('xs-bundle-title');
                if (titleEl) {
                    titleEl.textContent = '生成未完成, 缺少 bundle_complete 事件';
                    titleEl.style.color = '#fca5a5';
                }
                alert('9 件套未生成完整, 请重试');
            }
        } catch (e) {
            console.error('[xsStartBundle]', e);
            alert('9 件套生成失败: ' + e.message);
        }
    }

    // ============================================================
    // bundle_complete → 落盘到服务端 + 跳到 classroom
    // ============================================================

    function _outlineToSceneOutlines(outline) {
        // 把脑暴的 outline.scenes (id="s1", key_points=[...]) 翻译成
        // CourseData.outlines (id:int, key_points, type)
        const scenes = (outline && outline.scenes) || [];
        return scenes.map((s, i) => {
            const rawId = s && (s.id ?? s.scene_id);
            let intId = i + 1;
            if (typeof rawId === 'number' && Number.isFinite(rawId)) {
                intId = rawId;
            } else if (typeof rawId === 'string' && /^\d+$/.test(rawId)) {
                intId = parseInt(rawId, 10);
            } else if (typeof rawId === 'string' && /^s\d+$/.test(rawId)) {
                intId = parseInt(rawId.slice(1), 10) || (i + 1);
            }
            const keyPoints = (s && s.key_points) || [];
            return {
                id: intId,
                title: (s && s.title) || `场景 ${i + 1}`,
                type: (s && s.type) || 'slide',
                points: Array.isArray(keyPoints) ? keyPoints.length : 0,
                key_points: Array.isArray(keyPoints) ? keyPoints : [],
                description: (s && s.description) || '',
            };
        });
    }

    function _buildCourseData(bundle, studentId) {
        const outline = _state.outline || {};
        const components = (bundle && bundle.components) || {};
        const pptMeta = components.ppt || {};
        // 从 bundle PPT 组件提取 slides_v2, 让 classroom 直接可渲染
        var slidesV2 = (pptMeta.slides && Array.isArray(pptMeta.slides)) ? pptMeta.slides.slice() : [];
        // 如果 PPT 组件没带 slides 但 bundle 顶层有(兼容旧格式)
        if (!slidesV2.length && bundle && Array.isArray(bundle.slides_v2)) {
            slidesV2 = bundle.slides_v2.slice();
        }
        return {
            courseId: '',
            title: outline.title || _state.requirement || '未命名课程',
            outlines: _outlineToSceneOutlines(outline),
            slides: [],
            slides_v2: slidesV2,
            agent_team: [],
            quiz_data: [],
            exercise_data: [],
            interactive_data: [],
            code_data: [],
            tts_audio_urls: {},
            scene_actions: [],
            metadata: {
                student_id: String(studentId || ''),
                requirement: _state.requirement || '',
                brainstorm_id: _state.id || '',
                obg_pbl_mode: _state.obg_pbl_mode || 'obg',
                generated_at: new Date().toISOString(),
            },
            bundle: bundle || null,
        };
    }

    async function _saveAndRedirect(bundle, studentId) {
        if (!bundle) {
            throw new Error('9 件套未生成完整, 缺少 bundle_complete 事件');
        }
        const courseData = _buildCourseData(bundle, studentId);
        const pptPages = (bundle.components && bundle.components.ppt
            && (bundle.components.ppt.slide_count || bundle.components.ppt.slide_titles.length)) || 0;

        const resp = await fetch('/api/v2/course/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_data: courseData,
                student_id: String(studentId || ''),
                ppt_pages: pptPages,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
            throw new Error('保存失败: ' + (err.detail || err.message || `HTTP ${resp.status}`));
        }
        const result = await resp.json();
        if (!result || !result.success || !result.course_id) {
            throw new Error('保存返回异常: ' + JSON.stringify(result || {}));
        }
        courseData.courseId = result.course_id;

        // 1) 写 sessionStorage 让 classroom.js loadData() 立即可见
        try { sessionStorage.setItem('classroomData', JSON.stringify(courseData)); } catch (e) { /* ignore quota */ }
        // 2) 写 localStorage.courseHistory (与 openCourse 一致)
        try {
            const history = JSON.parse(localStorage.getItem('courseHistory') || '[]');
            const existingIdx = history.findIndex(c => c && c.courseId === courseData.courseId);
            const summary = {
                courseId: courseData.courseId,
                title: courseData.title,
                outlines: (courseData.outlines || []).length,
                slides: 0,
                slides_v2: 0,
                created_at: courseData.metadata.generated_at,
                requirement: _state.requirement,
            };
            if (existingIdx >= 0) history[existingIdx] = summary;
            else history.unshift(summary);
            localStorage.setItem('courseHistory', JSON.stringify(history.slice(0, 20)));
        } catch (e) { /* ignore */ }
        // 3) 也保留 xs_course_bundle 给潜在外部 hook
        try { sessionStorage.setItem('xs_course_bundle', JSON.stringify(bundle)); } catch (e) { /* ignore quota */ }

        // 4) 跳到 classroom, 携带 courseId 参数
        window.location.href = 'classroom.html?course_id=' + encodeURIComponent(result.course_id);
    }

    function _parseSseEvent(raw) {
        if (!raw) return null;
        const lines = raw.split('\n');
        let event = 'message';
        let data = null;
        for (const line of lines) {
            if (line.startsWith('event:')) event = line.slice(6).trim();
            else if (line.startsWith('data:')) {
                const s = line.slice(5).trim();
                if (!s) continue;
                try { data = JSON.parse(s); } catch (e) { data = s; }
            }
        }
        return { event, data };
    }

    function _resetAll() {
        const main = _$('openmaic-main');
        if (main) main.classList.remove('xs-bs-active');
        _hide(_$('xs-bs-panel'));
        _hide(_$('xs-confirm-panel'));
        _hide(_$('xs-bundle-panel'));
        if (main) _show(main);
        _state.id = '';
        _state.turn = 0;
        _state.slots = { goal: null, base: null, path: null, case: null };
        _state.outline = null;
    }

    function _escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    window.xsStartBrainstorm = xsStartBrainstorm;
    window.xsBsTurn = xsBsTurn;
    window.xsConfirmOutline = xsConfirmOutline;
    window.xsStartBundle = xsStartBundle;
})();
