#!/usr/bin/env python3
import sqlite3
import sys
sys.path.insert(0, 'server')

from app.config import ADMIN_IDS, DB_PATH

print(f"ADMIN_IDS: {ADMIN_IDS}")
print(f"DB_PATH: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT key, value FROM settings WHERE key = 'maintenance_mode'")
result = cursor.fetchone()
conn.close()

print(f"Maintenance mode in DB: {result}")

# Тестируем для не-админа
test_user_id = 999999999
print(f"\nTest user {test_user_id}:")
print(f"  Is admin: {test_user_id in ADMIN_IDS}")
print(f"  Should be blocked: {result and result[1] == '1' and test_user_id not in ADMIN_IDS}")

# Тестируем для админа
if ADMIN_IDS:
    admin_id = ADMIN_IDS[0]
    print(f"\nAdmin user {admin_id}:")
    print(f"  Is admin: {admin_id in ADMIN_IDS}")
    print(f"  Should be blocked: {result and result[1] == '1' and admin_id not in ADMIN_IDS}")
