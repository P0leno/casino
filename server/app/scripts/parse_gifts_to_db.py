#!/usr/bin/env python3
"""
Скрипт для парсинга подарков и сохранения в БД
Запуск: python3 -m app.scripts.parse_gifts_to_db
"""
import asyncio
import os
import sys
import sqlite3
import json
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from pyrogram import Client

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
DB_PATH = os.getenv("DB_PATH", "./users.db")

def int_to_hex_color(color_int):
    """Конвертирует integer в hex цвет"""
    return f"#{color_int:06x}"

def init_gifts_table():
    """Проверяет существование таблицы для подарков (создается в init_db)"""
    # Таблица создается автоматически в app.database.db.init_db()
    # Эта функция оставлена для совместимости
    pass

async def parse_and_save_gifts():
    """Парсит подарки и сохраняет в БД"""
    print("🚀 Запуск парсинга подарков...")
    
    if not SESSION_STRING or not API_ID or not API_HASH:
        print("❌ Не хватает credentials в .env")
        return
    
    app = Client(
        "gift_parser",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    )
    
    try:
        await app.start()
        me = await app.get_me()
        print(f"✅ Подключено как: {me.first_name}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        gifts_count = 0
        
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
            price = getattr(gift, 'transfer_price', 0)
            
            # Сохраняем в БД
            cursor.execute("""
                INSERT OR REPLACE INTO shop_gifts 
                (gift_id, slug, title, model_name, model_path, symbol_name, backdrop_name,
                 center_color, edge_color, pattern_color, text_color,
                 available_amount, total_amount, price,
                 rarity_model, rarity_symbol, rarity_backdrop, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                gift_id, slug, title, model_name, model_path, symbol_name, backdrop_name,
                center_color, edge_color, pattern_color, text_color,
                available_amount, total_amount, price,
                rarity_model, rarity_symbol, rarity_backdrop
            ))
            
            print(f"✅ {gifts_count}. {title} ({slug}) - {model_name} ({center_color} → {edge_color})")
        
        conn.commit()
        conn.close()
        
        print(f"\n📊 Всего обработано подарков: {gifts_count}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await app.stop()
        print("✅ Готово!")

if __name__ == "__main__":
    init_gifts_table()
    asyncio.run(parse_and_save_gifts())
