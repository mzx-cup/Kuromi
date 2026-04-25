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

// ============================================================
// 天气系统
// ============================================================
async function initWeather() {
    console.log('Initializing weather...');

    // 强制清除旧缓存，重新获取
    localStorage.removeItem('starlearn_weather');

    await fetchWeather();

    // 确保 UI 更新
    console.log('Final weather state:', weatherState);
    updateWeatherDisplay();
}

async function fetchWeather() {
    const city = localStorage.getItem('starlearn_weather_city');
    if (!city) {
        // 默认使用 IP 定位
        await fetchWeatherByIP();
        return;
    }
    await fetchWeatherByCity(city);
}

async function fetchWeatherByIP() {
    // 首先检查浏览器是否支持 Geolocation API
    if (!navigator.geolocation) {
        console.warn('Geolocation not supported, using default');
        setDefaultWeatherWithCity('定位不支持');
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
                        const cityName = bdcData.city || bdcData.locality || bdcData.principalSubdivision;
                        if (cityName) {
                            console.log('BigDataCloud reverse geocoded city:', cityName);
                            weatherState.city = cityName;
                            localStorage.setItem('starlearn_weather_city', cityName);
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
                                localStorage.setItem('starlearn_weather_city', cityName);
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
                                const city = nominatimData.address.city ||
                                           nominatimData.address.town ||
                                           nominatimData.address.village ||
                                           nominatimData.address.county ||
                                           nominatimData.address.state;
                                if (city) {
                                    console.log('Nominatim reverse geocoded city:', city);
                                    weatherState.city = city;
                                    localStorage.setItem('starlearn_weather_city', city);
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
                    weatherState.city = '定位中';
                    localStorage.setItem('starlearn_weather_city', '定位中');
                    await fetchWeatherByCoordinates(lat, lon);
                    resolve();
                } catch (e) {
                    console.error('All reverse geocoding failed:', e);
                    weatherState.city = '定位中';
                    localStorage.setItem('starlearn_weather_city', '定位中');
                    await fetchWeatherByCoordinates(lat, lon);
                    resolve();
                }
            },
            async (error) => {
                console.warn('Geolocation error:', error.message);
                // 定位被拒绝或失败时，使用默认城市让用户手动设置
                setDefaultWeatherWithCity('请点击设置城市');
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
async function fetchWeatherByCity(cityName) {
    // 过滤无效或占位的城市名称
    if (!cityName || cityName === '定位中' || cityName === '请点击设置城市' || cityName === '未知') {
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
        localStorage.removeItem('starlearn_weather_city');
        showTip('🌍 城市未找到，已切换为自动定位');
        setDefaultWeatherWithCity('请点击设置城市');
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
        triggerHarvestEffect(true);
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

    return rate;
}

function getWeatherWaterDecayMultiplier() {
    const config = WEATHER_CONFIG[weatherState.currentWeather];
    return config ? config.waterDecayRate : 1;
}

function getWeatherNutrientDecayMultiplier() {
    const config = WEATHER_CONFIG[weatherState.currentWeather];
    return config ? config.nutrientDecayRate : 1;
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
    const currentCity = localStorage.getItem('starlearn_weather_city') || '';
    const input = prompt('请输入城市名称（如：北京、上海）:\n留空则使用自动定位', currentCity);
    if (input === null) return; // 用户取消

    const city = input.trim();
    if (city) {
        localStorage.setItem('starlearn_weather_city', city);
        showTip(`🌍 已设置城市为：${city}，正在获取天气...`);
        fetchWeatherByCity(city);
    } else {
        localStorage.removeItem('starlearn_weather_city');
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
    triggerHarvestEffect(true);
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
            const adjustedTimeDecay = growthMult;
            slot.remainingTime = Math.max(0, slot.remainingTime - adjustedTimeDecay);

            // 应用天气加成的水分/营养消耗
            slot.water = Math.max(0, slot.water - (WATER_DECAY_RATE / 3600) * waterDecayMult);
            slot.nutrient = Math.max(0, slot.nutrient - (NUTRIENT_DECAY_RATE / 3600) * nutrientDecayMult);

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
    if (!config || config.growthRate === 1) return;

    const tipEl = document.getElementById('weather-tip');
    if (!tipEl) return;

    let tipText = '';
    if (weatherState.currentWeather === WEATHER_TYPES.CLEAR) {
        tipText = '☀️ 晴天生长加速，但水分消耗加剧！';
    } else if (weatherState.currentWeather === WEATHER_TYPES.RAIN) {
        tipText = '🌧️ 雨天自动浇水，水分充足！';
    } else if (weatherState.currentWeather === WEATHER_TYPES.SNOW) {
        if (weatherState.保温罩) {
            tipText = '❄️ 雪天！保温罩已开启，生长恢复80%';
        } else {
            tipText = '❄️ 雪天生长极缓，点击"保温罩"保护植物！';
        }
    } else if (weatherState.currentWeather === WEATHER_TYPES.SANDSTORM) {
        tipText = '🌪️ 沙尘暴！生长减缓40%...';
    }

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

        // 收获动画 - 先播放粒子
        triggerHarvestEffect(false);

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

        // 清空槽位（带延迟动画效果）
        setTimeout(() => {
            plantState.slots[selectedSlotIndex] = { plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() };
            savePlantState();
            renderPlantPots();
            renderCurrentPlant();
            renderPlantCollection();
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
