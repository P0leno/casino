import { useState } from 'react'
import './TopUpModal.css'

function TopUpModal({ isOpen, onClose, onPaymentSuccess }) {
  const [amount, setAmount] = useState(100)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isEditing, setIsEditing] = useState(false)

  const presetAmounts = [50, 100, 250, 500, 1000, 2500]

  const handleTopUp = async () => {
    if (amount < 1 || amount > 2500) {
      setError('Сумма должна быть от 1 до 2500 звезд')
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

      const apiUrl = import.meta.env.VITE_API_URL || ''
      const response = await fetch(`${apiUrl}/api/create-invoice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, amount })
      })

      const data = await response.json()

      if (data.success && data.invoiceUrl) {
        // Открываем invoice в Telegram
        tg.openInvoice(data.invoiceUrl, (status) => {
          if (status === 'paid') {
            // Оплата успешна - обновляем баланс без перезагрузки
            if (onPaymentSuccess) {
              onPaymentSuccess()
            }
          } else {
            // Просто закрываем если отменено
            onClose()
          }
        })
      } else {
        setError(data.message || 'Ошибка создания платежа')
      }
    } catch (err) {
      console.error('Error creating invoice:', err)
      setError('Ошибка подключения к серверу')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <button className="modal-close" onClick={onClose}>Назад</button>
          <h2>Пополнение</h2>
          <div style={{width: '60px'}}></div>
        </div>

        <div className="modal-body">
          <div className="amount-display" onClick={() => setIsEditing(true)}>
            {isEditing ? (
              <input
                type="number"
                className="amount-input"
                value={amount}
                onChange={(e) => setAmount(Math.max(1, Math.min(2500, parseInt(e.target.value) || 0)))}
                onBlur={() => setIsEditing(false)}
                autoFocus
                min="1"
                max="2500"
              />
            ) : (
              <div className="amount-number">{amount}</div>
            )}
            <div className="amount-label">Stars</div>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="preset-amounts">
            {presetAmounts.map(preset => (
              <button
                key={preset}
                className="preset-btn"
                onClick={() => setAmount(prev => Math.min(2500, prev + preset))}
              >
                + {preset}
              </button>
            ))}
          </div>

          <button 
            className="topup-btn" 
            onClick={handleTopUp}
            disabled={loading}
          >
            {loading ? 'Создание...' : 'Пополнить'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TopUpModal
