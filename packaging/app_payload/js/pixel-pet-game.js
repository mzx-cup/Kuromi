// 宠物数据
const PETS = [
    { id: 'cat', name: '星喵', emoji: '🐱', class: 'pixel-cat', unlocked: true, desc: '优雅的猫咪', personality: '高冷' },
    { id: 'dog', name: '星汪', emoji: '🐶', class: 'pixel-dog', unlocked: true, desc: '忠诚的狗狗', personality: '活泼' },
    { id: 'rabbit', name: '星兔', emoji: '🐰', class: 'pixel-rabbit', unlocked: true, desc: '温柔的兔子', personality: '害羞' },
    { id: 'hamster', name: '星鼠', emoji: '🐹', class: 'pixel-hamster', unlocked: true, desc: '可爱的仓鼠', personality: '贪吃' },
    { id: 'bear', name: '星熊', emoji: '🐻', class: 'pixel-bear', unlocked: true, desc: '守护大熊', personality: '稳重' },
    { id: 'fox', name: '星狐', emoji: '🦊', class: 'pixel-fox', unlocked: false, desc: '机智的狐狸', cost: 50, personality: '聪明' },
    { id: 'deer', name: '星鹿', emoji: '🦌', class: 'pixel-deer', unlocked: false, desc: '优雅的小鹿', cost: 80, personality: '优雅' },
    { id: 'koala', name: '星考拉', emoji: '🐨', class: 'pixel-koala', unlocked: false, desc: '慵懒的考拉', cost: 100, personality: '慵懒' },
    { id: 'penguin', name: '星企鹅', emoji: '🐧', class: 'pixel-penguin', unlocked: false, desc: '呆萌的企鹅', cost: 120, personality: '可爱' },
    { id: 'panda', name: '星熊猫', emoji: '🐼', class: 'pixel-panda', unlocked: false, desc: '国宝熊猫', cost: 200, personality: '憨厚' }
];

// 表情数据
const EMOTIONS = {
    happy: ['😊', '😄', '🥰', '✨', '🎉'],
    sad: ['😢', '😿', '💔', '😔', '🥺'],
    hungry: ['🍖', '🤤', '😋', '🥩', '🍗'],
    playful: ['🎮', '🎾', '🎉', '🎊', '🎈'],
    tired: ['💤', '😴', '🥱', '😪', '💫'],
    love: ['💕', '💗', '❤️', '🥺', '💖'],
    angry: ['😤', '😾', '💢', '😠'],
    curious: ['🤔', '👀', '❓', '🧐']
};

// 状态消息
const STATUS_MESSAGES = {
    happy: ['心情超好！', '好开心呀~', '今天真棒！', '嘿嘿嘿~', '学习进展顺利哦～', '你做得很好，继续加油！'],
    sad: ['有点难过...', '呜呜呜', '不开心...', '想哭了', '今天学习好累...'],
    hungry: ['肚子饿了...', '想吃东西~', '有吃的吗？', '好饿啊', '吃点零食，补充能量再学习~'],
    tired: ['好困...', '想睡觉~', 'Zzz...', '累了...', '先休息一下吧，学习效率更高~'],
    playful: ['一起玩吧！', '好无聊~', '想玩耍！', '来玩游戏！', '休息一下，刷道题如何？', '小游戏后再学习会更带劲~'],
    love: ['好喜欢你！', '抱抱~', '最爱你了！', '么么哒~', '你学到新知识了，我好替你高兴！']
};

// 游戏状态
let gameState = {
    coins: 100,
    stars: 0,
    currentPet: 0,
    hunger: 80,
    happiness: 70,
    energy: 90,
    intimacy: 50, // 新增亲密度
    level: 1,
    exp: 0,
    lastUpdate: Date.now(),
    miniGameScore: 0,
    miniGameActive: false,
    gameHour: 12,
    weather: 'clear'
};

// 从 starlearn_pet 同步状态（与个人中心同步）
function syncFromPersonalCenter() {
    const savedPet = localStorage.getItem('starlearn_pet');
    if (savedPet) {
        const petData = JSON.parse(savedPet);
        // 同步饱食度、情绪、亲密度
        gameState.hunger = petData.satiety || 80;
        gameState.happiness = petData.mood || 70;
        gameState.intimacy = petData.intimacy || 50;
    }
}

// 同步状态到个人中心
function syncToPersonalCenter() {
    const savedPet = localStorage.getItem('starlearn_pet');
    let petData = savedPet ? JSON.parse(savedPet) : {
        emoji: '🐱',
        name: '星宝',
        satiety: 80,
        mood: 70,
        intimacy: 50,
        lastInteraction: Date.now(),
        pressureLevel: 'low'
    };

    // 保证头像和名称与当前选择的宠物同步
    try {
        const pet = PETS[gameState.currentPet];
        if (pet) {
            petData.emoji = pet.emoji || petData.emoji;
            petData.name = pet.name || petData.name;
        }
    } catch (err) {}

    petData.satiety = Math.round(gameState.hunger);
    petData.mood = Math.round(gameState.happiness);
    petData.intimacy = Math.round(gameState.intimacy);
    petData.lastInteraction = Date.now();

    localStorage.setItem('starlearn_pet', JSON.stringify(petData));
}

// 初始化
function init() {
    loadGameState();
    syncFromPersonalCenter(); // 从个人中心同步
    createStars();
    createClouds();
    createFireflies();
    createBubbles();
    renderPetSelector();
    renderCurrentPet();
    startGameLoop();
    updateTime();
    setInterval(updateTime, 60000);
}

// 创建星星
function createStars() {
    const container = document.getElementById('stars-layer');
    for (let i = 0; i < 80; i++) {
        const star = document.createElement('div');
        const size = Math.random() < 0.6 ? 'small' : (Math.random() < 0.8 ? 'medium' : 'large');
        star.className = `star ${size}`;
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 50 + '%';
        star.style.animationDelay = Math.random() * 3 + 's';
        container.appendChild(star);
    }
}

// 创建云朵
function createClouds() {
    const container = document.getElementById('clouds-layer');
    for (let i = 0; i < 4; i++) {
        const cloud = document.createElement('div');
        cloud.className = 'cloud';
        cloud.style.width = (60 + Math.random() * 60) + 'px';
        cloud.style.height = (20 + Math.random() * 20) + 'px';
        cloud.style.top = (30 + Math.random() * 100) + 'px';
        cloud.style.animationDuration = (30 + Math.random() * 30) + 's';
        cloud.style.animationDelay = (-Math.random() * 30) + 's';
        container.appendChild(cloud);
    }
}

// 创建萤火虫
function createFireflies() {
    const container = document.getElementById('fireflies-container');
    if (!container) return;
    for (let i = 0; i < 15; i++) {
        const firefly = document.createElement('div');
        firefly.className = 'firefly';
        firefly.style.left = (10 + Math.random() * 80) + '%';
        firefly.style.top = (20 + Math.random() * 40) + '%';
        firefly.style.animationDelay = Math.random() * 2 + 's';
        firefly.style.animationDuration = (1.5 + Math.random() * 1) + 's';
        container.appendChild(firefly);
    }
}

// 创建气泡
function createBubbles() {
    const container = document.getElementById('bubbles-container');
    if (!container) return;
    for (let i = 0; i < 8; i++) {
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        const size = 8 + Math.random() * 16;
        bubble.style.width = size + 'px';
        bubble.style.height = size + 'px';
        bubble.style.left = (10 + Math.random() * 80) + '%';
        bubble.style.bottom = '0';
        bubble.style.animationDuration = (4 + Math.random() * 4) + 's';
        bubble.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(bubble);
    }
}

// 渲染宠物选择器
function renderPetSelector() {
    const grid = document.getElementById('pet-grid');
    grid.innerHTML = '';

    PETS.forEach((pet, index) => {
        const slot = document.createElement('div');
        slot.className = 'pet-slot' + (index === gameState.currentPet ? ' active' : '') + (!pet.unlocked ? ' locked' : '');
        slot.onclick = () => selectPet(index);

        slot.innerHTML = pet.unlocked ? pet.emoji : '❓';
        slot.title = pet.unlocked ? `${pet.name} - ${pet.personality}` : `需要 ${pet.cost} 金币解锁`;

        grid.appendChild(slot);
    });
}

// 渲染当前宠物
function renderCurrentPet() {
    const pet = PETS[gameState.currentPet];
    if (!pet.unlocked) return;

    document.getElementById('pet-avatar').textContent = pet.emoji;
    document.getElementById('pet-name').textContent = pet.name;

    const sprite = document.getElementById('pet-sprite');
    sprite.className = `pet-sprite ${pet.class}`;
    createPixelPet(sprite, pet.id);

    updateMood();
}

// 创建像素宠物
function createPixelPet(container, type) {
    const templates = {
        cat: `
            <div class="tail"></div>
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"></div>
            <div class="ear right"></div>
            <div class="ear-inner left"></div>
            <div class="ear-inner right"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="mouth"></div>
            <div class="whisker left-1"></div>
            <div class="whisker left-2"></div>
            <div class="whisker right-1"></div>
            <div class="whisker right-2"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        dog: `
            <div class="tail"></div>
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"></div>
            <div class="ear right"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="tongue"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        rabbit: `
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"><div class="ear-inner"></div></div>
            <div class="ear right"><div class="ear-inner"></div></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="cheek left"></div>
            <div class="cheek right"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        hamster: `
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"></div>
            <div class="ear right"></div>
            <div class="cheek left"></div>
            <div class="cheek right"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        bear: `
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"></div>
            <div class="ear right"></div>
            <div class="muzzle"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        fox: `
            <div class="tail"><div class="tail-tip"></div></div>
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"></div>
            <div class="ear right"></div>
            <div class="ear-inner left"></div>
            <div class="ear-inner right"></div>
            <div class="muzzle"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        deer: `
            <div class="body"></div>
            <div class="head"></div>
            <div class="antler left"></div>
            <div class="antler right"></div>
            <div class="ear left"></div>
            <div class="ear right"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        koala: `
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"><div class="ear-inner"></div></div>
            <div class="ear right"><div class="ear-inner"></div></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        penguin: `
            <div class="flipper left"></div>
            <div class="flipper right"></div>
            <div class="body"></div>
            <div class="belly"></div>
            <div class="head"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="beak"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `,
        panda: `
            <div class="body"></div>
            <div class="head"></div>
            <div class="ear left"></div>
            <div class="ear right"></div>
            <div class="eye-patch left"></div>
            <div class="eye-patch right"></div>
            <div class="eye left"></div>
            <div class="eye right"></div>
            <div class="nose"></div>
            <div class="mouth"></div>
            <div class="blush left"></div>
            <div class="blush right"></div>
        `
    };

    // Wrap template in a consistent frame to avoid layout issues across pets
    container.innerHTML = `<div class="pet-frame">${templates[type] || templates.cat}</div>`;
}

// 选择宠物
function selectPet(index) {
    const pet = PETS[index];

    if (!pet.unlocked) {
        if (gameState.coins >= pet.cost) {
            if (confirm(`花费 ${pet.cost} 金币解锁 ${pet.name}？`)) {
                gameState.coins -= pet.cost;
                PETS[index].unlocked = true;
                updateCoins();
                showAchievement('🎉', '解锁成功！', `欢迎 ${pet.name} 加入！`);
            }
        } else {
            showEmotion('💸', `还需要 ${pet.cost - gameState.coins} 金币`);
            return;
        }
    }

    gameState.currentPet = index;
    renderPetSelector();
    renderCurrentPet();

    const container = document.getElementById('pet-container');
    container.classList.remove('idle');
    container.classList.add('jumping');
    setTimeout(() => {
        container.classList.remove('jumping');
        container.classList.add('idle');
    }, 500);

    showEmotion('✨', `${pet.name} 出来啦！`);
    saveGameState();
    // 同步到个人中心，保持两个页面的头像/状态一致
    syncToPersonalCenter();
}

// 喂食
function feedPet() {
    if (gameState.hunger >= 100) {
        showEmotion('😋', '我已经很饱啦！');
        return;
    }

    gameState.hunger = Math.min(100, gameState.hunger + 10);
    gameState.happiness = Math.min(100, gameState.happiness + 5);
    gameState.intimacy = Math.min(100, gameState.intimacy + 2);
    updateStatus();

    const container = document.getElementById('pet-container');
    container.classList.remove('idle');
    container.classList.add('eating');
    const sprite = document.getElementById('pet-sprite');
    if (sprite) {
        sprite.classList.add('bounce');
        setTimeout(() => sprite.classList.remove('bounce'), 700);
    }
    setTimeout(() => {
        container.classList.remove('eating');
        container.classList.add('idle');
    }, 1500);

    showEmotion(getRandomEmotion('hungry'), getRandomMessage('happy'));
    createFloatingFood('🍖');
    createParticles(6, '#ffa500');
    addExp(5);
    saveGameState();
    syncToPersonalCenter();

    // 成就触发：喂食
    if (window.AchievementManager) {
        AchievementManager.incrementStat('pet_feed');
    }
}

// 玩耍
function playWithPet() {
    if (gameState.energy < 15) {
        showEmotion('😴', '我太累了，让我休息一下...');
        return;
    }

    gameState.happiness = Math.min(100, gameState.happiness + 20);
    gameState.intimacy = Math.min(100, gameState.intimacy + 5);
    gameState.energy = Math.max(0, gameState.energy - 15);
    gameState.hunger = Math.max(0, gameState.hunger - 8);
    updateStatus();

    const container = document.getElementById('pet-container');
    container.classList.remove('idle');
    container.classList.add('happy');
    const sprite = document.getElementById('pet-sprite');
    if (sprite) {
        sprite.classList.add('bounce');
        setTimeout(() => sprite.classList.remove('bounce'), 1000);
    }
    setTimeout(() => {
        container.classList.remove('happy');
        container.classList.add('idle');
    }, 2500);

    showEmotion(getRandomEmotion('playful'), getRandomMessage('happy'));
    createFloatingFood('🎾');
    createParticles(10, '#ff69b4');
    addExp(8);
    saveGameState();
    syncToPersonalCenter();

    // 成就触发：玩耍
    if (window.AchievementManager) {
        AchievementManager.incrementStat('pet_play');
    }
}

// 抚摸
function petThePet() {
    gameState.happiness = Math.min(100, gameState.happiness + 12);
    gameState.intimacy = Math.min(100, gameState.intimacy + 8);
    gameState.energy = Math.min(100, gameState.energy + 3);
    updateStatus();

    const container = document.getElementById('pet-container');
    container.classList.remove('idle');
    container.classList.add('happy');
    const sprite = document.getElementById('pet-sprite');
    if (sprite) {
        sprite.classList.add('bounce');
        setTimeout(() => sprite.classList.remove('bounce'), 700);
    }
    setTimeout(() => {
        container.classList.remove('happy');
        container.classList.add('idle');
    }, 1500);

    showEmotion(getRandomEmotion('love'), getRandomMessage('love'));
    createParticles(8, '#ff1493');
    addExp(3);
    saveGameState();
    syncToPersonalCenter();

    // 成就触发：亲密度检查
    if (window.AchievementManager) {
        const intimacy = Math.round(gameState.intimacy);
        AchievementManager.incrementStat('pet_intimacy', intimacy);
    }
}

// 休息
function letRest() {
    gameState.energy = Math.min(100, gameState.energy + 35);
    gameState.hunger = Math.max(0, gameState.hunger - 5);
    updateStatus();

    const container = document.getElementById('pet-container');
    container.classList.remove('idle');
    container.classList.add('sleeping');
    setTimeout(() => {
        container.classList.remove('sleeping');
        container.classList.add('idle');
    }, 3000);

    showEmotion('💤', 'Zzz...');
    saveGameState();
    syncToPersonalCenter();
}

// 显示表情
function showEmotion(emoji, text) {
    const container = document.getElementById('pet-container');
    const oldBubble = container.querySelector('.emotion-bubble');
    if (oldBubble) oldBubble.remove();

    const bubble = document.createElement('div');
    bubble.className = 'emotion-bubble';
    bubble.innerHTML = `${emoji} ${text}`;
    container.appendChild(bubble);

    setTimeout(() => bubble.remove(), 2500);
}

// 获取随机表情
function getRandomEmotion(type) {
    const emotions = EMOTIONS[type] || EMOTIONS.happy;
    return emotions[Math.floor(Math.random() * emotions.length)];
}

// 获取随机消息
function getRandomMessage(type) {
    const messages = STATUS_MESSAGES[type] || STATUS_MESSAGES.happy;
    return messages[Math.floor(Math.random() * messages.length)];
}

// 创建漂浮食物
function createFloatingFood(emoji) {
    const container = document.getElementById('pet-container');
    const rect = container.getBoundingClientRect();

    const food = document.createElement('div');
    food.className = 'floating-food';
    food.innerHTML = emoji;
    food.style.left = (rect.left + rect.width / 2 - 14) + 'px';
    food.style.top = (rect.top - 50) + 'px';
    document.body.appendChild(food);

    setTimeout(() => food.remove(), 1000);
}

// 创建粒子
function createParticles(count, color) {
    const container = document.getElementById('pet-container');
    const rect = container.getBoundingClientRect();

    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.innerHTML = ['✨', '⭐', '💫', '🌟'][Math.floor(Math.random() * 4)];
        particle.style.left = (rect.left + rect.width / 2) + 'px';
        particle.style.top = (rect.top + rect.height / 2) + 'px';
        particle.style.setProperty('--tx', (Math.random() - 0.5) * 120 + 'px');
        particle.style.setProperty('--ty', -Math.random() * 100 - 30 + 'px');
        document.body.appendChild(particle);

        setTimeout(() => particle.remove(), 1500);
    }
}

// 更新状态
function updateStatus() {
    document.getElementById('hunger-value').textContent = Math.round(gameState.hunger) + '%';
    document.getElementById('hunger-bar').style.width = gameState.hunger + '%';

    document.getElementById('happiness-value').textContent = Math.round(gameState.happiness) + '%';
    document.getElementById('happiness-bar').style.width = gameState.happiness + '%';

    document.getElementById('energy-value').textContent = Math.round(gameState.energy) + '%';
    document.getElementById('energy-bar').style.width = gameState.energy + '%';

    // 更新亲密度
    const intimacyValue = document.getElementById('intimacy-value');
    const intimacyBar = document.getElementById('intimacy-bar');
    if (intimacyValue) intimacyValue.textContent = Math.round(gameState.intimacy) + '%';
    if (intimacyBar) intimacyBar.style.width = gameState.intimacy + '%';

    updateMood();
}

// 更新心情
function updateMood() {
    const moodEl = document.getElementById('pet-mood');
    const avg = (gameState.hunger + gameState.happiness + gameState.energy) / 3;

    if (avg >= 80) {
        moodEl.textContent = '😊 超级开心';
    } else if (avg >= 60) {
        moodEl.textContent = '😄 心情不错';
    } else if (avg >= 40) {
        moodEl.textContent = '😐 一般般';
    } else if (avg >= 20) {
        moodEl.textContent = '😢 有点难过';
    } else {
        moodEl.textContent = '😭 很不开心';
    }
}

// 更新金币
function updateCoins() {
    document.getElementById('coins').textContent = gameState.coins;
}

// 添加经验
function addExp(amount) {
    gameState.exp += amount;
    const expNeeded = gameState.level * 100;
    if (gameState.exp >= expNeeded) {
        gameState.exp -= expNeeded;
        gameState.level++;
        showAchievement('⬆️', '升级了！', `达到 Lv.${gameState.level}`);
    }
}

// 显示成就
function showAchievement(icon, title, desc) {
    const popup = document.createElement('div');
    popup.className = 'achievement-popup';
    popup.innerHTML = `
        <span class="icon">${icon}</span>
        <div class="title">${title}</div>
        <div class="desc">${desc}</div>
    `;
    document.body.appendChild(popup);

    setTimeout(() => popup.remove(), 3000);
}

// 更新时间
function updateTime() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();

    document.getElementById('game-time').textContent =
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;

    const periodEl = document.getElementById('time-period');
    const sky = document.getElementById('sky');
    const moon = document.getElementById('moon');

    if (hours >= 6 && hours < 12) {
        periodEl.textContent = '☀️ 早晨';
        sky.className = 'sky';
        moon.style.opacity = '0';
    } else if (hours >= 12 && hours < 18) {
        periodEl.textContent = '🌤️ 下午';
        sky.className = 'sky';
        moon.style.opacity = '0';
    } else if (hours >= 18 && hours < 21) {
        periodEl.textContent = '🌅 傍晚';
        sky.className = 'sky sunset';
        moon.style.opacity = '0.5';
    } else {
        periodEl.textContent = '🌙 夜晚';
        sky.className = 'sky night';
        moon.style.opacity = '1';
    }

    gameState.gameHour = hours;
}

// 游戏循环
function startGameLoop() {
    setInterval(() => {
        const now = Date.now();
        const delta = (now - gameState.lastUpdate) / 1000;
        gameState.lastUpdate = now;

        // 状态缓慢消耗（降低消耗速度）
        gameState.hunger = Math.max(0, gameState.hunger - 0.03 * delta);
        gameState.happiness = Math.max(0, gameState.happiness - 0.02 * delta);
        gameState.energy = Math.min(100, gameState.energy + 0.05 * delta);

        updateStatus();

        // 随机移动
        if (Math.random() < 0.05) {
            movePetRandom();
        }

        // 随机表情
        if (Math.random() < 0.03) {
            const avg = (gameState.hunger + gameState.happiness + gameState.energy) / 3;
            let type = 'happy';
            if (gameState.hunger < 30) type = 'hungry';
            else if (gameState.happiness < 30) type = 'sad';
            else if (gameState.energy < 30) type = 'tired';
            showEmotion(getRandomEmotion(type), '');
        }

        // 随机获得金币
        if (Math.random() < 0.01) {
            gameState.coins += 1;
            gameState.stars += 1;
            updateCoins();
            document.getElementById('stars').textContent = gameState.stars;
        }

        saveGameState();
        syncToPersonalCenter(); // 同步到个人中心
    }, 1000);
}

// 随机移动
function movePetRandom() {
    const container = document.getElementById('pet-container');
    const newX = 15 + Math.random() * 70;

    container.classList.remove('idle');
    container.classList.add('walking');
    container.style.left = newX + '%';

    setTimeout(() => {
        container.classList.remove('walking');
        container.classList.add('idle');
    }, 800);
}

// 小游戏状态
let miniGameState = {
    active: false,
    score: 0,
    timeLeft: 60,
    combo: 0,
    maxCombo: 0,
    timer: null,
    spawnTimer: null,
    items: [],
    basketX: 0,
    gameDuration: 60
};

// 小游戏
function startMiniGame() {
    const overlay = document.getElementById('mini-game');
    overlay.classList.add('active');

    // 显示时间选择界面
    document.getElementById('time-select').classList.add('active');
    document.getElementById('game-over').classList.remove('active');

    // 重置状态
    miniGameState.score = 0;
    miniGameState.combo = 0;
    miniGameState.maxCombo = 0;
    miniGameState.active = false;

    document.getElementById('game-score').textContent = '0';
    document.getElementById('combo-display').classList.remove('active');

    initBasket();
}

function startGameWithTime(duration) {
    miniGameState.gameDuration = duration;
    miniGameState.timeLeft = duration;
    miniGameState.active = true;
    miniGameState.score = 0;
    miniGameState.combo = 0;
    miniGameState.maxCombo = 0;

    document.getElementById('time-select').classList.remove('active');
    document.getElementById('game-timer').textContent = duration;
    document.getElementById('game-timer').classList.remove('warning');
    document.getElementById('game-score').textContent = '0';
    document.getElementById('game-level-badge').textContent = 'Lv.' + gameState.level;

    // 清除旧物品
    const overlay = document.getElementById('mini-game');
    overlay.querySelectorAll('.falling-item, .score-float, .catch-star').forEach(el => el.remove());

    startGameTimer();
    spawnGameItems();
}

function initBasket() {
    const basket = document.getElementById('basket-container');
    const overlay = document.getElementById('mini-game');

    // 初始位置居中
    const overlayRect = overlay.getBoundingClientRect();
    miniGameState.basketX = overlayRect.width / 2 - 50;
    basket.style.left = miniGameState.basketX + 'px';

    // 鼠标拖动
    let isDragging = false;
    let startX = 0;
    let basketStartX = 0;

    basket.addEventListener('mousedown', (e) => {
        if (!miniGameState.active) return;
        isDragging = true;
        startX = e.clientX;
        basketStartX = miniGameState.basketX;
        basket.style.cursor = 'grabbing';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging || !miniGameState.active) return;
        const deltaX = e.clientX - startX;
        let newX = basketStartX + deltaX;

        // 边界限制
        const maxX = overlayRect.width - 100;
        newX = Math.max(0, Math.min(maxX, newX));

        miniGameState.basketX = newX;
        basket.style.left = newX + 'px';
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        basket.style.cursor = 'grab';
    });

    // 触摸拖动
    basket.addEventListener('touchstart', (e) => {
        if (!miniGameState.active) return;
        isDragging = true;
        startX = e.touches[0].clientX;
        basketStartX = miniGameState.basketX;
    });

    document.addEventListener('touchmove', (e) => {
        if (!isDragging || !miniGameState.active) return;
        const deltaX = e.touches[0].clientX - startX;
        let newX = basketStartX + deltaX;

        const maxX = overlayRect.width - 100;
        newX = Math.max(0, Math.min(maxX, newX));

        miniGameState.basketX = newX;
        basket.style.left = newX + 'px';
    });

    document.addEventListener('touchend', () => {
        isDragging = false;
    });
}

function startGameTimer() {
    if (miniGameState.timer) clearInterval(miniGameState.timer);

    miniGameState.timer = setInterval(() => {
        miniGameState.timeLeft--;
        const timerEl = document.getElementById('game-timer');
        timerEl.textContent = miniGameState.timeLeft;

        // 最后10秒警告
        if (miniGameState.timeLeft <= 10) {
            timerEl.classList.add('warning');
        }

        if (miniGameState.timeLeft <= 0) {
            endMiniGame();
        }
    }, 1000);
}

function spawnGameItems() {
    if (!miniGameState.active) return;

    const overlay = document.getElementById('mini-game');
    const overlayRect = overlay.getBoundingClientRect();

    // 创建掉落物品
    const item = document.createElement('div');
    item.className = 'falling-item';

    // 物品类型和分数
    const itemTypes = [
        { emoji: '🍎', score: 10, weight: 30 },
        { emoji: '🍊', score: 10, weight: 25 },
        { emoji: '🍇', score: 15, weight: 20 },
        { emoji: '🍓', score: 15, weight: 15 },
        { emoji: '🍖', score: 20, weight: 10 },
        { emoji: '🍕', score: 20, weight: 10 },
        { emoji: '⭐', score: 20, weight: 8, special: true },
        { emoji: '💎', score: 50, weight: 3, special: true },
        { emoji: '🌟', score: 30, weight: 5, special: true }
    ];

    // 加权随机选择
    const totalWeight = itemTypes.reduce((sum, t) => sum + t.weight, 0);
    let random = Math.random() * totalWeight;
    let selectedType = itemTypes[0];
    for (const type of itemTypes) {
        random -= type.weight;
        if (random <= 0) {
            selectedType = type;
            break;
        }
    }

    item.innerHTML = selectedType.emoji;
    item.dataset.score = selectedType.score;
    item.dataset.special = selectedType.special || false;

    // 随机X位置
    const x = 50 + Math.random() * (overlayRect.width - 150);
    item.style.left = x + 'px';
    item.style.top = '-50px';

    overlay.appendChild(item);
    miniGameState.items.push(item);

    // 掉落动画
    const fallDuration = 3000 + Math.random() * 2000; // 3-5秒
    const startTime = Date.now();
    const startY = -50;
    const endY = overlayRect.height - 100;

    function animateFall() {
        if (!miniGameState.active || !item.parentElement) return;

        const elapsed = Date.now() - startTime;
        const progress = elapsed / fallDuration;
        const currentY = startY + (endY - startY) * progress;

        item.style.top = currentY + 'px';

        // 检测碰撞
        const itemRect = item.getBoundingClientRect();
        const basketRect = document.getElementById('basket-container').getBoundingClientRect();

        if (checkCollision(itemRect, basketRect)) {
            catchItem(item, selectedType);
            return;
        }

        // 检测是否落地
        if (currentY >= endY - 20) {
            missItem(item);
            return;
        }

        requestAnimationFrame(animateFall);
    }

    requestAnimationFrame(animateFall);

    // 根据时间调整生成速度
    const spawnDelay = Math.max(400, 800 - (miniGameState.gameDuration - miniGameState.timeLeft) * 5);
    miniGameState.spawnTimer = setTimeout(spawnGameItems, spawnDelay);
}

function checkCollision(itemRect, basketRect) {
    // 物品中心点
    const itemCenterX = itemRect.left + itemRect.width / 2;
    const itemBottom = itemRect.bottom;

    // 篮子接住区域
    const basketTop = basketRect.top + 20;
    const basketLeft = basketRect.left + 10;
    const basketRight = basketRect.right - 10;

    return itemBottom >= basketTop &&
           itemBottom <= basketRect.bottom &&
           itemCenterX >= basketLeft &&
           itemCenterX <= basketRight;
}

function catchItem(item, type) {
    const basket = document.getElementById('basket-container');

    // 添加接住动画
    basket.classList.add('catching');
    setTimeout(() => basket.classList.remove('catching'), 200);

    // 更新分数
    const scoreGain = type.score + Math.floor(miniGameState.combo * 2);
    miniGameState.score += scoreGain;
    miniGameState.combo++;
    if (miniGameState.combo > miniGameState.maxCombo) {
        miniGameState.maxCombo = miniGameState.combo;
    }

    // 更新UI
    const scoreEl = document.getElementById('game-score');
    scoreEl.textContent = miniGameState.score;
    scoreEl.classList.add('pop');
    setTimeout(() => scoreEl.classList.remove('pop'), 300);

    // 显示连击
    if (miniGameState.combo >= 3) {
        const comboEl = document.getElementById('combo-display');
        comboEl.textContent = `🔥 连击 x${miniGameState.combo}`;
        comboEl.classList.add('active');
    }

    // 显示分数飘字
    showScoreFloat(item, '+' + scoreGain);

    // 显示星星特效
    showCatchStars(item);

    // 物品消失动画
    item.classList.add('caught');
    setTimeout(() => item.remove(), 400);

    // 从列表移除
    const index = miniGameState.items.indexOf(item);
    if (index > -1) miniGameState.items.splice(index, 1);
}

function missItem(item) {
    // 重置连击
    miniGameState.combo = 0;
    document.getElementById('combo-display').classList.remove('active');

    // 物品消失动画
    item.classList.add('missed');
    setTimeout(() => item.remove(), 300);

    // 从列表移除
    const index = miniGameState.items.indexOf(item);
    if (index > -1) miniGameState.items.splice(index, 1);
}

function showScoreFloat(item, text) {
    const rect = item.getBoundingClientRect();
    const overlay = document.getElementById('mini-game');
    const overlayRect = overlay.getBoundingClientRect();

    const float = document.createElement('div');
    float.className = 'score-float';
    float.textContent = text;
    float.style.left = (rect.left - overlayRect.left) + 'px';
    float.style.top = (rect.top - overlayRect.top) + 'px';

    overlay.appendChild(float);
    setTimeout(() => float.remove(), 800);
}

function showCatchStars(item) {
    const rect = item.getBoundingClientRect();
    const overlay = document.getElementById('mini-game');
    const overlayRect = overlay.getBoundingClientRect();

    for (let i = 0; i < 5; i++) {
        const star = document.createElement('div');
        star.className = 'catch-star';
        star.innerHTML = ['✨', '⭐', '💫'][Math.floor(Math.random() * 3)];
        star.style.left = (rect.left - overlayRect.left + Math.random() * 40 - 20) + 'px';
        star.style.top = (rect.top - overlayRect.top) + 'px';
        star.style.animationDelay = (Math.random() * 0.2) + 's';

        overlay.appendChild(star);
        setTimeout(() => star.remove(), 600);
    }
}

function endMiniGame() {
    miniGameState.active = false;

    if (miniGameState.timer) {
        clearInterval(miniGameState.timer);
        miniGameState.timer = null;
    }
    if (miniGameState.spawnTimer) {
        clearTimeout(miniGameState.spawnTimer);
        miniGameState.spawnTimer = null;
    }

    // 清除所有物品
    miniGameState.items.forEach(item => item.remove());
    miniGameState.items = [];

    // 计算奖励
    const reward = Math.floor(miniGameState.score / 5) + miniGameState.maxCombo * 2;

    // 显示结束画面
    document.getElementById('final-score').textContent = miniGameState.score;
    document.getElementById('max-combo').textContent = miniGameState.maxCombo;
    document.getElementById('reward-coins').textContent = reward;
    document.getElementById('game-over').classList.add('active');

    // 发放奖励
    if (reward > 0) {
        gameState.coins += reward;
        updateCoins();
    }
}

function restartMiniGame() {
    document.getElementById('game-over').classList.remove('active');
    startGameWithTime(miniGameState.gameDuration);
}

function closeMiniGame() {
    // 停止游戏
    miniGameState.active = false;
    if (miniGameState.timer) {
        clearInterval(miniGameState.timer);
        miniGameState.timer = null;
    }
    if (miniGameState.spawnTimer) {
        clearTimeout(miniGameState.spawnTimer);
        miniGameState.spawnTimer = null;
    }

    const overlay = document.getElementById('mini-game');
    overlay.classList.remove('active');

    // 清除所有物品
    overlay.querySelectorAll('.falling-item, .score-float, .catch-star').forEach(el => el.remove());
    miniGameState.items = [];

    // 隐藏子界面
    document.getElementById('time-select').classList.remove('active');
    document.getElementById('game-over').classList.remove('active');
}

// 保存/加载
function saveGameState() {
    localStorage.setItem('pixelPetGame', JSON.stringify({
        gameState,
        pets: PETS.map(p => ({ id: p.id, unlocked: p.unlocked }))
    }));
}

function loadGameState() {
    const saved = localStorage.getItem('pixelPetGame');
    if (saved) {
        const data = JSON.parse(saved);
        gameState = { ...gameState, ...data.gameState };
        data.pets?.forEach(p => {
            const pet = PETS.find(pet => pet.id === p.id);
            if (pet) pet.unlocked = p.unlocked;
        });
        updateCoins();
        updateStatus();
        document.getElementById('stars').textContent = gameState.stars;
    }

    // 从个人中心同步
    syncFromPersonalCenter();
    updateStatus();
}

// 返回
function goBack() {
    window.location.href = '/personal.html';
}

// 点击宠物互动
document.getElementById('pet-container').addEventListener('click', () => {
    petThePet();
});

// 启动
init();

// 当其他页面修改了 starlearn_pet（例如个人中心），监听 storage 事件并同步头像/状态
window.addEventListener('storage', (e) => {
  if (e.key === 'starlearn_pet') {
    try {
      syncFromPersonalCenter();
      renderCurrentPet();
      updateStatus();
    } catch (err) {
      // ignore
    }
  }
});