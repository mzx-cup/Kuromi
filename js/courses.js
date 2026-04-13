// ============================================
// Course Center - JavaScript Logic
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initSearch();
    initCourseCards();
});

// ============================================
// Tab Switching
// ============================================
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const courseCards = document.querySelectorAll('.course-card');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Update active tab
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Filter courses
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
    const visibleCards = document.querySelectorAll('.course-card[style="display: block"], .course-card:not([style])');
    let total = 0, learning = 0, completed = 0;

    visibleCards.forEach(card => {
        const btn = card.querySelector('.course-btn');
        if (btn) {
            total++;
            if (btn.classList.contains('continue')) learning++;
            if (btn.classList.contains('completed')) completed++;
        }
    });

    if (category === 'all') {
        document.getElementById('total-courses').textContent = document.querySelectorAll('.course-card').length;
        document.getElementById('learning-courses').textContent = document.querySelectorAll('.course-btn.continue').length;
        document.getElementById('completed-courses').textContent = document.querySelectorAll('.course-btn.completed').length;
    } else {
        document.getElementById('total-courses').textContent = total;
        document.getElementById('learning-courses').textContent = learning;
        document.getElementById('completed-courses').textContent = completed;
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
            searchInput.focus();
        }
    });

    searchInput?.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        const courseCards = document.querySelectorAll('.course-card');

        courseCards.forEach(card => {
            const title = card.querySelector('.course-title').textContent.toLowerCase();
            const desc = card.querySelector('.course-desc').textContent.toLowerCase();

            if (title.includes(query) || desc.includes(query)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });
}

// ============================================
// Course Card Interactions
// ============================================
function initCourseCards() {
    const courseBtns = document.querySelectorAll('.course-btn');

    courseBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const card = this.closest('.course-card');
            const courseName = card.querySelector('.course-title').textContent;

            if (this.classList.contains('continue')) {
                // Navigate to code practice
                window.location.href = '/html/code.html';
            } else if (this.classList.contains('start')) {
                // Start learning - could navigate to lesson page
                showToast(`开始学习: ${courseName}`);
            } else if (this.classList.contains('completed')) {
                // Review - navigate to review mode
                showToast(`复习: ${courseName}`);
            }
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
