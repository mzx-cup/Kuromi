import pymysql

# 注意：这里配置没有 'database' 字段，因为我们要从最底层连接 MySQL 来创建数据库
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root', # 确保这里的密码是你本地 MySQL 的密码
    'charset': 'utf8mb4'
}

def setup_database():
    print("开始连接 MySQL 服务器...")
    try:
        # 连接到 MySQL 服务器
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. 创建数据库 xingshi (如果不存在)
        print("1. 正在检查并创建数据库 'xingshi'...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS xingshi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        # 切换到刚刚创建的数据库
        cursor.execute("USE xingshi")
        print("   -> 成功连接到 xingshi 数据库")

        # 2. 创建 user 表 (如果不存在)
        print("2. 正在检查并创建 'user' 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                avatar VARCHAR(500) DEFAULT '',
                current_task VARCHAR(100) DEFAULT '大数据导论',
                last_login TIMESTAMP NULL DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("   -> user 表就绪")

        # 3. 创建 learning_records 表 (如果不存在)
        print("3. 正在检查并创建 'learning_records' 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
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
        print("   -> learning_records 表就绪")

        # 提交更改
        conn.commit()
        print("\n✅ 太棒了！数据库环境已全部初始化完成！")
        print("现在你可以直接启动 main.py 开始体验系统了。")

    except pymysql.err.OperationalError as e:
        print(f"\n❌ 连接 MySQL 失败: {e}")
        print("请检查：\n1. MySQL 服务是否已经启动\n2. 密码是否正确")
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    setup_database()