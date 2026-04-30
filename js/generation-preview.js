/**
 * Generation Preview Page JavaScript
 * Handles SSE streaming events and progress visualization
 * Enhanced with 6-step pipeline and AgentRevealModal
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

    // DOM Elements
    const backBtn = document.getElementById('back-btn');
    const abortBtn = document.getElementById('abort-btn');
    const progressDots = document.getElementById('progress-dots');
    const statusTitle = document.getElementById('status-title');
    const statusDesc = document.getElementById('status-desc');
    const warningBadge = document.getElementById('warning-badge');
    const warningText = document.getElementById('warning-text');
    const outlineListPreview = document.getElementById('outline-list-preview');
    const agentRevealModal = document.getElementById('agent-reveal-modal');

    // Viz containers
    const vizContainers = {
        'pdf-analysis': document.getElementById('viz-pdf'),
        'web-search': document.getElementById('viz-search'),
        'outline': document.getElementById('viz-outline'),
        'agent-generation': document.getElementById('viz-ai'),
        'slide-content': document.getElementById('viz-content'),
        'actions': document.getElementById('viz-actions')
    };

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

        const revealBtn = document.getElementById('reveal-btn');
        if (revealBtn) {
            revealBtn.addEventListener('click', hideAgentReveal);
        }

        const closeReveal = document.getElementById('agent-reveal-close');
        if (closeReveal) {
            closeReveal.addEventListener('click', hideAgentReveal);
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') hideAgentReveal();
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
        }
    }

    // ---- SSE Stream handling ----

    async function startGeneration() {
        abortController = new AbortController();

        // Support both old format (requirements.requirement) and flat format
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
        console.log('[DEBUG] SessionData:', JSON.stringify(sessionData));
        console.log('[DEBUG] Body sent:', JSON.stringify(body));

        try {
            const response = await fetch('/api/v2/course/generate/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: abortController.signal,
            });

            if (!response.ok) {
                const errText = await response.text();
                console.error('[DEBUG] 422 response body:', errText);
                throw new Error(`服务器错误: ${response.status} - ${errText}`);
            }

            abortBtn.style.display = 'flex';
        abortBtn.classList.add('visible');

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
            showRetryButton();
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

    let activeStepId = null;

    function updateStep(index, step) {
        currentStep = index;
        activeStepId = step.id;

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
            if (viz) viz.classList.toggle('active', id === step.id);
        });
    }

    function updateStatus(msg) {
        statusTitle.textContent = msg;
    }

    function showError(message) {
        statusTitle.textContent = '生成失败';
        statusDesc.textContent = message;
        Object.values(vizContainers).forEach(v => { if (v) v.classList.remove('active'); });
    }

    function showRetryButton() {
        const retryBtn = document.getElementById('retry-btn');
        if (retryBtn) {
            retryBtn.classList.add('visible');
            retryBtn.addEventListener('click', () => {
                retryBtn.style.display = 'none';
                startGeneration();
            });
        }
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

    // ---- Outline streaming ----

    function addOutlineItem(outline) {
        if (!outlineListPreview) return;
        const div = document.createElement('div');
        div.className = 'outline-item';
        const badgeType = outline.type || 'slide';
        const typeIcons = {
            'slide': '📖', 'quiz': '📝', 'exercise': '✏️',
            'interactive': '🎮', 'pbl': '🔬', 'code': '💻', 'video': '🎬'
        };
        div.innerHTML = `<span class="outline-type-icon">${typeIcons[badgeType] || '📖'}</span> ${outline.title || '新章节'}`;
        outlineListPreview.appendChild(div);
    }

    // ---- Agent Reveal Modal ----

    function showAgentReveal(agents) {
        if (!agentRevealModal) return;
        const backPanel = document.getElementById('agent-reveal-back');
        if (backPanel && agents) {
            backPanel.innerHTML = agents.map((a, i) => `
                <div class="agent-reveal-card-item" style="animation-delay: ${i * 0.15}s; border-left: 3px solid ${a.color || '#6366f1'};">
                    <div class="agent-card-avatar">${a.avatar || '🤖'}</div>
                    <div class="agent-card-info">
                        <h4 style="color: ${a.color || '#6366f1'};">${a.name || ''}</h4>
                        <p class="agent-card-role">${a.role || ''}</p>
                        <p class="agent-card-persona">${(a.persona || '').slice(0, 80)}...</p>
                        <span class="agent-card-voice">
                            <i class="fas fa-volume-up"></i> ${getVoiceLabel(a.voice_id || '')}
                        </span>
                    </div>
                </div>
            `).join('');
        }

        agentRevealModal.style.display = 'flex';
        agentRevealModal.classList.add('visible');
        requestAnimationFrame(() => {
            document.getElementById('agent-reveal-card-inner')?.classList.add('flipped');
        });
    }

    function hideAgentReveal() {
        if (agentRevealModal) agentRevealModal.style.display = 'none';
    }

    function getVoiceLabel(voiceId) {
        const map = {
            'female-shaonv': '青春少女', 'female-yujie': '温柔御姐',
            'female-danyun': '知性女声', 'male-qingshu': '青涩少年',
            'male-shaoshuai': '磁性男声'
        };
        return map[voiceId] || '默认语音';
    }

    // ---- Completion ----

    function completeGeneration(data) {
        courseData = data;
        abortBtn.style.display = 'none';

        // Merge progressive batch slides into final course data if present
        const progressiveSlides = sessionStorage.getItem('progressiveSlides');
        if (progressiveSlides) {
            try {
                const batchSlides = JSON.parse(progressiveSlides);
                if (batchSlides.length > 0 && courseData.slides) {
                    // Prepend progressive batch slides to the front
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
        updateStatus('课程生成完成！');
        statusDesc.textContent = '即将进入课堂...';
        updateStep(STEPS.length, STEPS[STEPS.length - 1]);

        // Save to server
        const studentId = sessionData?.student_id || '';
        fetch('/api/v2/course/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course_data: courseData, student_id: studentId })
        }).catch(err => console.warn('Save failed:', err));

        // Store for classroom
        sessionStorage.setItem('classroomData', JSON.stringify(courseData));

        // Show agent reveal if auto mode
        const agents = courseData?.agent_team;
        if (agents && agents.length > 0 && sessionData.requirements?.agent_mode === 'auto') {
            showAgentReveal(agents);
            // Navigate after reveal animation
            setTimeout(() => {
                hideAgentReveal();
                navigateToClassroom();
            }, 4000);
        } else {
            setTimeout(navigateToClassroom, 1200);
        }
    }

    function navigateToClassroom() {
        window.location.href = '/classroom.html';
    }

    // ---- SSE message handler ----

    function handleSSEMessage(event) {
        try {
            const raw = event.parsed || {};
            // SSE event field (e.g. "pdf_analysis", "status") - set via backend event: field
            const eventType = raw.type || event.type;
            // Inner data object (payload inside the JSON body)
            const msg = raw.data || {};
            // Top-level "data" key inside the SSE event body (for progress, error, etc.)
            const rootData = raw;

            switch (eventType) {
                case 'status':
                    if (msg.msg) updateStatus(msg.msg);
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
                    // Store progressive batch data for classroom
                    if (msg.slides) {
                        sessionStorage.setItem('progressiveSlides', JSON.stringify(msg.slides));
                        sessionStorage.setItem('progressiveQuizData', JSON.stringify(msg.quiz_data || []));
                        sessionStorage.setItem('progressiveExerciseData', JSON.stringify(msg.exercise_data || []));
                    }
                    break;

                case 'slide_content':
                    updateStep(4, STEPS[4]);
                    statusDesc.textContent = msg.title || msg.speech_preview || '正在生成内容...';
                    break;

                case 'image_progress':
                    updateStep(5, STEPS[5]);
                    if (msg.error) {
                        statusDesc.textContent = `配图跳过 (${msg.slide_id})`;
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
                    showRetryButton();
                    break;

                case 'warning':
                    showWarning(rootData.message || msg.msg || '');
                    break;
            }
        } catch (e) {
            console.error('SSE handler error:', e);
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
