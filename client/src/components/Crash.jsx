import { useState, useEffect, useRef } from 'react'
import './Crash.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import { useBalance } from '../contexts/BalanceContext'
import crashAnim from '../assets/crash.json'
import starAnim from '../assets/star.json'

function Crash({ onNavigateToTopUp }) {
  const { updateBalance, isAdmin } = useBalance()
  const [multiplier, setMultiplier] = useState(1.00)
  const [isRunning, setIsRunning] = useState(false)
  const [history, setHistory] = useState([])
  const [crashed, setCrashed] = useState(false)
  const [bets, setBets] = useState([])
  const [userBet, setUserBet] = useState(null)
  const [nextBet, setNextBet] = useState(null) // Ставка на следующий раунд от сервера
  const [showBetModal, setShowBetModal] = useState(false)
  const [betAmount, setBetAmount] = useState(25)
  const [isConnected, setIsConnected] = useState(false)
  const [wasConnected, setWasConnected] = useState(false) // Было ли подключение хоть раз
  const [showCrashPanel, setShowCrashPanel] = useState(false)
  const [isCountdown, setIsCountdown] = useState(false)
  const [countdownValue, setCountdownValue] = useState(0)
  
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
    
    // Проверяем параметр showCrashPanel в URL
    const urlParams = new URLSearchParams(window.location.search)
    setShowCrashPanel(urlParams.get('showCrashPanel') === 'true')
  }, [])

  // WebSocket подключение (без polling fallback)
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || ''
    const wsUrl = apiUrl.replace('https://', 'wss://').replace('http://', 'ws://')
    let shouldReconnect = true
    let reconnectTimeout = null
    
    const connectWebSocket = async () => {
      if (!shouldReconnect) return
      
      try {
        // Получаем токен для WebSocket через REST (избегаем длинной initData в URL)
        const initData = window.Telegram?.WebApp?.initData || ''
        let wsToken = ''
        try {
          const authRes = await fetch(`${apiUrl}/api/crash/auth-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData })
          })
          if (authRes.ok) {
            const authData = await authRes.json()
            wsToken = authData.token || ''
          }
        } catch (e) {
          console.warn('Failed to get WS token, falling back to initData', e)
        }

        // Используем токен или initData для WebSocket
        const wsUrlWithAuth = wsToken
          ? `${wsUrl}/api/crash/ws?token=${wsToken}`
          : `${wsUrl}/api/crash/ws?initData=${encodeURIComponent(initData)}`

        const ws = new WebSocket(wsUrlWithAuth)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('🔌 WebSocket connected to crash game')
          setIsConnected(true)
          setWasConnected(true)
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
          setIsConnected(false)
        }

        ws.onclose = () => {
          console.log('🔌 WebSocket disconnected')
          setIsConnected(false)
          if (shouldReconnect) {
            reconnectTimeout = setTimeout(connectWebSocket, 3000)
          }
        }
      } catch (error) {
        console.error('WebSocket creation error:', error)
        if (shouldReconnect) {
          reconnectTimeout = setTimeout(connectWebSocket, 3000)
        }
      }
    }

    connectWebSocket()

    return () => {
      shouldReconnect = false
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const handleGameStateUpdate = (data) => {
    setMultiplier(data.currentMultiplier)
    setHistory(data.history)
    setBets(data.bets || [])
    setIsCountdown(data.isCountdown || false)
    setCountdownValue(data.countdownValue || 0)
    
    // Ставка текущего пользователя приходит отдельно от сервера
    setUserBet(data.userBet || null)
    
    // Обновляем nextBet от сервера
    setNextBet(data.nextBet || null)
    
    // Определяем краш: переход из running в stopped
    if (previousIsRunning.current && !data.isRunning) {
      console.log('КРАШ ОБНАРУЖЕН! Multiplier:', data.currentMultiplier)
      setCrashed(true)
      
      // Вибрация при краше - паттерн "взрыв" (нарастающий, ~1 сек)
      if (tg?.HapticFeedback) {
        // Первый удар - тяжелый (начало)
        tg.HapticFeedback.impactOccurred('heavy')
        
        // Второй удар - тяжелый (нарастание)
        setTimeout(() => tg.HapticFeedback.impactOccurred('heavy'), 200)
        
        // Третий удар - тяжелый (пик)
        setTimeout(() => tg.HapticFeedback.impactOccurred('heavy'), 400)
        
        // Четвертый удар - средний (затухание)
        setTimeout(() => tg.HapticFeedback.impactOccurred('medium'), 700)
        
        // Всего ~900ms (меньше 1 секунды)
      }
      
      // Сбрасываем crashed через 1 секунду (время показа ставок после краша)
      if (crashedTimeoutRef.current) {
        clearTimeout(crashedTimeoutRef.current)
      }
      crashedTimeoutRef.current = setTimeout(() => {
        setCrashed(false)
      }, 1000)
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

      const apiUrl = import.meta.env.VITE_API_URL || ''
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
        // nextBet придет от сервера через WebSocket
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

      const apiUrl = import.meta.env.VITE_API_URL || ''
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

      const apiUrl = import.meta.env.VITE_API_URL || ''
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

  const handleExplodeCrash = async () => {
    if (!isAdmin || !user) return

    try {
      const initData = tg?.initData
      if (!initData) {
        if (tg) tg.showAlert('Ошибка авторизации')
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || ''
      const response = await fetch(`${apiUrl}/api/admin/crash/explode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      
      if (!response.ok || !data.success) {
        if (tg) {
          tg.showAlert(data.message || 'Ошибка взрыва')
        }
      } else {
        if (tg) {
          tg.HapticFeedback.notificationOccurred('success')
        }
      }
    } catch (error) {
      console.error('Error exploding crash:', error)
      if (tg) {
        tg.showAlert('Ошибка соединения')
      }
    }
  }

  const isMobile = window.Telegram?.WebApp?.platform === 'android' || 
                   window.Telegram?.WebApp?.platform === 'ios'
  // Всегда 0 чтобы кнопка была ровно 10px от safe area (без дополнительного отступа)
  const safeAreaBottom = 0

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

        {/* Ракета на фоне - показывается всегда */}
        <div className="crash-rocket-center">
          <LottieAnimation 
            animationData={crashAnim} 
            width={160} 
            height={160}
            loop={true}
            autoplay={true}
            rotation={2}
          />
        </div>

        {/* Большая цифра по центру - когда раунд идет или countdown */}
        {isRunning && !crashed && (
          <div className="crash-multiplier-big" style={{ color: getMultiplierColor() }}>
            {multiplier.toFixed(2)}
          </div>
        )}
        
        {/* Countdown отсчет перед раундом */}
        {isCountdown && countdownValue > 0 && (
          <div className="crash-multiplier-big" style={{ color: '#ffffff' }}>
            {countdownValue}
          </div>
        )}
      </div>

      {/* Countdown текст над историей - всегда присутствует для стабильности */}
      <div className="crash-countdown-text">
        {isCountdown ? `Начинаем через ${countdownValue}...` : ''}
      </div>

      {/* История коэффициентов */}
      <div className="crash-history-row">
        {history.length === 0 ? (
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

      {/* Контейнер для ставок - ВСЕГДА присутствует с фиксированной высотой */}
      <div className="crash-bet-container">
        {!isConnected && wasConnected ? (
          // Сообщение об отключении
          <div className="crash-user-bet-tile crash-disconnected-tile">
            <div className="disconnected-title">Отключено от сервера</div>
            <div className="disconnected-text">
              Если вы потеряли ставку, напишите в{' '}
              <a href="https://t.me/helpshellbot" target="_blank" rel="noopener noreferrer">
                поддержку
              </a>
            </div>
          </div>
        ) : (userBet || nextBet || bets.length > 0) ? (
          // Отображаем ставки
          <div style={{ width: '100%', maxHeight: '200px', overflowY: 'auto' }}>
            {/* Сначала ставка текущего пользователя */}
            {(userBet || nextBet) && (
              <div className="crash-user-bet-tile">
            <div className="bet-tile-left">
              <img 
                src={user?.photo_url || `https://ui-avatars.com/api/?name=${user?.first_name}&background=3b82f6&color=fff`} 
                alt="Avatar" 
                className="bet-tile-avatar"
              />
              <div className="bet-tile-info">
                <div className="bet-tile-name">{user?.first_name || 'Игрок'}</div>
                <div 
                  className="bet-tile-status"
                  style={{
                    color: userBet?.cashoutAt 
                      ? '#10b981' 
                      : (crashed && userBet && !userBet.cashoutAt) 
                        ? '#ff4444' 
                        : 'rgba(255, 255, 255, 0.6)'
                  }}
                >
                  {nextBet && !userBet ? (
                    // Ставка на следующий раунд - ожидание
                    'Следующий раунд'
                  ) : userBet?.cashoutAt ? (
                    // Забрал - показываем зафиксированный коэффициент зеленым
                    `${userBet.cashoutAt.toFixed(2)}x`
                  ) : crashed && userBet && !userBet.cashoutAt ? (
                    // Краш произошел и не забрал - красный коэффициент краша
                    `${multiplier.toFixed(2)}x`
                  ) : isRunning ? (
                    // Раунд идет - показываем текущий коэффициент
                    `${multiplier.toFixed(2)}x`
                  ) : (
                    // Ожидание следующего раунда
                    'Ожидание'
                  )}
                </div>
              </div>
            </div>
            <div className="bet-tile-amount">
              {userBet?.current_winnings !== undefined 
                ? Math.floor(userBet.current_winnings)
                : (nextBet?.amount || 0)
              }
              <LottieAnimation 
                animationData={starAnim} 
                loop={false} 
                autoplay={false}
                width={24}
                height={24}
              />
            </div>
              </div>
            )}
            
            {/* Остальные ставки игроков (кроме текущего пользователя) */}
            {bets
              .filter(bet => bet.userId !== user?.id)
              .map((bet, index) => (
                <div key={`${bet.userId}-${index}`} className="crash-user-bet-tile" style={{ marginTop: '8px' }}>
                  <div className="bet-tile-left">
                    <img 
                      src={bet.avatar || `https://ui-avatars.com/api/?name=${bet.username}&background=6366f1&color=fff`} 
                      alt={bet.username} 
                      className="bet-tile-avatar"
                    />
                    <div className="bet-tile-info">
                      <div className="bet-tile-name">{bet.username || 'Игрок'}</div>
                      <div 
                        className="bet-tile-status"
                        style={{
                          color: bet.cashoutAt 
                            ? '#10b981' 
                            : (crashed && !bet.cashoutAt) 
                              ? '#ff4444' 
                              : 'rgba(255, 255, 255, 0.6)'
                        }}
                      >
                        {bet.cashoutAt ? (
                          `${bet.cashoutAt.toFixed(2)}x`
                        ) : crashed && !bet.cashoutAt ? (
                          `${multiplier.toFixed(2)}x`
                        ) : isRunning ? (
                          `${multiplier.toFixed(2)}x`
                        ) : (
                          'Ожидание'
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="bet-tile-amount">
                    {bet.cashoutAt 
                      ? Math.floor(bet.amount * bet.cashoutAt)
                      : isRunning 
                        ? Math.floor(bet.amount * multiplier)
                        : bet.amount
                    }
                    <LottieAnimation 
                      animationData={starAnim} 
                      loop={false} 
                      autoplay={false}
                      width={24}
                      height={24}
                    />
                  </div>
                </div>
              ))
            }
          </div>
        ) : (
          // Ставки пока нет - панель с текстом
          <div className="crash-no-bet-panel">
            Ставок еще нет
          </div>
        )}
      </div>

      {/* Кнопки внизу */}
      <div className="crash-controls" style={{ bottom: `calc(10px + ${safeAreaBottom}px)` }}>
        {userBet && isRunning && !userBet.cashoutAt ? (
          // Ставка активна в текущем раунде - показываем "Забрать"
          <button className="crash-button crash-cashout-btn" onClick={handleCashout}>
            Забрать
          </button>
        ) : (
          // Показываем "Сделать ставку" (серая если есть nextBet или если забрал в текущем раунде)
          <button 
            className="crash-button" 
            onClick={() => setShowBetModal(true)}
            disabled={!!nextBet || (userBet?.cashoutAt && isRunning)}
            style={{
              opacity: (nextBet || (userBet?.cashoutAt && isRunning)) ? 0.5 : 1,
              cursor: (nextBet || (userBet?.cashoutAt && isRunning)) ? 'not-allowed' : 'pointer'
            }}
          >
            {nextBet ? 'Ставка принята' : 'Сделать ставку'}
          </button>
        )}
      </div>

      {/* Кнопка взрыва для админов (показывается только когда showCrashPanel=true) */}
      {isAdmin && showCrashPanel && isRunning && (
        <div style={{
          position: 'fixed',
          top: '10px',
          right: '10px',
          zIndex: 1000
        }}>
          <button 
            onClick={handleExplodeCrash}
            style={{
              background: 'linear-gradient(135deg, #ff4444, #cc0000)',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              padding: '12px 20px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(255, 68, 68, 0.4)',
              transition: 'all 0.2s ease'
            }}
            onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.95)'}
            onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
          >
            💥 Взорвать сейчас
          </button>
        </div>
      )}

      {/* Модалка ставки - bottom sheet */}
      {showBetModal && (
        <div className="crash-bet-modal" onClick={() => setShowBetModal(false)}>
          <div className="crash-bet-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>Новая ставка</h3>
            
            <div className="bet-amount-input-container">
              <input 
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                className="bet-amount-input"
                value={betAmount}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, ''); // Только цифры
                  const numValue = parseInt(value) || 0;
                  setBetAmount(Math.max(0, Math.min(20000, numValue))); // 0-20000
                }}
                placeholder="0"
              />
              <span className="bet-amount-label">stars</span>
            </div>
            
            <div className="bet-quick-buttons">
              <button onClick={() => setBetAmount(prev => Math.max(25, prev + 100))}>+ 100</button>
              <button onClick={() => setBetAmount(prev => Math.max(25, prev + 500))}>+ 500</button>
              <button onClick={() => setBetAmount(prev => Math.max(25, prev + 2500))}>+ 2 500</button>
            </div>
            
            <div className="bet-range-hint">От 50 до 20 000 звезд</div>
            
            <button className="crash-button bet-submit-btn" onClick={handlePlaceBet}>
              Сделать ставку
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Crash
