import './TabBar.css'
import { useEffect, useState, useRef } from 'react'
import shopIcon from '../assets/shop.svg'
import inventoryIcon from '../assets/inventory.svg'
import homeIcon from '../assets/home.svg'
import tasksIcon from '../assets/tasks.svg'

function TabBar({ activeTab, onTabChange }) {
  const [user, setUser] = useState(null)
  const [indicatorStyle, setIndicatorStyle] = useState({})
  const tabsRef = useRef([])
  const barRef = useRef(null)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
      setUser(tg.initDataUnsafe.user)
    }
  }, [])

  useEffect(() => {
    // Обновляем позицию индикатора при смене активной вкладки
    const activeIndex = tabs.findIndex(tab => tab.id === activeTab)
    if (activeIndex !== -1 && tabsRef.current[activeIndex] && activeTab !== 'profile') {
      const button = tabsRef.current[activeIndex]
      const left = button.offsetLeft
      const width = button.offsetWidth
      
      setIndicatorStyle({
        left: `${left}px`,
        width: `${width}px`
      })
    } else if (activeTab === 'profile') {
      // Скрываем индикатор когда открыт профиль
      setIndicatorStyle({
        opacity: 0
      })
    }
  }, [activeTab])

  const tabs = [
    { id: 'shop', label: 'Магазин', icon: shopIcon },
    { id: 'home', label: 'Главная', icon: homeIcon },
    { id: 'tasks', label: 'Задания', icon: tasksIcon }
  ]

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
    <>
      <div className="tab-bar" ref={barRef}>
        <div className="tab-indicator" style={indicatorStyle}></div>
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            ref={el => tabsRef.current[index] = el}
            className={`tab-button ${activeTab === tab.id && activeTab !== 'profile' ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <img src={tab.icon} alt={tab.label} className="tab-icon" />
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>
      
      <button 
        className={`profile-avatar-button ${activeTab === 'profile' ? 'active' : ''}`}
        onClick={() => onTabChange('profile')}
      >
        {getAvatarUrl() ? (
          <img src={getAvatarUrl()} alt="Avatar" className="avatar-img" />
        ) : (
          <div className="avatar-placeholder">
            {getInitials()}
          </div>
        )}
      </button>
    </>
  )
}

export default TabBar
