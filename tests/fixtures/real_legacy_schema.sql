-- calendar_events
CREATE TABLE calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        location TEXT DEFAULT '',
        start_at TEXT NOT NULL,
        end_at TEXT,
        all_day INTEGER DEFAULT 0,
        color TEXT DEFAULT '',
        recurrence_rule TEXT DEFAULT '',
        reminder_minutes INTEGER DEFAULT 0,
        source TEXT DEFAULT 'manual',
        external_id TEXT DEFAULT '',
        payload_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- classroom_records
CREATE TABLE classroom_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        course_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL DEFAULT '',
        ppt_pages INTEGER DEFAULT 0,
        full_data TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- classroom_sessions
CREATE TABLE classroom_sessions (
        id TEXT NOT NULL PRIMARY KEY,
        student_id TEXT NOT NULL,
        course_id TEXT NOT NULL DEFAULT '',
        course_data JSON DEFAULT NULL,
        current_scene_index INTEGER DEFAULT 0,
        visited_scenes JSON DEFAULT NULL,
        quiz_answers JSON DEFAULT NULL,
        chat_history JSON DEFAULT NULL,
        time_spent INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        teacher_persona TEXT NOT NULL DEFAULT 'expert_mentor',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT,
        `slides` JSON DEFAULT NULL,
        `is_demo` INTEGER DEFAULT 0,
        `demo_version` TEXT DEFAULT ''
    );

-- conversation_summaries
CREATE TABLE conversation_summaries (
        session_id TEXT NOT NULL PRIMARY KEY,
        student_id TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        key_facts TEXT,
        message_count INTEGER NOT NULL DEFAULT 0,
        last_message_at TEXT DEFAULT (datetime('now','localtime')),
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- course_generation_status
CREATE TABLE course_generation_status (
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

-- courses
CREATE TABLE courses (
        id TEXT PRIMARY KEY,
        subject_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        bvid TEXT DEFAULT '',
        playlist_url TEXT DEFAULT '',
        cover_url TEXT DEFAULT '',
        author_name TEXT DEFAULT '',
        total_lessons INTEGER DEFAULT 0,
        total_duration INTEGER DEFAULT 0,
        progress REAL DEFAULT 0.0,
        visible INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        student_id TEXT DEFAULT '',
        outlines JSON,
        scenes JSON,
        data_json JSON,
        status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT,
        is_demo INTEGER DEFAULT 0,
        demo_version TEXT DEFAULT ''
    );

-- daily_route_tasks
CREATE TABLE daily_route_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        route_date TEXT NOT NULL,
        task_key TEXT NOT NULL,
        title TEXT NOT NULL,
        task_type TEXT DEFAULT 'study',
        sort_order INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        completed_at TEXT,
        estimated_minutes INTEGER DEFAULT 0,
        actual_minutes INTEGER DEFAULT 0,
        node_id TEXT DEFAULT '',
        payload_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- daily_routes
CREATE TABLE daily_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        route_date TEXT NOT NULL,
        title TEXT DEFAULT '',
        summary TEXT,
        generated_at TEXT DEFAULT (datetime('now','localtime')),
        total_estimated_minutes INTEGER DEFAULT 0,
        total_actual_minutes INTEGER DEFAULT 0,
        completion_rate REAL DEFAULT 0.0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- focus_events
CREATE TABLE focus_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        event_type TEXT DEFAULT 'start',
        timestamp TEXT,
        flow_score REAL DEFAULT 0.0,
        metadata_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- focus_sessions
CREATE TABLE focus_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        started_at TEXT,
        ended_at TEXT,
        duration_minutes INTEGER DEFAULT 0,
        planned_minutes INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        subject TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- knowledge_nodes
CREATE TABLE knowledge_nodes (
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
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT,
        sm2_data_json TEXT,
        stats_json TEXT,
        position_x REAL DEFAULT 0,
        position_y REAL DEFAULT 0
    );

-- learning_goals
CREATE TABLE learning_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_type TEXT NOT NULL,
        title TEXT DEFAULT '',
        target_value INTEGER DEFAULT 0,
        current_value INTEGER DEFAULT 0,
        unit TEXT DEFAULT 'minutes',
        start_date DATE,
        end_date DATE,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- learning_path
CREATE TABLE learning_path (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        path_json TEXT,
        generated_at TEXT,
        reasoning TEXT DEFAULT NULL,
        data_sources JSON DEFAULT NULL,
        confidence REAL DEFAULT 0.0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );

-- learning_records
CREATE TABLE learning_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        interaction_count INTEGER DEFAULT 0,
        code_practice_time INTEGER DEFAULT 0,
        socratic_pass_rate REAL DEFAULT 0.0,
        difficulty_level TEXT DEFAULT 'basic',
        profile_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );

-- messages
CREATE TABLE messages (
        id TEXT NOT NULL PRIMARY KEY,
        session_id TEXT NOT NULL,
        student_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        message_type TEXT NOT NULL DEFAULT 'text',
        metadata TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- playlist_videos
CREATE TABLE playlist_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        playlist_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        position INTEGER DEFAULT 0,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );

-- quiz_records
CREATE TABLE quiz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        classroom_id TEXT NOT NULL,
        student_id TEXT NOT NULL,
        quiz_id TEXT NOT NULL DEFAULT '',
        score REAL DEFAULT 0.0,
        total INTEGER DEFAULT 0,
        passed INTEGER DEFAULT 0,
        answers JSON DEFAULT NULL,
        feedback JSON DEFAULT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- review_records
CREATE TABLE review_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        node_id TEXT NOT NULL,
        review_date TEXT DEFAULT (datetime('now','localtime')),
        quality INTEGER DEFAULT 0,
        response_time REAL DEFAULT 0,
        sm2_result_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- study_sessions
CREATE TABLE study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_date TEXT NOT NULL,
        duration_minutes INTEGER DEFAULT 0,
        start_time TEXT,
        end_time TEXT,
        subject TEXT DEFAULT '',
        node_id TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- telemetry_data
CREATE TABLE telemetry_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        context_id TEXT,
        event_type TEXT NOT NULL,
        event_data TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );

-- user
CREATE TABLE user (
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
    , role TEXT DEFAULT 'student', display_name TEXT DEFAULT '');

-- user_achievements
CREATE TABLE user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        achievements_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_coding_state
CREATE TABLE user_coding_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        coding_state_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_eco_data
CREATE TABLE user_eco_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        eco_data_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_evaluations
CREATE TABLE user_evaluations (
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
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_flashcard_progress
CREATE TABLE user_flashcard_progress (
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
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_flashcard_sessions
CREATE TABLE user_flashcard_sessions (
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
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_focus_history
CREATE TABLE user_focus_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        focus_date DATE DEFAULT NULL,
        total_focus_minutes INTEGER DEFAULT 0,
        sessions_count INTEGER DEFAULT 0,
        avg_flow_score REAL DEFAULT 0.0,
        deep_focus_minutes INTEGER DEFAULT 0,
        focus_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_garden
CREATE TABLE user_garden (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        seeds INTEGER DEFAULT 3,
        garden_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_memories
CREATE TABLE user_memories (
        id TEXT NOT NULL PRIMARY KEY,
        user_id TEXT NOT NULL,
        memory_type TEXT NOT NULL DEFAULT 'fact',
        content TEXT NOT NULL,
        source TEXT,
        confidence REAL DEFAULT 1.0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT,
        last_accessed TEXT,
        access_count INTEGER DEFAULT 1,
        confirmed INTEGER DEFAULT 0
    );

-- user_notifications
CREATE TABLE user_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        notifications_json TEXT,
        last_update_time INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_pet
CREATE TABLE user_pet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        pet_json TEXT,
        pet_game_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_preferences
CREATE TABLE user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        preferences_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_profile
CREATE TABLE user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        profile_json TEXT,
        evaluation_json TEXT,
        last_grade_record TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_projects
CREATE TABLE user_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        projects_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_settings
CREATE TABLE user_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        settings_json TEXT,
        weather_city TEXT DEFAULT '',
        floating_alarm_x INTEGER DEFAULT NULL,
        floating_alarm_y INTEGER DEFAULT NULL,
        hub_theme TEXT DEFAULT 'light',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_stats
CREATE TABLE user_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        stats_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- user_weather_cache
CREATE TABLE user_weather_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        weather_json TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

-- video_courses
CREATE TABLE video_courses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        subtitle TEXT DEFAULT '',
                        source_type TEXT NOT NULL DEFAULT 'bilibili',
                        bvid TEXT DEFAULT '',
                        page INTEGER DEFAULT 1,
                        local_path TEXT DEFAULT '',
                        duration_label TEXT DEFAULT '--:--',
                        ai_summary TEXT DEFAULT '',
                        ai_timeline TEXT DEFAULT '[]',
                        ai_questions TEXT DEFAULT '[]',
                        ai_suggestion TEXT DEFAULT '',
                        created_by TEXT DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );

-- video_playlists
CREATE TABLE video_playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL DEFAULT '默认列表',
                        position INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );

-- weekly_summary
CREATE TABLE weekly_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        week_start_date TEXT NOT NULL,
        daily_minutes TEXT,
        hourly_distribution TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        deleted_at TEXT
    );

