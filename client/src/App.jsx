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
import LapikSpin from './components/LapikSpin'
import Crash from './components/Crash'
import Profile from './components/Profile'
import TopUp from './components/TopUp'
import Tasks from './components/Tasks'
import TabBar from './components/TabBar'
import BannedScreen from './components/BannedScreen'
import Maintenance from './components/Maintenance'
import { BalanceProvider, useBalance } from './contexts/BalanceContext'
import { ErrorProvider } from './components/ErrorContext'
import ThemeDecorations from './components/ThemeDecorations'

function AppContent() {
  const { updateBalance } = useBalance()
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('home')
  const [isMobile, setIsMobile] = useState(false)
  const [isAndroid, setIsAndroid] = useState(false)
  const [currentPath, setCurrentPath] = useState(window.location.pathname)
  const [safeAreaTop, setSafeAreaTop] = useState(0)
  const [isBanned, setIsBanned] = useState(false)
  const [botUsername, setBotUsername] = useState('HelpShellBot')
  const [maintenanceMode, setMaintenanceMode] = useState(false)

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

    const savedTheme = localStorage.getItem('theme')
    if (savedTheme) {
      document.documentElement.setAttribute('data-theme', savedTheme)
    }
    const savedFont = localStorage.getItem('font')
    if (savedFont) {
      document.documentElement.setAttribute('data-font', savedFont)
    }
    const savedBlur = localStorage.getItem('userBlur')
    if (savedBlur) {
      document.documentElement.style.setProperty('--user-blur', savedBlur)
    }
    const savedOpacity = localStorage.getItem('userOpacity')
    if (savedOpacity) {
      document.documentElement.style.setProperty('--user-opacity', savedOpacity)
    }
    const savedSpeed = localStorage.getItem('userSpeed')
    if (savedSpeed) {
      document.documentElement.style.setProperty('--user-animate-speed', savedSpeed)
    }
    const savedAnimMode = localStorage.getItem('animMode')
    if (savedAnimMode && savedAnimMode !== 'default') {
      document.documentElement.setAttribute('data-animation', savedAnimMode)
    }
    const savedUiStyle = localStorage.getItem('uiStyle')
    if (savedUiStyle && savedUiStyle !== 'glass') {
      document.documentElement.setAttribute('data-ui', savedUiStyle)
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

    const apiUrl = import.meta.env.VITE_API_URL || ''

    // Один запрос validate - проверяет всё: валидность, бан, тех.работы, админ
    fetch(`${apiUrl}/api/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData })
    })
      .then(res => res.json())
      .then(data => {
        console.log('Validate response:', data)

        // Проверяем валидность
        if (!data.valid) {
          setError('Ошибка: данные не валидны')
          setLoading(false)
          return
        }

        // Проверяем тех.работы
        if (data.maintenance) {
          setMaintenanceMode(true)
          setLoading(false)
          return
        }

        // Проверяем бан
        if (data.isBanned) {
          setIsBanned(true)
          return // Оставляем лоадер, показываем BannedScreen
        }

        // Обновляем баланс и isAdmin
        updateBalance({
          balance: data.balance || 0,
          bonusBalance: data.bonusBalance || 0,
          isAdmin: data.isAdmin || false
        })

        // Все ок - показываем приложение
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

  // Показываем экран технических работ если режим включен
  if (maintenanceMode) {
    return <Maintenance />
  }

  // Если путь /spins - показываем SpinSelection без TabBar
  if (currentPath === '/spins') {
    return (
      <BalanceProvider>
        <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
          <ThemeDecorations />
          <SpinSelection onNavigateToTopUp={setActiveTab} />
        </div>
      </BalanceProvider>
    )
  }

  // Если путь /spins/free - показываем FreeSpin без TabBar
  if (currentPath === '/spins/free') {
    return (
      <BalanceProvider>
        <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
          <ThemeDecorations />
          <FreeSpin onNavigateToTopUp={setActiveTab} />
        </div>
      </BalanceProvider>
    )
  }

  // Если путь /spins/paid - показываем PaidSpin без TabBar
  if (currentPath === '/spins/paid' || currentPath.startsWith('/spins/promik')) {
    return (
      <BalanceProvider>
        <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
          <ThemeDecorations />
          <PaidSpin onNavigateToTopUp={setActiveTab} />
        </div>
      </BalanceProvider>
    )
  }

  // Если путь /spins/lapik - показываем LapikSpin без TabBar
  if (currentPath === '/spins/lapik') {
    return (
      <BalanceProvider>
        <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
          <ThemeDecorations />
          <LapikSpin onNavigateToTopUp={setActiveTab} />
        </div>
      </BalanceProvider>
    )
  }

  // Если путь /crash - показываем Crash без TabBar
  if (currentPath === '/crash') {
    return (
      <BalanceProvider>
        <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
          <ThemeDecorations />
          <Crash onNavigateToTopUp={setActiveTab} />
        </div>
      </BalanceProvider>
    )
  }

  // Если путь /spin - показываем Spin без TabBar
  if (currentPath === '/spin') {
    return (
      <div className={`app-container ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`} style={{ '--safe-area-top': `${safeAreaTop}px` }}>
        <ThemeDecorations />
        <Spin onNavigateToTopUp={setActiveTab} />
      </div>
    )
  }

  return (
    <div
      className={`app-container tab-${activeTab} ${isMobile ? 'platform-mobile' : 'platform-desktop'} ${isAndroid ? 'platform-android' : ''}`}
      style={{ '--safe-area-top': `${safeAreaTop}px` }}
    >
      <ThemeDecorations />
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

function App() {
  return (
    <ErrorProvider>
      <BalanceProvider>
        <AppContent />
      </BalanceProvider>
    </ErrorProvider>
  )
}

export default App
