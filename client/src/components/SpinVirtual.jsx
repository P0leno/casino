import { useState, useEffect, useRef, useMemo } from 'react'
import './Spin.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import bearAnim from '../assets/bear.json'
import cakeAnim from '../assets/cake.json'
import cupAnim from '../assets/cup.json'
import diamondAnim from '../assets/diamond.json'
import flowersAnim from '../assets/flowers.json'
import giftAnim from '../assets/gift.json'
import heartAnim from '../assets/heart.json'
import ringAnim from '../assets/ring.json'
import rocketAnim from '../assets/rocket.json'
import roseAnim from '../assets/rose.json'

const gifts = [
  { name: 'bear', animation: bearAnim },
  { name: 'cake', animation: cakeAnim },
  { name: 'cup', animation: cupAnim },
  { name: 'diamond', animation: diamondAnim },
  { name: 'flowers', animation: flowersAnim },
  { name: 'gift', animation: giftAnim },
  { name: 'heart', animation: heartAnim },
  { name: 'ring', animation: ringAnim },
  { name: 'rocket', animation: rocketAnim },
  { name: 'rose', animation: roseAnim }
]

const ITEM_WIDTH = 120
const GIFTS_COUNT = 10

function SpinVirtual() {
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState(null)
  const [offset, setOffset] = useState(0)
  const [available, setAvailable] = useState(false)
  const [timeLeft, setTimeLeft] = useState(0)
  const [visibleCount, setVisibleCount] = useState(5)
  
  const viewportRef = useRef(null)
  const animationFrameRef = useRef(null)
  const targetOffsetRef = useRef(0)
  const startTimeRef = useRef(0)
  const durationRef = useRef(5000)

  // Вычисляем количество видимых элементов при монтировании и ресайзе
  useEffect(() => {
    const calculateVisibleCount = () => {
      if (viewportRef.current) {
        const viewportWidth = viewportRef.current.offsetWidth
        const itemsOnScreen = Math.ceil(viewportWidth / ITEM_WIDTH)
        // Рендерим на 2 больше для буфера (слева и справа)
        setVisibleCount(itemsOnScreen + 2)
      }
    }

    calculateVisibleCount()
    window.addEventListener('resize', calculateVisibleCount)
    return () => window.removeEventListener('resize', calculateVisibleCount)
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

  // Бесконечная прокрутка когда не крутится
  useEffect(() => {
    if (!spinning) {
      let lastTime = Date.now()
      const scroll = () => {
        const now = Date.now()
        const delta = (now - lastTime) / 1000
        lastTime = now
        
        setOffset(prev => {
          const newOffset = prev + (ITEM_WIDTH * GIFTS_COUNT * delta / 50) // 50 секунд на полный круг
          // Сбрасываем offset когда прошли полный круг
          return newOffset % (ITEM_WIDTH * GIFTS_COUNT)
        })
        
        animationFrameRef.current = requestAnimationFrame(scroll)
      }
      
      animationFrameRef.current = requestAnimationFrame(scroll)
      
      return () => {
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
        }
      }
    }
  }, [spinning])

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

    // Вызываем API для получения результата
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
        // Находим индекс выигранного подарка
        const winIndex = gifts.findIndex(g => g.name === data.gift)
        
        if (winIndex === -1) {
          alert('Ошибка: подарок не найден')
          setSpinning(false)
          return
        }
        
        // Рассчитываем финальную позицию
        // Указатель находится в центре viewport, нужно чтобы выигрышный элемент оказался под ним
        const viewportWidth = viewportRef.current?.offsetWidth || 600
        const centerOffset = viewportWidth / 2 - ITEM_WIDTH / 2
        
        // 5 полных кругов + позиция выигрыша - центральный offset
        const fullRotations = 5
        const targetPosition = fullRotations * (ITEM_WIDTH * GIFTS_COUNT) + winIndex * ITEM_WIDTH - centerOffset
        
        // Добавляем небольшой случайный сдвиг в рамках элемента для реалистичности
        const randomOffset = Math.random() * 40 - 20
        targetOffsetRef.current = targetPosition + randomOffset
        
        // Запускаем анимацию
        startTimeRef.current = Date.now()
        durationRef.current = 5000
        
        const animate = () => {
          const now = Date.now()
          const elapsed = now - startTimeRef.current
          const progress = Math.min(elapsed / durationRef.current, 1)
          
          // Easing function - cubic bezier
          const easeProgress = progress < 0.5
            ? 4 * progress * progress * progress
            : 1 - Math.pow(-2 * progress + 2, 3) / 2
          
          setOffset(easeProgress * targetOffsetRef.current)
          
          if (progress < 1) {
            animationFrameRef.current = requestAnimationFrame(animate)
          } else {
            // Анимация завершена
            setTimeout(() => {
              setResult(data.gift)
              setSpinning(false)
              setAvailable(false)
              setTimeLeft(86400) // 24 часа
              // Сбрасываем offset для следующего спина
              setOffset(0)
            }, 500)
          }
        }
        
        animationFrameRef.current = requestAnimationFrame(animate)
        
      } else {
        alert(data.message)
        setSpinning(false)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
      setSpinning(false)
    }
  }

  // Вычисляем какие элементы нужно рендерить
  const visibleItems = useMemo(() => {
    const items = []
    const startIndex = Math.floor(offset / ITEM_WIDTH)
    
    for (let i = 0; i < visibleCount; i++) {
      const index = (startIndex + i) % GIFTS_COUNT
      const position = (startIndex + i) * ITEM_WIDTH - offset
      
      items.push({
        gift: gifts[index],
        position,
        key: startIndex + i
      })
    }
    
    return items
  }, [offset, visibleCount])

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="spin-page">
      <BalanceBar />
      <div className="spin-content">
        <div className="roulette-container">
          <div className="roulette-viewport" ref={viewportRef}>
            <div className="roulette-pointer">▼</div>
            <div className="roulette-strip-virtual">
              {visibleItems.map((item) => (
                <div
                  key={item.key}
                  className="roulette-item"
                  style={{
                    position: 'absolute',
                    left: `${item.position}px`,
                    width: `${ITEM_WIDTH}px`
                  }}
                >
                  <LottieAnimation 
                    animationData={item.gift.animation} 
                    width={80} 
                    height={80} 
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {result && (
          <div className="spin-result">
            <p>Вы выиграли:</p>
            <div className="result-gift-large">
              <LottieAnimation 
                animationData={gifts.find(g => g.name === result).animation} 
                width={120} 
                height={120} 
              />
            </div>
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

export default SpinVirtual
