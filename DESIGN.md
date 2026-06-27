# Design System — Casino Mini App

## Theme Engine

### CSS Variables (Tokens)
Все стили управляются через CSS-переменные в `:root`.
Переменные делятся на 4 категории:

| Category | Prefix | Example |
|----------|--------|---------|
| Glass | `--glass-*` | `--glass-blur: blur(16px)` |
| Accent | `--accent-*` | `--accent: #6c5ce7` |
| Background | `--bg-*` | `--bg-primary: #0e0e0e` |
| Text | `--text-*` | `--text-secondary: rgba(...)` |
| Safe area | `--safe-*` | `--safe-top: env(...)` |
| Radius | `--glass-radius-*` | `--glass-radius: 16px` |

### Glass Utility Classes
| Class | Description |
|-------|-------------|
| `.glass` | Base glass — blur(16px), border, shadow, highlight |
| `.glass-sm` | Light blur(8px), no shadow |
| `.glass-strong` | Higher opacity background + full blur/shadow |
| `.glass-gradient` | Purple-tinted gradient glass |
| `.glass-liquid` | Animated radial gradient overlay shift |

All defined in `src/index.css`

### Glass Liquid Animation
```css
.glass-liquid::before {
  background: radial-gradient(circle at 30% 40%, rgba(108,92,231,0.06), transparent 50%),
              radial-gradient(circle at 70% 60%, rgba(59,130,246,0.04), transparent 50%);
  animation: glassLiquidShift 12s ease-in-out infinite alternate;
}
```

### Safe Area
Переменные `--safe-top` и `--safe-bottom` используют `env(safe-area-inset-*)`.
Утилитарные классы: `.safe-top`, `.safe-bottom`.

### Preset Switching (реализовано)
Каждый preset — блок `:root[data-theme="<name>"]` с переопределением токенов в `index.css`.
Переключение через JS: `document.documentElement.setAttribute('data-theme', 'halloween')`
Сохранение в `localStorage` — применяется при загрузке App.jsx.

Пресеты:
| ID | Icon | Акцент | Glass | Фон |
|----|------|--------|-------|-----|
| `default` | 💜 | #6c5ce7 | blur 16px | #0e0e0e |
| `minimalism` | ⬜ | #ffffff | blur 8px, radius 4px | #0a0a0a |
| `halloween` | 🎃 | #ff6b35 | оранжевый glass | #0d0d0d |
| `newyear` | 🎄 | #ffd700 | золотой glass | #0f0d08 |
| `easter` | 🐰 | #f472b6 | розовый glass | #1a0f14 |
| `cny` | 🧧 | #dc2626 | красный glass | #0d0808 |
| `maximalism` | ✨ | #6c5ce7 | blur 24px, max прозрачность | #0e0e0e |

### User Customization (TODO)
В настройках админки («Тема оформления») — выбор пресета с превью.
Сохранение в `localStorage`.
Будущие слайдеры: blur, opacity, border, accent color, animation speed.

### User Customization (TODO)
В настройках админки — слайдеры для blur, opacity, border, radius, accent color, animation speed, background.
Сохранение в `localStorage`.

## Admin Panel Design

### Architecture
Отдельный React-компонент `AdminPanel.jsx` со своим стейтом и CSS.
Внедрён в Profile.jsx на замену старому inline-админ-блоку.

### Layout
```
┌──────────────────────────────┐
│  👑 Админ панель       ✕     │  ← glass header
├──────────────────────────────┤
│  🔍 Поиск пользователя       │  ← карточка с ID/username/balance/ban
│  💰 Пополнение / Списание    │
│  🎁 Выдача подарка           │
│  👑 Управление админами      │
│  📊 Статистика               │  ← 2×2 grid карточек
│  🎨 Тема оформления          │  ← placeholder
└──────────────────────────────┘
```

### Navigation
- Bottom sheet overlay с safe-area
- Меню → каждый пункт открывает отдельный экран
- Кнопка «← Назад» на каждом подэкранe
- Кнопка «✕» закрывает всю панель

### AdminPanel.jsx — Sections
| View | Features |
|------|----------|
| `menu` | 6 кнопок-навигация |
| `search` | Input ID → user info card + ban/unban |
| `user_detail` | Полная карточка пользователя |
| `topup` | ID + сумма (отрицательная = списание) |
| `givegift` | ID + название подарка |
| `adminmgmt` | ID пользователя → add/remove admin |
| `stats` | 6 stat cards (users, banned, balance, cases, gifts, admins) |
| `settings` | Placeholder для будущих тем |

### API Endpoints Used
| Endpoint | Method | Params |
|----------|--------|--------|
| `/api/admin/user-info` | POST | `{initData, userId}` |
| `/api/admin/top-up` | POST | `{initData, userId, amount}` |
| `/api/admin/give-gift` | POST | `{initData, userId, giftName}` |
| `/api/admin/add-admin` | POST | `{initData, adminId}` |
| `/api/admin/remove-admin` | POST | `{initData, adminId}` |
| `/api/admin/stats` | POST | `{initData}` |
| `/api/ban-user` | POST | `{initData, targetUserId}` |
| `/api/unban-user` | POST | `{initData, targetUserId}` |

### AdminPanel.css — Design Tokens
- `--accent: #6c5ce7` — purple accent for buttons/focus
- Glassmorphism background: `rgba(20, 22, 36, 0.92)` with `blur(20px)`
- Animations: `apFadeIn` (0.25s overlay), `apSlideUp` (0.3s sheet)
- Buttons: hover lift + brightness, active translateX(4px) on menu items
- Stat cards: 28px bold white values, uppercase labels

## Component Architecture

### Glass Component (реализовано)
```jsx
import Glass from './Glass'

<Glass variant="default" hover>
  <content />
</Glass>
```

Пропсы:
- `as`: 'div' | 'button' | 'a' (default: 'div')
- `variant`: 'default' | 'sm' | 'strong' | 'gradient' | 'liquid'
- `hover`: boolean — добавляет `.glass-hover` (lift + brightness on hover)
- `className`: string — дополнительные классы
- `style`: object — inline стили

### Page Transition (реализовано)
```css
.page-enter { opacity: 0; transform: translateY(8px); }
.page-enter-active { opacity: 1; transform: translateY(0); transition: var(--anim-speed, 0.25s) ease; }
```

Переменная `--anim-speed` управляет скоростью. По умолчанию 0.25s.

### Animation Presets (реализовано)
Управляются через `data-animation` на корневом элементе:
- `default` — 0.25s, translateY
- `fade` — 0.3s, только opacity
- `scale` — 0.2s, scale(0.97) → 1
- `none` — без анимаций

### Micro-interactions
`.glass-hover` — CSS класс для hover-эффектов на карточках (lift, яркость).
Определён в `index.css` с медиа-запросом `@media (hover: hover)` для мобил.

## Future Plan
1. Выделить админку в отдельный бандл (lazy load через React.lazy)
2. Добавить редактор пресетов с превью в реальном времени
3. Добавить кастомные анимации (Lottie для тем)
4. Сделать экспорт/импорт темы в JSON
5. Добавить A/B тестирование пресетов
6. Glass-компонент с пропсами через styled-components
7. Поиск пользователей по username (автокомплит)
8. Анимации переходов между экранами админки
