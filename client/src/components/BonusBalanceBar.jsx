import './BonusBalanceBar.css'
import LottieAnimation from './LottieAnimation'
import pawAnimation from '../assets/paw.json'
import { useBalance } from '../contexts/BalanceContext'

function BonusBalanceBar() {
  const { paws, bonusBalance } = useBalance()
  // Поддержка обоих названий для совместимости
  const displayBalance = paws || bonusBalance
  
  return (
    <div className="bonus-balance-bar">
      <div className="bonus-balance-content">
        <span className="bonus-balance-value">{displayBalance}</span>
        <div className="bonus-balance-icon">
          <LottieAnimation animationData={pawAnimation} width={20} height={20} />
        </div>
      </div>
    </div>
  )
}

export default BonusBalanceBar
