/**
 * 新手引导系统 — Spotlight Tour
 * Phase 4: First-time user onboarding with 3-step sidebar tour
 * 状态: localStorage('starlearn_onboarding_completed')
 */
(function() {
  'use strict';

  const STORAGE_KEY = 'starlearn_onboarding_completed';

  // 跳过参数: ?skip-onboarding=1
  if (window.location.search.includes('skip-onboarding=1')) return;
  if (localStorage.getItem(STORAGE_KEY)) return;

  let currentStep = 0;
  let overlay = null;
  let spotlight = null;
  let tooltip = null;

  const STEPS = [
    {
      target: '[data-section="ai-qa"]',
      title: 'AI 问答',
      description: '在这里，你可以和AI对话、生成课程、写代码练习——一个入口搞定所有学习需求。',
      position: 'right',
    },
    {
      target: '[data-section="courses"], [data-section="my-courses"]',
      title: '我的课程',
      description: '所有AI生成的课程都在这里，随时查看学习进度和日程安排。',
      position: 'right',
    },
    {
      target: '.app-kanban',
      title: '看板娘 · 小星',
      description: '随时点击右下角呼叫我，语音或打字都可以——导航、答疑、伴学，我都在~',
      position: 'top',
    },
  ];

  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', start);
    } else {
      start();
    }
  }

  function start() {
    // 等待看板娘先加载
    setTimeout(() => {
      showMascotGreeting();
      setTimeout(startTour, 2000);
    }, 1500);
  }

  function showMascotGreeting() {
    if (window.MascotCore && window.MascotCore.showBubble) {
      window.MascotCore.showBubble('欢迎来到星识！我是小星~', 4000);
    }
  }

  function startTour() {
    createOverlay();
    showStep(0);
  }

  function createOverlay() {
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.className = 'onboard-overlay';

    spotlight = document.createElement('div');
    spotlight.className = 'onboard-spotlight';

    tooltip = document.createElement('div');
    tooltip.className = 'onboard-tooltip';
    tooltip.innerHTML = `
      <div class="onboard-tooltip-title"></div>
      <div class="onboard-tooltip-desc"></div>
      <div class="onboard-tooltip-actions">
        <button class="onboard-btn onboard-btn--skip" id="onboard-skip">跳过</button>
        <span class="onboard-dots" id="onboard-dots"></span>
        <button class="onboard-btn onboard-btn--next" id="onboard-next">下一步</button>
      </div>
    `;

    overlay.appendChild(spotlight);
    overlay.appendChild(tooltip);
    document.body.appendChild(overlay);

    document.getElementById('onboard-skip').addEventListener('click', finish);
    document.getElementById('onboard-next').addEventListener('click', () => {
      if (currentStep < STEPS.length - 1) {
        showStep(currentStep + 1);
      } else {
        finish();
      }
    });
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) finish();
    });
  }

  function showStep(index) {
    currentStep = index;
    const step = STEPS[index];

    // 支持多个选择器（取第一个匹配的）
    const selectors = step.target.split(',').map(s => s.trim());
    let target = null;
    for (const sel of selectors) {
      target = document.querySelector(sel);
      if (target) break;
    }

    if (!target) {
      if (index < STEPS.length - 1) showStep(index + 1);
      else finish();
      return;
    }

    // Show overlay
    overlay.classList.add('visible');

    // Position spotlight
    const rect = target.getBoundingClientRect();
    const pad = 8;
    Object.assign(spotlight.style, {
      left: (rect.left - pad) + 'px',
      top: (rect.top - pad) + 'px',
      width: (rect.width + pad * 2) + 'px',
      height: (rect.height + pad * 2) + 'px',
    });
    spotlight.classList.add('visible');

    // Position tooltip
    const gap = 16;
    let ttipLeft, ttipTop;

    if (step.position === 'right') {
      ttipLeft = rect.right + gap;
      ttipTop = rect.top + rect.height / 2 - 80;
    } else if (step.position === 'top') {
      ttipLeft = rect.left + rect.width / 2 - 140;
      ttipTop = rect.top - 200;
    } else {
      ttipLeft = rect.left;
      ttipTop = rect.bottom + gap;
    }

    // Clamp to viewport
    ttipLeft = Math.max(16, Math.min(ttipLeft, window.innerWidth - 300));
    ttipTop = Math.max(16, Math.min(ttipTop, window.innerHeight - 220));

    Object.assign(tooltip.style, {
      left: ttipLeft + 'px',
      top: ttipTop + 'px',
    });
    tooltip.classList.add('visible');

    // Update content
    tooltip.querySelector('.onboard-tooltip-title').textContent = step.title;
    tooltip.querySelector('.onboard-tooltip-desc').textContent = step.description;

    // Update dots
    const dots = document.getElementById('onboard-dots');
    dots.innerHTML = STEPS.map((_, i) =>
      `<span class="onboard-dot ${i === index ? 'active' : ''}"></span>`
    ).join('');

    // Update button text
    const nextBtn = document.getElementById('onboard-next');
    nextBtn.textContent = index === STEPS.length - 1 ? '开始探索' : '下一步';
  }

  function finish() {
    if (overlay) overlay.classList.remove('visible');
    if (spotlight) spotlight.classList.remove('visible');
    if (tooltip) tooltip.classList.remove('visible');
    localStorage.setItem(STORAGE_KEY, 'true');
    setTimeout(() => {
      if (overlay) overlay.remove();
      overlay = spotlight = tooltip = null;
    }, 300);
  }

  // ===== 暴露 API =====
  window.Onboarding = {
    restart: () => {
      localStorage.removeItem(STORAGE_KEY);
      init();
    },
  };

  // ===== 自动启动 =====
  init();
})();

/* ============================================================
   Phase 1 — AI 问答重塑:首访引导卡片 (4 问)
   与上面的 spotlight tour 完全隔离,使用 xs- 前缀的 DOM/class
   ============================================================ */
(function () {
  'use strict';

  const QA_VERSION = 1;
  const QA_LS_KEY = 'xs_onboard_v';

  // 4 问定义(id, title, hint, options, multiple)
  const QUESTIONS = [
    {
      id: 'grade',
      title: '你目前的学段?',
      hint: '不同学段我会调整讲解深度和举例风格。',
      multiple: false,
      options: ['小学', '初中', '高中', '大专/本科', '研究生/在职', '其他'],
    },
    {
      id: 'direction',
      title: '想学哪些方向?(可多选)',
      hint: '我好匹配对应的项目案例。',
      multiple: true,
      options: ['大数据', 'AI/算法', '前端', '后端', '数据库', 'DevOps', '其他'],
    },
    {
      id: 'base',
      title: '当前的编程基础?',
      hint: '我会按你的基础选起点。',
      multiple: false,
      options: ['零基础', '写过简单脚本', '做过项目', '可以独立开发'],
    },
    {
      id: 'pref',
      title: '偏好哪种讲解?(可多选)',
      hint: '我可以按你的偏好调整教学风格。',
      multiple: true,
      options: ['图文并茂', '例子驱动', '先讲原理再代码', '多给练习'],
    },
  ];

  // ---- 状态 ----
  let stepIndex = 0;
  let answers = {};          // {grade, direction:[], base, pref:[]}
  let selected = new Set();  // 当前题已选 options
  let busy = false;

  // ---- DOM 引用 ----
  const $ = (id) => document.getElementById(id);
  const maskEl = () => $('xs-onboard-mask');
  const titleEl = () => $('xs-onboard-title');
  const hintEl = () => $('xs-onboard-hint');
  const optsEl = () => $('xs-onboard-options');
  const customEl = () => $('xs-onboard-custom');
  const nextBtn = () => $('xs-onboard-next');
  const skipBtn = () => $('xs-onboard-skip');
  const closeBtn = () => $('xs-onboard-close');
  const stepEl = () => $('xs-onboard-step');
  const fillEl = () => $('xs-onboard-fill');

  function showMask() {
    const m = maskEl();
    if (!m) return;
    m.classList.add('visible');
    m.setAttribute('aria-hidden', 'false');
  }
  function hideMask() {
    const m = maskEl();
    if (!m) return;
    m.classList.remove('visible');
    m.setAttribute('aria-hidden', 'true');
  }

  function getCurrentUserId() {
    try {
      const u = JSON.parse(localStorage.getItem('starlearn_user') || 'null');
      return u && u.id ? String(u.id) : null;
    } catch (e) {
      return null;
    }
  }

  function normalizeAnswer(qid, vals) {
    if (!vals || vals.length === 0) return null;
    const q = QUESTIONS.find((x) => x.id === qid);
    return q && q.multiple ? vals : vals[0];
  }

  // ---- 渲染当前题 ----
  function renderStep() {
    const q = QUESTIONS[stepIndex];
    if (!q) return;
    // 问卷 DOM 仅存在于 hub 页面（index.html），其他页面静默跳过
    if (!titleEl() || !hintEl() || !stepEl() || !fillEl() || !optsEl()) return;
    titleEl().textContent = q.title;
    hintEl().textContent = q.hint;
    stepEl().textContent = `${stepIndex + 1} / ${QUESTIONS.length}`;
    fillEl().style.width = `${((stepIndex + 1) / QUESTIONS.length) * 100}%`;

    selected = new Set();
    const prev = answers[q.id];
    if (Array.isArray(prev)) selected = new Set(prev);
    else if (prev) selected = new Set([prev]);

    optsEl().innerHTML = '';
    q.options.forEach((opt) => {
      const chip = document.createElement('div');
      chip.className = 'xs-onboard-option';
      chip.textContent = opt;
      if (selected.has(opt)) chip.classList.add('selected');
      chip.addEventListener('click', () => {
        if (q.multiple) {
          if (selected.has(opt)) selected.delete(opt);
          else selected.add(opt);
          chip.classList.toggle('selected');
        } else {
          selected.clear();
          selected.add(opt);
          optsEl().querySelectorAll('.xs-onboard-option').forEach((c) => c.classList.remove('selected'));
          chip.classList.add('selected');
        }
        updateNextEnabled();
      });
      optsEl().appendChild(chip);
    });

    // 自定义输入(只在 direction / pref 提示)
    if (q.id === 'direction' || q.id === 'pref') {
      customEl().classList.remove('hidden');
      customEl().placeholder = q.multiple ? '其他(可逗号分隔)' : '其他';
    } else {
      customEl().classList.add('hidden');
    }
    customEl().value = '';
    updateNextEnabled();
  }

  function updateNextEnabled() {
    const has = selected.size > 0 || (customEl().value || '').trim().length > 0;
    nextBtn().disabled = !has;
  }

  // ---- 跳到下一题 ----
  function goNext() {
    if (busy) return;
    const q = QUESTIONS[stepIndex];
    const custom = (customEl().value || '').trim();
    if (custom && q.multiple) {
      custom.split(/[,，;；\s]+/).filter(Boolean).forEach((s) => selected.add(s));
    } else if (custom) {
      selected.add(custom);
    }
    const normalized = normalizeAnswer(q.id, Array.from(selected));
    answers[q.id] = normalized;

    if (stepIndex < QUESTIONS.length - 1) {
      stepIndex += 1;
      renderStep();
    } else {
      submit();
    }
  }

  function goSkip() {
    if (busy) return;
    const q = QUESTIONS[stepIndex];
    answers[q.id] = null;
    if (stepIndex < QUESTIONS.length - 1) {
      stepIndex += 1;
      renderStep();
    } else {
      submit();
    }
  }

  // ---- 提交 ----
  async function submit() {
    busy = true;
    nextBtn().disabled = true;
    skipBtn().disabled = true;
    nextBtn().textContent = '提交中...';

    const userId = getCurrentUserId();
    try {
      if (userId) {
        const resp = await fetch(`${window.location.origin}/api/v2/chat/onboard`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ student_id: userId, answers }),
        });
        const data = await resp.json().catch(() => ({}));
        // 落库成功后刷新画像雷达
        if (data && (data.success || data.portrait) && typeof window.fetchPortrait === 'function') {
          try { await window.fetchPortrait(true); } catch (e) { console.warn('[xs-onboard] fetchPortrait 失败:', e); }
        }
      } else {
        console.warn('[xs-onboard] 未登录,只标记看过,不落库');
      }
    } catch (e) {
      console.error('[xs-onboard] 提交失败(非阻塞):', e);
    } finally {
      try { localStorage.setItem(QA_LS_KEY, String(QA_VERSION)); } catch (e) {}
      hideMask();
      nextBtn().textContent = '下一题 →';
      nextBtn().disabled = false;
      skipBtn().disabled = false;
      busy = false;
    }
  }

  // ---- 暴露 API:fetchPortrait / fetchIntent / xsRenderProactive / xsRenderBlocked ----
  window.fetchPortrait = async function (force) {
    const userId = getCurrentUserId();
    if (!userId) return null;
    try {
      const url = `${window.location.origin}/api/profile/portrait/${encodeURIComponent(userId)}` + (force ? '?_t=' + Date.now() : '');
      const resp = await fetch(url);
      if (!resp.ok) return null;
      const data = await resp.json();
      const radarData = (data && data.portrait && data.portrait.radar) ? data.portrait.radar : (data && data.radar) ? data.radar : null;
      if (typeof window.drawRadarChart === 'function' && radarData) {
        try { window.drawRadarChart(radarData); } catch (e) { console.warn('[xs-onboard] drawRadarChart 失败:', e); }
      }
      if (typeof window.renderEvaluation === 'function' && data) {
        try { window.renderEvaluation(data); } catch (e) { console.warn('[xs-onboard] renderEvaluation 失败:', e); }
      }
      return data;
    } catch (e) {
      console.warn('[xs-onboard] fetchPortrait 失败:', e);
      return null;
    }
  };

  window.fetchIntent = async function (userInput) {
    // 本期:前端不真做意图路由(主路由在后端 L1);保留入口以备 Phase 2 调用
    const s = (userInput || '').toLowerCase();
    if (/生成课程|出一门课|设计一门|create a course|learning path|teach me/.test(s)) {
      return 'course_generate';
    }
    if (/去|跳到|打开|go to|navigate|switch to/.test(s)) {
      return 'navigate';
    }
    return 'socratic_qa';
  };

  window.xsRenderProactive = function (data) {
    const msg = (data && data.message) || '我们聊聊你的学习画像?';
    const deeplink = data && data.deeplink;
    const wrap = document.createElement('div');
    wrap.className = 'proactive-chip';
    const spanMsg = document.createElement('span');
    spanMsg.textContent = msg;
    wrap.innerHTML = '<span>💡</span>';
    wrap.appendChild(spanMsg);
    if (deeplink) {
      const a = document.createElement('a');
      a.href = deeplink;
      a.textContent = '去完善 →';
      wrap.appendChild(a);
    }
    const chat = document.getElementById('chat-container') || document.getElementById('chat-messages') || document.querySelector('.chat-messages') || document.querySelector('[data-chat-container]');
    if (!chat) {
      console.warn('[xs-onboard] 找不到 chat 容器,proactive 暂不入 DOM');
      return;
    }
    if (chat.firstChild) chat.insertBefore(wrap, chat.firstChild);
    else chat.appendChild(wrap);
  };

  window.xsRenderBlocked = function (data) {
    const hint = (data && data.hint) || '输入未通过安全检查。';
    const banner = document.createElement('div');
    banner.className = 'xs-blocked-banner';
    const icon = document.createElement('span');
    icon.className = 'xs-blocked-icon';
    icon.textContent = '⚠️';
    const txt = document.createElement('span');
    txt.textContent = hint;
    banner.appendChild(icon);
    banner.appendChild(txt);
    const chat = document.getElementById('chat-container') || document.getElementById('chat-messages') || document.querySelector('.chat-messages') || document.querySelector('[data-chat-container]');
    if (chat) chat.appendChild(banner);
  };

  // ---- 入口:首访判定 ----
  window.xsOnboardInit = async function () {
    if (parseInt(localStorage.getItem(QA_LS_KEY) || '0', 10) >= QA_VERSION) return;
    // 问卷 DOM 仅存在于 hub 页面（index.html），其他页面静默跳过
    if (!titleEl() || !maskEl()) return;
    const userId = getCurrentUserId();
    if (userId) {
      try {
        const resp = await fetch(`${window.location.origin}/api/v2/chat/onboard/status?student_id=${encodeURIComponent(userId)}`);
        const data = await resp.json();
        if (data && data.completed) {
          localStorage.setItem(QA_LS_KEY, String(data.version || QA_VERSION));
          return;
        }
      } catch (e) {
        console.warn('[xs-onboard] status 查询失败(非阻塞):', e);
      }
    }
    // 等一帧再弹,避免页面渲染抖动
    setTimeout(() => {
      stepIndex = 0;
      answers = {};
      renderStep();
      showMask();
    }, 300);
  };

  // ---- 事件绑定 ----
  function bind() {
    if (nextBtn()) nextBtn().addEventListener('click', goNext);
    if (skipBtn()) skipBtn().addEventListener('click', goSkip);
    if (closeBtn()) closeBtn().addEventListener('click', () => {
      // 关闭等价于:把剩下的题全标 null,提交(只标"看过")
      while (stepIndex < QUESTIONS.length) {
        const q = QUESTIONS[stepIndex];
        if (!(q.id in answers)) answers[q.id] = null;
        stepIndex += 1;
      }
      submit();
    });
    if (customEl()) {
      customEl().addEventListener('input', updateNextEnabled);
      customEl().addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !nextBtn().disabled) {
          e.preventDefault();
          goNext();
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      bind();
      window.xsOnboardInit();
    });
  } else {
    bind();
    window.xsOnboardInit();
  }
})();
