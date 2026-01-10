
import asyncio
import os
import json
import logging
import sqlite3
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.handlers import MessageHandler
from dotenv import load_dotenv

# Imports for Price Parsing
from curl_cffi.requests import AsyncSession
try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    def get_ua():
        return ua.random
except ImportError:
    def get_ua():
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

# Load environment variables
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "./users.db")

# Robustly determine CLIENT_PUBLIC_PATH relative to this file location
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
default_public_path = os.path.join(root_dir, "client", "public")
CLIENT_PUBLIC_PATH = os.getenv("CLIENT_PUBLIC_PATH", default_public_path)

logger = logging.getLogger(__name__)

# Special backdrops for precise searching
SPECIAL_BACKDROPS = ["Onyx Black", "Black", "Ivory White", "Midnight Blue"]

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)

def int_to_hex_color(color_int):
    if color_int is None:
        return None
    return f"#{color_int:06x}"

def get_headers():
    """Headers for Tonnel API"""
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
        "user-agent": get_ua()
    }

async def search_tonnel_resale(gift_name, model=None, backdrop=None, max_retries=3):
    """Search for gift price on Tonnel"""
    
    filter_data = {
        "price": {"$exists": True},
        "refunded": {"$ne": True},
        "buyer": {"$exists": False},
        "export_at": {"$exists": True},
        "gift_name": gift_name,
        "asset": "TON"
    }
    
    # If special backdrop - search by backdrop + model
    if backdrop and backdrop in SPECIAL_BACKDROPS and model:
        filter_data["backdrop"] = {"$regex": f"^{backdrop} \\("}
        filter_data["model"] = {"$regex": f"^{model} \\("}
    # Otherwise only by model
    elif model:
        filter_data["model"] = {"$regex": f"^{model} \\("}
    
    sort_data = {
        'price': 1,  # Cheapest first
        'message_post_time': -1
    }
    
    json_data = {
        'page': 1,
        'limit': 1,
        'sort': json.dumps(sort_data),
        'filter': json.dumps(filter_data),
        'price_range': None,
        'user_auth': '',
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            async with AsyncSession(impersonate="chrome") as session:
                response = await session.post(
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
                elif response.status_code == 403:
                    if attempt < max_retries:
                        await asyncio.sleep(attempt * 2)
                        continue
                    else:
                        return None
                else:
                    if attempt < max_retries:
                        await asyncio.sleep(2)
                        continue
                    return None
        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(2)
                continue
            else:
                logger.error(f"❌ Error searching Tonnel: {e}")
                return None
    return None

from app.utils.redis_models import RedisSettings

async def notify_user(user_id, slug, title, ton_price=None):
    """Sends a notification via the Bot API."""
    import aiohttp
    
    stars_text = ""
    if ton_price and ton_price > 0:
        try:
            # Calculate Stars: TON * USD_Rate * 50
            ton_price_usd = RedisSettings.get_float('ton_price_usd', 5.5)
            stars_per_usd = 50
            stars_amount = int(ton_price * ton_price_usd * stars_per_usd)
            stars_text = f" - {stars_amount}⭐️"
        except Exception as e:
            logger.error(f"Error calculating stars: {e}")
            stars_text = ""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    text = f"🎁 <b>Подарок получен!</b>\n\nДобавлен в ваш инвентарь:\n{slug}{stars_text}"
    
    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"   ⚠️ Notification failed: {await resp.text()}")
                else:
                    logger.info(f"   ✅ Notification sent to {user_id}")
    except Exception as e:
        logger.error(f"   ❌ Error sending notification: {e}")

async def handle_gift_message_listener(client, message):
    try:
        if getattr(message, "service", None) != enums.MessageServiceType.GIFT:
            return

        logger.info(f"🎁 DETECTED GIFT from User {message.from_user.id}")
        
        gift = message.gift
        if not gift:
            return

        gift_id = str(gift.id)
        slug = getattr(gift, "name", None) or getattr(gift, "slug", None)
        title = gift.title
        
        attributes = {}
        
        # Extract attributes
        for attr in gift.attributes:
            attr_type = str(attr.type)
            if "MODEL" in attr_type:
                attributes['model_name'] = attr.name
                attributes['rarity_model'] = getattr(attr, 'rarity', 0)
            elif "SYMBOL" in attr_type:
                attributes['symbol_name'] = attr.name
                attributes['rarity_symbol'] = getattr(attr, 'rarity', 0)
            elif "BACKDROP" in attr_type:
                attributes['backdrop_name'] = attr.name
                attributes['rarity_backdrop'] = getattr(attr, 'rarity', 0)
                attributes['center_color'] = int_to_hex_color(getattr(attr, 'center_color', None))
                attributes['edge_color'] = int_to_hex_color(getattr(attr, 'edge_color', None))
                attributes['pattern_color'] = int_to_hex_color(getattr(attr, 'pattern_color', None))
                attributes['text_color'] = int_to_hex_color(getattr(attr, 'text_color', None))

        model_name = attributes.get('model_name')
        backdrop_name = attributes.get('backdrop_name')
        
        if not model_name:
            logger.warning("❌ Model name missing. Cannot process.")
            return

        # 1. SKIP Asset Download (User has all models)
        # We assume the path exists or will be handled by existing infrastructure
        # We just synthesize the path string for DB consistency
        safe_title = title.replace("/", "_")
        safe_model = model_name.replace("/", "_")
        model_path = f"/gifts/models/{safe_title}/{safe_model}.json"

        # 2. Parse Price from Tonnel
        logger.info(f"🔍 Searching price for {title} ({model_name}) on Tonnel...")
        ton_price = await search_tonnel_resale(title, model=model_name, backdrop=backdrop_name)
        
        if ton_price:
            logger.info(f"   ✅ Found price: {ton_price} TON")
        else:
            logger.info(f"   ⚠️ Price not found, defaulting to 0")
            ton_price = 0

        # 3. Update DB
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Upsert shop_gifts
        message_id = message.id  # Capture message ID from the update

        cursor.execute("SELECT id FROM shop_gifts WHERE gift_id = ?", (gift_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE shop_gifts SET
                    slug=?, title=?, model_name=?, model_path=?,
                    symbol_name=?, backdrop_name=?,
                    center_color=?, edge_color=?, pattern_color=?, text_color=?,
                    rarity_model=?, rarity_symbol=?, rarity_backdrop=?,
                    transfer_price=?, ton_price=?, message_id=?, updated_at=CURRENT_TIMESTAMP
                WHERE gift_id=?
            """, (
                slug, title, model_name, model_path,
                attributes.get('symbol_name'), attributes.get('backdrop_name'),
                attributes.get('center_color'), attributes.get('edge_color'), 
                attributes.get('pattern_color'), attributes.get('text_color'),
                attributes.get('rarity_model'), attributes.get('rarity_symbol'), attributes.get('rarity_backdrop'),
                getattr(gift, 'available_amount', 0), getattr(gift, 'total_amount', 0),
                getattr(gift, 'transfer_price', 0), ton_price, message_id, gift_id
            ))
        else:
            cursor.execute("""
                INSERT INTO shop_gifts 
                (gift_id, slug, title, model_name, model_path, symbol_name, backdrop_name,
                 center_color, edge_color, pattern_color, text_color,
                 rarity_model, rarity_symbol, rarity_backdrop,
                 available_amount, total_amount, price, transfer_price, ton_price, message_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                gift_id, slug, title, model_name, model_path,
                attributes.get('symbol_name'), attributes.get('backdrop_name'),
                attributes.get('center_color'), attributes.get('edge_color'), 
                attributes.get('pattern_color'), attributes.get('text_color'),
                attributes.get('rarity_model'), attributes.get('rarity_symbol'), attributes.get('rarity_backdrop'),
                getattr(gift, 'total_amount', 0),
                getattr(gift, 'transfer_price', 0), ton_price, message_id
            ))

        # 3.1 Insert into sold_gifts (Mark as owned by this user, so it's hidden from Shop)
        user_id = message.from_user.id
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO sold_gifts (slug, user_id, purchased_at)
                VALUES (?, ?, ?)
            """, (slug, user_id, datetime.now().isoformat()))
        except Exception as e:
            logger.error(f"Error inserting into sold_gifts: {e}")

        # 4. Add to User Inventory (Save only SLUG string to match system standard)
        user_id = message.from_user.id
        
        cursor.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            inventory = json.loads(row[0]) if row[0] else []
            inventory.append(slug)  # Save string, not object
            cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inventory), user_id))
            conn.commit()
            
            # 5. Notify
            await notify_user(user_id, slug, title, ton_price)
            
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error in gift handler: {e}")
        import traceback
        traceback.print_exc()

def register_gift_handlers(app: Client):
    """Registers gift handlers on the provided Pyrogram client."""
    logger.info("📥 Registering Gift Ingestion Handlers...")
    app.add_handler(MessageHandler(handle_gift_message_listener, filters.service))
    logger.info("✅ Gift Ingestion Handlers registered")
