/**
 * Theme System v4 — 统一主题与壁纸引擎
 *
 * 设计要点：
 *  - 6 个精品预设（3 亮 + 3 暗）+ 无限自定义主题
 *  - 单一背景容器 #theme-bg（自动注入），替代旧的 5 套机制
 *  - 配色 / 壁纸 / 视频 / 蒙版 / 亮度 / 模糊 / 对比度 全部走 CSS 变量
 *  - localStorage 主存储 + 后端 /api/user/theme/sync 同步（用 Auth.me.id）
 *  - 向后兼容：旧 data-theme="pink-dark" 等会自动映射，旧 StarTheme.* API 全保留
 */
(function () {
  'use strict';

  // ===== Constants =====
  var STORAGE_KEY = 'starlearn_theme_v4';
  var LEGACY_KEYS = ['starlearn_theme_v3', 'starlearn_theme_v2'];
  var CUSTOM_KEY  = 'starlearn_custom_themes';
  var SYNC_DEBOUNCE = 1500;

  // ===== 预设主题 =====
  var PRESETS = {
    'dawn':             { name: '晨曦',   mode: 'light', brand: '#f08a3e' },
    'forest':           { name: '森野',   mode: 'light', brand: '#3aa056' },
    'sakura':           { name: '樱语',   mode: 'light', brand: '#e85d8a' },
    'midnight':         { name: '子夜',   mode: 'dark',  brand: '#f5b65a' },
    'nebula':           { name: '星云',   mode: 'dark',  brand: '#a98cef' },
    'cyber':            { name: '赛博',   mode: 'dark',  brand: '#3dd9e0' },
    // 旧主题 ID（index.html 下拉面板直接调用 setTheme('ocean') 等）
    'ocean':            { name: '星海蓝', mode: 'light', brand: '#2563eb' },
    'sunset':           { name: '暮光橙', mode: 'light', brand: '#d97706' },
    'sakura-falling':   { name: '烂漫樱花', mode: 'light', brand: '#f9a8d4' },
    'starry-night':     { name: '浩瀚星空', mode: 'dark',  brand: '#3b82f6' },
    'lunar-halo':       { name: '皎月流光', mode: 'dark',  brand: '#94a3b8' },
    'flowing-aurora':   { name: '极光之影', mode: 'dark',  brand: '#2dd4bf' }
  };

  // ===== 旧主题 ID → 新主题（仅用于明暗模式推断，不再改写视觉主题） =====
  var LEGACY_THEME_MAP = {
    'warm-morning':    'dawn',
    'ocean-glass':     'dawn',
    'twilight-glow':   'dawn',
    'forest-light':    'forest',
    'bamboo-grove':    'forest',
    'sakura-whisper':  'sakura',
    'study-night':     'midnight',
    'starry-night':    'midnight',
    'pink-dark':       'midnight',
    'deep-ocean':      'nebula',
    'ocean-glass-dark':'nebula',
    'star-vault':      'nebula',
    'neon-cyber':      'cyber'
  };

  // ===== v1 旧主题 ID 的明暗模式（index.html 旧下拉面板用） =====
  var LEGACY_MODE = {
    'ocean': 'light', 'forest': 'light', 'sunset': 'light', 'sakura-falling': 'light',
    'starry-night': 'dark', 'lunar-halo': 'dark', 'flowing-aurora': 'dark'
  };

  // ===== 壁纸资源 =====
  var WALLPAPERS = [
    { id: 'default',    title: '主题底色',          type: 'none',    url: '', preview: '' },
    { id: 'study-night',title: '书房夜晚',          type: 'static',  url: '/static/wallpaper/static/书房夜晚/image.png', preview: '/static/wallpaper/static/书房夜晚/image-pre.webp' },
    { id: 'cozy',       title: '安逸舒适',          type: 'static',  url: '/static/wallpaper/static/安逸舒适/image.png', preview: '/static/wallpaper/static/安逸舒适/image-pre.webp' },
    { id: 'ocean-girl', title: '海洋女孩',          type: 'static',  url: '/static/wallpaper/static/海洋女孩/image.png', preview: '/static/wallpaper/static/海洋女孩/image-pre.webp' },
    { id: 'aerospace',  title: '向往航天的女孩',    type: 'dynamic', url: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane.webm', preview: '/static/wallpaper/dynamic/向往航天的女孩/Toy-Aeroplane-pre.webm' },
    { id: 'nier-team',  title: '尼尔：机械纪元 团队', type: 'dynamic', url: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team.webm', preview: '/static/wallpaper/dynamic/尼尔：机械纪元 团队/Nier-Automata-Team-pre.webm' }
  ];

  // ===== 品牌色快速选择 =====
  var BRAND_SWATCHES = [
    { hex: '#f08a3e', label: '暖橙', h: 32,  c: 0.18, l: 62 },
    { hex: '#3aa056', label: '翠绿', h: 148, c: 0.16, l: 52 },
    { hex: '#e85d8a', label: '樱粉', h: 340, c: 0.18, l: 60 },
    { hex: '#f5b65a', label: '琥珀', h: 38,  c: 0.19, l: 68 },
    { hex: '#a98cef', label: '紫罗兰', h: 268, c: 0.18, l: 70 },
    { hex: '#3dd9e0', label: '霓虹青', h: 192, c: 0.24, l: 64 },
    { hex: '#f43f5e', label: '玫红', h: 350, c: 0.22, l: 56 },
    { hex: '#fbbf24', label: '金色', h: 50,  c: 0.18, l: 70 }
  ];

  // ===== 自定义主题可调原语 =====
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

  // ===== 状态 =====
  var state = loadState();
  var customThemes = loadCustomThemes();
  var syncTimer = null;
  var videoEl = null;
  var bgContainer = null;

  // ===== 持久化 =====
  function loadState() {
    // v4 主存储
    try {
      var s = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (s && s.theme) return migrateState(s);
    } catch (e) {}
    // 尝试旧版本 v3/v2
    for (var i = 0; i < LEGACY_KEYS.length; i++) {
      try {
        var old = JSON.parse(localStorage.getItem(LEGACY_KEYS[i]) || 'null');
        if (old && old.theme) {
          var migrated = migrateState(old);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
          return migrated;
        }
      } catch (e) {}
    }
    // 默认（兼容页面已有 data-theme）
    var pageTheme = document.documentElement.getAttribute('data-theme');
    var seed = pageTheme && resolveThemeId(pageTheme);
    var fallback = seed || 'dawn';
    return defaultState(fallback);
  }

  function defaultState(theme) {
    var info = PRESETS[theme] || PRESETS.dawn;
    return {
      mode: info.mode,
      theme: theme,
      wallpaperId: 'default',
      brightness: 100,
      blur: 0,
      textContrast: 0
    };
  }

  function migrateState(s) {
    var theme = s.theme || 'dawn';
    return {
      mode: s.mode || getModeForTheme(theme),
      theme: theme,
      wallpaperId: s.wallpaperId || (s.wallpaper && s.wallpaper.id) || 'default',
      brightness: numOr(s.brightness !== undefined ? s.brightness : (s.wallpaper && s.wallpaper.brightness), 100),
      blur:       numOr(s.blur       !== undefined ? s.blur       : (s.wallpaper && s.wallpaper.blur),       0),
      textContrast: numOr(s.textContrast !== undefined ? s.textContrast : (s.wallpaper && s.wallpaper.textContrast), 0)
    };
  }

  function numOr(v, d) { v = Number(v); return isFinite(v) ? v : d; }

  function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
    scheduleSync();
  }

  function loadCustomThemes() {
    try {
      var saved = JSON.parse(localStorage.getItem(CUSTOM_KEY) || 'null');
      if (Array.isArray(saved)) return saved;
    } catch (e) {}
    return [];
  }

  function saveCustomThemes() {
    try { localStorage.setItem(CUSTOM_KEY, JSON.stringify(customThemes)); } catch (e) {}
    scheduleSync();
  }

  // ===== 主题信息 =====
  function resolveThemeId(themeId) {
    if (!themeId) return null;
    if (PRESETS[themeId]) return themeId;
    if (LEGACY_THEME_MAP[themeId]) return LEGACY_THEME_MAP[themeId];
    // 自定义主题
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === themeId) return themeId;
    }
    return null;
  }

  function getThemeInfo(themeId) {
    var resolved = resolveThemeId(themeId) || themeId;
    if (PRESETS[resolved]) return PRESETS[resolved];
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === resolved) {
        return { name: customThemes[i].name, mode: customThemes[i].mode, brand: customThemes[i].brand || '#888' };
      }
    }
    return { name: themeId, mode: getModeForTheme(themeId), brand: '#888' };
  }

  // 推断主题的明暗模式：预设 → 旧 ID 映射 → v1 旧 ID → 自定义主题 → 默认亮色
  function getModeForTheme(themeId) {
    if (!themeId) return 'light';
    if (PRESETS[themeId]) return PRESETS[themeId].mode;
    var resolved = resolveThemeId(themeId);
    if (resolved && PRESETS[resolved]) return PRESETS[resolved].mode;
    if (LEGACY_MODE[themeId]) return LEGACY_MODE[themeId];
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === themeId) return customThemes[i].mode;
    }
    return 'light';
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

  function isLightMode() { return state.mode === 'light'; }

  // ===== 应用主题 =====
  function applyTheme(themeId) {
    // 保留原始主题 ID（含旧主题 ID），旧 ID 视觉由 tokens.css / 页面旧样式层继续渲染；
    // LEGACY_THEME_MAP 仅用于明暗模式推断，不再改写主题本身。
    if (!themeId) themeId = 'dawn';
    state.theme = themeId;
    state.mode = getModeForTheme(themeId);

    // crossfade flag
    var root = document.documentElement;
    root.setAttribute('data-theme-transitioning', 'true');
    setTimeout(function () { root.removeAttribute('data-theme-transitioning'); }, 500);

    root.setAttribute('data-theme', themeId);
    if (document.body) {
      document.body.classList.toggle('light-theme', state.mode === 'light');
      document.body.classList.toggle('dark-theme',  state.mode === 'dark');
      document.body.setAttribute('data-theme-bg', 'true');
    }

    // 自定义主题：把 primitives 写到 :root
    var custom = null;
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === themeId) { custom = customThemes[i]; break; }
    }
    if (custom && custom.primitives) {
      applyCustomPrimitives(custom.primitives);
    } else {
      clearCustomPrimitives();
    }

    // 通知页面旧主题层（如 index.html 的旧下拉面板 / 动态特效），保持两套 UI 一致
    try {
      window.dispatchEvent(new CustomEvent('starlearn:theme-applied', {
        detail: { theme: state.theme, mode: state.mode }
      }));
    } catch (e) {}
  }

  function applyCustomPrimitives(prim) {
    var root = document.documentElement;
    PRIMITIVE_KEYS.forEach(function (k) {
      if (prim[k] !== undefined && prim[k] !== '') {
        root.style.setProperty('--' + k, prim[k]);
      } else {
        root.style.removeProperty('--' + k);
      }
    });
  }

  function clearCustomPrimitives() {
    var root = document.documentElement;
    PRIMITIVE_KEYS.forEach(function (k) { root.style.removeProperty('--' + k); });
  }

  function setMode(mode) {
    if (mode !== 'light' && mode !== 'dark') return;
    state.mode = mode;
    var themes = getThemesForMode(mode);
    if (themes.indexOf(state.theme) === -1) {
      state.theme = themes[0] || 'dawn';
    }
    applyTheme(state.theme);
    saveState();
  }

  function setTheme(themeId) {
    applyTheme(themeId);
    saveState();
  }

  // 旧页面（如 index.html 旧下拉面板）已有自己的视觉层：
  // 只把主题 ID 纳入 v4 状态并持久化/同步到服务器，不重新应用视觉
  function adoptTheme(themeId) {
    if (!themeId) return;
    state.theme = themeId;
    state.mode = getModeForTheme(themeId);
    saveState();
  }

  function toggleMode() {
    setMode(state.mode === 'light' ? 'dark' : 'light');
  }

  // ===== 壁纸 =====
  function ensureBgContainer() {
    if (bgContainer && document.body.contains(bgContainer)) return bgContainer;
    bgContainer = document.getElementById('theme-bg');
    if (!bgContainer) {
      bgContainer = document.createElement('div');
      bgContainer.id = 'theme-bg';
      bgContainer.innerHTML =
        '<div class="theme-bg-color"></div>' +
        '<div class="theme-bg-image"></div>' +
        '<video class="theme-bg-video" autoplay loop muted playsinline></video>' +
        '<div class="theme-bg-overlay"></div>';
      document.body.insertBefore(bgContainer, document.body.firstChild);
    }
    videoEl = bgContainer.querySelector('.theme-bg-video');
    return bgContainer;
  }

  function getWallpaper(id) {
    for (var i = 0; i < WALLPAPERS.length; i++) {
      if (WALLPAPERS[i].id === id) return WALLPAPERS[i];
    }
    return WALLPAPERS[0];
  }

  function applyWallpaper() {
    var wp = getWallpaper(state.wallpaperId);
    var container = ensureBgContainer();
    var root = document.documentElement;

    // 公共变量
    root.style.setProperty('--theme-brightness', state.brightness + '%');
    root.style.setProperty('--theme-blur', state.blur + 'px');
    root.style.setProperty('--theme-text-contrast', state.textContrast + '%');

    if (wp.type === 'none') {
      root.style.setProperty('--theme-bg-image', 'none');
      root.style.setProperty('--theme-bg-video', 'none');
      container.setAttribute('data-mode', 'color');
      if (videoEl) {
        videoEl.pause();
        videoEl.removeAttribute('src');
        videoEl.load();
      }
    } else if (wp.type === 'static') {
      root.style.setProperty('--theme-bg-image', 'url("' + wp.url + '")');
      root.style.setProperty('--theme-bg-video', 'none');
      container.setAttribute('data-mode', 'image');
      if (videoEl) {
        videoEl.pause();
        videoEl.removeAttribute('src');
        videoEl.load();
      }
    } else if (wp.type === 'dynamic') {
      root.style.setProperty('--theme-bg-image', 'none');
      root.style.setProperty('--theme-bg-video', 'url("' + wp.url + '")');
      container.setAttribute('data-mode', 'video');
      if (videoEl) {
        if (videoEl.getAttribute('src') !== wp.url) {
          videoEl.src = wp.url;
        }
        var p = videoEl.play();
        if (p && typeof p.catch === 'function') p.catch(function () {});
      }
    }
  }

  function setWallpaper(wpId) {
    state.wallpaperId = wpId;
    applyWallpaper();
    saveState();
  }

  function setBrightness(v) {
    state.brightness = numOr(v, 100);
    document.documentElement.style.setProperty('--theme-brightness', state.brightness + '%');
    saveState();
  }

  function setBlur(v) {
    state.blur = numOr(v, 0);
    document.documentElement.style.setProperty('--theme-blur', state.blur + 'px');
    saveState();
  }

  function setTextContrast(v) {
    state.textContrast = numOr(v, 0);
    document.documentElement.style.setProperty('--theme-text-contrast', state.textContrast + '%');
    saveState();
  }

  function restoreDefaults() {
    state.wallpaperId = 'default';
    state.brightness = 100;
    state.blur = 0;
    state.textContrast = 0;
    applyWallpaper();
    saveState();
  }

  function applyAll() {
    ensureBgContainer();
    applyTheme(state.theme);
    applyWallpaper();
  }

  // ===== 自定义主题 CRUD =====
  function createCustomTheme(name, mode, primitives) {
    var id = 'custom-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
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
        if (state.theme === id) applyCustomPrimitives(primitives);
        return true;
      }
    }
    return false;
  }

  function deleteCustomTheme(id) {
    customThemes = customThemes.filter(function (t) { return t.id !== id; });
    saveCustomThemes();
    if (state.theme === id) setTheme(state.mode === 'light' ? 'dawn' : 'midnight');
  }

  function exportTheme(themeId) {
    var resolved = resolveThemeId(themeId) || 'dawn';
    var info = getThemeInfo(resolved);
    var primitives = {};
    if (PRESETS[resolved]) {
      var root = document.documentElement;
      PRIMITIVE_KEYS.forEach(function (k) {
        var v = getComputedStyle(root).getPropertyValue('--' + k).trim();
        if (v) primitives[k] = v;
      });
    } else {
      for (var i = 0; i < customThemes.length; i++) {
        if (customThemes[i].id === resolved) {
          primitives = customThemes[i].primitives;
          break;
        }
      }
    }
    var payload = {
      version: 4,
      type: 'starlearn-theme',
      theme: { name: info.name, mode: info.mode, primitives: primitives }
    };
    var blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'starlearn-theme-' + resolved + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function importTheme(fileInput) {
    var file = fileInput.files && fileInput.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      try {
        var data = JSON.parse(e.target.result);
        if (data.type !== 'starlearn-theme' || !data.theme || !data.theme.primitives) {
          toast('无效的主题文件格式', 'error');
          return;
        }
        if (customThemes.some(function (t) { return t.name === data.theme.name; })) {
          toast('同名主题已存在，已跳过', 'warning');
          return;
        }
        createCustomTheme(data.theme.name, data.theme.mode || 'light', data.theme.primitives);
        toast('主题「' + data.theme.name + '」导入成功', 'success');
        if (window.__themeModalRefresh) window.__themeModalRefresh();
      } catch (err) {
        toast('主题文件解析失败', 'error');
      }
    };
    reader.readAsText(file);
  }

  function toast(msg, level) {
    if (window.Toast) {
      var fn = window.Toast[level === 'error' ? 'error' : level === 'warning' ? 'warning' : level === 'info' ? 'info' : 'ok'];
      if (typeof fn === 'function') return fn(msg);
    }
    console.log('[Theme]', msg);
  }

  // ===== 后端同步 =====
  function getUserId() {
    if (window.Auth && window.Auth.me && window.Auth.me.id) return window.Auth.me.id;
    if (window.__currentUserId) return window.__currentUserId;
    // index.html 未加载 auth.js，只能从 localStorage 兜底读用户 ID：
    // xs_user / sp_user（auth.js 写入）/ starlearn_user（login.js 写入）均为 {id, ...}
    var keys = ['xs_user', 'sp_user', 'starlearn_user'];
    for (var i = 0; i < keys.length; i++) {
      try {
        var u = JSON.parse(localStorage.getItem(keys[i]) || 'null');
        if (u && u.id) return u.id;
      } catch (e) {}
    }
    return null;
  }

  function scheduleSync() {
    if (syncTimer) clearTimeout(syncTimer);
    syncTimer = setTimeout(syncToServer, SYNC_DEBOUNCE);
  }

  function syncToServer() {
    var uid = getUserId();
    if (!uid) return; // 未登录跳过
    var payload = {
      userId: uid,
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
    }).catch(function () {});
  }

  function loadFromServer() {
    var uid = getUserId();
    if (!uid) return Promise.resolve(null);
    return fetch('/api/user/theme/sync?user_id=' + encodeURIComponent(uid))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.theme) {
          state = migrateState({
            mode: data.mode,
            theme: data.theme,
            wallpaperId: data.wallpaper && data.wallpaper.id,
            brightness: data.wallpaper && data.wallpaper.brightness,
            blur: data.wallpaper && data.wallpaper.blur,
            textContrast: data.wallpaper && data.wallpaper.textContrast
          });
          if (Array.isArray(data.customThemes)) {
            customThemes = data.customThemes;
            try { localStorage.setItem(CUSTOM_KEY, JSON.stringify(customThemes)); } catch (e) {}
          }
          try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
          applyAll();
        }
        return data;
      }).catch(function () { return null; });
  }

  // ===== 设置弹窗 =====
  function buildFab() {
    if (document.getElementById('app-theme-fab') || document.getElementById('theme-settings-btn')) return;
    var btn = document.createElement('button');
    btn.id = 'app-theme-fab';
    btn.type = 'button';
    btn.setAttribute('aria-label', '主题设置');
    btn.title = '主题设置';
    btn.innerHTML =
      '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">' +
        '<circle cx="12" cy="12" r="3"/>' +
        '<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke-linecap="round"/>' +
      '</svg>';
    btn.addEventListener('click', openModal);
    document.body.appendChild(btn);
  }

  function bindExistingTriggers() {
    var existing = document.getElementById('theme-settings-btn');
    if (existing && !existing.__themeBound) {
      existing.addEventListener('click', openModal);
      existing.__themeBound = true;
    }
  }

  function openModal() {
    closeModal();
    var overlay = document.createElement('div');
    overlay.id = 'theme-settings-modal';
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeModal(); });
    document.addEventListener('keydown', escClose);

    var modal = document.createElement('div');
    modal.className = 'tsm-modal';
    overlay.appendChild(modal);

    // Header
    var header = document.createElement('div');
    header.className = 'tsm-header';
    header.innerHTML = '<h2 class="tsm-title">主题设置</h2><button class="tsm-close" aria-label="关闭">×</button>';
    header.querySelector('.tsm-close').addEventListener('click', closeModal);
    modal.appendChild(header);

    // ----- 模式 -----
    var modeSec = section('模式');
    var modeRow = el('div', 'tsm-mode-toggle');
    var lightBtn = el('button', 'tsm-mode-btn', '☀ 亮色');
    var darkBtn  = el('button', 'tsm-mode-btn', '☾ 暗色');
    function syncModeBtns() {
      lightBtn.classList.toggle('active', state.mode === 'light');
      darkBtn .classList.toggle('active', state.mode === 'dark');
    }
    lightBtn.addEventListener('click', function () { setMode('light'); syncModeBtns(); renderThemes(); });
    darkBtn .addEventListener('click', function () { setMode('dark');  syncModeBtns(); renderThemes(); });
    syncModeBtns();
    modeRow.appendChild(lightBtn); modeRow.appendChild(darkBtn);
    modeSec.appendChild(modeRow);
    modal.appendChild(modeSec);

    // ----- 配色方案 -----
    var themeSec = section('配色方案');
    var themeGrid = el('div', 'tsm-theme-cards');
    themeSec.appendChild(themeGrid);
    modal.appendChild(themeSec);

    function renderThemes() {
      themeGrid.innerHTML = '';
      var ids = getThemesForMode(state.mode);
      ids.forEach(function (id) {
        var info = getThemeInfo(id);
        var brand = info.brand || resolveBrandColor(id);
        var card = el('div', 'tsm-theme-card' + (state.theme === id ? ' active' : ''));
        var sw = el('div', 'tsm-swatch'); sw.style.background = brand;
        card.appendChild(sw);
        card.appendChild(el('div', 'tsm-card-name', info.name));
        if (id.indexOf('custom-') === 0) {
          var del = el('button', 'tsm-delete-custom', '🗑');
          del.title = '删除自定义主题';
          del.addEventListener('click', function (e) {
            e.stopPropagation();
            if (confirm('删除主题「' + info.name + '」？')) {
              deleteCustomTheme(id);
              renderThemes();
            }
          });
          card.appendChild(del);
        }
        card.addEventListener('click', function () { setTheme(id); renderThemes(); });
        themeGrid.appendChild(card);
      });
    }
    renderThemes();

    // ----- 品牌色 -----
    var brandSec = section('品牌色（覆盖当前主题）');
    var brandRow = el('div', 'tsm-brand-row');
    BRAND_SWATCHES.forEach(function (bs) {
      var b = el('button', 'tsm-brand-swatch');
      b.style.background = bs.hex; b.title = bs.label;
      b.addEventListener('click', function () {
        document.documentElement.style.setProperty('--_brand-h', bs.h);
        document.documentElement.style.setProperty('--_brand-c', bs.c);
        document.documentElement.style.setProperty('--_brand-l', bs.l + '%');
      });
      brandRow.appendChild(b);
    });
    var picker = el('input', 'tsm-brand-input'); picker.type = 'color';
    picker.addEventListener('input', function () {
      var hcl = hexToHcl(picker.value);
      document.documentElement.style.setProperty('--_brand-h', hcl.h);
      document.documentElement.style.setProperty('--_brand-c', hcl.c);
      document.documentElement.style.setProperty('--_brand-l', hcl.l + '%');
    });
    brandRow.appendChild(picker);
    brandSec.appendChild(brandRow);
    modal.appendChild(brandSec);

    // ----- 壁纸 -----
    var wpSec = section('壁纸');
    var wpGrid = el('div', 'tsm-wp-grid');
    function renderWps() {
      wpGrid.innerHTML = '';
      WALLPAPERS.forEach(function (wp) {
        var card = el('div', 'tsm-wp-card' + (state.wallpaperId === wp.id ? ' active' : ''));
        if (wp.preview && wp.type !== 'dynamic') {
          var img = el('img', 'tsm-wp-thumb'); img.src = wp.preview; img.alt = wp.title; img.loading = 'lazy';
          card.appendChild(img);
        } else if (wp.preview && wp.type === 'dynamic') {
          var v = el('video', 'tsm-wp-thumb'); v.src = wp.preview; v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true;
          card.appendChild(v);
        } else {
          card.appendChild(el('div', 'tsm-wp-placeholder', '✦'));
        }
        if (wp.type === 'dynamic') card.appendChild(el('div', 'tsm-wp-badge', '动态'));
        else if (wp.type === 'static') card.appendChild(el('div', 'tsm-wp-badge', '静态'));
        card.appendChild(el('div', 'tsm-wp-name', wp.title));
        card.addEventListener('click', function () { setWallpaper(wp.id); renderWps(); });
        wpGrid.appendChild(card);
      });
    }
    renderWps();
    wpSec.appendChild(wpGrid);
    modal.appendChild(wpSec);

    // ----- 滑块（仅在壁纸非 default 时显示更多） -----
    var slidersSec = section('外观调节');
    var sBright = slider('亮度', state.brightness, 10, 100, 1, function (v) { setBrightness(v); }, '%');
    var sBlur   = slider('模糊', state.blur, 0, 30, 1, function (v) { setBlur(v); }, 'px');
    var sContrast = slider('文字对比蒙版', state.textContrast, 0, 80, 1, function (v) { setTextContrast(v); }, '%');
    slidersSec.appendChild(sBright.row);
    slidersSec.appendChild(sBlur.row);
    slidersSec.appendChild(sContrast.row);
    modal.appendChild(slidersSec);

    // ----- 操作区 -----
    var actions = el('div', 'tsm-actions');

    var resetBtn = el('button', 'tsm-btn', '恢复默认');
    resetBtn.addEventListener('click', function () {
      restoreDefaults();
      renderWps();
      sBright.set(state.brightness);
      sBlur.set(state.blur);
      sContrast.set(state.textContrast);
    });

    var importInput = el('input'); importInput.type = 'file'; importInput.accept = '.json'; importInput.style.display = 'none';
    importInput.addEventListener('change', function () { importTheme(importInput); importInput.value = ''; });
    var importBtn = el('button', 'tsm-btn', '导入');
    importBtn.addEventListener('click', function () { importInput.click(); });

    var exportBtn = el('button', 'tsm-btn', '导出');
    exportBtn.addEventListener('click', function () { exportTheme(state.theme); });

    var advanced = el('a', 'tsm-btn', '高级编辑 →');
    advanced.href = '/settings.html';
    advanced.style.textDecoration = 'none';

    actions.appendChild(resetBtn);
    actions.appendChild(importBtn);
    actions.appendChild(exportBtn);
    actions.appendChild(el('div', 'tsm-spacer'));
    actions.appendChild(advanced);
    actions.appendChild(importInput);
    modal.appendChild(actions);

    document.body.appendChild(overlay);

    // 暴露给外部刷新（导入主题后用）
    window.__themeModalRefresh = function () { renderThemes(); renderWps(); };
  }

  function closeModal() {
    var m = document.getElementById('theme-settings-modal');
    if (m) m.remove();
    document.removeEventListener('keydown', escClose);
    window.__themeModalRefresh = null;
  }

  function escClose(e) { if (e.key === 'Escape') closeModal(); }

  // ----- DOM 工具 -----
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function section(label) {
    var s = el('div', 'tsm-section');
    s.appendChild(el('div', 'tsm-section-label', label));
    return s;
  }

  function slider(label, value, min, max, step, onChange, unit) {
    var row = el('div', 'tsm-slider-row');
    var lab = el('div', 'tsm-slider-label');
    var lname = el('span', null, label);
    var lval = el('span', null, value + (unit || ''));
    lab.appendChild(lname); lab.appendChild(lval);
    var input = el('input', 'tsm-slider');
    input.type = 'range'; input.min = min; input.max = max; input.step = step; input.value = value;
    input.addEventListener('input', function () {
      lval.textContent = input.value + (unit || '');
      onChange(Number(input.value));
    });
    row.appendChild(lab); row.appendChild(input);
    return { row: row, set: function (v) { input.value = v; lval.textContent = v + (unit || ''); } };
  }

  // ----- 颜色辅助 -----
  function resolveBrandColor(id) {
    if (PRESETS[id] && PRESETS[id].brand) return PRESETS[id].brand;
    for (var i = 0; i < customThemes.length; i++) {
      if (customThemes[i].id === id) {
        var p = customThemes[i].primitives || {};
        if (p['_brand-h'] != null && p['_brand-c'] != null && p['_brand-l'] != null) {
          return 'oklch(' + p['_brand-l'] + ' ' + p['_brand-c'] + ' ' + p['_brand-h'] + ')';
        }
      }
    }
    return '#888';
  }

  function hexToHcl(hex) {
    var r = parseInt(hex.slice(1, 3), 16) / 255;
    var g = parseInt(hex.slice(3, 5), 16) / 255;
    var b = parseInt(hex.slice(5, 7), 16) / 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b);
    var L = (max + min) / 2;
    var d = max - min, H = 0, S = 0;
    if (d !== 0) {
      S = d / (1 - Math.abs(2 * L - 1));
      if (max === r) H = ((g - b) / d) % 6;
      else if (max === g) H = (b - r) / d + 2;
      else H = (r - g) / d + 4;
      H = Math.round(H * 60); if (H < 0) H += 360;
    }
    var C = Math.min(Math.round(S * 35) / 100, 0.32);
    return { h: H, c: C, l: Math.round(L * 100) };
  }

  // ===== Init =====
  function init() {
    ensureBgContainer();
    applyAll();
    bindExistingTriggers();
    buildFab();
    loadFromServer().then(function () {
      // 等 Auth.me 加载完再同步一次（首次进入时 Auth 可能还没就绪）
      if (!getUserId()) {
        setTimeout(loadFromServer, 1500);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ===== 公开 API（与旧 v3 API 完全兼容） =====
  window.StarTheme = {
    version: 4,
    WALLPAPERS: WALLPAPERS,
    PRESETS: PRESETS,
    LEGACY_THEME_MAP: LEGACY_THEME_MAP,
    BRAND_SWATCHES: BRAND_SWATCHES,
    getState: function () { return JSON.parse(JSON.stringify(state)); },
    getCustomThemes: function () { return customThemes.slice(); },
    setMode: setMode,
    setTheme: setTheme,
    adoptTheme: adoptTheme,
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
    openThemeModal: openModal,
    openModal: openModal,
    closeModal: closeModal,
    createCustomTheme: createCustomTheme,
    updateCustomTheme: updateCustomTheme,
    deleteCustomTheme: deleteCustomTheme,
    exportTheme: exportTheme,
    importTheme: importTheme,
    loadFromServer: loadFromServer,
    syncToServer: syncToServer,
    resolveThemeId: resolveThemeId
  };
})();
