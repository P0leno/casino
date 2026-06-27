# Design System — Casino Mini App

## Theme Engine

### CSS Variables (Tokens)
Все стили управляются через CSS-переменные в `:root`.  
Переменные делятся на 4 категории:

| Category | Prefix | Example |
|----------|--------|---------|
| Glass | `--glass-*` | `--glass-blur: blur(16px)` |
| Color | `--clr-*` | `--clr-accent: #3b82f6` |
| Spacing | `--sp-*` | `--sp-card-padding: 16px` |
| Radius | `--rd-*` | `--rd-card: 16px` |

### Preset Switching
Каждый preset — это блок `:root[data-theme="<name>"]` с переопределением токенов.

```css
:root[data-theme="minimalism"] {
  --clr-accent: #ffffff;
  --glass-bg: rgba(255,255,255,0.03);
  --glass-blur: blur(8px);
  --rd-card: 4px;
}

:root[data-theme="halloween"] {
  --clr-accent: #ff6b35;
  --glass-bg: rgba(255, 107, 53, 0.08);
  --glass-border: rgba(255, 107, 53, 0.2);
  --bg-primary: #0d0d0d;
}

:root[data-theme="newyear"] {
  --clr-accent: #ffd700;
  --glass-bg: rgba(212, 175, 55, 0.08);
  --glass-border: rgba(212, 175, 55, 0.2);
}

:root[data-theme="easter"] {
  --clr-accent: #f472b6;
  --glass-bg: rgba(244, 114, 182, 0.06);
  --glass-border: rgba(244, 114, 182, 0.15);
}

:root[data-theme="cny"] {
  --clr-accent: #dc2626;
  --glass-bg: rgba(220, 38, 38, 0.08);
  --glass-border: rgba(220, 38, 38, 0.2);
}

:root[data-theme="maximalism"] {
  --glass-bg: rgba(255,255,255,0.12);
  --glass-blur: blur(24px);
  --glass-shadow: 0 8px 48px rgba(0,0,0,0.4);
}
```

Переключение через JS: `document.documentElement.setAttribute('data-theme', 'halloween')`

### User Customization
В настройках админки — слайдеры для:
- **Blur** (4px–32px)
- **Opacity** (0.03–0.20 для `--glass-bg`)
- **Border opacity** (0.05–0.30)
- **Radius** (0–32px)
- **Accent color** (color picker)
- **Animation speed** (0x–3x)
- **Background** (light/dark/custom hex)

Все кастомные значения сохраняются в `localStorage`, при загрузке применяются поверх
выбранного пресета.

## Admin Panel Design (отдельное приложение)

### Architecture
Отдельный React-компонент `AdminPanel.jsx` со своим роутингом, НЕ вложенный в Profile.

### Layout
```
┌──────────────────────────────┐
│  👑 Админ панель     ✕       │  ← glass header с safe-area
├──────────────────────────────┤
│  🔍  Поиск пользователя...   │  ← поиск по ID/username
├──────────────────────────────┤
│  📊 Статистика               │  ← карточка-превью
│  ┌──────┬──────┬──────┐     │
│  │ Юзеры│ Кейсы│ Звёзд│     │
│  │ 1.2K │   12 │ 450K │     │
│  └──────┴──────┴──────┘     │
├──────────────────────────────┤
│  Меню                        │
│  ┌────────────────────────┐  │
│  │ 💰 Баланс / Топ-ап     │  │
│  │ 🎁 Выдача подарка      │  │
│  │ 👥 Управление админами │  │
│  │ 🚀 Краш                │  │
│  │ 🎲 Кейсы               │  │
│  │ 📋 Задания             │  │
│  │ 🔧 Настройки           │  │
│  │ 🎨 Тема оформления     │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

### Navigation
- Боковое меню (на десктопе) или bottom sheet (на мобилке)
- Каждый пункт открывает отдельный экран со своей формой
- Все экраны — компоненты внутри AdminPanel (без внешнего роутера)

### User Search
- Поле поиска в顶部
- При вводе — автокомплит (поиск по ID/username через `/api/admin/search-users`)
- Результат: карточка пользователя с кнопками (инфо, топ-ап, гивт, бан)

## Component Architecture

### Glass Component
```jsx
<Glass blur="16" opacity="0.06" border>
  <content />
</Glass>
```

Пропсы:
- `blur`: 4 | 8 | 12 | 16 | 24 | 32
- `opacity`: 0.03–0.20
- `border`: boolean
- `radius`: 0–32
- `hover`: boolean (подсветка при наведении)
- `as`: 'div' | 'button' | 'a'

### Page Transition
```css
.page-enter { opacity: 0; transform: translateY(8px); }
.page-enter-active { opacity: 1; transform: translateY(0); transition: 0.25s ease; }
```

### Animation Presets
Управляются через `data-animation`:
- `default` — 0.25s, translateY
- `fade` — 0.3s, просто opacity
- `scale` — 0.2s, scale(0.97) → 1
- `none` — без анимаций

## Future Plan
1. Выделить админку в отдельный бандл (lazy load через React.lazy)
2. Добавить редактор пресетов с превью в реальном времени
3. Добавить кастомные анимации (Lottie для тем)
4. Сделать экспорт/импорт темы в JSON
5. Добавить A/B тестирование пресетов
