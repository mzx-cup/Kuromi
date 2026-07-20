-- ============================================================================
-- ⚠️ 危险：删除数据库所有表
-- 仅限测试 / 开发环境使用！
-- 生产环境执行此脚本将清除所有数据，且不可恢复。
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `agent_turn_records`;
DROP TABLE IF EXISTS `quiz_records`;
DROP TABLE IF EXISTS `classroom_sessions`;
DROP TABLE IF EXISTS `user_memories`;
DROP TABLE IF EXISTS `conversation_summaries`;
DROP TABLE IF EXISTS `messages`;
DROP TABLE IF EXISTS `user_flashcard_sessions`;
DROP TABLE IF EXISTS `user_flashcard_progress`;
DROP TABLE IF EXISTS `course_generation_status`;
DROP TABLE IF EXISTS `classroom_records`;
DROP TABLE IF EXISTS `weekly_summary`;
DROP TABLE IF EXISTS `learning_goals`;
DROP TABLE IF EXISTS `study_sessions`;
DROP TABLE IF EXISTS `telemetry_data`;
DROP TABLE IF EXISTS `review_records`;
DROP TABLE IF EXISTS `knowledge_nodes`;
DROP TABLE IF EXISTS `daily_routes`;
DROP TABLE IF EXISTS `user_calendar_events`;
DROP TABLE IF EXISTS `user_projects`;
DROP TABLE IF EXISTS `user_eco_data`;
DROP TABLE IF EXISTS `user_focus_history`;
DROP TABLE IF EXISTS `user_weather_cache`;
DROP TABLE IF EXISTS `user_coding_state`;
DROP TABLE IF EXISTS `user_settings`;
DROP TABLE IF EXISTS `user_notifications`;
DROP TABLE IF EXISTS `user_stats`;
DROP TABLE IF EXISTS `user_achievements`;
DROP TABLE IF EXISTS `user_pet`;
DROP TABLE IF EXISTS `user_garden`;
DROP TABLE IF EXISTS `user_preferences`;
DROP TABLE IF EXISTS `user_evaluations`;
DROP TABLE IF EXISTS `user_profile`;
DROP TABLE IF EXISTS `learning_path`;
DROP TABLE IF EXISTS `learning_records`;
DROP TABLE IF EXISTS `user`;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 已删除 35 张表
-- ============================================================================