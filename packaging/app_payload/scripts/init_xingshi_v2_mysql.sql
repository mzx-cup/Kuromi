-- MySQL DDL for xingshi_v2 schema
-- Generated from app/models/* via SQLAlchemy
-- Engine: InnoDB, charset=utf8mb4, collation=utf8mb4_unicode_ci
-- Apply: mysql -h <host> -u root -p xingshi_v2 < scripts/init_xingshi_v2_mysql.sql


CREATE TABLE users (
	id VARCHAR(64) NOT NULL, 
	username VARCHAR(128) NOT NULL, 
	nickname VARCHAR(128) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	preferred_language VARCHAR(16) NOT NULL, 
	avatar_url VARCHAR(512) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE student_profiles (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	learning_style VARCHAR(32) NOT NULL, 
	cognitive_level VARCHAR(32) NOT NULL, 
	learning_progress FLOAT NOT NULL, 
	learning_goals TEXT, 
	interaction_count INTEGER NOT NULL, 
	socratic_pass_rate FLOAT NOT NULL, 
	code_practice_time INTEGER NOT NULL, 
	preferred_persona VARCHAR(32) COMMENT '学生偏好的教学风格(可选，为空则由系统根据画像自动选择)', 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_profile (
	user_id VARCHAR(64) NOT NULL, 
	preferred_language VARCHAR(16) NOT NULL, 
	theme VARCHAR(32) NOT NULL, 
	PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_themes (
	user_id VARCHAR(64) NOT NULL, 
	theme VARCHAR(32) NOT NULL, 
	accent_color VARCHAR(16) NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_stats (
	user_id VARCHAR(64) NOT NULL, 
	total_minutes INTEGER NOT NULL, 
	streak_days INTEGER NOT NULL, 
	completed_courses INTEGER NOT NULL, 
	last_active DATETIME NOT NULL, 
	PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE subjects (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	slug VARCHAR(64) NOT NULL, 
	icon VARCHAR(32) NOT NULL, 
	visible BOOL NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE scene_outlines (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	course_id VARCHAR(64) NOT NULL, 
	scene_index INTEGER NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	scene_type VARCHAR(32) NOT NULL, 
	key_points JSON, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE slides (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	course_id VARCHAR(64) NOT NULL, 
	scene_index INTEGER NOT NULL, 
	slide_index INTEGER NOT NULL, 
	layout VARCHAR(32) NOT NULL, 
	elements JSON, 
	notes TEXT NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE classroom_sessions (
	id VARCHAR(64) NOT NULL, 
	student_id VARCHAR(64) NOT NULL, 
	course_id VARCHAR(64) NOT NULL, 
	course_data JSON, 
	current_scene_index INTEGER NOT NULL, 
	visited_scenes JSON, 
	quiz_answers JSON, 
	chat_history JSON, 
	time_spent INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	teacher_persona VARCHAR(32) NOT NULL COMMENT 'AI教师角色: patient_tutor|socratic_questioner|energetic_lecturer|expert_mentor', 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	user_id VARCHAR(64), 
	started_at DATETIME, 
	ended_at DATETIME, 
	current_slide INTEGER NOT NULL, 
	teacher_mode BOOL NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_classroom_sessions_user_id ON classroom_sessions (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE quiz_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	classroom_id VARCHAR(64) NOT NULL, 
	student_id VARCHAR(64) NOT NULL, 
	quiz_id VARCHAR(64) NOT NULL, 
	score FLOAT NOT NULL, 
	total INTEGER NOT NULL, 
	passed BOOL NOT NULL, 
	answers JSON, 
	feedback JSON, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	session_id INTEGER, 
	user_id VARCHAR(64), 
	question TEXT NOT NULL, 
	answer TEXT NOT NULL, 
	correct BOOL NOT NULL, 
	max_score FLOAT NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_quiz_records_session_id ON quiz_records (session_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_quiz_records_user_id ON quiz_records (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE agent_turn_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	classroom_id VARCHAR(64) NOT NULL, 
	agent_id VARCHAR(64) NOT NULL, 
	agent_role VARCHAR(64) NOT NULL, 
	turn_index INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	actions JSON, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	session_id VARCHAR(64), 
	turn_number INTEGER NOT NULL, 
	user_input TEXT NOT NULL, 
	agent_output TEXT NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_agent_turn_records_session_id ON agent_turn_records (session_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE messages (
	id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL COMMENT '会话/课堂 ID，关联 classroom_sessions 或独立聊天会话', 
	student_id VARCHAR(64) NOT NULL COMMENT '学生 ID', 
	`role` VARCHAR(20) NOT NULL COMMENT '消息角色: user | assistant | system | tool', 
	content TEXT NOT NULL COMMENT '消息文本内容（Markdown 格式）', 
	message_type VARCHAR(20) NOT NULL COMMENT '消息类型: text | action | link | image | tool_call | proactive', 
	msg_metadata JSON COMMENT '扩展元数据: agent_id, links, actions, tokens_used, model, latency_ms...', 
	created_at DATETIME NOT NULL COMMENT '消息创建时间（UTC）' DEFAULT now(), 
	deleted_at DATETIME COMMENT '软删除时间，NULL 表示未删除', 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_session_time ON messages (session_id, created_at) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_student_id ON messages (student_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_student_time ON messages (student_id, created_at) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_role ON messages (`role`) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_role_type ON messages (`role`, message_type) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_deleted_at ON messages (deleted_at) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_created_at ON messages (created_at) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_session_id ON messages (session_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_messages_message_type ON messages (message_type) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE conversation_summaries (
	session_id VARCHAR(64) NOT NULL COMMENT '关联的会话 ID', 
	student_id VARCHAR(64) NOT NULL COMMENT '学生 ID', 
	summary_text TEXT NOT NULL COMMENT 'AI 生成的会话摘要（200 字以内）', 
	key_facts JSON COMMENT '结构化关键信息: {topic, current_chapter, difficulties, preferences}', 
	message_count INTEGER NOT NULL COMMENT '当前会话消息总数', 
	last_message_at DATETIME NOT NULL COMMENT '最后一条消息时间' DEFAULT now(), 
	updated_at DATETIME NOT NULL COMMENT '摘要最后更新时间' DEFAULT now(), 
	PRIMARY KEY (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_conversation_summaries_last_message_at ON conversation_summaries (last_message_at) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_conversation_summaries_student_id ON conversation_summaries (student_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_login_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	ip_address VARCHAR(64) NOT NULL, 
	user_agent VARCHAR(512) NOT NULL, 
	login_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_preferences (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	`key` VARCHAR(128) NOT NULL, 
	value JSON NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_user_preferences_user_id ON user_preferences (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_settings (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	setting_key VARCHAR(128) NOT NULL, 
	setting_value TEXT NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_user_settings_user_id ON user_settings (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE study_sessions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	subject VARCHAR(64) NOT NULL, 
	duration_minutes INTEGER NOT NULL, 
	session_date DATE NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_study_sessions_user_id ON study_sessions (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE learning_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	activity_type VARCHAR(64) NOT NULL, 
	subject VARCHAR(64) NOT NULL, 
	minutes INTEGER NOT NULL, 
	metadata_json JSON NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_learning_records_user_id ON learning_records (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE learning_goals (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	target_value FLOAT NOT NULL, 
	current_value FLOAT NOT NULL, 
	unit VARCHAR(32) NOT NULL, 
	deadline DATE, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_learning_goals_user_id ON learning_goals (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE weekly_summary (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	week_start DATE NOT NULL, 
	total_minutes INTEGER NOT NULL, 
	subjects JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_weekly_summary_user_id ON weekly_summary (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE course_progress (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	course_id VARCHAR(64) NOT NULL, 
	progress_percent FLOAT NOT NULL, 
	completed_at DATETIME, 
	last_accessed DATETIME NOT NULL, 
	state_json JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_course_progress_user_id ON course_progress (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_course_progress_course_id ON course_progress (course_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE learning_paths (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	description TEXT NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_learning_paths_user_id ON learning_paths (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_evaluations (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	subject VARCHAR(64) NOT NULL, 
	score FLOAT NOT NULL, 
	max_score FLOAT NOT NULL, 
	notes TEXT NOT NULL, 
	evaluated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_user_evaluations_user_id ON user_evaluations (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE course_generation_status (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	course_id VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	progress_percent FLOAT NOT NULL, 
	error_message TEXT NOT NULL, 
	started_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_course_generation_status_user_id ON course_generation_status (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_course_generation_status_course_id ON course_generation_status (course_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE course_deadlines (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	course_id VARCHAR(64) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	deadline DATE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_course_deadlines_user_id ON course_deadlines (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_course_deadlines_deadline ON course_deadlines (deadline) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_course_deadlines_course_id ON course_deadlines (course_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE courses (
	id VARCHAR(64) NOT NULL, 
	subject_id VARCHAR(64) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	description TEXT NOT NULL, 
	bvid VARCHAR(32) NOT NULL, 
	playlist_url VARCHAR(512) NOT NULL, 
	cover_url VARCHAR(512) NOT NULL, 
	author_name VARCHAR(128) NOT NULL, 
	total_lessons INTEGER NOT NULL, 
	total_duration INTEGER NOT NULL, 
	progress FLOAT NOT NULL, 
	visible BOOL NOT NULL, 
	sort_order INTEGER NOT NULL, 
	student_id VARCHAR(64) NOT NULL, 
	outlines JSON, 
	scenes JSON, 
	data_json JSON, 
	status VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(subject_id) REFERENCES subjects (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE knowledge_nodes (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	subject VARCHAR(64) NOT NULL, 
	description TEXT NOT NULL, 
	mastery FLOAT NOT NULL, 
	importance INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_knowledge_nodes_user_id ON knowledge_nodes (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE focus_sessions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	started_at DATETIME NOT NULL, 
	ended_at DATETIME, 
	duration_minutes INTEGER NOT NULL, 
	planned_minutes INTEGER NOT NULL, 
	completed BOOL NOT NULL, 
	subject VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_focus_sessions_user_id ON focus_sessions (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_focus_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	focus_date DATE NOT NULL, 
	total_focus_minutes INTEGER NOT NULL, 
	sessions_count INTEGER NOT NULL, 
	avg_flow_score FLOAT NOT NULL, 
	deep_focus_minutes INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_user_focus_history_user_id ON user_focus_history (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_garden (
	user_id VARCHAR(64) NOT NULL, 
	plants_json JSON NOT NULL, 
	last_watered DATETIME, 
	growth_points INTEGER NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_pet (
	user_id VARCHAR(64) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	level INTEGER NOT NULL, 
	happiness FLOAT NOT NULL, 
	hunger FLOAT NOT NULL, 
	energy FLOAT NOT NULL, 
	last_fed DATETIME, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_achievements (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	achievement_id VARCHAR(64) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	description TEXT NOT NULL, 
	unlocked_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_user_achievements_user_id ON user_achievements (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_eco_data (
	user_id VARCHAR(64) NOT NULL, 
	eco_points INTEGER NOT NULL, 
	co2_saved_kg FLOAT NOT NULL, 
	trees_planted INTEGER NOT NULL, 
	level VARCHAR(32) NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE chat_messages (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	`role` VARCHAR(32) NOT NULL, 
	content TEXT NOT NULL, 
	msg_metadata JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_chat_messages_user_id ON chat_messages (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE chat_conversation_summaries (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	conversation_id VARCHAR(64) NOT NULL, 
	summary TEXT NOT NULL, 
	key_facts JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_chat_conversation_summaries_user_id ON chat_conversation_summaries (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_chat_conversation_summaries_conversation_id ON chat_conversation_summaries (conversation_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE chat_agent_turn_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	agent_id VARCHAR(64) NOT NULL, 
	turn_number INTEGER NOT NULL, 
	user_input TEXT NOT NULL, 
	agent_output TEXT NOT NULL, 
	tool_calls JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_chat_agent_turn_records_user_id ON chat_agent_turn_records (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE user_memories (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	memory_type VARCHAR(32) NOT NULL, 
	content TEXT NOT NULL, 
	importance INTEGER NOT NULL, 
	source_conversation_id VARCHAR(64), 
	created_at DATETIME NOT NULL, 
	last_accessed DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_user_memories_user_id ON user_memories (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE learning_path_nodes (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	path_id INTEGER NOT NULL, 
	course_id VARCHAR(64), 
	title VARCHAR(256) NOT NULL, 
	order_index INTEGER NOT NULL, 
	completed BOOL NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(path_id) REFERENCES learning_paths (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_learning_path_nodes_path_id ON learning_path_nodes (path_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE chapters (
	id VARCHAR(64) NOT NULL, 
	course_id VARCHAR(64) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	description TEXT NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE knowledge_relations (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	source_node_id INTEGER NOT NULL, 
	target_node_id INTEGER NOT NULL, 
	relation_type VARCHAR(64) NOT NULL, 
	weight FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(source_node_id) REFERENCES knowledge_nodes (id), 
	FOREIGN KEY(target_node_id) REFERENCES knowledge_nodes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_knowledge_relations_user_id ON knowledge_relations (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE knowledge_reviews (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	node_id INTEGER NOT NULL, 
	ease_factor FLOAT NOT NULL, 
	interval_days INTEGER NOT NULL, 
	repetitions INTEGER NOT NULL, 
	next_review_date DATE NOT NULL, 
	last_reviewed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(node_id) REFERENCES knowledge_nodes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_knowledge_reviews_user_id ON knowledge_reviews (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_knowledge_reviews_node_id ON knowledge_reviews (node_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE knowledge_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	node_id INTEGER NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	quality INTEGER NOT NULL, 
	notes TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(node_id) REFERENCES knowledge_nodes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_knowledge_records_node_id ON knowledge_records (node_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_knowledge_records_user_id ON knowledge_records (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE knowledge_pending (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	node_id INTEGER NOT NULL, 
	due_date DATE NOT NULL, 
	priority INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(node_id) REFERENCES knowledge_nodes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_knowledge_pending_user_id ON knowledge_pending (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE review_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(64) NOT NULL, 
	node_id INTEGER NOT NULL, 
	next_review_date DATE NOT NULL, 
	reviewed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(node_id) REFERENCES knowledge_nodes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_review_history_user_id ON review_history (user_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_review_history_node_id ON review_history (node_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE focus_events (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	session_id INTEGER NOT NULL, 
	event_type VARCHAR(64) NOT NULL, 
	timestamp DATETIME NOT NULL, 
	flow_score FLOAT NOT NULL, 
	metadata_json JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES focus_sessions (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_focus_events_session_id ON focus_events (session_id) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE subchapters (
	id VARCHAR(64) NOT NULL, 
	chapter_id VARCHAR(64) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	description TEXT NOT NULL, 
	bvid VARCHAR(32) NOT NULL, 
	cid INTEGER NOT NULL, 
	page INTEGER NOT NULL, 
	duration INTEGER NOT NULL, 
	type VARCHAR(32) NOT NULL, 
	completed BOOL NOT NULL, 
	transcript TEXT NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(chapter_id) REFERENCES chapters (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE knowledge_points (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	subchapter_id VARCHAR(64) NOT NULL, 
	title VARCHAR(256) NOT NULL, 
	content TEXT NOT NULL, 
	difficulty VARCHAR(16) NOT NULL, 
	mastered BOOL NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(subchapter_id) REFERENCES subchapters (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

