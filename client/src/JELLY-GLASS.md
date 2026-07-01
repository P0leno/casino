# JellyGlass UI

Система стеклянно-желейных переключателей для Casinomood Telegram Mini App.

## Именование

Все компоненты JellyGlass используют префикс `jelly-`:

| Компонент | CSS-класс              | Где используется        |
|-----------|------------------------|-------------------------|
| Тоггл     | `.jelly-switch`        | SettingsDrawer          |
| Индикатор табов | `.jelly-indicator` | Profile tabs, TabBar    |
| Пилля категорий | `.jelly-pill`      | Profile inventory       |

## CSS-переменные (в `:root`)

```css
--jelly-spring: 0.34, 1.56, 0.64, 1;
--jelly-duration: 0.5s;
--jelly-press-scale: 0.92;
--jelly-glow: 0 0 16px rgba(59, 130, 246, 0.3);
```

## Анимации

### Spring (cubic-bezier)
```
cubic-bezier(0.34, 1.56, 0.64, 1)
```
- Overshoot: ~1.12×
- Settle time: ~0.5s
- Характер: упругий, желейный

### Press
```css
transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
transform: scale(0.92);
```

### Bounce (для индикатора табов)
```css
@keyframes jellyBounce {
  0%   { transform: scale(1); }
  25%  { transform: scaleY(1.15) scaleX(1.08); }
  50%  { transform: scaleY(0.92) scaleX(0.95); }
  75%  { transform: scaleY(1.03) scaleX(1.02); }
  100% { transform: scale(1); }
}
```

## Принципы

1. Все `jelly-*` элементы используют `--jelly-spring`
2. Все нажатия имеют `scale(0.92)` отдачу
3. Стекло = `backdrop-filter: blur(8px)` + `border: 1px solid rgba(255,255,255,0.06)` + `box-shadow`
4. Knob/пузырёк = градиент на белую гамму с тенью для 3D-глубины
5. В active/on состоянии — голубое свечение `--jelly-glow`
