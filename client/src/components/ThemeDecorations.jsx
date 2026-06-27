import { useEffect, useState } from 'react'
import './ThemeDecorations.css'

const THEMES = {
  halloween: {
    elements: ['🎃', '🕸️', '👻', '🦇', '🧙', '🕷️', '💀'],
    count: 12,
    speed: 'slow',
  },
  newyear: {
    elements: ['❄️', '🎄', '⛄', '🦌', '🎅', '🌟', '✨'],
    count: 15,
    speed: 'slow',
  },
  cny: {
    elements: ['🧧', '🏮', '🐉', '🧨', '🪷', '🥟', '✨'],
    count: 10,
    speed: 'normal',
  },
  easter: {
    elements: ['🐰', '🌸', '🌷', '🌼', '🐣', '🦋', '🥚'],
    count: 12,
    speed: 'slow',
  },
  maximalism: {
    elements: ['✨', '🌟', '💎', '⭐', '🔥', '💫', '⚡'],
    count: 18,
    speed: 'fast',
  },
  valentine: {
    elements: ['❤️', '💖', '💗', '💕', '💝', '🌹', '💘'],
    count: 14,
    speed: 'slow',
  },
}

function ThemeDecorations() {
  const [theme, setTheme] = useState('default')
  const [particles, setParticles] = useState([])

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
  }, [theme])

  if (!cfg || !particles.length) return null

  return (
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
    </div>
  )
}

export default ThemeDecorations
