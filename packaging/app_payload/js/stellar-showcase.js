/* ==========================================================================
 * 星云陈列室 (Stellar Showcase) — 渲染逻辑
 *
 * 数据流:
 *   1. 静态目录: window.ACHIEVEMENTS (来自 /js/achievements-data.js)
 *   2. 解锁状态: GET /api/achievements/load/{userId}
 *   3. 累计统计: GET /api/stats/load/{userId}
 *
 * 不做 localStorage 兜底 —— 后端是唯一真源。空数据时显示真实空状态。
 * ========================================================================== */
(function () {
    'use strict';

    // ===== 状态 =============================================================
    const state = {
        catalog: [],           // 目录(来自 window.ACHIEVEMENTS)
        unlocked: {},          // 已解锁: { id: { unlockedAt, ... } }
        stats: {},             // 累计统计: { study_count, ... }
        loading: true,
        error: null,
        userId: null,
        filters: {
            category: 'all',   // all / skill / course / master
            tier:     'all',   // all / legendary / epic / rare / common
            status:   'all',   // all / unlocked / locked
        },
    };

    // ===== 工具 =============================================================
    const TIER_LABEL = {
        legendary: '传奇',
        epic:      '史诗',
        rare:      '稀有',
        common:    '普通',
    };

    const CATEGORY_LABEL = {
        skill:  '技能徽章',
        course: '课程证书',
        master: '大师成就',
    };

    function getCurrentUserId() {
        try {
            const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
            return user.id || null;
        } catch (e) {
            return null;
        }
    }

    function escapeHtml(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatDate(timestamp) {
        if (!timestamp) return '';
        const d = new Date(timestamp);
        const pad = (n) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    }

    function formatDateTime(timestamp) {
        if (!timestamp) return '-';
        const d = new Date(timestamp);
        const pad = (n) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }

    function getStat(conditionType) {
        if (!conditionType) return 0;
        const keys = [conditionType, conditionType + '_count', conditionType + 's'];
        for (const k of keys) {
            if (typeof state.stats[k] === 'number') return state.stats[k];
        }
        return 0;
    }

    // 判断一条解锁记录是否"真正已解锁"。
    // 后端可能返回 { id: {} } 或 { id: { unlockedAt: null } } 这种占位记录,
    // !!entry 始终为 true,会把所有条目误判为已解锁。
    // 必须检查 entry.unlockedAt 是否为有效时间戳。
    function isEntryUnlocked(entry) {
        if (!entry || typeof entry !== 'object') return false;
        const ts = entry.unlockedAt;
        if (ts == null) return false;
        if (typeof ts === 'number') return ts > 0;
        if (typeof ts === 'string') {
            const n = Number(ts);
            return !Number.isNaN(n) && n > 0;
        }
        return false;
    }

    function getProgress(achievement) {
        const cond = achievement.condition || {};
        const current = getStat(cond.type);
        const target = cond.value || 1;
        const percent = Math.min(100, Math.round((current / target) * 100));
        return { current, target, percent };
    }

    // ===== API 调用 =========================================================
    async function fetchAchievements(userId) {
        const res = await fetch('/api/achievements/load/' + encodeURIComponent(userId), {
            credentials: 'include',
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        const raw = (data && data.success && data.achievementsData) || {};
        // 清理占位记录(无有效 unlockedAt),只保留真正解锁的条目
        const clean = {};
        Object.keys(raw).forEach((k) => {
            if (isEntryUnlocked(raw[k])) clean[k] = raw[k];
        });
        return clean;
    }

    async function fetchStats(userId) {
        try {
            const res = await fetch('/api/stats/load/' + encodeURIComponent(userId), {
                credentials: 'include',
            });
            if (!res.ok) return {};
            const data = await res.json();
            return (data && data.success && data.statsData) || {};
        } catch (e) {
            return {};
        }
    }

    // ===== 渲染: 顶栏计数 + Hero 进度 + 统计卡 =============================
    function renderHeader() {
        const total = state.catalog.length;
        const unlockedCount = state.catalog.filter((a) => isEntryUnlocked(state.unlocked[a.id])).length;
        const pct = total === 0 ? 0 : Math.round((unlockedCount / total) * 100);

        setText('ss-counter-value', unlockedCount);
        setText('ss-counter-total', total);
        setText('ss-hero-progress-pct', pct + '%');

        // 进度环 stroke-dashoffset (周长 ~ 2πr, r=28 → 176)
        const ring = document.getElementById('ss-hero-ring-fill');
        if (ring) {
            const C = 2 * Math.PI * 28;
            ring.setAttribute('stroke-dasharray', C.toFixed(2));
            ring.setAttribute('stroke-dashoffset', (C * (1 - pct / 100)).toFixed(2));
        }

        // 各 tier 计数 + tab 计数
        const tierCount = { legendary: 0, epic: 0, rare: 0, common: 0 };
        const catCount  = { all: 0, skill: 0, course: 0, master: 0 };
        state.catalog.forEach((a) => {
            if (isEntryUnlocked(state.unlocked[a.id])) tierCount[a.tier] = (tierCount[a.tier] || 0) + 1;
            catCount[a.category] = (catCount[a.category] || 0) + 1;
        });
        catCount.all = state.catalog.length;

        // 每种 tier 的"该 tier 共有多少"
        const tierTotal = { legendary: 0, epic: 0, rare: 0, common: 0 };
        state.catalog.forEach((a) => { tierTotal[a.tier] = (tierTotal[a.tier] || 0) + 1; });

        setText('ss-stat-legendary', tierCount.legendary);
        setText('ss-stat-epic',      tierCount.epic);
        setText('ss-stat-rare',      tierCount.rare);
        setText('ss-stat-common',    tierCount.common);

        const barEl = (id) => document.getElementById(id);
        if (barEl('ss-stat-bar-legendary')) {
            const set = (id, got, total) => {
                const el = barEl(id);
                if (el) el.style.width = (total > 0 ? (got / total) * 100 : 0) + '%';
            };
            set('ss-stat-bar-legendary', tierCount.legendary, tierTotal.legendary);
            set('ss-stat-bar-epic',      tierCount.epic,      tierTotal.epic);
            set('ss-stat-bar-rare',      tierCount.rare,      tierTotal.rare);
            set('ss-stat-bar-common',    tierCount.common,    tierTotal.common);
        }

        setText('ss-tab-count-all',    catCount.all);
        setText('ss-tab-count-skill',  catCount.skill);
        setText('ss-tab-count-course', catCount.course);
        setText('ss-tab-count-master', catCount.master);
    }

    // ===== 渲染: 徽章网格 ===================================================
    function renderBody() {
        const body = document.getElementById('ss-body');
        if (!body) return;

        const filtered = applyFilters(state.catalog);
        if (filtered.length === 0) {
            body.innerHTML = renderEmptyState();
            return;
        }

        // 按 tier 稀有度排序 (legendary > epic > rare > common),再按未解锁
        const tierOrder = { legendary: 0, epic: 1, rare: 2, common: 3 };
        const sorted = filtered.slice().sort((a, b) => {
            const ua = isEntryUnlocked(state.unlocked[a.id]) ? 0 : 1;
            const ub = isEntryUnlocked(state.unlocked[b.id]) ? 0 : 1;
            if (ua !== ub) return ua - ub;
            return (tierOrder[a.tier] ?? 9) - (tierOrder[b.tier] ?? 9);
        });

        const grid = document.createElement('div');
        grid.className = 'ss-grid';
        grid.innerHTML = sorted.map(renderCard).join('');
        body.innerHTML = '';
        body.appendChild(grid);
        bindCardEvents();
    }

    function renderCard(achievement) {
        const unlockData = state.unlocked[achievement.id];
        const isUnlocked = isEntryUnlocked(unlockData);
        const progress = getProgress(achievement);
        const iconSvg = (window.ACHIEVEMENT_ICONS && window.ACHIEVEMENT_ICONS[achievement.icon])
            || (window.ACHIEVEMENT_ICONS && window.ACHIEVEMENT_ICONS.compass)
            || '';

        const cls = 'ss-card' + (isUnlocked ? '' : ' ss-card-locked');

        const progressBlock = !isUnlocked
            ? '<div class="ss-card-progress">' +
                '<div class="ss-card-progress-label"><span>进度</span><strong>' + progress.current + ' / ' + progress.target + '</strong></div>' +
                '<div class="ss-progress-track"><div class="ss-progress-fill" style="width:' + progress.percent + '%"></div></div>' +
              '</div>'
            : '';

        const timeBlock = isUnlocked && unlockData && unlockData.unlockedAt
            ? '<div class="ss-card-time">' + formatDate(unlockData.unlockedAt) + ' 解锁</div>'
            : '';

        return '' +
            '<article class="' + cls + '" data-id="' + escapeHtml(achievement.id) + '" data-tier="' + escapeHtml(achievement.tier) + '" data-category="' + escapeHtml(achievement.category) + '">' +
                '<div class="ss-card-medal">' +
                    '<div class="ss-card-medal-shine"></div>' +
                    '<div class="ss-card-medal-disc"><svg viewBox="0 0 64 64" fill="none">' + iconSvg + '</svg></div>' +
                '</div>' +
                '<h3 class="ss-card-name">' + escapeHtml(achievement.name) + '</h3>' +
                '<p class="ss-card-desc">' + escapeHtml(achievement.desc) + '</p>' +
                '<span class="ss-card-tier">' + escapeHtml(TIER_LABEL[achievement.tier] || achievement.tier) + '</span>' +
                progressBlock +
                timeBlock +
            '</article>';
    }

    function renderEmptyState() {
        return '' +
            '<div class="ss-empty">' +
                '<div class="ss-empty-icon">✦</div>' +
                '<h3 class="ss-empty-title">该筛选下没有勋章</h3>' +
                '<p class="ss-empty-desc">试试切换分类、稀有度或状态,看看其他徽章吧</p>' +
            '</div>';
    }

    function applyFilters(list) {
        const f = state.filters;
        return list.filter((a) => {
            if (f.category !== 'all' && a.category !== f.category) return false;
            if (f.tier !== 'all' && a.tier !== f.tier) return false;
            const isUnlocked = isEntryUnlocked(state.unlocked[a.id]);
            if (f.status === 'unlocked' && !isUnlocked) return false;
            if (f.status === 'locked' && isUnlocked) return false;
            return true;
        });
    }

    // ===== 渲染: 加载 / 错误 ===============================================
    function renderLoading() {
        const body = document.getElementById('ss-body');
        if (body) {
            body.innerHTML = '<div class="ss-loading"><div class="ss-spinner"></div><span>正在加载勋章...</span></div>';
        }
    }

    function renderError(err) {
        const body = document.getElementById('ss-body');
        if (body) {
            body.innerHTML = '' +
                '<div class="ss-error">' +
                    '<div class="ss-error-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>' +
                    '<h3 class="ss-error-title">加载勋章失败</h3>' +
                    '<p class="ss-error-desc">' + escapeHtml((err && err.message) || '网络异常,请稍后重试') + '</p>' +
                    '<button class="ss-retry-btn" type="button" data-retry>重新加载</button>' +
                '</div>';
            const retry = body.querySelector('[data-retry]');
            if (retry) retry.addEventListener('click', loadAll);
        }
    }

    function renderLoginRequired() {
        const body = document.getElementById('ss-body');
        if (body) {
            body.innerHTML = '' +
                '<div class="ss-empty">' +
                    '<div class="ss-empty-icon">✦</div>' +
                    '<h3 class="ss-empty-title">请先登录</h3>' +
                    '<p class="ss-empty-desc">登录后即可查看你在星识之旅中收集到的勋章</p>' +
                    '<a href="/login.html" class="ss-retry-btn" style="text-decoration:none;display:inline-block;">前往登录</a>' +
                '</div>';
        }
    }

    // ===== 详情弹窗 ========================================================
    function openModal(achievementId) {
        const a = state.catalog.find((x) => x.id === achievementId);
        if (!a) return;

        const modal = document.getElementById('ss-modal');
        if (!modal) return;

        const unlockData = state.unlocked[achievement.id];
        const isUnlocked = isEntryUnlocked(unlockData);
        const progress = getProgress(a);
        const iconSvg = (window.ACHIEVEMENT_ICONS && window.ACHIEVEMENT_ICONS[a.icon])
            || (window.ACHIEVEMENT_ICONS && window.ACHIEVEMENT_ICONS.compass)
            || '';

        modal.setAttribute('data-tier', a.tier);
        modal.setAttribute('data-unlocked', isUnlocked ? '1' : '0');
        modal.hidden = false;

        setText('ss-modal-title',     a.name);
        setText('ss-modal-desc',      a.desc);
        setText('ss-modal-tier',      TIER_LABEL[a.tier] || a.tier);
        setText('ss-modal-category',  CATEGORY_LABEL[a.category] || a.category);

        const statusEl = document.getElementById('ss-modal-status');
        if (statusEl) {
            statusEl.textContent = isUnlocked ? '已解锁' : '未解锁';
            statusEl.className = 'ss-modal-status ' + (isUnlocked ? 'is-unlocked' : 'is-locked');
        }

        const iconEl = document.getElementById('ss-modal-icon');
        if (iconEl) iconEl.innerHTML = '<svg viewBox="0 0 64 64" fill="none">' + iconSvg + '</svg>';

        // 进度: 已解锁隐藏
        const progressBlock = document.getElementById('ss-modal-progress');
        if (progressBlock) {
            if (isUnlocked) {
                progressBlock.hidden = true;
            } else {
                progressBlock.hidden = false;
                setText('ss-modal-progress-text', progress.current + ' / ' + progress.target);
                const fill = document.getElementById('ss-modal-progress-fill');
                if (fill) fill.style.width = progress.percent + '%';
            }
        }

        setText('ss-stat-unlock-time', isUnlocked && unlockData && unlockData.unlockedAt
            ? formatDateTime(unlockData.unlockedAt)
            : '—');
        setText('ss-stat-rarity', TIER_LABEL[a.tier] || a.tier);
        setText('ss-stat-code', '#' + String(state.catalog.indexOf(a) + 1).padStart(3, '0'));

        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        const modal = document.getElementById('ss-modal');
        if (modal) modal.hidden = true;
        document.body.style.overflow = '';
    }

    // ===== 事件绑定 ========================================================
    function bindCardEvents() {
        const body = document.getElementById('ss-body');
        if (!body) return;
        body.querySelectorAll('.ss-card').forEach((el) => {
            el.addEventListener('click', () => {
                const id = el.getAttribute('data-id');
                if (id) openModal(id);
            });
        });
    }

    function bindGlobalEvents() {
        // 分类 tab
        document.querySelectorAll('.ss-tab').forEach((tab) => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.ss-tab').forEach((t) => t.classList.remove('active'));
                tab.classList.add('active');
                state.filters.category = tab.getAttribute('data-category') || 'all';
                renderBody();
            });
        });

        // 稀有度 + 状态 chip
        document.querySelectorAll('.ss-chip-group').forEach((group) => {
            const kind = group.querySelector('[data-tier]') ? 'tier' : 'status';
            group.querySelectorAll('.ss-chip').forEach((chip) => {
                chip.addEventListener('click', () => {
                    group.querySelectorAll('.ss-chip').forEach((c) => c.classList.remove('active'));
                    chip.classList.add('active');
                    state.filters[kind] = chip.getAttribute('data-' + kind) || 'all';
                    renderBody();
                });
            });
        });

        // 弹窗关闭
        const modal = document.getElementById('ss-modal');
        if (modal) {
            modal.querySelectorAll('[data-close]').forEach((el) => {
                el.addEventListener('click', closeModal);
            });
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && !modal.hidden) closeModal();
            });
        }
    }

    // ===== 辅助 ============================================================
    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    // ===== 加载数据 ========================================================
    async function loadAll() {
        state.userId = getCurrentUserId();
        if (!state.userId) {
            state.loading = false;
            renderLoginRequired();
            return;
        }

        state.catalog = (window.ACHIEVEMENTS && Array.isArray(window.ACHIEVEMENTS)) ? window.ACHIEVEMENTS : [];
        if (state.catalog.length === 0) {
            state.loading = false;
            state.error = new Error('未加载到成就目录');
            renderError(state.error);
            return;
        }

        state.loading = true;
        state.error = null;
        renderLoading();

        try {
            const [unlocked, stats] = await Promise.all([
                fetchAchievements(state.userId),
                fetchStats(state.userId),
            ]);
            state.unlocked = unlocked || {};
            state.stats = stats || {};
            state.loading = false;
            renderHeader();
            renderBody();
        } catch (e) {
            state.loading = false;
            state.error = e;
            renderError(e);
        }
    }

    // ===== 启动 ============================================================
    document.addEventListener('DOMContentLoaded', function () {
        bindGlobalEvents();
        loadAll();
    });
})();
