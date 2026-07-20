/**
 * 看板娘 对话面板 — Alpine.js 全功能版 (v2)
 *
 * 功能:
 *   - SSE 流式对话 (含 Markdown 渲染 + 代码高亮)
 *   - 语音输入 (MediaRecorder + ASR) + TTS 朗读
 *   - 学习链接卡片 (来自后端 link 事件)
 *   - 主动推送横幅 (来自后端 action 事件)
 *   - 消息操作 (复制/重试/👍/👎)
 *   - 记忆浏览器 (查看/确认/删除小星对你的记忆)
 *   - 用户画像卡片 ("AI眼中的你")
 *   - 番茄钟 (25分钟专注 + 5分钟休息)
 *   - 页面感知快捷建议
 *   - 智能时间问候
 *   - 聊天历史管理 (保存/加载/清除/导出)
 *   - 每日签到 (连续打卡追踪 + 庆祝动画)
 *   - 学习统计条
 *   - 通知 Toast (面板关闭时推送)
 *   - 键盘快捷键支持
 *   - 重试失败消息
 *
 * 依赖: Alpine.js 3.14+ (CDN defer) + mascot-services.js + mascot-core.js
 */
document.addEventListener('alpine:init', () => {
  'use strict';

  // ═══════════════════════════════════════════
  // 注入面板 HTML 到 body
  // ═══════════════════════════════════════════
  const template = /*html*/`
    <div
      x-data="mascotPanel"
      x-show="showPanel"
      @mascot:kanban-clicked.window="togglePanel()"
      @keydown.escape="showPanel = false"
      @mascot:idle-detected.window="onIdle()"
      x-transition:enter="mascot-panel-enter"
      x-transition:enter-start="mascot-panel-enter-start"
      x-transition:enter-end="mascot-panel-enter-end"
      x-transition:leave="mascot-panel-leave"
      x-transition:leave-start="mascot-panel-leave-start"
      x-transition:leave-end="mascot-panel-leave-end"
      class="mascot-panel"
      style="display:none"
    >
      <!-- ════ Stats Bar ════ -->
      <div class="mascot-stats-bar" x-show="stats.visible">
        <div class="mascot-stat-item" title="连续学习天数">
          <span>🔥</span><span x-text="stats.streakDays"></span>天
        </div>
        <div class="mascot-stat-item" title="今日学习">
          <span>⏱️</span><span x-text="stats.todayMinutes"></span>分
        </div>
        <div class="mascot-stat-item" title="本周进度">
          <span>📊</span><span x-text="stats.weekProgress"></span>%
        </div>
        <div class="mascot-stat-checkin">
          <button @click="doCheckin()"
            class="mascot-checkin-btn"
            :class="{ checked: checkinDone }"
            x-text="checkinDone ? '✅ 已签到' : '📅 签到'"
          ></button>
        </div>
      </div>

      <!-- ════ Header ════ -->
      <div class="mascot-panel-header">
        <div class="mascot-panel-avatar">
          <span x-text="expressionEmoji">😊</span>
        </div>
        <div class="mascot-panel-title-row">
          <span class="mascot-panel-title">小星</span>
          <span class="mascot-panel-badge" x-text="pageContext.label" x-show="pageContext.label"></span>
        </div>
        <span class="mascot-panel-status">
          <span x-show="isThinking" class="mascot-status-thinking">思考中...</span>
          <span x-show="isRecording" class="mascot-status-recording">🎤 聆听中</span>
          <span x-show="pomodoro.active" class="mascot-status-pomodoro">
            🍅 <span x-text="pomodoroDisplay"></span>
          </span>
        </span>
        <!-- AI 模型指示器 -->
        <button @click="showAiModelSelector = !showAiModelSelector; showHeaderMenu = false"
          class="mascot-ai-model-badge"
          :title="'AI模型: ' + currentAiModel + ' (点击切换)'"
          x-text="'🤖 ' + (aiConfig && aiConfig.ai_available ? currentAiModel : '离线')"
          :class="{ offline: !(aiConfig && aiConfig.ai_available) }"></button>
        <!-- AI 模型选择下拉 -->
        <div x-show="showAiModelSelector" @click.outside="showAiModelSelector = false"
          class="mascot-ai-model-dropdown" x-transition>
          <div class="mascot-ai-model-title">🤖 选择 AI 模型</div>
          <template x-for="aiModel in aiModels" :key="aiModel.id">
            <button @click="switchAiModel(aiModel.id); showAiModelSelector = false"
              class="mascot-ai-model-option"
              :class="{ active: aiModel.id === currentAiModel, disabled: !aiModel.available }"
              :disabled="!aiModel.available">
              <span class="mascot-ai-model-provider" x-text="aiModel.provider"></span>
              <span class="mascot-ai-model-name" x-text="aiModel.name"></span>
              <span x-show="aiModel.id === currentAiModel" class="mascot-ai-model-check">✓</span>
              <span x-show="!aiModel.available" class="mascot-ai-model-unavailable">需配置</span>
            </button>
          </template>
          <div x-show="aiModels.length === 0" class="mascot-ai-model-empty">
            正在加载模型列表...
          </div>
        </div>
        <div class="mascot-panel-header-actions">
          <!-- 模型切换按钮 -->
          <button @click="showModelSelector = !showModelSelector; showHeaderMenu = false"
            class="mascot-model-switch-btn"
            :class="{ active: modelSwitching }"
            :disabled="modelSwitching"
            :title="'切换角色 (当前: ' + currentModelName + ')'">
            <span x-show="modelSwitching" class="mascot-model-spin">⏳</span>
            <span x-show="!modelSwitching">🎭</span>
          </button>
          <button @click="showHeaderMenu = !showHeaderMenu" class="mascot-header-menu-btn" title="更多">⋯</button>
          <button @click="showPanel = false" class="mascot-panel-close" title="关闭面板">&times;</button>
        </div>
        <!-- 模型选择下拉 -->
        <div x-show="showModelSelector" @click.outside="showModelSelector = false" class="mascot-model-dropdown" x-transition>
          <div class="mascot-model-dropdown-title">🎭 选择角色</div>
          <template x-for="model in availableModels" :key="model.name">
            <button
              @click="switchModel(model.name); showModelSelector = false"
              class="mascot-model-option"
              :class="{ active: model.name === currentModelName }"
              :disabled="modelSwitching">
              <span class="mascot-model-option-icon" x-text="model.name === currentModelName ? '✅' : '👤'"></span>
              <span class="mascot-model-option-name" x-text="model.name"></span>
              <span class="mascot-model-option-badge" x-show="model.name === currentModelName">当前</span>
            </button>
          </template>
        </div>
        <!-- 下拉菜单 -->
        <div x-show="showHeaderMenu" @click.outside="showHeaderMenu = false" class="mascot-dropdown" x-transition>
          <button @click="loadHistory(); showHeaderMenu = false">📥 加载历史</button>
          <button @click="saveHistory(); showHeaderMenu = false">💾 保存对话</button>
          <button @click="exportHistory(); showHeaderMenu = false">📤 导出对话</button>
          <button @click="clearHistory(); showHeaderMenu = false">🗑️ 清除对话</button>
          <hr>
          <button @click="toggleMemoryPanel(); showHeaderMenu = false">🧠 小星的记忆</button>
          <button @click="toggleProfileCard(); showHeaderMenu = false">👤 我的画像</button>
          <button @click="togglePomodoro(); showHeaderMenu = false">🍅 番茄钟</button>
        </div>
      </div>

      <!-- ════ Messages ════ -->
      <div
        class="mascot-panel-messages"
        x-ref="msgContainer"
        @scroll.debounce.50ms="onScroll()"
      >
        <!-- 空状态 -->
        <div x-show="messages.length === 0" class="mascot-empty">
          <div class="mascot-empty-icon">⭐</div>
          <p class="mascot-empty-greeting">
            <span x-text="greeting.emoji"></span>
            <span x-text="greeting.text"></span>！
          </p>
          <p x-text="greeting.sub"></p>

          <!-- 用户画像卡片 -->
          <div x-show="profileCard.visible && profileCard.data" class="mascot-profile-mini">
            <div class="mascot-profile-mini-title">🤖 AI眼中的你</div>
            <div class="mascot-profile-mini-tags">
              <template x-for="trait in profileCard.topTraits" :key="trait.label">
                <span class="mascot-profile-tag" x-text="trait.label"
                  :style="'--score:' + trait.score"></span>
              </template>
            </div>
          </div>

          <p style="margin-top:12px;font-size:13px">有什么学习问题想问我吗？</p>
          <div class="mascot-quick-actions">
            <template x-for="sugg in quickSuggestions" :key="sugg.text">
              <button @click="sendQuick(sugg.text)" class="mascot-quick-btn">
                <span x-text="sugg.icon"></span>
                <span x-text="sugg.label"></span>
              </button>
            </template>
          </div>

          <!-- 签到庆祝 -->
          <div x-show="showCheckinCelebration" class="mascot-checkin-celebration" x-transition>
            <div class="mascot-checkin-big">🎉</div>
            <p x-text="checkinMsg"></p>
          </div>
        </div>

        <!-- 消息列表 -->
        <template x-for="msg in messages" :key="msg.id">
          <div class="mascot-msg-group">
            <!-- 系统消息 -->
            <div x-show="msg.role === 'system'" class="mascot-msg mascot-msg--system" x-text="msg.content"></div>

            <!-- 用户消息 -->
            <div x-show="msg.role === 'user'" class="mascot-msg mascot-msg--user" x-text="msg.content"></div>

            <!-- 助手消息 -->
            <div x-show="msg.role === 'assistant'" class="mascot-msg-wrapper">
              <div class="mascot-msg mascot-msg--assistant" :class="{ 'mascot-msg--loading': msg.typing }">
                <span x-show="msg.typing" class="mascot-typing">
                  <span></span><span></span><span></span>
                </span>
                <span x-show="!msg.typing" x-html="renderMarkdown(msg.content)"></span>
                <!-- TTS -->
                <button x-show="!msg.typing && msg.content"
                  @click="speak(msg)" class="mascot-tts-btn"
                  :disabled="speakingId === msg.id"
                  x-text="speakingId === msg.id ? '🔊' : '🔈'"
                  title="朗读"></button>
                <!-- 错误重试 -->
                <button x-show="msg.error"
                  @click="retryMessage(msg)" class="mascot-retry-btn"
                  title="重新发送">🔄</button>
              </div>
              <!-- 消息操作栏 -->
              <div x-show="!msg.typing && msg.content && !msg.error" class="mascot-msg-actions">
                <button @click="copyMessage(msg)" class="mascot-action-btn" title="复制">
                  <span x-text="msg.copied ? '✅' : '📋'"></span>
                </button>
                <button @click="likeMessage(msg)" class="mascot-action-btn"
                  :class="{ liked: msg.liked }" title="有帮助">
                  👍<span x-show="msg.likes" x-text="msg.likes" style="font-size:10px;margin-left:2px"></span>
                </button>
                <button @click="dislikeMessage(msg)" class="mascot-action-btn"
                  :class="{ disliked: msg.disliked }" title="没帮助">👎</button>
                <button @click="retryMessage(msg)" class="mascot-action-btn" title="重新生成">🔄</button>
              </div>
            </div>

            <!-- 链接卡片 -->
            <div x-show="msg.links && msg.links.length > 0" class="mascot-link-cards">
              <template x-for="link in msg.links" :key="link.url">
                <a :href="link.url" class="mascot-link-card"
                  :class="'mascot-link-card--' + (link.type || 'internal')"
                  @click.prevent="navigateLink(link)">
                  <span class="mascot-link-card-icon" x-text="link.icon || '📚'"></span>
                  <div class="mascot-link-card-body">
                    <div class="mascot-link-card-title" x-text="link.title"></div>
                    <div class="mascot-link-card-desc" x-text="link.description || ''"></div>
                  </div>
                  <span class="mascot-link-card-arrow">→</span>
                </a>
              </template>
            </div>

            <!-- 主动推送横幅 -->
            <div x-show="msg.actions && msg.actions.length > 0" class="mascot-action-banners">
              <template x-for="action in msg.actions" :key="action.title">
                <div class="mascot-action-banner" :class="'mascot-action-banner--' + (action.priority || 'normal')">
                  <span class="mascot-action-banner-icon">
                    <span x-show="action.priority === 'high' || action.priority === 'critical'">⚠️</span>
                    <span x-show="!action.priority || action.priority === 'normal'">💡</span>
                  </span>
                  <div class="mascot-action-banner-body">
                    <strong x-text="action.title"></strong>
                    <span x-text="action.content"></span>
                  </div>
                  <button x-show="action.action_label"
                    @click="handleProactiveAction(action)" class="mascot-action-banner-btn"
                    x-text="action.action_label"></button>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- ════ Pomodoro Timer Bar ════ -->
      <div x-show="pomodoro.active" class="mascot-pomodoro-bar" :class="{ 'mascot-pomodoro--break': pomodoro.isBreak }">
        <span class="mascot-pomodoro-icon">🍅</span>
        <span class="mascot-pomodoro-label" x-text="pomodoro.isBreak ? '休息' : '专注'"></span>
        <span class="mascot-pomodoro-time" x-text="pomodoroDisplay"></span>
        <span class="mascot-pomodoro-sessions" x-text="'已完成 ' + pomodoro.sessions + ' 轮'"></span>
        <button @click="stopPomodoro()" class="mascot-pomodoro-stop">✕</button>
      </div>

      <!-- ════ Memory Browser Sub-Panel ════ -->
      <div x-show="showMemoryPanel" class="mascot-subpanel" x-transition>
        <div class="mascot-subpanel-header">
          <span>🧠 小星的记忆</span>
          <button @click="showMemoryPanel = false" class="mascot-subpanel-close">&times;</button>
        </div>
        <div class="mascot-subpanel-body">
          <div x-show="memoryLoading" class="mascot-subpanel-loading">加载中...</div>
          <div x-show="!memoryLoading && memories.length === 0" class="mascot-subpanel-empty">
            小星还没有关于你的记忆，多聊聊天吧~
          </div>
          <template x-for="mem in memories" :key="mem.id">
            <div class="mascot-memory-item" :class="{ 'mascot-memory--confirmed': mem.confirmed }">
              <span class="mascot-memory-type" x-text="typeLabel(mem.memory_type)"></span>
              <span class="mascot-memory-content" x-text="mem.content"></span>
              <div class="mascot-memory-actions">
                <button @click="confirmMemoryItem(mem)" class="mascot-memory-btn"
                  :class="{ confirmed: mem.confirmed }"
                  x-text="mem.confirmed ? '✓' : '确认'" title="确认这条记忆"></button>
                <button @click="deleteMemoryItem(mem)" class="mascot-memory-btn delete" title="删除">✕</button>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- ════ Input Row ════ -->
      <div class="mascot-panel-input-row">
        <button @click="toggleVoice()"
          class="mascot-panel-mic"
          :class="{ recording: isRecording }"
          :disabled="isThinking"
          title="语音输入">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </button>
        <!-- 番茄钟快捷按钮 -->
        <button @click="togglePomodoro()"
          class="mascot-panel-pomodoro-btn"
          :class="{ active: pomodoro.active }"
          :disabled="isThinking"
          title="番茄钟">🍅</button>
        <input type="text" class="mascot-panel-input"
          x-model="inputText" x-ref="input"
          placeholder="输入消息，或点击麦克风说话..."
          @keydown.enter="sendMessage()"
          :disabled="isThinking"
          autocomplete="off">
        <button @click="sendMessage()"
          class="mascot-panel-send"
          :disabled="isThinking || !inputText.trim()"
          title="发送">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', template);

  // ═══════════════════════════════════════════
  // Alpine 组件定义
  // ═══════════════════════════════════════════
  Alpine.data('mascotPanel', () => ({
    // ─── 核心状态 ───
    showPanel: false,
    messages: [],
    inputText: '',
    isRecording: false,
    isThinking: false,
    speakingId: null,
    expression: 'neutral',
    abortController: null,
    _msgIdCounter: 0,
    _autoSaveTimer: null,

    // ─── 统计 ───
    stats: { visible: false, todayMinutes: 0, streakDays: 0, weekProgress: 0 },

    // ─── 签到 ───
    checkinDone: false,
    checkinData: null,
    showCheckinCelebration: false,
    checkinMsg: '',

    // ─── 问候 ───
    greeting: { text: '你好', emoji: '😊', sub: '今天想学什么？' },

    // ─── 页面感知 ───
    pageContext: { type: '', label: '' },
    quickSuggestions: [],

    // ─── 菜单 ───
    showHeaderMenu: false,

    // ─── 模型选择 ───
    showModelSelector: false,
    availableModels: [],
    currentModelName: 'Hibiki',
    modelSwitching: false,

    // ─── AI 模型 ───
    showAiModelSelector: false,
    aiModels: [],
    currentAiModel: 'MiniMax-Text-01',
    aiConfig: null,
    aiModelLoading: false,

    // ─── 记忆浏览器 ───
    showMemoryPanel: false,
    memories: [],
    memoryLoading: false,

    // ─── 画像卡片 ───
    profileCard: { visible: false, data: null, topTraits: [] },

    // ─── 番茄钟 ───
    pomodoro: { active: false, minutes: 25, seconds: 0, intervalId: null, sessions: 0, isBreak: false },

    // ═══════════════════════════════════
    // Computed
    // ═══════════════════════════════════
    get expressionEmoji() {
      return MascotServices.emojiFor(this.expression);
    },

    get pomodoroDisplay() {
      const m = String(this.pomodoro.minutes).padStart(2, '0');
      const s = String(this.pomodoro.seconds).padStart(2, '0');
      return `${m}:${s}`;
    },

    // ═══════════════════════════════════
    // 初始化
    // ═══════════════════════════════════
    async init() {
      // 表情指令监听
      window.addEventListener('mascot:set-expression', (e) => {
        this.expression = e.detail;
      });

      // 模型切换事件监听
      window.addEventListener('mascot:model-switched', (e) => {
        this.currentModelName = e.detail.model;
        this.loadAvailableModels();
        this.modelSwitching = false;
      });
      window.addEventListener('mascot:model-switching', () => {
        this.modelSwitching = true;
      });

      // 初始化问候语
      this.greeting = MascotServices.getTimeGreeting();

      // 初始化页面感知
      this.pageContext = MascotServices.getPageContext();
      this.quickSuggestions = MascotServices.getQuickSuggestions(this.pageContext);

      // 加载可用模型
      this.loadAvailableModels();

      // 加载 AI 模型列表
      this.loadAiModels();

      // 加载统计
      this.loadStats();

      // 检查今日签到
      this.checkTodayCheckin();

      // 自动加载历史
      const saved = MascotServices.loadChatHistory(window.MascotContext?.studentId);
      if (saved && saved.length > 0) {
        this.messages = saved;
        this._msgIdCounter = saved.length;
        this.$nextTick(() => this.scrollToBottom());
      }
    },

    // ═══════════════════════════════════
    // 面板切换
    // ═══════════════════════════════════
    togglePanel() {
      this.showPanel = !this.showPanel;
      if (this.showPanel) {
        this.$nextTick(() => {
          this.$refs.input?.focus();
          this.scrollToBottom();
        });
        // 刷新上下文
        this.pageContext = MascotServices.getPageContext();
        this.quickSuggestions = MascotServices.getQuickSuggestions(this.pageContext);
        this.greeting = MascotServices.getTimeGreeting();
        this.loadStats();
        // 同步角色: 面板打开
        window.dispatchEvent(new CustomEvent('mascot:panel-opened'));
      } else {
        // 同步角色: 面板关闭
        window.dispatchEvent(new CustomEvent('mascot:panel-closed'));
      }
    },

    // ═══════════════════════════════════
    // 模型选择与切换
    // ═══════════════════════════════════
    loadAvailableModels() {
      if (window.MascotCore && typeof window.MascotCore.getModelList === 'function') {
        const list = window.MascotCore.getModelList();
        if (Array.isArray(list) && list.length > 0) {
          this.availableModels = list;
        }
      }
      // Fallback: if MascotCore not ready, build from MODEL_LIST (defined in kanban.js)
      if (this.availableModels.length === 0 && typeof MODEL_LIST !== 'undefined') {
        this.availableModels = MODEL_LIST.map(m => ({ name: m.name, loaded: false, expressions: 0, motions: 0 }));
      }
      if (window.MascotCore && typeof window.MascotCore.getModelName === 'function') {
        this.currentModelName = window.MascotCore.getModelName() || 'Hibiki';
      }
      // Also try to get current from kanban.js global state
      if (!this.currentModelName && window.MascotCore) {
        this.currentModelName = window.MascotCore.getModelName?.() || 'Hibiki';
      }
    },

    async switchModel(modelName) {
      if (!window.MascotCore || !window.MascotCore.switchModel) {
        this.addMsg('system', '模型切换功能不可用~');
        return;
      }
      if (modelName === this.currentModelName) return;

      this.modelSwitching = true;
      this.addMsg('system', `正在切换为 ${modelName} ... 🎭`);

      const success = await window.MascotCore.switchModel(modelName);

      if (success) {
        this.currentModelName = modelName;
        this.loadAvailableModels();
        this.addMsg('system', `已切换为 ${modelName}，点击角色可互动哦~ ✨`);
      } else {
        this.addMsg('system', `切换 ${modelName} 失败，请稍后重试 😢`);
      }

      this.modelSwitching = false;
    },

    // ═══════════════════════════════════
    // AI 模型选择
    // ═══════════════════════════════════
    async loadAiModels() {
      try {
        const models = await MascotServices.fetchModels();
        if (models && models.length > 0) {
          this.aiModels = models;
          const defaultModel = models.find(m => m.default);
          if (defaultModel) this.currentAiModel = defaultModel.id;
        }
        const config = await MascotServices.fetchConfig();
        if (config) this.aiConfig = config;
      } catch (e) {
        console.warn('[小星] AI 模型列表加载失败:', e);
      }
    },

    switchAiModel(modelId) {
      if (modelId === this.currentAiModel) return;
      const model = this.aiModels.find(m => m.id === modelId);
      if (!model || !model.available) return;
      this.currentAiModel = modelId;
      this.addMsg('system', `已切换到 ${model.name}，后续对话将使用此模型 🤖`);
    },

    // ═══════════════════════════════════
    // 发送消息
    // ═══════════════════════════════════
    async sendMessage() {
      const text = this.inputText.trim();
      if (!text || this.isThinking) return;

      this.inputText = '';
      this.isThinking = true;
      this.expression = 'thinking';
      this.showPanel = true;

      // 同步角色: 思考中
      window.MascotCore?.syncPanelState?.({ state: 'thinking', active: true });
      window.dispatchEvent(new CustomEvent('mascot:set-expression', { detail: 'thinking' }));

      const userMsg = this.addMsg('user', text);
      const assistantMsg = this.addMsg('assistant', '', true);
      assistantMsg.links = [];
      assistantMsg.actions = [];
      this.scrollToBottom();

      try {
        this.abortController = new AbortController();

        const history = this.messages
          .filter(m => !m.typing && m.role !== 'system')
          .slice(-20)
          .map(m => ({ role: m.role, content: m.content }));

        for await (const chunk of MascotServices.streamChat(
          text, history, window.MascotContext?.pageContext,
          { signal: this.abortController.signal, model: this.currentAiModel }
        )) {
          if (chunk.type === 'text' || chunk.event === 'text_delta') {
            const content = chunk.content || (chunk.data && chunk.data.content) || '';
            assistantMsg.content += content;
            assistantMsg.typing = false;
            this.scrollToBottom();
          } else if (chunk.type === 'command' || chunk.event === 'command') {
            const data = chunk.data || chunk;
            this.handleCommand(data.tag, data.content);
          } else if (chunk.type === 'link' || chunk.event === 'link') {
            const data = chunk.data || chunk;
            assistantMsg.links = assistantMsg.links || [];
            assistantMsg.links.push(data);
          } else if (chunk.type === 'action' || chunk.event === 'action') {
            const data = chunk.data || chunk;
            if (data.type === 'proactive') {
              assistantMsg.actions = assistantMsg.actions || [];
              assistantMsg.actions.push(data);
            }
          } else if (chunk.type === 'done' || chunk.event === 'done') {
            // 流正常结束
          } else if (chunk.type === 'error' || chunk.event === 'error') {
            const data = chunk.data || chunk;
            assistantMsg.content = '抱歉，出了点问题: ' + (data.message || data.content || '未知错误');
            assistantMsg.typing = false;
            assistantMsg.error = true;
          }
        }

        // 流结束后的清理
        if (assistantMsg.typing) {
          assistantMsg.typing = false;
          if (!assistantMsg.content) assistantMsg.content = '(回复为空)';
        }

        this.expression = 'happy';
        this.autoSave();
      } catch (err) {
        if (err.name === 'AbortError') {
          assistantMsg.typing = false;
          if (!assistantMsg.content) assistantMsg.content = '(已取消)';
        } else {
          assistantMsg.content = '网络连接失败，请稍后重试 😢';
          assistantMsg.typing = false;
          assistantMsg.error = true;
          this.expression = 'surprised';
        }
      } finally {
        this.isThinking = false;
        this.abortController = null;
        // 同步角色: 思考结束
        window.MascotCore?.syncPanelState?.({ state: 'thinking', active: false });
      }
    },

    sendQuick(text) {
      this.inputText = text;
      this.sendMessage();
    },

    async retryMessage(msg) {
      // 找到该消息之前的用户消息
      const idx = this.messages.indexOf(msg);
      if (idx < 1) return;
      const prevMsg = this.messages[idx - 1];
      if (prevMsg.role !== 'user') return;

      // 删除当前消息及其后的所有内容
      this.messages = this.messages.slice(0, idx);
      this._msgIdCounter -= (this._msgIdCounter - idx);

      // 重新发送
      this.isThinking = false;
      this.inputText = prevMsg.content;
      this.sendMessage();
    },

    // ═══════════════════════════════════
    // 语音
    // ═══════════════════════════════════
    async toggleVoice() {
      if (this.isRecording) {
        const blob = await MascotServices.stopRecording();
        this.isRecording = false;
        // 同步角色: 录音结束
        window.MascotCore?.syncPanelState?.({ state: 'recording', active: false });
        if (blob) {
          try {
            const text = await MascotServices.speechToText(blob);
            if (text) { this.inputText = text; this.sendMessage(); }
          } catch (e) {
            this.addMsg('system', '语音识别失败，请使用文字输入~');
          }
        }
      } else {
        try {
          await MascotServices.startRecording();
          this.isRecording = true;
          // 同步角色: 录音中
          window.MascotCore?.syncPanelState?.({ state: 'recording', active: true });
        } catch (e) {
          this.addMsg('system', '麦克风权限被拒绝，您可以使用文字输入与我对话~');
        }
      }
    },

    // ═══════════════════════════════════
    // TTS 朗读
    // ═══════════════════════════════════
    async speak(msg) {
      if (this.speakingId === msg.id) return;
      try {
        this.speakingId = msg.id;
        const url = await MascotServices.textToSpeech(msg.content);
        if (url) {
          const audio = new Audio(url);
          audio.onended = () => { this.speakingId = null; URL.revokeObjectURL(url); };
          audio.onerror = () => { this.speakingId = null; URL.revokeObjectURL(url); };
          audio.play();
        } else { this.speakingId = null; }
      } catch (e) { this.speakingId = null; }
    },

    // ═══════════════════════════════════
    // 指令处理
    // ═══════════════════════════════════
    handleCommand(tag, content) {
      switch (tag) {
        case 'navigate': {
          const ok = MascotServices.navigate(content);
          if (!ok) this.addMsg('system', `抱歉，我找不到"${content}"这个页面~`);
          break;
        }
        case 'expression': {
          this.expression = content;
          window.dispatchEvent(new CustomEvent('mascot:set-expression', { detail: content }));
          break;
        }
        case 'action': {
          window.dispatchEvent(new CustomEvent('mascot:trigger-action', { detail: content }));
          break;
        }
        case 'open_link': {
          if (content.startsWith('http')) window.open(content, '_blank');
          break;
        }
      }
    },

    // ═══════════════════════════════════
    // 链接导航
    // ═══════════════════════════════════
    navigateLink(link) {
      if (link.type === 'internal' && link.url) {
        window.location.href = link.url;
      } else if (link.url) {
        window.open(link.url, '_blank');
      }
    },

    // ═══════════════════════════════════
    // 主动推送动作处理
    // ═══════════════════════════════════
    handleProactiveAction(action) {
      const label = action.action_label || '';
      if (label.includes('复习')) window.location.href = '/courses.html';
      else if (label.includes('练习') || label.includes('提示')) this.addMsg('system', '请直接告诉我你需要什么帮助~');
      else if (label.includes('休息') || label.includes('知道')) this.addMsg('system', '好的，注意劳逸结合哦~');
      else if (label.includes('计划') || label.includes('查看')) window.location.href = '/personal.html';
      else if (label.includes('番茄')) this.togglePomodoro();
      else this.addMsg('system', '好的，请告诉我你需要什么~');
    },

    // ═══════════════════════════════════
    // 消息操作
    // ═══════════════════════════════════
    copyMessage(msg) {
      navigator.clipboard.writeText(msg.content).then(() => {
        msg.copied = true;
        setTimeout(() => { msg.copied = false; }, 2000);
      }).catch(() => {
        this.addMsg('system', '复制失败，请手动选择复制~');
      });
    },

    likeMessage(msg) {
      if (msg.disliked) msg.disliked = false;
      msg.liked = !msg.liked;
      if (msg.liked) msg.likes = (msg.likes || 0) + 1;
      else msg.likes = Math.max(0, (msg.likes || 0) - 1);
    },

    dislikeMessage(msg) {
      if (msg.liked) { msg.liked = false; msg.likes = Math.max(0, (msg.likes || 0) - 1); }
      msg.disliked = !msg.disliked;
    },

    // ═══════════════════════════════════
    // Markdown 渲染
    // ═══════════════════════════════════
    renderMarkdown(text) {
      return MascotServices.renderMarkdown(text);
    },

    // ═══════════════════════════════════
    // 消息管理
    // ═══════════════════════════════════
    addMsg(role, content = '', typing = false) {
      const msg = {
        id: ++this._msgIdCounter,
        role, content, typing,
        links: null, actions: null,
        liked: false, disliked: false, likes: 0, copied: false, error: false,
      };
      this.messages.push(msg);
      return msg;
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.msgContainer;
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    onScroll() {
      // 预留：滚动到顶部加载更多历史消息
    },

    // ═══════════════════════════════════
    // 历史管理
    // ═══════════════════════════════════
    autoSave() {
      if (this._autoSaveTimer) clearTimeout(this._autoSaveTimer);
      this._autoSaveTimer = setTimeout(() => {
        MascotServices.saveChatHistory(this.messages, window.MascotContext?.studentId);
      }, 2000);
    },

    saveHistory() {
      MascotServices.saveChatHistory(this.messages, window.MascotContext?.studentId);
      this.addMsg('system', '对话已保存 💾');
    },

    loadHistory() {
      const saved = MascotServices.loadChatHistory(window.MascotContext?.studentId);
      if (saved && saved.length > 0) {
        this.messages = saved;
        this._msgIdCounter = saved.length;
        this.addMsg('system', `已加载 ${saved.length} 条历史消息 📥`);
        this.$nextTick(() => this.scrollToBottom());
      } else {
        this.addMsg('system', '没有找到历史对话~');
      }
    },

    clearHistory() {
      if (this.messages.length === 0) return;
      if (confirm('确定要清除所有对话记录吗？此操作不可撤销。')) {
        this.messages = [];
        this._msgIdCounter = 0;
        MascotServices.clearChatHistory(window.MascotContext?.studentId);
        this.addMsg('system', '对话已清除 🗑️');
      }
    },

    exportHistory() {
      if (this.messages.filter(m => !m.typing).length === 0) {
        this.addMsg('system', '没有对话可以导出~');
        return;
      }
      MascotServices.downloadChatHistory(this.messages);
      this.addMsg('system', '对话记录已下载 📤');
    },

    // ═══════════════════════════════════
    // 记忆浏览器
    // ═══════════════════════════════════
    toggleMemoryPanel() {
      this.showMemoryPanel = !this.showMemoryPanel;
      if (this.showMemoryPanel) this.loadMemories();
    },

    async loadMemories() {
      this.memoryLoading = true;
      try {
        const studentId = window.MascotContext?.studentId || 'default';
        const res = await MascotServices.fetchMemories(studentId);
        if (res.success) {
          this.memories = (res.memories || []).slice(0, 30);
        }
      } catch (e) {
        this.memories = [];
      } finally {
        this.memoryLoading = false;
      }
    },

    typeLabel(type) {
      const map = {
        background: '🏠', knowledge: '📚', preference: '💡',
        interest: '🎯', goal: '🎯', emotion: '💭',
        learning_trait: '🎓', personality: '🧠', interaction: '💬',
        fact: '📌',
      };
      return map[type] || '📌';
    },

    async confirmMemoryItem(mem) {
      try {
        await MascotServices.confirmMemory(mem.id || mem.memory_id, !mem.confirmed);
        mem.confirmed = !mem.confirmed;
      } catch (e) { /* ignore */ }
    },

    async deleteMemoryItem(mem) {
      try {
        await MascotServices.deleteMemory(mem.id || mem.memory_id);
        this.memories = this.memories.filter(m => m !== mem);
      } catch (e) { /* ignore */ }
    },

    // ═══════════════════════════════════
    // 用户画像
    // ═══════════════════════════════════
    toggleProfileCard() {
      this.profileCard.visible = !this.profileCard.visible;
      if (this.profileCard.visible && !this.profileCard.data) this.loadProfile();
    },

    async loadProfile() {
      try {
        const studentId = window.MascotContext?.studentId || 'default';
        const res = await MascotServices.fetchProfile(studentId);
        if (res.success && res.profile) {
          this.profileCard.data = res.profile;
          // 提取所有特质
          const all = [
            ...(res.profile.learning_traits || []),
            ...(res.profile.personality_traits || []),
            ...(res.profile.goals_interests || []),
          ].sort((a, b) => (b.score || 0) - (a.score || 0));
          this.profileCard.topTraits = all.slice(0, 5);
        }
      } catch (e) { /* ignore */ }
    },

    // ═══════════════════════════════════
    // 番茄钟
    // ═══════════════════════════════════
    togglePomodoro() {
      if (this.pomodoro.active) {
        this.stopPomodoro();
      } else {
        this.startPomodoro();
      }
    },

    startPomodoro(minutes = 25) {
      if (this.pomodoro.intervalId) clearInterval(this.pomodoro.intervalId);
      this.pomodoro.active = true;
      this.pomodoro.minutes = minutes;
      // 同步角色: 番茄钟启动
      window.MascotCore?.syncPanelState?.({ state: 'pomodoro', active: true });
      this.pomodoro.seconds = 0;
      this.pomodoro.isBreak = false;
      this.pomodoro.intervalId = setInterval(() => {
        if (this.pomodoro.seconds > 0) {
          this.pomodoro.seconds--;
        } else if (this.pomodoro.minutes > 0) {
          this.pomodoro.minutes--;
          this.pomodoro.seconds = 59;
        } else {
          // 时间到
          this.pomodoroComplete();
        }
      }, 1000);
    },

    pomodoroComplete() {
      clearInterval(this.pomodoro.intervalId);
      if (this.pomodoro.isBreak) {
        // 休息结束 → 提示
        this.addMsg('system', '🍅 休息结束！准备开始新的番茄钟吗？');
        this.pomodoro.active = false;
        this.pomodoro.isBreak = false;
        window.dispatchEvent(new CustomEvent('mascot:show-toast', {
          detail: { title: '休息结束', content: '准备开始新的番茄钟！', type: 'success' },
        }));
      } else {
        // 专注结束 → 开始休息
        this.pomodoro.sessions++;
        this.addMsg('system', `🍅 番茄钟完成！已累计 ${this.pomodoro.sessions} 轮。休息 5 分钟吧~`);
        window.dispatchEvent(new CustomEvent('mascot:trigger-action', { detail: 'celebrate' }));
        // 5分钟休息
        this.pomodoro.isBreak = true;
        this.startPomodoro(5);
      }
    },

    stopPomodoro() {
      if (this.pomodoro.intervalId) clearInterval(this.pomodoro.intervalId);
      this.pomodoro.active = false;
      this.pomodoro.isBreak = false;
      this.pomodoro.minutes = 25;
      this.pomodoro.seconds = 0;
      // 同步角色: 番茄钟结束
      window.MascotCore?.syncPanelState?.({ state: 'pomodoro', active: false });
    },

    // ═══════════════════════════════════
    // 每日签到
    // ═══════════════════════════════════
    async doCheckin() {
      if (this.checkinDone) return;
      try {
        const studentId = window.MascotContext?.studentId || 'default';
        const res = await MascotServices.dailyCheckin(studentId);
        if (res.success) {
          this.checkinDone = true;
          this.checkinData = res;
          if (res.is_first_today) {
            this.showCheckinCelebration = true;
            this.checkinMsg = res.message;
            this.stats.streakDays = res.streak;
            window.dispatchEvent(new CustomEvent('mascot:trigger-action', { detail: 'checkin' }));
            setTimeout(() => { this.showCheckinCelebration = false; }, 5000);
          }
          // 保存签到日期
          localStorage.setItem('starlearn_checkin_date', new Date().toISOString().slice(0, 10));
          localStorage.setItem('starlearn_checkin_streak', res.streak);
        }
      } catch (e) {
        this.addMsg('system', '签到失败，请稍后再试~');
      }
    },

    checkTodayCheckin() {
      const saved = localStorage.getItem('starlearn_checkin_date');
      const today = new Date().toISOString().slice(0, 10);
      if (saved === today) {
        this.checkinDone = true;
        this.stats.streakDays = parseInt(localStorage.getItem('starlearn_checkin_streak') || '0');
      }
    },

    // ═══════════════════════════════════
    // 学习统计
    // ═══════════════════════════════════
    async loadStats() {
      try {
        const studentId = window.MascotContext?.studentId || 'default';
        const res = await MascotServices.fetchStats(studentId);
        if (res && res.success && res.data) {
          this.stats.todayMinutes = res.data.today_minutes || 0;
          this.stats.streakDays = res.data.streak_days || 0;
          this.stats.weekProgress = res.data.weekly_goal_percent || 0;
          this.stats.visible = true;
        }
      } catch (e) {
        // 降级：使用 localStorage
        this.stats.visible = true;
      }
    },

    // ═══════════════════════════════════
    // 空闲检测回调
    // ═══════════════════════════════════
    onIdle() {
      // 面板关闭时才弹 toast
      if (!this.showPanel) {
        window.MascotCore.showToast(
          '还在吗？',
          '你已经一段时间没操作了，需要我帮你回顾点什么吗？',
          { type: 'tip', duration: 8000, actionLabel: '打开小星', actionCallback: () => { this.showPanel = true; } }
        );
      }
    },

    // ═══════════════════════════════════
    // 销毁
    // ═══════════════════════════════════
    destroy() {
      if (this.abortController) { this.abortController.abort(); this.abortController = null; }
      if (this.pomodoro.intervalId) clearInterval(this.pomodoro.intervalId);
      if (this._autoSaveTimer) clearTimeout(this._autoSaveTimer);
    },
  }));

  // Alpine 在 alpine:init 之前已完成 DOM 扫描，需手动初始化新插入的面板
  const panelEl = document.querySelector('.mascot-panel');
  if (panelEl) {
    Alpine.initTree(panelEl);
  }
});
