import { useState } from 'react'
import './AdminPanel.css'
import Icon from './Icons'

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

  const switchFont = (name) => {
    setCurrentFont(name)
    if (name === 'montserrat') {
      document.documentElement.removeAttribute('data-font')
      localStorage.removeItem('font')
    } else {
      document.documentElement.setAttribute('data-font', name)
      localStorage.setItem('font', name)
    }
  }

  const [currentFont, setCurrentFont] = useState(() => {
    return localStorage.getItem('font') || 'montserrat'
  })

  const [userBlur, setUserBlur] = useState(() => {
    return parseFloat(localStorage.getItem('userBlur')) || 1
  })

  const [userOpacity, setUserOpacity] = useState(() => {
    return parseFloat(localStorage.getItem('userOpacity')) || 1
  })

  const [userSpeed, setUserSpeed] = useState(() => {
    return parseFloat(localStorage.getItem('userSpeed')) || 1
  })

  const updateCSSVar = (name, value) => {
    document.documentElement.style.setProperty(name, value)
  }

  const handleBlurChange = (v) => {
    const val = parseFloat(v)
    setUserBlur(val)
    localStorage.setItem('userBlur', val)
    updateCSSVar('--user-blur', val)
  }

  const handleOpacityChange = (v) => {
    const val = parseFloat(v)
    setUserOpacity(val)
    localStorage.setItem('userOpacity', val)
    updateCSSVar('--user-opacity', val)
  }

  const handleSpeedChange = (v) => {
    const val = parseFloat(v)
    setUserSpeed(val)
    localStorage.setItem('userSpeed', val)
    updateCSSVar('--user-animate-speed', val)
  }

  const [iconFill, setIconFill] = useState(() => localStorage.getItem('iconFill') === 'true')
  const [iconGlow, setIconGlow] = useState(() => localStorage.getItem('iconGlow') === 'true')
  const [iconBold, setIconBold] = useState(() => localStorage.getItem('iconBold') !== 'false')
  const [animMode, setAnimMode] = useState(() => localStorage.getItem('animMode') || 'default')
  const [uiStyle, setUiStyle] = useState(() => localStorage.getItem('uiStyle') || 'glass')

  const toggleIconFill = () => {
    const v = !iconFill
    setIconFill(v)
    localStorage.setItem('iconFill', v)
  }

  const toggleIconGlow = () => {
    const v = !iconGlow
    setIconGlow(v)
    localStorage.setItem('iconGlow', v)
  }

  const toggleIconBold = () => {
    const v = !iconBold
    setIconBold(v)
    localStorage.setItem('iconBold', v)
  }

  const switchAnimMode = (mode) => {
    setAnimMode(mode)
    localStorage.setItem('animMode', mode)
    if (mode === 'default') {
      document.documentElement.removeAttribute('data-animation')
    } else {
      document.documentElement.setAttribute('data-animation', mode)
    }
  }

  const switchUiStyle = (style) => {
    setUiStyle(style)
    localStorage.setItem('uiStyle', style)
    if (style === 'glass') {
      document.documentElement.removeAttribute('data-ui')
    } else {
      document.documentElement.setAttribute('data-ui', style)
    }
  }

  const THEME_PALETTE = {
    default: { bg: '#6c5ce7', fg: '#ffffff' },
    minimalism: { bg: '#ffffff', fg: '#0a0a0a' },
    halloween: { bg: '#ff6b35', fg: '#0d0d0d' },
    newyear: { bg: '#ffd700', fg: '#0f0d08' },
    easter: { bg: '#f472b6', fg: '#1a0f14' },
    cny: { bg: '#dc2626', fg: '#0d0808' },
    maximalism: { bg: 'linear-gradient(135deg, #6c5ce7, #a855f7, #3b82f6)', fg: '#0a0a0a' },
    valentine: { bg: '#e11d48', fg: '#1a0a0f' },
  }

  const PRESETS = [
    { id: 'default', label: 'Стандарт', icon: 'star', desc: 'Фиолетовый акцент, blur 16px' },
    { id: 'minimalism', label: 'Минимализм', icon: 'home', desc: 'Белый акцент, blur 8px, острые углы' },
    { id: 'halloween', label: 'Хэллоуин', icon: 'fire', desc: 'Оранжевый, тёмный фон' },
    { id: 'newyear', label: 'Новый год', icon: 'star', desc: 'Золотой акцент, праздничный' },
    { id: 'easter', label: 'Пасха', icon: 'gift', desc: 'Розовый, пастельные тона' },
    { id: 'cny', label: 'Китайский НГ', icon: 'fire', desc: 'Красный, золотой' },
    { id: 'maximalism', label: 'Максимализм', icon: 'bolt', desc: 'Максимум стекла, blur 24px' },
    { id: 'valentine', label: 'Валентинки', icon: 'star', desc: 'Красный, розовый, сердца' },
  ]

  const FONTS = [
    { id: 'montserrat', label: 'Montserrat', icon: 'Aa', desc: 'Геометричный гротеск', style: { fontWeight: 600 } },
    { id: 'inter', label: 'Inter', icon: 'Aa', desc: 'Чистый, разреженный', style: { fontWeight: 500, letterSpacing: '-0.02em' } },
    { id: 'sf-pro', label: 'SF Pro', icon: 'Aa', desc: 'Системный Apple', style: { fontWeight: 500, letterSpacing: '-0.01em' } },
    { id: 'helvetica', label: 'Helvetica', icon: 'Aa', desc: 'Классическая гарнитура', style: { fontFamily: 'Helvetica, Arial, sans-serif', fontWeight: 600 } },
    { id: 'georgia', label: 'Georgia', icon: 'Aa', desc: 'Элегантный сериф', style: { fontFamily: 'Georgia, serif', fontWeight: 700, letterSpacing: '0.02em' } },
    { id: 'playfair', label: 'Playfair', icon: 'Aa', desc: 'Высокий контраст', style: { fontFamily: '"Playfair Display", Georgia, serif', fontWeight: 700, fontStyle: 'italic' } },
    { id: 'courier', label: 'Courier', icon: 'Aa', desc: 'Моноширинный терминал', style: { fontFamily: '"Courier New", monospace', fontWeight: 600, letterSpacing: '0.05em' } },
    { id: 'system-ui', label: 'System UI', icon: 'Aa', desc: 'Нативная система', style: { fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif', fontWeight: 500 } },
    { id: 'rounded', label: 'Rounded', icon: 'Aa', desc: 'Мягкие скругления', style: { fontFamily: '"Nunito", "Rounded Mplus 1c", sans-serif', fontWeight: 700 } },
    { id: 'avenir', label: 'Avenir', icon: 'Aa', desc: 'Геометричный гуманист', style: { fontFamily: '"Avenir", "Avenir Next", sans-serif', fontWeight: 500 } },
    { id: 'futura', label: 'Futura', icon: 'Aa', desc: 'Конструктив 20-х', style: { fontFamily: '"Futura", "Trebuchet MS", sans-serif', fontWeight: 500, letterSpacing: '0.03em' } },
    { id: 'gill-sans', label: 'Gill Sans', icon: 'Aa', desc: 'Британский классик', style: { fontFamily: '"Gill Sans", "Gill Sans MT", sans-serif', fontWeight: 400 } },
    { id: 'din-pro', label: 'Din Pro', icon: 'Aa', desc: 'Технический гротеск', style: { fontFamily: '"DIN Pro", "DIN Alternate", sans-serif', fontWeight: 500, letterSpacing: '0.02em' } },
    { id: 'acumin', label: 'Acumin', icon: 'Aa', desc: 'Универсальный sans', style: { fontFamily: '"Acumin Pro", "Acumin", sans-serif', fontWeight: 500 } },
    { id: 'proxima', label: 'Proxima', icon: 'Aa', desc: 'Современный гротеск', style: { fontFamily: '"Proxima Nova", "Proxima", sans-serif', fontWeight: 600, letterSpacing: '-0.01em' } },
    { id: 'charter', label: 'Charter', icon: 'Aa', desc: 'Тёплый сериф', style: { fontFamily: '"Charter", "Georgia", serif', fontWeight: 600 } },
    { id: 'montserrat-thin', label: 'Montserrat Thin', icon: 'Aa', desc: 'Тонкий, воздушный', style: { fontWeight: 200, letterSpacing: '0.05em' } },
    { id: 'montserrat-black', label: 'Montserrat Black', icon: 'Aa', desc: 'Жирный, мощный', style: { fontWeight: 900, letterSpacing: '-0.03em' } },
    { id: 'typewriter', label: 'Typewriter', icon: 'Aa', desc: 'Печатная машинка', style: { fontFamily: '"Special Elite", "Courier New", monospace', fontWeight: 400, letterSpacing: '0.08em' } },
    { id: 'thin-sans', label: 'Thin Sans', icon: 'Aa', desc: 'Максимально тонкий', style: { fontWeight: 100, letterSpacing: '0.1em' } },
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
          <Icon name="search" size="lg" className="ap-menu-icon" />
          <span>Поиск пользователя</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('topup')}>
          <Icon name="coin" size="lg" className="ap-menu-icon" />
          <span>Пополнение / Списание</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('givegift')}>
          <Icon name="gift" size="lg" className="ap-menu-icon" />
          <span>Выдача подарка</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('adminmgmt')}>
          <Icon name="admin" size="lg" className="ap-menu-icon" />
          <span>Управление админами</span>
        </button>
        <button className="ap-menu-btn" onClick={loadStats}>
          <Icon name="chart" size="lg" className="ap-menu-icon" />
          <span>Статистика</span>
        </button>
        <button className="ap-menu-btn" onClick={() => setView('settings')}>
          <Icon name="palette" size="lg" className="ap-menu-icon" />
          <span>Тема оформления</span>
        </button>
      </div>
    ),

    search: (
      <div className="ap-view">
        <button className="ap-back" onClick={() => setView('menu')}>← Назад</button>
        <h3 className="ap-view-title"><Icon name="search" size="md" /> Поиск пользователя</h3>
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
                  <span className="ap-sr-balance">{u.balance} <Icon name="star" size="sm" /></span>
                  {u.isBanned && <span className="ap-sr-banned"><Icon name="ban" size="sm" /></span>}
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
              <p><strong>Баланс:</strong> {userInfo.balance} <Icon name="star" size="sm" /></p>
              <p><strong>Бонус:</strong> {userInfo.bonusBalance} <Icon name="star" size="sm" /></p>
              <p><strong>Инвентарь:</strong> {userInfo.inventory?.length || 0} предметов</p>
              <p><strong>Бан:</strong> {userInfo.isBanned ? <><Icon name="ban" size="sm" /> Да</> : <><Icon name="check" size="sm" /> Нет</>}</p>
              <p><strong>Создан:</strong> {userInfo.creationDate || '—'}</p>
            </div>
            <div className="ap-user-actions">
              <button className="ap-btn ap-btn-danger" onClick={handleBan} disabled={loading}>
                <Icon name="ban" size="sm" /> {userInfo?.isBanned ? 'Забанен' : 'Забанить'}
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
        <h3 className="ap-view-title"><Icon name="coin" size="md" /> Пополнение / Списание</h3>
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
        <h3 className="ap-view-title"><Icon name="gift" size="md" /> Выдача подарка</h3>
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
        <h3 className="ap-view-title"><Icon name="admin" size="md" /> Управление админами</h3>
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
        <h3 className="ap-view-title"><Icon name="chart" size="md" /> Статистика</h3>
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
            <span className="ap-stat-label">Всего <Icon name="star" size="sm" /></span>
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
        <h3 className="ap-view-title"><Icon name="palette" size="md" /> Цветовая тема</h3>
        <p className="ap-hint">Выберите пресет оформления.</p>
        <div className="ap-theme-grid">
          {PRESETS.map(p => (
            <button
              key={p.id}
              className={`ap-theme-card ${currentTheme === p.id ? 'active' : ''}`}
              onClick={() => switchTheme(p.id)}
            >
              <span className="ap-theme-swatch" style={{ background: THEME_PALETTE[p.id].bg }}>
                <Icon name={p.icon} size="sm" />
              </span>
              <span className="ap-theme-label">{p.label}</span>
              <span className="ap-theme-desc">{p.desc}</span>
            </button>
          ))}
        </div>

        <div className="ap-section-divider" />

        <h3 className="ap-view-title"><Icon name="settings" size="md" /> Шрифт</h3>
        <p className="ap-hint">20 вариантов на любой вкус.</p>
        <div className="ap-font-grid">
          {FONTS.map(f => (
            <button
              key={f.id}
              className={`ap-font-card ${currentFont === f.id ? 'active' : ''}`}
              onClick={() => switchFont(f.id)}
            >
              <span className="ap-font-icon" style={f.style}>{f.icon}</span>
              <span className="ap-font-label">{f.label}</span>
              <span className="ap-font-desc">{f.desc}</span>
            </button>
          ))}
        </div>

        <div className="ap-section-divider" />

        <h3 className="ap-view-title"><Icon name="settings" size="md" /> Тонкая настройка</h3>
        <p className="ap-hint">Blur, прозрачность и скорость анимаций.</p>

        <div className="ap-slider-group">
          <div className="ap-slider-header">
            <label>Стекло (blur): {userBlur.toFixed(1)}x</label>
            <span className="ap-slider-range">0.5 — 2.0</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="2"
            step="0.1"
            value={userBlur}
            onChange={e => handleBlurChange(e.target.value)}
            className="ap-slider"
          />
          <div className="ap-slider-header">
            <label>Прозрачность: {userOpacity.toFixed(1)}x</label>
            <span className="ap-slider-range">0.3 — 2.0</span>
          </div>
          <input
            type="range"
            min="0.3"
            max="2"
            step="0.1"
            value={userOpacity}
            onChange={e => handleOpacityChange(e.target.value)}
            className="ap-slider"
          />
          <div className="ap-slider-header">
            <label>Скорость: {userSpeed.toFixed(1)}x</label>
            <span className="ap-slider-range">0.2 — 3.0</span>
          </div>
          <input
            type="range"
            min="0.2"
            max="3"
            step="0.1"
            value={userSpeed}
            onChange={e => handleSpeedChange(e.target.value)}
            className="ap-slider"
          />
        </div>

        <div className="ap-section-divider" />

        <h3 className="ap-view-title"><Icon name="bolt" size="md" /> Стиль интерфейса</h3>
        <p className="ap-hint">Общий стиль UI-элементов.</p>
        <div className="ap-theme-grid">
          {[
            { id: 'glass', label: 'Glassmorphism', icon: 'star', desc: 'Стекло, blur, свечения' },
            { id: 'minimal', label: 'Минимал', icon: 'home', desc: 'Тонкие границы, минимум эффектов' },
            { id: 'maximal', label: 'Максимализм', icon: 'bolt', desc: 'Неон, жирные обводки, ярко' },
          ].map(s => (
            <button
              key={s.id}
              className={`ap-theme-card ${uiStyle === s.id ? 'active' : ''}`}
              onClick={() => switchUiStyle(s.id)}
            >
              <span className="ap-theme-swatch" style={{ background: s.id === 'glass' ? '#6c5ce7' : s.id === 'minimal' ? '#ffffff' : 'linear-gradient(135deg, #6c5ce7, #a855f7, #3b82f6)' }}>
                <Icon name={s.icon} size="sm" />
              </span>
              <span className="ap-theme-label">{s.label}</span>
              <span className="ap-theme-desc">{s.desc}</span>
            </button>
          ))}
        </div>

        <div className="ap-section-divider" />

        <h3 className="ap-view-title"><Icon name="refresh" size="md" /> Анимации</h3>
        <p className="ap-hint">Режим анимаций интерфейса.</p>
        <div className="ap-theme-grid">
          {[
            { id: 'default', label: 'Стандарт', desc: 'Fade + slide' },
            { id: 'fade', label: 'Fade', desc: 'Только плавное появление' },
            { id: 'scale', label: 'Scale', desc: 'Масштабирование' },
            { id: 'none', label: 'Без анимаций', desc: 'Всё мгновенно' },
          ].map(a => (
            <button
              key={a.id}
              className={`ap-theme-card ${animMode === a.id ? 'active' : ''}`}
              onClick={() => switchAnimMode(a.id)}
            >
              <span className="ap-theme-label">{a.label}</span>
              <span className="ap-theme-desc">{a.desc}</span>
            </button>
          ))}
        </div>

        <div className="ap-section-divider" />

        <h3 className="ap-view-title"><Icon name="star" size="md" /> Иконки</h3>
        <p className="ap-hint">Настройка отображения иконок.</p>
        <div className="ap-toggle-group">
          <label className="ap-toggle-row" onClick={toggleIconBold}>
            <span>Жирные иконки (stroke 2.5px)</span>
            <span className={`ap-toggle-switch ${iconBold ? 'on' : ''}`} />
          </label>
          <label className="ap-toggle-row" onClick={toggleIconFill}>
            <span>Активные — заливка</span>
            <span className={`ap-toggle-switch ${iconFill ? 'on' : ''}`} />
          </label>
          <label className="ap-toggle-row" onClick={toggleIconGlow}>
            <span>Активные — свечение</span>
            <span className={`ap-toggle-switch ${iconGlow ? 'on' : ''}`} />
          </label>
        </div>
      </div>
    ),
  }

  return (
    <div className="ap-overlay">
      <div className="ap-sheet">
        <div className="ap-header">
          <div className="ap-header-content">
            <Icon name="admin" size="xl" className="ap-header-icon" />
            <h2 className="ap-header-title">Админ панель</h2>
          </div>
          <button className="ap-close-btn" onClick={onClose}><Icon name="close" size="lg" /></button>
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
