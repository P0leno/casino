# Casino Project — Knowledge Base

## Overview
Casino Telegram Mini App: shop, spin cases, crash game, gift trading, inventory management.
Frontend (React/Vite) + FastAPI backend + 3 aiogram bots + Pyrogram MTProto client.

## Links
- **App (HTTPS)**: https://proxmox-bubuntu1.tailcfe40a.ts.net (Tailscale serve)
- **Server SSH**: kek@100.127.92.87 (tailscale) / kek@37.214.59.140 (public)
- **Repo**: https://github.com/P0leno/casino.git
- **Bot**: @kfjlfssvh_bot
- **clSSH Config**: /Users/pavel/Downloads/Telegram Desktop/mank.json (pass: 111qqq111)

## Tech Stack
| Layer | Tech |
|---|---|
| Frontend | React 19 + Vite 7, plain JSX (no TS, no UI lib), 25 components |
| Backend | Python 3.12 + FastAPI + Uvicorn |
| Bots | aiogram 3.x — main bot, log bot, support bot |
| DB | SQLite (users.db, support.db, database.db), Redis optional |
| Gifts | Pyrogram (PyroFork) MTProto client for gift operations |
| Payments | Telegram Stars, CryptoBot (aiocryptopay), TON (TONAPI) |
| Docker | Server: python:3.12-slim + gcc (tgcrypto), Client: node:22-alpine → nginx:alpine |

## Docker
- **Server** (casino-server): port 3779, SQLite volumes
- **Client** (casino-client): port 80, nginx proxies /api/ → server:3779, resolver 127.0.0.11
- DNS overrides: 8.8.8.8, 1.1.1.1 (host uses systemd-resolved 127.0.0.53)
- Build: `docker compose up -d --build`

## Deployment (via SSH)
```bash
ssh kek@100.127.92.87 "cd ~/casino && git pull && docker compose up -d --build"
```

## Bot
- **Commands**: `/start` (WebApp), `/admin` (admin panel, admin-only)
- **No other text commands** — all admin actions via inline buttons
- **Admin bot flows**: balance top-up, give gift, user info, stats — all prompted via bot messages

## Features

### User Features
- **Home**: balance, bonus balance, promo codes, quick links to crash/spins
- **Shop**: buy gifts from Fragment/Shelloch for stars, paws, or TON
- **Cases**: free daily spin (free_spin), star spins (bazmin), paw spins (lapik), promo spins (promik)
- **Crash**: real-time multiplayer crash game via WebSocket (/api/crash/ws)
- **Inventory**: view and withdraw gifts (regular Telegram gifts + NFT Fragment gifts)
- **Profile**: avatar, user info, settings, admin panel (for admins)
- **Tasks**: earn rewards by completing tasks
- **Top-Up**: buy stars via CryptoBot invoices or TON transfers

### Admin Features
#### Bot Admin Panel (/admin)
- 📊 Open WebApp admin panel
- 💰 User management: info, top-up, give gift, stats
- 👥 Admin list
- 🔄 Force gift parse & sync
- 📝 Maintenance reason
- 🚧 Restart server
- ⏻ Toggle maintenance mode

#### Web Admin Panel (Profile.jsx overlay)
- Ban/unban user
- Chances/cases management (CRUD, gifts, probabilities)
- Refund payments (user ID + transaction ID)
- Crash settings (max multiplier, debt, big bet threshold, force explode)
- Tasks management (list, create, delete, check permissions)
- System settings
- Top-up / give gift / user info (inline inputs)
- Admin management (add/remove)
- Server stats

## API Routes

### Public
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/validate | Validate initData, check ban/maintenance, return user data |
| POST | /api/get-chances | Get spin chances for a mode |
| POST | /api/update-chances | Update spin chances (admin) |
| POST | /api/get-settings | Get system settings |
| POST | /api/update-setting | Update system setting (admin) |
| POST | /api/ban-user | Ban user (admin) |
| POST | /api/unban-user | Unban user (admin) |
| POST | /api/toggle-maintenance | Toggle maintenance (admin) |
| POST | /api/restart-server | Graceful restart (admin) |

### Cases (/api/game)
| Method | Path | Description |
|--------|------|-------------|
| POST | /case-info | Get case info (price, currency, spin limit) |
| POST | /spin-paid | Execute paid spin |
| POST | /bazmin-spin | Bazmin spin wrapper |
| POST | /lapik-spin | Lapik spin wrapper |

### Crash (/api/crash)
| Method | Path | Description |
|--------|------|-------------|
| GET | /history | Last 50 rounds |
| POST | /bet | Place bet (25–20000 stars) |
| POST | /cashout | Cash out current bet |
| POST | /cancel | Cancel bet before round starts |
| WS | /ws | Real-time game state (20 updates/sec) |
| WS | /admin/ws | Admin tunnel (minimal state) |
| POST | /get-settings | Get crash settings (admin) |
| POST | /update-settings | Update crash settings (admin) |

### Admin (/api/admin)
| Method | Path | Description |
|--------|------|-------------|
| POST | /admin/cases | List all cases |
| POST | /admin/cases/update | Update case |
| POST | /admin/cases/create | Create case (multipart) |
| POST | /admin/cases/delete | Delete case |
| POST | /admin/cases/gifts | List gifts for case |
| POST | /admin/cases/toggle-gift | Enable/disable gift in case |
| POST | /admin/refund-payment | Refund stars |
| POST | /admin/crash/explode | Force crash game explode |
| POST | /admin/tasks/list | List tasks |
| POST | /admin/tasks/create | Create task |
| POST | /admin/tasks/delete | Delete task |
| POST | /admin/tasks/check-bot-permissions | Check TG bot perms |
| POST | /admin/user-info | Get user info |
| POST | /admin/top-up | Top-up/deduct balance |
| POST | /admin/give-gift | Give gift to user |
| POST | /admin/add-admin | Add admin |
| POST | /admin/remove-admin | Remove admin |
| POST | /admin/stats | Server statistics |

## Background Tasks (run.py)
1. Main bot polling (aiogram)
2. Log bot polling (callbacks)
3. Support bot polling (if SUPPORT_BOT_TOKEN)
4. Pyrogram client keepalive
5. Crash game loop (continuous rounds with countdown)
6. TON transaction checker (10s)
7. Gift parser (hourly full sync + TON price update)
8. TON price updater (5 min)
9. Gift models checker (Lottie animation downloads)
10. CryptoBot invoice checker (30s)
11. Spin notification loop
12. Antifraud task (5 min)
13. Redis sync (5 min)
14. Restart monitor

## Environment Variables (.env)
| Variable | Description |
|---|---|
| BOT_TOKEN | Main bot token |
| ADMIN_IDS | Comma-separated admin IDs |
| LOG_BOT_TOKEN | Log channel bot |
| SUPPORT_BOT_TOKEN | Support bot |
| CHECKER_BOT_TOKEN | Gift checker bot |
| LOGS_ID | Log channel chat ID |
| SUPPORT_GROUP_ID | Support group ID |
| SERVER_URL | Public server URL |
| API_ID / API_HASH | Pyrogram credentials |
| SESSION_STRING | Pyrogram session string |
| TON_MERCHANT_ADDRESS | TON payment wallet |
| SEND_TOKEN | CryptoBot API token |
| ALLOWED_ORIGINS | CORS origins |

## Database Tables
users, gift_chances, gift_prices, cases, settings, promocodes, tasks,
shop_gifts, support_dialogs, cryptobot_invoices, payments,
antifraud_* (limits, violations), gift_models, gift_withdrawals

## Crash Game
- WebSocket real-time multiplayer
- Provably-fair-ish algorithm with risk management:
  - Big bet protection
  - Anti-scalper (strike system)
  - House debt tracking
  - Periodic low crashes (every 3-5 rounds)
  - Boost mechanic on early cashouts
- Configurable via Redis: max_multiplier, always_profit, max_debt, big_bet_threshold, big_bet_lose_chance
- Rate limits: bet 100/35min, cashout 100/25min

## Cases
- Free daily spin, star spins, paw spins, promo spins
- Admin CRUD: create cases with SVG icons, set prices, spin limits
- Admin configures gift probabilities per case (visible + real chances)
- Star/paw ranges configurable per gift

## Design System
- Dark theme with glassmorphism (backdrop-filter: blur)
- CSS custom properties for theming
- Global glass utility classes (.glass, .glass-sm, .glass-strong)
- Safe area handling via env(safe-area-inset-*) + JS fallback
- Future: preset themes (halloween, newyear, easter, cny, minimalism, maximalism)
- Full design spec in DESIGN.md

## Key Files
| Path | Description |
|---|---|
| server/app/run.py | Entry point, creates FastAPI, starts all tasks |
| server/app/bot.py | Main bot setup, includes routers |
| server/app/config.py | Environment config |
| server/app/crash_game.py | Crash game logic (509 lines) |
| server/app/handlers/start.py | /start command |
| server/app/handlers/admin.py | Bot admin panel callbacks |
| server/app/routers/crash.py | Crash WebSocket + REST |
| server/app/routers/spins.py | Spin/cases logic |
| server/app/routers/admin.py | Web API admin routes |
| server/app/utils/database.py | DB init + helpers |
| server/app/utils/redis_models.py | Redis settings model |
| client/src/App.jsx | Root component, routing, safe area |
| client/src/index.css | Global styles + CSS variables |
| client/src/components/Profile.jsx | Profile page + admin panel overlay |
| client/src/components/Crash.jsx | Crash game UI |
| client/src/components/Inventory.jsx | Gift inventory |
| docker-compose.yml | Docker compose config |

## CSS Architecture
25 CSS files across components, ~7200 lines total.
No global CSS variables file — variables are component-scoped.
Glass aesthetic used in ~20 components with backdrop-filter blur.
Safe area handled via env(safe-area-inset-*) and JS `--safe-area-top` variable.

## Known Issues
- **Support DB**: `no such table: users` (support.db missing users table)
- **CryptoBot**: 401 UNAUTHORIZED (token not set in config)
- **Admin WS tunnel**: created but not used by frontend
- **game.py router**: not included in FastAPI app (superseded by spins.py)
