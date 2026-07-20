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

    // MiniMax TTS voice mapping (string key -> {index, name, description})
    // index 0-4 maps to /api/socratic/tts voice_id
    const MINIMAX_VOICES = {
        'female-shaonv': { index: 0, name: '晓雅', description: '活泼可爱的年轻女声' },
        'female-yujie': { index: 0, name: '晓雅', description: '成熟温柔的姐姐声音' },
        'female-danyun': { index: 4, name: '雅典娜', description: '知性优雅的女性声音' },
        'male-qingshu': { index: 1, name: '云起', description: '清新自然的年轻男声' },
        'male-shaoshuai': { index: 2, name: '雨辰', description: '沉稳磁性的成熟男声' }
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
            this.currentTeacher = null;
            this.quizAnswers = {};
            this.visitedScenes = new Set();
            this.isPlaying = false;
            this.isChatLoading = false;
            this.chatHistory = [];
            this.sceneStartTime = Date.now();
            this.totalTimeSpent = 0;
            this.currentAudio = null;
            this.settings = {};

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

            // Discussion state
            this.discussionActive = false;
            this.discussionMessages = [];
            this.discussionStreamController = null;
            this.currentDiscussionTab = 'qa';

            // Whiteboard state
            this.whiteboardRenderer = null;
            this.whiteboardContainer = document.getElementById('whiteboard-container');
            this.whiteboardStage = document.getElementById('whiteboard-stage');
            this.whiteboardToggleBtn = document.getElementById('whiteboard-toggle-btn');
            this.whiteboardClearBtn = document.getElementById('wb-clear-btn');
            this.whiteboardAIDrawBtn = document.getElementById('wb-ai-draw-btn');
            this.wbTextBtn = document.getElementById('wb-text-btn');
            this.wbThemeBtn = document.getElementById('wb-theme-btn');
            this.wbPenGroup = document.getElementById('wb-pen-group');
            this.wbPenToggleBtn = document.getElementById('wb-pen-toggle-btn');
            this.wbEraserBtn = document.getElementById('wb-eraser-btn');
            this.wbPenUndoBtn = document.getElementById('wb-pen-undo-btn');
            this.wbPenWidthInput = document.getElementById('wb-pen-width');
            this.wbTheme = 'light'; // 'light' | 'dark'

            // Animation state
            this.currentAnimationEffects = [];
            this.isTransitioning = false;
            this.animationQueue = [];

            // TTS 预加载状态（按需：用户停留7秒后预加载下一场景）
            this._ttsPreloadTimer = null;
            this._ttsPreloadPromises = new Map(); // sceneId -> Promise

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
            this.teacherArea = document.getElementById('teacher-area');
            this.teacherStatus = document.getElementById('teacher-status');
            this.speechText = document.getElementById('speech-text');
            this.voiceWaveform = document.getElementById('voice-waveform');
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
            this.chatPanel = document.getElementById('chat-panel');
            this.chatToggleBtn = document.getElementById('chat-toggle-btn');
            this.discussionArea = document.getElementById('discussion-area');
            this.discussionMessages = document.getElementById('discussion-messages');
            this.discussionStartBtn = document.getElementById('discussion-start-btn');
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
                    onWhiteboardAction: function(action) {
                        self.executeWhiteboardAction(action);
                    },
                    onGenerateTTS: function(text) {
                        const voiceId = self.ttsConfig?.voice || TTS_CONFIG.voice;
                        const speed = self.ttsConfig?.speed || TTS_CONFIG.speed;
                        return self.generateTTS(text, voiceId, speed);
                    },
                });
            }

            // Speech recognition for chat
            this.chatVoiceBtn = document.getElementById('chat-voice-btn');
            this.chatRecognition = null;
            this.chatIsRecording = false;
            this.chatInterimText = '';
        }

        _escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;')
                      .replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;')
                      .replace(/'/g, '&#039;');
        }

        // ---- Init ----

        async init() {
            this.loadData();

            // 兜底: 当 sessionStorage 没有数据时, 从 URL ?course_id= 取, 调 GET /api/v2/classroom/{id} 拉取
            if (!this.courseData) {
                const cid = (new URLSearchParams(location.search)).get('course_id')
                    || sessionStorage.getItem('courseId')
                    || null;
                if (cid) {
                    try {
                        const r = await fetch('/api/v2/classroom/' + encodeURIComponent(cid), {
                            headers: { 'Accept': 'application/json' }
                        });
                        if (r.ok) {
                            const resp = await r.json();
                            const cd = (resp && resp.record && resp.record.course_data)
                                || (resp && resp.course_data)
                                || (resp && resp.record)
                                || null;
                            if (cd && (cd.outlines || cd.slides_v2 || cd.bundle || cd.title)) {
                                this.courseData = cd;
                                if (!this.courseData.courseId) this.courseData.courseId = cid;
                                this.courseId = this.courseData.courseId;
                                try { sessionStorage.setItem('classroomData', JSON.stringify(this.courseData)); } catch (e) {}
                            }
                        } else if (r.status === 404) {
                            alert('课堂数据不存在或已被删除 (course_id: ' + cid + '), 正在返回首页...');
                            window.location.href = '/index.html';
                            return;
                        }
                    } catch (e) {
                        console.warn('[classroom] Fallback fetch failed:', e);
                    }
                }
            }

            if (!this.courseData) {
                alert('未找到课堂数据，正在返回首页...');
                window.location.href = '/index.html';
                return;
            }

            // 验证: courseData 必须有 outlines 或 slides_v2, 否则视为空数据
            const hasContent = (Array.isArray(this.courseData.outlines) && this.courseData.outlines.length > 0)
                || (Array.isArray(this.courseData.slides_v2) && this.courseData.slides_v2.length > 0)
                || (Array.isArray(this.courseData.slides) && this.courseData.slides.length > 0)
                || (this.courseData.bundle);
            if (!hasContent) {
                // 生成中状态: 保留 courseId 但显示生成占位符, 让后台轮询去拉数据
                console.warn('[classroom] courseData 缺少可渲染内容 (可能正在生成中):', Object.keys(this.courseData || {}));
                if (this.courseId) {
                    this._showGeneratingPlaceholder();
                    // 仍然 init UI 但不 buildScenes, 让后续轮询填充内容
                    this.setupUI();
                    this.bindEvents();
                    this.initVoiceSelector();
                    this.initTTS();
                    this.startBackgroundPolling();
                    return;
                }
                alert('课堂数据为空，正在返回首页...');
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
            this.initTeacherAreaInteraction();
            this.loadSettings(); // Load saved settings
            this.startEyeBlinkScheduler();
            // 启动后台轮询（如果courseId存在且生成未完成）
            this.startBackgroundPolling();
        }

        loadData() {
            const saved = sessionStorage.getItem('classroomData');
            if (saved) {
                try { this.courseData = JSON.parse(saved); } catch (e) {}
            }
            if (this.courseData) {
                this.agentTeam = this.courseData.agent_team || [];

                // 加载分配的老师配置
                if (this.courseData && this.courseData.teacher) {
                    this.currentTeacher = this.courseData.teacher;
                } else if (this.courseData && this.courseData.agent_team && this.courseData.agent_team.length > 0) {
                    // 兼容旧的agent_team结构
                    this.currentTeacher = this.courseData.agent_team[0];
                }

                // 如果有指定音色，优先使用老师的音色
                // 兼容 voiceId（驼峰，来自 agent_team）和 voice_id（下划线，来自 TeacherInfo）
                const teacherVoice = this.currentTeacher && (this.currentTeacher.voiceId || this.currentTeacher.voice_id);
                if (teacherVoice && MINIMAX_VOICES[teacherVoice]) {
                    TTS_CONFIG.voice = teacherVoice;
                }

                this.courseData.tts_audio_urls = this.courseData.tts_audio_urls || {};
                // 保存courseId用于后台轮询
                this.courseId = this.courseData.courseId || this.courseData.metadata?.session_id || sessionStorage.getItem('courseId') || null;

                // 加载渐进式生成的数据（测验、练习、新幻灯片）
                try {
                    const progressiveQuiz = JSON.parse(sessionStorage.getItem('progressiveQuizData') || '[]');
                    const progressiveExercise = JSON.parse(sessionStorage.getItem('progressiveExerciseData') || '[]');
                    const progressiveSlides = JSON.parse(sessionStorage.getItem('progressiveSlides') || '[]');
                    const progressiveSlidesV2 = JSON.parse(sessionStorage.getItem('progressiveSlidesV2') || '[]');

                    // 合并到courseData
                    if (progressiveQuiz.length > 0) {
                        this.courseData.quiz_data = (this.courseData.quiz_data || []).concat(progressiveQuiz);
                    }
                    if (progressiveExercise.length > 0) {
                        this.courseData.exercise_data = (this.courseData.exercise_data || []).concat(progressiveExercise);
                    }
                    if (progressiveSlides.length > 0) {
                        this.courseData.slides = (this.courseData.slides || []).concat(progressiveSlides);
                    }
                    if (progressiveSlidesV2.length > 0) {
                        this.courseData.slides_v2 = (this.courseData.slides_v2 || []).concat(progressiveSlidesV2);
                    }
                    // 加载渐进式 code_data
                    try {
                        const progressiveCode = JSON.parse(sessionStorage.getItem('progressiveCodeData') || '[]');
                        if (progressiveCode.length > 0) {
                            this.courseData.code_data = (this.courseData.code_data || []).concat(progressiveCode);
                        }
                    } catch (e) {
                        console.warn('[classroom] Failed to load progressive code data:', e);
                    }
                } catch (e) {
                    console.warn('[classroom] Failed to load progressive data:', e);
                }
            }
        }

        // ---- 后台轮询：增量加载新幻灯片 ----
        startBackgroundPolling() {
            if (!this.courseId) {
                console.warn('[classroom] No courseId, skipping background polling');
                return;
            }
            console.log('[classroom] Starting background polling for courseId:', this.courseId);
            const self = this;
            let consecutiveFails = 0;
            this.pollingInterval = setInterval(async function() {
                try {
                    // 优先尝试轮询 pending 接口
                    const resp = await fetch(`/api/v2/course/${self.courseId}/slides/pending`);
                    if (resp.ok) {
                        const data = await resp.json();
                        consecutiveFails = 0;
                        console.log('[classroom] Poll result:', {
                            pendingV2: (data.pending_slides_v2 || []).length,
                            pendingQuiz: (data.pending_quiz_data || []).length,
                            pendingExercise: (data.pending_exercise_data || []).length,
                            isComplete: data.is_complete,
                            generatedCount: data.generated_count,
                            totalOutlines: data.total_outlines
                        });
                        // 处理 pending slides / quiz / exercise
                        const hasPending = (data.pending_slides_v2 && data.pending_slides_v2.length > 0) ||
                                           (data.pending_quiz_data && data.pending_quiz_data.length > 0) ||
                                           (data.pending_exercise_data && data.pending_exercise_data.length > 0);
                        if (hasPending) {
                            const addedCount = self.addNewScenes(data);
                            // 消费成功后通知后端清空已消费的 slides，避免重复轮询
                            if (addedCount > 0 && data.pending_slides_v2 && data.pending_slides_v2.length > 0) {
                                try {
                                    const consumedTitles = data.pending_slides_v2.map(function(s) { return s.title; });
                                    await fetch(`/api/v2/course/${self.courseId}/slides/consume`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ consumed_slide_titles: consumedTitles })
                                    });
                                    console.log('[classroom] Consumed pending slides, titles:', consumedTitles);
                                } catch (consumeErr) {
                                    console.warn('[classroom] Failed to consume pending slides:', consumeErr);
                                }
                            }
                        }
                        // 只有确认 total_outlines > 0 且 generated_count >= total_outlines 时才认为真正完成
                        // 避免数据库无记录时错误返回 is_complete=True 导致停止轮询
                        const trulyComplete = data.is_complete && data.total_outlines > 0 && data.generated_count >= data.total_outlines;
                        if (trulyComplete) {
                            console.log('[classroom] Generation truly complete (generated_count >= total_outlines), stopping poll');
                            clearInterval(self.pollingInterval);
                            // 生成完成后保存到本地历史，确保最近课堂能显示
                            self._saveToRecentHistory();
                            // 同步完整课程数据到服务器
                            self._persistCourseData();
                            return;
                        }
                    } else if (resp.status === 404) {
                        // pending 接口不存在, 改用 classroom 接口轮询完整课程数据
                        consecutiveFails = 0;
                        try {
                            const clsResp = await fetch('/api/v2/classroom/' + encodeURIComponent(self.courseId));
                            if (clsResp.ok) {
                                const clsData = await clsResp.json();
                                const cd = (clsData && clsData.record && clsData.record.course_data) || (clsData && clsData.course_data) || null;
                                if (cd) {
                                    const hasOutlines = Array.isArray(cd.outlines) && cd.outlines.length > 0;
                                    const hasSlides = Array.isArray(cd.slides_v2) && cd.slides_v2.length > 0;
                                    if (hasOutlines || hasSlides) {
                                        console.log('[classroom] Classroom API returned content, reloading');
                                        try { sessionStorage.setItem('classroomData', JSON.stringify(cd)); } catch (e) {}
                                        // 简单做法: 整页刷新让 classroom.js 重新走正常流程
                                        clearInterval(self.pollingInterval);
                                        window.location.reload();
                                        return;
                                    }
                                }
                            } else if (clsResp.status === 404) {
                                // classroom API 也找不到 → 课程不存在, 停止轮询
                                console.warn('[classroom] Course not found in any table, stopping poll');
                                clearInterval(self.pollingInterval);
                                self.pollingInterval = null;
                                return;
                            }
                        } catch (e) {
                            // 静默失败, 继续轮询
                        }
                    } else {
                        console.warn('[classroom] Poll response not OK:', resp.status);
                        consecutiveFails++;
                        if (consecutiveFails >= 3) {
                            console.warn('[classroom] Poll failed', consecutiveFails, 'times, stopping');
                            clearInterval(self.pollingInterval);
                            self.pollingInterval = null;
                        }
                        return;
                    }
                } catch (e) {
                    console.warn('[classroom] Polling error:', e);
                }
            }, 5000);
        }

        addNewScenes(data) {
            const pendingV2 = data.pending_slides_v2 || [];
            const pendingQuiz = data.pending_quiz_data || [];
            const pendingExercise = data.pending_exercise_data || [];

            const self = this;
            let addedCount = 0;

            // 同步到 courseData
            if (!this.courseData.quiz_data) this.courseData.quiz_data = [];
            if (!this.courseData.exercise_data) this.courseData.exercise_data = [];
            if (!this.courseData.slides_v2) this.courseData.slides_v2 = [];

            // 处理只有quiz/exercise数据但没有slides_v2的场景（如测验场景）
            pendingQuiz.forEach(function(quizItem) {
                // 检查是否已存在该quiz场景
                const exists = self.scenes.some(function(s) {
                    return s.id === quizItem.scene_id;
                });
                if (exists) {
                    // 更新已有场景的quiz数据
                    const scene = self.scenes.find(function(s) { return s.id === quizItem.scene_id; });
                    if (scene && !scene.quiz) {
                        scene.quiz = quizItem;
                        console.log('[Classroom] Updated quiz for scene:', scene.id);
                    }
                    return;
                }
                // 同步到 courseData
                self.courseData.quiz_data.push(quizItem);
                // 创建新的quiz场景
                const newScene = {
                    id: quizItem.scene_id || ('quiz_' + Date.now()),
                    title: quizItem.title || '课堂测验',
                    type: 'quiz',
                    slides_v2: [],
                    slide: null,
                    quiz: quizItem,
                    exercise: null,
                    audioUrl: null,
                    imageUrl: null,
                };
                self.scenes.push(newScene);
                addedCount++;
                console.log('[Classroom] Added quiz scene:', newScene.id);
            });

            pendingExercise.forEach(function(exItem) {
                const exists = self.scenes.some(function(s) {
                    return s.id === exItem.scene_id;
                });
                if (exists) {
                    const scene = self.scenes.find(function(s) { return s.id === exItem.scene_id; });
                    if (scene && !scene.exercise) {
                        scene.exercise = exItem;
                    }
                    return;
                }
                // 同步到 courseData
                self.courseData.exercise_data.push(exItem);
                const newScene = {
                    id: exItem.scene_id || ('exercise_' + Date.now()),
                    title: exItem.title || '课堂练习',
                    type: 'exercise',
                    slides_v2: [],
                    slide: null,
                    quiz: null,
                    exercise: exItem,
                    audioUrl: null,
                    imageUrl: null,
                };
                self.scenes.push(newScene);
                addedCount++;
            });

            // 处理新的slides_v2数据
            if (pendingV2.length === 0) {
                if (addedCount > 0) {
                    this.renderSceneSidebar();
                    if (this.totalSlidesEl) {
                        this.totalSlidesEl.textContent = this.scenes.length;
                    }
                    this.showNewScenesToast(addedCount);
                    this._persistCourseData();
                }
                return addedCount;
            }

            pendingV2.forEach(function(slideV2) {
                // Try to merge into existing scene by scene_id or originalId
                var merged = false;
                if (slideV2.scene_id != null) {
                    var matchedScene = self.scenes.find(function(s) {
                        return String(s.id) === String(slideV2.scene_id) ||
                               String(s.originalId) === String(slideV2.scene_id);
                    });
                    if (matchedScene) {
                        // Check duplicate by title AND layout_type within the scene (more robust than title alone)
                        var slideExists = matchedScene.slides_v2.some(function(s) {
                            return s.title === slideV2.title &&
                                   (s.layout_type || s.layoutType) === (slideV2.layout_type || slideV2.layoutType);
                        });
                        if (!slideExists) {
                            matchedScene.slides_v2.push(slideV2);
                            self.courseData.slides_v2.push(slideV2);
                            addedCount++;
                            console.log('[Classroom] Merged slide into scene:', matchedScene.id, 'title:', slideV2.title);
                            // 如果当前正在查看该场景，实时刷新内容
                            if (self.currentIndex === self.scenes.indexOf(matchedScene)) {
                                self.renderScene(self.currentIndex);
                            }
                        } else {
                            console.log('[Classroom] Skipped duplicate slide in scene:', matchedScene.id, 'title:', slideV2.title);
                        }
                        merged = true;
                    }
                }
                if (merged) return;

                // Fallback: check global duplicate by scene_id + title (more robust than title alone)
                const exists = self.scenes.some(function(s) {
                    return s.slides_v2 && s.slides_v2.length > 0 &&
                           (String(s.id) === String(slideV2.scene_id) || s.slides_v2[0].title === slideV2.title);
                });
                if (exists) {
                    console.log('[Classroom] Skipped duplicate scene for slide:', slideV2.title, 'scene_id:', slideV2.scene_id);
                    return;
                }

                // 检测是否为欢迎页：去重且置顶
                const isWelcome = (slideV2.layout_type || slideV2.layoutType) === 'edu-welcome';
                if (isWelcome) {
                    const hasWelcome = self.scenes.some(function(s) {
                        return s.slides_v2 && s.slides_v2.length > 0 &&
                               (s.slides_v2[0].layout_type === 'edu-welcome' || s.slides_v2[0].layoutType === 'edu-welcome');
                    });
                    if (hasWelcome) return; // 跳过重复的欢迎页
                }

                // Create new scene
                const newScene = {
                    id: slideV2.scene_id || ('scene_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)),
                    title: slideV2.title || '新页面',
                    type: 'slide',
                    slides_v2: [slideV2],
                    slide: null,
                    quiz: null,
                    exercise: null,
                    audioUrl: null,
                    imageUrl: slideV2.content && slideV2.content[0] && slideV2.content[0].image_url || null,
                    actions: slideV2.actions || null,
                };

                // Try matching quiz or exercise
                const matchedQuiz = pendingQuiz.find(function(q) {
                    return q.scene_id === slideV2.scene_id;
                });
                if (matchedQuiz) newScene.quiz = matchedQuiz;

                const matchedExercise = pendingExercise.find(function(e) {
                    return e.scene_id === slideV2.scene_id;
                });
                if (matchedExercise) newScene.exercise = matchedExercise;

                self.courseData.slides_v2.push(slideV2);
                if (isWelcome) {
                    self.scenes.unshift(newScene); // 欢迎页插入到开头
                } else {
                    self.scenes.push(newScene);
                }
                addedCount++;
                console.log('[Classroom] Created new scene for slide:', slideV2.title, 'scene_id:', newScene.id);
            });

            if (addedCount > 0) {
                console.log(`[classroom] Added ${addedCount} new scenes, total now: ${this.scenes.length}`);
                // 重新渲染侧边栏
                this.renderSceneSidebar();
                // 更新总页数
                if (this.totalSlidesEl) {
                    this.totalSlidesEl.textContent = this.scenes.length;
                }
                // 显示提示
                this.showNewScenesToast(addedCount);
                // 高亮闪烁新添加的场景（最后 N 个）
                setTimeout(function() {
                    const thumbs = self.sceneThumbnails?.querySelectorAll('.scene-thumb');
                    if (thumbs) {
                        for (var i = thumbs.length - addedCount; i < thumbs.length; i++) {
                            if (thumbs[i]) thumbs[i].classList.add('scene-thumb-new');
                        }
                    }
                }, 150);
                this._persistCourseData();
            }
            return addedCount;
        }

        showNewScenesToast(count) {
            const toast = document.createElement('div');
            toast.className = 'new-scenes-toast';
            toast.innerHTML = `<i class="fas fa-plus-circle"></i> 已添加 ${count} 个新页面`;
            toast.style.cssText = 'position:fixed;top:80px;left:50%;transform:translateX(-50%);' +
                'background:linear-gradient(135deg,var(--primary),var(--accent));' +
                'color:#fff;padding:12px 24px;border-radius:24px;z-index:9999;' +
                'animation:slideDown 0.3s ease';
            document.body.appendChild(toast);
            setTimeout(function() {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s';
                setTimeout(function() { toast.remove(); }, 300);
            }, 3000);
        }

        _saveToRecentHistory() {
            try {
                const courseId = this.courseId || this.courseData?.courseId || '';
                const title = this.courseData?.title || '未命名课程';
                if (!courseId) return;
                const historyKey = 'courseHistory';
                let history = JSON.parse(localStorage.getItem(historyKey) || '[]');
                const existingIndex = history.findIndex(function(c) { return c.courseId === courseId; });
                const entry = {
                    courseId: courseId,
                    title: title,
                    createdAt: Date.now(),
                    slideCount: this.scenes.length || 0,
                    _dbRecord: {
                        course_id: courseId,
                        title: title,
                        ppt_pages: this.scenes.length || 0,
                        created_at: new Date().toISOString()
                    }
                };
                if (existingIndex >= 0) {
                    history[existingIndex] = entry;
                } else {
                    history.unshift(entry);
                }
                if (history.length > 20) {
                    history = history.slice(0, 20);
                }
                localStorage.setItem(historyKey, JSON.stringify(history));
                console.log('[classroom] Saved to recent history:', courseId);
            } catch (e) {
                console.warn('[classroom] Failed to save recent history:', e);
            }
        }

        _persistCourseData() {
            try {
                if (!this.courseData) return;
                // 更新 sessionStorage
                sessionStorage.setItem('classroomData', JSON.stringify(this.courseData));
                // 同步到服务器
                const courseId = this.courseData.courseId || this.courseData.course_id || '';
                if (!courseId) return;
                const currentUser = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
                const studentId = String(currentUser.id || this.courseData.metadata?.student_id || '');
                const pageCount = this.scenes.length || 0;
                fetch('/api/v2/course/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        course_data: this.courseData,
                        student_id: studentId,
                        ppt_pages: pageCount
                    })
                }).then(function(resp) {
                    if (!resp.ok) {
                        console.warn('[classroom] Server save failed:', resp.status);
                    } else {
                        console.log('[classroom] Course data persisted to server:', courseId);
                    }
                }).catch(function(err) {
                    console.warn('[classroom] Server save error:', err);
                });
            } catch (e) {
                console.warn('[classroom] Failed to persist course data:', e);
            }
        }

        buildScenes() {
            // 兼容 outlines 是 dict/object 或 null 的情况, 始终归一为数组
            const normalizeList = (v) => {
                if (Array.isArray(v)) return v;
                if (v && typeof v === 'object') {
                    // 常见 schema: {items: [...]}, {scenes: [...]}, {outlines: [...]}
                    for (const k of ['items', 'scenes', 'outlines', 'data']) {
                        if (Array.isArray(v[k])) return v[k];
                    }
                    // 否则视为空数组, 避免 .map 失败
                    return [];
                }
                return Array.isArray(v) ? v : [];
            };
            const outlines = normalizeList(this.courseData.outlines);
            const slides = normalizeList(this.courseData.slides);
            const quizData = normalizeList(this.courseData.quiz_data);
            const exerciseData = normalizeList(this.courseData.exercise_data);
            const codeData = normalizeList(this.courseData.code_data);
            const slidesV2 = normalizeList(this.courseData.slides_v2);

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
            const findSceneDataAll = function(items, outline) {
                var matches = (items || []).filter(function(item) { return matchesScene(item, outline); });
                return matches.length > 0 ? matches : null;
            };
            const findSceneData = function(items, outline) {
                var matches = findSceneDataAll(items, outline);
                return matches ? matches[0] : null;
            };

            // slides_v2 now includes scene_id from MiniMax PPT provider
            // Use findSceneDataAll for scene_id matching (Strategy 1), fallback to index for legacy
            var usedSlideV2Indices = new Set();
            var usedSlideIndices = new Set();
            this.scenes = outlines.map(function(outline, i) {
                var sceneId = outline.id || i + 1;
                var matchedSlide = findSceneData(slides, outline);
                var matchedSlidesV2 = findSceneDataAll(slidesV2, outline);

                // Fallback: if no scene_id match, find by index or first valid slides_v2 entry with content
                if (!matchedSlidesV2) {
                    if (i < slidesV2.length) {
                        var candidate = slidesV2[i];
                        // If the indexed entry has no content, scan forward to find the first with valid content
                        var hasContent = (candidate.elements && candidate.elements.length > 0) ||
                                         (candidate.content && candidate.content.length > 0);
                        if (!hasContent) {
                            for (var j = i; j < slidesV2.length; j++) {
                                var c = slidesV2[j];
                                if ((c.elements && c.elements.length > 0) || (c.content && c.content.length > 0)) {
                                    candidate = c;
                                    break;
                                }
                            }
                        }
                        matchedSlidesV2 = [candidate];
                    }
                    if (!matchedSlidesV2) matchedSlidesV2 = null;
                }

                // Track which slidesV2 are matched to outlines
                if (matchedSlidesV2) {
                    matchedSlidesV2.forEach(function(s) {
                        var matchedIdx = slidesV2.indexOf(s);
                        if (matchedIdx >= 0) usedSlideV2Indices.add(matchedIdx);
                    });
                }

                // Track which legacy slides are matched to outlines
                if (matchedSlide) {
                    var matchedSlideIdx = slides.indexOf(matchedSlide);
                    if (matchedSlideIdx >= 0) usedSlideIndices.add(matchedSlideIdx);
                }

                var matchedQuiz = findSceneData(quizData, outline);
                var matchedExercise = findSceneData(exerciseData, outline);
                var matchedCode = findSceneData(codeData, outline);

                var isWb = outline.type === 'whiteboard';
                var wbDesc = isWb ? (outline.whiteboard_description || outline.description || outline.title) : null;
                var wbActions = isWb ? (outline.whiteboard_actions || null) : null;
                return {
                    id: sceneId,
                    originalId: sceneId,
                    title: outline.title || ('Scene ' + sceneId),
                    type: outline.type || 'slide',
                    description: outline.description || '',
                    keyPoints: outline.key_points || outline.keyPoints || [],
                    slide: matchedSlide,
                    slides_v2: matchedSlidesV2 || [],
                    quiz: matchedQuiz,
                    exercise: matchedExercise,
                    code_data: matchedCode,
                    audioUrl: (this.courseData.tts_audio_urls || {})[String(sceneId)] || null,
                    imageUrl: (matchedSlide && matchedSlide.content && matchedSlide.content.elements && matchedSlide.content.elements[0] && matchedSlide.content.elements[0].image_url) || null,
                    whiteboard_description: wbDesc,
                    whiteboard_actions: wbActions,
                };
            }, this);

            // Add remaining slides_v2 that weren't matched to any outline as extra scenes
            slidesV2.forEach(function(slideV2, i) {
                if (!usedSlideV2Indices.has(i)) {
                    this.scenes.push({
                        id: slideV2.scene_id || slideV2.id || ('slide-' + i),
                        title: slideV2.title || ('幻灯片 ' + (i + 1)),
                        type: 'slide',
                        description: '',
                        keyPoints: [],
                        slide: null,
                        slides_v2: [slideV2],
                        quiz: null,
                        exercise: null,
                        code_data: null,
                        audioUrl: null,
                        imageUrl: null,
                    });
                }
            }, this);

            // Add remaining legacy slides that weren't matched to any outline as extra scenes
            slides.forEach(function(slide, i) {
                if (!usedSlideIndices.has(i)) {
                    this.scenes.push({
                        id: slide.scene_id || slide.sceneId || slide.id || ('slide-' + i),
                        title: slide.title || ('幻灯片 ' + (i + 1)),
                        type: 'slide',
                        description: '',
                        keyPoints: [],
                        slide: slide,
                        slides_v2: [],
                        quiz: null,
                        exercise: null,
                        code_data: null,
                        audioUrl: null,
                        imageUrl: (slide.content && slide.content.elements && slide.content.elements[0] && slide.content.elements[0].image_url) || null,
                    });
                }
            }, this);

            // Expand scenes that contain multiple slides into individual scenes
            this.expandMultiSlideScenes();

            // Redistribute consecutive non-slide scenes to prevent clustering
            this.redistributeConsecutiveNonSlideScenes();
        }

        redistributeConsecutiveNonSlideScenes() {
            // AI-driven scene placement: redistribute consecutive non-slide scenes
            // to appear at pedagogically appropriate positions with good spacing
            const NON_SLIDE_TYPES = new Set(['quiz', 'exercise', 'interactive', 'pbl', 'diagram', 'code', 'video']);

            if (this.scenes.length < 4) return;

            // Identify consecutive non-slide clusters (only clusters with 2+ non-slides)
            const clusters = [];
            let clusterStart = -1;
            let consecutiveNonSlides = 0;
            let prevNonSlide = false;

            for (let i = 0; i < this.scenes.length; i++) {
                const isNonSlide = NON_SLIDE_TYPES.has(this.scenes[i].type);
                if (isNonSlide) {
                    if (!prevNonSlide) {
                        clusterStart = i;
                        consecutiveNonSlides = 1;
                    } else {
                        consecutiveNonSlides++;
                    }
                } else {
                    if (consecutiveNonSlides >= 2) {
                        clusters.push({ start: clusterStart, end: i - 1, count: consecutiveNonSlides });
                    }
                    consecutiveNonSlides = 0;
                }
                prevNonSlide = isNonSlide;
            }
            // Handle trailing cluster
            if (consecutiveNonSlides >= 2) {
                clusters.push({ start: clusterStart, end: this.scenes.length - 1, count: consecutiveNonSlides });
            }

            if (clusters.length === 0) return;

            // Build new order: remove clusters and re-distribute non-slide scenes with spacing
            const newOrder = [];
            const nonSlideScenes = [];

            // First pass: collect non-slide scenes and build slide-only order
            for (let i = 0; i < this.scenes.length; i++) {
                const scene = this.scenes[i];
                const inCluster = clusters.some(c => i >= c.start && i <= c.end);

                if (NON_SLIDE_TYPES.has(scene.type) && inCluster) {
                    nonSlideScenes.push(scene);
                } else {
                    newOrder.push(scene);
                }
            }

            // Second pass: redistribute non-slide scenes by interleaving with slides
            // Insert each non-slide after the next available slide
            const result = [];
            let slideIdx = 0;
            const slideCount = newOrder.filter(s => !NON_SLIDE_TYPES.has(s.type)).length;

            if (slideCount === 0 || nonSlideScenes.length === 0) {
                // No slides to interleave with, keep original order
                return;
            }

            // Calculate spread: each non-slide should be roughly slideCount / nonSlideScenes slides apart
            const interval = Math.max(1, Math.floor(slideCount / nonSlideScenes.length));

            for (let i = 0; i < newOrder.length; i++) {
                result.push(newOrder[i]);

                // Check if we should insert a non-slide scene after this slide
                const nonSlideCount = result.filter(s => NON_SLIDE_TYPES.has(s.type)).length;
                if (nonSlideCount < nonSlideScenes.length) {
                    const insertAfter = (i + 1) % (interval + 1) === 0 ||
                                        i === newOrder.length - 1 && nonSlideCount < nonSlideScenes.length;
                    if (insertAfter && slideIdx < nonSlideScenes.length) {
                        result.push(nonSlideScenes[slideIdx++]);
                    }
                }
            }

            // Apply if order changed
            const originalOrder = this.scenes.map(s => s.id).join(',');
            const newOrderIds = result.map(s => s.id).join(',');

            if (originalOrder !== newOrderIds) {
                console.log('[Classroom] Redistributed consecutive non-slide scenes');
                this.scenes = result;
            }
        }

        expandMultiSlideScenes() {
            const expanded = [];
            this.scenes.forEach((scene) => {
                const slides = scene.slides_v2 || [];
                if (slides.length <= 1) {
                    expanded.push(scene);
                    return;
                }
                slides.forEach((slide, idx) => {
                    expanded.push({
                        id: scene.id + '_slide_' + idx,
                        originalId: scene.originalId || scene.id,
                        title: this.SlideRenderer._stripThinkTags(slide.title || scene.title || ('幻灯片 ' + (idx + 1))),
                        type: scene.type || 'slide',
                        description: scene.description || '',
                        keyPoints: scene.keyPoints || [],
                        slide: null,
                        slides_v2: [slide],
                        quiz: idx === 0 ? scene.quiz : null,
                        exercise: idx === 0 ? scene.exercise : null,
                        code_data: idx === 0 ? scene.code_data : null,
                        audioUrl: scene.audioUrl,
                        imageUrl: (slide.content && slide.content[0] && slide.content[0].image_url) ||
                                  (slide.image_url) || scene.imageUrl || null,
                    });
                });
            });
            this.scenes = expanded;
        }

        setupUI() {
            if (this.courseTitle && this.courseData.title) {
                this.courseTitle.textContent = this.SlideRenderer._stripThinkTags(this.courseData.title);
            }
            if (this.totalSlidesEl) {
                this.totalSlidesEl.textContent = this.scenes.length;
            }
            // 同步实际页数到本地历史记录，确保首页显示与课堂一致
            try {
                const actualPageCount = this.scenes.length;
                const courseId = this.courseData.courseId || this.courseData.course_id || '';
                if (courseId && actualPageCount > 0) {
                    // 更新 courseData
                    this.courseData.ppt_pages = actualPageCount;
                    // 更新 localStorage 的 courseHistory
                    const historyKey = 'courseHistory';
                    let history = JSON.parse(localStorage.getItem(historyKey) || '[]');
                    const idx = history.findIndex(c => c.courseId === courseId);
                    if (idx >= 0) {
                        history[idx].slideCount = actualPageCount;
                        history[idx].createdAt = Date.now(); // 更新时间确保合并时本地优先
                        if (history[idx]._dbRecord) {
                            history[idx]._dbRecord.ppt_pages = actualPageCount;
                        }
                        localStorage.setItem(historyKey, JSON.stringify(history));
                    } else {
                        // 如果 history 中还没有该课程，添加一条新记录（确保从外部链接直接进入课堂后也能在首页显示）
                        const newEntry = {
                            courseId: courseId,
                            title: this.courseData.title || '未命名课程',
                            createdAt: Date.now(),
                            slideCount: actualPageCount,
                            slides: this.courseData.slides || [],
                            slides_v2: this.courseData.slides_v2 || [],
                            outlines: this.courseData.outlines || [],
                            agent_team: this.courseData.agent_team || [],
                            quiz_data: this.courseData.quiz_data || [],
                            exercise_data: this.courseData.exercise_data || [],
                            code_data: this.courseData.code_data || [],
                            teacher: this.courseData.teacher || null,
                            metadata: this.courseData.metadata || {},
                            _dbRecord: {
                                course_id: courseId,
                                title: this.courseData.title || '未命名课程',
                                ppt_pages: actualPageCount,
                                created_at: new Date().toISOString()
                            }
                        };
                        history.unshift(newEntry);
                        if (history.length > 20) history = history.slice(0, 20);
                        localStorage.setItem(historyKey, JSON.stringify(history));
                    }
                }
            } catch (e) { /* silent */ }
            // Set teacher avatar - use image if available, otherwise keep kawaii style
            if (this.courseData.teacher) {
                const teacher = this.courseData.teacher;
                if (teacher.avatar && teacher.avatar.startsWith('http')) {
                    this.teacherAvatar.innerHTML = `<img src="${teacher.avatar}" alt="教师" class="avatar-img">`;
                }
                // else: keep the default kawaii face
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
            this.chatToggleBtn?.addEventListener('click', () => {
                this.chatPanel.classList.toggle('collapsed');
                this.chatToggleBtn.classList.toggle('expanded');
            });
            // Chat tab switching
            document.querySelectorAll('.chat-tab').forEach(tab => {
                tab.addEventListener('click', (e) => {
                    const tabName = e.target.dataset.tab;
                    this.switchChatTab(tabName);
                });
            });
            // Discussion start button
            this.discussionStartBtn?.addEventListener('click', () => this.startDiscussion());
            // Close chat panel when clicking on the main content area
            document.getElementById('classroom-page')?.addEventListener('click', (e) => {
                if (e.target.closest('.chat-panel') || e.target.closest('.chat-toggle-btn')) return;
                if (!this.chatPanel.classList.contains('collapsed')) {
                    this.chatPanel.classList.add('collapsed');
                    this.chatToggleBtn.classList.remove('expanded');
                }
                // Tabbed content tab switching
                const tabBtn = e.target.closest('.tab-btn');
                if (tabBtn) {
                    const tabIdx = tabBtn.dataset.tab;
                    const container = tabBtn.closest('.slide-v2-container');
                    container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
                    tabBtn.classList.add('active');
                    container.querySelector(`.tab-panel[data-panel="${tabIdx}"]`)?.classList.add('active');
                }
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
            // Settings
            document.getElementById('settings-btn')?.addEventListener('click', () => this.showSettingsModal());
            document.getElementById('cancel-settings')?.addEventListener('click', () => this.hideSettingsModal());
            document.getElementById('save-settings')?.addEventListener('click', () => this.saveSettings());
            // Whiteboard toggle
            this.whiteboardToggleBtn?.addEventListener('click', () => this.toggleWhiteboard());
            this.whiteboardClearBtn?.addEventListener('click', () => this.clearWhiteboard());
            this.whiteboardAIDrawBtn?.addEventListener('click', () => this._showAIDrawModal());
            this.wbTextBtn?.addEventListener('click', () => this._showTextInputModal());
            this.wbThemeBtn?.addEventListener('click', () => this._toggleWhiteboardTheme());
            // Pen controls
            this.wbPenToggleBtn?.addEventListener('click', () => this._togglePenMode());
            this.wbEraserBtn?.addEventListener('click', () => this._toggleEraserMode());
            this.wbPenUndoBtn?.addEventListener('click', () => {
                const renderer = this._getWhiteboardRenderer();
                if (renderer) renderer.undo();
            });
            this.wbPenWidthInput?.addEventListener('input', (e) => {
                const renderer = this._getWhiteboardRenderer();
                if (renderer) renderer.setPenWidth(parseInt(e.target.value, 10) || 3);
            });
            document.querySelectorAll('.wb-pen-color').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const color = e.currentTarget.dataset.color;
                    const renderer = this._getWhiteboardRenderer();
                    if (renderer) renderer.setPenColor(color);
                    document.querySelectorAll('.wb-pen-color').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                });
            });
            // AI draw modal
            document.getElementById('wb-ai-draw-modal-close')?.addEventListener('click', () => this._hideAIDrawModal());
            document.getElementById('wb-ai-draw-modal-cancel')?.addEventListener('click', () => this._hideAIDrawModal());
            document.getElementById('wb-ai-draw-modal-submit')?.addEventListener('click', () => this._submitAIDraw());
            document.getElementById('wb-ai-draw-input')?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && e.ctrlKey) this._submitAIDraw();
            });
            document.querySelectorAll('.wb-modal-example-chip').forEach(chip => {
                chip.addEventListener('click', (e) => {
                    const input = document.getElementById('wb-ai-draw-input');
                    if (input) input.value = e.currentTarget.dataset.example;
                });
            });
            // Text modal
            document.getElementById('wb-text-modal-close')?.addEventListener('click', () => this._hideTextModal());
            document.getElementById('wb-text-modal-cancel')?.addEventListener('click', () => this._hideTextModal());
            document.getElementById('wb-text-modal-submit')?.addEventListener('click', () => this._submitTextInput());
            document.getElementById('wb-text-input')?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this._submitTextInput();
            });
            document.getElementById('wb-text-size')?.addEventListener('input', (e) => {
                document.getElementById('wb-text-size-value').textContent = e.target.value + 'px';
            });
            document.querySelectorAll('.wb-text-color').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.wb-text-color').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                });
            });
            // Quiz popup buttons
            this.quizToggleBtn?.addEventListener('click', () => this._onQuizToggleClick());
            this.quizCloseBtn?.addEventListener('click', () => this.closeQuizPopup());
            this.quizStartBtn?.addEventListener('click', () => this.startQuiz());
            this.quizSubmitBtn?.addEventListener('click', () => this._submitForGrading());
            this.quizRetryBtn?.addEventListener('click', () => this.retryQuiz());
            document.addEventListener('keydown', e => this.onKey(e));
            this.initChatVoiceInput();
        }

        // ---- Eye Blink Scheduler ----

        startEyeBlinkScheduler() {
            this._eyeBlinkTimer = null;
            this.scheduleNextBlink();
        }

        scheduleNextBlink() {
            if (this._eyeBlinkTimer) clearTimeout(this._eyeBlinkTimer);
            const interval = Math.random() * 4000 + 2000; // 2-6s
            this._eyeBlinkTimer = setTimeout(() => this.triggerRandomBlink(), interval);
        }

        triggerRandomBlink() {
            const eyes = this.teacherAvatar?.querySelectorAll('.eye');
            if (!eyes || eyes.length === 0) {
                this.scheduleNextBlink();
                return;
            }
            const r = Math.random();
            let className, duration, targetEyes;
            if (r < 0.55) {
                // 55% 单眨
                className = 'blinking-single';
                duration = 400;
                targetEyes = eyes;
            } else if (r < 0.80) {
                // 25% 双眨
                className = 'blinking-double';
                duration = 700;
                targetEyes = eyes;
            } else {
                // 20% wink（单眼眨）
                className = 'blinking-wink';
                duration = 450;
                const eyeIdx = Math.random() < 0.5 ? 0 : 1;
                targetEyes = [eyes[eyeIdx]];
            }
            eyes.forEach(eye => {
                eye.classList.remove('blinking-single', 'blinking-double', 'blinking-wink');
                void eye.offsetWidth; // force reflow
            });
            targetEyes.forEach(eye => eye.classList.add(className));
            setTimeout(() => {
                eyes.forEach(eye => eye.classList.remove(className));
                this.scheduleNextBlink();
            }, duration);
        }

        onKey(e) {
            if (e.target === this.chatInput || e.target === document.getElementById('exercise-answer')) return;
            // Block navigation when quiz popup is open
            var quizOpen = this.quizPopupOverlay && this.quizPopupOverlay.style.display === 'flex';
            switch (e.key) {
                case 'ArrowLeft': if (!quizOpen) this.prevScene(); break;
                case 'ArrowRight': if (!quizOpen) this.nextScene(); break;
                case ' ': e.preventDefault(); this.toggleVoice(); break;
                case 'w': if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); this.toggleWhiteboard(); } break;
            }
        }

        // ---- Scene Sidebar ----

        renderSceneSidebar() {
            if (!this.sceneThumbnails) return;
            const currentIdx = this.currentIndex || 0;
            const icons = { slide: '📖', quiz: '📝', exercise: '✏️', interactive: '🎮', pbl: '🔬', code: '💻' };
            this.sceneThumbnails.innerHTML = this.scenes.map((s, i) => `
                <div class="scene-thumb ${i === currentIdx ? 'active' : ''}" data-index="${i}">
                    <span class="scene-thumb-icon">${icons[s.type] || '📖'}</span>
                    <span class="scene-thumb-label">${this.SlideRenderer._stripThinkTags(s.title || '').slice(0, 8)}</span>
                    <span class="scene-thumb-badge">${s.type}</span>
                </div>
            `).join('');

            // Event delegation for scene thumbnail clicks
            this.sceneThumbnails.onclick = (e) => {
                const thumb = e.target.closest('.scene-thumb');
                if (thumb) {
                    const index = parseInt(thumb.dataset.index, 10);
                    if (!isNaN(index)) {
                        this.goToScene(index);
                    }
                }
            };
        }

        updateSidebarActive(index) {
            this.sceneThumbnails?.querySelectorAll('.scene-thumb').forEach((t, i) =>
                t.classList.toggle('active', i === index));
        }

        // ---- Scene Rendering ----

        renderScene(index) {
            if (index < 0 || index >= this.scenes.length) return;

            // Stop any currently playing audio before rendering new scene
            this.stopAudio();

            this.visitedScenes.add(this.currentIndex);
            this.totalTimeSpent += Math.floor((Date.now() - this.sceneStartTime) / 1000);
            this.sceneStartTime = Date.now();
            this.currentIndex = index;

            const scene = this.scenes[index];
            this.hideAllSceneContainers();

            // If navigating away from whiteboard scene, close it and restore controls
            if (scene.type !== 'whiteboard' && this.whiteboardVisible) {
                this.whiteboardVisible = false;
                this.whiteboardToggleBtn?.classList.remove('active');
                if (this.whiteboardContainer) {
                    this.whiteboardContainer.style.display = 'none';
                    this.whiteboardContainer.classList.remove('wb-active', 'wb-exiting');
                }
                const renderer = this._getWhiteboardRenderer();
                if (renderer) {
                    renderer.disablePenMode();
                    renderer.disableEraserMode();
                }
                this.wbPenToggleBtn?.classList.remove('active');
                this.wbEraserBtn?.classList.remove('active');
                if (this.wbPenGroup) this.wbPenGroup.style.display = 'none';
                if (this.slideControls) this.slideControls.style.display = '';
                if (this.progressBar) this.progressBar.style.display = '';
            }

            switch (scene.type) {
                case 'quiz': this.openQuizPopup(scene, true); break;
                case 'exercise': this.renderExerciseScene(scene); break;
                case 'interactive': this.renderInteractiveScene(scene); break;
                case 'pbl': this.renderPBLScene(scene); break;
                case 'whiteboard': {
                    this.whiteboardVisible = true;
                    this.whiteboardToggleBtn?.classList.add('active');
                    this._animateWhiteboardOpen();
                    this._initWhiteboard();
                    if (this.teacherArea) this.teacherArea.classList.remove('slide-mode');
                    // Show pen controls for students
                    if (this.wbPenGroup) this.wbPenGroup.style.display = 'flex';
                    // Auto-draw if scene has whiteboard content description
                    const wbDesc = scene.whiteboard_description || scene.description || scene.title;
                    if (wbDesc && scene.auto_draw !== false) {
                        this._autoDrawWhiteboardContent(wbDesc, scene);
                    }
                    break;
                }
                case 'code': {
                    if (scene.code_data) {
                        if (this.interactiveContainer) this.interactiveContainer.style.display = 'block';
                        this._renderCodeEditorScene(scene, scene.code_data);
                    } else if (scene.slides_v2 && scene.slides_v2.length > 0) {
                        this.renderSlideV2Scene(scene);
                    } else {
                        this.renderSlideScene(scene);
                    }
                    break;
                }
                case 'slide': case 'diagram': case 'video': {
                    if (scene.slides_v2 && scene.slides_v2.length > 0) {
                        this.renderSlideV2Scene(scene);
                    } else {
                        this.renderSlideScene(scene);
                    }
                    break;
                }
                default: {
                    this._renderSceneErrorPlaceholder(scene);
                }
            }

            this.updateTeacherSpeech(scene);
            this.updateSidebarActive(index);
            this.updateNav();
            if (this.isPlaying) this.playSceneAudio(scene);
            this.checkCompletion();

            // 按需预加载：停留7秒后缓存下一场景的语音
            this._scheduleNextScenePreload(index);
        }

        hideAllSceneContainers() {
            [this.slideContainer, this.quizContainer, this.exerciseContainer, this.interactiveContainer]
                .forEach(el => { if (el) el.style.display = 'none'; });
            // Hide quiz popup
            if (this.quizPopupOverlay) this.quizPopupOverlay.style.display = 'none';
            const quizSubmit = document.getElementById('quiz-submit-btn');
            const quizResult = document.getElementById('quiz-result');
            if (quizSubmit) quizSubmit.style.display = 'none';
            if (quizResult) quizResult.style.display = 'none';
        }

        _renderSceneErrorPlaceholder(scene) {
            if (!this.slideContainer) return;
            var esc = function(s) {
                if (!s) return '';
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
            };
            this.slideContainer.style.display = 'block';
            this.slideContainer.innerHTML = `
                <div class="slide-v2-container layout-title-only">
                    <div class="slide-header">
                        <h1>${esc(this.SlideRenderer._stripThinkTags(scene.title || '内容加载异常'))}</h1>
                    </div>
                    <div class="slide-body" style="display:flex;align-items:center;justify-content:center;min-height:300px;">
                        <div style="text-align:center;color:#64748b;padding:2rem;">
                            <div style="font-size:3rem;margin-bottom:1rem;">📭</div>
                            <p style="font-size:1.1rem;font-weight:600;">暂不支持该场景类型</p>
                            <p style="font-size:0.9rem;margin-top:0.5rem;">场景类型: ${esc(scene.type || '未知')}</p>
                        </div>
                    </div>
                </div>
            `;
        }

        // 生成中占位符: 当 courseId 存在但还没内容时显示, 配合后台轮询
        _showGeneratingPlaceholder() {
            if (!this.slideContainer) return;
            var esc = function(s) {
                if (!s) return '';
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
            };
            this.slideContainer.style.display = 'block';
            var reqText = (this.courseData && (this.courseData.requirement || this.courseData.title)) || '';
            this.slideContainer.innerHTML = `
                <div class="slide-v2-container layout-title-only">
                    <div class="slide-header">
                        <h1>${esc(this.courseData && this.courseData.title ? this.courseData.title : '课程生成中')}</h1>
                    </div>
                    <div class="slide-body" style="display:flex;align-items:center;justify-content:center;min-height:300px;">
                        <div style="text-align:center;color:#64748b;padding:2rem;">
                            <div style="font-size:3rem;margin-bottom:1rem;animation:spin 2s linear infinite;">⏳</div>
                            <p style="font-size:1.1rem;font-weight:600;">AI 老师正在生成课件...</p>
                            ${reqText ? `<p style="font-size:0.85rem;margin-top:0.8rem;max-width:480px;color:#94a3b8;">需求: ${esc(reqText).slice(0, 200)}</p>` : ''}
                            <p style="font-size:0.8rem;margin-top:1rem;color:#cbd5e1;">本页面会自动刷新, 课件生成完成后即可看到</p>
                        </div>
                    </div>
                </div>
            `;
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

            _stripThinkTags(str) {
                if (!str) return str;
                return str.replace(/<think>[\s\S]*?<\/think>/g, '').replace(/<\/think>/g, '');
            },

            _cycleCardThemes(cards) {
                if (!cards || !Array.isArray(cards) || cards.length === 0) return cards || [];
                // Normalize color_theme (snake_case) to colorTheme (camelCase) for all cards
                for (let i = 0; i < cards.length; i++) {
                    if (cards[i]) {
                        if (!cards[i].colorTheme && cards[i].color_theme) {
                            cards[i].colorTheme = cards[i].color_theme;
                        }
                    }
                }
                // Single card with valid theme: keep it, no cycling needed
                if (cards.length === 1) return cards;
                // Two or more cards: always cycle themes for visual variety
                for (let i = 0; i < cards.length; i++) {
                    cards[i].colorTheme = this.COLOR_THEMES[i % this.COLOR_THEMES.length];
                }
                return cards;
            },

            render(slideV2, container) {
                if (!slideV2 || !container) return;
                const layoutType = slideV2.layoutType || slideV2.layout_type || 'two-column';
                const renderer = this._getRenderer(layoutType);
                const html = renderer(slideV2);
                container.innerHTML = html;
            },

            _getRenderer(layoutType) {
                const renderers = {
                    // 11种文字布局
                    'spotlight-focus': this._renderSpotlightFocus.bind(this),
                    'kinetic-type': this._renderKineticType.bind(this),
                    'isometric-cards': this._renderIsometricCards.bind(this),
                    'orbit-ring': this._renderOrbitRing.bind(this),
                    'gradient-split': this._renderGradientSplit.bind(this),
                    'dark-header': this._renderDarkHeader.bind(this),
                    'circle-radial': this._renderCircleRadial.bind(this),
                    'stair-step': this._renderStairStep.bind(this),
                    'quote-wall': this._renderQuoteWall.bind(this),
                    'info-graphic': this._renderInfoGraphic.bind(this),
                    'floating-overlap': this._renderFloatingOverlap.bind(this),
                    // 2种图片布局
                    'magazine-cover': this._renderMagazineCover.bind(this),
                    'photo-story': this._renderPhotoStory.bind(this),
                    // 2种视频布局
                    'media-showcase': this._renderMediaShowcase.bind(this),
                    'video-lecture': this._renderVideoLecture.bind(this),
                };
                return renderers[layoutType] || this._renderSpotlightFocus.bind(this);
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

            _renderTimelineSteps(slide) {
                const items = slide.content || [];
                const stepsHtml = items.map((item, i) => {
                    const icon = this._getIcon(item.icon);
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || item.content || '' });
                    const isBullets = textHtml.startsWith('<ul');
                    return `
                        <div class="timeline-step">
                            <div class="timeline-number">${i + 1}</div>
                            <div class="timeline-connector"></div>
                            <div class="timeline-content">
                                ${icon ? `<div class="timeline-icon">${icon}</div>` : ''}
                                <div class="timeline-title">${this._escapeHtml(item.subTitle || item.title || '')}</div>
                                ${textHtml && !isBullets ? `<div class="timeline-text">${textHtml}</div>` : ''}
                                ${textHtml && isBullets ? textHtml : ''}
                            </div>
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-timeline-steps">
                            ${stepsHtml}
                        </div>
                    </div>
                `;
            },

            _renderComparison(slide) {
                const items = slide.content || [];
                const leftCard = items[0] ? this._renderContentCard(items[0], 0) : '';
                const rightCard = items[1] ? this._renderContentCard(items[1], 1) : '';
                return `
                    <div class="slide-v2-container layout-comparison">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-compare">
                            <div class="compare-left">${leftCard}</div>
                            <div class="compare-vs"><span>VS</span></div>
                            <div class="compare-right">${rightCard}</div>
                        </div>
                    </div>
                `;
            },

            _renderFullwidthBanner(slide) {
                const cards = (slide.content || []).map((item, i) => this._renderBannerCard(item, i)).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-fullwidth-banner">
                            ${cards}
                        </div>
                    </div>
                `;
            },

            _renderThreeColumnCards(slide) {
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-three-column-cards">
                            ${cards}
                        </div>
                    </div>
                `;
            },

            _renderAsymmetricSplit(slide) {
                const items = slide.content || [];
                const leftCard = items[0] ? this._renderContentCard(items[0], 0) : '';
                const rightCard = items[1] ? this._renderContentCard(items[1], 1) : '';
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-asymmetric-split">
                            <div class="asymmetric-left">${leftCard}</div>
                            <div class="asymmetric-right">${rightCard}</div>
                        </div>
                    </div>
                `;
            },

            _renderNumberedList(slide) {
                const items = slide.content || [];
                const itemsHtml = items.map((item, i) => {
                    const card = this._renderContentCard(item, i);
                    const num = i + 1;
                    return `
                        <div class="numbered-item">
                            <div class="numbered-big">${num}</div>
                            <div class="numbered-content">${card}</div>
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="slide-body layout-numbered-list">
                            ${itemsHtml}
                        </div>
                    </div>
                `;
            },

            // ========== 新增 15 种布局渲染器 ==========

            _renderHeroCenter(slide) {
                const item = slide.content?.[0];
                const icon = item ? this._getIcon(item.icon) : '';
                const textHtml = item ? this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' }) : '';
                // 兜底：确保 hero-center 至少有描述文字
                const fallbackText = !textHtml && slide.title
                    ? `<div class="hero-desc"><p>${this._escapeHtml(slide.title)} — 本页展示相关知识点与核心概念。</p></div>`
                    : '';
                return `
                    <div class="slide-v2-container layout-hero-center">
                        <div class="hero-content">
                            ${icon ? `<div class="hero-icon">${icon}</div>` : ''}
                            <h1 class="hero-title">${this._escapeHtml(slide.title || '')}</h1>
                            ${item?.subTitle ? `<div class="hero-subtitle">${this._escapeHtml(item.subTitle)}</div>` : ''}
                            ${textHtml && !textHtml.startsWith('<ul') ? `<div class="hero-desc">${textHtml}</div>` : ''}
                            ${textHtml && textHtml.startsWith('<ul') ? textHtml : ''}
                            ${fallbackText}
                        </div>
                    </div>
                `;
            },

            _renderLeftSidebar(slide) {
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
                return `
                    <div class="slide-v2-container layout-left-sidebar">
                        <div class="sidebar-title">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="sidebar-body">${cards}</div>
                    </div>
                `;
            },

            _renderFloatingOverlap(slide) {
                const cards = (slide.content || []).map((item, i) => {
                    const card = this._renderContentCard(item, i);
                    const offset = i * 20;
                    return `<div class="floating-card" style="margin-top: ${offset}px; z-index: ${i + 1};">${card}</div>`;
                }).join('');
                return `
                    <div class="slide-v2-container layout-floating-overlap">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="floating-body">${cards}</div>
                    </div>
                `;
            },

            _renderQuoteWall(slide) {
                const items = slide.content || [];
                const quotesHtml = items.map((item, i) => {
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    const subTitle = this._escapeHtml(item.subTitle || item.title || '');
                    const sizeClass = i % 3 === 0 ? 'quote-large' : i % 3 === 1 ? 'quote-medium' : 'quote-small';
                    return `
                        <div class="quote-card theme-${this._validateTheme(item.colorTheme)} ${sizeClass}">
                            <div class="quote-mark"><i class="fas fa-quote-left"></i></div>
                            ${textHtml && !textHtml.startsWith('<ul') ? `<div class="quote-text">${textHtml}</div>` : ''}
                            ${textHtml && textHtml.startsWith('<ul') ? textHtml : ''}
                            ${subTitle ? `<div class="quote-author">— ${subTitle}</div>` : ''}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-quote-wall">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="quote-wall-body">${quotesHtml}</div>
                    </div>
                `;
            },

            _renderInfoGraphic(slide) {
                const items = slide.content || [];
                const infoHtml = items.map((item, i) => {
                    const icon = this._getIcon(item.icon) || '';
                    const subTitle = this._escapeHtml(item.subTitle || item.title || '');
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    return `
                        <div class="info-item theme-${this._validateTheme(item.colorTheme)}">
                            ${icon ? `<div class="info-icon">${icon}</div>` : ''}
                            <div class="info-number">${i + 1}</div>
                            <div class="info-label">${subTitle}</div>
                            ${textHtml && !textHtml.startsWith('<ul') ? `<div class="info-desc">${textHtml}</div>` : ''}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-info-graphic">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="info-body">${infoHtml}</div>
                    </div>
                `;
            },

            _renderTabbedContent(slide) {
                const items = slide.content || [];
                const tabsHtml = items.map((item, i) => `
                    <button class="tab-btn ${i === 0 ? 'active' : ''}" data-tab="${i}">
                        ${this._getIcon(item.icon) || ''} ${this._escapeHtml(item.subTitle || item.title || `标签${i + 1}`)}
                    </button>
                `).join('');
                const panelsHtml = items.map((item, i) => {
                    const card = this._renderContentCard(item, i);
                    return `<div class="tab-panel ${i === 0 ? 'active' : ''}" data-panel="${i}">${card}</div>`;
                }).join('');
                return `
                    <div class="slide-v2-container layout-tabbed">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="tab-header">${tabsHtml}</div>
                        <div class="tab-content">${panelsHtml}</div>
                    </div>
                `;
            },

            _renderDarkHeader(slide) {
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
                return `
                    <div class="slide-v2-container layout-dark-header">
                        <div class="dark-header-bar">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="dark-content">${cards}</div>
                    </div>
                `;
            },

            _renderGradientSplit(slide) {
                const items = slide.content || [];
                const leftCard = items[0] ? this._renderContentCard(items[0], 0) : '';
                const rightCard = items[1] ? this._renderContentCard(items[1], 1) : '';
                return `
                    <div class="slide-v2-container layout-gradient-split">
                        <div class="gradient-left theme-${items[0] ? this._validateTheme(items[0].colorTheme) : 'blue'}">
                            ${leftCard}
                        </div>
                        <div class="gradient-right">${rightCard}</div>
                    </div>
                `;
            },

            _renderCircleRadial(slide) {
                const items = slide.content || [];
                const centerItem = items[0];
                const centerIcon = centerItem ? this._getIcon(centerItem.icon) : '';
                const centerTitle = this._escapeHtml(centerItem?.subTitle || slide.title || '');
                const itemsHtml = items.slice(1).map((item, i) => {
                    const card = this._renderContentCard(item, i + 1);
                    return `<div class="radial-item" data-index="${i}">${card}</div>`;
                }).join('');
                return `
                    <div class="slide-v2-container layout-circle-radial">
                        <div class="radial-center theme-${centerItem ? this._validateTheme(centerItem.colorTheme) : 'blue'}">
                            ${centerIcon ? `<div class="radial-icon">${centerIcon}</div>` : ''}
                            <div class="radial-title">${centerTitle}</div>
                        </div>
                        <div class="radial-ring">${itemsHtml}</div>
                    </div>
                `;
            },

            _renderStairStep(slide) {
                const items = slide.content || [];
                const stepsHtml = items.map((item, i) => {
                    const card = this._renderContentCard(item, i);
                    return `
                        <div class="stair-item" style="margin-left: ${i * 40}px;">
                            ${card}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-stair-step">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="stair-body">${stepsHtml}</div>
                    </div>
                `;
            },

            _renderHorizontalScroll(slide) {
                const cards = (slide.content || []).map((item, i) => this._renderContentCard(item, i)).join('');
                return `
                    <div class="slide-v2-container layout-horizontal-scroll">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="h-scroll-track">${cards}</div>
                    </div>
                `;
            },

            _renderEduDefinition(slide) {
                const items = slide.content || [];
                const defItem = items[0] || {};
                const propItems = items.slice(1, 5);
                const summaryItem = items[5] || {};
                const defText = this._renderBulletsOrText({ bullets: defItem.bullets, text: defItem.text || '' });
                const propsHtml = propItems.map((item, i) => {
                    const theme = ['blue', 'green', 'purple', 'orange'][i % 4];
                    return `<div class="edu-prop-tag theme-${theme}">${this._getIcon(item.icon)} ${this._escapeHtml(item.subTitle || item.title || '')}</div>`;
                }).join('');
                const summaryText = summaryItem.text || summaryItem.subTitle || '';
                return `
                    <div class="slide-v2-container layout-edu-definition">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="edu-definition-body">
                            <div class="edu-definition-left">
                                <div class="edu-definition-box">
                                    <div class="edu-def-quote">"</div>
                                    <div class="edu-def-text">${defText}</div>
                                </div>
                            </div>
                            <div class="edu-definition-right">
                                <div class="edu-prop-title">关键属性</div>
                                <div class="edu-prop-tags">${propsHtml}</div>
                            </div>
                        </div>
                        ${summaryText ? `<div class="edu-summary-bar">${this._escapeHtml(summaryText)}</div>` : ''}
                    </div>
                `;
            },

            _renderEduKeypoints(slide) {
                const items = slide.content || [];
                const cards = items.slice(0, 3).map((item, i) => {
                    const theme = this.COLOR_THEMES[i % this.COLOR_THEMES.length];
                    const icon = this._getIcon(item.icon);
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || item.content || '' });
                    const isBullets = textHtml.startsWith('<ul');
                    return `
                        <div class="edu-keypoint-card theme-${theme}">
                            <div class="edu-kp-topbar"></div>
                            <div class="edu-kp-body">
                                <div class="edu-kp-header">${icon} <span>${this._escapeHtml(item.subTitle || item.title || '')}</span></div>
                                ${textHtml && !isBullets ? `<div class="edu-kp-text">${textHtml}</div>` : ''}
                                ${textHtml && isBullets ? textHtml : ''}
                            </div>
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-edu-keypoints">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="edu-keypoints-body">${cards}</div>
                        <div class="edu-keypoints-footer"><i class="fas fa-lightbulb"></i> 记住这些要点</div>
                    </div>
                `;
            },

            _renderEduExample(slide) {
                const items = slide.content || [];
                const leftItem = items[0] || {};
                const rightItem = items[1] || {};
                const leftText = this._renderBulletsOrText({ bullets: leftItem.bullets, text: leftItem.text || '' });
                const isLeftBullets = leftText.startsWith('<ul');
                const rightText = rightItem.text || rightItem.codeSnippet || '';
                const rightHtml = rightItem.codeSnippet
                    ? this._renderCodeSnippet(rightItem.codeSnippet)
                    : (rightText ? `<div class="edu-example-text">${this._parseMarkdown(rightText)}</div>` : '');
                return `
                    <div class="slide-v2-container layout-edu-example">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="edu-example-body">
                            <div class="edu-example-left">
                                <div class="edu-example-label">概念说明</div>
                                ${leftItem.subTitle ? `<div class="edu-example-subtitle">${this._escapeHtml(leftItem.subTitle)}</div>` : ''}
                                ${leftText && !isLeftBullets ? `<div class="edu-example-desc">${leftText}</div>` : ''}
                                ${leftText && isLeftBullets ? leftText : ''}
                            </div>
                            <div class="edu-example-right">
                                <div class="edu-example-badge">示例</div>
                                <div class="edu-example-content">${rightHtml}</div>
                            </div>
                        </div>
                    </div>
                `;
            },

            _renderEduSummary(slide) {
                const items = slide.content || [];
                const sections = [
                    { label: '知识回顾', icon: 'book', theme: 'blue' },
                    { label: '实践要点', icon: 'lightbulb', theme: 'green' },
                    { label: '下节预告', icon: 'star', theme: 'orange' }
                ];
                const blocksHtml = sections.map((sec, i) => {
                    const item = items[i] || {};
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    const isBullets = textHtml.startsWith('<ul');
                    return `
                        <div class="edu-summary-block theme-${sec.theme}">
                            <div class="edu-summary-block-header">
                                <div class="edu-summary-icon">${this._getIcon(sec.icon)}</div>
                                <div class="edu-summary-label">${sec.label}</div>
                            </div>
                            <div class="edu-summary-block-body">
                                ${item.subTitle ? `<div class="edu-summary-block-title">${this._escapeHtml(item.subTitle)}</div>` : ''}
                                ${textHtml && !isBullets ? `<div class="edu-summary-text">${textHtml}</div>` : ''}
                                ${textHtml && isBullets ? textHtml : ''}
                            </div>
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-edu-summary">
                        <div class="edu-summary-title">${this._escapeHtml(slide.title || '')}</div>
                        <div class="edu-summary-body">${blocksHtml}</div>
                    </div>
                `;
            },

            _renderHeaderContent(slide) {
                const items = slide.content || [];
                const headerItem = items[0];
                const remaining = items.slice(1);
                const headerHtml = headerItem ? this._renderContentCard(headerItem, 0) : '';
                const contentHtml = remaining.map((item, i) => this._renderContentCard(item, i + 1)).join('');
                return `
                    <div class="slide-v2-container layout-header-content">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="header-content-area">
                            ${headerHtml}
                            <div class="header-content-stack">${contentHtml}</div>
                        </div>
                    </div>
                `;
            },

            _renderEduWelcome(slide) {
                const items = slide.content || [];
                const theme = slide.colorTheme || 'blue';
                const themeMap = {
                    blue: { bg: '#DBEAFE', accent: '#3B82F6', text: '#1E40AF', gradient: 'linear-gradient(135deg, #3B82F6, #1D4ED8)' },
                    green: { bg: '#D1FAE5', accent: '#10B981', text: '#065F46', gradient: 'linear-gradient(135deg, #10B981, #047857)' },
                    orange: { bg: '#FFEDD5', accent: '#F59E0B', text: '#92400E', gradient: 'linear-gradient(135deg, #F59E0B, #D97706)' },
                    purple: { bg: '#EDE9FE', accent: '#8B5CF6', text: '#5B21B6', gradient: 'linear-gradient(135deg, #8B5CF6, #7C3AED)' },
                };
                const t = themeMap[theme] || themeMap.blue;
                const cardsHtml = items.slice(0, 3).map((item, i) => {
                    const labels = ['是什么', '能做什么', '如何学习'];
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    return `
                        <div class="edu-welcome-card" style="--card-accent: ${t.accent}">
                            <div class="edu-welcome-card-bar" style="background: ${t.gradient}"></div>
                            <div class="edu-welcome-card-label">${labels[i] || ''}</div>
                            <div class="edu-welcome-card-title">${this._escapeHtml(item.subTitle || '')}</div>
                            ${textHtml}
                        </div>
                    `;
                }).join('');
                const slogan = slide.slogan || items[3]?.text || '开始你的学习之旅吧！';
                return `
                    <div class="slide-v2-container layout-edu-welcome" style="--welcome-theme: ${t.accent}">
                        <div class="edu-welcome-header">
                            <div class="edu-welcome-badge" style="background: ${t.gradient}">欢迎学习</div>
                            <h1 class="edu-welcome-title">${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="edu-welcome-body">${cardsHtml}</div>
                        <div class="edu-welcome-slogan" style="background: ${t.gradient}">${this._escapeHtml(slogan)}</div>
                    </div>
                `;
            },

            _renderMediaShowcase(slide) {
                const items = slide.content || [];
                const mainItem = items[0] || {};
                const videoUrl = mainItem.videoUrl || mainItem.video_url || '';
                const imageUrl = mainItem.imageUrl || mainItem.image_url || '';
                const descItems = items.slice(1);
                const descHtml = descItems.map((item, i) => {
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    return `<div class="media-desc-item">${this._getIcon(item.icon)} ${textHtml}</div>`;
                }).join('');
                // 兜底：确保 media-showcase 至少有描述文字
                const fallbackDesc = !descHtml && slide.title
                    ? `<div class="media-showcase-desc"><div class="media-desc-item">📖 <p>${this._escapeHtml(slide.title)} — 本页展示相关知识点与核心概念。</p></div></div>`
                    : '';
                return `
                    <div class="slide-v2-container layout-media-showcase">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="media-showcase-body">
                            <div class="media-showcase-stage">
                                ${videoUrl ? `<video src="${this._escapeAttr(videoUrl)}" controls autoplay loop muted playsinline class="media-showcase-video"></video>` : ''}
                                ${!videoUrl && imageUrl ? `<img src="${this._escapeAttr(imageUrl)}" alt="" class="media-showcase-image">` : ''}
                                ${!videoUrl && !imageUrl ? '<div class="media-showcase-placeholder">📷 媒体内容将在此展示</div>' : ''}
                            </div>
                            ${descHtml ? `<div class="media-showcase-desc">${descHtml}</div>` : fallbackDesc}
                        </div>
                    </div>
                `;
            },

            _renderEduProgrammingConcept(slide) {
                const items = slide.content || [];
                const conceptItem = items[0] || {};
                const specItem = items[1] || {};
                const typeItems = items.slice(2);
                const conceptText = this._renderBulletsOrText({ bullets: conceptItem.bullets, text: conceptItem.text || '' });
                const specText = this._renderBulletsOrText({ bullets: specItem.bullets, text: specItem.text || '' });
                const typesHtml = typeItems.map((item, i) => {
                    const code = item.codeSnippet || item.code_snippet || '';
                    return `
                        <div class="prog-type-card theme-${this._validateTheme(item.colorTheme)}">
                            <div class="prog-type-name">${this._escapeHtml(item.subTitle || '')}</div>
                            <div class="prog-type-desc">${this._escapeHtml(item.text || '')}</div>
                            ${code ? `<div class="prog-type-code"><code>${this._escapeHtml(code)}</code></div>` : ''}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-edu-programming-concept">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="prog-concept-body">
                            <div class="prog-concept-left">
                                <div class="prog-section-title">💡 什么是这个概念？</div>
                                ${conceptText ? `<div class="prog-concept-text">${conceptText}</div>` : ''}
                            </div>
                            <div class="prog-concept-right">
                                <div class="prog-section-title">⚠️ 使用规范</div>
                                ${specText ? `<div class="prog-concept-text">${specText}</div>` : ''}
                            </div>
                        </div>
                        ${typesHtml ? `
                            <div class="prog-types-section">
                                <div class="prog-types-title">📋 类型与分类</div>
                                <div class="prog-types-grid">${typesHtml}</div>
                            </div>
                        ` : ''}
                    </div>
                `;
            },

            _renderVideoLecture(slide) {
                const items = slide.content || [];
                const mainItem = items[0] || {};
                const videoUrl = mainItem.videoUrl || mainItem.video_url || '';
                const descItems = items.slice(1);
                const descHtml = descItems.map((item, i) => {
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    return `<div class="video-lecture-card">${this._getIcon(item.icon)} <div class="video-lecture-card-text">${textHtml}</div></div>`;
                }).join('');
                // 兜底：确保 video-lecture 至少有描述文字
                const fallbackNotes = !descHtml && slide.title
                    ? `<div class="video-lecture-card">📖 <div class="video-lecture-card-text"><p>${this._escapeHtml(slide.title)} — 本页展示相关知识点与核心概念。</p></div></div>`
                    : '';
                return `
                    <div class="slide-v2-container layout-video-lecture">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="video-lecture-body">
                            <div class="video-lecture-player">
                                ${videoUrl ? `<video src="${this._escapeAttr(videoUrl)}" controls autoplay loop muted playsinline class="video-lecture-video"></video>` : '<div class="video-lecture-placeholder">▶ 视频将在此播放</div>'}
                            </div>
                            <div class="video-lecture-notes">
                                ${descHtml || fallbackNotes || '<div class="video-lecture-empty">暂无要点</div>'}
                            </div>
                        </div>
                    </div>
                `;
            },

            // ========== 已废弃的非教育布局（保留代码但不再注册） ==========

            _renderMagazineCover(slide) {
                const item = slide.content?.[0];
                const imgUrl = item?.imageUrl || item?.image_url || '';
                const textHtml = item ? this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' }) : '';
                // 兜底：确保 magazine-cover 至少有标题和描述文字
                const fallbackText = !textHtml && slide.title ? `<p>${this._escapeHtml(slide.title)} — 本页展示相关知识点与核心概念。</p>` : '';
                return `
                    <div class="slide-v2-container layout-magazine-cover">
                        ${imgUrl ? `<div class="magazine-bg" style="background-image:url('${imgUrl}')"></div>` : '<div class="magazine-bg magazine-bg-fallback"></div>'}
                        <div class="magazine-overlay"></div>
                        <div class="magazine-content">
                            <div class="magazine-tag">FEATURED</div>
                            <h1 class="magazine-title">${this._escapeHtml(slide.title || '')}</h1>
                            ${item?.subTitle ? `<div class="magazine-subtitle">${this._escapeHtml(item.subTitle)}</div>` : ''}
                            ${textHtml ? `<div class="magazine-lead">${textHtml}</div>` : fallbackText}
                        </div>
                    </div>
                `;
            },

            _renderPhotoStory(slide) {
                const items = slide.content || [];
                const leftItem = items[0];
                const rightItems = items.slice(1);
                const leftImg = leftItem?.imageUrl || leftItem?.image_url || '';
                const leftText = leftItem ? this._renderBulletsOrText({ bullets: leftItem.bullets, text: leftItem.text || '' }) : '';
                const rightHtml = rightItems.map((item, i) => this._renderContentCard(item, i)).join('');
                // 兜底：确保 photo-story 至少有标题和描述文字
                const fallbackText = !leftText && !rightHtml && slide.title
                    ? `<div class="photo-story-lead"><p>${this._escapeHtml(slide.title)} — 本页展示相关知识点与核心概念。</p></div>`
                    : '';
                return `
                    <div class="slide-v2-container layout-photo-story">
                        <div class="photo-story-visual">
                            ${leftImg ? `<img src="${leftImg}" alt="" class="photo-story-img">` : '<div class="photo-story-img photo-story-img-fallback"></div>'}
                            <div class="photo-story-caption">${this._escapeHtml(leftItem?.subTitle || slide.title || '')}</div>
                        </div>
                        <div class="photo-story-narrative">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                            ${leftText ? `<div class="photo-story-lead">${leftText}</div>` : fallbackText}
                            <div class="photo-story-cards">${rightHtml}</div>
                        </div>
                    </div>
                `;
            },

            _renderSpotlightFocus(slide) {
                const items = slide.content || [];
                const centerItem = items[0];
                const surroundItems = items.slice(1, 7);
                const centerIcon = centerItem ? this._getIcon(centerItem.icon) : '';
                const centerText = centerItem ? this._renderBulletsOrText({ bullets: centerItem.bullets, text: centerItem.text || '' }) : '';
                const surroundHtml = surroundItems.map((item, i) => {
                    const icon = this._getIcon(item.icon);
                    const satText = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    return `
                        <div class="spotlight-satellite theme-${this._validateTheme(item.colorTheme)}">
                            ${icon ? `<div class="spotlight-sat-icon">${icon}</div>` : ''}
                            <div class="spotlight-sat-title">${this._escapeHtml(item.subTitle || item.title || '')}</div>
                            ${satText && !satText.startsWith('<ul') ? `<div class="spotlight-sat-text">${satText}</div>` : ''}
                            ${satText && satText.startsWith('<ul') ? satText : ''}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-spotlight-focus">
                        <div class="spotlight-vignette"></div>
                        <div class="spotlight-center theme-${centerItem ? this._validateTheme(centerItem.colorTheme) : 'blue'}">
                            ${centerIcon ? `<div class="spotlight-c-icon">${centerIcon}</div>` : ''}
                            <h1 class="spotlight-c-title">${this._escapeHtml(slide.title || '')}</h1>
                            ${centerItem?.subTitle ? `<div class="spotlight-c-sub">${this._escapeHtml(centerItem.subTitle)}</div>` : ''}
                            ${centerText ? `<div class="spotlight-c-text">${centerText}</div>` : ''}
                        </div>
                        <div class="spotlight-surround">${surroundHtml}</div>
                    </div>
                `;
            },

            _renderKineticType(slide) {
                const items = slide.content || [];
                const item = items[0];
                const textHtml = item ? this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' }) : '';
                const words = (slide.title || '').split('');
                const kineticTitle = words.map((ch, i) => `<span class="kinetic-char" style="animation-delay:${i * 0.04}s">${this._escapeHtml(ch)}</span>`).join('');
                // Render additional content items beyond the first
                const extraItems = items.slice(1, 4).map((it, i) => {
                    const extraText = this._renderBulletsOrText({ bullets: it.bullets, text: it.text || '' });
                    return `
                        <div class="kinetic-extra" style="animation-delay:${0.8 + i * 0.2}s">
                            <div class="kinetic-extra-title">${this._escapeHtml(it.subTitle || it.title || '')}</div>
                            ${extraText ? `<div class="kinetic-extra-text">${extraText}</div>` : ''}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-kinetic-type">
                        <div class="kinetic-accent-line"></div>
                        <div class="kinetic-main">${kineticTitle}</div>
                        ${item?.subTitle ? `<div class="kinetic-slant">${this._escapeHtml(item.subTitle)}</div>` : ''}
                        ${textHtml ? `<div class="kinetic-body">${textHtml}</div>` : ''}
                        ${extraItems ? `<div class="kinetic-extras">${extraItems}</div>` : ''}
                        <div class="kinetic-deco">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                `;
            },

            _renderIsometricCards(slide) {
                const items = slide.content || [];
                const cardsHtml = items.map((item, i) => {
                    const icon = this._getIcon(item.icon);
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    const delay = (i + 1) * 0.15;
                    return `
                        <div class="iso-card theme-${this._validateTheme(item.colorTheme)}" style="animation-delay:${delay}s">
                            <div class="iso-face iso-face-front">
                                ${icon ? `<div class="iso-icon">${icon}</div>` : ''}
                                <div class="iso-title">${this._escapeHtml(item.subTitle || item.title || '')}</div>
                                ${textHtml ? `<div class="iso-text">${textHtml}</div>` : ''}
                            </div>
                            <div class="iso-face iso-face-side"></div>
                            <div class="iso-face iso-face-top"></div>
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-isometric-cards">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="iso-stage">${cardsHtml}</div>
                    </div>
                `;
            },

            _renderOrbitRing(slide) {
                const items = slide.content || [];
                const centerItem = items[0];
                // 限制卫星最多6个，避免 overcrowding
                const satellites = items.slice(1, 7);
                const centerIcon = centerItem ? this._getIcon(centerItem.icon) : '';
                const centerText = centerItem ? this._renderBulletsOrText({ bullets: centerItem.bullets, text: centerItem.text || '' }) : '';
                // 中心标题截断，防止溢出圆形
                const centerTitle = this._escapeHtml(slide.title || '').substring(0, 32);
                const satHtml = satellites.map((item, i) => {
                    const icon = this._getIcon(item.icon);
                    // 卫星文字截断，防止卡片过大
                    const rawBullets = (item.bullets || []).map(b => String(b).substring(0, 48));
                    const rawText = String(item.text || '').substring(0, 96);
                    const satText = this._renderBulletsOrText({ bullets: rawBullets, text: rawText });
                    const angle = (360 / Math.max(satellites.length, 1)) * i;
                    // 轨道半径 140px：确保卫星(宽100px/2=50px)内边缘到中心距离 = 140-50=90px > 中心圆半径70px，不重叠
                    const radius = 140;
                    const x = Math.cos((angle - 90) * Math.PI / 180) * radius;
                    const y = Math.sin((angle - 90) * Math.PI / 180) * radius;
                    // 标准 transform chaining：先中心对齐(-50%,-50%)，再环形偏移(x,y)
                    return `
                        <div class="orbit-satellite theme-${this._validateTheme(item.colorTheme)}" style="transform:translate(-50%,-50%) translate(${x.toFixed(1)}px,${y.toFixed(1)}px)">
                            ${icon ? `<div class="orbit-sat-icon">${icon}</div>` : ''}
                            <div class="orbit-sat-label">${this._escapeHtml(String(item.subTitle || item.title || '').substring(0, 24))}</div>
                            ${satText && !satText.startsWith('<ul') ? `<div class="orbit-sat-text">${satText}</div>` : ''}
                            ${satText && satText.startsWith('<ul') ? satText : ''}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-orbit-ring">
                        <div class="orbit-system">
                            <div class="orbit-center theme-${centerItem ? this._validateTheme(centerItem.colorTheme) : 'blue'}">
                                ${centerIcon ? `<div class="orbit-c-icon">${centerIcon}</div>` : ''}
                                <div class="orbit-c-title">${centerTitle}</div>
                                ${centerText && !centerText.startsWith('<ul') ? `<div class="orbit-c-text">${centerText}</div>` : ''}
                                ${centerText && centerText.startsWith('<ul') ? centerText : ''}
                            </div>
                            <div class="orbit-ring-visual"></div>
                            <div class="orbit-satellites">${satHtml}</div>
                        </div>
                    </div>
                `;
            },

            _renderFilmStrip(slide) {
                const items = slide.content || [];
                const framesHtml = items.map((item, i) => {
                    const icon = this._getIcon(item.icon);
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' });
                    const img = item.imageUrl || item.image_url || '';
                    return `
                        <div class="film-frame">
                            <div class="film-frame-inner theme-${this._validateTheme(item.colorTheme)}">
                                ${img ? `<img src="${img}" class="film-frame-img" alt="">` : ''}
                                ${icon ? `<div class="film-frame-icon">${icon}</div>` : ''}
                                <div class="film-frame-title">${this._escapeHtml(item.subTitle || item.title || '')}</div>
                                ${textHtml ? `<div class="film-frame-text">${textHtml}</div>` : ''}
                            </div>
                            <div class="film-sprocket"></div>
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-film-strip">
                        <div class="slide-header">
                            <h1>${this._escapeHtml(slide.title || '')}</h1>
                        </div>
                        <div class="film-track">${framesHtml}</div>
                    </div>
                `;
            },

            _renderChapterDivider(slide) {
                const items = slide.content || [];
                const item = items[0];
                const textHtml = item ? this._renderBulletsOrText({ bullets: item.bullets, text: item.text || '' }) : '';
                const chapterNum = item?.subTitle || '01';
                // Render additional content items as extra description blocks
                const extraDesc = items.slice(1, 4).map((it, i) => {
                    const extraText = this._renderBulletsOrText({ bullets: it.bullets, text: it.text || '' });
                    return `
                        <div class="chapter-extra" style="animation-delay:${0.6 + i * 0.15}s">
                            <div class="chapter-extra-title">${this._escapeHtml(it.subTitle || it.title || '')}</div>
                            ${extraText ? `<div class="chapter-extra-text">${extraText}</div>` : ''}
                        </div>
                    `;
                }).join('');
                return `
                    <div class="slide-v2-container layout-chapter-divider">
                        <div class="chapter-number">${this._escapeHtml(chapterNum)}</div>
                        <div class="chapter-line"></div>
                        <h1 class="chapter-title">${this._escapeHtml(slide.title || '')}</h1>
                        ${item?.subTitle ? `<div class="chapter-sub">${this._escapeHtml(item.subTitle)}</div>` : ''}
                        ${textHtml ? `<div class="chapter-desc">${textHtml}</div>` : ''}
                        ${extraDesc ? `<div class="chapter-extras">${extraDesc}</div>` : ''}
                    </div>
                `;
            },

            _renderMediaCard(item, cardIndex) {
                try {
                    const icon = this._getIcon(item.icon);
                    const theme = this._validateTheme(item.colorTheme);
                    const subTitle = this._escapeHtml(item.subTitle || item.sub_title || item.title || '');
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || item.content || '' });
                    const isBullets = textHtml.startsWith('<ul');
                    const imageHtml = item.imageUrl || item.image_url ? this._renderImage(item.imageUrl || item.image_url) : '';
                    const idxAttr = (cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : '';

                    return `
                        <div class="media-card theme-${theme}"${idxAttr}>
                            <div class="media-icon-wrap">${icon}</div>
                            <div class="media-content">
                                ${subTitle ? `<div class="media-title">${subTitle}</div>` : ''}
                                ${textHtml && !isBullets ? `<div class="media-text">${textHtml}</div>` : ''}
                                ${textHtml && isBullets ? textHtml : ''}
                                ${imageHtml}
                            </div>
                        </div>
                    `;
                } catch (e) {
                    return `<div class="media-card theme-blue"${(cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : ''}>
                        <div class="media-icon-wrap">⚠️</div>
                        <div class="media-content">
                            <div class="media-title">数据加载异常</div>
                        </div>
                    </div>`;
                }
            },

            _renderStatCard(item, cardIndex) {
                try {
                    const icon = this._getIcon(item.icon);
                    const theme = this._validateTheme(item.colorTheme);
                    const subTitle = this._escapeHtml(item.subTitle || item.sub_title || item.title || '');
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || item.content || '' });
                    const isBullets = textHtml.startsWith('<ul');
                    const idxAttr = (cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : '';

                    return `
                        <div class="stat-card theme-${theme}"${idxAttr}>
                            ${icon ? `<div class="stat-icon">${icon}</div>` : ''}
                            <div class="stat-value">${subTitle}</div>
                            ${textHtml && !isBullets ? `<div class="stat-label">${textHtml}</div>` : ''}
                            ${textHtml && isBullets ? textHtml : ''}
                        </div>
                    `;
                } catch (e) {
                    return `<div class="stat-card theme-blue"${(cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : ''}>
                        <div class="stat-value">--</div>
                        <div class="stat-label">数据异常</div>
                    </div>`;
                }
            },

            _renderBannerCard(item, cardIndex) {
                try {
                    const icon = this._getIcon(item.icon);
                    const theme = this._validateTheme(item.colorTheme);
                    const subTitle = this._escapeHtml(item.subTitle || item.sub_title || item.title || '');
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || item.content || '' });
                    const isBullets = textHtml.startsWith('<ul');
                    const idxAttr = (cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : '';

                    return `
                        <div class="banner-card theme-${theme}"${idxAttr}>
                            <div class="banner-inner">
                                ${icon ? `<div class="banner-icon">${icon}</div>` : ''}
                                <div class="banner-content">
                                    ${subTitle ? `<div class="banner-title">${subTitle}</div>` : ''}
                                    ${textHtml && !isBullets ? `<div class="banner-text">${textHtml}</div>` : ''}
                                    ${textHtml && isBullets ? textHtml : ''}
                                </div>
                            </div>
                        </div>
                    `;
                } catch (e) {
                    return `<div class="banner-card theme-blue"${(cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : ''}>
                        <div class="banner-inner">
                            <div class="banner-title">数据加载异常</div>
                        </div>
                    </div>`;
                }
            },

            _renderContentCard(item, cardIndex) {
                try {
                    const icon = this._getIcon(item.icon);
                    const theme = this._validateTheme(item.colorTheme);
                    const subTitle = this._escapeHtml(item.subTitle || item.sub_title || item.title || '');
                    const textHtml = this._renderBulletsOrText({ bullets: item.bullets, text: item.text || item.content || '' });
                    const isBullets = textHtml.startsWith('<ul');
                    const codeHtml = item.codeSnippet ? this._renderCodeSnippet(item.codeSnippet) : '';
                    const videoUrl = item.videoUrl || item.video_url || '';
                    const imageUrl = item.imageUrl || item.image_url || '';
                    const videoHtml = videoUrl ? `<video src="${this._escapeAttr(videoUrl)}" controls autoplay loop muted playsinline style="width:100%;border-radius:8px;max-height:280px;object-fit:cover;"></video>` : '';
                    const imageHtml = !videoUrl && imageUrl ? this._renderImage(imageUrl) : '';
                    const idxAttr = (cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : '';
                    // 兜底：确保每个卡片至少有一些文字
                    const hasContent = subTitle || textHtml || codeHtml || videoHtml || imageHtml;
                    const fallbackText = !hasContent ? '<div class="card-text">📖 相关知识点内容</div>' : '';

                    return `
                        <div class="content-card theme-${theme}"${idxAttr}>
                            ${subTitle ? `<div class="card-title">${icon} ${subTitle}</div>` : ''}
                            ${textHtml && !isBullets ? `<div class="card-text">${textHtml}</div>` : ''}
                            ${textHtml && isBullets ? textHtml : ''}
                            ${codeHtml}
                            ${videoHtml}
                            ${imageHtml}
                            ${fallbackText}
                        </div>
                    `;
                } catch (e) {
                    return `<div class="content-card theme-blue"${(cardIndex !== undefined) ? ` data-card-index="${cardIndex}"` : ''}>
                        <div class="card-title">⚠️ 数据加载异常</div>
                        <div class="card-text">卡片内容无法渲染，请刷新重试</div>
                    </div>`;
                }
            },

            _renderBulletsOrText(item) {
                if (item.bullets && Array.isArray(item.bullets) && item.bullets.length > 0) {
                    try {
                        const items = item.bullets
                            .map(b => `<li>${this._escapeHtml(String(b))}</li>`)
                            .join('');
                        return `<ul class="card-bullets">${items}</ul>`;
                    } catch (e) {
                        return `<ul class="card-bullets"><li>数据加载异常</li></ul>`;
                    }
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
                if (theme && this.COLOR_THEMES.includes(theme)) return theme;
                return 'blue';
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

            try {
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
                } else if (firstSlide.content && Array.isArray(firstSlide.content) && firstSlide.content.length > 0) {
                    // SlideV2 format: use content + layout_type directly
                    // Normalize field names: backend uses snake_case, frontend renderers expect camelCase
                    const normalizedContent = firstSlide.content.map(item => ({
                        subTitle: item.sub_title || item.subTitle || '',
                        bullets: item.bullets || [],
                        narration: item.narration || '',
                        text: item.text || '',
                        icon: item.icon || 'book',
                        colorTheme: item.color_theme || item.colorTheme || 'blue',
                        codeSnippet: item.code_snippet || item.codeSnippet || '',
                        imageUrl: item.image_url || item.imageUrl || '',
                        imagePrompt: item.image_prompt || item.imagePrompt || '',
                        videoUrl: item.video_url || item.videoUrl || '',
                        videoPrompt: item.video_prompt || item.videoPrompt || '',
                    }));
                    cardData = {
                        title: this.SlideRenderer._stripThinkTags(firstSlide.title || scene.title || ''),
                        content: this.SlideRenderer._cycleCardThemes(normalizedContent),
                        layoutType: firstSlide.layout_type || firstSlide.layoutType || 'two-column'
                    };
                } else {
                    // content is null/empty or elements format unknown - fallback to legacy slide rendering
                    this.renderSlideScene(scene);
                    return;
                }

                this.SlideRenderer.render(cardData, this.slideContainer);
                console.log('[Classroom] SlideRenderer.render called, cardData:', {
                    layoutType: cardData.layoutType,
                    contentCount: cardData.content?.length,
                    cardThemes: cardData.content?.map(c => c.colorTheme)
                });

                // Store actions for playback pipeline (spotlight/laser/wb_draw use element IDs)
                this._currentOpenMAICActions = firstSlide.actions
                    || scene.actions
                    || (scene.slides_v2?.[0]?.teacher_actions?.length ? scene.slides_v2[0].teacher_actions : null);
                // Store element-to-card mapping for spotlight/laser targeting
                this._currentElemToCard = cardData._elemToCard || null;
            } catch (e) {
                console.error('[Classroom] renderSlideV2Scene error:', e);
            }

            // Always check: did we actually render content? If container is empty, show error placeholder
            if (!this.slideContainer.innerHTML.trim()) {
                this._renderSceneErrorPlaceholder(scene);
            }
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
            // Strip <think> reasoning tags from title
            slideTitle = this.SlideRenderer._stripThinkTags(slideTitle);

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

            var layoutType = slide.layout_type || slide.layoutType ||
                             (cards.length <= 1 ? 'title-only' :
                              cards.length <= 2 ? 'two-column' : 'grid-cards');

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

            this.SlideRenderer._cycleCardThemes(cards);

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
                            <h1 class="interactive-title">${this._escapeHtml(this.SlideRenderer._stripThinkTags(scene.title || ''))}</h1>
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

            window.addEventListener('beforeunload', () => {
                window.speechSynthesis?.cancel();
                if (this.pollingInterval) clearInterval(this.pollingInterval);
            });
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
                        <h1 class="slide-title animate-in">${this.SlideRenderer._stripThinkTags(scene.title || '')}</h1>
                        <p class="slide-description animate-in" style="animation-delay:0.2s">${scene.description}</p>
                    </div>
                `;
                return;
            }

            // Apply slide background with gradient/solid from theme
            this._applySlideBackground(slide);

            let html = `<div class="slide-header-bar"></div>`;
            html += `<div class="slide-content slide-enter">`;
            html += `<h1 class="slide-title animate-in">${this.SlideRenderer._stripThinkTags(slide.title || scene.title || '')}</h1>`;
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

            var rect = targetElem ? targetElem.getBoundingClientRect() : {left: 200, top: 150, width: 600, height: 300};
            var pad = 10;

            if (targetElem) {
                targetElem.classList.add('spotlight-target');
            }

            // OpenMAIC 风格的 SVG mask 实现
            var svgNS = 'http://www.w3.org/2000/svg';
            var svg = document.createElementNS(svgNS, 'svg');
            svg.setAttribute('class', 'openmaic-spotlight-svg');
            svg.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';

            var maskId = 'spotlight-mask-' + Date.now();
            var defs = document.createElementNS(svgNS, 'defs');
            var mask = document.createElementNS(svgNS, 'mask');
            mask.setAttribute('id', maskId);

            var whiteRect = document.createElementNS(svgNS, 'rect');
            whiteRect.setAttribute('width', '100%');
            whiteRect.setAttribute('height', '100%');
            whiteRect.setAttribute('fill', 'white');
            mask.appendChild(whiteRect);

            var hole = document.createElementNS(svgNS, 'rect');
            hole.setAttribute('x', Math.max(0, rect.left - pad));
            hole.setAttribute('y', Math.max(0, rect.top - pad));
            hole.setAttribute('width', rect.width + pad * 2);
            hole.setAttribute('height', rect.height + pad * 2);
            hole.setAttribute('fill', 'black');
            hole.setAttribute('rx', '14');
            mask.appendChild(hole);

            defs.appendChild(mask);
            svg.appendChild(defs);

            var dimRect = document.createElementNS(svgNS, 'rect');
            dimRect.setAttribute('width', '100%');
            dimRect.setAttribute('height', '100%');
            dimRect.setAttribute('fill', 'rgba(15, 23, 42, 0.6)');
            dimRect.setAttribute('mask', 'url(#' + maskId + ')');
            svg.appendChild(dimRect);

            var glow = document.createElementNS(svgNS, 'rect');
            glow.setAttribute('x', Math.max(0, rect.left - pad));
            glow.setAttribute('y', Math.max(0, rect.top - pad));
            glow.setAttribute('width', rect.width + pad * 2);
            glow.setAttribute('height', rect.height + pad * 2);
            glow.setAttribute('fill', 'none');
            glow.setAttribute('stroke', 'rgba(99, 102, 241, 0.7)');
            glow.setAttribute('stroke-width', '2.5');
            glow.setAttribute('rx', '14');
            glow.setAttribute('class', 'openmaic-spotlight-glow');
            svg.appendChild(glow);

            this.actionOverlay.appendChild(svg);
            this.spotlightElement = svg;

            // 记录当前 spotlight 目标，用于语音同步
            this._currentSpotlightTarget = elementId;
        }

        clearSpotlight() {
            var overlay = document.getElementById('spotlight-overlay');
            if (overlay) overlay.remove();

            var svg = this.actionOverlay ? this.actionOverlay.querySelector('.openmaic-spotlight-svg') : null;
            if (svg) svg.remove();

            if (this.slideContainer) {
                this.slideContainer.classList.remove('spotlight-active');
            }
            if (this.spotlightElement) {
                if (this.spotlightElement.classList) {
                    this.spotlightElement.classList.remove('spotlight-target');
                }
                this.spotlightElement.style.filter = '';
                this.spotlightElement.style.transform = '';
                this.spotlightElement = null;
            }

            this._currentSpotlightTarget = null;

            document.querySelectorAll('.spotlight-target').forEach(el => {
                el.classList.remove('spotlight-target');
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

            var cx = window.innerWidth / 2;
            var cy = window.innerHeight / 2;

            if (targetElem) {
                var rect = targetElem.getBoundingClientRect();
                cx = rect.left + rect.width / 2;
                cy = rect.top + rect.height / 2;

                if (targetElem.classList.contains('content-card')) {
                    targetElem.classList.add('laser-target');
                }
                targetElem.style.transition = 'filter 0.3s ease';
                targetElem.style.filter = `brightness(1.2) drop-shadow(0 0 15px ${color})`;

                this.laserTargetElem = targetElem;
            }

            if (this.actionOverlay) {
                var vw = window.innerWidth;
                var vh = window.innerHeight;

                // 从最近的角落飞入
                var startX = cx < vw / 2 ? -20 : vw + 20;
                var startY = cy < vh / 2 ? -20 : vh + 20;

                var container = document.createElement('div');
                container.className = 'openmaic-laser-container';

                var ring = document.createElement('div');
                ring.className = 'openmaic-laser-ring';
                ring.style.left = (cx - 20) + 'px';
                ring.style.top = (cy - 20) + 'px';
                ring.style.borderColor = color;
                container.appendChild(ring);

                var dot = document.createElement('div');
                dot.className = 'openmaic-laser-dot';
                dot.style.setProperty('--laser-start-x', startX + 'px');
                dot.style.setProperty('--laser-start-y', startY + 'px');
                dot.style.setProperty('--laser-end-x', cx + 'px');
                dot.style.setProperty('--laser-end-y', cy + 'px');
                container.appendChild(dot);

                this.actionOverlay.appendChild(container);
            }

            // 记录当前 laser 目标
            this._currentLaserTarget = elementId;
        }

        clearLaser() {
            var laser = document.getElementById('laser-overlay');
            if (laser) laser.remove();

            var openmaicLaser = this.actionOverlay ? this.actionOverlay.querySelector('.openmaic-laser-container') : null;
            if (openmaicLaser) openmaicLaser.remove();

            if (this.laserTargetElem) {
                this.laserTargetElem.classList.remove('laser-target');
                this.laserTargetElem.style.filter = '';
                this.laserTargetElem = null;
            }

            this._currentLaserTarget = null;

            document.querySelectorAll('.laser-target').forEach(el => {
                el.classList.remove('laser-target');
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

            // Stop any currently playing audio before starting new one
            this.stopAudio();

            // ---- Spotlight 跟随语音：自动切换到当前讲解的卡片 ----
            var currentElementId = this._findElementForSpeech(text);
            if (currentElementId && currentElementId !== this._currentSpotlightTarget) {
                this.clearSpotlight();
                this.renderSpotlight(currentElementId);
            }

            this.speechText.textContent = text;
            this.updateTeacherSpeechText(text);
            this.showSpeechSyncIndicator(true);
            this.updateTeacherStatus('讲解中', true);

            // Update teacher avatar to speaking state
            if (this.teacherAvatar) {
                this.teacherAvatar.classList.add('speaking');
            }

            // Try MiniMax TTS first
            const ttsResult = await this.generateTTS(text, voiceId, speed);

            if (ttsResult.success && ttsResult.audioUrl && this.audioPlayer) {
                // Play generated audio with sync
                this.audioPlayer.load();
                this.audioPlayer.src = ttsResult.audioUrl;

                this.audioPlayer.onloadedmetadata = () => {
                    // Update speech progress
                    this.updateSpeechProgress();
                };

                this.audioPlayer.onended = () => {
                    this.showSpeechSyncIndicator(false);
                    this.updateTeacherStatus('待机中', false);
                    if (this.teacherAvatar) {
                        this.teacherAvatar.classList.remove('speaking');
                    }
                    this.clearSpotlight();
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
                    this.updateTeacherStatus('讲解中', true);
                };

                utterance.onend = () => {
                    if (this.teacherAvatar) {
                        this.teacherAvatar.classList.remove('speaking');
                    }
                    this.showSpeechSyncIndicator(false);
                    this.updateTeacherStatus('待机中', false);
                    this.clearSpotlight();
                    resolve();
                };

                utterance.onerror = () => {
                    if (this.teacherAvatar) {
                        this.teacherAvatar.classList.remove('speaking');
                    }
                    this.showSpeechSyncIndicator(false);
                    this.updateTeacherStatus('待机中', false);
                    resolve();
                };

                window.speechSynthesis.speak(utterance);
            });
        }

        _findElementForSpeech(text) {
            if (!this.courseData || !this.courseData.scenes) return null;

            var currentScene = this.scenes[this.currentIndex];
            if (!currentScene) return null;

            // 尝试从 scene_actions 中匹配
            var sceneActions = this.courseData.scene_actions || [];
            var actionData = sceneActions.find(a =>
                a.scene_id === currentScene.id ||
                a.scene_index === this.currentIndex
            );

            if (actionData?.actions) {
                for (var i = 0; i < actionData.actions.length; i++) {
                    var act = actionData.actions[i];
                    if (act.type === 'speech' && act.text === text) {
                        // 查找同一个 action 块中紧随其后的 spotlight action
                        if (i + 1 < actionData.actions.length) {
                            var nextAct = actionData.actions[i + 1];
                            if (nextAct.type === 'spotlight') {
                                return nextAct.element_id;
                            }
                        }
                        // 或者查找同组中唯一的 spotlight
                        for (var j = 0; j < actionData.actions.length; j++) {
                            if (actionData.actions[j].type === 'spotlight') {
                                return actionData.actions[j].element_id;
                            }
                        }
                    }
                }
            }

            // Fallback: 从当前 scene 的 slides_v2 content 中匹配 text
            var slideV2 = currentScene.slide || currentScene;
            var slidesV2 = currentScene.slides_v2 || [];
            var bestMatch = null;
            var bestScore = 0;

            // Helper: compute similarity score between two strings
            function scoreMatch(a, b) {
                if (!a || !b) return 0;
                a = a.toLowerCase().trim();
                b = b.toLowerCase().trim();
                if (a === b) return 100;
                if (a.indexOf(b) >= 0 || b.indexOf(a) >= 0) return 80;
                var aWords = a.split(/\s+/);
                var bWords = b.split(/\s+/);
                var common = aWords.filter(function(w) { return bWords.indexOf(w) >= 0; });
                return Math.round((common.length / Math.max(aWords.length, bWords.length)) * 60);
            }

            // Check slides_v2 content items
            var allContent = [];
            if (slideV2.content) {
                allContent = slideV2.content;
            } else if (slidesV2.length > 0 && slidesV2[0].content) {
                allContent = slidesV2[0].content;
            }

            for (var k = 0; k < allContent.length; k++) {
                var item = allContent[k];
                var candidates = [];
                if (item.narration) candidates.push(item.narration);
                if (item.text) candidates.push(item.text);
                if (item.title) candidates.push(item.title);
                if (item.subTitle) candidates.push(item.subTitle);
                if (item.bullets) candidates = candidates.concat(item.bullets);

                for (var c = 0; c < candidates.length; c++) {
                    var score = scoreMatch(text, candidates[c]);
                    if (score > bestScore) {
                        bestScore = score;
                        bestMatch = 'card-' + (k + 1);
                    }
                }
            }

            // Also check title match
            var title = currentScene.title || '';
            if (scoreMatch(text, title) > bestScore) {
                bestScore = scoreMatch(text, title);
                bestMatch = 'card-1';
            }

            return bestScore >= 30 ? bestMatch : null;
        }

        async generateTTS(text, voiceId = null, speed = 1.0) {
            const voice = voiceId || TTS_CONFIG.voice;
            const voiceConfig = MINIMAX_VOICES[voice] || MINIMAX_VOICES['female-yujie'];
            const voiceIndex = voiceConfig.index || 0;

            try {
                // Use /api/socratic/tts endpoint (same as socratic-ai.html)
                const response = await fetch('/api/socratic/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        voice_id: voiceIndex
                    })
                });

                const data = await response.json();
                console.log('[Classroom] TTS response:', data);
                if (data.success && data.audio_url && typeof data.audio_url === 'string' && data.audio_url.trim().length > 0) {
                    console.log('[Classroom] TTS audioUrl:', data.audio_url);
                    return { success: true, audioUrl: data.audio_url.trim() };
                }
                if (data.error) {
                    console.error('[Classroom] TTS API error:', data.error);
                }
                return { success: false, error: data.error || 'TTS generation failed' };
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

        updateTeacherStatus(text, isActive) {
            if (!this.teacherStatus) return;
            const statusText = this.teacherStatus.querySelector('.status-text');
            if (statusText) statusText.textContent = text;
            if (isActive) {
                this.teacherStatus.classList.add('active');
                this.teacherArea.classList.add('speaking');
                // Expand to compact mode when speaking
                if (this.teacherArea.dataset.state === 'minimized') {
                    this.setTeacherAreaState('compact');
                }
                // Show voice waveform
                if (this.voiceWaveform) this.voiceWaveform.style.display = 'flex';
            } else {
                this.teacherStatus.classList.remove('active');
                this.teacherArea.classList.remove('speaking');
                // Hide voice waveform
                if (this.voiceWaveform) this.voiceWaveform.style.display = 'none';
            }
        }

        // ---- TTS 预加载 ----

        getSceneSpeechText(scene) {
            if (!scene) return null;
            const text = scene.slide?.speech
                || scene.slides_v2?.[0]?.content?.[0]?.narration
                || scene.quiz?.speech
                || scene.exercise?.speech
                || null;
            return text && text.trim().length > 0 ? text.trim() : null;
        }

        _scheduleNextScenePreload(currentIdx) {
            // 取消之前的定时器
            if (this._ttsPreloadTimer) {
                clearTimeout(this._ttsPreloadTimer);
                this._ttsPreloadTimer = null;
            }

            const nextIdx = currentIdx + 1;
            if (nextIdx >= this.scenes.length) return;

            const nextScene = this.scenes[nextIdx];
            const text = this.getSceneSpeechText(nextScene);
            if (!text) return;

            // 如果已经缓存，不需要再预加载
            if (nextScene.audioUrl || this.courseData.tts_audio_urls?.[String(nextScene.id)]) return;

            // 15秒后如果用户还在当前场景，预加载下一场景
            this._ttsPreloadTimer = setTimeout(() => {
                if (this.currentIndex !== currentIdx) return; // 用户已切换场景，取消
                this._preloadSceneTTS(nextScene);
            }, 7000);
        }

        async _preloadSceneTTS(scene) {
            const text = this.getSceneSpeechText(scene);
            if (!text) return;
            const sceneId = String(scene.id);

            // 如果已经在缓存中，跳过
            if (scene.audioUrl || this.courseData.tts_audio_urls?.[sceneId]) return;

            // 如果该场景正在预加载中，复用 Promise
            if (this._ttsPreloadPromises.has(sceneId)) {
                return this._ttsPreloadPromises.get(sceneId);
            }

            const voiceId = this.ttsConfig?.voice || TTS_CONFIG.voice;
            const speed = this.ttsConfig?.speed || TTS_CONFIG.speed;

            const preloadPromise = (async () => {
                try {
                    const result = await this.generateTTS(text, voiceId, speed);
                    if (result.success && result.audioUrl) {
                        scene.audioUrl = result.audioUrl;
                        if (!this.courseData.tts_audio_urls) this.courseData.tts_audio_urls = {};
                        this.courseData.tts_audio_urls[sceneId] = result.audioUrl;
                        // 持久化到 sessionStorage，刷新后缓存仍有效
                        try {
                            sessionStorage.setItem('classroomData', JSON.stringify(this.courseData));
                        } catch (e) {}
                        console.log('[Classroom] TTS preloaded for scene', scene.id, ':', result.audioUrl);
                    }
                } catch (e) {
                    console.warn('[Classroom] TTS preload failed for scene', scene.id, e);
                }
            })();

            this._ttsPreloadPromises.set(sceneId, preloadPromise);
            return preloadPromise;
        }

        async _ensureSceneTTSCached(scene) {
            const sceneId = String(scene.id);
            // 1. 检查内存缓存
            if (scene.audioUrl) return scene.audioUrl;
            if (this.courseData.tts_audio_urls?.[sceneId]) {
                scene.audioUrl = this.courseData.tts_audio_urls[sceneId];
                return scene.audioUrl;
            }

            const text = this.getSceneSpeechText(scene);
            if (!text) return null;

            // 2. 如果该场景正在后台预加载中，等待它完成
            if (this._ttsPreloadPromises.has(sceneId)) {
                await this._ttsPreloadPromises.get(sceneId);
                return scene.audioUrl || this.courseData.tts_audio_urls?.[sceneId] || null;
            }

            // 3. 否则立即生成（插队）
            this.updateTeacherStatus('正在合成语音...', false);
            const voiceId = this.ttsConfig?.voice || TTS_CONFIG.voice;
            const speed = this.ttsConfig?.speed || TTS_CONFIG.speed;
            const result = await this.generateTTS(text, voiceId, speed);
            if (result.success && result.audioUrl) {
                scene.audioUrl = result.audioUrl;
                if (!this.courseData.tts_audio_urls) this.courseData.tts_audio_urls = {};
                this.courseData.tts_audio_urls[sceneId] = result.audioUrl;
                try {
                    sessionStorage.setItem('classroomData', JSON.stringify(this.courseData));
                } catch (e) {}
                return result.audioUrl;
            }
            return null;
        }

        updateTeacherSpeechText(text) {
            // Update both full-text and mini-text elements
            const fullTextEl = this.speechText;
            const miniTextEl = this.teacherArea?.querySelector('.mini-text');
            if (fullTextEl) {
                fullTextEl.textContent = text;
                // Scroll to top when text updates
                const bubble = fullTextEl.closest('.speech-bubble');
                if (bubble) bubble.scrollTop = 0;
            }
            if (miniTextEl) miniTextEl.textContent = text;
        }

        setTeacherAreaState(state) {
            if (!this.teacherArea) return;
            this.teacherArea.dataset.state = state;
            // Remove all state classes
            this.teacherArea.classList.remove('minimized', 'compact', 'full');
            this.teacherArea.classList.add(state);
        }

        // Hover/click interaction for teacher area
        initTeacherAreaInteraction() {
            if (!this.teacherArea) return;
            const self = this;
            let hoverTimeout = null;
            let isTransitioning = false;

            // Mouse enter/leave for hover expand
            this.teacherArea.addEventListener('mouseenter', function() {
                if (isTransitioning) return;
                clearTimeout(hoverTimeout);
                if (self.teacherArea.dataset.state === 'minimized') {
                    hoverTimeout = setTimeout(() => {
                        isTransitioning = true;
                        self.setTeacherAreaState('compact');
                        setTimeout(() => { isTransitioning = false; }, 400);
                    }, 150);
                }
            });

            this.teacherArea.addEventListener('mouseleave', function() {
                clearTimeout(hoverTimeout);
                if (isTransitioning) return;
                if (!self.teacherArea.classList.contains('speaking') &&
                    self.teacherArea.dataset.state === 'compact') {
                    hoverTimeout = setTimeout(() => {
                        isTransitioning = true;
                        self.setTeacherAreaState('minimized');
                        setTimeout(() => { isTransitioning = false; }, 400);
                    }, 200);
                }
            });

            // Click avatar to toggle full mode
            const avatar = this.teacherArea.querySelector('.teacher-avatar');
            if (avatar) {
                avatar.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const current = self.teacherArea.dataset.state;
                    if (current === 'minimized') {
                        self.setTeacherAreaState('compact');
                    } else if (current === 'compact') {
                        self.setTeacherAreaState('full');
                    } else {
                        self.setTeacherAreaState('compact');
                    }
                });
            }

            // Click outside to collapse from full mode
            document.addEventListener('click', function(e) {
                if (!self.teacherArea.contains(e.target) &&
                    self.teacherArea.dataset.state === 'full' &&
                    !self.teacherArea.classList.contains('speaking')) {
                    self.setTeacherAreaState('minimized');
                }
            });

            // Keyboard: Escape to collapse from full
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' &&
                    self.teacherArea.dataset.state === 'full' &&
                    !self.teacherArea.classList.contains('speaking')) {
                    self.setTeacherAreaState('compact');
                }
            });
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
                    <span>${this.SlideRenderer._stripThinkTags(quiz?.title || scene.title || '')}</span>
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

            const exercises = data?.exercises || [];
            const hasCodeExercise = exercises.some(ex => ex.type === 'code' || ex.language);
            const hasInteractiveExercise = exercises.some(ex => ['choice','fill_blank','true_false'].includes(ex.type));

            if (content) {
                if (exercises.length === 0) {
                    content.innerHTML = `<h3>${this.SlideRenderer._stripThinkTags(scene.title || '')}</h3><p>${scene.description || ''}</p>`;
                } else {
                    content.innerHTML = exercises.map((ex, i) => {
                        if (ex.type === 'code' || ex.language) {
                            return this._renderExerciseCodeEditor(ex, i);
                        }
                        if (ex.type === 'choice') {
                            return this._renderExerciseChoice(ex, i);
                        }
                        if (ex.type === 'fill_blank') {
                            return this._renderExerciseFillBlank(ex, i);
                        }
                        if (ex.type === 'true_false') {
                            return this._renderExerciseTrueFalse(ex, i);
                        }
                        return `<div class="exercise-item"><h4>练习 ${i+1}</h4><p>${ex.instruction || ''}</p></div>`;
                    }).join('');

                    // Bind code editor events for code exercises
                    exercises.forEach((ex, i) => {
                        if (ex.type === 'code' || ex.language) {
                            this._bindExerciseCodeEditorEvents(ex, i);
                        }
                    });
                    // Bind interactive exercise events
                    exercises.forEach((ex, i) => {
                        if (['choice','fill_blank','true_false'].includes(ex.type)) {
                            this._bindInteractiveExerciseEvents(ex, i, scene);
                        }
                    });
                }
            }

            if (hints) {
                if (data?.exercises?.[0]?.hints && !hasCodeExercise && !hasInteractiveExercise) {
                    hints.innerHTML = '<strong>提示：</strong>' + data.exercises[0].hints.map(h => `<span class="hint-badge">${h}</span>`).join('');
                    hints.style.display = 'block';
                } else {
                    hints.style.display = 'none';
                    hints.innerHTML = '';
                }
            }

            if (answer) {
                if (hasCodeExercise || hasInteractiveExercise) {
                    answer.style.display = 'none';
                } else {
                    answer.style.display = 'block';
                    answer.value = '';
                }
            }

            if (submitBtn) {
                if (hasCodeExercise || hasInteractiveExercise) {
                    submitBtn.style.display = 'none';
                } else {
                    submitBtn.style.display = 'block';
                    submitBtn.innerHTML = '<span>提交答案</span><i class="fas fa-arrow-right"></i>';
                    submitBtn.onclick = () => {
                        const ans = answer?.value.trim();
                        if (ans) {
                            this.addChatMessage('user', `练习答案：${ans}`);
                            this.sendExerciseAnswer(scene, ans);
                        }
                    };
                }
            }
        }

        _renderExerciseChoice(ex, index) {
            const opts = (ex.options || []).map((opt, j) => {
                const label = String(opt).match(/^[A-D]\.\s*/)? opt : `${String.fromCharCode(65+j)}. ${opt}`;
                return `<label class="ex-choice-option" data-index="${j}"><input type="radio" name="ex-choice-${index}" value="${j}"><span class="ex-choice-label">${this._escapeHtml(label)}</span></label>`;
            }).join('');
            return `
                <div class="exercise-interactive" data-ex-index="${index}" data-ex-type="choice">
                    <div class="ex-interactive-header"><span class="ex-interactive-badge">选择题</span><h4>练习 ${index+1}</h4></div>
                    <div class="ex-interactive-instruction">${this._escapeHtml(ex.instruction || '')}</div>
                    <div class="ex-choice-options">${opts}</div>
                    <div class="ex-interactive-feedback" id="ex-feedback-${index}" style="display:none;"></div>
                    <button class="ex-interactive-submit" id="ex-submit-${index}"><i class="fas fa-check"></i> 提交答案</button>
                </div>
            `;
        }

        _renderExerciseFillBlank(ex, index) {
            const parts = (ex.instruction || '').split('___');
            const html = parts.map((p, j) => {
                if (j === parts.length - 1) return this._escapeHtml(p);
                return `${this._escapeHtml(p)}<input type="text" class="ex-fill-input" id="ex-fill-${index}-${j}" placeholder="填空${j+1}">`;
            }).join('');
            return `
                <div class="exercise-interactive" data-ex-index="${index}" data-ex-type="fill_blank">
                    <div class="ex-interactive-header"><span class="ex-interactive-badge">填空题</span><h4>练习 ${index+1}</h4></div>
                    <div class="ex-interactive-instruction ex-fill-instruction">${html}</div>
                    <div class="ex-interactive-feedback" id="ex-feedback-${index}" style="display:none;"></div>
                    <button class="ex-interactive-submit" id="ex-submit-${index}"><i class="fas fa-check"></i> 提交答案</button>
                </div>
            `;
        }

        _renderExerciseTrueFalse(ex, index) {
            return `
                <div class="exercise-interactive" data-ex-index="${index}" data-ex-type="true_false">
                    <div class="ex-interactive-header"><span class="ex-interactive-badge">判断题</span><h4>练习 ${index+1}</h4></div>
                    <div class="ex-interactive-instruction">${this._escapeHtml(ex.instruction || '')}</div>
                    <div class="ex-tf-options">
                        <label class="ex-tf-option" data-value="true"><input type="radio" name="ex-tf-${index}" value="true"><span class="ex-tf-label"><i class="fas fa-check-circle"></i> 正确</span></label>
                        <label class="ex-tf-option" data-value="false"><input type="radio" name="ex-tf-${index}" value="false"><span class="ex-tf-label"><i class="fas fa-times-circle"></i> 错误</span></label>
                    </div>
                    <div class="ex-interactive-feedback" id="ex-feedback-${index}" style="display:none;"></div>
                    <button class="ex-interactive-submit" id="ex-submit-${index}"><i class="fas fa-check"></i> 提交答案</button>
                </div>
            `;
        }

        _bindInteractiveExerciseEvents(ex, index, scene) {
            const submitBtn = document.getElementById(`ex-submit-${index}`);
            const feedbackEl = document.getElementById(`ex-feedback-${index}`);
            if (!submitBtn) return;

            submitBtn.addEventListener('click', () => {
                let isCorrect = false;
                let studentAnswer = '';

                if (ex.type === 'choice') {
                    const selected = document.querySelector(`input[name="ex-choice-${index}"]:checked`);
                    if (!selected) { feedbackEl.innerHTML = '<span class="ex-feedback-warn">请先选择一个选项</span>'; feedbackEl.style.display = 'block'; return; }
                    studentAnswer = parseInt(selected.value);
                    isCorrect = studentAnswer === (ex.correct_answer ?? 0);
                } else if (ex.type === 'fill_blank') {
                    const inputs = document.querySelectorAll(`[id^="ex-fill-${index}-"]`);
                    const answers = Array.from(inputs).map(inp => inp.value.trim());
                    studentAnswer = answers.join(', ');
                    const correct = String(ex.correct_answer || '');
                    isCorrect = answers.some(a => a.toLowerCase() === correct.toLowerCase());
                } else if (ex.type === 'true_false') {
                    const selected = document.querySelector(`input[name="ex-tf-${index}"]:checked`);
                    if (!selected) { feedbackEl.innerHTML = '<span class="ex-feedback-warn">请先选择正确或错误</span>'; feedbackEl.style.display = 'block'; return; }
                    studentAnswer = selected.value === 'true';
                    isCorrect = studentAnswer === (ex.correct_answer === true || ex.correct_answer === 'true');
                }

                const icon = isCorrect ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-times-circle"></i>';
                const cls = isCorrect ? 'ex-feedback-correct' : 'ex-feedback-wrong';
                const explain = ex.explanation ? `<div class="ex-feedback-explain">${this._escapeHtml(ex.explanation)}</div>` : '';
                feedbackEl.innerHTML = `<div class="${cls}">${icon} ${isCorrect ? '回答正确！' : '回答错误，请再思考一下。'}</div>${explain}`;
                feedbackEl.style.display = 'block';

                if (isCorrect) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-check"></i> 已完成';
                    submitBtn.style.opacity = '0.6';
                }

                this.addChatMessage('user', `练习答案：${studentAnswer} (${isCorrect ? '正确' : '错误'})`);
            });
        }

        _renderExerciseCodeEditor(ex, index) {
            const lang = ex.language || 'python';
            const starterCode = ex.starter_code || ex.code || '';
            const instruction = ex.instruction || '';
            return `
                <div class="exercise-code-editor" data-ex-index="${index}">
                    <div class="exercise-code-header">
                        <span class="exercise-code-title"><i class="fas fa-code"></i> 编程练习 ${index + 1}</span>
                        <select class="exercise-code-lang" id="ex-code-lang-${index}">
                            <option value="python" ${lang === 'python' ? 'selected' : ''}>Python</option>
                            <option value="javascript" ${lang === 'javascript' ? 'selected' : ''}>JavaScript</option>
                            <option value="html" ${lang === 'html' ? 'selected' : ''}>HTML</option>
                        </select>
                    </div>
                    ${instruction ? `<div class="exercise-code-instruction">${this._escapeHtml(instruction)}</div>` : ''}
                    <textarea class="exercise-code-area" id="ex-code-area-${index}" spellcheck="false" placeholder="// 在此输入代码...">${this._escapeHtml(starterCode)}</textarea>
                    <div class="exercise-code-actions">
                        <button class="exercise-code-run" id="ex-code-run-${index}"><i class="fas fa-play"></i> 运行代码</button>
                        <button class="exercise-code-hint" id="ex-code-hint-${index}"><i class="fas fa-robot"></i> AI 提示</button>
                    </div>
                    <div class="exercise-code-output" id="ex-code-output-${index}" style="display:none;"></div>
                </div>
            `;
        }

        _bindExerciseCodeEditorEvents(ex, index) {
            const textarea = document.getElementById(`ex-code-area-${index}`);
            const runBtn = document.getElementById(`ex-code-run-${index}`);
            const hintBtn = document.getElementById(`ex-code-hint-${index}`);
            const output = document.getElementById(`ex-code-output-${index}`);
            const langSelect = document.getElementById(`ex-code-lang-${index}`);

            if (textarea) {
                textarea.addEventListener('keydown', (e) => {
                    if (e.key === 'Tab') {
                        e.preventDefault();
                        const start = textarea.selectionStart;
                        const end = textarea.selectionEnd;
                        textarea.value = textarea.value.substring(0, start) + '    ' + textarea.value.substring(end);
                        textarea.selectionStart = textarea.selectionEnd = start + 4;
                    }
                });
            }

            if (runBtn) {
                runBtn.addEventListener('click', () => {
                    const code = textarea ? textarea.value : '';
                    const language = langSelect ? langSelect.value : 'python';
                    if (!code.trim()) return;
                    this._runCodeInScene(language, code, output);
                });
            }

            if (hintBtn) {
                hintBtn.addEventListener('click', () => {
                    const code = textarea ? textarea.value : '';
                    const language = langSelect ? langSelect.value : 'python';
                    const scene = this.scenes[this.currentIndex];
                    this._getCodeHintFromAI(scene, code, language, output);
                });
            }
        }

        renderInteractiveScene(scene) {
            if (!this.interactiveContainer) return;
            this.interactiveContainer.style.display = 'block';
            const iframe = document.getElementById('interactive-iframe');

            // Check for enhanced interactive data with widget_type
            const interactiveData = this.courseData.interactive_data?.find(i => i.id === scene.id);
            const widgetType = interactiveData?.widget_type;
            const htmlContent = interactiveData?.html_content || interactiveData?.html;

            // Detect code scene: widget type is 'code', or scene type is 'code', or has language data
            const isCodeScene = widgetType === 'code' || scene.type === 'code' || scene.code_data || (interactiveData?.language);
            if (isCodeScene) {
                if (iframe) iframe.style.display = 'none';
                this._renderCodeEditorScene(scene, interactiveData);
                return;
            }
            const existingEditor = this.interactiveContainer.querySelector('.scene-code-editor-wrapper');
            if (existingEditor) existingEditor.remove();
            if (iframe) iframe.style.display = 'block';

            if (iframe) {
                if (htmlContent) {
                    // Render actual interactive HTML content
                    iframe.srcdoc = htmlContent;
                } else if (widgetType) {
                    // Render rich interactive widget based on type
                    iframe.srcdoc = this._buildInteractiveWidgetHTML(scene, widgetType);
                } else {
                    // Basic placeholder - show clear message
                    const safeHtml = this._escapeHtml ? this._escapeHtml.bind(this) : (v => v || '');
                    iframe.srcdoc = `<html><body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#1a1a2e;color:#e0e7ff;margin:0;">
                        <div style="text-align:center;padding:2rem;">
                            <div style="font-size:4rem;margin-bottom:1rem;">📭</div>
                            <h2>${safeHtml(scene.title || '交互式学习')}</h2>
                            <p style="color:#a0aec0;margin-top:0.5rem;">${safeHtml(scene.description || '该场景暂无可用内容')}</p>
                            <p style="color:#6366f1;font-size:0.85rem;margin-top:1rem;">场景类型: ${safeHtml(scene.type)}</p>
                        </div></body></html>`;
                }
            }
        }

        _buildInteractiveWidgetHTML(scene, widgetType) {
            const title = this.SlideRenderer._stripThinkTags(scene.title || '交互式学习');
            const desc = scene.description || '';
            const safe = (str) => String(str || '').replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]));
            const config = scene.config || {};

            const baseStyles = `
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; flex-direction: column; }
                    .widget-header { padding: 1.25rem 1.5rem; background: #1e293b; border-bottom: 1px solid #334155; }
                    .widget-header h2 { font-size: 1.25rem; color: #f8fafc; margin-bottom: 0.25rem; }
                    .widget-header p { font-size: 0.875rem; color: #94a3b8; line-height: 1.5; }
                    .widget-body { flex: 1; padding: 1.5rem; overflow: auto; }
                    .widget-footer { padding: 1rem 1.5rem; background: #1e293b; border-top: 1px solid #334155; font-size: 0.8rem; color: #64748b; display: flex; justify-content: space-between; align-items: center; }
                    .btn { background: #3b82f6; color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; transition: background 0.2s; }
                    .btn:hover { background: #2563eb; }
                    .btn-secondary { background: #475569; }
                    .btn-secondary:hover { background: #334155; }
                    .panel { background: #1e293b; border-radius: 0.5rem; padding: 1rem; border: 1px solid #334155; }
                    input[type="range"] { width: 100%; margin: 0.5rem 0; }
                    label { font-size: 0.8rem; color: #94a3b8; }
                </style>
            `;

            if (widgetType === 'simulation') {
                // Programming-focused simulation: sorting algorithm visualization
                const isAlgoSim = /排序|算法|algorithm|sort|bubble|quick/i.test(title + ' ' + desc);
                if (isAlgoSim) {
                    return `
                        <!DOCTYPE html>
                        <html><head><meta charset="utf-8">${baseStyles}</head>
                        <body>
                            <div class="widget-header"><h2>${safe(title)}</h2><p>${safe(desc)}</p></div>
                            <div class="widget-body" style="display:flex;flex-direction:column;align-items:center;gap:1rem;">
                                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:center;">
                                    <button class="btn btn-secondary" id="btn-bubble">冒泡排序</button>
                                    <button class="btn btn-secondary" id="btn-select">选择排序</button>
                                    <button class="btn btn-secondary" id="btn-insert">插入排序</button>
                                    <button class="btn" id="btn-shuffle">重置数据</button>
                                </div>
                                <div class="panel" style="width:100%;max-width:700px;position:relative;">
                                    <canvas id="algo-canvas" width="660" height="280" style="background:#0f172a;border-radius:0.375rem;"></canvas>
                                    <div id="algo-info" style="position:absolute;top:8px;left:12px;font-size:0.8rem;color:#94a3b8;">点击上方按钮开始可视化</div>
                                </div>
                                <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;justify-content:center;">
                                    <label>速度: <input type="range" id="speed" min="50" max="800" value="300" style="width:120px;vertical-align:middle;"></label>
                                    <label>元素数: <input type="range" id="count" min="5" max="30" value="15" style="width:120px;vertical-align:middle;"></label>
                                </div>
                            </div>
                            <div class="widget-footer"><span>算法可视化</span><span id="algo-status">就绪</span></div>
                            <script>
                                const canvas = document.getElementById('algo-canvas');
                                const ctx = canvas.getContext('2d');
                                let arr = [], animating = false, delay = 300;
                                function genArr(n) { arr = Array.from({length:n},(_,i)=>i+1).sort(()=>Math.random()-0.5); }
                                function draw(hi=-1, hj=-1, done=false) {
                                    ctx.clearRect(0,0,canvas.width,canvas.height);
                                    const n=arr.length, w=Math.floor((canvas.width-40)/n), max=Math.max(...arr);
                                    arr.forEach((v,i)=>{
                                        const h=(v/max)*220, x=20+i*(w+2), y=canvas.height-20-h;
                                        ctx.fillStyle = done ? '#22c55e' : (i===hi||i===hj ? '#f59e0b' : '#3b82f6');
                                        ctx.fillRect(x,y,w,h);
                                        if(n<=20){ ctx.fillStyle='#fff'; ctx.font='10px sans-serif'; ctx.textAlign='center'; ctx.fillText(v,x+w/2,y-4); }
                                    });
                                }
                                function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
                                async function bubbleSort(){
                                    if(animating) return; animating=true; document.getElementById('algo-status').textContent='运行中...';
                                    const n=arr.length;
                                    for(let i=0;i<n;i++){
                                        for(let j=0;j<n-i-1;j++){
                                            draw(j,j+1); await sleep(delay);
                                            if(arr[j]>arr[j+1]){ [arr[j],arr[j+1]]=[arr[j+1],arr[j]]; draw(j,j+1); await sleep(delay); }
                                        }
                                    }
                                    draw(-1,-1,true); animating=false; document.getElementById('algo-status').textContent='完成';
                                    document.getElementById('algo-info').textContent='冒泡排序完成：时间复杂度 O(n²)';
                                }
                                async function selectSort(){
                                    if(animating) return; animating=true; document.getElementById('algo-status').textContent='运行中...';
                                    const n=arr.length;
                                    for(let i=0;i<n;i++){
                                        let min=i;
                                        for(let j=i+1;j<n;j++){ draw(min,j); await sleep(delay); if(arr[j]<arr[min]) min=j; }
                                        if(min!==i){ [arr[i],arr[min]]=[arr[min],arr[i]]; draw(i,min); await sleep(delay); }
                                    }
                                    draw(-1,-1,true); animating=false; document.getElementById('algo-status').textContent='完成';
                                    document.getElementById('algo-info').textContent='选择排序完成：时间复杂度 O(n²)';
                                }
                                async function insertSort(){
                                    if(animating) return; animating=true; document.getElementById('algo-status').textContent='运行中...';
                                    const n=arr.length;
                                    for(let i=1;i<n;i++){
                                        let key=arr[i], j=i-1;
                                        draw(i,j); await sleep(delay);
                                        while(j>=0 && arr[j]>key){ arr[j+1]=arr[j]; j--; draw(i,j); await sleep(delay); }
                                        arr[j+1]=key; draw(i,j+1); await sleep(delay);
                                    }
                                    draw(-1,-1,true); animating=false; document.getElementById('algo-status').textContent='完成';
                                    document.getElementById('algo-info').textContent='插入排序完成：时间复杂度 O(n²)';
                                }
                                document.getElementById('btn-bubble').addEventListener('click', bubbleSort);
                                document.getElementById('btn-select').addEventListener('click', selectSort);
                                document.getElementById('btn-insert').addEventListener('click', insertSort);
                                document.getElementById('btn-shuffle').addEventListener('click', ()=>{ animating=false; genArr(parseInt(document.getElementById('count').value)); draw(); document.getElementById('algo-status').textContent='就绪'; document.getElementById('algo-info').textContent='数据已重置'; });
                                document.getElementById('speed').addEventListener('input', e=>{ delay=850-parseInt(e.target.value); });
                                document.getElementById('count').addEventListener('input', e=>{ if(!animating){ genArr(parseInt(e.target.value)); draw(); }});
                                genArr(15); draw();
                            <\/script>
                        </body></html>`;
                }
                // Generic parameter simulation fallback
                const vars = config.variables || [{ name: 'param1', min: 1, max: 100, value: 50, label: '参数 A' }, { name: 'param2', min: 0, max: 10, value: 5, label: '参数 B' }];
                const varInputs = vars.map((v, i) => `
                    <div style="margin-bottom:1rem;">
                        <label>${safe(v.label || v.name)}: <span id="val-${i}">${v.value}</span></label>
                        <input type="range" id="var-${i}" min="${v.min}" max="${v.max}" value="${v.value}" step="${v.step || 1}">
                    </div>
                `).join('');
                return `
                    <!DOCTYPE html>
                    <html><head><meta charset="utf-8">${baseStyles}</head>
                    <body>
                        <div class="widget-header"><h2>${safe(title)}</h2><p>${safe(desc)}</p></div>
                        <div class="widget-body" style="display:flex;gap:1.5rem;flex-wrap:wrap;">
                            <div class="panel" style="flex:1;min-width:260px;max-width:320px;">
                                <h3 style="font-size:1rem;margin-bottom:1rem;color:#f8fafc;">参数控制</h3>
                                ${varInputs}
                                <button class="btn" id="run-btn" style="width:100%;margin-top:0.5rem;"><i class="fas fa-play"></i> 运行模拟</button>
                            </div>
                            <div class="panel" style="flex:2;min-width:300px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                                <canvas id="sim-canvas" width="500" height="320" style="background:#0f172a;border-radius:0.375rem;border:1px solid #334155;"></canvas>
                                <div id="sim-result" style="margin-top:1rem;font-size:0.875rem;color:#94a3b8;min-height:1.5rem;"></div>
                            </div>
                        </div>
                        <div class="widget-footer"><span>实时模拟</span><span id="sim-status">就绪</span></div>
                        <script>
                            const canvas = document.getElementById('sim-canvas');
                            const ctx = canvas.getContext('2d');
                            const vars = ${JSON.stringify(vars)};
                            const values = vars.map((v,i) => ({ idx: i, val: v.value }));
                            function drawStatic() {
                                ctx.clearRect(0,0,canvas.width,canvas.height);
                                ctx.fillStyle='#94a3b8'; ctx.font='14px sans-serif'; ctx.textAlign='center';
                                ctx.fillText('参数模拟器', canvas.width/2, canvas.height/2);
                                ctx.font='12px sans-serif';
                                values.forEach((v,i)=>{ ctx.fillText(vars[v.idx].label + ': ' + v.val, canvas.width/2, canvas.height/2 + 24 + i*20); });
                            }
                            vars.forEach((v,i) => {
                                const el = document.getElementById('var-'+i);
                                if(!el) return;
                                el.addEventListener('input', e => { values[i].val = parseFloat(e.target.value); document.getElementById('val-'+i).textContent = values[i].val; drawStatic(); });
                            });
                            document.getElementById('run-btn').addEventListener('click', ()=>{
                                document.getElementById('sim-status').textContent='运行完成';
                                document.getElementById('sim-result').textContent='参数更新: ' + values.map(v=>vars[v.idx].label+'='+v.val).join(', ');
                                drawStatic();
                            });
                            drawStatic();
                        <\/script>
                    </body></html>`;
            }

            if (widgetType === 'diagram') {
                const diagramType = config.diagram_type || 'flowchart';
                const mermaidCode = config.mermaid_code || `flowchart TD\n    A[开始] --> B{判断}\n    B -->|是| C[执行A]\n    B -->|否| D[执行B]\n    C --> E[结束]\n    D --> E`;
                const uid = 'dgm-' + Math.random().toString(36).slice(2, 8);
                return `
                    <!DOCTYPE html>
                    <html><head><meta charset="utf-8">${baseStyles}
                        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"><\/script>
                        <style>
                            .mermaid { min-width: 200px; min-height: 120px; }
                            .mermaid svg { max-width: 100%; height: auto; }
                        </style>
                    </head>
                    <body>
                        <div class="widget-header"><h2>${safe(title)}</h2><p>${safe(desc)}</p></div>
                        <div class="widget-body" style="display:flex;flex-direction:column;align-items:center;">
                            <div class="panel" style="width:100%;max-width:900px;margin:0 auto;">
                                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;flex-wrap:wrap;gap:0.5rem;">
                                    <span style="font-size:0.8rem;color:#94a3b8;">类型: ${safe(diagramType)}</span>
                                    <button class="btn btn-secondary" id="${uid}-refresh">重新渲染</button>
                                </div>
                                <div id="${uid}-container" style="display:flex;justify-content:center;min-height:200px;align-items:center;">
                                    <div class="mermaid">${safe(mermaidCode)}</div>
                                </div>
                            </div>
                        </div>
                        <div class="widget-footer"><span>交互式图表</span><span>Mermaid.js 驱动</span></div>
                        <script>
                            mermaid.initialize({ startOnLoad: true, theme: 'dark', securityLevel: 'loose' });
                            document.getElementById('${uid}-refresh').addEventListener('click', () => {
                                const container = document.getElementById('${uid}-container');
                                const code = \`${safe(mermaidCode)}\`;
                                container.innerHTML = '<div class="mermaid">' + code + '</div>';
                                mermaid.init(undefined, container.querySelectorAll('.mermaid'));
                            });
                        <\/script>
                    </body></html>`;
            }

            if (widgetType === 'game') {
                const pairs = config.pairs || [
                    { q: 'def', a: '定义函数' },
                    { q: 'class', a: '定义类' },
                    { q: 'for', a: '循环遍历' },
                    { q: 'if', a: '条件判断' },
                    { q: 'return', a: '返回结果' },
                    { q: 'import', a: '导入模块' },
                    { q: 'list', a: '列表' },
                    { q: 'dict', a: '字典' }
                ];
                const items = [];
                pairs.forEach((p, i) => { items.push({ id: i+'q', text: p.q, match: i+'a' }); items.push({ id: i+'a', text: p.a, match: i+'q' }); });
                items.sort(() => Math.random() - 0.5);
                const cards = items.map(it => `
                    <div class="game-card" data-id="${it.id}" data-match="${it.match}" style="background:#1e293b;border:2px solid #334155;border-radius:0.5rem;padding:1rem;cursor:pointer;text-align:center;transition:all 0.2s;min-height:80px;display:flex;align-items:center;justify-content:center;font-size:0.9rem;user-select:none;">
                        <span class="card-text" style="display:none;color:#f8fafc;">${safe(it.text)}</span>
                        <span class="card-cover" style="font-size:1.5rem;">?</span>
                    </div>
                `).join('');
                return `
                    <!DOCTYPE html>
                    <html><head><meta charset="utf-8">${baseStyles}</head>
                    <body>
                        <div class="widget-header"><h2>${safe(title)}</h2><p>${safe(desc)}</p></div>
                        <div class="widget-body" style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
                            <div style="display:flex;gap:1rem;margin-bottom:1.5rem;align-items:center;">
                                <div style="font-size:0.9rem;color:#94a3b8;">得分: <span id="score" style="color:#f59e0b;font-weight:bold;">0</span></div>
                                <div style="font-size:0.9rem;color:#94a3b8;">步数: <span id="moves" style="color:#3b82f6;font-weight:bold;">0</span></div>
                                <button class="btn" id="reset-game" style="font-size:0.8rem;padding:0.35rem 0.75rem;">重新开始</button>
                            </div>
                            <div id="game-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;max-width:640px;width:100%;">${cards}</div>
                            <div id="game-msg" style="margin-top:1rem;font-size:0.9rem;color:#94a3b8;min-height:1.5rem;"></div>
                        </div>
                        <div class="widget-footer"><span>记忆配对游戏</span><span>点击卡片翻转匹配</span></div>
                        <script>
                            let first=null, score=0, moves=0, lock=false, matched=0;
                            const totalPairs = ${pairs.length};
                            function update() { document.getElementById('score').textContent=score; document.getElementById('moves').textContent=moves; }
                            function flip(card, show) {
                                const text=card.querySelector('.card-text'), cover=card.querySelector('.card-cover');
                                text.style.display=show?'block':'none'; cover.style.display=show?'none':'block';
                                card.style.borderColor=show?'#3b82f6':'#334155';
                            }
                            function init() {
                                first=null; score=0; moves=0; lock=false; matched=0; update();
                                document.getElementById('game-msg').textContent='';
                                document.querySelectorAll('.game-card').forEach(c=>{ flip(c,false); c.classList.remove('matched'); c.style.opacity='1'; });
                            }
                            document.getElementById('game-grid').addEventListener('click', e=>{
                                const card=e.target.closest('.game-card'); if(!card||lock||card.classList.contains('matched')) return;
                                if(first===card) return;
                                flip(card,true);
                                if(!first){ first=card; return; }
                                moves++; update(); lock=true;
                                const c1=first, c2=card;
                                if(c1.dataset.match===c2.dataset.id){ score+=10; matched++; update(); c1.classList.add('matched'); c2.classList.add('matched'); c1.style.borderColor='#22c55e'; c2.style.borderColor='#22c55e'; first=null; lock=false; if(matched===totalPairs) document.getElementById('game-msg').textContent='🎉 恭喜完成全部配对！'; }
                                else { setTimeout(()=>{ flip(c1,false); flip(c2,false); first=null; lock=false; },800); }
                            });
                            document.getElementById('reset-game').addEventListener('click', init);
                        <\/script>
                    </body></html>`;
            }

            if (widgetType === 'visualization3d') {
                const shape = config.shape || 'cube';
                return `
                    <!DOCTYPE html>
                    <html><head><meta charset="utf-8">${baseStyles}
                        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>
                    </head>
                    <body>
                        <div class="widget-header"><h2>${safe(title)}</h2><p>${safe(desc)}</p></div>
                        <div class="widget-body" style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
                            <div id="three-container" style="width:100%;max-width:700px;height:400px;border-radius:0.5rem;border:1px solid #334155;overflow:hidden;background:#000;"></div>
                            <div style="margin-top:1rem;display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:center;">
                                <button class="btn btn-secondary shape-btn" data-shape="cube">立方体</button>
                                <button class="btn btn-secondary shape-btn" data-shape="sphere">球体</button>
                                <button class="btn btn-secondary shape-btn" data-shape="torus">圆环</button>
                                <button class="btn btn-secondary shape-btn" data-shape="cone">圆锥</button>
                            </div>
                        </div>
                        <div class="widget-footer"><span>3D 可视化</span><span>Three.js 驱动</span></div>
                        <script>
                            const container = document.getElementById('three-container');
                            const scene3d = new THREE.Scene();
                            scene3d.background = new THREE.Color(0x0f172a);
                            const camera = new THREE.PerspectiveCamera(60, container.clientWidth/container.clientHeight, 0.1, 1000);
                            camera.position.z = 4;
                            const renderer = new THREE.WebGLRenderer({ antialias: true });
                            renderer.setSize(container.clientWidth, container.clientHeight);
                            container.appendChild(renderer.domElement);
                            const ambient = new THREE.AmbientLight(0xffffff, 0.6);
                            const directional = new THREE.DirectionalLight(0xffffff, 0.8);
                            directional.position.set(2,2,2);
                            scene3d.add(ambient, directional);
                            let mesh = null;
                            function createShape(type) {
                                if(mesh){ scene3d.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); }
                                let geo;
                                if(type==='sphere') geo=new THREE.SphereGeometry(1,32,32);
                                else if(type==='torus') geo=new THREE.TorusGeometry(0.8,0.3,16,50);
                                else if(type==='cone') geo=new THREE.ConeGeometry(1,2,32);
                                else geo=new THREE.BoxGeometry(1.5,1.5,1.5);
                                const mat = new THREE.MeshStandardMaterial({ color: 0x3b82f6, metalness: 0.3, roughness: 0.4 });
                                mesh = new THREE.Mesh(geo, mat);
                                scene3d.add(mesh);
                            }
                            createShape('${shape}');
                            function animate() { requestAnimationFrame(animate); if(mesh){ mesh.rotation.x+=0.005; mesh.rotation.y+=0.01; } renderer.render(scene3d, camera); }
                            animate();
                            document.querySelectorAll('.shape-btn').forEach(btn=>{
                                btn.addEventListener('click',()=>{ createShape(btn.dataset.shape); });
                            });
                            window.addEventListener('resize',()=>{
                                const w=container.clientWidth, h=container.clientHeight;
                                camera.aspect=w/h; camera.updateProjectionMatrix(); renderer.setSize(w,h);
                            });
                        <\/script>
                    </body></html>`;
            }

            if (widgetType === 'terminal') {
                const isGit = /git/i.test(title + ' ' + desc);
                const isPython = /python|pip/i.test(title + ' ' + desc);
                const termTitle = isGit ? 'Git CLI 模拟器' : (isPython ? 'Python REPL 模拟器' : '命令行模拟器');
                const promptStr = isGit ? 'user@repo:~$' : (isPython ? '>>>' : '127.0.0.1:6379>');
                const presetData = config.preset_data || {
                    'name': { type: 'string', value: 'Alice' },
                    'age': { type: 'string', value: '25' },
                    'users:1': { type: 'hash', value: { name: 'Bob', email: 'bob@example.com', role: 'admin' } },
                    'users:2': { type: 'hash', value: { name: 'Carol', email: 'carol@example.com', role: 'user' } },
                    'tasks': { type: 'list', value: ['学习Redis', '练习命令', '完成测验'] },
                    'course': { type: 'string', value: 'Redis基础入门' }
                };
                const presetJson = JSON.stringify(presetData).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                return `
                    <!DOCTYPE html>
                    <html><head><meta charset="utf-8">${baseStyles}
                        <style>
                            .terminal-wrap { background:#0a0a0f; border-radius:0.5rem; border:1px solid #1e293b; overflow:hidden; display:flex; flex-direction:column; height:100%; max-height:520px; }
                            .terminal-header { background:#1e293b; padding:0.5rem 1rem; display:flex; align-items:center; gap:0.5rem; border-bottom:1px solid #334155; }
                            .term-btn { width:12px; height:12px; border-radius:50%; }
                            .term-btn.r { background:#ef4444; } .term-btn.y { background:#eab308; } .term-btn.g { background:#22c55e; }
                            .terminal-title { font-size:0.8rem; color:#94a3b8; margin-left:0.5rem; }
                            .terminal-body { flex:1; padding:1rem; overflow-y:auto; font-family:'Consolas','Monaco','Courier New',monospace; font-size:0.9rem; line-height:1.6; }
                            .terminal-line { margin:0.15rem 0; }
                            .terminal-prompt { color:#22d3ee; }
                            .terminal-input { color:#4ade80; background:transparent; border:none; outline:none; font-family:inherit; font-size:inherit; width:80%; }
                            .terminal-output { color:#e2e8f0; }
                            .terminal-error { color:#ef4444; }
                            .terminal-success { color:#4ade80; }
                            .terminal-info { color:#94a3b8; }
                            .terminal-welcome { color:#f59e0b; margin-bottom:0.5rem; }
                            .terminal-input-line { display:flex; align-items:center; gap:0.35rem; }
                        </style>
                    </head>
                    <body>
                        <div class="widget-header"><h2>${safe(title)}</h2><p>${safe(desc)}</p></div>
                        <div class="widget-body" style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
                            <div class="terminal-wrap" style="width:100%;max-width:720px;">
                                <div class="terminal-header">
                                    <span class="term-btn r"></span><span class="term-btn y"></span><span class="term-btn g"></span>
                                    <span class="terminal-title">${termTitle}</span>
                                </div>
                                <div class="terminal-body" id="term-body">
                                    <div class="terminal-welcome">🚀 欢迎使用 ${termTitle}！</div>
                                    <div class="terminal-info">输入 HELP 查看可用命令列表</div>
                                    <div class="terminal-info">当前已预加载一些示例数据，试着输入：GET name</div>
                                </div>
                                <div style="padding:0.5rem 1rem;background:#0a0a0f;border-top:1px solid #1e293b;">
                                    <div class="terminal-input-line">
                                        <span class="terminal-prompt">${promptStr}&gt;</span>
                                        <input type="text" class="terminal-input" id="term-input" autocomplete="off" spellcheck="false" placeholder="输入命令...">
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="widget-footer"><span>${termTitle}</span><span>纯客户端模拟，无后端通信</span></div>
                        <script>
                            const db = new Map();
                            const preset = JSON.parse('${presetJson}');
                            Object.keys(preset).forEach(k => {
                                const v = preset[k];
                                db.set(k, { type: v.type, value: JSON.parse(JSON.stringify(v.value)), expires: null });
                            });
                            const history = []; let histIdx = -1;
                            const body = document.getElementById('term-body');
                            const input = document.getElementById('term-input');
                            function appendLine(text, cls) {
                                const div = document.createElement('div');
                                div.className = 'terminal-line ' + (cls || 'terminal-output');
                                div.textContent = text;
                                body.appendChild(div);
                                body.scrollTop = body.scrollHeight;
                            }
                            function appendPrompt(cmd) {
                                const div = document.createElement('div');
                                div.className = 'terminal-line';
                                div.innerHTML = '<span class="terminal-prompt">127.0.0.1:6379&gt;</span> ' + escapeHtml(cmd);
                                body.appendChild(div);
                                body.scrollTop = body.scrollHeight;
                            }
                            function escapeHtml(s) {
                                return String(s).replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
                            }
                            function checkExpired(key) {
                                const entry = db.get(key);
                                if (entry && entry.expires && Date.now() > entry.expires) { db.delete(key); return null; }
                                return entry;
                            }
                            function execCmd(cmd) {
                                const parts = cmd.trim().split(/\s+/);
                                if (parts.length === 0) return;
                                const c = parts[0].toUpperCase();
                                if (c === 'HELP') {
                                    appendLine('可用命令：', 'terminal-success');
                                    appendLine('  SET key value        - 设置键值对', 'terminal-info');
                                    appendLine('  GET key              - 获取键值', 'terminal-info');
                                    appendLine('  DEL key              - 删除键', 'terminal-info');
                                    appendLine('  EXISTS key           - 检查键是否存在', 'terminal-info');
                                    appendLine('  KEYS pattern         - 查找键（支持 * 通配符）', 'terminal-info');
                                    appendLine('  HSET key field value - 设置哈希字段', 'terminal-info');
                                    appendLine('  HGET key field       - 获取哈希字段', 'terminal-info');
                                    appendLine('  HGETALL key          - 获取哈希所有字段', 'terminal-info');
                                    appendLine('  LPUSH key value      - 列表左侧插入', 'terminal-info');
                                    appendLine('  LRANGE key start stop- 获取列表范围', 'terminal-info');
                                    appendLine('  EXPIRE key seconds   - 设置过期时间', 'terminal-info');
                                    appendLine('  TTL key              - 查看剩余时间', 'terminal-info');
                                    appendLine('  CLEAR                - 清屏', 'terminal-info');
                                    appendLine('  HELP                 - 显示此帮助', 'terminal-info');
                                    return;
                                }
                                if (c === 'CLEAR') { body.innerHTML = ''; return; }
                                if (c === 'SET' && parts.length >= 3) {
                                    const key = parts[1];
                                    const value = parts.slice(2).join(' ');
                                    db.set(key, { type: 'string', value: value, expires: null });
                                    appendLine('OK', 'terminal-success'); return;
                                }
                                if (c === 'GET' && parts.length >= 2) {
                                    const entry = checkExpired(parts[1]);
                                    if (!entry) { appendLine('(nil)', 'terminal-info'); return; }
                                    if (entry.type !== 'string') { appendLine('(error) WRONGTYPE 该键不是字符串类型', 'terminal-error'); return; }
                                    appendLine(String(entry.value), 'terminal-output'); return;
                                }
                                if (c === 'DEL' && parts.length >= 2) {
                                    let count = 0;
                                    for (let i = 1; i < parts.length; i++) { if (db.has(parts[i])) { db.delete(parts[i]); count++; } }
                                    appendLine('(integer) ' + count, 'terminal-success'); return;
                                }
                                if (c === 'EXISTS' && parts.length >= 2) {
                                    const entry = checkExpired(parts[1]);
                                    appendLine('(integer) ' + (entry ? 1 : 0), 'terminal-success'); return;
                                }
                                if (c === 'KEYS' && parts.length >= 2) {
                                    const pattern = parts[1];
                                    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$');
                                    const matches = [];
                                    db.forEach((v, k) => { if (regex.test(k) && checkExpired(k)) matches.push(k); });
                                    if (matches.length === 0) { appendLine('(empty list)', 'terminal-info'); return; }
                                    matches.forEach(k => appendLine(k, 'terminal-output'));
                                    return;
                                }
                                if (c === 'HSET' && parts.length >= 4) {
                                    const key = parts[1], field = parts[2];
                                    const value = parts.slice(3).join(' ');
                                    let entry = checkExpired(key);
                                    if (!entry) { entry = { type: 'hash', value: {}, expires: null }; db.set(key, entry); }
                                    if (entry.type !== 'hash') { appendLine('(error) WRONGTYPE', 'terminal-error'); return; }
                                    const isNew = !(field in entry.value);
                                    entry.value[field] = value;
                                    appendLine('(integer) ' + (isNew ? 1 : 0), 'terminal-success'); return;
                                }
                                if (c === 'HGET' && parts.length >= 3) {
                                    const entry = checkExpired(parts[1]);
                                    if (!entry) { appendLine('(nil)', 'terminal-info'); return; }
                                    if (entry.type !== 'hash') { appendLine('(error) WRONGTYPE', 'terminal-error'); return; }
                                    appendLine(entry.value[parts[2]] !== undefined ? String(entry.value[parts[2]]) : '(nil)', 'terminal-output'); return;
                                }
                                if (c === 'HGETALL' && parts.length >= 2) {
                                    const entry = checkExpired(parts[1]);
                                    if (!entry) { appendLine('(empty list)', 'terminal-info'); return; }
                                    if (entry.type !== 'hash') { appendLine('(error) WRONGTYPE', 'terminal-error'); return; }
                                    Object.keys(entry.value).forEach(f => { appendLine(f, 'terminal-output'); appendLine(String(entry.value[f]), 'terminal-output'); });
                                    return;
                                }
                                if (c === 'LPUSH' && parts.length >= 3) {
                                    const key = parts[1];
                                    const value = parts.slice(2).join(' ');
                                    let entry = checkExpired(key);
                                    if (!entry) { entry = { type: 'list', value: [], expires: null }; db.set(key, entry); }
                                    if (entry.type !== 'list') { appendLine('(error) WRONGTYPE', 'terminal-error'); return; }
                                    entry.value.unshift(value);
                                    appendLine('(integer) ' + entry.value.length, 'terminal-success'); return;
                                }
                                if (c === 'LRANGE' && parts.length >= 4) {
                                    const entry = checkExpired(parts[1]);
                                    if (!entry) { appendLine('(empty list)', 'terminal-info'); return; }
                                    if (entry.type !== 'list') { appendLine('(error) WRONGTYPE', 'terminal-error'); return; }
                                    const start = parseInt(parts[2]), stop = parseInt(parts[3]);
                                    const arr = entry.value.slice(start, stop + 1);
                                    if (arr.length === 0) { appendLine('(empty list)', 'terminal-info'); return; }
                                    arr.forEach((v, i) => appendLine((start + i) + ') "' + v + '"', 'terminal-output'));
                                    return;
                                }
                                if (c === 'EXPIRE' && parts.length >= 3) {
                                    const entry = checkExpired(parts[1]);
                                    if (!entry) { appendLine('(integer) 0', 'terminal-success'); return; }
                                    entry.expires = Date.now() + parseInt(parts[2]) * 1000;
                                    appendLine('(integer) 1', 'terminal-success'); return;
                                }
                                if (c === 'TTL' && parts.length >= 2) {
                                    const entry = checkExpired(parts[1]);
                                    if (!entry) { appendLine('(integer) -2', 'terminal-success'); return; }
                                    if (!entry.expires) { appendLine('(integer) -1', 'terminal-success'); return; }
                                    const ttl = Math.ceil((entry.expires - Date.now()) / 1000);
                                    appendLine('(integer) ' + (ttl > 0 ? ttl : -2), 'terminal-success'); return;
                                }
                                appendLine('(error) 未知命令或参数不足。输入 HELP 查看可用命令。', 'terminal-error');
                            }
                            input.addEventListener('keydown', e => {
                                if (e.key === 'Enter') {
                                    const cmd = input.value.trim();
                                    if (cmd) {
                                        history.push(cmd); histIdx = history.length;
                                        appendPrompt(cmd);
                                        execCmd(cmd);
                                    }
                                    input.value = '';
                                } else if (e.key === 'ArrowUp') {
                                    e.preventDefault();
                                    if (histIdx > 0) { histIdx--; input.value = history[histIdx]; }
                                } else if (e.key === 'ArrowDown') {
                                    e.preventDefault();
                                    if (histIdx < history.length - 1) { histIdx++; input.value = history[histIdx]; }
                                    else if (histIdx >= history.length - 1) { histIdx = history.length; input.value = ''; }
                                }
                            });
                            input.focus();
                        <\/script>
                    </body></html>`;
            }

            if (widgetType === 'code_visualizer') {
                return `
                    <!DOCTYPE html>
                    <html><head><meta charset="utf-8">${baseStyles}</head>
                    <body>
                        <div class="widget-header"><h2>${safe(title)}</h2><p>${safe(desc)}</p></div>
                        <div class="widget-body" style="display:flex;flex-direction:column;align-items:center;gap:1rem;">
                            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:center;">
                                <button class="btn btn-secondary" id="cv-bubble">冒泡排序</button>
                                <button class="btn btn-secondary" id="cv-select">选择排序</button>
                                <button class="btn btn-secondary" id="cv-insert">插入排序</button>
                                <button class="btn" id="cv-shuffle">重置数据</button>
                            </div>
                            <div class="panel" style="width:100%;max-width:700px;position:relative;">
                                <canvas id="cv-canvas" width="660" height="280" style="background:#0f172a;border-radius:0.375rem;"></canvas>
                                <div id="cv-info" style="position:absolute;top:8px;left:12px;font-size:0.8rem;color:#94a3b8;">点击上方按钮开始算法可视化</div>
                            </div>
                            <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;justify-content:center;">
                                <label>速度: <input type="range" id="cv-speed" min="50" max="800" value="300" style="width:120px;vertical-align:middle;"></label>
                                <label>元素数: <input type="range" id="cv-count" min="5" max="30" value="15" style="width:120px;vertical-align:middle;"></label>
                            </div>
                        </div>
                        <div class="widget-footer"><span>代码可视化</span><span id="cv-status">就绪</span></div>
                        <script>
                            const canvas = document.getElementById('cv-canvas');
                            const ctx = canvas.getContext('2d');
                            let arr = [], animating = false, delay = 300;
                            function genArr(n) { arr = Array.from({length:n},(_,i)=>i+1).sort(()=>Math.random()-0.5); }
                            function draw(hi=-1, hj=-1, done=false) {
                                ctx.clearRect(0,0,canvas.width,canvas.height);
                                const n=arr.length, w=Math.floor((canvas.width-40)/n), max=Math.max(...arr);
                                arr.forEach((v,i)=>{
                                    const h=(v/max)*220, x=20+i*(w+2), y=canvas.height-20-h;
                                    ctx.fillStyle = done ? '#22c55e' : (i===hi||i===hj ? '#f59e0b' : '#3b82f6');
                                    ctx.fillRect(x,y,w,h);
                                    if(n<=20){ ctx.fillStyle='#fff'; ctx.font='10px sans-serif'; ctx.textAlign='center'; ctx.fillText(v,x+w/2,y-4); }
                                });
                            }
                            function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
                            async function bubbleSort(){
                                if(animating) return; animating=true; document.getElementById('cv-status').textContent='运行中...';
                                const n=arr.length;
                                for(let i=0;i<n;i++){
                                    for(let j=0;j<n-i-1;j++){
                                        draw(j,j+1); await sleep(delay);
                                        if(arr[j]>arr[j+1]){ [arr[j],arr[j+1]]=[arr[j+1],arr[j]]; draw(j,j+1); await sleep(delay); }
                                    }
                                }
                                draw(-1,-1,true); animating=false; document.getElementById('cv-status').textContent='完成';
                                document.getElementById('cv-info').textContent='冒泡排序完成：时间复杂度 O(n²)';
                            }
                            async function selectSort(){
                                if(animating) return; animating=true; document.getElementById('cv-status').textContent='运行中...';
                                const n=arr.length;
                                for(let i=0;i<n;i++){
                                    let min=i;
                                    for(let j=i+1;j<n;j++){ draw(min,j); await sleep(delay); if(arr[j]<arr[min]) min=j; }
                                    if(min!==i){ [arr[i],arr[min]]=[arr[min],arr[i]]; draw(i,min); await sleep(delay); }
                                }
                                draw(-1,-1,true); animating=false; document.getElementById('cv-status').textContent='完成';
                                document.getElementById('cv-info').textContent='选择排序完成：时间复杂度 O(n²)';
                            }
                            async function insertSort(){
                                if(animating) return; animating=true; document.getElementById('cv-status').textContent='运行中...';
                                const n=arr.length;
                                for(let i=1;i<n;i++){
                                    let key=arr[i], j=i-1;
                                    draw(i,j); await sleep(delay);
                                    while(j>=0 && arr[j]>key){ arr[j+1]=arr[j]; j--; draw(i,j); await sleep(delay); }
                                    arr[j+1]=key; draw(i,j+1); await sleep(delay);
                                }
                                draw(-1,-1,true); animating=false; document.getElementById('cv-status').textContent='完成';
                                document.getElementById('cv-info').textContent='插入排序完成：时间复杂度 O(n²)';
                            }
                            document.getElementById('cv-bubble').addEventListener('click', bubbleSort);
                            document.getElementById('cv-select').addEventListener('click', selectSort);
                            document.getElementById('cv-insert').addEventListener('click', insertSort);
                            document.getElementById('cv-shuffle').addEventListener('click', ()=>{ animating=false; genArr(parseInt(document.getElementById('cv-count').value)); draw(); document.getElementById('cv-status').textContent='就绪'; document.getElementById('cv-info').textContent='数据已重置'; });
                            document.getElementById('cv-speed').addEventListener('input', e=>{ delay=850-parseInt(e.target.value); });
                            document.getElementById('cv-count').addEventListener('input', e=>{ if(!animating){ genArr(parseInt(e.target.value)); draw(); }});
                            genArr(15); draw();
                        <\/script>
                    </body></html>`;
            }

            // Fallback for unknown widget types
            return `
                <!DOCTYPE html>
                <html><head><meta charset="utf-8">${baseStyles}</head>
                <body style="display:flex;align-items:center;justify-content:center;height:100vh;">
                    <div style="text-align:center;padding:2rem;">
                        <div style="font-size:3rem;margin-bottom:1rem;">🔧</div>
                        <h2>${safe(title)}</h2>
                        <p style="color:#94a3b8;margin-top:0.5rem;">${safe(desc)}</p>
                        <p style="color:#64748b;font-size:0.8rem;margin-top:1rem;">组件类型: ${safe(widgetType)}</p>
                    </div>
                </body></html>`;
        }

        renderPBLScene(scene) {
            if (!this.interactiveContainer) return;
            this.interactiveContainer.style.display = 'block';
            const title = this.SlideRenderer._stripThinkTags(scene.title || '项目式学习');
            const desc = scene.description || '';
            const scenario = scene.scenario || scene.pbl_scenario || desc;
            const objectives = scene.objectives || scene.pbl_objectives || ['理解核心概念', '应用知识解决实际问题', '培养批判性思维'];
            const safe = (str) => String(str || '').replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]));

            const html = `
                <!DOCTYPE html>
                <html><head><meta charset="utf-8">
                <style>
                    * { margin:0; padding:0; box-sizing:border-box; }
                    body { font-family:'Segoe UI',system-ui,sans-serif; background:#0f172a; color:#e2e8f0; min-height:100vh; }
                    .pbl-header { padding:1.5rem 2rem; background:#1e293b; border-bottom:1px solid #334155; }
                    .pbl-header h2 { font-size:1.4rem; color:#f8fafc; margin-bottom:0.5rem; }
                    .pbl-header .tag { display:inline-block; background:#3b82f6; color:white; font-size:0.75rem; padding:0.25rem 0.75rem; border-radius:9999px; margin-right:0.5rem; }
                    .pbl-body { padding:2rem; max-width:960px; margin:0 auto; }
                    .pbl-section { background:#1e293b; border-radius:0.5rem; padding:1.25rem; margin-bottom:1.25rem; border:1px solid #334155; }
                    .pbl-section h3 { font-size:1rem; color:#f8fafc; margin-bottom:0.75rem; display:flex;align-items:center;gap:0.5rem; }
                    .pbl-section p, .pbl-section li { font-size:0.9rem; color:#94a3b8; line-height:1.6; }
                    .pbl-section ul { padding-left:1.25rem; }
                    .pbl-section li { margin-bottom:0.35rem; }
                    .pbl-workspace { background:#0f172a; border:1px dashed #475569; border-radius:0.5rem; padding:1rem; min-height:120px; }
                    .pbl-workspace textarea { width:100%; min-height:100px; background:transparent; border:none; color:#e2e8f0; font-family:inherit; font-size:0.9rem; resize:vertical; outline:none; }
                    .pbl-actions { display:flex; gap:0.75rem; margin-top:1rem; }
                    .btn { background:#3b82f6; color:white; border:none; padding:0.6rem 1.2rem; border-radius:0.375rem; cursor:pointer; font-size:0.9rem; transition:background 0.2s; }
                    .btn:hover { background:#2563eb; }
                    .btn-outline { background:transparent; border:1px solid #475569; color:#94a3b8; }
                    .btn-outline:hover { background:#334155; color:#e2e8f0; }
                    .hint-box { display:none; background:#1e3a5f; border-left:3px solid #3b82f6; padding:0.75rem 1rem; margin-top:0.75rem; border-radius:0 0.25rem 0.25rem 0; font-size:0.85rem; color:#bfdbfe; }
                </style>
                </head>
                <body>
                    <div class="pbl-header">
                        <div style="margin-bottom:0.5rem;"><span class="tag">PBL</span><span class="tag">项目式学习</span></div>
                        <h2>${safe(title)}</h2>
                        <p style="color:#94a3b8;font-size:0.9rem;margin-top:0.25rem;">${safe(desc)}</p>
                    </div>
                    <div class="pbl-body">
                        <div class="pbl-section">
                            <h3>🎯 问题场景</h3>
                            <p>${safe(scenario)}</p>
                        </div>
                        <div class="pbl-section">
                            <h3>📋 学习目标</h3>
                            <ul>${objectives.map(o => '<li>' + safe(o) + '</li>').join('')}</ul>
                        </div>
                        <div class="pbl-section">
                            <h3>🔍 分析步骤</h3>
                            <div class="pbl-workspace">
                                <textarea id="pbl-analysis" placeholder="在此记录你的分析思路..."></textarea>
                            </div>
                        </div>
                        <div class="pbl-section">
                            <h3>💡 解决方案</h3>
                            <div class="pbl-workspace">
                                <textarea id="pbl-solution" placeholder="在此描述你的解决方案..."></textarea>
                            </div>
                            <div id="pbl-hint" class="hint-box"></div>
                            <div class="pbl-actions">
                                <button class="btn" id="pbl-submit"><i class="fas fa-check"></i> 提交方案</button>
                                <button class="btn btn-outline" id="pbl-hint-btn"><i class="fas fa-lightbulb"></i> 获取提示</button>
                            </div>
                        </div>
                    </div>
                </body></html>
            `;

            const iframe = document.getElementById('interactive-iframe');
            const existingEditor = this.interactiveContainer.querySelector('.scene-code-editor-wrapper');
            if (existingEditor) existingEditor.remove();
            if (iframe) {
                iframe.style.display = 'block';
                iframe.srcdoc = html;
            }
        }

        // ---- Interactive Code Editor ----

        _generateDefaultCodeExercise(scene, existingData) {
            const title = (scene.title || '').toLowerCase();
            const desc = (scene.description || '').toLowerCase();
            const combined = title + ' ' + desc;

            // Infer language from title/description
            let lang = 'python';
            if (combined.includes('javascript') || combined.includes('js') || combined.includes('前端')) {
                lang = 'javascript';
            } else if (combined.includes('html') || combined.includes('网页') || combined.includes('页面')) {
                lang = 'html';
            } else if (combined.includes('sql') || combined.includes('数据库') || combined.includes('查询')) {
                lang = 'sql';
            }

            // Generate starter code and instruction based on topic
            let starterCode = '';
            let instruction = '';
            let expectedOutput = '';
            let hints = [];

            if (lang === 'python') {
                starterCode = '# TODO: 请根据题目要求补全下面的代码\\n# 提示：可以先尝试运行，观察当前输出\\n\\ndef main():\\n    # 请在此编写你的代码\\n    pass\\n\\nif __name__ == "__main__":\\n    main()';
                instruction = scene.description || ('请完成关于 "' + scene.title + '" 的编程练习。\\n\\n这是一个入门级别的练习，目的是帮助你熟悉基本的编程概念。请先阅读题目要求，然后补全代码中的 TODO 部分。');
                expectedOutput = '（根据你的代码实现，输出可能不同）';
                hints = [
                    '先仔细阅读题目要求，理解需要实现什么功能',
                    '从简单的实现开始，不要想得太复杂',
                    '可以多次运行代码，观察输出结果来调整',
                    '如果遇到困难，可以点击"AI提示"获取帮助'
                ];
            } else if (lang === 'javascript') {
                starterCode = '// TODO: 请根据题目要求补全下面的代码\\n// 提示：可以先尝试运行，观察当前输出\\n\\nfunction main() {\\n    // 请在此编写你的代码\\n    console.log("Hello World!");\\n}\\n\\nmain();';
                instruction = scene.description || ('请完成关于 "' + scene.title + '" 的编程练习。\\n\\n这是一个入门级别的练习。请先阅读题目要求，然后补全代码中的 TODO 部分。');
                expectedOutput = '（根据你的代码实现，输出可能不同）';
                hints = [
                    'JavaScript 使用 console.log() 来输出内容',
                    '仔细阅读题目要求，理解需要实现什么功能',
                    '可以多次运行代码，观察输出结果来调整'
                ];
            } else if (lang === 'html') {
                starterCode = '<!-- TODO: 请根据题目要求修改下面的 HTML 代码 -->\\n<!DOCTYPE html>\\n<html>\\n<head>\\n    <title>我的页面</title>\\n</head>\\n<body>\\n    <!-- 请在此添加你的 HTML 内容 -->\\n    <p>Hello World!</p>\\n</body>\\n</html>';
                instruction = scene.description || ('请完成关于 "' + scene.title + '" 的HTML练习。\\n\\n这是一个入门级别的练习。请修改 HTML 代码来实现题目要求。');
                expectedOutput = '（一个正确渲染的网页）';
                hints = [
                    'HTML 使用标签来组织内容，如 <p> 是段落标签',
                    '注意标签要正确配对开启和关闭',
                    '可以使用 <div> 来创建区块容器'
                ];
            }

            return Object.assign({}, existingData, {
                language: lang,
                starter_code: starterCode,
                instruction: instruction,
                expected_output: expectedOutput,
                hints: hints,
                explanation: scene.description || ('关于 "' + scene.title + '" 的知识点讲解')
            });
        }

        _renderCodeEditorScene(scene, interactiveData) {
            const existing = this.interactiveContainer.querySelector('.scene-code-editor-wrapper');
            if (existing) existing.remove();

            let codeData = interactiveData || scene.code_data || {};

            // If codeData is empty/incomplete, generate default exercise based on scene title/description
            if (!codeData.starter_code && !codeData.code && !codeData.instruction) {
                codeData = this._generateDefaultCodeExercise(scene, codeData);
            }

            const lang = codeData.language || 'python';
            const starterCode = codeData.starter_code || codeData.code || '';
            const instruction = codeData.instruction || scene.description || '';
            const expectedOutput = codeData.expected_output || '';
            const hints = codeData.hints || [];
            const explanation = codeData.explanation || '';
            const hasSlides = scene.slides_v2 && scene.slides_v2.length > 0;
            const title = this.SlideRenderer._stripThinkTags(scene.title || '代码练习');

            const wrapper = document.createElement('div');
            wrapper.className = 'scene-code-editor-wrapper';
            wrapper.innerHTML = `
                <div class="scene-code-header">
                    <h3 class="scene-code-title"><i class="fas fa-code"></i> ${title}</h3>
                    <div class="scene-code-lang-wrap">
                        <select class="scene-code-lang-select" id="scene-code-lang">
                            <option value="python" ${lang === 'python' ? 'selected' : ''}>Python</option>
                            <option value="javascript" ${lang === 'javascript' ? 'selected' : ''}>JavaScript</option>
                            <option value="html" ${lang === 'html' ? 'selected' : ''}>HTML</option>
                        </select>
                    </div>
                </div>
                ${instruction ? `<div class="scene-code-instruction">${this._escapeHtml(instruction)}</div>` : ''}
                ${expectedOutput ? `<div class="scene-code-expected"><div class="expected-label"><i class="fas fa-bullseye"></i> 预期输出</div><pre class="expected-text">${this._escapeHtml(expectedOutput)}</pre></div>` : ''}
                <div class="scene-code-editor-wrap">
                    <textarea class="scene-code-textarea" id="scene-code-input" spellcheck="false" placeholder="// 在此输入代码...">${this._escapeHtml(starterCode)}</textarea>
                </div>
                <div class="scene-code-toolbar">
                    <button class="scene-code-run-btn" id="scene-code-run"><i class="fas fa-play"></i> 运行代码</button>
                    <button class="scene-code-hint-btn" id="scene-code-hint"><i class="fas fa-robot"></i> AI 提示</button>
                    ${hints.length > 0 ? `<button class="scene-code-hint-toggle-btn" id="scene-code-hint-toggle"><i class="fas fa-lightbulb"></i> 查看提示 (${hints.length})</button>` : ''}
                    ${(hasSlides || explanation) ? `<button class="scene-code-explain-btn" id="scene-code-explain"><i class="fas fa-book"></i> 查看讲解</button>` : ''}
                </div>
                <div class="scene-code-hints-panel" id="scene-code-hints-panel" style="display:none;"></div>
                <div class="scene-code-explanation" id="scene-code-explanation" style="display:none;"></div>
                <div class="scene-code-output" id="scene-code-output" style="display:none;"></div>
            `;
            this.interactiveContainer.appendChild(wrapper);
            this._bindCodeEditorSceneEvents(scene, wrapper, interactiveData);
        }

        _bindCodeEditorSceneEvents(scene, wrapper, interactiveData) {
            const runBtn = wrapper.querySelector('#scene-code-run');
            const hintBtn = wrapper.querySelector('#scene-code-hint');
            const hintToggleBtn = wrapper.querySelector('#scene-code-hint-toggle');
            const explainBtn = wrapper.querySelector('#scene-code-explain');
            const textarea = wrapper.querySelector('#scene-code-input');
            const output = wrapper.querySelector('#scene-code-output');
            const hintsPanel = wrapper.querySelector('#scene-code-hints-panel');
            const explanationEl = wrapper.querySelector('#scene-code-explanation');
            const langSelect = wrapper.querySelector('#scene-code-lang');

            const codeData = interactiveData || scene.code_data || {};
            const hints = codeData.hints || [];
            const explanation = codeData.explanation || '';
            let revealedHintIndex = 0;

            if (textarea) {
                textarea.addEventListener('keydown', (e) => {
                    if (e.key === 'Tab') {
                        e.preventDefault();
                        const start = textarea.selectionStart;
                        const end = textarea.selectionEnd;
                        textarea.value = textarea.value.substring(0, start) + '    ' + textarea.value.substring(end);
                        textarea.selectionStart = textarea.selectionEnd = start + 4;
                    }
                });
            }

            if (runBtn) {
                runBtn.addEventListener('click', () => {
                    const code = textarea ? textarea.value : '';
                    const language = langSelect ? langSelect.value : 'python';
                    if (!code.trim()) return;
                    this._runCodeInScene(language, code, output);
                });
            }

            if (hintBtn) {
                hintBtn.addEventListener('click', () => {
                    const code = textarea ? textarea.value : '';
                    const language = langSelect ? langSelect.value : 'python';
                    this._getCodeHintFromAI(scene, code, language, output);
                });
            }

            if (hintToggleBtn && hintsPanel) {
                hintToggleBtn.addEventListener('click', () => {
                    if (hintsPanel.style.display === 'none') {
                        hintsPanel.style.display = 'block';
                        // Reveal next hint on each click
                        if (revealedHintIndex < hints.length) {
                            const hintItem = document.createElement('div');
                            hintItem.className = 'hint-item';
                            hintItem.innerHTML = `<div class="hint-number">提示 ${revealedHintIndex + 1}</div><div class="hint-text">${this._escapeHtml(hints[revealedHintIndex])}</div>`;
                            hintsPanel.appendChild(hintItem);
                            revealedHintIndex++;
                        }
                        if (revealedHintIndex >= hints.length) {
                            hintToggleBtn.innerHTML = '<i class="fas fa-check"></i> 已显示全部提示';
                            hintToggleBtn.disabled = true;
                            hintToggleBtn.style.opacity = '0.6';
                        }
                    }
                });
            }

            if (explainBtn && explanationEl) {
                explainBtn.addEventListener('click', () => {
                    if (explanationEl.style.display === 'none') {
                        explanationEl.style.display = 'block';
                        let contentHtml = '';
                        if (explanation) {
                            contentHtml += `<div class="explanation-section"><div class="explanation-label"><i class="fas fa-book-open"></i> 知识点讲解</div><div class="explanation-text">${this._escapeHtml(explanation).replace(/\n/g, '<br>')}</div></div>`;
                        }
                        if (scene.slides_v2 && scene.slides_v2.length > 0) {
                            contentHtml += `<div class="explanation-section"><div class="explanation-label"><i class="fas fa-slideshare"></i> 概念幻灯片</div><div class="explanation-slides-note">请使用左右箭头切换查看相关概念讲解幻灯片</div></div>`;
                        }
                        explanationEl.innerHTML = contentHtml || '<div class="explanation-text">暂无讲解内容</div>';
                        explainBtn.innerHTML = '<i class="fas fa-eye-slash"></i> 隐藏讲解';
                    } else {
                        explanationEl.style.display = 'none';
                        explainBtn.innerHTML = '<i class="fas fa-book"></i> 查看讲解';
                    }
                });
            }
        }

        async _runCodeInScene(language, code, outputEl) {
            if (!outputEl) return;
            outputEl.style.display = 'block';
            outputEl.innerHTML = '<div class="code-running"><i class="fas fa-spinner fa-spin"></i> 执行中...</div>';

            try {
                if (language === 'javascript') {
                    let result = '';
                    const originalLog = console.log;
                    const logs = [];
                    console.log = (...args) => logs.push(args.join(' '));
                    try {
                        result = eval(code); // eslint-disable-line
                    } catch (e) {
                        result = 'Error: ' + e.message;
                    } finally {
                        console.log = originalLog;
                    }
                    const output = logs.length > 0 ? logs.join('\n') : (result !== undefined ? String(result) : '(无输出)');
                    outputEl.innerHTML = `<div class="output-result"><div class="output-label">输出:</div><pre class="output-text">${this._escapeHtml(output)}</pre></div>`;
                } else if (language === 'html') {
                    outputEl.innerHTML = `<iframe class="html-preview-frame" sandbox="allow-scripts" srcdoc="${this._escapeHtml(code)}"></iframe>`;
                } else {
                    const resp = await fetch('/api/run_code', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code: code, language: 'python' })
                    });
                    const result = await resp.json();
                    if (result.success) {
                        const statusClass = result.passed ? 'success' : 'error';
                        const statusBadge = result.passed
                            ? '<div class="pass-badge"><i class="fas fa-check"></i> 通过</div>'
                            : '<div class="fail-badge"><i class="fas fa-times"></i> 未通过</div>';
                        outputEl.innerHTML = `
                            <div class="output-result ${statusClass}">
                                <div class="output-label">输出:</div>
                                <pre class="output-text">${this._escapeHtml(result.actual_output || '(无输出)')}</pre>
                                ${statusBadge}
                            </div>
                        `;
                    } else {
                        outputEl.innerHTML = `<div class="code-error"><i class="fas fa-exclamation-triangle"></i> 错误: ${this._escapeHtml(result.error || '未知错误')}</div>`;
                    }
                }
            } catch (e) {
                outputEl.innerHTML = `<div class="code-error"><i class="fas fa-exclamation-triangle"></i> 执行失败: ${e.message}</div>`;
            }
        }

        async _getCodeHintFromAI(scene, code, language, outputEl) {
            if (!outputEl) return;
            outputEl.style.display = 'block';
            outputEl.innerHTML = '<div class="code-running"><i class="fas fa-spinner fa-spin"></i> AI 思考中...</div>';

            try {
                const resp = await fetch('/api/v2/course/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: this.courseData.metadata?.student_id || '',
                        course_id: this.courseData.courseId || '',
                        slide_index: this.currentIndex,
                        slide_title: this.SlideRenderer._stripThinkTags(scene.title || ''),
                        user_input: `请给以下${language}代码提供优化建议和提示：\n\`\`\`${language}\n${code}\n\`\`\`\n请简要指出代码中的问题和改进方向。`
                    })
                });
                const data = await resp.json();
                const hint = data.reply || data.message || '暂无提示';
                outputEl.innerHTML = `<div class="ai-hint-box"><div class="ai-hint-label"><i class="fas fa-robot"></i> AI 提示</div><pre class="ai-hint-text">${this._escapeHtml(hint)}</pre></div>`;
            } catch (e) {
                outputEl.innerHTML = `<div class="code-error">获取提示失败: ${e.message}</div>`;
            }
        }

        // ---- Whiteboard ----

        _getWhiteboardRenderer() {
            if (!this.whiteboardRenderer && window.WhiteboardRenderer) {
                this.whiteboardRenderer = new window.WhiteboardRenderer({
                    containerId: 'whiteboard-container',
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

        _animateWhiteboardOpen() {
            if (this.whiteboardContainer) {
                this.whiteboardContainer.style.display = 'flex';
                void this.whiteboardContainer.offsetHeight;
                this.whiteboardContainer.classList.add('wb-active');
                this.whiteboardContainer.classList.remove('wb-exiting');
            }
        }

        _animateWhiteboardClose() {
            if (this.whiteboardContainer) {
                this.whiteboardContainer.classList.add('wb-exiting');
                this.whiteboardContainer.classList.remove('wb-active');
            }
            setTimeout(() => {
                if (!this.whiteboardVisible && this.whiteboardContainer) {
                    this.whiteboardContainer.style.display = 'none';
                    this.whiteboardContainer.classList.remove('wb-exiting');
                }
            }, 320);
        }

        toggleWhiteboard() {
            const wasVisible = this.whiteboardVisible;
            this.whiteboardVisible = !wasVisible;
            this.whiteboardToggleBtn?.classList.toggle('active', this.whiteboardVisible);

            if (this.whiteboardVisible) {
                // Switch to whiteboard view with animation
                this.stopAudio();
                this.hideAllSceneContainers();
                this._animateWhiteboardOpen();
                this._initWhiteboard();
                // Show pen controls for students
                if (this.wbPenGroup) this.wbPenGroup.style.display = 'flex';
                // Slide mode off when using whiteboard (more space available)
                if (this.teacherArea) this.teacherArea.classList.remove('slide-mode');
            } else {
                // Switch back to slide view with exit animation
                this._animateWhiteboardClose();
                const renderer = this._getWhiteboardRenderer();
                if (renderer) {
                    renderer.disablePenMode();
                    renderer.disableEraserMode();
                }
                this.wbPenToggleBtn?.classList.remove('active');
                this.wbEraserBtn?.classList.remove('active');
                if (this.wbPenGroup) this.wbPenGroup.style.display = 'none';
                // Restore slide view after animation
                setTimeout(() => {
                    if (this.slideControls) this.slideControls.style.display = '';
                    if (this.progressBar) this.progressBar.style.display = '';
                    this.renderScene(this.currentIndex);
                }, 320);
            }
        }

        clearWhiteboard() {
            const renderer = this._getWhiteboardRenderer();
            if (renderer) renderer.clear();
        }

        // ---- Whiteboard Theme ----

        _toggleWhiteboardTheme() {
            const stage = this.whiteboardStage;
            if (!stage) return;
            this.wbTheme = this.wbTheme === 'light' ? 'dark' : 'light';
            stage.classList.toggle('wb-dark', this.wbTheme === 'dark');
            // Update renderer background awareness for pen color defaults
            const renderer = this._getWhiteboardRenderer();
            if (renderer) {
                renderer._theme = this.wbTheme;
            }
        }

        // ---- Whiteboard Text Input ----

        _showTextInputModal() {
            const modal = document.getElementById('wb-text-modal');
            if (!modal) return;
            modal.style.display = 'flex';
            const input = document.getElementById('wb-text-input');
            if (input) { input.value = ''; input.focus(); }
        }

        _hideTextModal() {
            const modal = document.getElementById('wb-text-modal');
            if (modal) modal.style.display = 'none';
        }

        _submitTextInput() {
            const input = document.getElementById('wb-text-input');
            const text = input?.value?.trim();
            if (!text) return;
            const size = parseInt(document.getElementById('wb-text-size')?.value, 10) || 20;
            const activeColor = document.querySelector('.wb-text-color.active');
            const color = activeColor?.dataset.color || '#1e293b';
            this._addTextToWhiteboard(text, size, color);
            this._hideTextModal();
        }

        _addTextToWhiteboard(text, fontSize, color) {
            const renderer = this._getWhiteboardRenderer();
            if (!renderer) return;
            // Pick a reasonable position near center with some randomness to avoid stacking
            const x = 300 + Math.random() * 300;
            const y = 200 + Math.random() * 150;
            renderer.drawText({ content: text, x: x, y: y, fontSize: fontSize, color: color });
        }

        // ---- Whiteboard AI Draw Modal ----

        _showAIDrawModal() {
            const modal = document.getElementById('wb-ai-draw-modal');
            if (!modal) return;
            modal.style.display = 'flex';
            const input = document.getElementById('wb-ai-draw-input');
            if (input) { input.value = ''; input.focus(); }
        }

        _hideAIDrawModal() {
            const modal = document.getElementById('wb-ai-draw-modal');
            if (modal) modal.style.display = 'none';
        }

        async _submitAIDraw() {
            const input = document.getElementById('wb-ai-draw-input');
            const description = input?.value?.trim();
            if (!description) return;
            this._hideAIDrawModal();
            await this._executeAIDraw(description);
        }

        async _executeAIDraw(description) {
            const renderer = this._getWhiteboardRenderer();
            if (!renderer) {
                alert('白板渲染器不可用');
                return;
            }

            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'wb-ai-loading';
            loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> AI 正在绘制...';
            loadingDiv.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);padding:12px 20px;background:rgba(15,23,42,0.9);border-radius:8px;color:#818cf8;font-size:14px;z-index:100;pointer-events:none;';
            this.whiteboardContainer.appendChild(loadingDiv);

            try {
                const resp = await fetch('/api/whiteboard/draw', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        description: description.trim(),
                        is_custom_prompt: true
                    })
                });
                const data = await resp.json();
                if (data.success && data.actions) {
                    // Execute actions with smoother sequential animation
                    for (let i = 0; i < data.actions.length; i++) {
                        renderer.execute(data.actions[i]);
                        // Add a small delay between elements for a drawing feel
                        await new Promise(r => setTimeout(r, 180));
                    }
                } else {
                    alert(data.error || 'AI 绘图失败，请重试');
                }
            } catch (e) {
                console.error('AI draw failed:', e);
                alert('AI 绘图请求失败：' + e.message);
            } finally {
                loadingDiv.remove();
            }
        }

        _togglePenMode() {
            const renderer = this._getWhiteboardRenderer();
            if (!renderer) return;
            if (renderer._penEnabled) {
                renderer.disablePenMode();
                this.wbPenToggleBtn?.classList.remove('active');
            } else {
                // Disable eraser when enabling pen
                renderer.disableEraserMode();
                this.wbEraserBtn?.classList.remove('active');
                const activeColor = document.querySelector('.wb-pen-color.active');
                const color = activeColor?.dataset.color || '#ef4444';
                const width = parseInt(this.wbPenWidthInput?.value, 10) || 3;
                renderer.enablePenMode(color, width);
                this.wbPenToggleBtn?.classList.add('active');
            }
        }

        _toggleEraserMode() {
            const renderer = this._getWhiteboardRenderer();
            if (!renderer) return;
            if (renderer._eraserEnabled) {
                renderer.disableEraserMode();
                this.wbEraserBtn?.classList.remove('active');
            } else {
                // Disable pen when enabling eraser
                renderer.disablePenMode();
                this.wbPenToggleBtn?.classList.remove('active');
                renderer.enableEraserMode(20);
                this.wbEraserBtn?.classList.add('active');
            }
        }

        /**
         * Auto-draw whiteboard content based on scene description.
         * Called when a whiteboard-type scene is rendered.
         */
        async _autoDrawWhiteboardContent(description, scene) {
            if (!description) return;
            const renderer = this._getWhiteboardRenderer();
            if (!renderer) {
                console.warn('[Classroom] WhiteboardRenderer not available for auto-draw');
                return;
            }

            // Temporarily disable pen/eraser mode during AI drawing
            const penWasEnabled = renderer._penEnabled;
            const eraserWasEnabled = renderer._eraserEnabled;
            if (penWasEnabled) renderer.disablePenMode();
            if (eraserWasEnabled) renderer.disableEraserMode();
            this.wbPenToggleBtn?.classList.remove('active');
            this.wbEraserBtn?.classList.remove('active');

            // Show loading indicator
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'wb-ai-loading';
            loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> AI 正在绘制课程内容...';
            loadingDiv.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);padding:12px 20px;background:rgba(15,23,42,0.9);border-radius:8px;color:#818cf8;font-size:14px;z-index:100;pointer-events:none;';
            this.whiteboardContainer.appendChild(loadingDiv);

            let actions = null;

            try {
                // Priority 1: use pre-generated actions from scene data (avoids extra API call)
                if (scene.whiteboard_actions && scene.whiteboard_actions.length > 0) {
                    actions = scene.whiteboard_actions;
                    console.log('[Classroom] Using pre-generated whiteboard actions:', actions.length);
                } else {
                    // Priority 2: call backend API to generate actions from description
                    const resp = await fetch('/api/whiteboard/draw', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            description: description.trim(),
                            course_id: this.courseData?.courseId || '',
                            scene_title: this.SlideRenderer._stripThinkTags(scene.title || ''),
                            auto_mode: true
                        })
                    });
                    const data = await resp.json();
                    if (data.success && data.actions && data.actions.length > 0) {
                        actions = data.actions;
                    } else {
                        console.warn('[Classroom] Auto-draw returned no actions:', data.error);
                    }
                }

                if (actions && actions.length > 0) {
                    // Create AI drawing cursor
                    const cursor = document.createElement('div');
                    cursor.className = 'wb-ai-cursor';
                    cursor.innerHTML = '<i class="fas fa-pen-nib"></i>';
                    cursor.style.cssText = 'position:absolute;width:24px;height:24px;display:flex;align-items:center;justify-content:center;color:#6366f1;font-size:14px;pointer-events:none;z-index:50;transition:top 400ms ease-out,left 400ms ease-out;opacity:0;';
                    this.whiteboardContainer.appendChild(cursor);

                    // Execute actions sequentially with small delay for visual effect
                    for (let i = 0; i < actions.length; i++) {
                        const action = actions[i];
                        const params = action.params || {};
                        // Move cursor to approximate target position before drawing
                        let tx = params.x || params.startX || 500;
                        let ty = params.y || params.startY || 300;
                        if (action.type === 'wb_draw_text') { tx = params.x; ty = params.y; }
                        if (action.type === 'wb_draw_shape') { tx = params.x + (params.width || 0) / 2; ty = params.y + (params.height || 0) / 2; }
                        if (action.type === 'wb_draw_line') { tx = (params.startX + params.endX) / 2; ty = (params.startY + params.endY) / 2; }
                        cursor.style.opacity = '1';
                        cursor.style.left = `${tx}px`;
                        cursor.style.top = `${ty}px`;
                        await new Promise(r => setTimeout(r, 350));
                        renderer.execute(action);
                        await new Promise(r => setTimeout(r, 250));
                    }
                    cursor.style.opacity = '0';
                    setTimeout(() => cursor.remove(), 400);
                }
            } catch (e) {
                console.error('[Classroom] Auto-draw failed:', e);
            } finally {
                loadingDiv.remove();
                // Re-enable pen mode if it was active before
                if (penWasEnabled) {
                    const activeColor = document.querySelector('.wb-pen-color.active');
                    const color = activeColor?.dataset.color || '#ef4444';
                    const width = parseInt(this.wbPenWidthInput?.value, 10) || 3;
                    renderer.enablePenMode(color, width);
                    this.wbPenToggleBtn?.classList.add('active');
                }
                // Re-enable eraser mode if it was active before
                if (eraserWasEnabled) {
                    renderer.enableEraserMode(20);
                    this.wbEraserBtn?.classList.add('active');
                }
            }
        }

        /** Execute a whiteboard action (wb_*) from the AI teacher pipeline */
        executeWhiteboardAction(action) {
            const renderer = this._getWhiteboardRenderer();
            if (!renderer) {
                console.warn('[Classroom] WhiteboardRenderer not available');
                return;
            }
            // Normalize to {type, params} format - action can be flat or wrapped
            var name = action.type || action.name || '';
            var params = action.params || {};
            // If params is empty, the action might be flat (from OpenMAICSlidePlayer)
            if (Object.keys(params).length === 0) {
                params = this._mapWbActionParams(action);
            }
            var normalizedAction = { type: name, params: params };

            // Auto-open whiteboard on first draw action
            if (!this.whiteboardVisible && name.startsWith('wb_draw_')) {
                this.whiteboardVisible = true;
                this.whiteboardToggleBtn?.classList.add('active');
                this.stopAudio();
                this.hideAllSceneContainers();
                this._animateWhiteboardOpen();
                this._initWhiteboard();
                // Show pen controls for students
                if (this.wbPenGroup) this.wbPenGroup.style.display = 'flex';
            }
            // Handle wb_close - switch back to slides
            if (name === 'wb_close') {
                this.whiteboardVisible = false;
                this.whiteboardToggleBtn?.classList.remove('active');
                this._animateWhiteboardClose();
                const renderer = this._getWhiteboardRenderer();
                if (renderer) {
                    renderer.disablePenMode();
                    renderer.disableEraserMode();
                }
                this.wbPenToggleBtn?.classList.remove('active');
                this.wbEraserBtn?.classList.remove('active');
                if (this.wbPenGroup) this.wbPenGroup.style.display = 'none';
                setTimeout(() => {
                    if (this.slideControls) this.slideControls.style.display = '';
                    if (this.progressBar) this.progressBar.style.display = '';
                }, 320);
                this.renderScene(this.currentIndex);
                return;
            }
            if (name === 'wb_clear') {
                renderer.clear();
                return;
            }
            if (name === 'wb_delete') {
                renderer.delete(params.elementId);
                return;
            }
            renderer.execute(normalizedAction);
        }

        updateTeacherSpeech(scene) {
            if (!this.speechText) return;
            // narration from slides_v2 content (V2 format)
            const narration = scene.slides_v2?.[0]?.content?.[0]?.narration || '';
            const speech = scene.slide?.speech || scene.quiz?.speech || scene.description || narration;
            const displayText = speech || `现在讲解：${this.SlideRenderer._stripThinkTags(scene.title || '')}`;
            this.speechText.textContent = displayText;
            this.updateTeacherSpeechText(displayText);

            // Update avatar if agent team has different teachers per scene
            const teacherIdx = scene.teacher_index || 0;
            const agent = this.agentTeam[teacherIdx];
            if (agent && this.teacherAvatar && agent.avatar && agent.avatar.startsWith('http')) {
                this.teacherAvatar.innerHTML = `<img src="${agent.avatar}" alt="${agent.name}" class="avatar-img">`;
            }
            // else: keep the default kawaii face
        }

        // ---- Audio / TTS ----

        async playSceneAudio(scene) {
            // 防御: scene 可能为 undefined (例如 scenes 为空时)
            if (!scene) {
                console.warn('[Classroom] playSceneAudio: scene is undefined, skipping');
                this.isPlaying = false;
                const playBtn = document.getElementById('playback-play-btn');
                const playIcon = playBtn?.querySelector('i');
                if (playBtn) {
                    playBtn.classList.remove('playing');
                    playBtn.title = '播放';
                }
                if (playIcon) playIcon.className = 'fas fa-play';
                return;
            }
            this.stopAudio();
            // Activate slide mode when playing slides (compact UI to avoid covering content)
            if (this.teacherArea) this.teacherArea.classList.add('slide-mode');
            // Update play button to pause icon
            const playBtn = document.getElementById('playback-play-btn');
            const playIcon = playBtn?.querySelector('i');
            if (playBtn) {
                playBtn.classList.add('playing');
                playBtn.title = '暂停';
            }
            if (playIcon) playIcon.className = 'fas fa-pause';

            // If OpenMAIC actions are available, use the action pipeline (speech + spotlight + laser)
            if (this._currentOpenMAICActions && this._currentOpenMAICActions.length > 0 && this.openmaicPlayer) {
                console.log('[Classroom] Starting OpenMAIC action pipeline with', this._currentOpenMAICActions.length, 'actions');
                this.speechSync.style.display = 'flex';
                this.openmaicPlayer.start(this._currentOpenMAICActions);
                return;
            }

            // 1. 优先使用课程自带音频
            const builtInUrl = scene.slide?.content?.elements?.find(el => el.audio_url)?.audio_url
                || scene.slide?.content?.elements?.[0]?.audio_url;
            if (builtInUrl && typeof builtInUrl === 'string' && builtInUrl.trim().length > 0 && this.audioPlayer) {
                this._playAudioUrl(builtInUrl, scene);
                return;
            }

            // 2. 检查是否有可 TTS 的文本
            const speechText = this.getSceneSpeechText(scene);
            if (!speechText) {
                // 无音频也无文本，直接结束播放状态
                this.isPlaying = false;
                if (playBtn) {
                    playBtn.classList.remove('playing');
                    playBtn.title = '播放';
                }
                if (playIcon) playIcon.className = 'fas fa-play';
                return;
            }

            // 3. 确保 TTS 音频已缓存（优先用缓存，否则实时生成）
            const cachedUrl = await this._ensureSceneTTSCached(scene);
            // 等待期间用户可能已点击暂停，需检查状态
            if (!this.isPlaying) {
                if (playBtn) {
                    playBtn.classList.remove('playing');
                    playBtn.title = '播放';
                }
                if (playIcon) playIcon.className = 'fas fa-play';
                return;
            }
            if (cachedUrl && this.audioPlayer) {
                this._playAudioUrl(cachedUrl, scene);
            } else {
                // 生成失败，回退到浏览器 TTS
                this.fallbackTTS(scene);
            }
        }

        _playAudioUrl(url, scene) {
            if (!this.audioPlayer) return;
            // 如果用户已暂停，不要开始播放
            if (!this.isPlaying) {
                this.speechSync.style.display = 'none';
                return;
            }
            this.speechSync.style.display = 'flex';
            this.audioPlayer.load();
            this.audioPlayer.src = url;
            this.audioPlayer.play().catch(() => this.fallbackTTS(scene));
            this.audioPlayer.onended = () => {
                this.speechSync.style.display = 'none';
                const playBtn = document.getElementById('playback-play-btn');
                const playIcon = playBtn?.querySelector('i');
                if (playBtn) {
                    playBtn.classList.remove('playing');
                    playBtn.title = '播放';
                }
                if (playIcon) playIcon.className = 'fas fa-play';
                if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                    setTimeout(() => this.nextScene(), 800);
                }
            };
        }

        async _playTTSWithVoice(text) {
            if (!text) return;
            this.stopAudio();
            this.speechSync.style.display = 'flex';
            const voiceId = this.ttsConfig?.voice || TTS_CONFIG.voice;
            const speed = this.ttsConfig?.speed || TTS_CONFIG.speed;
            const result = await this.generateTTS(text, voiceId, speed);
            console.log('[Classroom] _playTTSWithVoice result:', result);
            if (result.success && result.audioUrl && this.audioPlayer) {
                this.audioPlayer.load();
                this.audioPlayer.src = result.audioUrl;
                this.audioPlayer.onloadedmetadata = () => {
                    console.log('[Classroom] audio metadata loaded: duration=', this.audioPlayer.duration);
                };
                this.audioPlayer.onplay = () => {
                    console.log('[Classroom] audio play event fired!');
                };
                this.audioPlayer.onerror = () => {
                    console.error('[Classroom] audio error, falling back to browser TTS:', this.audioPlayer.error);
                    this.fallbackTTS({ slide: { speech: text } });
                };
                this.audioPlayer.onended = () => {
                    this.speechSync.style.display = 'none';
                    const playBtn = document.getElementById('playback-play-btn');
                    const playIcon = playBtn?.querySelector('i');
                    if (playBtn) {
                        playBtn.classList.remove('playing');
                        playBtn.title = '播放';
                    }
                    if (playIcon) playIcon.className = 'fas fa-play';
                    if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                        setTimeout(() => this.nextScene(), 800);
                    }
                };
                this.audioPlayer.play().catch(() => {
                    this.fallbackTTS({ slide: { speech: text } });
                });
            } else {
                this.fallbackTTS({ slide: { speech: text } });
            }
        }

        fallbackTTS(scene) {
            const text = scene.slide?.speech || scene.quiz?.speech || scene.slides_v2?.[0]?.content?.[0]?.narration || '';
            if (!text) return;
            // Use browser SpeechSynthesis since HTMLAudioElement is blocked on this machine
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
                var utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'zh-CN';
                utterance.rate = this.ttsConfig?.speed || TTS_CONFIG.speed;
                utterance.onend = () => {
                    this.speechSync.style.display = 'none';
                    const playBtn = document.getElementById('playback-play-btn');
                    const playIcon = playBtn?.querySelector('i');
                    if (playBtn) {
                        playBtn.classList.remove('playing');
                        playBtn.title = '播放';
                    }
                    if (playIcon) playIcon.className = 'fas fa-play';
                    if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                        setTimeout(() => this.nextScene(), 800);
                    }
                };
                utterance.onerror = () => { this.speechSync.style.display = 'none'; };
                this.speechSynthesisUtterance = utterance;
                window.speechSynthesis.speak(utterance);
            } else {
                this.speechSync.style.display = 'none';
            }
        }

        toggleVoice() {
            this.isPlaying = !this.isPlaying;
            this.voiceBtn?.classList.toggle('playing', this.isPlaying);
            const icon = this.voiceBtn?.querySelector('i');
            if (icon) icon.className = this.isPlaying ? 'fas fa-volume-mute' : 'fas fa-volume-up';

            // Sync prominent play/pause button
            const playBtn = document.getElementById('playback-play-btn');
            const playIcon = playBtn?.querySelector('i');
            if (playBtn) {
                playBtn.classList.toggle('playing', this.isPlaying);
                playBtn.title = this.isPlaying ? '暂停' : '播放';
            }
            if (playIcon) playIcon.className = this.isPlaying ? 'fas fa-pause' : 'fas fa-play';

            if (this.isPlaying) this.playSceneAudio(this.scenes[this.currentIndex]);
            else this.stopAudio();
        }

        stopAudio() {
            if (this.audioPlayer) {
                // Remove event listeners first to prevent fallback TTS from firing when we clear src
                this.audioPlayer.onloadedmetadata = null;
                this.audioPlayer.onplay = null;
                this.audioPlayer.onended = null;
                this.audioPlayer.onerror = null;
                this.audioPlayer.pause();
                // Do NOT set src to empty string — it triggers MEDIA_ERR_SRC_NOT_SUPPORTED
                // (code 4: MEDIA_ELEMENT_ERROR: Empty src attribute). Just pause and clear
                // listeners; the next play call will set a new src.
            }
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            if (this.openmaicPlayer) this.openmaicPlayer.stop({ keepSlide: true });
            if (this.speechSync) this.speechSync.style.display = 'none';
            // Clear spotlight when audio stops
            this.clearSpotlight();
            // Reset pause state
            this.audioPausedBefore = false;
            // Deactivate slide mode when audio stops
            if (this.teacherArea) this.teacherArea.classList.remove('slide-mode');
            // Reset play button state
            const playBtn = document.getElementById('playback-play-btn');
            const playIcon = playBtn?.querySelector('i');
            if (playBtn) {
                playBtn.classList.remove('playing');
                playBtn.title = '播放';
            }
            if (playIcon) playIcon.className = 'fas fa-play';
        }

        replaySpeech() {
            this.isPlaying = true;
            const playBtn = document.getElementById('playback-play-btn');
            const playIcon = playBtn?.querySelector('i');
            if (playBtn) {
                playBtn.classList.add('playing');
                playBtn.title = '暂停';
            }
            if (playIcon) playIcon.className = 'fas fa-pause';
            this.playSceneAudio(this.scenes[this.currentIndex]);
        }
        pauseSpeech() {
            // Pause MiniMax TTS audio
            if (this.audioPlayer && !this.audioPlayer.paused) {
                this.audioPausedBefore = true;
                this.audioPlayer.pause();
            }
            // Cancel browser TTS (Web Speech API doesn't support pause/resume well)
            if (window.speechSynthesis && window.speechSynthesis.speaking) {
                window.speechSynthesis.cancel();
            }
        }

        resumeSpeech() {
            // Resume MiniMax TTS audio if it was playing
            if (this.audioPlayer && this.audioPausedBefore) {
                this.audioPlayer.play().catch(() => {});
                this.audioPausedBefore = false;
            }
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
            console.log('[Classroom] Toggle quiz, found scene:', quizScene);
            console.log('[Classroom] All scenes types:', this.scenes.map(function(s) { return s.type; }));
            if (!quizScene) {
                this.addChatMessage('teacher', '当前课程没有测验环节。');
                return;
            }
            this.openQuizPopup(quizScene);
        }

        openQuizPopup(scene, inlineMode = false) {
            if (!scene || scene.type !== 'quiz') return;
            this.currentQuizScene = scene;
            this.quizPhase = 'not_started';
            this.quizUserAnswers = {};
            this.quizResults = [];
            this._quizInlineMode = inlineMode;

            if (inlineMode) {
                // Inline mode: show as part of slide viewer, no modal overlay
                if (this.quizPopupOverlay) {
                    this.quizPopupOverlay.classList.add('quiz-inline-mode');
                    this.quizPopupOverlay.style.display = 'block';
                }
                // Hide close button in inline mode (user uses nav buttons)
                if (this.quizCloseBtn) this.quizCloseBtn.style.display = 'none';
            } else {
                // Modal popup mode
                if (this.quizPopupOverlay) {
                    this.quizPopupOverlay.classList.remove('quiz-inline-mode');
                    this.quizPopupOverlay.style.display = 'flex';
                }

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
                if (this.quizCloseBtn) this.quizCloseBtn.style.display = 'block';
            }

            // Hide all phase containers
            if (this.quizCover) this.quizCover.style.display = 'flex';
            if (this.quizQuestionsArea) this.quizQuestionsArea.style.display = 'none';
            if (this.quizGrading) this.quizGrading.style.display = 'none';
            if (this.quizReviewArea) this.quizReviewArea.style.display = 'none';
            if (this.quizPopupFooter) this.quizPopupFooter.style.display = 'none';
            if (this.quizSubmitBtn) this.quizSubmitBtn.style.display = 'none';
            if (this.quizRetryBtn) this.quizRetryBtn.style.display = 'none';

            // Render cover
            this._renderQuizCover(scene);

            // Update toggle button state
            if (this.quizToggleBtn) this.quizToggleBtn.classList.add('active');
        }

        _renderQuizCover(scene) {
            var quiz = scene.quiz_data || scene.quiz;
            if (!quiz) {
                if (this.quizCoverTitle) {
                    this.quizCoverTitle.textContent = this.SlideRenderer._stripThinkTags(scene.title || '课堂测验');
                }
                if (this.quizCoverMeta) {
                    this.quizCoverMeta.innerHTML =
                        '<span><i class="fas fa-info-circle"></i> 测验数据尚未生成</span>';
                }
                if (this.quizStartBtn) this.quizStartBtn.style.display = 'none';
                return;
            }
            if (this.quizStartBtn) this.quizStartBtn.style.display = 'flex';

            var questions = quiz.questions || [];
            var totalPoints = questions.reduce(function(sum, q) { return sum + (q.points || 10); }, 0);
            var passing = quiz.passing_score || 60;

            if (this.quizCoverTitle) {
                this.quizCoverTitle.textContent = quiz.title || '课堂测验';
            }
            // Calculate difficulty distribution
            var diffCounts = { basic: 0, medium: 0, advanced: 0 };
            questions.forEach(function(q) {
                var d = q.difficulty || 'medium';
                if (d === 'basic' || d === 'easy') diffCounts.basic++;
                else if (d === 'advanced' || d === 'hard') diffCounts.advanced++;
                else diffCounts.medium++;
            });
            var diffHtml = '';
            if (diffCounts.basic > 0) diffHtml += '<span class="diff-tag diff-basic"><i class="fas fa-seedling"></i> 基础 ' + diffCounts.basic + '</span>';
            if (diffCounts.medium > 0) diffHtml += '<span class="diff-tag diff-medium"><i class="fas fa-bolt"></i> 中等 ' + diffCounts.medium + '</span>';
            if (diffCounts.advanced > 0) diffHtml += '<span class="diff-tag diff-advanced"><i class="fas fa-fire"></i> 挑战 ' + diffCounts.advanced + '</span>';

            if (this.quizCoverMeta) {
                this.quizCoverMeta.innerHTML =
                    '<span><i class="fas fa-question-circle"></i> ' + questions.length + ' 道题</span>' +
                    '<span><i class="fas fa-star"></i> 总分 ' + totalPoints + '</span>' +
                    '<span><i class="fas fa-check-circle"></i> 及格线 ' + passing + '%</span>' +
                    (diffHtml ? '<div style="width:100%;margin-top:0.5rem;display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:center;">' + diffHtml + '</div>' : '');
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
            if (!quiz) {
                console.warn('[Classroom] No quiz data found in scene');
                if (this.quizQuestionsArea) {
                    this.quizQuestionsArea.innerHTML =
                        '<div class="quiz-error">' +
                        '<i class="fas fa-info-circle"></i> ' +
                        '<p>测验数据尚未生成</p>' +
                        '<p class="quiz-error-sub">请关闭后重新进入课堂，或稍后再试</p>' +
                        '</div>';
                }
                if (this.quizPopupFooter) this.quizPopupFooter.style.display = 'none';
                return;
            }
            var questions = quiz.questions || [];
            if (questions.length === 0) {
                console.warn('[Classroom] No questions in quiz');
                if (this.quizQuestionsArea) {
                    this.quizQuestionsArea.innerHTML = '<div class="quiz-error">暂无测验题目</div>';
                }
                return;
            }

            // Sort questions by difficulty: basic → medium → advanced
            var diffOrder = { basic: 0, easy: 0, medium: 1, advanced: 2, hard: 2 };
            var sortedQuestions = questions.slice().sort(function(a, b) {
                var da = diffOrder[a.difficulty || 'medium'] || 1;
                var db = diffOrder[b.difficulty || 'medium'] || 1;
                return da - db;
            });

            // Group by difficulty and render
            var html = '';
            var currentDiff = null;
            var diffLabels = { basic: '基础题', easy: '基础题', medium: '中等题', advanced: '挑战题', hard: '挑战题' };
            var diffClasses = { basic: 'diff-section-basic', easy: 'diff-section-basic', medium: 'diff-section-medium', advanced: 'diff-section-advanced', hard: 'diff-section-advanced' };

            sortedQuestions.forEach(function(q, displayIndex) {
                var d = q.difficulty || 'medium';
                if (d !== currentDiff) {
                    currentDiff = d;
                    var label = diffLabels[d] || '题目';
                    var cls = diffClasses[d] || '';
                    html += '<div class="quiz-diff-section ' + cls + '">' +
                        '<div class="quiz-diff-label"><i class="fas fa-layer-group"></i> ' + label + '</div>' +
                        '</div>';
                }
                // Find original index for answer tracking
                var origIndex = questions.indexOf(q);
                html += self._renderQuestionCard(q, origIndex, displayIndex + 1);
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

        _renderQuestionCard(q, index, displayIndex) {
            var self = this;
            var esc = function(s) {
                if (!s) return '';
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
            };
            var type = q.question_type || 'single';
            var points = q.points || 10;
            var typeLabels = { single: '单选题', multiple: '多选题', short_answer: '简答题' };
            var typeLabel = typeLabels[type] || '单选题';
            var typeClass = type === 'multiple' ? 'tag-multiple' : (type === 'short_answer' ? 'tag-short' : 'tag-single');
            var diffLabels = { basic: '基础', easy: '基础', medium: '中等', advanced: '挑战', hard: '挑战' };
            var diffClass = 'diff-' + (q.difficulty || 'medium');
            var diffLabel = diffLabels[q.difficulty || 'medium'] || '';
            var num = displayIndex !== undefined ? displayIndex : (index + 1);

            var html = '<div class="question-card" id="question-card-' + index + '">';
            html += '<div class="question-card-header">';
            html += '<span class="question-card-num">第 ' + num + ' 题</span>';
            html += '<span class="question-type-tag ' + typeClass + '">' + typeLabel + '</span>';
            if (diffLabel) {
                html += '<span class="question-diff-tag ' + diffClass + '">' + diffLabel + '</span>';
            }
            html += '<span class="question-card-points">' + points + ' 分</span>';
            html += '</div>';
            html += '<div class="question-body">' + esc(q.question) + '</div>';

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
            var esc = function(s) {
                if (!s) return '';
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
            };
            var html = '<div class="question-options">';

            options.forEach(function(opt, oi) {
                html += '<div class="quiz-option' + (isMulti ? ' multi' : '') + '" data-option-index="' + oi + '">';
                html += '<div class="quiz-option-radio' + (isMulti ? ' multi' : '') + '"></div>';
                html += '<span class="quiz-option-text">' + labels[oi] + '. ' + esc(typeof opt === 'string' ? opt : (opt.text || opt.key || '')) + '</span>';
                html += '</div>';
            });

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
                // Normalize options to string array (backend expects list[str])
                var opts = (q.options || []).map(function(opt) {
                    return (opt && typeof opt === 'object') ? (opt.label || opt.text || String(opt)) : String(opt);
                });
                return {
                    question_index: i,
                    question: q.question,
                    question_type: q.question_type || 'single',
                    options: opts,
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
            var esc = function(s) {
                if (!s) return '';
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
            };
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
            html += '<div class="question-body">' + esc(q.question) + '</div>';

            if (type === 'short_answer') {
                // Show user answer + AI feedback
                var userAnswer = '';
                var existing = this.quizUserAnswers[index];
                if (existing) userAnswer = existing.value || '';
                html += '<div class="sa-answer-area">';
                html += '<div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;">你的答案：</div>';
                html += '<div style="font-size:13px;color:var(--text-primary);padding:8px 12px;background:rgba(255,255,255,0.03);border-radius:8px;border:1px solid var(--glass-border);margin-bottom:10px;">' + esc(userAnswer || '(未作答)') + '</div>';
                if (result.feedback) {
                    html += '<div class="sa-feedback-box" id="sa-feedback-' + index + '">';
                    html += '<div class="sa-feedback-label"><i class="fas fa-robot"></i> AI 点评</div>';
                    html += '<div class="sa-feedback-text" id="sa-feedback-text-' + index + '"></div>';
                    html += '<span class="typing-cursor" id="sa-cursor-' + index + '"></span>';
                    html += '</div>';
                }
                if (result.correct_answer) {
                    html += '<div style="font-size:11px;color:var(--text-secondary);margin-top:8px;">参考答案：' + esc(result.correct_answer) + '</div>';
                }
                html += '</div>';
            } else {
                // Show options in review mode
                html += this._renderChoiceOptionsReview(q, index, result, type);
                if (result.feedback) {
                    html += '<div class="choice-feedback-box" id="choice-feedback-' + index + '" style="padding:10px 16px 14px;">';
                    html += '<div class="choice-feedback-label"><i class="fas fa-robot"></i> AI 点评</div>';
                    html += '<div class="choice-feedback-text" id="choice-feedback-text-' + index + '">' + esc(result.feedback) + '</div>';
                    html += '</div>';
                }
            }

            html += '</div>';
            return html;
        }

        _renderChoiceOptionsReview(q, index, result, type) {
            var options = q.options || [];
            var labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            var isMulti = type === 'multiple';
            var userSet = new Set();
            var correctSet = new Set();
            var esc = function(s) {
                if (!s) return '';
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
            };

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
                html += '<span class="quiz-option-text">' + labels[oi] + '. ' + esc(typeof opt === 'string' ? opt : (opt.text || opt.key || '')) + '</span>';
                html += iconHtml;
                html += '</div>';
            });
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
                this.quizPopupOverlay.classList.remove('quiz-inline-mode');
            }

            // Remove dimming (only in modal mode)
            if (!this._quizInlineMode && this.slideViewer) {
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

            // Restore speech if it was playing before (only in modal mode)
            if (!this._quizInlineMode && this._wasSpeakingBeforeQuiz) {
                this._wasSpeakingBeforeQuiz = false;
                this.isPlaying = true;
                this.voiceBtn?.classList.add('playing');
                var vi = this.voiceBtn?.querySelector('i');
                if (vi) vi.className = 'fas fa-volume-mute';
                this.playSceneAudio(this.scenes[this.currentIndex]);
            }
            this._quizInlineMode = false;

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
                    // Short answer — can't grade locally, provide helpful fallback
                    score = Math.round(points * 0.5);
                    feedback = '已收到你的答案。参考答案：' + (q.answer || '暂无') + '。\n\n建议从以下几个方面对照检查自己的答案：\n1. 是否涵盖了题目要求的核心知识点？\n2. 表述是否清晰、逻辑是否连贯？\n3. 是否有具体的例子或论证支撑？\n\n请继续完成其他题目。';
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
                        slide_title: this.SlideRenderer._stripThinkTags(scene.title || ''),
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
                this.addChatMessage('teacher', data.content || '抱歉，暂时无法回答。', data.links || null);
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

        addChatMessage(type, text, links = null) {
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
                // Load user avatar from localStorage
                let userAvatarHtml = `<i class="fas fa-user" style="color:var(--accent-light);"></i>`;
                try {
                    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
                    if (user && user.avatar) {
                        userAvatarHtml = `<img src="${user.avatar}" alt="用户" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                    }
                } catch (e) {}
                avatarHtml = userAvatarHtml;
            }

            let linksHtml = '';
            if (links && links.length > 0 && window.smartLinkRenderer) {
                const linksContainer = document.createElement('div');
                linksContainer.className = 'message-links';
                const rendered = window.smartLinkRenderer.render(links);
                if (rendered) {
                    linksContainer.appendChild(rendered);
                    linksHtml = linksContainer.outerHTML;
                }
            }

            div.innerHTML = `<div class="message-avatar">${avatarHtml}</div><div class="message-bubble"><p>${this.escapeHtml(text)}</p>${linksHtml}</div>`;
            this.chatMessages.appendChild(div);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }

        // ---- Discussion ----

        switchChatTab(tabName) {
            this.currentDiscussionTab = tabName;
            document.querySelectorAll('.chat-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));

            if (tabName === 'qa') {
                document.getElementById('chat-messages').style.display = 'flex';
                document.getElementById('chat-input').closest('.chat-input-area').style.display = 'flex';
                this.discussionArea.style.display = 'none';
            } else {
                document.getElementById('chat-messages').style.display = 'none';
                document.getElementById('chat-input').closest('.chat-input-area').style.display = 'none';
                this.discussionArea.style.display = 'flex';
            }
        }

        async startDiscussion() {
            if (this.discussionActive) return;
            if (!this.courseId) {
                window.starlearnNotifications?.showNotification({
                    title: '无法发起讨论',
                    content: '未找到课程数据，请重新生成课程',
                    type: 'system'
                });
                return;
            }

            const scene = this.scenes[this.currentIndex];
            const slideTopic = scene?.title || '';

            // 优先从 slides_v2 (V2格式) 提取内容，fallback 到旧 slide 格式
            let slideContent = '';
            if (scene?.slides_v2 && scene.slides_v2.length > 0) {
                const slideV2 = scene.slides_v2[0];
                // 收集所有卡片的文字内容
                slideContent = (slideV2.content || [])
                    .map(item => {
                        const texts = [];
                        if (item.sub_title) texts.push(item.sub_title);
                        if (item.text) texts.push(item.text);
                        if (item.bullets && item.bullets.length) texts.push(item.bullets.join('\n'));
                        if (item.code_snippet) texts.push('代码: ' + item.code_snippet);
                        return texts.join('\n');
                    })
                    .join('\n\n');
            } else if (scene?.slide?.content?.elements) {
                slideContent = scene.slide.content.elements.map(e => e.content).join('\n');
            }
            const speechContent = scene?.slide?.speech || scene?.quiz?.speech || '';

            this.discussionActive = true;
            if (this.discussionStartBtn) {
                this.discussionStartBtn.disabled = true;
                this.discussionStartBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 讨论中...';
            }
            this.clearDiscussionMessages();

            try {
                const response = await fetch('/api/v2/course/discussion/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: this.courseData.metadata?.student_id || '',
                        course_id: this.courseId,
                        slide_topic: slideTopic,
                        slide_content: slideContent,
                        speech_content: speechContent,
                        user_message: '',
                        agent_ids: []
                    })
                });

                if (!response.ok) {
                    const errorText = await response.text().catch(() => '');
                    throw new Error(errorText || 'HTTP ' + response.status);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const parts = buffer.split('\n\n');
                    buffer = parts.pop() || '';

                    for (const part of parts) {
                        if (!part.trim()) continue;
                        const lines = part.split('\n');
                        let eventData = '';
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                eventData = line.slice(6);
                            }
                        }
                        if (eventData) {
                            try {
                                const event = JSON.parse(eventData);
                                this.handleDiscussionEvent(event);
                            } catch (e) {
                                console.warn('Failed to parse discussion event', e);
                            }
                        }
                    }
                }
            } catch (e) {
                console.error('Discussion stream error', e);
                window.starlearnNotifications?.showNotification({
                    title: '讨论启动失败',
                    content: '网络请求失败，请稍后重试',
                    type: 'system'
                });
                this.addDiscussionMessage('system', '讨论启动失败，请稍后重试。');
            } finally {
                this.discussionActive = false;
                if (this.discussionStartBtn) {
                    this.discussionStartBtn.disabled = false;
                    this.discussionStartBtn.innerHTML = '<i class="fas fa-plus"></i> 发起讨论';
                }
            }
        }

        handleDiscussionEvent(event) {
            switch (event.type) {
                case 'discussion_start':
                    this.addDiscussionMessage('system', '各位AI同学开始讨论...');
                    break;

                case 'agent_chunk':
                    // 流式发言内容，传递完整event以获取agent_name和agent_color
                    this.appendDiscussionChunk(event.agent_id, event.content, event);
                    break;

                case 'debate_round_complete':
                    this.addDiscussionMessage('system', event.message || '第一轮发言完成');
                    break;

                case 'discussion_complete':
                    if (event.final_answer) {
                        this.showDiscussionSummary(event.final_answer);
                    }
                    break;

                case 'error':
                    this.addDiscussionMessage('system', '讨论出错: ' + event.message);
                    break;
            }
        }

        appendDiscussionChunk(agentId, content, event = {}) {
            let msgEl = document.getElementById(`discussion-msg-${agentId}`);
            if (!msgEl) {
                // 优先从 agentTeam 查找（课程自带的AI团队），找不到则使用 event 中的数据
                const agent = this.agentTeam.find(a => a.id === agentId) || {};
                const agentName = agent.name || event.agent_name || 'AI同学';
                // 颜色优先级：agent.color（课程） > event.agent_color（预设角色） > 默认颜色
                const agentColorRaw = agent.color || event.agent_color || '#6366f1';
                const roleClass = agentId ? `role-${agentId}` : 'role-agent';
                // 解析颜色值，生成气泡样式
                let bubbleStyle = '';
                if (agentColorRaw.startsWith('#')) {
                    // HEX颜色转换
                    const r = parseInt(agentColorRaw.slice(1, 3), 16);
                    const g = parseInt(agentColorRaw.slice(3, 5), 16);
                    const b = parseInt(agentColorRaw.slice(5, 7), 16);
                    bubbleStyle = `background: rgba(${r}, ${g}, ${b}, 0.15); border-color: rgba(${r}, ${g}, ${b}, 0.4);`;
                } else {
                    bubbleStyle = `background: rgba(99, 102, 241, 0.15); border-color: rgba(99, 102, 241, 0.4);`;
                }
                msgEl = document.createElement('div');
                msgEl.className = `discussion-message ${roleClass}`;
                msgEl.id = `discussion-msg-${agentId}`;
                msgEl.innerHTML = `
                    <div class="message-avatar" style="background: ${agentColorRaw}">${agentName?.charAt(0) || 'AI'}</div>
                    <div class="message-content" style="${bubbleStyle}">
                        <div class="message-header">
                            <span class="message-name">${agentName}</span>
                        </div>
                        <div class="message-text"></div>
                    </div>
                `;
                this.discussionMessages?.appendChild(msgEl);
            }
            const textEl = msgEl.querySelector('.message-text');
            if (textEl) {
                // 过滤掉<think>和</think>标签内容
                const cleanContent = content.replace(/<think>[\s\S]*?<\/think>/g, '').replace(/<\/think>/g, '');
                textEl.textContent += cleanContent;
                this.discussionMessages.scrollTop = this.discussionMessages.scrollHeight;
            }
        }

        showDiscussionSummary(summaryText) {
            const summaryEl = document.createElement('div');
            summaryEl.className = 'discussion-summary';
            // 过滤掉 <think> 标签内容
            const cleanText = (summaryText || '').replace(/<think>[\s\S]*?<\/think>/g, '').replace(/<\/think>/g, '');
            const formattedText = this._formatDiscussionText(cleanText);
            summaryEl.innerHTML = `
                <div class="discussion-summary-title"><i class="fas fa-graduation-cap"></i> 讨论总结</div>
                <div class="discussion-summary-text">${formattedText}</div>
            `;
            this.discussionMessages?.appendChild(summaryEl);
            // defer scroll until after layout so scrollHeight includes the new element
            requestAnimationFrame(() => {
                if (this.discussionMessages) {
                    this.discussionMessages.scrollTop = this.discussionMessages.scrollHeight;
                    summaryEl.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }
            });
        }

        _formatDiscussionText(text) {
            if (!text) return '';
            // 转义HTML
            let html = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');

            // 换行 -> <br>
            html = html.replace(/\n+/g, '<br>');

            // 粗体 **text** 或 *text*
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

            // 行内代码 `code`
            html = html.replace(/`(.*?)`/g, '<code>$1</code>');

            // Markdown无序列表 - 行首的 - 或 * 列表项
            html = html.replace(/<br>\s*[-*]\s+(.*?)(?=<br>|$)/g, '<br><span class="list-bullet">•</span> $1');

            // 清理多余br
            html = html.replace(/(<br>)+/g, '<br>');
            html = html.replace(/^<br>/, '');

            return html;
        }

        clearDiscussionMessages() {
            if (this.discussionMessages) {
                this.discussionMessages.innerHTML = '';
            }
        }

        addDiscussionMessage(type, text, agentInfo = null) {
            if (!this.discussionMessages) return;
            // 过滤掉 <think> 标签内容
            const cleanText = (text || '').replace(/<think>[\s\S]*?<\/think>/g, '').replace(/<\/think>/g, '');
            const div = document.createElement('div');
            let roleClass = '';
            if (type === 'user') roleClass = 'user-message';
            else if (type === 'system') roleClass = 'system-message';
            else if (agentInfo?.id) roleClass = `role-${agentInfo.id}`;
            else if (agentInfo?.role) roleClass = `role-${agentInfo.role}`;
            div.className = `discussion-message ${roleClass}`;

            if (type === 'system') {
                div.innerHTML = `
                    <div class="message-content" style="margin-left: 0;">
                        <div class="message-text" style="color: var(--text-tertiary); font-style: italic;">${this.escapeHtml(cleanText)}</div>
                    </div>
                `;
            } else if (type === 'user') {
                div.innerHTML = `
                    <div class="message-avatar"><i class="fas fa-user" style="color: var(--accent-light);"></i></div>
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-name">我</span>
                        </div>
                        <div class="message-text">${this.escapeHtml(cleanText)}</div>
                    </div>
                `;
            } else {
                // 使用 agent.color 作为背景色
                const agentColor = agentInfo?.color || `hsl(${Math.abs((agentInfo?.id || 'ai').split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % 360}, 70%, 50%)`;
                let bubbleStyle = '';
                if (agentColor.startsWith('#')) {
                    const r = parseInt(agentColor.slice(1, 3), 16);
                    const g = parseInt(agentColor.slice(3, 5), 16);
                    const b = parseInt(agentColor.slice(5, 7), 16);
                    bubbleStyle = `background: rgba(${r}, ${g}, ${b}, 0.15); border-color: rgba(${r}, ${g}, ${b}, 0.4);`;
                }
                div.innerHTML = `
                    <div class="message-avatar" style="background: ${agentColor}">${agentInfo?.name?.charAt(0) || 'AI'}</div>
                    <div class="message-content" style="${bubbleStyle}">
                        <div class="message-header">
                            <span class="message-name">${agentInfo?.name || 'AI同学'}</span>
                        </div>
                        <div class="message-text">${this.escapeHtml(cleanText)}</div>
                    </div>
                `;
            }

            this.discussionMessages.appendChild(div);
            this.discussionMessages.scrollTop = this.discussionMessages.scrollHeight;
        }

        // ---- Navigation ----

        goToScene(index) { this.renderScene(index); }
        prevScene() { if (this.currentIndex > 0) this.renderScene(this.currentIndex - 1); }
        nextScene() { if (this.currentIndex < this.scenes.length - 1) this.renderScene(this.currentIndex + 1); }

        updateNav() {
            const total = this.scenes.length;
            if (this.currentSlideEl) {
                const newSlideNum = this.currentIndex + 1;
                if (this.currentSlideEl.textContent != newSlideNum) {
                    this.currentSlideEl.textContent = newSlideNum;
                    this.currentSlideEl.classList.remove('changed');
                    void this.currentSlideEl.offsetWidth; // trigger reflow
                    this.currentSlideEl.classList.add('changed');
                }
            }
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

        // ---- Settings ----

        showSettingsModal() {
            const modal = document.getElementById('settings-modal');
            if (!modal) return;
            // Load current settings into form
            const voiceSelect = document.getElementById('settings-voice-select');
            const speedSelect = document.getElementById('settings-speed-select');
            const autoplayToggle = document.getElementById('settings-autoplay');
            const progressToggle = document.getElementById('settings-show-progress');
            const slideNumToggle = document.getElementById('settings-show-slide-num');
            const notifToggle = document.getElementById('settings-notifications');

            if (voiceSelect) voiceSelect.value = this.settings?.voice || 'female-yujie';
            if (speedSelect) speedSelect.value = this.settings?.speed || '1.0';
            if (autoplayToggle) autoplayToggle.checked = this.settings?.autoplay !== false;
            if (progressToggle) progressToggle.checked = this.settings?.showProgress !== false;
            if (slideNumToggle) slideNumToggle.checked = this.settings?.showSlideNum !== false;
            if (notifToggle) notifToggle.checked = this.settings?.notifications !== false;

            modal.style.display = 'flex';
        }

        hideSettingsModal() {
            const el = document.getElementById('settings-modal');
            if (el) el.style.display = 'none';
        }

        saveSettings() {
            const voiceSelect = document.getElementById('settings-voice-select');
            const speedSelect = document.getElementById('settings-speed-select');
            const autoplayToggle = document.getElementById('settings-autoplay');
            const progressToggle = document.getElementById('settings-show-progress');
            const slideNumToggle = document.getElementById('settings-show-slide-num');
            const notifToggle = document.getElementById('settings-notifications');

            this.settings = {
                voice: voiceSelect?.value || 'female-yujie',
                speed: speedSelect?.value || '1.0',
                autoplay: autoplayToggle?.checked ?? true,
                showProgress: progressToggle?.checked ?? true,
                showSlideNum: slideNumToggle?.checked ?? true,
                notifications: notifToggle?.checked ?? true
            };

            // Apply settings
            if (this.settings.voice) this.setVoice(this.settings.voice);
            if (this.settings.speed) this.setSpeed(parseFloat(this.settings.speed));

            const progressBar = document.querySelector('.progress-bar');
            if (progressBar) progressBar.style.display = this.settings.showProgress ? 'block' : 'none';

            const slideControls = document.querySelector('.slide-controls');
            const slideIndicator = document.querySelector('.slide-indicator');
            if (slideIndicator) slideIndicator.style.display = this.settings.showSlideNum ? 'flex' : 'none';

            // Save to localStorage
            localStorage.setItem('classroom-settings', JSON.stringify(this.settings));

            this.hideSettingsModal();
            this.showNotification('设置已保存', 'success');
        }

        loadSettings() {
            try {
                const saved = localStorage.getItem('classroom-settings');
                if (saved) {
                    this.settings = JSON.parse(saved);
                    // Apply loaded settings
                    if (this.settings.voice) this.setVoice(this.settings.voice);
                    if (this.settings.speed) this.setSpeed(parseFloat(this.settings.speed));

                    const progressBar = document.querySelector('.progress-bar');
                    if (progressBar) progressBar.style.display = this.settings.showProgress !== false ? 'block' : 'none';

                    const slideIndicator = document.querySelector('.slide-indicator');
                    if (slideIndicator) slideIndicator.style.display = this.settings.showSlideNum !== false ? 'flex' : 'none';
                }
            } catch (e) {
                console.warn('Failed to load settings:', e);
            }
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
            const voiceSelect = document.getElementById('voice-select');
            if (!voiceSelect) return;

            // Load saved voice preference
            const saved = localStorage.getItem('classroom_voice');
            if (saved && MINIMAX_VOICES[saved]) {
                TTS_CONFIG.voice = saved;
                voiceSelect.value = saved;
            }

            voiceSelect.addEventListener('change', (e) => {
                TTS_CONFIG.voice = e.target.value;
                this.saveVoicePreference(e.target.value);
            });
        }

        saveVoicePreference(voiceId) {
            localStorage.setItem('classroom_voice', voiceId);
        }

        loadVoicePreference() {
            const saved = localStorage.getItem('classroom_voice');
            if (saved && MINIMAX_VOICES[saved]) {
                TTS_CONFIG.voice = saved;
                // Sync header select
                const headerSelect = document.getElementById('header-voice-select');
                if (headerSelect) headerSelect.value = saved;
                // Sync custom dropdown
                const dropdownValue = document.getElementById('voice-dropdown-value');
                const dropdownItems = document.querySelectorAll('.voice-dropdown-item');
                if (dropdownValue) {
                    const item = document.querySelector(`.voice-dropdown-item[data-value="${saved}"]`);
                    if (item) dropdownValue.textContent = item.textContent;
                }
                dropdownItems.forEach(i => {
                    i.classList.toggle('selected', i.dataset.value === saved);
                });
            }
        }

        setVoice(voiceId) {
            if (MINIMAX_VOICES[voiceId]) {
                TTS_CONFIG.voice = voiceId;
                this.saveVoicePreference(voiceId);
                // Sync header voice select if exists
                const headerSelect = document.getElementById('header-voice-select');
                if (headerSelect) headerSelect.value = voiceId;
                // Sync custom dropdown
                const dropdownValue = document.getElementById('voice-dropdown-value');
                const dropdownItems = document.querySelectorAll('.voice-dropdown-item');
                if (dropdownValue) {
                    const item = document.querySelector(`.voice-dropdown-item[data-value="${voiceId}"]`);
                    if (item) dropdownValue.textContent = item.textContent;
                }
                dropdownItems.forEach(i => {
                    i.classList.toggle('selected', i.dataset.value === voiceId);
                });
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
