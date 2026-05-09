/**
 * Generation Preview Page JavaScript
 * OpenMAIC Style - Clean glass-morphism UI
 */

(function() {
    'use strict';

    // Step definitions (7 steps)
    const STEPS = [
        { id: 'pdf-analysis', title: '正在分析需求...', desc: '解析学习需求与内容' },
        { id: 'requirement-analysis', title: '正在分析学习需求...', desc: '解析目标、难度与受众' },
        { id: 'web-search', title: '正在搜索资料...', desc: '获取相关学习资源' },
        { id: 'outline', title: '正在生成课程大纲...', desc: 'AI设计课程结构' },
        { id: 'agent-generation', title: '正在配置AI教师...', desc: '教师团队准备中' },
        { id: 'slide-content', title: '正在生成课程内容...', desc: '制作幻灯片与练习' },
        { id: 'actions', title: '正在收尾...', desc: '生成配图与语音讲解' }
    ];

    // State
    let currentStep = 0;
    let abortController = null;
    let sessionData = null;
    let courseData = null;
    let isError = false;
    let actionInterval = null;

    // DOM Elements
    const backBtn = document.getElementById('back-btn');
    const abortBtn = document.getElementById('abort-btn');
    const progressDots = document.getElementById('progress-dots');
    const statusTitle = document.getElementById('status-title');
    const statusDesc = document.getElementById('status-desc');
    const warningBadge = document.getElementById('warning-badge');
    const warningText = document.getElementById('warning-text');
    const outlineListPreview = document.getElementById('outline-list-preview');
    const footerHint = document.getElementById('footer-hint');
    const retryBtn = document.getElementById('retry-btn');
    const visualizerContainer = document.getElementById('visualizer-container');
    const featureCardsContainer = document.getElementById('feature-cards');

    // Viz containers
    const vizContainers = {
        'error': document.getElementById('viz-error'),
        'complete': document.getElementById('viz-complete'),
        'pdf-analysis': document.getElementById('viz-pdf'),
        'requirement-analysis': document.getElementById('viz-requirement-analysis'),
        'web-search': document.getElementById('viz-search'),
        'outline': document.getElementById('viz-outline'),
        'agent-generation': document.getElementById('viz-ai'),
        'slide-content': document.getElementById('viz-content'),
        'actions': document.getElementById('viz-actions')
    };

    // Feature card state
    const featureState = {
        image: { active: false, done: false },
        tts: { active: false, done: false },
        video: { active: false, done: false },
        websearch: { active: false, done: false },
        interactive: { active: false, done: false }
    };

    // Feature card definitions
    const FEATURE_DEFS = [
        {
            key: 'websearch',
            label: '网络搜索',
            icon: 'fa-search',
            cssClass: 'search-card',
            stepId: 'web-search'
        },
        {
            key: 'image',
            label: '生成图片',
            icon: 'fa-image',
            cssClass: 'image-card',
            stepId: 'actions'
        },
        {
            key: 'tts',
            label: '语音讲解',
            icon: 'fa-microphone',
            cssClass: 'tts-card',
            stepId: 'actions'
        },
        {
            key: 'video',
            label: '生成视频',
            icon: 'fa-video',
            cssClass: 'video-card',
            stepId: 'actions'
        },
        {
            key: 'interactive',
            label: '深度交互',
            icon: 'fa-bolt',
            cssClass: 'interactive-card',
            stepId: 'agent-generation'
        }
    ];

    // Search elements
    const searchResults = document.getElementById('search-results');
    const sourceBadge = document.getElementById('source-badge');
    const sourceCount = document.getElementById('source-count');

    // Action items
    const actionItems = document.querySelectorAll('.action-item');

    function init() {
        loadSession();
        setupEventListeners();
        if (sessionData) {
            displayAssignedTeacher();
            startGeneration();
        } else {
            showError('未找到生成会话，请返回首页重试');
            backBtn.style.display = 'flex';
        }
    }

    // 显示分配的AI教师
    function displayAssignedTeacher() {
        const display = document.getElementById('teacher-assign-display');
        if (!display || !sessionData) return;

        const teacherName = sessionData.requirements?.teacher_name;
        const teacherIcon = sessionData.requirements?.teacher_icon;
        const teacherProfession = sessionData.requirements?.teacher_profession;
        const teacherPersonality = sessionData.requirements?.teacher_personality;
        const teacherStyle = sessionData.requirements?.teacher_teaching_style;

        if (!teacherName) return;

        display.style.display = 'block';

        display.querySelector('.teacher-assign-icon').textContent = teacherIcon || '👨‍🏫';
        display.querySelector('.teacher-assign-name').textContent = teacherName;
        display.querySelector('.teacher-assign-profession').textContent = teacherProfession;
        display.querySelector('.teacher-personality').textContent = teacherPersonality;
        display.querySelector('.teacher-style').textContent = teacherStyle;

        const agentMode = sessionData.requirements?.agent_mode;
        const matchReason = display.querySelector('.teacher-match-reason');
        if (agentMode === 'auto') {
            matchReason.textContent = '根据课程内容自动分配';
        } else {
            matchReason.textContent = '手动选择';
        }
    }

    function loadSession() {
        const saved = sessionStorage.getItem('generationSession');
        if (saved) {
            try {
                sessionData = JSON.parse(saved);
            } catch (e) {
                console.error('Failed to parse session:', e);
            }
        }
    }

    function setupEventListeners() {
        backBtn?.addEventListener('click', goBack);
        abortBtn?.addEventListener('click', abortGeneration);

        retryBtn?.addEventListener('click', () => {
            retryBtn.style.display = 'none';
            isError = false;
            startGeneration();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Close any modals if needed
            }
        });
    }

    function goBack() {
        if (abortController) abortController.abort();
        sessionStorage.removeItem('generationSession');
        window.location.href = '/index.html';
    }

    function abortGeneration() {
        if (abortController) {
            abortController.abort();
            showError('生成已取消');
            abortBtn.style.display = 'none';
            if (footerHint) footerHint.style.display = 'none';
        }
    }

    // ---- SSE Stream handling ----

    async function startGeneration() {
        // Reset state
        isError = false;
        currentStep = 0;

        // Hide all visualizers first
        Object.values(vizContainers).forEach(viz => {
            if (viz) {
                viz.style.display = 'none';
                viz.classList.remove('active');
            }
        });

        // Show first visualizer
        if (vizContainers['pdf-analysis']) {
            vizContainers['pdf-analysis'].style.display = 'flex';
            vizContainers['pdf-analysis'].classList.add('active');
        }

        // Reset progress dots
        const dots = progressDots.querySelectorAll('.dot');
        dots.forEach((dot, i) => {
            dot.classList.remove('active', 'completed');
            if (i === 0) dot.classList.add('active');
        });

        // Reset status
        statusTitle.textContent = STEPS[0].title;
        statusDesc.textContent = STEPS[0].desc;
        abortBtn.style.display = 'flex';
        abortBtn.classList.add('visible');
        if (footerHint) footerHint.style.display = 'flex';
        if (retryBtn) retryBtn.style.display = 'none';

        // Initialize feature cards based on enabled features
        initFeatureCards();

        abortController = new AbortController();

        const reqs = sessionData.requirements || sessionData || {};
        const hasPdfContent = !!(reqs.enable_pdf_upload && reqs.pdf_text);

        // 如果有PDF内容，更新第一步描述
        if (hasPdfContent) {
            STEPS[0].title = '正在解析文档...';
            STEPS[0].desc = '基于PDF参考文档构建课程';
        } else {
            STEPS[0].title = '正在分析需求...';
            STEPS[0].desc = '解析学习需求与内容';
        }

        const body = {
            requirement: reqs.requirement || '',
            student_id: String(sessionData.student_id || reqs.student_id || ''),
            enable_image: reqs.enable_image || false,
            enable_tts: reqs.enable_tts !== false,
            enable_video: reqs.enable_video || false,
            voice_id: reqs.voice_id || 'female-shaonv',
            agent_mode: reqs.agent_mode || 'preset',
            interactive_mode: reqs.interactive_mode || false,
            enable_web_search: reqs.enable_web_search !== false,
            enable_pdf_upload: reqs.enable_pdf_upload ?? false,
            pdf_text: reqs.pdf_text || '',
        };

        try {
            const response = await fetch('/api/v2/course/generate/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: abortController.signal,
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`服务器错误: ${response.status} - ${errText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const result = parseSSEBuffer(buffer);
                buffer = result.remainder;

                for (const event of result.parsed) {
                    handleSSEMessage(event);
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.warn('SSE连接失败:', error);
            showError('连接失败，请检查网络后重试');
        }
    }

    function parseSSEBuffer(buffer) {
        const parsed = [];
        let remainder = buffer;
        const parts = buffer.split('\n\n');

        if (parts.length > 1) {
            remainder = parts.pop();

            for (const part of parts) {
                const lines = part.split('\n');
                let eventType = 'message';
                let dataStr = '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        dataStr = line.slice(6).trim();
                    }
                }

                if (dataStr) {
                    try {
                        parsed.push({
                            type: eventType,
                            data: dataStr,
                            parsed: JSON.parse(dataStr)
                        });
                    } catch (e) {
                        console.warn('Failed to parse SSE data:', e);
                    }
                }
            }
        }

        return { parsed, remainder };
    }

    // ---- Step visualization ----

    function updateStep(index, step) {
        if (isError) return;

        currentStep = index;

        // Update progress dots
        const dots = progressDots.querySelectorAll('.dot');
        dots.forEach((dot, i) => {
            dot.classList.remove('active', 'completed');
            if (i < index) dot.classList.add('completed');
            else if (i === index) dot.classList.add('active');
        });

        // Update status
        statusTitle.textContent = step.title;
        statusDesc.textContent = step.desc;

        // Switch active visualizer
        Object.entries(vizContainers).forEach(([id, viz]) => {
            if (viz) {
                viz.style.display = id === step.id ? 'flex' : 'none';
                viz.classList.toggle('active', id === step.id);
            }
        });

        // Start action animation if on actions step
        if (step.id === 'actions') {
            startActionAnimation();
        } else {
            stopActionAnimation();
        }
    }

    function startActionAnimation() {
        if (actionInterval) return;
        let activeIndex = 0;
        actionItems.forEach((item, i) => {
            item.classList.toggle('active', i === 0);
        });
        actionInterval = setInterval(() => {
            actionItems.forEach((item, i) => {
                item.classList.toggle('active', i === activeIndex);
            });
            activeIndex = (activeIndex + 1) % actionItems.length;
        }, 1600);
    }

    function stopActionAnimation() {
        if (actionInterval) {
            clearInterval(actionInterval);
            actionInterval = null;
        }
        actionItems.forEach(item => item.classList.remove('active'));
    }

    // ---- Feature Cards ----

    function initFeatureCards() {
        if (!featureCardsContainer) return;

        const reqs = sessionData.requirements || sessionData || {};
        const enabledFeatures = [];

        if (reqs.enable_web_search) enabledFeatures.push('websearch');
        if (reqs.enable_image) enabledFeatures.push('image');
        if (reqs.enable_tts !== false) enabledFeatures.push('tts');
        if (reqs.enable_video) enabledFeatures.push('video');
        if (reqs.interactive_mode) enabledFeatures.push('interactive');

        if (enabledFeatures.length === 0) {
            featureCardsContainer.style.display = 'none';
            return;
        }

        featureCardsContainer.innerHTML = '';
        featureCardsContainer.style.display = 'flex';

        enabledFeatures.forEach((key, i) => {
            const def = FEATURE_DEFS.find(d => d.key === key);
            if (!def) return;

            featureState[key] = { active: false, done: false };

            const card = document.createElement('div');
            card.className = `feature-card ${def.cssClass} waiting`;
            card.id = `feature-card-${key}`;
            card.style.animationDelay = `${i * 0.1}s`;
            card.innerHTML = `
                <i class="fas ${def.icon} feature-icon"></i>
                <span class="feature-text">${def.label}</span>
            `;
            featureCardsContainer.appendChild(card);
        });

        requestAnimationFrame(() => {
            featureCardsContainer.classList.add('visible');
        });
    }

    function activateFeatureCard(key) {
        const card = document.getElementById(`feature-card-${key}`);
        if (!card || featureState[key].done) return;

        // Deactivate all first
        Object.keys(featureState).forEach(k => {
            const c = document.getElementById(`feature-card-${k}`);
            if (c && !featureState[k].done) {
                c.classList.remove('active');
            }
        });

        featureState[key].active = true;
        featureState[key].done = true;

        card.classList.remove('waiting');
        card.classList.add('active');

        // Mark done after a brief active period
        setTimeout(() => {
            card.classList.add('done');
            const icon = card.querySelector('.feature-icon');
            if (icon) {
                icon.className = `fas ${FEATURE_DEFS.find(d => d.key === key).icon} feature-icon`;
            }
        }, 1500);
    }

    function hideFeatureCards() {
        if (!featureCardsContainer) return;
        featureCardsContainer.classList.remove('visible');
        setTimeout(() => {
            if (featureCardsContainer) featureCardsContainer.style.display = 'none';
        }, 400);
    }

    function showError(message) {
        isError = true;
        stopActionAnimation();
        hideFeatureCards();

        // Hide all visualizers
        Object.values(vizContainers).forEach(viz => {
            if (viz) {
                viz.style.display = 'none';
                viz.classList.remove('active');
            }
        });

        // Show error visualizer
        if (vizContainers['error']) {
            vizContainers['error'].style.display = 'flex';
            vizContainers['error'].classList.add('active');
        }

        // Update status
        statusTitle.textContent = '生成失败';
        statusDesc.textContent = message;

        // Hide abort, show retry
        abortBtn.style.display = 'none';
        if (footerHint) footerHint.style.display = 'none';
        if (retryBtn) {
            retryBtn.style.display = 'flex';
            retryBtn.classList.add('visible');
        }
    }

    function showComplete() {
        stopActionAnimation();
        hideFeatureCards();

        // Hide all visualizers
        Object.values(vizContainers).forEach(viz => {
            if (viz) {
                viz.style.display = 'none';
                viz.classList.remove('active');
            }
        });

        // Show complete visualizer
        if (vizContainers['complete']) {
            vizContainers['complete'].style.display = 'flex';
            vizContainers['complete'].classList.add('active');
        }

        statusTitle.textContent = '课程生成完成！';
        statusDesc.textContent = '即将进入课堂...';

        abortBtn.style.display = 'none';
        if (footerHint) footerHint.style.display = 'none';
    }

    function showWarning(text) {
        if (warningBadge && warningText) {
            warningText.textContent = text;
            warningBadge.classList.add('visible');
            warningBadge.style.display = 'flex';
        }
    }

    function updateProgress(percent) {
        console.log('Progress:', percent + '%');
    }

    // ---- Search results update ----

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/[&<>"']/g, function(m) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m];
        });
    }

    function formatRequirementAnalysis(data) {
        const parts = [];
        const difficultyMap = { 'basic': '基础', 'medium': '进阶', 'advanced': '高级' };
        if (data.difficulty) {
            parts.push(`难度: ${difficultyMap[data.difficulty] || data.difficulty}`);
        }
        if (data.target_audience) {
            parts.push(`受众: ${data.target_audience}`);
        }
        if (data.estimated_duration) {
            parts.push(`时长: ${data.estimated_duration}`);
        }
        if (data.learning_goals && data.learning_goals.length > 0) {
            parts.push(`目标: ${data.learning_goals.slice(0, 2).join('、')}`);
        }
        if (data.suggested_scene_types && data.suggested_scene_types.length > 0) {
            const typeMap = { 'slide': '幻灯片', 'quiz': '测验', 'exercise': '练习', 'interactive': '交互', 'code': '代码', 'video': '视频', 'pbl': '项目' };
            parts.push(`场景: ${data.suggested_scene_types.map(t => typeMap[t] || t).join('、')}`);
        }
        return parts.join(' | ') || '正在解析学习需求...';
    }

    function updateSearchSources(sources) {
        if (!searchResults) return;

        searchResults.innerHTML = sources.slice(0, 4).map((source, i) => {
            const title = source.title || source.query || '搜索结果';
            const url = source.url || '';
            const domain = url ? url.replace(/^https?:\/\//, '').split('/')[0] : '';
            return `
                <div class="search-result-item">
                    <div class="result-title-text">${escapeHtml(title)}</div>
                    ${domain ? `<div class="result-url-text">${escapeHtml(domain)}</div>` : ''}
                </div>
            `;
        }).join('');

        if (sourceBadge && sourceCount) {
            sourceBadge.style.display = 'flex';
            sourceCount.textContent = sources.length;
        }
    }

    // ---- Outline streaming ----

    function addOutlineItem(outline) {
        if (!outlineListPreview) return;

        // Check if showing placeholder
        const placeholder = outlineListPreview.querySelector('.outline-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        const div = document.createElement('div');
        div.className = 'outline-item';
        const badgeType = outline.type || 'slide';
        const typeIcons = {
            'slide': '📖', 'quiz': '📝', 'exercise': '✏️',
            'interactive': '🎮', 'pbl': '🔬', 'code': '💻', 'video': '🎬'
        };
        div.innerHTML = `
            <div class="outline-bullet"></div>
            <span class="outline-text-main">${typeIcons[badgeType] || '📖'} ${outline.title || '新章节'}</span>
        `;
        outlineListPreview.appendChild(div);
    }

    // ---- SSE message handler ----

    function handleSSEMessage(event) {
        try {
            const raw = event.parsed || {};
            const eventType = raw.type || event.type;
            const msg = raw.data || {};
            const rootData = raw;

            switch (eventType) {
                case 'status':
                    if (msg.msg) statusDesc.textContent = msg.msg;
                    if (rootData.progress) updateProgress(rootData.progress);
                    break;

                case 'pdf_analysis':
                    updateStep(0, STEPS[0]);
                    break;

                case 'requirement_analysis':
                    updateStep(1, STEPS[1]);
                    if (msg.learning_goals || msg.difficulty || msg.target_audience) {
                        statusDesc.textContent = formatRequirementAnalysis(msg);
                    }
                    break;

                case 'web_search':
                    updateStep(2, STEPS[2]);
                    activateFeatureCard('websearch');
                    if (msg.sources_count !== undefined) {
                        statusDesc.textContent = `已找到 ${msg.sources_count} 条相关资料`;
                    }
                    if (msg.sources && msg.sources.length > 0) {
                        updateSearchSources(msg.sources);
                    }
                    break;

                case 'outline':
                    updateStep(3, STEPS[3]);
                    if (msg.title) addOutlineItem(msg);
                    break;

                case 'outline_progress':
                    if (rootData.progress) updateProgress(rootData.progress);
                    break;

                case 'agent_generation':
                    updateStep(4, STEPS[4]);
                    activateFeatureCard('interactive');
                    const agents = msg.agents || [];
                    if (agents.length > 0) {
                        statusDesc.textContent = `已生成 ${agents.length} 位AI教师`;
                    }
                    break;

                case 'progressive_batch':
                    // Always save quiz/exercise data, even when slides are empty (quiz scenes have no slides)
                    if (msg.quiz_data && msg.quiz_data.length > 0) {
                        sessionStorage.setItem('progressiveQuizData', JSON.stringify(msg.quiz_data));
                    }
                    if (msg.exercise_data && msg.exercise_data.length > 0) {
                        sessionStorage.setItem('progressiveExerciseData', JSON.stringify(msg.exercise_data));
                    }
                    if (msg.slides) {
                        sessionStorage.setItem('progressiveSlides', JSON.stringify(msg.slides));
                    }
                    if (msg.slides_v2 && msg.slides_v2.length > 0) {
                        sessionStorage.setItem('progressiveSlidesV2', JSON.stringify(msg.slides_v2));
                    }
                    if (msg.code_data && msg.code_data.length > 0) {
                        sessionStorage.setItem('progressiveCodeData', JSON.stringify(msg.code_data));
                    }
                    break;

                case 'first_batch_complete':
                    console.log('[generation-preview] first_batch_complete received:', {
                        session_id: msg.session_id,
                        slides_count: (msg.slides || []).length,
                        slides_v2_count: (msg.slides_v2 || []).length,
                        quiz_count: (msg.quiz_data || []).length,
                        exercise_count: (msg.exercise_data || []).length,
                        code_count: (msg.code_data || []).length,
                        outlines_count: (msg.outlines || []).length,
                    });
                    statusTitle.textContent = '首批内容已生成';
                    statusDesc.textContent = '即将进入课堂...';
                    // 隐藏abort按钮
                    if (abortBtn) abortBtn.style.display = 'none';
                    if (footerHint) footerHint.style.display = 'none';

                    // 构建初步的 classroomData 用于课堂初始化
                    const reqs = sessionData.requirements || sessionData || {};
                    if (msg.session_id) {
                        const initialCourseData = {
                            courseId: msg.session_id,
                            title: msg.course_title || '课程',
                            outlines: msg.outlines || [],
                            slides: msg.slides || [],
                            slides_v2: msg.slides_v2 || [],
                            agent_team: msg.agent_team || [],
                            quiz_data: msg.quiz_data || [],
                            exercise_data: msg.exercise_data || [],
                            code_data: msg.code_data || [],
                            teacher: {
                                name: '星识教师',
                                avatar: '',
                                role: '课程导师',
                                voice_id: 0
                            },
                            tts_audio_urls: {},
                            metadata: {
                                session_id: msg.session_id,
                                requirement: reqs.requirement || '',
                                student_id: String(sessionData.student_id || ''),
                                voice_id: reqs.voice_id || 'female-shaonv',
                                agent_mode: reqs.agent_mode || 'preset',
                                interactive_mode: reqs.interactive_mode || false,
                            }
                        };
                        sessionStorage.setItem('classroomData', JSON.stringify(initialCourseData));
                        sessionStorage.setItem('courseId', msg.session_id);
                    }

                    // 保存渐进式数据（用于 classroom 页面合并）
                    if (msg.slides && msg.slides.length > 0) {
                        sessionStorage.setItem('progressiveSlides', JSON.stringify(msg.slides));
                    }
                    if (msg.slides_v2 && msg.slides_v2.length > 0) {
                        sessionStorage.setItem('progressiveSlidesV2', JSON.stringify(msg.slides_v2));
                    }
                    if (msg.quiz_data && msg.quiz_data.length > 0) {
                        sessionStorage.setItem('progressiveQuizData', JSON.stringify(msg.quiz_data));
                    }
                    if (msg.exercise_data && msg.exercise_data.length > 0) {
                        sessionStorage.setItem('progressiveExerciseData', JSON.stringify(msg.exercise_data));
                    }
                    if (msg.code_data && msg.code_data.length > 0) {
                        sessionStorage.setItem('progressiveCodeData', JSON.stringify(msg.code_data));
                    }

                    // 1秒后跳转到课堂
                    setTimeout(() => {
                        console.log('[generation-preview] Navigating to classroom...');
                        navigateToClassroom();
                    }, 1000);
                    break;

                case 'slide_content':
                    updateStep(5, STEPS[5]);
                    if (msg.speech_preview) {
                        statusDesc.textContent = msg.speech_preview.slice(0, 30) + '...';
                    } else {
                        statusDesc.textContent = msg.title || '正在生成内容...';
                    }
                    break;

                case 'image_progress':
                    updateStep(6, STEPS[6]);
                    activateFeatureCard('image');
                    if (msg.error) {
                        statusDesc.textContent = `配图跳过 (幻灯片 ${msg.slide_id})`;
                    } else if (!msg.skipped) {
                        statusDesc.textContent = `配图完成 (幻灯片 ${msg.slide_id})`;
                    }
                    break;

                case 'tts_progress':
                    updateStep(6, STEPS[6]);
                    activateFeatureCard('tts');
                    if (msg.error) {
                        console.warn('TTS failed:', msg.error);
                    } else if (!msg.skipped) {
                        statusDesc.textContent = `语音完成 (幻灯片 ${msg.slide_id})`;
                    }
                    break;

                case 'done':
                    completeGeneration(msg);
                    break;

                case 'error':
                    showError(rootData.error || msg.error || '生成失败');
                    break;

                case 'warning':
                    showWarning(rootData.message || msg.msg || '');
                    break;
            }
        } catch (e) {
            console.error('SSE handler error:', e);
        }
    }

    // ---- Completion ----

    async function completeGeneration(data) {
        courseData = data;
        stopActionAnimation();
        showComplete();

        // Merge progressive data (slides, quiz, exercise)
        const progressiveSlides = sessionStorage.getItem('progressiveSlides');
        const progressiveQuiz = sessionStorage.getItem('progressiveQuizData');
        const progressiveExercise = sessionStorage.getItem('progressiveExerciseData');
        const progressiveSlidesV2 = sessionStorage.getItem('progressiveSlidesV2');
        const progressiveCode = sessionStorage.getItem('progressiveCodeData');
        if (progressiveSlides) {
            try {
                const batchSlides = JSON.parse(progressiveSlides);
                if (batchSlides.length > 0 && courseData.slides) {
                    courseData.slides = [...batchSlides, ...courseData.slides];
                }
            } catch (e) {
                console.warn('Failed to merge progressive slides:', e);
            }
        }
        if (progressiveQuiz) {
            try {
                const batchQuiz = JSON.parse(progressiveQuiz);
                if (batchQuiz.length > 0) {
                    courseData.quiz_data = [...(courseData.quiz_data || []), ...batchQuiz];
                }
            } catch (e) {
                console.warn('Failed to merge progressive quiz:', e);
            }
        }
        if (progressiveExercise) {
            try {
                const batchExercise = JSON.parse(progressiveExercise);
                if (batchExercise.length > 0) {
                    courseData.exercise_data = [...(courseData.exercise_data || []), ...batchExercise];
                }
            } catch (e) {
                console.warn('Failed to merge progressive exercise:', e);
            }
        }
        if (progressiveSlidesV2) {
            try {
                const batchV2 = JSON.parse(progressiveSlidesV2);
                if (batchV2.length > 0) {
                    courseData.slides_v2 = [...batchV2, ...(courseData.slides_v2 || [])];
                }
            } catch (e) {
                console.warn('Failed to merge progressive slides_v2:', e);
            }
        }
        if (progressiveCode) {
            try {
                const batchCode = JSON.parse(progressiveCode);
                if (batchCode.length > 0) {
                    courseData.code_data = [...(courseData.code_data || []), ...batchCode];
                }
            } catch (e) {
                console.warn('Failed to merge progressive code_data:', e);
            }
        }

        // Update all dots to completed
        const dots = progressDots.querySelectorAll('.dot');
        dots.forEach(dot => {
            dot.classList.remove('active');
            dot.classList.add('completed');
        });

        // Save to server
        const studentId = String(sessionData?.student_id || '');
        const pageCount = (courseData.slides && courseData.slides.length > 0)
            ? courseData.slides.length
            : 0;
        try {
            const response = await fetch('/api/v2/course/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    course_data: courseData,
                    student_id: studentId,
                    ppt_pages: pageCount
                })
            });
            if (!response.ok) {
                console.error('Save failed with status:', response.status);
            }
        } catch (err) {
            console.warn('Save failed:', err);
        }

        // Store for classroom and navigate
        sessionStorage.setItem('classroomData', JSON.stringify(courseData));

        const agents = courseData?.agent_team;
        if (agents && agents.length > 0 && sessionData.requirements?.agent_mode === 'auto') {
            // Show agent reveal modal
            setTimeout(() => {
                navigateToClassroom();
            }, 2000);
        } else {
            setTimeout(navigateToClassroom, 1200);
        }
    }

    function navigateToClassroom() {
        window.location.href = '/classroom.html';
    }

    // Cleanup on page leave
    window.addEventListener('beforeunload', () => {
        stopActionAnimation();
    });

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();