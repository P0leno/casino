from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from urllib.parse import parse_qs
import json
import aiohttp
from app.config import BOT_TOKEN, ADMIN_IDS, CHECKER_BOT_TOKEN
from app.utils.validate import validate_init_data
from app.utils.rate_limit import tasks_rate_limiter
from app.utils.balance import get_user_balance
from app.utils.redis_models import RedisUser
from app.utils.database import get_db_connection, DB_PATH
from app.utils.error_logger import send_error_log

router = APIRouter(prefix="/api", tags=["tasks"])

class ValidateRequest(BaseModel):
    initData: str

class CreateTaskRequest(BaseModel):
    initData: str
    target: str
    type: str
    award: int
    currency: str
    customInvite: Optional[str] = None

class DeleteTaskRequest(BaseModel):
    initData: str
    taskId: int

class CheckBotPermissionsRequest(BaseModel):
    initData: str
    channelUsername: str

class CompleteTaskRequest(BaseModel):
    initData: str
    taskId: int

class GetInviteLinkRequest(BaseModel):
    initData: str
    taskId: int

# Проверка является ли пользователь админом
def is_admin(init_data: str) -> tuple[bool, int]:
    is_valid = validate_init_data(init_data, BOT_TOKEN)
    if not is_valid:
        return False, 0
    
    try:
        parsed = parse_qs(init_data)
        user_data = parsed.get('user', [''])[0]
        if not user_data:
            return False, 0
        
        user = json.loads(user_data)
        user_id = user.get('id')
        
        if user_id not in ADMIN_IDS:
            return False, 0
        
        return True, user_id
    except Exception:
        return False, 0

# Получение user_id из initData
def get_user_id(init_data: str) -> int:
    is_valid = validate_init_data(init_data, BOT_TOKEN)
    if not is_valid:
        return 0
    
    try:
        parsed = parse_qs(init_data)
        user_data = parsed.get('user', [''])[0]
        if not user_data:
            return 0
        
        user = json.loads(user_data)
        return user.get('id', 0)
    except Exception:
        return 0

# Проверка прав бота в канале (публичный или частный)
async def check_bot_admin_rights(channel_identifier: str) -> bool:
    if not CHECKER_BOT_TOKEN:
        print("⚠️  CHECKER_BOT_TOKEN не установлен")
        return False
    
    try:
        # Получаем bot_id из токена
        bot_id = CHECKER_BOT_TOKEN.split(':')[0]
        
        # Определяем это ID или username
        chat_id = channel_identifier
        if not channel_identifier.startswith('-'):
            # Это username публичного канала
            chat_id = f"@{channel_identifier.lstrip('@')}"
        # Иначе это уже ID частного канала
        
        print(f"🔍 Проверка прав бота {bot_id} в канале {chat_id}")
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{CHECKER_BOT_TOKEN}/getChatMember"
            params = {
                "chat_id": chat_id,
                "user_id": bot_id
            }
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                data = await response.json()
                
                if data.get("ok"):
                    member = data.get("result", {})
                    status = member.get("status")
                    is_admin = status in ["administrator", "creator"]
                    print(f"✅ Статус бота в канале: {status}, Админ: {is_admin}")
                    return is_admin
                else:
                    error_desc = data.get("description", "Unknown error")
                    print(f"❌ Ошибка API Telegram: {error_desc}")
                    return False
    except Exception as e:
        print(f"❌ Error checking bot permissions: {e}")
        await send_error_log(e, "tasks.py: check_bot_admin_rights")
        return False

# Проверка подписки пользователя на канал (публичный или частный)
async def check_user_subscription(user_id: int, channel_identifier: str) -> bool:
    if not CHECKER_BOT_TOKEN:
        return False
    
    try:
        # Определяем это ID или username
        chat_id = channel_identifier
        if not channel_identifier.startswith('-'):
            # Это username публичного канала
            chat_id = f"@{channel_identifier.lstrip('@')}"
        # Иначе это уже ID частного канала
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{CHECKER_BOT_TOKEN}/getChatMember"
            params = {
                "chat_id": chat_id,
                "user_id": user_id
            }
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get("ok"):
                    member = data.get("result", {})
                    status = member.get("status")
                    # Даже если пользователь в бан-листе, он когда-то был участником
                    return status in ["member", "administrator", "creator", "restricted", "left", "kicked"]
                
                return False
    except Exception as e:
        print(f"Error checking user subscription: {e}")
        await send_error_log(e, "tasks.py: check_user_subscription")
        return False

# Получить invite link для частного канала
async def get_channel_invite_link(channel_id: str) -> str:
    if not CHECKER_BOT_TOKEN:
        return ""
    
    try:
        async with aiohttp.ClientSession() as session:
            # Сначала пробуем получить существующую ссылку
            url = f"https://api.telegram.org/bot{CHECKER_BOT_TOKEN}/exportChatInviteLink"
            params = {"chat_id": channel_id}
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get("ok"):
                    return data.get("result", "")
                
                return ""
    except Exception as e:
        print(f"Error getting invite link: {e}")
        await send_error_log(e, "tasks.py: get_channel_invite_link")
        return ""

# Получить все задания (для админки)
@router.post("/tasks/list")
async def get_tasks_list(request: ValidateRequest):
    """
    Универсальный эндпоинт для получения заданий:
    - Для админа: все задания
    - Для пользователя: только невыполненные
    """
    user_id = get_user_id(request.initData)
    if user_id == 0:
        return {"valid": False, "tasks": []}
    
    # Rate limiting: 5 запросов в 100 секунд (только для не-админов)
    admin_check, _ = is_admin(request.initData)
    if not admin_check:
        allowed, remaining_time = tasks_rate_limiter.is_allowed(user_id)
        if not allowed:
            return {
                "valid": False, 
                "error": f"Слишком частые запросы. Попробуйте через {remaining_time} секунд",
                "tasks": []
            }
    
    try:
        # Инвалидируем Redis кэш перед чтением чтобы гарантировать свежие данные
        RedisUser.invalidate(user_id)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if admin_check:
            # Админ видит все задания
            cursor.execute("SELECT id, target, type, award, currency FROM tasks")
            results = cursor.fetchall()
            conn.close()
            tasks = [{"id": r[0], "target": r[1], "type": r[2], "award": r[3], "currency": r[4]} for r in results]
        else:
            # КРИТИЧНО: Всегда берем completed_tasks из БД (источник истины)
            cursor.execute("SELECT completed_tasks FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                completed_tasks = json.loads(result[0] or "[]")
                print(f"[TASKS/LIST] User {user_id} completed_tasks from DB: {completed_tasks}")
            else:
                conn.close()
                return {"valid": False, "tasks": [], "error": "User not found"}
            
            cursor.execute("SELECT id, target, type, award, currency FROM tasks")
            all_tasks = cursor.fetchall()
            conn.close()
            
            # Приводим completed_tasks к int для корректного сравнения
            completed_ids = set(int(t) for t in completed_tasks)
            all_task_ids = [t[0] for t in all_tasks]
            
            print(f"[TASKS/LIST] All task IDs: {all_task_ids}, Completed IDs: {completed_ids}")
            
            tasks = [
                {"id": t[0], "target": t[1], "type": t[2], "award": t[3], "currency": t[4]}
                for t in all_tasks if t[0] not in completed_ids
            ]
            
            print(f"[TASKS/LIST] User {user_id} filtered tasks: {[t['id'] for t in tasks]}")
        
        return {"valid": True, "tasks": tasks}
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        await send_error_log(e, "tasks.py: get_tasks_list")
        return {"valid": False, "tasks": []}

# Проверить права бота в канале
@router.post("/admin/tasks/check-bot-permissions")
async def check_bot_permissions(request: CheckBotPermissionsRequest):
    admin_check, _ = is_admin(request.initData)
    if not admin_check:
        return {"valid": False, "hasPermissions": False}
    
    has_permissions = await check_bot_admin_rights(request.channelUsername)
    return {"valid": True, "hasPermissions": has_permissions}

# Создать задание
@router.post("/admin/tasks/create")
async def create_task(request: CreateTaskRequest):
    try:
        admin_check, _ = is_admin(request.initData)
        if not admin_check:
            return {"success": False, "message": "Not authorized"}
        
        # Проверка прав бота для типов subscribe и private_channel
        if request.type in ["subscribe", "private_channel"]:
            print(f"📝 Создание задания типа {request.type} для {request.target}")
            has_permissions = await check_bot_admin_rights(request.target)
            if not has_permissions:
                print(f"⚠️  Бот не имеет прав администратора в канале {request.target}")
                return {"success": False, "message": "Bot doesn't have admin rights in this channel"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (target, type, award, currency, custom_invite) VALUES (?, ?, ?, ?, ?)",
            (request.target, request.type, request.award, request.currency, request.customInvite)
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        
        print(f"✅ Задание создано: ID={task_id}, type={request.type}, target={request.target}")
        return {"success": True, "message": "Task created", "taskId": task_id}
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        await send_error_log(e, "tasks.py: create_task")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"Error: {str(e)}"}

# Удалить задание
@router.post("/admin/tasks/delete")
async def delete_task(request: DeleteTaskRequest):
    admin_check, _ = is_admin(request.initData)
    if not admin_check:
        return {"success": False, "message": "Not authorized"}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (request.taskId,))
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Task deleted"}
    except Exception as e:
        print(f"Error deleting task: {e}")
        await send_error_log(e, "tasks.py: delete_task")
        return {"success": False, "message": "Database error"}

# Получить invite link для частного канала
@router.post("/tasks/get-invite-link")
async def get_invite_link(request: GetInviteLinkRequest):
    user_id = get_user_id(request.initData)
    if user_id == 0:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получить задание
        cursor.execute("SELECT target, type, custom_invite FROM tasks WHERE id = ?", (request.taskId,))
        task = cursor.fetchone()
        conn.close()
        
        if not task:
            return {"success": False, "message": "Task not found"}
        
        target, task_type, custom_invite = task
        
        if task_type != "private_channel":
            return {"success": False, "message": "This task is not for private channel"}
        
        # Если есть кастомная ссылка - используем её
        if custom_invite:
            return {"success": True, "inviteLink": custom_invite}
        
        # Иначе получаем через API
        invite_link = await get_channel_invite_link(target)
        
        if not invite_link:
            return {"success": False, "message": "Could not get invite link"}
        
        return {"success": True, "inviteLink": invite_link}
    except Exception as e:
        print(f"Error getting invite link: {e}")
        await send_error_log(e, "tasks.py: get_invite_link")
        return {"success": False, "message": "Database error"}



# Выполнить задание
@router.post("/tasks/complete")
async def complete_task(request: CompleteTaskRequest):
    user_id = get_user_id(request.initData)
    if user_id == 0:
        return {"success": False, "message": "Invalid initData"}
    
    # Rate limiting: 5 запросов в 100 секунд
    allowed, remaining_time = tasks_rate_limiter.is_allowed(user_id)
    if not allowed:
        return {
            "success": False, 
            "message": f"Слишком частые запросы. Попробуйте через {remaining_time} секунд"
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получить задание
        cursor.execute("SELECT target, type, award, currency FROM tasks WHERE id = ?", (request.taskId,))
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            return {"success": False, "message": "Task not found"}
        
        target, task_type, award, currency = task
        
        # Проверяем есть ли пользователь в БД, если нет - создаем
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            print(f"[TASKS] ⚠️ User {user_id} not in DB, creating...")
            
            # КРИТИЧНО: Сначала удаляем старый кэш (если был)
            from app.utils.redis_client import cache
            deleted = cache.delete(f"user:{user_id}")
            print(f"[TASKS] 🗑️ Invalidated old cache for user {user_id}, deleted: {deleted}")
            
            from datetime import datetime
            cursor.execute("""
                INSERT INTO users (id, user_id, username, creation_date, balance, bonus_balance, inventory, completed_tasks, activated_promocodes)
                VALUES (?, ?, '', ?, 0, 0, '[]', '[]', '[]')
            """, (user_id, user_id, datetime.now().isoformat()))
            conn.commit()
            print(f"[TASKS] ✅ User {user_id} created in DB with empty completed_tasks")
        
        # Получаем пользователя через Redis (после создания он точно есть в БД)
        user = RedisUser.get(user_id)
        if not user:
            conn.close()
            print(f"[TASKS] ❌ User {user_id} not found in Redis/DB even after creation")
            return {"success": False, "message": "User not found"}
        
        completed_tasks = user.get('completed_tasks', [])
        
        print(f"[TASKS] User {user_id} trying to complete task {request.taskId} (type: {type(request.taskId).__name__})")
        print(f"[TASKS] User from Redis: balance={user.get('balance')}, bonus_balance={user.get('bonus_balance')}")
        print(f"[TASKS] Completed tasks from Redis: {completed_tasks}")
        print(f"[TASKS] Completed tasks types: {[type(t).__name__ for t in completed_tasks]}")
        print(f"[TASKS] Check: {request.taskId} in {completed_tasks} = {request.taskId in completed_tasks}")
        
        # Дополнительная проверка: сверяем с БД
        cursor.execute("SELECT completed_tasks FROM users WHERE id = ?", (user_id,))
        db_row = cursor.fetchone()
        if db_row:
            db_completed = json.loads(db_row[0] or "[]")
            print(f"[TASKS] 🔍 DB verification: completed_tasks = {db_completed}")
            if db_completed != completed_tasks:
                print(f"[TASKS] ⚠️ WARNING: Redis and DB are out of sync!")
                print(f"[TASKS] ⚠️ Redis: {completed_tasks}")
                print(f"[TASKS] ⚠️ DB: {db_completed}")
                # Используем данные из БД как источник истины
                completed_tasks = db_completed
                print(f"[TASKS] ✅ Using DB data as source of truth")
        
        if request.taskId in completed_tasks:
            conn.close()
            print(f"[TASKS] ⚠️ Task {request.taskId} already completed by user {user_id}")
            return {"success": False, "message": "Task already completed"}
        
        # Проверка выполнения в зависимости от типа
        if task_type in ["subscribe", "private_channel"]:
            # Проверить подписку через бота - был ли пользователь когда-либо участником
            is_subscribed = await check_user_subscription(user_id, target)
            if not is_subscribed:
                conn.close()
                # Не выводим ошибку, просто возвращаем false без сообщения
                return {"success": False}
        
        # Для open_url не требуется проверка, сразу выдаем награду
        
        # Получаем текущий баланс из БД
        cursor.execute("SELECT balance, bonus_balance FROM users WHERE id = ?", (user_id,))
        balance_row = cursor.fetchone()
        current_balance = balance_row[0] if balance_row else 0
        current_bonus = balance_row[1] if balance_row else 0
        
        conn.close()
        
        # Отметить задание как выполненное (как int!)
        completed_tasks.append(int(request.taskId))
        
        # Вычисляем новый баланс
        new_balance = current_balance + (award if currency == "star" else 0)
        new_bonus = current_bonus + (award if currency == "paws" else 0)
        
        # Обновляем через RedisUser (автоматически синхронизирует БД и Redis)
        print(f"[TASKS] Updating user {user_id}: completed_tasks={completed_tasks}, balance={new_balance}, bonus_balance={new_bonus}")
        success = RedisUser.update(
            user_id,
            completed_tasks=completed_tasks,
            balance=new_balance,
            bonus_balance=new_bonus
        )
        
        if not success:
            print(f"[TASKS] ❌ Failed to update user {user_id} in DB!")
            return {"success": False, "message": "Failed to update user - user not found in database"}
        
        # Явно инвалидируем кэш для гарантии синхронизации
        RedisUser.invalidate(user_id)
        
        print(f"[TASKS] ✅ Task {request.taskId} completed by user {user_id}, new completed_tasks: {completed_tasks}")
        
        # Проверяем что данные действительно обновились в Redis
        user_check = RedisUser.get(user_id)
        if user_check:
            print(f"[TASKS] 🔍 Verification: Redis completed_tasks = {user_check.get('completed_tasks', [])}")
        
        # Получаем обновленный баланс
        user_balance = get_user_balance(user_id)
        
        return {
            "success": True, 
            "message": "Task completed", 
            "award": award, 
            "currency": currency,
            **user_balance
        }
    except Exception as e:
        print(f"Error completing task: {e}")
        await send_error_log(e, "tasks.py: complete_task")
        return {"success": False, "message": "Database error"}
