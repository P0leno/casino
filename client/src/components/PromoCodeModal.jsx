import { useState, useEffect } from 'react'
import './PromoCodeModal.css'
import LottieAnimation from './LottieAnimation'
import giftAnim from '../assets/gift.json'
import starAnim from '../assets/star.json'

function PromoCodeModal({ isOpen, onClose }) {
  const [promoCode, setPromoCode] = useState('')
  const [showCreateSection, setShowCreateSection] = useState(false)
  const [showRules, setShowRules] = useState(false)
  const [generatedCode, setGeneratedCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [invitedCount, setInvitedCount] = useState(0)
  const [requiredRefs, setRequiredRefs] = useState(10)
  const [promoType, setPromoType] = useState('ref')
  const [showCustomNameInput, setShowCustomNameInput] = useState(false)
  const [customName, setCustomName] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const [history, setHistory] = useState([])
  const [refBalance, setRefBalance] = useState(0)
  const [showWithdrawalDialog, setShowWithdrawalDialog] = useState(false)
  const [withdrawalAmount, setWithdrawalAmount] = useState('')

  // Проверяем существующий промокод при открытии секции создания
  useEffect(() => {
    if (isOpen && showCreateSection && !generatedCode) {
      checkExistingPromoCode()
    }
  }, [isOpen, showCreateSection])

  // Автообновление баланса каждые 3 секунды когда показан промокод
  useEffect(() => {
    if (!isOpen || !showCreateSection || !generatedCode) return

    const interval = setInterval(() => {
      checkExistingPromoCode()
    }, 3000)

    return () => clearInterval(interval)
  }, [isOpen, showCreateSection, generatedCode])

  const checkExistingPromoCode = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/promocode/my-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, type: 'ref' })
      })
      
      const data = await response.json()
      
      if (data.success && data.promoCode) {
        setGeneratedCode(data.promoCode)
        setInvitedCount(data.invitedCount || 0)
        setRequiredRefs(data.requiredRefs || 10)
        setPromoType(data.promoType || 'ref')
        setRefBalance(data.refBalance || 0)
      }
    } catch (error) {
      console.error('Error checking existing promo code:', error)
    }
  }

  const handleActivate = async () => {
    if (!promoCode.trim()) return
    
    setIsLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/promocode/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, promoCode: promoCode.trim() })
      })
      
      const data = await response.json()
      
      if (data.success) {
        tg?.showAlert(`✅ Промокод активирован! Получено: ${data.reward} ⭐`)
        setPromoCode('')
        onClose()
      } else {
        tg?.showAlert(`❌ ${data.error || 'Ошибка активации промокода'}`)
      }
    } catch (error) {
      console.error('Error activating promo code:', error)
      window.Telegram?.WebApp?.showAlert('❌ Ошибка при активации промокода')
    } finally {
      setIsLoading(false)
    }
  }

  const generatePromoCode = async () => {
    setIsLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/promocode/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, type: 'ref' })
      })
      
      const data = await response.json()
      
      if (data.success) {
        setGeneratedCode(data.promoCode)
        setInvitedCount(data.invitedCount || 0)
        setRequiredRefs(data.requiredRefs || 10)
        setPromoType(data.promoType || 'ref')
      } else {
        tg?.showAlert(`❌ ${data.error || 'Ошибка создания промокода'}`)
      }
    } catch (error) {
      console.error('Error generating promo code:', error)
      window.Telegram?.WebApp?.showAlert('❌ Ошибка при создании промокода')
    } finally {
      setIsLoading(false)
    }
  }

  const copyPromoCode = () => {
    navigator.clipboard.writeText(generatedCode)
    window.Telegram?.WebApp?.showAlert('✅ Промокод скопирован!')
  }

  const loadHistory = async () => {
    setIsLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/promocode/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, type: 'ref' })
      })
      
      const data = await response.json()
      
      if (data.success) {
        setHistory(data.history || [])
        setShowHistory(true)
      } else {
        window.Telegram?.WebApp?.showAlert('❌ Ошибка загрузки истории')
      }
    } catch (error) {
      console.error('Error loading history:', error)
      window.Telegram?.WebApp?.showAlert('❌ Ошибка при загрузке истории')
    } finally {
      setIsLoading(false)
    }
  }

  const sanitizePromoCode = (input) => {
    // Удаляем все кроме букв, цифр и дефиса/подчеркивания
    return input
      .toUpperCase()
      .replace(/[^A-Z0-9_-]/g, '')
      .slice(0, 16)
  }

  const createCustomPromoCode = async () => {
    if (!customName.trim()) {
      window.Telegram?.WebApp?.showAlert('❌ Введите название промокода')
      return
    }

    const sanitized = sanitizePromoCode(customName)
    
    if (sanitized.length < 3) {
      window.Telegram?.WebApp?.showAlert('❌ Минимум 3 символа (буквы, цифры, _ или -)')
      return
    }

    setIsLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/promocode/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, newName: sanitized })
      })
      
      const data = await response.json()
      
      if (data.success) {
        setGeneratedCode(data.promoCode)
        setPromoType('refCustom')
        setShowCustomNameInput(false)
        setCustomName('')
        tg?.showAlert('✅ Именной промокод создан!')
      } else {
        tg?.showAlert(`❌ ${data.error || 'Ошибка создания именного промокода'}`)
      }
    } catch (error) {
      console.error('Error creating custom promo code:', error)
      window.Telegram?.WebApp?.showAlert('❌ Ошибка при создании именного промокода')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <>
      <div className="promo-modal-backdrop" onClick={onClose} />
      <div className="promo-modal-sheet">
        <button className="promo-close-btn" onClick={onClose}>✕</button>
        
        {generatedCode && (
          <button className="promo-back-btn" onClick={() => {
            setGeneratedCode('')
            setShowCreateSection(false)
            setShowCustomNameInput(false)
          }}>
            Активировать
          </button>
        )}
        
        <div className="promo-modal-content">
          {!showCreateSection ? (
            <>
              {/* Секция активации промокода */}
              <div className="promo-animation-container">
                <LottieAnimation animationData={giftAnim} width={120} height={120} />
              </div>
              
              <h2 className="promo-modal-title">Введите промокод</h2>
              
              <input
                type="text"
                className="promo-input"
                placeholder="Введите код..."
                value={promoCode}
                onChange={(e) => setPromoCode(sanitizePromoCode(e.target.value))}
                maxLength={16}
                disabled={isLoading}
              />
              
              <button 
                className="promo-button promo-button-primary"
                onClick={handleActivate}
                disabled={isLoading || !promoCode.trim()}
              >
                {isLoading ? 'Загрузка...' : 'Активировать'}
              </button>
              
              <button 
                className="promo-link-button"
                onClick={() => setShowCreateSection(true)}
              >
                Создать свой промокод
              </button>
            </>
          ) : (
            <>
              {/* Секция создания промокода */}
              {!generatedCode ? (
                <>
                  <div className="promo-animation-container-bottom">
                    <LottieAnimation animationData={giftAnim} width={100} height={100} />
                  </div>
                  
                  <div className="promo-rules-section">
                    <div 
                      className="promo-rules-header"
                      onClick={() => setShowRules(!showRules)}
                    >
                      <span className="promo-rules-title">Правила реферальной программы</span>
                      <span className="promo-rules-arrow">{showRules ? '▼' : '▶'}</span>
                    </div>
                    
                    {showRules && (
                      <div className="promo-rules-content">
                        <p className="promo-rule-item">
                          🎁 За активацию вашего промокода друг получает <strong>25 звезд</strong>
                        </p>
                        <p className="promo-rule-item">
                          💰 Вы получаете <strong>10% от всех его пополнений</strong> на реферальный баланс
                        </p>
                        <p className="promo-rule-item">
                          ⭐ Реферальный баланс можно использовать для игры
                        </p>
                      </div>
                    )}
                  </div>
                  
                  <button 
                    className="promo-button promo-button-primary"
                    onClick={generatePromoCode}
                    disabled={isLoading}
                  >
                    {isLoading ? 'Генерация...' : 'Сгенерировать промокод'}
                  </button>
                  
                  <button 
                    className="promo-link-button"
                    onClick={() => setShowCreateSection(false)}
                  >
                    ← Назад к активации
                  </button>
                </>
              ) : (
                <>
                  {/* Показываем сгенерированный промокод */}
                  <div className="promo-animation-container">
                    <LottieAnimation animationData={giftAnim} width={120} height={120} />
                  </div>
                  
                  <h2 className="promo-modal-title">Ваш промокод</h2>
                  
                  <div className="promo-code-display" onClick={copyPromoCode}>
                    <span className="promo-code-text">{generatedCode}</span>
                    <span className="promo-code-hint">Нажмите чтобы скопировать</span>
                  </div>
                  
                  {/* Кнопки баланс и история */}
                  <div className="promo-action-buttons">
                    <div 
                      className="promo-balance-display promo-balance-clickable"
                      onClick={() => setShowWithdrawalDialog(true)}
                    >
                      <LottieAnimation animationData={starAnim} width={24} height={24} />
                      <span className="promo-balance-text">{refBalance}</span>
                    </div>
                    <button 
                      className="promo-history-btn"
                      onClick={() => loadHistory()}
                    >
                      История
                    </button>
                  </div>
                  
                  <div className="promo-invite-info">
                    {!showCustomNameInput && promoType === 'ref' ? (
                      <>
                        <p className="promo-invite-text">
                          {invitedCount >= requiredRefs ? 'Вы можете создать именной промокод!' : `Нужно ${requiredRefs} приглашенных (${invitedCount}/${requiredRefs})`}
                        </p>
                        <button 
                          className={`promo-button ${invitedCount >= requiredRefs ? 'promo-button-primary' : 'promo-button-secondary'}`}
                          disabled={invitedCount < requiredRefs}
                          onClick={() => setShowCustomNameInput(true)}
                        >
                          Именной промокод
                        </button>
                      </>
                    ) : showCustomNameInput ? (
                      <>
                        <h3 className="promo-modal-subtitle">Создать именной промокод</h3>
                        <input
                          type="text"
                          className="promo-input"
                          placeholder="Введите название (до 16 символов)"
                          value={customName}
                          onChange={(e) => setCustomName(sanitizePromoCode(e.target.value))}
                          maxLength={16}
                          disabled={isLoading}
                        />
                        <p className="promo-hint-text">Разрешены: буквы, цифры, _ и -</p>
                        <div className="promo-button-row">
                          <button 
                            className="promo-button promo-button-secondary"
                            onClick={() => {
                              setShowCustomNameInput(false)
                              setCustomName('')
                            }}
                            disabled={isLoading}
                          >
                            Отмена
                          </button>
                          <button 
                            className="promo-button promo-button-primary"
                            onClick={createCustomPromoCode}
                            disabled={isLoading || customName.length < 3}
                          >
                            {isLoading ? 'Создание...' : 'Создать'}
                          </button>
                        </div>
                      </>
                    ) : promoType === 'refCustom' ? (
                      <>
                        <p className="promo-invite-text">
                          ✨ Ваш промокод уже именной!
                        </p>
                      </>
                    ) : null}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Модалка истории */}
      {showHistory && (
        <div className="promo-modal-backdrop promo-history-backdrop" onClick={() => setShowHistory(false)}>
          <div className="promo-modal-sheet promo-history-sheet" onClick={(e) => e.stopPropagation()}>
            <button className="promo-close-btn" onClick={() => setShowHistory(false)}>×</button>
            
            <div className="promo-modal-content">
              <h2 className="promo-modal-title">История промокода</h2>
              
              {history.length === 0 ? (
                <div className="promo-history-empty">
                  <p>История пуста</p>
                </div>
              ) : (
                <div className="promo-history-list">
                  {history.map((item, index) => (
                    <div key={index} className="promo-history-item">
                      <div className="promo-history-avatar">
                        {item.avatarUrl ? (
                          <img src={item.avatarUrl} alt={item.username} />
                        ) : (
                          <div className="promo-history-avatar-placeholder">
                            {item.username.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                      <div className="promo-history-info">
                        <div className="promo-history-username">{item.username}</div>
                        <div className="promo-history-date">{new Date(item.createdAt).toLocaleDateString()}</div>
                      </div>
                      <div className="promo-history-action">
                        {item.actionType === 'activated' ? (
                          'Активировал промокод'
                        ) : (
                          <div className="promo-history-topup">
                            <div className="promo-history-topup-amount">Пополнил +{item.amount}⭐</div>
                            <div className="promo-history-topup-income">Доход 10%</div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Диалог вывода средств */}
      {showWithdrawalDialog && (
        <>
          <div className="promo-withdrawal-backdrop" onClick={() => setShowWithdrawalDialog(false)} />
          <div className="promo-withdrawal-sheet">
            <button className="promo-close-btn" onClick={() => setShowWithdrawalDialog(false)}>×</button>
            
            <div className="promo-withdrawal-content">
              <div>
                <p className="promo-withdrawal-balance">
                  Доступно для вывода
                </p>
                <div className="promo-withdrawal-amount-display">
                  {refBalance} ⭐
                </div>
              </div>
              
              <div className="promo-withdrawal-input-wrapper">
                <label className="promo-withdrawal-input-label">
                  Сумма вывода
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  className="promo-withdrawal-input"
                  placeholder="0"
                  value={withdrawalAmount}
                  onChange={(e) => {
                    const value = e.target.value.replace(/[^0-9]/g, '')
                    setWithdrawalAmount(value)
                  }}
                  maxLength="10"
                />
              </div>
              
              <button
                className="promo-withdrawal-submit"
                onClick={() => {
                  const amount = parseInt(withdrawalAmount)
                  if (amount > 0 && amount <= refBalance) {
                    const botUsername = 'HelpShellBot'
                    const url = `https://t.me/${botUsername}?start=withdraw_${amount}`
                    window.Telegram?.WebApp?.openTelegramLink(url)
                    setShowWithdrawalDialog(false)
                    setWithdrawalAmount('')
                  }
                }}
                disabled={!withdrawalAmount || parseInt(withdrawalAmount) <= 0 || parseInt(withdrawalAmount) > refBalance}
              >
                Продолжить
              </button>
            </div>
          </div>
        </>
      )}
    </>
  )
}

export default PromoCodeModal
