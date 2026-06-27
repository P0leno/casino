# Casino Project — Knowledge Base

## Overview
Casino Telegram Mini App: shop, spin cases, crash game, gift trading.
Frontend + FastAPI backend + 3 aiogram bots + Pyrogram client.

## Links
- **App (HTTPS)**: https://proxmox-bubuntu1.tailcfe40a.ts.net
- **Server SSH**: kek@100.127.92.57 (tailscale) or kek@37.214.59.140 (public)
- **Repo**: https://github.com/P0leno/casino.git
- **Bot**: @kfjlfssvh_bot (token: 8904204319:AAFfkeYlN7PiwJjwE6-fX21G-pDykhf5eXA)
- **clSSH API**: http://localhost:5670 (credentials in mank.json: password 111qqq111)

## Tech Stack
| Layer | Tech |
|---|---|
| Frontend | React 19 + Vite 7 (plain JSX, no TS, no UI lib) |
| Backend | Python 3.12 + FastAPI + Uvicorn |
| Bot | aiogram 3.x (3 bots: main, log, support) |
| DB | SQLite (users.db, support.db, database.db) + Redis (optional cache) |
| Gifts | Pyrogram (PyroFork) MTProto client |
| Payments | Telegram Stars, CryptoBot (aiocryptopay), TON (TONAPI) |
| Docker | Server: python:3.12-slim, Client: node:22-alpine → nginx:alpine |

## Docker
- **Server** (casino-server): port 3779, env_file ./server/.env, SQLite volumes
- **Client** (casino-client): port 80, nginx proxies /api/ → server:3779
- Compose: /Users/pavel/Desktop/prj/shell/docker-compose.yml
- Build: `docker compose build server` / `docker compose build client`
- Deploy: `docker compose up -d --force-recreate server` / `client`
- DNS: 8.8.8.8, 1.1.1.1 (since host uses 127.0.0.53 systemd-resolved)

## Bot Commands
- `/start` — opens WebApp (verified users) or "in development" message
- `/admin` — admin panel (inline keyboard: open panel, parse gifts, restart, maintenance)

## Admin Features
### Bot (/admin panel)
- Open dashboard (WebApp)
- Force gift parse & sync
- Graceful server restart
- Toggle maintenance mode
- Various callback handlers in log_bot.py (confirm gifts, antifraud, manual withdrawals)

### API Routes (admin, auth via Telegram initData)
- `/api/get-chances`, `/api/update-chances` — spin configs
- `/api/admin/refund-payment` — refund stars
- `/api/crash/*` — crash settings & force explode
- `/api/get-settings`, `/api/update-setting` — system settings
- `/api/toggle-maintenance` — maintenance mode
- `/api/restart-server` — graceful restart
- `/api/ban-user`, `/api/unban-user` — user bans
- `/api/admin/cases/*` — case CRUD

## Background Tasks (run.py)
1. Main bot polling (aiogram)
2. Log bot polling (callbacks only)
3. Support bot polling (if SUPPORT_BOT_TOKEN set)
4. Pyrogram client (keepalive loop)
5. Crash game loop (continuous rounds)
6. TON transaction checker (every 10s)
7. Gift parser (hourly full sync)
8. TON price updater (every 5 min)
9. Gift models checker (Lottie animations)
10. CryptoBot invoice checker (every 30s)
11. Spin notification loop
12. Antifraud task (every 5 min)
13. Redis sync (every 5 min)
14. Restart monitor

## Environment Variables (.env)
| Variable | Default | Description |
|---|---|---|
| BOT_TOKEN | — | Main bot token |
| ADMIN_IDS | — | Comma-separated admin Telegram IDs |
| LOG_BOT_TOKEN | "" | Log channel bot |
| SUPPORT_BOT_TOKEN | "" | Support bot |
| CHECKER_BOT_TOKEN | "" | Checker bot |
| LOGS_ID | 0 | Log channel chat ID |
| SUPPORT_GROUP_ID | 0 | Support group ID |
| SERVER_URL | http://localhost:8000 | Public server URL |
| API_ID / API_HASH | "" | Pyrogram credentials |
| SESSION_STRING | "" | Pyrogram session |
| TON_MERCHANT_ADDRESS | UQA3XG... | TON wallet |
| SEND_TOKEN | "" | CryptoBot API token |
| ALLOWED_ORIGINS | http://localhost:5173 | CORS origins |

## Database
Main tables: users, gift_chances, gift_prices, cases, settings, promocodes, tasks,
shop_gifts, support_dialogs, cryptobot_invoices, antifraud_*, gift_models

## Key Files
| Path | Description |
|---|---|
| server/app/run.py | Entry point, creates FastAPI app, starts all tasks |
| server/app/bot.py | Main bot setup, includes all routers |
| server/app/handlers/admin.py | /admin command + admin callbacks |
| server/app/handlers/start.py | /start command |
| server/app/log_bot.py | Log channel bot (callbacks + notifications) |
| server/app/support_bot.py | User support bot (2072 lines) |
| server/app/config.py | All env vars |
| server/app/routers/admin.py | Web API admin routes (1038 lines) |
| server/requirements.txt | Python deps |
| client/src/components/*.jsx | React components |
| client/nginx.conf | Nginx proxy config |
| docker-compose.yml | Docker orchestration |
| server/Dockerfile | Server image (python:3.12-slim + gcc) |
| client/Dockerfile | Client image (node build → nginx) |

## Common Commands (via clSSH)
```bash
# Pull + rebuild server
curl -X POST http://localhost:5670/run -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/kek/casino && git pull && docker compose build server && docker compose up -d --force-recreate server", "timeout": 300}'

# Rebuild client only
curl -X POST http://localhost:5670/run -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/kek/casino && git pull && docker compose build client && docker compose up -d --force-recreate client", "timeout": 300}'

# View logs
curl -X POST http://localhost:5670/run -H "Content-Type: application/json" \
  -d '{"cmd": "docker logs casino-server --tail 20", "timeout": 10}'
```

## Tailscale
- **Node**: proxmox-bubuntu1 (hostname: serv)
- **Tailnet**: tailcfe40a.ts.net
- **IP**: 100.127.92.87
- **Serve**: `tailscale serve --bg 80` enables HTTPS via Tailscale
- **Funnel**: `sudo tailscale funnel 80` (needs admin panel enable + funnel capability)
- **Note**: Funnel not enabled on tailnet. Use serve for tailnet-only access.
