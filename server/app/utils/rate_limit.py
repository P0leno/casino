from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window  # в секундах
        self.requests = defaultdict(list)
        self.lock = Lock()
    
    def is_allowed(self, user_id: int) -> tuple[bool, int]:
        """
        Проверяет можно ли сделать запрос
        Возвращает (allowed, remaining_time)
        """
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.time_window)
            
            # Очищаем старые запросы
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > cutoff
            ]
            
            # Проверяем лимит
            if len(self.requests[user_id]) >= self.max_requests:
                # Вычисляем сколько ждать
                oldest_request = self.requests[user_id][0]
                wait_until = oldest_request + timedelta(seconds=self.time_window)
                remaining_seconds = int((wait_until - now).total_seconds())
                return False, max(0, remaining_seconds)
            
            # Добавляем новый запрос
            self.requests[user_id].append(now)
            return True, 0

# Создаем глобальный rate limiter: 5 запросов за 3 минуты (180 секунд)
invoice_rate_limiter = RateLimiter(max_requests=5, time_window=180)

# Rate limiter для команды /start: 6 запросов за 3 минуты (180 секунд)
start_command_rate_limiter = RateLimiter(max_requests=6, time_window=180)
