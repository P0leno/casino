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
uvicorn main:app --reload
```

The server will start at http://localhost:8000
