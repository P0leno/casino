import { useState } from 'react'
import './AdminPanel.css'

const tg = window.Telegram?.WebApp
const initData = tg?.initData
const apiUrl = import.meta.env.VITE_API_URL || ''

function AdminPanel({ onClose }) {
  const [view, setView] = useState('menu')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [searchQuery, setSearchQuery] = useState('')
  const [searchUsers, setSearchUsers] = useState([])
  const [searchTyping, setSearchTyping] = useState(null)
  const [searchNoResults, setSearchNoResults] = useState(false)

  const [topUpUserId, setTopUpUserId] = useState('')
  const [topUpAmount, setTopUpAmount] = useState('')
  const [giftUserId, setGiftUserId] = useState('')
  const [giftName, setGiftName] = useState('')
  const [adminMgmtId, setAdminMgmtId] = useState('')

  const [stats, setStats] = useState(null)

  const [userInfo, setUserInfo] = useState(null)
  const [userInfoId, setUserInfoId] = useState(null)

  const [currentTheme, setCurrentTheme] = useState(() => {
    return localStorage.getItem('theme') || 'default'
  })

  const switchTheme = (name) => {
    setCurrentTheme(name)
    if (name === 'default') {
      document.documentElement.removeAttribute('data-theme')
      localStorage.removeItem('theme')
    } else {
      document.documentElement.setAttribute('data-theme', name)
      localStorage.setItem('theme', name)
    }
  }

  const PRESETS = [
    { id: 'default', label: 'Стандарт', icon: '💜', desc: 'Фиолетовый акцент, blur 16px' },
    { id: 'minimalism', label: 'Минимализм', icon: '⬜', desc: 'Белый акцент, blur 8px, острые углы' },
    { id: 'halloween', label: 'Хэллоуин', icon: '🎃', desc: 'Оранжевый, тёмный фон' },
    { id: 'newyear', label: 'Новый год', icon: '🎄', desc: 'Золотой акцент, праздничный' },
    { id: 'easter', label: 'Пасха', icon: '🐰', desc: 'Розовый, пастельные тона' },
    { id: 'cny', label: 'Китайский НГ', icon: '🧧', desc: 'Красный, золотой' },
    { id: 'maximalism', label: 'Максимализм', icon: '✨', desc: 'Максимум стекла, blur 24px' },
  ]

  const callApi = async (endpoint, body) => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, ...body })
      })
      const data = await res.json()
      if (!data.success) throw new Error(data.message || 'Ошибка')
      return data
    } catch (e) {
      setError(e.message)
      return null
    } finally {
      setLoading(false)
    }
  }

  const doSearch = async (q) => {
    if (!q.trim()) {
      setSearchUsers([])
      setSearchNoResults(false)
      return
    }
    const data = await callApi('/api/admin/search-users', { query: q.trim() })
    if (data) {
      setSearchUsers(data.users || [])
      setSearchNoResults(data.users && data.users.length === 0)
    }
  }

  const handleSearchInput = (e) => {
    const v = e.target.value
    setSearchQuery(v)
    setUserInfo(null)
    setUserInfoId(null)
    setSearchNoResults(false)
    if (searchTyping) clearTimeout(searchTyping)
    if (v.trim().length >= 1) {
      setSearchTyping(setTimeout(() => doSearch(v), 350))
    } else {
      setSearchUsers([])
    }
  }

  const handleSelectUser = async (u) => {
    setSearchQuery(u.username ? `@${u.username}` : String(u.id))
    setSearchUsers([])
    setUserInfoId(u.id)
    const data = await callApi('/api/admin/user-info', { userId: u.id })
    if (data) {
      setUserInfo(data.user)
    }
  }

  const handleTopUp = async () => {
    if (!topUpUserId.trim() || !topUpAmount.trim()) return
    const data = await callApi('/api/admin/top-up', {
      userId: parseInt(topUpUserId),
      amount: parseInt(topUpAmount)
    })
    if (data) {
      alert(`✅ Пополнено на ${data.amount} ⭐. Баланс: ${data.newBalance} ⭐`)
      setTopUpAmount('')
    }
  }

  const handleGiveGift = async () => {
    if (!giftUserId.trim() || !giftName.trim()) return
    const data = await callApi('/api/admin/give-gift', {
      userId: parseInt(giftUserId),
      giftName: giftName.trim()
    })
    if (data) {
      alert(`✅ Подарок "${data.giftName}" выдан`)
      setGiftName('')
    }
  }

  const handleAddAdmin = async () => {
    if (!adminMgmtId.trim()) return
    const data = await callApi('/api/admin/add-admin', { adminId: parseInt(adminMgmtId) })
    if (data) {
      alert(`✅ Админ ${adminMgmtId} добавлен`)
      setAdminMgmtId('')
    }
  }

  const handleRemoveAdmin = async () => {
    if (!adminMgmtId.trim()) return
    const data = await callApi('/api/admin/remove-admin', { adminId: parseInt(adminMgmtId) })
    if (data) {
      alert(`✅ Админ ${adminMgmtId} удалён`)
      setAdminMgmtId('')
    }
  }

  const handleBan = async () => {
    if (!userInfoId) return
    const data = await callApi('/api/ban-user', { targetUserId: userInfoId })
    if (data) {
      alert('✅ Пользователь забанен')
      const d2 = await callApi('/api/admin/user-info', { userId: userInfoId })
      if (d2) setUserInfo(d2.user)
    }
  }

  const handleUnban = async () => {
    if (!userInfoId) return
    const data = await callApi('/api/unban-user', { targetUserId: userInfoId })
    if (data) {
      alert('✅ Пользователь разбанен')
      const d2 = await callApi('/api/admin/user-info', { userId: userInfoId })
      if (d2) setUserInfo(d2.user)
    }
  }

  const loadStats = async () => {
    const data = await callApi('/api/admin/stats', {})
    if (data) {
      setStats(data)
      setView('stats')
    }
  }

  const views = {
    menu: (
      <div className="ap-menu">
        <button className="ap-menu-btn" onClick={() => { setView('search'); setSearchQuery(''); setSearchUsers([]); setUserInfo(null); setUserInfoId(null); }}>
          <span className="ap-menu-icon">🔍</span>
          <span>Поиск пользователя</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('topup')}>
          <span className="ap-menu-icon">💰</span>
          <span>Пополнение / Списание</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('givegift')}>
          <span className="ap-menu-icon">🎁</span>
          <span>Выдача подарка</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('adminmgmt')}>
          <span className="ap-menu-icon">👑</span>
          <span>Управление админами</span>
        </button>
        <button className="ap-menu-btn" onClick={loadStats}>
          <span className="ap-menu-icon">📊</span>
          <span>Статистика</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('settings')}>
          <span className="ap-menu-icon">🎨</span>
          <span>Тема оформления</span>
        </button>
      </div>
    ),

    search: (
      <div className="ap-view">
        <button className="ap-back" onClick={() => setView('menu')}>← Назад</button>
        <h3 className="ap-view-title">🔍 Поиск пользователя</h3>
        <div className="ap-search-wrapper">
          <div className="ap-search-row">
            <input
              className="ap-input ap-search-input"
              placeholder="ID или @username"
              value={searchQuery}
              onChange={handleSearchInput}
              autoFocus
            />
            {loading && <span className="ap-search-spinner" />}
          </div>
          {searchUsers.length > 0 && (
            <div className="ap-search-results">
              {searchUsers.map(u => (
                <div key={u.id} className="ap-search-result-item" onClick={() => handleSelectUser(u)}>
                  <span className="ap-sr-id">{u.id}</span>
                  <span className="ap-sr-name">@{u.username || '—'}</span>
                  <span className="ap-sr-balance">{u.balance} ⭐</span>
                  {u.isBanned && <span className="ap-sr-banned">🚫</span>}
                </div>
              ))}
            </div>
          )}
          {searchNoResults && searchQuery.trim() && !searchUsers.length && (
            <p className="ap-no-results">Пользователи не найдены</p>
          )}
        </div>
        {userInfo && (
          <div className="ap-user-card glass">
            <div className="ap-user-info">
              <p><strong>ID:</strong> {userInfo.id}</p>
              <p><strong>Username:</strong> @{userInfo.username || '—'}</p>
              <p><strong>Баланс:</strong> {userInfo.balance} ⭐</p>
              <p><strong>Бонус:</strong> {userInfo.bonusBalance} ⭐</p>
              <p><strong>Инвентарь:</strong> {userInfo.inventory?.length || 0} предметов</p>
              <p><strong>Бан:</strong> {userInfo.isBanned ? '🚫 Да' : '✅ Нет'}</p>
              <p><strong>Создан:</strong> {userInfo.creationDate || '—'}</p>
            </div>
            <div className="ap-user-actions">
              <button className="ap-btn ap-btn-danger" onClick={handleBan} disabled={loading}>
                {userInfo?.isBanned ? '🚫 Забанен' : 'Забанить'}
              </button>
              <button className="ap-btn ap-btn-success" onClick={handleUnban} disabled={loading || !userInfo?.isBanned}>
                Разбанить
              </button>
            </div>
          </div>
        )}
      </div>
    ),

    topup: (
      <div className="ap-view">
        <button className="ap-back" onClick={() => setView('menu')}>← Назад</button>
        <h3 className="ap-view-title">💰 Пополнение / Списание</h3>
        <div className="ap-input-group">
          <label>ID пользователя</label>
          <input className="ap-input" placeholder="12345" value={topUpUserId} onChange={e => setTopUpUserId(e.target.value)} />
        </div>
        <div className="ap-input-group">
          <label>Сумма (отрицательная — списание)</label>
          <input className="ap-input" type="number" placeholder="1000" value={topUpAmount} onChange={e => setTopUpAmount(e.target.value)} />
        </div>
        <button className="ap-btn ap-btn-primary" onClick={handleTopUp} disabled={loading}>
          {loading ? '...' : 'Выполнить'}
        </button>
      </div>
    ),

    givegift: (
      <div className="ap-view">
        <button className="ap-back" onClick={() => setView('menu')}>← Назад</button>
        <h3 className="ap-view-title">🎁 Выдача подарка</h3>
        <div className="ap-input-group">
          <label>ID пользователя</label>
          <input className="ap-input" placeholder="12345" value={giftUserId} onChange={e => setGiftUserId(e.target.value)} />
        </div>
        <div className="ap-input-group">
          <label>Название подарка</label>
          <input className="ap-input" placeholder="flowers" value={giftName} onChange={e => setGiftName(e.target.value)} />
        </div>
        <button className="ap-btn ap-btn-primary" onClick={handleGiveGift} disabled={loading}>
          {loading ? '...' : 'Выдать'}
        </button>
      </div>
    ),

    adminmgmt: (
      <div className="ap-view">
        <button className="ap-back" onClick={() => setView('menu')}>← Назад</button>
        <h3 className="ap-view-title">👑 Управление админами</h3>
        <div className="ap-input-group">
          <label>ID пользователя</label>
          <input className="ap-input" placeholder="6252527489" value={adminMgmtId} onChange={e => setAdminMgmtId(e.target.value)} />
        </div>
        <div className="ap-btn-row">
          <button className="ap-btn ap-btn-success" onClick={handleAddAdmin} disabled={loading}>+ Добавить</button>
          <button className="ap-btn ap-btn-danger" onClick={handleRemoveAdmin} disabled={loading}>— Удалить</button>
        </div>
      </div>
    ),

    stats: stats ? (
      <div className="ap-view">
        <button className="ap-back" onClick={() => setView('menu')}>← Назад</button>
        <h3 className="ap-view-title">📊 Статистика</h3>
        <div className="ap-stats-grid">
          <div className="ap-stat-card glass">
            <span className="ap-stat-value">{stats.users}</span>
            <span className="ap-stat-label">Пользователей</span>
          </div>
          <div className="ap-stat-card glass">
            <span className="ap-stat-value">{stats.banned}</span>
            <span className="ap-stat-label">Забанено</span>
          </div>
          <div className="ap-stat-card glass">
            <span className="ap-stat-value">{stats.totalBalance}</span>
            <span className="ap-stat-label">Всего ⭐</span>
          </div>
          <div className="ap-stat-card glass">
            <span className="ap-stat-value">{stats.cases}</span>
            <span className="ap-stat-label">Кейсов</span>
          </div>
          <div className="ap-stat-card glass">
            <span className="ap-stat-value">{stats.gifts}</span>
            <span className="ap-stat-label">Подарков</span>
          </div>
          <div className="ap-stat-card glass">
            <span className="ap-stat-value">{stats.admins}</span>
            <span className="ap-stat-label">Админов</span>
          </div>
        </div>
      </div>
    ) : null,

    settings: (
      <div className="ap-view">
        <button className="ap-back" onClick={() => setView('menu')}>← Назад</button>
        <h3 className="ap-view-title">🎨 Тема оформления</h3>
        <p className="ap-hint">Выберите пресет. Сохраняется в localStorage.</p>
        <div className="ap-theme-grid">
          {PRESETS.map(p => (
            <button
              key={p.id}
              className={`ap-theme-card ${currentTheme === p.id ? 'active' : ''}`}
              onClick={() => switchTheme(p.id)}
            >
              <span className="ap-theme-icon">{p.icon}</span>
              <span className="ap-theme-label">{p.label}</span>
              <span className="ap-theme-desc">{p.desc}</span>
            </button>
          ))}
        </div>
      </div>
    ),
  }

  return (
    <div className="ap-overlay">
      <div className="ap-sheet">
        <div className="ap-header">
          <div className="ap-header-content">
            <span className="ap-header-icon">👑</span>
            <h2 className="ap-header-title">Админ панель</h2>
          </div>
          <button className="ap-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="ap-body">
          {error && <div className="ap-error">{error}</div>}
          {views[view] || views.menu}
        </div>
      </div>
    </div>
  )
}

export default AdminPanel
