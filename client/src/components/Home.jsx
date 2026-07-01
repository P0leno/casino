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

  const handleNavigateToPromo = () => {
    window.history.pushState({}, '', '/spins/promik')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return (
    <div className="home-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="home-content" style={{ paddingTop: `${contentPadding}px` }}>

        {/* 777 Promo Banner */}
        <div className="banner-777 glass-liquid glass-hover" onClick={handleNavigateToPromo}>
          <div className="banner-777-glow" />
          <div className="banner-777-content">
            <span className="banner-777-title">777</span>
            <span className="banner-777-sub">Крути слот и выигрывай!</span>
          </div>
          <div className="banner-777-sparkles" />
        </div>

        {/* Games List */}
        <div className="home-games-list">
          <div className="home-game-row glass-hover" onClick={handleNavigateToCrash}>
            <div className="home-game-icon">
              <LottieAnimation animationData={crashAnim} width={40} height={40} rotation={2} />
            </div>
            <div className="home-game-info">
              <span className="home-game-name">Краш</span>
              <span className="home-game-desc">Следи за ракетой!</span>
            </div>
            <svg className="home-game-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          <div className="home-game-row glass-hover" onClick={handleNavigateToSpins}>
            <div className="home-game-icon">
              <LottieAnimation animationData={spinsAnim} width={40} height={40} rotation={2} />
            </div>
            <div className="home-game-info">
              <span className="home-game-name">Кейсы</span>
              <span className="home-game-desc">Выбирай и открывай!</span>
            </div>
            <svg className="home-game-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          <div className="home-game-row glass-hover" onClick={handleNavigateToFreeSpin}>
            <div className="home-game-icon home-game-icon-gold">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="#FFD700"/>
              </svg>
            </div>
            <div className="home-game-info">
              <span className="home-game-name">Бесплатный спин</span>
              <span className="home-game-desc">Крути бесплатно каждый день!</span>
            </div>
            <svg className="home-game-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
