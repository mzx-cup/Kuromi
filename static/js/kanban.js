/**
 * 看板娘 v4 — Live2D 角色「小星」
 *
 * 使用 pixi-live2d-display + PixiJS 渲染 Live2D 开源模型。
 * 模型来源: npm live2d-widget-model-* 系列 (jsDelivr CDN)。
 *
 * Haru 模型 (live2d-widget-model-haru) — 官方 Live2D 免费示例模型
 *   8 个表情: f01(neutral) f02(happy) f03(concerned) f04(angry)
 *             f05-f08(扩展表情)
 *   支持拖拽、点击、表情切换
 *
 * 兼容所有已引入 mascot 脚本的页面。
 */
(function() {
  'use strict';

  const kanban = document.querySelector('.app-kanban');
  if (!kanban) return;

  // ═══════════════════════════════════════════
  // Config
  // ═══════════════════════════════════════════
  const PIXI_CDN   = 'https://cdn.jsdelivr.net/npm/pixi.js@5.3.12/dist/pixi.min.js';
  const CUBISM2_CDN = 'https://cdn.jsdelivr.net/npm/pixi-live2d-display@0.4.0/dist/cubism2.min.js'
  const LIVE2D_CORE_CDN = 'https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js'

  const DEFAULT_MODEL = 'Hibiki';

  const MODEL_LIST = [
    { name: 'Hibiki',   url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-hibiki@1.0.5/assets/hibiki.model.json' },
    { name: 'Haru',     url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-haru@1.0.5/01/assets/haru01.model.json' },
    { name: 'Izumi',    url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-izumi@1.0.5/assets/izumi.model.json' },
    { name: 'Shizuku',  url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-shizuku@1.0.5/assets/shizuku.model.json' },
    { name: 'Chitose',  url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-chitose@1.0.5/assets/chitose.model.json' },
    { name: 'Haruto',   url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-haruto@1.0.5/assets/haruto.model.json' },
    { name: 'Wanko',    url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-wanko@1.0.5/assets/wanko.model.json' },
    { name: 'Miku',     url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-miku@1.0.5/assets/miku.model.json' },
    { name: 'Z16',      url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-z16@1.0.5/assets/z16.model.json' },
    { name: 'Nito',     url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-nito@1.0.5/assets/nito.model.json' },
    { name: 'Nico',     url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-nico@1.0.5/assets/nico.model.json' },
    { name: 'Nipsilon', url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-nipsilon@1.0.5/assets/nipsilon.model.json' },
    { name: 'Tororo',   url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-tororo@1.0.5/assets/tororo.model.json' },
    { name: 'Tsumiki',  url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-tsumiki@1.0.5/assets/tsumiki.model.json' },
    { name: 'Unitychan',url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-unitychan@1.0.5/assets/unitychan.model.json' },
    { name: 'Koharu',   url: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-koharu@1.0.5/assets/koharu.model.json' },
  ];

  // ═══════════════════════════════════════════
  // 1. Build DOM
  // ═══════════════════════════════════════════
  function buildCharacter() {
    kanban.innerHTML = /*html*/`
      <canvas id="ak-canvas"></canvas>
      <button class="ak-close-btn" id="ak-close" title="隐藏小星">&times;</button>
      <div class="ak-pomodoro-indicator" id="ak-pomodoro-icon">🍅</div>
      <span class="ak-zzz" id="ak-zzz">💤</span>
      <div class="ak-bubble" id="ak-bubble"></div>
    `;
  }

  buildCharacter();

  // DOM refs
  const canvas  = document.getElementById('ak-canvas');
  const bubble  = document.getElementById('ak-bubble');
  const closeBtn = document.getElementById('ak-close');
  const pomodoroIcon = document.getElementById('ak-pomodoro-icon');
  const zzzEl = document.getElementById('ak-zzz');

  // ═══════════════════════════════════════════
  // 2. State
  // ═══════════════════════════════════════════
  let isHidden          = false;
  let currentExpression = 'neutral';
  let currentState      = '';
  let bubbleTimer       = null;
  let idleTipTimer      = null;
  let expressionTimer   = null;
  let clickCount        = 0;
  let clickResetTimer   = null;
  let loadingFailed     = false;

  // PIXI objects
  let app   = null;
  let model = null;
  let availableExpressions = [];   // [{ name: 'f01' }, ...]
  let exprMap = {};               // ourExpr -> modelExprName

  // ═══════════════════════════════════════════
  // 3. Dialogue Library
  // ═══════════════════════════════════════════
  const GREETINGS = {
    morning: [
      '早上好呀~ 新的一天要元气满满哦！☀️',
      '早安！今天也是学习的好天气呢~',
      '早啊~ 昨晚休息得还好吗？',
      '早上好！来一杯咖啡开始今天的学习吧 ☕',
      '清晨的阳光和知识最配了~'
    ],
    afternoon: [
      '下午好~ 学习进度如何啦？',
      '午后的阳光真舒服，但别打瞌睡哦！',
      '下午茶时间到~ 休息一下再继续吧 🍰',
      '下午好！今天的任务完成了吗？',
      '加油加油！下午的效率最高了~'
    ],
    evening: [
      '晚上好呀~ 今天学习辛苦了！',
      '天黑了，但学习的热情不能灭 🔥',
      '晚上了，来回顾一下今天的学习成果吧~',
      '晚上好！记得按时吃晚饭哦',
      '夜晚是深度学习的好时机呢~'
    ],
    night: [
      '这么晚了还在学习呀，要注意休息哦~ 🌙',
      '夜深了呢... 明天再继续吧',
      '该睡觉啦！充足的睡眠才能更好地学习~',
      '晚安~ 做个好梦，明天见！💤',
      '星识的夜空因为有你在努力而更加璀璨 ✨'
    ]
  };

  const CLICK_REACTIONS = [
    '诶？你戳我干嘛~',
    '别闹，我在认真学习呢！',
    '嘻嘻，有点痒~',
    '怎么啦？需要帮忙吗？',
    '啊！被你发现了什么小秘密吗~',
    '有这时间戳我，不如去背几个单词！📝',
    '嗯？有什么可以帮到你的？',
    '再戳我就要生气啦！...开玩笑的~',
    '嘿嘿，其实我一直在默默给你加油呢 💪',
    '点我可以打开AI助手面板哦！'
  ];

  const IDLE_TIPS = [
    '记得每天签到打卡哦~ 📅',
    '试试番茄钟，提升学习效率吧！🍅',
    '知识生态树每天都在成长呢 🌳',
    '去自习室找个学习伙伴吧！',
    '看看今天的数据统计，回顾学习成果~ 📊',
    '定期回顾知识点能帮助记忆哦 🧠',
    '遇到困难的时候，记得休息一下再继续',
    '代码工坊可以帮你练习编程哦 💻',
    '按 Ctrl+Shift+K 可以快速打开AI助手',
    '今天的小目标都完成了吗？'
  ];

  function getTimePeriod() {
    const h = new Date().getHours();
    if (h >= 6 && h < 12) return 'morning';
    if (h >= 12 && h < 18) return 'afternoon';
    if (h >= 18 && h < 23) return 'evening';
    return 'night';
  }

  function randomPick(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  // ═══════════════════════════════════════════
  // 4. Speech Bubble System
  // ═══════════════════════════════════════════
  function showBubble(msg, duration) {
    if (!bubble || isHidden) return;
    duration = duration || 4000;
    bubble.textContent = msg;
    bubble.classList.add('visible');
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(() => {
      bubble.classList.remove('visible');
    }, duration);
  }

  function hideBubble() {
    if (!bubble) return;
    bubble.classList.remove('visible');
    clearTimeout(bubbleTimer);
  }

  // ═══════════════════════════════════════════
  // 5. Expression System (Live2D)
  // ═══════════════════════════════════════════

  /**
   * Build expression name mapping: our canonical names -> model's actual expression IDs.
   * Each entry is a priority-ordered list of model expression names to try.
   */
  function buildExpressionMap() {
    const modelExprs = availableExpressions.map(e => e.name || e);
    // Log what's available for debugging
    console.log('[小星 v4] 模型可用表情:', modelExprs.join(', '));

    // Priority lists for mapping our expressions to model expression names
    const MAPPING_PRIORITY = {
      happy:      ['f02', 'happy', 'smile', 'fun', 'f01'],
      thinking:   ['f03', 'concerned', 'worried', 'sad', 'f04'],
      surprised:  ['f04', 'surprised', 'angry', 'shock', 'surprise'],
      encourage:  ['f05', 'encourage', 'f02', 'smile', 'happy'],
      celebrate:  ['f06', 'celebrate', 'f02', 'fun', 'happy'],
      love:       ['f07', 'love', 'f02', 'happy', 'smile'],
      sleepy:     ['f08', 'sleepy', 'tired', 'f03'],
      cool:       ['cool', 'f02', 'smile', 'f06'],
    };

    for (const [ourExpr, priorities] of Object.entries(MAPPING_PRIORITY)) {
      for (const candidate of priorities) {
        if (modelExprs.includes(candidate)) {
          exprMap[ourExpr] = candidate;
          break;
        }
      }
      if (!exprMap[ourExpr]) {
        exprMap[ourExpr] = modelExprs[0] || null;
      }
    }

    console.log('[小星 v4] 表情映射:', JSON.stringify(exprMap));
  }

  function setExpression(expr, duration) {
    if (!model || isHidden) return;
    if (currentExpression === expr && !duration) return;

    const modelExpr = exprMap[expr];
    if (!modelExpr) return;

    try {
      // Set expression on the Live2D model
      model.expression(modelExpr);
      currentExpression = expr;
    } catch (e) {
      console.warn('[小星 v4] 设置表情失败:', expr, e);
      return;
    }

    // Show/hide ZZZ overlay for sleepy expression
    if (zzzEl) {
      zzzEl.style.display = (expr === 'sleepy') ? 'block' : 'none';
    }

    // Auto-reset
    clearTimeout(expressionTimer);
    if (duration && duration > 0) {
      expressionTimer = setTimeout(() => resetExpression(), duration);
    }
  }

  function resetExpression() {
    if (!model) return;
    const neutralExpr = exprMap['neutral'] || availableExpressions[0]?.name;
    if (neutralExpr) {
      try {
        model.expression(neutralExpr);
      } catch (e) { /* silent */ }
    }
    currentExpression = 'neutral';
    clearTimeout(expressionTimer);
    // Hide ZZZ
    if (zzzEl) zzzEl.style.display = 'none';
  }

  function resetExpression() {
    if (!model) return;
    const neutralExpr = exprMap['neutral'] || availableExpressions[0]?.name;
    if (neutralExpr) {
      try {
        model.expression(neutralExpr);
      } catch (e) { /* silent */ }
    }
    currentExpression = 'neutral';
    clearTimeout(expressionTimer);
  }

  // ═══════════════════════════════════════════
  // 6. State System
  // ═══════════════════════════════════════════
  function setState(state, active) {
    if (!kanban) return;
    const cls = 'ak-state-' + state;
    if (active) {
      kanban.classList.add(cls);
      currentState = state;
    } else {
      kanban.classList.remove(cls);
      if (currentState === state) currentState = '';
    }
  }

  // ═══════════════════════════════════════════
  // 7. Action Triggers
  // ═══════════════════════════════════════════
  const ACTION_EXPRESSION = {
    encourage: ['encourage', 4000],
    celebrate: ['celebrate', 5000],
    happy:     ['happy', 3000],
    surprised: ['surprised', 3000],
    thinking:  ['thinking', 4000],
    love:      ['love', 4000],
    sleepy:    ['sleepy', 5000],
    cool:      ['cool', 3000],
    checkin:   ['celebrate', 6000],
    neutral:   [null, 0],
  };

  function triggerAction(action) {
    const [expr, duration] = ACTION_EXPRESSION[action] || ACTION_EXPRESSION['happy'];
    if (expr) {
      setExpression(expr, duration);
      const messages = {
        encourage: '加油！你可以的！💪',
        celebrate: '太棒了！🎉',
        checkin:   '签到成功！继续坚持哦~ 🔥',
        love:      '最喜欢和你一起学习啦~ 💜',
      };
      if (messages[action]) showBubble(messages[action], 3000);
    }
    // Try playing a random motion for extra liveliness
    if (model) {
      try {
        const motions = model.getMotions ? model.getMotions() : null;
        if (motions && motions.length > 0) {
          const rand = motions[Math.floor(Math.random() * motions.length)];
          model.motion(rand.group, rand.no || 0);
        }
      } catch (e) { /* motion is optional enhancement */ }
    }
    // Particle effects
    spawnParticles(action === 'celebrate' || action === 'checkin' ? 'celebrate' : 'encourage');
  }

  // ═══════════════════════════════════════════
  // 8. Particle Effects
  // ═══════════════════════════════════════════
  function spawnParticles(type) {
    const container = document.createElement('div');
    container.className = 'ak-particles';
    const rect = kanban.getBoundingClientRect();
    container.style.left = (rect.left + rect.width / 2 - 100) + 'px';
    container.style.bottom = (window.innerHeight - rect.top + 20) + 'px';
    container.style.width = '200px';
    container.style.height = '200px';
    document.body.appendChild(container);

    const emojiSets = {
      encourage: ['⭐', '🌟', '✨', '💪', '🔥'],
      celebrate: ['🎉', '🎊', '🥳', '✨', '🌟', '💫', '🏆', '🎯'],
      checkin:   ['🔥', '📅', '✅', '🌟', '💪', '🎯'],
      default:   ['⭐', '✨', '💫'],
    };
    const emojis = emojiSets[type] || emojiSets.default;
    const count = type === 'celebrate' ? 22 : type === 'checkin' ? 16 : 12;

    for (let i = 0; i < count; i++) {
      const particle = document.createElement('span');
      particle.className = 'ak-particle';
      particle.textContent = emojis[Math.floor(Math.random() * emojis.length)];
      particle.style.left = (15 + Math.random() * 70) + '%';
      particle.style.bottom = '0';
      particle.style.animationDelay = (Math.random() * 0.6) + 's';
      particle.style.animationDuration = (1.2 + Math.random() * 2) + 's';
      particle.style.fontSize = (14 + Math.random() * 14) + 'px';
      container.appendChild(particle);
    }

    setTimeout(() => container.remove(), 2800);
  }

  // ═══════════════════════════════════════════
  // 9. Click + DblClick Interaction
  // ═══════════════════════════════════════════
  let clickTimeout = null;

  canvas.addEventListener('click', (e) => {
    if (isHidden || loadingFailed) return;

    // Detect dblclick manually (PIXI canvas swallows native dblclick)
    if (clickTimeout) {
      // Double click detected
      clearTimeout(clickTimeout);
      clickTimeout = null;
      e.preventDefault();
      showBubble(randomPick([
        '哇！双击暴击！',
        '来了来了！有什么吩咐~',
        '这么热情呀~ 我们一起加油吧！',
      ]), 3000);
      setExpression('love', 3000);
      spawnParticles('encourage');
      return;
    }

    clickTimeout = setTimeout(() => {
      clickTimeout = null;
      // Single click
      clickCount++;
      clearTimeout(clickResetTimer);
      clickResetTimer = setTimeout(() => { clickCount = 0; }, 1500);

      if (clickCount >= 5) {
        showBubble('啊啊啊别戳了！我认输！(>_<)', 3000);
        setExpression('surprised', 2500);
        clickCount = 0;
      } else {
        showBubble(randomPick(CLICK_REACTIONS), 3200);
        const randExpr = randomPick(['happy', 'cool', 'love', 'encourage']);
        setExpression(randExpr, 2500);
      }

      // Trigger panel toggle
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('mascot:kanban-clicked'));
      }, 150);
    }, 280);
  });

  // ═══════════════════════════════════════════
  // 10. Drag Support
  // ═══════════════════════════════════════════
  let dragging = false;
  let dragStartX, dragStartY;
  let kanbanStartRight, kanbanStartBottom;

  canvas.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    dragging = true;
    kanban.classList.add('dragging');
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    const style = window.getComputedStyle(kanban);
    kanbanStartRight = parseInt(style.right) || 12;
    kanbanStartBottom = parseInt(style.bottom) || -6;
    kanban.style.transition = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const dx = dragStartX - e.clientX;
    const dy = dragStartY - e.clientY;
    kanban.style.right = (kanbanStartRight + dx) + 'px';
    kanban.style.bottom = (kanbanStartBottom + dy) + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    kanban.classList.remove('dragging');
    kanban.style.transition = '';
  });

  // Touch drag
  canvas.addEventListener('touchstart', (e) => {
    if (e.touches.length !== 1) return;
    dragging = true;
    kanban.classList.add('dragging');
    dragStartX = e.touches[0].clientX;
    dragStartY = e.touches[0].clientY;
    const style = window.getComputedStyle(kanban);
    kanbanStartRight = parseInt(style.right) || 12;
    kanbanStartBottom = parseInt(style.bottom) || -6;
    kanban.style.transition = 'none';
  }, { passive: false });

  document.addEventListener('touchmove', (e) => {
    if (!dragging) return;
    const dx = dragStartX - e.touches[0].clientX;
    const dy = dragStartY - e.touches[0].clientY;
    kanban.style.right = (kanbanStartRight + dx) + 'px';
    kanban.style.bottom = (kanbanStartBottom + dy) + 'px';
  }, { passive: false });

  document.addEventListener('touchend', () => {
    if (!dragging) return;
    dragging = false;
    kanban.classList.remove('dragging');
    kanban.style.transition = '';
  });

  // ═══════════════════════════════════════════
  // 11. Close / Restore
  // ═══════════════════════════════════════════
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isHidden = true;
    kanban.style.opacity = '0';
    kanban.style.transform = 'scale(0.8)';
    clearTimeout(idleTipTimer);
    hideBubble();

    setTimeout(() => {
      kanban.style.display = 'none';
      showRestoreButton();
    }, 350);
  });

  function showRestoreButton() {
    let restoreBtn = document.querySelector('.ak-restore-btn');
    if (!restoreBtn) {
      restoreBtn = document.createElement('button');
      restoreBtn.className = 'ak-restore-btn';
      restoreBtn.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 6v6l4 2"/>
        </svg>
      `;
      restoreBtn.title = '召唤小星';
      restoreBtn.addEventListener('click', restoreKanban);
      document.body.appendChild(restoreBtn);
    }
    restoreBtn.style.display = 'flex';
  }

  function restoreKanban() {
    isHidden = false;
    kanban.style.display = '';
    // Re-initialize PIXI if needed
    if (app && app.renderer) {
      app.renderer.resize(canvas.clientWidth, canvas.clientHeight);
    }
    setTimeout(() => {
      kanban.style.opacity = '1';
      kanban.style.transform = 'scale(1)';
    }, 20);

    const restoreBtn = document.querySelector('.ak-restore-btn');
    if (restoreBtn) restoreBtn.style.display = 'none';

    setTimeout(() => {
      showBubble(randomPick(GREETINGS[getTimePeriod()]), 4500);
      setExpression('happy', 3000);
    }, 500);

    startIdleTips();
  }

  window.MascotCore = window.MascotCore || {};
  window.MascotCore.restoreKanban = restoreKanban;

  // ═══════════════════════════════════════════
  // 12. Idle Tips Loop
  // ═══════════════════════════════════════════
  function startIdleTips() {
    clearTimeout(idleTipTimer);
    if (isHidden) return;
    const nextDelay = 15000 + Math.random() * 20000;
    idleTipTimer = setTimeout(() => {
      if (isHidden) return;
      const allTips = IDLE_TIPS.concat(GREETINGS[getTimePeriod()]);
      showBubble(randomPick(allTips), 5000);
      startIdleTips();
    }, nextDelay);
  }

  // ═══════════════════════════════════════════
  // 13. External Event Listeners
  // ═══════════════════════════════════════════

  window.addEventListener('mascot:set-expression', (e) => {
    if (isHidden) return;
    const expr = e.detail;
    if (expr && expr !== 'neutral') {
      setExpression(expr, 4000);
    } else if (expr === 'neutral') {
      resetExpression();
    }
  });

  window.addEventListener('mascot:trigger-action', (e) => {
    if (isHidden) return;
    triggerAction(e.detail);
  });

  window.addEventListener('mascot:update-state', (e) => {
    if (isHidden) return;
    const { state, active } = e.detail || {};
    if (state) setState(state, active !== false);
  });

  window.addEventListener('mascot:show-toast', (e) => {
    const { type } = e.detail || {};
    if (type === 'success') {
      setExpression('happy', 3000);
    } else if (type === 'warning') {
      setExpression('surprised', 2500);
    }
  });

  window.addEventListener('mascot:idle-detected', () => {
    if (isHidden) return;
    setExpression('sleepy', 6000);
    showBubble('你已经好一会没动了哦... 需要休息一下吗？😴', 6000);
  });

  // ═══════════════════════════════════════════
  // 14. Expose API
  // ═══════════════════════════════════════════
  let currentModelLoaded = false;

  async function switchModel(modelName) {
    const modelInfo = MODEL_LIST.find(m => m.name === modelName);
    if (!modelInfo) {
      console.warn(`[小星 v4] 未找到模型: ${modelName}`);
      return false;
    }
    if (modelInfo.loaded && model) {
      console.log(`[小星 v4] 模型 ${modelName} 已加载，跳过切换`);
      return true;
    }
    if (loadingFailed) {
      console.warn('[小星 v4] Live2D 加载失败，无法切换模型');
      return false;
    }

    console.log(`[小星 v4] 切换模型: → ${modelName}`);

    // Store panel state before destroying
    const wasPanelOpen = window.dispatchEvent(new CustomEvent('mascot:model-switching', { detail: { from: getCurrentModelName(), to: modelName } }));

    // Remove old model from stage
    if (model && app && app.stage) {
      try {
        app.stage.removeChild(model);
        if (model.destroy) model.destroy();
      } catch (e) {
        console.warn('[小星 v4] 销毁旧模型出错:', e);
      }
      model = null;
    }

    // Reset markers
    MODEL_LIST.forEach(m => { m.loaded = false; });

    // Load new model
    try {
      model = await loadModel(modelInfo);
      currentModelLoaded = true;
      showBubble(`${modelName} 来啦~ ✨`, 3000);
      window.dispatchEvent(new CustomEvent('mascot:model-switched', { detail: { model: modelName } }));
      return true;
    } catch (err) {
      console.error(`[小星 v4] 切换模型失败:`, err);
      showBubble(`切换失败 😢 重新加载默认模型...`, 3000);
      // Fallback: reload first model
      try {
        const fallback = MODEL_LIST[0];
        model = await loadModel(fallback);
        currentModelLoaded = true;
        window.dispatchEvent(new CustomEvent('mascot:model-switched', { detail: { model: fallback.name } }));
        return true;
      } catch (e2) {
        console.error('[小星 v4] 回退模型也加载失败:', e2);
        return false;
      }
    }
  }

  function getModelList() {
    return MODEL_LIST.map(m => ({
      name: m.name,
      loaded: !!m.loaded,
      expressions: m._rawDefinition?.expressions?.length || 0,
      motions: m._rawDefinition?.motions ? Object.keys(m._rawDefinition.motions).length : 0,
    }));
  }

  function getCurrentModelName() {
    if (loadingFailed || !model) return null;
    return MODEL_LIST.find(m => m.loaded)?.name || null;
  }

  window.MascotCore = window.MascotCore || {};
  Object.assign(window.MascotCore, {
    setExpression,
    resetExpression,
    showBubble,
    hideBubble,
    triggerAction,
    spawnParticles,
    setState,
    isHidden: () => isHidden,
    getExpression: () => currentExpression,
    getState: () => currentState,
    getModelName: getCurrentModelName,
    getModelList,
    switchModel,
  });

  // ═══════════════════════════════════════════
  // 15. Live2D Core — Script Loading & Init
  // ═══════════════════════════════════════════

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      // Check if already loaded
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) { resolve(); return; }

      const script = document.createElement('script');
      script.src = src;
      script.crossOrigin = 'anonymous';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Script load failed: ' + src));
      document.head.appendChild(script);
    });
  }

  async function loadDependencies() {
    // Load PixiJS
    await loadScript(PIXI_CDN);
    // pixi-live2d-display needs window.PIXI
    if (!window.PIXI) {
      throw new Error('PixiJS failed to initialize');
    }
    // Load Cubism 2.1 runtime (sets window.Live2D)
    await loadScript(LIVE2D_CORE_CDN);
    if (!window.Live2D) {
      throw new Error('Cubism 2.1 runtime failed to initialize');
    }
    // Load pixi-live2d-display Cubism 2 bundle (standalone — includes core + Cubism 2)
    await loadScript(CUBISM2_CDN);
    if (!window.PIXI.live2d || !window.PIXI.live2d.Live2DModel) {
      throw new Error('pixi-live2d-display failed to initialize');
    }
  }

  async function initPixiApp() {
    const { Application } = window.PIXI;

    app = new Application({
      view: canvas,
      width: 240,
      height: 400,
      transparent: true,
      antialias: true,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
      autoDensity: true,
    });

    // Ensure the canvas fills the container
    canvas.style.width = '100%';
    canvas.style.height = '100%';
  }

  async function loadModel(modelInfo) {
    const { Live2DModel } = window.PIXI.live2d;

    console.log(`[小星 v4] 尝试加载模型: ${modelInfo.name}...`);
    const m = await Live2DModel.from(modelInfo.url);

    // Auto-scale to fit canvas
    const canvasW = app.renderer.width / (app.renderer.resolution || 1);
    const canvasH = app.renderer.height / (app.renderer.resolution || 1);

    const modelW = m.width || m.internalModel?.getCanvasWidth?.() || 1000;
    const modelH = m.height || m.internalModel?.getCanvasHeight?.() || 1000;

    const scaleX = canvasW / modelW;
    const scaleY = canvasH / modelH;
    const scale = Math.min(scaleX, scaleY, 0.6);

    m.scale.set(scale);
    m.x = canvasW / 2;
    m.y = canvasH * 0.48;
    m.anchor?.set?.(0.5, 0.45);

    app.stage.addChild(m);

    // Get available expressions — try multiple approaches
    availableExpressions = [];

    // Approach 1: model.getExpressions()
    if (typeof m.getExpressions === 'function') {
      const raw = m.getExpressions();
      console.log('[小星 v4] getExpressions() 原始返回:', raw, 'type:', typeof raw, 'isArray:', Array.isArray(raw));
      if (Array.isArray(raw) && raw.length > 0) {
        availableExpressions = raw;
      }
    }

    // Approach 2: model.internalModel.getExpressions()
    if (availableExpressions.length === 0 && m.internalModel && typeof m.internalModel.getExpressions === 'function') {
      const raw = m.internalModel.getExpressions();
      console.log('[小星 v4] internalModel.getExpressions() 原始返回:', raw);
      if (Array.isArray(raw) && raw.length > 0) {
        availableExpressions = raw;
      }
    }

    // Approach 3: inspect model.internalModel for expressions
    if (availableExpressions.length === 0) {
      const im = m.internalModel;
      if (im) {
        console.log('[小星 v4] internalModel keys:', Object.keys(im));
        // Cubism2 models may store expressions in _expressions or expressions property
        const candidateKeys = ['_expressions', 'expressions', '_expressionManager', 'expressionManager', 'expressionNames'];
        for (const key of candidateKeys) {
          const val = im[key];
          console.log(`[小星 v4] internalModel.${key}:`, val);
          if (Array.isArray(val) && val.length > 0) {
            availableExpressions = val;
            break;
          }
        }
      }
    }

    // Approach 4: parse model JSON definition directly as fallback
    if (availableExpressions.length === 0 && modelInfo._rawDefinition) {
      const def = modelInfo._rawDefinition;
      if (def.expressions && Array.isArray(def.expressions)) {
        console.log('[小星 v4] 从模型 JSON 直接读取 expressions:', def.expressions);
        availableExpressions = def.expressions;
      }
    }

    // Normalize expressions to { name } objects
    availableExpressions = availableExpressions.map(e => {
      if (typeof e === 'string') return { name: e };
      if (e && e.name) return e;
      return null;
    }).filter(Boolean);

    buildExpressionMap();
    modelInfo.loaded = true;

    // Set initial expression to neutral/first
    if (availableExpressions.length > 0) {
      const firstExpr = availableExpressions[0].name;
      if (firstExpr) {
        try { m.expression(firstExpr); } catch (e) { console.warn('[小星 v4] 初始表情设置失败:', e); }
      }
    }

    console.log(`[小星 v4] ✓ 模型 ${modelInfo.name} 加载成功 (${availableExpressions.length} 表情, 缩放 ${scale.toFixed(2)})`);
    return m;
  }

  async function initLive2D() {
    // Pre-fetch model JSON definitions for expression fallback
    for (const info of MODEL_LIST) {
      try {
        const resp = await fetch(info.url);
        if (resp.ok) {
          info._rawDefinition = await resp.json();
          console.log(`[小星 v4] 预加载模型定义: ${info.name} (${info._rawDefinition.expressions?.length || 0} 表达式)`);
        }
      } catch (e) {
        console.warn(`[小星 v4] 预加载 ${info.name} 定义失败:`, e.message);
      }
    }

    // Try each model in order
    for (const modelInfo of MODEL_LIST) {
      try {
        model = await loadModel(modelInfo);
        return; // Success
      } catch (err) {
        console.warn(`[小星 v4] 模型 ${modelInfo.name} 加载失败:`, err.message);
        // Remove failed model from stage if partial
        if (model && app.stage.children.includes(model)) {
          app.stage.removeChild(model);
        }
        model = null;
      }
    }

    // All models failed
    throw new Error('所有 Live2D 模型均加载失败');
  }

  // ═══════════════════════════════════════════
  // 16. Fallback (when Live2D fails entirely)
  // ═══════════════════════════════════════════
  function showFallback() {
    loadingFailed = true;
    console.warn('[小星 v4] Live2D 不可用，使用降级方案');

    // Replace canvas with a simple character display
    if (canvas) canvas.style.display = 'none';

    const fallback = document.createElement('div');
    fallback.className = 'ak-fallback';
    fallback.innerHTML = `
      <div class="ak-fallback-character">
        <span class="ak-fallback-icon">🌟</span>
        <span class="ak-fallback-label">小星</span>
      </div>
    `;
    kanban.appendChild(fallback);

    // Make the fallback clickable
    fallback.addEventListener('click', () => {
      if (isHidden) return;
      window.dispatchEvent(new CustomEvent('mascot:kanban-clicked'));
    });

    // Still show greeting via bubble
    showBubble('小星今天有点害羞... 但还是会陪着你哦~ 💫', 5000);
  }

  // ═══════════════════════════════════════════
  // 17. Initialization
  // ═══════════════════════════════════════════
  async function init() {
    try {
      // Load dependencies (PixiJS + pixi-live2d-display)
      await loadDependencies();

      // Initialize PixiJS application
      await initPixiApp();

      // Load a Live2D model
      await initLive2D();
    } catch (err) {
      console.error('[小星 v4] Live2D 初始化失败:', err.message);
      showFallback();
    }

    // Show the kanban
    kanban.style.opacity = '1';
    kanban.style.transform = 'scale(1)';

    // Initial greeting
    if (!loadingFailed) {
      setTimeout(() => {
        if (!isHidden) {
          showBubble(randomPick(GREETINGS[getTimePeriod()]), 5000);
          setExpression('happy', 3500);
        }
      }, 1200);
    }

    // Start idle tips
    startIdleTips();

    console.log(`[小星 v4] 看板娘就绪 ✨ — Live2D ${loadingFailed ? '降级' : '完整'}模式`);
  }

  // Start when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
