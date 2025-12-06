import { useState, useEffect, useRef } from 'react'
import './Crash.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import { useBalance } from '../contexts/BalanceContext'
import crashAnim from '../assets/crash.json'

function Crash({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const [multiplier, setMultiplier] = useState(1.00)
  const [isRunning, setIsRunning] = useState(false)
  const [history, setHistory] = useState([])
  const [crashed, setCrashed] = useState(false)
  const [bets, setBets] = useState([])
  const [userBet, setUserBet] = useState(null)
  const [showBetModal, setShowBetModal] = useState(false)
  const [betAmount, setBetAmount] = useState(25)
  
  const previousIsRunning = useRef(false)
  const crashedTimeoutRef = useRef(null)
  const wsRef = useRef(null)

  const tg = window.Telegram?.WebApp
  const user = tg?.initDataUnsafe?.user

  useEffect(() => {
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

  // WebSocket подключение (без polling fallback)
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
    const wsUrl = apiUrl.replace('https://', 'wss://').replace('http://', 'ws://')
    
    const connectWebSocket = () => {
      try {
        // Добавляем initData как query параметр для авторизации
        const initData = window.Telegram?.WebApp?.initData || ''
        const wsUrlWithAuth = `${wsUrl}/api/crash/ws?initData=${encodeURIComponent(initData)}`
        const ws = new WebSocket(wsUrlWithAuth)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('🔌 WebSocket connected to crash game')
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            handleGameStateUpdate(data)
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
        }

        ws.onclose = () => {
          console.log('🔌 WebSocket disconnected, reconnecting in 3s...')
          // Переподключение через 3 секунды
          setTimeout(connectWebSocket, 3000)
        }
      } catch (error) {
        console.error('WebSocket creation error:', error)
        // Переподключение через 3 секунды
        setTimeout(connectWebSocket, 3000)
      }
    }

    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const handleGameStateUpdate = (data) => {
    setMultiplier(data.currentMultiplier)
    setHistory(data.history)
    setBets(data.bets || [])
    
    // Находим ставку текущего пользователя
    if (user) {
      const myBet = data.bets?.find(b => b.userId === user.id)
      setUserBet(myBet || null)
    }
    
    // Определяем краш: переход из running в stopped
    if (previousIsRunning.current && !data.isRunning) {
      console.log('КРАШ ОБНАРУЖЕН! Multiplier:', data.currentMultiplier)
      setCrashed(true)
      
      // Вибрация при краше (3 раза)
      if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('heavy')
        setTimeout(() => tg.HapticFeedback.impactOccurred('heavy'), 100)
        setTimeout(() => tg.HapticFeedback.impactOccurred('heavy'), 200)
      }
      
      // Сбрасываем crashed через 3 секунды
      if (crashedTimeoutRef.current) {
        clearTimeout(crashedTimeoutRef.current)
      }
      crashedTimeoutRef.current = setTimeout(() => {
        setCrashed(false)
      }, 3000)
    }
    
    // Обновляем состояние isRunning и сохраняем предыдущее
    previousIsRunning.current = data.isRunning
    setIsRunning(data.isRunning)
    
    // Если начался новый раунд - сбрасываем crashed
    if (data.isRunning && crashed) {
      setCrashed(false)
    }
  }

  const getMultiplierColor = () => {
    if (crashed) return '#ff4444'
    if (multiplier >= 10) return '#ffd700'
    if (multiplier >= 5) return '#ff8c00'
    if (multiplier >= 2) return '#00ff88'
    return '#ffffff'
  }

  const handlePlaceBet = async () => {
    if (!user || betAmount < 25) return

    try {
      const initData = tg?.initData
      if (!initData) {
        if (tg) tg.showAlert('Ошибка авторизации')
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/crash/bet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          amount: betAmount
        })
      })

      const data = await response.json()
      
      if (response.ok) {
        updateBalance(data)
        setShowBetModal(false)
      } else {
        if (tg) {
          tg.showAlert(data.detail || 'Ошибка при размещении ставки')
        }
      }
    } catch (error) {
      console.error('Error placing bet:', error)
      if (tg) {
        tg.showAlert('Ошибка соединения')
      }
    }
  }

  const handleCashout = async () => {
    if (!user || !userBet) return

    try {
      const initData = tg?.initData
      if (!initData) {
        if (tg) tg.showAlert('Ошибка авторизации')
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/crash/cashout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      
      if (!response.ok || !data.success) {
        if (tg) {
          tg.showAlert(data.error || 'Ошибка')
        }
      } else {
        updateBalance(data)
      }
    } catch (error) {
      console.error('Error cashing out:', error)
    }
  }

  const handleCancelBet = async () => {
    if (!user) return

    try {
      const initData = tg?.initData
      if (!initData) {
        if (tg) tg.showAlert('Ошибка авторизации')
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/crash/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      
      if (!response.ok || !data.success) {
        if (tg) {
          tg.showAlert(data.error || 'Ошибка отмены ставки')
        }
      }
    } catch (error) {
      console.error('Error canceling bet:', error)
    }
  }

  const isMobile = window.Telegram?.WebApp?.platform === 'android' || 
                   window.Telegram?.WebApp?.platform === 'ios'
  const safeAreaBottom = tg?.safeAreaInset?.bottom || tg?.contentSafeAreaInset?.bottom || 0

  return (
    <div className="crash-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />

      <div className="crash-game-area">
        {/* Сеточка фона - интенсивность зависит от коэффициента */}
        <div 
          className={`crash-grid ${isRunning ? 'running' : ''} ${crashed ? 'crashed' : ''}`}
          style={{
            animationDuration: isRunning ? `${Math.max(0.5, 3 - (multiplier * 0.2))}s` : '3s'
          }}
        >
          <div className="grid-lines-horizontal">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="grid-line"></div>
            ))}
          </div>
          <div className="grid-lines-vertical">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="grid-line"></div>
            ))}
          </div>
        </div>

        {/* Ракета на фоне */}
        {isRunning && (
          <div className="crash-rocket-center">
            <LottieAnimation 
              animationData={crashAnim} 
              width={80} 
              height={80}
              loop={true}
              autoplay={true}
              rotation={2}
            />
          </div>
        )}

        {/* Большая цифра по центру */}
        <div className="crash-multiplier-big" style={{ color: getMultiplierColor() }}>
          {crashed ? '💥' : multiplier.toFixed(2)}
        </div>
      </div>

      {/* История коэффициентов или "Ожидание" */}
      <div className="crash-history-row">
        {!isRunning && history.length === 0 ? (
          <div className="crash-waiting-text">Ожидание</div>
        ) : (
          [...history].reverse().slice(0, 10).map((mult, idx) => (
            <div 
              key={idx} 
              className={`crash-history-item ${mult >= 10 ? 'mega' : mult >= 2 ? 'high' : 'low'}`}
            >
              x{mult.toFixed(2)}
            </div>
          ))
        )}
      </div>

      {/* Ставки пока нет - панель с текстом */}
      {!userBet && (
        <div className="crash-no-bet-panel">
          Ставок еще нет
        </div>
      )}

      {/* Кнопки внизу */}
      <div className="crash-controls" style={{ bottom: `calc(10px + ${safeAreaBottom}px)` }}>
        {userBet && isRunning && !userBet.cashoutAt ? (
          <button className="spin-button-fixed crash-cashout-btn" onClick={handleCashout}>
            <span className="button-main-text">Забрать</span>
          </button>
        ) : (
          <button className="spin-button-fixed" onClick={() => setShowBetModal(true)}>
            <span className="button-main-text">Сделать ставку</span>
          </button>
        )}
      </div>

      {/* Модалка ставки */}
      {showBetModal && (
        <div className="crash-bet-modal" onClick={() => setShowBetModal(false)}>
          <div className="crash-bet-modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Сделать ставку</h3>
            <div className="bet-input-group">
              <label>Сумма (минимум 25 ⭐️)</label>
              <input 
                type="number" 
                value={betAmount} 
                onChange={(e) => setBetAmount(Math.max(25, parseInt(e.target.value) || 25))}
                min="25"
              />
            </div>
            <div className="bet-modal-buttons">
              <button onClick={() => setShowBetModal(false)}>Отмена</button>
              <button onClick={handlePlaceBet} className="primary">Подтвердить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Crash
