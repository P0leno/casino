import { useState, useEffect } from 'react'
import './App.css'
import Home from './components/Home'
import Inventory from './components/Inventory'
import SpinVirtual from './components/SpinVirtual'
import FreeSpin from './components/FreeSpin'
import Crash from './components/Crash'
import Profile from './components/Profile'
import TopUp from './components/TopUp'
import TabBar from './components/TabBar'

function App() {
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('home')
  const [isMobile, setIsMobile] = useState(false)
  const [currentPath, setCurrentPath] = useState(window.location.pathname)

  useEffect(() => {
    localStorage.setItem('currentTab', activeTab)
  }, [activeTab])

  useEffect(() => {
    // Отслеживание изменений URL
    const handlePopState = () => {
      const path = window.location.pathname
      setCurrentPath(path)
      
      // Если вернулись на главную страницу - скрываем BackButton
      if (path === '/' || path === '') {
        const tg = window.Telegram?.WebApp
        if (tg) {
          tg.BackButton.hide()
        }
      }
    }
    
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  useEffect(() => {
    const tg = window.Telegram?.WebApp

    if (!tg) {
      setError('Telegram Web App SDK не загружен')
      setLoading(false)
      return
    }

    tg.ready()
    tg.headerColor = '#000000'

    if (tg.platform === 'android' || tg.platform === 'ios') {
      tg.requestFullscreen()
      setIsMobile(true)
    } else {
      setIsMobile(false)
    }

    const initData = tg.initData

    if (!initData) {
      // Нет initData - оставляем бесконечный лоадер
      return
    }

    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
    
    fetch(`${apiUrl}/api/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData })
    })
      .then(res => {
        console.log('Validate response status:', res.status)
        return res.json()
      })
      .then(data => {
        console.log('Validate response data:', data)
        
        // Проверяем валидность
        if (!data.valid) {
          console.log('Invalid initData')
          setError('Ошибка: данные не валидны')
          setLoading(false)
          return
        }
        
        // Проверяем бан - оставляем бесконечный лоадер
        if (data.isBanned === true) {
          console.log('User is banned, showing infinite loader')
          // НЕ вызываем setLoading(false) - остается лоадер навсегда
          return
        }
        
        // Все ок - убираем лоадер и показываем приложение
        console.log('User validated successfully, showing app')
        setLoading(false)
      })
      .catch(err => {
        console.error('Validation error:', err)
        setError('Ошибка соединения с сервером: ' + err.message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="loader-container">
        <div className="loader-wrapper">
          <div className="preloader">
            <div className="crack"></div>
            <div className="crack crack2"></div>
            <div className="crack crack3"></div>
            <div className="crack crack4"></div>
            <div className="crack crack5"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">{error}</div>
      </div>
    )
  }

  // Если путь /spins/free - показываем FreeSpin без TabBar
  if (currentPath === '/spins/free') {
    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'}`}>
        <FreeSpin onNavigateToTopUp={setActiveTab} />
      </div>
    )
  }

  // Если путь /crash - показываем Crash с TabBar
  if (currentPath === '/crash') {
    const handleTabChangeFromCrash = (tab) => {
      // Возвращаемся на главную страницу
      window.history.back()
      setCurrentPath('/')
      setActiveTab(tab)
    }

    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'}`}>
        <Crash onNavigateToTopUp={setActiveTab} />
        <TabBar activeTab="home" onTabChange={handleTabChangeFromCrash} />
      </div>
    )
  }

  return (
    <div className={`app-container tab-${activeTab} ${isMobile ? 'platform-mobile' : 'platform-desktop'}`}>
      {activeTab === 'home' && <Home onNavigateToTopUp={setActiveTab} />}
      {activeTab === 'inventory' && <Inventory onNavigateToTopUp={setActiveTab} />}
      {activeTab === 'spin' && <SpinVirtual onNavigateToTopUp={setActiveTab} />}
      {activeTab === 'profile' && <Profile />}
      {activeTab === 'topup' && <TopUp onNavigateBack={setActiveTab} />}
      {activeTab !== 'topup' && <TabBar activeTab={activeTab} onTabChange={setActiveTab} />}
    </div>
  )
}

export default App
