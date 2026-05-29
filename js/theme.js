/**
 * Theme System - Wallpaper + Liquid Glass + Light/Dark
 *
 * - Light/dark mode toggle
 * - Wallpaper selection (static images + dynamic webm videos)
 * - Selecting a non-default wallpaper auto-enables liquid glass globally
 * - Brightness, blur, text contrast sliders
 * - Persisted to localStorage
 */
(function() {
  'use strict';

  var STORAGE_KEY = 'starlearn_theme_v2';
  var DEFAULT_THEME = 'warm-morning';

  // Wallpaper presets
  var WALLPAPERS = [
    { id: 'default',   title: '默认星图',     type: 'none',   url: '', preview: '' },
    { id: 'study-night', title: '书房夜晚',    type: 'static', url: '/static/wallpaper/static/书房夜晚/image.png', preview: '/static/wallpaper/static/书房夜晚/image-pre.webp' },
    { id: 'cozy',        title: '安逸舒适',    type: 'static', url: '/static/wallpaper/static/安逸舒适/image.png', preview: '/static/wallpaper/static/安逸舒适/image-pre.webp' },
    { id: 'ocean-girl',  title: '海洋女孩',    type: 'static', url: '/static/wallpaper/static/海洋女孩/image.png', preview: '/static/wallpaper/static/海洋女孩/image-pre.webp' },
    { id: 'aerospace',   title: '向往航天的女孩', type: 'dynamic', url: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane.webm', preview: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane-pre.webm' },
    { id: 'nier-team',   title: '尼尔：机械纪元 团队', type: 'dynamic', url: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team.webm', preview: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team-pre.webm' }
  ];

  var LIGHT_THEMES = ['warm-morning'];

  // Load or init state
  var state = loadState();

  function loadState() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && saved.theme) return saved;
    } catch (e) { /* ignore */ }
    return {
      theme: DEFAULT_THEME,
      wallpaperId: 'default',
      brightness: 85,
      blur: 5,
      textContrast: 30
    };
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function isLightTheme(theme) {
    return LIGHT_THEMES.indexOf(theme) !== -1;
  }

  function getWallpaper(id) {
    for (var i = 0; i < WALLPAPERS.length; i++) {
      if (WALLPAPERS[i].id === id) return WALLPAPERS[i];
    }
    return WALLPAPERS[0];
  }

  function applyWallpaper() {
    var wp = getWallpaper(state.wallpaperId);
    var root = document.documentElement;

    if (!wp || wp.type === 'none' || state.wallpaperId === 'default') {
      root.style.setProperty('--leleo-bg-image', 'none');
      root.style.setProperty('--leleo-bg-type', 'none');
      root.style.setProperty('--leleo-bg-video', 'none');
      root.setAttribute('data-glass', 'false');
      removeVideoBg();
    } else {
      if (wp.type === 'dynamic') {
        root.style.setProperty('--leleo-bg-image', 'url("' + (wp.preview || wp.url) + '")');
        root.style.setProperty('--leleo-bg-type', 'dynamic');
        root.style.setProperty('--leleo-bg-video', 'url("' + wp.url + '")');
        ensureVideoBg(wp.url);
      } else {
        root.style.setProperty('--leleo-bg-image', 'url("' + wp.url + '")');
        root.style.setProperty('--leleo-bg-type', 'static');
        root.style.setProperty('--leleo-bg-video', 'none');
        removeVideoBg();
      }
      root.setAttribute('data-glass', 'true');
    }

    root.style.setProperty('--leleo-brightness', state.brightness + '%');
    root.style.setProperty('--leleo-blur', state.blur + 'px');
    root.style.setProperty('--leleo-text-contrast', (state.textContrast / 100).toString());
  }

  var videoBgEl = null;

  function ensureVideoBg(url) {
    removeVideoBg();
    videoBgEl = document.createElement('video');
    videoBgEl.src = url;
    videoBgEl.autoplay = true;
    videoBgEl.loop = true;
    videoBgEl.muted = true;
    videoBgEl.playsInline = true;
    videoBgEl.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;object-fit:cover;z-index:-2;pointer-events:none;filter:brightness(' + state.brightness + '%) blur(' + state.blur + 'px);';
    videoBgEl.setAttribute('data-video-bg', 'true');
    document.body.prepend(videoBgEl);
  }

  function removeVideoBg() {
    if (videoBgEl && videoBgEl.parentNode) {
      videoBgEl.parentNode.removeChild(videoBgEl);
    }
    videoBgEl = null;
    // Also clean up any orphaned video bg
    var existing = document.querySelector('[data-video-bg]');
    if (existing) existing.remove();
  }

  function updateVideoFilter() {
    if (videoBgEl) {
      videoBgEl.style.filter = 'brightness(' + state.brightness + '%) blur(' + state.blur + 'px)';
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    var isLight = isLightTheme(theme);
    document.body.classList.toggle('light-theme', isLight);
    document.documentElement.classList.toggle('dark', !isLight);

    // (sakura particles removed — theme no longer exists)

    updateToggleButton(theme);
  }

  function applyAll() {
    applyTheme(state.theme);
    applyWallpaper();
  }

  function toggleTheme() {
    var current = state.theme;
    var next;
    if (current === 'warm-morning') {
      next = 'study-night';
    } else if (current === 'study-night') {
      next = 'starry-night';
    } else {
      next = 'warm-morning';
    }
    state.theme = next;
    saveState();
    applyAll();
  }

  function setWallpaper(wpId) {
    state.wallpaperId = wpId;
    saveState();
    applyWallpaper();
  }

  function setBrightness(val) {
    state.brightness = val;
    saveState();
    applyWallpaper();
    updateVideoFilter();
  }

  function setBlur(val) {
    state.blur = val;
    saveState();
    applyWallpaper();
    updateVideoFilter();
  }

  function setTextContrast(val) {
    state.textContrast = val;
    saveState();
    applyWallpaper();
  }

  function restoreDefaults() {
    state.wallpaperId = 'default';
    state.brightness = 85;
    state.blur = 5;
    state.textContrast = 30;
    saveState();
    applyAll();
  }

  // ---- Theme toggle button ----
  function updateToggleButton(theme) {
    var btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;
    var sunIcon = btn.querySelector('.sun-icon');
    var moonIcon = btn.querySelector('.moon-icon');
    if (!sunIcon || !moonIcon) return;

    if (isLightTheme(theme)) {
      sunIcon.style.opacity = '0';
      sunIcon.style.transform = 'rotate(0deg) scale(0)';
      moonIcon.style.opacity = '1';
      moonIcon.style.transform = 'rotate(0deg) scale(1)';
    } else {
      sunIcon.style.opacity = '1';
      sunIcon.style.transform = 'rotate(0deg) scale(1)';
      moonIcon.style.opacity = '0';
      moonIcon.style.transform = 'rotate(90deg) scale(0)';
    }
  }

  // ---- Theme Settings Modal ----
  function initThemeSettingsModal() {
    var triggerBtn = document.getElementById('theme-settings-btn');
    if (!triggerBtn) return;
    triggerBtn.addEventListener('click', openThemeModal);
  }

  function openThemeModal() {
    // Remove existing modal if any
    var existing = document.getElementById('theme-settings-modal');
    if (existing) existing.remove();

    var wp = getWallpaper(state.wallpaperId);
    var html = '';
    html += '<div class="theme-modal-overlay" id="theme-settings-modal">';
    html += '<div class="theme-modal glass-card">';
    html += '<div class="theme-modal-header">';
    html += '<h3 class="theme-modal-title">主题设置</h3>';
    html += '<button class="theme-modal-close" id="theme-modal-close">';
    html += '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    html += '</button></div>';

    // Appearance mode
    html += '<div class="theme-modal-section">';
    html += '<label class="theme-modal-label">外观模式</label>';
    html += '<div class="theme-mode-toggle">';
    html += '<button class="theme-mode-btn' + (isLightTheme(state.theme) ? '' : ' active') + '" data-mode="dark">深色</button>';
    html += '<button class="theme-mode-btn' + (isLightTheme(state.theme) ? ' active' : '') + '" data-mode="light">浅色</button>';
    html += '</div></div>';

    // Theme color selection
    html += '<div class="theme-modal-section">';
    html += '<label class="theme-modal-label">配色方案</label>';
    html += '<div class="theme-color-options">';
    html += '<button class="theme-color-btn' + (state.theme === 'warm-morning' ? ' active' : '') + '" data-theme="warm-morning"><span class="theme-color-swatch" style="background:linear-gradient(135deg,#f97316,#f59e0b)"></span>日出晨光</button>';
    html += '<button class="theme-color-btn' + (state.theme === 'study-night' ? ' active' : '') + '" data-theme="study-night"><span class="theme-color-swatch" style="background:linear-gradient(135deg,#fb923c,#21252b)"></span>深夜书房</button>';
    html += '<button class="theme-color-btn' + (state.theme === 'starry-night' ? ' active' : '') + '" data-theme="starry-night"><span class="theme-color-swatch" style="background:linear-gradient(135deg,#fbbf24,#a78bfa)"></span>星夜</button>';
    html += '</div></div>';

    // Wallpaper grid
    html += '<div class="theme-modal-section">';
    html += '<label class="theme-modal-label">壁纸</label>';
    html += '<div class="theme-wallpaper-grid">';
    for (var i = 0; i < WALLPAPERS.length; i++) {
      var w = WALLPAPERS[i];
      var selected = state.wallpaperId === w.id ? ' selected' : '';
      var isDyn = w.type === 'dynamic' ? ' dynamic' : '';
      html += '<button class="theme-wallpaper-thumb' + selected + isDyn + '" data-wp-id="' + w.id + '">';
      if (w.preview) {
        html += '<img src="' + w.preview + '" alt="' + w.title + '" class="theme-wallpaper-img" loading="lazy" onerror="this.style.display=\'none\'">';
      } else {
        html += '<div class="theme-wallpaper-placeholder">';
        html += '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M12 2a10 10 0 0 0 0 20"/><path d="M2 12h20"/></svg>';
        html += '</div>';
      }
      html += '<span class="theme-wallpaper-label">' + w.title + '</span>';
      if (w.type === 'dynamic') html += '<span class="theme-wallpaper-badge">动态</span>';
      html += '</button>';
    }
    html += '</div></div>';

    // Sliders
    html += '<div class="theme-modal-section">';
    html += '<div class="theme-slider-row">';
    html += '<label class="theme-modal-label">壁纸亮度 <span class="theme-slider-val">' + state.brightness + '%</span></label>';
    html += '<input type="range" class="theme-slider" id="theme-brightness" min="40" max="150" value="' + state.brightness + '">';
    html += '</div>';
    html += '<div class="theme-slider-row">';
    html += '<label class="theme-modal-label">模糊 <span class="theme-slider-val">' + state.blur + 'px</span></label>';
    html += '<input type="range" class="theme-slider" id="theme-blur" min="0" max="20" value="' + state.blur + '">';
    html += '</div>';
    html += '</div>';

    // Actions
    html += '<div class="theme-modal-actions">';
    html += '<button class="theme-action-btn ghost" id="theme-restore-btn">恢复默认</button>';
    html += '<button class="theme-action-btn ghost" id="theme-cancel-btn">取消</button>';
    html += '<button class="theme-action-btn primary" id="theme-confirm-btn">确认</button>';
    html += '</div>';

    html += '</div></div>';

    document.body.insertAdjacentHTML('beforeend', html);

    // Event bindings
    var modal = document.getElementById('theme-settings-modal');

    // Close
    document.getElementById('theme-modal-close').addEventListener('click', closeModal);
    document.getElementById('theme-cancel-btn').addEventListener('click', closeModal);
    modal.addEventListener('click', function(e) { if (e.target === modal) closeModal(); });

    // Mode toggle
    modal.querySelectorAll('.theme-mode-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        modal.querySelectorAll('.theme-mode-btn').forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
      });
    });

    // Color theme buttons
    modal.querySelectorAll('.theme-color-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        modal.querySelectorAll('.theme-color-btn').forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
      });
    });

    // Wallpaper thumbnails
    modal.querySelectorAll('.theme-wallpaper-thumb').forEach(function(btn) {
      btn.addEventListener('click', function() {
        modal.querySelectorAll('.theme-wallpaper-thumb').forEach(function(b) { b.classList.remove('selected'); });
        this.classList.add('selected');
        var wpId = this.getAttribute('data-wp-id');
        var wp = getWallpaper(wpId);
        // Preview: temporarily apply wallpaper
        if (wp && wp.type !== 'none') {
          document.documentElement.style.setProperty('--leleo-bg-image', 'url("' + (wp.preview || wp.url) + '")');
          document.documentElement.style.setProperty('--leleo-bg-type', wp.type);
          if (wp.type === 'dynamic') {
            document.documentElement.style.setProperty('--leleo-bg-video', 'url("' + wp.url + '")');
            ensureVideoBg(wp.url);
          } else {
            removeVideoBg();
          }
          document.documentElement.setAttribute('data-glass', 'true');
        } else {
          document.documentElement.style.setProperty('--leleo-bg-image', 'none');
          document.documentElement.setAttribute('data-glass', 'false');
          removeVideoBg();
        }
      });
    });

    // Sliders
    var brightnessSlider = document.getElementById('theme-brightness');
    var blurSlider = document.getElementById('theme-blur');
    brightnessSlider.addEventListener('input', function() {
      var val = parseInt(this.value);
      document.documentElement.style.setProperty('--leleo-brightness', val + '%');
      this.parentElement.querySelector('.theme-slider-val').textContent = val + '%';
      updateVideoFilter();
    });
    blurSlider.addEventListener('input', function() {
      var val = parseInt(this.value);
      document.documentElement.style.setProperty('--leleo-blur', val + 'px');
      this.parentElement.querySelector('.theme-slider-val').textContent = val + 'px';
      updateVideoFilter();
    });

    // Confirm
    document.getElementById('theme-confirm-btn').addEventListener('click', function() {
      var selectedThumb = modal.querySelector('.theme-wallpaper-thumb.selected');
      if (selectedThumb) {
        state.wallpaperId = selectedThumb.getAttribute('data-wp-id');
      }
      state.brightness = parseInt(brightnessSlider.value);
      state.blur = parseInt(blurSlider.value);

      var activeColorBtn = modal.querySelector('.theme-color-btn.active');
      if (activeColorBtn) {
        state.theme = activeColorBtn.getAttribute('data-theme');
      }

      var activeModeBtn = modal.querySelector('.theme-mode-btn.active');
      if (activeModeBtn) {
        var mode = activeModeBtn.getAttribute('data-mode');
        if (mode === 'light' && state.theme !== 'warm-morning') {
          state.theme = 'warm-morning';
        } else if (mode === 'dark' && state.theme === 'warm-morning') {
          state.theme = 'study-night';
        }
      }

      saveState();
      applyAll();
      closeModal();
    });

    // Restore
    document.getElementById('theme-restore-btn').addEventListener('click', function() {
      restoreDefaults();
      modal.querySelectorAll('.theme-wallpaper-thumb').forEach(function(b) { b.classList.remove('selected'); });
      var defaultThumb = modal.querySelector('[data-wp-id="default"]');
      if (defaultThumb) defaultThumb.classList.add('selected');
      brightnessSlider.value = 85;
      blurSlider.value = 5;
      document.querySelectorAll('.theme-slider-val')[0].textContent = '85%';
      document.querySelectorAll('.theme-slider-val')[1].textContent = '5px';
    });

    // Esc key
    function onKeydown(e) { if (e.key === 'Escape') { closeModal(); document.removeEventListener('keydown', onKeydown); } }
    document.addEventListener('keydown', onKeydown);
  }

  function closeModal() {
    var m = document.getElementById('theme-settings-modal');
    if (m) m.remove();
    // Restore current state visuals
    applyAll();
  }

  // ---- Sakura particles (existing) ----
  var sakuraCanvas = null, sakuraAnimationId = null;

  function renderSakuraParticles() {
    var existing = document.getElementById('sakura-canvas');
    if (existing) { existing.remove(); sakuraCanvas = null; }

    sakuraCanvas = document.createElement('canvas');
    sakuraCanvas.id = 'sakura-canvas';
    sakuraCanvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.6;';
    document.body.appendChild(sakuraCanvas);

    var canvas = sakuraCanvas;
    var ctx = canvas.getContext('2d');
    var particles = [];
    var particleCount = 50;

    function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
    resize();
    window.addEventListener('resize', resize);

    function SakuraParticle() { this.reset(); }
    SakuraParticle.prototype.reset = function() {
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height - canvas.height;
      this.size = Math.random() * 8 + 4;
      this.speedY = Math.random() * 1 + 0.5;
      this.speedX = Math.random() * 0.5 - 0.25;
      this.rotation = Math.random() * 360;
      this.rotationSpeed = Math.random() * 2 - 1;
      this.opacity = Math.random() * 0.5 + 0.3;
    };
    SakuraParticle.prototype.update = function() {
      this.y += this.speedY;
      this.x += this.speedX;
      this.rotation += this.rotationSpeed;
      if (this.y > canvas.height) { this.reset(); this.y = -10; }
    };
    SakuraParticle.prototype.draw = function() {
      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.rotate(this.rotation * Math.PI / 180);
      ctx.globalAlpha = this.opacity;
      ctx.fillStyle = '#ffb7c5';
      ctx.beginPath();
      ctx.ellipse(0, 0, this.size, this.size / 2, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    };

    for (var i = 0; i < particleCount; i++) particles.push(new SakuraParticle());

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < particles.length; i++) { particles[i].update(); particles[i].draw(); }
      sakuraAnimationId = requestAnimationFrame(animate);
    }
    animate();
  }

  function stopSakuraParticles() {
    if (sakuraAnimationId) { cancelAnimationFrame(sakuraAnimationId); sakuraAnimationId = null; }
    if (sakuraCanvas) { sakuraCanvas.remove(); sakuraCanvas = null; }
  }

  // ---- Init ----
  function init() {
    applyAll();

    // Theme toggle button (light/dark quick switch)
    var toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleTheme);
    }

    // Theme settings button (opens full modal)
    initThemeSettingsModal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Public API
  window.StarTheme = {
    WALLPAPERS: WALLPAPERS,
    getState: function() { return state; },
    setWallpaper: setWallpaper,
    setBrightness: setBrightness,
    setBlur: setBlur,
    setTextContrast: setTextContrast,
    restoreDefaults: restoreDefaults,
    applyAll: applyAll,
    toggleTheme: toggleTheme,
    openThemeModal: openThemeModal
  };
})();
