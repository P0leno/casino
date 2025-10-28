import { useEffect, useState } from 'react'
import './Profile.css'
import LottieAnimation from './LottieAnimation'
import bearAnim from '../assets/bear.json'
import cakeAnim from '../assets/cake.json'
import cupAnim from '../assets/cup.json'
import diamondAnim from '../assets/diamond.json'
import flowersAnim from '../assets/flowers.json'
import giftAnim from '../assets/gift.json'
import heartAnim from '../assets/heart.json'
import ringAnim from '../assets/ring.json'
import rocketAnim from '../assets/rocket.json'
import roseAnim from '../assets/rose.json'

const giftAnimations = {
  bear: bearAnim,
  cake: cakeAnim,
  cup: cupAnim,
  diamond: diamondAnim,
  flowers: flowersAnim,
  gift: giftAnim,
  heart: heartAnim,
  ring: ringAnim,
  rocket: rocketAnim,
  rose: roseAnim
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

  const handleUpdateChance = async (giftName, visibleChance, realChance) => {
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      
      const response = await fetch(`${apiUrl}/api/update-chances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, giftName, visibleChance, realChance })
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
                    </div>
                    <div className="chance-actions">
                      {editingGift === chance.name ? (
                        <>
                          <button 
                            className="chance-btn save-btn"
                            onClick={() => {
                              const visible = parseFloat(document.getElementById(`visible-${chance.name}`).value)
                              const real = parseFloat(document.getElementById(`real-${chance.name}`).value)
                              handleUpdateChance(chance.name, visible, real)
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
    </div>
  )
}

export default Profile
