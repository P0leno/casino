import { useState, useEffect } from 'react'
import './Inventory.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import giftAnimation from '../assets/gift.json'
import bearAnim from '../assets/bear.json'
import cakeAnim from '../assets/cake.json'
import cupAnim from '../assets/cup.json'
import diamondAnim from '../assets/diamond.json'
import flowersAnim from '../assets/flowers.json'
import heartAnim from '../assets/heart.json'
import ringAnim from '../assets/ring.json'
import rocketAnim from '../assets/rocket.json'
import roseAnim from '../assets/rose.json'

const giftAnimations = {
  bear: bearAnim,
  cake: cakeAnim,
  cup: cupAnim,
  diamond: diamondAnim,
  flowers: flowersAnim,
  gift: giftAnimation,
  heart: heartAnim,
  ring: ringAnim,
  rocket: rocketAnim,
  rose: roseAnim
}

function Inventory({ onNavigateToTopUp }) {
  const [showOverlay, setShowOverlay] = useState(false)
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [prices, setPrices] = useState({})

  useEffect(() => {
    loadInventory()
    loadPrices()
  }, [])

  const loadInventory = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) {
        setLoading(false)
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/get-inventory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid) {
        setInventory(data.inventory)
      }
    } catch (error) {
      console.error('Error loading inventory:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenBot = () => {
    window.open('https://t.me/shellrelayer', '_blank')
    setShowOverlay(false)
  }

  const loadPrices = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/get-prices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid) {
        setPrices(data.prices)
      }
    } catch (error) {
      console.error('Error loading prices:', error)
    }
  }

  const handleWithdraw = (giftName) => {
    alert('Функция вывода пока не реализована')
  }

  const handleSell = async (giftName, index) => {
    const price = prices[giftName] || 0
    const confirmed = confirm(`Продать ${giftName} за ${price} ⭐?`)
    
    if (!confirmed) return

    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'

      const response = await fetch(`${apiUrl}/api/sell-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, giftName, index })
      })

      const data = await response.json()
      if (data.success) {
        alert(`Продано! +${data.price} ⭐ к балансу`)
        loadInventory()
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    }
  }

  return (
    <div className="inventory-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="inventory-content">
        {loading ? (
          <div className="inventory-loading">Загрузка...</div>
        ) : inventory.length === 0 ? (
          <div className="inventory-grid">
            <div className="empty-inventory">
              <div className="empty-icon">
                <LottieAnimation animationData={giftAnimation} width={100} height={100} />
              </div>
              <p className="empty-text">Ваш инвентарь пуст</p>
            </div>
          </div>
        ) : (
          <div className="inventory-grid-filled">
            {inventory.map((giftName, index) => (
              <div key={`${giftName}-${index}`} className="gift-card">
                <div className="gift-card-animation">
                  {giftAnimations[giftName] && (
                    <LottieAnimation animationData={giftAnimations[giftName]} width={100} height={100} loop={false} autoplay={false} />
                  )}
                </div>
                <div className="gift-actions">
                  <button className="gift-withdraw-btn" onClick={() => handleWithdraw(giftName)}>
                    Вывести
                  </button>
                  <button className="gift-sell-btn" onClick={() => handleSell(giftName, index)}>
                    Продать
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="add-gifts-text" onClick={() => setShowOverlay(true)}>
        Добавить подарки
      </div>

      {showOverlay && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowOverlay(false)} />
          <div className="overlay-sheet">
            <div className="sheet-handle"></div>
            
            <div className="sheet-content">
              <div className="overlay-icon">
                <LottieAnimation animationData={giftAnimation} width={80} height={80} />
              </div>
              <h2 className="overlay-title">Добавить подарки</h2>
              <p className="overlay-text">
                Чтобы подарки появились в вашем инвентаре, отправьте их боту
              </p>

              <button className="overlay-button" onClick={handleOpenBot}>
                Отправить
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Inventory
