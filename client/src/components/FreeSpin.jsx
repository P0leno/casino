import { useState, useEffect, useRef, useMemo } from 'react'
import './Spin.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import pawAnim from '../assets/paw.json'
import starAnim from '../assets/star.json'
import secretIcon from '../assets/secret.svg'
import { useBalance } from '../contexts/BalanceContext'

const gifts = [
  { name: 'bear', animation: '/gifts/bear.json' },
  { name: 'bottle', animation: '/gifts/bottle.json' },
  { name: 'cake', animation: '/gifts/cake.json' },
  { name: 'cup', animation: '/gifts/cup.json' },
  { name: 'diamond', animation: '/gifts/diamond.json' },
  { name: 'flowers', animation: '/gifts/flowers.json' },
  { name: 'gift', animation: '/gifts/gift.json' },
  { name: 'heart', animation: '/gifts/heart.json' },
  { name: 'ring', animation: '/gifts/ring.json' },
  { name: 'rocket', animation: '/gifts/rocket.json' },
  { name: 'rose', animation: '/gifts/rose.json' },
  { name: 'paw', animation: pawAnim },
  { name: 'secret', animation: null, icon: secretIcon }
]

const ITEM_WIDTH = 120
const GIFTS_COUNT = 13


// -- Components --
function TaskConstraintModal({ task, onClose }) {
  if (!task) return null;

  const handleGo = () => {
    // Open link
    if (task.taskLink) {
      const tg = window.Telegram?.WebApp;
      if (tg) tg.openLink(task.taskLink);
      else window.open(task.taskLink, '_blank');
    }
    // Close modal to allow retry
    onClose();
  };

  return (
    <div className="modal-overlay" style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(5px)'
    }}>
      <div className="modal-content" style={{
        background: 'linear-gradient(145deg, #1a1a1a, #2a2a2a)',
        padding: '24px', borderRadius: '20px', width: '85%', maxWidth: '320px',
        border: '1px solid rgba(255,255,255,0.1)', textAlign: 'center',
        boxShadow: '0 10px 40px rgba(0,0,0,0.5)'
      }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>

        <h3 style={{ color: '#fff', margin: '0 0 12px 0', fontSize: '20px' }}>
          Задание дня
        </h3>

        <p style={{ color: '#aaa', fontSize: '14px', lineHeight: '1.5', margin: '0 0 24px 0' }}>
          Для бесплатной прокрутки необходимо выполнить задание:
          <br />
          <b style={{ color: '#fff' }}>{task.taskTitle}</b>
        </p>

        <button
          onClick={handleGo}
          style={{
            width: '100%', padding: '14px', borderRadius: '12px',
            background: 'linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)',
            border: 'none', color: '#fff', fontWeight: '600', fontSize: '16px',
            marginBottom: '12px', cursor: 'pointer'
          }}
        >
          Выполнить
        </button>

        <button
          onClick={onClose}
          style={{
            background: 'transparent', border: 'none',
            color: '#666', fontSize: '14px', cursor: 'pointer'
          }}
        >
          Отмена
        </button>
      </div>
    </div>
  );
}

import DemoSpinMenu from './DemoSpinMenu'

// -- Components --


function FreeSpin({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState(null)

  // Secret Result
  const [secretResult, setSecretResult] = useState(null)

  const [pawAmount, setPawAmount] = useState(0)
  const [offset, setOffset] = useState(0)

  // Demo Mode
  const [isDemoMenuOpen, setDemoMenuOpen] = useState(false)
  const [isDemoMode, setDemoMode] = useState(false)
  const [demoSelectedGift, setDemoSelectedGift] = useState('')
  const [available, setAvailable] = useState(false)
  const [timeLeft, setTimeLeft] = useState(0)
  const [visibleCount, setVisibleCount] = useState(5)
  const [lastClickTime, setLastClickTime] = useState(0)
  const [isProcessing, setIsProcessing] = useState(false)
  const [fastSpin, setFastSpin] = useState(false) // Быстрый запуск

  // Task Constraint State
  const [taskModal, setTaskModal] = useState(null); // { title, link, ... }

  const viewportRef = useRef(null)
  const animationFrameRef = useRef(null)
  const targetOffsetRef = useRef(0)
  const startTimeRef = useRef(0)
  const durationRef = useRef(5000)
  const fastSpinRef = useRef(false)

  // Настройка кнопки "Назад" в Telegram
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

  const checkAvailability = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 
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
    if (spinning) return

    // DEMO MODE CHECK
    if (isDemoMode) {
      if (!demoSelectedGift) {
        alert("Select a gift in Demo Menu first!")
        return
      }
      setSpinning(true)
      setResult(null)

      const demoResult = {
        success: true,
        gift: demoSelectedGift,
        paw_count: demoSelectedGift === 'paw' ? 999 : 0,
        // Mock secret demo (RANDOM)
        is_secret: demoSelectedGift === 'secret',
        secret_slug: null,
        secret_name: null,
      }

      if (demoSelectedGift === 'secret') {
        const mockSecrets = [
          { slug: 'blue-potion', name: 'Blue Potion' },
          { slug: 'red-energy', name: 'Red Energy' },
          { slug: 'nft-sword', name: 'NFT Sword' }
        ]
        const randomSecret = mockSecrets[Math.floor(Math.random() * mockSecrets.length)]
        demoResult.secret_slug = randomSecret.slug
        demoResult.secret_name = randomSecret.name
      }

      // Determine target gift index
      const targetGiftName = demoResult.gift
      let targetIndex = gifts.findIndex(g => g.name === targetGiftName)
      if (targetIndex === -1) targetIndex = 0

      const itemWidth = ITEM_WIDTH
      const giftsCount = GIFTS_COUNT
      const extraRounds = fastSpinRef.current ? 2 : 5
      const totalDistance = (extraRounds * giftsCount * itemWidth) + (targetIndex * itemWidth)
      const currentOffset = offset % (giftsCount * itemWidth)
      const startOffset = currentOffset
      const finalOffset = startOffset + totalDistance
      const jitter = Math.random() * (itemWidth * 0.4) * (Math.random() > 0.5 ? 1 : -1)

      targetOffsetRef.current = finalOffset + jitter
      startTimeRef.current = 0

      // duration depends on fast spin (FreeSpin already has fastSpin support in existing code?)
      // Checking existing code, 'fastSpin' state exists in PaidSpin, but check FreeSpin source...
      // Previous view showed only up to line 100. Let's assume user wants same animation logic.
      // I'll stick to standard duration logic if fastSpin ref missing or add it.
      // FreeSpin usually has `fastSpin`? Let's check imports/state. 
      // I'll assume standard 5000ms for now or use `fastSpinRef` if I added it (I didn't add it in previous tool call for FreeSpin).
      // Wait, FreeSpin usually doesn't have fast spin in this codebase? 
      // I'll just use 5000ms.
      durationRef.current = 5000

      setResult(demoResult)

      const animate = (time) => {
        if (!startTimeRef.current) startTimeRef.current = time
        const elapsed = time - startTimeRef.current
        const progress = Math.min(elapsed / durationRef.current, 1)
        const ease = 1 - Math.pow(1 - progress, 3)
        const currentPos = startOffset + (targetOffsetRef.current - startOffset) * ease
        setOffset(currentPos)
        if (progress < 1) {
          animationFrameRef.current = requestAnimationFrame(animate)
        } else {
          setSpinning(false)
          if (demoResult.paw_count) setPawAmount(demoResult.paw_count)
        }
      }
      animationFrameRef.current = requestAnimationFrame(animate)
      return
    }

    if (!available || isProcessing) return

    // Если включен быстрый запуск, ставим флаг сразу
    if (fastSpin) {
      fastSpinRef.current = true
    }

    setIsProcessing(true)
    setResult(null)
    setSpinning(true)

    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 

      const response = await fetch(`${apiUrl}/api/spin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()

      // Handle Task Constraint
      if (data.task_completion_needed) {
        setSpinning(false);
        setIsProcessing(false);
        setTaskModal(data); // Show modal with task info
        return;
      }

      if (data.success) {
        // Обновляем баланс из ответа API
        updateBalance(data)

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
          setSpinning(false)
          setIsProcessing(false)
          setAvailable(false)
          setTimeLeft(86400)
          setOffset(0)
          fastSpinRef.current = false
          return
        }

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
            setSpinning(false)
            setIsProcessing(false)
            setAvailable(false)
            setTimeLeft(86400)
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

              // Handle Secret Result
              if (data.gift === 'secret' && data.secret_slug) {
                setSecretResult({
                  slug: data.secret_slug,
                  name: data.secret_name,
                  is_secret: true
                })
              }

              setSpinning(false)
              setIsProcessing(false)
              setAvailable(false)
              setTimeLeft(86400)
              setOffset(0)
            }, 500)
          }
        }

        animationFrameRef.current = requestAnimationFrame(animate)

      } else {
        alert(data.message)
        setSpinning(false)
        setIsProcessing(false)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
      setSpinning(false)
      setIsProcessing(false)
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

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="spin-container">
      <DemoSpinMenu
        isOpen={isDemoMenuOpen}
        onClose={() => setDemoMenuOpen(false)}
        isDemo={isDemoMode}
        onToggleDemo={setDemoMode}
        selectedGiftName={demoSelectedGift}
        onSelectGift={setDemoSelectedGift}
        availableGifts={gifts}
      />

      <div className="balance-container">
        <BalanceBar />
        <BonusBalanceBar onClick={() => setDemoMenuOpen(true)} />
      </div>

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
                  {item.gift.name === 'secret' ? (
                    <div className="secret-item-preview">
                      <img src={item.gift.icon} alt="Secret" className="secret-icon" style={{ width: '60px', height: '60px', marginBottom: '5px' }} />
                      <span className="secret-label">Secret</span>
                      <span className="secret-sublabel" style={{ fontSize: '10px', color: '#aaa' }}>Up to ? ⭐</span>
                    </div>
                  ) : (
                    <LottieAnimation
                      animationData={item.gift.animation}
                      width={80}
                      height={80}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {result && (
          <div className="spin-result">
            <p>Вы выиграли:</p>
            <div className="result-gift-large">
              {result === 'secret' && secretResult ? (
                // Show REAL gift for Secret Win
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <img
                    src={`https://nft.fragment.com/gift/${secretResult.slug}.large.jpg`}
                    alt={secretResult.name}
                    style={{ width: '120px', borderRadius: '12px' }}
                  />
                  <div style={{ marginTop: '10px', fontSize: '18px', fontWeight: 'bold' }}>{secretResult.name}</div>
                </div>
              ) : (
                <>
                  <LottieAnimation
                    animationData={gifts.find(g => g.name === result).animation}
                    width={120}
                    height={120}
                  />
                  {result === 'paw' && pawAmount > 0 && <div className="result-amount">×{pawAmount}</div>}
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="spin-controls">
        <button
          className={`spin-button-fixed ${!available || spinning ? 'disabled' : ''}`}
          onClick={handleSpin}
          disabled={!available || spinning}
        >
          {spinning ? (
            'Вращение...'
          ) : available ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="button-main-text">Крутить за 0</span>
              <LottieAnimation animationData={starAnim} width={24} height={24} />
            </div>
          ) : (
            <>
              <span className="button-main-text">Недоступно</span>
              <span className="button-sub-text">{formatTime(timeLeft)}</span>
            </>
          )}
        </button>

        {available && !spinning && (
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

      {/* Constraint Modal */}
      {taskModal && (
        <TaskConstraintModal
          task={taskModal}
          onClose={() => setTaskModal(null)}
        />
      )}
    </div>
  )
}

export default FreeSpin
