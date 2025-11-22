from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from urllib.parse import parse_qs
import json
import sqlite3
import aiohttp
from app.config import BOT_TOKEN, ADMIN_IDS, DB_PATH, CHECKER_BOT_TOKEN
from app.utils.validate import validate_init_data

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
        return ""

# Получить все задания (для админки)
@router.post("/admin/tasks/list")
async def get_all_tasks(request: ValidateRequest):
    admin_check, _ = is_admin(request.initData)
    if not admin_check:
        return {"valid": False, "tasks": []}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, target, type, award, currency FROM tasks")
        results = cursor.fetchall()
        conn.close()
        
        tasks = [{"id": r[0], "target": r[1], "type": r[2], "award": r[3], "currency": r[4]} for r in results]
        return {"valid": True, "tasks": tasks}
    except Exception as e:
        print(f"Error fetching tasks: {e}")
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
        
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (request.taskId,))
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Task deleted"}
    except Exception as e:
        print(f"Error deleting task: {e}")
        return {"success": False, "message": "Database error"}

# Получить invite link для частного канала
@router.post("/tasks/get-invite-link")
async def get_invite_link(request: GetInviteLinkRequest):
    user_id = get_user_id(request.initData)
    if user_id == 0:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        conn = sqlite3.connect(DB_PATH)
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
        return {"success": False, "message": "Database error"}

# Получить доступные задания для пользователя
@router.post("/tasks/available")
async def get_available_tasks(request: ValidateRequest):
    user_id = get_user_id(request.initData)
    if user_id == 0:
        return {"valid": False, "tasks": []}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получить выполненные задания пользователя
        cursor.execute("SELECT completed_tasks FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        completed_tasks = json.loads(result[0]) if result and result[0] else []
        
        # Получить все задания
        cursor.execute("SELECT id, target, type, award, currency FROM tasks")
        all_tasks = cursor.fetchall()
        conn.close()
        
        # Фильтровать невыполненные задания
        available = [
            {"id": t[0], "target": t[1], "type": t[2], "award": t[3], "currency": t[4]}
            for t in all_tasks if t[0] not in completed_tasks
        ]
        
        return {"valid": True, "tasks": available}
    except Exception as e:
        print(f"Error fetching available tasks: {e}")
        return {"valid": False, "tasks": []}

# Выполнить задание
@router.post("/tasks/complete")
async def complete_task(request: CompleteTaskRequest):
    user_id = get_user_id(request.initData)
    if user_id == 0:
        return {"success": False, "message": "Invalid initData"}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получить задание
        cursor.execute("SELECT target, type, award, currency FROM tasks WHERE id = ?", (request.taskId,))
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            return {"success": False, "message": "Task not found"}
        
        target, task_type, award, currency = task
        
        # Проверить не выполнено ли уже
        cursor.execute("SELECT completed_tasks FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        completed_tasks = json.loads(result[0]) if result and result[0] else []
        
        if request.taskId in completed_tasks:
            conn.close()
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
        
        # Выдать награду
        # star = balance, paws = bonus_balance
        if currency == "paws":
            cursor.execute("UPDATE users SET bonus_balance = bonus_balance + ? WHERE id = ?", (award, user_id))
        elif currency == "star":
            cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (award, user_id))
        
        # Отметить задание как выполненное
        completed_tasks.append(request.taskId)
        cursor.execute("UPDATE users SET completed_tasks = ? WHERE id = ?", (json.dumps(completed_tasks), user_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Task completed", "award": award, "currency": currency}
    except Exception as e:
        print(f"Error completing task: {e}")
        return {"success": False, "message": "Database error"}
