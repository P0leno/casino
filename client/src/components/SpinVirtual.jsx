import { useState, useEffect } from 'react'
import './Spin.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import freeSpinBanner from '../assets/freespin.svg'

function SpinVirtual({ onNavigateToTopUp }) {
  const handleFreeSpin = () => {
    window.history.pushState({}, '', '/spins/free')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return (
    <div className="spin-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="spin-banner-container">
        <img 
          src={freeSpinBanner} 
          alt="Free Spin" 
          className="spin-banner"
          onClick={handleFreeSpin}
        />
      </div>
    </div>
  )
}

export default SpinVirtual
