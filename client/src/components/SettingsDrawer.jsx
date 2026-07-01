import { useState, useEffect, useRef, useCallback } from 'react'
import './SettingsDrawer.css'

function SettingsDrawer({ onClose }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('sd_language') || 'ru')
  const [notifications, setNotifications] = useState(() => localStorage.getItem('sd_notifications') !== 'false')
  const [vibration, setVibration] = useState(() => localStorage.getItem('sd_vibration') !== 'false')
  const [animations, setAnimations] = useState(() => localStorage.getItem('sd_animations') !== 'false')

  const [dragY, setDragY] = useState(0)
  const [dragging, setDragging] = useState(false)
  const dragStartY = useRef(0)
  const sheetRef = useRef(null)

  useEffect(() => { localStorage.setItem('sd_language', language) }, [language])
  useEffect(() => { localStorage.setItem('sd_notifications', String(notifications)) }, [notifications])
  useEffect(() => { localStorage.setItem('sd_vibration', String(vibration)) }, [vibration])
  useEffect(() => { localStorage.setItem('sd_animations', String(animations)) }, [animations])

  const haptic = (style) => {
    try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(style || 'light') } catch {}
  }

  const toggleWithHaptic = (setter, value) => {
    haptic('light')
    setter(!value)
  }

  const handleTouchStart = useCallback((e) => {
    if (e.touches.length === 1) {
      dragStartY.current = e.touches[0].clientY
      setDragging(true)
    }
  }, [])

  const handleTouchMove = useCallback((e) => {
    if (!dragging) return
    const dy = e.touches[0].clientY - dragStartY.current
    if (dy > 0) setDragY(dy)
  }, [dragging])

  const handleTouchEnd = useCallback(() => {
    if (dragY > 100) {
      onClose()
    } else {
      setDragY(0)
    }
    setDragging(false)
  }, [dragY, onClose])

  return (
    <>
      <div className="sd-backdrop" onClick={onClose} style={dragging ? { opacity: 1 - (dragY / 300) } : undefined} />
      <div
        className="sd-sheet"
        ref={sheetRef}
        style={{ transform: dragging ? `translateY(${dragY}px)` : 'translateY(0)', transition: dragging ? 'none' : undefined }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="sd-drag-handle" onTouchStart={handleTouchStart}>
          <div className="sd-drag-bar" />
        </div>
        <div className="sd-inner">
          <div className="sd-header">
            <h2 className="sd-title">Настройки</h2>
            <button className="sd-close-btn" onClick={onClose}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M13 1L1 13M1 1l12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>

          <div className="sd-body">
            {/* Language */}
            <div className="sd-section">
              <div className="sd-row">
                <span className="sd-row-label">Язык / Language</span>
              </div>
              <div className="sd-lang-switch">
                <div className="sd-lang-slider" style={{ left: language === 'ru' ? '2px' : 'calc(50% + 1px)' }} />
                <button
                  className={`sd-lang-btn ${language === 'ru' ? 'active' : ''}`}
                  onClick={() => { if (language !== 'ru') { haptic('light'); setLanguage('ru') } }}
                >
                  <span className="sd-lang-flag">🇷🇺</span>
                  <span>Русский</span>
                </button>
                <button
                  className={`sd-lang-btn ${language === 'en' ? 'active' : ''}`}
                  onClick={() => { if (language !== 'en') { haptic('light'); setLanguage('en') } }}
                >
                  <span className="sd-lang-flag">🇬🇧</span>
                  <span>English</span>
                </button>
              </div>
            </div>

            {/* Notifications */}
            <div className="sd-section">
              <div className="sd-row">
                <span className="sd-row-label">Уведомления</span>
                <button
                  className={`jelly-switch ${notifications ? 'on' : ''}`}
                  role="switch"
                  aria-checked={notifications}
                  onClick={() => toggleWithHaptic(setNotifications, notifications)}
                >
                  <span className="jelly-switch-track">
                    <span className="jelly-switch-knob">
                      <span className="jelly-switch-knob-inner" />
                    </span>
                  </span>
                </button>
              </div>
            </div>

            {/* Vibration */}
            <div className="sd-section">
              <div className="sd-row">
                <span className="sd-row-label">Вибрация</span>
                <button
                  className={`jelly-switch ${vibration ? 'on' : ''}`}
                  role="switch"
                  aria-checked={vibration}
                  onClick={() => toggleWithHaptic(setVibration, vibration)}
                >
                  <span className="jelly-switch-track">
                    <span className="jelly-switch-knob">
                      <span className="jelly-switch-knob-inner" />
                    </span>
                  </span>
                </button>
              </div>
            </div>

            {/* Animations */}
            <div className="sd-section">
              <div className="sd-row">
                <span className="sd-row-label">Анимации</span>
                <button
                  className={`jelly-switch ${animations ? 'on' : ''}`}
                  role="switch"
                  aria-checked={animations}
                  onClick={() => toggleWithHaptic(setAnimations, animations)}
                >
                  <span className="jelly-switch-track">
                    <span className="jelly-switch-knob">
                      <span className="jelly-switch-knob-inner" />
                    </span>
                  </span>
                </button>
              </div>
            </div>

            {/* Links */}
            <div className="sd-section">
              <div className="sd-links-header">Cсылки</div>
              <a className="sd-link" href="https://t.me/helpshell" target="_blank" rel="noopener noreferrer">
                <span>Канал Quark</span>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M1 11L11 1M11 1H4.5M11 1V7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
              <a className="sd-link" href="https://t.me/helpshellbot" target="_blank" rel="noopener noreferrer">
                <span>Поддержка</span>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M1 11L11 1M11 1H4.5M11 1V7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
              <a className="sd-link" href="https://t.me/helpshell_games" target="_blank" rel="noopener noreferrer">
                <span>Игры Quark</span>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M1 11L11 1M11 1H4.5M11 1V7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default SettingsDrawer
