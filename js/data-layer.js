/**
 * 星识 (Star-Learn) 统一数据访问层
 *
 * 所有用户数据统一经过此模块读写，确保：
 * 1. localStorage 作为即时缓存（用户操作立即可见）
 * 2. 服务端数据库作为持久化存储（登录后自动同步）
 * 3. 离线可用（服务器不可达时仍可使用缓存数据）
 *
 * 使用方法：
 *   // 读取
 *   const plants = await StarData.getPlants();
 *   // 保存
 *   await StarData.setPlants(plantData, seeds);
 *   // 登录后全量加载
 *   await StarData.loadAllFromServer(userId);
 */
window.StarData = (function () {
  const API_URL = window.location.origin;

  // 当前登录用户ID（null 表示未登录或游客）
  let currentUserId = null;

  // 防抖定时器（批量保存用）
  const _debounceTimers = {};
  const DEBOUNCE_MS = 2000;

  // 是否已初始化
  let _initialized = false;

  // ========================
  // 内部工具函数
  // ========================

  function _getUserId() {
    if (currentUserId) return currentUserId;
    try {
      const user = JSON.parse(localStorage.getItem("starlearn_user") || "{}");
      currentUserId = user.id || null;
    } catch (e) {
      currentUserId = null;
    }
    return currentUserId;
  }

  function _setUserId(id) {
    currentUserId = id;
  }

  /** 异步POST到服务端，失败不抛出 */
  async function _post(url, body) {
    const uid = _getUserId();
    if (!uid) return; // 未登录不保存
    try {
      const res = await fetch(`${API_URL}${url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: uid, ...body }),
      });
      return await res.json();
    } catch (e) {
      console.warn("[StarData] Server save failed:", url, e.message);
    }
  }

  /** 异步从服务端GET，失败返回null */
  async function _get(url) {
    const uid = _getUserId();
    if (!uid) return null;
    try {
      const res = await fetch(`${API_URL}${url}/${uid}`);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.warn("[StarData] Server load failed:", url, e.message);
      return null;
    }
  }

  /** 本地读 */
  function _localGet(key) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  /** 本地写 */
  function _localSet(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.warn("[StarData] localStorage write failed:", key);
    }
  }

  // ========================
  // 公开 API
  // ========================

  const api = {
    /** 初始化：设置当前用户ID */
    init(userId) {
      _setUserId(userId);
      _initialized = true;
    },

    /** 获取当前用户ID */
    getUserId() {
      return _getUserId();
    },

    /** 是否已登录（有真实userId） */
    isLoggedIn() {
      return !!_getUserId();
    },

    // ========================================
    // 全量加载（登录后调用）
    // ========================================

    /**
     * 从服务端加载所有用户数据并写入 localStorage 缓存
     * 优先调用 /api/login-v2 返回的数据直接注入，
     * 或调用 /api/user/state/{id}
     */
    async loadAllFromServer(userIdOrLoginData) {
      let state;

      if (typeof userIdOrLoginData === "object" && userIdOrLoginData !== null) {
        // 传入的是 login-v2 返回的完整数据
        state = userIdOrLoginData;
        _setUserId(state.userId);
      } else if (typeof userIdOrLoginData === "number") {
        _setUserId(userIdOrLoginData);
        const res = await _get("/api/user/state");
        if (!res || !res.success) return false;
        state = res;
      } else {
        return false;
      }

      // 将服务端数据写入 localStorage 缓存
      if (state.preferences) _localSet("starlearn_preferences", state.preferences);
      if (state.garden) {
        const gardenData = state.gardenData || state.garden_data || state.garden || {};
        if (gardenData) _localSet("starlearn_plants", gardenData);
        if (state.seeds !== undefined) localStorage.setItem("starlearn_seeds", String(state.seeds));
      }
      if (state.pet) {
        if (state.pet.pet || state.petData) _localSet("starlearn_pet", state.pet.pet || state.petData);
        if (state.pet.pet_game || state.petGameData) _localSet("pixelPetGame", state.pet.pet_game || state.petGameData);
      }
      if (state.achievements) _localSet("starlearn_achievements", state.achievements);
      if (state.stats) _localSet("starlearn_stats", state.stats);
      if (state.notifications) {
        const notifs = state.notifications.notifications || state.notifications;
        if (notifs) _localSet("starlearn_notifications", notifs);
        if (state.notifications.last_update_time) {
          localStorage.setItem("starlearn_notifications_last_update", String(state.notifications.last_update_time));
        }
      }
      if (state.settings) {
        const s = state.settings;
        if (s.settings) _localSet("starlearn_settings", s.settings);
        if (s.weather_city) localStorage.setItem("starlearn_weather_city", s.weather_city);
        if (s.floating_alarm_x != null && s.floating_alarm_y != null) {
          _localSet("floatingAlarmPosition", { x: s.floating_alarm_x, y: s.floating_alarm_y });
        }
        if (s.hub_theme) localStorage.setItem("hub-theme", s.hub_theme);
      }
      if (state.codingState || state.coding_state) {
        _localSet("starlearn_unified_coding_state", state.codingState || state.coding_state);
      }
      if (state.weatherCache || state.weather_cache) {
        _localSet("starlearn_weather", state.weatherCache || state.weather_cache);
      }
      if (state.focusHistory || state.focus_history) {
        _localSet("starlearn_focus_recent", state.focusHistory || state.focus_history);
      }
      if (state.ecoData || state.eco_data) {
        _localSet("eco_data", state.ecoData || state.eco_data);
      }
      if (state.projects) _localSet("architecture_projects", state.projects);
      if (state.calendarEvents || state.calendar_events) {
        _localSet("blueprint_calendar_events", state.calendarEvents || state.calendar_events);
      }

      _initialized = true;
      console.log("[StarData] Full state loaded from server for user", _getUserId());
      return true;
    },

    // ========================================
    // 花园 / 植物
    // ========================================

    async getPlants() {
      const local = _localGet("starlearn_plants");
      if (local) return local;
      const res = await _get("/api/garden/load");
      if (res && res.success && res.gardenData) {
        _localSet("starlearn_plants", res.gardenData);
        if (res.seeds !== undefined) localStorage.setItem("starlearn_seeds", String(res.seeds));
        return res.gardenData;
      }
      return {};
    },

    async setPlants(gardenData, seeds) {
      _localSet("starlearn_plants", gardenData);
      if (seeds !== undefined) localStorage.setItem("starlearn_seeds", String(seeds));
      // 异步保存到服务端
      _post("/api/garden/save", { seeds: seeds, gardenData: gardenData });
    },

    async getSeeds() {
      const local = localStorage.getItem("starlearn_seeds");
      if (local !== null) return parseInt(local) || 0;
      const res = await _get("/api/garden/load");
      if (res && res.success) {
        const s = res.seeds || 3;
        localStorage.setItem("starlearn_seeds", String(s));
        return s;
      }
      return 3;
    },

    async setSeeds(seeds) {
      localStorage.setItem("starlearn_seeds", String(seeds));
      const gardenData = _localGet("starlearn_plants") || {};
      _post("/api/garden/save", { seeds: seeds, gardenData: gardenData });
    },

    // ========================================
    // 宠物
    // ========================================

    async getPet() {
      return _localGet("starlearn_pet") || {};
    },

    async setPet(petData) {
      _localSet("starlearn_pet", petData);
      _post("/api/pet/save", { petData: petData });
    },

    async getPetGame() {
      return _localGet("pixelPetGame") || {};
    },

    async setPetGame(gameData) {
      _localSet("pixelPetGame", gameData);
      _post("/api/pet/save", { petGameData: gameData });
    },

    /** 同时保存宠物和宠物游戏数据 */
    async setPetAll(petData, gameData) {
      if (petData) _localSet("starlearn_pet", petData);
      if (gameData) _localSet("pixelPetGame", gameData);
      _post("/api/pet/save", { petData: petData, petGameData: gameData });
    },

    // ========================================
    // 成就
    // ========================================

    async getAchievements() {
      const local = _localGet("starlearn_achievements");
      if (local) return local;
      const res = await _get("/api/achievements/load");
      if (res && res.success && res.achievementsData) {
        _localSet("starlearn_achievements", res.achievementsData);
        return res.achievementsData;
      }
      return {};
    },

    async setAchievements(data) {
      _localSet("starlearn_achievements", data);
      _post("/api/achievements/save", { achievementsData: data });
    },

    // ========================================
    // 统计数据
    // ========================================

    async getStats() {
      const local = _localGet("starlearn_stats");
      if (local) return local;
      const res = await _get("/api/stats/load");
      if (res && res.success && res.statsData) {
        _localSet("starlearn_stats", res.statsData);
        return res.statsData;
      }
      return {};
    },

    async setStats(data) {
      _localSet("starlearn_stats", data);
      _post("/api/stats/save", { statsData: data });
    },

    /** 获取单个统计值 */
    async getStat(key) {
      const stats = await this.getStats();
      return stats[key] || 0;
    },

    /** 设置单个统计值 */
    async setStat(key, value) {
      const stats = await this.getStats();
      stats[key] = value;
      await this.setStats(stats);
    },

    /** 增加单个统计值 */
    async incrementStat(key, delta = 1) {
      const stats = await this.getStats();
      stats[key] = (stats[key] || 0) + delta;
      await this.setStats(stats);
    },

    // ========================================
    // 通知
    // ========================================

    async getNotifications() {
      return _localGet("starlearn_notifications") || [];
    },

    async setNotifications(notifications) {
      _localSet("starlearn_notifications", notifications);
      const lastUpdate = Date.now();
      localStorage.setItem("starlearn_notifications_last_update", String(lastUpdate));
      _post("/api/notifications/save", { notificationsData: notifications, lastUpdateTime: lastUpdate });
    },

    async getNotificationsLastUpdate() {
      const ts = localStorage.getItem("starlearn_notifications_last_update");
      return ts ? parseInt(ts) : 0;
    },

    // ========================================
    // 设置
    // ========================================

    async getSettings() {
      return _localGet("starlearn_settings") || {};
    },

    async setSettings(settingsData) {
      _localSet("starlearn_settings", settingsData);
      _post("/api/settings/save", { settingsData: settingsData });
    },

    async getWeatherCity() {
      return localStorage.getItem("starlearn_weather_city") || "";
    },

    async setWeatherCity(city) {
      localStorage.setItem("starlearn_weather_city", city);
      _post("/api/settings/save", { weatherCity: city });
    },

    async getAlarmPosition() {
      return _localGet("floatingAlarmPosition") || { x: null, y: null };
    },

    async setAlarmPosition(x, y) {
      _localSet("floatingAlarmPosition", { x, y });
      _post("/api/settings/save", { floatingAlarmX: x, floatingAlarmY: y });
    },

    async getHubTheme() {
      return localStorage.getItem("hub-theme") || "";
    },

    async setHubTheme(theme) {
      localStorage.setItem("hub-theme", theme);
      _post("/api/settings/save", { hubTheme: theme });
    },

    // ========================================
    // 主题（系统主题）
    // ========================================

    async getTheme() {
      return localStorage.getItem("starlearn_theme") || "ocean";
    },

    async setTheme(theme) {
      localStorage.setItem("starlearn_theme", theme);
      _post("/api/user/meta", { theme: theme });
    },

    // ========================================
    // 编程语言偏好
    // ========================================

    async getPreferredLang() {
      return localStorage.getItem("starlearn_preferred_lang") || "python";
    },

    async setPreferredLang(lang) {
      localStorage.setItem("starlearn_preferred_lang", lang);
      _post("/api/user/meta", { preferredLanguage: lang });
    },

    // ========================================
    // 代理ID
    // ========================================

    async getAgent() {
      return localStorage.getItem("starlearn_agent") || "";
    },

    async setAgent(agentId) {
      localStorage.setItem("starlearn_agent", agentId);
      _post("/api/user/meta", { lastAgentId: agentId });
    },

    // ========================================
    // 偏好设置
    // ========================================

    async getPreferences() {
      return _localGet("starlearn_preferences") || {};
    },

    async setPreferences(prefs) {
      _localSet("starlearn_preferences", prefs);
      const uid = _getUserId();
      if (uid) {
        try {
          await fetch(`${API_URL}/api/user/preferences`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ userId: uid, preferences: prefs }),
          });
        } catch (e) {
          console.warn("[StarData] Preferences save failed:", e.message);
        }
      }
    },

    // ========================================
    // 心流偏好
    // ========================================

    async getFlowPrefs() {
      return _localGet("starlearn_flow_prefs") || {};
    },

    async setFlowPrefs(prefs) {
      _localSet("starlearn_flow_prefs", prefs);
      // 合并到 preferences 一起保存
      const allPrefs = await this.getPreferences();
      allPrefs.flowPrefs = prefs;
      await this.setPreferences(allPrefs);
    },

    // ========================================
    // 闪卡时长
    // ========================================

    async getFlashcardDuration() {
      return localStorage.getItem("starlearn_flashcard_duration") || "180";
    },

    async setFlashcardDuration(duration) {
      localStorage.setItem("starlearn_flashcard_duration", duration);
      const prefs = await this.getPreferences();
      prefs.flashcardDuration = duration;
      await this.setPreferences(prefs);
    },

    // ========================================
    // 侧边栏偏好
    // ========================================

    async getSidebarPrefs() {
      return _localGet("starlearn_sidebar_prefs") || {};
    },

    async setSidebarPrefs(prefs) {
      _localSet("starlearn_sidebar_prefs", prefs);
      const allPrefs = await this.getPreferences();
      allPrefs.sidebarPrefs = prefs;
      await this.setPreferences(allPrefs);
    },

    // ========================================
    // 专注历史
    // ========================================

    async getFocusHistory() {
      return _localGet("starlearn_focus_recent") || [];
    },

    async setFocusHistory(items) {
      _localSet("starlearn_focus_recent", items);
      _post("/api/focus/save", { focusData: items });
    },

    // ========================================
    // 编程状态
    // ========================================

    async getCodingState() {
      return _localGet("starlearn_unified_coding_state") || _localGet("starlearn_coding_state") || {};
    },

    async setCodingState(state) {
      _localSet("starlearn_unified_coding_state", state);
      _post("/api/coding-state/save", { codingStateData: state });
    },

    // ========================================
    // 天气缓存
    // ========================================

    async getWeatherCache() {
      return _localGet("starlearn_weather") || null;
    },

    async setWeatherCache(data) {
      _localSet("starlearn_weather", data);
      _post("/api/weather/save", { weatherData: data });
    },

    async clearWeatherCache() {
      localStorage.removeItem("starlearn_weather");
      const uid = _getUserId();
      if (uid) {
        try {
          await fetch(`${API_URL}/api/weather/clear/${uid}`, { method: "DELETE" });
        } catch (e) {
          console.warn("[StarData] Weather clear failed:", e.message);
        }
      }
    },

    // ========================================
    // 生态数据
    // ========================================

    async getEcoData() {
      return _localGet("eco_data") || {};
    },

    async setEcoData(data) {
      _localSet("eco_data", data);
      _post("/api/eco/save", { ecoData: data });
    },

    // ========================================
    // 架构项目
    // ========================================

    async getProjects() {
      return _localGet("architecture_projects") || [];
    },

    async setProjects(data) {
      _localSet("architecture_projects", data);
      _post("/api/projects/save", { projectsData: data });
    },

    // ========================================
    // 日历事件
    // ========================================

    async getCalendarEvents() {
      return _localGet("blueprint_calendar_events") || {};
    },

    async setCalendarEvents(data) {
      _localSet("blueprint_calendar_events", data);
      _post("/api/calendar-events/save", { eventsData: data });
    },

    // ========================================
    // 已完成概念
    // ========================================

    async getCompletedConcepts() {
      return _localGet("completedConcepts") || [];
    },

    async setCompletedConcepts(concepts) {
      _localSet("completedConcepts", concepts);
      // 合并到 focus history 一起保存
      _post("/api/focus/save", { focusData: concepts });
    },

    // ========================================
    // 用户基本信息
    // ========================================

    getUserSync() {
      return _localGet("starlearn_user") || { name: "同学", avatar: "", currentTask: "大数据导论" };
    },

    setUserSync(userData) {
      _localSet("starlearn_user", userData);
      if (userData.id) _setUserId(userData.id);
    },

    // ========================================
    // 评估数据
    // ========================================

    async getEvaluation() {
      return _localGet("starlearn_evaluation") || {};
    },

    async setEvaluation(data) {
      _localSet("starlearn_evaluation", data);
    },

    // ========================================
    // 学习上下文（sessionStorage，不同步到服务器）
    // ========================================

    getLearningContext() {
      try {
        const raw = sessionStorage.getItem("currentLearningContext");
        return raw || null;
      } catch (e) {
        return null;
      }
    },

    setLearningContext(ctx) {
      try {
        sessionStorage.setItem("currentLearningContext", typeof ctx === "string" ? ctx : JSON.stringify(ctx));
      } catch (e) {}
    },

    clearLearningContext() {
      try {
        sessionStorage.removeItem("currentLearningContext");
      } catch (e) {}
    },

    // ========================================
    // 学生画像（6维度）
    // ========================================

    /**
     * 更新学生画像
     * @param {string} source - 交互来源：socratic, code, chat, index, other
     * @param {object} interactionData - 交互数据
     */
    async updatePortrait(source, interactionData) {
      const uid = _getUserId();
      if (!uid) return null;
      try {
        const res = await fetch(`${API_URL}/api/profile/portrait/update`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: uid,
            source: source,
            interaction_data: interactionData
          }),
        });
        return await res.json();
      } catch (e) {
        console.warn("[StarData] Portrait update failed:", e.message);
        return null;
      }
    },

    /**
     * 获取学生画像
     */
    async getPortrait() {
      const uid = _getUserId();
      if (!uid) return null;
      try {
        const res = await fetch(`${API_URL}/api/profile/portrait/${uid}`);
        if (!res.ok) return null;
        const data = await res.json();
        return data.portrait || null;
      } catch (e) {
        console.warn("[StarData] Portrait get failed:", e.message);
        return null;
      }
    },
  };

  return api;
})();

console.log("[StarData] Data layer initialized");

/**
 * fetchSSEStream — POST-based SSE stream reader.
 *
 * Uses fetch + ReadableStream to handle POST SSE endpoints.
 * Native EventSource is NOT used because it only supports GET
 * and cannot carry complex JSON payloads or custom headers.
 *
 * @param {Object} options
 * @param {string} options.url — POST endpoint URL
 * @param {Object} options.body — JSON-serializable request body
 * @param {function} options.onEvent — callback(eventType, data)
 * @param {function} [options.onError] — callback(error)
 * @param {function} [options.onDone] — callback()
 * @returns {{ abort: function }} — controller to abort the stream
 */
window.fetchSSEStream = function ({ url, body, onEvent, onError, onDone }) {
  const controller = new AbortController();
  const parser = new SSEParser();
  parser.onEvent = onEvent;

  (async () => {
    let reader;
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE stream failed: HTTP ${response.status}`);
      }

      reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          parser.flush();
          if (onDone) onDone();
          break;
        }
        // CRITICAL: feed decoded text to parser which accumulates
        // and splits by \n\n before JSON.parse. Never parse chunks directly.
        parser.feed(decoder.decode(value, { stream: true }));
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('[fetchSSEStream] Error:', err);
      if (onError) onError(err);
    } finally {
      if (reader) {
        try { reader.releaseLock(); } catch (_) {}
      }
    }
  })();

  return {
    abort: () => controller.abort(),
  };
};

