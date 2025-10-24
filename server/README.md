# Python Backend

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with your bot token:
```bash
BOT_TOKEN=your_telegram_bot_token_here
```

## Run

```bash
# Вариант 1: используя start.sh
./start.sh

# Вариант 2: напрямую
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 3779
```

The server will start at http://localhost:3779
