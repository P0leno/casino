import { useState, useEffect, useRef, useMemo } from 'react'
import './Spin.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import pawAnim from '../assets/paw.json'
import starAnim from '../assets/star.json'

const gifts = [
  { name: 'bear', animation: '/gifts/bear.json' },
  { name: 'gift', animation: '/gifts/gift.json' },
  { name: 'heart', animation: '/gifts/heart.json' },
  { name: 'rose', animation: '/gifts/rose.json' },
  { name: 'paw', animation: pawAnim },
  { name: 'star', animation: starAnim }
]

const ITEM_WIDTH = 120
const GIFTS_COUNT = 6

function PaidSpin({ onNavigateToTopUp }) {
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState(null)
  const [pawAmount, setPawAmount] = useState(0)
  const [starAmount, setStarAmount] = useState(0)
  const [offset, setOffset] = useState(0)
  const [visibleCount, setVisibleCount] = useState(5)
  const [lastClickTime, setLastClickTime] = useState(0)
  const [isProcessing, setIsProcessing] = useState(false)
  const [fastSpin, setFastSpin] = useState(false) // Быстрый запуск
  
  const viewportRef = useRef(null)
  const animationFrameRef = useRef(null)
  const targetOffsetRef = useRef(0)
  const startTimeRef = useRef(0)
  const durationRef = useRef(5000)
  const fastSpinRef = useRef(false)

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
    const calculateVisibleCount = () => {
      if (viewportRef.current) {
        const viewportWidth = viewportRef.current.offsetWidth
        const itemsOnScreen = Math.ceil(viewportWidth / ITEM_WIDTH)
        setVisibleCount(itemsOnScreen + 2)
      }
    }

    calculateVisibleCount()
    window.addEventListener('resize', calculateVisibleCount)
    return () => window.removeEventListener('resize', calculateVisibleCount)
  }, [])

  useEffect(() => {
    if (!spinning) {
      let lastTime = Date.now()
      const scroll = () => {
        const now = Date.now()
        const delta = (now - lastTime) / 1000
        lastTime = now
        
        setOffset(prev => {
          const newOffset = prev + (ITEM_WIDTH * GIFTS_COUNT * delta / 50)
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

  const handleSpin = async () => {
    if (isProcessing) return
    
    // Если включен быстрый запуск, ставим флаг сразу
    if (fastSpin) {
      fastSpinRef.current = true
    }
    
    setIsProcessing(true)
    
    // Отменяем текущую анимацию если есть
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
    
    setResult(null)
    setPawAmount(0)
    setStarAmount(0)
    
    // Ждем 50ms для возможности второго клика (кнопка остается активной)
    await new Promise(resolve => setTimeout(resolve, 50))
    
    // Теперь блокируем кнопку визуально
    setSpinning(true)
    
    // Делаем запрос к серверу
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      console.log('Sending paid-spin request to:', `${apiUrl}/api/paid-spin`)
      
      const response = await fetch(`${apiUrl}/api/paid-spin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      console.log('Response status:', response.status)
      const data = await response.json()
      console.log('Response data:', data)
      
      if (data.success) {
        const winIndex = gifts.findIndex(g => g.name === data.gift)
        
        if (winIndex === -1) {
          alert('Ошибка: подарок не найден')
          setSpinning(false)
          setIsProcessing(false)
          return
        }
        
        // Если был двойной клик - показываем результат сразу
        if (fastSpinRef.current) {
          setResult(data.gift)
          setPawAmount(data.paw_count || 0)
          setStarAmount(data.star_count || 0)
          setSpinning(false)
          setIsProcessing(false)
          setOffset(0)
          fastSpinRef.current = false
          return
        }
        
        // Запуск анимации
        const viewportWidth = viewportRef.current?.offsetWidth || 600
        const centerOffset = viewportWidth / 2 - ITEM_WIDTH / 2
        
        const fullRotations = 5
        const targetPosition = fullRotations * (ITEM_WIDTH * GIFTS_COUNT) + winIndex * ITEM_WIDTH - centerOffset
        
        const randomOffset = Math.random() * 40 - 20
        targetOffsetRef.current = targetPosition + randomOffset
        
        startTimeRef.current = Date.now()
        durationRef.current = 5000
        
        const animate = () => {
            // Проверяем, нужно ли прервать анимацию (двойной клик)
            if (fastSpinRef.current) {
              if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current)
              }
              setResult(data.gift)
              setPawAmount(data.paw_count || 0)
              setStarAmount(data.star_count || 0)
              setSpinning(false)
              setIsProcessing(false)
              setOffset(0)
              fastSpinRef.current = false
              return
            }
            
            const now = Date.now()
            const elapsed = now - startTimeRef.current
            const progress = Math.min(elapsed / durationRef.current, 1)
            
            const easeProgress = progress < 0.5
              ? 4 * progress * progress * progress
              : 1 - Math.pow(-2 * progress + 2, 3) / 2
            
            setOffset(easeProgress * targetOffsetRef.current)
            
            if (progress < 1) {
              animationFrameRef.current = requestAnimationFrame(animate)
            } else {
              setTimeout(() => {
                setResult(data.gift)
                setPawAmount(data.paw_count || 0)
                setStarAmount(data.star_count || 0)
                setSpinning(false)
                setIsProcessing(false)
                setOffset(0)
              }, 500)
            }
        }
        
        animationFrameRef.current = requestAnimationFrame(animate)
        
      } else {
        setSpinning(false)
        setIsProcessing(false)
        if (data.needTopUp) {
          const tg = window.Telegram?.WebApp
          if (tg && tg.showAlert) {
            tg.showAlert('Недостаточно звезд')
          } else {
            alert('Недостаточно звезд')
          }
        } else {
          const tg = window.Telegram?.WebApp
          if (tg && tg.showAlert) {
            tg.showAlert(data.message || 'Ошибка')
          } else {
            alert(data.message || 'Ошибка')
          }
        }
      }
    } catch (error) {
      setSpinning(false)
      setIsProcessing(false)
      const tg = window.Telegram?.WebApp
      if (tg && tg.showAlert) {
        tg.showAlert('Ошибка соединения с сервером')
      } else {
        alert('Ошибка соединения с сервером')
      }
    }
  }

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

  return (
    <div className="spin-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
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
            <div className="result-gift-large" style={{position: 'relative'}}>
              <LottieAnimation 
                animationData={gifts.find(g => g.name === result).animation} 
                width={120} 
                height={120} 
              />
              {result === 'paw' && pawAmount > 0 && (
                <div className="result-amount">×{pawAmount}</div>
              )}
              {result === 'star' && starAmount > 0 && (
                <div className="result-amount">×{starAmount}</div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="spin-controls">
        <button
          className={`spin-button-fixed ${spinning ? 'disabled' : ''}`}
          onClick={handleSpin}
          disabled={spinning}
        >
          {spinning ? (
            'Вращение...'
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="button-main-text">Крутить за 5</span>
              <LottieAnimation animationData={starAnim} width={24} height={24} />
            </div>
          )}
        </button>
        
        {!spinning && (
          <div className="fast-spin-toggle">
            <span className="toggle-label">Быстрый запуск</span>
            <label className="switch">
              <input 
                type="checkbox" 
                className="toggle" 
                checked={fastSpin}
                onChange={(e) => setFastSpin(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>
        )}
      </div>
    </div>
  )
}

export default PaidSpin
