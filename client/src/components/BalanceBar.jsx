import './BalanceBar.css'
import LottieAnimation from './LottieAnimation'
import starAnimation from '../assets/star.json'
import { useBalance } from '../contexts/BalanceContext'

function BalanceBar({ onNavigateToTopUp }) {
  const { balance } = useBalance()
  const handleBalanceClick = () => {
    const tg = window.Telegram?.WebApp
    const currentTab = localStorage.getItem('currentTab') || 'home'
    localStorage.setItem('previousTab', currentTab)
    if (onNavigateToTopUp) {
      onNavigateToTopUp('topup')
    }
  }

  return (
    <div className="balance-bar" onClick={handleBalanceClick}>
      <div className="balance-content">
        <span className="balance-value">{balance}</span>
        <div className="balance-icon">
          <LottieAnimation animationData={starAnimation} width={20} height={20} />
        </div>
      </div>
    </div>
  )
}

export default BalanceBar
