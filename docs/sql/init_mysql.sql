-- ============================================================================
-- 星识 (Star-Learn) MySQL 数据库初始化脚本
-- 兼容 MySQL 5.7+ / 8.0
-- 使用前请确保：
--   1. 已创建数据库：CREATE DATABASE xingshi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--   2. 已创建用户并授予 xingshi.* 权限
-- 本脚本所有 CREATE TABLE 使用 IF NOT EXISTS，可重复执行。
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- 1. user - 用户认证
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `nickname` VARCHAR(50) DEFAULT '',
    `avatar` VARCHAR(500) DEFAULT '',
    `current_task` VARCHAR(100) DEFAULT '大数据导论',
    `preferred_language` VARCHAR(20) DEFAULT 'python',
    `theme` VARCHAR(50) DEFAULT 'ocean',
    `last_agent_id` VARCHAR(50) DEFAULT '',
    `last_login` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 2. learning_records - 学习记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `learning_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` VARCHAR(64) NOT NULL,
    `interaction_count` INT DEFAULT 0,
    `code_practice_time` INT DEFAULT 0,
    `socratic_pass_rate` FLOAT DEFAULT 0.0,
    `difficulty_level` VARCHAR(20) DEFAULT 'basic',
    `profile_json` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_lr_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 3. learning_path - 学习路径
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `learning_path` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `path_json` LONGTEXT,
    `generated_at` DATETIME DEFAULT NULL,
    `reasoning` TEXT DEFAULT NULL,
    `data_sources` JSON DEFAULT NULL,
    `confidence` FLOAT DEFAULT 0.0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 4. user_profile - 用户画像
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_profile` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `profile_json` LONGTEXT,
    `evaluation_json` LONGTEXT,
    `last_grade_record` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 5. user_evaluations - 用户评估指标历史
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_evaluations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `interaction_count` INT DEFAULT 0,
    `socratic_pass_rate` FLOAT DEFAULT 0.0,
    `difficulty_level` VARCHAR(20) DEFAULT 'basic',
    `code_practice_time` INT DEFAULT 0,
    `focus_time_today` INT DEFAULT 0,
    `flashcards_studied` INT DEFAULT 0,
    `streak_days` INT DEFAULT 0,
    `eval_json` LONGTEXT,
    `record_date` DATE NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_eval_user_date` (`user_id`, `record_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 6. user_preferences - 用户偏好设置
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_preferences` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `preferences_json` LONGTEXT,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 7. user_garden - 花园/植物种植
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_garden` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `seeds` INT DEFAULT 3,
    `garden_json` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 8. user_pet - 宠物状态
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_pet` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `pet_json` LONGTEXT,
    `pet_game_json` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 9. user_achievements - 用户成就
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_achievements` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `achievements_json` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 10. user_stats - 统计数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_stats` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `stats_json` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 11. user_notifications - 通知
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `notifications_json` LONGTEXT,
    `last_update_time` BIGINT DEFAULT 0,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 12. user_settings - 综合设置
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `settings_json` LONGTEXT,
    `weather_city` VARCHAR(50) DEFAULT '',
    `floating_alarm_x` INT DEFAULT NULL,
    `floating_alarm_y` INT DEFAULT NULL,
    `hub_theme` VARCHAR(50) DEFAULT 'light',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 13. user_coding_state - 编程练习状态
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_coding_state` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `coding_state_json` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 14. user_weather_cache - 天气缓存
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_weather_cache` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `weather_json` LONGTEXT,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 15. user_focus_history - 专注历史
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_focus_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `focus_json` LONGTEXT,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 16. user_eco_data - 生态数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_eco_data` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `eco_data_json` LONGTEXT,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 17. user_projects - 架构项目
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_projects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `projects_json` LONGTEXT,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 18. user_calendar_events - 日历事件
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_calendar_events` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `events_json` LONGTEXT,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 19. daily_routes - 每日学习路线
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `daily_routes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `route_date` DATE NOT NULL,
    `tasks_json` LONGTEXT,
    `completed_json` LONGTEXT,
    `generated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_user_date` (`user_id`, `route_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 20. knowledge_nodes - 知识节点（SM2间隔重复）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `knowledge_nodes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `node_id` VARCHAR(255) NOT NULL UNIQUE,
    `name` VARCHAR(255) NOT NULL,
    `parent_id` VARCHAR(255),
    `level` VARCHAR(50) DEFAULT 'leaf',
    `icon` VARCHAR(50) DEFAULT '📚',
    `subject` VARCHAR(100) DEFAULT '',
    `is_active` TINYINT DEFAULT 0,
    `first_studied_at` TIMESTAMP NULL,
    `last_studied_at` TIMESTAMP NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `sm2_data_json` TEXT,
    `stats_json` TEXT,
    `position_x` REAL DEFAULT 0,
    `position_y` REAL DEFAULT 0,
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 21. review_records - 复习记录（SM2）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `review_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `record_id` VARCHAR(255) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `node_id` VARCHAR(255) NOT NULL,
    `review_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `quality` INT DEFAULT 0,
    `response_time` REAL DEFAULT 0,
    `sm2_result_json` TEXT,
    INDEX `idx_user_node` (`user_id`, `node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 22. telemetry_data - 遥测/行为数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `telemetry_data` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(50) NOT NULL,
    `context_id` VARCHAR(100),
    `event_type` VARCHAR(100) NOT NULL,
    `event_data` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_student` (`student_id`),
    INDEX `idx_context` (`context_id`),
    INDEX `idx_event` (`event_type`),
    INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 23. study_sessions - 学习时段记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `study_sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `session_date` DATE NOT NULL,
    `duration_minutes` INT DEFAULT 0,
    `start_time` TEXT,
    `end_time` TEXT,
    `subject` VARCHAR(100) DEFAULT '',
    `node_id` VARCHAR(255) DEFAULT '',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    INDEX `idx_user_date` (`user_id`, `session_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 24. learning_goals - 学习目标
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `learning_goals` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `goal_type` VARCHAR(50) NOT NULL,
    `title` VARCHAR(255) DEFAULT '',
    `target_value` INT DEFAULT 0,
    `current_value` INT DEFAULT 0,
    `unit` VARCHAR(20) DEFAULT 'minutes',
    `start_date` DATE,
    `end_date` DATE,
    `is_active` TINYINT DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 25. weekly_summary - 周学习总结
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `weekly_summary` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `week_start_date` DATE NOT NULL,
    `daily_minutes` TEXT,
    `hourly_distribution` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_user_week` (`user_id`, `week_start_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 26. classroom_records - 课堂记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `classroom_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `course_id` VARCHAR(100) NOT NULL UNIQUE,
    `title` VARCHAR(255) NOT NULL DEFAULT '',
    `ppt_pages` INT DEFAULT 0,
    `full_data` LONGTEXT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 27. course_generation_status - 课程生成状态跟踪
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `course_generation_status` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `course_id` VARCHAR(100) NOT NULL UNIQUE,
    `total_outlines` INT DEFAULT 0,
    `generated_count` INT DEFAULT 0,
    `pending_slides_v2` TEXT,
    `pending_quiz_data` TEXT,
    `pending_exercise_data` TEXT,
    `is_complete` TINYINT DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_course_id` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 28. user_flashcard_progress - 用户胶囊卡片进度
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_flashcard_progress` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `card_hash` VARCHAR(64) NOT NULL,
    `course_id` VARCHAR(100) DEFAULT 'bigdata',
    `chapter_name` VARCHAR(255) DEFAULT '',
    `front_text` TEXT NOT NULL,
    `back_text` TEXT NOT NULL,
    `hint_text` VARCHAR(500) DEFAULT '',
    `is_mastered` TINYINT DEFAULT 0,
    `is_favorite` TINYINT DEFAULT 0,
    `difficulty` VARCHAR(20) DEFAULT 'medium',
    `user_note` VARCHAR(1000) DEFAULT '',
    `review_count` INT DEFAULT 0,
    `first_seen_at` TIMESTAMP NULL,
    `last_reviewed_at` TIMESTAMP NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_user_card` (`user_id`, `card_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 29. user_flashcard_sessions - 用户胶囊学习会话
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_flashcard_sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `session_date` DATE NOT NULL,
    `course_id` VARCHAR(100) DEFAULT 'bigdata',
    `chapter_name` VARCHAR(255) DEFAULT '',
    `cards_total` INT DEFAULT 0,
    `cards_answered` INT DEFAULT 0,
    `cards_mastered` INT DEFAULT 0,
    `cards_favorited` INT DEFAULT 0,
    `duration_seconds` INT DEFAULT 0,
    `session_json` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    INDEX `idx_user_date` (`user_id`, `session_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 30. messages - 聊天消息（AI 对话历史）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `messages` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `session_id` VARCHAR(64) NOT NULL,
    `student_id` VARCHAR(64) NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `message_type` VARCHAR(20) NOT NULL DEFAULT 'text',
    `metadata` LONGTEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_messages_session_time` (`session_id`, `created_at`),
    INDEX `idx_messages_student_time` (`student_id`, `created_at`),
    INDEX `idx_messages_role_type` (`role`, `message_type`),
    INDEX `idx_messages_created_at` (`created_at`),
    INDEX `idx_messages_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 31. conversation_summaries - 会话摘要（AI 上下文压缩）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conversation_summaries` (
    `session_id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `student_id` VARCHAR(64) NOT NULL,
    `summary_text` LONGTEXT NOT NULL,
    `key_facts` LONGTEXT,
    `message_count` INT NOT NULL DEFAULT 0,
    `last_message_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_conversation_summaries_student_id` (`student_id`),
    INDEX `idx_conversation_summaries_last_message_at` (`last_message_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 32. user_memories - 用户长期记忆（AI 画像记忆库）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_memories` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `user_id` VARCHAR(64) NOT NULL,
    `memory_type` VARCHAR(20) NOT NULL DEFAULT 'fact',
    `content` TEXT NOT NULL,
    `source` TEXT,
    `confidence` FLOAT DEFAULT 1.0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `last_accessed` TIMESTAMP NULL DEFAULT NULL,
    `access_count` INT DEFAULT 1,
    `confirmed` TINYINT DEFAULT 0,
    INDEX `idx_user_memories_user_id` (`user_id`),
    INDEX `idx_user_memories_type` (`memory_type`),
    INDEX `idx_user_memories_access_count` (`access_count`),
    INDEX `idx_user_memories_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 33. classroom_sessions - 课堂会话状态
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `classroom_sessions` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `student_id` VARCHAR(64) NOT NULL,
    `course_id` VARCHAR(64) NOT NULL DEFAULT '',
    `course_data` JSON DEFAULT NULL,
    `current_scene_index` INT DEFAULT 0,
    `visited_scenes` JSON DEFAULT NULL,
    `quiz_answers` JSON DEFAULT NULL,
    `chat_history` JSON DEFAULT NULL,
    `time_spent` INT DEFAULT 0,
    `status` VARCHAR(20) DEFAULT 'active',
    `teacher_persona` VARCHAR(32) NOT NULL DEFAULT 'expert_mentor',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_cs_student` (`student_id`),
    INDEX `idx_cs_updated` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 34. quiz_records - 课堂测验记录
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `quiz_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `classroom_id` VARCHAR(64) NOT NULL,
    `student_id` VARCHAR(64) NOT NULL,
    `quiz_id` VARCHAR(64) NOT NULL DEFAULT '',
    `score` FLOAT DEFAULT 0.0,
    `total` INT DEFAULT 0,
    `passed` TINYINT DEFAULT 0,
    `answers` JSON DEFAULT NULL,
    `feedback` JSON DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_qr_student` (`student_id`),
    INDEX `idx_qr_classroom` (`classroom_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 35. agent_turn_records - 智能体对话轮次
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `agent_turn_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `classroom_id` VARCHAR(64) NOT NULL,
    `agent_id` VARCHAR(64) NOT NULL,
    `agent_role` VARCHAR(64) NOT NULL,
    `turn_index` INT NOT NULL,
    `content` TEXT NOT NULL,
    `actions` JSON DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_atr_classroom` (`classroom_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 初始化完成。共 35 张表（脚本基于 Navicat/setup_database.py 同步生成）
-- ============================================================================