"""
Automatic SQLite database backup
Creates backups in /app/backups/ directory every 6 hours
Keeps last 14 days of backups
"""
import os
import shutil
import time
import asyncio
import glob
from datetime import datetime

BACKUP_DIR = os.environ.get('BACKUP_DIR', '/app/backups')
RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '14'))

DB_FILES = [
    '/app/users.db',
    '/app/support.db',
]


def backup_db():
    """Создаёт копию всех SQLite файлов"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
    count = 0

    for db_path in DB_FILES:
        if not os.path.exists(db_path):
            print(f"⚠️ Backup: {db_path} not found, skipping")
            continue

        db_name = os.path.basename(db_path)
        backup_name = f"{timestamp_str}_{db_name}"
        backup_path = os.path.join(BACKUP_DIR, backup_name)

        try:
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup: {db_path} -> {backup_path}")
            count += 1
        except Exception as e:
            print(f"❌ Backup failed for {db_path}: {e}")

    # Удаляем старые бекапы
    cutoff = time.time() - RETENTION_DAYS * 86400
    for f in glob.glob(os.path.join(BACKUP_DIR, "*_*.db")):
        try:
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
                print(f"🗑️ Removed old backup: {f}")
        except Exception as e:
            print(f"⚠️ Error removing old backup {f}: {e}")

    return count


async def backup_loop():
    """Запускает бекап каждые 6 часов (4 раза в день)"""
    print(f"🗄️ DB Backup loop started (dir: {BACKUP_DIR}, retention: {RETENTION_DAYS}d)")
    while True:
        try:
            count = backup_db()
            print(f"📦 Backup completed: {count} files")
        except Exception as e:
            print(f"❌ Backup error: {e}")
            import traceback
            traceback.print_exc()
        await asyncio.sleep(6 * 3600)
