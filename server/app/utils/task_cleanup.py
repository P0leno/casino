import json
from app.utils.database import get_db_connection
from app.utils.redis_models import RedisUser
from app.utils.error_logger import send_error_log

async def remove_task_history(task_id: int):
    """
    Удаляет ID задания из истории выполненных у всех пользователей.
    Используется при удалении задания админом или достижении лимита.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Находим всех пользователей, у которых это задание в выполненных
        # Используем json_each для поиска внутри JSON массива
        try:
            cursor.execute("""
                SELECT users.id, users.completed_tasks 
                FROM users, json_each(users.completed_tasks) 
                WHERE json_each.value = ?
            """, (task_id,))
            rows = cursor.fetchall()
        except Exception as e:
            print(f"⚠️ json_each not supported or error: {e}. Falling back to full scan.")
            # Fallback: если json_each нет, сканируем всех (медленно, но работает)
            cursor.execute("SELECT id, completed_tasks FROM users")
            rows = []
            all_users = cursor.fetchall()
            for r in all_users:
                try:
                    ct = json.loads(r[1] or "[]")
                    if task_id in ct:
                        rows.append(r)
                except: pass

        print(f"🧹 Clearing task {task_id} history for {len(rows)} users")
        
        for row in rows:
            user_id = row[0]
            try:
                completed = json.loads(row[1] or "[]")
                # Приводим к int, так как в JSON могут быть смешанные типы иногда
                completed = [int(x) for x in completed]
                
                if task_id in completed:
                    completed = [x for x in completed if x != task_id]
                    
                    # Обновляем через RedisUser для синхронизации кэша
                    RedisUser.update(user_id, completed_tasks=completed)
            except Exception as e:
                print(f"Error clearing history for user {user_id}: {e}")
                
        conn.close()
    except Exception as e:
        print(f"Error in remove_task_history: {e}")
        await send_error_log(e, "tasks.py: remove_task_history")
