"""
Краш-игра механика и рандомайзер
"""
import random
import time
import asyncio
from typing import Dict, List
import math
from app.utils.aiosqlite_pool import db_pool
from app.utils.redis_models import RedisSettings

class CrashGame:
    def __init__(self):
        self.current_multiplier = 1.0
        self.is_running = False
        self.is_countdown = False  # Фаза отсчета перед раундом
        self.countdown_value = 0  # 3, 2, 1
        self.game_id = 0
        self.history = []  # История последних 50 раундов
        self.crash_point = 1.0
        self.start_time = None
        self.bets = {}  # {user_id: {"amount": 100, "cashout_at": None, "username": "", "avatar": ""}}
        self.next_round_bets = {}  # Ставки на следующий раунд
        self.shutting_down = False  # Флаг для graceful shutdown
        
        # Always Profit Mode - система компенсации
        self.debt_to_recover = 0  # Долг который нужно откупить (выигрыши игроков)
        self.rounds_since_debt = 0  # Раундов с момента появления долга
        self.suspicious_users = {}  # {user_id: count} - сколько раз забрал на 1.01-1.15
        self.rounds_since_low_crash = 0  # Раундов с последнего низкого краша (для пустых раундов)
    
    def get_max_multiplier(self) -> float:
        """Получает максимальный коэффициент из Redis"""
        return RedisSettings.get_float('max_crash_multiplier', 10.0)
    
    def is_always_profit_mode(self) -> bool:
        """Проверяет включен ли режим 'Всегда в плюсе' из Redis"""
        return RedisSettings.get_bool('crash_always_profit', False)
    
    def get_max_debt_threshold(self) -> int:
        """Получает порог долга из Redis"""
        return RedisSettings.get_int('crash_max_debt', 300)
    
    def get_big_bet_threshold(self) -> int:
        """Получает порог большой ставки из Redis"""
        return RedisSettings.get_int('crash_big_bet_threshold', 100)
    
    def get_big_bet_lose_chance(self) -> int:
        """Получает шанс проигрыша на большой ставке (в %) из Redis"""
        return RedisSettings.get_int('crash_big_bet_lose_chance', 30)
        
    def generate_crash_point(self) -> float:
        """
        Генерирует точку краша используя провабельно честный алгоритм
        Адаптивное распределение в зависимости от max_multiplier
        """
        # --- RISK MANAGEMENT LOGIC (Active Always or via Settings) ---
        if self.bets:
            total_bets = sum(bet["amount"] for bet in self.bets.values())
            
            # Retrieve Thresholds (defaults tuned for house edge)
            max_debt = self.get_max_debt_threshold()
            big_bet_threshold = self.get_big_bet_threshold()
            
            # Default lose chance 40% -> can be higher in redis
            big_bet_lose_chance = RedisSettings.get_int('crash_big_bet_lose_chance', 40)
            
            # Проверка 1: Крупные ставки (>= порога)
            # Если ставка реально большая (например 2x от порога), повышаем риск
            risk_factor = 1.0
            if total_bets >= big_bet_threshold * 2:
                risk_factor = 1.5
            
            if total_bets >= big_bet_threshold:
                effective_chance = min(90, big_bet_lose_chance * risk_factor)
                
                if random.randint(1, 100) <= effective_chance:
                    # Проигрыш - ранний краш
                    rand = random.random()
                    if rand < 0.20: # 20% instant (1.00-1.05)
                        low_crash = round(random.uniform(1.00, 1.05), 2)
                    elif rand < 0.70: # 50% very low (1.05-1.20)
                        low_crash = round(random.uniform(1.05, 1.20), 2)
                    else: # 30% low (1.20-1.45)
                        low_crash = round(random.uniform(1.20, 1.45), 2)
                        
                    print(f"💰 [RISK] Крупная ставка ({total_bets}⭐), шанс {effective_chance:.1f}% -> краш: {low_crash}x")
                    return low_crash

            # Проверка 2: Хитрецы (Scalpers)
            # Only active if profit mode or explicitly set, but let's keep it generally active
            for user_id in self.bets.keys():
                if self.suspicious_users.get(user_id, 0) >= 3: # 3 strikes
                    low_crash = round(random.uniform(1.00, 1.03), 2)
                    print(f"💰 [Anti-Scalper] Хитрец #{user_id} -> краш: {low_crash}x")
                    return low_crash
            
            # Проверка 3: Долг (Debt Recovery)
            # Если казино в минусе, мы ДОЛЖНЫ отбивать долг
            if self.debt_to_recover > 0:
                debt_ratio = self.debt_to_recover / max(1, max_debt)
                
                # Если долг огромный (> 1.5x порога), очень агрессивно
                if self.debt_to_recover >= max_debt * 1.5:
                    rand = random.random()
                    if rand < 0.30: # 30% instant death
                        low_crash = 1.00
                    elif rand < 0.90:
                        low_crash = round(random.uniform(1.01, 1.20), 2)
                    else:
                        low_crash = round(random.uniform(1.20, 1.50), 2)
                    print(f"💰 [DEBT-CRITICAL] Долг {self.debt_to_recover}⭐ -> краш: {low_crash}x")
                    return low_crash
                
                # Если просто долг, повышаем шанс слива
                # Чем больше долг, тем выше шанс.
                recovery_chance = 0.3 + (0.4 * min(1, debt_ratio)) # 30% to 70% chance
                
                if random.random() < recovery_chance:
                    # Разрешаем иногда чуть выше 1.0
                    low_crash = round(random.uniform(1.00, 1.35), 2)
                    print(f"💰 [DEBT-RECOVERY] Долг {self.debt_to_recover}⭐ (chance {recovery_chance:.2f}) -> краш: {low_crash}x")
                    return low_crash

        # Standard Distribution (if passed risk checks)
        # ... (falls through to standard logic below)
        
        # Проверка 6: Периодический Low Crash (Every 3-5 rounds)
        self.rounds_since_low_crash += 1
        if self.rounds_since_low_crash >= random.randint(3, 5):
             low_crash = round(random.uniform(1.00, 1.50), 2)
             self.rounds_since_low_crash = 0
             return low_crash
        
        max_mult = self.get_max_multiplier()
        rand = random.random()
        
        # Адаптивная генерация в зависимости от max_multiplier
        if max_mult <= 3.0:
            # Для малых max (до 3x)
            if rand < 0.60:
                return round(random.uniform(1.0, 1.5), 2)
            elif rand < 0.90:
                return round(random.uniform(1.5, 2.0), 2)
            else:
                return round(random.uniform(2.0, max_mult), 2)
        
        elif max_mult <= 10.0:
            # Для средних max (до 10x)
            if rand < 0.50:
                return round(random.uniform(1.0, 2.0), 2)
            elif rand < 0.80:
                return round(random.uniform(2.0, max_mult * 0.5), 2)
            else:
                return round(random.uniform(max_mult * 0.5, max_mult), 2)
        
        else:
            # Для больших max (больше 10x) - оригинальная логика
            if rand < 0.50:
                return round(random.uniform(1.0, 2.0), 2)
            elif rand < 0.80:
                return round(random.uniform(2.0, 5.0), 2)
            elif rand < 0.95:
                return round(random.uniform(5.0, min(10.0, max_mult * 0.2)), 2)
            elif rand < 0.99:
                return round(random.uniform(10.0, min(50.0, max_mult * 0.5)), 2)
            else:
                return round(random.uniform(50.0, max_mult), 2)
    
    def calculate_multiplier(self, elapsed_seconds: float) -> float:
        """
        Вычисляет текущий множитель на основе прошедшего времени
        Экспоненциальный рост: 1.00x растет до crash_point за ~10-30 секунд
        """
        if elapsed_seconds <= 0:
            return 1.00
        
        # Скорость роста зависит от crash_point
        # Чем выше crash_point, тем медленнее растет в начале
        growth_rate = 0.1 + (self.crash_point / 100)
        
        multiplier = 1.0 + (elapsed_seconds * growth_rate)
        return min(multiplier, self.crash_point)
    
    async def start_round(self):
        """Запускает новый раунд игры"""
        if self.is_running:
            return
        
        self.game_id += 1
        self.is_running = True
        
        # СНАЧАЛА переносим ставки из next_round_bets в текущие bets
        self.bets = {}
        for user_id, bet in self.next_round_bets.items():
            bet["waiting"] = False  # Убираем флаг ожидания
            self.bets[user_id] = bet
        self.next_round_bets = {}
        
        # ПОТОМ генерируем crash_point с учетом текущих ставок
        self.crash_point = self.generate_crash_point()
        self.start_time = time.time()
        self.current_multiplier = 1.0
        
        print(f"🎮 Раунд #{self.game_id} начался! Crash point: {self.crash_point}x, Ставок: {len(self.bets)}")
        
        # Игра идет пока не достигнут crash_point
        boost_activated = False
        
        while self.is_running and self.current_multiplier < self.crash_point:
            elapsed = time.time() - self.start_time
            self.current_multiplier = self.calculate_multiplier(elapsed)
            
            # Логика буста коэффициента
            # Если ставки БЫЛИ, но сейчас ВСЕ активные игроки вышли (cashout_at is not None)
            # И буст еще не активирован
            if not boost_activated and self.bets:
                active_players = sum(1 for bet in self.bets.values() if bet["cashout_at"] is None)
                if active_players == 0:
                    # Все вышли! Шанс 30% на буст
                    if random.random() < 0.30:
                        max_mult = self.get_max_multiplier()
                        # Бустим только если есть куда расти
                        if self.crash_point < max_mult:
                            old_crash = self.crash_point
                            # Генерируем новый краш от текущего до максимума
                            # Используем экспоненциальное распределение смещенное к низу, чтобы не всегда x1000
                            # Но пользователь просил "вплоть до максимального"
                            
                            # Вариант 1: Равномерное
                            # self.crash_point = round(random.uniform(old_crash, max_mult), 2)
                            
                            # Вариант 2 (поинтереснее): Гарантированный x1.5-x5 от текущего, но не больше max
                            boost_factor = random.uniform(1.2, 5.0)
                            potential_crash = old_crash * boost_factor
                            
                            # Или иногда даем огромный буст если max позволяет
                            if random.random() < 0.1: # 10% шанс на мега-буст
                                potential_crash = random.uniform(old_crash, max_mult)
                                
                            self.crash_point = round(min(potential_crash, max_mult), 2)
                            
                            print(f"🚀 [BOOST] Все вышли! Коэффициент увеличен с {old_crash}x до {self.crash_point}x")
                    
                    # Помечаем что попытка буста была (даже если не сработал рандом, чтобы не проверять каждый тик)
                    boost_activated = True
            
            # Обновления каждые 100ms
            await asyncio.sleep(0.1)
        
        # Краш!
        self.current_multiplier = self.crash_point
        await self.end_round()
    
    async def end_round(self):
        """Завершает раунд"""
        if not self.is_running:
            return
        
        # Сначала останавливаем игру
        self.is_running = False
        self.current_multiplier = self.crash_point
        
        # Добавляем в историю
        self.history.append(self.crash_point)
        if len(self.history) > 50:
            self.history.pop(0)
        
        # Подсчет выигравших/проигравших
        winners = sum(1 for bet in self.bets.values() if bet["cashout_at"] is not None)
        losers = len(self.bets) - winners
        
        # Always Track Profit & Debt (House Mechanics always active)
        if self.bets:
            round_profit = 0  # Профит игроков в этом раунде
            
            for user_id, bet in self.bets.items():
                amount = bet["amount"]
                cashout_at = bet["cashout_at"]
                
                if cashout_at is not None:
                    # Игрок выиграл
                    winnings = amount * cashout_at
                    profit = winnings - amount
                    round_profit += profit
                    
                    # Проверяем - это "хитрец"? (забрал на 1.01-1.15)
                    if 1.01 <= cashout_at <= 1.15:
                        self.suspicious_users[user_id] = self.suspicious_users.get(user_id, 0) + 1
                    elif cashout_at > 1.50:
                        if user_id in self.suspicious_users:
                            self.suspicious_users[user_id] = max(0, self.suspicious_users[user_id] - 2)
            
            if round_profit > 0:
                # Игроки в плюсе -> Увеличиваем "Долг" казино
                profit_margin = 1.15  # 15% margin
                debt_with_margin = round(round_profit * profit_margin)
                self.debt_to_recover += debt_with_margin
                print(f"💰 [FINANCE] Игроки выиграли: +{round_profit}⭐ | Общий долг: {self.debt_to_recover}⭐")
            
            # Если был низкий краш - откупаем долг
            if self.crash_point <= 1.30 and self.debt_to_recover > 0:
                lost_bets = sum(bet["amount"] for bet in self.bets.values() if bet["cashout_at"] is None)
                self.debt_to_recover = max(0, self.debt_to_recover - lost_bets)
                print(f"💰 [FINANCE] Откупили {lost_bets}⭐ | Остаток долга: {self.debt_to_recover}⭐")
        
        print(f"💥 Раунд #{self.game_id} завершен! Crashed at {self.crash_point}x | Выиграли: {winners}, Проиграли: {losers}")
        
        # Пауза 1 секунда - показываем результат со ставками
        await asyncio.sleep(1)
        
        # Очищаем ставки текущего раунда
        self.bets = {}
        
        # Проверяем флаг shutting_down - если рестарт, не запускаем новый раунд
        if self.shutting_down:
            print("🛑 Graceful shutdown: не запускаем новый раунд")
            return
        
        # Фаза countdown - 3, 2, 1 (во время countdown можно ставить)
        self.is_countdown = True
        for countdown in [3, 2, 1]:
            self.countdown_value = countdown
            await asyncio.sleep(1)
        self.is_countdown = False
        self.countdown_value = 0
        
        # Запускаем новый раунд
        asyncio.create_task(self.start_round())
    
    def place_bet(self, user_id: int, amount: float, username: str, avatar: str = None) -> Dict:
        """Размещает ставку игрока"""
        # Проверка что игрок еще не сделал ставку в этом раунде
        if user_id in self.bets or user_id in self.next_round_bets:
            return {"success": False, "error": "Уже есть активная ставка"}
        
        # Если раунд идет - ставка на следующий раунд
        if self.is_running:
            self.next_round_bets[user_id] = {
                "amount": amount,
                "cashout_at": None,
                "username": username,
                "avatar": avatar,
                "waiting": True
            }
            return {"success": True, "waiting": True, "message": "Ставка будет размещена в следующем раунде"}
        # Если countdown или ожидание - ставка принимается на следующий раунд
        else:
            self.next_round_bets[user_id] = {
                "amount": amount,
                "cashout_at": None,
                "username": username,
                "avatar": avatar,
                "waiting": False
            }
            return {"success": True, "waiting": False, "message": "Ставка принята"}
    
    def cashout(self, user_id: int) -> Dict:
        """Забирает выигрыш"""
        if user_id not in self.bets:
            return {"success": False, "error": "Нет активной ставки"}
        
        if not self.is_running:
            return {"success": False, "error": "Раунд не идет"}
        
        bet = self.bets[user_id]
        if bet["cashout_at"] is not None:
            return {"success": False, "error": "Ставка уже забрана"}
        
        # Сохраняем множитель кэшаута
        bet["cashout_at"] = self.current_multiplier
        winnings = round(bet["amount"] * self.current_multiplier)
        
        return {"success": True, "multiplier": self.current_multiplier, "winnings": winnings}
    
    def cancel_bet(self, user_id: int) -> Dict:
        """Отменяет ставку (только если ожидает следующий раунд)"""
        if user_id in self.next_round_bets:
            amount = self.next_round_bets[user_id]["amount"]
            del self.next_round_bets[user_id]
            return {"success": True, "refund": amount}
        return {"success": False, "error": "Нет ставки для отмены"}
    
    async def shutdown_gracefully(self):
        """
        Корректное завершение работы:
        1. Устанавливаем флаг завершения (новые раунды не начнутся)
        2. Ждем окончания текущего раунда
        3. Возвращаем все ставки на следующий раунд
        """
        print("🛑 CrashGame: инициализация graceful shutdown...")
        self.shutting_down = True
        
        # Ждем окончания текущего раунда
        while self.is_running:
            print(f"⏳ CrashGame: ждем окончания раунда #{self.game_id} (x{self.current_multiplier:.2f})...")
            await asyncio.sleep(1)
            
        print("✅ CrashGame: раунд завершен или не был активен")
        
        # Возвращаем ставки на следующий раунд
        if self.next_round_bets:
            print(f"💸 CrashGame: Возврат {len(self.next_round_bets)} ставок на следующий раунд...")
            
            try:
                async with db_pool.connection() as conn:
                    refunded_count = 0
                    for user_id, bet in self.next_round_bets.items():
                        amount = bet["amount"]
                        try:
                            # Возвращаем средства на баланс
                            await conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
                            refunded_count += 1
                            print(f"   ↩️ Возврат {amount} пользователю {user_id}")
                        except Exception as e:
                            print(f"❌ Ошибка возврата ставки пользователю {user_id}: {e}")
                    
                    await conn.commit()
                    print(f"✅ CrashGame: Успешно возвращено {refunded_count} ставок")
                    self.next_round_bets.clear()
                
            except Exception as e:
                print(f"❌ CrashGame: Критическая ошибка при возврате ставок: {e}")
        else:
            print("INFO: Нет ставок на следующий раунд для возврата")

        return True

    def get_state(self, user_id=None) -> Dict:
        """Возвращает текущее состояние игры (опционально для конкретного пользователя)"""
        # Если игра идет - отправляем время начала для клиентского расчета
        # Если взорвалась - отправляем финальный множитель
        state = {
            "gameId": self.game_id,
            "isRunning": self.is_running,
            "isCountdown": self.is_countdown,
            "countdownValue": self.countdown_value,
            "history": self.history[-10:],
            "bets": [
                {
                    "userId": uid,
                    "username": bet["username"],
                    "avatar": bet["avatar"],
                    "amount": bet["amount"],
                    "cashoutAt": bet["cashout_at"]
                }
                for uid, bet in self.bets.items()
            ]
        }
        
        # Добавляем userBet если запрашивается для конкретного пользователя
        if user_id and user_id in self.bets:
            bet = self.bets[user_id]
            amount = bet["amount"]
            cashout_at = bet.get("cashout_at")
            
            # Вычисляем текущий выигрыш
            if cashout_at:
                # Если уже забрал - показываем зафиксированный выигрыш
                current_winnings = amount * cashout_at
            elif self.is_running:
                # Если раунд идет - показываем текущий потенциальный выигрыш
                current_winnings = amount * self.current_multiplier
            else:
                # Раунд не начался - показываем ставку
                current_winnings = amount
            
            state["userBet"] = {
                "user_id": user_id,
                "amount": amount,
                "cashoutAt": cashout_at,
                "current_winnings": round(current_winnings, 2)
            }
        else:
            state["userBet"] = None
        
        # Добавляем nextBet если запрашивается для конкретного пользователя
        if user_id and user_id in self.next_round_bets:
            state["nextBet"] = {
                "amount": self.next_round_bets[user_id]["amount"]
            }
        else:
            state["nextBet"] = None
        
        if self.is_running:
            # Игра идет - отправляем время начала
            state["startTime"] = self.start_time
            state["currentMultiplier"] = round(self.current_multiplier, 2)
        else:
            # Игра не идет
            state["startTime"] = None
            if self.start_time and (time.time() - self.start_time) < 3.5:
                # Только что взорвалась - показываем результат
                state["crashed"] = True
                state["crashedAt"] = self.crash_point
            else:
                # Ожидание нового раунда
                state["crashed"] = False
            state["currentMultiplier"] = round(self.current_multiplier, 2)
        
        return state

# Глобальный экземпляр игры
crash_game = CrashGame()

async def start_crash_game_loop():
    """Запускает бесконечный цикл краш-игры"""
    print("🚀 Запуск краш-игры...")
    await crash_game.start_round()
