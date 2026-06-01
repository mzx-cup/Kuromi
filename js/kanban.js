/**
 * 看板娘 — Live2D 角色 + 智能对话系统
 *
 * 依赖: oh-my-live2d CDN (动态加载)
 * fallback: 静态立绘 + 3D视差跟随
 */
(function() {
  'use strict';

  const kanban = document.querySelector('.app-kanban');
  const img = document.querySelector('.app-kanban-img');
  const bubble = document.querySelector('.app-kanban-bubble');
  const closeBtn = document.querySelector('.app-kanban-close');
  if (!kanban) return;

  // ===== 模型配置 =====
  const MODEL_CONFIGS = [
    {
      name: 'Senko',
      path: 'https://cdn.jsdelivr.net/gh/Eikanya/Live2d-model/Live2D/Senko_Normals/senko.model3.json',
      scale: 0.1,
      position: [0, 40],
      stageStyle: { width: 300, height: 480 }
    },
    {
      name: 'Shizuku',
      path: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-shizuku@latest/assets/shizuku.model.json',
      scale: 1,
      position: [10, 30],
      stageStyle: { width: 300, height: 480 }
    }
  ];

  // ===== 对话库 =====
  var GREETINGS = {
    morning: [
      '早上好呀~ 新的一天要元气满满哦！',
      '早安！今天也是学习的好天气呢~',
      '早啊~ 昨晚休息得还好吗？',
      '早上好！来一杯咖啡开始今天的学习吧',
      '清晨的阳光和知识最配了~'
    ],
    afternoon: [
      '下午好~ 学习进度如何啦？',
      '午后的阳光真舒服，但别打瞌睡哦！',
      '下午茶时间到~ 休息一下再继续吧',
      '下午好！今天的每日路线完成了吗？',
      '加油加油！下午的效率最高了~'
    ],
    evening: [
      '晚上好呀~ 今天学习辛苦了！',
      '天黑了，但学习的热情不能灭',
      '晚上了，来回顾一下今天的学习成果吧~',
      '晚上好！记得按时吃晚饭哦',
      '夜晚是深度学习的好时机呢~'
    ],
    night: [
      '这么晚了还在学习呀，要注意休息哦~',
      '夜深了呢... 明天再继续吧',
      '该睡觉啦！充足的睡眠才能更好地学习~',
      '晚安~ 做个好梦，明天见！',
      '星识的夜空因为有你在努力而更加璀璨'
    ]
  };

  var CLICK_REACTIONS = [
    '诶？你戳我干嘛~',
    '别闹，我在认真学习呢！',
    '嘻嘻，有点痒~',
    '怎么啦？需要帮忙吗？',
    '啊！被你发现了什么小秘密吗~',
    '点击有惊喜哦... 才怪啦！',
    '有这时间戳我，不如去背几个单词！',
    '嗯？有什么可以帮到你的？',
    '再戳我就要生气啦！...开玩笑的~',
    '嘿嘿，其实我一直在默默给你加油呢'
  ];

  var IDLE_TIPS = [
    '记得每天完成每日路线打卡哦~',
    '心流分数越高，学习效果越好！',
    '试试专注计时器，提升学习效率吧~',
    '知识生态树每天都在成长呢',
    '去自习室找个学习伙伴吧！',
    '看看今天的数据统计，回顾学习成果~',
    '定期回顾知识点能帮助记忆哦',
    '标签云里有你感兴趣的所有主题',
    '看板可以帮你管理工作和学习任务',
    '遇到困难的时候，记得休息一下再继续'
  ];

  // ===== 状态 =====
  var isLive2DReady = false;
  var live2dInstance = null;
  var dialogueTimer = null;
  var isHidden = false;

  // ===== 工具函数 =====
  function getTimePeriod() {
    var h = new Date().getHours();
    if (h >= 6 && h < 12) return 'morning';
    if (h >= 12 && h < 18) return 'afternoon';
    if (h >= 18 && h < 23) return 'evening';
    return 'night';
  }

  function randomPick(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  // ===== 对话系统 =====
  function showBubble(msg, duration) {
    if (!bubble || isHidden) return;
    duration = duration || 4000;
    bubble.textContent = msg;
    bubble.classList.add('visible');
    clearTimeout(bubble._timeout);
    bubble._timeout = setTimeout(function() {
      bubble.classList.remove('visible');
    }, duration);
  }

  function showLive2DTip(msg) {
    if (isHidden) return;
    // 优先使用 oh-my-live2d 原生 tipsMessage
    if (live2dInstance && typeof live2dInstance.tipsMessage === 'function') {
      live2dInstance.tipsMessage(msg);
    } else if (
      live2dInstance &&
      live2dInstance.stage &&
      typeof live2dInstance.stage.tipsMessage === 'function'
    ) {
      live2dInstance.stage.tipsMessage(msg);
    } else {
      // fallback 到自定义气泡
      showBubble(msg, 4500);
    }
  }

  function speakGreeting() {
    showLive2DTip(randomPick(GREETINGS[getTimePeriod()]));
  }

  function showRandomTip() {
    if (isHidden) return;
    var allTips = IDLE_TIPS.concat(GREETINGS[getTimePeriod()]);
    showLive2DTip(randomPick(allTips));
    var nextDelay = 8000 + Math.random() * 12000;
    dialogueTimer = setTimeout(showRandomTip, nextDelay);
  }

  function showClickReaction() {
    showLive2DTip(randomPick(CLICK_REACTIONS));
  }

  // ===== Live2D 加载 =====
  function loadScript(url) {
    return new Promise(function(resolve, reject) {
      var script = document.createElement('script');
      script.src = url;
      script.async = true;
      script.onload = function() { resolve(); };
      script.onerror = function() { reject(new Error('Script load failed: ' + url)); };
      document.head.appendChild(script);
    });
  }

  function createLoadingIndicator() {
    var loader = document.createElement('div');
    loader.className = 'app-kanban-loading active';
    kanban.appendChild(loader);
    return loader;
  }

  function positionOml2dStage() {
    // oh-my-live2d 创建的元素需要 CSS 定位到右下角
    var selectors = [
      '#oml2d-stage',
      '[class*="oml2d-stage"]',
      '[id*="oml2d"]',
      '.oml2d',
      'canvas[id*="oml2d"]'
    ];
    for (var i = 0; i < selectors.length; i++) {
      try {
        var el = document.querySelector(selectors[i]);
        if (el) {
          el.style.cssText += ';position:fixed !important;bottom:0 !important;right:20px !important;z-index:500 !important;pointer-events:auto !important;';
          // Also try to find parent container
          var parent = el.parentElement;
          if (parent && parent !== document.body && parent.tagName !== 'BODY') {
            parent.style.cssText += ';position:fixed !important;bottom:0 !important;right:20px !important;z-index:500 !important;pointer-events:none !important;';
          }
          return true;
        }
      } catch (e) { /* try next selector */ }
    }
    return false;
  }

  function tryGetTipsMessageAPI() {
    // oh-my-live2d 不同版本的 tipsMessage 可能在返回值的不同位置
    if (live2dInstance) {
      if (typeof live2dInstance.tipsMessage === 'function') return;
      if (live2dInstance.stage && typeof live2dInstance.stage.tipsMessage === 'function') return;
    }

    // 检查 OML2D 全局对象
    if (typeof OML2D !== 'undefined') {
      if (typeof OML2D.tipsMessage === 'function') {
        live2dInstance = OML2D;
        return;
      }
      if (OML2D.stage && typeof OML2D.stage.tipsMessage === 'function') {
        live2dInstance = OML2D;
        return;
      }
      // tipsMessage 可能在 OML2D 的其他属性中
      for (var key in OML2D) {
        if (OML2D[key] && typeof OML2D[key].tipsMessage === 'function') {
          live2dInstance = OML2D[key];
          return;
        }
      }
    }
  }

  async function initLive2D() {
    var loader = createLoadingIndicator();

    try {
      await loadScript('https://cdn.jsdelivr.net/npm/oh-my-live2d/dist/index.min.js');
    } catch (e) {
      console.warn('[看板娘] oh-my-live2d CDN 加载失败，使用静态立绘 fallback:', e.message);
      loader.classList.remove('active');
      fallbackToStatic();
      return;
    }

    if (typeof OML2D === 'undefined' || typeof OML2D.loadOml2d !== 'function') {
      console.warn('[看板娘] OML2D 全局对象不可用，使用静态立绘 fallback');
      loader.classList.remove('active');
      fallbackToStatic();
      return;
    }

    for (var i = 0; i < MODEL_CONFIGS.length; i++) {
      var cfg = MODEL_CONFIGS[i];
      try {
        console.log('[看板娘] 尝试加载模型:', cfg.name);

        live2dInstance = OML2D.loadOml2d({
          models: [{
            path: cfg.path,
            scale: cfg.scale,
            position: cfg.position,
            stageStyle: cfg.stageStyle
          }],
          tips: {
            style: {
              width: 240,
              offsetX: 0,
              offsetY: -20
            },
            idleTips: {
              interval: 20000
            }
          },
          menus: {},
          mobileShow: false,
          dockedPosition: 'right'
        });

        await new Promise(function(resolve) { setTimeout(resolve, 2000); });

        if (positionOml2dStage()) {
          console.log('[看板娘] 模型 ' + cfg.name + ' 加载成功');
          loader.classList.remove('active');
          isLive2DReady = true;
          tryGetTipsMessageAPI();
          onLive2DReady();
          return;
        }
      } catch (e) {
        console.warn('[看板娘] 模型 ' + cfg.name + ' 加载失败:', e.message);
      }
    }

    console.warn('[看板娘] 所有模型加载失败，使用静态立绘 fallback');
    loader.classList.remove('active');
    fallbackToStatic();
  }

  function onLive2DReady() {
    if (img) {
      img.style.opacity = '0';
      img.style.pointerEvents = 'none';
    }

    // 定期重试定位（某些 Live2D 库异步创建 DOM）
    var retryCount = 0;
    var retryInterval = setInterval(function() {
      retryCount++;
      if (positionOml2dStage() || retryCount >= 5) {
        clearInterval(retryInterval);
      }
    }, 800);

    setTimeout(function() { speakGreeting(); }, 1500);
    dialogueTimer = setTimeout(showRandomTip, 12000);
  }

  function fallbackToStatic() {
    isLive2DReady = false;
    if (img) {
      img.style.opacity = '1';
      img.style.pointerEvents = 'auto';
    }
    initStaticParallax();
    setTimeout(function() {
      showBubble(randomPick(GREETINGS[getTimePeriod()]), 5000);
    }, 1000);
    dialogueTimer = setTimeout(cycleStaticTips, 12000);
  }

  function cycleStaticTips() {
    if (isHidden || isLive2DReady) return;
    var allTips = IDLE_TIPS.concat(GREETINGS[getTimePeriod()]);
    showBubble(randomPick(allTips), 4000);
    dialogueTimer = setTimeout(cycleStaticTips, 8000 + Math.random() * 10000);
  }

  // ===== 静态立绘 3D 视差 =====
  function initStaticParallax() {
    if (!img) return;
    var mouseX = 0.5, mouseY = 0.5;
    var currentRotateY = 8, currentRotateX = -2;
    var baseRotateY = 8, baseRotateX = -2;
    var maxRotate = 12;
    var startTime = Date.now();

    document.addEventListener('mousemove', function(e) {
      mouseX = e.clientX / window.innerWidth;
      mouseY = e.clientY / window.innerHeight;
    });

    function animate() {
      if (isLive2DReady || isHidden) { requestAnimationFrame(animate); return; }

      var elapsed = Date.now() - startTime;
      var floatY = Math.sin(elapsed * 0.0015) * 10;
      var targetRY = baseRotateY - (mouseX - 0.5) * maxRotate * 2;
      var targetRX = baseRotateX + (mouseY - 0.5) * maxRotate;

      currentRotateY += (targetRY - currentRotateY) * 0.08;
      currentRotateX += (targetRX - currentRotateX) * 0.08;

      img.style.transform =
        'perspective(800px) ' +
        'rotateY(' + currentRotateY.toFixed(2) + 'deg) ' +
        'rotateX(' + currentRotateX.toFixed(2) + 'deg) ' +
        'translateY(' + floatY.toFixed(2) + 'px)';

      requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
  }

  // ===== 关闭按钮 =====
  if (closeBtn) {
    var kanbanInner = document.querySelector('.app-kanban-inner');
    if (kanbanInner) {
      kanbanInner.addEventListener('mouseenter', function() {
        if (!isHidden) closeBtn.classList.add('show');
      });
      kanbanInner.addEventListener('mouseleave', function() {
        closeBtn.classList.remove('show');
      });
    }

    closeBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      isHidden = true;
      kanban.style.opacity = '0';
      kanban.style.transform = 'scale(0.8)';
      clearTimeout(dialogueTimer);
      if (bubble) bubble.classList.remove('visible');

      setTimeout(function() {
        kanban.style.display = 'none';
        showRestoreButton();
      }, 400);
    });
  }

  // ===== 恢复按钮 =====
  function showRestoreButton() {
    var restoreBtn = document.querySelector('.app-kanban-restore');
    if (!restoreBtn) {
      restoreBtn = document.createElement('button');
      restoreBtn.className = 'app-kanban-restore';
      restoreBtn.innerHTML =
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        '<circle cx="12" cy="12" r="10"/>' +
        '<polyline points="12 6 12 12 16 14"/>' +
        '</svg>';
      restoreBtn.title = '召唤看板娘';
      Object.assign(restoreBtn.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: '501',
        width: '44px',
        height: '44px',
        borderRadius: '50%',
        background: 'var(--surface-glass, rgba(255,255,255,0.1))',
        border: '1px solid var(--border-glass, rgba(255,255,255,0.15))',
        color: 'var(--brand, #6366f1)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
        transition: 'all 0.3s ease-out',
        animation: 'fadeInUp 0.4s var(--ease-out, ease-out)',
        padding: '0'
      });
      restoreBtn.addEventListener('click', restoreKanban);
      restoreBtn.addEventListener('mouseenter', function() {
        this.style.transform = 'scale(1.1)';
        this.style.boxShadow = '0 6px 24px rgba(0,0,0,0.3)';
      });
      restoreBtn.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
        this.style.boxShadow = '0 4px 16px rgba(0,0,0,0.2)';
      });
      document.body.appendChild(restoreBtn);
    }
    restoreBtn.style.display = 'flex';
  }

  function restoreKanban() {
    isHidden = false;
    kanban.style.display = '';
    setTimeout(function() {
      kanban.style.opacity = '1';
      kanban.style.transform = 'scale(1)';
    }, 20);

    var restoreBtn = document.querySelector('.app-kanban-restore');
    if (restoreBtn) restoreBtn.style.display = 'none';

    setTimeout(function() { speakGreeting(); }, 500);
    dialogueTimer = setTimeout(showRandomTip, 10000);
  }

  // ===== 点击交互 =====
  if (kanbanInner) {
    var clickCount = 0;
    var clickResetTimer = null;

    kanbanInner.addEventListener('click', function(e) {
      if (e.target === closeBtn || isHidden) return;
      clickCount++;
      clearTimeout(clickResetTimer);
      clickResetTimer = setTimeout(function() { clickCount = 0; }, 1500);

      if (clickCount >= 5) {
        showLive2DTip('啊啊啊别戳了！我认输！(>_<)');
        clickCount = 0;
      } else {
        showClickReaction();
      }
    });

    kanbanInner.addEventListener('dblclick', function(e) {
      if (e.target === closeBtn || isHidden) return;
      e.preventDefault();
      showLive2DTip(randomPick([
        '哇！双击暴击！',
        '来了来了！有什么吩咐~',
        '这么热情呀~ 我们一起加油吧！'
      ]));
    });
  }

  // ===== 初始化 =====
  function init() {
    kanban.style.opacity = '1';
    kanban.style.transform = 'scale(1)';
    initLive2D();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
