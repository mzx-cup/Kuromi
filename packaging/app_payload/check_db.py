import sqlite3
import json

conn = sqlite3.connect('xingshi.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

if 'user' in tables:
    cursor.execute('SELECT id, username FROM user LIMIT 3')
    for row in cursor.fetchall():
        print('user:', row)

if 'user_profile' in tables:
    cursor.execute('SELECT user_id, evaluation_json FROM user_profile LIMIT 3')
    for row in cursor.fetchall():
        print('user_profile:', row)

conn.close()
