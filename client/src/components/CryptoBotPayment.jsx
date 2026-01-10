import { useState, useEffect } from 'react'
import './TopUp.css'

function CryptoBotPayment({ onNavigateBack, isEmbedded = false }) {
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

    // Если встроенный, не управляем нативной кнопкой назад
    if (isEmbedded) return

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
  }, [showPayment, isEmbedded])

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

        // Авто-открытие (как в handleTopUpStars)
        // User requested: "оно открывает эту ссылку в телеграмме само а кнопка оплатить ткрывает ссылку в барузере"
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

    // User requested: "Pay button opens link in browser"
    // window.open usually opens in browser (system browser on mobile)
    if (paymentData.invoiceUrl) {
      window.open(paymentData.invoiceUrl, '_blank')
    }
  }

  // Render Inner Content
  const renderContent = () => {
    if (showPayment && paymentData) {
      return (
        <div className={`topup-body ${isEmbedded ? '' : 'topup-content'}`} style={!isEmbedded ? { paddingTop: `${topPadding}px` } : {}}>
          {!isEmbedded && <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Оплата через CryptoBot</h2>}

          {/* Информация о платеже */}
          {/* Input is displayed disabled to show amount */}
          <div className="amount-display disabled" style={{ opacity: 0.7 }}>
            <div className="amount-number">{paymentData.usdtAmount}</div>
            <div className="amount-label">USDT</div>
          </div>

          <div className="payment-info" style={{ marginTop: '20px' }}>
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
            Оплатить
          </button>

          <div style={{
            marginTop: '16px',
            textAlign: 'center',
            fontSize: '13px',
            color: '#888',
            lineHeight: '1.5'
          }}>
            💡 Оплатите счет через @CryptoBot<br />
            После оплаты баланс будет автоматически пополнен
          </div>

          <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'center' }}>
            <button
              className="text-btn"
              onClick={() => setShowPayment(false)}
              style={{ color: '#888', background: 'none', border: 'none', padding: '10px' }}
            >
              Отменить / Изменить сумму
            </button>
          </div>
        </div>
      )
    }

    return (
      <div className={`topup-body ${isEmbedded ? '' : 'topup-content'}`} style={!isEmbedded ? { paddingTop: `${topPadding}px` } : {}}>
        {!isEmbedded && <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>CryptoBot</h2>}

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
    )
  }

  if (isEmbedded) {
    return renderContent()
  }

  return (
    <div className="topup-page">
      {renderContent()}
    </div>
  )
}

export default CryptoBotPayment
