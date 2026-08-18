-- ============================================================================
-- 星识 (Star-Learn) SQLite 数据库初始化脚本
-- 兼容 SQLite 3.x（Python 内置）
-- 注意：SQLite 默认关闭外键约束，使用前请执行 PRAGMA foreign_keys = ON;
--       本脚本由 init_mysql.sql 通过 mysql_to_sqlite 转换规则自动生成。
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. user - 用户认证
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    nickname TEXT DEFAULT '',
    avatar TEXT DEFAULT '',
    current_task TEXT DEFAULT '大数据导论',
    preferred_language TEXT DEFAULT 'python',
    theme TEXT DEFAULT 'ocean',
    last_agent_id TEXT DEFAULT '',
    last_login TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 2. learning_records - 学习记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    interaction_count INTEGER DEFAULT 0,
    code_practice_time INTEGER DEFAULT 0,
    socratic_pass_rate REAL DEFAULT 0.0,
    difficulty_level TEXT DEFAULT 'basic',
    profile_json TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_lr_user ON learning_records (user_id);

-- ----------------------------------------------------------------------------
-- 3. learning_path - 学习路径
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS learning_path (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    path_json TEXT,
    generated_at TEXT,
    reasoning TEXT,
    data_sources TEXT,
    confidence REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 4. user_profile - 用户画像
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    profile_json TEXT,
    evaluation_json TEXT,
    last_grade_record TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 5. user_evaluations - 用户评估指标历史
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    interaction_count INTEGER DEFAULT 0,
    socratic_pass_rate REAL DEFAULT 0.0,
    difficulty_level TEXT DEFAULT 'basic',
    code_practice_time INTEGER DEFAULT 0,
    focus_time_today INTEGER DEFAULT 0,
    flashcards_studied INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    eval_json TEXT,
    record_date TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_eval_user_date ON user_evaluations (user_id, record_date);

-- ----------------------------------------------------------------------------
-- 6. user_preferences - 用户偏好设置
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    preferences_json TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 7. user_garden - 花园/植物种植
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_garden (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    seeds INTEGER DEFAULT 3,
    garden_json TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 8. user_pet - 宠物状态
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_pet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    pet_json TEXT,
    pet_game_json TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 9. user_achievements - 用户成就
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    achievements_json TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 10. user_stats - 统计数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    stats_json TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 11. user_notifications - 通知
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    notifications_json TEXT,
    last_update_time INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 12. user_settings - 综合设置
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    settings_json TEXT,
    weather_city TEXT DEFAULT '',
    floating_alarm_x INTEGER,
    floating_alarm_y INTEGER,
    hub_theme TEXT DEFAULT 'light',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 13. user_coding_state - 编程练习状态
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_coding_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    coding_state_json TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 14. user_weather_cache - 天气缓存
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_weather_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    weather_json TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 15. user_focus_history - 专注历史
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_focus_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    focus_json TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 16. user_eco_data - 生态数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_eco_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    eco_data_json TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 17. user_projects - 架构项目
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    projects_json TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 18. user_calendar_events - 日历事件
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    events_json TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 19. daily_routes - 每日学习路线
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    route_date TEXT NOT NULL,
    tasks_json TEXT,
    completed_json TEXT,
    generated_at TEXT DEFAULT (datetime('now','localtime')),
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_date ON daily_routes (user_id, route_date);

-- ----------------------------------------------------------------------------
-- 20. knowledge_nodes - 知识节点（SM2间隔重复）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    parent_id TEXT,
    level TEXT DEFAULT 'leaf',
    icon TEXT DEFAULT '📚',
    subject TEXT DEFAULT '',
    is_active INTEGER DEFAULT 0,
    first_studied_at TEXT,
    last_studied_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    sm2_data_json TEXT,
    stats_json TEXT,
    position_x REAL DEFAULT 0,
    position_y REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_user_id ON knowledge_nodes (user_id);

-- ----------------------------------------------------------------------------
-- 21. review_records - 复习记录（SM2）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    review_date TEXT DEFAULT (datetime('now','localtime')),
    quality INTEGER DEFAULT 0,
    response_time REAL DEFAULT 0,
    sm2_result_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_user_node ON review_records (user_id, node_id);

-- ----------------------------------------------------------------------------
-- 22. telemetry_data - 遥测/行为数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    context_id TEXT,
    event_type TEXT NOT NULL,
    event_data TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_student ON telemetry_data (student_id);
CREATE INDEX IF NOT EXISTS idx_context ON telemetry_data (context_id);
CREATE INDEX IF NOT EXISTS idx_event ON telemetry_data (event_type);
CREATE INDEX IF NOT EXISTS idx_created ON telemetry_data (created_at);

-- ----------------------------------------------------------------------------
-- 23. study_sessions - 学习时段记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_date TEXT NOT NULL,
    duration_minutes INTEGER DEFAULT 0,
    start_time TEXT,
    end_time TEXT,
    subject TEXT DEFAULT '',
    node_id TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_user_date ON study_sessions (user_id, session_date);

-- ----------------------------------------------------------------------------
-- 24. learning_goals - 学习目标
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS learning_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    goal_type TEXT NOT NULL,
    title TEXT DEFAULT '',
    target_value INTEGER DEFAULT 0,
    current_value INTEGER DEFAULT 0,
    unit TEXT DEFAULT 'minutes',
    start_date TEXT,
    end_date TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ----------------------------------------------------------------------------
-- 25. weekly_summary - 周学习总结
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weekly_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start_date TEXT NOT NULL,
    daily_minutes TEXT,
    hourly_distribution TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_week ON weekly_summary (user_id, week_start_date);

-- ----------------------------------------------------------------------------
-- 26. classroom_records - 课堂记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS classroom_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL DEFAULT '',
    ppt_pages INTEGER DEFAULT 0,
    full_data TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_user_id ON classroom_records (user_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON classroom_records (created_at);

-- ----------------------------------------------------------------------------
-- 27. course_generation_status - 课程生成状态跟踪
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS course_generation_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL UNIQUE,
    total_outlines INTEGER DEFAULT 0,
    generated_count INTEGER DEFAULT 0,
    pending_slides_v2 TEXT,
    pending_quiz_data TEXT,
    pending_exercise_data TEXT,
    is_complete INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_course_id ON course_generation_status (course_id);

-- ----------------------------------------------------------------------------
-- 28. user_flashcard_progress - 用户胶囊卡片进度
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_flashcard_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_hash TEXT NOT NULL,
    course_id TEXT DEFAULT 'bigdata',
    chapter_name TEXT DEFAULT '',
    front_text TEXT NOT NULL,
    back_text TEXT NOT NULL,
    hint_text TEXT DEFAULT '',
    is_mastered INTEGER DEFAULT 0,
    is_favorite INTEGER DEFAULT 0,
    difficulty TEXT DEFAULT 'medium',
    user_note TEXT DEFAULT '',
    review_count INTEGER DEFAULT 0,
    first_seen_at TEXT,
    last_reviewed_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_card ON user_flashcard_progress (user_id, card_hash);

-- ----------------------------------------------------------------------------
-- 29. user_flashcard_sessions - 用户胶囊学习会话
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_flashcard_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_date TEXT NOT NULL,
    course_id TEXT DEFAULT 'bigdata',
    chapter_name TEXT DEFAULT '',
    cards_total INTEGER DEFAULT 0,
    cards_answered INTEGER DEFAULT 0,
    cards_mastered INTEGER DEFAULT 0,
    cards_favorited INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    session_json TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_user_date ON user_flashcard_sessions (user_id, session_date);

-- ----------------------------------------------------------------------------
-- 30. messages - 聊天消息（AI 对话历史）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id TEXT NOT NULL PRIMARY KEY,
    session_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages (session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_student_time ON messages (student_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role_type ON messages (role, message_type);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at);
CREATE INDEX IF NOT EXISTS idx_messages_deleted_at ON messages (deleted_at);

-- ----------------------------------------------------------------------------
-- 31. conversation_summaries - 会话摘要
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_summaries (
    session_id TEXT NOT NULL PRIMARY KEY,
    student_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    key_facts TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    last_message_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_student_id ON conversation_summaries (student_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_last_message_at ON conversation_summaries (last_message_at);

-- ----------------------------------------------------------------------------
-- 32. user_memories - 用户长期记忆
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_memories (
    id TEXT NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'fact',
    content TEXT NOT NULL,
    source TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    last_accessed TEXT,
    access_count INTEGER DEFAULT 1,
    confirmed INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories (user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_type ON user_memories (memory_type);
CREATE INDEX IF NOT EXISTS idx_user_memories_access_count ON user_memories (access_count);
CREATE INDEX IF NOT EXISTS idx_user_memories_created_at ON user_memories (created_at);

-- ----------------------------------------------------------------------------
-- 33. classroom_sessions - 课堂会话状态
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS classroom_sessions (
    id TEXT NOT NULL PRIMARY KEY,
    student_id TEXT NOT NULL,
    course_id TEXT NOT NULL DEFAULT '',
    course_data TEXT,
    current_scene_index INTEGER DEFAULT 0,
    visited_scenes TEXT,
    quiz_answers TEXT,
    chat_history TEXT,
    time_spent INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    teacher_persona TEXT NOT NULL DEFAULT 'expert_mentor',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_cs_student ON classroom_sessions (student_id);
CREATE INDEX IF NOT EXISTS idx_cs_updated ON classroom_sessions (updated_at);

-- ----------------------------------------------------------------------------
-- 34. quiz_records - 课堂测验记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    quiz_id TEXT NOT NULL DEFAULT '',
    score REAL DEFAULT 0.0,
    total INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    answers TEXT,
    feedback TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_qr_student ON quiz_records (student_id);
CREATE INDEX IF NOT EXISTS idx_qr_classroom ON quiz_records (classroom_id);

-- ----------------------------------------------------------------------------
-- 35. agent_turn_records - 智能体对话轮次
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_turn_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    actions TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_atr_classroom ON agent_turn_records (classroom_id);

-- ============================================================================
-- 初始化完成。共 35 张表。
-- ============================================================================