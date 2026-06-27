import { useState, useEffect } from 'react'
import './TopUp.css'

function TonPayment({ onNavigateBack }) {
  const [tonAmount, setTonAmount] = useState(1)
  const [starsAmount, setStarsAmount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPayment, setShowPayment] = useState(false)
  const [paymentData, setPaymentData] = useState(null)
  const [returnTab, setReturnTab] = useState('home')
  const [isEditing, setIsEditing] = useState(false)
  
  const isMobile = window.Telegram?.WebApp?.platform === 'android' || 
                   window.Telegram?.WebApp?.platform === 'ios'
  const safeAreaTopValue = window.Telegram?.WebApp?.safeAreaInset?.top || 
                           window.Telegram?.WebApp?.contentSafeAreaInset?.top || 0
  const topPadding = isMobile ? (safeAreaTopValue + 10) : 10

  const presetAmounts = [1, 2, 5, 10]

  useEffect(() => {
    const savedTab = localStorage.getItem('previousTab') || 'home'
    setReturnTab(savedTab)
    
    const tg = window.Telegram?.WebApp
    if (tg?.BackButton) {
      tg.BackButton.show()
      
      const handleBackClick = () => {
        if (showPayment) {
          setShowPayment(false)
        } else if (onNavigateBack) {
          onNavigateBack(savedTab)
        }
      }
      
      tg.BackButton.onClick(handleBackClick)
      
      return () => {
        tg.BackButton.hide()
        tg.BackButton.offClick(handleBackClick)
      }
    }
  }, [showPayment])

  // Рассчитываем Stars при изменении TON
  useEffect(() => {
    if (tonAmount >= 0.1) {
      calculateStars()
    } else {
      setStarsAmount(0)
    }
  }, [tonAmount])

  const calculateStars = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 
      const response = await fetch(`${apiUrl}/api/ton/calculate-stars`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, tonAmount })
      })

      const data = await response.json()
      if (data.success) {
        setStarsAmount(data.stars)
      }
    } catch (err) {
      console.error('Error calculating stars:', err)
    }
  }

  const handleCreatePayment = async () => {
    if (tonAmount < 0.1) {
      setError('Минимальная сумма 0.1 TON')
      return
    }

    setLoading(true)
    setError('')

    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData

      if (!initData) {
        setError('Telegram WebApp недоступен')
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 
      const response = await fetch(`${apiUrl}/api/ton/create-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, tonAmount })
      })

      const data = await response.json()

      if (data.success) {
        setPaymentData(data)
        setShowPayment(true)
      } else {
        setError(data.message || 'Ошибка создания платежа')
      }
    } catch (err) {
      console.error('Error creating payment:', err)
      setError('Ошибка подключения к серверу')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenWallet = () => {
    if (!paymentData) return
    
    const tg = window.Telegram?.WebApp
    
    // Используем ton:// для универсальности (работает для всех кошельков)
    if (tg && tg.openLink) {
      tg.openLink(paymentData.deepLinkTon)
    } else {
      window.open(paymentData.deepLinkTon, '_blank')
    }
  }

  if (showPayment && paymentData) {
    return (
      <div className="topup-page">
        <div className="topup-content" style={{ paddingTop: `${topPadding}px` }}>
          <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Оплата TON</h2>
          
          {/* QR код */}
          <div style={{ textAlign: 'center', marginBottom: '20px' }}>
            <img 
              src={paymentData.qrCode} 
              alt="QR Code" 
              style={{ 
                width: '250px', 
                height: '250px',
                border: '2px solid rgba(255,255,255,0.1)',
                borderRadius: '16px',
                padding: '10px',
                background: 'white'
              }} 
            />
          </div>

          {/* Информация о платеже */}
          <div className="payment-info">
            <div className="info-row">
              <span>Сумма:</span>
              <span style={{ fontWeight: 'bold' }}>{paymentData.tonAmount} TON</span>
            </div>
            <div className="info-row">
              <span>Вы получите:</span>
              <span style={{ fontWeight: 'bold', color: '#0FBCE0' }}>
                {paymentData.starsAmount} ⭐ (+5% бонус)
              </span>
            </div>
            <div className="info-row">
              <span>Комментарий:</span>
              <span style={{ 
                fontFamily: 'monospace', 
                background: 'rgba(255,255,255,0.1)',
                padding: '4px 8px',
                borderRadius: '4px'
              }}>
                {paymentData.paymentCode}
              </span>
            </div>
          </div>

          {/* Адрес */}
          <div style={{ 
            marginTop: '20px',
            padding: '12px',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '12px',
            fontSize: '12px',
            wordBreak: 'break-all'
          }}>
            <div style={{ marginBottom: '4px', color: '#888' }}>Адрес получателя:</div>
            <div style={{ fontFamily: 'monospace' }}>{paymentData.merchantAddress}</div>
          </div>

          {/* Кнопка оплаты */}
          <button 
            className="topup-btn" 
            onClick={handleOpenWallet}
            style={{ marginTop: '20px' }}
          >
            Открыть кошелек для оплаты
          </button>

          <div style={{ 
            marginTop: '16px', 
            textAlign: 'center', 
            fontSize: '13px', 
            color: '#888' 
          }}>
            💡 Отсканируйте QR код или нажмите кнопку для оплаты через TON кошелек
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="topup-page">
      <div className="topup-content" style={{ paddingTop: `${topPadding}px` }}>
        <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>💎 Пополнение через TON</h2>

        <div className="topup-body">
          {/* Количество TON по середине */}
          <div className="amount-display" onClick={() => setIsEditing(true)}>
            {isEditing ? (
              <input
                type="number"
                step="0.1"
                min="0.1"
                className="amount-input"
                value={tonAmount}
                onChange={(e) => setTonAmount(Math.max(0.1, parseFloat(e.target.value) || 0.1))}
                onBlur={() => setIsEditing(false)}
                autoFocus
              />
            ) : (
              <div className="amount-number">{tonAmount}</div>
            )}
            <div className="amount-label">TON</div>
          </div>

          {/* Показываем сколько получит Stars */}
          {starsAmount > 0 && (
            <div style={{
              textAlign: 'center',
              marginTop: '12px',
              marginBottom: '20px',
              fontSize: '16px',
              color: '#0FBCE0'
            }}>
              Получите {starsAmount} ⭐
            </div>
          )}

          {error && <div className="error-message">{error}</div>}

          {/* Быстрые кнопки */}
          <div className="preset-amounts">
            {presetAmounts.map(preset => (
              <button
                key={preset}
                className="preset-btn"
                onClick={() => setTonAmount(tonAmount + preset)}
              >
                + {preset} TON
              </button>
            ))}
          </div>

          <button 
            className="topup-btn" 
            onClick={handleCreatePayment}
            disabled={loading || tonAmount < 0.1}
          >
            {loading ? 'Создание...' : 'Оплатить'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TonPayment
