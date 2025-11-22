import { useState, useEffect } from 'react'
import './App.css'
import LottieAnimation from './components/LottieAnimation'
import pawAnim from './assets/paw.json'
import Home from './components/Home'
import Shop from './components/Shop'
import Inventory from './components/Inventory'
import SpinVirtual from './components/SpinVirtual'
import Spin from './components/Spin'
import SpinSelection from './components/SpinSelection'
import FreeSpin from './components/FreeSpin'
import PaidSpin from './components/PaidSpin'
import Crash from './components/Crash'
import Profile from './components/Profile'
import TopUp from './components/TopUp'
import Tasks from './components/Tasks'
import TabBar from './components/TabBar'
import BannedScreen from './components/BannedScreen'

function App() {
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('home')
  const [isMobile, setIsMobile] = useState(false)
  const [isAndroid, setIsAndroid] = useState(false)
  const [currentPath, setCurrentPath] = useState(window.location.pathname)
  const [safeAreaTop, setSafeAreaTop] = useState(0)
  const [isBanned, setIsBanned] = useState(false)
  const [botUsername, setBotUsername] = useState('HelpShellBot')

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
    tg.setHeaderColor('#1a1a1a')
    tg.setBackgroundColor('#1a1a1a')

    if (tg.platform === 'android' || tg.platform === 'ios') {
      tg.requestFullscreen()
      setIsMobile(true)
      if (tg.platform === 'android') {
        setIsAndroid(true)
      }
      
      // Получаем safe area и добавляем 20px для баланс баров на мобиле
      const topInset = tg.safeAreaInset?.top || tg.contentSafeAreaInset?.top || 0
      setSafeAreaTop(topInset + 20)
    } else {
      setIsMobile(false)
      setIsAndroid(false)
      setSafeAreaTop(5) // На ПК просто 5px
    }

    const initData = tg.initData

    if (!initData) {
      // Нет initData - оставляем бесконечный лоадер
      return
    }

    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
    
    // Сначала проверяем бан
    fetch(`${apiUrl}/api/check-ban`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData })
    })
      .then(res => res.json())
      .then(data => {
        if (data.banned) {
          setIsBanned(true)
          setBotUsername(data.botUsername || 'HelpShellBot')
          // НЕ делаем setLoading(false) - оставляем лоадер
          return null // Прерываем цепочку
        }
        
        // Если не забанен - проверяем валидность
        return fetch(`${apiUrl}/api/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData })
        })
      })
      .then(res => {
        // Если res === null, значит пользователь забанен
        if (res === null) return null
        
        console.log('Validate response status:', res.status)
        return res.json()
      })
      .then(data => {
        // Если data === null, значит пользователь забанен
        if (data === null) return
        
        console.log('Validate response data:', data)
        
        // Проверяем валидность
        if (!data.valid) {
          console.log('Invalid initData')
          setError('Ошибка: данные не валидны')
          setLoading(false)
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
      <>
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
        {isBanned && <BannedScreen botUsername={botUsername} />}
      </>
    )
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">{error}</div>
      </div>
    )
  }

  // Если путь /spins - показываем SpinSelection без TabBar
  if (currentPath === '/spins') {
    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
        <SpinSelection onNavigateToTopUp={setActiveTab} />
      </div>
    )
  }

  // Если путь /spins/free - показываем FreeSpin без TabBar
  if (currentPath === '/spins/free') {
    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
        <FreeSpin onNavigateToTopUp={setActiveTab} />
      </div>
    )
  }

  // Если путь /spins/paid - показываем PaidSpin без TabBar
  if (currentPath === '/spins/paid') {
    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
        <PaidSpin onNavigateToTopUp={setActiveTab} />
      </div>
    )
  }

  // Если путь /crash - показываем Crash без TabBar
  if (currentPath === '/crash') {
    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
        <Crash onNavigateToTopUp={setActiveTab} />
      </div>
    )
  }

  // Если путь /spin - показываем Spin без TabBar
  if (currentPath === '/spin') {
    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
        <Spin onNavigateToTopUp={setActiveTab} />
      </div>
    )
  }

  return (
    <div 
      className={`app-container tab-${activeTab} ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`}
      style={{ '--safe-area-top': `${safeAreaTop}px` }}
    >
      {activeTab === 'home' && <Home onNavigateToTopUp={setActiveTab} />}
      {activeTab === 'shop' && <Shop onNavigateToTopUp={setActiveTab} />}
      {activeTab === 'inventory' && <Inventory onNavigateToTopUp={setActiveTab} />}
      {activeTab === 'tasks' && <Tasks onNavigateToTopUp={setActiveTab} />}
      {activeTab === 'profile' && <Profile />}
      {activeTab === 'topup' && <TopUp onNavigateBack={setActiveTab} />}
      {activeTab !== 'topup' && <TabBar activeTab={activeTab} onTabChange={setActiveTab} />}
    </div>
  )
}

export default App
