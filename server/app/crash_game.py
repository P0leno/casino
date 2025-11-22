"""
Краш-игра механика и рандомайзер
"""
import random
import time
import asyncio
from typing import Dict, List
import math
import sqlite3
from app.config import DB_PATH

class CrashGame:
    def __init__(self):
        self.current_multiplier = 1.0
        self.is_running = False
        self.game_id = 0
        self.history = []  # История последних 50 раундов
        self.crash_point = 1.0
        self.start_time = None
        self.bets = {}  # {user_id: {"amount": 100, "cashout_at": None, "username": "", "avatar": ""}}
        self.next_round_bets = {}  # Ставки на следующий раунд
    
    def get_max_multiplier(self) -> float:
        """Получает максимальный коэффициент из настроек"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'max_crash_multiplier'")
            result = cursor.fetchone()
            conn.close()
            return float(result[0]) if result else 10.0
        except Exception as e:
            print(f"Ошибка получения max_multiplier: {e}")
            return 1000.0
        
    def generate_crash_point(self) -> float:
        """
        Генерирует точку краша используя провабельно честный алгоритм
        Адаптивное распределение в зависимости от max_multiplier
        """
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
        self.crash_point = self.generate_crash_point()
        self.start_time = time.time()
        self.current_multiplier = 1.0
        
        # Переносим ставки из next_round_bets в текущие bets
        self.bets = {}
        for user_id, bet in self.next_round_bets.items():
            bet["waiting"] = False  # Убираем флаг ожидания
            self.bets[user_id] = bet
        self.next_round_bets = {}
        
        print(f"🎮 Раунд #{self.game_id} начался! Crash point: {self.crash_point}x, Ставок: {len(self.bets)}")
        
        # Игра идет пока не достигнут crash_point
        while self.is_running and self.current_multiplier < self.crash_point:
            elapsed = time.time() - self.start_time
            self.current_multiplier = self.calculate_multiplier(elapsed)
            
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
        
        print(f"💥 Раунд #{self.game_id} завершен! Crashed at {self.crash_point}x | Выиграли: {winners}, Проиграли: {losers}")
        
        # Пауза 3 секунды чтобы показать результат
        await asyncio.sleep(3)
        
        # Очищаем ставки текущего раунда
        self.bets = {}
        
        # Пауза 2 секунды перед следующим раундом
        await asyncio.sleep(2)
        
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
    
    def get_state(self) -> Dict:
        """Возвращает текущее состояние игры"""
        # Если игра идет - отправляем время начала для клиентского расчета
        # Если взорвалась - отправляем финальный множитель
        state = {
            "gameId": self.game_id,
            "isRunning": self.is_running,
            "history": self.history[-10:],
            "bets": [
                {
                    "userId": uid,
                    "username": bet["username"],
                    "avatar": bet["avatar"],
                    "amount": bet["amount"],
                    "cashoutAt": bet["cashout_at"],
                    "waiting": bet.get("waiting", False)
                }
                for uid, bet in {**self.bets, **self.next_round_bets}.items()
            ]
        }
        
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
