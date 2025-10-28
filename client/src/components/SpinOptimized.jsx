import { useState, useEffect, useRef, useMemo } from 'react'
import './Spin.css'

// Простые эмодзи для максимальной производительности
const getGiftEmoji = (giftName) => {
  const emojiMap = {
    bear: '🧸',
    cake: '🎂',
    cup: '🏆',
    diamond: '💎',
    flowers: '💐',
    gift: '🎁',
    heart: '❤️',
    ring: '💍',
    rocket: '🚀',
    rose: '🌹'
  }
  return emojiMap[giftName] || '🎁'
}

const giftNames = ['bear', 'cake', 'cup', 'diamond', 'flowers', 'gift', 'heart', 'ring', 'rocket', 'rose']

function SpinOptimized() {
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState(null)
  const [rotation, setRotation] = useState(0)
  const [available, setAvailable] = useState(false)
  const [timeLeft, setTimeLeft] = useState(0)
  const viewportRef = useRef(null)

  // Мемоизация элементов рулетки
  const rouletteItems = useMemo(() => {
    return [...Array(6)].flatMap((_, repeatIndex) =>
      giftNames.map((giftName) => ({
        id: `${repeatIndex}-${giftName}`,
        emoji: getGiftEmoji(giftName),
        name: giftName
      }))
    )
  }, [])

  useEffect(() => {
    checkAvailability()
  }, [])

  useEffect(() => {
    if (timeLeft > 0) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000)
      return () => clearTimeout(timer)
    } else if (timeLeft === 0 && !available) {
      setAvailable(true)
    }
  }, [timeLeft, available])

  const checkAvailability = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/check-spin-available`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid) {
        setAvailable(data.available)
        setTimeLeft(data.timeLeft || 0)
      }
    } catch (error) {
      console.error('Error checking availability:', error)
    }
  }

  const handleSpin = async () => {
    if (!available || spinning) return

    setSpinning(true)
    setResult(null)

    const randomIndex = Math.floor(Math.random() * 10)
    const basePosition = 120 * 25
    const offset = (randomIndex * 120) + Math.random() * 60 - 30
    const finalRotation = basePosition + offset

    setRotation(finalRotation)

    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'

      const response = await fetch(`${apiUrl}/api/spin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.success) {
        setTimeout(() => {
          setResult(data.gift)
          setSpinning(false)
          setAvailable(false)
          setTimeLeft(86400)
        }, 5000)
      } else {
        alert(data.message)
        setSpinning(false)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
      setSpinning(false)
    }
  }

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="spin-page">
      <div className="spin-content">
        <div className="roulette-container" ref={viewportRef}>
          <div className="roulette-viewport">
            <div className="roulette-pointer">▼</div>
            <div
              className="roulette-strip"
              style={{
                transform: `translate3d(${spinning ? -rotation : 0}px, 0, 0)`,
                transition: spinning ? 'transform 5s cubic-bezier(0.17, 0.67, 0.12, 0.99)' : 'none',
                animation: !spinning ? 'scroll-roulette 50s linear infinite' : 'none'
              }}
            >
              {rouletteItems.map((item) => (
                <div key={item.id} className="roulette-item">
                  <div className="gift-placeholder">
                    <span className="gift-emoji">{item.emoji}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {result && (
          <div className="spin-result">
            <p>Вы выиграли:</p>
            <div className="result-gift-emoji">{getGiftEmoji(result)}</div>
          </div>
        )}
      </div>

      <button
        className={`spin-button-fixed ${!available || spinning ? 'disabled' : ''}`}
        onClick={handleSpin}
        disabled={!available || spinning}
      >
        {spinning ? (
          'Вращение...'
        ) : available ? (
          <>
            <span className="button-main-text">Крутить</span>
            <span className="button-sub-text">Фри спин</span>
          </>
        ) : (
          <>
            <span className="button-main-text">Недоступно</span>
            <span className="button-sub-text">{formatTime(timeLeft)}</span>
          </>
        )}
      </button>
    </div>
  )
}

export default SpinOptimized
