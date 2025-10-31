import './Home.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import LottieAnimation from './LottieAnimation'
import crashAnim from '../assets/crash.json'

function Home({ onNavigateToTopUp }) {
  const handleNavigateToCrash = () => {
    window.history.pushState({}, '', '/crash')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const handleNavigateToFreeSpin = () => {
    window.history.pushState({}, '', '/spins/free')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return (
    <div className="home-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="home-content">
        <div className="welcome-card">
          <h2>Добро пожаловать! 👋</h2>
          <p>Это главная страница приложения</p>
        </div>

        <div className="crash-dynamic-banner" onClick={handleNavigateToCrash}>
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
      </div>
    </div>
  )
}

export default Home
