import { useState, useEffect } from 'react'
import './Crash.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import crashAnim from '../assets/crash.json'

function Crash({ onNavigateToTopUp }) {
  const [multiplier, setMultiplier] = useState(1.00)
  const [isRunning, setIsRunning] = useState(false)
  const [history, setHistory] = useState([])
  const [crashed, setCrashed] = useState(false)
  const [bets, setBets] = useState([])
  const [userBet, setUserBet] = useState(null)
  const [showBetModal, setShowBetModal] = useState(false)
  const [betAmount, setBetAmount] = useState(25)

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

  useEffect(() => {
    fetchGameState()
    const interval = setInterval(fetchGameState, 100)
    return () => clearInterval(interval)
  }, [])

  const fetchGameState = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/crash/state`)
      const data = await response.json()
      
      setMultiplier(data.currentMultiplier)
      setIsRunning(data.isRunning)
      setHistory(data.history)
      setBets(data.bets || [])
      
      // Находим ставку текущего пользователя
      if (user) {
        const myBet = data.bets?.find(b => b.userId === user.id)
        setUserBet(myBet || null)
      }
      
      if (!data.isRunning && data.crashPoint) {
        setCrashed(true)
        
        // Вибрация при краше (3 раза)
        if (tg?.HapticFeedback) {
          tg.HapticFeedback.impactOccurred('heavy')
          setTimeout(() => tg.HapticFeedback.impactOccurred('heavy'), 100)
          setTimeout(() => tg.HapticFeedback.impactOccurred('heavy'), 200)
        }
        
        setTimeout(() => setCrashed(false), 3000)
      }
    } catch (error) {
      console.error('Error fetching game state:', error)
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
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/crash/bet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          amount: betAmount,
          username: user.username || user.first_name,
          avatar: user.photo_url
        })
      })

      const data = await response.json()
      
      if (response.ok) {
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
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/crash/cashout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id })
      })

      const data = await response.json()
      
      if (!response.ok || !data.success) {
        if (tg) {
          tg.showAlert(data.error || 'Ошибка')
        }
      }
    } catch (error) {
      console.error('Error cashing out:', error)
    }
  }

  const handleCancelBet = async () => {
    if (!user) return

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/crash/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id })
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

  const renderBetButton = () => {
    // Если есть ставка и она в ожидании
    if (userBet && userBet.waiting) {
      return null // Кнопка не показывается, т.к. отменить можно из списка
    }

    // Если есть активная ставка в раунде
    if (userBet && isRunning && !userBet.cashoutAt) {
      return (
        <button className="crash-bet-button cashout" onClick={handleCashout}>
          Забрать
        </button>
      )
    }

    // Если ставки нет - показываем кнопку сделать ставку
    if (!userBet) {
      return (
        <button className="crash-bet-button" onClick={() => setShowBetModal(true)}>
          Сделать ставку
        </button>
      )
    }

    return null
  }

  return (
    <div className="crash-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />

      <div className="crash-game-area">
        {/* Сеточка фона */}
        <div className={`crash-grid ${isRunning ? 'running' : ''} ${crashed ? 'crashed' : ''}`}>
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

        {/* Линия траектории */}
        {isRunning && (
          <div className="crash-trajectory-line" style={{
            width: `${Math.min((multiplier - 1) * 80, 90)}%`
          }}></div>
        )}

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

        <div className="crash-multiplier-display" style={{ color: getMultiplierColor() }}>
          x{multiplier.toFixed(2)}
        </div>

        {crashed && (
          <div className="crash-crashed-text">КРАШ!</div>
        )}
      </div>

      <div className="crash-history-row">
        {history.map((mult, idx) => (
          <div 
            key={idx} 
            className={`crash-history-item ${mult >= 10 ? 'mega' : mult >= 2 ? 'high' : 'low'}`}
          >
            {mult.toFixed(2)}
          </div>
        ))}
      </div>

      {renderBetButton()}

      <div className="crash-bets-list">
        {/* Своя ставка всегда сверху если в ожидании */}
        {userBet && userBet.waiting && (
          <div className="crash-bet-item my-bet waiting">
            <div className="bet-user-info">
              {userBet.avatar && <img src={userBet.avatar} alt="" className="bet-avatar" />}
              <div className="bet-details">
                <div className="bet-username">{userBet.username}</div>
                <div className="bet-waiting-text">Ожидание след раунда</div>
              </div>
            </div>
            <button className="bet-cancel-button" onClick={handleCancelBet}>
              Отменить
            </button>
          </div>
        )}

        {/* Остальные ставки */}
        {bets.filter(b => !b.waiting).map((bet, idx) => (
          <div key={idx} className={`crash-bet-item ${bet.userId === user?.id ? 'my-bet' : ''}`}>
            <div className="bet-user-info">
              {bet.avatar && <img src={bet.avatar} alt="" className="bet-avatar" />}
              <div className="bet-details">
                <div className="bet-username">{bet.username}</div>
                <div className="bet-amount">{bet.amount} ⭐️</div>
              </div>
            </div>
            <div className="bet-result">
              {bet.cashoutAt ? (
                <span className="bet-cashout">x{bet.cashoutAt.toFixed(2)}</span>
              ) : isRunning ? (
                <span className="bet-multiplier">x{multiplier.toFixed(2)}</span>
              ) : null}
            </div>
          </div>
        ))}
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
