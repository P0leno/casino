import './BalanceBar.css'
import Icon from './Icons'
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
    <div className="balance-bar glass-sm" onClick={handleBalanceClick}>
      <div className="balance-content">
        <span className="balance-value">{balance}</span>
        <Icon name="star" size="md" className="balance-star-icon" />
      </div>
    </div>
  )
}

export default BalanceBar
