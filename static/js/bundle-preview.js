/* ============================================================
 * bundle-preview.js — 9 件套生成结果预览面板
 * ------------------------------------------------------------
 * 目标: bundle 生成完成后不直接跳 classroom, 先在生成页就地预览:
 *   - PPT: 轮播 (element 格式走 OpenMAICSlidePlayer 等比缩放,
 *           卡片格式走轻量渲染器)
 *   - 其余 8 件 + ability_graph: 各自结构化渲染
 *   - 支持生成中增量到达 (brainstorm.js pushComponent 实时刷新)
 *   - 每件可单独下载 JSON
 *
 * 对外 API: window.xsBundlePreview.{open, pushComponent, close}
 * 依赖: openmaic-slide-player.js (element 幻灯片; 未加载时自动降级)
 * ============================================================ */
(function () {
    'use strict';

    // 组件元信息: 顺序即 Tab 顺序
    var COMPONENT_META = {
        ppt:        { label: '课件 PPT',  icon: '🖥' },
        outline:    { label: '课程大纲',  icon: '🗺' },
        plan:       { label: '教案',      icon: '📋' },
        graph:      { label: '知识图谱',  icon: '🕸' },
        ability_graph: { label: '能力图谱', icon: '🧭' },
        radar:      { label: '学情雷达',  icon: '📡' },
        project:    { label: '实战项目',  icon: '🚀' },
        case:       { label: '案例研究',  icon: '📖' },
        exercises:  { label: '课后习题',  icon: '✏️' },
        survey:     { label: '课前问卷',  icon: '📝' },
    };

    // 雷达 8 维中文名
    var RADAR_DIMS = [
        ['knowledge_mastery', '知识掌握'],
        ['code_skill', '代码技能'],
        ['cognitive_level', '认知水平'],
        ['learning_goal', '学习目标'],
        ['weakness', '薄弱环节'],
        ['focus_level', '专注程度'],
        ['process', '过程投入'],
        ['innovation', '创新思维'],
    ];

    var THEME_COLORS = {
        blue: '#2563eb', yellow: '#d97706', green: '#059669',
        purple: '#7c3aed', orange: '#ea580c',
    };

    var state = {
        open: false,
        courseData: null,
        components: {},          // name -> payload
        classroomUrl: '',
        activeTab: 'ppt',
        slideIndex: 0,
        player: null,            // OpenMAICSlidePlayer 实例
        keyboardBound: false,
    };

    // ---------- 工具 ----------

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function el(id) { return document.getElementById(id); }

    /** 富文本: 只放行白名单标签, 其余转义 (payload 来自 LLM, 不可全信) */
    function rich(s) {
        var raw = String(s == null ? '' : s);
        var safe = raw.replace(/<(?!\/?(h[1-6]|b|strong|i|em|u|br|ul|ol|li|code|pre|p|span|div)\b)[^>]*>/gi, function (m) {
            return esc(m);
        });
        // strip 事件属性与 javascript: 链接
        safe = safe.replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '');
        safe = safe.replace(/href\s*=\s*("|')\s*javascript:[^"']*\1/gi, '');
        return safe;
    }

    // ---------- 面板骨架 ----------

    function ensurePanel() {
        if (el('xsvp-overlay')) return;
        var overlay = document.createElement('div');
        overlay.id = 'xsvp-overlay';
        overlay.className = 'xsvp-overlay';
        overlay.innerHTML =
            '<div class="xsvp-panel" role="dialog" aria-label="课程 9 件套预览">' +
                '<header class="xsvp-header">' +
                    '<div class="xsvp-head-text">' +
                        '<div class="xsvp-title" id="xsvp-title">课程 9 件套预览</div>' +
                        '<div class="xsvp-sub" id="xsvp-sub"></div>' +
                    '</div>' +
                    '<div class="xsvp-head-actions">' +
                        '<button class="xsvp-btn xsvp-btn-ghost" id="xsvp-dl-all">全部下载</button>' +
                        '<button class="xsvp-btn xsvp-btn-primary" id="xsvp-enter">进入课堂 →</button>' +
                        '<button class="xsvp-icon-btn" id="xsvp-close" aria-label="关闭">✕</button>' +
                    '</div>' +
                '</header>' +
                '<div class="xsvp-body">' +
                    '<nav class="xsvp-nav" id="xsvp-nav"></nav>' +
                    '<main class="xsvp-main" id="xsvp-main"></main>' +
                '</div>' +
            '</div>';
        document.body.appendChild(overlay);

        el('xsvp-close').addEventListener('click', api.close);
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) api.close();
        });
        el('xsvp-enter').addEventListener('click', function () {
            if (state.classroomUrl) window.location.href = state.classroomUrl;
        });
        el('xsvp-dl-all').addEventListener('click', function () {
            Object.keys(state.components).forEach(function (name, i) {
                setTimeout(function () { downloadJson(name, state.components[name]); }, i * 250);
            });
        });
    }

    function bindKeyboard() {
        if (state.keyboardBound) return;
        state.keyboardBound = true;
        document.addEventListener('keydown', function (e) {
            if (!state.open) return;
            if (e.key === 'Escape') { api.close(); return; }
            if (state.activeTab !== 'ppt') return;
            if (e.key === 'ArrowLeft') { navSlide(-1); e.preventDefault(); }
            if (e.key === 'ArrowRight') { navSlide(1); e.preventDefault(); }
        });
    }

    // ---------- 对外 API ----------

    var api = window.xsBundlePreview = {

        /** 打开面板. courseData 为 brainstorm._buildCourseData 的产物 */
        open: function (courseData, opts) {
            opts = opts || {};
            state.courseData = courseData || {};
            state.classroomUrl = opts.classroomUrl || '';
            state.components = normalizeComponents(state.courseData);
            state.open = true;
            state.slideIndex = 0;

            ensurePanel();
            bindKeyboard();

            var title = (state.courseData && state.courseData.title) || '课程 9 件套';
            el('xsvp-title').textContent = title + ' — 生成结果预览';
            var counts = Object.keys(state.components).length;
            el('xsvp-sub').textContent = counts + ' 件已生成 · 保存于课程库, 关闭本页不丢失';
            var enterBtn = el('xsvp-enter');
            if (!state.classroomUrl) enterBtn.style.display = 'none';
            else enterBtn.style.display = '';

            var overlay = el('xsvp-overlay');
            overlay.style.display = 'flex';
            requestAnimationFrame(function () { overlay.classList.add('xsvp-visible'); });

            // 默认落在 PPT; PPT 没到就看第一个有的
            state.activeTab = state.components.ppt ? 'ppt' : firstAvailable();
            renderNav();
            renderActive();
        },

        /** 生成中增量推送: 某件 ready 即刻可见 */
        pushComponent: function (name, payload) {
            if (!name || !payload) return;
            state.components[name] = payload;
            if (!state.open) return;
            // 面板已开: 刷新 Tab 状态; 当前 Tab 就是它则重渲内容
            renderNav();
            if (state.activeTab === name) renderActive();
            var counts = Object.keys(state.components).length;
            var sub = el('xsvp-sub');
            if (sub) sub.textContent = counts + ' 件已生成 · 保存于课程库, 关闭本页不丢失';
        },

        close: function () {
            state.open = false;
            var overlay = el('xsvp-overlay');
            if (!overlay) return;
            overlay.classList.remove('xsvp-visible');
            setTimeout(function () { overlay.style.display = 'none'; }, 180);
        },

        /** 关闭面板后重新打开: 从 sessionStorage 恢复已保存的课程 */
        reopenFromSession: function () {
            var raw = null;
            try { raw = sessionStorage.getItem('classroomData'); } catch (e) { /* ignore */ }
            if (!raw) { alert('本地没有已保存的课程数据'); return; }
            var courseData;
            try { courseData = JSON.parse(raw); } catch (e) { alert('课程数据解析失败'); return; }
            var url = '';
            if (courseData.courseId) url = 'classroom.html?course_id=' + encodeURIComponent(courseData.courseId);
            api.open(courseData, { classroomUrl: url });
        },
    };

    function firstAvailable() {
        var order = Object.keys(COMPONENT_META);
        for (var i = 0; i < order.length; i++) {
            if (state.components[order[i]]) return order[i];
        }
        return 'ppt';
    }

    /** bundle.components 为准, 兼容顶层平铺的 *_data 字段 */
    function normalizeComponents(courseData) {
        var out = {};
        var bundle = courseData && courseData.bundle;
        var fromBundle = (bundle && bundle.components) || {};
        Object.keys(fromBundle).forEach(function (k) {
            var v = fromBundle[k];
            if (v && typeof v === 'object') out[k] = v;
        });
        var flat = {
            outline: courseData.outline_data, plan: courseData.plan_data,
            ppt: courseData.ppt_data, graph: courseData.graph_data,
            radar: courseData.radar_data, project: courseData.project_data,
            case: courseData.case_data, exercises: courseData.exercises_data,
            survey: courseData.survey_data,
        };
        Object.keys(flat).forEach(function (k) {
            if (!out[k] && flat[k] && typeof flat[k] === 'object') out[k] = flat[k];
        });
        return out;
    }

    // ---------- Tab 导航 ----------

    function renderNav() {
        var nav = el('xsvp-nav');
        if (!nav) return;
        var html = '';
        Object.keys(COMPONENT_META).forEach(function (name) {
            var meta = COMPONENT_META[name];
            var has = !!state.components[name];
            var cls = 'xsvp-tab' + (state.activeTab === name ? ' xsvp-tab-active' : '') + (has ? '' : ' xsvp-tab-missing');
            html += '<button class="' + cls + '" data-xsvp-tab="' + name + '" ' + (has ? '' : 'disabled') + '>' +
                '<span class="xsvp-tab-icon">' + meta.icon + '</span>' +
                '<span class="xsvp-tab-label">' + esc(meta.label) + '</span>' +
                '<span class="xsvp-tab-dot' + (has ? ' xsvp-tab-dot-on' : '') + '"></span>' +
                '</button>';
        });
        nav.innerHTML = html;
        Array.prototype.forEach.call(nav.querySelectorAll('.xsvp-tab'), function (btn) {
            btn.addEventListener('click', function () {
                state.activeTab = btn.getAttribute('data-xsvp-tab');
                if (state.activeTab === 'ppt') state.slideIndex = 0;
                renderNav();
                renderActive();
            });
        });
    }

    function renderActive() {
        var main = el('xsvp-main');
        if (!main) return;
        var payload = state.components[state.activeTab];
        if (!payload) {
            main.innerHTML = '<div class="xsvp-empty">该组件尚未生成…</div>';
            return;
        }
        try {
            main.innerHTML = componentShell(state.activeTab, payload);
            wireShell(state.activeTab, payload, main);
        } catch (e) {
            console.error('[xsBundlePreview] render "' + state.activeTab + '" failed', e);
            main.innerHTML = '<div class="xsvp-empty">渲染失败: ' + esc(e.message) + '</div>';
        }
    }

    /** 每件内容外的公共壳: fallback 提示 + 下载按钮 */
    function componentShell(name, payload) {
        var meta = COMPONENT_META[name] || { label: name, icon: '📄' };
        var head = '<div class="xsvp-comp-head">' +
            '<h2>' + meta.icon + ' ' + esc(meta.label) + '</h2>' +
            '<button class="xsvp-btn xsvp-btn-ghost xsvp-dl" data-xsvp-dl="' + esc(name) + '">下载 JSON</button>' +
            '</div>';
        var note = '';
        if (payload.status && payload.status !== 'ok' && payload.note) {
            note = '<div class="xsvp-note">⚠ ' + esc(payload.note) + '</div>';
        }
        var body = renderComponentBody(name, payload);
        return head + note + body;
    }

    function wireShell(name, payload, main) {
        var dl = main.querySelector('.xsvp-dl');
        if (dl) dl.addEventListener('click', function () { downloadJson(name, payload); });
        wireComponent(name, payload, main);
    }

    function downloadJson(name, payload) {
        try {
            var blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'course-' + name + '.json';
            document.body.appendChild(a);
            a.click();
            setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
        } catch (e) { console.warn('[xsBundlePreview] download failed', e); }
    }

    // ---------- 各组件渲染 ----------

    function renderComponentBody(name, payload) {
        switch (name) {
            case 'ppt': return renderPpt(payload);
            case 'outline': return renderOutline(payload);
            case 'plan': return renderPlan(payload);
            case 'graph': return renderGraph(payload.nodes, payload.edges);
            case 'ability_graph': return renderAbilityGraph(payload);
            case 'radar': return renderRadar(payload);
            case 'project': return renderProject(payload);
            case 'case': return renderCase(payload);
            case 'exercises': return renderExercises(payload);
            case 'survey': return renderSurvey(payload);
            default: return renderGeneric(payload);
        }
    }

    function wireComponent(name, payload, main) {
        if (name === 'ppt') wirePpt(main);
        if (name === 'exercises') wireExercises(main);
    }

    // ---- PPT 轮播 ----

    /** 取幻灯片数组: 直挂 slides, 或 OpenMAIC deck 嵌套 */
    function pptSlides(payload) {
        var slides = (payload && payload.slides) || [];
        if (!slides.length && window.OpenMAICSlidePlayer) {
            var deck = window.OpenMAICSlidePlayer.extractDeck(payload);
            if (deck) slides = deck.slides;
        }
        return slides;
    }

    function renderPpt(payload) {
        var slides = pptSlides(payload);
        if (!slides.length) {
            return '<div class="xsvp-empty">PPT 组件没有幻灯片数据' +
                (payload && payload.note ? ' — ' + esc(payload.note) : '') + '</div>';
        }
        return '<div class="xsvp-ppt">' +
            '<div class="xsvp-slide-stage" id="xsvp-slide-stage"></div>' +
            '<div class="xsvp-slide-ctrl">' +
                '<button class="xsvp-icon-btn" id="xsvp-prev" aria-label="上一页">‹</button>' +
                '<span class="xsvp-slide-count" id="xsvp-slide-count"></span>' +
                '<button class="xsvp-icon-btn" id="xsvp-next" aria-label="下一页">›</button>' +
            '</div>' +
            '<div class="xsvp-slide-thumbs" id="xsvp-thumbs"></div>' +
            '</div>';
    }

    function wirePpt() {
        var payload = state.components.ppt || {};
        var slides = pptSlides(payload);
        var stage = el('xsvp-slide-stage');
        if (!stage || !slides.length) return;

        var prev = el('xsvp-prev'), next = el('xsvp-next');
        if (prev) prev.addEventListener('click', function () { navSlide(-1); });
        if (next) next.addEventListener('click', function () { navSlide(1); });

        // 缩略图
        var thumbs = el('xsvp-thumbs');
        if (thumbs) {
            var html = '';
            slides.forEach(function (s, i) {
                var t = (s && s.title) || sceneTitleOf(s) || ('第 ' + (i + 1) + ' 页');
                html += '<button class="xsvp-thumb" data-i="' + i + '" title="' + esc(t) + '">' + esc(t.slice(0, 14)) + '</button>';
            });
            thumbs.innerHTML = html;
            Array.prototype.forEach.call(thumbs.querySelectorAll('.xsvp-thumb'), function (b) {
                b.addEventListener('click', function () {
                    state.slideIndex = parseInt(b.getAttribute('data-i'), 10) || 0;
                    showSlide();
                });
            });
        }
        state.slideIndex = Math.min(state.slideIndex, slides.length - 1);
        showSlide();
    }

    function navSlide(delta) {
        var slides = pptSlides(state.components.ppt || {});
        if (!slides.length) return;
        state.slideIndex = (state.slideIndex + delta + slides.length) % slides.length;
        showSlide();
    }

    function sceneTitleOf(slide) {
        if (slide && slide._scene_title) return slide._scene_title;
        return '';
    }

    function showSlide() {
        var slides = pptSlides(state.components.ppt || {});
        var stage = el('xsvp-slide-stage');
        if (!stage || !slides.length) return;

        var slide = slides[state.slideIndex] || {};
        var count = el('xsvp-slide-count');
        if (count) count.textContent = (state.slideIndex + 1) + ' / ' + slides.length;

        var thumbs = el('xsvp-thumbs');
        if (thumbs) {
            Array.prototype.forEach.call(thumbs.querySelectorAll('.xsvp-thumb'), function (b, i) {
                b.classList.toggle('xsvp-thumb-active', i === state.slideIndex);
            });
        }

        if (Array.isArray(slide.elements) && window.OpenMAICSlidePlayer) {
            // element 格式 → 真实播放器, 画布固定 1000x562.5 等比缩放
            if (!state.player) {
                state.player = new window.OpenMAICSlidePlayer({ container: stage });
            }
            state.player.render(slide);
            var canvas = stage.querySelector('.openmaic-slide-canvas');
            if (canvas) {
                canvas.style.width = '1000px';
                canvas.style.height = '562.5px';
                canvas.style.transformOrigin = '0 0';
                fitCanvas(canvas);
            }
        } else {
            // 卡片格式 → 轻量渲染
            state.player = null;
            stage.innerHTML = renderCardSlide(slide);
        }
    }

    /** 窗口尺寸变化时重算缩放 (1000px 逻辑宽 → 实际容器宽) */
    function fitCanvas(canvas) {
        var stage = canvas.parentElement && canvas.parentElement.parentElement;
        if (!stage) return;
        var scale = stage.clientWidth / 1000;
        canvas.style.transform = 'scale(' + scale + ')';
    }

    window.addEventListener('resize', function () {
        if (!state.open || state.activeTab !== 'ppt') return;
        var canvas = document.querySelector('#xsvp-slide-stage .openmaic-slide-canvas');
        if (canvas) fitCanvas(canvas);
    });

    // ---- 卡片格式幻灯片 (slide_content_v2) 轻量渲染 ----

    function renderCardSlide(slide) {
        var contents = (slide && slide.content) || [];
        var theme = (contents[0] && contents[0].colorTheme) || slide._color_hint || 'blue';
        var color = THEME_COLORS[theme] || THEME_COLORS.blue;

        var bodyHtml = '';
        if (contents.length === 0) {
            bodyHtml = '<div class="xc-empty">（无内容）</div>';
        } else if (contents.length === 1) {
            bodyHtml = cardBlock(contents[0], color, true);
        } else {
            var cols = contents.length >= 4 ? 'xc-cols-2' : 'xc-cols-row';
            bodyHtml = '<div class="xc-multi ' + cols + '">' +
                contents.map(function (c) { return cardBlock(c, color, false); }).join('') +
                '</div>';
        }

        var sceneTag = slide._scene_title
            ? '<div class="xc-scene-tag">' + esc(slide._scene_title) + '</div>' : '';
        var layout = slide.layoutType || slide.layout_type || '';

        return '<div class="xsvp-card-slide" style="--xc-accent:' + color + '">' +
            '<div class="xc-accent-bar"></div>' +
            sceneTag +
            '<h1 class="xc-title">' + esc(slide.title || '未命名') + '</h1>' +
            bodyHtml +
            '<div class="xc-layout-tag">' + esc(layout) + '</div>' +
            '</div>';
    }

    function cardBlock(c, color, wide) {
        var html = '<div class="xc-block' + (wide ? ' xc-block-wide' : '') + '">';
        if (c.subTitle) html += '<h3 class="xc-sub">' + esc(c.subTitle) + '</h3>';
        var bullets = c.bullets || [];
        if (bullets.length) {
            html += '<ul class="xc-bullets">' +
                bullets.map(function (b) { return '<li>' + rich(b) + '</li>'; }).join('') +
                '</ul>';
        }
        if (c.codeSnippet) {
            html += '<pre class="xc-code"><code>' + esc(c.codeSnippet) + '</code></pre>';
        }
        html += '</div>';
        return html;
    }

    // ---- outline ----

    function renderOutline(payload) {
        var scenes = (payload && payload.scenes) || [];
        if (!scenes.length) return '<div class="xsvp-empty">大纲没有场景数据</div>';
        var meta = [];
        if (payload.total_scenes) meta.push(payload.total_scenes + ' 个场景');
        if (payload.estimated_total_min) meta.push('预计 ' + payload.estimated_total_min + ' 分钟');
        var html = meta.length ? '<div class="xsvp-meta">' + esc(meta.join(' · ')) + '</div>' : '';
        html += '<ol class="xsvp-outline">';
        scenes.forEach(function (s, i) {
            var kps = (s.key_points || []).map(function (k) { return '<span class="xsvp-kp">' + esc(k) + '</span>'; }).join('');
            html += '<li class="xsvp-outline-item">' +
                '<div class="xsvp-outline-head">' +
                    '<span class="xsvp-outline-num">' + (i + 1) + '</span>' +
                    '<span class="xsvp-outline-title">' + esc(s.title || ('场景 ' + (i + 1))) + '</span>' +
                    '<span class="xsvp-badge">' + esc(s.type || 'slide') + '</span>' +
                    (s.duration_min ? '<span class="xsvp-badge xsvp-badge-soft">' + esc(s.duration_min) + ' min</span>' : '') +
                '</div>' +
                (s.description ? '<p class="xsvp-outline-desc">' + esc(s.description) + '</p>' : '') +
                (kps ? '<div class="xsvp-kps">' + kps + '</div>' : '') +
                '</li>';
        });
        html += '</ol>';
        return html;
    }

    // ---- plan ----

    function renderPlan(payload) {
        var plans = (payload && payload.plans) || {};
        var keys = Object.keys(plans);
        if (!keys.length) return '<div class="xsvp-empty">教案没有数据</div>';
        var html = '<div class="xsvp-plans">';
        keys.forEach(function (sceneId) {
            var p = plans[sceneId] || {};
            html += '<details class="xsvp-plan"' + (keys.length <= 3 ? ' open' : '') + '>' +
                '<summary>场景 ' + esc(sceneId) +
                    (p.duration_min ? ' <span class="xsvp-badge xsvp-badge-soft">' + esc(p.duration_min) + ' min</span>' : '') +
                '</summary><div class="xsvp-plan-body">' +
                planSection('教学目标', p.objectives, 'xsvp-obj') +
                planSection('核心要点', p.key_points, '') +
                (p.methods && p.methods.length ? planSection('教学方法', p.methods, '') : '') +
                (p.blackboard ? '<div class="xsvp-plan-row"><h4>板书设计</h4><pre class="xc-code xsvp-blackboard">' + esc(p.blackboard) + '</pre></div>' : '') +
                '</div></details>';
        });
        html += '</div>';
        return html;
    }

    function planSection(title, items, extraCls) {
        if (!items || !items.length) return '';
        return '<div class="xsvp-plan-row ' + (extraCls || '') + '"><h4>' + esc(title) + '</h4>' +
            '<ul>' + items.map(function (x) { return '<li>' + rich(x) + '</li>'; }).join('') + '</ul></div>';
    }

    // ---- graph / ability_graph ----

    function renderGraph(nodes, edges) {
        nodes = nodes || []; edges = edges || [];
        if (!nodes.length) return '<div class="xsvp-empty">图谱没有节点数据</div>';

        // 按 layer 分列 (0=核心 1=依赖 2=延伸)
        var W = 860, H = Math.max(360, nodes.length * 46);
        var layers = [[], [], []];
        nodes.forEach(function (n) {
            var l = Math.min(2, Math.max(0, n.layer || 0));
            layers[l].push(n);
        });
        var colW = W / 3;
        var pos = {};
        layers.forEach(function (col, li) {
            col.forEach(function (n, ri) {
                pos[n.id] = {
                    x: colW * li + colW / 2,
                    y: (H / (col.length + 1)) * (ri + 1),
                };
            });
        });

        var svg = '<svg class="xsvp-graph-svg" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet">';
        edges.forEach(function (e) {
            var a = pos[e.from_id || e.from], b = pos[e.to_id || e.to];
            if (!a || !b) return;
            var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
            svg += '<path d="M' + a.x + ' ' + a.y + ' Q' + mx + ' ' + (my - 24) + ' ' + b.x + ' ' + b.y + '" class="xsvp-graph-edge" marker-end="url(#xsvp-arrow)"/>';
            if (e.label) {
                svg += '<text x="' + mx + '" y="' + (my - 18) + '" class="xsvp-graph-elabel" text-anchor="middle">' + esc(e.label) + '</text>';
            }
        });
        svg += '<defs><marker id="xsvp-arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" class="xsvp-graph-arrow"/></marker></defs>';
        nodes.forEach(function (n) {
            var p = pos[n.id]; if (!p) return;
            svg += '<g class="xsvp-graph-node xsvp-graph-layer' + Math.min(2, n.layer || 0) + '" data-id="' + esc(n.id) + '">' +
                '<rect x="' + (p.x - 62) + '" y="' + (p.y - 19) + '" rx="10" width="124" height="38" />' +
                '<text x="' + p.x + '" y="' + (p.y + 5) + '" text-anchor="middle">' + esc(n.label || n.id) + '</text>' +
                '</g>';
        });
        svg += '</svg>';

        var legend = '<div class="xsvp-graph-legend">' +
            '<span class="xsvp-lg xsvp-lg0"></span>核心' +
            '<span class="xsvp-lg xsvp-lg1"></span>依赖' +
            '<span class="xsvp-lg xsvp-lg2"></span>延伸</div>';

        return '<div class="xsvp-graph-wrap">' + svg + legend + '</div>';
    }

    function renderAbilityGraph(payload) {
        var comps = (payload && payload.competencies) || [];
        var html = '';
        if (comps.length) {
            html += '<div class="xsvp-meta">' + comps.length + ' 项能力</div><div class="xsvp-abilities">';
            comps.forEach(function (c) {
                var pct = Math.round((c.target_level || 0) * 100);
                html += '<div class="xsvp-ability">' +
                    '<div class="xsvp-ability-head">' +
                        '<span class="xsvp-ability-name">' + esc(c.name) + '</span>' +
                        '<span class="xsvp-badge">' + esc(c.category || '') + '</span>' +
                        '<span class="xsvp-badge xsvp-badge-soft">Bloom ' + esc(c.bloom_level || 1) + '</span>' +
                    '</div>' +
                    (c.description ? '<p class="xsvp-outline-desc">' + esc(c.description) + '</p>' : '') +
                    '<div class="xsvp-ability-bar"><span style="width:' + pct + '%"></span><i>' + pct + '%</i></div>' +
                    '</div>';
            });
            html += '</div>';
        }
        // 复用知识图谱渲染 graph_view
        var gv = payload && payload.graph_view;
        if (gv && gv.nodes && gv.nodes.length) {
            html += '<h3 class="xsvp-sec-title">能力依赖图</h3>' + renderGraph(gv.nodes, gv.edges);
        }
        if (!html) html = '<div class="xsvp-empty">能力图谱没有数据</div>';
        return html;
    }

    // ---- radar ----

    function renderRadar(payload) {
        var dims = RADAR_DIMS.map(function (d) {
            return { key: d[0], label: d[1], value: Number(payload[d[0]]) || 0 };
        });
        if (!dims.some(function (d) { return d.value > 0; })) {
            return '<div class="xsvp-empty">雷达数据全为 0</div>';
        }

        var cx = 220, cy = 210, R = 150, N = dims.length;
        function pt(i, r) {
            var ang = -Math.PI / 2 + (2 * Math.PI * i) / N;
            return [cx + Math.cos(ang) * r, cy + Math.sin(ang) * r];
        }
        var svg = '<svg class="xsvp-radar-svg" viewBox="0 0 440 420">';
        // 网格环
        [0.25, 0.5, 0.75, 1].forEach(function (f) {
            var pts = dims.map(function (_, i) { return pt(i, R * f).join(','); }).join(' ');
            svg += '<polygon points="' + pts + '" class="xsvp-radar-grid"/>';
        });
        // 轴 + 标签
        dims.forEach(function (d, i) {
            var p = pt(i, R);
            svg += '<line x1="' + cx + '" y1="' + cy + '" x2="' + p[0] + '" y2="' + p[1] + '" class="xsvp-radar-axis"/>';
            var lp = pt(i, R + 30);
            svg += '<text x="' + lp[0] + '" y="' + lp[1] + '" class="xsvp-radar-label" text-anchor="middle">' +
                esc(d.label) + ' ' + Math.round(d.value) + '</text>';
        });
        // 数据多边形
        var dataPts = dims.map(function (d, i) { return pt(i, (Math.min(100, d.value) / 100) * R).join(','); }).join(' ');
        svg += '<polygon points="' + dataPts + '" class="xsvp-radar-poly"/>';
        dims.forEach(function (d, i) {
            var p = pt(i, (Math.min(100, d.value) / 100) * R);
            svg += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="4" class="xsvp-radar-dot"/>';
        });
        svg += '</svg>';

        var post = payload.post_course_estimate || {};
        var postHtml = '';
        var postKeys = Object.keys(post);
        if (postKeys.length) {
            postHtml = '<h3 class="xsvp-sec-title">课后预期提升</h3><div class="xsvp-abilities">';
            RADAR_DIMS.forEach(function (d) {
                if (post[d[0]] === undefined) return;
                var pct = Math.round(Number(post[d[0]]) || 0);
                postHtml += '<div class="xsvp-ability"><div class="xsvp-ability-head">' +
                    '<span class="xsvp-ability-name">' + esc(d[1]) + '</span></div>' +
                    '<div class="xsvp-ability-bar"><span style="width:' + Math.min(100, pct) + '%"></span><i>' + pct + '</i></div></div>';
            });
            postHtml += '</div>';
        }
        return '<div class="xsvp-radar-wrap">' + svg + '</div>' + postHtml;
    }

    // ---- project ----

    function renderProject(payload) {
        var meta = [];
        if (payload.estimated_hours) meta.push('预计 ' + payload.estimated_hours + ' 小时');
        if (payload.difficulty) meta.push('难度: ' + esc(payload.difficulty));
        var html = '';
        if (meta.length) html += '<div class="xsvp-meta">' + meta.join(' · ') + '</div>';
        if (payload.title) html += '<h2 class="xsvp-big-title">🚀 ' + esc(payload.title) + '</h2>';
        if (payload.scenario) html += blockLabel('真实场景', esc(payload.scenario));
        if (payload.background) html += blockLabel('项目背景', esc(payload.background));
        html += listBlock('需求清单', payload.requirements);
        html += listBlock('验收标准', payload.acceptance, true);
        var ms = payload.milestones || [];
        if (ms.length) {
            html += '<h3 class="xsvp-sec-title">里程碑</h3><ol class="xsvp-outline">';
            ms.forEach(function (m, i) {
                html += '<li class="xsvp-outline-item"><div class="xsvp-outline-head">' +
                    '<span class="xsvp-outline-num">' + (i + 1) + '</span>' +
                    '<span class="xsvp-outline-title">' + esc(m.title || '') + '</span></div>' +
                    (m.description ? '<p class="xsvp-outline-desc">' + esc(m.description) + '</p>' : '') +
                    (m.deliverable ? '<div class="xsvp-kp-line">交付物: ' + esc(m.deliverable) + '</div>' : '') +
                    '</li>';
            });
            html += '</ol>';
        }
        if (!html) html = '<div class="xsvp-empty">项目没有数据</div>';
        return html;
    }

    // ---- case ----

    function renderCase(payload) {
        var html = '';
        if (payload.title) html += '<h2 class="xsvp-big-title">📖 ' + esc(payload.title) + '</h2>';
        if (payload.story) html += '<div class="xsvp-story">' + esc(payload.story).replace(/\n/g, '<br>') + '</div>';
        html += listBlock('关键决策点', payload.decision_points);
        html += listBlock('反思题', payload.reflection);
        if (payload.takeaway) html += blockLabel('案例启示', esc(payload.takeaway));
        if (!html) html = '<div class="xsvp-empty">案例没有数据</div>';
        return html;
    }

    function blockLabel(label, text) {
        return '<div class="xsvp-block-label"><h4>' + esc(label) + '</h4><p>' + text + '</p></div>';
    }

    function listBlock(label, items, ordered) {
        if (!items || !items.length) return '';
        var tag = ordered ? 'ol' : 'ul';
        return '<div class="xsvp-block-label"><h4>' + esc(label) + '</h4>' +
            '<' + tag + ' class="xsvp-list">' +
            items.map(function (x) { return '<li>' + rich(x) + '</li>'; }).join('') +
            '</' + tag + '></div>';
    }

    // ---- exercises ----

    function renderExercises(payload) {
        var qs = (payload && payload.questions) || [];
        if (!qs.length) return '<div class="xsvp-empty">习题没有数据</div>';
        var typeLabel = { single: '单选', multi: '多选', fill: '填空', code: '编程' };
        var html = '<div class="xsvp-meta">共 ' + qs.length + ' 题</div><div class="xsvp-quiz">';
        qs.forEach(function (q, i) {
            var opts = '';
            (q.options || []).forEach(function (o, oi) {
                opts += '<li class="xsvp-opt" data-q="' + i + '">' +
                    '<span class="xsvp-opt-key">' + String.fromCharCode(65 + oi) + '</span>' +
                    '<span>' + rich(o) + '</span></li>';
            });
            html += '<div class="xsvp-question" data-qi="' + i + '">' +
                '<div class="xsvp-q-head">' +
                    '<span class="xsvp-outline-num">' + (i + 1) + '</span>' +
                    '<span class="xsvp-q-stem">' + rich(q.stem) + '</span>' +
                    '<span class="xsvp-badge">' + esc(typeLabel[q.type] || q.type) + '</span>' +
                    (q.difficulty ? '<span class="xsvp-badge xsvp-badge-soft">' + esc(q.difficulty) + '</span>' : '') +
                '</div>' +
                (opts ? '<ul class="xsvp-opts">' + opts + '</ul>' : '') +
                '<button class="xsvp-btn xsvp-btn-ghost xsvp-reveal" data-q="' + i + '">显示答案</button>' +
                '<div class="xsvp-answer" id="xsvp-ans-' + i + '">' +
                    '<strong>答案:</strong> ' + esc(formatAnswer(q.answer, q.type)) +
                    (q.rubric ? '<div class="xsvp-rubric"><strong>评分:</strong> ' + esc(q.rubric) + '</div>' : '') +
                '</div>' +
                '</div>';
        });
        html += '</div>';
        return html;
    }

    function wireExercises() {
        Array.prototype.forEach.call(document.querySelectorAll('.xsvp-reveal'), function (btn) {
            btn.addEventListener('click', function () {
                var ans = el('xsvp-ans-' + btn.getAttribute('data-q'));
                if (ans) ans.classList.toggle('xsvp-answer-show');
                btn.textContent = ans && ans.classList.contains('xsvp-answer-show') ? '隐藏答案' : '显示答案';
            });
        });
    }

    function formatAnswer(ans, type) {
        if (ans === null || ans === undefined) return '（略）';
        if (type === 'single' && typeof ans === 'number') return String.fromCharCode(65 + ans) + '. ' + ans;
        if (Array.isArray(ans)) return ans.map(function (a) { return typeof a === 'number' ? String.fromCharCode(65 + a) : a; }).join('、');
        return String(ans);
    }

    // ---- survey ----

    function renderSurvey(payload) {
        var sections = (payload && payload.sections) || [];
        if (!sections.length) return '<div class="xsvp-empty">问卷没有数据</div>';
        var typeLabel = { single: '单选', multi: '多选', scale: '量表', text: '开放题' };
        var html = payload.estimated_minutes
            ? '<div class="xsvp-meta">预计 ' + payload.estimated_minutes + ' 分钟</div>' : '';
        sections.forEach(function (sec, si) {
            html += '<div class="xsvp-survey-sec">' +
                '<h3 class="xsvp-sec-title">' + esc(sec.title || ('第 ' + (si + 1) + ' 部分')) + '</h3>' +
                (sec.description ? '<p class="xsvp-outline-desc">' + esc(sec.description) + '</p>' : '') +
                '<ol class="xsvp-survey-qs">';
            (sec.questions || []).forEach(function (q) {
                var opts = (q.options || []).map(function (o) {
                    return '<span class="xsvp-kp">' + rich(o) + '</span>';
                }).join('');
                html += '<li><div class="xsvp-q-head">' +
                    '<span class="xsvp-q-stem">' + rich(q.stem) + '</span>' +
                    '<span class="xsvp-badge">' + esc(typeLabel[q.type] || q.type) + '</span>' +
                    (q.required === false ? '<span class="xsvp-badge xsvp-badge-soft">选填</span>' : '') +
                    '</div>' + (opts ? '<div class="xsvp-kps">' + opts + '</div>' : '') + '</li>';
            });
            html += '</ol></div>';
        });
        return html;
    }

    // ---- 兜底: 未知结构走键值漫游 ----

    function renderGeneric(payload) {
        return '<pre class="xsvp-json">' + esc(JSON.stringify(payload, null, 2)) + '</pre>';
    }
})();
