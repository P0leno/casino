from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json
import random
import asyncio
from datetime import datetime

from app.utils.database import get_db_connection, db_connection
from app.utils.validate import validate_init_data
from app.utils.rate_limit import spin_rate_limiter
from app.utils.balance import get_user_balance
from app.utils.redis_models import RedisUser
from app.config import BOT_TOKEN, LOGS_ID
from app.utils.error_logger import send_error_log
from urllib.parse import parse_qs

router = APIRouter(prefix="/api/game", tags=["spins"])

class CaseSpinRequest(BaseModel):
    initData: str
    slug: str
    promikCode: Optional[str] = None # Added for Promik support

class ValidateRequest(BaseModel):
    initData: str

class CaseInfoRequest(BaseModel):
    initData: str
    slug: str

@router.post("/case-info")
async def get_case_info(request: CaseInfoRequest):
    """
    Get public info about a case, including price, currency, and special limits (e.g. Secret max stars).
    """
    try:
        # Validate initData (light check, mainly for integrity)
        if not validate_init_data(request.initData, BOT_TOKEN):
            return {"success": False, "message": "Invalid initData"}
            
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Get fundamental case info
            cursor.execute("SELECT title, price, currency, is_active, spin_limit FROM cases WHERE slug = ?", (request.slug,))
            case_row = cursor.fetchone()
            
            if not case_row:
                 # Fallback for old/missing DB entries (e.g. bazmin default)
                 if request.slug == 'bazmin':
                     return {"success": True, "title": "Bazmin", "price": 5, "currency": "star", "secret_limit": 5}
                 return {"success": False, "message": "Case not found"}
            
            title, price, currency, is_active, spin_limit = case_row
            
            # 2. Check for 'secret' drop limit in this case mode
            cursor.execute("SELECT star_max FROM gift_chances WHERE mode = ? AND gift_name = 'secret'", (request.slug,))
            secret_row = cursor.fetchone()
            secret_limit = secret_row[0] if secret_row else None
            
            return {
                "success": True,
                "title": title,
                "price": price,
                "currency": currency,
                "isActive": bool(is_active),
                "secret_limit": secret_limit
            }
            
    except Exception as e:
        await send_error_log(e, "spins.py: get_case_info")
        return {"success": False, "message": "Server Error"}

async def process_paid_spin(user_id: int, slug: str, promik_code: str = None) -> dict:
    """
    Generic logic for paid spins (reading price/currency from DB).
    Supports 'star' and 'paw' currencies.
    Uses context manager for DB safety.
    """
    try:
        # 0.5 Anti-Fraud Imports (Pre-import to be safe)
        from app.tasks.antifraud import check_promo_fraud, check_same_ip_promo_activation

        with db_connection() as conn:
            cursor = conn.cursor()
            
            # 0. Special Logic for 'promik' Case
            skip_balance_check = False
            
            if slug == 'promik':
                # 0.1 Validate Input
                if not promik_code:
                     return {"success": False, "message": "Введите промокод"}
                
                # Sanitize
                import re
                promo_code = re.sub(r'[^A-Z0-9_-]', '', promik_code.upper())[:16]
                
                # 0.2 Check Promo Validity
                cursor.execute("SELECT id, owner, reward, type FROM promocodes WHERE promo = ?", (promo_code,))
                promo = cursor.fetchone()
                if not promo:
                     return {"success": False, "message": "Промокод не найден"}
                
                promo_id, owner_id, reward, promo_type = promo
                
                if owner_id == user_id:
                     return {"success": False, "message": "Нельзя использовать свой код"}
                
                # 0.3 Check if already used
                cursor.execute("SELECT activated_promocodes FROM users WHERE id = ?", (user_id,))
                user_act = cursor.fetchone()
                activated_ids = json.loads(user_act[0] or '[]') if user_act else []
                
                if promo_id in activated_ids:
                     return {"success": False, "message": "Этот код уже использован"}
                     
                # 0.4 Strict Rule: One Ref Code Per User (Global)
                if promo_type in ['ref', 'refCustom']:
                     if activated_ids:
                         cursor.execute(f"SELECT count(*) FROM promocodes WHERE id IN ({','.join(['?']*len(activated_ids))}) AND type IN ('ref', 'refCustom')", activated_ids)
                         if cursor.fetchone()[0] > 0:
                             return {"success": False, "message": "Вы уже активировали инвайт код"}

                # 0.6 Activate Code (Effectively "Pay" for the spin)
                activated_ids.append(promo_id)
                cursor.execute("UPDATE users SET activated_promocodes = ? WHERE id = ?", (json.dumps(activated_ids), user_id))
                cursor.execute("UPDATE promocodes SET invited_count = invited_count + 1 WHERE id = ?", (promo_id,))
                cursor.execute("INSERT INTO promo_history (promo_id, user_id, action_type) VALUES (?, ?, 'activated_spin')", (promo_id, user_id))
                
                skip_balance_check = True
            
            else:
                skip_balance_check = False

            # 1. Получаем инфо о кейсе
            cursor.execute("SELECT title, price, currency, is_active, spin_limit, spins_count FROM cases WHERE slug = ?", (slug,))
            case_info = cursor.fetchone()
            
            if not case_info:
                # Fallback for old hardcoded modes if DB entry missing (migration safety)
                if slug == 'bazmin':
                    price, currency, spin_limit, spins_count = 5, 'star', -1, 0
                    title, is_active = "Bazmin", 1
                elif slug == 'lapik':
                    price, currency, spin_limit, spins_count = 10, 'paw', -1, 0
                    title, is_active = "Lapik", 1
                else:
                    return {"success": False, "message": "Case not found"}
            else:
                title, price, currency, is_active, spin_limit, spins_count = case_info
                
                if not is_active:
                    return {"success": False, "message": "Case is disabled or deleted"}
            
            # 1.1 Check Global Spin Limit (AND Auto-Delete)
            should_delete_after = False
            if spin_limit > -1:
                if spins_count >= spin_limit:
                     return {"success": False, "message": "Case sold out"}
                
                if spins_count + 1 >= spin_limit:
                    should_delete_after = True
            
            # 2. Проверяем баланс (If not skipped)
            cursor.execute("SELECT balance, bonus_balance, inventory FROM users WHERE id = ?", (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                 return {"success": False, "message": "User not found"}
                 
            balance = user_row[0] or 0
            bonus_balance = user_row[1] or 0
            inventory_json = user_row[2] or "[]"
            
            if not skip_balance_check:
                if currency == 'star':
                    if balance < price:
                        return {"success": False, "message": "Недостаточно звезд", "needTopUp": True}
                    # Списываем
                    new_balance = balance - price
                    new_bonus = bonus_balance
                    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
                    
                elif currency == 'paw':
                    if bonus_balance < price:
                        return {"success": False, "message": "Недостаточно лапок"}
                    # Списываем
                    new_balance = balance
                    new_bonus = bonus_balance - price
                    cursor.execute("UPDATE users SET bonus_balance = ? WHERE id = ?", (new_bonus, user_id))
                    
                else:
                    new_balance = balance
                    new_bonus = bonus_balance
            else:
                new_balance = balance
                new_bonus = bonus_balance
            
            # 1.2 Increment Global Spin Count
            cursor.execute("UPDATE cases SET spins_count = spins_count + 1 WHERE slug = ?", (slug,))
            
            # 1.3 Auto-Delete if Limit Reached
            if should_delete_after:
                 print(f"⚠️ Limit reached for case {slug} ({spin_limit}). Deleting case.")
                 cursor.execute("DELETE FROM cases WHERE slug = ?", (slug,))
                 cursor.execute("DELETE FROM gift_chances WHERE mode = ?", (slug,))
                 
                 # Log event
                 title_safe = title or slug
                 try:
                     from app.log_bot import log_bot
                     asyncio.create_task(log_bot.send_message(LOGS_ID, f"🗑️ <b>Case Deleted</b>\n\nName: {title_safe}\nSlug: {slug}\nLimit Reached: {spin_limit}"))
                 except: pass

            conn.commit()
            
            # 3. Крутим рулетку
            cursor.execute("SELECT gift_name, real_chance, paw_min, paw_max, star_min, star_max FROM gift_chances WHERE mode = ?", (slug,))
            chances = cursor.fetchall()
            
            if not chances:
                return {"success": False, "message": f"No gifts config for {slug}"}

            # 3.1 Pre-filtering for 'secret' items (dynamic chance)
            # We need to know if 'secret' is possible before spinning
            from app.utils.shop_cache import get_cached_shop_gifts, update_cached_gift
            
            valid_chances = []
            secret_gifts_pool = [] # List of eligible gifts for secret drop
            
            for row in chances:
                gift_name, chance, _, _, _, star_max = row
                
                if gift_name == 'secret':
                    # Check cache for available items under limit
                    shop_gifts = get_cached_shop_gifts()
                    limit = star_max or 999999
                    
                    # Filter: Price <= Limit AND Stock > 0
                    eligible = [
                        g for g in shop_gifts 
                        if g.get('price', 999999) <= limit and g.get('available_amount', 0) > 0
                    ]
                    
                    if eligible:
                        # FOUND valid secret items
                        # Sort by price ASC (Cheapest first) as per requirement
                        eligible.sort(key=lambda x: x.get('price', 0))
                        secret_gifts_pool = eligible
                        valid_chances.append(row)
                    else:
                        # No valid items for secret -> Chance becomes 0 (exclude from pool)
                        # We just don't add it to valid_chances
                        pass
                else:
                    valid_chances.append(row)
            
            if not valid_chances:
                 return {"success": False, "message": "No available gifts in this case"}

            chances = valid_chances
            total = sum(c[1] for c in chances)
            
            if total <= 0:
                return {"success": False, "message": "Config error (total chance 0)"}
                
            rand = random.uniform(0, total)
            current_val = 0
            selected_row = chances[0]
            
            for row in chances:
                current_val += row[1]
                if rand <= current_val:
                    selected_row = row
                    break
            
            # 4. Начисляем выигрыш
            gift_name, _, paw_min, paw_max, star_min, star_max = selected_row
            
            response_data = {"success": True, "gift": gift_name}
            
            if gift_name == 'paw':
                amount = random.randint(paw_min or 1, paw_max or 10)
                new_bonus += amount
                cursor.execute("UPDATE users SET bonus_balance = ? WHERE id = ?", (new_bonus, user_id))
                response_data['paw_count'] = amount
                
            elif gift_name == 'star':
                amount = random.randint(star_min or 1, star_max or 5)
                new_balance += amount
                cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
                response_data['star_count'] = amount
            
            elif gift_name == 'secret':
                # Handle Secret Drop
                # We already populated secret_gifts_pool sorted by price ASC
                # Pick the first one (Cheapest)
                if not secret_gifts_pool:
                     return {"success": False, "message": "Secret item disappeared"} # Race condition safety
                
                secret_item = secret_gifts_pool[0]
                secret_slug = secret_item['slug']
                secret_title = secret_item['title']
                
                # 1. Decrement Stock (DB)
                cursor.execute("UPDATE shop_gifts SET available_amount = available_amount - 1 WHERE slug = ? AND available_amount > 0", (secret_slug,))
                if cursor.rowcount == 0:
                     return {"success": False, "message": "Item sold out during spin"}
                
                # 2. Update Cache
                new_amount = secret_item['available_amount'] - 1
                update_cached_gift(secret_slug, new_amount)
                
                # 3. Add to User Inventory
                try:
                    inv = json.loads(inventory_json)
                except: inv = []
                inv.append(secret_slug) # Add real item slug
                cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inv), user_id))
                
                # 4. Add to Sold Gifts History
                cursor.execute("INSERT INTO sold_gifts (slug, user_id, purchased_at) VALUES (?, ?, ?)", 
                               (secret_slug, user_id, datetime.utcnow().isoformat()))
                
                # Response data
                response_data['secret_slug'] = secret_slug
                response_data['secret_name'] = secret_title
                response_data['is_secret'] = True
                
            else:
                # Предмет (Standard named gift from chances)
                # Note: This branch might need similar specific checking if standard items have stock? 
                # Assuming standard named gifts in 'gift_chances' are abstract or infinite unless they match a shop slug?
                # For now keeping existing logic for 'other'
                try:
                    inv = json.loads(inventory_json)
                except: 
                    inv = []
                inv.append(gift_name)
                cursor.execute("UPDATE users SET inventory = ? WHERE id = ?", (json.dumps(inv), user_id))
            
            conn.commit()
            
            RedisUser.invalidate(user_id)
            
            return {
                **response_data,
                "balance": new_balance,
                "bonus_balance": new_bonus
            }
            
    except Exception as e:
        print(f"Error in process_paid_spin({slug}): {e}")
        await send_error_log(e, f"spins.py: process_paid_spin({slug})")
        return {"success": False, "message": "Server error internal"}

@router.post("/spin-paid")
async def case_spin(request: CaseSpinRequest):
    """Generic endpoint for any case spin"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    if not is_valid: return {"success": False, "message": "Invalid initData"}
    
    parsed = parse_qs(request.initData)
    user = json.loads(parsed.get('user', [''])[0])
    user_id = user.get('id')
    
    allowed, remaining = spin_rate_limiter.is_allowed(user_id)
    if not allowed: return {"success": False, "message": f"Wait {remaining}s"}
    
    # Pass promikCode (which was frontend input) to process logic
    return await process_paid_spin(user_id, request.slug, request.promikCode)

@router.post("/bazmin-spin")
async def bazmin_spin_wrapper(request: ValidateRequest):
    """Legacy wrapper for bazmin"""
    return await case_spin(CaseSpinRequest(initData=request.initData, slug='bazmin'))

@router.post("/lapik-spin")
async def lapik_spin_wrapper(request: ValidateRequest):
    """Legacy wrapper for lapik"""
    return await case_spin(CaseSpinRequest(initData=request.initData, slug='lapik'))


# ============================================================
# Backward-compatible routes (used by FreeSpin.jsx, Spin.jsx, SpinOptimized.jsx)
# ============================================================

legacy_router = APIRouter(prefix="/api", tags=["spins-legacy"])


class SpinRequest(BaseModel):
    initData: str


@legacy_router.post("/check-spin-available")
async def check_spin_available(request: SpinRequest):
    """Проверить доступность бесплатного спина (аналог /api/game/case-info для free_spin)"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    if not is_valid:
        return {"valid": False, "available": False, "timeLeft": 0}

    try:
        parsed = parse_qs(request.initData)
        user_data = json.loads(parsed.get('user', [''])[0])
        user_id = user_data.get('id')
    except Exception:
        return {"valid": False, "available": False, "timeLeft": 0}

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT last_spin_date FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"valid": True, "available": True, "timeLeft": 0}

    last_spin = datetime.fromisoformat(row[0])
    now = datetime.now()
    elapsed = (now - last_spin).total_seconds()
    cooldown = 24 * 3600

    if elapsed >= cooldown:
        return {"valid": True, "available": True, "timeLeft": 0}
    else:
        return {"valid": True, "available": False, "timeLeft": int(cooldown - elapsed)}


@legacy_router.post("/spin")
async def free_spin(request: SpinRequest):
    """Бесплатный спин (обёртка над case_spin для free_spin)"""
    is_valid = validate_init_data(request.initData, BOT_TOKEN)
    if not is_valid:
        return {"success": False, "message": "Invalid initData"}

    try:
        parsed = parse_qs(request.initData)
        user_data = json.loads(parsed.get('user', [''])[0])
        user_id = user_data.get('id')
    except Exception:
        return {"success": False, "message": "Invalid user data"}

    # Проверка доступности
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_spin_date FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    now = datetime.now()
    if row and row[0]:
        last_spin = datetime.fromisoformat(row[0])
        elapsed = (now - last_spin).total_seconds()
        if elapsed < 24 * 3600:
            conn.close()
            return {"success": False, "message": "Спин ещё недоступен"}

    # Выполняем бесплатный спин (slug='free_spin')
    result = await process_paid_spin(user_id, 'free_spin')

    if result.get("success"):
        cursor.execute("UPDATE users SET last_spin_date = ? WHERE id = ?",
                       (now.isoformat(), user_id))
        conn.commit()

    conn.close()
    return result



