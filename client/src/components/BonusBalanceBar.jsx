import { useState, useEffect } from 'react'
import './BonusBalanceBar.css'
import LottieAnimation from './LottieAnimation'
import pawAnimation from '../assets/paw.json'

function BonusBalanceBar() {
  const [bonusBalance, setBonusBalance] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBonusBalance()
    const interval = setInterval(loadBonusBalance, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadBonusBalance = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) {
        setLoading(false)
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/get-balance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid) {
        setBonusBalance(data.bonusBalance || 0)
      }
    } catch (error) {
      console.error('Error loading bonus balance:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bonus-balance-bar">
      <div className="bonus-balance-content">
        <span className="bonus-balance-value">{loading ? '...' : bonusBalance}</span>
        <div className="bonus-balance-icon">
          <LottieAnimation animationData={pawAnimation} width={20} height={20} />
        </div>
      </div>
    </div>
  )
}

export default BonusBalanceBar
