import { useState, useEffect } from 'react'
import './TopUp.css'

function TopUp({ onNavigateBack }) {
  const [paymentMethod, setPaymentMethod] = useState('stars') // 'stars' или 'ton'
  const [amount, setAmount] = useState(100)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [returnTab, setReturnTab] = useState('home')
  const [walletAddress, setWalletAddress] = useState(null)
  
  // Определяем мобильную платформу и safe area
  const isMobile = window.Telegram?.WebApp?.platform === 'android' || 
                   window.Telegram?.WebApp?.platform === 'ios'
  const safeAreaTopValue = window.Telegram?.WebApp?.safeAreaInset?.top || 
                           window.Telegram?.WebApp?.contentSafeAreaInset?.top || 0
  const topPadding = isMobile ? (safeAreaTopValue + 10) : 10

  const presetAmounts = [50, 100, 250, 500, 1000, 2500]

  useEffect(() => {
    const savedTab = localStorage.getItem('previousTab') || 'home'
    setReturnTab(savedTab)
    
    // Показываем нативную кнопку "Назад" от Telegram
    const tg = window.Telegram?.WebApp
    if (tg?.BackButton) {
      tg.BackButton.show()
      
      // Обработчик клика на кнопку назад
      const handleBackClick = () => {
        if (onNavigateBack) {
          onNavigateBack(savedTab)
        }
      }
      
      tg.BackButton.onClick(handleBackClick)
      
      // Скрываем кнопку при размонтировании компонента
      return () => {
        tg.BackButton.hide()
        tg.BackButton.offClick(handleBackClick)
      }
    }

    // Инициализируем TON Connect UI
    if (window.TON_CONNECT_UI && !window.tonConnectUI) {
      window.tonConnectUI = new window.TON_CONNECT_UI.TonConnectUI({
        manifestUrl: 'https://shelloch.xyz/tonconnect-manifest.json',
        buttonRootId: null
      })

      // Проверяем уже подключенный кошелек
      window.tonConnectUI.onStatusChange((wallet) => {
        if (wallet) {
          const address = wallet.account.address
          saveWalletToServer(address)
        }
      })
    }

    // Загружаем сохраненный кошелек с сервера
    loadWalletFromServer()
  }, [])

  const loadWalletFromServer = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/ton/get-wallet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.success && data.wallet) {
        setWalletAddress(data.wallet)
      }
    } catch (err) {
      console.error('Error loading wallet:', err)
    }
  }

  const saveWalletToServer = async (address) => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/ton/connect-wallet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, walletAddress: address })
      })

      const data = await response.json()
      if (data.success) {
        setWalletAddress(address)
        console.log('Wallet saved to server')
      }
    } catch (err) {
      console.error('Error saving wallet:', err)
    }
  }

  const disconnectWallet = async () => {
    try {
      setLoading(true)
      
      // Отключаем через TON Connect
      if (window.tonConnectUI) {
        await window.tonConnectUI.disconnect()
      }

      // Удаляем с сервера
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (initData) {
        const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
        await fetch(`${apiUrl}/api/ton/connect-wallet`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData, walletAddress: null })
        })
      }

      setWalletAddress(null)
      console.log('Wallet disconnected')
    } catch (err) {
      console.error('Error disconnecting wallet:', err)
    } finally {
      setLoading(false)
    }
  }



  const connectTonWallet = async () => {
    try {
      setLoading(true)
      setError('')

      // Инициализируем TON Connect UI
      if (!window.tonConnectUI) {
        window.tonConnectUI = new window.TON_CONNECT_UI.TonConnectUI({
          manifestUrl: 'https://shelloch.xyz/tonconnect-manifest.json',
          buttonRootId: null
        })
      }

      const tonConnectUI = window.tonConnectUI

      // Подключаем кошелек
      const connectedWallet = await tonConnectUI.connectWallet()
      
      if (connectedWallet) {
        const address = connectedWallet.account.address
        // Сохраняем на сервер
        await saveWalletToServer(address)
        setError('')
        
        console.log('Wallet connected:', address)
      }
    } catch (err) {
      console.error('Error connecting wallet:', err)
      if (err.message?.includes('user rejected')) {
        setError('Подключение отменено')
      } else {
        setError('Ошибка подключения кошелька')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleTopUpStars = async () => {
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

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/create-invoice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, amount })
      })

      const data = await response.json()

      if (data.success && data.invoiceUrl) {
        tg.openInvoice(data.invoiceUrl, (status) => {
          if (status === 'paid') {
            onNavigateBack(returnTab)
          } else {
            onNavigateBack(returnTab)
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

  const handleTopUpTon = async () => {
    if (!walletAddress) {
      setError('Сначала подключите кошелек')
      return
    }

    if (amount < 1) {
      setError('Минимальная сумма 1 звезда')
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

      // Создаем платеж на сервере (сервер генерирует код)
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const paymentResponse = await fetch(`${apiUrl}/api/ton/create-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, amount })
      })

      const paymentData = await paymentResponse.json()
      
      if (!paymentData.success) {
        setError(paymentData.message || 'Ошибка создания платежа')
        return
      }

      const { tonAmount, paymentCode, merchantAddress } = paymentData

      // Проверяем что получили адрес
      if (!merchantAddress || typeof merchantAddress !== 'string') {
        setError('Ошибка: адрес мерчанта не получен')
        return
      }

      // Отправляем транзакцию через TON Connect
      const tonConnectUI = window.tonConnectUI
      
      if (!tonConnectUI) {
        setError('TON Connect не инициализирован')
        return
      }

      // Отправляем через TON Connect UI (поддерживает все кошельки)
      // Без payload - backend найдет по точной сумме + времени
      
      const transaction = {
        validUntil: Math.floor(Date.now() / 1000) + 600,
        messages: [
          {
            address: merchantAddress.trim(),
            amount: Math.floor(tonAmount * 1e9).toString()
          }
        ]
      }

      console.log('Sending transaction:', {
        address: merchantAddress,
        paymentCode,
        amount: Math.floor(tonAmount * 1e9),
        note: 'Matching by amount + time (no payload)'
      })
      
      const result = await tonConnectUI.sendTransaction(transaction)
      
      if (result) {
        console.log('Transaction sent:', result)
        // Возвращаемся назад после отправки
        setTimeout(() => {
          onNavigateBack(returnTab)
        }, 2000)
      }

    } catch (err) {
      console.error('Error creating TON transaction:', err)
      
      // Показываем более детальную ошибку
      let errorMessage = 'Ошибка создания транзакции'
      if (err.message) {
        if (err.message.includes('user reject')) {
          errorMessage = 'Вы отклонили транзакцию'
        } else if (err.message.includes('insufficient')) {
          errorMessage = 'Недостаточно средств в кошельке'
        } else {
          errorMessage = `Ошибка: ${err.message}`
        }
      }
      
      setError(errorMessage)
      
      // Выводим ошибку в консоль
      console.error('TON payment error:', errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleTopUp = () => {
    if (paymentMethod === 'stars') {
      handleTopUpStars()
    } else {
      handleTopUpTon()
    }
  }

  return (
    <div className="topup-page">
      <div className="topup-content" style={{ paddingTop: `${topPadding}px` }}>
        {/* Табы выбора метода оплаты */}
        <div className="payment-tabs">
          <button 
            className={`payment-tab ${paymentMethod === 'stars' ? 'active' : ''}`}
            onClick={() => setPaymentMethod('stars')}
          >
            ⭐️ Звезды
          </button>
          <button 
            className={`payment-tab ${paymentMethod === 'ton' ? 'active' : ''}`}
            onClick={() => setPaymentMethod('ton')}
          >
            💎 TON
          </button>
        </div>

        <div className="topup-body">
          {/* Блок для TON */}
          {paymentMethod === 'ton' && !walletAddress && (
            <div className="wallet-connect-section">
              <p className="wallet-info">Подключите кошелек TON для пополнения</p>
              <button 
                className="connect-wallet-btn" 
                onClick={connectTonWallet}
                disabled={loading}
              >
                {loading ? 'Подключение...' : 'Подключить кошелек'}
              </button>
            </div>
          )}

          {paymentMethod === 'ton' && walletAddress && (
            <div className="ton-info-section">
              <div className="wallet-connected">
                <div className="wallet-header">
                  <div>
                    <p className="wallet-label">Подключенный кошелек:</p>
                    <p className="wallet-address">{walletAddress.slice(0, 8)}...{walletAddress.slice(-6)}</p>
                  </div>
                  <button 
                    className="disconnect-wallet-btn" 
                    onClick={disconnectWallet}
                    disabled={loading}
                  >
                    Отключить
                  </button>
                </div>
                <p className="ton-hint">💡 При нажатии "Пополнить" откроется ваш TON кошелек для подтверждения транзакции. Код платежа будет автоматически добавлен в комментарий.</p>
              </div>
            </div>
          )}

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
            disabled={loading || (paymentMethod === 'ton' && !walletAddress)}
          >
            {loading ? 'Создание...' : 'Пополнить'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TopUp
