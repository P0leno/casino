"""
Фоновая задача для парсинга подарков из Telegram
"""
import asyncio
import sqlite3
import os
from app.config import API_ID, API_HASH, SESSION_STRING, LOG_BOT_TOKEN, LOGS_ID, ADMIN_IDS

DB_PATH = os.getenv("DB_PATH", "./users.db")

async def send_log_to_channel(message):
    """Отправляет сообщение в канал логов через постоянный log_bot"""
    if not LOG_BOT_TOKEN or not LOGS_ID:
        return
    
    try:
        from app.log_bot import send_message_to_logs
        await send_message_to_logs(message)
    except Exception as e:
        print(f"⚠️  Не удалось отправить лог в канал: {e}")

async def send_log_to_channel_with_button(message):
    """Отправляет сообщение в канал логов с кнопкой принудительного парсинга через постоянный log_bot"""
    if not LOG_BOT_TOKEN or not LOGS_ID:
        return
    
    try:
        from app.log_bot import send_message_to_logs
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Создаем кнопку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Принудительный парсинг", callback_data="force_gift_parse")]
        ])
        
        await send_message_to_logs(message, reply_markup=keyboard)
    except Exception as e:
        print(f"⚠️  Не удалось отправить лог в канал: {e}")

def int_to_hex_color(color_int):
    """Конвертирует integer в hex цвет"""
    if color_int is None:
        return None
    return f"#{color_int:06x}"

def init_gifts_table():
    """Проверяет таблицу подарков (создается в init_db)"""
    # Таблица создается в app.database.db.init_db()
    pass

async def parse_gift_attributes_with_retry(app, gift, max_retries=10):
    """
    Парсит атрибуты подарка с retry логикой.
    Если backdrop не найден, пробует повторно до max_retries раз.
    Возвращает dict с атрибутами или None если не удалось распарсить backdrop.
    """
    for attempt in range(max_retries):
        try:
            model_name = None
            model_path = None
            symbol_name = None
            backdrop_name = None
            center_color = None
            edge_color = None
            pattern_color = None
            text_color = None
            rarity_model = None
            rarity_symbol = None
            rarity_backdrop = None
            
            # Парсим attributes
            if hasattr(gift, 'attributes') and gift.attributes:
                for attr in gift.attributes:
                    # Преобразуем в dict, обрабатываем вложенные объекты
                    if hasattr(attr, '__dict__'):
                        attr_dict = attr.__dict__
                    elif isinstance(attr, dict):
                        attr_dict = attr
                    else:
                        continue
                
                    attr_name = attr_dict.get('name', '')
                    attr_type = str(attr_dict.get('type', ''))
                
                    # MODEL type
                    if 'MODEL' in attr_type or (hasattr(attr, 'sticker') and hasattr(attr, 'name') and not hasattr(attr, 'center_color')):
                        model_name = attr_name
                        rarity_model = attr_dict.get('rarity', 0)
                        # Формируем путь к анимации
                        if model_name:
                            model_path = f"/gifts/models/{gift.title}/{model_name}.json"
                
                    # SYMBOL type
                    elif 'SYMBOL' in attr_type:
                        symbol_name = attr_name
                        rarity_symbol = attr_dict.get('rarity', 0)
                
                    # BACKDROP type - определяем по наличию center_color
                    elif hasattr(attr, 'center_color') or 'BACKDROP' in attr_type:
                        backdrop_name = attr_name
                        rarity_backdrop = attr_dict.get('rarity', 0)
                    
                        # Конвертируем цвета (с проверкой на None)
                        if hasattr(attr, 'center_color') and attr.center_color is not None:
                            center_color = int_to_hex_color(attr.center_color)
                        if hasattr(attr, 'edge_color') and attr.edge_color is not None:
                            edge_color = int_to_hex_color(attr.edge_color)
                        if hasattr(attr, 'pattern_color') and attr.pattern_color is not None:
                            pattern_color = int_to_hex_color(attr.pattern_color)
                        if hasattr(attr, 'text_color') and attr.text_color is not None:
                            text_color = int_to_hex_color(attr.text_color)
            
            # Проверяем что backdrop найден
            if backdrop_name:
                return {
                    'model_name': model_name,
                    'model_path': model_path,
                    'symbol_name': symbol_name,
                    'backdrop_name': backdrop_name,
                    'center_color': center_color,
                    'edge_color': edge_color,
                    'pattern_color': pattern_color,
                    'text_color': text_color,
                    'rarity_model': rarity_model,
                    'rarity_symbol': rarity_symbol,
                    'rarity_backdrop': rarity_backdrop
                }
            
            # Backdrop не найден - пробуем снова
            if attempt < max_retries - 1:
                print(f"⚠️  Попытка {attempt + 1}/{max_retries}: backdrop не найден для {gift.title} ({gift.id}), повтор через 0.5 сек...")
                await asyncio.sleep(0.5)
                # Пробуем перезапросить gift
                try:
                    gifts_list = []
                    async for g in app.get_chat_gifts(chat_id=(await app.get_me()).id, exclude_unlimited=True):
                        if str(g.id) == str(gift.id):
                            gift = g
                            break
                except Exception as e:
                    print(f"⚠️  Ошибка при повторном запросе gift: {e}")
        
        except Exception as e:
            print(f"⚠️  Ошибка парсинга атрибутов (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5)
    
    # После всех попыток backdrop не найден
    print(f"❌ Не удалось распарсить backdrop для {gift.title} ({gift.id}) после {max_retries} попыток - подарок НЕ сохранен")
    return None

async def parse_gifts(send_log=True):
    """Парсит подарки из Telegram и сохраняет в БД"""
    if not SESSION_STRING or not API_ID or not API_HASH:
        print("⚠️  Нет credentials для парсинга подарков")
        if send_log:
            await send_log_to_channel("⚠️ <b>Gift Parser</b>\nНет credentials для парсинга подарков")
        return
    
    # Импортируем pyrogram только здесь, чтобы избежать конфликта с event loop при импорте модуля
    try:
        from pyrogram import Client
    except Exception as e:
        print(f"⚠️  Не удалось импортировать pyrogram: {e}")
        return
    
    # Используем no_updates=True для избежания ошибок с закрытой БД
    app = Client(
        "gift_parser",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True,
        no_updates=True  # Отключаем обновления для избежания ошибок с БД
    )
    
    try:
        await app.start()
        me = await app.get_me()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        gifts_count = 0
        skipped_count = 0
        
        try:
            # Получаем подарки с аккаунта (с полной информацией: title, attributes, transfer_price)
            # exclude_unlimited=True - только LIMITED подарки
            async for gift in app.get_chat_gifts(
                chat_id=me.id,
                exclude_unlimited=True
            ):
                # ВАЖНО: Сохраняем только подарки с transfer_price (LIMITED NFT, которые можно перепродать)
                transfer_price = getattr(gift, 'transfer_price', None)
                
                if not transfer_price:
                    # Игнорируем подарки без возможности перепродажи
                    skipped_count += 1
                    continue
                
                gifts_count += 1
            
                # Извлекаем данные
                gift_id = str(gift.id)
                slug = getattr(gift, 'name', None)  # HappyBrownie-95259
                title = gift.title
                
                # Парсим attributes с retry логикой (до 10 попыток)
                attrs = await parse_gift_attributes_with_retry(app, gift, max_retries=10)
                
                # Если не удалось распарсить backdrop - НЕ сохраняем подарок
                if attrs is None:
                    skipped_count += 1
                    continue
                
                # Извлекаем распарсенные атрибуты
                model_name = attrs['model_name']
                model_path = attrs['model_path']
                symbol_name = attrs['symbol_name']
                backdrop_name = attrs['backdrop_name']
                center_color = attrs['center_color']
                edge_color = attrs['edge_color']
                pattern_color = attrs['pattern_color']
                text_color = attrs['text_color']
                rarity_model = attrs['rarity_model']
                rarity_symbol = attrs['rarity_symbol']
                rarity_backdrop = attrs['rarity_backdrop']
            
                available_amount = getattr(gift, 'available_amount', 0)
                total_amount = getattr(gift, 'total_amount', 0)
                # Цена теперь обновляется через price_updater.py (каждый час с Tonnel)
            
                # Сохраняем в БД (БЕЗ изменения price - он обновляется отдельно)
                # Проверяем существует ли подарок
                cursor.execute("SELECT id, price FROM shop_gifts WHERE gift_id = ?", (gift_id,))
                existing = cursor.fetchone()
            
                if existing:
                    # Обновляем все кроме price
                    cursor.execute("""
                        UPDATE shop_gifts SET
                            slug = ?, title = ?, model_name = ?, model_path = ?,
                            symbol_name = ?, backdrop_name = ?,
                            center_color = ?, edge_color = ?, pattern_color = ?, text_color = ?,
                            available_amount = ?, total_amount = ?,
                            rarity_model = ?, rarity_symbol = ?, rarity_backdrop = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE gift_id = ?
                    """, (
                        slug, title, model_name, model_path, symbol_name, backdrop_name,
                        center_color, edge_color, pattern_color, text_color,
                        available_amount, total_amount,
                        rarity_model, rarity_symbol, rarity_backdrop,
                        gift_id
                    ))
                else:
                    # Новый подарок - вставляем с price = 0 (будет обновлен price_updater)
                    cursor.execute("""
                        INSERT INTO shop_gifts 
                        (gift_id, slug, title, model_name, model_path, symbol_name, backdrop_name,
                         center_color, edge_color, pattern_color, text_color,
                         available_amount, total_amount, price,
                         rarity_model, rarity_symbol, rarity_backdrop, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        gift_id, slug, title, model_name, model_path, symbol_name, backdrop_name,
                        center_color, edge_color, pattern_color, text_color,
                        available_amount, total_amount,
                        rarity_model, rarity_symbol, rarity_backdrop
                    ))
        except (AttributeError, ConnectionError) as e:
            # Pyrogram connection lost during iteration
            print(f"⚠️  Pyrogram connection lost: {e}")
        
        conn.commit()
        conn.close()
        
        total_received = gifts_count + skipped_count
        print(f"📊 Получено из Telegram: {total_received}, обработано: {gifts_count}, пропущено: {skipped_count}")
        
        if gifts_count > 0:
            if send_log:
                print(f"✅ Обновлено подарков в магазине: {gifts_count}")
                if skipped_count > 0:
                    print(f"⏭️  Пропущено подарков без transfer_price: {skipped_count}")
                
                message = f"✅ <b>Gift Parser</b>\nОбновлено подарков: <b>{gifts_count}</b>"
                if skipped_count > 0:
                    message += f"\nПропущено: {skipped_count} шт (без transfer_price + без backdrop)"
                await send_log_to_channel_with_button(message)
            else:
                # При старте - краткий лог
                if skipped_count > 0:
                    print(f"⏭️  Пропущено подарков без transfer_price: {skipped_count}")
        else:
            if send_log:
                print("ℹ️  Нет новых подарков для обновления")
                if skipped_count > 0:
                    print(f"⏭️  Пропущено подарков без transfer_price: {skipped_count}")
                
                message = "ℹ️ <b>Gift Parser</b>\nНет новых подарков для обновления"
                if skipped_count > 0:
                    message += f"\nПропущено: {skipped_count} шт (без transfer_price + без backdrop)"
                await send_log_to_channel_with_button(message)
        
        return {"updated": gifts_count, "skipped": skipped_count}
        
    except Exception as e:
        error_message = f"❌ <b>Gift Parser Error</b>\n\n<code>{str(e)}</code>"
        print(f"❌ Ошибка парсинга подарков: {e}")
        import traceback
        traceback.print_exc()
        if send_log:
            await send_log_to_channel(error_message)
        return {"updated": 0, "skipped": 0}
    
    finally:
        try:
            if app.is_connected:
                await app.stop()
        except Exception as e:
            print(f"⚠️  Ошибка при остановке Pyrogram: {e}")

async def force_parse_and_sync(search_tonnel_resale_func, update_gift_ton_price_func):
    """Обновление цен через Tonnel для существующих подарков"""
    if not SESSION_STRING or not API_ID or not API_HASH:
        return {"prices_updated": 0}
    
    prices_updated = 0
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем все подарки из БД для обновления цен
        cursor.execute("SELECT gift_id, title, model_name, backdrop_name FROM shop_gifts")
        gifts = cursor.fetchall()
        
        print(f"💰 Обновление цен для {len(gifts)} подарков...")
        
        # Обновляем цены через Tonnel для каждого подарка
        for gift_id, title, model_name, backdrop_name in gifts:
            if not model_name:
                continue
            
            print(f"  🔍 {title} ({model_name})")
            
            # Определяем специальные фоны
            SPECIAL_BACKDROPS = ["Onyx Black", "Black", "Ivory White", "Midnight Blue"]
            search_by_backdrop = backdrop_name and backdrop_name in SPECIAL_BACKDROPS
            
            # Парсим цену с Tonnel
            if search_by_backdrop:
                min_ton_price = await search_tonnel_resale_func(
                    title,
                    model_name,
                    backdrop_name
                )
            else:
                min_ton_price = await search_tonnel_resale_func(
                    title,
                    model_name
                )
            
            if min_ton_price is not None and min_ton_price > 0:
                if update_gift_ton_price_func(gift_id, min_ton_price):
                    print(f"     ✅ Цена: {min_ton_price} TON")
                    prices_updated += 1
                else:
                    print(f"     ⚠️  Не удалось обновить цену")
            else:
                print(f"     ⚠️  Цена не найдена на Tonnel")
            
            # Задержка между запросами
            await asyncio.sleep(3)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Обновление цен завершено: {prices_updated}/{len(gifts)}")
        
        return {"prices_updated": prices_updated}
        
    except Exception as e:
        print(f"❌ Ошибка обновления цен: {e}")
        import traceback
        traceback.print_exc()
        return {"prices_updated": 0}

# Глобальная переменная для управления таймером
last_full_sync_time = None

async def full_sync_with_prices():
    """Полная синхронизация: parse_gifts через pyrogram + обновление цен через Tonnel"""
    global last_full_sync_time
    
    from app.tasks.price_updater import search_tonnel_resale, update_gift_ton_price
    
    print("=" * 80)
    print(f"🔄 ПОЛНАЯ СИНХРОНИЗАЦИЯ (каждый час)")
    print("=" * 80)
    
    # 1. Парсим подарки через pyrogram (только с аккаунта)
    print("\n1️⃣  Обновление подарков через Telegram (pyrogram)...")
    parse_result = await parse_gifts(send_log=False)  # Не отправляем лог отдельно
    
    # 2. Обновляем цены в TON через Tonnel
    print("\n2️⃣  Обновление цен в TON через Tonnel...")
    sync_result = await force_parse_and_sync(search_tonnel_resale, update_gift_ton_price)
    
    # Инвалидируем кэш магазина (цены в звездах пересчитаются автоматически)
    from app.utils.shop_cache import invalidate_shop_cache
    invalidate_shop_cache()
    
    # Отправляем краткий отчет в канал
    message = f"✅ <b>Парсинг завершен</b>\n\n"
    message += f"📦 Подарков обновлено (pyrogram): <b>{parse_result['updated']}</b>\n"
    message += f"💰 Цен в TON обновлено (Tonnel): <b>{sync_result['prices_updated']}</b>\n"
    message += f"🔄 Кэш магазина инвалидирован"
    
    await send_log_to_channel_with_button(message)
    
    # Обновляем время последней синхронизации
    last_full_sync_time = asyncio.get_event_loop().time()
    
    print("=" * 80)
    print(f"✅ Полная синхронизация завершена")
    print("=" * 80)

async def gift_parser_loop():
    """Фоновая задача - полная синхронизация раз в час (parse_gifts + Tonnel)"""
    global last_full_sync_time
    
    # Инициализируем таблицу (если нужно)
    init_gifts_table()
    
    # Инициализируем таймер
    last_full_sync_time = asyncio.get_event_loop().time()
    
    print("[GIFT_PARSER] 🔄 Цикл запущен: полная синхронизация каждый час")
    
    # Первая синхронизация через 1 минуту после старта
    print("[GIFT_PARSER] ⏳ Первая синхронизация через 1 минуту...")
    await asyncio.sleep(60)  # 1 минута
    
    try:
        await full_sync_with_prices()
        print("[GIFT_PARSER] ✅ Первая синхронизация завершена успешно")
    except Exception as e:
        print(f"[GIFT_PARSER] ❌ Ошибка первой синхронизации: {e}")
        import traceback
        traceback.print_exc()
    
    # Цикл полной синхронизации
    while True:
        # Задержка 1 час
        print("[GIFT_PARSER] ⏳ Следующая синхронизация через 1 час...")
        await asyncio.sleep(3600)  # 1 час = 3600 секунд
        
        print("[GIFT_PARSER] ⏰ Время для полной синхронизации...")
        try:
            await full_sync_with_prices()
            print("[GIFT_PARSER] ✅ Полная синхронизация завершена успешно")
        except Exception as e:
            print(f"[GIFT_PARSER] ❌ Ошибка полной синхронизации: {e}")
            import traceback
            traceback.print_exc()
