// ============================================
// Course Center - JavaScript Logic
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initSearch();
    initCourseCards();
    initReviewButtons();
    initStartButtons();
    initCompletedButtons();
    initContinueButtons();
    initReviewDrawerLinks();
});

// ============================================
// Course Navigation Router
// ============================================
const CourseRouter = {
    routes: {
        'continue': '/hub.html',
        'start': '/hub.html',
        'review': '/code.html',
        'certificate': '/stellar-showcase.html'
    },

    // 直接跳转到指定路径
    navigateToPath(path) {
        console.log(`[CourseRouter] Direct navigation to: ${path}`);
        showToast('正在跳转...');
        setTimeout(() => {
            window.location.href = path;
        }, 300);
    },

    navigate(action, courseId, card) {
        const courseName = card.querySelector('.course-title').textContent;
        const courseData = {
            course_id: courseId,
            course_name: courseName,
            action: action
        };

        let targetUrl = this.routes[action] || '/courses.html';
        const params = new URLSearchParams();

        params.set('course_id', courseId);
        params.set('action', action);

        if (action === 'continue') {
            const lastChapter = card.dataset.lastChapter || '';
            const progress = card.dataset.progress || '0';
            params.set('last_chapter', encodeURIComponent(lastChapter));
            params.set('progress', progress);
        }

        if (action === 'start') {
            const outlineItems = card.querySelectorAll('.outline-item span:last-child');
            const outline = Array.from(outlineItems).map(item => item.textContent);
            params.set('outline', encodeURIComponent(JSON.stringify(outline)));
        }

        if (action === 'review') {
            params.set('mode', 'review');
        }

        if (action === 'certificate') {
            params.set('show_cert', 'true');
        }

        const fullUrl = `${targetUrl}?${params.toString()}`;
        console.log(`[CourseRouter] Navigating to: ${fullUrl}`);

        showToast(`正在进入: ${courseName}`);

        setTimeout(() => {
            window.location.href = fullUrl;
        }, 500);
    }
};

// ============================================
// Tab Switching
// ============================================
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            const category = this.dataset.category;
            filterCourses(category);
        });
    });
}

function filterCourses(category) {
    const courseCards = document.querySelectorAll('.course-card');

    courseCards.forEach(card => {
        if (category === 'all' || card.dataset.category === category) {
            card.style.display = 'block';
            card.style.animation = 'fadeIn 0.3s ease';
        } else {
            card.style.display = 'none';
        }
    });

    updateStats(category);
}

function updateStats(category) {
    const totalEl = document.getElementById('total-courses');
    const learningEl = document.getElementById('learning-courses');
    const completedEl = document.getElementById('completed-courses');

    if (!totalEl) return;

    const allCards = document.querySelectorAll('.course-card');
    const continueBtns = document.querySelectorAll('.course-btn.continue');
    const completedBtns = document.querySelectorAll('.course-btn.completed');

    if (category === 'all') {
        totalEl.textContent = allCards.length;
        learningEl.textContent = continueBtns.length;
        completedEl.textContent = completedBtns.length;
    } else {
        let visibleContinue = 0, visibleCompleted = 0;
        allCards.forEach(card => {
            if (card.style.display !== 'none') {
                const btn = card.querySelector('.course-btn');
                if (btn?.classList.contains('continue')) visibleContinue++;
                if (btn?.classList.contains('completed')) visibleCompleted++;
            }
        });
        const visibleTotal = Array.from(allCards).filter(c => c.style.display !== 'none').length;
        totalEl.textContent = visibleTotal;
        learningEl.textContent = visibleContinue;
        completedEl.textContent = visibleCompleted;
    }
}

// ============================================
// Search Functionality
// ============================================
function initSearch() {
    const searchToggle = document.getElementById('search-toggle');
    const searchContainer = document.getElementById('search-container');
    const searchInput = document.getElementById('course-search');

    searchToggle?.addEventListener('click', function() {
        searchContainer.classList.toggle('hidden');
        if (!searchContainer.classList.contains('hidden')) {
            searchInput?.focus();
        }
    });

    searchInput?.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        const courseCards = document.querySelectorAll('.course-card');

        courseCards.forEach(card => {
            const title = card.querySelector('.course-title')?.textContent.toLowerCase() || '';
            const desc = card.querySelector('.course-desc')?.textContent.toLowerCase() || '';

            if (title.includes(query) || desc.includes(query)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });
}

// ============================================
// Continue Learning Button - Dynamic Island
// ============================================
function initContinueButtons() {
    const continueBtns = document.querySelectorAll('.course-btn.continue');

    continueBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (this.classList.contains('expanding')) return;

            const card = this.closest('.course-card');
            const courseId = card.dataset.category + '_' + Date.now().toString(36);

            this.classList.add('expanding');
            const miniProgress = this.querySelector('.mini-progress');
            if (miniProgress) {
                const progress = parseInt(this.dataset.progress) || 0;
                miniProgress.style.width = progress + '%';
            }

            setTimeout(() => {
                CourseRouter.navigate('continue', courseId, card);
            }, 600);
        });
    });
}

// ============================================
// Start Learning Button - Outline Preview
// ============================================
function initStartButtons() {
    const startBtns = document.querySelectorAll('.course-btn.start');

    startBtns.forEach(btn => {
        let hoverTimeout;

        btn.addEventListener('mouseenter', function() {
            hoverTimeout = setTimeout(() => {
                const popup = this.querySelector('.outline-popup');
                if (popup) {
                    popup.style.opacity = '1';
                    popup.style.visibility = 'visible';
                    popup.style.transform = 'translateX(-50%) translateY(0) scale(1)';
                }
            }, 300);
        });

        btn.addEventListener('mouseleave', function() {
            clearTimeout(hoverTimeout);
            const popup = this.querySelector('.outline-popup');
            if (popup) {
                popup.style.opacity = '0';
                popup.style.visibility = 'hidden';
                popup.style.transform = 'translateX(-50%) translateY(8px) scale(0.95)';
            }
        });

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const card = this.closest('.course-card');
            const courseId = card.dataset.category + '_01';

            CourseRouter.navigate('start', courseId, card);
        });
    });
}

// ============================================
// Review Button - Drawer Menu & Dynamic Stats
// ============================================
function initReviewButtons() {
    const reviewBtns = document.querySelectorAll('.course-btn.review');

    reviewBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            this.classList.toggle('active');
        });

        btn.addEventListener('mouseenter', function() {
            const card = this.closest('.course-card');
            const stats = card.querySelector('.review-stats');
            const suggest = card.querySelector('.review-suggest');
            if (stats) stats.style.opacity = '0';
            if (suggest) {
                suggest.style.display = 'inline';
                setTimeout(() => suggest.style.opacity = '1', 50);
            }
        });

        btn.addEventListener('mouseleave', function() {
            const card = this.closest('.course-card');
            const stats = card.querySelector('.review-stats');
            const suggest = card.querySelector('.review-suggest');
            if (stats) stats.style.opacity = '1';
            if (suggest) {
                suggest.style.opacity = '0';
                setTimeout(() => suggest.style.display = 'none', 300);
            }
        });
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.course-btn.review')) {
            document.querySelectorAll('.course-btn.review.active').forEach(btn => {
                btn.classList.remove('active');
            });
        }
    });
}

// ============================================
// Review Drawer Item Click Handlers
// ============================================
function initReviewDrawerLinks() {
    const drawerItems = document.querySelectorAll('.drawer-item');

    drawerItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const btn = this.closest('.course-btn.review');
            const card = btn.closest('.course-card');
            const courseId = card.dataset.category + '_review';
            const actionType = this.dataset.action || 'review';

            btn.classList.remove('active');

            // 根据 data-action 执行不同的跳转
            switch(actionType) {
                case 'mistake-book':
                    // 查看错题本 - 跳转到代码练习页面的错题本模式
                    CourseRouter.navigateToPath('/code.html?course_id=' + courseId + '&mode=mistake-book');
                    break;
                case 'review-core':
                    // 重温核心知识点 - 跳转到学习中心复习模式
                    CourseRouter.navigate('review', courseId, card);
                    break;
                case 'final-exam':
                    // 进行期末测验 - 跳转到测验页面
                    CourseRouter.navigateToPath('/assessment.html?course_id=' + courseId + '&type=final-exam');
                    break;
                default:
                    // 默认复习模式
                    CourseRouter.navigate('review', courseId, card);
            }
        });
    });
}

// ============================================
// Completed Button - Confetti & Text Flip
// ============================================
function initCompletedButtons() {
    const completedBtns = document.querySelectorAll('.course-btn.completed');

    completedBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const card = this.closest('.course-card');
            const courseId = card.dataset.category + '_completed';

            CourseRouter.navigate('certificate', courseId, card);
        });
    });
}

// ============================================
// Trigger Confetti Animation
// ============================================
function triggerConfetti(btn) {
    btn.classList.add('celebrating');
    setTimeout(() => {
        btn.classList.remove('celebrating');
    }, 1000);
}

// ============================================
// Course Card Interactions
// ============================================
function initCourseCards() {
    // 只处理 continue 和 start 按钮，review 和 completed 由各自的初始化函数处理
    const continueBtns = document.querySelectorAll('.course-btn.continue');
    const startBtns = document.querySelectorAll('.course-btn.start');

    continueBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const card = this.closest('.course-card');
            const courseId = card.dataset.category + '_' + Date.now().toString(36);
            CourseRouter.navigate('continue', courseId, card);
        });
    });

    startBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const card = this.closest('.course-card');
            const courseId = card.dataset.category + '_01';
            CourseRouter.navigate('start', courseId, card);
        });
    });
}

// ============================================
// Toast Notification
// ============================================
function showToast(message) {
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        background: rgba(30, 41, 59, 0.95);
        color: white;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
        z-index: 9999;
        backdrop-filter: blur(16px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        animation: toastIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translate(-50%, 12px)';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes toastIn {
        from { opacity: 0; transform: translate(-50%, 20px); }
        to { opacity: 1; transform: translate(-50%, 0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
