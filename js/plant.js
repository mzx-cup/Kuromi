const PLANT_DATA = [
    { id: 'bamboo', name: '逻辑之竹', emoji: '🎋', stages: ['🌰', '🌱', '🎋', '🎍'], growTime: 120, desc: '逻辑思维' },
    { id: 'vine', name: '算法之藤', emoji: '🌿', stages: ['🌰', '🌱', '🌿', '🍃'], growTime: 100, desc: '算法能力' },
    { id: 'sunflower', name: '数据向日葵', emoji: '🌻', stages: ['🌰', '🌱', '🌻', '🌻'], growTime: 90, desc: '数据分析' },
    { id: 'cactus', name: '极客仙人掌', emoji: '🌵', stages: ['🌰', '🌱', '🌵', '🏜️'], growTime: 150, desc: '耐心韧性' },
    { id: 'rose', name: '星空玫瑰', emoji: '🌹', stages: ['🌹', '🌷', '🌹', '💐'], growTime: 180, desc: '追求卓越' },
    { id: 'tree', name: '智慧之树', emoji: '🌳', stages: ['🌱', '🌿', '🌳', '🌲'], growTime: 200, desc: '知识沉淀' },
    { id: 'lotus', name: '架构莲花', emoji: '🪷', stages: ['🪷', '🪷', '🪷', '✨'], growTime: 160, desc: '系统设计' },
    { id: 'mushroom', name: '敏捷蘑菇', emoji: '🍄', stages: ['🍄', '🍄', '🍄', '🌟'], growTime: 80, desc: '快速迭代' },
    { id: 'flower', name: '创新之花', emoji: '🌸', stages: ['🌸', '🌺', '🌸', '💮'], growTime: 120, desc: '创新思维' },
    { id: 'palm', name: '运维棕榈', emoji: '🌴', stages: ['🌴', '🌴', '🌴', '🏝️'], growTime: 140, desc: '稳定运维' }
];

const STAGE_NAMES = ['种子 Seed', '萌芽 Sprout', '成长期 Growth', '成熟 Harvest'];
const WATER_PER_ACTION = 20;
const NUTRIENT_PER_ACTION = 15;
const WATER_DECAY_RATE = 2;
const NUTRIENT_DECAY_RATE = 1;
const WATER_TIME_REDUCTION = 10 * 60;
const NUTRIENT_TIME_REDUCTION = 30 * 60;

let plantState = {
    seeds: 0,
    ownedPlants: [],
    currentPlant: null,
    stage: 0,
    remainingTime: 0,
    water: 0,
    nutrient: 0,
    lastUpdate: Date.now()
};

function init() {
    loadPlantState();
    renderSeedCount();
    renderPlantCollection();
    renderCurrentPlant();
    startGrowthTimer();
    generateParticles();
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function loadPlantState() {
    const saved = localStorage.getItem('starlearn_plants');
    if (saved) {
        plantState = JSON.parse(saved);
        const elapsed = (Date.now() - plantState.lastUpdate) / 1000;
        if (plantState.remainingTime > 0) {
            plantState.remainingTime = Math.max(0, plantState.remainingTime - elapsed);
        }
        if (plantState.water > 0) {
            plantState.water = Math.max(0, plantState.water - (elapsed / 3600) * WATER_DECAY_RATE);
        }
        if (plantState.nutrient > 0) {
            plantState.nutrient = Math.max(0, plantState.nutrient - (elapsed / 3600) * NUTRIENT_DECAY_RATE);
        }
    }
    plantState.seeds = parseInt(localStorage.getItem('starlearn_seeds') || '0');
}

function savePlantState() {
    plantState.lastUpdate = Date.now();
    localStorage.setItem('starlearn_plants', JSON.stringify(plantState));
}

function renderSeedCount() {
    const el = document.getElementById('seed-count');
    if (el) el.textContent = plantState.seeds;
}

function renderPlantCollection() {
    const grid = document.getElementById('plant-collection');
    if (!grid) return;
    grid.innerHTML = PLANT_DATA.map(plant => {
        const owned = plantState.ownedPlants.includes(plant.id);
        return `
            <div class="plant-collection-item ${owned ? 'owned' : ''}" onclick="selectPlant('${plant.id}')" title="${plant.desc}">
                <span class="emoji">${plant.emoji}</span>
                <span class="name">${plant.name}</span>
            </div>
        `;
    }).join('');
}

function selectPlant(plantId) {
    if (plantState.seeds <= 0 && !plantState.ownedPlants.includes(plantId)) {
        showTip('没有种子了！完成专注计时获得种子~');
        return;
    }
    const plant = PLANT_DATA.find(p => p.id === plantId);
    if (!plant) return;

    if (!plantState.ownedPlants.includes(plantId)) {
        plantState.seeds--;
        plantState.ownedPlants.push(plantId);
        localStorage.setItem('starlearn_seeds', String(plantState.seeds));
    }

    plantState.currentPlant = plantId;
    plantState.stage = 0;
    plantState.remainingTime = plant.growTime * 60;
    plantState.water = 50;
    plantState.nutrient = 50;

    savePlantState();
    renderSeedCount();
    renderPlantCollection();
    renderCurrentPlant();
    showTip(`成功种植「${plant.name}」！记得浇水施肥加速成长~`);
}

function renderCurrentPlant() {
    const display = document.getElementById('plant-display');
    const nameEl = document.getElementById('plant-name');
    const stageEl = document.getElementById('plant-stage');
    const timerEl = document.getElementById('plant-timer');
    const waterEl = document.getElementById('water-value');
    const nutrientEl = document.getElementById('nutrient-value');
    const harvestBtn = document.getElementById('harvest-btn');

    if (!plantState.currentPlant) {
        if (display) { display.textContent = '🌱'; display.className = 'plant-display seed'; }
        if (nameEl) nameEl.textContent = '选择你的第一株植物';
        if (stageEl) stageEl.textContent = '等待种植';
        if (timerEl) timerEl.textContent = '--:--:--';
        if (waterEl) waterEl.textContent = '0%';
        if (nutrientEl) nutrientEl.textContent = '0%';
        if (harvestBtn) harvestBtn.style.display = 'none';
        return;
    }

    const plant = PLANT_DATA.find(p => p.id === plantState.currentPlant);
    if (!plant) return;

    if (display) {
        display.textContent = plant.stages[plantState.stage];
        display.className = `plant-display ${['seed', 'sprout', 'growth', 'harvest'][plantState.stage]}`;
    }
    if (nameEl) nameEl.textContent = plant.name;
    if (stageEl) stageEl.textContent = STAGE_NAMES[plantState.stage];
    if (waterEl) waterEl.textContent = Math.round(plantState.water) + '%';
    if (nutrientEl) nutrientEl.textContent = Math.round(plantState.nutrient) + '%';

    if (harvestBtn) {
        harvestBtn.style.display = plantState.stage >= 3 ? 'flex' : 'none';
    }

    updateTimerDisplay();
}

function updateTimerDisplay() {
    const timerEl = document.getElementById('plant-timer');
    if (!timerEl) return;

    if (plantState.stage >= 3) {
        timerEl.textContent = '可收获!';
        timerEl.style.color = '#34d399';
        return;
    }

    const hours = Math.floor(plantState.remainingTime / 3600);
    const mins = Math.floor((plantState.remainingTime % 3600) / 60);
    const secs = Math.floor(plantState.remainingTime % 60);
    timerEl.textContent = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    timerEl.style.color = plantState.remainingTime < 300 ? '#f87171' : '#a78bfa';
}

function startGrowthTimer() {
    setInterval(() => {
        if (!plantState.currentPlant || plantState.stage >= 3) return;

        plantState.remainingTime = Math.max(0, plantState.remainingTime - 1);
        plantState.water = Math.max(0, plantState.water - (WATER_DECAY_RATE / 3600));
        plantState.nutrient = Math.max(0, plantState.nutrient - (NUTRIENT_DECAY_RATE / 3600));

        const plant = PLANT_DATA.find(p => p.id === plantState.currentPlant);
        if (plant) {
            const progress = 1 - (plantState.remainingTime / (plant.growTime * 60));
            const newStage = Math.min(3, Math.floor(progress * 4));
            if (newStage > plantState.stage) {
                plantState.stage = newStage;
                triggerStageUpEffect();
                showTip(`🎉 恭喜！${plant.name}进入${STAGE_NAMES[newStage]}阶段！`);
            }
        }

        savePlantState();
        renderCurrentPlant();
    }, 1000);
}

function plantAction(action) {
    if (!plantState.currentPlant) {
        showTip('请先在下方选择并种植一株植物~');
        return;
    }

    const display = document.getElementById('plant-display');
    const pot = document.getElementById('plant-pot');

    if (action === 'water') {
        plantState.water = Math.min(100, plantState.water + WATER_PER_ACTION);
        plantState.remainingTime = Math.max(0, plantState.remainingTime - WATER_TIME_REDUCTION);
        if (display) {
            display.classList.remove('plant-pulse-animation');
            void display.offsetWidth;
            display.classList.add('plant-pulse-animation');
        }
        if (pot) {
            pot.classList.remove('water-drop-animation');
            void pot.offsetWidth;
            pot.classList.add('water-drop-animation');
        }
        showTip('💧 浇水成功！水分+' + WATER_PER_ACTION + '%，生长时间缩短10分钟~');
    } else if (action === 'nutrient') {
        plantState.nutrient = Math.min(100, plantState.nutrient + NUTRIENT_PER_ACTION);
        plantState.remainingTime = Math.max(0, plantState.remainingTime - NUTRIENT_TIME_REDUCTION);
        if (display) {
            display.classList.remove('plant-pulse-animation');
            void display.offsetWidth;
            display.classList.add('plant-pulse-animation');
        }
        showTip('🧪 施肥成功！营养+' + NUTRIENT_PER_ACTION + '%，生长时间缩短30分钟~');
    } else if (action === 'harvest') {
        if (plantState.stage < 3) return;
        const plant = PLANT_DATA.find(p => p.id === plantState.currentPlant);
        triggerHarvestEffect();
        showTip('🌾 收获成功！恭喜获得一株成熟的「' + (plant ? plant.name : '植物') + '」！');
        plantState.currentPlant = null;
        plantState.stage = 0;
        plantState.remainingTime = 0;
        plantState.water = 0;
        plantState.nutrient = 0;
        savePlantState();
        renderCurrentPlant();
        renderPlantCollection();
        return;
    }

    savePlantState();
    renderCurrentPlant();
}

function triggerStageUpEffect() {
    const display = document.getElementById('plant-display');
    if (display) {
        display.classList.remove('plant-pulse-animation');
        void display.offsetWidth;
        display.classList.add('plant-pulse-animation');
    }
    triggerHarvestEffect();
}

function triggerHarvestEffect() {
    const container = document.getElementById('gold-rain');
    if (!container) return;

    const emojis = ['✨', '🌟', '💫', '⭐', '🌾', '🍃', '🌸', '💐'];
    for (let i = 0; i < 40; i++) {
        const particle = document.createElement('div');
        particle.className = 'gold-particle';
        particle.textContent = emojis[Math.floor(Math.random() * emojis.length)];
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 0.5 + 's';
        particle.style.animationDuration = (1.5 + Math.random()) + 's';
        container.appendChild(particle);
        setTimeout(() => particle.remove(), 3000);
    }
}

function showTip(message) {
    const tipEl = document.getElementById('plant-tip');
    if (tipEl) {
        tipEl.textContent = '💡 ' + message;
        tipEl.style.animation = 'none';
        void tipEl.offsetWidth;
        tipEl.style.animation = 'fadeIn 0.3s ease';
    }
}

function generateParticles() {
    const bg = document.getElementById('plant-bg');
    if (!bg) return;
    for (let i = 0; i < 25; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 15 + 's';
        particle.style.animationDuration = (10 + Math.random() * 10) + 's';
        particle.style.opacity = 0.2 + Math.random() * 0.4;
        bg.appendChild(particle);
    }
}

function goBack() {
    window.location.href = '/html/index.html';
}

document.addEventListener('DOMContentLoaded', init);
