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
