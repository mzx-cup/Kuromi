/**
 * Theme System v3 — Three-Layer Token Architecture
 * - mode (light/dark) + theme (color scheme) two-layer switching
 * - 5 preset themes + unlimited custom themes
 * - localStorage primary + server sync backup
 * - Wallpaper system (unchanged from v2)
 */
(function() {
  'use strict';

  // ===== Constants =====
  var STORAGE_KEY = 'starlearn_theme_v3';
  var CUSTOM_KEY = 'starlearn_custom_themes';
  var SYNC_DEBOUNCE = 2000;

  // ===== Preset Themes =====
  var PRESETS = {
    'warm-morning':  { name: '日出晨光', mode: 'light' },
    'forest-light':  { name: '林间晨光', mode: 'light' },
    'study-night':   { name: '深夜书房', mode: 'dark' },
    'starry-night':  { name: '星夜',     mode: 'dark' },
    'neon-cyber':    { name: '霓虹电光', mode: 'dark' },
    'pink-dark':     { name: '暗夜暖黄', mode: 'dark' }
  };

  // ===== Wallpapers =====
  var WALLPAPERS = [
    { id: 'default',     title: '默认星图',     type: 'none',    url: '', preview: '' },
    { id: 'study-night', title: '书房夜晚',     type: 'static',  url: '/static/wallpaper/static/书房夜晚/image.png', preview: '/static/wallpaper/static/书房夜晚/image-pre.webp' },
    { id: 'cozy',        title: '安逸舒适',     type: 'static',  url: '/static/wallpaper/static/安逸舒适/image.png', preview: '/static/wallpaper/static/安逸舒适/image-pre.webp' },
    { id: 'ocean-girl',  title: '海洋女孩',     type: 'static',  url: '/static/wallpaper/static/海洋女孩/image.png', preview: '/static/wallpaper/static/海洋女孩/image-pre.webp' },
    { id: 'aerospace',   title: '向往航天的女孩', type: 'dynamic', url: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane.webm', preview: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane-pre.webm' },
    { id: 'nier-team',   title: '尼尔：机械纪元 团队', type: 'dynamic', url: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team.webm', preview: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team-pre.webm' }
  ];

  // Preset brand colors for modal swatch preview
  var PRESET_BRAND_COLORS = {
    'warm-morning': '#f97316',
    'forest-light': '#16a34a',
    'study-night': '#fb923c',
    'starry-night': '#fbbf24',
    'neon-cyber': '#00e5ff',
    'pink-dark': '#f59e0b'
  };

  function getThemeBrandColor(themeId) {
    if (PRESET_BRAND_COLORS[themeId]) return PRESET_BRAND_COLORS[themeId];
    for (var i = 0; i < customThemes.length; i++) {
      var ct = customThemes[i];
      if (ct.id === themeId && ct.primitives) {
        var p = ct.primitives;
        if (typeof p['_brand-h'] !== 'undefined' && typeof p['_brand-c'] !== 'undefined' && typeof p['_brand-l'] !== 'undefined') {
          return 'hsl(' + p['_brand-h'] + ', ' + p['_brand-c'] + '%, ' + p['_brand-l'] + '%)';
        }
      }
    }
    return '#888';
  }

  // ===== State =====
  var state = loadState();
  var customThemes = loadCustomThemes();
  var syncTimer = null;
  var videoBgEl = null;

  function loadState() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && saved.theme && saved.mode) return saved;
    } catch (e) {}
    return {
      mode: 'dark',
      theme: 'pink-dark',
      wallpaperId: 'default',
      brightness: 85,
      blur: 5,
      textContrast: 30
    };
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    scheduleSync();
  }

  function loadCustomThemes() {
    try {
      var saved = JSON.parse(localStorage.getItem(CUSTOM_KEY));
      if (Array.isArray(saved)) return saved;
    } catch (e) {}
    return [];
  }

  function saveCustomThemes() {
    localStorage.setItem(CUSTOM_KEY, JSON.stringify(customThemes));
    scheduleSync();
  }

  // ===== Theme Info =====
  function getThemeInfo(themeId) {
    if (PRESETS[themeId]) return PRESETS[themeId];
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === themeId) {
        return { name: customThemes[i].name, mode: customThemes[i].mode };
      }
    }
    return { name: themeId, mode: 'light' };
  }

  function isLightMode() {
    return state.mode === 'light';
  }

  function getThemesForMode(mode) {
    var ids = [];
    for (var id in PRESETS) {
      if (PRESETS[id].mode === mode) ids.push(id);
    }
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].mode === mode) ids.push(customThemes[i].id);
    }
    return ids;
  }

  // ===== Apply =====
  function applyTheme(themeId) {
    state.theme = themeId;
    var info = getThemeInfo(themeId);
    state.mode = info.mode;
    document.documentElement.setAttribute('data-theme', themeId);
    document.body.classList.toggle('light-theme', state.mode === 'light');

    // Apply custom theme primitives if not a preset
    if (!PRESETS[themeId]) {
      for (var i = 0; i < customThemes.length; i++) {
        if (customThemes[i].id === themeId) {
          applyCustomThemePrimitives(customThemes[i].primitives);
          break;
        }
      }
    } else {
      clearCustomThemePrimitives();
    }
  }

  // CSS component primitives — setting these triggers full scale regeneration
  var PRIMITIVE_KEYS = [
    '_brand-h', '_brand-c', '_brand-l',
    '_success-h', '_success-c', '_success-l',
    '_warning-h', '_warning-c', '_warning-l',
    '_danger-h', '_danger-c', '_danger-l',
    '_info-h', '_info-c', '_info-l',
    '_neutral-h', '_neutral-c',
    '_shadow-strength', '_surface-saturation',
    '_color-scheme'
  ];

  function applyCustomThemePrimitives(primitives) {
    var root = document.documentElement;
    for (var i = 0; i < PRIMITIVE_KEYS.length; i++) {
      var key = PRIMITIVE_KEYS[i];
      if (primitives[key] !== undefined) {
        root.style.setProperty('--' + key, primitives[key]);
      }
    }
  }

  function clearCustomThemePrimitives() {
    var root = document.documentElement;
    for (var i = 0; i < PRIMITIVE_KEYS.length; i++) {
      root.style.removeProperty('--' + PRIMITIVE_KEYS[i]);
    }
  }

  function setMode(mode) {
    state.mode = mode;
    var themes = getThemesForMode(mode);
    if (themes.indexOf(state.theme) === -1) {
      state.theme = themes[0];
    }
    applyTheme(state.theme);
    saveState();
  }

  function setTheme(themeId) {
    applyTheme(themeId);
    saveState();
  }

  function toggleMode() {
    setMode(state.mode === 'light' ? 'dark' : 'light');
  }

  // ===== Wallpaper =====
  function getWallpaper(id) {
    for (var i = 0; i < WALLPAPERS.length; i++) {
      if (WALLPAPERS[i].id === id) return WALLPAPERS[i];
    }
    return WALLPAPERS[0];
  }

  function applyWallpaper() {
    var wp = getWallpaper(state.wallpaperId);
    removeVideoBg();

    if (wp.type === 'none') {
      document.documentElement.style.setProperty('--leleo-bg-image', 'none');
      document.documentElement.style.setProperty('--leleo-bg-type', 'none');
      document.documentElement.style.setProperty('--leleo-bg-video', 'none');
      document.documentElement.setAttribute('data-glass', 'false');
    } else {
      document.documentElement.style.setProperty('--leleo-bg-image', 'url("' + wp.url + '")');
      document.documentElement.style.setProperty('--leleo-bg-type', wp.type);
      document.documentElement.style.setProperty('--leleo-brightness', state.brightness + '%');
      document.documentElement.style.setProperty('--leleo-blur', state.blur + 'px');
      document.documentElement.style.setProperty('--leleo-text-contrast', state.textContrast + '%');
      document.documentElement.setAttribute('data-glass', 'true');
      if (wp.type === 'dynamic') {
        ensureVideoBg(wp.url);
      }
    }
  }

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
    var existing = document.querySelector('[data-video-bg]');
    if (existing) existing.remove();
  }

  function updateVideoFilter() {
    if (videoBgEl) {
      videoBgEl.style.filter = 'brightness(' + state.brightness + '%) blur(' + state.blur + 'px)';
    }
  }

  function setWallpaper(wpId) {
    state.wallpaperId = wpId;
    saveState();
    applyWallpaper();
  }

  function setBrightness(val) {
    state.brightness = val;
    saveState();
    document.documentElement.style.setProperty('--leleo-brightness', val + '%');
    updateVideoFilter();
  }

  function setBlur(val) {
    state.blur = val;
    saveState();
    document.documentElement.style.setProperty('--leleo-blur', val + 'px');
    updateVideoFilter();
  }

  function setTextContrast(val) {
    state.textContrast = val;
    saveState();
    document.documentElement.style.setProperty('--leleo-text-contrast', val + '%');
  }

  function restoreDefaults() {
    state.wallpaperId = 'default';
    state.brightness = 85;
    state.blur = 5;
    state.textContrast = 30;
    saveState();
    applyAll();
  }

  function applyAll() {
    applyTheme(state.theme);
    applyWallpaper();
  }

  // ===== Custom Theme CRUD =====
  function createCustomTheme(name, mode, primitives) {
    var id = 'custom-' + Date.now();
    customThemes.push({ id: id, name: name, mode: mode, primitives: primitives });
    saveCustomThemes();
    return id;
  }

  function updateCustomTheme(id, name, mode, primitives) {
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === id) {
        customThemes[i].name = name;
        customThemes[i].mode = mode;
        customThemes[i].primitives = primitives;
        saveCustomThemes();
        if (state.theme === id) {
          applyCustomThemePrimitives(primitives);
        }
        return true;
      }
    }
    return false;
  }

  function deleteCustomTheme(id) {
    customThemes = customThemes.filter(function(t) { return t.id !== id; });
    saveCustomThemes();
    if (state.theme === id) {
      setTheme(state.mode === 'light' ? 'warm-morning' : 'study-night');
    }
  }

  // ===== Server Sync =====
  function scheduleSync() {
    if (syncTimer) clearTimeout(syncTimer);
    syncTimer = setTimeout(syncToServer, SYNC_DEBOUNCE);
  }

  function syncToServer() {
    if (typeof window.__currentUserId === 'undefined') return;
    var payload = {
      userId: window.__currentUserId,
      mode: state.mode,
      theme: state.theme,
      wallpaper: {
        id: state.wallpaperId,
        brightness: state.brightness,
        blur: state.blur,
        textContrast: state.textContrast
      },
      customThemes: customThemes
    };
    fetch('/api/user/theme/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).catch(function(e) { console.warn('Theme sync failed:', e); });
  }

  function loadFromServer() {
    if (typeof window.__currentUserId === 'undefined') return;
    fetch('/api/user/theme/sync?user_id=' + window.__currentUserId)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data && data.theme) {
          state.mode = data.mode || 'light';
          state.theme = data.theme;
          if (data.wallpaper) {
            state.wallpaperId = data.wallpaper.id || 'default';
            state.brightness = data.wallpaper.brightness || 85;
            state.blur = data.wallpaper.blur || 5;
            state.textContrast = data.wallpaper.textContrast || 30;
          }
          if (Array.isArray(data.customThemes)) {
            customThemes = data.customThemes;
            saveCustomThemes();
          }
          saveState();
          applyAll();
        }
      }).catch(function(e) { console.warn('Theme sync failed:', e); });
  }

  // ===== Modal =====
  function initThemeSettingsModal() {
    var triggerBtn = document.getElementById('theme-settings-btn');
    if (!triggerBtn) return;
    triggerBtn.addEventListener('click', openThemeModal);
  }

  function openThemeModal() {
    var existing = document.getElementById('theme-settings-modal');
    if (existing) existing.remove();

    var themeCardsContainer, wpGrid;
    var brightnessInput, brightnessValEl;
    var blurInput, blurValEl;
    var textContrastInput, textContrastValEl;
    var lightBtn, darkBtn;

    var overlay = document.createElement('div');
    overlay.id = 'theme-settings-modal';
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeModal();
    });

    var modal = document.createElement('div');
    modal.className = 'tsm-modal';

    // --- Header ---
    var header = document.createElement('div');
    header.className = 'tsm-header';

    var title = document.createElement('h2');
    title.className = 'tsm-title';
    title.textContent = '主题设置';

    var closeBtn = document.createElement('button');
    closeBtn.className = 'tsm-close';
    closeBtn.textContent = '✕';
    closeBtn.addEventListener('click', closeModal);

    header.appendChild(title);
    header.appendChild(closeBtn);
    modal.appendChild(header);

    // --- Mode Toggle ---
    var modeSection = document.createElement('div');
    modeSection.className = 'tsm-section';

    var modeLabel = document.createElement('div');
    modeLabel.className = 'tsm-section-label';
    modeLabel.textContent = '模式';
    modeSection.appendChild(modeLabel);

    var modeToggle = document.createElement('div');
    modeToggle.className = 'tsm-mode-toggle';

    function updateModeButtons() {
      lightBtn.classList.toggle('active', state.mode === 'light');
      darkBtn.classList.toggle('active', state.mode === 'dark');
    }

    lightBtn = document.createElement('button');
    lightBtn.className = 'tsm-mode-btn';
    lightBtn.textContent = '亮色';
    if (state.mode === 'light') lightBtn.classList.add('active');
    lightBtn.addEventListener('click', function() {
      if (state.mode !== 'light') {
        setMode('light');
        updateModeButtons();
        renderThemeCards();
      }
    });
    modeToggle.appendChild(lightBtn);

    darkBtn = document.createElement('button');
    darkBtn.className = 'tsm-mode-btn';
    darkBtn.textContent = '暗色';
    if (state.mode === 'dark') darkBtn.classList.add('active');
    darkBtn.addEventListener('click', function() {
      if (state.mode !== 'dark') {
        setMode('dark');
        updateModeButtons();
        renderThemeCards();
      }
    });
    modeToggle.appendChild(darkBtn);

    modeSection.appendChild(modeToggle);
    modal.appendChild(modeSection);

    // --- Theme Cards ---
    var themeSection = document.createElement('div');
    themeSection.className = 'tsm-section';

    var themeLabel = document.createElement('div');
    themeLabel.className = 'tsm-section-label';
    themeLabel.textContent = '配色方案';
    themeSection.appendChild(themeLabel);

    themeCardsContainer = document.createElement('div');
    themeCardsContainer.className = 'tsm-theme-cards';
    themeSection.appendChild(themeCardsContainer);

    function renderThemeCards() {
      themeCardsContainer.innerHTML = '';
      var themes = getThemesForMode(state.mode);

      for (var i = 0; i < themes.length; i++) {
        var themeId = themes[i];
        var info = getThemeInfo(themeId);
        var brandColor = getThemeBrandColor(themeId);

        var card = document.createElement('div');
        card.className = 'tsm-theme-card';
        if (state.theme === themeId) card.classList.add('active');

        var swatch = document.createElement('div');
        swatch.className = 'tsm-swatch';
        swatch.style.background = brandColor;

        var nameEl = document.createElement('div');
        nameEl.className = 'tsm-card-name';
        nameEl.textContent = info.name;

        card.appendChild(swatch);
        card.appendChild(nameEl);

        (function(tid) {
          card.addEventListener('click', function() {
            setTheme(tid);
            renderThemeCards();
          });
        })(themeId);

        themeCardsContainer.appendChild(card);
      }
    }

    renderThemeCards();
    modal.appendChild(themeSection);

    // --- Brand Color Quick Picker ---
    var BRAND_SWATCHES = [
      { hex: '#f97316', label: '暖橙', h: 42,  c: 0.18, l: 62 },
      { hex: '#16a34a', label: '森林绿', h: 148, c: 0.16, l: 52 },
      { hex: '#00e5ff', label: '电光青', h: 195, c: 0.26, l: 62 },
      { hex: '#fbbf24', label: '金色', h: 52,  c: 0.17, l: 72 },
      { hex: '#8b5cf6', label: '紫罗兰', h: 270, c: 0.18, l: 54 },
      { hex: '#f43f5e', label: '玫红', h: 10,  c: 0.20, l: 58 }
    ];

    var brandSection = document.createElement('div');
    brandSection.className = 'tsm-section';

    var brandLabel = document.createElement('div');
    brandLabel.className = 'tsm-section-label';
    brandLabel.textContent = '品牌色';
    brandSection.appendChild(brandLabel);

    var brandRow = document.createElement('div');
    brandRow.className = 'tsm-brand-row';

    for (var b = 0; b < BRAND_SWATCHES.length; b++) {
      (function(bs) {
        var sw = document.createElement('button');
        sw.className = 'tsm-brand-swatch';
        sw.title = bs.label;
        sw.style.background = bs.hex;
        sw.addEventListener('click', function() {
          var root = document.documentElement;
          root.style.setProperty('--_brand-h', bs.h);
          root.style.setProperty('--_brand-c', bs.c);
          root.style.setProperty('--_brand-l', bs.l + '%');
        });
        brandRow.appendChild(sw);
      })(BRAND_SWATCHES[b]);
    }

    var colorInput = document.createElement('input');
    colorInput.type = 'color';
    colorInput.className = 'tsm-brand-input';
    colorInput.title = '自定义品牌色';
    colorInput.addEventListener('input', function() {
      var hex = colorInput.value;
      var r = parseInt(hex.slice(1,3), 16) / 255;
      var g = parseInt(hex.slice(3,5), 16) / 255;
      var b_ = parseInt(hex.slice(5,7), 16) / 255;
      var max = Math.max(r,g,b_), min = Math.min(r,g,b_);
      var L = Math.round((max + min) / 2 * 100);
      var delta = max - min;
      var H = 0, S = 0;
      if (delta !== 0) {
        S = delta / (1 - Math.abs(2 * L/100 - 1));
        if (max === r) H = ((g - b_) / delta) % 6;
        else if (max === g) H = (b_ - r) / delta + 2;
        else H = (r - g) / delta + 4;
        H = Math.round(H * 60);
        if (H < 0) H += 360;
      }
      var C = Math.round(S * 35) / 100;
      var root = document.documentElement;
      root.style.setProperty('--_brand-h', H);
      root.style.setProperty('--_brand-c', Math.min(C, 0.32));
      root.style.setProperty('--_brand-l', L + '%');
    });
    brandRow.appendChild(colorInput);

    brandSection.appendChild(brandRow);
    modal.appendChild(brandSection);

    // --- Wallpaper Section ---
    var wallpaperSection = document.createElement('div');
    wallpaperSection.className = 'tsm-section';

    var wpLabel = document.createElement('div');
    wpLabel.className = 'tsm-section-label';
    wpLabel.textContent = '壁纸';
    wallpaperSection.appendChild(wpLabel);

    wpGrid = document.createElement('div');
    wpGrid.className = 'tsm-wp-grid';

    function renderWallpapers() {
      wpGrid.innerHTML = '';
      for (var i = 0; i < WALLPAPERS.length; i++) {
        var wp = WALLPAPERS[i];

        var wpCard = document.createElement('div');
        wpCard.className = 'tsm-wp-card';
        if (state.wallpaperId === wp.id) wpCard.classList.add('active');

        if (wp.preview) {
          var thumb = document.createElement('img');
          thumb.className = 'tsm-wp-thumb';
          thumb.src = wp.preview;
          thumb.alt = wp.title;
          wpCard.appendChild(thumb);
        } else {
          var placeholder = document.createElement('div');
          placeholder.className = 'tsm-wp-placeholder';
          placeholder.textContent = '★';
          wpCard.appendChild(placeholder);
        }

        var wpName = document.createElement('div');
        wpName.className = 'tsm-wp-name';
        wpName.textContent = wp.title;
        wpCard.appendChild(wpName);

        (function(wid) {
          wpCard.addEventListener('click', function() {
            setWallpaper(wid);
            updateWallpaperHighlight();
          });
        })(wp.id);

        wpGrid.appendChild(wpCard);
      }
    }

    function updateWallpaperHighlight() {
      var cards = wpGrid.querySelectorAll('.tsm-wp-card');
      for (var i = 0; i < cards.length; i++) {
        var wpId = WALLPAPERS[i] ? WALLPAPERS[i].id : '';
        cards[i].classList.toggle('active', state.wallpaperId === wpId);
      }
    }

    renderWallpapers();
    wallpaperSection.appendChild(wpGrid);
    modal.appendChild(wallpaperSection);

    // --- Sliders ---
    var slidersSection = document.createElement('div');
    slidersSection.className = 'tsm-section';

    function createSlider(label, value, min, max, step, onChange) {
      var row = document.createElement('div');
      row.className = 'tsm-slider-row';

      var labelRow = document.createElement('div');
      labelRow.className = 'tsm-slider-label';

      var lblSpan = document.createElement('span');
      lblSpan.textContent = label;

      var valSpan = document.createElement('span');
      valSpan.textContent = value;

      labelRow.appendChild(lblSpan);
      labelRow.appendChild(valSpan);

      var input = document.createElement('input');
      input.type = 'range';
      input.className = 'tsm-slider';
      input.min = String(min);
      input.max = String(max);
      input.step = String(step);
      input.value = String(value);

      input.addEventListener('input', function() {
        valSpan.textContent = input.value;
        onChange(Number(input.value));
      });

      row.appendChild(labelRow);
      row.appendChild(input);

      return { row: row, input: input, valSpan: valSpan };
    }

    var brightnessSlider = createSlider('亮度', state.brightness, 10, 100, 1, setBrightness);
    brightnessInput = brightnessSlider.input;
    brightnessValEl = brightnessSlider.valSpan;
    slidersSection.appendChild(brightnessSlider.row);

    var blurSlider = createSlider('模糊度', state.blur, 0, 20, 1, setBlur);
    blurInput = blurSlider.input;
    blurValEl = blurSlider.valSpan;
    slidersSection.appendChild(blurSlider.row);

    var textContrastSlider = createSlider('文字对比度', state.textContrast, 0, 100, 1, setTextContrast);
    textContrastInput = textContrastSlider.input;
    textContrastValEl = textContrastSlider.valSpan;
    slidersSection.appendChild(textContrastSlider.row);

    modal.appendChild(slidersSection);

    // --- Actions ---
    var actions = document.createElement('div');
    actions.className = 'tsm-actions';

    var restoreBtn = document.createElement('button');
    restoreBtn.className = 'tsm-restore-btn';
    restoreBtn.textContent = '恢复默认';
    restoreBtn.addEventListener('click', function() {
      restoreDefaults();
      renderThemeCards();
      renderWallpapers();
      brightnessInput.value = String(state.brightness);
      brightnessValEl.textContent = state.brightness;
      blurInput.value = String(state.blur);
      blurValEl.textContent = state.blur;
      textContrastInput.value = String(state.textContrast);
      textContrastValEl.textContent = state.textContrast;
    });

    var advancedLink = document.createElement('a');
    advancedLink.className = 'tsm-advanced-link';
    advancedLink.textContent = '高级编辑 →';
    advancedLink.href = 'settings.html';

    actions.appendChild(restoreBtn);
    actions.appendChild(advancedLink);
    modal.appendChild(actions);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  }

  function closeModal() {
    var m = document.getElementById('theme-settings-modal');
    if (m) m.remove();
    applyAll();
  }

  // ===== Init =====
  function init() {
    applyAll();
    loadFromServer();
    initThemeSettingsModal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ===== Public API =====
  window.StarTheme = {
    WALLPAPERS: WALLPAPERS,
    PRESETS: PRESETS,
    getState: function() { return Object.assign({}, state); },
    getCustomThemes: function() { return customThemes.slice(); },
    setMode: setMode,
    setTheme: setTheme,
    toggleMode: toggleMode,
    isLightMode: isLightMode,
    getThemesForMode: getThemesForMode,
    getThemeInfo: getThemeInfo,
    setWallpaper: setWallpaper,
    setBrightness: setBrightness,
    setBlur: setBlur,
    setTextContrast: setTextContrast,
    restoreDefaults: restoreDefaults,
    applyAll: applyAll,
    openThemeModal: openThemeModal,
    createCustomTheme: createCustomTheme,
    updateCustomTheme: updateCustomTheme,
    deleteCustomTheme: deleteCustomTheme,
    loadFromServer: loadFromServer
  };
})();
