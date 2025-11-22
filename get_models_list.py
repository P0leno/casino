#!/usr/bin/env python3
"""
Скрипт для получения списка всех моделей подарков из shelloch.xyz/gifts/models
"""

import requests
from bs4 import BeautifulSoup
import json

def get_models_list():
    """Получить список директорий моделей"""
    url = "https://shelloch.xyz/gifts/models/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем все ссылки на директории (заканчиваются на /)
        models = []
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href.endswith('/') and href not in ['../', './']:
                # Убираем слеш и декодируем URL
                model_name = href.rstrip('/')
                # Заменяем %20 на пробелы
                model_name = model_name.replace('%20', ' ')
                models.append(model_name)
        
        # Сортируем по алфавиту
        models.sort()
        
        print(f"Найдено моделей: {len(models)}\n")
        print("Список моделей:")
        print("-" * 50)
        for model in models:
            print(f"  '{model}'")
        
        print("\n" + "-" * 50)
        print("\nJSON формат для кода:")
        print(json.dumps(models, indent=2, ensure_ascii=False))
        
        # Сохраняем в файл
        with open('models_list.json', 'w', encoding='utf-8') as f:
            json.dump(models, f, indent=2, ensure_ascii=False)
        
        print("\n✓ Список сохранен в models_list.json")
        
        return models
        
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе: {e}")
        return []
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

if __name__ == "__main__":
    print("Получение списка моделей подарков...\n")
    models = get_models_list()
    
    if models:
        print(f"\n✓ Успешно получено {len(models)} моделей")
    else:
        print("\n✗ Не удалось получить список моделей")
