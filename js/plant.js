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
// Weakened time reductions: water/ nutrient speed-up reduced to be less aggressive
const WATER_TIME_REDUCTION = 5 * 60; // 由 10 分钟 -> 5 分钟
const NUTRIENT_TIME_REDUCTION = 15 * 60; // 由 30 分钟 -> 15 分钟
const PLANT_SLOTS = 3; // 并行种植槽位数

let plantState = {
    seeds: 0,
    ownedPlants: [],
    slots: [], // 每个槽：{ plantId, stage, remainingTime, water, nutrient, lastUpdate }
    lastUpdate: Date.now()
};

let selectedPlantId = null; // 选中要种的植物id
let selectedSlotIndex = 0; // 当前查看的槽位

function init() {
    loadPlantState();
    renderSeedCount();
    renderPlantCollection();
    renderPlantPots();
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
        const parsed = JSON.parse(saved);
        // 兼容旧格式：如果存在 currentPlant 字段，则把它放到第一个槽
        if (parsed.slots && Array.isArray(parsed.slots)) {
            plantState = parsed;
        } else {
            // 旧格式兼容
            plantState = {
                seeds: parsed.seeds || 0,
                ownedPlants: parsed.ownedPlants || parsed.ownedPlants || [],
                slots: [] ,
                lastUpdate: parsed.lastUpdate || Date.now()
            };
            // 初始化槽位并填充第一个槽为旧的 currentPlant
            for (let i = 0; i < PLANT_SLOTS; i++) {
                plantState.slots.push({ plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() });
            }
            if (parsed.currentPlant) {
                plantState.slots[0] = {
                    plantId: parsed.currentPlant,
                    stage: parsed.stage || 0,
                    remainingTime: parsed.remainingTime || 0,
                    water: parsed.water || 0,
                    nutrient: parsed.nutrient || 0,
                    lastUpdate: parsed.lastUpdate || Date.now()
                };
            }
        }

        // 基于 lastUpdate 调整衰减
        const now = Date.now();
        plantState.slots.forEach(slot => {
            if (!slot || !slot.lastUpdate) slot.lastUpdate = now;
            const elapsed = (now - slot.lastUpdate) / 1000;
            if (slot.remainingTime > 0) slot.remainingTime = Math.max(0, slot.remainingTime - elapsed);
            if (slot.water > 0) slot.water = Math.max(0, slot.water - (elapsed / 3600) * WATER_DECAY_RATE);
            if (slot.nutrient > 0) slot.nutrient = Math.max(0, slot.nutrient - (elapsed / 3600) * NUTRIENT_DECAY_RATE);
            slot.lastUpdate = now;
        });
    } else {
        // 未保存，初始化槽位
        plantState.slots = [];
        for (let i = 0; i < PLANT_SLOTS; i++) plantState.slots.push({ plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() });
    }
    plantState.seeds = parseInt(localStorage.getItem('starlearn_seeds') || (plantState.seeds || '0'));
}

function savePlantState() {
    plantState.lastUpdate = Date.now();
    // 也保留兼容字段（第一个非空槽）便于旧页面读取
    const legacy = {};
    const firstSlot = plantState.slots.find(s => s && s.plantId);
    if (firstSlot) {
        legacy.currentPlant = firstSlot.plantId;
        legacy.stage = firstSlot.stage;
        legacy.remainingTime = firstSlot.remainingTime;
        legacy.water = firstSlot.water;
        legacy.nutrient = firstSlot.nutrient;
    }
    const toSave = { ...plantState, ...legacy };
    localStorage.setItem('starlearn_plants', JSON.stringify(toSave));
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
        const active = selectedPlantId === plant.id ? 'selected' : '';
        return `
            <div class="plant-collection-item ${owned ? 'owned' : ''} ${active}" onclick="selectPlant('${plant.id}')" title="${plant.desc}">
                <span class="emoji">${plant.emoji}</span>
                <span class="name">${plant.name}</span>
            </div>
        `;
    }).join('');
}

function selectPlant(plantId) {
    // 切换选择（不立刻种植），用户需点击「种植」按钮确认
    selectedPlantId = plantId;
    renderPlantCollection();
    const plant = PLANT_DATA.find(p => p.id === plantId);
    if (plant) showTip(`已选择 ${plant.name}。点击“种植”开始栽种（消耗 1 个种子）。`);
}

function plantSeed() {
    if (!selectedPlantId) { showTip('请先从下方选择一种植物。'); return; }
    // 找到一个空槽位优先使用选择的槽位
    let targetIdx = selectedSlotIndex;
    const slot = plantState.slots[targetIdx];
    // 如果选中槽有植物，尝试寻找第一个空槽
    if (slot && slot.plantId) {
        targetIdx = plantState.slots.findIndex(s => !s.plantId);
        if (targetIdx === -1) { showTip('所有槽位均已占用，请收获或移除后再种植。'); return; }
    }

    if (plantState.seeds <= 0) { showTip('没有种子了！完成专注计时获得种子~'); return; }

    const plant = PLANT_DATA.find(p => p.id === selectedPlantId);
    if (!plant) return;

    plantState.seeds = Math.max(0, plantState.seeds - 1);
    plantState.ownedPlants = Array.from(new Set([...plantState.ownedPlants, selectedPlantId]));

    // 初始化槽位
    plantState.slots[targetIdx] = {
        plantId: selectedPlantId,
        stage: 0,
        remainingTime: plant.growTime * 60,
        water: 50,
        nutrient: 50,
        lastUpdate: Date.now()
    };

    // 动画：对应槽位的 pot 摇动与生长脉冲
    const pot = document.querySelector(`.plant-pot[data-slot='${targetIdx}']`);
    const display = document.getElementById(`plant-display-${targetIdx}`) || document.getElementById('plant-display');
    if (pot) {
        pot.classList.remove('plant-pot-planting');
        void pot.offsetWidth;
        pot.classList.add('plant-pot-planting');
    }
    if (display) {
        display.classList.remove('plant-grow-anim');
        void display.offsetWidth;
        display.classList.add('plant-grow-anim');
    }

    localStorage.setItem('starlearn_seeds', String(plantState.seeds));
    savePlantState();
    renderSeedCount();
    renderPlantCollection();
    renderPlantPots();
    // 切换查看到新种植的槽
    selectedSlotIndex = targetIdx;
    renderCurrentPlant();
    showTip(`成功在槽位 ${targetIdx+1} 种植「${plant.name}」！浇水或施肥可加速成长`);

    // 同步到个人中心
    try { localStorage.setItem('starlearn_plants', JSON.stringify(plantState)); } catch(e) {}
}

function renderPlantPots() {
    const container = document.getElementById('plant-pots');
    if (!container) return;
    container.innerHTML = '';
    plantState.slots.forEach((slot, idx) => {
        const plant = slot && slot.plantId ? PLANT_DATA.find(p => p.id === slot.plantId) : null;
        const emoji = plant ? plant.stages[slot.stage] : '🌱';
        const cls = plant ? ['seed','sprout','growth','harvest'][slot.stage] : 'seed';
        const ownedClass = slot.plantId ? 'occupied' : 'empty';
        const selectedClass = idx === selectedSlotIndex ? ' selected' : '';
        const html = `
            <div class="plant-pot ${ownedClass}${selectedClass}" data-slot="${idx}" onclick="selectSlot(${idx})">
                <div class="plant-display ${cls}" id="plant-display-${idx}">${emoji}</div>
                <div class="slot-index">#${idx+1}</div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });
}

function renderCurrentPlant() {
    // 渲染主面板，基于 selectedSlotIndex
    const slot = plantState.slots[selectedSlotIndex];
    const display = document.getElementById('plant-display');
    const nameEl = document.getElementById('plant-name');
    const stageEl = document.getElementById('plant-stage');
    const timerEl = document.getElementById('plant-timer');
    const waterEl = document.getElementById('water-value');
    const nutrientEl = document.getElementById('nutrient-value');
    const harvestBtn = document.getElementById('harvest-btn');

    if (!slot || !slot.plantId) {
        if (display) { display.textContent = '🌱'; display.className = 'plant-display seed'; }
        if (nameEl) nameEl.textContent = '选择你的第一株植物';
        if (stageEl) stageEl.textContent = '等待种植';
        if (timerEl) timerEl.textContent = '--:--:--';
        if (waterEl) waterEl.textContent = '0%';
        if (nutrientEl) nutrientEl.textContent = '0%';
        if (harvestBtn) harvestBtn.style.display = 'none';
        return;
    }

    const plant = PLANT_DATA.find(p => p.id === slot.plantId);
    if (!plant) return;

    if (display) {
        display.textContent = plant.stages[slot.stage];
        display.className = `plant-display ${['seed', 'sprout', 'growth', 'harvest'][slot.stage]}`;
    }
    if (nameEl) nameEl.textContent = plant.name;
    if (stageEl) stageEl.textContent = STAGE_NAMES[slot.stage];
    if (waterEl) waterEl.textContent = Math.round(slot.water) + '%';
    if (nutrientEl) nutrientEl.textContent = Math.round(slot.nutrient) + '%';

    if (harvestBtn) {
        harvestBtn.style.display = slot.stage >= 3 ? 'flex' : 'none';
    }

    updateTimerDisplay();
}

function updateTimerDisplay() {
    const timerEl = document.getElementById('plant-timer');
    if (!timerEl) return;
    const slot = plantState.slots[selectedSlotIndex];
    if (!slot || !slot.plantId) {
        timerEl.textContent = '--:--:--';
        timerEl.style.color = '#a78bfa';
        return;
    }

    if (slot.stage >= 3) {
        timerEl.textContent = '可收获!';
        timerEl.style.color = '#34d399';
        return;
    }

    const hours = Math.floor(slot.remainingTime / 3600);
    const mins = Math.floor((slot.remainingTime % 3600) / 60);
    const secs = Math.floor(slot.remainingTime % 60);
    timerEl.textContent = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    timerEl.style.color = slot.remainingTime < 300 ? '#f87171' : '#a78bfa';
}

function startGrowthTimer() {
    setInterval(() => {
        const now = Date.now();
        let changed = false;
        plantState.slots.forEach((slot, idx) => {
            if (!slot || !slot.plantId || slot.stage >= 3) return;
            slot.remainingTime = Math.max(0, slot.remainingTime - 1);
            slot.water = Math.max(0, slot.water - (WATER_DECAY_RATE / 3600));
            slot.nutrient = Math.max(0, slot.nutrient - (NUTRIENT_DECAY_RATE / 3600));

            const plant = PLANT_DATA.find(p => p.id === slot.plantId);
            if (plant) {
                const progress = 1 - (slot.remainingTime / (plant.growTime * 60));
                const newStage = Math.min(3, Math.floor(progress * 4));
                if (newStage > slot.stage) {
                    slot.stage = newStage;
                    triggerStageUpEffect(idx);
                    showTip(`🎉 恭喜！${plant.name}进入${STAGE_NAMES[newStage]}阶段！（槽位 ${idx+1}）`);
                }
            }
            slot.lastUpdate = now;
            changed = true;
        });

        if (changed) {
            savePlantState();
            renderPlantPots();
            renderCurrentPlant();
        }
    }, 1000);
}

function plantAction(action) {
    const slot = plantState.slots[selectedSlotIndex];
    if (!slot || !slot.plantId) { showTip('请先选择一个已种植的槽位或种植新的植物~'); return; }

    const displayEl = document.getElementById(`plant-display-${selectedSlotIndex}`) || document.getElementById('plant-display');
    const potEl = document.querySelector(`.plant-pot[data-slot='${selectedSlotIndex}']`);

    if (action === 'water') {
        slot.water = Math.min(100, slot.water + WATER_PER_ACTION);
        slot.remainingTime = Math.max(0, slot.remainingTime - WATER_TIME_REDUCTION);
        if (displayEl) {
            displayEl.classList.remove('plant-pulse-animation');
            void displayEl.offsetWidth;
            displayEl.classList.add('plant-pulse-animation');
        }
        if (potEl) {
            potEl.classList.remove('water-drop-animation');
            void potEl.offsetWidth;
            potEl.classList.add('water-drop-animation');
        }
        showTip('💧 浇水成功！水分+' + WATER_PER_ACTION + '%，生长时间缩短10分钟~');
    } else if (action === 'nutrient') {
        slot.nutrient = Math.min(100, slot.nutrient + NUTRIENT_PER_ACTION);
        slot.remainingTime = Math.max(0, slot.remainingTime - NUTRIENT_TIME_REDUCTION);
        if (displayEl) {
            displayEl.classList.remove('plant-pulse-animation');
            void displayEl.offsetWidth;
            displayEl.classList.add('plant-pulse-animation');
        }
        showTip('🧪 施肥成功！营养+' + NUTRIENT_PER_ACTION + '%，生长时间缩短30分钟~');
    } else if (action === 'harvest') {
        if (slot.stage < 3) return;
        const plant = PLANT_DATA.find(p => p.id === slot.plantId);
        triggerHarvestEffect();
        // 右上角推送通知（iOS 风格液态玻璃）
        if (window.starlearnNotifications && typeof window.starlearnNotifications.showNotification === 'function') {
            window.starlearnNotifications.showNotification({
                title: '🌾 收获成功',
                content: `你收获了成熟的「${plant ? plant.name : '植物'}」！`,
                actionLabel: '查看林场',
                actionUrl: '/html/plant.html',
                type: 'achievement'
            });
        }
        showTip('🌾 收获成功！恭喜获得一株成熟的「' + (plant ? plant.name : '植物') + '」！');
        // 清空槽位
        plantState.slots[selectedSlotIndex] = { plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() };
        savePlantState();
        renderPlantPots();
        renderCurrentPlant();
        renderPlantCollection();
        return;
    }

    // 保存并更新UI
    savePlantState();
    renderPlantPots();
    renderCurrentPlant();
}

function triggerStageUpEffect(slotIndex) {
    // 播放单槽的阶段升级动画
    const display = document.getElementById(`plant-display-${slotIndex}`) || document.getElementById('plant-display');
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

function selectSlot(idx) {
    selectedSlotIndex = idx;
    renderPlantPots();
    renderCurrentPlant();
    const slot = plantState.slots[idx];
    if (!slot || !slot.plantId) {
        showTip(`槽位 ${idx+1} 为空，选择左侧植物并点击【种植】开始种植。`);
    } else {
        const plant = PLANT_DATA.find(p => p.id === slot.plantId);
        if (plant) showTip(`已查看槽位 ${idx+1}：${plant.name} - ${STAGE_NAMES[slot.stage]}`);
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
