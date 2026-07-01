import './TabBar.css'
import { useEffect, useState, useRef } from 'react'
import Icon from './Icons'

function TabBar({ activeTab, onTabChange }) {
  const [user, setUser] = useState(null)
  const [indicatorStyle, setIndicatorStyle] = useState({})
  const [bounce, setBounce] = useState(false)
  const tabsRef = useRef([])
  const bounceTimer = useRef(null)

  const iconFill = localStorage.getItem('iconFill') === 'true'
  const iconGlow = localStorage.getItem('iconGlow') === 'true'
  const iconBold = localStorage.getItem('iconBold') !== 'false'

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
      setUser(tg.initDataUnsafe.user)
    }
  }, [])

  useEffect(() => {
    const activeIndex = tabs.findIndex(tab => tab.id === activeTab)
    if (activeIndex !== -1 && tabsRef.current[activeIndex] && activeTab !== 'profile') {
      const button = tabsRef.current[activeIndex]
      const left = button.offsetLeft
      const width = button.offsetWidth
      setIndicatorStyle({ left: `${left}px`, width: `${width}px` })
      setBounce(true)
      clearTimeout(bounceTimer.current)
      bounceTimer.current = setTimeout(() => setBounce(false), 600)
    } else if (activeTab === 'profile') {
      setIndicatorStyle({ opacity: 0 })
    }
    return () => clearTimeout(bounceTimer.current)
  }, [activeTab])

  const tabs = [
    { id: 'shop', label: 'Магазин', icon: 'shop' },
    { id: 'home', label: 'Главная', icon: 'home' },
    { id: 'tasks', label: 'Задания', icon: 'tasks' },
  ]

  const getAvatarUrl = () => user?.photo_url || null

  const getInitials = () => {
    if (!user) return '?'
    const first = user.first_name?.[0] || ''
    const last = user.last_name?.[0] || ''
    return (first + last).toUpperCase() || '?'
  }

  return (
    <>
      <div className="tab-bar glass-strong">
        <div className={`tab-indicator${bounce ? ' bounce' : ''}`} style={indicatorStyle} />
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            ref={el => tabsRef.current[index] = el}
            className={`tab-button ${activeTab === tab.id && activeTab !== 'profile' ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <Icon name={tab.icon} size="md" className={`tab-icon ${activeTab === tab.id ? 'active-tab' : ''}`} fill={iconFill && activeTab === tab.id} glow={iconGlow && activeTab === tab.id} bold={iconBold} />
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>

      <button
        className={`profile-avatar-button glass ${activeTab === 'profile' ? 'active' : ''}`}
        onClick={() => onTabChange('profile')}
      >
        {getAvatarUrl() ? (
          <img src={getAvatarUrl()} alt="" className="avatar-img" />
        ) : (
          <div className="avatar-placeholder">{getInitials()}</div>
        )}
      </button>
    </>
  )
}

export default TabBar
