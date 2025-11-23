"""
Фоновая задача для парсинга подарков из Telegram
"""
import asyncio
import sqlite3
import os
from app.config import API_ID, API_HASH, SESSION_STRING

DB_PATH = os.getenv("DB_PATH", "./users.db")

def int_to_hex_color(color_int):
    """Конвертирует integer в hex цвет"""
    return f"#{color_int:06x}"

def init_gifts_table():
    """Проверяет таблицу подарков (создается в init_db)"""
    # Таблица создается в app.database.db.init_db()
    pass

async def parse_gifts():
    """Парсит подарки из Telegram и сохраняет в БД"""
    if not SESSION_STRING or not API_ID or not API_HASH:
        print("⚠️  Нет credentials для парсинга подарков")
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
        
        try:
            async for gift in app.get_chat_gifts(
                chat_id=me.id,
                exclude_unlimited=True,
                limit=100
            ):
                gifts_count += 1
            
                # Извлекаем данные
                gift_id = str(gift.id)
                slug = getattr(gift, 'name', None)  # HappyBrownie-95259
                title = gift.title
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
                                model_path = f"/gifts/models/{title}/{model_name}.json"
                    
                        # SYMBOL type
                        elif 'SYMBOL' in attr_type:
                            symbol_name = attr_name
                            rarity_symbol = attr_dict.get('rarity', 0)
                    
                        # BACKDROP type - определяем по наличию center_color
                        elif hasattr(attr, 'center_color') or 'BACKDROP' in attr_type:
                            backdrop_name = attr_name
                            rarity_backdrop = attr_dict.get('rarity', 0)
                        
                            # Конвертируем цвета
                            if hasattr(attr, 'center_color'):
                                center_color = int_to_hex_color(attr.center_color)
                            if hasattr(attr, 'edge_color'):
                                edge_color = int_to_hex_color(attr.edge_color)
                            if hasattr(attr, 'pattern_color'):
                                pattern_color = int_to_hex_color(attr.pattern_color)
                            if hasattr(attr, 'text_color'):
                                text_color = int_to_hex_color(attr.text_color)
            
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
        
        if gifts_count > 0:
            print(f"✅ Обновлено подарков в магазине: {gifts_count}")
        else:
            print("ℹ️  Нет новых подарков для обновления")
        
    except Exception as e:
        print(f"❌ Ошибка парсинга подарков: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            if app.is_connected:
                await app.stop()
        except Exception as e:
            print(f"⚠️  Ошибка при остановке Pyrogram: {e}")

async def gift_parser_loop():
    """Фоновая задача - парсит подарки каждые 5 минут"""
    # Инициализируем таблицу (если нужно)
    init_gifts_table()
    
    # Цикл парсинга
    while True:
        # Задержка перед запуском (при старте уже выполнено одноразово)
        await asyncio.sleep(300)  # 5 минут
        
        try:
            await parse_gifts()
        except (AttributeError, ConnectionError) as e:
            print(f"⚠️  Pyrogram connection error (will retry): {e}")
        except Exception as e:
            print(f"❌ Ошибка в gift_parser_loop: {e}")
