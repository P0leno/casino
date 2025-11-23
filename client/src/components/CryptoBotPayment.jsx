import { useState, useEffect } from 'react'
import './TopUp.css'

function CryptoBotPayment({ onNavigateBack }) {
  const [usdtAmount, setUsdtAmount] = useState(1)
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

  const presetAmounts = [1, 5, 10, 25]

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

  // Рассчитываем Stars при изменении USDT
  useEffect(() => {
    if (usdtAmount >= 1) {
      calculateStars()
    } else {
      setStarsAmount(0)
    }
  }, [usdtAmount])

  const calculateStars = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/cryptobot/calculate-stars`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, usdtAmount })
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
    if (usdtAmount < 1) {
      setError('Минимальная сумма 1 USDT')
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

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/cryptobot/create-invoice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, usdtAmount })
      })

      const data = await response.json()

      if (data.success) {
        setPaymentData(data)
        setShowPayment(true)
        
        // Открываем счет сразу
        if (data.invoiceUrl && tg && tg.openLink) {
          tg.openLink(data.invoiceUrl)
        }
      } else {
        setError(data.message || 'Ошибка создания счета')
      }
    } catch (err) {
      console.error('Error creating invoice:', err)
      setError('Ошибка подключения к серверу')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenInvoice = () => {
    if (!paymentData) return
    
    const tg = window.Telegram?.WebApp
    
    if (tg && tg.openLink) {
      tg.openLink(paymentData.invoiceUrl)
    } else {
      window.open(paymentData.invoiceUrl, '_blank')
    }
  }

  if (showPayment && paymentData) {
    return (
      <div className="topup-page">
        <div className="topup-content" style={{ paddingTop: `${topPadding}px` }}>
          <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Оплата через CryptoBot</h2>
          
          {/* Информация о платеже */}
          <div className="payment-info" style={{ marginTop: '30px' }}>
            <div className="info-row">
              <span>Сумма:</span>
              <span style={{ fontWeight: 'bold' }}>{paymentData.usdtAmount} USDT</span>
            </div>
            <div className="info-row">
              <span>Вы получите:</span>
              <span style={{ fontWeight: 'bold', color: '#0FBCE0' }}>
                {paymentData.starsAmount} ⭐ (+5% бонус)
              </span>
            </div>
            <div className="info-row" style={{ fontSize: '12px', color: '#888' }}>
              <span>Счет действителен:</span>
              <span>30 минут</span>
            </div>
          </div>

          {/* Кнопка оплаты */}
          <button 
            className="topup-btn" 
            onClick={handleOpenInvoice}
            style={{ marginTop: '30px' }}
          >
            Открыть счет для оплаты
          </button>

          <div style={{ 
            marginTop: '16px', 
            textAlign: 'center', 
            fontSize: '13px', 
            color: '#888',
            lineHeight: '1.5'
          }}>
            💡 Оплатите счет через @CryptoBot<br/>
            После оплаты баланс будет автоматически пополнен
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="topup-page">
      <div className="topup-content" style={{ paddingTop: `${topPadding}px` }}>
        <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>CryptoBot</h2>

        <div className="topup-body">
          {/* Количество USDT по середине */}
          <div className="amount-display" onClick={() => setIsEditing(true)}>
            {isEditing ? (
              <input
                type="number"
                step="1"
                min="1"
                className="amount-input"
                value={usdtAmount}
                onChange={(e) => setUsdtAmount(Math.max(1, parseFloat(e.target.value) || 1))}
                onBlur={() => setIsEditing(false)}
                autoFocus
              />
            ) : (
              <div className="amount-number">{usdtAmount}</div>
            )}
            <div className="amount-label">USDT</div>
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
                onClick={() => setUsdtAmount(usdtAmount + preset)}
              >
                + {preset} USDT
              </button>
            ))}
          </div>

          <button 
            className="topup-btn" 
            onClick={handleCreatePayment}
            disabled={loading || usdtAmount < 1}
          >
            {loading ? 'Создание...' : 'Оплатить'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default CryptoBotPayment
