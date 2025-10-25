import { useEffect, useState } from 'react'
import './Profile.css'

function Profile() {
  const [user, setUser] = useState(null)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
      setUser(tg.initDataUnsafe.user)
    }
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

  return (
    <div className="profile-page">
      <div className="profile-header">
        <h1>Профиль</h1>
      </div>

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

        <div className="profile-actions">
          <button className="action-button">
            <span className="button-icon">⚙️</span>
            <span className="button-text">Настройки</span>
          </button>

          <button className="action-button">
            <span className="button-icon">📊</span>
            <span className="button-text">Статистика</span>
          </button>

          <button className="action-button">
            <span className="button-icon">ℹ️</span>
            <span className="button-text">О приложении</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default Profile
