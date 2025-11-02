import { useState, useEffect, useRef, useMemo } from 'react'
import './Spin.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import bearAnim from '../assets/bear.json'
import giftAnim from '../assets/gift.json'
import heartAnim from '../assets/heart.json'
import roseAnim from '../assets/rose.json'
import pawAnim from '../assets/paw.json'
import starAnim from '../assets/star.json'

const gifts = [
  { name: 'bear', animation: bearAnim },
  { name: 'gift', animation: giftAnim },
  { name: 'heart', animation: heartAnim },
  { name: 'rose', animation: roseAnim },
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
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  
  const viewportRef = useRef(null)
  const animationFrameRef = useRef(null)
  const targetOffsetRef = useRef(0)
  const startTimeRef = useRef(0)
  const durationRef = useRef(5000)

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

  const handleOpenModal = () => {
    setShowConfirmModal(true)
  }

  const handleCloseModal = () => {
    setShowConfirmModal(false)
  }

  const handleSpin = async () => {
    setIsProcessing(true)
    
    // Сначала делаем запрос к серверу
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
      
      setIsProcessing(false)
      
      if (data.success) {
        // Закрываем модалку
        setShowConfirmModal(false)
        
        const winIndex = gifts.findIndex(g => g.name === data.gift)
        
        if (winIndex === -1) {
          alert('Ошибка: подарок не найден')
          return
        }
        
        // Отменяем текущую анимацию если есть
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
        }
        
        // Устанавливаем состояние spinning и сбрасываем результаты
        setSpinning(true)
        setResult(null)
        setPawAmount(0)
        setStarAmount(0)
        
        // Небольшая задержка перед запуском анимации
        setTimeout(() => {
          const viewportWidth = viewportRef.current?.offsetWidth || 600
          const centerOffset = viewportWidth / 2 - ITEM_WIDTH / 2
          
          const fullRotations = 5
          const targetPosition = fullRotations * (ITEM_WIDTH * GIFTS_COUNT) + winIndex * ITEM_WIDTH - centerOffset
          
          const randomOffset = Math.random() * 40 - 20
          targetOffsetRef.current = targetPosition + randomOffset
          
          startTimeRef.current = Date.now()
          durationRef.current = 5000
          
          const animate = () => {
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
                setOffset(0)
              }, 500)
            }
          }
          
          animationFrameRef.current = requestAnimationFrame(animate)
        }, 100)
        
      } else {
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
      setShowConfirmModal(false)
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

      <button
        className={`spin-button-fixed ${spinning ? 'disabled' : ''}`}
        onClick={handleOpenModal}
        disabled={spinning}
      >
        {spinning ? (
          'Вращение...'
        ) : (
          <>
            <span className="button-main-text">Крутить</span>
            <span className="button-sub-text">Бомж кейс</span>
          </>
        )}
      </button>

      {showConfirmModal && (
        <div className="modal-overlay" onClick={isProcessing ? undefined : handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Бомж кейс</h3>
            <p>Стоимость: 5 ⭐</p>
            <div className="modal-buttons">
              <button 
                className="modal-button modal-button-confirm" 
                onClick={handleSpin}
                disabled={isProcessing}
              >
                {isProcessing ? 'Обработка...' : 'Крутить за 5 ⭐'}
              </button>
              <button 
                className="modal-button modal-button-cancel" 
                onClick={handleCloseModal}
                disabled={isProcessing}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PaidSpin
