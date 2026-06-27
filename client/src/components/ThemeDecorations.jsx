import { useEffect, useState } from 'react'
import './ThemeDecorations.css'

const THEMES = {
  halloween: {
    elements: ['🎃', '🕸️', '👻', '🦇', '🧙', '🕷️', '💀'],
    count: 12,
    speed: 'slow',
    snow: false,
    corner: 'halloween',
  },
  newyear: {
    elements: ['❄️', '🎄', '⛄', '🦌', '🎅', '🌟', '✨'],
    count: 10,
    speed: 'slow',
    snow: true,
    snowCount: 30,
    corner: 'newyear',
  },
  cny: {
    elements: ['🧧', '🏮', '🐉', '🧨', '🪷', '🥟', '✨'],
    count: 8,
    speed: 'normal',
    snow: false,
    corner: 'cny',
  },
  easter: {
    elements: ['🐰', '🌸', '🌷', '🌼', '🐣', '🦋', '🥚'],
    count: 10,
    speed: 'slow',
    snow: false,
    corner: 'easter',
  },
  maximalism: {
    elements: ['✨', '🌟', '💎', '⭐', '🔥', '💫', '⚡'],
    count: 16,
    speed: 'fast',
    snow: false,
    corner: null,
  },
  valentine: {
    elements: ['❤️', '💖', '💗', '💕', '💝', '🌹', '💘'],
    count: 12,
    speed: 'slow',
    snow: false,
    corner: 'valentine',
  },
}

function ThemeDecorations() {
  const [theme, setTheme] = useState('default')
  const [particles, setParticles] = useState([])
  const [snowflakes, setSnowflakes] = useState([])

  useEffect(() => {
    const check = () => {
      const t = document.documentElement.getAttribute('data-theme') || 'default'
      setTheme(t)
    }
    check()
    const mo = new MutationObserver(check)
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => mo.disconnect()
  }, [])

  const cfg = THEMES[theme]

  useEffect(() => {
    if (!cfg) {
      setParticles([])
      setSnowflakes([])
      return
    }

    const items = []
    for (let i = 0; i < cfg.count; i++) {
      items.push({
        id: i,
        emoji: cfg.elements[i % cfg.elements.length],
        left: Math.random() * 100,
        delay: Math.random() * 8,
        duration: 8 + Math.random() * 12,
        size: 14 + Math.random() * 18,
        opacity: 0.15 + Math.random() * 0.25,
      })
    }
    setParticles(items)

    if (cfg.snow) {
      const flakes = []
      for (let i = 0; i < (cfg.snowCount || 30); i++) {
        flakes.push({
          id: i,
          left: Math.random() * 100,
          delay: Math.random() * 10,
          duration: 3 + Math.random() * 5,
          size: 2 + Math.random() * 4,
          opacity: 0.3 + Math.random() * 0.5,
          drift: -20 + Math.random() * 40,
        })
      }
      setSnowflakes(flakes)
    } else {
      setSnowflakes([])
    }
  }, [theme])

  if (!cfg || !particles.length) return null

  return (
    <>
      <div className="theme-decorations" aria-hidden="true">
        {particles.map(p => (
          <span
            key={p.id}
            className={`td-particle td-${cfg.speed}`}
            style={{
              left: `${p.left}%`,
              animationDelay: `${p.delay}s`,
              fontSize: `${p.size}px`,
              opacity: p.opacity,
            }}
          >
            {p.emoji}
          </span>
        ))}
        {snowflakes.map(s => (
          <span
            key={`snow-${s.id}`}
            className="td-snowflake"
            style={{
              left: `${s.left}%`,
              animationDelay: `${s.delay}s`,
              animationDuration: `${s.duration}s`,
              width: `${s.size}px`,
              height: `${s.size}px`,
              opacity: s.opacity,
              '--drift': `${s.drift}px`,
            }}
          />
        ))}
      </div>
      {cfg.corner && <div className={`td-corner-${cfg.corner}`} aria-hidden="true" />}
    </>
  )
}

export default ThemeDecorations
