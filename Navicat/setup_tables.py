import pymysql

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'xingshi',
    'charset': 'utf8mb4'
}

def column_exists(cursor, table, column):
    cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{DB_CONFIG['database']}' AND TABLE_NAME = '{table}' AND COLUMN_NAME = '{column}'")
    return cursor.fetchone() is not None

def table_exists(cursor, table):
    cursor.execute(f"SHOW TABLES LIKE '{table}'")
    return cursor.fetchone() is not None

def init_tables():
    print("开始连接数据库...")
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        if not table_exists(cursor, 'user'):
            print("1. 正在创建 'user' 表...")
            cursor.execute("""
                CREATE TABLE user (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    nickname VARCHAR(50) DEFAULT '',
                    avatar VARCHAR(500) DEFAULT '',
                    current_task VARCHAR(100) DEFAULT '大数据导论',
                    last_login TIMESTAMP NULL DEFAULT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("   -> user 表创建成功")
        else:
            print("1. 'user' 表已存在，检查字段...")
            if not column_exists(cursor, 'user', 'nickname'):
                cursor.execute("ALTER TABLE user ADD COLUMN nickname VARCHAR(50) DEFAULT '' AFTER password")
                print("   -> 添加 nickname 字段成功")
            if not column_exists(cursor, 'user', 'avatar'):
                cursor.execute("ALTER TABLE user ADD COLUMN avatar VARCHAR(500) DEFAULT '' AFTER nickname")
                print("   -> 添加 avatar 字段成功")
            if not column_exists(cursor, 'user', 'current_task'):
                cursor.execute("ALTER TABLE user ADD COLUMN current_task VARCHAR(100) DEFAULT '大数据导论' AFTER avatar")
                print("   -> 添加 current_task 字段成功")
            if not column_exists(cursor, 'user', 'last_login'):
                cursor.execute("ALTER TABLE user ADD COLUMN last_login TIMESTAMP NULL DEFAULT NULL AFTER current_task")
                print("   -> 添加 last_login 字段成功")

        if not table_exists(cursor, 'learning_records'):
            print("2. 正在创建 'learning_records' 表...")
            cursor.execute("""
                CREATE TABLE learning_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    interaction_count INT DEFAULT 0,
                    code_practice_time INT DEFAULT 0,
                    socratic_pass_rate FLOAT DEFAULT 0.0,
                    difficulty_level VARCHAR(20) DEFAULT 'basic',
                    profile_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("   -> learning_records 表创建成功")
        else:
            print("2. 'learning_records' 表已存在，检查字段...")
            if not column_exists(cursor, 'learning_records', 'interaction_count'):
                cursor.execute("ALTER TABLE learning_records ADD COLUMN interaction_count INT DEFAULT 0 AFTER user_id")
                print("   -> 添加 interaction_count 字段成功")
            if not column_exists(cursor, 'learning_records', 'code_practice_time'):
                cursor.execute("ALTER TABLE learning_records ADD COLUMN code_practice_time INT DEFAULT 0 AFTER interaction_count")
                print("   -> 添加 code_practice_time 字段成功")
            if not column_exists(cursor, 'learning_records', 'socratic_pass_rate'):
                cursor.execute("ALTER TABLE learning_records ADD COLUMN socratic_pass_rate FLOAT DEFAULT 0.0 AFTER code_practice_time")
                print("   -> 添加 socratic_pass_rate 字段成功")
            if not column_exists(cursor, 'learning_records', 'difficulty_level'):
                cursor.execute("ALTER TABLE learning_records ADD COLUMN difficulty_level VARCHAR(20) DEFAULT 'basic' AFTER socratic_pass_rate")
                print("   -> 添加 difficulty_level 字段成功")

        if not table_exists(cursor, 'learning_path'):
            print("3. 正在创建 'learning_path' 表...")
            cursor.execute("""
                CREATE TABLE learning_path (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    path_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("   -> learning_path 表创建成功")

        if not table_exists(cursor, 'user_profile'):
            print("4. 正在创建 'user_profile' 表...")
            cursor.execute("""
                CREATE TABLE user_profile (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    profile_json TEXT,
                    evaluation_json TEXT,
                    last_grade_record TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("   -> user_profile 表创建成功")
        else:
            print("4. 'user_profile' 表已存在，检查字段...")
            if not column_exists(cursor, 'user_profile', 'profile_json'):
                cursor.execute("ALTER TABLE user_profile ADD COLUMN profile_json TEXT AFTER user_id")
                print("   -> 添加 profile_json 字段成功")
            if not column_exists(cursor, 'user_profile', 'evaluation_json'):
                cursor.execute("ALTER TABLE user_profile ADD COLUMN evaluation_json TEXT AFTER profile_json")
                print("   -> 添加 evaluation_json 字段成功")
            if not column_exists(cursor, 'user_profile', 'last_grade_record'):
                cursor.execute("ALTER TABLE user_profile ADD COLUMN last_grade_record TEXT AFTER evaluation_json")
                print("   -> 添加 last_grade_record 字段成功")

        conn.commit()
        print("\n太棒了！数据库表结构更新完成！")
        print("现在你可以直接运行 python main.py 启动项目了。")

    except Exception as e:
        print(f"\n❌ 更新表结构时发生错误: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    init_tables()