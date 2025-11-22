import { useEffect } from 'react'
import './SpinSelection.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import freeSpinBanner from '../assets/freespin.svg'
import paidSpinBanner from '../assets/paidspin.svg'

function SpinSelection({ onNavigateToTopUp }) {
  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.BackButton.show()
      
      const handleBack = () => {
        window.history.back()
      }
      
      tg.BackButton.onClick(handleBack)
      
      return () => {
        tg.BackButton.hide()
        tg.BackButton.offClick(handleBack)
      }
    }
  }, [])

  const handleNavigateToFreeSpin = () => {
    window.history.pushState({}, '', '/spins/free')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const handleNavigateToPaidSpin = () => {
    window.history.pushState({}, '', '/spins/paid')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return (
    <div className="home-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="home-content">
        <div className="spin-banner-item" onClick={handleNavigateToFreeSpin}>
          <img src={freeSpinBanner} alt="Free Spin" className="spin-banner-image" />
        </div>
        
        <div className="spin-banner-item" onClick={handleNavigateToPaidSpin}>
          <img src={paidSpinBanner} alt="Paid Spin" className="spin-banner-image" />
        </div>
      </div>
    </div>
  )
}

export default SpinSelection
