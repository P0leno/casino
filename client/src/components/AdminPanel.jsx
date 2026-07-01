import { useState, useCallback } from 'react'
import './AdminPanel.css'
import Icon from './Icons'
import { haptic } from '../utils/haptic'

const tg = window.Telegram?.WebApp
const initData = tg?.initData
const apiUrl = import.meta.env.VITE_API_URL || ''

const TABS = [
  { id: 'users', label: 'Пользователи', icon: 'search' },
  { id: 'finance', label: 'Финансы', icon: 'coin' },
  { id: 'gifts', label: 'Подарки', icon: 'gift' },
  { id: 'cases', label: 'Кейсы', icon: 'gift' },
  { id: 'fights', label: 'Файты', icon: 'bolt' },
  { id: 'crash', label: 'Краш', icon: 'chart' },
  { id: 'admins', label: 'Админы', icon: 'admin' },
  { id: 'system', label: 'Система', icon: 'settings' },
]

function AdminPanel({ onClose }) {
  const [activeTab, setActiveTab] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [searchQuery, setSearchQuery] = useState('')
  const [searchUsers, setSearchUsers] = useState([])
  const [searchTyping, setSearchTyping] = useState(null)
  const [searchNoResults, setSearchNoResults] = useState(false)
  const [userInfo, setUserInfo] = useState(null)
  const [userInfoId, setUserInfoId] = useState(null)

  const [topUpUserId, setTopUpUserId] = useState('')
  const [topUpAmount, setTopUpAmount] = useState('')
  const [stats, setStats] = useState(null)

  const [giftUserId, setGiftUserId] = useState('')
  const [giftName, setGiftName] = useState('')

  const [adminMgmtId, setAdminMgmtId] = useState('')

  const [currentTheme, setCurrentTheme] = useState(() => localStorage.getItem('theme') || 'default')
  const [currentFont, setCurrentFont] = useState(() => localStorage.getItem('font') || 'montserrat')
  const [userBlur, setUserBlur] = useState(() => parseFloat(localStorage.getItem('userBlur')) || 1)
  const [userOpacity, setUserOpacity] = useState(() => parseFloat(localStorage.getItem('userOpacity')) || 1)
  const [userSpeed, setUserSpeed] = useState(() => parseFloat(localStorage.getItem('userSpeed')) || 1)
  const [iconFill, setIconFill] = useState(() => localStorage.getItem('iconFill') === 'true')
  const [iconGlow, setIconGlow] = useState(() => localStorage.getItem('iconGlow') === 'true')
  const [iconBold, setIconBold] = useState(() => localStorage.getItem('iconBold') !== 'false')
  const [animMode, setAnimMode] = useState(() => localStorage.getItem('animMode') || 'default')
  const [uiStyle, setUiStyle] = useState(() => localStorage.getItem('uiStyle') || 'glass')

  const updateCSSVar = (name, value) => document.documentElement.style.setProperty(name, value)

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

  const toggleIconFill = () => {
    const v = !iconFill; setIconFill(v); localStorage.setItem('iconFill', v)
  }
  const toggleIconGlow = () => {
    const v = !iconGlow; setIconGlow(v); localStorage.setItem('iconGlow', v)
  }
  const toggleIconBold = () => {
    const v = !iconBold; setIconBold(v); localStorage.setItem('iconBold', v)
  }

  const switchAnimMode = (mode) => {
    setAnimMode(mode)
    localStorage.setItem('animMode', mode)
    if (mode === 'default') document.documentElement.removeAttribute('data-animation')
    else document.documentElement.setAttribute('data-animation', mode)
  }

  const switchUiStyle = (style) => {
    setUiStyle(style)
    localStorage.setItem('uiStyle', style)
    if (style === 'glass') document.documentElement.removeAttribute('data-ui')
    else document.documentElement.setAttribute('data-ui', style)
  }

  const callApi = useCallback(async (endpoint, body) => {
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
  }, [])

  const doSearch = async (q) => {
    if (!q.trim()) { setSearchUsers([]); setSearchNoResults(false); return }
    const data = await callApi('/api/admin/search-users', { query: q.trim() })
    if (data) {
      setSearchUsers(data.users || [])
      setSearchNoResults(data.users && data.users.length === 0)
    }
  }

  const handleSearchInput = (e) => {
    const v = e.target.value
    setSearchQuery(v); setUserInfo(null); setUserInfoId(null); setSearchNoResults(false)
    if (searchTyping) clearTimeout(searchTyping)
    if (v.trim().length >= 1) setSearchTyping(setTimeout(() => doSearch(v), 350))
    else setSearchUsers([])
  }

  const handleSelectUser = async (u) => {
    setSearchQuery(u.username ? `@${u.username}` : String(u.id))
    setSearchUsers([]); setUserInfoId(u.id)
    const data = await callApi('/api/admin/user-info', { userId: u.id })
    if (data) setUserInfo(data.user)
  }

  const handleTopUp = async () => {
    if (!topUpUserId.trim() || !topUpAmount.trim()) return
    const data = await callApi('/api/admin/top-up', { userId: parseInt(topUpUserId), amount: parseInt(topUpAmount) })
    if (data) { alert(`✅ Пополнено на ${data.amount} ⭐. Баланс: ${data.newBalance} ⭐`); setTopUpAmount('') }
  }

  const handleGiveGift = async () => {
    if (!giftUserId.trim() || !giftName.trim()) return
    const data = await callApi('/api/admin/give-gift', { userId: parseInt(giftUserId), giftName: giftName.trim() })
    if (data) { alert(`✅ Подарок "${data.giftName}" выдан`); setGiftName('') }
  }

  const handleAddAdmin = async () => {
    if (!adminMgmtId.trim()) return
    const data = await callApi('/api/admin/add-admin', { adminId: parseInt(adminMgmtId) })
    if (data) { alert(`✅ Админ ${adminMgmtId} добавлен`); setAdminMgmtId('') }
  }

  const handleRemoveAdmin = async () => {
    if (!adminMgmtId.trim()) return
    const data = await callApi('/api/admin/remove-admin', { adminId: parseInt(adminMgmtId) })
    if (data) { alert(`✅ Админ ${adminMgmtId} удалён`); setAdminMgmtId('') }
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
    if (data) setStats(data)
  }

  const activeIndex = TABS.findIndex(t => t.id === activeTab)

  const THEME_PRESETS = [
    { id: 'default', label: 'Стандарт', icon: 'star', desc: 'Фиолетовый', color: '#6c5ce7' },
    { id: 'minimalism', label: 'Минимализм', icon: 'home', desc: 'Белый', color: '#ffffff' },
    { id: 'halloween', label: 'Хэллоуин', icon: 'fire', desc: 'Оранжевый', color: '#ff6b35' },
    { id: 'newyear', label: 'Новый год', icon: 'star', desc: 'Золотой', color: '#ffd700' },
    { id: 'easter', label: 'Пасха', icon: 'gift', desc: 'Розовый', color: '#f472b6' },
    { id: 'cny', label: 'Китайский НГ', icon: 'fire', desc: 'Красный', color: '#dc2626' },
    { id: 'maximalism', label: 'Макси', icon: 'bolt', desc: 'Неон', color: '#a855f7' },
    { id: 'valentine', label: 'Валентинки', icon: 'star', desc: 'Розовый', color: '#e11d48' },
  ]

  const FONTS = [
    { id: 'montserrat', label: 'Montserrat', icon: 'Aa', style: { fontWeight: 600 } },
    { id: 'inter', label: 'Inter', icon: 'Aa', style: { fontWeight: 500, letterSpacing: '-0.02em' } },
    { id: 'sf-pro', label: 'SF Pro', icon: 'Aa', style: { fontWeight: 500 } },
    { id: 'georgia', label: 'Georgia', icon: 'Aa', style: { fontFamily: 'Georgia, serif', fontWeight: 700 } },
    { id: 'playfair', label: 'Playfair', icon: 'Aa', style: { fontFamily: '"Playfair Display", serif', fontWeight: 700 } },
    { id: 'courier', label: 'Courier', icon: 'Aa', style: { fontFamily: '"Courier New", monospace', fontWeight: 600 } },
    { id: 'futura', label: 'Futura', icon: 'Aa', style: { fontFamily: '"Futura", sans-serif', fontWeight: 500 } },
    { id: 'rounded', label: 'Rounded', icon: 'Aa', style: { fontFamily: '"Nunito", sans-serif', fontWeight: 700 } },
  ]

  return (
    <div className="ap-overlay">
      <div className="ap-sheet">
        <div className="ap-header">
          <div className="ap-header-left">
            <div className="ap-header-icon-wrap">
              <Icon name="admin" size="md" />
            </div>
            <h2 className="ap-header-title">Админ панель</h2>
          </div>
          <button className="ap-close-btn" onClick={onClose}>
            <Icon name="close" size="lg" />
          </button>
        </div>

        <div className="ap-body">
          {error && <div className="ap-error">{error}</div>}

          {!activeTab && (
            <div className="ap-menu-list">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  className="ap-menu-item"
                  onClick={() => { haptic('light'); setActiveTab(tab.id) }}
                >
                  <Icon name={tab.icon} size="md" />
                  <span>{tab.label}</span>
                  <svg className="ap-menu-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              ))}
            </div>
          )}

          {activeTab && (
            <button className="ap-back-btn" onClick={() => setActiveTab(null)}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M10 12l-4-4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Назад</span>
            </button>
          )}

          {activeTab === 'users' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Поиск пользователя</h3>
                <div className="ap-search-box">
                  <div className="ap-search-field">
                    <Icon name="search" size="sm" className="ap-search-icon" />
                    <input
                      className="ap-input"
                      placeholder="ID или @username"
                      value={searchQuery}
                      onChange={handleSearchInput}
                      autoFocus
                    />
                    {loading && <span className="ap-field-spinner" />}
                  </div>
                  {searchUsers.length > 0 && (
                    <div className="ap-search-dropdown">
                      {searchUsers.map(u => (
                        <div key={u.id} className="ap-search-row-item" onClick={() => handleSelectUser(u)}>
                          <span className="ap-row-id">#{u.id}</span>
                          <span className="ap-row-name">@{u.username || '—'}</span>
                          <span className="ap-row-balance">{u.balance} <Icon name="star" size="sm" /></span>
                          {u.isBanned && <span className="ap-row-banned"><Icon name="ban" size="sm" /></span>}
                        </div>
                      ))}
                    </div>
                  )}
                  {searchNoResults && searchQuery.trim() && !searchUsers.length && (
                    <p className="ap-no-results">Пользователи не найдены</p>
                  )}
                </div>
              </div>

              {userInfo && (
                <div className="ap-card">
                  <div className="ap-card-header">
                    <div className="ap-card-avatar">
                      {userInfo.username ? userInfo.username[0].toUpperCase() : '?'}
                    </div>
                    <div className="ap-card-info">
                      <span className="ap-card-name">@{userInfo.username || '—'}</span>
                      <span className="ap-card-id">ID: {userInfo.id}</span>
                    </div>
                  </div>
                  <div className="ap-card-stats">
                    <div className="ap-card-stat">
                      <span className="ap-cs-value">{userInfo.balance}</span>
                      <span className="ap-cs-label">Баланс</span>
                    </div>
                    <div className="ap-card-stat">
                      <span className="ap-cs-value">{userInfo.bonusBalance}</span>
                      <span className="ap-cs-label">Бонус</span>
                    </div>
                    <div className="ap-card-stat">
                      <span className="ap-cs-value">{userInfo.inventory?.length || 0}</span>
                      <span className="ap-cs-label">Предметов</span>
                    </div>
                  </div>
                  <div className="ap-card-meta">
                    <span className={`ap-meta-badge ${userInfo.isBanned ? 'banned' : 'active'}`}>
                      {userInfo.isBanned ? 'Забанен' : 'Активен'}
                    </span>
                    <span className="ap-meta-date">{userInfo.creationDate || '—'}</span>
                  </div>
                  <div className="ap-card-actions">
                    <button className="ap-btn ap-btn-danger" onClick={handleBan} disabled={loading || !userInfoId}>
                      <Icon name="ban" size="sm" /> Забанить
                    </button>
                    <button className="ap-btn ap-btn-secondary" onClick={handleUnban} disabled={loading || !userInfo?.isBanned}>
                      Разбанить
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'finance' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Пополнение / Списание</h3>
                <div className="ap-input-group">
                  <label>ID пользователя</label>
                  <input className="ap-input" placeholder="12345" value={topUpUserId} onChange={e => setTopUpUserId(e.target.value)} />
                </div>
                <div className="ap-input-group">
                  <label>Сумма (отрицательная — списание)</label>
                  <input className="ap-input" type="number" placeholder="1000" value={topUpAmount} onChange={e => setTopUpAmount(e.target.value)} />
                </div>
                <button className="ap-btn ap-btn-primary" onClick={handleTopUp} disabled={loading}>
                  {loading ? <span className="ap-btn-spinner" /> : 'Выполнить'}
                </button>
              </div>

              <div className="ap-section-divider" />

              <div className="ap-section">
                <div className="ap-section-row">
                  <h3 className="ap-section-title">Статистика</h3>
                  {!stats && <button className="ap-btn ap-btn-ghost ap-btn-sm" onClick={loadStats} disabled={loading}>Загрузить</button>}
                </div>
                {stats && (
                  <div className="ap-stats-grid">
                    {[
                      { value: stats.users, label: 'Пользователей' },
                      { value: stats.banned, label: 'Забанено' },
                      { value: stats.totalBalance, label: 'Всего ⭐' },
                      { value: stats.cases, label: 'Кейсов' },
                      { value: stats.gifts, label: 'Подарков' },
                      { value: stats.admins, label: 'Админов' },
                    ].map((s, i) => (
                      <div key={i} className="ap-stat-item">
                        <span className="ap-stat-num">{s.value}</span>
                        <span className="ap-stat-desc">{s.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'gifts' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Выдача подарка</h3>
                <div className="ap-input-group">
                  <label>ID пользователя</label>
                  <input className="ap-input" placeholder="12345" value={giftUserId} onChange={e => setGiftUserId(e.target.value)} />
                </div>
                <div className="ap-input-group">
                  <label>Название подарка</label>
                  <input className="ap-input" placeholder="flowers" value={giftName} onChange={e => setGiftName(e.target.value)} />
                </div>
                <button className="ap-btn ap-btn-primary" onClick={handleGiveGift} disabled={loading}>
                  {loading ? <span className="ap-btn-spinner" /> : 'Выдать'}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'cases' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Управление кейсами</h3>
                <p className="ap-section-desc">Создание, редактирование и управление кейсами</p>
                <div className="ap-placeholder-info">
                  <Icon name="gift" size="lg" />
                  <span>Управление кейсами (шансы, наполнение) — будет здесь</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'fights' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Файты / Соревнования</h3>
                <p className="ap-section-desc">Управление игровыми режимами PvP</p>
                <div className="ap-placeholder-info">
                  <Icon name="bolt" size="lg" />
                  <span>Управление файтами и турнирами — будет здесь</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'crash' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Краш-игра</h3>
                <p className="ap-section-desc">Настройки краш-раундов, мультипликаторы, комиссия</p>
                <div className="ap-placeholder-info">
                  <Icon name="chart" size="lg" />
                  <span>Управление краш-игрой — будет здесь</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'admins' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Управление админами</h3>
                <div className="ap-input-group">
                  <label>ID пользователя</label>
                  <input className="ap-input" placeholder="6252527489" value={adminMgmtId} onChange={e => setAdminMgmtId(e.target.value)} />
                </div>
                <div className="ap-btn-row">
                  <button className="ap-btn ap-btn-primary" onClick={handleAddAdmin} disabled={loading}>+ Добавить</button>
                  <button className="ap-btn ap-btn-danger" onClick={handleRemoveAdmin} disabled={loading}>— Удалить</button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'system' && (
            <div className="ap-tab-content">
              <div className="ap-section">
                <h3 className="ap-section-title">Цветовая тема</h3>
                <div className="ap-theme-grid">
                  {THEME_PRESETS.map(p => (
                    <button
                      key={p.id}
                      className={`ap-theme-chip ${currentTheme === p.id ? 'active' : ''}`}
                      onClick={() => switchTheme(p.id)}
                    >
                      <span className="ap-theme-dot" style={{ background: p.color }} />
                      <span className="ap-theme-name">{p.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="ap-section-divider" />

              <div className="ap-section">
                <h3 className="ap-section-title">Шрифт</h3>
                <div className="ap-font-grid">
                  {FONTS.map(f => (
                    <button
                      key={f.id}
                      className={`ap-font-chip ${currentFont === f.id ? 'active' : ''}`}
                      onClick={() => switchFont(f.id)}
                    >
                      <span className="ap-font-sample" style={f.style}>{f.icon}</span>
                      <span className="ap-font-name">{f.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="ap-section-divider" />

              <div className="ap-section">
                <h3 className="ap-section-title">Тонкая настройка</h3>
                <div className="ap-sliders">
                  <div className="ap-slider-group">
                    <div className="ap-slider-head">
                      <span>Стекло (blur)</span>
                      <span className="ap-slider-val">{userBlur.toFixed(1)}x</span>
                    </div>
                    <input type="range" min="0.5" max="2" step="0.1" value={userBlur} onChange={e => handleBlurChange(e.target.value)} className="ap-range" />
                  </div>
                  <div className="ap-slider-group">
                    <div className="ap-slider-head">
                      <span>Прозрачность</span>
                      <span className="ap-slider-val">{userOpacity.toFixed(1)}x</span>
                    </div>
                    <input type="range" min="0.3" max="2" step="0.1" value={userOpacity} onChange={e => handleOpacityChange(e.target.value)} className="ap-range" />
                  </div>
                  <div className="ap-slider-group">
                    <div className="ap-slider-head">
                      <span>Скорость</span>
                      <span className="ap-slider-val">{userSpeed.toFixed(1)}x</span>
                    </div>
                    <input type="range" min="0.2" max="3" step="0.1" value={userSpeed} onChange={e => handleSpeedChange(e.target.value)} className="ap-range" />
                  </div>
                </div>
              </div>

              <div className="ap-section-divider" />

              <div className="ap-section">
                <h3 className="ap-section-title">Стиль UI</h3>
                <div className="ap-style-grid">
                  {[
                    { id: 'glass', label: 'Glass', icon: 'star' },
                    { id: 'minimal', label: 'Минимал', icon: 'home' },
                    { id: 'maximal', label: 'Макси', icon: 'bolt' },
                  ].map(s => (
                    <button
                      key={s.id}
                      className={`ap-style-chip ${uiStyle === s.id ? 'active' : ''}`}
                      onClick={() => switchUiStyle(s.id)}
                    >
                      <Icon name={s.icon} size="sm" />
                      <span>{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="ap-section-divider" />

              <div className="ap-section">
                <h3 className="ap-section-title">Анимации</h3>
                <div className="ap-style-grid">
                  {[
                    { id: 'default', label: 'Стандарт' },
                    { id: 'fade', label: 'Fade' },
                    { id: 'scale', label: 'Scale' },
                    { id: 'none', label: 'Без аним.' },
                  ].map(a => (
                    <button
                      key={a.id}
                      className={`ap-style-chip ${animMode === a.id ? 'active' : ''}`}
                      onClick={() => switchAnimMode(a.id)}
                    >
                      <span>{a.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="ap-section-divider" />

              <div className="ap-section">
                <h3 className="ap-section-title">Иконки</h3>
                <div className="ap-toggles">
                  <label className="ap-toggle" onClick={toggleIconBold}>
                    <span>Жирные (stroke 2.5px)</span>
                    <span className={`ap-toggle-track ${iconBold ? 'on' : ''}`} />
                  </label>
                  <label className="ap-toggle" onClick={toggleIconFill}>
                    <span>Активные — заливка</span>
                    <span className={`ap-toggle-track ${iconFill ? 'on' : ''}`} />
                  </label>
                  <label className="ap-toggle" onClick={toggleIconGlow}>
                    <span>Активные — свечение</span>
                    <span className={`ap-toggle-track ${iconGlow ? 'on' : ''}`} />
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AdminPanel
