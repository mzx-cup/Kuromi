// ============================================
// Data Particle Animation
// ============================================
function createDataParticles() {
    const bg = document.getElementById('hub-bg');
    if (!bg) return;

    const particleCount = 30;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'data-particle';

        const size = Math.random() * 4 + 2;
        const left = Math.random() * 100;
        const duration = Math.random() * 20 + 15;
        const delay = Math.random() * 20;

        const colors = [
            'rgba(168, 85, 247, 0.6)',
            'rgba(59, 130, 246, 0.6)',
            'rgba(16, 185, 129, 0.6)',
            'rgba(249, 115, 22, 0.6)',
            'rgba(236, 72, 153, 0.6)'
        ];

        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${left}%;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            animation-duration: ${duration}s;
            animation-delay: -${delay}s;
        `;

        bg.appendChild(particle);
    }
}

// ============================================
// Daily Adaptive Route (今日星际航线)
// ============================================
function initDailyRoute() {
    const launchBtn = document.getElementById('launch-btn');
    const pathNodes = document.querySelectorAll('.path-node');

    if (launchBtn) {
        launchBtn.addEventListener('click', handleLaunch);
    }

    pathNodes.forEach(node => {
        node.addEventListener('click', () => handleNodeClick(node));
    });
}

function handleLaunch() {
    const launchBtn = document.getElementById('launch-btn');
    const currentNode = document.querySelector('.path-node.current');

    launchBtn.style.transform = 'scale(0.95)';

    setTimeout(() => {
        launchBtn.style.transform = '';
        showLaunchAnimation();

        if (currentNode) {
            const taskName = currentNode.dataset.task;
            showToast(`🚀 启动 "${taskName}" 学习任务！`, 'success');
        }
    }, 150);
}

function showLaunchAnimation() {
    const card = document.querySelector('.mothership-card');
    if (!card) return;

    card.style.boxShadow = `
        0 25px 50px -12px rgba(0, 0, 0, 0.5),
        0 0 80px rgba(168, 85, 247, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.2)
    `;

    setTimeout(() => {
        card.style.boxShadow = `
            0 25px 50px -12px rgba(0, 0, 0, 0.5),
            0 0 40px rgba(99, 102, 241, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.1)
        `;
    }, 1000);
}

function handleNodeClick(node) {
    if (node.classList.contains('completed')) {
        showToast('⏪ 回顾已完成的任务', 'info');
        return;
    }

    if (node.classList.contains('current')) {
        const taskName = node.dataset.task;
        showToast(`⚡ 继续 "${taskName}"`, 'success');
        return;
    }

    if (node.classList.contains('pending')) {
        const taskName = node.dataset.task;
        showToast(`📋 已记录 "${taskName}" 任务待完成`, 'info');
    }
}

// ============================================
// 星际自习大厅 (Interstellar Study Hall)
// ============================================
function initStudyHall() {
    const joinBtn = document.getElementById('join-study-btn');
    const peerPods = document.querySelectorAll('.peer-pod');

    if (joinBtn) {
        joinBtn.addEventListener('click', handleJoinStudy);
        initMagneticEffect(joinBtn);
    }

    peerPods.forEach(pod => {
        pod.addEventListener('click', () => handlePeerClick(pod));
    });
}

function initMagneticEffect(btn) {
    btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        btn.style.setProperty('--mouse-x', `${x}%`);
        btn.style.setProperty('--mouse-y', `${y}%`);
    });
}

function handleJoinStudy() {
    showToast('🔍 正在匹配学习伙伴...', 'info');
    setTimeout(() => {
        showToast('🎉 成功匹配到 3 位学习伙伴！', 'success');
    }, 2000);
}

function handlePeerClick(pod) {
    const name = pod.querySelector('.pod-name')?.textContent || '该用户';
    const time = pod.querySelector('.pod-focus-time')?.textContent || '';

    if (pod.classList.contains('current-user')) {
        showToast('📊 这是你的专注状态', 'info');
    } else {
        showToast(`👤 查看 ${name} 的专注数据 (${time})`, 'info');
    }
}

// ============================================
// Toast Notification System
// ============================================
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.style.cssText = `
        padding: 14px 20px;
        background: rgba(20, 20, 40, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        color: #fff;
        font-size: 14px;
        animation: slideIn 0.3s ease;
        backdrop-filter: blur(20px);
    `;

    const colors = {
        success: 'rgba(16, 185, 129, 0.4)',
        error: 'rgba(239, 68, 68, 0.4)',
        warning: 'rgba(249, 115, 22, 0.4)',
        info: 'rgba(59, 130, 246, 0.4)'
    };
    toast.style.borderColor = colors[type] || colors.info;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================
// URL Parameter Parser (课程中心跳转参数解析)
// ============================================
function parseCourseParams() {
    const params = new URLSearchParams(window.location.search);
    const courseId = params.get('course_id');
    const action = params.get('action');
    const courseName = params.get('course_name');
    const lastChapter = params.get('last_chapter');
    const progress = params.get('progress');
    const outline = params.get('outline');

    if (courseId) {
        console.log(`[Hub] 接收到课程参数: course_id=${courseId}, action=${action}`);
        console.log(`[Hub] 课程名称: ${courseName || '未知'}`);

        const header = document.querySelector('.hub-header');
        if (header && courseName) {
            const titleEl = header.querySelector('h1') || header.querySelector('.title');
            if (titleEl) {
                titleEl.textContent = `${courseName} - 学习中心`;
            }
        }

        if (action === 'continue' && lastChapter) {
            const decodedChapter = decodeURIComponent(lastChapter);
            console.log(`[Hub] 继续学习，上次章节: ${decodedChapter}`);
            showToast(`📚 继续学习: ${decodedChapter}`, 'info');
        }

        if (action === 'start' && outline) {
            try {
                const outlineItems = JSON.parse(decodeURIComponent(outline));
                console.log(`[Hub] 课程大纲:`, outlineItems);
            } catch (e) {
                console.warn('[Hub] 无法解析课程大纲参数');
            }
        }
    }
}

// ============================================
// Radial Progress Animation
// ============================================
function animateRadialProgress() {
    const rings = document.querySelectorAll('.radial-ring .progress');
    rings.forEach((ring, index) => {
        const offset = ring.style.strokeDashoffset;
        setTimeout(() => {
            ring.style.strokeDashoffset = offset;
        }, 300 + (index * 150));
    });
}

// ============================================
// Bar Chart Animation
// ============================================
function animateBarCharts() {
    const bars = document.querySelectorAll('.bar, .focus-bar');
    bars.forEach((bar, index) => {
        const height = bar.style.height;
        bar.style.height = '0';
        setTimeout(() => {
            bar.style.height = height;
        }, 100 + (index * 80));
    });
}

// ============================================
// Line Chart Animation
// ============================================
function animateLineChart() {
    const path = document.querySelector('.chart-path');
    const area = document.querySelector('.chart-area');
    const dots = document.querySelectorAll('.chart-dot');

    if (path) {
        const length = path.getTotalLength();
        path.style.strokeDasharray = length;
        path.style.strokeDashoffset = length;

        setTimeout(() => {
            path.style.transition = 'stroke-dashoffset 2s ease-out';
            path.style.strokeDashoffset = '0';
        }, 500);
    }

    if (area) {
        area.style.opacity = '0';
        setTimeout(() => {
            area.style.transition = 'opacity 1s ease-out';
            area.style.opacity = '1';
        }, 1500);
    }

    dots.forEach((dot, index) => {
        dot.style.opacity = '0';
        dot.style.transform = 'scale(0)';
        setTimeout(() => {
            dot.style.transition = 'all 0.3s ease-out';
            dot.style.opacity = '1';
            dot.style.transform = 'scale(1)';
        }, 2000 + (index * 100));
    });
}

// ============================================
// 全息知识生态 - 树状金字塔布局
// ============================================
function initHoloEcosystem() {
    const container = document.getElementById('holoTree');
    const nodesContainer = document.getElementById('holoNodes');

    if (!container || !nodesContainer) return;

    const nodes = nodesContainer.querySelectorAll('.holo-node');
    nodes.forEach((node, index) => {
        node.style.animationDelay = (0.1 + index * 0.1) + 's';
    });

    drawTreeConnections();

    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(drawTreeConnections, 100);
    });
}

// 绘制树状金字塔的 SVG 连线
function drawTreeConnections() {
    const svgContainer = document.getElementById('holoConnections');
    const nodesContainer = document.getElementById('holoNodes');

    if (!svgContainer || !nodesContainer) return;

    const rootNode = nodesContainer.querySelector('.node-root');
    const branchNodes = nodesContainer.querySelectorAll('.node-branch');
    const leafNodes = nodesContainer.querySelectorAll('.node-leaf');

    if (!rootNode) return;

    svgContainer.innerHTML = `
        <defs>
            <linearGradient id="lineGradientHealthy" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(52, 211, 153, 0.6)"/>
                <stop offset="100%" stop-color="rgba(52, 211, 153, 0.3)"/>
            </linearGradient>
            <linearGradient id="lineGradientWarning" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(251, 191, 36, 0.6)"/>
                <stop offset="100%" stop-color="rgba(251, 191, 36, 0.3)"/>
            </linearGradient>
            <linearGradient id="lineGradientDanger" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(248, 113, 113, 0.6)"/>
                <stop offset="100%" stop-color="rgba(248, 113, 113, 0.3)"/>
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
    `;

    svgContainer.setAttribute('viewBox', '0 0 100 100');
    svgContainer.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    const containerRect = nodesContainer.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const containerHeight = containerRect.height;

    function getNodeCenter(node) {
        const rect = node.getBoundingClientRect();
        const containerRect = nodesContainer.getBoundingClientRect();
        const x = ((rect.left + rect.width / 2) - containerRect.left) / containerWidth * 100;
        const y = ((rect.top + rect.height / 2) - containerRect.top) / containerHeight * 100;
        return { x, y };
    }

    function getNodeStatus(node) {
        return node.dataset.status || 'healthy';
    }

    branchNodes.forEach((branchNode) => {
        const rootCenter = getNodeCenter(rootNode);
        const branchCenter = getNodeCenter(branchNode);
        const status = getNodeStatus(branchNode);

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const midY = (rootCenter.y + branchCenter.y) / 2;
        const d = `M${rootCenter.x} ${rootCenter.y} Q${rootCenter.x} ${midY} ${branchCenter.x} ${branchCenter.y - 10}`;

        path.setAttribute('d', d);
        path.setAttribute('class', `connection-line ${status}`);
        path.setAttribute('filter', 'url(#glow)');
        path.style.opacity = '0';
        path.style.strokeWidth = '1';
        path.style.fill = 'none';

        svgContainer.appendChild(path);

        setTimeout(() => {
            path.style.transition = 'opacity 0.5s ease';
            path.style.opacity = '0.6';
        }, 300 + Math.random() * 300);
    });

    leafNodes.forEach((leafNode) => {
        const parentId = leafNode.dataset.parent;
        const parentNode = nodesContainer.querySelector(`[data-id="${parentId}"]`);
        if (!parentNode) return;

        const parentCenter = getNodeCenter(parentNode);
        const leafCenter = getNodeCenter(leafNode);
        const status = getNodeStatus(leafNode);

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const midY = (parentCenter.y + leafCenter.y) / 2;
        const d = `M${parentCenter.x} ${parentCenter.y} Q${parentCenter.x} ${midY} ${leafCenter.x} ${leafCenter.y - 10}`;

        path.setAttribute('d', d);
        path.setAttribute('class', `connection-line ${status}`);
        path.setAttribute('filter', 'url(#glow)');
        path.style.opacity = '0';
        path.style.strokeWidth = '0.8';
        path.style.fill = 'none';

        svgContainer.appendChild(path);

        setTimeout(() => {
            path.style.transition = 'opacity 0.5s ease';
            path.style.opacity = '0.5';
        }, 400 + Math.random() * 300);
    });
}

// ============================================
// Theme Toggle System
// ============================================
const THEME_STORAGE_KEY = 'hub-theme';

function initThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) {
        console.warn('Theme toggle button not found');
        return;
    }

    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');

    setTheme(initialTheme);

    toggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
        localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    });

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem(THEME_STORAGE_KEY)) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
}

function setTheme(theme) {
    if (theme !== 'light' && theme !== 'dark') {
        console.warn('Invalid theme:', theme, 'Defaulting to light');
        theme = 'light';
    }

    document.documentElement.setAttribute('data-theme', theme);

    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        if (theme === 'dark') {
            toggleBtn.setAttribute('aria-label', '切换到浅色模式');
        } else {
            toggleBtn.setAttribute('aria-label', '切换到深色模式');
        }
    }

    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${theme}`);
}

// ============================================
// Personalized Content based on Assessment
// ============================================
function initPersonalizedContent() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');

    if (!user.hasCompletedAssessment) {
        // User hasn't completed assessment, redirect to assessment page
        console.log('[Hub] User has not completed assessment, redirecting...');
        // Don't redirect here, allow viewing hub but show default content
        return;
    }

    // Update welcome message with personalized info
    updateWelcomeMessage(user);

    // Update recommended learning path based on profile
    updateRecommendedPath(user);

    // Update study recommendations based on radar scores
    updateStudyRecommendations(user);

    // Update peer pods to show compatible study partners
    updatePeerRecommendations(user);

    console.log('[Hub] Personalized content initialized with profile:', user.profile);
}

function updateWelcomeMessage(user) {
    const welcomeEl = document.querySelector('.welcome-section h1');
    if (!welcomeEl) return;

    const profile = user.profile || {};
    const direction = profile.learningDirection || '大数据技术';
    const level = profile.knowledgeBase || '基础入门';

    welcomeEl.textContent = `欢迎回来，${direction}学习者`;
}

function updateRecommendedPath(user) {
    const pathNodes = document.querySelectorAll('.path-node');
    const profile = user.profile || {};
    const learningPath = user.learningPath || [];

    if (learningPath.length === 0) return;

    pathNodes.forEach((node, index) => {
        if (learningPath[index]) {
            node.dataset.task = learningPath[index].topic;
            const titleEl = node.querySelector('.node-title');
            if (titleEl) {
                titleEl.textContent = learningPath[index].topic;
            }
            const descEl = node.querySelector('.node-desc');
            if (descEl) {
                descEl.textContent = learningPath[index].desc;
            }

            // Update status based on path
            node.classList.remove('current', 'completed', 'pending');
            node.classList.add(learningPath[index].status || 'pending');
        }
    });
}

function updateStudyRecommendations(user) {
    const radarScores = user.radarScores || [];
    const radarLabels = user.radarLabels || ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度'];

    if (radarScores.length !== 6) return;

    // Find weakest dimension
    const minScore = Math.min(...radarScores);
    const minIndex = radarScores.indexOf(minScore);
    const weakDimension = radarLabels[minIndex];

    // Update recommendation cards based on weak areas
    const recCards = document.querySelectorAll('.recommendation-card');
    recCards.forEach(card => {
        const titleEl = card.querySelector('.rec-title');
        if (titleEl && minScore < 50) {
            // Add emphasis on weak dimension
            const badge = card.querySelector('.weakness-badge');
            if (badge) {
                badge.textContent = `需加强: ${weakDimension}`;
                badge.style.display = 'inline-block';
            }
        }
    });

    // Update stream topics based on radar scores
    const streamTopics = document.querySelectorAll('.stream-topic');
    streamTopics.forEach((topic, index) => {
        // Prioritize content for weak dimensions
        if (index < 3 && minScore < 60) {
            topic.classList.add('priority-topic');
        }
    });
}

function updatePeerRecommendations(user) {
    const profile = user.profile || {};
    const peerPods = document.querySelectorAll('.peer-pod');

    peerPods.forEach(pod => {
        // Filter peers by compatible learning direction
        const podDirection = pod.dataset.direction;
        if (profile.learningDirection && podDirection !== profile.learningDirection) {
            pod.style.opacity = '0.5';
        }
    });
}

// ============================================
// User Avatar Initialization
// ============================================
function initUserAvatar() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (user && user.avatar) {
        const avatarImg = document.querySelector('#user-avatar img.user-avatar');
        if (avatarImg) {
            avatarImg.src = user.avatar;
        }
    }
}

// ============================================
// 今日要闻 (Daily News) Fetching with Caching
// ============================================
const NEWS_CACHE_KEY = 'starlearn_daily_news';
const NEWS_CACHE_DURATION = 12 * 60 * 60 * 1000; // 12小时缓存

function getCategoryClass(category) {
    const categoryMap = {
        'AI科技': 'ai',
        'AI': 'ai',
        '人工智能': 'ai',
        '民生': 'livelihood',
        '生活': 'life',
        '国际形势': 'international',
        '国际': 'international',
        'Web': 'web',
        '云原生': 'cloud',
        '数据': 'data'
    };
    return categoryMap[category] || 'ai';
}

function renderNewsCards(news) {
    const grid = document.getElementById('highlights-grid');
    if (!grid) return;

    grid.innerHTML = '';

    if (!news || news.length === 0) {
        grid.innerHTML = `
            <div class="highlight-error">
                <span class="error-icon">📭</span>
                <span>暂无新闻数据</span>
            </div>
        `;
        return;
    }

    news.forEach((item, index) => {
        const isMain = index === 0;
        const categoryClass = getCategoryClass(item.category);

        const card = document.createElement('div');
        card.className = `highlight-card ${isMain ? 'highlight-main' : 'highlight-side'}`;

        if (isMain) {
            card.innerHTML = `
                <div class="highlight-category ${categoryClass}">
                    <span class="category-tag">${item.category}</span>
                    <span class="category-time">${item.timestamp || '今日'}</span>
                </div>
                <div class="highlight-content">
                    <h3 class="highlight-title">${item.title}</h3>
                    <p class="highlight-desc">${item.description}</p>
                </div>
                <div class="highlight-footer">
                    <div class="highlight-tags">
                        <span class="tag ai-tag">${item.source}</span>
                    </div>
                    <span class="highlight-source">${item.source}</span>
                </div>
            `;
        } else {
            card.innerHTML = `
                <div class="highlight-category ${categoryClass}">
                    <span class="category-tag">${item.category}</span>
                    <span class="category-time">${item.timestamp || '今日'}</span>
                </div>
                <div class="highlight-content">
                    <h3 class="highlight-title">${item.title}</h3>
                    <p class="highlight-desc">${item.description}</p>
                </div>
            `;
        }

        grid.appendChild(card);
    });
}

function getCachedNews() {
    try {
        const cached = localStorage.getItem(NEWS_CACHE_KEY);
        if (!cached) return null;

        const { news, date, timestamp } = JSON.parse(cached);
        const now = Date.now();
        const cacheAge = now - timestamp;

        // 缓存超过12小时，视为过期
        if (cacheAge > NEWS_CACHE_DURATION) {
            return null;
        }

        return { news, date, isStale: cacheAge > 6 * 60 * 60 * 1000 }; // 超过6小时显示刷新提示
    } catch (e) {
        return null;
    }
}

function setCachedNews(news, date) {
    try {
        localStorage.setItem(NEWS_CACHE_KEY, JSON.stringify({
            news,
            date,
            timestamp: Date.now()
        }));
    } catch (e) {
        console.warn('[Hub] Failed to cache news:', e);
    }
}

async function fetchTodayNews(showLoading = false) {
    const grid = document.getElementById('highlights-grid');
    const dateEl = document.getElementById('news-date');

    // 先尝试从缓存读取
    const cached = getCachedNews();
    if (cached && cached.news) {
        if (dateEl && cached.date) {
            const dateParts = cached.date.match(/(\d+)年(\d+)月(\d+)日/);
            if (dateParts) {
                const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date().getDay()];
                dateEl.textContent = `${dateParts[2]}月${dateParts[3]}日 · ${weekday}`;
            }
        }
        renderNewsCards(cached.news);

        // 缓存过期了，在后台静默更新
        if (cached.isStale) {
            silentRefreshNews();
        }
        return;
    }

    // 无缓存，显示加载状态（仅首次）
    if (showLoading && grid) {
        grid.innerHTML = `
            <div class="highlight-loading">
                <div class="loading-spinner"></div>
                <span>正在加载今日要闻...</span>
            </div>
        `;
    }

    try {
        const response = await fetch('/api/news/today');
        const data = await response.json();

        if (data.success && data.news) {
            if (dateEl && data.date) {
                const dateParts = data.date.match(/(\d+)年(\d+)月(\d+)日/);
                if (dateParts) {
                    const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date().getDay()];
                    dateEl.textContent = `${dateParts[2]}月${dateParts[3]}日 · ${weekday}`;
                }
            }

            setCachedNews(data.news, data.date);
            renderNewsCards(data.news);
        } else {
            throw new Error('Failed to fetch news');
        }
    } catch (error) {
        console.error('[Hub] Failed to fetch today news:', error);

        if (grid) {
            grid.innerHTML = `
                <div class="highlight-error">
                    <span class="error-icon">😵</span>
                    <span>新闻加载失败</span>
                    <button class="retry-btn" onclick="fetchTodayNews(true)">重新加载</button>
                </div>
            `;
        }
    }
}

// ============================================
// 侧边栏与导航控制
// ============================================
function toggleSidebar() {
    const sidebar = document.getElementById('hub-sidebar');
    sidebar.classList.toggle('open');
}

function updateNotificationDot() {
    const notificationDot = document.getElementById('notification-dot');
    if (!notificationDot) return;
    const unreadCount = document.querySelectorAll('.notification-item.unread').length;
    if (unreadCount > 0) {
        notificationDot.classList.add('active');
    } else {
        notificationDot.classList.remove('active');
    }
}

function initSidebarAndNotifications() {
    // 侧边栏切换
    document.getElementById('sidebar-toggle')?.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleSidebar();
    });

    // 点击其他区域关闭侧边栏
    document.addEventListener('click', function(e) {
        const sidebar = document.getElementById('hub-sidebar');
        const toggle = document.getElementById('sidebar-toggle');
        if (sidebar?.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            !toggle?.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });

    // 导航高亮
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href && href !== '#' && window.location.pathname === href) {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');
        }
    });

    // 导航点击处理
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (!href || href === '#') {
                e.preventDefault();
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                this.classList.add('active');
                const section = this.dataset.section;
                const target = document.getElementById('section-' + section);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            } else {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });

    // 通知面板
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationBackdrop = document.getElementById('notification-backdrop');
    const markAllRead = document.getElementById('mark-all-read');
    const notificationItems = document.querySelectorAll('.notification-item');

    notificationBtn?.addEventListener('click', function(e) {
        e.stopPropagation();
        notificationPanel?.classList.toggle('active');
        notificationBackdrop?.classList.toggle('active');
    });

    notificationBackdrop?.addEventListener('click', function() {
        notificationPanel?.classList.remove('active');
        notificationBackdrop?.classList.remove('active');
    });

    markAllRead?.addEventListener('click', function() {
        notificationItems.forEach(item => {
            item.classList.remove('unread');
        });
        notificationDot?.classList.remove('active');
    });

    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            this.classList.remove('unread');
            updateNotificationDot();
        });
    });

    updateNotificationDot();
}

// 通知持久化存储
const NOTIF_STORAGE_KEY = 'starlearn_notifications';

function getStoredNotifications() {
    try {
        return JSON.parse(localStorage.getItem(NOTIF_STORAGE_KEY) || '[]');
    } catch (e) { return []; }
}

function saveNotificationToStorage(notif) {
    const list = getStoredNotifications();
    list.unshift({ ...notif, id: Date.now(), time: new Date().toLocaleString('zh-CN') });
    if (list.length > 50) list.splice(50);
    localStorage.setItem(NOTIF_STORAGE_KEY, JSON.stringify(list));
}

// 添加通知到 hub 面板
function addNotificationToHubPanel(payload) {
    const { title = '', content = '', type = 'system' } = payload || {};
    const list = document.getElementById('notification-list');
    if (!list) return;

    const iconMap = {
        achievement: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>`,
        seed: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>`,
        system: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        reminder: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
    };

    const colorMap = {
        achievement: 'achievement',
        seed: 'business',
        system: 'system',
        reminder: 'activity'
    };

    const icon = iconMap[type] || iconMap.system;
    const colorClass = colorMap[type] || 'system';

    const item = document.createElement('div');
    item.className = 'notification-item unread';
    item.innerHTML = `
        <div class="notification-icon ${colorClass}">${icon}</div>
        <div class="notification-content">
            <p class="notification-title">${escapeHtml(title)}</p>
            <p class="notification-text">${escapeHtml(content)}</p>
            <span class="notification-time">刚刚</span>
        </div>
    `;

    item.addEventListener('click', () => {
        item.classList.remove('unread');
        updateNotificationDot();
    });

    // 插入到最前面
    list.insertBefore(item, list.firstChild);

    // 持久化
    saveNotificationToStorage({ title, content, type });

    // 更新红点
    updateNotificationDot();

    // 同步到所有打开的 hub 页面（跨标签页）
    localStorage.setItem('starlearn_notifications_last_update', String(Date.now()));
}

// 监听 achievement-unlocked 事件
document.addEventListener('achievement-unlocked', (e) => {
    const { achievement } = e.detail || {};
    if (achievement) {
        addNotificationToHubPanel({
            title: '🏆 成就解锁',
            content: `${achievement.name} - ${achievement.desc}`,
            type: 'achievement'
        });
    }
});

// 监听 starlearnNotifications 调用（统一拦截）
const _origShowNotif = window.starlearnNotifications?.showNotification;
window.starlearnNotifications = window.starlearnNotifications || { showNotification: () => {} };
const _origFn = window.starlearnNotifications.showNotification.bind(window.starlearnNotifications);
window.starlearnNotifications.showNotification = function(payload) {
    _origFn(payload);
    addNotificationToHubPanel(payload);
};

// 跨标签页同步通知
window.addEventListener('storage', (e) => {
    if (e.key === 'starlearn_notifications_last_update') {
        const list = document.getElementById('notification-list');
        if (!list) return;
        const stored = getStoredNotifications();
        // 去重后重新渲染
        const existingIds = new Set(
            Array.from(list.querySelectorAll('.notification-item')).map(el => el.dataset.tempId).filter(Boolean)
        );
        stored.forEach(n => {
            if (!existingIds.has(String(n.id))) {
                const item = document.createElement('div');
                item.className = 'notification-item';
                item.dataset.tempId = n.id;
                const iconMap = {
                    achievement: 'achievement', seed: 'business', system: 'system', reminder: 'activity'
                };
                const iconSvg = {
                    achievement: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>`,
                    seed: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>`,
                    system: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
                    reminder: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
                };
                item.innerHTML = `
                    <div class="notification-icon ${iconMap[n.type] || 'system'}">${iconSvg[n.type] || iconSvg.system}</div>
                    <div class="notification-content">
                        <p class="notification-title">${escapeHtml(n.title)}</p>
                        <p class="notification-text">${escapeHtml(n.content)}</p>
                        <span class="notification-time">${n.time || '刚刚'}</span>
                    </div>
                `;
                item.addEventListener('click', () => {
                    item.classList.remove('unread');
                    updateNotificationDot();
                });
                list.insertBefore(item, list.firstChild);
                updateNotificationDot();
            }
        });
    }
});

function escapeHtml(str) {
    if (!str && str !== 0) return '';
    return String(str).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initSidebarAndNotifications);

// 后台静默刷新新闻（缓存超过6小时时触发）
async function silentRefreshNews() {
    try {
        const response = await fetch('/api/news/today');
        const data = await response.json();

        if (data.success && data.news) {
            setCachedNews(data.news, data.date);
            const cached = getCachedNews();
            if (cached && !cached.isStale) {
                renderNewsCards(data.news);
            }
        }
    } catch (e) {
        // 静默失败，不打扰用户
    }
}

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();
    createDataParticles();
    initDailyRoute();
    initStudyHall();
    animateRadialProgress();
    animateBarCharts();
    animateLineChart();
    parseCourseParams();
    initHoloEcosystem();
    initPersonalizedContent();
    initUserAvatar();
    // 使用缓存，不显示加载状态
    fetchTodayNews(false);
});

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});