/**
 * 看板娘 — 二次元少女「小星」v3
 *
 * 纯 CSS 绘制 + JS 表情/状态控制。零外部依赖，不需 Live2D CDN。
 * 兼容所有已引入 mascot 脚本的页面（hub/code/courses/index/personal/my-courses/socratic-ai）。
 *
 * 角色特征:
 *   - 紫色双马尾 + 星形发夹 + 呆毛
 *   - 8 种表情 (neutral/happy/thinking/surprised/encourage/celebrate/love/sleepy/cool)
 *   - 3 种状态 (recording/pomodoro/idle 浮动)
 *   - 点击/双击/拖拽交互
 *   - 对话气泡 + 粒子特效
 *   - 关闭/恢复按钮
 */
(function() {
  'use strict';

  const kanban = document.querySelector('.app-kanban');
  if (!kanban) return;

  // ═══════════════════════════════════════════
  // 1. 构建角色 DOM
  // ═══════════════════════════════════════════
  function buildCharacter() {
    kanban.innerHTML = /*html*/`
      <div class="ak-kanban-body idle-anim" id="ak-body">
        <!-- 关闭按钮 -->
        <button class="ak-close-btn" id="ak-close" title="隐藏小星">&times;</button>

        <!-- 番茄钟指示器 -->
        <div class="ak-pomodoro-indicator" id="ak-pomodoro-icon">🍅</div>

        <!-- ZZZ 睡眠 -->
        <span class="ak-zzz" id="ak-zzz">💤</span>

        <!-- 星形发夹 -->
        <div class="ak-star-pin"></div>

        <!-- 呆毛 -->
        <div class="ak-ahoge"></div>

        <!-- 后发 + 双马尾 -->
        <div class="ak-hair-back"></div>
        <div class="ak-tail ak-tail-l"></div>
        <div class="ak-tail ak-tail-r"></div>
        <div class="ak-tail-ribbon ak-tail-ribbon-l"></div>
        <div class="ak-tail-ribbon ak-tail-ribbon-r"></div>

        <!-- 头部 -->
        <div class="ak-head">
          <div class="ak-ear ak-ear-l"></div>
          <div class="ak-ear ak-ear-r"></div>
        </div>

        <!-- 手臂 -->
        <div class="ak-arm ak-arm-l"></div>
        <div class="ak-arm ak-arm-r"></div>

        <!-- 身体 -->
        <div class="ak-body">
          <div class="ak-dress-star"></div>
        </div>
        <div class="ak-collar"></div>

        <!-- 前发 -->
        <div class="ak-hair-front"></div>
        <div class="ak-bangs"></div>
        <div class="ak-hair-side-l"></div>
        <div class="ak-hair-side-r"></div>

        <!-- 五官 -->
        <div class="ak-eyebrow ak-eyebrow-l"></div>
        <div class="ak-eyebrow ak-eyebrow-r"></div>
        <div class="ak-eye ak-eye-l">
          <div class="ak-iris"></div>
          <div class="ak-eye-highlight"></div>
        </div>
        <div class="ak-eye ak-eye-r">
          <div class="ak-iris"></div>
          <div class="ak-eye-highlight"></div>
        </div>
        <div class="ak-blush ak-blush-l"></div>
        <div class="ak-blush ak-blush-r"></div>
        <div class="ak-nose"></div>
        <div class="ak-mouth"></div>

        <!-- 对话气泡 -->
        <div class="ak-bubble" id="ak-bubble"></div>
      </div>
    `;
  }

  buildCharacter();

  // ═══════════════════════════════════════════
  // 2. DOM 引用
  // ═══════════════════════════════════════════
  const body   = document.getElementById('ak-body');
  const bubble = document.getElementById('ak-bubble');
  const closeBtn = document.getElementById('ak-close');
  const pomodoroIcon = document.getElementById('ak-pomodoro-icon');
  const zzzEl = document.getElementById('ak-zzz');

  // ═══════════════════════════════════════════
  // 3. 状态
  // ═══════════════════════════════════════════
  let isHidden = false;
  let currentExpression = 'neutral';
  let currentState = '';
  let bubbleTimer = null;
  let idleTipTimer = null;
  let expressionTimer = null;
  let clickCount = 0;
  let clickResetTimer = null;

  // ═══════════════════════════════════════════
  // 4. 对话库
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
  // 5. 气泡系统
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
  // 6. 表情系统
  // ═══════════════════════════════════════════
  const EXPR_CLASSES = [
    'ak-expr-happy', 'ak-expr-thinking', 'ak-expr-surprised',
    'ak-expr-encourage', 'ak-expr-celebrate', 'ak-expr-love',
    'ak-expr-sleepy', 'ak-expr-cool'
  ];

  function setExpression(expr, duration) {
    if (!body || isHidden) return;
    if (currentExpression === expr && !duration) return;

    // 清除旧表情
    EXPR_CLASSES.forEach(c => body.classList.remove(c));
    currentExpression = expr;

    // 设置新表情
    const cls = 'ak-expr-' + expr;
    if (EXPR_CLASSES.includes(cls)) {
      body.classList.add(cls);
    }

    // 自动恢复
    clearTimeout(expressionTimer);
    if (duration && duration > 0) {
      expressionTimer = setTimeout(() => resetExpression(), duration);
    }
  }

  function resetExpression() {
    if (!body) return;
    EXPR_CLASSES.forEach(c => body.classList.remove(c));
    currentExpression = 'neutral';
    clearTimeout(expressionTimer);
  }

  // ═══════════════════════════════════════════
  // 7. 状态系统
  // ═══════════════════════════════════════════
  function setState(state, active) {
    if (!body) return;
    const cls = 'ak-state-' + state;
    if (active) {
      body.classList.add(cls);
      currentState = state;
    } else {
      body.classList.remove(cls);
      if (currentState === state) currentState = '';
    }
  }

  // ═══════════════════════════════════════════
  // 8. 表情联动动作
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
    // 粒子特效
    spawnParticles(action === 'celebrate' || action === 'checkin' ? 'celebrate' : 'encourage');
  }

  // ═══════════════════════════════════════════
  // 9. 粒子特效
  // ═══════════════════════════════════════════
  function spawnParticles(type) {
    const container = document.createElement('div');
    container.className = 'ak-particles';
    // 定位在角色上方
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
  // 10. 点击 + 双击交互
  // ═══════════════════════════════════════════
  body.addEventListener('click', (e) => {
    if (isHidden || e.target === closeBtn || e.target.closest('.ak-close-btn')) return;

    clickCount++;
    clearTimeout(clickResetTimer);
    clickResetTimer = setTimeout(() => { clickCount = 0; }, 1500);

    if (clickCount >= 5) {
      showBubble('啊啊啊别戳了！我认输！(>_<)', 3000);
      setExpression('surprised', 2500);
      clickCount = 0;
    } else {
      showBubble(randomPick(CLICK_REACTIONS), 3200);
      // 随机表情
      const randExpr = randomPick(['happy', 'cool', 'love', 'encourage']);
      setExpression(randExpr, 2500);
    }

    // 触发面板切换 (延迟，让点击反应先播放)
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('mascot:kanban-clicked'));
    }, 150);
  });

  body.addEventListener('dblclick', (e) => {
    if (isHidden) return;
    e.preventDefault();
    showBubble(randomPick([
      '哇！双击暴击！',
      '来了来了！有什么吩咐~',
      '这么热情呀~ 我们一起加油吧！',
    ]), 3000);
    setExpression('love', 3000);
    spawnParticles('encourage');
  });

  // ═══════════════════════════════════════════
  // 11. 拖拽支持
  // ═══════════════════════════════════════════
  let dragging = false;
  let dragStartX, dragStartY;
  let kanbanStartRight, kanbanStartBottom;

  body.addEventListener('mousedown', (e) => {
    if (e.target === closeBtn || e.target.closest('.ak-close-btn')) return;
    if (e.button !== 0) return;
    dragging = true;
    body.classList.add('dragging');
    body.classList.remove('idle-anim');
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
    body.classList.remove('dragging');
    body.classList.add('idle-anim');
    kanban.style.transition = '';
  });

  // 触摸拖拽
  body.addEventListener('touchstart', (e) => {
    if (e.target === closeBtn || e.target.closest('.ak-close-btn')) return;
    if (e.touches.length !== 1) return;
    dragging = true;
    body.classList.add('dragging');
    body.classList.remove('idle-anim');
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
    body.classList.remove('dragging');
    body.classList.add('idle-anim');
    kanban.style.transition = '';
  });

  // ═══════════════════════════════════════════
  // 12. 关闭 / 恢复
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
    }, 400);
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

  // 暴露恢复函数
  window.MascotCore = window.MascotCore || {};
  window.MascotCore.restoreKanban = restoreKanban;

  // ═══════════════════════════════════════════
  // 13. 空闲 Tips 循环
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
  // 14. 外部事件监听 (来自 mascot-core / mascot-panel)
  // ═══════════════════════════════════════════

  // 表情指令
  window.addEventListener('mascot:set-expression', (e) => {
    if (isHidden) return;
    const expr = e.detail;
    if (expr && expr !== 'neutral') {
      setExpression(expr, 4000);
    } else if (expr === 'neutral') {
      resetExpression();
    }
  });

  // 动作触发
  window.addEventListener('mascot:trigger-action', (e) => {
    if (isHidden) return;
    triggerAction(e.detail);
  });

  // 来自面板的状态同步
  window.addEventListener('mascot:update-state', (e) => {
    if (isHidden) return;
    const { state, active } = e.detail || {};
    if (state) setState(state, active !== false);
  });

  // Toast 通知 (面板关闭时 via mascot-core)
  window.addEventListener('mascot:show-toast', (e) => {
    // Toast 由 mascot-core 处理，这里只做表情联动
    const { type } = e.detail || {};
    if (type === 'success') {
      setExpression('happy', 3000);
    } else if (type === 'warning') {
      setExpression('surprised', 2500);
    }
  });

  // 空闲检测 — 角色表现困倦
  window.addEventListener('mascot:idle-detected', () => {
    if (isHidden) return;
    setExpression('sleepy', 6000);
    showBubble('你已经好一会没动了哦... 需要休息一下吗？😴', 6000);
  });

  // ═══════════════════════════════════════════
  // 15. 暴露 API
  // ═══════════════════════════════════════════
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
  });

  // ═══════════════════════════════════════════
  // 16. 初始化
  // ═══════════════════════════════════════════
  function init() {
    kanban.style.opacity = '1';
    kanban.style.transform = 'scale(1)';

    // 初次问候
    setTimeout(() => {
      if (!isHidden) {
        showBubble(randomPick(GREETINGS[getTimePeriod()]), 5000);
        setExpression('happy', 3500);
      }
    }, 1200);

    // 启动空闲 Tips
    startIdleTips();

    console.log('[小星 v3] 二次元少女就绪 ✨ — 紫色双马尾 + 呆毛 + 星形发夹');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
