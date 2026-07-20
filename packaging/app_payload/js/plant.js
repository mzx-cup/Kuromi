// ============================================================
// 植物数据：80种，5个稀有度
// 普通30 + 稀有20 + 精良15 + 史诗10 + 传说5 = 80种
// ============================================================

// 装饰性粒子配置
const DECORATIVE_LEAVES = ['🍃', '🍂', '🌿', '🌸', '💮', '🪷', '🌺'];
const PARTICLE_COUNT = 8;
const PARTICLE_LIFETIME = 12000; // 12秒

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
    { id: 'radish',    name: '⚪ 白萝卜',   emoji: '⚪', stages: ['🌱','🌿','⚪','⚪'], growTime: 55,  desc: '快根蔬菜', rarity: 'common' },
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
const STAGE_DESCS = [
    '🌰 种子沉睡中，等待破土...',
    '🌱 嫩芽破土而出，充满生机！',
    '🌿 枝叶舒展，茁壮成长中！',
    '🌟 已完全成熟，快来收获吧！'
];
const WATER_PER_ACTION = 20;
const NUTRIENT_PER_ACTION = 15;
const WATER_DECAY_RATE = 2;
const NUTRIENT_DECAY_RATE = 1;
const WATER_TIME_REDUCTION = 5 * 60;
const NUTRIENT_TIME_REDUCTION = 15 * 60;

// ============================================================
// 稀有变体系统：异色 / 炫彩 / 异色炫彩
// ============================================================
const VARIANT_TYPES = {
    NORMAL: 'normal',
    ALT_COLOR: '异色',
    SHINY: '炫彩',
    ALT_SHINY: '异色炫彩'
};

const VARIANT_CONFIG = {
    [VARIANT_TYPES.NORMAL]: { label: '普通', suffix: '', glowColor: '', chance: 0.74 },
    [VARIANT_TYPES.ALT_COLOR]: { label: '异色', suffix: '异', glowColor: '#8b5cf6', chance: 0.15 },
    [VARIANT_TYPES.SHINY]: { label: '炫彩', suffix: '炫', glowColor: '#f59e0b', chance: 0.08 },
    [VARIANT_TYPES.ALT_SHINY]: { label: '异色炫彩', suffix: '异炫', glowColor: '#ec4899', chance: 0.03 }
};

function rollVariantType() {
    const r = Math.random();
    let cumulative = 0;
    // 按 chance 降序遍历，确保异色炫彩(3%)最先被检查
    const entries = Object.entries(VARIANT_CONFIG).sort((a, b) => b[1].chance - a[1].chance);
    for (const [key, config] of entries) {
        cumulative += config.chance;
        if (r < cumulative) return key;
    }
    return VARIANT_TYPES.NORMAL;
}

function getVariantEmoji(baseEmoji, variantType) {
    if (variantType === VARIANT_TYPES.NORMAL) return baseEmoji;
    // 为变体添加不同的后缀标记
    const suffixMap = {
        [VARIANT_TYPES.ALT_COLOR]: '🌈',
        [VARIANT_TYPES.SHINY]: '✨',
        [VARIANT_TYPES.ALT_SHINY]: '💎'
    };
    return baseEmoji + (suffixMap[variantType] || '');
}

const VARIANT_DISPLAY_ORDER = [
    VARIANT_TYPES.ALT_SHINY,
    VARIANT_TYPES.SHINY,
    VARIANT_TYPES.ALT_COLOR,
    VARIANT_TYPES.NORMAL
];

const VARIANT_CLASS_NAMES = {
    [VARIANT_TYPES.NORMAL]: 'variant-normal',
    [VARIANT_TYPES.ALT_COLOR]: 'variant-altcolor',
    [VARIANT_TYPES.SHINY]: 'variant-shiny',
    [VARIANT_TYPES.ALT_SHINY]: 'variant-alt-shiny'
};

const PLANT_ALT_HUE_OVERRIDES = {
    carrot: 242
};

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[char]));
}

function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, '&#96;');
}

function hashText(value) {
    let hash = 0;
    for (let i = 0; i < value.length; i++) {
        hash = ((hash << 5) - hash) + value.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}

function getPlantAltHue(plant) {
    if (Object.prototype.hasOwnProperty.call(PLANT_ALT_HUE_OVERRIDES, plant.id)) {
        return PLANT_ALT_HUE_OVERRIDES[plant.id];
    }
    const rarityOffset = { common: 12, rare: 58, fine: 116, epic: 202, legendary: 284 };
    return (hashText(plant.id) * 37 + (rarityOffset[plant.rarity] || 0)) % 360;
}

function getVariantClass(variantType) {
    return VARIANT_CLASS_NAMES[variantType] || VARIANT_CLASS_NAMES[VARIANT_TYPES.NORMAL];
}

function getVariantLabel(variantType) {
    return (VARIANT_CONFIG[variantType] && VARIANT_CONFIG[variantType].label) || '普通';
}

function getVariantCssVars(plant, variantType) {
    const hue = getPlantAltHue(plant);
    const hue2 = (hue + 48) % 360;
    const hue3 = (hue + 128) % 360;
    return [
        `--variant-hue:${hue}deg`,
        `--variant-accent:hsl(${hue}, 82%, 56%)`,
        `--variant-accent-2:hsl(${hue2}, 88%, 60%)`,
        `--variant-accent-3:hsl(${hue3}, 92%, 66%)`
    ].join(';');
}

function hasVariant(ownedEntry, variantType) {
    if (!ownedEntry) return false;
    if (variantType === VARIANT_TYPES.NORMAL) return true;
    return !!((ownedEntry.variants || {})[variantType]);
}

function getVariantCount(ownedEntry, variantType) {
    if (!ownedEntry) return 0;
    const variants = ownedEntry.variants || {};
    if (variantType === VARIANT_TYPES.NORMAL) {
        return (variants[VARIANT_TYPES.NORMAL] && variants[VARIANT_TYPES.NORMAL].count) || ownedEntry.harvestCount || 1;
    }
    return (variants[variantType] && variants[variantType].count) || 0;
}

function getDisplayVariant(ownedEntry) {
    if (!ownedEntry) return VARIANT_TYPES.NORMAL;
    const variants = ownedEntry.variants || {};
    return VARIANT_DISPLAY_ORDER.find(type => type === VARIANT_TYPES.NORMAL || variants[type]) || VARIANT_TYPES.NORMAL;
}

function renderVariantArt(plant, variantType, options = {}) {
    const classes = [
        'plant-variant-art',
        getVariantClass(variantType),
        options.locked ? 'is-locked' : '',
        options.compact ? 'is-compact' : ''
    ].filter(Boolean).join(' ');

    return `
        <span class="${classes}" style="${getVariantCssVars(plant, variantType)}" aria-hidden="true">
            <span class="variant-aura"></span>
            <span class="variant-emoji-main">${escapeHtml(plant.emoji)}</span>
            <span class="variant-emoji-echo">${escapeHtml(plant.emoji)}</span>
        </span>
    `;
}

function renderVariantBadge(plant, variantType) {
    return `
        <span class="variant-badge ${getVariantClass(variantType)}" style="${getVariantCssVars(plant, variantType)}" title="${escapeAttr(getVariantLabel(variantType))}已收集">
            <span>${escapeHtml(plant.emoji)}</span>
        </span>
    `;
}

// ============================================================
// 天气 API 配置 - 使用 Open-Meteo (免费无需 API key)
// ============================================================

// 天气类型映射
const WEATHER_TYPES = {
    CLEAR: 'clear',       // 晴天
    CLOUDY: 'cloudy',     // 多云/阴天
    RAIN: 'rain',         // 雨天
    SNOW: 'snow',         // 雪天
    SANDSTORM: 'sandstorm' // 沙尘暴
};

// 天气配置
const WEATHER_CONFIG = {
    clear: {
        name: '晴天',
        icon: '☀️',
        growthRate: 1.15,
        waterDecayRate: 2.5,
        nutrientDecayRate: 1.2,
        bgHue: 195,
        particleEffect: 'none'
    },
    cloudy: {
        name: '多云',
        icon: '⛅',
        growthRate: 1.0,
        waterDecayRate: 1.0,
        nutrientDecayRate: 1.0,
        bgHue: 200,
        particleEffect: 'none'
    },
    rain: {
        name: '雨天',
        icon: '🌧️',
        growthRate: 1.05,
        waterDecayRate: 0,
        nutrientDecayRate: 0.8,
        bgHue: 220,
        particleEffect: 'rain'
    },
    snow: {
        name: '雪天',
        icon: '❄️',
        growthRate: 0.4,
        waterDecayRate: 0.3,
        nutrientDecayRate: 0.5,
        bgHue: 230,
        particleEffect: 'snow'
    },
    sandstorm: {
        name: '沙尘暴',
        icon: '🌪️',
        growthRate: 0.6,
        waterDecayRate: 1.8,
        nutrientDecayRate: 1.5,
        bgHue: 35,
        particleEffect: 'sand'
    }
};

let weatherState = {
    currentWeather: 'cloudy',
    temperature: 20,
    city: '',
    cityId: '',
    lastUpdate: 0,
   保温罩: false  // 雪天保温
};

const WEATHER_CITY_STORAGE_KEY = 'starlearn_weather_city';
const WEATHER_MANUAL_STORAGE_KEY = 'starlearn_weather_manual';
const WEATHER_LAST_CITY_STORAGE_KEY = 'starlearn_weather_last_city';
const WEATHER_CITY_PLACEHOLDERS = new Set(['定位中', '当前位置', '请点击设置城市', '未知', '定位不支持', '自动定位失败']);

function isValidWeatherCity(cityName) {
    return Boolean(cityName && !WEATHER_CITY_PLACEHOLDERS.has(cityName));
}

function getStoredWeatherCity() {
    const cityName = localStorage.getItem(WEATHER_CITY_STORAGE_KEY) || '';
    if (!cityName) return '';
    if (!isValidWeatherCity(cityName)) {
        localStorage.removeItem(WEATHER_CITY_STORAGE_KEY);
        return '';
    }
    return cityName;
}

function getLastWeatherCity() {
    const cityName = localStorage.getItem(WEATHER_LAST_CITY_STORAGE_KEY) || '';
    return isValidWeatherCity(cityName) ? cityName : '';
}

function rememberWeatherCity(cityName, displayName = cityName) {
    if (!isValidWeatherCity(cityName)) return;
    localStorage.setItem(WEATHER_CITY_STORAGE_KEY, cityName);
    const displayCity = isValidWeatherCity(displayName) ? displayName : cityName;
    localStorage.setItem(WEATHER_LAST_CITY_STORAGE_KEY, displayCity);
}

function getWeatherFallbackCity(defaultLabel = '自动定位失败', preferredCity = '') {
    if (isValidWeatherCity(preferredCity)) return preferredCity;
    return getStoredWeatherCity() || getLastWeatherCity() || defaultLabel;
}

async function fallbackWeatherAfterLocationFailure(defaultLabel = '自动定位失败', preferredCity = '') {
    const networkLocated = await fetchWeatherByNetworkLocation();
    if (networkLocated) return;

    const fallbackCity = getWeatherFallbackCity(defaultLabel, preferredCity);
    if (isValidWeatherCity(fallbackCity)) {
        await fetchWeatherByCity(fallbackCity, { silentFallback: true });
    } else {
        setDefaultWeatherWithCity(defaultLabel);
    }
}

// ============================================================
// 天气系统
// ============================================================
async function initWeather() {
    console.log('Initializing weather...');

    const cachedWeather = localStorage.getItem('starlearn_weather');
    if (cachedWeather) {
        try {
            weatherState = { ...weatherState, ...JSON.parse(cachedWeather) };
            if (!isValidWeatherCity(weatherState.city)) {
                weatherState.city = getStoredWeatherCity() || getLastWeatherCity() || '定位中';
            }
            updateWeatherDisplay();
        } catch (e) {
            console.warn('Weather cache invalid, refreshing:', e);
        }
    }

    await fetchWeather();

    // 确保 UI 更新
    console.log('Final weather state:', weatherState);
    updateWeatherDisplay();
}

async function fetchWeather() {
    const city = getStoredWeatherCity();
    const isManual = localStorage.getItem(WEATHER_MANUAL_STORAGE_KEY) === '1';
    if (!city) {
        await fetchWeatherByIP();
        return;
    }
    // 如果是手动设置的城市，直接使用；否则先尝试 IP 定位获取更精确位置
    if (isManual) {
        await fetchWeatherByCity(city);
    } else {
        // 自动定位的场景，优先用 IP 重新定位（可能已移动）
        await fetchWeatherByIP(city);
    }
}

async function fetchWeatherByIP(fallbackCity = '') {
    // 首先检查浏览器是否支持 Geolocation API
    if (!navigator.geolocation) {
        console.warn('Geolocation not supported, using default');
        await fallbackWeatherAfterLocationFailure('定位不支持', fallbackCity);
        return;
    }

    // 使用浏览器原生 Geolocation API
    return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                console.log('Got coordinates:', lat, lon);

                // 保存坐标
                weatherState.lat = lat;
                weatherState.lon = lon;

                try {
                    // 尝试 BigDataCloud 逆地理编码 (支持 CORS)
                    const bdcRes = await fetch(
                        `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}`
                    );
                    if (bdcRes.ok) {
                        const bdcData = await bdcRes.json();
                        // 对于直辖市（principalSubdivision 含"市"），优先使用 principalSubdivision
                        // 对于省份，优先使用 city，如果没有则组合 locality + principalSubdivision
                        let cityName = '';
                        const subdivision = bdcData.principalSubdivision || '';
                        const isMunicipality = subdivision.includes('市') &&
                            (subdivision.includes('北京') || subdivision.includes('上海') ||
                             subdivision.includes('天津') || subdivision.includes('重庆'));

                        if (isMunicipality) {
                            // 直辖市：使用 locality（区/县）作为 API 查询名，完整名称用于显示
                            const district = bdcData.locality || bdcData.city || '';
                            const apiName = district || subdivision;
                            const displayName = (district && district !== subdivision) ? district + ', ' + subdivision : (district || subdivision);
                            weatherState.city = displayName; // 显示用完整名称（如"巴南区, 重庆市"）
                            cityName = apiName; // localStorage / API 用纯净区名
                        } else {
                            // 其他省份：优先使用 city，其次组合 locality + 省份
                            cityName = bdcData.city || '';
                            if (!cityName && bdcData.locality && subdivision) {
                                cityName = bdcData.locality + ' ' + subdivision;
                            } else if (!cityName && subdivision) {
                                cityName = subdivision;
                            }
                            weatherState.city = cityName;
                        }

                        if (cityName) {
                            console.log('BigDataCloud reverse geocoded city:', cityName, 'display:', weatherState.city);
                            rememberWeatherCity(cityName, weatherState.city);
                            await fetchWeatherByCity(cityName);
                            resolve();
                            return;
                        }
                    }

                    // 备用：尝试 Open-Meteo 逆地理编码
                    try {
                        const reverseGeoRes = await fetch(
                            `https://geocoding-api.open-meteo.com/v1/reverse?latitude=${lat}&longitude=${lon}&language=zh&count=1`
                        );
                        if (reverseGeoRes.ok) {
                            const reverseGeoData = await reverseGeoRes.json();
                            if (reverseGeoData.results && reverseGeoData.results[0]) {
                                const cityName = reverseGeoData.results[0].name;
                                console.log('Open-Meteo reverse geocoded city:', cityName);
                                weatherState.city = cityName;
                                rememberWeatherCity(cityName);
                                await fetchWeatherByCity(cityName);
                                resolve();
                                return;
                            }
                        }
                    } catch (omErr) {
                        console.warn('Open-Meteo reverse geocoding failed:', omErr);
                    }

                    // 备用：尝试 Nominatim
                    try {
                        const nominatimRes = await fetch(
                            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=zh`,
                            { headers: { 'User-Agent': 'StarLearn-App/1.0' } }
                        );
                        if (nominatimRes.ok) {
                            const nominatimData = await nominatimRes.json();
                            if (nominatimData.address) {
                                const addr = nominatimData.address;
                                // 对于直辖市（state 含"市"），优先使用 state，避免 county（区）不准确
                                let city = '';
                                if (addr.state && addr.state.includes('市')) {
                                    // 直辖市：显示"巴南区, 重庆市"，API 查询只用区名
                                    const district = addr.city || addr.town || addr.village || addr.county || '';
                                    const apiName = district || addr.state;
                                    const displayName = (district && district !== addr.state) ? district + ', ' + addr.state : (district || addr.state);
                                    weatherState.city = displayName;
                                    city = apiName;
                                } else {
                                    city = addr.city || addr.town || addr.village || addr.county || addr.state;
                                    weatherState.city = city;
                                }
                                if (city) {
                                    console.log('Nominatim reverse geocoded city:', city, 'display:', weatherState.city);
                                    rememberWeatherCity(city, weatherState.city);
                                    await fetchWeatherByCity(city);
                                    resolve();
                                    return;
                                }
                            }
                        }
                    } catch (nominatimErr) {
                        console.warn('Nominatim reverse geocoding failed:', nominatimErr);
                    }

                    // 如果所有逆地理编码都失败，直接用坐标获取天气
                    weatherState.city = getWeatherFallbackCity('当前位置', fallbackCity);
                    await fetchWeatherByCoordinates(lat, lon);
                    resolve();
                } catch (e) {
                    console.error('All reverse geocoding failed:', e);
                    weatherState.city = getWeatherFallbackCity('当前位置', fallbackCity);
                    await fetchWeatherByCoordinates(lat, lon);
                    resolve();
                }
            },
            async (error) => {
                console.warn('Geolocation error:', error.message);
                // 定位被拒绝或失败时，先尝试网络定位，再回退到上次成功城市
                await fallbackWeatherAfterLocationFailure('自动定位失败', fallbackCity);
                resolve();
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // 缓存5分钟
            }
        );
    });
}

// 浏览器定位不可用时，用 IP 粗定位做兜底
async function fetchWeatherByNetworkLocation() {
    try {
        const locationRes = await fetch('https://ipapi.co/json/');
        if (!locationRes.ok) throw new Error('IP location lookup failed');
        const locationData = await locationRes.json();
        const cityName = locationData.city || locationData.region || locationData.country_name || '';
        const lat = Number(locationData.latitude);
        const lon = Number(locationData.longitude);

        if (!cityName && (!Number.isFinite(lat) || !Number.isFinite(lon))) {
            return false;
        }

        weatherState.city = cityName || '当前位置';
        if (cityName) rememberWeatherCity(cityName);

        if (Number.isFinite(lat) && Number.isFinite(lon)) {
            await fetchWeatherByCoordinates(lat, lon);
            return true;
        }

        await fetchWeatherByCity(cityName, { silentFallback: true });
        return true;
    } catch (e) {
        console.warn('IP location fallback failed:', e);
        return false;
    }
}

// 通过坐标获取天气（不通过城市名）
async function fetchWeatherByCoordinates(lat, lon) {
    try {
        const weatherRes = await fetch(
            `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true&timezone=auto`
        );
        if (!weatherRes.ok) throw new Error('Weather fetch failed');
        const weatherData = await weatherRes.json();

        if (weatherData.current_weather) {
            weatherState.lastUpdate = Date.now();
            processWeatherDataFromOpenMeteo(weatherData.current_weather);
            applyWeatherEffect(weatherState.currentWeather);
            updateWeatherDisplay();
            saveWeatherState();
        } else {
            setDefaultWeatherWithCity(weatherState.city);
        }
    } catch (e) {
        console.error('Weather fetch by coordinates failed:', e);
        setDefaultWeatherWithCity(weatherState.city);
    }
}

// 使用 Open-Meteo 免费天气 API
async function fetchWeatherByCity(cityName, options = {}) {
    // 过滤无效或占位的城市名称
    if (!isValidWeatherCity(cityName)) {
        console.warn('Invalid city name, falling back to IP-based weather');
        await fetchWeatherByIP();
        return;
    }

    try {
        // 1. 先用 Open-Meteo Geocoding API 获取城市坐标
        const geoRes = await fetch(
            `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=1&language=zh&format=json`
        );
        if (!geoRes.ok) throw new Error('Geo lookup failed');
        const geoData = await geoRes.json();

        if (!geoData.results || geoData.results.length === 0) {
            throw new Error('City not found');
        }

        const { latitude, longitude, name, country } = geoData.results[0];
        weatherState.city = name;
        rememberWeatherCity(cityName, name);

        // 2. 用坐标获取天气
        const weatherRes = await fetch(
            `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current_weather=true&timezone=auto`
        );
        if (!weatherRes.ok) throw new Error('Weather fetch failed');
        const weatherData = await weatherRes.json();

        if (weatherData.current_weather) {
            weatherState.lastUpdate = Date.now();
            processWeatherDataFromOpenMeteo(weatherData.current_weather);
            applyWeatherEffect(weatherState.currentWeather);
            updateWeatherDisplay();
            saveWeatherState();
        } else {
            setDefaultWeatherWithCity(name);
        }
    } catch (e) {
        console.error('Weather fetch by city failed:', e);
        // 城市无法识别，清除无效的城市缓存，切换到自动定位
        localStorage.removeItem(WEATHER_CITY_STORAGE_KEY);
        if (localStorage.getItem(WEATHER_LAST_CITY_STORAGE_KEY) === cityName) {
            localStorage.removeItem(WEATHER_LAST_CITY_STORAGE_KEY);
        }
        if (!options.silentFallback) {
            showTip('🌍 城市未找到，已切换为自动定位');
        }
        setDefaultWeatherWithCity(options.silentFallback ? '自动定位失败' : '请点击设置城市');
    }
}

// 处理 Open-Meteo 天气数据
function processWeatherDataFromOpenMeteo(weather) {
    weatherState.temperature = Math.round(weather.temperature);
    const weatherCode = weather.weathercode;

    // WMO 天气码映射到我们的天气类型
    // 0: 晴天, 1-3: 多云, 45-48: 雾, 51-67: 雨, 71-77: 雪, 80-82: 阵雨, 85-86: 阵雪, 95-99: 雷暴
    if (weatherCode === 0) {
        weatherState.currentWeather = WEATHER_TYPES.CLEAR;
    } else if (weatherCode >= 1 && weatherCode <= 3) {
        weatherState.currentWeather = WEATHER_TYPES.CLOUDY;
    } else if (weatherCode >= 45 && weatherCode <= 48) {
        weatherState.currentWeather = WEATHER_TYPES.CLOUDY; // 雾按多云处理
    } else if ((weatherCode >= 51 && weatherCode <= 67) || (weatherCode >= 80 && weatherCode <= 82)) {
        weatherState.currentWeather = WEATHER_TYPES.RAIN;
    } else if ((weatherCode >= 71 && weatherCode <= 77) || (weatherCode >= 85 && weatherCode <= 86)) {
        weatherState.currentWeather = WEATHER_TYPES.SNOW;
    } else if (weatherCode >= 95) {
        weatherState.currentWeather = WEATHER_TYPES.RAIN; // 雷暴按雨天处理
    } else {
        weatherState.currentWeather = WEATHER_TYPES.CLOUDY;
    }
}

function setDefaultWeatherWithCity(cityName) {
    weatherState.currentWeather = WEATHER_TYPES.CLOUDY;
    weatherState.temperature = 20;
    weatherState.city = cityName;
    weatherState.lastUpdate = Date.now();
    applyWeatherEffect(WEATHER_TYPES.CLOUDY);
    updateWeatherDisplay();
}

function processWeatherData(nowData) {
    weatherState.temperature = parseInt(nowData.temp) || 20;
    const weatherCode = parseInt(nowData.icon);

    // 根据天气码判断天气类型
    let weatherType = WEATHER_TYPES.CLOUDY;

    // 和风天气码映射：1xx=晴, 2xx=阴天, 3xx=雨, 4xx=雪, 5xx=雾, 6xx=沙尘, 7xx=大风, 8xx=云, 9xx=晴天
    if (weatherCode >= 100 && weatherCode < 104) {
        weatherType = WEATHER_TYPES.CLEAR;
    } else if ((weatherCode >= 104 && weatherCode < 150) || (weatherCode >= 152 && weatherCode < 160)) {
        weatherType = WEATHER_TYPES.CLOUDY;
    } else if (weatherCode >= 300 && weatherCode < 350) {
        weatherType = WEATHER_TYPES.RAIN;
    } else if (weatherCode >= 400 && weatherCode < 450) {
        weatherType = WEATHER_TYPES.SNOW;
    } else if (weatherCode >= 500 && weatherCode < 515) {
        weatherType = WEATHER_TYPES.RAIN; // 雾按雨天处理
    } else if (weatherCode >= 600 && weatherCode < 630) {
        weatherType = WEATHER_TYPES.SANDSTORM;
    } else if (weatherCode >= 150 && weatherCode < 160) {
        weatherType = WEATHER_TYPES.CLOUDY;
    } else if (weatherCode >= 160 && weatherCode < 170) {
        weatherType = WEATHER_TYPES.CLOUDY;
    } else if (weatherCode >= 170 && weatherCode < 200) {
        weatherType = WEATHER_TYPES.CLEAR;
    } else {
        weatherType = WEATHER_TYPES.CLOUDY;
    }

    weatherState.currentWeather = weatherType;
    weatherState.lastUpdate = Date.now();
    saveWeatherState();
    applyWeatherEffect(weatherType);

    // 更新UI显示
    updateWeatherDisplay();
}

function setDefaultWeather() {
    weatherState.currentWeather = WEATHER_TYPES.CLOUDY;
    weatherState.temperature = 20;
    // 不覆盖城市名，保持已有值
    weatherState.lastUpdate = Date.now();
    applyWeatherEffect(WEATHER_TYPES.CLOUDY);
    updateWeatherDisplay();
}

function saveWeatherState() {
    localStorage.setItem('starlearn_weather', JSON.stringify(weatherState));
}

function updateWeatherDisplay() {
    const tempDisplay = document.getElementById('weather-temp');
    const iconDisplay = document.getElementById('weather-icon');
    const cityDisplay = document.getElementById('weather-city');

    if (tempDisplay) tempDisplay.textContent = weatherState.temperature + '°C';
    if (iconDisplay) iconDisplay.textContent = WEATHER_CONFIG[weatherState.currentWeather].icon;
    if (cityDisplay) cityDisplay.textContent = weatherState.city;

    // 应用天气背景类
    document.body.className = 'weather-' + weatherState.currentWeather;
}

function applyWeatherEffect(weatherType) {
    const config = WEATHER_CONFIG[weatherType];
    if (!config) return;

    // 更新背景色调
    document.documentElement.style.setProperty('--weather-hue', config.bgHue);

    // 清除现有粒子效果
    clearWeatherParticles();

    // 应用新的粒子效果
    switch (config.particleEffect) {
        case 'rain':
            startRainEffect();
            break;
        case 'snow':
            startSnowEffect();
            break;
        case 'sand':
            startSandEffect();
            break;
    }
}

function clearWeatherParticles() {
    const container = document.getElementById('weather-particles');
    if (container) {
        container.innerHTML = '';
    }
}

// ============================================================
// 雨滴效果
// ============================================================
let rainInterval = null;

function startRainEffect() {
    const container = document.getElementById('weather-particles') || createWeatherContainer();
    if (!container) return;

    stopWeatherEffect();

    const createRainDrop = () => {
        const drop = document.createElement('div');
        drop.className = 'rain-drop';
        drop.style.left = Math.random() * 100 + '%';
        drop.style.animationDuration = (0.5 + Math.random() * 0.3) + 's';
        drop.style.opacity = 0.3 + Math.random() * 0.5;
        drop.style.width = (1 + Math.random() * 2) + 'px';
        drop.style.height = (15 + Math.random() * 20) + 'px';
        container.appendChild(drop);

        setTimeout(() => drop.remove(), 1200);
    };

    // 初始创建
    for (let i = 0; i < 50; i++) {
        setTimeout(createRainDrop, i * 20);
    }

    // 持续生成
    rainInterval = setInterval(() => {
        for (let i = 0; i < 5; i++) {
            createRainDrop();
        }
    }, 100);
}

function stopWeatherEffect() {
    if (rainInterval) {
        clearInterval(rainInterval);
        rainInterval = null;
    }
    if (snowInterval) {
        clearInterval(snowInterval);
        snowInterval = null;
    }
}

// ============================================================
// 雪花效果
// ============================================================
let snowInterval = null;

function startSnowEffect() {
    const container = document.getElementById('weather-particles') || createWeatherContainer();
    if (!container) return;

    stopWeatherEffect();

    const createSnowflake = () => {
        const flake = document.createElement('div');
        flake.className = 'snow-flake';
        flake.textContent = ['❄', '❅', '❆', '✦', '✧'][Math.floor(Math.random() * 5)];
        flake.style.left = Math.random() * 100 + '%';
        flake.style.animationDuration = (4 + Math.random() * 4) + 's';
        flake.style.opacity = 0.5 + Math.random() * 0.5;
        flake.style.fontSize = (8 + Math.random() * 12) + 'px';
        container.appendChild(flake);

        setTimeout(() => flake.remove(), 9000);
    };

    // 初始创建
    for (let i = 0; i < 30; i++) {
        setTimeout(createSnowflake, i * 200);
    }

    // 持续生成
    snowInterval = setInterval(() => {
        for (let i = 0; i < 3; i++) {
            createSnowflake();
        }
    }, 500);
}

// ============================================================
// 沙尘效果
// ============================================================
let sandInterval = null;

function startSandEffect() {
    const container = document.getElementById('weather-particles') || createWeatherContainer();
    if (!container) return;

    stopWeatherEffect();

    const createSandParticle = () => {
        const particle = document.createElement('div');
        particle.className = 'sand-particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDuration = (3 + Math.random() * 3) + 's';
        particle.style.opacity = 0.2 + Math.random() * 0.4;
        particle.style.width = (2 + Math.random() * 4) + 'px';
        particle.style.height = (2 + Math.random() * 4) + 'px';
        particle.style.background = `rgba(200, 170, 120, ${0.3 + Math.random() * 0.4})`;
        container.appendChild(particle);

        setTimeout(() => particle.remove(), 7000);
    };

    // 初始创建
    for (let i = 0; i < 40; i++) {
        setTimeout(createSandParticle, i * 100);
    }

    // 持续生成
    sandInterval = setInterval(() => {
        for (let i = 0; i < 4; i++) {
            createSandParticle();
        }
    }, 200);
}

function createWeatherContainer() {
    const existing = document.getElementById('weather-particles');
    if (existing) return existing;

    const container = document.createElement('div');
    container.id = 'weather-particles';
    container.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
        z-index: 4;
        overflow: hidden;
    `;
    document.body.appendChild(container);
    return container;
}

// ============================================================
// 保温罩功能（雪天）
// ============================================================
function toggle保温罩() {
    if (weatherState.currentWeather !== WEATHER_TYPES.SNOW) {
        showTip('❄️ 只有雪天才需要保温罩！');
        return;
    }

    weatherState.保温罩 = !weatherState.保温罩;
    update保温罩Display();

    if (weatherState.保温罩) {
        showTip('🔥 保温罩已开启，植物生长速度恢复 80%！');
        try { triggerHarvestEffect(true); } catch(e) { /* ignore */ }
    } else {
        showTip('❄️ 保温罩已关闭，植物生长缓慢...');
    }
}

function update保温罩Display() {
    const btn = document.getElementById('insulation-btn');
    if (!btn) return;

    if (weatherState.保温罩) {
        btn.style.background = 'linear-gradient(135deg, #ff7043, #ff5722)';
        btn.style.boxShadow = '0 6px 20px rgba(255, 112, 67, 0.5)';
        btn.innerHTML = '<span class="btn-icon">🔥</span><span class="btn-label">保温中</span>';
    } else {
        btn.style.background = 'linear-gradient(135deg, #90a4ae, #607d8b)';
        btn.style.boxShadow = '0 6px 20px rgba(96, 125, 139, 0.3)';
        btn.innerHTML = '<span class="btn-icon">❄️</span><span class="btn-label">保温罩</span>';
    }
}

// 获取当前天气加成
function getWeatherGrowthMultiplier() {
    const config = WEATHER_CONFIG[weatherState.currentWeather];
    if (!config) return 1;

    let rate = config.growthRate;

    // 雪天且开启保温罩
    if (weatherState.currentWeather === WEATHER_TYPES.SNOW && weatherState.保温罩) {
        rate = Math.max(rate, 0.8); // 保温罩恢复80%生长
    }

    // 温度修正：极端温度影响生长
    const temp = weatherState.temperature;
    if (temp > 35) {
        rate *= 0.7; // 酷热，生长缓慢
    } else if (temp >= 25 && temp <= 35) {
        rate *= 0.9; // 较热，轻微影响
    } else if (temp >= 15 && temp < 25) {
        rate *= 1.1; // 适宜温度，加速生长
    } else if (temp >= 5 && temp < 15) {
        rate *= 0.85; // 偏冷
    } else if (temp < 5) {
        rate *= 0.6; // 严寒
    }

    return Math.max(0.1, rate); // 最低不低于 0.1
}

function getWeatherWaterDecayMultiplier() {
    const config = WEATHER_CONFIG[weatherState.currentWeather];
    let rate = config ? config.waterDecayRate : 1;

    // 温度修正
    const temp = weatherState.temperature;
    if (temp > 35) rate *= 2.0;
    else if (temp >= 15 && temp < 25) rate *= 0.8;

    return rate;
}

function getWeatherNutrientDecayMultiplier() {
    const config = WEATHER_CONFIG[weatherState.currentWeather];
    let rate = config ? config.nutrientDecayRate : 1;

    // 温度修正
    const temp = weatherState.temperature;
    if (temp > 35) rate *= 1.5;
    else if (temp >= 15 && temp < 25) rate *= 0.85;

    return rate;
}

// ============================================================
// 天气 UI 渲染
// ============================================================
function renderWeatherUI() {
    return `
        <div class="weather-display" id="weather-display">
            <span class="weather-icon" id="weather-icon">⛅</span>
            <span class="weather-temp" id="weather-temp">--°C</span>
            <span class="weather-city" id="weather-city">定位中</span>
        </div>
        <button class="weather-settings-btn" onclick="openWeatherSettings()" title="设置城市">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
        </button>
    `;
}

// 天气设置弹窗
function openWeatherSettings() {
    const currentCity = getStoredWeatherCity() || getLastWeatherCity();
    const input = prompt('请输入城市名称（如：重庆、北京、巴南区）:\n输入精确区县名称可获得更准确定位\n留空则使用自动定位', currentCity);
    if (input === null) return; // 用户取消

    const city = input.trim();
    if (city) {
        localStorage.setItem(WEATHER_CITY_STORAGE_KEY, city);
        localStorage.setItem(WEATHER_MANUAL_STORAGE_KEY, '1');
        showTip(`🌍 已设置城市为：${city}，正在获取天气...`);
        fetchWeatherByCity(city);
    } else {
        localStorage.removeItem(WEATHER_CITY_STORAGE_KEY);
        localStorage.removeItem(WEATHER_MANUAL_STORAGE_KEY);
        showTip('🌍 已切换为自动定位，正在获取天气...');
        fetchWeatherByIP();
    }
}
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
    // 启动装饰性落叶/花瓣粒子
    startDecorativeParticles();
    // 初始化天气系统（异步）
    initWeather().then(() => {
        console.log('Weather initialized:', weatherState);
    }).catch(e => {
        console.error('Weather init failed:', e);
    });
}

// ============================================================
// 装饰性落叶/花瓣粒子效果 - 营造治愈氛围
// ============================================================
function createFallingParticle() {
    const container = document.getElementById('falling-particles');
    if (!container) return;

    const leaf = document.createElement('div');
    leaf.className = 'falling-leaf';
    leaf.textContent = DECORATIVE_LEAVES[Math.floor(Math.random() * DECORATIVE_LEAVES.length)];
    leaf.style.left = Math.random() * 100 + '%';
    leaf.style.animationDuration = (10 + Math.random() * 8) + 's';
    leaf.style.animationDelay = Math.random() * 2 + 's';
    leaf.style.fontSize = (14 + Math.random() * 10) + 'px';
    leaf.style.opacity = 0.5 + Math.random() * 0.4;

    container.appendChild(leaf);

    setTimeout(() => {
        if (leaf.parentNode) {
            leaf.remove();
        }
    }, PARTICLE_LIFETIME);
}

function startDecorativeParticles() {
    // 初始创建几个粒子
    for (let i = 0; i < 3; i++) {
        setTimeout(() => createFallingParticle(), i * 1500);
    }
    // 持续生成粒子
    setInterval(() => {
        if (document.querySelectorAll('.falling-leaf').length < PARTICLE_COUNT) {
            createFallingParticle();
        }
    }, 3000 + Math.random() * 4000);
}

// ============================================================
// 阶段升级闪光效果
// ============================================================
function triggerStageUpEffect(slotIndex) {
    const display = document.getElementById(`plant-display-${slotIndex}`) || document.getElementById('plant-display');
    const potWrapper = document.querySelector(`.plant-pot-wrapper[data-slot='${slotIndex}']`);

    if (display) {
        display.classList.remove('plant-grow-anim');
        void display.offsetWidth;
        display.classList.add('plant-grow-anim');
    }

    // 添加闪光效果
    if (potWrapper) {
        const flash = document.createElement('div');
        flash.className = 'stage-up-flash';
        potWrapper.appendChild(flash);
        setTimeout(() => flash.remove(), 1000);
    }

    // 触发收获粒子效果（少量）
    try { triggerHarvestEffect(true); } catch(e) { /* ignore */ }
}

// ============================================================
// 收获粒子效果
// ============================================================
function triggerHarvestEffect(isMini) {
    const goldRain = document.getElementById('gold-rain');
    if (!goldRain) return;

    const count = isMini ? 8 : 24;
    const emojis = isMini ? ['✨', '⭐', '💫'] : ['🪙', '✨', '⭐', '💫', '🌟'];

    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'gold-particle';
        particle.textContent = emojis[Math.floor(Math.random() * emojis.length)];
        particle.style.left = (20 + Math.random() * 60) + '%';
        particle.style.top = (10 + Math.random() * 40) + '%';
        particle.style.fontSize = (isMini ? 12 : 16) + Math.random() * 8 + 'px';
        particle.style.animationDuration = (1.5 + Math.random() * 1.5) + 's';
        particle.style.animationDelay = Math.random() * 0.5 + 's';
        goldRain.appendChild(particle);
        setTimeout(() => particle.remove(), 3000);
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

    // 兼容旧格式 ownedPlants（字符串数组）→ 新格式（对象数组）
    if (plantState.ownedPlants && plantState.ownedPlants.length > 0) {
        if (typeof plantState.ownedPlants[0] === 'string') {
            plantState.ownedPlants = plantState.ownedPlants.map(id => {
                const plant = PLANT_DATA.find(p => p.id === id);
                return plant ? { id: plant.id, name: plant.name, emoji: plant.emoji, rarity: plant.rarity } : null;
            }).filter(Boolean);
        } else {
            // 兼容旧对象格式：补充缺失的 obtainedAt 和 harvestCount 字段
            plantState.ownedPlants = plantState.ownedPlants.map(entry => {
                if (entry && typeof entry === 'object' && !entry.hasOwnProperty('harvestCount')) {
                    // 这些是旧版本获取的植物，无法知道确切获取时间
                    // 设为当前时间作为估算值
                    return { ...entry, obtainedAt: Date.now(), harvestCount: 1 };
                }
                return entry;
            });
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
    // 同步到服务端数据库
    if (window.StarData) StarData.setPlants(toSave, plantState.seeds);
    // 广播自定义事件，通知其他页面（如个人中心）
    window.dispatchEvent(new CustomEvent('plantStateUpdated', { detail: toSave }));
}

function renderSeedCount() {
    // 更新导航栏种子数
    const navEl = document.getElementById('seed-count-nav');
    if (navEl) navEl.textContent = plantState.seeds;
    // 同步到 localStorage
    localStorage.setItem('starlearn_seeds', String(plantState.seeds));
    // 同步到服务端数据库
    if (window.StarData) StarData.setSeeds(plantState.seeds);
}

function renderPlantCollection() {
    const grid = document.getElementById('plant-collection');
    if (!grid) return;

    grid.innerHTML = PLANT_DATA.map(plant => {
        const ownedEntry = plantState.ownedPlants.find(o => o.id === plant.id);
        const owned = !!ownedEntry;
        const rarityColor = RARITY_COLORS[plant.rarity];
        const rarityBg = RARITY_BG[plant.rarity];
        const variants = (ownedEntry && ownedEntry.variants) || {};
        const displayVariant = getDisplayVariant(ownedEntry);
        const displayVariantClass = getVariantClass(displayVariant);
        const displayVariantLabel = getVariantLabel(displayVariant);
        const cardTitle = `${plant.name} · ${plant.desc}${displayVariant !== VARIANT_TYPES.NORMAL ? ` · ${displayVariantLabel}` : ''}`;

        const variantBadges = [
            VARIANT_TYPES.ALT_COLOR,
            VARIANT_TYPES.SHINY,
            VARIANT_TYPES.ALT_SHINY
        ].filter(type => variants[type]).map(type => renderVariantBadge(plant, type)).join('');

        const itemClasses = [
            'plant-collection-item',
            owned ? 'owned' : '',
            `collection-${displayVariantClass}`,
            displayVariant !== VARIANT_TYPES.NORMAL ? 'has-special-variant' : ''
        ].filter(Boolean).join(' ');

        return `
            <div class="${itemClasses}" data-plant-id="${escapeAttr(plant.id)}" style="${getVariantCssVars(plant, displayVariant)}" onclick="showPlantDetail('${escapeAttr(plant.id)}')" title="${escapeAttr(cardTitle)}">
                <div class="item-rarity-dot" style="background:${rarityColor}"></div>
                ${renderVariantArt(plant, displayVariant, { compact: true })}
                <span class="item-name">${escapeHtml(plant.name)}</span>
                ${displayVariant !== VARIANT_TYPES.NORMAL ? `<span class="item-variant-label">${escapeHtml(displayVariantLabel)}</span>` : ''}
                ${owned ? `<span class="item-owned-tag" style="color:${rarityColor};background:${rarityBg}">${RARITY_NAMES[plant.rarity]}</span>` : ''}
                ${variantBadges ? `<div class="variant-badges-row">${variantBadges}</div>` : ''}
            </div>
        `;
    }).join('');

    // 更新已拥有计数
    const ownedCountEl = document.getElementById('owned-count');
    if (ownedCountEl) {
        ownedCountEl.textContent = plantState.ownedPlants.length;
    }
}

function bindHarvestRevealEvents(modal) {
    if (!modal || modal.dataset.eventsBound === '1') return;
    modal.addEventListener('click', handleHarvestRevealJump);
    modal.addEventListener('pointerup', handleHarvestRevealJump);
    modal.dataset.eventsBound = '1';
}

function getHarvestRevealModal() {
    let modal = document.getElementById('plant-harvest-reveal');
    if (modal) {
        bindHarvestRevealEvents(modal);
        return modal;
    }

    modal = document.createElement('div');
    modal.id = 'plant-harvest-reveal';
    modal.className = 'plant-harvest-reveal';
    modal.innerHTML = '<div class="plant-harvest-reveal-card" role="button" tabindex="0"></div>';
    bindHarvestRevealEvents(modal);
    document.body.appendChild(modal);
    return modal;
}

function closeHarvestReveal() {
    const modal = document.getElementById('plant-harvest-reveal');
    if (modal) {
        modal.classList.remove('active');
        delete modal.dataset.jumping;
    }
}

function scrollToCollectionPlant(plantId) {
    closeHarvestReveal();
    const target = document.querySelector(`.plant-collection-item[data-plant-id="${plantId}"]`);
    if (!target) return;

    target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    target.classList.remove('collection-focus');
    void target.offsetWidth;
    target.classList.add('collection-focus');
    setTimeout(() => target.classList.remove('collection-focus'), 2200);
}

function handleHarvestRevealJump(event) {
    const modal = document.getElementById('plant-harvest-reveal');
    if (!modal || !modal.classList.contains('active') || modal.dataset.jumping === '1') return;

    const plantId = modal.dataset.plantId;
    modal.dataset.jumping = '1';
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    scrollToCollectionPlant(plantId);
}

function showHarvestReveal(plant, variantType, rarityName) {
    const modal = getHarvestRevealModal();
    const card = modal.querySelector('.plant-harvest-reveal-card');
    if (!card) return;

    const variantLabel = getVariantLabel(variantType);
    const variantText = variantType === VARIANT_TYPES.NORMAL ? '原色' : variantLabel;
    card.style.cssText = getVariantCssVars(plant, variantType);
    card.innerHTML = `
        <div class="harvest-reveal-kicker">收获成功</div>
        <div class="harvest-reveal-art-wrap">
            ${renderVariantArt(plant, variantType)}
        </div>
        <div class="harvest-reveal-name">${escapeHtml(plant.name)}</div>
        <div class="harvest-reveal-meta">
            <span>${escapeHtml(rarityName)}</span>
            <span>${escapeHtml(variantText)}</span>
        </div>
    `;

    modal.dataset.plantId = plant.id;
    delete modal.dataset.jumping;
    modal.onclick = null;
    modal.onpointerup = null;
    card.onclick = null;
    card.onpointerup = null;
    card.onkeydown = (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            handleHarvestRevealJump(event);
        }
    };

    modal.classList.add('active');
    card.focus({ preventScroll: true });
}

// 显示植物详情弹窗
function showPlantDetail(plantId) {
    const plant = PLANT_DATA.find(p => p.id === plantId);
    if (!plant) return;

    const ownedEntry = plantState.ownedPlants.find(o => o.id === plantId);
    const owned = !!ownedEntry;
    const rarityColor = RARITY_COLORS[plant.rarity];
    const rarityBg = RARITY_BG[plant.rarity];

    // 更新弹窗内容
    const detailVariant = getDisplayVariant(ownedEntry);
    const detailEmojiEl = document.getElementById('detail-emoji');
    if (detailEmojiEl) {
        detailEmojiEl.innerHTML = renderVariantArt(plant, detailVariant, { compact: true, locked: !owned });
    }
    document.getElementById('detail-name').textContent = plant.name;
    document.getElementById('detail-desc').textContent = plant.desc;

    const rarityEl = document.getElementById('detail-rarity');
    rarityEl.textContent = RARITY_NAMES[plant.rarity];
    rarityEl.style.color = rarityColor;
    rarityEl.style.background = rarityBg;

    const obtainedEl = document.getElementById('detail-obtained');
    if (owned) {
        obtainedEl.textContent = '已获取 ✓';
        obtainedEl.className = 'detail-stat-value obtained';
    } else {
        obtainedEl.textContent = '未获取';
        obtainedEl.className = 'detail-stat-value not-obtained';
    }

    const obtainedTimeEl = document.getElementById('detail-obtained-time');
    if (owned && ownedEntry.obtainedAt) {
        const date = new Date(ownedEntry.obtainedAt);
        obtainedTimeEl.textContent = `${date.getFullYear()}/${String(date.getMonth()+1).padStart(2,'0')}/${String(date.getDate()).padStart(2,'0')} ${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}`;
    } else {
        obtainedTimeEl.textContent = '--';
    }

    document.getElementById('detail-harvest-count').textContent = owned ? (ownedEntry.harvestCount || 1) : '0';
    document.getElementById('detail-rarity-level').textContent = RARITY_NAMES[plant.rarity];

    const growTimeEl = document.getElementById('detail-grow-time');
    const mins = Math.floor(plant.growTime);
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    if (hours > 0) {
        growTimeEl.textContent = `${hours}小时${remainingMins}分钟`;
    } else {
        growTimeEl.textContent = `${mins}分钟`;
    }

    // 更新变体收集进度
    const variantTypes = [VARIANT_TYPES.NORMAL, VARIANT_TYPES.ALT_COLOR, VARIANT_TYPES.SHINY, VARIANT_TYPES.ALT_SHINY];
    const variantsGrid = document.querySelector('#plant-detail-modal .variants-grid');
    if (variantsGrid) {
        variantsGrid.innerHTML = variantTypes.map(vType => {
            const obtained = hasVariant(ownedEntry, vType);
            const count = getVariantCount(ownedEntry, vType);
            const statusText = obtained ? `✓ ${count}次` : '未获取';
            const statusClass = obtained ? 'variant-status obtained' : 'variant-status';
            const itemClasses = [
                'variant-item',
                getVariantClass(vType),
                obtained ? 'obtained' : ''
            ].filter(Boolean).join(' ');

            return `
                <div class="${itemClasses}" id="variant-${escapeAttr(vType)}" style="${getVariantCssVars(plant, vType)}">
                    ${renderVariantArt(plant, vType, { compact: true, locked: !obtained })}
                    <span class="variant-label">${escapeHtml(getVariantLabel(vType))}</span>
                    <span class="${statusClass}" id="variant-${escapeAttr(vType)}-status">${statusText}</span>
                </div>
            `;
        }).join('');
    }

    // 显示弹窗
    document.getElementById('plant-detail-modal').classList.add('active');
}

// 关闭植物详情弹窗
function closePlantDetail() {
    document.getElementById('plant-detail-modal').classList.remove('active');
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
    // 同步到服务端数据库
    if (window.StarData) StarData.setPlants(plantState, plantState.seeds);
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
    const waterBtn = document.getElementById('water-btn');
    const nutrientBtn = document.getElementById('nutrient-btn');

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
    // 各阶段显示不同的神秘 emoji，成熟后显示真实植物
    const displayEmoji = isMature ? (slot.plantEmoji || '🌟') : MYSTERY_STAGES[slot.stage];
    const displayName = isMature ? (slot.plantName || '神秘植物') : MYSTERY_STAGES[slot.stage] + ' 神秘植物';

    if (display) {
        display.textContent = displayEmoji;
        display.className = `plant-main-emoji stage-${slot.stage}${isMature ? ' mature' : ''}`;
        display.style.filter = isMature ? 'none' : 'none';
    }
    if (nameEl) nameEl.textContent = displayName;
    if (stageEl) {
        if (isMature) {
            const rColor = RARITY_COLORS[slot.plantRarity] || '#9CA3AF';
            stageEl.innerHTML = `<span style="color:${rColor};font-weight:800">🌟 ${RARITY_NAMES[slot.plantRarity]} - 已成熟！</span>`;
        } else {
            stageEl.innerHTML = `<span>${STAGE_DESCS[slot.stage] || '🌱 神秘植物成长中...'}</span>`;
        }
    }
    if (waterEl) waterEl.textContent = Math.round(slot.water) + '%';
    if (nutrientEl) nutrientEl.textContent = Math.round(slot.nutrient) + '%';
    if (waterBar) waterBar.style.width = Math.round(slot.water) + '%';
    if (nutrientBar) nutrientBar.style.width = Math.round(slot.nutrient) + '%';

    // 更新浇水/施肥按钮状态
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

    // 雪天显示保温罩按钮
    const insulationBtn = document.getElementById('insulation-btn');
    if (insulationBtn) {
        if (weatherState.currentWeather === WEATHER_TYPES.SNOW && !isMature) {
            insulationBtn.style.display = 'flex';
            update保温罩Display();
        } else {
            insulationBtn.style.display = 'none';
        }
    }

    // 更新天气提示
    updateWeatherGrowthTip();

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

        // 获取天气加成
        const growthMult = getWeatherGrowthMultiplier();
        const waterDecayMult = getWeatherWaterDecayMultiplier();
        const nutrientDecayMult = getWeatherNutrientDecayMultiplier();

        plantState.slots.forEach((slot, idx) => {
            if (!slot || !slot.plantId || slot.stage >= 3) return;

            // 应用天气加成的生长时间流逝
            let adjustedTimeDecay = growthMult;

            // 雨天额外加速：每秒额外减少 0.5 秒
            if (weatherState.currentWeather === WEATHER_TYPES.RAIN) {
                adjustedTimeDecay += 0.5;
            }

            slot.remainingTime = Math.max(0, slot.remainingTime - adjustedTimeDecay);

            // 应用天气加成的水分/营养消耗
            slot.water = Math.max(0, slot.water - (WATER_DECAY_RATE / 3600) * waterDecayMult);
            slot.nutrient = Math.max(0, slot.nutrient - (NUTRIENT_DECAY_RATE / 3600) * nutrientDecayMult);

            // 沙尘暴极低概率造成额外消耗
            if (weatherState.currentWeather === WEATHER_TYPES.SANDSTORM && Math.random() < 0.01) {
                slot.water = Math.max(0, slot.water - 2);
                slot.nutrient = Math.max(0, slot.nutrient - 1);
            }

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
            updateWeatherGrowthTip();
        }
    }, 1000);
}

// 更新天气提示
function updateWeatherGrowthTip() {
    const config = WEATHER_CONFIG[weatherState.currentWeather];
    const tipEl = document.getElementById('weather-tip');
    if (!tipEl) return;

    let tipText = '';
    const temp = weatherState.temperature;

    // 温度提示
    let tempTip = '';
    if (temp > 35) tempTip = '🌡️ 酷热！生长严重受阻';
    else if (temp >= 25 && temp <= 35) tempTip = '🌡️ 温度偏高，略有影响';
    else if (temp >= 15 && temp < 25) tempTip = '🌡️ 温度适宜，生长加速';
    else if (temp >= 5 && temp < 15) tempTip = '🌡️ 温度偏低，生长减缓';
    else if (temp < 5 && temp > 0) tempTip = '🌡️ 严寒！生长极度缓慢';
    else if (temp <= 0) tempTip = '🌡️ 冰点！注意防冻';

    // 天气提示
    let weatherTip = '';
    if (weatherState.currentWeather === WEATHER_TYPES.CLEAR) {
        weatherTip = '☀️ 晴天，水分消耗快';
    } else if (weatherState.currentWeather === WEATHER_TYPES.RAIN) {
        weatherTip = '🌧️ 雨天生长加速，自动补水';
    } else if (weatherState.currentWeather === WEATHER_TYPES.SNOW) {
        if (weatherState.保温罩) {
            weatherTip = '❄️ 保温罩已开启';
        } else {
            weatherTip = '❄️ 点击保温罩保护植物！';
        }
    } else if (weatherState.currentWeather === WEATHER_TYPES.SANDSTORM) {
        weatherTip = '🌪️ 沙尘暴！有害作物';
    } else {
        weatherTip = '⛅ 多云天气，生长平稳';
    }

    tipText = weatherTip + (tempTip ? ' · ' + tempTip : '');

    if (tipText) {
        tipEl.textContent = tipText;
        tipEl.style.display = 'block';
    }
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
        const oldWater = slot.water;
        slot.water = Math.min(100, slot.water + WATER_PER_ACTION);
        slot.remainingTime = Math.max(0, slot.remainingTime - WATER_TIME_REDUCTION);

        // 柔和的生长脉冲动画
        if (displayEl) {
            displayEl.classList.remove('plant-grow-anim');
            void displayEl.offsetWidth;
            displayEl.classList.add('plant-grow-anim');
        }
        // 水滴效果
        if (potWrapper) {
            potWrapper.classList.remove('water-drop-anim');
            void potWrapper.offsetWidth;
            potWrapper.classList.add('water-drop-anim');
            setTimeout(() => potWrapper.classList.remove('water-drop-anim'), 1000);
        }
        showTip('💧 浇水成功！水分+' + WATER_PER_ACTION + '%，生长时间缩短5分钟~');

        // 数值跳动动画
        triggerValueBump('water-value');
    } else if (action === 'nutrient') {
        if (slot.nutrient >= 100) {
            showTip('🧪 营养已达上限，无需再施肥！');
            return;
        }
        slot.nutrient = Math.min(100, slot.nutrient + NUTRIENT_PER_ACTION);
        slot.remainingTime = Math.max(0, slot.remainingTime - NUTRIENT_TIME_REDUCTION);

        // 柔和的生长脉冲动画
        if (displayEl) {
            displayEl.classList.remove('plant-grow-anim');
            void displayEl.offsetWidth;
            displayEl.classList.add('plant-grow-anim');
        }
        // 营养闪光效果
        if (potWrapper) {
            potWrapper.classList.remove('nutrient-pop-anim');
            void potWrapper.offsetWidth;
            potWrapper.classList.add('nutrient-pop-anim');
            setTimeout(() => potWrapper.classList.remove('nutrient-pop-anim'), 900);
        }
        showTip('🧪 施肥成功！营养+' + NUTRIENT_PER_ACTION + '%，生长时间缩短15分钟~');

        // 数值跳动动画
        triggerValueBump('nutrient-value');
    } else if (action === 'harvest') {
        if (slot.stage < 3) return;

        const rarityName = RARITY_NAMES[slot.plantRarity] || '普通';
        const rarityColor = RARITY_COLORS[slot.plantRarity] || '#9CA3AF';
        const harvestedPlant = PLANT_DATA.find(p => p.id === slot.plantId) || {
            id: slot.plantId,
            name: slot.plantName,
            emoji: slot.plantEmoji,
            rarity: slot.plantRarity,
            desc: ''
        };

        // 收获动画 - 先播放粒子
        try { triggerHarvestEffect(false); } catch(e) { console.warn('Harvest effect error:', e); }

        // Roll 变体类型
        const variantType = rollVariantType();
        const variantConfig = VARIANT_CONFIG[variantType] || VARIANT_CONFIG[VARIANT_TYPES.NORMAL];
        const variantLabel = variantConfig.label;
        const variantSuffix = variantConfig.suffix;

        // 变体收获时的特殊提示
        let variantTip = '';
        if (variantType !== VARIANT_TYPES.NORMAL) {
            variantTip = ` ✨ 稀有变体【${variantLabel}】！`;
            try { triggerHarvestEffect(true); } catch(e) { /* ignore */ }
        }

        const vEmoji = getVariantEmoji(slot.plantEmoji, variantType);
        showTip(`🌾 收获成功！稀有度：${rarityName}${variantTip}「${slot.plantName}」已被收录到图鉴！`);

        // 右上角推送通知，揭晓真实植物和稀有度
        const notifTitle = variantType !== VARIANT_TYPES.NORMAL
            ? `🌾 ${vEmoji} ${slot.plantName} [${variantLabel}]`
            : `🌾 ${slot.plantEmoji} ${slot.plantName}`;
        const notifContent = variantType !== VARIANT_TYPES.NORMAL
            ? `稀有度：${rarityName} ✨ 变体：${variantLabel}！`
            : `稀有度：${rarityName} ✨ 恭喜发现隐藏的植物！`;
        if (window.starlearnNotifications && typeof window.starlearnNotifications.showNotification === 'function') {
            window.starlearnNotifications.showNotification({
                title: notifTitle,
                content: notifContent,
                type: 'achievement'
            });
        }

        // 记录到已拥有（去重），携带变体信息
        const existingIdx = plantState.ownedPlants.findIndex(o => o.id === slot.plantId);
        if (existingIdx >= 0) {
            // 已拥有：更新信息，增加收获次数
            plantState.ownedPlants[existingIdx].harvestCount = (plantState.ownedPlants[existingIdx].harvestCount || 1) + 1;
            // 记录变体
            if (!plantState.ownedPlants[existingIdx].variants) {
                plantState.ownedPlants[existingIdx].variants = {};
            }
            const vKey = variantType;
            if (!plantState.ownedPlants[existingIdx].variants[vKey]) {
                plantState.ownedPlants[existingIdx].variants[vKey] = { count: 1, firstObtained: Date.now() };
            } else {
                plantState.ownedPlants[existingIdx].variants[vKey].count += 1;
            }
        } else {
            // 新获取
            plantState.ownedPlants.push({
                id: slot.plantId,
                name: slot.plantName,
                emoji: slot.plantEmoji,
                rarity: slot.plantRarity,
                obtainedAt: Date.now(),
                harvestCount: 1,
                variants: {
                    [variantType]: { count: 1, firstObtained: Date.now() }
                }
            });
        }

        // 清空槽位（带延迟动画效果）
        setTimeout(() => {
            plantState.slots[selectedSlotIndex] = { plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() };
            savePlantState();
            renderPlantPots();
            renderCurrentPlant();
            renderPlantCollection();
            showHarvestReveal(harvestedPlant, variantType, rarityName);
        }, 300);

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

function showTip(message) {
    const tipEl = document.getElementById('plant-tip');
    if (tipEl) {
        tipEl.textContent = '💡 ' + message;
    }
}

// 触发数值跳动动画
function triggerValueBump(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.classList.remove('bump');
    void el.offsetWidth; // force reflow
    el.classList.add('bump');
    setTimeout(() => el.classList.remove('bump'), 400);
}

function selectSlot(idx) {
    // 槽位切换时添加淡入淡出效果
    const display = document.getElementById('plant-emoji-display');
    const infoPanel = document.querySelector('.plant-info-left');

    if (display) {
        display.classList.add('fade-out');
    }
    if (infoPanel) {
        infoPanel.style.opacity = '0';
        infoPanel.style.transform = 'translateX(10px)';
    }

    setTimeout(() => {
        selectedSlotIndex = idx;
        renderPlantPots();
        renderCurrentPlant();

        if (display) {
            display.classList.remove('fade-out');
            display.classList.add('fade-in');
            setTimeout(() => display.classList.remove('fade-in'), 400);
        }
        if (infoPanel) {
            infoPanel.style.opacity = '1';
            infoPanel.style.transform = 'translateX(0)';
            infoPanel.style.transition = 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        }

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
    }, 150);
}

function generateParticles() {
    // 已废弃，背景改为 CSS 实现
}

document.addEventListener('DOMContentLoaded', init);

// ESC 键关闭详情弹窗
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeHarvestReveal();
        closePlantDetail();
    }
});
