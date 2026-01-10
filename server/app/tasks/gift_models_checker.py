"""
Мониторинг и синхронизация моделей подарков из Telegram Gift API
"""
import os
import asyncio
from app.utils.database import get_db_connection, DB_PATH
import sqlite3
import json
from datetime import datetime
import aiohttp
from app.config import DB_PATH, LOG_BOT_TOKEN, LOGS_ID
from app.utils.error_logger import send_error_log

BASE_API = "https://api.changes.tg"
MODELS_DIR = "/var/www/shell/gifts/models"
MODELS_LIST_JSON = "/var/www/shell/gifts/models_list.json"

async def send_log_to_channel(message, reply_markup=None):
    """Отправляет сообщение в канал логов через постоянный log_bot"""
    if not LOG_BOT_TOKEN or not LOGS_ID:
        return
    
    try:
        from app.log_bot import send_message_to_logs
        await send_message_to_logs(message, reply_markup=reply_markup)
    except Exception as e:
        print(f"⚠️  Не удалось отправить лог в канал: {e}")

def init_gift_models_table():
    """Создаёт таблицу gift_models если её нет"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gift_models (
                gift_name TEXT PRIMARY KEY,
                models TEXT NOT NULL,
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                folder_exists INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Таблица gift_models готова")
    except Exception as e:
        print(f"❌ Ошибка создания таблицы gift_models: {e}")

def scan_local_gifts():
    """Сканирует локальную папку /var/www/shell/gifts/models"""
    if not os.path.exists(MODELS_DIR):
        print(f"⚠️  Папка {MODELS_DIR} не существует")
        return {}
    
    gifts_data = {}
    
    for gift_folder in os.listdir(MODELS_DIR):
        folder_path = os.path.join(MODELS_DIR, gift_folder)
        if os.path.isdir(folder_path):
            # Получаем список .json файлов (моделей)
            models = [f.replace(".json", "") for f in os.listdir(folder_path) if f.endswith(".json")]
            if models:
                gifts_data[gift_folder] = models
                print(f"  📦 {gift_folder}: {len(models)} моделей")
    
    return gifts_data

async def update_models_list_json():
    """Обновляет /var/www/shell/gifts/models_list.json на основе локальных папок"""
    try:
        gifts_data = {}
        
        if os.path.exists(MODELS_DIR):
            for gift_folder in os.listdir(MODELS_DIR):
                folder_path = os.path.join(MODELS_DIR, gift_folder)
                if os.path.isdir(folder_path):
                    # Получаем список .json файлов
                    models = sorted([f.replace(".json", "") for f in os.listdir(folder_path) if f.endswith(".json")])
                    if models:
                        gifts_data[gift_folder] = {
                            "models": models,
                            "count": len(models)
                        }
        
        # Записываем в JSON
        with open(MODELS_LIST_JSON, 'w', encoding='utf-8') as f:
            json.dump(gifts_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Файл {MODELS_LIST_JSON} обновлен ({len(gifts_data)} подарков)")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления models_list.json: {e}")
        return False

async def sync_folders_with_json():
    """Проверяет и синхронизирует папки с моделями и JSON при старте"""
    print("🔄 Проверка синхронизации models_list.json...")
    
    try:
        if not os.path.exists(MODELS_DIR):
            print(f"  ⚠️  Папка {MODELS_DIR} не существует, создаю...")
            os.makedirs(MODELS_DIR, exist_ok=True)
            # Создаём пустой JSON
            with open(MODELS_LIST_JSON, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            print(f"  ✅ Создан пустой {MODELS_LIST_JSON}")
            return
        
        # Сканируем локальные папки
        local_gifts = {}
        for gift_folder in os.listdir(MODELS_DIR):
            folder_path = os.path.join(MODELS_DIR, gift_folder)
            if os.path.isdir(folder_path):
                models = sorted([f.replace(".json", "") for f in os.listdir(folder_path) if f.endswith(".json")])
                if models:
                    local_gifts[gift_folder] = models
        
        print(f"  📂 Найдено папок с моделями: {len(local_gifts)}")
        
        # Читаем текущий JSON если существует
        existing_json = {}
        json_gifts_count = 0
        if os.path.exists(MODELS_LIST_JSON):
            with open(MODELS_LIST_JSON, 'r', encoding='utf-8') as f:
                existing_json = json.load(f)
            json_gifts_count = len(existing_json)
        
        print(f"  📄 Подарков в JSON: {json_gifts_count}")
        
        # Проверяем расхождения
        needs_update = False
        new_gifts = []
        changed_gifts = []
        
        # Проверяем что все папки есть в JSON
        for gift_name, models in local_gifts.items():
            if gift_name not in existing_json:
                new_gifts.append(gift_name)
                needs_update = True
            else:
                # Поддержка старого формата (массив) и нового (объект)
                json_models = existing_json[gift_name]
                try:
                    if isinstance(json_models, list):
                        # Старый формат - просто массив моделей
                        if set(models) != set(json_models):
                            changed_gifts.append(gift_name)
                            needs_update = True
                    elif isinstance(json_models, dict):
                        # Новый формат - объект с "models" и "count"
                        if set(models) != set(json_models.get("models", [])):
                            changed_gifts.append(gift_name)
                            needs_update = True
                    else:
                        print(f"  ⚠️  Неизвестный формат для '{gift_name}', обновляю")
                        needs_update = True
                except Exception as e:
                    print(f"  ⚠️  Ошибка сравнения '{gift_name}': {e}, обновляю")
                    needs_update = True
        
        # Также обновляем если JSON пустой, а папки есть
        if not existing_json and local_gifts:
            print(f"  ℹ️  JSON пустой, но найдено {len(local_gifts)} папок")
            needs_update = True
        
        # Выводим детали
        if new_gifts:
            print(f"  🆕 Новых подарков: {len(new_gifts)}")
            for gift in new_gifts[:5]:
                print(f"     • {gift}")
            if len(new_gifts) > 5:
                print(f"     ... и еще {len(new_gifts) - 5}")
        
        if changed_gifts:
            print(f"  🔄 Изменённых подарков: {len(changed_gifts)}")
            for gift in changed_gifts[:3]:
                print(f"     • {gift}")
            if len(changed_gifts) > 3:
                print(f"     ... и еще {len(changed_gifts) - 3}")
        
        if needs_update:
            print("  🔄 Обновляю models_list.json...")
            success = await update_models_list_json()
            if success:
                print("  ✅ Синхронизация завершена успешно")
            else:
                print("  ⚠️  Синхронизация завершена с ошибками")
        else:
            print("  ✅ models_list.json актуален, обновление не требуется")
    
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")
        import traceback
        traceback.print_exc()
        # Пытаемся принудительно обновить JSON
        print("  🔄 Попытка принудительного обновления...")
        try:
            await update_models_list_json()
        except Exception as e2:
            print(f"  ❌ Принудительное обновление не удалось: {e2}")

async def fetch_json(session, url):
    """Получает JSON с API"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                print(f"⚠️  Ошибка {resp.status}: {url}")
                return None
            return await resp.json()
    except Exception as e:
        print(f"❌ Ошибка запроса {url}: {e}")
        return None

async def download_file(session, url, path):
    """Скачивает файл"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status != 200:
                print(f"⚠️  Ошибка {resp.status} при скачивании {url}")
                return False

            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024):
                    f.write(chunk)
            
            return True
    except Exception as e:
        print(f"❌ Ошибка скачивания {url}: {e}")
        return False

async def check_new_gifts():
    """Проверяет наличие новых подарков в API"""
    print("=" * 80)
    print(f"🔍 ПРОВЕРКА НОВЫХ ПОДАРКОВ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        try:
            # Получаем список подарков из API
            print("📡 Запрос списка подарков из API...")
            api_gifts = await fetch_json(session, f"{BASE_API}/gifts")
            
            if not api_gifts:
                print("⚠️  Не удалось получить список подарков из API")
                return
            
            print(f"✅ Получено подарков из API: {len(api_gifts)}")
            
            # Получаем подарки из БД
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT gift_name, models FROM gift_models")
            db_gifts = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
            
            print(f"📊 Подарков в БД: {len(db_gifts)}")
            
            # Находим новые подарки
            new_gifts = set(api_gifts) - set(db_gifts.keys())
            
            if not new_gifts:
                print("✅ Новых подарков не найдено")
                conn.close()
                return
            
            print(f"🆕 Найдено новых подарков: {len(new_gifts)}")
            
            # Обрабатываем каждый новый подарок
            for gift_name in new_gifts:
                print(f"\n→ Обрабатываю новый подарок: {gift_name}")
                
                # Получаем модели для подарка
                models_data = await fetch_json(session, f"{BASE_API}/models/{gift_name}?sorted")
                
                if not models_data:
                    print(f"  ⚠️  Модели не найдены для {gift_name}")
                    continue
                
                model_names = [m["name"] for m in models_data]
                print(f"  📦 Моделей найдено: {len(model_names)}")
                
                # Сохраняем в БД
                cursor.execute(
                    "INSERT OR REPLACE INTO gift_models (gift_name, models, last_check, folder_exists) VALUES (?, ?, CURRENT_TIMESTAMP, 0)",
                    (gift_name, json.dumps(model_names))
                )
                conn.commit()
                
                # Формируем сообщение для логов
                message = f"🆕 <b>В API появился новый подарок</b>\n\n"
                message += f"<b>Название:</b> {gift_name}\n"
                message += f"<b>Моделей:</b> {len(model_names)}\n\n"
                
                # Добавляем список моделей
                max_models_in_message = 20
                models_list = model_names[:max_models_in_message]
                
                message += "<blockquote>"
                for model in models_list:
                    message += f"• {model}\n"
                
                if len(model_names) > max_models_in_message:
                    message += f"\n<i>и еще {len(model_names) - max_models_in_message}</i>"
                message += "</blockquote>\n\n"
                message += "Хотите обновить папку с моделями?"
                
                # Создаём кнопки
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Принять", callback_data=f"download_models:{gift_name}"),
                        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_models:{gift_name}")
                    ]
                ])
                
                await send_log_to_channel(message, reply_markup=keyboard)
                print(f"  📨 Отправлено уведомление в логи")
            
            conn.close()
            print("\n" + "=" * 80)
            print("✅ Проверка завершена")
            print("=" * 80)
        finally:
            pass  # Session closed automatically by async with

async def download_gift_models(gift_name, message_to_edit=None):
    """Скачивает модели для подарка с прогрессом"""
    print(f"📥 Начинаю загрузку моделей для {gift_name}...")
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        # Получаем список моделей
        models_data = await fetch_json(session, f"{BASE_API}/models/{gift_name}?sorted")
        
        if not models_data:
            print(f"❌ Не удалось получить модели для {gift_name}")
            return False
        
        total_models = len(models_data)
        
        # Создаём папку для подарка
        gift_folder = os.path.join(MODELS_DIR, gift_name)
        os.makedirs(gift_folder, exist_ok=True)
        print(f"📁 Папка создана: {gift_folder}")
        
        success_count = 0
        failed_count = 0
        last_progress_update = 0
        
        for i, model in enumerate(models_data):
            model_name = model["name"]
            safe_name = model_name.replace("/", "_")
            out_path = os.path.join(gift_folder, f"{safe_name}.json")
            url = f"{BASE_API}/model/{gift_name}/{model_name}.json"
            
            print(f"  ↓ Скачиваю [{i+1}/{total_models}]: {model_name}")
            
            if await download_file(session, url, out_path):
                success_count += 1
            else:
                failed_count += 1
            
            # Обновляем прогресс каждые 5 моделей
            if message_to_edit and (i + 1 - last_progress_update >= 5 or i + 1 == total_models):
                try:
                    from aiogram import Bot
                    progress_text = f"⏳ <b>Загружаю модели...</b> [{i+1}/{total_models}]"
                    await message_to_edit.edit_text(
                        f"{message_to_edit.text.split('⏳')[0].strip()}\n\n{progress_text}",
                        parse_mode="HTML"
                    )
                    last_progress_update = i + 1
                except Exception as e:
                    print(f"⚠️  Не удалось обновить прогресс: {e}")
            
            # Небольшая задержка между запросами
            await asyncio.sleep(0.5)
        
        # Обновляем БД
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE gift_models SET folder_exists = 1, last_check = CURRENT_TIMESTAMP WHERE gift_name = ?",
            (gift_name,)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Загрузка завершена: {success_count} успешно, {failed_count} ошибок")
        
        # Обновляем models_list.json
        await update_models_list_json()
        
        return failed_count == 0

async def verify_gift_folders():
    """Проверяет целостность папок с моделями"""
    print("🔍 Проверка целостности папок с моделями...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT gift_name, models, folder_exists FROM gift_models")
    gifts = cursor.fetchall()
    
    issues = []
    
    for gift_name, models_json, folder_exists in gifts:
        expected_models = json.loads(models_json)
        gift_folder = os.path.join(MODELS_DIR, gift_name)
        
        if not os.path.exists(gift_folder):
            issues.append(f"❌ {gift_name}: папка не существует")
            cursor.execute("UPDATE gift_models SET folder_exists = 0 WHERE gift_name = ?", (gift_name,))
            continue
        
        # Проверяем наличие всех моделей
        existing_models = [f.replace(".json", "").replace("_", "/") 
                          for f in os.listdir(gift_folder) if f.endswith(".json")]
        
        missing = set(expected_models) - set(existing_models)
        
        if missing:
            issues.append(f"⚠️  {gift_name}: отсутствует {len(missing)} моделей")
            cursor.execute("UPDATE gift_models SET folder_exists = 0 WHERE gift_name = ?", (gift_name,))
        else:
            cursor.execute("UPDATE gift_models SET folder_exists = 1 WHERE gift_name = ?", (gift_name,))
    
    conn.commit()
    conn.close()
    
    if issues:
        print("⚠️  Найдены проблемы:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ Все папки в порядке")

async def init_from_local_folder():
    """Инициализирует БД из локальной папки (если БД пустая)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM gift_models")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"ℹ️  В БД уже есть {count} подарков, пропускаю инициализацию")
        conn.close()
        return
    
    print("📂 Инициализация БД из локальной папки...")
    
    local_gifts = scan_local_gifts()
    
    if not local_gifts:
        print("ℹ️  Локальная папка пустая")
        conn.close()
        return
    
    for gift_name, models in local_gifts.items():
        cursor.execute(
            "INSERT OR IGNORE INTO gift_models (gift_name, models, last_check, folder_exists) VALUES (?, ?, CURRENT_TIMESTAMP, 1)",
            (gift_name, json.dumps(models))
        )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Добавлено {len(local_gifts)} подарков из локальной папки")

async def gift_models_checker_loop():
    """Основной цикл проверки (каждый час)"""
    # Инициализация
    init_gift_models_table()
    
    # При старте проверяем локальную папку
    try:
        await init_from_local_folder()
    except Exception as e:
        print(f"❌ Ошибка init_from_local_folder: {e}")
        import traceback
        traceback.print_exc()
    
    # Синхронизируем models_list.json с локальными папками
    try:
        await sync_folders_with_json()
    except Exception as e:
        print(f"❌ Ошибка sync_folders_with_json: {e}")
        await send_error_log(e, "gift_models_checker.py: startup sync_folders_with_json")
        import traceback
        traceback.print_exc()
    
    # Проверяем целостность
    try:
        await verify_gift_folders()
    except Exception as e:
        print(f"❌ Ошибка verify_gift_folders: {e}")
        import traceback
        traceback.print_exc()
    
    # Первая проверка сразу
    try:
        await check_new_gifts()
    except Exception as e:
        print(f"❌ Ошибка check_new_gifts при старте: {e}")
        await send_error_log(e, "gift_models_checker.py: startup check_new_gifts")
        import traceback
        traceback.print_exc()
    
    # Цикл проверки каждый час
    while True:
        await asyncio.sleep(3600)  # 1 час
        
        try:
            await check_new_gifts()
            await verify_gift_folders()
        except Exception as e:
            print(f"❌ Ошибка в gift_models_checker_loop: {e}")
            await send_error_log(e, "gift_models_checker.py: gift_models_checker_loop")
            import traceback
            traceback.print_exc()

# Для ручного запуска
if __name__ == "__main__":
    asyncio.run(gift_models_checker_loop())
