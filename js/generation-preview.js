/**
 * Generation Preview Page JavaScript
 * OpenMAIC Style - Clean glass-morphism UI
 */

(function() {
    'use strict';

    // Step definitions (6 steps)
    const STEPS = [
        { id: 'pdf-analysis', title: '正在分析需求...', desc: '解析学习需求与内容' },
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

    // Viz containers
    const vizContainers = {
        'error': document.getElementById('viz-error'),
        'complete': document.getElementById('viz-complete'),
        'pdf-analysis': document.getElementById('viz-pdf'),
        'web-search': document.getElementById('viz-search'),
        'outline': document.getElementById('viz-outline'),
        'agent-generation': document.getElementById('viz-ai'),
        'slide-content': document.getElementById('viz-content'),
        'actions': document.getElementById('viz-actions')
    };

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
            startGeneration();
        } else {
            showError('未找到生成会话，请返回首页重试');
            backBtn.style.display = 'flex';
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

        abortController = new AbortController();

        const reqs = sessionData.requirements || sessionData || {};
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

    function showError(message) {
        isError = true;
        stopActionAnimation();

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

    function updateSearchSources(sources) {
        if (!searchResults) return;

        searchResults.innerHTML = sources.slice(0, 4).map((source, i) => `
            <div class="search-result-item">
                <div class="result-title" style="width: ${60 + Math.random() * 30}%"></div>
                <div class="result-url"></div>
            </div>
        `).join('');

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

                case 'web_search':
                    updateStep(1, STEPS[1]);
                    if (msg.sources_count !== undefined) {
                        statusDesc.textContent = `已找到 ${msg.sources_count} 条相关资料`;
                    }
                    if (msg.sources && msg.sources.length > 0) {
                        updateSearchSources(msg.sources);
                    }
                    break;

                case 'outline':
                    updateStep(2, STEPS[2]);
                    if (msg.title) addOutlineItem(msg);
                    break;

                case 'outline_progress':
                    if (rootData.progress) updateProgress(rootData.progress);
                    break;

                case 'agent_generation':
                    updateStep(3, STEPS[3]);
                    const agents = msg.agents || [];
                    if (agents.length > 0) {
                        statusDesc.textContent = `已生成 ${agents.length} 位AI教师`;
                    }
                    break;

                case 'progressive_batch':
                    if (msg.slides) {
                        sessionStorage.setItem('progressiveSlides', JSON.stringify(msg.slides));
                        sessionStorage.setItem('progressiveQuizData', JSON.stringify(msg.quiz_data || []));
                        sessionStorage.setItem('progressiveExerciseData', JSON.stringify(msg.exercise_data || []));
                    }
                    break;

                case 'slide_content':
                    updateStep(4, STEPS[4]);
                    if (msg.speech_preview) {
                        statusDesc.textContent = msg.speech_preview.slice(0, 30) + '...';
                    } else {
                        statusDesc.textContent = msg.title || '正在生成内容...';
                    }
                    break;

                case 'image_progress':
                    updateStep(5, STEPS[5]);
                    if (msg.error) {
                        statusDesc.textContent = `配图跳过 (幻灯片 ${msg.slide_id})`;
                    } else if (!msg.skipped) {
                        statusDesc.textContent = `配图完成 (幻灯片 ${msg.slide_id})`;
                    }
                    break;

                case 'tts_progress':
                    updateStep(5, STEPS[5]);
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

        // Merge progressive slides
        const progressiveSlides = sessionStorage.getItem('progressiveSlides');
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