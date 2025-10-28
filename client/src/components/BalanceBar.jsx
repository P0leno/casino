import { useState, useEffect } from 'react'
import './BalanceBar.css'
import LottieAnimation from './LottieAnimation'
import starAnimation from '../assets/star.json'

function BalanceBar({ onNavigateToTopUp }) {
  const [balance, setBalance] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBalance()
    // Обновляем баланс каждые 5 секунд
    const interval = setInterval(loadBalance, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadBalance = async () => {
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
        setBalance(data.balance || 0)
      }
    } catch (error) {
      console.error('Error loading balance:', error)
    } finally {
      setLoading(false)
    }
  }

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
        <span className="balance-value">{loading ? '...' : balance}</span>
        <div className="balance-icon">
          <LottieAnimation animationData={starAnimation} width={20} height={20} />
        </div>
      </div>
    </div>
  )
}

export default BalanceBar
