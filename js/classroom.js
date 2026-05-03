/**
 * Classroom Page JavaScript - ClassroomController
 * Handles multi-scene rendering (slide/quiz/exercise/interactive),
 * TTS audio sync, AI teacher chat, quiz grading, completion celebration
 */

(function() {
    'use strict';

    // Animation types
    const ANIMATION_TYPES = {
        ENTER: 'enter',
        EXIT: 'exit',
        ATTENTION: 'attention'
    };

    // Enter animations
    const ENTER_ANIMATIONS = {
        fade: 'elem-enter-fade',
        fadeUp: 'elem-enter-up',
        fadeDown: 'elem-enter-down',
        zoom: 'elem-enter-zoom',
        bounce: 'elem-enter-bounce',
        slideLeft: 'elem-enter-slide-left',
        slideRight: 'elem-enter-slide-right'
    };

    // Attention animations
    const ATTENTION_ANIMATIONS = {
        pulse: 'elem-attention-pulse',
        shake: 'elem-attention-shake',
        wobble: 'elem-attention-wobble',
        heartbeat: 'elem-attention-heartbeat'
    };

    // MiniMax TTS voice mapping
    const MINIMAX_VOICES = {
        'female-shaonv': { voice_id: 'female_shaonv', name: '青春少女', description: '活泼可爱的年轻女声' },
        'female-yujie': { voice_id: 'female_yujie', name: '温柔御姐', description: '成熟温柔的姐姐声音' },
        'female-danyun': { voice_id: 'female_danyun', name: '知性女声', description: '知性优雅的女性声音' },
        'male-qingshu': { voice_id: 'male_qingshu', name: '青涩少年', description: '清新自然的年轻男声' },
        'male-shaoshuai': { voice_id: 'male_shaoshuai', name: '磁性男声', description: '沉稳磁性的成熟男声' }
    };

    // Default TTS config
    const TTS_CONFIG = {
        provider: 'minimax',
        voice: 'female-yujie',
        speed: 1.0,
        pitch: 1.0,
        volume: 1.0,
        speedOptions: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    };

    // Slide transition effects
    const SLIDE_TRANSITIONS = {
        none: 'none',
        fade: 'fade',
        slideLeft: 'slide-left',
        slideRight: 'slide-right',
        zoom: 'zoom'
    };

    class ClassroomController {
        constructor() {
            this.courseData = null;
            this.currentIndex = 0;
            this.scenes = [];
            this.agentTeam = [];
            this.quizAnswers = {};
            this.visitedScenes = new Set();
            this.isPlaying = false;
            this.isChatLoading = false;
            this.chatHistory = [];
            this.sceneStartTime = Date.now();
            this.totalTimeSpent = 0;
            this.currentAudio = null;

            // Action system state
            this.actionQueue = [];
            this.currentAction = null;
            this.isProcessingActions = false;
            this.spotlightOverlay = null;
            this.laserOverlay = null;
            this.whiteboardVisible = false;

            // Animation state
            this.currentAnimationEffects = [];
            this.isTransitioning = false;
            this.animationQueue = [];

            // Spotlight/laser state
            this.spotlightElement = null;
            this.laserElements = [];

            // DOM refs
            this.courseTitle = document.getElementById('course-title')?.querySelector('span');
            this.outlineList = document.getElementById('outline-list');
            this.slideContainer = document.getElementById('slide-container');
            this.quizContainer = document.getElementById('quiz-container');
            this.exerciseContainer = document.getElementById('exercise-container');
            this.interactiveContainer = document.getElementById('interactive-container');
            this.teacherAvatar = document.getElementById('teacher-avatar');
            this.speechText = document.getElementById('speech-text');
            this.prevBtn = document.getElementById('prev-slide');
            this.nextBtn = document.getElementById('next-slide');
            this.currentSlideEl = document.getElementById('current-slide');
            this.totalSlidesEl = document.getElementById('total-slides');
            this.progressFill = document.getElementById('progress-fill');
            this.voiceBtn = document.getElementById('voice-btn');
            this.speechSync = document.getElementById('speech-sync');
            this.chatMessages = document.getElementById('chat-messages');
            this.chatInput = document.getElementById('chat-input');
            this.sendChat = document.getElementById('send-chat');
            this.chatAgentSelect = document.getElementById('chat-agent-select');
            this.sceneThumbnails = document.getElementById('scene-thumbnails');
            this.sceneSidebar = document.getElementById('scene-sidebar');
            this.completionOverlay = document.getElementById('completion-overlay');
            this.audioPlayer = document.getElementById('tts-audio-player');

            // OpenMAIC slide player initialization
            this.openmaicDeck = null;
            this.openmaicPlayer = null;
            if (window.OpenMAICSlidePlayer) {
                this.openmaicPlayer = new window.OpenMAICSlidePlayer({
                    container: this.slideContainer,
                    stage: this.slideStage,
                    overlay: this.actionOverlay,
                    audioElement: this.audioPlayer,
                    speechText: this.speechText,
                    syncElement: this.speechSync,
                    teacherAvatar: this.teacherAvatar,
                    getSpeed: function() { return 1.0; },
                });
            }

            // Action overlays (create if not exist)
            this.actionOverlay = document.getElementById('action-overlay');
            if (!this.actionOverlay) {
                this.actionOverlay = document.createElement('div');
                this.actionOverlay.id = 'action-overlay';
                this.actionOverlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';
                document.body.appendChild(this.actionOverlay);
            }

            // Speech recognition for chat
            this.chatVoiceBtn = document.getElementById('chat-voice-btn');
            this.chatRecognition = null;
            this.chatIsRecording = false;
            this.chatInterimText = '';
        }

        // ---- Init ----

        async init() {
            this.loadData();
            if (!this.courseData) {
                alert('未找到课堂数据，正在返回首页...');
                window.location.href = '/index.html';
                return;
            }
            this.loadVoicePreference();
            this.buildScenes();
            this.setupUI();
            this.bindEvents();
            this.initVoiceSelector();
            this.initTTS();
            this.renderSceneSidebar();
            this.renderScene(0);
            this.updateNav();
        }

        loadData() {
            const saved = sessionStorage.getItem('classroomData');
            if (saved) {
                try { this.courseData = JSON.parse(saved); } catch (e) {}
            }
            if (this.courseData) {
                this.agentTeam = this.courseData.agent_team || [];
                this.courseData.tts_audio_urls = this.courseData.tts_audio_urls || {};
            }
        }

        buildScenes() {
            const outlines = this.courseData.outlines || [];
            const slides = this.courseData.slides || [];
            const quizData = this.courseData.quiz_data || [];
            const exerciseData = this.courseData.exercise_data || [];
            const slidesV2 = this.courseData.slides_v2 || [];

            const sameId = function(a, b) {
                return String(a != null ? a : '') !== '' && String(a != null ? a : '') === String(b != null ? b : '');
            };
            const sameTitle = function(item, outline) {
                return item && item.title && outline && outline.title && String(item.title).trim() === String(outline.title).trim();
            };
            const matchesScene = function(item, outline) {
                var sceneId = outline && outline.id;
                if (sceneId == null || sceneId === '') return false;
                // Strategy 1 (best): strict scene_id match (new courses)
                if (sameId(item && item.scene_id, sceneId)) return true;
                if (sameId(item && item.sceneId, sceneId)) return true;
                // Strategy 2: direct id match
                if (sameId(item && item.id, sceneId)) return true;
                // Strategy 3 (legacy fallback): title match for old courses where scene_id is undefined
                if ((item && item.scene_id == null) && (item && item.sceneId == null)) {
                    return sameTitle(item, outline);
                }
                return false;
            };
            const findSceneData = function(items, outline) {
                return (items || []).find(function(item) { return matchesScene(item, outline); }) || null;
            };

            this.scenes = outlines.map(function(outline, i) {
                var sceneId = outline.id || i + 1;
                var matchedSlide = findSceneData(slides, outline);
                var matchedSlideV2 = findSceneData(slidesV2, outline);
                var matchedQuiz = findSceneData(quizData, outline);
                var matchedExercise = findSceneData(exerciseData, outline);

                return {
                    id: sceneId,
                    title: outline.title || ('Scene ' + sceneId),
                    type: outline.type || 'slide',
                    description: outline.description || '',
                    keyPoints: outline.key_points || outline.keyPoints || [],
                    slide: matchedSlide,
                    slides_v2: matchedSlideV2 ? [matchedSlideV2] : [],
                    quiz: matchedQuiz,
                    exercise: matchedExercise,
                    audioUrl: (this.courseData.tts_audio_urls || {})[String(sceneId)] || null,
                    imageUrl: (matchedSlide && matchedSlide.content && matchedSlide.content.elements && matchedSlide.content.elements[0] && matchedSlide.content.elements[0].image_url) || null,
                };
            }, this);
        }

        setupUI() {
            if (this.courseTitle && this.courseData.title) {
                this.courseTitle.textContent = this.courseData.title;
            }
            if (this.totalSlidesEl) {
                this.totalSlidesEl.textContent = this.scenes.length;
            }
            // Set teacher avatar - use image if available, otherwise gradient circle with initials
            if (this.courseData.teacher) {
                const teacher = this.courseData.teacher;
                if (teacher.avatar && teacher.avatar.startsWith('http')) {
                    this.teacherAvatar.innerHTML = `<img src="${teacher.avatar}" alt="教师" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                } else if (teacher.name) {
                    // Generate initials from name
                    const initials = teacher.name.slice(0, 2).toUpperCase();
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;font-weight:700;color:white;">${initials}</span>`;
                } else {
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;">👩‍🏫</span>`;
                }
            }
            // Populate agent selector in chat
            if (this.chatAgentSelect && this.agentTeam.length > 0) {
                this.chatAgentSelect.innerHTML = this.agentTeam.map(a =>
                    `<option value="${a.id || ''}">${a.name || 'AI教师'} (${a.role || ''})</option>`
                ).join('');
            }
        }

        bindEvents() {
            document.getElementById('toggle-sidebar')?.addEventListener('click', () => {
                this.sceneSidebar.classList.toggle('collapsed');
            });
            this.prevBtn?.addEventListener('click', () => this.prevScene());
            this.nextBtn?.addEventListener('click', () => this.nextScene());
            this.voiceBtn?.addEventListener('click', () => this.toggleVoice());
            document.getElementById('replay-btn')?.addEventListener('click', () => this.replaySpeech());
            document.getElementById('pause-btn')?.addEventListener('click', () => this.pauseSpeech());
            document.getElementById('speed-btn')?.addEventListener('click', () => {
                this.cycleSpeed();
            });
            this.sendChat?.addEventListener('click', () => this.sendMessage());
            this.chatInput?.addEventListener('keypress', e => { if (e.key === 'Enter') this.sendMessage(); });
            document.getElementById('exit-btn')?.addEventListener('click', () => this.showExitModal());
            document.getElementById('cancel-exit')?.addEventListener('click', () => this.hideExitModal());
            document.getElementById('confirm-exit')?.addEventListener('click', () => this.confirmExit());
            document.addEventListener('keydown', e => this.onKey(e));
            this.initChatVoiceInput();
        }

        onKey(e) {
            if (e.target === this.chatInput) return;
            switch (e.key) {
                case 'ArrowLeft': this.prevScene(); break;
                case 'ArrowRight': this.nextScene(); break;
                case ' ': e.preventDefault(); this.toggleVoice(); break;
            }
        }

        // ---- Scene Sidebar ----

        renderSceneSidebar() {
            if (!this.sceneThumbnails) return;
            const icons = { slide: '📖', quiz: '📝', exercise: '✏️', interactive: '🎮', pbl: '🔬', code: '💻' };
            this.sceneThumbnails.innerHTML = this.scenes.map((s, i) => `
                <div class="scene-thumb ${i === 0 ? 'active' : ''}" data-index="${i}" onclick="classroomController.goToScene(${i})">
                    <span class="scene-thumb-icon">${icons[s.type] || '📖'}</span>
                    <span class="scene-thumb-label">${s.title.slice(0, 8)}</span>
                    <span class="scene-thumb-badge">${s.type}</span>
                </div>
            `).join('');
        }

        updateSidebarActive(index) {
            this.sceneThumbnails?.querySelectorAll('.scene-thumb').forEach((t, i) =>
                t.classList.toggle('active', i === index));
        }

        // ---- Scene Rendering ----

        renderScene(index) {
            if (index < 0 || index >= this.scenes.length) return;
            this.visitedScenes.add(this.currentIndex);
            this.totalTimeSpent += Math.floor((Date.now() - this.sceneStartTime) / 1000);
            this.sceneStartTime = Date.now();
            this.currentIndex = index;

            const scene = this.scenes[index];
            this.hideAllSceneContainers();

            switch (scene.type) {
                case 'quiz': this.renderQuizScene(scene); break;
                case 'exercise': this.renderExerciseScene(scene); break;
                case 'interactive': case 'pbl': this.renderInteractiveScene(scene); break;
                default: {
                    // Check if V2 slides are available
                    if (scene.slides_v2 && scene.slides_v2.length > 0) {
                        this.renderSlideV2Scene(scene);
                    } else {
                        this.renderSlideScene(scene);
                    }
                }
            }

            this.updateTeacherSpeech(scene);
            this.updateSidebarActive(index);
            this.updateNav();
            if (this.isPlaying) this.playSceneAudio(scene);
            this.checkCompletion();
        }

        hideAllSceneContainers() {
            [this.slideContainer, this.quizContainer, this.exerciseContainer, this.interactiveContainer]
                .forEach(el => { if (el) el.style.display = 'none'; });
            const quizSubmit = document.getElementById('quiz-submit-btn');
            const quizResult = document.getElementById('quiz-result');
            if (quizSubmit) quizSubmit.style.display = 'none';
            if (quizResult) quizResult.style.display = 'none';
        }

        // ============================================================
        // SlideV2 渲染器（结构化布局）
        // ============================================================

        SlideRenderer = {
            ICON_MAP: {
                'book': '📖', 'lightbulb': '💡', 'code': '💻',
                'check': '✅', 'star': '⭐', 'question': '❓',
                'warning': '⚠️', 'info': 'ℹ️'
            },
            COLOR_THEMES: ['blue', 'yellow', 'green', 'purple', 'orange'],

            render(slideV2, container) {
                if (!slideV2 || !container) return;
                const layoutType = slideV2.layoutType || 'two-column';
                const renderer = this._getRenderer(layoutType);
                const html = renderer(slideV2);
                container.innerHTML = html;
            },

            _getRenderer(layoutType) {
                const renderers = {
                    'title-only': this._renderTitleOnly.bind(this),
                    'two-column': this._renderTwoColumn.bind(this),
                    'grid-cards': this._renderGridCards.bind(this),
                    'header-content': this._renderHeaderContent.bind(this),
                    'quote-highlight': this._renderQuoteHighlight.bind(this),
                };
                return renderers[layoutType] || this._renderTwoColumn.bind(this);
            },

            _renderTitleOnly(slide) {
                return `
                    <div class="slide-v2-container layout-title-only">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                    </div>
                `;
            },

            _renderTwoColumn(slide) {
                const cards = (slide.content || []).map(item => this._renderContentCard(item)).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-two-column">
                            ${cards}
                        </div>
                    </div>
                `;
            },

            _renderGridCards(slide) {
                const cards = (slide.content || []).map(item => this._renderContentCard(item)).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-grid-cards">
                            ${cards}
                        </div>
                    </div>
                `;
            },

            _renderHeaderContent(slide) {
                const cards = (slide.content || []).map(item => this._renderContentCard(item)).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-header-content">
                            ${cards}
                        </div>
                    </div>
                `;
            },

            _renderQuoteHighlight(slide) {
                const cards = (slide.content || []).map(item => this._renderContentCard(item)).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-quote-highlight">
                            ${cards}
                        </div>
                    </div>
                `;
            },

            _renderContentCard(item) {
                const icon = this._getIcon(item.icon);
                const theme = this._validateTheme(item.colorTheme);
                const subTitle = this._escapeHtml(item.subTitle || '');
                const textHtml = this._parseMarkdown(item.text || '');
                const codeHtml = item.codeSnippet ? this._renderCodeSnippet(item.codeSnippet) : '';
                const imageHtml = item.imageUrl ? this._renderImage(item.imageUrl) : '';

                return `
                    <div class="content-card theme-${theme}">
                        ${subTitle ? `<div class="card-title">${icon} ${subTitle}</div>` : ''}
                        ${textHtml ? `<div class="card-text">${textHtml}</div>` : ''}
                        ${codeHtml}
                        ${imageHtml}
                    </div>
                `;
            },

            _renderCodeSnippet(code) {
                return `<div class="card-code"><code>${this._escapeHtml(code)}</code></div>`;
            },

            _renderImage(url) {
                return `<div class="card-image"><img src="${url}" alt="" loading="lazy"></div>`;
            },

            _getIcon(iconName) {
                return this.ICON_MAP[iconName] || this.ICON_MAP['book'];
            },

            _validateTheme(theme) {
                return this.COLOR_THEMES.includes(theme) ? theme : 'blue';
            },

            _parseMarkdown(text) {
                if (!text) return '';
                // Bold: **text** → <strong>text</strong>
                let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
                // Inline code: `code` → <code>code</code>
                html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
                // Unordered lists: - item → <li>item</li>
                const lines = html.split('\n');
                const processed = [];
                let inList = false;
                for (const line of lines) {
                    const m = line.match(/^-\s+(.+)/);
                    if (m) {
                        if (!inList) { processed.push('<ul>'); inList = true; }
                        processed.push(`<li>${m[1]}</li>`);
                    } else {
                        if (inList) { processed.push('</ul>'); inList = false; }
                        processed.push(line);
                    }
                }
                if (inList) processed.push('</ul>');
                html = processed.join('\n');
                // Convert newlines to <br>
                html = html.replace(/\n/g, '<br>');
                return html;
            },

            _escapeHtml(str) {
                if (!str) return '';
                return str.replace(/&/g, '&amp;')
                          .replace(/</g, '&lt;')
                          .replace(/>/g, '&gt;')
                          .replace(/"/g, '&quot;')
                          .replace(/'/g, '&#039;');
            }
        };

        renderSlideV2Scene(scene) {
            if (!this.slideContainer) return;
            this.slideContainer.style.display = 'block';
            this.slideContainer.style.animation = 'slideEnter 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
            this.slideContainer.className = 'slide-container openmaic-slide-host';

            const slides_v2 = scene.slides_v2 || [];
            if (slides_v2.length === 0) {
                this.renderSlideScene(scene);
                return;
            }

            const adapter = window.SlideV2ToOpenMAICAdapter;
            if (!adapter) {
                this.SlideRenderer.render(slides_v2[0], this.slideContainer);
                return;
            }

            const openmaicSlide = adapter.convert(slides_v2[0], scene.id);
            // Graceful degradation: if adapter returns null or empty elements, fallback
            if (!openmaicSlide || !openmaicSlide.elements || openmaicSlide.elements.length === 0) {
                console.warn('[Classroom] Adapter produced invalid slide, falling back to SlideRenderer');
                this.SlideRenderer.render(slides_v2[0], this.slideContainer);
                return;
            }
            if (this.openmaicPlayer) {
                this.openmaicPlayer.render(openmaicSlide);
            } else {
                this.SlideRenderer.render(slides_v2[0], this.slideContainer);
            }
        }

        // ============================================================
        // 沉浸式互动场景渲染器
        // ============================================================

        InteractiveRenderer = {
            // 组件渲染器映射
            _renderers: {
                text_card: '_renderTextCard',
                quiz: '_renderQuiz',
                code_editor: '_renderCodeEditor',
                simulation: '_renderSimulation'
            },

            // 主渲染入口
            render(scene, container) {
                if (!scene || !container) return;

                // 停止上一个场景的 TTS
                if (window.speechSynthesis) {
                    window.speechSynthesis.cancel();
                }

                // 渲染 audio_script（需要用户点击播放）
                this._renderAudioNarration(scene, container);

                // 渲染 components
                const body = container.querySelector('.interactive-body') || container;
                body.innerHTML = '';

                (scene.components || []).forEach(component => {
                    const renderer = this._renderers[component.type];
                    if (renderer && typeof this[renderer] === 'function') {
                        const html = this[renderer](component);
                        if (html) {
                            body.innerHTML += html;
                            this._bindComponentEvents(component, body.lastElementChild);
                        }
                    }
                });
            },

            // 渲染语音旁白控制按钮
            _renderAudioNarration(scene, container) {
                if (!scene.audio_script) return;

                const script = encodeURIComponent(scene.audio_script);
                const ttsHtml = `
                    <div class="tts-control">
                        <button class="tts-play-btn" data-script="${script}">
                            <span class="tts-icon">🔊</span>
                            <span class="tts-label">播放旁白</span>
                        </button>
                        <div class="tts-progress" style="display:none">
                            <div class="tts-wave"></div>
                        </div>
                    </div>
                `;

                // 在容器顶部添加 TTS 控制
                let existingHeader = container.querySelector('.interactive-header');
                if (!existingHeader) {
                    container.innerHTML = `
                        <div class="interactive-header">
                            <h1 class="interactive-title">${this._escapeHtml(scene.title || '')}</h1>
                            ${ttsHtml}
                        </div>
                        <div class="interactive-body"></div>
                    `;
                } else {
                    existingHeader.querySelector('.tts-control')?.remove();
                    existingHeader.innerHTML += ttsHtml;
                }
            },

            // 绑定组件事件
            _bindComponentEvents(component, element) {
                if (!element) return;

                switch (component.type) {
                    case 'quiz':
                        this._bindQuizEvents(component, element);
                        break;
                    case 'code_editor':
                        this._bindCodeEditorEvents(component, element);
                        break;
                    case 'simulation':
                        this._bindSimulationEvents(component, element);
                        break;
                }
            },

            // 渲染 TextCard 组件
            _renderTextCard(comp) {
                const icon = this._getIcon(comp.icon);
                const theme = this._validateTheme(comp.color_theme);
                const title = this._escapeHtml(comp.title || '');
                const textHtml = this._parseMarkdown(comp.content || '');

                return `
                    <div class="content-card theme-${theme}">
                        ${title ? `<div class="card-title">${icon} ${title}</div>` : ''}
                        ${textHtml ? `<div class="card-text">${textHtml}</div>` : ''}
                    </div>
                `;
            },

            // 渲染 Quiz 组件（防作弊设计）
            _renderQuiz(comp) {
                // 安全设计：options 不包含 is_correct，explanation 为空
                const optionsHtml = (comp.options || []).map(opt => `
                    <div class="quiz-option" data-key="${this._escapeHtml(opt.key)}">
                        <span class="option-key">${this._escapeHtml(opt.key)}</span>
                        <span class="option-text">${this._escapeHtml(opt.text)}</span>
                    </div>
                `).join('');

                return `
                    <div class="quiz-container" data-quiz-id="${this._escapeHtml(comp.id)}">
                        <div class="quiz-question">${this._escapeHtml(comp.question || '')}</div>
                        <div class="quiz-options">${optionsHtml}</div>
                        <button class="quiz-submit-btn" disabled>请先选择答案</button>
                        <div class="quiz-feedback" style="display:none"></div>
                    </div>
                `;
            },

            // Quiz 事件绑定（防作弊）
            _bindQuizEvents(comp, element) {
                const container = element;
                const options = container.querySelectorAll('.quiz-option');
                const submitBtn = container.querySelector('.quiz-submit-btn');

                // 选项点击
                options.forEach(opt => {
                    opt.addEventListener('click', () => {
                        options.forEach(o => o.classList.remove('selected'));
                        opt.classList.add('selected');
                        submitBtn.disabled = false;
                    });
                });

                // 提交答案
                submitBtn.addEventListener('click', async () => {
                    const selected = container.querySelector('.quiz-option.selected')?.dataset.key;
                    if (!selected) return;

                    submitBtn.textContent = '提交中...';
                    submitBtn.disabled = true;

                    try {
                        const response = await fetch('/api/quiz/grade', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                quiz_id: comp.id,
                                selected_key: selected,
                                question: comp.question,
                                options: comp.options  // 不含 is_correct
                            })
                        });
                        const result = await response.json();
                        this._showQuizFeedback(container, selected, result);
                    } catch (e) {
                        container.querySelector('.quiz-feedback').innerHTML =
                            `<div class="feedback-error">提交失败: ${e.message}</div>`;
                        container.querySelector('.quiz-feedback').style.display = 'block';
                        submitBtn.disabled = false;
                        submitBtn.textContent = '重新提交';
                    }
                });
            },

            // 显示 Quiz 反馈
            _showQuizFeedback(container, selected, result) {
                const feedback = container.querySelector('.quiz-feedback');
                const submitBtn = container.querySelector('.quiz-submit-btn');

                // 显示正确/错误状态
                const isCorrect = result.is_correct;
                const correctKey = result.correct_key || '';

                // 高亮正确选项
                container.querySelectorAll('.quiz-option').forEach(opt => {
                    if (opt.dataset.key === correctKey) {
                        opt.classList.add(isCorrect ? 'correct' : 'show-correct');
                    }
                    if (opt.dataset.key === selected && !isCorrect) {
                        opt.classList.add('wrong');
                    }
                });

                // 显示反馈
                feedback.innerHTML = `
                    <div class="feedback-result ${isCorrect ? 'correct' : 'wrong'}">
                        ${isCorrect ? '✓ 回答正确！' : '✗ 回答错误'}
                    </div>
                    <div class="feedback-explanation">${this._escapeHtml(result.explanation || '')}</div>
                `;
                feedback.style.display = 'block';
                submitBtn.textContent = isCorrect ? '已通过' : '继续学习';
            },

            // 渲染 CodeEditor 组件
            _renderCodeEditor(comp) {
                return `
                    <div class="code-editor-container" data-lang="${this._escapeHtml(comp.language)}">
                        <div class="code-header">
                            <span class="code-title">${this._escapeHtml(comp.title || '')}</span>
                            <span class="code-lang-badge">${(comp.language || 'TEXT').toUpperCase()}</span>
                        </div>
                        <div class="code-instruction">${this._escapeHtml(comp.instruction || '')}</div>
                        <div class="code-editor-area">
                            <textarea class="code-input">${this._escapeHtml(comp.starter_code || '')}</textarea>
                        </div>
                        <div class="code-actions">
                            <button class="code-run-btn">运行代码</button>
                            <button class="code-hint-btn">查看提示</button>
                        </div>
                        <div class="code-output" style="display:none"></div>
                        <div class="code-hints" style="display:none">
                            ${(comp.hints || []).map((h, i) => `<div class="hint-item">提示${i+1}: ${this._escapeHtml(h)}</div>`).join('')}
                        </div>
                    </div>
                `;
            },

            // CodeEditor 事件绑定
            _bindCodeEditorEvents(comp, element) {
                const runBtn = element.querySelector('.code-run-btn');
                const hintBtn = element.querySelector('.code-hint-btn');
                const output = element.querySelector('.code-output');
                const hints = element.querySelector('.code-hints');

                // 运行代码
                runBtn.addEventListener('click', async () => {
                    const code = element.querySelector('.code-input').value;
                    output.style.display = 'block';
                    output.innerHTML = '<div class="code-running">执行中...</div>';

                    try {
                        const response = await fetch('/api/run_code', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                code: code,
                                language: comp.language,
                                expected_output: comp.expected_output || ''
                            })
                        });
                        const result = await response.json();

                        if (result.success) {
                            const statusClass = result.passed ? 'success' : 'error';
                            const statusBadge = result.passed
                                ? '<div class="pass-badge">✓ 通过</div>'
                                : '<div class="fail-badge">✗ 未通过</div>';
                            output.innerHTML = `
                                <div class="output-result ${statusClass}">
                                    <div class="output-label">输出:</div>
                                    <pre class="output-text">${this._escapeHtml(result.actual_output || '(无输出)')}</pre>
                                    ${statusBadge}
                                </div>
                            `;
                        } else {
                            output.innerHTML = `<div class="code-error">错误: ${this._escapeHtml(result.error || '未知错误')}</div>`;
                        }
                    } catch (e) {
                        output.innerHTML = `<div class="code-error">执行失败: ${e.message}</div>`;
                    }
                });

                // 显示/隐藏提示
                hintBtn.addEventListener('click', () => {
                    const isVisible = hints.style.display !== 'none';
                    hints.style.display = isVisible ? 'none' : 'block';
                    hintBtn.textContent = isVisible ? '查看提示' : '隐藏提示';
                });
            },

            // 渲染 Simulation 组件
            _renderSimulation(comp) {
                return `
                    <div class="simulation-container">
                        <div class="simulation-header">
                            <span class="simulation-title">${this._escapeHtml(comp.title || '')}</span>
                        </div>
                        <div class="simulation-description">${this._escapeHtml(comp.description || '')}</div>
                        <div class="simulation-frame">
                            <iframe srcdoc="${this._escapeHtml(comp.html_content || '<p>无可用内容</p>')}"
                                    sandbox="allow-scripts"
                                    height="${comp.height || 400}">
                            </iframe>
                        </div>
                    </div>
                `;
            },

            // Simulation 事件绑定（暂无特殊交互）
            _bindSimulationEvents(comp, element) {
                // iframe sandbox 不需要额外绑定
            },

            // 辅助函数
            _getIcon(iconName) {
                const icons = {
                    'book': '📖', 'lightbulb': '💡', 'code': '💻',
                    'check': '✅', 'star': '⭐', 'question': '❓',
                    'warning': '⚠️', 'info': 'ℹ️'
                };
                return icons[iconName] || icons['book'];
            },

            _validateTheme(theme) {
                const themes = ['blue', 'yellow', 'green', 'purple', 'orange'];
                return themes.includes(theme) ? theme : 'blue';
            },

            _parseMarkdown(text) {
                if (!text) return '';
                let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
                html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
                const lines = html.split('\n');
                const processed = [];
                let inList = false;
                for (const line of lines) {
                    const m = line.match(/^-\s+(.+)/);
                    if (m) {
                        if (!inList) { processed.push('<ul>'); inList = true; }
                        processed.push(`<li>${m[1]}</li>`);
                    } else {
                        if (inList) { processed.push('</ul>'); inList = false; }
                        processed.push(line);
                    }
                }
                if (inList) processed.push('</ul>');
                html = processed.join('\n');
                html = html.replace(/\n/g, '<br>');
                return html;
            },

            _escapeHtml(str) {
                if (!str) return '';
                return str.replace(/&/g, '&amp;')
                          .replace(/</g, '&lt;')
                          .replace(/>/g, '&gt;')
                          .replace(/"/g, '&quot;')
                          .replace(/'/g, '&#039;');
            }
        };

        // TTS 播放控制（全局）
        initTTS() {
            window.ttsIsPlaying = false;
            document.addEventListener('click', (e) => {
                const ttsBtn = e.target.closest('.tts-play-btn');
                if (!ttsBtn) return;

                e.preventDefault();
                e.stopPropagation();

                if (window.ttsIsPlaying) {
                    window.speechSynthesis.cancel();
                    window.ttsIsPlaying = false;
                    const icon = ttsBtn.querySelector('.tts-icon');
                    const label = ttsBtn.querySelector('.tts-label');
                    if (icon) icon.textContent = '🔊';
                    if (label) label.textContent = '播放旁白';
                } else {
                    const script = decodeURIComponent(ttsBtn.dataset.script || '');
                    if (!script) return;

                    const utterance = new SpeechSynthesisUtterance(script);
                    utterance.lang = 'zh-CN';
                    utterance.rate = 1.0;

                    utterance.onstart = () => {
                        window.ttsIsPlaying = true;
                        const icon = ttsBtn.querySelector('.tts-icon');
                        const label = ttsBtn.querySelector('.tts-label');
                        if (icon) icon.textContent = '⏸';
                        if (label) label.textContent = '暂停';
                    };
                    utterance.onend = utterance.onerror = () => {
                        window.ttsIsPlaying = false;
                        const icon = ttsBtn.querySelector('.tts-icon');
                        const label = ttsBtn.querySelector('.tts-label');
                        if (icon) icon.textContent = '🔊';
                        if (label) label.textContent = '播放旁白';
                    };

                    window.speechSynthesis.cancel();
                    window.speechSynthesis.speak(utterance);
                }
            }, true);

            window.addEventListener('beforeunload', () => window.speechSynthesis?.cancel());
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) window.speechSynthesis?.cancel();
            });
        }

        renderSlideScene(scene) {
            if (!this.slideContainer) return;
            this.slideContainer.style.display = 'block';

            // Add transition animation
            this.slideContainer.style.animation = 'slideEnter 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';

            const slide = scene.slide;
            if (!slide) {
                this.slideContainer.innerHTML = `
                    <div class="slide-content slide-enter">
                        <h1 class="slide-title animate-in">${scene.title}</h1>
                        <p class="slide-description animate-in" style="animation-delay:0.2s">${scene.description}</p>
                    </div>
                `;
                return;
            }

            // Apply slide background with gradient/solid from theme
            this._applySlideBackground(slide);

            let html = `<div class="slide-header-bar"></div>`;
            html += `<div class="slide-content slide-enter">`;
            html += `<h1 class="slide-title animate-in">${slide.title || scene.title}</h1>`;
            html += `<div class="slide-body">`;

            // Get theme colors for styling
            const themeColors = slide.theme?.themeColors || ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#818cf8'];
            const fontColor = slide.theme?.fontColor || '#e2e8f0';
            const bgColor = slide.background?.color || slide.theme?.backgroundColor || '#1a1a2e';

            if (slide.content?.elements) {
                slide.content.elements.forEach((el, idx) => {
                    const elemId = el.id ? `id="elem-${el.id}"` : '';
                    const animDelay = `animation-delay:${idx * 0.12 + 0.1}s`;
                    const animClass = el.animation?.effect
                        ? ENTER_ANIMATIONS[el.animation.effect] || ENTER_ANIMATIONS.fadeUp
                        : ENTER_ANIMATIONS.fadeUp;

                    if (el.type === 'text') {
                        // Text elements: use absolute positioning for proper card layout
                        const textStyle = this._buildElementStyle(el);
                        // Determine background: transparent = no bg, otherwise use fill color
                        const hasBg = el.fill && el.fill !== 'transparent';
                        const bgStyle = hasBg ? `background:${el.fill};` : '';
                        // Text-specific styling (no glass effect for infographic style)
                        const textStyleStr = [
                            bgStyle,
                            `color:${el.default_color || fontColor || '#1E293B'}`,
                            `font-family:${el.default_font_name || 'Microsoft YaHei'}, sans-serif`,
                            `font-size:${el.font_size ? el.font_size * 0.1 : 15}px`,
                            `line-height:${el.line_height || 1.8}`,
                            `padding:${el.fill && el.fill !== 'transparent' ? '0.75rem 1rem' : '0'}`,
                            `word-wrap:break-word`,
                            `white-space:normal`,
                            `box-sizing:border-box`,
                        ].join(';');
                        // Parse markdown if content contains markdown syntax
                        let textContent = el.content || '';
                        if (textContent.includes('##') || textContent.includes('**') || textContent.includes('```') || textContent.includes('- ')) {
                            textContent = this.parseSimpleMarkdown(textContent);
                        } else {
                            textContent = textContent.replace(/\n/g, '<br>');
                        }
                        html += `<div class="slide-text ${animClass}" ${elemId} style="${textStyle};${textStyleStr};${animDelay}">${textContent}</div>`;
                    } else if (el.type === 'code') {
                        // Code elements: use absolute positioning for proper layout
                        const codeStyle = this._buildElementStyle(el);
                        html += `<pre class="slide-code ${animClass}" ${elemId} style="${codeStyle};${animDelay}"><code>${this.escapeHtml(el.content || '')}</code></pre>`;
                    } else if (el.type === 'image' && el.src) {
                        const imgStyle = this._buildElementStyle(el);
                        html += `<img class="slide-image ${animClass}" ${elemId} src="${el.src}" alt="" style="${imgStyle};${animDelay}" loading="lazy">`;
                    } else if (el.type === 'shape') {
                        const shapeStyle = this._buildShapeStyle(el);
                        html += `<div class="slide-shape ${animClass}" ${elemId} style="${shapeStyle};${animDelay}">${this._renderShapeContent(el)}</div>`;
                    } else if (el.type === 'chart' && el.chart_type) {
                        html += `<div class="slide-chart ${animClass}" ${elemId} data-chart-type="${el.chart_type}" style="height:220px;${animDelay}">${this._renderChartPlaceholder(el)}</div>`;
                    } else if (el.type === 'latex' && el.latex) {
                        html += `<div class="slide-latex ${animClass}" ${elemId} style="font-size:18px;${animDelay}">${this._renderLatex(el.latex)}</div>`;
                    } else if (el.type === 'table' && el.table_data) {
                        html += `<div class="slide-table ${animClass}" ${elemId} style="${animDelay}">${this._renderTable(el.table_data)}</div>`;
                    }
                });
            }

            html += '</div></div>';
            this.slideContainer.innerHTML = html;

            // Load and process scene actions after render
            this.loadSceneActions(scene);
        }

        _applySlideBackground(slide) {
            if (!slide || !this.slideContainer) return;

            const bg = slide.background || {};
            const theme = slide.theme || {};

            // Priority: explicit background > theme backgroundColor
            if (bg.type === 'gradient' && bg.gradient?.colors) {
                const colors = bg.gradient.colors.map(c => typeof c === 'string' ? c : c.color).join(', ');
                const angle = bg.gradient.rotate || 135;
                this.slideContainer.style.background = `linear-gradient(${angle}deg, ${colors})`;
            } else if (bg.type === 'solid' && bg.color) {
                this.slideContainer.style.backgroundColor = bg.color;
            } else if (theme.backgroundColor) {
                // Use theme background color
                this.slideContainer.style.backgroundColor = theme.backgroundColor;
            } else {
                // Default: use light background for infographic-style cards
                this.slideContainer.style.backgroundColor = '#FFFFFF';
            }
        }

        _buildTextElementStyle(el, themeColors, defaultFontColor) {
            const styles = [];

            // Width and height
            if (el.width !== undefined) styles.push(`width:${el.width * 0.1}px`);
            if (el.height !== undefined) styles.push(`height:${el.height * 0.1}px`);
            if (el.min_width) styles.push(`min-width:${el.min_width * 0.1}px`);
            if (el.min_height) styles.push(`min-height:${el.min_height * 0.1}px`);

            // Font styling - use theme colors if not specified
            const textColor = el.default_color || el.color || defaultFontColor || '#e2e8f0';
            styles.push(`color:${textColor}`);

            const fontName = el.default_font_name || 'Microsoft YaHei';
            styles.push(`font-family:${fontName}, sans-serif`);

            if (el.font_size) {
                styles.push(`font-size:${el.font_size * 0.1}px`);
            } else {
                styles.push(`font-size:16px`); // Default font size
            }

            if (el.font_weight) styles.push(`font-weight:${el.font_weight}`);
            if (el.line_height) styles.push(`line-height:${el.line_height}`);
            else styles.push(`line-height:1.7`); // Default line height for readability

            if (el.text_align) styles.push(`text-align:${el.text_align}`);

            // Background with subtle gradient or glass effect
            if (el.fill && el.fill !== 'transparent') {
                styles.push(`background:${el.fill}`);
            } else {
                // Default text card background - semi-transparent with blur
                styles.push(`background:rgba(99, 102, 241, 0.08)`);
                styles.push(`backdrop-filter:blur(10px)`);
            }

            // Border for cards
            styles.push(`border:1px solid rgba(255, 255, 255, 0.1)`);
            styles.push(`border-radius:12px`);

            // Padding for card content
            styles.push(`padding:1rem 1.25rem`);

            // Text shadow for better readability on dark backgrounds
            styles.push(`text-shadow:0 1px 2px rgba(0,0,0,0.3)`);

            return styles.join(';');
        }

        _renderShapeContent(el) {
            // Render SVG shape if path is provided
            if (el.path && el.view_box) {
                const vb = el.view_box;
                const vbStr = Array.isArray(vb) ? vb.join(' ') : vb;
                return `<svg viewBox="${vbStr}" style="width:100%;height:100%;overflow:visible;"><path d="${el.path}" fill="${el.fill || '#6366f1'}"/></svg>`;
            }
            // Fallback to CSS shapes
            const shapeName = (el.shape_name || 'rectangle').toLowerCase();
            if (shapeName === 'circle') return '';
            if (shapeName === 'triangle') return '';
            return '';
        }

        _renderChartPlaceholder(el) {
            const chartType = el.chart_type || 'bar';
            const chartData = el.chart_data || { labels: ['A', 'B', 'C'], series: [[100, 200, 150]] };
            const colors = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd'];
            let barsHtml = '';
            if (chartData.series && chartData.series[0]) {
                const max = Math.max(...chartData.series[0]);
                chartData.series[0].forEach((val, i) => {
                    const pct = (val / max) * 100;
                    const color = colors[i % colors.length];
                    barsHtml += `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">
                        <div style="width:100%;max-width:40px;height:${pct}%;background:${color};border-radius:4px 4px 0 0;"></div>
                        <span style="font-size:10px;color:#94a3b8;">${chartData.labels?.[i] || ''}</span>
                    </div>`;
                });
            }
            return `<div style="display:flex;align-items:flex-end;justify-content:center;gap:16px;height:100%;padding:16px;">${barsHtml}</div>`;
        }

        _renderLatex(latex) {
            // Simple LaTeX rendering - in production would use KaTeX or MathJax
            return `<span style="font-family:'Cambria Math','STIX Two Math',serif;font-size:1.2em;color:#1E293B;background:rgba(99,102,241,0.1);padding:8px 16px;border-radius:8px;display:inline-block;">${this.escapeHtml(latex)}</span>`;
        }

        /**
         * Simple markdown parser for slide text content.
         * Supports: ## headings, **bold**, - lists, ```code blocks```, > blockquote, `inline code`
         */
        parseSimpleMarkdown(text) {
            if (!text) return '';
            // Escape HTML first
            let html = this.escapeHtml(text);
            // Code blocks: ```lang\ncode\n``` → <pre><code>code</code></pre>
            html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
                return `<pre class="slide-md-code"><code>${code.trim()}</code></pre>`;
            });
            // Headings: ## text → <h2>text</h2>
            html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
            // Bold: **text** → <strong>text</strong>
            html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            // Italic: *text* → <em>text</em>
            html = html.replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>');
            // Inline code: `code` → <code class="slide-md-inline-code">code</code>
            html = html.replace(/`([^`\n]+)`/g, '<code class="slide-md-inline-code">$1</code>');
            // Blockquote: > text → <blockquote>text</blockquote>
            html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
            // Unordered lists: lines starting with - space → <li> items wrapped in <ul>
            const lines = html.split('\n');
            const processedLines = [];
            let inList = false;
            for (const line of lines) {
                const listMatch = line.match(/^(\s*)-\s+(.+)/);
                if (listMatch) {
                    if (!inList) {
                        processedLines.push('<ul class="slide-md-list">');
                        inList = true;
                    }
                    processedLines.push(`<li>${listMatch[2]}</li>`);
                } else {
                    if (inList) {
                        processedLines.push('</ul>');
                        inList = false;
                    }
                    processedLines.push(line);
                }
            }
            if (inList) processedLines.push('</ul>');
            html = processedLines.join('\n');
            // Convert remaining newlines to <br> (but not inside tags)
            html = html.replace(/\n/g, '<br>');
            return html;
        }

        _renderTable(tableData) {
            if (!tableData || !tableData.rows) return '<table class="data-table"><tr><td>No data</td></tr></table>';
            let html = '<table class="data-table" style="width:100%;border-collapse:collapse;">';
            tableData.rows.forEach((row, ri) => {
                html += '<tr>';
                row.forEach((cell, ci) => {
                    const isHeader = ri === 0;
                    html += `<td style="padding:12px;border:1px solid rgba(255,255,255,0.1);${isHeader ? 'background:rgba(99,102,241,0.2);font-weight:600;' : ''}">${this.escapeHtml(cell)}</td>`;
                });
                html += '</tr>';
            });
            html += '</table>';
            return html;
        }

        _buildLineStyle(el) {
            const styles = [];
            if (el.width) styles.push(`width:${el.width * 0.1}px`);
            if (el.height) styles.push(`height:${el.height * 0.1}px`);
            return styles.join(';');
        }

        _buildLineAttrs(el) {
            const attrs = [];
            if (el.start) attrs.push(`x1="${el.start[0] * 0.1}" y1="${el.start[1] * 0.1}"`);
            if (el.end) attrs.push(`x2="${el.end[0] * 0.1}" y2="${el.end[1] * 0.1}"`);
            if (el.color) attrs.push(`stroke="${el.color}"`);
            if (el.line_width || el.stroke_width) attrs.push(`stroke-width="${el.line_width || el.stroke_width || 2}"`);
            attrs.push(`vector-effect="non-scaling-stroke"`);
            return attrs.join(' ');
        }

        _buildElementStyle(el) {
            const styles = [];
            // Use position absolute for code/shape/image elements, but NOT text
            // Text elements should flow in document flow to prevent vertical stacking issues
            // Only use position:absolute for text when it has a fill (card background)
            if (el.type === 'code' || el.type === 'shape' || el.type === 'image') {
                styles.push(`position:absolute`);
            }
            if (el.type === 'text' && el.fill && el.fill !== 'transparent') {
                styles.push(`position:absolute`);
            }
            // Position and size (scaled for CSS)
            if (el.left !== undefined) styles.push(`left:${el.left * 0.1}px`);
            if (el.top !== undefined) styles.push(`top:${el.top * 0.1}px`);
            if (el.width !== undefined) styles.push(`width:${el.width * 0.1}px`);
            // For code elements, ensure minimum height for scrolling, scale height by 0.1
            if (el.height !== undefined) {
                const scaledHeight = Math.max(el.height * 0.1, 150); // Minimum 150px for code blocks
                styles.push(`height:${scaledHeight}px`);
            }
            if (el.min_width) styles.push(`min-width:${el.min_width * 0.1}px`);
            if (el.min_height) styles.push(`min-height:${el.min_height * 0.1}px`);

            // Background fill (solid color)
            if (el.fill) styles.push(`background:${el.fill}`);

            // Gradient fill
            if (el.gradient && el.gradient.colors) {
                const gradType = el.gradient.type === 'radial' ? 'radial-gradient' : 'linear-gradient';
                const angle = el.gradient.rotate || 0;
                const colors = el.gradient.colors.map(c => {
                    if (typeof c === 'string') return c;
                    return `${c.color} ${c.pos !== undefined ? c.pos + '%' : ''}`;
                }).join(', ');
                if (gradType === 'linear-gradient') {
                    styles.push(`background:${gradType}(${angle}deg, ${colors})`);
                } else {
                    styles.push(`background:${gradType}(circle at center, ${colors})`);
                }
            }

            // Text styling
            if (el.default_color) styles.push(`color:${el.default_color}`);
            if (el.default_font_name) styles.push(`font-family:${el.default_font_name}`);
            if (el.font_size) styles.push(`font-size:${el.font_size * 0.1}px`);
            if (el.font_weight) styles.push(`font-weight:${el.font_weight}`);
            if (el.line_height) styles.push(`line-height:${el.line_height}`);
            if (el.word_space) styles.push(`letter-spacing:${el.word_space}px`);
            if (el.text_align) styles.push(`text-align:${el.text_align}`);

            // Opacity
            if (el.opacity !== undefined && el.opacity < 1) styles.push(`opacity:${el.opacity}`);

            // Rotation
            if (el.rotate) styles.push(`transform:rotate(${el.rotate}deg)`);

            // Shadow - OpenMAIC style shadow
            if (el.shadow) {
                const { h = 0, v = 0, blur = 0, color = 'rgba(0,0,0,0.3)' } = el.shadow;
                styles.push(`filter:drop-shadow(${h * 0.1}px ${v * 0.1}px ${blur * 0.1}px ${color})`);
            }

            // Outline/border
            if (el.outline) {
                const ow = el.outline.width || 1;
                const oc = el.outline.color || '#6366f1';
                const os = el.outline.style || 'solid';
                if (os === 'dashed') {
                    styles.push(`border:${ow}px dashed ${oc}`);
                } else if (os === 'dotted') {
                    styles.push(`border:${ow}px dotted ${oc}`);
                } else {
                    styles.push(`border:${ow}px solid ${oc}`);
                }
            }

            // Border radius
            if (el.border_radius !== undefined) styles.push(`border-radius:${el.border_radius * 0.1}px`);

            // Vertical text
            if (el.vertical) styles.push(`writing-mode:vertical-rl`);

            // Paragraph spacing
            if (el.paragraph_space !== undefined) {
                styles.push(`margin-bottom:${el.paragraph_space * 0.1}px`);
            }

            return styles.join(';');
        }

        _buildShapeStyle(el) {
            const styles = [];
            // Position
            if (el.left !== undefined) styles.push(`position:absolute;left:${el.left * 0.1}px`);
            if (el.top !== undefined) styles.push(`top:${el.top * 0.1}px`);
            // Size
            if (el.width !== undefined) styles.push(`width:${el.width * 0.1}px`);
            if (el.height !== undefined) styles.push(`height:${el.height * 0.1}px`);
            // Opacity
            if (el.opacity !== undefined && el.opacity < 1) styles.push(`opacity:${el.opacity}`);
            // Rotation
            if (el.rotate) styles.push(`transform:rotate(${el.rotate}deg)`);
            // Shadow
            if (el.shadow) {
                const { h = 0, v = 0, blur = 0, color = 'rgba(0,0,0,0.3)' } = el.shadow;
                styles.push(`filter:drop-shadow(${h * 0.1}px ${v * 0.1}px ${blur * 0.1}px ${color})`);
            }
            // For CSS-only shapes (no SVG path)
            const shapeName = (el.shape_name || 'rectangle').toLowerCase();
            if (shapeName === 'circle' || shapeName === 'ellipse') {
                styles.push('border-radius:50%');
            } else if (shapeName === 'triangle') {
                styles.push('width:0;height:0;border-left:50px solid transparent;border-right:50px solid transparent;border-bottom:100px solid #6366f1;');
            } else {
                // Rectangle: apply fill and border-radius
                if (el.fill) styles.push(`background:${el.fill}`);
                if (el.border_radius !== undefined) styles.push(`border-radius:${el.border_radius}px`);
            }
            return styles.join(';');
        }

        loadSceneActions(scene) {
            const sceneActions = this.courseData.scene_actions || [];
            const actionData = sceneActions.find(a =>
                a.scene_id === scene.id ||
                a.scene_id === scene.slide?.id ||
                a.scene_index === this.currentIndex
            );
            if (actionData?.actions?.length > 0) {
                this.actionQueue = [...actionData.actions];
                this.processActionQueue();
            }
        }

        async processActionQueue() {
            if (this.isProcessingActions || this.actionQueue.length === 0) return;
            this.isProcessingActions = true;

            while (this.actionQueue.length > 0) {
                const action = this.actionQueue.shift();
                await this.processAction(action);
            }

            this.isProcessingActions = false;
        }

        async processAction(action) {
            const delay = action.delay || 0;
            const duration = action.duration || 1;

            if (delay > 0) {
                await this._sleep(delay * 1000);
            }

            switch (action.type) {
                case 'spotlight':
                    this.renderSpotlight(action.element_id, action.options);
                    await this._sleep(duration * 1000);
                    if (!action.persist) this.clearSpotlight();
                    break;

                case 'laser':
                    this.renderLaser(action.element_id, action.color || '#ff6b6b', action.options);
                    await this._sleep(duration * 1000);
                    if (!action.persist) this.clearLaser();
                    break;

                case 'speech':
                    await this.playSpeechAction(action.text, action.voice, action.speed);
                    break;

                case 'highlight':
                    this.highlightElement(action.element_id, action.color || 'var(--primary)');
                    break;

                case 'attention':
                    this.applyAttentionAnimation(action.element_id, action.effect || 'pulse');
                    break;

                case 'wb_open':
                    this.showWhiteboard(action.options);
                    break;

                case 'wb_close':
                    this.hideWhiteboard();
                    break;

                case 'wb_draw_text':
                    this.drawTextOnWhiteboard(action.text, action.x, action.y, action.style);
                    break;

                case 'wb_draw_shape':
                    this.drawShapeOnWhiteboard(action.shape || 'rectangle', action.x, action.y, action.size);
                    break;

                case 'wb_draw_line':
                    this.drawLineOnWhiteboard(action.start, action.end, action.color, action.width);
                    break;

                case 'transition':
                    this.executeSlideTransition(action.direction || 'next', action.effect || 'fade');
                    break;

                default:
                    console.warn('Unknown action type:', action.type);
            }
        }

        renderSpotlight(elementId, options = {}) {
            this.clearSpotlight();

            const targetElem = elementId ? document.getElementById(`elem-${elementId}`) : null;
            const overlay = document.createElement('div');
            overlay.id = 'spotlight-overlay';
            overlay.className = 'spotlight-overlay';

            let holeStyle = '';

            if (targetElem) {
                const rect = targetElem.getBoundingClientRect();
                const padding = 20;
                holeStyle = `
                    position: absolute;
                    left: ${rect.left - padding}px;
                    top: ${rect.top - padding}px;
                    width: ${rect.width + padding * 2}px;
                    height: ${rect.height + padding * 2}px;
                    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.75);
                    border-radius: 12px;
                    animation: spotlightPulse 2s ease-in-out infinite;
                `;

                // Highlight the element
                targetElem.style.transition = 'filter 0.4s ease, transform 0.4s ease';
                targetElem.style.filter = 'brightness(1.3) drop-shadow(0 0 20px var(--primary-glow))';
                targetElem.style.transform = 'scale(1.02)';

                this.spotlightElement = targetElem;
            }

            const hole = document.createElement('div');
            hole.style.cssText = holeStyle;
            overlay.appendChild(hole);
            this.actionOverlay.appendChild(overlay);
        }

        clearSpotlight() {
            const overlay = document.getElementById('spotlight-overlay');
            if (overlay) overlay.remove();

            if (this.spotlightElement) {
                this.spotlightElement.style.filter = '';
                this.spotlightElement.style.transform = '';
                this.spotlightElement = null;
            }

            // Clear all element highlights
            document.querySelectorAll('.slide-text, .slide-code, .slide-image, .slide-shape, .slide-latex, .slide-table').forEach(el => {
                el.style.filter = '';
                el.style.transform = '';
            });
        }

        renderLaser(elementId, color, options = {}) {
            this.clearLaser();

            const targetElem = elementId ? document.getElementById(`elem-${elementId}`) : null;
            const laserContainer = document.createElement('div');
            laserContainer.id = 'laser-overlay';
            laserContainer.className = 'laser-overlay';

            let cx = window.innerWidth / 2;
            let cy = window.innerHeight / 2;

            if (targetElem) {
                const rect = targetElem.getBoundingClientRect();
                cx = rect.left + rect.width / 2;
                cy = rect.top + rect.height / 2;

                // Highlight element with glow
                targetElem.style.transition = 'filter 0.3s ease';
                targetElem.style.filter = `brightness(1.2) drop-shadow(0 0 15px ${color})`;
            }

            laserContainer.innerHTML = `
                <div class="laser-dot" style="left:${cx}px;top:${cy}px;background:radial-gradient(circle, ${color} 0%, transparent 70%);"></div>
                <div class="laser-ring" style="left:${cx}px;top:${cy}px;border-color:${color};"></div>
                <svg width="100%" height="100%" style="position:absolute;top:0;left:0;pointer-events:none;">
                    <line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy}"
                          stroke="${color}" stroke-width="2" stroke-dasharray="5,5"
                          style="animation: laserTrace 0.5s ease forwards;">
                        <animate attributeName="x2" values="${cx};${cx + 50}" dur="0.5s" fill="freeze"/>
                        <animate attributeName="y2" values="${cy};${cy - 30}" dur="0.5s" fill="freeze"/>
                    </line>
                </svg>
            `;

            this.actionOverlay.appendChild(laserContainer);
        }

        clearLaser() {
            const laser = document.getElementById('laser-overlay');
            if (laser) laser.remove();

            document.querySelectorAll('.slide-text, .slide-code, .slide-image, .slide-shape, .slide-latex, .slide-table').forEach(el => {
                el.style.filter = '';
            });
        }

        highlightElement(elementId, color) {
            const elem = elementId ? document.getElementById(`elem-${elementId}`) : null;
            if (!elem) return;

            elem.style.transition = 'all 0.3s ease';
            elem.style.boxShadow = `0 0 30px ${color}, inset 0 0 20px ${color}`;
            elem.style.borderColor = color;

            setTimeout(() => {
                elem.style.boxShadow = '';
                elem.style.borderColor = '';
            }, 2000);
        }

        applyAttentionAnimation(elementId, effect) {
            const elem = elementId ? document.getElementById(`elem-${elementId}`) : null;
            if (!elem) return;

            const animClass = ATTENTION_ANIMATIONS[effect] || ATTENTION_ANIMATIONS.pulse;

            // Remove any existing attention animations
            Object.values(ATTENTION_ANIMATIONS).forEach(cls => {
                elem.classList.remove(cls);
            });

            // Force reflow to restart animation
            void elem.offsetWidth;
            elem.classList.add(animClass);

            // Remove after animation completes (except pulse which loops)
            if (effect !== 'pulse' && effect !== 'heartbeat') {
                setTimeout(() => {
                    elem.classList.remove(animClass);
                }, 2000);
            }
        }

        async executeSlideTransition(direction, effect) {
            if (this.isTransitioning) return;
            this.isTransitioning = true;

            const oldContainer = this.slideContainer;

            if (effect === 'fade') {
                oldContainer.style.animation = 'fadeOut 0.3s ease forwards';
                await this._sleep(300);
                this.renderScene(this.currentIndex);
                this.slideContainer.style.animation = 'fadeIn 0.4s ease forwards';
            } else if (effect === 'slideLeft') {
                oldContainer.style.animation = 'slideOutLeft 0.4s ease forwards';
                await this._sleep(400);
                this.renderScene(this.currentIndex);
                this.slideContainer.style.animation = 'slideInRight 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
            } else if (effect === 'slideRight') {
                oldContainer.style.animation = 'slideOutRight 0.4s ease forwards';
                await this._sleep(400);
                this.renderScene(this.currentIndex);
                this.slideContainer.style.animation = 'slideInLeft 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
            } else if (effect === 'zoom') {
                oldContainer.style.animation = 'zoomOut 0.4s ease forwards';
                await this._sleep(400);
                this.renderScene(this.currentIndex);
                this.slideContainer.style.animation = 'zoomIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
            }

            await this._sleep(500);
            this.isTransitioning = false;
        }

        async playSpeechAction(text, voiceId = null, speed = 1.0) {
            if (!text) return;

            this.speechText.textContent = text;
            this.showSpeechSyncIndicator(true);

            // Update teacher avatar to speaking state
            if (this.teacherAvatar) {
                this.teacherAvatar.classList.add('speaking');
            }

            // Try MiniMax TTS first
            const ttsResult = await this.generateTTS(text, voiceId, speed);

            if (ttsResult.success && this.audioPlayer) {
                // Play generated audio with sync
                this.audioPlayer.src = ttsResult.audioUrl;

                this.audioPlayer.onloadedmetadata = () => {
                    // Update speech progress
                    this.updateSpeechProgress();
                };

                this.audioPlayer.onended = () => {
                    this.showSpeechSyncIndicator(false);
                    if (this.teacherAvatar) {
                        this.teacherAvatar.classList.remove('speaking');
                    }
                };

                this.audioPlayer.onerror = () => {
                    // Fallback to browser TTS
                    this._speakText(text, voiceId, speed);
                };

                await this.audioPlayer.play().catch(() => {
                    this._speakText(text, voiceId, speed);
                });
            } else {
                // Fallback to browser TTS
                await this._speakText(text, voiceId, speed);
            }
        }

        _speakText(text, voiceId = null, speed = 1.0) {
            return new Promise((resolve) => {
                if (!window.speechSynthesis) {
                    resolve();
                    return;
                }

                // Cancel any ongoing speech
                window.speechSynthesis.cancel();

                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'zh-CN';
                utterance.rate = speed;

                // Map to browser voice if available
                if (voiceId && window.speechSynthesis.getVoices) {
                    const voices = window.speechSynthesis.getVoices();
                    const targetVoice = voices.find(v => v.lang.includes('zh'));
                    if (targetVoice) {
                        utterance.voice = targetVoice;
                    }
                }

                utterance.onstart = () => {
                    if (this.teacherAvatar) {
                        this.teacherAvatar.classList.add('speaking');
                    }
                    this.showSpeechSyncIndicator(true);
                };

                utterance.onend = () => {
                    if (this.teacherAvatar) {
                        this.teacherAvatar.classList.remove('speaking');
                    }
                    this.showSpeechSyncIndicator(false);
                    resolve();
                };

                utterance.onerror = () => {
                    if (this.teacherAvatar) {
                        this.teacherAvatar.classList.remove('speaking');
                    }
                    this.showSpeechSyncIndicator(false);
                    resolve();
                };

                window.speechSynthesis.speak(utterance);
            });
        }

        async generateTTS(text, voiceId = null, speed = 1.0) {
            const voice = voiceId || TTS_CONFIG.voice;
            const voiceConfig = MINIMAX_VOICES[voice] || MINIMAX_VOICES['female-yujie'];

            try {
                const response = await fetch('/api/socratic/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        voice_id: voiceConfig.voice_id,
                        speed: speed,
                        provider: 'minimax'
                    })
                });

                const data = await response.json();
                if (data.success && data.audio_url) {
                    return { success: true, audioUrl: data.audio_url };
                }
                return { success: false, error: 'TTS generation failed' };
            } catch (e) {
                console.error('TTS API error:', e);
                return { success: false, error: e.message };
            }
        }

        showSpeechSyncIndicator(show) {
            if (this.speechSync) {
                this.speechSync.style.display = show ? 'flex' : 'none';
                if (show) {
                    this.speechSync.classList.add('syncing');
                } else {
                    this.speechSync.classList.remove('syncing');
                }
            }
        }

        updateSpeechProgress() {
            if (!this.audioPlayer || !this.speechSync) return;

            const progress = (this.audioPlayer.currentTime / this.audioPlayer.duration) * 100;
            const progressBar = this.speechSync.querySelector('.sync-progress');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
        }

        showWhiteboard(options = {}) {
            let wb = document.getElementById('whiteboard-overlay');

            const colors = options.colors || ['#6366f1', '#8b5cf6', '#ef4444', '#10b981', '#f59e0b', '#000000'];
            const tools = options.tools || ['pen', 'rectangle', 'circle', 'line', 'text', 'eraser'];

            if (!wb) {
                wb = document.createElement('div');
                wb.id = 'whiteboard-overlay';
                wb.style.cssText = `
                    position:fixed;top:0;left:0;width:100%;height:100%;
                    background:rgba(0,0,0,0.85);z-index:10000;
                    display:flex;align-items:center;justify-content:center;
                    animation: fadeIn 0.3s ease;
                `;

                wb.innerHTML = `
                    <div class="whiteboard-container" style="
                        width:90%;max-width:1000px;height:85%;
                        background:#fff;border-radius:20px;
                        box-shadow:0 25px 80px rgba(0,0,0,0.5);
                        display:flex;flex-direction:column;overflow:hidden;
                    ">
                        <div class="wb-header" style="
                            display:flex;align-items:center;justify-content:space-between;
                            padding:12px 20px;background:linear-gradient(135deg,var(--primary),var(--accent));
                            color:white;
                        ">
                            <div class="wb-title" style="font-size:16px;font-weight:600;">
                                <i class="fas fa-chalkboard"></i> 电子白板
                            </div>
                            <div class="wb-tools" style="display:flex;gap:8px;">
                                ${tools.map(t => `
                                    <button class="wb-tool-btn" data-tool="${t}" style="
                                        width:36px;height:36px;border:none;border-radius:8px;
                                        background:rgba(255,255,255,0.2);color:white;
                                        cursor:pointer;font-size:14px;transition:all 0.2s;
                                    " title="${t}">
                                        <i class="fas fa-${this._getToolIcon(t)}"></i>
                                    </button>
                                `).join('')}
                            </div>
                            <div class="wb-colors" style="display:flex;gap:6px;">
                                ${colors.map(c => `
                                    <button class="wb-color-btn" data-color="${c}" style="
                                        width:24px;height:24px;border-radius:50%;
                                        background:${c};border:2px solid transparent;
                                        cursor:pointer;transition:all 0.2s;
                                    "></button>
                                `).join('')}
                            </div>
                            <button class="wb-close-btn" style="
                                width:36px;height:36px;border:none;border-radius:50%;
                                background:rgba(255,255,255,0.2);color:white;
                                cursor:pointer;font-size:18px;transition:all 0.2s;
                            ">×</button>
                        </div>
                        <canvas id="whiteboard-canvas" style="
                            flex:1;cursor:crosshair;
                        "></canvas>
                    </div>
                `;

                document.body.appendChild(wb);

                // Initialize canvas after DOM insert
                this._initWhiteboardCanvas(wb, options);

                // Event listeners
                wb.querySelector('.wb-close-btn').addEventListener('click', () => this.hideWhiteboard());
                wb.querySelectorAll('.wb-tool-btn').forEach(btn => {
                    btn.addEventListener('click', () => this._selectWhiteboardTool(btn.dataset.tool));
                });
                wb.querySelectorAll('.wb-color-btn').forEach(btn => {
                    btn.addEventListener('click', () => this._selectWhiteboardColor(btn.dataset.color));
                });
            }

            wb.style.display = 'flex';
            this.whiteboardVisible = true;
        }

        _initWhiteboardCanvas(wb, options) {
            const canvas = wb.querySelector('#whiteboard-canvas');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const rect = wb.querySelector('.whiteboard-container').getBoundingClientRect();

            canvas.width = rect.width;
            canvas.height = rect.height - 56; // minus header

            // Drawing state
            let drawing = false;
            let lastX = 0, lastY = 0;
            let currentTool = 'pen';
            let currentColor = options.colors?.[0] || '#6366f1';
            let lineWidth = 3;

            const startDraw = (e) => {
                drawing = true;
                const pos = this._getCanvasPos(canvas, e);
                lastX = pos.x;
                lastY = pos.y;

                if (currentTool === 'rectangle' || currentTool === 'circle') {
                    // Store start for shape drawing
                    canvas.dataset.startX = lastX;
                    canvas.dataset.startY = lastY;
                }
            };

            const draw = (e) => {
                if (!drawing) return;
                const pos = this._getCanvasPos(canvas, e);

                ctx.strokeStyle = currentColor;
                ctx.lineWidth = lineWidth;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';

                if (currentTool === 'pen') {
                    ctx.beginPath();
                    ctx.moveTo(lastX, lastY);
                    ctx.lineTo(pos.x, pos.y);
                    ctx.stroke();
                }

                lastX = pos.x;
                lastY = pos.y;
            };

            const endDraw = (e) => {
                if (!drawing) return;
                drawing = false;

                if (currentTool === 'rectangle' || currentTool === 'circle') {
                    const startX = parseFloat(canvas.dataset.startX);
                    const startY = parseFloat(canvas.dataset.startY);
                    const pos = this._getCanvasPos(canvas, e);

                    ctx.strokeStyle = currentColor;
                    ctx.lineWidth = lineWidth;

                    if (currentTool === 'rectangle') {
                        ctx.strokeRect(startX, startY, pos.x - startX, pos.y - startY);
                    } else if (currentTool === 'circle') {
                        const r = Math.sqrt(Math.pow(pos.x - startX, 2) + Math.pow(pos.y - startY, 2));
                        ctx.beginPath();
                        ctx.arc(startX, startY, r, 0, Math.PI * 2);
                        ctx.stroke();
                    }
                }
            };

            canvas.addEventListener('mousedown', startDraw);
            canvas.addEventListener('mousemove', draw);
            canvas.addEventListener('mouseup', endDraw);
            canvas.addEventListener('mouseleave', () => drawing = false);

            // Touch support
            canvas.addEventListener('touchstart', (e) => {
                e.preventDefault();
                startDraw(e.touches[0]);
            });
            canvas.addEventListener('touchmove', (e) => {
                e.preventDefault();
                draw(e.touches[0]);
            });
            canvas.addEventListener('touchend', endDraw);
        }

        _getCanvasPos(canvas, e) {
            const rect = canvas.getBoundingClientRect();
            return {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
        }

        _getToolIcon(tool) {
            const icons = {
                pen: 'pen',
                rectangle: 'square-o',
                circle: 'circle-o',
                line: 'minus',
                text: 'font',
                eraser: 'eraser'
            };
            return icons[tool] || 'pen';
        }

        _selectWhiteboardTool(tool) {
            document.querySelectorAll('.wb-tool-btn').forEach(btn => {
                btn.style.background = btn.dataset.tool === tool
                    ? 'rgba(255,255,255,0.4)'
                    : 'rgba(255,255,255,0.2)';
            });
            this.currentWhiteboardTool = tool;
        }

        _selectWhiteboardColor(color) {
            document.querySelectorAll('.wb-color-btn').forEach(btn => {
                btn.style.borderColor = btn.dataset.color === color ? 'white' : 'transparent';
            });
            this.currentWhiteboardColor = color;
        }

        hideWhiteboard() {
            const wb = document.getElementById('whiteboard-overlay');
            if (wb) wb.style.display = 'none';
            this.whiteboardVisible = false;
        }

        drawOnWhiteboard(content) {
            const canvas = document.getElementById('whiteboard-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.font = '20px Microsoft YaHei';
            ctx.fillStyle = '#333';
            ctx.fillText(content, 50, 50);
        }

        drawTextOnWhiteboard(text, x = 50, y = 50, style = {}) {
            const canvas = document.getElementById('whiteboard-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.font = `${style.fontSize || 20}px ${style.fontFamily || 'Microsoft YaHei'}`;
            ctx.fillStyle = style.color || '#333';
            ctx.fillText(text, x, y);
        }

        drawLineOnWhiteboard(start, end, color = '#6366f1', width = 3) {
            const canvas = document.getElementById('whiteboard-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(start.x || start[0], start.y || start[1]);
            ctx.lineTo(end.x || end[0], end.y || end[1]);
            ctx.stroke();
        }

        drawShapeOnWhiteboard(shapeType) {
            const canvas = document.getElementById('whiteboard-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.strokeStyle = '#8b5cf6';
            ctx.lineWidth = 3;

            const cx = 350, cy = 225, r = 60;
            ctx.beginPath();
            if (shapeType === 'circle') {
                ctx.arc(cx, cy, r, 0, Math.PI * 2);
            } else if (shapeType === 'triangle') {
                ctx.moveTo(cx, cy - r);
                ctx.lineTo(cx - r, cy + r);
                ctx.lineTo(cx + r, cy + r);
                ctx.closePath();
            } else {
                ctx.rect(cx - r, cy - r, r * 2, r * 2);
            }
            ctx.stroke();
        }

        _sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        renderQuizScene(scene) {
            if (!this.quizContainer) return;
            this.quizContainer.style.display = 'block';
            this.quizContainer.style.animation = 'fadeInUp 0.5s ease';

            const quiz = scene.quiz;
            const header = document.getElementById('quiz-header');
            const questions = document.getElementById('quiz-questions');
            const submitBtn = document.getElementById('quiz-submit-btn');
            const result = document.getElementById('quiz-result');

            if (header) {
                header.innerHTML = `
                    <i class="fas fa-pencil-alt"></i>
                    <span>${quiz?.title || scene.title}</span>
                    <span class="quiz-progress">(${this.currentIndex + 1}/${this.scenes.length})</span>
                `;
            }
            if (result) result.style.display = 'none';

            if (!quiz?.questions?.length) {
                if (questions) questions.innerHTML = '<p class="text-muted">此测验暂无题目</p>';
                return;
            }

            if (questions) {
                questions.innerHTML = quiz.questions.map((q, qi) => `
                    <div class="quiz-question" data-question="${qi}" style="animation-delay:${qi * 0.1}s">
                        <div class="quiz-question-text">
                            <span class="question-number">${qi + 1}</span>
                            <span class="question-content">${q.question || ''}</span>
                        </div>
                        <div class="quiz-options">
                            ${(q.options || []).map((opt, oi) => `
                                <label class="quiz-option" data-q="${qi}" data-opt="${oi}">
                                    <input type="radio" name="q_${qi}" value="${oi}">
                                    <span class="option-letter">${String.fromCharCode(65 + oi)}</span>
                                    <span class="option-text">${opt.label || opt}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                `).join('');

                // Add click handlers with animation
                questions.querySelectorAll('.quiz-option').forEach(option => {
                    option.addEventListener('click', () => {
                        const qIdx = option.dataset.q;
                        const options = document.querySelectorAll(`.quiz-option[data-q="${qIdx}"]`);

                        // Remove selected from siblings
                        options.forEach(opt => opt.classList.remove('selected'));

                        // Add selected to clicked
                        option.classList.add('selected');

                        // Update radio
                        const radio = option.querySelector('input[type="radio"]');
                        if (radio) radio.checked = true;

                        // Animate selection
                        option.style.animation = 'bounceIn 0.3s ease';
                    });
                });
            }

            if (submitBtn) {
                submitBtn.style.display = 'block';
                submitBtn.innerHTML = '<span>提交答案</span><i class="fas fa-arrow-right"></i>';
                submitBtn.onclick = () => this.submitQuiz(scene);
            }
        }

        renderExerciseScene(scene) {
            if (!this.exerciseContainer) return;
            this.exerciseContainer.style.display = 'block';
            const data = scene.exercise;
            const content = document.getElementById('exercise-content');
            const hints = document.getElementById('exercise-hints');
            const answer = document.getElementById('exercise-answer');
            const submitBtn = document.getElementById('exercise-submit-btn');

            if (content) {
                const exercises = data?.exercises || [];
                content.innerHTML = exercises.length > 0
                    ? exercises.map((ex, i) => `<div class="exercise-item"><h4>练习 ${i+1}</h4><p>${ex.instruction || ''}</p></div>`).join('')
                    : `<h3>${scene.title}</h3><p>${scene.description}</p>`;
            }
            if (hints && data?.exercises?.[0]?.hints) {
                hints.innerHTML = '<strong>提示：</strong>' + data.exercises[0].hints.map(h => `<span class="hint-badge">${h}</span>`).join('');
                hints.style.display = 'block';
            }
            if (answer) answer.value = '';
            if (submitBtn) submitBtn.onclick = () => {
                const ans = answer?.value.trim();
                if (ans) {
                    this.addChatMessage('user', `练习答案：${ans}`);
                    this.sendExerciseAnswer(scene, ans);
                }
            };
        }

        renderInteractiveScene(scene) {
            if (!this.interactiveContainer) return;
            this.interactiveContainer.style.display = 'block';
            const iframe = document.getElementById('interactive-iframe');

            // Check for enhanced interactive data with widget_type
            const interactiveData = this.courseData.interactive_data?.find(i => i.id === scene.id);
            const widgetType = interactiveData?.widget_type;
            const htmlContent = interactiveData?.html_content || interactiveData?.html;

            if (iframe) {
                if (htmlContent) {
                    // Render actual interactive HTML content
                    iframe.srcdoc = htmlContent;
                } else if (widgetType) {
                    // Render placeholder with widget type
                    iframe.srcdoc = `<html><body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#1a1a2e;color:#e0e7ff;margin:0;">
                        <div style="text-align:center;padding:2rem;">
                            <div style="font-size:4rem;margin-bottom:1rem;">${widgetType === 'simulation' ? '🔬' : widgetType === 'diagram' ? '📊' : widgetType === 'code' ? '💻' : widgetType === 'game' ? '🎮' : widgetType === 'visualization3d' ? '🌐' : '🎯'}</div>
                            <h2>${scene.title}</h2>
                            <p style="color:#a0aec0;">${scene.description || '交互式学习内容'}</p>
                            <p style="color:#6366f1;font-size:0.9rem;margin-top:1rem;">Widget类型: ${widgetType}</p>
                        </div></body></html>`;
                } else {
                    // Basic placeholder
                    iframe.srcdoc = `<html><body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#1a1a2e;color:#e0e7ff;">
                        <div style="text-align:center;"><h2>${scene.title}</h2><p>${scene.description}</p></div></body></html>`;
                }
            }
        }

        updateTeacherSpeech(scene) {
            if (!this.speechText) return;
            const speech = scene.slide?.speech || scene.quiz?.speech || scene.description || '';
            this.speechText.textContent = speech || `现在讲解：${scene.title}`;

            // Update avatar if agent team has different teachers per scene
            const teacherIdx = scene.teacher_index || 0;
            const agent = this.agentTeam[teacherIdx];
            if (agent && this.teacherAvatar) {
                if (agent.avatar && agent.avatar.startsWith('http')) {
                    this.teacherAvatar.innerHTML = `<img src="${agent.avatar}" alt="${agent.name}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                } else if (agent.name) {
                    const initials = agent.name.slice(0, 2).toUpperCase();
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;font-weight:700;color:white;">${initials}</span>`;
                } else {
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;">👩‍🏫</span>`;
                }
            }
        }

        // ---- Audio / TTS ----

        playSceneAudio(scene) {
            this.stopAudio();
            const url = scene.audioUrl
                || scene.slide?.content?.elements?.find(el => el.audio_url)?.audio_url
                || scene.slide?.content?.elements?.[0]?.audio_url;

            if (url && this.audioPlayer) {
                this.speechSync.style.display = 'flex';
                this.audioPlayer.src = url;
                this.audioPlayer.play().catch(() => this.fallbackTTS(scene));
                this.audioPlayer.onended = () => {
                    this.speechSync.style.display = 'none';
                    if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                        setTimeout(() => this.nextScene(), 800);
                    }
                };
            } else if (scene.slide?.speech) {
                this.fallbackTTS(scene);
            }
        }

        fallbackTTS(scene) {
            const text = scene.slide?.speech || scene.quiz?.speech || '';
            if (!text || !window.speechSynthesis) return;
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'zh-CN';
            utterance.rate = 1.0;
            this.speechSync.style.display = 'flex';
            utterance.onend = () => {
                this.speechSync.style.display = 'none';
                if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                    setTimeout(() => this.nextScene(), 800);
                }
            };
            window.speechSynthesis.speak(utterance);
        }

        toggleVoice() {
            this.isPlaying = !this.isPlaying;
            this.voiceBtn?.classList.toggle('playing', this.isPlaying);
            const icon = this.voiceBtn?.querySelector('i');
            if (icon) icon.className = this.isPlaying ? 'fas fa-volume-mute' : 'fas fa-volume-up';
            if (this.isPlaying) this.playSceneAudio(this.scenes[this.currentIndex]);
            else this.stopAudio();
        }

        stopAudio() {
            if (this.audioPlayer) { this.audioPlayer.pause(); this.audioPlayer.src = ''; }
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            if (this.speechSync) this.speechSync.style.display = 'none';
        }

        replaySpeech() { this.playSceneAudio(this.scenes[this.currentIndex]); }
        pauseSpeech() {
            if (this.audioPlayer?.paused === false) this.audioPlayer.pause();
            else this.audioPlayer?.play().catch(() => {});
            if (window.speechSynthesis.paused) window.speechSynthesis.resume();
            else if (window.speechSynthesis.speaking) window.speechSynthesis.pause();
        }

        // ---- Quiz ----

        async submitQuiz(scene) {
            const quiz = scene.quiz;
            if (!quiz?.questions) return;

            const answers = [];
            let hasAnswer = false;

            quiz.questions.forEach((q, qi) => {
                const sel = document.querySelector(`input[name="q_${qi}"]:checked`);
                answers.push({ question_index: qi, selected_option: sel ? parseInt(sel.value) : -1 });
                if (sel) hasAnswer = true;
            });

            if (!hasAnswer) {
                // Shake the quiz container
                this.quizContainer.style.animation = 'shake 0.5s ease';
                setTimeout(() => {
                    this.quizContainer.style.animation = '';
                }, 500);
                return;
            }

            // Animate checking
            const questions = document.querySelectorAll('.quiz-question');
            questions.forEach((q, i) => {
                setTimeout(() => {
                    q.style.animation = 'pulse 0.5s ease';
                }, i * 150);
            });

            await this._sleep(questions.length * 150 + 300);

            // Show correct/wrong with animations
            quiz.questions.forEach((q, qi) => {
                const options = document.querySelectorAll(`.quiz-option[data-q="${qi}"]`);
                const correctOpt = options[parseInt(q.correct_answer)];

                // First show wrong answers
                options.forEach((opt, oi) => {
                    if (oi !== q.correct_answer) {
                        const sel = opt.querySelector('input[type="radio"]');
                        if (sel && sel.checked) {
                            opt.classList.add('wrong');
                            opt.style.animation = 'shake 0.5s ease';
                        }
                    }
                });

                // Then highlight correct
                setTimeout(() => {
                    if (correctOpt) {
                        correctOpt.classList.add('correct');
                        correctOpt.style.animation = 'bounceIn 0.5s ease';
                    }
                }, 500);
            });

            await this._sleep(800);

            // Calculate and show result
            const correct = answers.filter((a, i) =>
                a.selected_option === (quiz.questions[i]?.correct_answer || 0)
            ).length;
            const total = quiz.questions.length;
            const percentage = Math.round((correct / total) * 100);
            const passed = percentage >= 60;

            const resultEl = document.getElementById('quiz-result');
            const submitBtn = document.getElementById('quiz-submit-btn');

            if (resultEl) {
                resultEl.style.display = 'block';
                resultEl.style.animation = 'zoomIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
                resultEl.innerHTML = `
                    <div class="quiz-score ${passed ? 'passed' : 'failed'}">${percentage}%</div>
                    <div class="quiz-score-label">
                        ${passed ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-times-circle"></i>'}
                        答对 ${correct}/${total} 题 ${passed ? '通过' : '未通过'}
                    </div>
                    <div class="quiz-feedback">
                        ${passed ? '太棒了！继续加油！' : '别灰心，再试试看！'}
                    </div>
                `;
            }

            if (submitBtn) {
                submitBtn.innerHTML = passed
                    ? '<span>继续学习</span><i class="fas fa-forward"></i>'
                    : '<span>重新答题</span><i class="fas fa-redo"></i>';
                submitBtn.onclick = passed ? () => this.nextScene() : () => this.renderScene(this.currentIndex);
            }

            this.quizAnswers[scene.id] = answers;
            this.checkCompletion();
        }

        // ---- Exercise ----

        async sendExerciseAnswer(scene, answer) {
            try {
                const resp = await fetch('/api/v2/course/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: this.courseData.metadata?.student_id || '',
                        course_id: this.courseData.courseId || '',
                        slide_index: this.currentIndex,
                        slide_title: scene.title,
                        slide_content: JSON.stringify(scene.exercise || {}),
                        speech: scene.description || '',
                        user_input: `我的练习答案是：${answer}。请评估并给出反馈。`,
                        history: []
                    })
                });
                const data = await resp.json();
                this.addChatMessage('teacher', data.content || '收到你的答案，做得不错！');
            } catch (e) {
                this.addChatMessage('teacher', '收到你的答案！请继续下一场景。');
            }
        }

        // ---- Chat ----

        async sendMessage() {
            const text = this.chatInput?.value.trim();
            if (!text || this.isChatLoading) return;

            this.addChatMessage('user', text);
            if (this.chatInput) this.chatInput.value = '';

            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message teacher';
            loadingDiv.id = 'chat-loading';
            const teacher = this.courseData?.teacher;
            let teacherAvatarHtml;
            if (teacher?.avatar && teacher.avatar.startsWith('http')) {
                teacherAvatarHtml = `<img src="${teacher.avatar}" alt="教师" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
            } else if (teacher?.name) {
                const initials = teacher.name.slice(0, 2).toUpperCase();
                teacherAvatarHtml = `<span style="font-size:0.8rem;font-weight:700;color:white;">${initials}</span>`;
            } else {
                teacherAvatarHtml = `<i class="fas fa-chalkboard-teacher" style="color:white;"></i>`;
            }
            loadingDiv.innerHTML = `<div class="message-avatar">${teacherAvatarHtml}</div><div class="message-bubble"><p>思考中...</p></div>`;
            this.chatMessages?.appendChild(loadingDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            this.isChatLoading = true;

            const scene = this.scenes[this.currentIndex];
            const agentId = this.chatAgentSelect?.value || '';

            try {
                const resp = await fetch('/api/v2/course/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: this.courseData.metadata?.student_id || '',
                        course_id: this.courseData.courseId || '',
                        slide_index: this.currentIndex,
                        slide_title: scene?.title || '',
                        slide_content: scene?.slide?.content?.elements?.map(e => e.content).join('\n') || '',
                        speech: scene?.slide?.speech || scene?.quiz?.speech || '',
                        user_input: text,
                        history: this.chatHistory.slice(-10),
                        agent_role: agentId ? (this.agentTeam.find(a => a.id === agentId)?.role || 'AI助教') : 'AI助教',
                    })
                });
                const data = await resp.json();
                document.getElementById('chat-loading')?.remove();
                this.addChatMessage('teacher', data.content || '抱歉，暂时无法回答。');
                if (data.success) {
                    this.chatHistory.push({ role: 'user', content: text });
                    this.chatHistory.push({ role: 'assistant', content: data.content });
                }
            } catch (e) {
                document.getElementById('chat-loading')?.remove();
                this.addChatMessage('teacher', '网络异常，请稍后重试。');
            } finally {
                this.isChatLoading = false;
            }
        }

        addChatMessage(type, text) {
            if (!this.chatMessages) return;
            const div = document.createElement('div');
            div.className = `message ${type}`;

            let avatarHtml;
            if (type === 'teacher') {
                const teacher = this.courseData?.teacher;
                if (teacher?.avatar && teacher.avatar.startsWith('http')) {
                    avatarHtml = `<img src="${teacher.avatar}" alt="教师" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                } else if (teacher?.name) {
                    const initials = teacher.name.slice(0, 2).toUpperCase();
                    avatarHtml = `<span style="font-size:0.8rem;font-weight:700;color:white;">${initials}</span>`;
                } else {
                    avatarHtml = `<i class="fas fa-chalkboard-teacher" style="color:white;"></i>`;
                }
            } else {
                avatarHtml = `<i class="fas fa-user" style="color:var(--accent-light);"></i>`;
            }

            div.innerHTML = `<div class="message-avatar">${avatarHtml}</div><div class="message-bubble"><p>${this.escapeHtml(text)}</p></div>`;
            this.chatMessages.appendChild(div);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }

        // ---- Navigation ----

        goToScene(index) { this.renderScene(index); }
        prevScene() { if (this.currentIndex > 0) this.renderScene(this.currentIndex - 1); }
        nextScene() { if (this.currentIndex < this.scenes.length - 1) this.renderScene(this.currentIndex + 1); }

        updateNav() {
            const total = this.scenes.length;
            if (this.currentSlideEl) this.currentSlideEl.textContent = this.currentIndex + 1;
            if (this.totalSlidesEl) this.totalSlidesEl.textContent = total;
            if (this.prevBtn) this.prevBtn.disabled = this.currentIndex === 0;
            if (this.nextBtn) this.nextBtn.disabled = this.currentIndex === total - 1;
            if (this.progressFill) this.progressFill.style.width = `${((this.currentIndex + 1) / total) * 100}%`;
        }

        // ---- Completion ----

        checkCompletion() {
            const allVisited = this.scenes.every((_, i) => this.visitedScenes.has(i) || i === this.currentIndex);
            const quizScenes = this.scenes.filter(s => s.type === 'quiz');
            const allQuizzesDone = quizScenes.every(s => this.quizAnswers[s.id]);
            if (allVisited && (quizScenes.length === 0 || allQuizzesDone)) {
                this.showCompletion();
            }
        }

        async showCompletion() {
            if (this.completionOverlay.style.display === 'flex') return;
            this.stopAudio();
            this.completionOverlay.style.display = 'flex';
            this.startConfetti();

            // Compute quiz score
            let totalScore = 0;
            let quizCount = 0;
            Object.values(this.quizAnswers).forEach(answers => {
                if (Array.isArray(answers)) {
                    answers.forEach(a => { if (a.selected_option >= 0) quizCount++; });
                }
            });
            const completedScenes = this.visitedScenes.size + 1;

            try {
                const resp = await fetch('/api/v2/course/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        course_id: this.courseData.courseId || '',
                        student_id: this.courseData.metadata?.student_id || '',
                        quiz_score: totalScore,
                        time_spent: this.totalTimeSpent,
                        scenes_visited: [...this.visitedScenes, this.currentIndex],
                        total_scenes: this.scenes.length,
                    })
                });
                const data = await resp.json();
                this.renderCompletionStats(data, completedScenes);
            } catch (e) {
                this.renderCompletionStats({ badges: ['课堂参与者'], next_steps: ['回顾重点内容'], summary: '恭喜完成课程！' }, completedScenes);
            }
        }

        renderCompletionStats(data, completed) {
            const subtitle = document.getElementById('completion-subtitle');
            const stats = document.getElementById('completion-stats');
            const badges = document.getElementById('completion-badges');
            const next = document.getElementById('completion-next');

            if (subtitle) subtitle.textContent = data.summary || `完成了 ${completed} 个学习场景`;
            if (stats) stats.innerHTML = `
                <div class="completion-stat"><span class="stat-value">${completed}</span><span class="stat-label">完成场景</span></div>
                <div class="completion-stat"><span class="stat-value">${data.quiz_score || '-'}%</span><span class="stat-label">测验成绩</span></div>
                <div class="completion-stat"><span class="stat-value">${Math.floor(this.totalTimeSpent / 60)}分钟</span><span class="stat-label">学习时长</span></div>
            `;
            if (badges) badges.innerHTML = (data.badges || []).map(b =>
                `<span class="completion-badge">${b}</span>`).join('');
            if (next) next.innerHTML = '<h4>下一步建议</h4>' + (data.next_steps || []).map(s =>
                `<p class="next-step-item">${s}</p>`).join('');
        }

        startConfetti() {
            const canvas = document.getElementById('confetti-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            const particles = Array.from({ length: 80 }, () => ({
                x: Math.random() * canvas.width,
                y: -20 - Math.random() * 100,
                w: Math.random() * 8 + 4,
                h: Math.random() * 5 + 2,
                color: `hsl(${Math.random() * 360}, 80%, ${50 + Math.random() * 20}%)`,
                vy: Math.random() * 2 + 1.5,
                vx: (Math.random() - 0.5) * 2,
                rot: Math.random() * 360,
                rv: (Math.random() - 0.5) * 4,
            }));

            const animate = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                let done = true;
                particles.forEach(p => {
                    if (p.y < canvas.height + 20) {
                        p.y += p.vy;
                        p.x += p.vx;
                        p.rot += p.rv;
                        done = false;
                    }
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate(p.rot * Math.PI / 180);
                    ctx.fillStyle = p.color;
                    ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
                    ctx.restore();
                });
                if (!done) requestAnimationFrame(animate);
            };
            animate();
        }

        // ---- Exit ----

        showExitModal() { const el = document.getElementById('exit-modal'); if (el) el.style.display = 'flex'; }
        hideExitModal() { const el = document.getElementById('exit-modal'); if (el) el.style.display = 'none'; }
        confirmExit() {
            this.stopAudio();
            sessionStorage.removeItem('generationSession');
            window.location.href = '/index.html';
        }

        // ---- Chat Voice Input (Speech Recognition) ----

        initChatVoiceInput() {
            const btn = this.chatVoiceBtn;
            const input = this.chatInput;
            if (!btn || !input) return;

            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.chatRecognition = new SpeechRecognition();
                this.chatRecognition.continuous = true;
                this.chatRecognition.interimResults = true;
                this.chatRecognition.lang = 'zh-CN';

                this.chatRecognition.onstart = () => {
                    this.chatIsRecording = true;
                    btn.classList.add('recording');
                    btn.querySelector('i')?.classList.replace('fa-microphone', 'fa-stop');
                };

                this.chatRecognition.onresult = (event) => {
                    let finalTranscript = '';
                    let newInterim = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            finalTranscript += transcript;
                        } else {
                            newInterim += transcript;
                        }
                    }
                    if (this.chatInterimText) {
                        input.value = input.value.slice(0, input.value.length - this.chatInterimText.length);
                    }
                    if (finalTranscript) {
                        input.value += finalTranscript;
                        this.chatInterimText = '';
                    } else if (newInterim) {
                        input.value += newInterim;
                        this.chatInterimText = newInterim;
                    }
                    input.focus();
                };

                this.chatRecognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    this.stopChatRecording();
                };

                this.chatRecognition.onend = () => {
                    this.stopChatRecording();
                };

                btn.addEventListener('click', () => {
                    if (this.chatIsRecording) {
                        this.chatRecognition?.stop();
                    } else {
                        this.chatRecognition?.start();
                    }
                });
            } else {
                btn.style.opacity = '0.5';
                btn.style.pointerEvents = 'none';
                btn.title = '浏览器不支持语音识别';
            }
        }

        stopChatRecording() {
            this.chatIsRecording = false;
            const input = this.chatInput;
            if (input && this.chatInterimText) {
                input.value = input.value.slice(0, input.value.length - this.chatInterimText.length);
                this.chatInterimText = '';
            }
            const btn = this.chatVoiceBtn;
            if (btn) {
                btn.classList.remove('recording');
                btn.querySelector('i')?.classList.replace('fa-stop', 'fa-microphone');
            }
        }

        // ---- Utils ----

        initVoiceSelector() {
            const teacherArea = document.getElementById('teacher-area');
            if (!teacherArea) return;

            // Create voice selector dropdown
            const voiceSelector = document.createElement('div');
            voiceSelector.className = 'voice-selector';
            voiceSelector.innerHTML = `
                <select id="voice-select" class="voice-select">
                    ${Object.entries(MINIMAX_VOICES).map(([id, v]) =>
                        `<option value="${id}" ${id === TTS_CONFIG.voice ? 'selected' : ''}>${v.name}</option>`
                    ).join('')}
                </select>
            `;

            // Style the selector
            voiceSelector.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 10;
            `;

            const select = voiceSelector.querySelector('select');
            select.style.cssText = `
                background: var(--surface-glass);
                border: 1px solid var(--glass-border);
                border-radius: 8px;
                padding: 6px 12px;
                color: var(--text-primary);
                font-size: 12px;
                cursor: pointer;
                outline: none;
            `;

            select.addEventListener('change', (e) => {
                TTS_CONFIG.voice = e.target.value;
                this.saveVoicePreference(e.target.value);
            });

            teacherArea.appendChild(voiceSelector);
        }

        saveVoicePreference(voiceId) {
            localStorage.setItem('classroom_voice', voiceId);
        }

        loadVoicePreference() {
            const saved = localStorage.getItem('classroom_voice');
            if (saved && MINIMAX_VOICES[saved]) {
                TTS_CONFIG.voice = saved;
            }
        }

        setVoice(voiceId) {
            if (MINIMAX_VOICES[voiceId]) {
                TTS_CONFIG.voice = voiceId;
                this.saveVoicePreference(voiceId);
            }
        }

        setSpeed(speed) {
            if (TTS_CONFIG.speedOptions.includes(speed)) {
                TTS_CONFIG.speed = speed;
                if (this.audioPlayer) {
                    this.audioPlayer.playbackRate = speed;
                }
                this.updateSpeedDisplay(speed);
            }
        }

        updateSpeedDisplay(speed) {
            const speedBtn = document.getElementById('speed-btn');
            const speedLabel = speedBtn?.querySelector('.speed-label');
            if (speedLabel) {
                speedLabel.textContent = `${speed}x`;
            }
        }

        cycleSpeed() {
            const currentIndex = TTS_CONFIG.speedOptions.indexOf(TTS_CONFIG.speed);
            const nextIndex = (currentIndex + 1) % TTS_CONFIG.speedOptions.length;
            this.setSpeed(TTS_CONFIG.speedOptions[nextIndex]);
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Global instance
    let classroomController;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            classroomController = new ClassroomController();
            classroomController.init();
        });
    } else {
        classroomController = new ClassroomController();
        classroomController.init();
    }
})();
