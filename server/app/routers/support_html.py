from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import sqlite3
from app.config import DB_PATH
from datetime import datetime
import pytz

router = APIRouter()

@router.get("/support/dialog/{dialog_id}", response_class=HTMLResponse)
async def get_dialog_html(dialog_id: int):
    """Получить HTML-визуализацию диалога"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем информацию о диалоге
    cursor.execute(
        "SELECT user_id, username, category, status, created_at, closed_at FROM support_dialogs WHERE dialog_id = ?",
        (dialog_id,)
    )
    dialog_info = cursor.fetchone()
    
    if not dialog_info:
        conn.close()
        raise HTTPException(status_code=404, detail="Диалог не найден")
    
    user_id, username, category, status, created_at, closed_at = dialog_info
    
    # Получаем сообщения диалога
    cursor.execute(
        "SELECT sender_type, sender_name, message_text, photo_path, sent_at FROM dialog_messages WHERE dialog_id = ? ORDER BY sent_at ASC",
        (dialog_id,)
    )
    messages = cursor.fetchall()
    
    conn.close()
    
    # Конвертируем время в МСК
    msk_tz = pytz.timezone('Europe/Moscow')
    
    def format_time_msk(time_str):
        """Конвертировать время в МСК и отформатировать"""
        try:
            dt = datetime.fromisoformat(time_str)
            # Предполагаем что время в БД в UTC
            dt_utc = pytz.utc.localize(dt)
            dt_msk = dt_utc.astimezone(msk_tz)
            return dt_msk.strftime("%d.%m.%Y %H:%M:%S")
        except:
            return time_str
    
    # Генерируем HTML
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Диалог #{dialog_id} - Поддержка Shell</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .user-info {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .user-avatar {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: 600;
        }}
        
        .user-details {{
            flex: 1;
        }}
        
        .user-name {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
        }}
        
        .user-id {{
            font-size: 14px;
            color: #666;
        }}
        
        .messages {{
            padding: 20px 30px;
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .message {{
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease-in;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .message-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .sender {{
            font-weight: 600;
            font-size: 14px;
        }}
        
        .sender.user {{
            color: #667eea;
        }}
        
        .sender.support {{
            color: #764ba2;
        }}
        
        .timestamp {{
            font-size: 12px;
            color: #999;
        }}
        
        .message-content {{
            background: #f8f9fa;
            padding: 12px 16px;
            border-radius: 12px;
            border-left: 3px solid #667eea;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .message.support .message-content {{
            border-left-color: #764ba2;
            background: #f0f4ff;
        }}
        
        .message-photo {{
            margin-top: 10px;
            border-radius: 8px;
            max-width: 100%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Поддержка Shell</h1>
            <p>Спасибо за использование Shell</p>
        </div>
        
        <div class="user-info">
            <div class="user-avatar">
                {username[0].upper() if username else "?"}
            </div>
            <div class="user-details">
                <div class="user-name">@{username}</div>
                <div class="user-id">ID: {user_id} • Категория: {category}</div>
            </div>
        </div>
        
        <div class="messages">
"""
    
    if messages:
        for sender_type, sender_name, message_text, photo_path, sent_at in messages:
            time_formatted = format_time_msk(sent_at)
            sender_class = "user" if sender_type == "user" else "support"
            
            html += f"""
            <div class="message {sender_class}">
                <div class="message-header">
                    <span class="sender {sender_class}">{sender_name}</span>
                    <span class="timestamp">{time_formatted}</span>
                </div>
                <div class="message-content">
                    {message_text or "(фото)"}
                </div>
"""
            
            if photo_path:
                # Преобразуем путь для веб-доступа
                photo_url = f"/api/{photo_path}"
                html += f"""
                <img src="{photo_url}" alt="Фото" class="message-photo">
"""
            
            html += """
            </div>
"""
    else:
        html += """
            <div class="empty-state">
                <p>Нет сообщений в этом диалоге</p>
            </div>
"""
    
    html += """
        </div>
    </div>
</body>
</html>
"""
    
    return html
