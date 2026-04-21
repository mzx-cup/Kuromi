// ============================================================
// 植物数据：80种，5个稀有度
// 普通30 + 稀有20 + 精良15 + 史诗10 + 传说5 = 80种
// ============================================================
const PLANT_DATA = [
    // ─── 普通 common (30种) ───
    { id: 'carrot',    name: '🥕 胡萝卜',   emoji: '🥕', stages: ['🌱','🌿','🥕','🥕'], growTime: 60,  desc: '基础根茎', rarity: 'common' },
    { id: 'cabbage',   name: '🥬 卷心菜',   emoji: '🥬', stages: ['🌱','🌿','🥬','🥬'], growTime: 65,  desc: '绿叶蔬菜', rarity: 'common' },
    { id: 'tomato',    name: '🍅 番茄',     emoji: '🍅', stages: ['🌱','🌿','🍅','🍅'], growTime: 70,  desc: '茄科果实', rarity: 'common' },
    { id: 'corn',      name: '🌽 玉米',     emoji: '🌽', stages: ['🌱','🌿','🌽','🌽'], growTime: 72,  desc: '谷物之王', rarity: 'common' },
    { id: 'eggplant',  name: '🍆 茄子',     emoji: '🍆', stages: ['🌱','🌿','🍆','🍆'], growTime: 68,  desc: '紫皮果实', rarity: 'common' },
    { id: 'pepper',    name: '🌶️ 青椒',     emoji: '🌶️', stages: ['🌱','🌿','🌶️','🌶️'], growTime: 62,  desc: '辛辣植物', rarity: 'common' },
    { id: 'cucumber',  name: '🥒 黄瓜',     emoji: '🥒', stages: ['🌱','🌿','🥒','🥒'], growTime: 66,  desc: '藤蔓作物', rarity: 'common' },
    { id: 'broccoli',  name: '🥦 西兰花',   emoji: '🥦', stages: ['🌱','🌿','🥦','🥦'], growTime: 74,  desc: '十字花科', rarity: 'common' },
    { id: 'onion',     name: '🧅 洋葱',     emoji: '🧅', stages: ['🌱','🌿','🧅','🧅'], growTime: 60,  desc: '鳞茎植物', rarity: 'common' },
    { id: 'garlic',    name: '🧄 大蒜',     emoji: '🧄', stages: ['🌱','🌿','🧄','🧄'], growTime: 58,  desc: '调味料之王', rarity: 'common' },
    { id: 'potato',    name: '🥔 土豆',     emoji: '🥔', stages: ['🌱','🌿','🥔','🥔'], growTime: 64,  desc: '块茎之王', rarity: 'common' },
    { id: 'sweetpot',  name: '🍠 红薯',     emoji: '🍠', stages: ['🌱','🌿','🍠','🍠'], growTime: 68,  desc: '块根作物', rarity: 'common' },
    { id: 'radish',    name: '🔴 白萝卜',   emoji: '🔴', stages: ['🌱','🌿','🔴','🔴'], growTime: 55,  desc: '快根蔬菜', rarity: 'common' },
    { id: 'pumpkin',   name: '🎃 南瓜',     emoji: '🎃', stages: ['🌱','🌿','🎃','🎃'], growTime: 80,  desc: '瓜类作物', rarity: 'common' },
    { id: 'melon',     name: '🍈 甜瓜',     emoji: '🍈', stages: ['🌱','🌿','🍈','🍈'], growTime: 76,  desc: '蔓生水果', rarity: 'common' },
    { id: 'watermelon',name: '🍉 西瓜',     emoji: '🍉', stages: ['🌱','🌿','🍉','🍉'], growTime: 82,  desc: '夏季水果', rarity: 'common' },
    { id: 'strawberry',name: '🍓 草莓',     emoji: '🍓', stages: ['🌱','🌿','🍓','🍓'], growTime: 70,  desc: '浆果之王', rarity: 'common' },
    { id: 'apple',     name: '🍎 红苹果',   emoji: '🍎', stages: ['🌱','🌿','🍎','🍎'], growTime: 90,  desc: '温带水果', rarity: 'common' },
    { id: 'pear',      name: '🍐 雪梨',     emoji: '🍐', stages: ['🌱','🌿','🍐','🍐'], growTime: 88,  desc: '梨属水果', rarity: 'common' },
    { id: 'peach',     name: '🍑 桃子',     emoji: '🍑', stages: ['🌱','🌿','🍑','🍑'], growTime: 86,  desc: '核果类', rarity: 'common' },
    { id: 'cherry',    name: '🍒 樱桃',     emoji: '🍒', stages: ['🌱','🌿','🍒','🍒'], growTime: 84,  desc: '春季浆果', rarity: 'common' },
    { id: 'grape',    name: '🍇 葡萄',     emoji: '🍇', stages: ['🌱','🌿','🍇','🍇'], growTime: 92,  desc: '藤本水果', rarity: 'common' },
    { id: 'banana',    name: '🍌 香蕉',     emoji: '🍌', stages: ['🌱','🌿','🍌','🍌'], growTime: 96,  desc: '热带水果', rarity: 'common' },
    { id: 'orange',    name: '🍊 橙子',     emoji: '🍊', stages: ['🌱','🌿','🍊','🍊'], growTime: 90,  desc: '柑橘类', rarity: 'common' },
    { id: 'lemon',     name: '🍋 柠檬',     emoji: '🍋', stages: ['🌱','🌿','🍋','🍋'], growTime: 88,  desc: '酸味水果', rarity: 'common' },
    { id: 'mango',     name: '🥭 芒果',     emoji: '🥭', stages: ['🌱','🌿','🥭','🥭'], growTime: 95,  desc: '热带果王', rarity: 'common' },
    { id: 'pineapple', name: '🍍 菠萝',    emoji: '🍍', stages: ['🌱','🌿','🍍','🍍'], growTime: 100, desc: '热带特产', rarity: 'common' },
    { id: 'coconut',   name: '🥥 椰子',     emoji: '🥥', stages: ['🌱','🌿','🥥','🥥'], growTime: 105, desc: '海岸水果', rarity: 'common' },
    { id: 'kiwi',      name: '🥝 猕猴桃',   emoji: '🥝', stages: ['🌱','🌿','🥝','🥝'], growTime: 85,  desc: '维C之王', rarity: 'common' },
    { id: 'avocado',   name: '🥑 牛油果',  emoji: '🥑', stages: ['🌱','🌿','🥑','🥑'], growTime: 98,  desc: '森林奶油', rarity: 'common' },

    // ─── 稀有 rare (20种) ───
    { id: 'coffee',    name: '☕ 咖啡果',   emoji: '☕', stages: ['🌱','🌿','☕','☕'], growTime: 120, desc: '提神圣品', rarity: 'rare' },
    { id: 'tea',       name: '🍵 茶树',     emoji: '🍵', stages: ['🌱','🌿','🍵','🍃'], growTime: 115, desc: '东方树叶', rarity: 'rare' },
    { id: 'cocoa',     name: '🍫 可可果',   emoji: '🍫', stages: ['🌱','🌿','🍫','🍫'], growTime: 125, desc: '巧克力原料', rarity: 'rare' },
    { id: 'tobacco',   name: '🍂 烟草叶',   emoji: '🍂', stages: ['🌱','🌿','🍂','🍂'], growTime: 118, desc: '特殊经济作物', rarity: 'rare' },
    { id: 'lavender',  name: '💜 薰衣草',  emoji: '💜', stages: ['🌱','🌿','💜','💜'], growTime: 110, desc: '芳香植物', rarity: 'rare' },
    { id: 'tulip',     name: '🌷 郁金香',   emoji: '🌷', stages: ['🌱','🌿','🌷','🌷'], growTime: 105, desc: '花卉皇后', rarity: 'rare' },
    { id: 'orchid',    name: '🪻 兰花',     emoji: '🪻', stages: ['🌱','🌿','🪻','🪻'], growTime: 112, desc: '花中君子', rarity: 'rare' },
    { id: 'bonsai',    name: '🌳 盆景树',   emoji: '🌳', stages: ['🌱','🌿','🌳','🌳'], growTime: 130, desc: '东方美学', rarity: 'rare' },
    { id: 'bamboo_p',  name: '🎋 观赏竹',   emoji: '🎋', stages: ['🌱','🌿','🎋','🎍'], growTime: 108, desc: '竹影清风', rarity: 'rare' },
    { id: 'maple',     name: '🍁 枫树',     emoji: '🍁', stages: ['🌱','🌿','🍁','🍁'], growTime: 128, desc: '秋色叶树', rarity: 'rare' },
    { id: 'willow',    name: '🌿 垂柳',     emoji: '🌿', stages: ['🌱','🌿','🌿','🌿'], growTime: 115, desc: '河边风景', rarity: 'rare' },
    { id: 'jasmine',   name: '🤍 茉莉花',   emoji: '🤍', stages: ['🌱','🌿','🤍','🤍'], growTime: 108, desc: '芳香小白花', rarity: 'rare' },
    { id: 'lotus_f',   name: '🪷 莲花',     emoji: '🪷', stages: ['🌱','🌿','🪷','🪷'], growTime: 118, desc: '出水芙蓉', rarity: 'rare' },
    { id: 'reindeer',  name: '🍄 驯鹿苔',   emoji: '🍄', stages: ['🌱','🌿','🍄','🍄'], growTime: 105, desc: '极地植物', rarity: 'rare' },
    { id: 'ginseng',   name: '🌿 人参',     emoji: '🌿', stages: ['🌱','🌿','🌿','🌿'], growTime: 140, desc: '百草之王', rarity: 'rare' },
    { id: 'cactus_r',  name: '🌵 仙人掌',   emoji: '🌵', stages: ['🌱','🌵','🌵','🌵'], growTime: 135, desc: '沙漠英雄', rarity: 'rare' },
    { id: 'bonsai_p',  name: '🌲 松树',     emoji: '🌲', stages: ['🌱','🌿','🌲','🌲'], growTime: 132, desc: '常青乔木', rarity: 'rare' },
    { id: 'sakura',    name: '🌸 樱花树',   emoji: '🌸', stages: ['🌱','🌿','🌸','🌸'], growTime: 125, desc: '春日浪漫', rarity: 'rare' },
    { id: 'olive',     name: '🫒 橄榄树',   emoji: '🫒', stages: ['🌱','🌿','🫒','🫒'], growTime: 130, desc: '和平之树', rarity: 'rare' },
    { id: 'cherry_b', name: '🌺 木棉',     emoji: '🌺', stages: ['🌱','🌿','🌺','🌺'], growTime: 120, desc: '英雄之花', rarity: 'rare' },

    // ─── 精良 fine (15种) ───
    { id: 'relic_flower', name: '🔮 灵草',    emoji: '🌿', stages: ['🌱','🌿','🔮','✨'], growTime: 160, desc: '蕴含灵气', rarity: 'fine' },
    { id: 'moon_flower',  name: '🌙 月花',    emoji: '🌙', stages: ['🌱','🌿','🌙','🌙'], growTime: 155, desc: '月光之花', rarity: 'fine' },
    { id: 'star_plant',   name: '⭐ 星之草',  emoji: '⭐', stages: ['🌱','🌿','⭐','✨'], growTime: 150, desc: '星光熠熠', rarity: 'fine' },
    { id: 'crystal_fern', name: '💎 水晶蕨',  emoji: '💎', stages: ['🌱','🌿','💎','💎'], growTime: 158, desc: '透明叶片', rarity: 'fine' },
    { id: 'rainbow_rose',name: '🌈 彩虹玫瑰',emoji: '🌈', stages: ['🌱','🌿','🌈','🌈'], growTime: 162, desc: '七色花瓣', rarity: 'fine' },
    { id: 'phoenix_tree', name: '🔆 凤凰木',  emoji: '🔥', stages: ['🌱','🌿','🔥','🔥'], growTime: 165, desc: '烈火红叶', rarity: 'fine' },
    { id: 'thunder_vine', name: '⚡ 雷藤',    emoji: '⚡', stages: ['🌱','🌿','⚡','⚡'], growTime: 152, desc: '电光缠绕', rarity: 'fine' },
    { id: 'frost_pine',  name: '❄️ 霜松',    emoji: '❄️', stages: ['🌱','🌿','❄️','❄️'], growTime: 160, desc: '冰霜常青', rarity: 'fine' },
    { id: 'cloud_lotus', name: '☁️ 云莲',    emoji: '☁️', stages: ['🌱','🌿','☁️','☁️'], growTime: 155, desc: '云端之花', rarity: 'fine' },
    { id: 'sun_bloom',   name: '☀️ 阳炎花',  emoji: '☀️', stages: ['🌱','🌿','☀️','☀️'], growTime: 158, desc: '向阳而生', rarity: 'fine' },
    { id: 'moon_moss',   name: '🌑 月苔',    emoji: '🌑', stages: ['🌱','🌿','🌑','🌑'], growTime: 150, desc: '暗夜微光', rarity: 'fine' },
    { id: 'void_fern',   name: '🕳️ 虚空蕨', emoji: '🕳️', stages: ['🌱','🌿','🕳️','🕳️'], growTime: 162, desc: '深渊植物', rarity: 'fine' },
    { id: 'nebula_bloom',name: '🌌 星云花',  emoji: '🌌', stages: ['🌱','🌿','🌌','🌌'], growTime: 168, desc: '宇宙绽放', rarity: 'fine' },
    { id: 'aurora_grass',name: '🎆 极光草',  emoji: '🎆', stages: ['🌱','🌿','🎆','🎆'], growTime: 155, desc: '极光之色', rarity: 'fine' },
    { id: 'ember_rose',  name: '💥 灰烬玫瑰',emoji: '💥', stages: ['🌱','🌿','💥','💥'], growTime: 160, desc: '涅槃重生', rarity: 'fine' },

    // ─── 史诗 epic (10种) ───
    { id: 'dragon_tree',  name: '🐉 龙血树', emoji: '🩸', stages: ['🌱','🌿','🩸','🐉'], growTime: 200, desc: '龙之血脉', rarity: 'epic' },
    { id: 'phoenix_tree_e',name: '🔥 凤凰树', emoji: '🔥', stages: ['🌱','🌿','🔥','🔥'], growTime: 210, desc: '浴火重生', rarity: 'epic' },
    { id: 'crystal_tree', name: '💠 水晶树',  emoji: '💠', stages: ['🌱','🌿','💠','💠'], growTime: 205, desc: '晶莹剔透', rarity: 'epic' },
    { id: 'dream_blossom',name: '💫 梦樱',    emoji: '💫', stages: ['🌱','🌿','💫','💫'], growTime: 198, desc: '梦中花开', rarity: 'epic' },
    { id: 'void_bloom',  name: '🌀 虚空花',  emoji: '🌀', stages: ['🌱','🌿','🌀','🌀'], growTime: 212, desc: '混沌之花', rarity: 'epic' },
    { id: 'time_vine',   name: '⏳ 时光藤',  emoji: '⏳', stages: ['🌱','🌿','⏳','⏳'], growTime: 208, desc: '时光流转', rarity: 'epic' },
    { id: 'star_root',   name: '🌟 星根',   emoji: '🌟', stages: ['🌱','🌿','🌟','✨'], growTime: 215, desc: '星辰之力', rarity: 'epic' },
    { id: 'spirit_vine', name: '👻 幽灵藤',  emoji: '👻', stages: ['🌱','🌿','👻','👻'], growTime: 200, desc: '灵异之藤', rarity: 'epic' },
    { id: 'world_tree',  name: '🌍 世界树',  emoji: '🌍', stages: ['🌱','🌿','🌍','🌏'], growTime: 220, desc: '通天彻地', rarity: 'epic' },
    { id: 'ancient_fern',name: '🏛️ 古蕨',  emoji: '🏛️', stages: ['🌱','🌿','🏛️','🏛️'], growTime: 205, desc: '亿年活化石', rarity: 'epic' },

    // ─── 传说 legendary (5种) ───
    { id: 'eden_blossom', name: '🌺 伊甸花',    emoji: '🌺', stages: ['🌱','🌿','🌺','✨'], growTime: 300, desc: '创世之美', rarity: 'legendary' },
    { id: 'cosmos_tree',  name: '🌌 宇宙树',    emoji: '🌌', stages: ['🌱','🌿','🌌','🌟'], growTime: 320, desc: '万物归宗', rarity: 'legendary' },
    { id: 'chaos_vine',  name: '💀 混沌藤',    emoji: '💀', stages: ['🌱','🌿','💀','💀'], growTime: 280, desc: '混沌之力', rarity: 'legendary' },
    { id: 'immortal_elm',name: '☠️ 不死榆',    emoji: '☠️', stages: ['🌱','🌿','☠️','☠️'], growTime: 260, desc: '永生之木', rarity: 'legendary' },
    { id: 'origin_flower',name: '🌾 起源花',   emoji: '🌾', stages: ['🌱','🌿','🌾','🌾'], growTime: 350, desc: '万物起源', rarity: 'legendary' },
];

// 稀有度权重（总和=100）
const RARITY_WEIGHTS = { common: 60, rare: 25, fine: 10, epic: 4, legendary: 1 };
const RARITY_NAMES   = { common: '普通', rare: '稀有', fine: '精良', epic: '史诗', legendary: '传说' };
const RARITY_COLORS  = {
    common:    '#9CA3AF',
    rare:      '#3B82F6',
    fine:      '#8B5CF6',
    epic:      '#F59E0B',
    legendary: '#EF4444',
};
const RARITY_BG = {
    common:    'rgba(156,163,175,0.15)',
    rare:      'rgba(59,130,246,0.15)',
    fine:      'rgba(139,92,246,0.15)',
    epic:      'rgba(245,158,11,0.15)',
    legendary: 'rgba(239,68,68,0.15)',
};

// 神秘生长阶段显示（生长中不显示真实植物）
const MYSTERY_STAGES = ['🌰', '🌱', '🌿'];

const STAGE_NAMES = ['种子', '萌芽', '成长期', '已成熟'];
const WATER_PER_ACTION = 20;
const NUTRIENT_PER_ACTION = 15;
const WATER_DECAY_RATE = 2;
const NUTRIENT_DECAY_RATE = 1;
const WATER_TIME_REDUCTION = 5 * 60;
const NUTRIENT_TIME_REDUCTION = 15 * 60;
const PLANT_SLOTS = 3;

let plantState = {
    seeds: 0,
    ownedPlants: [], // [{id, name, emoji, rarity}]
    slots: [],
    lastUpdate: Date.now()
};

let selectedSlotIndex = 0;

// 根据稀有度权重随机选一株植物
function randomPickPlant() {
    const total = Object.values(RARITY_WEIGHTS).reduce((a, b) => a + b, 0);
    let r = Math.random() * total;
    let chosenRarity = 'common';
    for (const [rarity, weight] of Object.entries(RARITY_WEIGHTS)) {
        r -= weight;
        if (r <= 0) { chosenRarity = rarity; break; }
    }
    const candidates = PLANT_DATA.filter(p => p.rarity === chosenRarity);
    return candidates[Math.floor(Math.random() * candidates.length)];
}

function init() {
    loadPlantState();
    renderSeedCount();
    renderPlantCollection();
    renderPlantPots();
    renderCurrentPlant();
    startGrowthTimer();
    // 粒子效果已移除，使用 CSS 天空背景
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

    // 兼容旧格式 ownedPlants（字符串数组）→ 新格式（对象数组）
    if (plantState.ownedPlants && plantState.ownedPlants.length > 0) {
        if (typeof plantState.ownedPlants[0] === 'string') {
            plantState.ownedPlants = plantState.ownedPlants.map(id => {
                const plant = PLANT_DATA.find(p => p.id === id);
                return plant ? { id: plant.id, name: plant.name, emoji: plant.emoji, rarity: plant.rarity } : null;
            }).filter(Boolean);
        }
    }
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
    // 广播自定义事件，通知其他页面（如个人中心）
    window.dispatchEvent(new CustomEvent('plantStateUpdated', { detail: toSave }));
}

function renderSeedCount() {
    // 更新导航栏种子数
    const navEl = document.getElementById('seed-count-nav');
    if (navEl) navEl.textContent = plantState.seeds;
    // 同步到 localStorage
    localStorage.setItem('starlearn_seeds', String(plantState.seeds));
}

function renderPlantCollection() {
    const grid = document.getElementById('plant-collection');
    if (!grid) return;
    grid.innerHTML = PLANT_DATA.map(plant => {
        const ownedEntry = plantState.ownedPlants.find(o => o.id === plant.id);
        const owned = !!ownedEntry;
        const rarityColor = RARITY_COLORS[plant.rarity];
        const rarityBg = RARITY_BG[plant.rarity];
        return `
            <div class="plant-collection-item ${owned ? 'owned' : ''}" title="${plant.desc}">
                <div class="item-rarity-dot" style="background:${rarityColor}"></div>
                <span class="item-emoji">${plant.emoji}</span>
                <span class="item-name">${plant.name}</span>
                ${owned ? `<span class="item-owned-tag" style="color:${rarityColor};background:${rarityBg}">${RARITY_NAMES[plant.rarity]}</span>` : ''}
            </div>
        `;
    }).join('');

    // 更新已拥有计数
    const ownedCountEl = document.getElementById('owned-count');
    if (ownedCountEl) {
        ownedCountEl.textContent = plantState.ownedPlants.length;
    }
}

function selectPlant(plantId) {
    // 切换选择（不立刻种植），用户需点击「种植」按钮确认
    selectedPlantId = plantId;
    renderPlantCollection();
    const plant = PLANT_DATA.find(p => p.id === plantId);
    if (plant) showTip(`已选择 ${plant.name}。点击“种植”开始栽种（消耗 1 个种子）。`);
}

function plantSeed() {
    // 找到一个空槽位优先使用选中的槽位
    let targetIdx = selectedSlotIndex;
    const slot = plantState.slots[targetIdx];
    if (slot && slot.plantId) {
        targetIdx = plantState.slots.findIndex(s => !s.plantId);
        if (targetIdx === -1) { showTip('所有槽位均已占用，请收获或移除后再种植。'); return; }
    }

    if (plantState.seeds <= 0) { showTip('没有种子了！完成专注计时获得种子~'); return; }

    // 随机选取一株植物（稀有度加权）
    const plant = randomPickPlant();
    if (!plant) return;

    plantState.seeds = Math.max(0, plantState.seeds - 1);

    // 初始化槽位（存储真实植物信息，但 UI 只显示 MYSTERY_STAGES）
    plantState.slots[targetIdx] = {
        plantId: plant.id,
        plantName: plant.name,
        plantEmoji: plant.emoji,
        plantRarity: plant.rarity,
        stage: 0,
        remainingTime: plant.growTime * 60,
        water: 50,
        nutrient: 50,
        lastUpdate: Date.now()
    };

    // 动画：对应槽位的 pot 摇动与生长脉冲
    const potWrapper = document.querySelector(`.plant-pot-wrapper[data-slot='${targetIdx}']`);
    const display = document.getElementById(`plant-display-${targetIdx}`) || document.getElementById('plant-display');
    if (potWrapper) {
        potWrapper.classList.remove('pot-shake');
        void potWrapper.offsetWidth;
        potWrapper.classList.add('pot-shake');
        setTimeout(() => potWrapper.classList.remove('pot-shake'), 600);
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
    showTip(`🌱 在槽位 ${targetIdx+1} 播下神秘种子！浇水或施肥可加速成长~`);

    // 同步到个人中心
    try { localStorage.setItem('starlearn_plants', JSON.stringify(plantState)); } catch(e) {}
}

function renderPlantPots() {
    const container = document.getElementById('plant-pots');
    if (!container) return;
    container.innerHTML = '';
    plantState.slots.forEach((slot, idx) => {
        const hasPlant = slot && slot.plantId;
        // 成熟前显示神秘阶段，成熟后显示真实植物
        const emoji = hasPlant
            ? (slot.stage >= 3 ? (slot.plantEmoji || MYSTERY_STAGES[3]) : MYSTERY_STAGES[slot.stage])
            : '🌱';
        const stageClass = hasPlant ? `stage-${slot.stage}` : 'stage-0';
        const emptyClass = hasPlant ? '' : 'empty';
        const selectedClass = idx === selectedSlotIndex ? 'selected' : '';
        const html = `
            <div class="plant-pot-wrapper ${emptyClass} ${selectedClass}" data-slot="${idx}" onclick="selectSlot(${idx})">
                <div class="plant-pot-3d">
                    <div class="pot-body"></div>
                    <div class="pot-soil"></div>
                    <div class="plant-in-pot ${stageClass}" id="plant-display-${idx}">${emoji}</div>
                </div>
                <div class="slot-label">槽位 ${idx + 1}</div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });
}

function renderCurrentPlant() {
    // 渲染主面板，基于 selectedSlotIndex
    const slot = plantState.slots[selectedSlotIndex];
    const display = document.getElementById('plant-emoji-display');
    const nameEl = document.getElementById('plant-name');
    const stageEl = document.getElementById('plant-stage');
    const timerEl = document.getElementById('plant-timer');
    const waterEl = document.getElementById('water-value');
    const nutrientEl = document.getElementById('nutrient-value');
    const harvestBtn = document.getElementById('harvest-btn');
    const waterBar = document.getElementById('water-bar');
    const nutrientBar = document.getElementById('nutrient-bar');
    const plantBtn = document.getElementById('plant-btn');
    const tipEl = document.getElementById('plant-tip');

    if (!slot || !slot.plantId) {
        if (display) { display.textContent = '🌱'; display.className = 'plant-main-emoji stage-0'; }
        if (nameEl) nameEl.textContent = '选择一块地开始种植';
        if (stageEl) stageEl.textContent = '等待种植';
        if (timerEl) timerEl.textContent = '--:--:--';
        if (waterEl) waterEl.textContent = '0%';
        if (nutrientEl) nutrientEl.textContent = '0%';
        if (waterBar) waterBar.style.width = '0%';
        if (nutrientBar) nutrientBar.style.width = '0%';
        if (harvestBtn) harvestBtn.style.display = 'none';
        if (waterBtn) waterBtn.style.display = 'none';
        if (nutrientBtn) nutrientBtn.style.display = 'none';
        if (plantBtn) plantBtn.style.display = 'flex';
        if (tipEl) tipEl.textContent = '💡 点击上方槽位，然后点击"种植"播下神秘种子！稀有度只有在收获时才会揭晓~';
        return;
    }

    const isMature = slot.stage >= 3;
    // 成熟前显示神秘 emoji，成熟后显示真实植物
    const displayEmoji = isMature ? (slot.plantEmoji || MYSTERY_STAGES[3]) : MYSTERY_STAGES[slot.stage];
    const displayName = isMature ? (slot.plantName || '??? 神秘植物') : '??? 神秘植物';

    if (display) {
        display.textContent = displayEmoji;
        display.className = `plant-main-emoji stage-${slot.stage}${isMature ? ' mature' : ''}`;
    }
    if (nameEl) nameEl.textContent = displayName;
    if (stageEl) {
        if (isMature) {
            const rColor = RARITY_COLORS[slot.plantRarity] || '#9CA3AF';
            stageEl.innerHTML = `<span style="color:${rColor};font-weight:800">🌟 ${RARITY_NAMES[slot.plantRarity]} - 已成熟！</span>`;
        } else {
            stageEl.textContent = `🌿 ${STAGE_NAMES[slot.stage]} - 神秘植物`;
        }
    }
    if (waterEl) waterEl.textContent = Math.round(slot.water) + '%';
    if (nutrientEl) nutrientEl.textContent = Math.round(slot.nutrient) + '%';
    if (waterBar) waterBar.style.width = Math.round(slot.water) + '%';
    if (nutrientBar) nutrientBar.style.width = Math.round(slot.nutrient) + '%';

    // 更新浇水/施肥按钮状态
    const waterBtn = document.getElementById('water-btn');
    const nutrientBtn = document.getElementById('nutrient-btn');
    if (waterBtn) {
        if (slot.water >= 100) {
            waterBtn.classList.add('disabled');
            waterBtn.style.opacity = '0.5';
            waterBtn.style.cursor = 'not-allowed';
        } else {
            waterBtn.classList.remove('disabled');
            waterBtn.style.opacity = '1';
            waterBtn.style.cursor = 'pointer';
        }
    }
    if (nutrientBtn) {
        if (slot.nutrient >= 100) {
            nutrientBtn.classList.add('disabled');
            nutrientBtn.style.opacity = '0.5';
            nutrientBtn.style.cursor = 'not-allowed';
        } else {
            nutrientBtn.classList.remove('disabled');
            nutrientBtn.style.opacity = '1';
            nutrientBtn.style.cursor = 'pointer';
        }
    }

    if (harvestBtn) {
        harvestBtn.style.display = isMature ? 'flex' : 'none';
    }

    // 成熟时隐藏浇水/施肥/种植按钮，只保留收获
    if (isMature) {
        if (waterBtn) waterBtn.style.display = 'none';
        if (nutrientBtn) nutrientBtn.style.display = 'none';
        if (plantBtn) plantBtn.style.display = 'none';
    } else {
        if (waterBtn) waterBtn.style.display = 'flex';
        if (nutrientBtn) nutrientBtn.style.display = 'flex';
        if (plantBtn) plantBtn.style.display = 'none';
    }

    updateTimerDisplay();
}

function updateTimerDisplay() {
    const timerEl = document.getElementById('plant-timer');
    if (!timerEl) return;
    const slot = plantState.slots[selectedSlotIndex];
    if (!slot || !slot.plantId) {
        timerEl.textContent = '--:--:--';
        timerEl.style.color = '#BF6327';
        return;
    }

    if (slot.stage >= 3) {
        timerEl.textContent = '可收获!';
        timerEl.style.color = '#43A047';
        return;
    }

    const hours = Math.floor(slot.remainingTime / 3600);
    const mins = Math.floor((slot.remainingTime % 3600) / 60);
    const secs = Math.floor(slot.remainingTime % 60);
    timerEl.textContent = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    timerEl.style.color = slot.remainingTime < 300 ? '#e53935' : '#BF6327';
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
                    if (newStage >= 3) {
                        showTip(`🎉 恭喜！槽位 ${idx+1} 的神秘植物已成熟，可以收获啦！`);
                    } else {
                        showTip(`🎉 恭喜！槽位 ${idx+1} 的神秘植物进入${STAGE_NAMES[newStage]}阶段！`);
                    }
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
    const potWrapper = document.querySelector(`.plant-pot-wrapper[data-slot='${selectedSlotIndex}']`);

    if (action === 'water') {
        if (slot.water >= 100) {
            showTip('💧 水分已达上限，无需再浇水！');
            return;
        }
        slot.water = Math.min(100, slot.water + WATER_PER_ACTION);
        slot.remainingTime = Math.max(0, slot.remainingTime - WATER_TIME_REDUCTION);
        if (displayEl) {
            displayEl.classList.remove('plant-grow-anim');
            void displayEl.offsetWidth;
            displayEl.classList.add('plant-grow-anim');
        }
        if (potWrapper) {
            potWrapper.classList.remove('water-drop-anim');
            void potWrapper.offsetWidth;
            potWrapper.classList.add('water-drop-anim');
            setTimeout(() => potWrapper.classList.remove('water-drop-anim'), 900);
        }
        showTip('💧 浇水成功！水分+' + WATER_PER_ACTION + '%，生长时间缩短5分钟~');
    } else if (action === 'nutrient') {
        if (slot.nutrient >= 100) {
            showTip('🧪 营养已达上限，无需再施肥！');
            return;
        }
        slot.nutrient = Math.min(100, slot.nutrient + NUTRIENT_PER_ACTION);
        slot.remainingTime = Math.max(0, slot.remainingTime - NUTRIENT_TIME_REDUCTION);
        if (displayEl) {
            displayEl.classList.remove('plant-grow-anim');
            void displayEl.offsetWidth;
            displayEl.classList.add('plant-grow-anim');
        }
        if (potWrapper) {
            potWrapper.classList.remove('nutrient-pop-anim');
            void potWrapper.offsetWidth;
            potWrapper.classList.add('nutrient-pop-anim');
            setTimeout(() => potWrapper.classList.remove('nutrient-pop-anim'), 800);
        }
        showTip('🧪 施肥成功！营养+' + NUTRIENT_PER_ACTION + '%，生长时间缩短15分钟~');
    } else if (action === 'harvest') {
        if (slot.stage < 3) return;
        const plant = PLANT_DATA.find(p => p.id === slot.plantId);
        const rarityName = RARITY_NAMES[slot.plantRarity] || '普通';
        const rarityColor = RARITY_COLORS[slot.plantRarity] || '#9CA3AF';
        triggerHarvestEffect();
        // 右上角推送通知，揭晓真实植物和稀有度
        if (window.starlearnNotifications && typeof window.starlearnNotifications.showNotification === 'function') {
            window.starlearnNotifications.showNotification({
                title: `🌾 收获 ${slot.plantEmoji} ${slot.plantName}`,
                content: `稀有度：${rarityName} ✨ 恭喜发现隐藏的植物！`,
                actionLabel: '查看林场',
                actionUrl: '/html/plant.html',
                type: 'achievement'
            });
        }
        showTip(`🌾 收获成功！稀有度：${rarityName} ✨「${slot.plantName}」已被收录到图鉴！`);
        // 记录到已拥有（去重）
        const ownedEntry = { id: slot.plantId, name: slot.plantName, emoji: slot.plantEmoji, rarity: slot.plantRarity };
        const existingIdx = plantState.ownedPlants.findIndex(o => o.id === slot.plantId);
        if (existingIdx >= 0) {
            plantState.ownedPlants[existingIdx] = ownedEntry;
        } else {
            plantState.ownedPlants.push(ownedEntry);
        }
        // 清空槽位
        plantState.slots[selectedSlotIndex] = { plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() };
        savePlantState();
        renderPlantPots();
        renderCurrentPlant();
        renderPlantCollection();

        // 成就触发：收获
        if (window.AchievementManager) {
            AchievementManager.incrementStat('harvest_count');
            AchievementManager.incrementStat('plant_count');
        }
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
        display.classList.remove('plant-grow-anim');
        void display.offsetWidth;
        display.classList.add('plant-grow-anim');
    }
    triggerHarvestEffect();
}

function triggerHarvestEffect() {
    const container = document.getElementById('gold-rain');
    if (!container) return;

    const emojis = ['✨', '🌟', '💫', '🌾', '🍃', '🌸', '💐', '🪙', '⭐'];
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
    }
}

function selectSlot(idx) {
    selectedSlotIndex = idx;
    renderPlantPots();
    renderCurrentPlant();
    const slot = plantState.slots[idx];
    if (!slot || !slot.plantId) {
        showTip(`槽位 ${idx+1} 为空，点击【种植】播下神秘种子！`);
    } else {
        const isMature = slot.stage >= 3;
        if (isMature) {
            showTip(`槽位 ${idx+1}：${slot.plantName} 已成熟！点击【收获】揭晓稀有度~`);
        } else {
            showTip(`槽位 ${idx+1}：神秘植物 · ${STAGE_NAMES[slot.stage]}，浇水施肥加速成长！`);
        }
    }
}

function generateParticles() {
    // 已废弃，背景改为 CSS 实现
}

document.addEventListener('DOMContentLoaded', init);
