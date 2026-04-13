document.addEventListener('DOMContentLoaded', function() {
    createStarfield();
    initCategoryFilter();
    init3DMouseEffect();
    initModal();
    updateBadgeCount();
});

function createStarfield() {
    const bg = document.getElementById('stellar-bg');
    const starCount = 150;
    
    for (let i = 0; i < starCount; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.setProperty('--duration', (2 + Math.random() * 4) + 's');
        star.style.setProperty('--delay', Math.random() * 5 + 's');
        star.style.opacity = 0.1 + Math.random() * 0.5;
        bg.appendChild(star);
    }
}

function initCategoryFilter() {
    const tabs = document.querySelectorAll('.category-tab');
    const cards = document.querySelectorAll('.badge-card');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            const category = tab.dataset.category;
            
            cards.forEach(card => {
                if (category === 'all' || card.dataset.category === category) {
                    card.classList.remove('hidden');
                    card.style.animation = 'fadeIn 0.5s ease forwards';
                } else {
                    card.classList.add('hidden');
                }
            });
        });
    });
}

function init3DMouseEffect() {
    const cards = document.querySelectorAll('.badge-card:not(.locked)');
    
    cards.forEach(card => {
        const base = card.querySelector('.badge-base');
        
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / centerY * -8;
            const rotateY = (x - centerX) / centerX * 8;
            
            base.style.transform = `translateY(-8px) scale(1.05) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });
        
        card.addEventListener('mouseleave', () => {
            base.style.transform = '';
        });
    });
}

function initModal() {
    const modal = document.getElementById('badge-modal');
    const closeBtn = document.getElementById('modal-close');
    const cards = document.querySelectorAll('.badge-card:not(.locked)');
    
    cards.forEach(card => {
        card.addEventListener('click', () => {
            const name = card.querySelector('.badge-name').textContent;
            const desc = card.querySelector('.badge-desc').textContent;
            const tier = card.querySelector('.badge-tier').textContent;
            const iconSvg = card.querySelector('.badge-icon').innerHTML;
            
            document.getElementById('modal-title').textContent = name;
            document.getElementById('modal-desc').textContent = desc;
            document.getElementById('modal-tier').textContent = tier;
            document.getElementById('modal-tier').className = `modal-tier badge-tier ${card.dataset.tier}`;
            document.getElementById('modal-icon').outerHTML = iconSvg.replace('badge-icon', 'badge-icon');
            
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        });
    });
    
    closeBtn.addEventListener('click', closeModal);
    
    modal.querySelector('.modal-backdrop').addEventListener('click', closeModal);
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });
    
    function closeModal() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function updateBadgeCount() {
    const unlockedBadges = document.querySelectorAll('.badge-card:not(.locked)').length;
    document.getElementById('badge-count').textContent = unlockedBadges;
}

const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
