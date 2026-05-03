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

            // Quiz state
            this.quizPhase = 'not_started';  // not_started | answering | grading | reviewing
            this.currentQuizScene = null;
            this.quizUserAnswers = {};       // {index: {type, value/values}}
            this.quizResults = [];
            this._wasSpeakingBeforeQuiz = false;

            // Whiteboard state
            this.whiteboardRenderer = null;
            this.whiteboardContainer = document.getElementById('whiteboard-container');
            this.whiteboardStage = document.getElementById('whiteboard-stage');
            this.whiteboardToggleBtn = document.getElementById('whiteboard-toggle-btn');
            this.whiteboardClearBtn = document.getElementById('wb-clear-btn');

            // Animation state
            this.currentAnimationEffects = [];
            this.isTransitioning = false;
            this.animationQueue = [];

            // Spotlight/laser state
            this.spotlightElement = null;
            this.laserTargetElem = null;
            this.laserElements = [];
            this._currentElemToCard = null;

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
            this.slideControls = document.querySelector('.slide-controls');
            this.progressBar = document.querySelector('.progress-bar');

            // Quiz popup DOM refs
            this.quizPopupOverlay = document.getElementById('quiz-popup-overlay');
            this.quizCover = document.getElementById('quiz-cover');
            this.quizQuestionsArea = document.getElementById('quiz-questions-area');
            this.quizGrading = document.getElementById('quiz-grading');
            this.quizReviewArea = document.getElementById('quiz-review-area');
            this.quizPopupFooter = document.getElementById('quiz-popup-footer');
            this.quizCoverTitle = document.getElementById('quiz-cover-title');
            this.quizCoverMeta = document.getElementById('quiz-cover-meta');
            this.quizToggleBtn = document.getElementById('quiz-toggle-btn');
            this.quizStartBtn = document.getElementById('quiz-start-btn');
            this.quizSubmitBtn = document.getElementById('quiz-popup-submit-btn');
            this.quizRetryBtn = document.getElementById('quiz-popup-retry-btn');
            this.quizCloseBtn = document.getElementById('quiz-popup-close');
            this.gradingProgressList = document.getElementById('grading-progress-list');
            this.gradingText = document.getElementById('quiz-grading-text');
            this.slideViewer = document.querySelector('.slide-viewer');

            // Action overlays (create if not exist)
            this.actionOverlay = document.getElementById('action-overlay');
            if (!this.actionOverlay) {
                this.actionOverlay = document.createElement('div');
                this.actionOverlay.id = 'action-overlay';
                this.actionOverlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';
                document.body.appendChild(this.actionOverlay);
            }

            // OpenMAIC slide player initialization
            this.openmaicDeck = null;
            this.openmaicPlayer = null;
            if (window.OpenMAICSlidePlayer) {
                var self = this;
                this.openmaicPlayer = new window.OpenMAICSlidePlayer({
                    container: this.slideContainer,
                    overlay: this.actionOverlay,
                    audioElement: this.audioPlayer,
                    speechText: this.speechText,
                    syncElement: this.speechSync,
                    teacherAvatar: this.teacherAvatar,
                    getSpeed: function() { return self.ttsConfig ? self.ttsConfig.speed : 1.0; },
                    onSlideEnd: function() {
                        self.speechSync.style.display = 'none';
                        if (self.isPlaying && self.currentIndex < self.scenes.length - 1) {
                            setTimeout(function() { self.nextScene(); }, 800);
                        } else if (self.currentIndex >= self.scenes.length - 1) {
                            // Last scene finished — stop playback
                            self.isPlaying = false;
                            self.stopAudio();
                            self.voiceBtn?.classList.remove('playing');
                            var vi = self.voiceBtn?.querySelector('i');
                            if (vi) vi.className = 'fas fa-volume-up';
                        }
                    },
                });
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

            // slides_v2 now includes scene_id from MiniMax PPT provider
            // Use findSceneData for scene_id matching (Strategy 1), fallback to index for legacy
            this.scenes = outlines.map(function(outline, i) {
                var sceneId = outline.id || i + 1;
                var matchedSlide = findSceneData(slides, outline);
                var matchedSlideV2 = findSceneData(slidesV2, outline) || slidesV2[i] || null;
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
            document.getElementById('playback-play-btn')?.addEventListener('click', () => this.toggleVoice());
            document.getElementById('speed-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleSpeedMenu();
            });
            // Close speed menu on outside click
            document.addEventListener('click', () => this.closeSpeedMenu());
            // Speed menu option clicks
            document.getElementById('speed-menu')?.addEventListener('click', (e) => {
                var opt = e.target.closest('.speed-option');
                if (opt) {
                    var speed = parseFloat(opt.dataset.speed);
                    if (!isNaN(speed)) this.setSpeed(speed);
                    this.closeSpeedMenu();
                }
            });
            this.sendChat?.addEventListener('click', () => this.sendMessage());
            this.chatInput?.addEventListener('keypress', e => { if (e.key === 'Enter') this.sendMessage(); });
            document.getElementById('exit-btn')?.addEventListener('click', () => this.showExitModal());
            document.getElementById('cancel-exit')?.addEventListener('click', () => this.hideExitModal());
            document.getElementById('confirm-exit')?.addEventListener('click', () => this.confirmExit());
            // Whiteboard toggle
            this.whiteboardToggleBtn?.addEventListener('click', () => this.toggleWhiteboard());
            this.whiteboardClearBtn?.addEventListener('click', () => this.clearWhiteboard());
            // Quiz popup buttons
            this.quizToggleBtn?.addEventListener('click', () => this._onQuizToggleClick());
            this.quizCloseBtn?.addEventListener('click', () => this.closeQuizPopup());
            this.quizStartBtn?.addEventListener('click', () => this.startQuiz());
            this.quizSubmitBtn?.addEventListener('click', () => this._submitForGrading());
            this.quizRetryBtn?.addEventListener('click', () => this.retryQuiz());
            document.addEventListener('keydown', e => this.onKey(e));
            this.initChatVoiceInput();
        }

        onKey(e) {
            if (e.target === this.chatInput || e.target === document.getElementById('exercise-answer')) return;
            // Block navigation when quiz popup is open
            var quizOpen = this.quizPopupOverlay && this.quizPopupOverlay.style.display === 'flex';
            switch (e.key) {
                case 'ArrowLeft': if (!this.whiteboardVisible && !quizOpen) this.prevScene(); break;
                case 'ArrowRight': if (!this.whiteboardVisible && !quizOpen) this.nextScene(); break;
                case ' ': e.preventDefault(); this.toggleVoice(); break;
                case 'w': if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); this.toggleWhiteboard(); } break;
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
                case 'quiz': this.openQuizPopup(scene); break;
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
            // Hide whiteboard if visible, but don't toggle state
            if (this.whiteboardContainer) this.whiteboardContainer.style.display = 'none';
            // Hide quiz popup
            if (this.quizPopupOverlay) this.quizPopupOverlay.style.display = 'none';
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

            _cycleCardThemes(cards) {
                if (!cards || cards.length <= 1) return cards;
                const themes = new Set(cards.map(c => c.colorTheme));
                const needsCycle = themes.size <= 1 || cards.some(c => !c.colorTheme);
                if (!needsCycle) return cards;
                for (let i = 0; i < cards.length; i++) {
                    cards[i].colorTheme = this.COLOR_THEMES[i % this.COLOR_THEMES.length];
                }
                return cards;
            },

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
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
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
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
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
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
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
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
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

            _renderContentCard(item, cardIndex) {
                const icon = this._getIcon(item.icon);
                const theme = this._validateTheme(item.colorTheme);
                const subTitle = this._escapeHtml(item.subTitle || '');
                const textHtml = this._renderBulletsOrText(item);
                const isBullets = textHtml.startsWith('<ul');
                const codeHtml = item.codeSnippet ? this._renderCodeSnippet(item.codeSnippet) : '';
                const imageHtml = item.imageUrl ? this._renderImage(item.imageUrl) : '';
                const idxAttr = (cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : '';

                return `
                    <div class="content-card theme-${theme}"${idxAttr}>
                        ${subTitle ? `<div class="card-title">${icon} ${subTitle}</div>` : ''}
                        ${textHtml && !isBullets ? `<div class="card-text">${textHtml}</div>` : ''}
                        ${textHtml && isBullets ? textHtml : ''}
                        ${codeHtml}
                        ${imageHtml}
                    </div>
                `;
            },

            _renderBulletsOrText(item) {
                if (item.bullets && Array.isArray(item.bullets) && item.bullets.length > 0) {
                    const items = item.bullets
                        .map(b => `<li>${this._escapeHtml(String(b))}</li>`)
                        .join('');
                    return `<ul class="card-bullets">${items}</ul>`;
                }
                return this._parseMarkdown(item.text || '');
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
            this.slideContainer.className = 'slide-container';

            const slides_v2 = scene.slides_v2 || [];
            if (slides_v2.length === 0) {
                this.renderSlideScene(scene);
                return;
            }

            const firstSlide = slides_v2[0];

            // Determine card data from either format, route to SlideRenderer for consistent UI
            var cardData;
            if (firstSlide.elements && Array.isArray(firstSlide.elements) && firstSlide.elements.length > 0) {
                // OpenMAIC format: group elements into cards by ID prefix
                cardData = this._groupOpenMAICElementsToCards(firstSlide);
            } else if (firstSlide.content && Array.isArray(firstSlide.content)) {
                // SlideV2 format: use content + layout_type directly
                cardData = {
                    title: firstSlide.title || scene.title || '',
                    content: SlideRenderer._cycleCardThemes(firstSlide.content),
                    layoutType: firstSlide.layoutType || firstSlide.layout_type || 'two-column'
                };
            } else {
                this.renderSlideScene(scene);
                return;
            }

            this.SlideRenderer.render(cardData, this.slideContainer);

            // Store actions for playback pipeline (spotlight/laser use element IDs)
            this._currentOpenMAICActions = firstSlide.actions || scene.actions || null;
            // Store element-to-card mapping for spotlight/laser targeting
            this._currentElemToCard = cardData._elemToCard || null;
        }

        // ---- OpenMAIC Elements → Card Data Converter ----
        // Groups absolutely-positioned elements into semantic cards by ID prefix.
        // OpenMAIC/MiniMax elements follow naming: el-card-{N} (shape bg),
        // el-card-{N}-title, el-card-{N}-content, el-card-{N}-code, etc.

        _groupOpenMAICElementsToCards(slide) {
            var elements = slide.elements || [];
            var slideTitle = slide.title || '';

            // Extract title from header element
            var headerText = null;
            for (var i = 0; i < elements.length; i++) {
                var id = elements[i].id || '';
                if (id.indexOf('header-title') >= 0 || (id.indexOf('-title') >= 0 && elements[i].top < 30)) {
                    headerText = elements[i];
                    break;
                }
            }
            if (headerText && headerText.content) {
                var m = headerText.content.match(/<h1[^>]*>([\s\S]+?)<\/h1>/i);
                if (m) slideTitle = m[1].replace(/<[^>]+>/g, '').trim();
            }

            // Group elements by card prefix: "card-1", "card-2", etc.
            var cardGroups = {};
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var elId = el.id || '';
                var cardMatch = elId.match(/card-(\d+)/);
                if (cardMatch) {
                    var idx = parseInt(cardMatch[1], 10) - 1;
                    if (!cardGroups[idx]) cardGroups[idx] = { shape: null, texts: [], code: null, image: null };
                    if (el.type === 'shape') cardGroups[idx].shape = el;
                    else if (el.type === 'code') cardGroups[idx].code = el;
                    else if (el.type === 'image') cardGroups[idx].image = el;
                    else cardGroups[idx].texts.push(el);
                }
            }

            // Build card data from groups
            var cards = [];
            var indices = Object.keys(cardGroups).sort(function(a, b) { return a - b; });
            for (var gi = 0; gi < indices.length; gi++) {
                var group = cardGroups[indices[gi]];
                if (!group.shape) continue;

                // Infer theme color from shape fill
                var fill = (group.shape.fill || '').toUpperCase();
                var theme = 'blue';
                if (fill.indexOf('FFFBEB') >= 0 || fill.indexOf('FEF3C7') >= 0 || fill.indexOf('FDE68A') >= 0) theme = 'yellow';
                else if (fill.indexOf('ECFDF5') >= 0 || fill.indexOf('D1FAE5') >= 0 || fill.indexOf('A7F3D0') >= 0) theme = 'green';
                else if (fill.indexOf('EDE9FE') >= 0 || fill.indexOf('DDD6FE') >= 0) theme = 'purple';
                else if (fill.indexOf('FFF7ED') >= 0 || fill.indexOf('FFEDD5') >= 0) theme = 'orange';

                // Extract title (short text at top of card) and body (longer text below)
                var subTitle = '';
                var bodyText = '';
                var icon = 'book';

                for (var ti = 0; ti < group.texts.length; ti++) {
                    var tel = group.texts[ti];
                    var raw = (tel.content || '').replace(/<[^>]+>/g, '').trim();
                    var isSmallText = (tel.height || 999) <= 42;
                    var hasHeading = /<h[12]/i.test(tel.content || '');
                    var hasStrong = /<strong/i.test(tel.content || '');
                    var isShort = raw.length < 50;

                    if (hasHeading || hasStrong || ((isSmallText || isShort) && !bodyText)) {
                        subTitle = raw.replace(/^[📖💡💻✅⭐❓⚠ℹ️\s]+/, '').trim();
                    } else {
                        bodyText = tel.content || '';
                    }
                }

                // Extract code snippet
                var codeSnippet = '';
                if (group.code) {
                    codeSnippet = group.code.content ||
                        (group.code.lines || []).map(function(l) { return l.content || ''; }).join('\n');
                }

                // Parse bullets from bodyText
                var bullets = [];
                if (bodyText) {
                    var plainText = bodyText.replace(/<[^>]+>/g, '').trim();
                    var lines = plainText.split('\n');
                    for (var li = 0; li < lines.length; li++) {
                        var line = lines[li].trim();
                        var bm = line.match(/^[-*]\s+(.+)/);
                        if (bm) {
                            bullets.push(bm[1]);
                        } else if (line && !bullets.length) {
                            bullets.push(line.substring(0, 200));
                        }
                    }
                }

                cards.push({
                    subTitle: subTitle || ('要点 ' + (parseInt(indices[gi], 10) + 1)),
                    text: bodyText,
                    bullets: bullets,
                    narration: '',
                    icon: icon,
                    colorTheme: theme,
                    codeSnippet: codeSnippet,
                    imageUrl: group.image ? group.image.src || '' : ''
                });
            }

            var layoutType = cards.length <= 1 ? 'title-only' :
                             cards.length <= 2 ? 'two-column' : 'grid-cards';

            // Build element-to-card-index mapping for spotlight/laser actions
            var elemToCard = {};
            var cardIndices = Object.keys(cardGroups);
            for (var mi = 0; mi < cardIndices.length; mi++) {
                var cgIdx = cardIndices[mi];
                var cg = cardGroups[cgIdx];
                // Map the shape element ID to card index
                if (cg.shape && cg.shape.id) elemToCard[cg.shape.id] = mi;
                // Also map text/code/image element IDs within this card group
                for (var ei = 0; ei < cg.texts.length; ei++) {
                    if (cg.texts[ei].id) elemToCard[cg.texts[ei].id] = mi;
                }
                if (cg.code && cg.code.id) elemToCard[cg.code.id] = mi;
                if (cg.image && cg.image.id) elemToCard[cg.image.id] = mi;
            }

            SlideRenderer._cycleCardThemes(cards);

            return {
                title: slideTitle,
                content: cards,
                layoutType: layoutType,
                _elemToCard: elemToCard
            };
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
                // Detect simplified {bullets} format: elements without type but with bullets
                var hasSimplifiedFormat = slide.content.elements.length > 0 &&
                    !slide.content.elements[0].type &&
                    slide.content.elements[0].bullets &&
                    Array.isArray(slide.content.elements[0].bullets);

                if (hasSimplifiedFormat) {
                    for (var si = 0; si < slide.content.elements.length; si++) {
                        var se = slide.content.elements[si];
                        if (se.title) {
                            html += `<h3 class="simplified-card-title">${this.escapeHtml(se.title)}</h3>`;
                        }
                        if (se.bullets && se.bullets.length) {
                            html += '<ul class="card-bullets simplified-bullets">';
                            for (var bi = 0; bi < se.bullets.length; bi++) {
                                html += `<li>${this.escapeHtml(String(se.bullets[bi]))}</li>`;
                            }
                            html += '</ul>';
                        }
                    }
                } else {
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
                } // end else (not simplified format)
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
                    this.toggleWhiteboard();
                    break;

                case 'wb_close':
                    if (this.whiteboardVisible) this.toggleWhiteboard();
                    break;

                case 'wb_clear':
                    this.clearWhiteboard();
                    break;

                case 'wb_delete':
                    this._getWhiteboardRenderer()?.delete(action.elementId || action.element_id);
                    break;

                case 'wb_draw_text':
                case 'wb_draw_shape':
                case 'wb_draw_svg':
                case 'wb_draw_latex':
                case 'wb_draw_chart':
                case 'wb_draw_table':
                case 'wb_draw_line':
                case 'wb_draw_code':
                    this.executeWhiteboardAction({
                        type: action.type,
                        params: this._mapWbActionParams(action)
                    });
                    break;

                case 'transition':
                    this.executeSlideTransition(action.direction || 'next', action.effect || 'fade');
                    break;

                case 'quiz_open':
                    // Auto-open quiz for the first quiz scene
                    var quizScene = this.scenes.find(function(s) { return s.type === 'quiz'; });
                    if (quizScene) { this.openQuizPopup(quizScene); }
                    else { console.warn('No quiz scene found in course'); }
                    break;

                case 'quiz_close':
                    if (this.quizPopupOverlay && this.quizPopupOverlay.style.display === 'flex') {
                        this.closeQuizPopup();
                    }
                    break;

                default:
                    console.warn('Unknown action type:', action.type);
            }
        }

        /** Map flat action properties to WhiteboardRenderer params format */
        _mapWbActionParams(action) {
            const type = action.type || '';
            const base = {};
            // Copy common fields
            if (action.elementId != null) base.elementId = action.elementId;
            if (action.element_id != null) base.elementId = action.element_id;
            if (action.x != null) base.x = action.x;
            if (action.y != null) base.y = action.y;
            if (action.color != null) base.color = action.color;
            if (action.width != null) base.width = action.width;
            if (action.height != null) base.height = action.height;
            if (action.fontSize != null) base.fontSize = action.fontSize;

            switch (type) {
                case 'wb_draw_text':
                    if (action.content != null) base.content = action.content;
                    if (action.text != null) base.content = action.text;
                    break;
                case 'wb_draw_shape':
                    if (action.shape != null) base.shape = action.shape;
                    if (action.fillColor != null) base.fillColor = action.fillColor;
                    if (action.strokeColor != null) base.strokeColor = action.strokeColor;
                    break;
                case 'wb_draw_svg':
                    if (action.svg != null) base.svg = action.svg;
                    break;
                case 'wb_draw_latex':
                    if (action.latex != null) base.latex = action.latex;
                    break;
                case 'wb_draw_chart':
                    if (action.chartType != null) base.chartType = action.chartType;
                    if (action.data != null) base.data = action.data;
                    break;
                case 'wb_draw_table':
                    if (action.data != null) base.data = action.data;
                    break;
                case 'wb_draw_line':
                    if (action.startX != null) base.startX = action.startX;
                    if (action.startY != null) base.startY = action.startY;
                    if (action.endX != null) base.endX = action.endX;
                    if (action.endY != null) base.endY = action.endY;
                    if (action.style != null) base.style = action.style;
                    // Support old format: action.start, action.end
                    if (action.start != null && base.startX == null) {
                        base.startX = action.start.x || action.start[0] || 0;
                        base.startY = action.start.y || action.start[1] || 0;
                    }
                    if (action.end != null && base.endX == null) {
                        base.endX = action.end.x || action.end[0] || 0;
                        base.endY = action.end.y || action.end[1] || 0;
                    }
                    break;
                case 'wb_draw_code':
                    if (action.code != null) base.code = action.code;
                    if (action.language != null) base.language = action.language;
                    if (action.fileName != null) base.fileName = action.fileName;
                    break;
            }
            return base;
        }

        renderSpotlight(elementId, options = {}) {
            this.clearSpotlight();

            // Try legacy element lookup first: #elem-{elementId}
            var targetElem = elementId ? document.getElementById(`elem-${elementId}`) : null;

            // Fallback: try card-based targeting via _currentElemToCard mapping
            if (!targetElem && elementId && this._currentElemToCard) {
                var cardIdx = this._currentElemToCard[elementId];
                if (cardIdx !== undefined) {
                    targetElem = this.slideContainer.querySelector(`.content-card[data-card-index="${cardIdx}"]`);
                }
            }
            // Fallback: try matching card-{N} prefix directly
            if (!targetElem && elementId) {
                var cardMatch = elementId.match(/card-(\d+)/);
                if (cardMatch) {
                    var ci = parseInt(cardMatch[1], 10) - 1;
                    targetElem = this.slideContainer.querySelector(`.content-card[data-card-index="${ci}"]`);
                }
            }

            // Card-based spotlight: use CSS classes for dimming + highlight
            if (targetElem && targetElem.classList.contains('content-card')) {
                this.slideContainer.classList.add('spotlight-active');
                targetElem.classList.add('spotlight-target');
                this.spotlightElement = targetElem;
                return;
            }

            // Legacy overlay-based spotlight
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

            // Clear card-based spotlight classes
            if (this.slideContainer) {
                this.slideContainer.classList.remove('spotlight-active');
            }
            if (this.spotlightElement) {
                this.spotlightElement.classList.remove('spotlight-target');
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

            // Try legacy element lookup first: #elem-{elementId}
            var targetElem = elementId ? document.getElementById(`elem-${elementId}`) : null;

            // Fallback: try card-based targeting via _currentElemToCard mapping
            if (!targetElem && elementId && this._currentElemToCard) {
                var cardIdx = this._currentElemToCard[elementId];
                if (cardIdx !== undefined) {
                    targetElem = this.slideContainer.querySelector(`.content-card[data-card-index="${cardIdx}"]`);
                }
            }
            // Fallback: try matching card-{N} prefix directly
            if (!targetElem && elementId) {
                var cardMatch = elementId.match(/card-(\d+)/);
                if (cardMatch) {
                    var ci = parseInt(cardMatch[1], 10) - 1;
                    targetElem = this.slideContainer.querySelector(`.content-card[data-card-index="${ci}"]`);
                }
            }

            const laserContainer = document.createElement('div');
            laserContainer.id = 'laser-overlay';
            laserContainer.className = 'laser-overlay';

            var cx = window.innerWidth / 2;
            var cy = window.innerHeight / 2;

            if (targetElem) {
                const rect = targetElem.getBoundingClientRect();
                cx = rect.left + rect.width / 2;
                cy = rect.top + rect.height / 2;

                // Card-based: add laser-target class
                if (targetElem.classList.contains('content-card')) {
                    targetElem.classList.add('laser-target');
                }
                // Highlight element with glow
                targetElem.style.transition = 'filter 0.3s ease';
                targetElem.style.filter = `brightness(1.2) drop-shadow(0 0 15px ${color})`;

                this.laserTargetElem = targetElem;
            }

            laserContainer.innerHTML = `
                <div class="laser-dot" style="left:${cx}px;top:${cy}px;background:radial-gradient(circle, ${color} 0%, transparent 70%); animation: laserFlyIn 0.5s cubic-bezier(0.22, 1, 0.36, 1);"></div>
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
            if (this.laserTargetElem) {
                this.laserTargetElem.classList.remove('laser-target');
                this.laserTargetElem.style.filter = '';
                this.laserTargetElem = null;
            }

            document.querySelectorAll('.slide-text, .slide-code, .slide-image, .slide-shape, .slide-latex, .slide-table').forEach(el => {
                el.style.filter = '';
            });
        }

        clearEffects() {
            this.clearSpotlight();
            this.clearLaser();
            if (this.slideContainer) {
                this.slideContainer.classList.remove('spotlight-active');
                var cards = this.slideContainer.querySelectorAll('.content-card');
                cards.forEach(function(c) {
                    c.classList.remove('spotlight-target', 'laser-target');
                });
            }
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
            if (!this.whiteboardVisible) this.toggleWhiteboard();
        }

        hideWhiteboard() {
            if (this.whiteboardVisible) this.toggleWhiteboard();
        }

        drawTextOnWhiteboard(text, x = 50, y = 50, style = {}) {
            this.executeWhiteboardAction({
                type: 'wb_draw_text',
                params: {
                    content: text,
                    x: x,
                    y: y,
                    fontSize: style.fontSize || 20,
                    color: style.color || '#333'
                }
            });
        }

        drawLineOnWhiteboard(start, end, color = '#6366f1', width = 3) {
            this.executeWhiteboardAction({
                type: 'wb_draw_line',
                params: {
                    startX: start?.x ?? start?.[0] ?? 0,
                    startY: start?.y ?? start?.[1] ?? 0,
                    endX: end?.x ?? end?.[0] ?? 100,
                    endY: end?.y ?? end?.[1] ?? 100,
                    color: color,
                    width: width
                }
            });
        }

        drawShapeOnWhiteboard(shapeType) {
            this.executeWhiteboardAction({
                type: 'wb_draw_shape',
                params: {
                    shape: shapeType || 'rectangle',
                    x: 100, y: 100,
                    width: 200, height: 150
                }
            });
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

        // ---- Whiteboard ----

        _getWhiteboardRenderer() {
            if (!this.whiteboardRenderer && window.WhiteboardRenderer) {
                this.whiteboardRenderer = new window.WhiteboardRenderer({
                    containerId: 'whiteboard-stage',
                    width: 1000,
                    height: 562.5
                });
            }
            return this.whiteboardRenderer;
        }

        _initWhiteboard() {
            if (!this.whiteboardStage) return;
            const renderer = this._getWhiteboardRenderer();
            if (renderer) renderer._initContainer();
        }

        toggleWhiteboard() {
            this.whiteboardVisible = !this.whiteboardVisible;
            this.whiteboardToggleBtn?.classList.toggle('active', this.whiteboardVisible);

            if (this.whiteboardVisible) {
                // Switch to whiteboard view
                this.stopAudio();
                this.hideAllSceneContainers();
                if (this.whiteboardContainer) {
                    this.whiteboardContainer.style.display = 'flex';
                }
                this._initWhiteboard();
                // Hide slide navigation during whiteboard
                if (this.slideControls) this.slideControls.style.display = 'none';
                if (this.progressBar) this.progressBar.style.display = 'none';
            } else {
                // Switch back to slide view
                if (this.whiteboardContainer) {
                    this.whiteboardContainer.style.display = 'none';
                }
                if (this.slideControls) this.slideControls.style.display = '';
                if (this.progressBar) this.progressBar.style.display = '';
                this.renderScene(this.currentIndex);
            }
        }

        clearWhiteboard() {
            const renderer = this._getWhiteboardRenderer();
            if (renderer) renderer.clear();
        }

        /** Execute a whiteboard action (wb_*) from the AI teacher pipeline */
        executeWhiteboardAction(action) {
            const renderer = this._getWhiteboardRenderer();
            if (!renderer) {
                console.warn('[Classroom] WhiteboardRenderer not available');
                return;
            }
            // Auto-open whiteboard on first draw action
            var name = action.type || action.name || '';
            if (!this.whiteboardVisible && name.startsWith('wb_draw_')) {
                this.whiteboardVisible = true;
                this.whiteboardToggleBtn?.classList.add('active');
                this.stopAudio();
                this.hideAllSceneContainers();
                if (this.whiteboardContainer) {
                    this.whiteboardContainer.style.display = 'flex';
                }
                this._initWhiteboard();
                if (this.slideControls) this.slideControls.style.display = 'none';
                if (this.progressBar) this.progressBar.style.display = 'none';
            }
            // Handle wb_close - switch back to slides
            if (name === 'wb_close') {
                this.whiteboardVisible = false;
                this.whiteboardToggleBtn?.classList.remove('active');
                if (this.whiteboardContainer) {
                    this.whiteboardContainer.style.display = 'none';
                }
                if (this.slideControls) this.slideControls.style.display = '';
                if (this.progressBar) this.progressBar.style.display = '';
                this.renderScene(this.currentIndex);
                return;
            }
            if (name === 'wb_clear') {
                renderer.clear();
                return;
            }
            if (name === 'wb_delete') {
                renderer.delete(action.params?.elementId);
                return;
            }
            renderer.execute(action);
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

            // If OpenMAIC actions are available, use the action pipeline (speech + spotlight + laser)
            if (this._currentOpenMAICActions && this._currentOpenMAICActions.length > 0 && this.openmaicPlayer) {
                console.log('[Classroom] Starting OpenMAIC action pipeline with', this._currentOpenMAICActions.length, 'actions');
                this.speechSync.style.display = 'flex';
                this.openmaicPlayer.start(this._currentOpenMAICActions);
                return;
            }

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

            // Sync prominent play/pause button
            const playBtn = document.getElementById('playback-play-btn');
            const playIcon = playBtn?.querySelector('i');
            if (playBtn) playBtn.classList.toggle('playing', this.isPlaying);
            if (playIcon) playIcon.className = this.isPlaying ? 'fas fa-pause' : 'fas fa-play';

            if (this.isPlaying) this.playSceneAudio(this.scenes[this.currentIndex]);
            else this.stopAudio();
        }

        stopAudio() {
            if (this.audioPlayer) { this.audioPlayer.pause(); this.audioPlayer.src = ''; }
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            if (this.openmaicPlayer) this.openmaicPlayer.stop({ keepSlide: true });
            if (this.speechSync) this.speechSync.style.display = 'none';
            // Reset play button state
            const playBtn = document.getElementById('playback-play-btn');
            const playIcon = playBtn?.querySelector('i');
            if (playBtn) playBtn.classList.remove('playing');
            if (playIcon) playIcon.className = 'fas fa-play';
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

        // ============================================================
        // Quiz Popup Lifecycle — Phase 5
        // ============================================================

        _onQuizToggleClick() {
            // Find the first quiz scene in the course
            var quizScene = this.scenes.find(function(s) { return s.type === 'quiz'; });
            if (!quizScene) {
                this.addChatMessage('teacher', '当前课程没有测验环节。');
                return;
            }
            this.openQuizPopup(quizScene);
        }

        openQuizPopup(scene) {
            if (!scene || scene.type !== 'quiz') return;
            this.currentQuizScene = scene;
            this.quizPhase = 'not_started';
            this.quizUserAnswers = {};
            this.quizResults = [];

            // Pause AI speech if currently playing
            this._wasSpeakingBeforeQuiz = this.isPlaying;
            if (this.isPlaying) {
                this.isPlaying = false;
                this.stopAudio();
                var vi = this.voiceBtn?.querySelector('i');
                if (vi) vi.className = 'fas fa-volume-up';
            }

            // Dim slide viewer to block interaction
            if (this.slideViewer) {
                this.slideViewer.classList.add('slide-viewer-dimmed');
            }

            // Hide all phase containers
            if (this.quizCover) this.quizCover.style.display = 'flex';
            if (this.quizQuestionsArea) this.quizQuestionsArea.style.display = 'none';
            if (this.quizGrading) this.quizGrading.style.display = 'none';
            if (this.quizReviewArea) this.quizReviewArea.style.display = 'none';
            if (this.quizPopupFooter) this.quizPopupFooter.style.display = 'none';
            if (this.quizCloseBtn) this.quizCloseBtn.style.display = 'block';
            if (this.quizSubmitBtn) this.quizSubmitBtn.style.display = 'none';
            if (this.quizRetryBtn) this.quizRetryBtn.style.display = 'none';

            // Show overlay
            if (this.quizPopupOverlay) {
                this.quizPopupOverlay.style.display = 'flex';
            }

            // Render cover
            this._renderQuizCover(scene);

            // Update toggle button state
            if (this.quizToggleBtn) this.quizToggleBtn.classList.add('active');
        }

        _renderQuizCover(scene) {
            var quiz = scene.quiz_data || scene.quiz;
            if (!quiz) return;

            var questions = quiz.questions || [];
            var totalPoints = questions.reduce(function(sum, q) { return sum + (q.points || 10); }, 0);
            var passing = quiz.passing_score || 60;

            if (this.quizCoverTitle) {
                this.quizCoverTitle.textContent = quiz.title || '课堂测验';
            }
            if (this.quizCoverMeta) {
                this.quizCoverMeta.innerHTML =
                    '<span><i class="fas fa-question-circle"></i> ' + questions.length + ' 道题</span>' +
                    '<span><i class="fas fa-star"></i> 总分 ' + totalPoints + '</span>' +
                    '<span><i class="fas fa-check-circle"></i> 及格线 ' + passing + '%</span>';
            }
        }

        startQuiz() {
            if (this.quizPhase !== 'not_started') return;
            this.quizPhase = 'answering';

            if (this.quizCover) this.quizCover.style.display = 'none';
            if (this.quizQuestionsArea) this.quizQuestionsArea.style.display = 'block';
            if (this.quizPopupFooter) this.quizPopupFooter.style.display = 'flex';
            if (this.quizSubmitBtn) this.quizSubmitBtn.style.display = 'flex';
            if (this.quizRetryBtn) this.quizRetryBtn.style.display = 'none';

            this._renderAllQuestions(this.currentQuizScene);
        }

        _renderAllQuestions(scene) {
            var self = this;
            var quiz = scene.quiz_data || scene.quiz;
            var questions = quiz.questions || [];

            var html = '';
            questions.forEach(function(q, i) {
                html += self._renderQuestionCard(q, i);
            });
            if (this.quizQuestionsArea) {
                this.quizQuestionsArea.innerHTML = html;
            }

            // Bind option click handlers
            questions.forEach(function(q, i) {
                var card = document.getElementById('question-card-' + i);
                if (!card) return;
                var type = q.question_type || 'single';

                if (type === 'single') {
                    card.querySelectorAll('.quiz-option').forEach(function(opt) {
                        opt.addEventListener('click', function() {
                            card.querySelectorAll('.quiz-option').forEach(function(o) { o.classList.remove('selected'); });
                            opt.classList.add('selected');
                            self.quizUserAnswers[i] = { type: 'single', value: parseInt(opt.dataset.optionIndex) };
                        });
                    });
                } else if (type === 'multiple') {
                    card.querySelectorAll('.quiz-option').forEach(function(opt) {
                        opt.addEventListener('click', function() {
                            opt.classList.toggle('selected');
                            var idx = parseInt(opt.dataset.optionIndex);
                            if (!self.quizUserAnswers[i]) {
                                self.quizUserAnswers[i] = { type: 'multiple', values: [] };
                            }
                            var arr = self.quizUserAnswers[i].values;
                            var pos = arr.indexOf(idx);
                            if (pos >= 0) { arr.splice(pos, 1); }
                            else { arr.push(idx); }
                        });
                    });
                }
            });

            // Short answer voice input buttons
            this.quizQuestionsArea.querySelectorAll('.sa-voice-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var qIdx = parseInt(btn.dataset.questionIndex);
                    self._startShortAnswerVoice(qIdx, btn);
                });
            });
        }

        _renderQuestionCard(q, index) {
            var type = q.question_type || 'single';
            var points = q.points || 10;
            var typeLabels = { single: '单选题', multiple: '多选题', short_answer: '简答题' };
            var typeLabel = typeLabels[type] || '单选题';
            var typeClass = type === 'multiple' ? 'tag-multiple' : (type === 'short_answer' ? 'tag-short' : 'tag-single');

            var html = '<div class="question-card" id="question-card-' + index + '">';
            html += '<div class="question-card-header">';
            html += '<span class="question-card-num">第 ' + (index + 1) + ' 题</span>';
            html += '<span class="question-type-tag ' + typeClass + '">' + typeLabel + '</span>';
            html += '<span class="question-card-points">' + points + ' 分</span>';
            html += '</div>';
            html += '<div class="question-body">' + this._escapeHtml(q.question) + '</div>';

            if (type === 'short_answer') {
                html += this._renderShortAnswerQuestion(q, index);
            } else {
                html += this._renderChoiceOptions(q, index, type);
            }

            html += '</div>';
            return html;
        }

        _renderChoiceOptions(q, index, type) {
            var options = q.options || [];
            var labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            var isMulti = type === 'multiple';
            var html = '<div class="question-options">';

            options.forEach(function(opt, oi) {
                html += '<div class="quiz-option' + (isMulti ? ' multi' : '') + '" data-option-index="' + oi + '">';
                html += '<div class="quiz-option-radio' + (isMulti ? ' multi' : '') + '"></div>';
                html += '<span class="quiz-option-text">' + labels[oi] + '. ' + this._escapeHtml(typeof opt === 'string' ? opt : (opt.text || opt.key || '')) + '</span>';
                html += '</div>';
            }.bind(this));

            html += '</div>';
            return html;
        }

        _renderShortAnswerQuestion(q, index) {
            var html = '<div class="sa-answer-area">';
            html += '<textarea class="sa-textarea" id="sa-textarea-' + index + '" placeholder="请输入你的答案..."></textarea>';
            html += '<button class="sa-voice-btn" data-question-index="' + index + '" type="button">';
            html += '<i class="fas fa-microphone"></i> 语音输入';
            html += '</button>';
            html += '</div>';
            return html;
        }

        _startShortAnswerVoice(qIndex, btn) {
            var self = this;
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                self.addChatMessage('teacher', '语音输入需要 Chrome 浏览器支持。');
                return;
            }
            if (btn.classList.contains('recording')) {
                // Already recording — stop handled by recognition.onend
                return;
            }

            var recognition = new SpeechRecognition();
            recognition.lang = 'zh-CN';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            btn.classList.add('recording');
            var icon = btn.querySelector('i');
            if (icon) icon.className = 'fas fa-microphone-slash';

            recognition.onresult = function(event) {
                var transcript = event.results[0][0].transcript;
                var textarea = document.getElementById('sa-textarea-' + qIndex);
                if (textarea) {
                    textarea.value = (textarea.value ? textarea.value + ' ' : '') + transcript;
                }
                self.quizUserAnswers[qIndex] = { type: 'short_answer', value: textarea ? textarea.value : transcript };
            };

            recognition.onerror = function() {
                btn.classList.remove('recording');
                if (icon) icon.className = 'fas fa-microphone';
            };

            recognition.onend = function() {
                btn.classList.remove('recording');
                if (icon) icon.className = 'fas fa-microphone';
            };

            recognition.start();
        }

        _collectQuizAnswers() {
            var self = this;
            var answers = [];
            var quiz = this.currentQuizScene;
            if (!quiz) return answers;
            var questions = (quiz.quiz_data || quiz.quiz || {}).questions || [];

            questions.forEach(function(q, i) {
                var type = q.question_type || 'single';
                var existing = self.quizUserAnswers[i];

                if (type === 'short_answer') {
                    var textarea = document.getElementById('sa-textarea-' + i);
                    var value = textarea ? textarea.value : (existing ? existing.value : '');
                    if (existing) existing.value = value;
                    answers.push({
                        question_index: i,
                        answer_value: value,
                        answer_values: []
                    });
                } else if (type === 'multiple') {
                    var values = existing ? (existing.values || []) : [];
                    answers.push({
                        question_index: i,
                        answer_value: values.join(','),
                        answer_values: values
                    });
                } else {
                    // single choice
                    var val = existing ? existing.value : -1;
                    answers.push({
                        question_index: i,
                        answer_value: val >= 0 ? String(val) : '',
                        answer_values: []
                    });
                }
            });

            return answers;
        }

        async _submitForGrading() {
            if (this.quizPhase !== 'answering') return;

            // Validate: check if any question is answered
            var answers = this._collectQuizAnswers();
            var quiz = this.currentQuizScene;
            var questions = (quiz.quiz_data || quiz.quiz || {}).questions || [];
            var hasAnyAnswer = answers.some(function(a) {
                return a.answer_value || (a.answer_values && a.answer_values.length > 0);
            });

            if (!hasAnyAnswer) {
                // Shake the submit button
                if (this.quizSubmitBtn) {
                    this.quizSubmitBtn.style.animation = 'none';
                    this.quizSubmitBtn.offsetHeight; // trigger reflow
                    this.quizSubmitBtn.style.animation = 'shake 0.5s ease';
                }
                return;
            }

            this.quizPhase = 'grading';
            if (this.quizQuestionsArea) this.quizQuestionsArea.style.display = 'none';
            if (this.quizGrading) this.quizGrading.style.display = 'flex';
            if (this.quizSubmitBtn) this.quizSubmitBtn.style.display = 'none';
            if (this.gradingText) this.gradingText.textContent = 'AI 正在批改你的答案...';

            // Build progress list
            var shortAnswerCount = questions.filter(function(q) { return (q.question_type || 'single') === 'short_answer'; }).length;
            this._buildGradingProgress(questions);

            // Build request payload
            var batchQuestions = questions.map(function(q, i) {
                return {
                    question_index: i,
                    question: q.question,
                    question_type: q.question_type || 'single',
                    options: q.options || [],
                    correct_answer: q.correct_answer || 0,
                    correct_answers: q.correct_answers || [],
                    answer: q.answer || '',
                    comment_prompt: q.comment_prompt || '',
                    points: q.points || 10,
                    key_points: q.key_points || []
                };
            });

            var self = this;

            try {
                // For short answer questions, show per-question progress
                if (shortAnswerCount > 0 && this.gradingText) {
                    this.gradingText.textContent = '正在批改选择题...';
                }

                // Simulate grading progress for choice questions first
                for (var i = 0; i < questions.length; i++) {
                    var qType = questions[i].question_type || 'single';
                    if (qType === 'single' || qType === 'multiple') {
                        this._updateGradingProgress(i, questions.length, 'choice', 'done');
                    }
                }

                if (shortAnswerCount > 0 && this.gradingText) {
                    this.gradingText.textContent = '正在批改简答题，这可能需要一些时间...';
                }

                // Make the batch API call
                var resp = await fetch('/api/v2/grade/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        questions: batchQuestions,
                        answers: answers,
                        quiz_id: quiz.id || ''
                    })
                });

                if (!resp.ok) {
                    throw new Error('API returned ' + resp.status);
                }

                var data = await resp.json();

                // Mark all progress items done
                questions.forEach(function(_, i) {
                    self._updateGradingProgress(i, questions.length, 'short_answer', 'done');
                });

                if (this.gradingText) {
                    this.gradingText.textContent = '批改完成！';
                }

                // Short delay so user sees completion
                await this._sleep(600);
                this.showQuizResults(data);

            } catch (e) {
                console.error('Quiz grading failed:', e);
                // Fallback: use local grading only
                self._gradeLocallyAndShow(questions, answers, quiz);
            }
        }

        _buildGradingProgress(questions) {
            if (!this.gradingProgressList) return;
            var html = '';
            for (var i = 0; i < questions.length; i++) {
                var q = questions[i];
                var type = q.question_type || 'single';
                var typeLabel = type === 'short_answer' ? '简答题' : (type === 'multiple' ? '多选题' : '单选题');
                html += '<div class="grading-progress-item" id="grading-item-' + i + '">';
                html += '<span class="progress-icon"><span class="mini-spinner"></span></span>';
                html += '<span>第 ' + (i + 1) + ' 题 (' + typeLabel + ') 批改中...</span>';
                html += '</div>';
            }
            this.gradingProgressList.innerHTML = html;
        }

        _updateGradingProgress(index, total, questionType, status) {
            var item = document.getElementById('grading-item-' + index);
            if (!item) return;
            if (status === 'done') {
                item.classList.add('done');
                var icon = item.querySelector('.progress-icon');
                if (icon) icon.innerHTML = '<i class="fas fa-check-circle" style="color:#34d399;font-size:14px;"></i>';
                item.querySelector('span:last-child').textContent =
                    '第 ' + (index + 1) + ' 题 批改完成';
            }
        }

        showQuizResults(response) {
            this.quizPhase = 'reviewing';
            this.quizResults = response.results || [];

            if (this.quizGrading) this.quizGrading.style.display = 'none';
            if (this.quizReviewArea) this.quizReviewArea.style.display = 'block';
            if (this.quizPopupFooter) this.quizPopupFooter.style.display = 'flex';
            if (this.quizRetryBtn) this.quizRetryBtn.style.display = 'flex';
            if (this.quizCloseBtn) this.quizCloseBtn.style.display = 'block';

            var self = this;
            var results = this.quizResults;
            var totalPoints = response.total_points || 0;
            var totalScore = response.total_score || 0;
            var percentage = response.percentage || 0;

            // Render score banner
            var reviewHtml = self._renderScoreBanner(results, totalPoints, percentage);

            // Render each question with feedback
            var quiz = this.currentQuizScene;
            var questions = (quiz.quiz_data || quiz.quiz || {}).questions || [];

            questions.forEach(function(q, i) {
                var result = results[i] || {};
                reviewHtml += self._renderQuestionReview(q, i, result);
            });

            if (this.quizReviewArea) {
                this.quizReviewArea.innerHTML = reviewHtml;
            }

            // Animate score ring after render
            var self_ = this;
            setTimeout(function() {
                self_._animateScoreRing(percentage);
            }, 200);

            // Start typewriter effect for short answer feedbacks (sequential)
            var saResults = results.filter(function(r) {
                var q = questions[r.question_index];
                return q && (q.question_type || 'single') === 'short_answer' && r.feedback;
            });
            if (saResults.length > 0) {
                self._typewriteAllFeedback(saResults, 0);
            }

            // Store answers for completion tracking
            if (quiz && quiz.id) {
                this.quizAnswers[quiz.id] = results;
            }
        }

        _renderScoreBanner(results, totalPoints, percentage) {
            var tierClass = percentage >= 80 ? 'score-emerald' : (percentage >= 60 ? 'score-amber' : 'score-red');
            var passFailClass = percentage >= 60 ? 'passed' : 'failed';
            var passFailText = percentage >= 60 ? '恭喜通过！' : '未通过，继续加油！';
            var correctCount = results.filter(function(r) { return r.is_correct; }).length;
            var totalCount = results.length;
            var score = results.reduce(function(s, r) { return s + (r.score || 0); }, 0);

            var circumference = 2 * Math.PI * 45; // r=45
            var offset = circumference * (1 - percentage / 100);

            var html = '<div class="score-banner ' + tierClass + '">';
            html += '<div class="score-ring-wrap">';
            html += '<svg class="score-ring-svg" width="120" height="120" viewBox="0 0 120 120">';
            html += '<circle class="score-ring-bg" cx="60" cy="60" r="45"/>';
            html += '<circle class="score-ring-fill" cx="60" cy="60" r="45"';
            html += ' stroke-dasharray="' + circumference + '" stroke-dashoffset="' + circumference + '"';
            html += ' id="score-ring-fill"/>';
            html += '</svg>';
            html += '<div class="score-ring-center">' + Math.round(percentage) + '%</div>';
            html += '</div>';
            html += '<div class="score-detail">';
            html += '<span><i class="fas fa-check-circle"></i> 正确 ' + correctCount + '/' + totalCount + '</span>';
            html += '<span><i class="fas fa-trophy"></i> 得分 ' + Math.round(score) + '/' + Math.round(totalPoints) + '</span>';
            html += '</div>';
            html += '<div class="score-pass-fail ' + passFailClass + '">' + passFailText + '</div>';
            html += '</div>';
            return html;
        }

        _animateScoreRing(percentage) {
            var ring = document.getElementById('score-ring-fill');
            if (!ring) return;
            var circumference = 2 * Math.PI * 45;
            var targetOffset = circumference * (1 - percentage / 100);
            // Trigger animation
            requestAnimationFrame(function() {
                ring.style.strokeDashoffset = targetOffset;
            });
        }

        _renderQuestionReview(q, index, result) {
            var type = q.question_type || 'single';
            var isCorrect = result.is_correct;
            var correctClass = isCorrect ? 'review-correct' : 'review-incorrect';
            var markIcon = isCorrect
                ? '<i class="fas fa-check-circle question-review-correct-mark"></i>'
                : '<i class="fas fa-times-circle question-review-incorrect-mark"></i>';

            var html = '<div class="question-card ' + correctClass + '" id="review-card-' + index + '">';
            html += '<div class="question-card-header">';
            html += '<span class="question-card-num">第 ' + (index + 1) + ' 题</span>';
            html += '<span class="question-card-points">' + Math.round(result.score || 0) + ' / ' + Math.round(result.total_points || q.points || 10) + ' 分</span>';
            html += markIcon;
            html += '</div>';
            html += '<div class="question-body">' + this._escapeHtml(q.question) + '</div>';

            if (type === 'short_answer') {
                // Show user answer + AI feedback
                var userAnswer = '';
                var existing = this.quizUserAnswers[index];
                if (existing) userAnswer = existing.value || '';
                html += '<div class="sa-answer-area">';
                html += '<div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;">你的答案：</div>';
                html += '<div style="font-size:13px;color:var(--text-primary);padding:8px 12px;background:rgba(255,255,255,0.03);border-radius:8px;border:1px solid var(--glass-border);margin-bottom:10px;">' + this._escapeHtml(userAnswer || '(未作答)') + '</div>';
                if (result.feedback) {
                    html += '<div class="sa-feedback-box" id="sa-feedback-' + index + '">';
                    html += '<div class="sa-feedback-label"><i class="fas fa-robot"></i> AI 点评</div>';
                    html += '<div class="sa-feedback-text" id="sa-feedback-text-' + index + '"></div>';
                    html += '<span class="typing-cursor" id="sa-cursor-' + index + '"></span>';
                    html += '</div>';
                }
                if (result.correct_answer) {
                    html += '<div style="font-size:11px;color:var(--text-secondary);margin-top:8px;">参考答案：' + this._escapeHtml(result.correct_answer) + '</div>';
                }
                html += '</div>';
            } else {
                // Show options in review mode
                html += this._renderChoiceOptionsReview(q, index, result, type);
                if (result.feedback) {
                    html += '<div style="padding:8px 16px 14px;font-size:12px;color:var(--text-secondary);line-height:1.5;">';
                    html += '<i class="fas fa-lightbulb" style="color:#fbbf24;margin-right:4px;"></i>';
                    html += this._escapeHtml(result.feedback);
                    html += '</div>';
                }
            }

            html += '</div>';
            return html;
        }

        _renderChoiceOptionsReview(q, index, result, type) {
            var options = q.options || [];
            var labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            var correctAnswer = result.correct_answer || '';
            var isMulti = type === 'multiple';
            var userSet = new Set();
            var correctSet = new Set();

            if (isMulti) {
                var existing = this.quizUserAnswers[index];
                if (existing && existing.values) userSet = new Set(existing.values);
                if (q.correct_answers) correctSet = new Set(q.correct_answers);
            } else {
                var existing = this.quizUserAnswers[index];
                if (existing && existing.value >= 0) userSet = new Set([existing.value]);
                correctSet = new Set([q.correct_answer]);
            }

            var html = '<div class="question-options">';
            options.forEach(function(opt, oi) {
                var isUserSelected = userSet.has(oi);
                var isCorrectOption = correctSet.has(oi);
                var cls = '';
                if (isCorrectOption) cls = ' correct';
                else if (isUserSelected && !isCorrectOption) cls = ' incorrect';

                var iconHtml = '';
                if (isCorrectOption) iconHtml = '<i class="fas fa-check" style="color:#34d399;font-size:12px;margin-left:auto;"></i>';
                else if (isUserSelected && !isCorrectOption) iconHtml = '<i class="fas fa-times" style="color:#f87171;font-size:12px;margin-left:auto;"></i>';

                html += '<div class="quiz-option' + cls + '">';
                html += '<div class="quiz-option-radio' + (isMulti ? ' multi' : '') + ' review-icon">';
                if (isUserSelected) html += '<i class="fas ' + (isCorrectOption ? 'fa-check' : 'fa-times') + '" style="font-size:12px;"></i>';
                html += '</div>';
                html += '<span class="quiz-option-text">' + labels[oi] + '. ' + this._escapeHtml(typeof opt === 'string' ? opt : (opt.text || opt.key || '')) + '</span>';
                html += iconHtml;
                html += '</div>';
            }.bind(this));
            html += '</div>';
            return html;
        }

        _typewriteAllFeedback(results, idx) {
            if (idx >= results.length) return;
            var self = this;
            var r = results[idx];
            var textEl = document.getElementById('sa-feedback-text-' + r.question_index);
            var cursorEl = document.getElementById('sa-cursor-' + r.question_index);
            if (!textEl) {
                // No element — skip to next
                this._typewriteAllFeedback(results, idx + 1);
                return;
            }
            this._typewriteFeedback(textEl, cursorEl, r.feedback, 25, function() {
                self._typewriteAllFeedback(results, idx + 1);
            });
        }

        _typewriteFeedback(textEl, cursorEl, text, speed, onDone) {
            var i = 0;
            textEl.textContent = '';
            var interval = setInterval(function() {
                if (i < text.length) {
                    textEl.textContent += text.charAt(i);
                    i++;
                } else {
                    clearInterval(interval);
                    if (cursorEl) cursorEl.style.display = 'none';
                    if (onDone) onDone();
                }
            }, speed);
        }

        retryQuiz() {
            this.quizPhase = 'not_started';
            this.quizUserAnswers = {};
            this.quizResults = [];

            if (this.quizReviewArea) this.quizReviewArea.style.display = 'none';
            if (this.quizRetryBtn) this.quizRetryBtn.style.display = 'none';
            if (this.quizSubmitBtn) this.quizSubmitBtn.style.display = 'none';

            // Reset question cards (remove review classes)
            var allCards = this.quizQuestionsArea?.querySelectorAll('.question-card');
            if (allCards) {
                allCards.forEach(function(c) {
                    c.classList.remove('review-correct', 'review-incorrect');
                });
            }

            // Go back to cover
            this._renderQuizCover(this.currentQuizScene);
            if (this.quizCover) this.quizCover.style.display = 'flex';
            if (this.quizQuestionsArea) this.quizQuestionsArea.style.display = 'none';
            if (this.quizGrading) this.quizGrading.style.display = 'none';
        }

        closeQuizPopup() {
            if (this.quizPopupOverlay) {
                this.quizPopupOverlay.style.display = 'none';
            }

            // Remove dimming
            if (this.slideViewer) {
                this.slideViewer.classList.remove('slide-viewer-dimmed');
            }

            // Reset quiz state
            this.quizPhase = 'not_started';
            this.currentQuizScene = null;
            this.quizUserAnswers = {};
            this.quizResults = [];

            // Hide all phase containers
            if (this.quizCover) this.quizCover.style.display = 'none';
            if (this.quizQuestionsArea) this.quizQuestionsArea.style.display = 'none';
            if (this.quizGrading) this.quizGrading.style.display = 'none';
            if (this.quizReviewArea) this.quizReviewArea.style.display = 'none';
            if (this.quizPopupFooter) this.quizPopupFooter.style.display = 'none';

            // Update toggle button
            if (this.quizToggleBtn) this.quizToggleBtn.classList.remove('active');

            // Restore speech if it was playing before
            if (this._wasSpeakingBeforeQuiz) {
                this._wasSpeakingBeforeQuiz = false;
                this.isPlaying = true;
                this.voiceBtn?.classList.add('playing');
                var vi = this.voiceBtn?.querySelector('i');
                if (vi) vi.className = 'fas fa-volume-mute';
                this.playSceneAudio(this.scenes[this.currentIndex]);
            }

            // Check completion (quiz answers were already stored)
            this.checkCompletion();
        }

        _gradeLocallyAndShow(questions, answers, quiz) {
            // Fallback: local-only grading when API is unavailable
            var results = [];
            var totalScore = 0;
            var totalPoints = 0;

            questions.forEach(function(q, i) {
                var type = q.question_type || 'single';
                var points = q.points || 10;
                totalPoints += points;

                var ans = answers[i];
                var isCorrect = false;
                var score = 0;
                var feedback = '';

                if (type === 'single') {
                    var userVal = ans ? parseInt(ans.answer_value) : -1;
                    isCorrect = (userVal === q.correct_answer) && userVal >= 0;
                    score = isCorrect ? points : 0;
                    var optLabel = q.options && q.options[q.correct_answer] ? q.options[q.correct_answer] : '';
                    feedback = isCorrect
                        ? '回答正确！'
                        : '回答错误。正确答案是 ' + String.fromCharCode(65 + (q.correct_answer || 0)) + '. ' + (typeof optLabel === 'string' ? optLabel : '');
                } else if (type === 'multiple') {
                    var userVals = ans ? (ans.answer_values || []) : [];
                    var correctVals = q.correct_answers || [];
                    var userSet = new Set(userVals);
                    var correctSet = new Set(correctVals);
                    isCorrect = userSet.size === correctSet.size && Array.from(userSet).every(function(v) { return correctSet.has(v); });
                    score = isCorrect ? points : 0;
                    feedback = isCorrect
                        ? '回答正确！'
                        : '回答不完整或有误。';
                } else {
                    // Short answer — can't grade locally
                    score = Math.round(points * 0.5);
                    feedback = '已收到你的答案（本地评分无法评估简答题，请联网后重试）。';
                }

                totalScore += score;
                results.push({
                    question_index: i,
                    is_correct: isCorrect,
                    score: score,
                    total_points: points,
                    feedback: feedback,
                    correct_answer: q.answer || (q.options && q.options[q.correct_answer]) || '',
                    key_points_hit: [],
                    key_points_missed: [],
                    graded_by: 'local'
                });
            });

            var percentage = totalPoints > 0 ? Math.round(totalScore / totalPoints * 100) : 0;
            this.showQuizResults({
                results: results,
                total_score: totalScore,
                total_points: totalPoints,
                percentage: percentage,
                passed: percentage >= 60,
                graded_count: results.length
            });
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
            // Sync dropdown menu active state
            const menu = document.getElementById('speed-menu');
            if (menu) {
                menu.querySelectorAll('.speed-option').forEach(opt => {
                    var optSpeed = parseFloat(opt.dataset.speed);
                    opt.classList.toggle('active', optSpeed === speed);
                });
            }
        }

        toggleSpeedMenu() {
            const menu = document.getElementById('speed-menu');
            if (!menu) return;
            const isOpen = menu.style.display !== 'none';
            menu.style.display = isOpen ? 'none' : 'block';
        }

        closeSpeedMenu() {
            const menu = document.getElementById('speed-menu');
            if (menu) menu.style.display = 'none';
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

    // Expose classroom as global alias for dynamically added methods
    window.classroom = classroomController;
    window.classroomController = classroomController;
})();
