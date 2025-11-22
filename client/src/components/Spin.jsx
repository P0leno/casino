import { useState, useEffect, useRef } from 'react'
import './Spin.css'
import LottieAnimation from './LottieAnimation'
import { preloadGiftAnimations } from '../utils/giftLoader'

const gifts = [
  { name: 'bear', animation: '/gifts/bear.json' },
  { name: 'cake', animation: '/gifts/cake.json' },
  { name: 'cup', animation: '/gifts/cup.json' },
  { name: 'diamond', animation: '/gifts/diamond.json' },
  { name: 'flowers', animation: '/gifts/flowers.json' },
  { name: 'gift', animation: '/gifts/gift.json' },
  { name: 'heart', animation: '/gifts/heart.json' },
  { name: 'ring', animation: '/gifts/ring.json' },
  { name: 'rocket', animation: '/gifts/rocket.json' },
  { name: 'rose', animation: '/gifts/rose.json' }
]

function Spin() {
  const [spinning, setSpinning] = useState(false)
  const [available, setAvailable] = useState(true)
  const [timeLeft, setTimeLeft] = useState(0)
  const [rotation, setRotation] = useState(0)
  const [result, setResult] = useState(null)
  const wheelRef = useRef(null)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.BackButton.show()
      
      const handleBack = () => {
        window.history.back()
      }
      
      tg.BackButton.onClick(handleBack)
      
      return () => {
        tg.BackButton.hide()
        tg.BackButton.offClick(handleBack)
      }
    }
  }, [])

  useEffect(() => {
    checkAvailability()
    // Предзагрузка анимаций в фоне
    const giftNames = gifts.map(g => g.name)
    preloadGiftAnimations(giftNames)
  }, [])

  useEffect(() => {
    if (timeLeft > 0) {
      const timer = setTimeout(() => {
        setTimeLeft(timeLeft - 1)
      }, 1000)
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
        setTimeLeft(data.timeLeft)
      }
    } catch (error) {
      console.error('Error checking spin availability:', error)
    }
  }

  const handleSpin = async () => {
    if (!available || spinning) return

    setSpinning(true)
    setResult(null)

    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/spin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.success) {
        const giftIndex = gifts.findIndex(g => g.name === data.gift)
        const itemWidth = 120 // ширина одной плитки
        const totalWidth = gifts.length * itemWidth
        const targetPosition = (totalWidth * 10) + (giftIndex * itemWidth) + (itemWidth / 2) - (window.innerWidth / 2)
        
        setRotation(targetPosition)
        
        setTimeout(() => {
          setResult(data.gift)
          setSpinning(false)
          setAvailable(false)
          setTimeLeft(86400) // 24 часа
        }, 5000)
      } else {
        alert(data.message)
        setSpinning(false)
      }
    } catch (error) {
      alert('Ошибка при выполнении спина')
      setSpinning(false)
    }
  }

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  return (
    <div className="spin-page">
      <div className="spin-content">
        <div className="roulette-container">
          <div className="roulette-viewport">
            <div 
              ref={wheelRef}
              className="roulette-strip" 
              style={{ 
                transform: `translateX(${spinning ? -rotation : 0}px)`,
                transition: spinning ? 'transform 5s cubic-bezier(0.17, 0.67, 0.12, 0.99)' : 'none',
                animation: !spinning ? 'scroll-roulette 50s linear infinite' : 'none'
              }}
            >
              {/* Минимальная прокрутка для производительности */}
              {[...Array(8)].map((_, repeatIndex) => (
                gifts.map((gift, index) => (
                  <div
                    key={`${repeatIndex}-${gift.name}`}
                    className="roulette-item"
                  >
                    <LottieAnimation animationData={gift.animation} width={80} height={80} />
                  </div>
                ))
              ))}
            </div>
            <div className="roulette-pointer"></div>
          </div>
        </div>

        {result && (
          <div className="spin-result">
            <p>Вы выиграли:</p>
            <LottieAnimation animationData={gifts.find(g => g.name === result)?.animation} width={100} height={100} />
          </div>
        )}
      </div>

      <button 
        className={`spin-button-fixed ${!available || spinning ? 'disabled' : ''}`}
        onClick={handleSpin}
        disabled={!available || spinning}
      >
        <span className="button-main-text">
          {spinning ? 'Крутится...' : (available ? 'Крутить' : 'Недоступно')}
        </span>
        {!available && timeLeft > 0 && (
          <span className="button-timer-text">
            через {formatTime(timeLeft)}
          </span>
        )}
      </button>
    </div>
  )
}

export default Spin
