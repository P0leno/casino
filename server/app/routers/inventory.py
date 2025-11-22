from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
import json
import os
from datetime import datetime
from app.routers.auth import verify_init_data

router = APIRouter(prefix="/api", tags=["inventory"])

# Database path
DB_PATH = os.getenv("DB_PATH", "./users.db")

# Фоны для которых ищем по подарку + фону + модели
SPECIAL_BACKDROPS = ["Onyx Black", "Black", "Ivory White", "Midnight Blue"]

class GetInventoryRequest(BaseModel):
    initData: str

class GetSellPriceRequest(BaseModel):
    initData: str
    slug: str

class SellGiftRequest(BaseModel):
    initData: str
    slug: str

def sanitize_error(error: Exception) -> str:
    """
    Фильтрует технические детали ошибок
    """
    error_str = str(error).lower()
    
    technical_keywords = [
        'table', 'column', 'sqlite', 'sql', 'database', 
        'syntax', 'constraint', 'foreign key', 'primary key',
        'insert', 'update', 'delete', 'select', 'from', 'where'
    ]
    
    if any(keyword in error_str for keyword in technical_keywords):
        return "Произошла ошибка при обработке запроса"
    
    return str(error)

def get_headers():
    return {
        "authority": "gifts2.tonnel.network",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": "https://market.tonnel.network",
        "priority": "u=1, i",
        "referer": "https://market.tonnel.network/",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }

def search_tonnel_resale(gift_name, model=None, backdrop=None):
    """Поиск подарка на Tonnel маркетплейсе"""
    try:
        from curl_cffi import requests
    except ImportError:
        import requests
    
    # Базовый фильтр
    filter_data = {
        "price": {"$exists": True},
        "refunded": {"$ne": True},
        "buyer": {"$exists": False},
        "export_at": {"$exists": True},
        "gift_name": gift_name,
        "asset": "TON"
    }
    
    # Если фон специальный - ищем по фону + модели
    if backdrop and backdrop in SPECIAL_BACKDROPS and model:
        filter_data["backdrop"] = {"$regex": f"^{backdrop} \\("}
        filter_data["model"] = {"$regex": f"^{model} \\("}
    # Иначе только по модели
    elif model:
        filter_data["model"] = {"$regex": f"^{model} \\("}
    
    sort_data = {
        'price': 1,  # Сортировка по цене (от дешевых)
        'message_post_time': -1
    }
    
    json_data = {
        'page': 1,
        'limit': 1,  # Нужна только минимальная цена
        'sort': json.dumps(sort_data),
        'filter': json.dumps(filter_data),
        'price_range': None,
        'user_auth': '',
    }
    
    try:
        # Пытаемся использовать curl_cffi
        try:
            from curl_cffi import requests as curl_requests
            response = curl_requests.post(
                'https://gifts2.tonnel.network/api/pageGifts',
                json=json_data,
                headers=get_headers(),
                impersonate="chrome",
                timeout=10
            )
        except ImportError:
            # Fallback на обычный requests
            response = requests.post(
                'https://gifts2.tonnel.network/api/pageGifts',
                json=json_data,
                headers=get_headers(),
                timeout=10
            )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get('price')
            return None
        else:
            print(f"⚠️  Tonnel API error: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"⚠️  Error fetching from Tonnel: {e}")
        return None

def get_ton_to_stars_rate():
    """Получить курс конвертации TON в Stars"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем цену TON в USD
        cursor.execute("SELECT value FROM settings WHERE key = 'ton_price_usd'")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            ton_price_usd = float(result[0])
            # 1 Star = примерно $0.015 (может меняться)
            # Поэтому 1 TON = ton_price_usd / 0.015 Stars
            stars_per_ton = ton_price_usd / 0.015
            return stars_per_ton
        
        return 366.67  # Дефолт ~5.5 / 0.015
    except Exception as e:
        print(f"Error getting TON to Stars rate: {e}")
        return 366.67

# Список обычных (не NFT) подарков
REGULAR_GIFTS = ['bear', 'cake', 'cup', 'diamond', 'flowers', 'gift', 'heart', 'ring', 'rocket', 'rose', 'bottle']

@router.post("/inventory/get")
async def get_inventory(request: GetInventoryRequest):
    """Получить инвентарь пользователя с полной информацией о подарках"""
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
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"inventory": []}
        
        inventory_json = result['inventory']
        inventory_items = json.loads(inventory_json) if inventory_json else []
        
        if not inventory_items:
            conn.close()
            return {"inventory": []}
        
        # Разделяем на обычные подарки (по имени) и NFT (по slug)
        regular_gift_names = [item for item in inventory_items if item in REGULAR_GIFTS]
        nft_slugs = [item for item in inventory_items if item not in REGULAR_GIFTS]
        
        inventory_gifts = []
        
        # Получаем обычные подарки из gift_prices
        if regular_gift_names:
            placeholders = ','.join(['?'] * len(regular_gift_names))
            cursor.execute(f"""
                SELECT gift_name, price, gift_id
                FROM gift_prices
                WHERE gift_name IN ({placeholders})
            """, regular_gift_names)
            
            for row in cursor.fetchall():
                gift_name, price, gift_id = row
                # Формируем данные для обычного подарка
                inventory_gifts.append({
                    'gift_id': gift_id,
                    'slug': gift_name,  # Для обычных подарков slug = gift_name
                    'title': gift_name.capitalize(),
                    'model_name': None,
                    'model_path': f"/gifts/{gift_name}.json",  # Путь к Lottie анимации
                    'symbol_name': None,
                    'backdrop_name': None,
                    'center_color': None,
                    'edge_color': None,
                    'pattern_color': None,
                    'text_color': None,
                    'rarity_model': None,
                    'rarity_symbol': None,
                    'rarity_backdrop': None,
                    'ton_price': None,
                    'price': price,
                    'is_regular_gift': True
                })
        
        # Получаем NFT подарки из shop_gifts
        if nft_slugs:
            placeholders = ','.join(['?'] * len(nft_slugs))
            cursor.execute(f"""
                SELECT 
                    gift_id, slug, title, model_name, model_path,
                    symbol_name, backdrop_name, center_color, edge_color,
                    pattern_color, text_color, rarity_model, rarity_symbol,
                    rarity_backdrop, ton_price
                FROM shop_gifts
                WHERE slug IN ({placeholders})
            """, nft_slugs)
            
            for row in cursor.fetchall():
                gift_dict = dict(row)
                gift_dict['is_regular_gift'] = False
                gift_dict['price'] = None
                inventory_gifts.append(gift_dict)
        
        conn.close()
        
        return {"inventory": inventory_gifts}
        
    except Exception as e:
        print(f"Error getting inventory: {e}")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.post("/inventory/get-sell-price")
async def get_sell_price(request: GetSellPriceRequest):
    """Получить цену продажи подарка (с комиссией)"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем что подарок в инвентаре пользователя
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        inventory_json = result[0]
        inventory = json.loads(inventory_json) if inventory_json else []
        
        if request.slug not in inventory:
            conn.close()
            raise HTTPException(status_code=400, detail="Подарок не найден в инвентаре")
        
        # Получаем информацию о подарке
        cursor.execute("""
            SELECT gift_id, title, model_name, backdrop_name, ton_price
            FROM shop_gifts
            WHERE slug = ?
        """, (request.slug,))
        
        gift = cursor.fetchone()
        
        if not gift:
            conn.close()
            raise HTTPException(status_code=404, detail="Подарок не найден в базе")
        
        gift_id, title, model_name, backdrop_name, cached_ton_price = gift
        
        # Получаем комиссию на продажу
        cursor.execute("SELECT value FROM settings WHERE key = 'sell_commission'")
        commission_result = cursor.fetchone()
        sell_commission = float(commission_result[0]) if commission_result else 10.0
        
        conn.close()
        
        # Получаем актуальную цену с Tonnel
        print(f"🔍 Поиск цены для: {title} (модель: {model_name}, фон: {backdrop_name})")
        
        search_by_backdrop = backdrop_name and backdrop_name in SPECIAL_BACKDROPS
        
        if search_by_backdrop:
            min_ton_price = search_tonnel_resale(title, model=model_name, backdrop=backdrop_name)
        else:
            min_ton_price = search_tonnel_resale(title, model=model_name)
        
        # Если не нашли на Tonnel - используем кешированную цену
        if min_ton_price is None:
            if cached_ton_price:
                min_ton_price = cached_ton_price
                print(f"⚠️  Не найдено на Tonnel, используем кешированную цену: {cached_ton_price} TON")
            else:
                raise HTTPException(status_code=400, detail="Не удалось определить цену подарка")
        else:
            print(f"✅ Найдена цена на Tonnel: {min_ton_price} TON")
        
        # Вычитаем комиссию
        price_after_commission = min_ton_price * (1 - sell_commission / 100)
        
        # Конвертируем в Stars
        stars_per_ton = get_ton_to_stars_rate()
        stars_price = int(price_after_commission * stars_per_ton)
        
        return {
            "slug": request.slug,
            "title": title,
            "ton_price": min_ton_price,
            "commission_percent": sell_commission,
            "ton_price_after_commission": round(price_after_commission, 2),
            "stars_price": stars_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting sell price: {e}")
        raise HTTPException(status_code=500, detail=sanitize_error(e))

@router.post("/inventory/sell")
async def sell_gift(request: SellGiftRequest):
    """Продать подарок из инвентаря"""
    user_data = verify_init_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user_data['id']
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем пользователя
        cursor.execute("SELECT inventory, balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        inventory_json, balance = result
        inventory = json.loads(inventory_json) if inventory_json else []
        
        # Проверяем что подарок в инвентаре
        if request.slug not in inventory:
            conn.close()
            raise HTTPException(status_code=400, detail="Подарок не найден в инвентаре")
        
        # Получаем информацию о подарке
        cursor.execute("""
            SELECT gift_id, title, model_name, backdrop_name, ton_price
            FROM shop_gifts
            WHERE slug = ?
        """, (request.slug,))
        
        gift = cursor.fetchone()
        
        if not gift:
            conn.close()
            raise HTTPException(status_code=404, detail="Подарок не найден в базе")
        
        gift_id, title, model_name, backdrop_name, cached_ton_price = gift
        
        # Получаем комиссию
        cursor.execute("SELECT value FROM settings WHERE key = 'sell_commission'")
        commission_result = cursor.fetchone()
        sell_commission = float(commission_result[0]) if commission_result else 10.0
        
        # Получаем актуальную цену с Tonnel
        print(f"🔍 Продажа: {title} (модель: {model_name}, фон: {backdrop_name})")
        
        search_by_backdrop = backdrop_name and backdrop_name in SPECIAL_BACKDROPS
        
        if search_by_backdrop:
            min_ton_price = search_tonnel_resale(title, model=model_name, backdrop=backdrop_name)
        else:
            min_ton_price = search_tonnel_resale(title, model=model_name)
        
        # Если не нашли - используем кешированную
        if min_ton_price is None:
            if cached_ton_price:
                min_ton_price = cached_ton_price
                print(f"⚠️  Используем кешированную цену: {cached_ton_price} TON")
            else:
                conn.close()
                raise HTTPException(status_code=400, detail="Не удалось определить цену подарка")
        
        # Вычисляем цену со всеми комиссиями
        price_after_commission = min_ton_price * (1 - sell_commission / 100)
        stars_per_ton = get_ton_to_stars_rate()
        stars_price = int(price_after_commission * stars_per_ton)
        
        # Удаляем подарок из инвентаря (только первое вхождение)
        inventory.remove(request.slug)
        
        # Обновляем баланс и инвентарь
        new_balance = balance + stars_price
        cursor.execute("""
            UPDATE users 
            SET inventory = ?, balance = ? 
            WHERE id = ?
        """, (json.dumps(inventory), new_balance, user_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Продан подарок {title} за {stars_price}⭐")
        
        return {
            "success": True,
            "message": f"Подарок \"{title}\" продан!",
            "stars_earned": stars_price,
            "new_balance": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error selling gift: {e}")
        raise HTTPException(status_code=500, detail=sanitize_error(e))
