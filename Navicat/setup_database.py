"""
星识数据库初始化脚本
使用方法: python setup_database.py
依赖: pip install pymysql
"""
import pymysql

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'charset': 'utf8mb4'
}
DATABASE_NAME = 'xingshi'


def create_database():
    print("正在连接 MySQL 服务器...")
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {DATABASE_NAME}")
        print(f"  -> 数据库 '{DATABASE_NAME}' 就绪")

        # user 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                nickname VARCHAR(50) DEFAULT '',
                avatar VARCHAR(500) DEFAULT '',
                current_task VARCHAR(100) DEFAULT '大数据导论',
                last_login TIMESTAMP NULL DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("  -> user 表就绪")

        # learning_records 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                interaction_count INT DEFAULT 0,
                code_practice_time INT DEFAULT 0,
                socratic_pass_rate FLOAT DEFAULT 0.0,
                difficulty_level VARCHAR(20) DEFAULT 'basic',
                profile_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("  -> learning_records 表就绪")

        # learning_path 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_path (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                path_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("  -> learning_path 表就绪")

        # user_profile 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                profile_json TEXT,
                evaluation_json TEXT,
                last_grade_record TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("  -> user_profile 表就绪")

        conn.commit()
        print(f"\n数据库 '{DATABASE_NAME}' 初始化完成！")
        print("现在可以直接运行 python main.py 启动项目。")

    except pymysql.err.OperationalError as e:
        print(f"\n连接 MySQL 失败: {e}")
        print("请检查: 1) MySQL 服务是否已启动  2) 密码是否正确")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == '__main__':
    create_database()