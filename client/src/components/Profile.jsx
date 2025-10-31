import { useEffect, useState } from 'react'
import './Profile.css'
import LottieAnimation from './LottieAnimation'
import bearAnim from '../assets/bear.json'
import bottleAnim from '../assets/bottle.json'
import cakeAnim from '../assets/cake.json'
import cupAnim from '../assets/cup.json'
import diamondAnim from '../assets/diamond.json'
import flowersAnim from '../assets/flowers.json'
import giftAnim from '../assets/gift.json'
import heartAnim from '../assets/heart.json'
import ringAnim from '../assets/ring.json'
import rocketAnim from '../assets/rocket.json'
import roseAnim from '../assets/rose.json'
import pawAnim from '../assets/paw.json'

const giftAnimations = {
  bear: bearAnim,
  bottle: bottleAnim,
  cake: cakeAnim,
  cup: cupAnim,
  diamond: diamondAnim,
  flowers: flowersAnim,
  gift: giftAnim,
  heart: heartAnim,
  ring: ringAnim,
  rocket: rocketAnim,
  rose: roseAnim,
  paw: pawAnim
}

function Profile() {
  const [user, setUser] = useState(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showAdminPanel, setShowAdminPanel] = useState(false)
  const [targetUserId, setTargetUserId] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [showChancesPanel, setShowChancesPanel] = useState(false)
  const [chances, setChances] = useState([])
  const [editingGift, setEditingGift] = useState(null)
  const [refundUserId, setRefundUserId] = useState('')
  const [refundTransactionId, setRefundTransactionId] = useState('')
  const [refundLoading, setRefundLoading] = useState(false)
  const [showRefundPanel, setShowRefundPanel] = useState(false)
  const [deductFromBalance, setDeductFromBalance] = useState(false)
  const [showCrashPanel, setShowCrashPanel] = useState(false)
  const [crashMaxMultiplier, setCrashMaxMultiplier] = useState(1000)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
      setUser(tg.initDataUnsafe.user)
    }

    const checkAdmin = async () => {
      try {
        const initData = tg?.initData
        if (!initData) {
          setLoading(false)
          return
        }

        const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
        const response = await fetch(`${apiUrl}/api/check-admin`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData })
        })

        const data = await response.json()
        if (data.valid && data.isAdmin) {
          setIsAdmin(true)
        }
      } catch (error) {
        console.error('Error checking admin status:', error)
      } finally {
        setLoading(false)
      }
    }

    checkAdmin()
  }, [])

  const getAvatarUrl = () => {
    if (user?.photo_url) {
      return user.photo_url
    }
    return null
  }

  const getInitials = () => {
    if (!user) return '?'
    const first = user.first_name?.[0] || ''
    const last = user.last_name?.[0] || ''
    return (first + last).toUpperCase() || '?'
  }

  const handleBanUser = async () => {
    if (!targetUserId.trim()) {
      alert('Введите User ID')
      return
    }

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/ban-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, targetUserId: parseInt(targetUserId) })
      })

      const data = await response.json()
      if (data.success) {
        alert('Пользователь забанен')
        setTargetUserId('')
      } else {
        alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'))
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }

  const loadChances = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/get-chances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid) {
        setChances(data.chances)
      }
    } catch (error) {
      console.error('Error loading chances:', error)
    }
  }

  const handleUpdateChance = async (giftName, visibleChance, realChance, pawMin = 0, pawMax = 0) => {
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/update-chances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, giftName, visibleChance, realChance, pawMin, pawMax })
      })

      const data = await response.json()
      if (data.success) {
        alert('Шансы обновлены')
        loadChances()
        setEditingGift(null)
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }

  const handleUnbanUser = async () => {
    if (!targetUserId.trim()) {
      alert('Введите User ID')
      return
    }

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/unban-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, targetUserId: parseInt(targetUserId) })
      })

      const data = await response.json()
      if (data.success) {
        alert('Пользователь разбанен')
        setTargetUserId('')
      } else {
        alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'))
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }

  const loadCrashSettings = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/crash/get-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid) {
        setCrashMaxMultiplier(data.maxMultiplier)
      }
    } catch (error) {
      console.error('Error loading crash settings:', error)
    }
  }

  const handleUpdateCrashSettings = async () => {
    if (!crashMaxMultiplier || crashMaxMultiplier < 2 || crashMaxMultiplier > 100000) {
      alert('Максимальный коэффициент должен быть от 2 до 100000')
      return
    }

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/crash/update-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, maxMultiplier: parseFloat(crashMaxMultiplier) })
      })

      const data = await response.json()
      if (data.success) {
        alert('Настройки краш-игры обновлены')
        setShowCrashPanel(false)
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }

  const handleRefund = async () => {
    if (!refundUserId.trim() || !refundTransactionId.trim()) {
      alert('Заполните все поля')
      return
    }

    const confirmText = deductFromBalance 
      ? `Вернуть платеж для пользователя ${refundUserId}?\nTransaction: ${refundTransactionId}\n\n⚠️ Баланс пользователя будет уменьшен (может уйти в минус)`
      : `Вернуть платеж для пользователя ${refundUserId}?\nTransaction: ${refundTransactionId}`
    
    const confirmed = confirm(confirmText)
    if (!confirmed) return

    setRefundLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/admin/refund-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          initData, 
          userId: parseInt(refundUserId),
          transactionId: refundTransactionId,
          deductFromBalance: deductFromBalance
        })
      })

      const data = await response.json()
      if (data.success) {
        let message = '✅ Платеж успешно возвращен'
        if (data.deductedAmount !== undefined && data.deductedAmount > 0) {
          message += `\nСписано со счета: ${data.deductedAmount} ⭐`
        }
        if (data.newBalance !== undefined) {
          message += `\nНовый баланс: ${data.newBalance} ⭐`
        }
        alert(message)
        setRefundUserId('')
        setRefundTransactionId('')
        setDeductFromBalance(false)
      } else {
        alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'))
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setRefundLoading(false)
    }
  }

  return (
    <div className="profile-page">
      <div className="profile-content">
        <div className="profile-card">
          <div className="avatar-container">
            {getAvatarUrl() ? (
              <img src={getAvatarUrl()} alt="Avatar" className="avatar-img" />
            ) : (
              <div className="avatar-placeholder">
                {getInitials()}
              </div>
            )}
          </div>

          <div className="profile-info">
            <h2 className="profile-name">
              {user?.first_name} {user?.last_name}
            </h2>
            {user?.username && (
              <p className="profile-username">@{user.username}</p>
            )}
          </div>

          <div className="profile-details">
            <div className="detail-item">
              <span className="detail-label">ID</span>
              <span className="detail-value">{user?.id || 'N/A'}</span>
            </div>
          </div>
        </div>

        {!loading && isAdmin && (
          <div className="profile-actions">
            <button className="action-button admin-button" onClick={() => setShowAdminPanel(true)}>
              <span className="button-icon">👑</span>
              <span className="button-text">Админ панель</span>
            </button>
          </div>
        )}
      </div>

      {showAdminPanel && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowAdminPanel(false)} />
          <div className="overlay-sheet admin-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowAdminPanel(false)}>✕</button>
            
            <div className="sheet-content">
              <h2 className="admin-panel-title">Админ панель</h2>
              
              <div className="admin-input-group">
                <label className="admin-label">User ID</label>
                <input
                  type="number"
                  className="admin-input"
                  placeholder="Введите ID пользователя"
                  value={targetUserId}
                  onChange={(e) => setTargetUserId(e.target.value)}
                  disabled={actionLoading}
                />
              </div>

              <div className="admin-buttons">
                <button 
                  className="admin-action-button ban-button" 
                  onClick={handleBanUser}
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Загрузка...' : 'Забанить'}
                </button>
                <button 
                  className="admin-action-button unban-button" 
                  onClick={handleUnbanUser}
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Загрузка...' : 'Разбанить'}
                </button>
              </div>

              <div className="admin-divider"></div>

              <button 
                className="admin-chances-button" 
                onClick={() => { 
                  loadChances(); 
                  setShowChancesPanel(true); 
                }}
                disabled={actionLoading}
              >
                <span className="button-icon">🎲</span>
                <span className="button-text">Управление шансами</span>
              </button>

              <div className="admin-divider"></div>

              <button 
                className="admin-chances-button refund-panel-button" 
                onClick={() => setShowRefundPanel(true)}
                disabled={actionLoading}
              >
                <span className="button-icon">💰</span>
                <span className="button-text">Возврат</span>
              </button>

              <div className="admin-divider"></div>

              <button 
                className="admin-chances-button crash-panel-button" 
                onClick={() => { 
                  loadCrashSettings(); 
                  setShowCrashPanel(true); 
                }}
                disabled={actionLoading}
              >
                <span className="button-icon">🚀</span>
                <span className="button-text">Краш</span>
              </button>
            </div>
          </div>
        </>
      )}

      {showChancesPanel && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowChancesPanel(false)} />
          <div className="overlay-sheet chances-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowChancesPanel(false)}>✕</button>
            
            <div className="sheet-content">
              <h2 className="admin-panel-title">Управление шансами</h2>
              <p className="chances-mode">Режим: Фри спин</p>
              
              <div className="chances-list">
                {chances.map((chance) => (
                  <div key={chance.name} className="chance-item">
                    <div className="chance-icon">
                      <LottieAnimation animationData={giftAnimations[chance.name]} width={50} height={50} />
                    </div>
                    <div className="chance-details">
                      <div className="chance-row">
                        <span className="chance-label">Видимый шанс:</span>
                        {editingGift === chance.name ? (
                          <input
                            type="number"
                            className="chance-input"
                            defaultValue={chance.visible}
                            id={`visible-${chance.name}`}
                            disabled={actionLoading}
                          />
                        ) : (
                          <span className="chance-value">{chance.visible}%</span>
                        )}
                      </div>
                      <div className="chance-row">
                        <span className="chance-label">Реальный шанс:</span>
                        {editingGift === chance.name ? (
                          <input
                            type="number"
                            className="chance-input"
                            defaultValue={chance.real}
                            id={`real-${chance.name}`}
                            disabled={actionLoading}
                          />
                        ) : (
                          <span className="chance-value">{chance.real}%</span>
                        )}
                      </div>
                      {chance.name === 'paw' && (
                        <div className="chance-row">
                          <span className="chance-label">Лапок (диапазон):</span>
                          {editingGift === chance.name ? (
                            <div className="paw-range-inputs">
                              <input
                                type="number"
                                className="chance-input paw-range-input"
                                defaultValue={chance.pawMin || 1}
                                id={`pawMin-${chance.name}`}
                                min="0"
                                max="100"
                                placeholder="От"
                                disabled={actionLoading}
                              />
                              <span className="range-separator">-</span>
                              <input
                                type="number"
                                className="chance-input paw-range-input"
                                defaultValue={chance.pawMax || 5}
                                id={`pawMax-${chance.name}`}
                                min="0"
                                max="100"
                                placeholder="До"
                                disabled={actionLoading}
                              />
                            </div>
                          ) : (
                            <span className="chance-value">{chance.pawMin || 0}-{chance.pawMax || 0}</span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="chance-actions">
                      {editingGift === chance.name ? (
                        <>
                          <button 
                            className="chance-btn save-btn"
                            onClick={() => {
                              const visible = parseFloat(document.getElementById(`visible-${chance.name}`).value)
                              const real = parseFloat(document.getElementById(`real-${chance.name}`).value)
                              let pawMin = 0, pawMax = 0
                              if (chance.name === 'paw') {
                                pawMin = parseInt(document.getElementById(`pawMin-${chance.name}`).value) || 0
                                pawMax = parseInt(document.getElementById(`pawMax-${chance.name}`).value) || 0
                              }
                              handleUpdateChance(chance.name, visible, real, pawMin, pawMax)
                            }}
                            disabled={actionLoading}
                          >
                            ✓
                          </button>
                          <button 
                            className="chance-btn cancel-btn"
                            onClick={() => setEditingGift(null)}
                            disabled={actionLoading}
                          >
                            ✕
                          </button>
                        </>
                      ) : (
                        <button 
                          className="chance-btn edit-btn"
                          onClick={() => setEditingGift(chance.name)}
                        >
                          ✎
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {showRefundPanel && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowRefundPanel(false)} />
          <div className="overlay-sheet refund-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowRefundPanel(false)}>✕</button>
            
            <div className="sheet-content">
              <h2 className="admin-panel-title">Возврат платежа</h2>
              
              <div className="admin-input-group">
                <label className="admin-label">User ID</label>
                <input
                  type="number"
                  className="admin-input"
                  placeholder="ID пользователя"
                  value={refundUserId}
                  onChange={(e) => setRefundUserId(e.target.value)}
                  disabled={refundLoading}
                />
              </div>

              <div className="admin-input-group">
                <label className="admin-label">Transaction ID</label>
                <input
                  type="text"
                  className="admin-input"
                  placeholder="Telegram Payment Charge ID"
                  value={refundTransactionId}
                  onChange={(e) => setRefundTransactionId(e.target.value)}
                  disabled={refundLoading}
                />
              </div>

              <div className="admin-toggle-group">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    className="toggle-checkbox"
                    checked={deductFromBalance}
                    onChange={(e) => setDeductFromBalance(e.target.checked)}
                    disabled={refundLoading}
                  />
                  <span className="toggle-slider"></span>
                  <span className="toggle-text">Списать с баланса</span>
                </label>
                {deductFromBalance && (
                  <p className="toggle-hint">⚠️ Баланс может уйти в минус</p>
                )}
              </div>

              <button 
                className="admin-action-button refund-button" 
                onClick={handleRefund}
                disabled={refundLoading || !refundUserId || !refundTransactionId}
              >
                {refundLoading ? 'Загрузка...' : 'Вернуть'}
              </button>
            </div>
          </div>
        </>
      )}

      {showCrashPanel && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowCrashPanel(false)} />
          <div className="overlay-sheet crash-settings-panel">
            <button className="close-panel-btn" onClick={() => setShowCrashPanel(false)}>✕</button>
            
            <div className="sheet-content">
              <h2 className="admin-panel-title">Настройки краш-игры</h2>
              
              <div className="admin-input-group">
                <label className="admin-label">Максимальный коэффициент</label>
                <input
                  type="number"
                  className="admin-input"
                  placeholder="От 2 до 100000"
                  value={crashMaxMultiplier}
                  onChange={(e) => setCrashMaxMultiplier(e.target.value)}
                  disabled={actionLoading}
                  min="2"
                  max="100000"
                  step="0.1"
                />
                <p className="input-hint">
                  Определяет максимальный множитель, который может выпасть в краш-игре (1% шанс на диапазон 50x - max)
                </p>
              </div>

              <button 
                className="admin-action-button save-button" 
                onClick={handleUpdateCrashSettings}
                disabled={actionLoading}
              >
                {actionLoading ? 'Загрузка...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Profile
