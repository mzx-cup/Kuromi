// 成就勋章数据 - 覆盖项目所有事件
const ACHIEVEMENTS = [
    // ========== 学习基础类 (10个) ==========
    {
        id: 'first_study',
        name: '初次启航',
        desc: '完成第一次学习',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'compass',
        condition: { type: 'study_count', value: 1 }
    },
    {
        id: 'study_10',
        name: '学习新手',
        desc: '累计学习10次',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'book',
        condition: { type: 'study_count', value: 10 }
    },
    {
        id: 'study_50',
        name: '学习达人',
        desc: '累计学习50次',
        category: 'skill',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'book-open',
        condition: { type: 'study_count', value: 50 }
    },
    {
        id: 'study_100',
        name: '学习大师',
        desc: '累计学习100次',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'graduation',
        condition: { type: 'study_count', value: 100 }
    },
    {
        id: 'study_500',
        name: '知识海洋',
        desc: '累计学习500次',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'ocean',
        condition: { type: 'study_count', value: 500 }
    },
    {
        id: 'time_1h',
        name: '初识门径',
        desc: '累计学习1小时',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'clock',
        condition: { type: 'study_minutes', value: 60 }
    },
    {
        id: 'time_10h',
        name: '渐入佳境',
        desc: '累计学习10小时',
        category: 'skill',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'hourglass',
        condition: { type: 'study_minutes', value: 600 }
    },
    {
        id: 'time_100h',
        name: '时间领主',
        desc: '累计学习100小时',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'time-master',
        condition: { type: 'study_minutes', value: 6000 }
    },
    {
        id: 'time_1000h',
        name: '时光守护者',
        desc: '累计学习1000小时',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'eternity',
        condition: { type: 'study_minutes', value: 60000 }
    },
    {
        id: 'daily_goal',
        name: '目标达成',
        desc: '首次完成每日学习目标',
        category: 'skill',
        tier: 'rare',
        color: '16, 185, 129',
        icon: 'target',
        condition: { type: 'daily_goal_complete', value: 1 }
    },

    // ========== 连续学习类 (8个) ==========
    {
        id: 'streak_3',
        name: '三连击',
        desc: '连续学习3天',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'fire-small',
        condition: { type: 'streak_days', value: 3 }
    },
    {
        id: 'streak_7',
        name: '周常达人',
        desc: '连续学习7天',
        category: 'skill',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'fire',
        condition: { type: 'streak_days', value: 7 }
    },
    {
        id: 'streak_14',
        name: '双周坚持',
        desc: '连续学习14天',
        category: 'skill',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'fire-medium',
        condition: { type: 'streak_days', value: 14 }
    },
    {
        id: 'streak_30',
        name: '月度之星',
        desc: '连续学习30天',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'fire-large',
        condition: { type: 'streak_days', value: 30 }
    },
    {
        id: 'streak_60',
        name: '双月传奇',
        desc: '连续学习60天',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'fire-epic',
        condition: { type: 'streak_days', value: 60 }
    },
    {
        id: 'streak_100',
        name: '百日筑基',
        desc: '连续学习100天',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'fire-legendary',
        condition: { type: 'streak_days', value: 100 }
    },
    {
        id: 'streak_365',
        name: '年度霸主',
        desc: '连续学习365天',
        category: 'master',
        tier: 'legendary',
        color: '236, 72, 153',
        icon: 'crown',
        condition: { type: 'streak_days', value: 365 }
    },
    {
        id: 'early_bird',
        name: '早起鸟儿',
        desc: '连续7天早起学习(6点前)',
        category: 'skill',
        tier: 'epic',
        color: '245, 158, 11',
        icon: 'sunrise',
        condition: { type: 'early_study_streak', value: 7 }
    },

    // ========== 算法挑战类 (8个) ==========
    {
        id: 'algo_first',
        name: '算法入门',
        desc: '完成第一道算法题',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'code',
        condition: { type: 'algo_count', value: 1 }
    },
    {
        id: 'algo_10',
        name: '算法学徒',
        desc: '完成10道算法题',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'code-block',
        condition: { type: 'algo_count', value: 10 }
    },
    {
        id: 'algo_50',
        name: '算法高手',
        desc: '完成50道算法题',
        category: 'skill',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'terminal',
        condition: { type: 'algo_count', value: 50 }
    },
    {
        id: 'algo_100',
        name: '算法大师',
        desc: '完成100道算法题',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'star-code',
        condition: { type: 'algo_count', value: 100 }
    },
    {
        id: 'algo_500',
        name: '算法宗师',
        desc: '完成500道算法题',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'diamond-code',
        condition: { type: 'algo_count', value: 500 }
    },
    {
        id: 'algo_streak_10',
        name: '连胜达人',
        desc: '连续答对10道算法题',
        category: 'skill',
        tier: 'rare',
        color: '16, 185, 129',
        icon: 'zap',
        condition: { type: 'algo_streak', value: 10 }
    },
    {
        id: 'algo_perfect',
        name: '完美答卷',
        desc: '一次通过困难难度算法题',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'check-circle',
        condition: { type: 'algo_perfect_hard', value: 1 }
    },
    {
        id: 'algo_all_medium',
        name: '中等征服者',
        desc: '完成所有中等难度题目',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'shield',
        condition: { type: 'algo_all_medium', value: 1 }
    },

    // ========== 课程证书类 (10个) ==========
    {
        id: 'course_python',
        name: 'Python入门',
        desc: '完成Python基础课程',
        category: 'course',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'python',
        condition: { type: 'course_complete', course: 'python' }
    },
    {
        id: 'course_python_adv',
        name: 'Python进阶',
        desc: '完成Python高级课程',
        category: 'course',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'python-adv',
        condition: { type: 'course_complete', course: 'python_adv' }
    },
    {
        id: 'course_c',
        name: 'C语言基础',
        desc: '完成C语言入门课程',
        category: 'course',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'c-lang',
        condition: { type: 'course_complete', course: 'c' }
    },
    {
        id: 'course_cpp',
        name: 'C++开发者',
        desc: '完成C++核心课程',
        category: 'course',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'cpp',
        condition: { type: 'course_complete', course: 'cpp' }
    },
    {
        id: 'course_bigdata',
        name: '大数据入门',
        desc: '完成大数据导论课程',
        category: 'course',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'database',
        condition: { type: 'course_complete', course: 'bigdata' }
    },
    {
        id: 'course_hadoop',
        name: 'Hadoop专家',
        desc: '完成Hadoop全部课程',
        category: 'course',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'elephant',
        condition: { type: 'course_complete', course: 'hadoop' }
    },
    {
        id: 'course_spark',
        name: 'Spark大师',
        desc: '完成Spark核心课程',
        category: 'course',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'lightning',
        condition: { type: 'course_complete', course: 'spark' }
    },
    {
        id: 'course_algorithm',
        name: '算法通关',
        desc: '完成算法与数据结构课程',
        category: 'course',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'tree',
        condition: { type: 'course_complete', course: 'algorithm' }
    },
    {
        id: 'course_os',
        name: '操作系统精通',
        desc: '完成操作系统课程',
        category: 'course',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'cpu',
        condition: { type: 'course_complete', course: 'os' }
    },
    {
        id: 'course_all',
        name: '全科通才',
        desc: '完成所有课程学习',
        category: 'course',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'encyclopedia',
        condition: { type: 'course_all', value: 1 }
    },

    // ========== 星友互动类 (8个) ==========
    {
        id: 'pet_adopt',
        name: '星友初遇',
        desc: '领养第一只星友',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'heart',
        condition: { type: 'pet_adopt', value: 1 }
    },
    {
        id: 'pet_feed_10',
        name: '爱心喂养',
        desc: '喂食星友10次',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'food',
        condition: { type: 'pet_feed', value: 10 }
    },
    {
        id: 'pet_feed_100',
        name: '贴心主人',
        desc: '喂食星友100次',
        category: 'skill',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'food-bowl',
        condition: { type: 'pet_feed', value: 100 }
    },
    {
        id: 'pet_play_50',
        name: '快乐伙伴',
        desc: '与星友玩耍50次',
        category: 'skill',
        tier: 'rare',
        color: '16, 185, 129',
        icon: 'ball',
        condition: { type: 'pet_play', value: 50 }
    },
    {
        id: 'pet_intimacy_80',
        name: '亲密无间',
        desc: '星友亲密度达到80%',
        category: 'skill',
        tier: 'epic',
        color: '236, 72, 153',
        icon: 'hearts',
        condition: { type: 'pet_intimacy', value: 80 }
    },
    {
        id: 'pet_intimacy_100',
        name: '灵魂伴侣',
        desc: '星友亲密度达到100%',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'heart-glow',
        condition: { type: 'pet_intimacy', value: 100 }
    },
    {
        id: 'pet_unlock_5',
        name: '星友收藏家',
        desc: '解锁5种星友',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'paw',
        condition: { type: 'pet_unlock', value: 5 }
    },
    {
        id: 'pet_unlock_all',
        name: '星友大师',
        desc: '解锁全部10种星友',
        category: 'master',
        tier: 'legendary',
        color: '236, 72, 153',
        icon: 'star-pet',
        condition: { type: 'pet_unlock', value: 10 }
    },

    // ========== 植物林场类 (6个) ==========
    {
        id: 'plant_first',
        name: '播种希望',
        desc: '种植第一株植物',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'seed',
        condition: { type: 'plant_count', value: 1 }
    },
    {
        id: 'plant_10',
        name: '绿手指',
        desc: '种植10株植物',
        category: 'skill',
        tier: 'rare',
        color: '16, 185, 129',
        icon: 'plant',
        condition: { type: 'plant_count', value: 10 }
    },
    {
        id: 'harvest_5',
        name: '初获丰收',
        desc: '收获5株植物',
        category: 'skill',
        tier: 'rare',
        color: '16, 185, 129',
        icon: 'basket',
        condition: { type: 'harvest_count', value: 5 }
    },
    {
        id: 'harvest_20',
        name: '丰收达人',
        desc: '收获20株植物',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'wheat',
        condition: { type: 'harvest_count', value: 20 }
    },
    {
        id: 'harvest_100',
        name: '农场主',
        desc: '收获100株植物',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'farm',
        condition: { type: 'harvest_count', value: 100 }
    },
    {
        id: 'plant_all_types',
        name: '植物图鉴',
        desc: '种植过所有类型植物',
        category: 'master',
        tier: 'legendary',
        color: '236, 72, 153',
        icon: 'flower-crown',
        condition: { type: 'plant_all_types', value: 1 }
    },

    // ========== 小游戏类 (5个) ==========
    {
        id: 'game_first',
        name: '游戏新手',
        desc: '完成第一次小游戏',
        category: 'skill',
        tier: 'common',
        color: '148, 163, 184',
        icon: 'gamepad',
        condition: { type: 'game_play', value: 1 }
    },
    {
        id: 'game_50',
        name: '游戏达人',
        desc: '完成50次小游戏',
        category: 'skill',
        tier: 'rare',
        color: '59, 130, 246',
        icon: 'trophy',
        condition: { type: 'game_play', value: 50 }
    },
    {
        id: 'game_score_500',
        name: '高分选手',
        desc: '单局游戏得分超过500',
        category: 'skill',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'medal',
        condition: { type: 'game_high_score', value: 500 }
    },
    {
        id: 'game_score_1000',
        name: '游戏王者',
        desc: '单局游戏得分超过1000',
        category: 'skill',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'crown-game',
        condition: { type: 'game_high_score', value: 1000 }
    },
    {
        id: 'game_combo_20',
        name: '连击大师',
        desc: '单局达成20连击',
        category: 'skill',
        tier: 'epic',
        color: '245, 158, 11',
        icon: 'flame',
        condition: { type: 'game_max_combo', value: 20 }
    },

    // ========== 大师成就类 (5个) ==========
    {
        id: 'explore_all',
        name: '星际探索者',
        desc: '探索全部学习模块',
        category: 'master',
        tier: 'legendary',
        color: '236, 72, 153',
        icon: 'rocket',
        condition: { type: 'explore_all', value: 1 }
    },
    {
        id: 'knowledge_master',
        name: '知识大师',
        desc: '掌握5大学科知识',
        category: 'master',
        tier: 'epic',
        color: '168, 85, 247',
        icon: 'brain',
        condition: { type: 'knowledge_mastery', value: 5 }
    },
    {
        id: 'code_poet',
        name: '代码诗人',
        desc: '编写优雅代码1000行',
        category: 'master',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'feather',
        condition: { type: 'code_lines', value: 1000 }
    },
    {
        id: 'star_child',
        name: '星辰之子',
        desc: '收集全部传奇徽章',
        category: 'master',
        tier: 'legendary',
        color: '79, 70, 229',
        icon: 'star-child',
        condition: { type: 'legendary_badges', value: 15 }
    },
    {
        id: 'ultimate',
        name: '终极荣耀',
        desc: '解锁所有成就徽章',
        category: 'master',
        tier: 'legendary',
        color: '251, 191, 36',
        icon: 'infinity',
        condition: { type: 'all_badges', value: 1 }
    }
];

// 成就图标SVG模板
const ACHIEVEMENT_ICONS = {
    'compass': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="2" fill="rgba(148,163,184,0.1)"/><path d="M32 16L36 32L32 48L28 32Z" fill="currentColor"/><circle cx="32" cy="32" r="4" fill="currentColor"/>',
    'book': '<rect x="14" y="10" width="36" height="44" rx="4" stroke="currentColor" stroke-width="2" fill="rgba(148,163,184,0.1)"/><path d="M32 10V54" stroke="currentColor" stroke-width="2"/>',
    'book-open': '<path d="M8 12H28L32 16L36 12H56V48H36L32 44L28 48H8V12Z" stroke="currentColor" stroke-width="2" fill="rgba(59,130,246,0.1)"/>',
    'graduation': '<path d="M32 8L8 20L32 32L56 20L32 8Z" fill="currentColor"/><path d="M20 28V40L32 48L44 40V28" stroke="currentColor" stroke-width="2" fill="none"/>',
    'ocean': '<path d="M8 32Q16 20 24 32T40 32T56 32" stroke="currentColor" stroke-width="3" fill="none"/><path d="M8 40Q16 28 24 40T40 40T56 40" stroke="currentColor" stroke-width="3" fill="none"/><path d="M8 48Q16 36 24 48T40 48T56 48" stroke="currentColor" stroke-width="3" fill="none"/>',
    'clock': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="2" fill="rgba(148,163,184,0.1)"/><path d="M32 16V32L42 42" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    'hourglass': '<path d="M16 8H48V16L32 32L48 48V56H16V48L32 32L16 16V8Z" stroke="currentColor" stroke-width="2" fill="rgba(59,130,246,0.1)"/>',
    'time-master': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="3" fill="rgba(168,85,247,0.1)"/><circle cx="32" cy="32" r="16" stroke="currentColor" stroke-width="2" fill="none"/><circle cx="32" cy="32" r="8" fill="currentColor"/>',
    'eternity': '<path d="M16 32C16 24 24 16 32 16C40 16 48 24 48 32C48 40 40 48 32 48C24 48 16 40 16 32" stroke="currentColor" stroke-width="3" fill="none"/><path d="M24 32C24 28 28 24 32 24C36 24 40 28 40 32C40 36 36 40 32 40C28 40 24 36 24 32" stroke="currentColor" stroke-width="2" fill="none"/>',
    'target': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="2" fill="none"/><circle cx="32" cy="32" r="16" stroke="currentColor" stroke-width="2" fill="none"/><circle cx="32" cy="32" r="8" stroke="currentColor" stroke-width="2" fill="none"/><circle cx="32" cy="32" r="3" fill="currentColor"/>',
    'fire-small': '<path d="M32 12C32 12 24 24 24 36C24 44 28 48 32 48C36 48 40 44 40 36C40 24 32 12 32 12Z" fill="currentColor"/>',
    'fire': '<path d="M32 8C32 8 20 24 20 40C20 48 24 52 32 52C40 52 44 48 44 40C44 24 32 8 32 8Z" fill="currentColor"/><path d="M32 20C32 20 26 30 26 38C26 44 28 46 32 46C36 46 38 44 38 38C38 30 32 20 32 20Z" fill="rgba(255,255,255,0.3)"/>',
    'fire-medium': '<path d="M28 10C28 10 16 26 16 42C16 50 22 54 32 54C42 54 48 50 48 42C48 26 36 10 28 10Z" fill="currentColor"/>',
    'fire-large': '<path d="M32 6C32 6 14 24 14 44C14 54 20 58 32 58C44 58 50 54 50 44C50 24 32 6 32 6Z" fill="currentColor"/><path d="M32 18C32 18 22 32 22 42C22 50 26 52 32 52C38 52 42 50 42 42C42 32 32 18 32 18Z" fill="rgba(255,255,255,0.3)"/>',
    'fire-epic': '<path d="M32 4C32 4 10 22 10 44C10 56 18 60 32 60C46 60 54 56 54 44C54 22 32 4 32 4Z" fill="currentColor"/>',
    'fire-legendary': '<path d="M32 2C32 2 6 20 6 46C6 58 16 62 32 62C48 62 58 58 58 46C58 20 32 2 32 2Z" fill="currentColor"/><path d="M32 16C32 16 18 32 18 44C18 52 24 54 32 54C40 54 46 52 46 44C46 32 32 16 32 16Z" fill="rgba(255,255,255,0.4)"/>',
    'crown': '<path d="M8 48H56L52 24L40 36L32 16L24 36L12 24L8 48Z" fill="currentColor"/><rect x="8" y="48" width="48" height="8" fill="currentColor"/>',
    'sunrise': '<path d="M8 48H56" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><path d="M32 40V24" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><path d="M16 44L20 36" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M48 44L44 36" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="32" cy="20" r="8" fill="currentColor"/>',
    'code': '<path d="M20 20L8 32L20 44" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M44 20L56 32L44 44" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M36 16L28 48" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',
    'code-block': '<rect x="8" y="12" width="48" height="40" rx="4" stroke="currentColor" stroke-width="2" fill="rgba(148,163,184,0.1)"/><path d="M16 24H32M16 32H40M16 40H28" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    'terminal': '<rect x="8" y="8" width="48" height="48" rx="4" stroke="currentColor" stroke-width="2" fill="rgba(59,130,246,0.1)"/><path d="M16 24L24 32L16 40" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M28 40H48" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    'star-code': '<path d="M32 8L36 24H52L40 34L44 50L32 40L20 50L24 34L12 24H28L32 8Z" fill="currentColor"/>',
    'diamond-code': '<path d="M32 8L56 28L32 56L8 28L32 8Z" fill="currentColor"/><path d="M32 20L44 28L32 44L20 28L32 20Z" fill="rgba(255,255,255,0.3)"/>',
    'zap': '<path d="M32 4L20 32H30L24 60L44 28H34L32 4Z" fill="currentColor"/>',
    'check-circle': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="2" fill="rgba(168,85,247,0.1)"/><path d="M20 32L28 40L44 24" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
    'shield': '<path d="M32 8L8 20V36C8 48 18 54 32 56C46 54 56 48 56 36V20L32 8Z" stroke="currentColor" stroke-width="2" fill="rgba(251,191,36,0.1)"/>',
    'python': '<path d="M24 12C24 8 28 8 32 8C36 8 40 8 40 12V24H24V12Z" fill="currentColor"/><path d="M40 52C40 56 36 56 32 56C28 56 24 56 24 52V40H40V52Z" fill="currentColor"/><circle cx="30" cy="16" r="2" fill="white"/><circle cx="34" cy="48" r="2" fill="white"/>',
    'python-adv': '<path d="M20 8H44C48 8 52 12 52 16V28H28V20H44V16H20V28H12V16C12 12 16 8 20 8Z" fill="currentColor"/><path d="M44 56H20C16 56 12 52 12 48V36H36V44H20V48H44V36H52V48C52 52 48 56 44 56Z" fill="currentColor"/>',
    'c-lang': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="3" fill="rgba(59,130,246,0.1)"/><path d="M36 20C32 18 26 20 24 26C22 32 24 40 30 44C36 48 42 46 44 40" stroke="currentColor" stroke-width="3" stroke-linecap="round" fill="none"/>',
    'cpp': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="3" fill="rgba(168,85,247,0.1)"/><path d="M28 24V32H36" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M36 24V32H44" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    'database': '<ellipse cx="32" cy="16" rx="20" ry="8" stroke="currentColor" stroke-width="2" fill="rgba(59,130,246,0.1)"/><path d="M12 16V48C12 52 20 56 32 56C44 56 52 52 52 48V16" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 32C12 36 20 40 32 40C44 40 52 36 52 32" stroke="currentColor" stroke-width="2" fill="none"/>',
    'elephant': '<ellipse cx="32" cy="36" rx="20" ry="16" fill="currentColor"/><ellipse cx="32" cy="24" rx="12" ry="10" fill="currentColor"/><path d="M20 36C20 36 12 40 8 48" stroke="currentColor" stroke-width="4" stroke-linecap="round" fill="none"/>',
    'lightning': '<path d="M32 4L20 32H28L22 60L48 28H38L32 4Z" fill="currentColor"/>',
    'tree': '<path d="M32 56V40" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="M32 8L16 28L24 28L12 48H52L40 28L48 28L32 8Z" fill="currentColor"/>',
    'cpu': '<rect x="16" y="16" width="32" height="32" rx="4" stroke="currentColor" stroke-width="2" fill="rgba(168,85,247,0.1)"/><path d="M24 8V16M32 8V16M40 8V16M24 48V56M32 48V56M40 48V56M8 24H16M8 32H16M8 40H16M48 24H56M48 32H56M48 40H56" stroke="currentColor" stroke-width="2"/>',
    'encyclopedia': '<rect x="8" y="8" width="20" height="48" rx="2" fill="currentColor"/><rect x="30" y="8" width="20" height="48" rx="2" fill="currentColor"/><rect x="52" y="8" width="4" height="48" rx="1" fill="currentColor"/>',
    'heart': '<path d="M32 56C32 56 8 40 8 24C8 16 14 10 22 10C28 10 32 16 32 16C32 16 36 10 42 10C50 10 56 16 56 24C56 40 32 56 32 56Z" fill="currentColor"/>',
    'food': '<ellipse cx="32" cy="40" rx="20" ry="12" stroke="currentColor" stroke-width="2" fill="rgba(148,163,184,0.1)"/><path d="M24 28C24 20 28 16 32 16C36 16 40 20 40 28" stroke="currentColor" stroke-width="2" fill="none"/>',
    'food-bowl': '<path d="M8 32H56L52 48C52 52 44 56 32 56C20 56 12 52 12 48L8 32Z" fill="currentColor"/><ellipse cx="32" cy="28" rx="24" ry="8" stroke="currentColor" stroke-width="2" fill="none"/>',
    'ball': '<circle cx="32" cy="32" r="20" stroke="currentColor" stroke-width="2" fill="rgba(16,185,129,0.1)"/><path d="M32 12V52M12 32H52" stroke="currentColor" stroke-width="2"/>',
    'hearts': '<path d="M24 44C24 44 12 36 12 26C12 20 16 16 22 16C26 16 28 20 28 20C28 20 30 16 34 16C40 16 44 20 44 26C44 36 32 44 32 44" fill="currentColor"/><path d="M40 52C40 52 32 46 32 40C32 36 35 34 38 34C40 34 41 36 41 36C41 36 42 34 44 34C47 34 50 36 50 40C50 46 42 52 42 52" fill="currentColor"/>',
    'heart-glow': '<path d="M32 52C32 52 8 38 8 22C8 14 14 8 22 8C28 8 32 14 32 14C32 14 36 8 42 8C50 8 56 14 56 22C56 38 32 52 32 52Z" fill="currentColor"/><circle cx="32" cy="24" r="8" fill="rgba(255,255,255,0.4)"/>',
    'paw': '<ellipse cx="32" cy="40" rx="12" ry="10" fill="currentColor"/><circle cx="20" cy="28" r="6" fill="currentColor"/><circle cx="44" cy="28" r="6" fill="currentColor"/><circle cx="26" cy="20" r="5" fill="currentColor"/><circle cx="38" cy="20" r="5" fill="currentColor"/>',
    'star-pet': '<path d="M32 4L36 20H52L40 30L44 46L32 36L20 46L24 30L12 20H28L32 4Z" fill="currentColor"/><ellipse cx="32" cy="52" rx="8" ry="6" fill="currentColor"/>',
    'seed': '<path d="M32 56C32 56 20 48 20 36C20 28 24 24 32 24C40 24 44 28 44 36C44 48 32 56 32 56Z" fill="currentColor"/><path d="M32 24V12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    'plant': '<path d="M32 56V32" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><path d="M32 32C32 32 20 28 20 20C20 14 26 12 32 16C38 12 44 14 44 20C44 28 32 32 32 32Z" fill="currentColor"/>',
    'basket': '<path d="M12 36H52L48 52H16L12 36Z" fill="currentColor"/><path d="M8 36C8 32 12 28 16 28H48C52 28 56 32 56 36" stroke="currentColor" stroke-width="2" fill="none"/>',
    'wheat': '<path d="M32 56V24" stroke="currentColor" stroke-width="2"/><ellipse cx="32" cy="20" rx="6" ry="10" fill="currentColor"/><ellipse cx="26" cy="28" rx="5" ry="8" fill="currentColor"/><ellipse cx="38" cy="28" rx="5" ry="8" fill="currentColor"/>',
    'farm': '<path d="M8 56H56" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M16 56V40L24 32V56M40 56V40L48 32V56" stroke="currentColor" stroke-width="2"/><path d="M28 56V48L36 48V56" stroke="currentColor" stroke-width="2"/>',
    'flower-crown': '<circle cx="32" cy="32" r="20" stroke="currentColor" stroke-width="2" fill="none"/><circle cx="32" cy="12" r="6" fill="currentColor"/><circle cx="49" cy="22" r="6" fill="currentColor"/><circle cx="49" cy="42" r="6" fill="currentColor"/><circle cx="32" cy="52" r="6" fill="currentColor"/><circle cx="15" cy="42" r="6" fill="currentColor"/><circle cx="15" cy="22" r="6" fill="currentColor"/>',
    'gamepad': '<rect x="8" y="20" width="48" height="28" rx="8" stroke="currentColor" stroke-width="2" fill="rgba(148,163,184,0.1)"/><circle cx="20" cy="34" r="4" fill="currentColor"/><circle cx="44" cy="30" r="3" fill="currentColor"/><circle cx="44" cy="38" r="3" fill="currentColor"/>',
    'trophy': '<path d="M20 8H44V24C44 32 38 36 32 36C26 36 20 32 20 24V8Z" stroke="currentColor" stroke-width="2" fill="rgba(59,130,246,0.1)"/><path d="M12 8H20V20C16 20 12 16 12 8Z" stroke="currentColor" stroke-width="2" fill="none"/><path d="M44 8H52V20C48 20 44 16 44 8Z" stroke="currentColor" stroke-width="2" fill="none"/><path d="M24 36V44H40V36" stroke="currentColor" stroke-width="2" fill="none"/><rect x="20" y="44" width="24" height="8" fill="currentColor"/>',
    'medal': '<circle cx="32" cy="28" r="16" stroke="currentColor" stroke-width="2" fill="rgba(168,85,247,0.1)"/><path d="M32 12V4M24 8L32 12L40 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M24 44L32 36L40 44L32 56L24 44Z" fill="currentColor"/>',
    'crown-game': '<path d="M8 44H56L52 24L40 32L32 16L24 32L12 24L8 44Z" fill="currentColor"/><rect x="8" y="44" width="48" height="8" fill="currentColor"/><circle cx="32" cy="28" r="4" fill="rgba(255,255,255,0.5)"/>',
    'flame': '<path d="M32 8C32 8 18 24 18 40C18 50 24 54 32 54C40 54 46 50 46 40C46 24 32 8 32 8Z" fill="currentColor"/><path d="M32 24C32 24 26 34 26 42C26 48 28 50 32 50C36 50 38 48 38 42C38 34 32 24 32 24Z" fill="rgba(255,255,255,0.3)"/>',
    'rocket': '<path d="M32 8L40 24V48L32 56L24 48V24L32 8Z" fill="currentColor"/><path d="M24 40L16 48V40L24 36" fill="currentColor"/><path d="M40 40L48 48V40L40 36" fill="currentColor"/><circle cx="32" cy="28" r="4" fill="rgba(255,255,255,0.5)"/>',
    'brain': '<path d="M32 8C20 8 12 16 12 28C12 36 16 40 22 42C20 44 20 48 22 52C24 56 30 56 32 56C34 56 40 56 42 52C44 48 44 44 42 42C48 40 52 36 52 28C52 16 44 8 32 8Z" stroke="currentColor" stroke-width="2" fill="rgba(168,85,247,0.1)"/>',
    'feather': '<path d="M32 56V24" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M32 24C32 24 20 20 16 12C16 12 28 16 32 24Z" fill="currentColor"/><path d="M32 24C32 24 44 20 48 12C48 12 36 16 32 24Z" fill="currentColor"/><path d="M32 32C32 32 22 30 18 24" stroke="currentColor" stroke-width="1.5" fill="none"/>',
    'star-child': '<circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="2" fill="rgba(79,70,229,0.1)"/><path d="M32 12L34 24H46L36 30L40 42L32 34L24 42L28 30L18 24H30L32 12Z" fill="currentColor"/>',
    'infinity': '<path d="M32 20C32 20 24 12 16 12C8 12 4 20 4 28C4 36 8 44 16 44C24 44 32 36 32 36C32 36 40 44 48 44C56 44 60 36 60 28C60 20 56 12 48 12C40 12 32 20 32 20Z" stroke="currentColor" stroke-width="3" fill="none"/>'
};

// 导出
window.ACHIEVEMENTS = ACHIEVEMENTS;
window.ACHIEVEMENT_ICONS = ACHIEVEMENT_ICONS;
