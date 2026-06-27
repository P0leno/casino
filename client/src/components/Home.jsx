import './Home.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import LottieAnimation from './LottieAnimation'
import crashAnim from '../assets/crash.json'
import spinsAnim from '../assets/spins.json'

function Home({ onNavigateToTopUp }) {
  const isMobile = window.Telegram?.WebApp?.platform === 'android' || 
                   window.Telegram?.WebApp?.platform === 'ios'
  
  const tg = window.Telegram?.WebApp
  const safeAreaTop = tg?.safeAreaInset?.top || tg?.contentSafeAreaInset?.top || 0
  // Отступ = safe area + 20px (отступ баланс баров) + 36px (высота баланс бара с padding) + 10px (gap)
  const contentPadding = isMobile ? (safeAreaTop + 66) : 50

  const handleNavigateToCrash = () => {
    window.history.pushState({}, '', '/crash')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const handleNavigateToFreeSpin = () => {
    window.history.pushState({}, '', '/spins/free')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const handleNavigateToSpins = () => {
    window.history.pushState({}, '', '/spins')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return (
    <div className="home-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="home-content" style={{ paddingTop: `${contentPadding}px` }}>
        <div className="welcome-card glass">
          <h2>Добро пожаловать!</h2>
          <p>Это главная страница приложения</p>
        </div>

        <div className="crash-dynamic-banner glass gradient glass-hover" onClick={handleNavigateToCrash}>
          <div className="crash-banner-line"></div>
          <div className="crash-banner-content">
            <div className="crash-banner-text">
              <h2 className="crash-banner-title">Краш</h2>
              <p className="crash-banner-subtitle">Следи за ракетой!</p>
            </div>
          </div>
          <div className="crash-banner-rocket">
            <LottieAnimation 
              animationData={crashAnim} 
              width={60} 
              height={60}
              rotation={2}
            />
          </div>
        </div>

        <div className="crash-dynamic-banner spins-banner glass-hover" onClick={handleNavigateToSpins}>
          <div className="crash-banner-line"></div>
          <div className="crash-banner-content">
            <div className="crash-banner-text">
              <h2 className="crash-banner-title">Спины</h2>
              <p className="crash-banner-subtitle">Крути и выигрывай!</p>
            </div>
          </div>
          <div className="crash-banner-rocket">
            <LottieAnimation 
              animationData={spinsAnim} 
              width={60} 
              height={60}
              rotation={2}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
