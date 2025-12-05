import { useState, useEffect } from 'react'
import './Spin.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import freeSpinBanner from '../assets/freespin.svg'
import bazminBanner from '../assets/bazmin.svg'

function SpinVirtual({ onNavigateToTopUp }) {
  const handleFreeSpin = () => {
    window.history.pushState({}, '', '/spins/free')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const handlePaidSpin = () => {
    window.history.pushState({}, '', '/spins/paid')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return (
    <div className="spin-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="spin-banner-container">
        <div className="spin-banners-grid">
          <img 
            src={freeSpinBanner} 
            alt="Free Spin" 
            className="spin-banner"
            onClick={handleFreeSpin}
          />
          <img 
            src={bazminBanner} 
            alt="Бомж Кейс" 
            className="spin-banner"
            onClick={handlePaidSpin}
          />
        </div>
      </div>
    </div>
  )
}

export default SpinVirtual
