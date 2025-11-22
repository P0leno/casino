from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import sqlite3
import os
import json
from datetime import datetime
from app.routers.auth import verify_init_data

router = APIRouter(prefix="/api", tags=["shop"])

# Database path
DB_PATH = os.getenv("DB_PATH", "./users.db")

def sanitize_error(error: Exception) -> str:
    """
    Фильтрует технические детали ошибок, чтобы не отдавать структуру БД пользователям
    """
    error_str = str(error).lower()
    
    # Список технических слов, которые указывают на внутренние ошибки
    technical_keywords = [
        'table', 'column', 'sqlite', 'sql', 'database', 
        'syntax', 'constraint', 'foreign key', 'primary key',
        'insert', 'update', 'delete', 'select', 'from', 'where'
    ]
    
    # Если ошибка содержит технические детали - возвращаем общее сообщение
    if any(keyword in error_str for keyword in technical_keywords):
        return "Произошла ошибка при обработке запроса"
    
    # Если это обычная ошибка - возвращаем как есть
    return str(error)

class ShopGift(BaseModel):
    id: int
    gift_id: str
    slug: Optional[str]
    title: str
    model_name: Optional[str]
    model_path: Optional[str]
    symbol_name: Optional[str]
    backdrop_name: Optional[str]
    center_color: Optional[str]
    edge_color: Optional[str]
    pattern_color: Optional[str]
    text_color: Optional[str]
    available_amount: int
    total_amount: int
    price: int
    rarity_model: Optional[int]
    rarity_symbol: Optional[int]
    rarity_backdrop: Optional[int]

class BuyGiftRequest(BaseModel):
    initData: str
    slug: str

class GetShopGiftsRequest(BaseModel):
    initData: str

@router.post("/shop/gifts", response_model=List[ShopGift])
async def get_shop_gifts(request: GetShopGiftsRequest):
    """
    Получить список подарков для магазина (исключая те, что в инвентаре)
    """
    # Проверяем initData
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем инвентарь пользователя
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        user_result = cursor.fetchone()
        
        inventory_slugs = []
        if user_result and user_result['inventory']:
            try:
                inventory_slugs = json.loads(user_result['inventory'])
            except:
                inventory_slugs = []
        
        # Получаем все подарки (кроме тех, что в инвентаре)
        if inventory_slugs:
            placeholders = ','.join(['?'] * len(inventory_slugs))
            query = f"""
                SELECT * FROM shop_gifts 
                WHERE available_amount > 0 
                  AND slug NOT IN ({placeholders})
                ORDER BY price ASC
            """
            cursor.execute(query, inventory_slugs)
        else:
            cursor.execute("""
                SELECT * FROM shop_gifts 
                WHERE available_amount > 0
                ORDER BY price ASC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        gifts = []
        for row in rows:
            gift_dict = dict(row)
            gifts.append(ShopGift(**gift_dict))
        
        return gifts
        
    except Exception as e:
        print(f"Error fetching shop gifts: {e}")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.get("/shop/gift/{gift_id}")
async def get_gift_details(gift_id: str):
    """Получить детали конкретного подарка"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM shop_gifts WHERE gift_id = ?", (gift_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Gift not found")
        
        return dict(row)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching gift details: {e}")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.post("/shop/buy-gift")
async def buy_gift(request: BuyGiftRequest):
    """Купить подарок из магазина"""
    # Проверка и валидация initData
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    username = user_data.get('username', '')
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем подарок по slug
        cursor.execute("""
            SELECT gift_id, title, price, available_amount, slug 
            FROM shop_gifts 
            WHERE slug = ?
        """, (request.slug,))
        
        gift = cursor.fetchone()
        
        if not gift:
            conn.close()
            raise HTTPException(status_code=404, detail="Подарок не найден")
        
        gift_id, title, price, available_amount, slug = gift
        
        # Проверяем доступность
        if available_amount <= 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Подарок закончился")
        
        # Получаем или создаем пользователя (по полю id, а не user_id!)
        cursor.execute("SELECT balance, inventory FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            # Создаем пользователя если его нет (безопасно - после валидации initData)
            cursor.execute("""
                INSERT INTO users (id, user_id, username, creation_date, balance, inventory, is_banned)
                VALUES (?, ?, ?, ?, 0, '[]', 0)
            """, (user_id, user_id, username, datetime.now().isoformat()))
            conn.commit()
            
            balance = 0
            inventory_json = '[]'
        else:
            balance, inventory_json = user
        
        # Проверяем баланс
        if balance < price:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Недостаточно звезд. Нужно: {price}⭐, есть: {balance}⭐")
        
        # Парсим инвентарь
        try:
            inventory = json.loads(inventory_json) if inventory_json else []
        except:
            inventory = []
        
        # Добавляем slug в инвентарь
        inventory.append(slug)
        
        # Обновляем баланс и инвентарь
        new_balance = balance - price
        cursor.execute("""
            UPDATE users 
            SET balance = ?, inventory = ? 
            WHERE id = ?
        """, (new_balance, json.dumps(inventory), user_id))
        
        # Уменьшаем available_amount
        cursor.execute("""
            UPDATE shop_gifts 
            SET available_amount = available_amount - 1 
            WHERE slug = ?
        """, (request.slug,))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"Подарок \"{title}\" куплен!",
            "new_balance": new_balance,
            "gift_slug": slug
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error buying gift: {e}")
        raise HTTPException(status_code=500, detail=sanitize_error(e))
