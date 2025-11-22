import { useState, useEffect, useRef } from 'react'
import './Inventory.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import GiftDetailsModal from './GiftDetailsModal'
import starStaticIcon from '../assets/star_static.svg'

function Inventory({ onNavigateToTopUp }) {
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedGift, setSelectedGift] = useState(null)
  const [showGiftDetails, setShowGiftDetails] = useState(false)
  const [sellingGift, setSellingGift] = useState(null)
  const gridRef = useRef(null)
  const observerRef = useRef(null)

  // Проверяем мобильную платформу и рассчитываем отступ
  const isMobile = window.Telegram?.WebApp?.platform === 'android' || 
                   window.Telegram?.WebApp?.platform === 'ios'
  
  const tg = window.Telegram?.WebApp
  const safeAreaTop = tg?.safeAreaInset?.top || tg?.contentSafeAreaInset?.top || 0
  // Отступ = safe area + 20px (отступ баланс баров) + 50px (высота баланс бара) + 20px (gap)
  const topPadding = isMobile ? (safeAreaTop + 90) : 50
  
  console.log('Inventory - safeAreaTop:', safeAreaTop, 'topPadding:', topPadding, 'isMobile:', isMobile)

  useEffect(() => {
    loadInventory()
  }, [])

  useEffect(() => {
    // Intersection Observer для оптимизации Lottie анимаций
    if (!gridRef.current) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const lottieElement = entry.target.querySelector('.lottie-container, .lottie-container-regular')
          if (lottieElement) {
            if (entry.isIntersecting) {
              lottieElement.classList.add('visible')
            } else {
              lottieElement.classList.remove('visible')
            }
          }
        })
      },
      { threshold: 0.1, rootMargin: '50px' }
    )

    const cards = gridRef.current.querySelectorAll('.gift-card-inventory, .gift-card-inventory-regular')
    cards.forEach((card) => observerRef.current.observe(card))

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [inventory])

  const loadInventory = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) {
        setLoading(false)
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/inventory/get`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.inventory) {
        setInventory(data.inventory)
      }
    } catch (error) {
      console.error('Error loading inventory:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleViewGift = (gift) => {
    setSelectedGift(gift)
    setShowGiftDetails(true)
  }

  // Вывод обычных подарков (через существующую механику)
  const handleWithdrawRegular = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
    
    // Подтверждение
    const confirmMessage = `Вывести ${gift.title} на ваш аккаунт Telegram?`
    const confirmed = tg?.showConfirm 
      ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
      : window.confirm(confirmMessage)
    
    if (!confirmed) return

    try {
      const response = await fetch(`${apiUrl}/api/withdraw-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, giftName: gift.slug, index: 0 })
      })

      const data = await response.json()
      
      if (data.success) {
        if (tg?.showAlert) {
          tg.showAlert('✅ Подарок успешно отправлен!')
        } else {
          alert('✅ Подарок успешно отправлен!')
        }
        loadInventory()
        setShowGiftDetails(false)
      } else {
        const errorMsg = data.message || 'Не удалось отправить подарок'
        if (tg?.showAlert) {
          tg.showAlert(errorMsg)
        } else {
          alert(errorMsg)
        }
      }
    } catch (error) {
      console.error('Withdraw error:', error)
      if (tg?.showAlert) {
        tg.showAlert('Ошибка соединения с сервером')
      } else {
        alert('Ошибка соединения с сервером')
      }
    }
  }

  // Продажа обычных подарков
  const handleSellRegular = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'

    try {
      // Для обычных подарков используем существующий API sell-gift
      const response = await fetch(`${apiUrl}/api/sell-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, giftName: gift.slug })
      })

      const data = await response.json()
      
      if (data.success) {
        if (tg?.showAlert) {
          tg.showAlert(`Продано! +${data.price} ⭐ к балансу`)
        } else {
          alert(`Продано! +${data.price} ⭐ к балансу`)
        }
        loadInventory()
        setShowGiftDetails(false)
      } else {
        const errorMsg = data.message || 'Ошибка продажи'
        if (tg?.showAlert) {
          tg.showAlert(errorMsg)
        } else {
          alert(errorMsg)
        }
      }
    } catch (error) {
      console.error('Sell error:', error)
      if (tg?.showAlert) {
        tg.showAlert('Ошибка соединения с сервером')
      } else {
        alert('Ошибка соединения с сервером')
      }
    }
  }

  // Продажа NFT подарков
  const handleSellNFT = async (gift) => {
    if (sellingGift) return
    
    setSellingGift(gift.slug)
    
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
    
    try {
      // Получаем цену продажи
      const priceResponse = await fetch(`${apiUrl}/api/inventory/get-sell-price`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug: gift.slug })
      })

      const priceData = await priceResponse.json()

      if (!priceResponse.ok) {
        throw new Error(priceData.detail || 'Не удалось определить цену')
      }

      // Диалоговое окно подтверждения
      const confirmMessage = `Продать "${gift.title}"?\n\nЦена на Tonnel: ${priceData.ton_price} TON\nКомиссия: ${priceData.commission_percent}%\nВы получите: ${priceData.stars_price}⭐`
      
      const confirmed = tg?.showConfirm 
        ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
        : window.confirm(confirmMessage)

      if (!confirmed) {
        setSellingGift(null)
        return
      }

      // Продаем подарок
      const sellResponse = await fetch(`${apiUrl}/api/inventory/sell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug: gift.slug })
      })

      const sellData = await sellResponse.json()

      if (!sellResponse.ok) {
        throw new Error(sellData.detail || 'Ошибка продажи')
      }

      if (tg?.showAlert) {
        tg.showAlert(`${sellData.message}\n+${sellData.stars_earned}⭐`)
      } else {
        alert(`${sellData.message}\n+${sellData.stars_earned}⭐`)
      }

      // Обновляем инвентарь
      loadInventory()
      setShowGiftDetails(false)

    } catch (error) {
      console.error('Sell error:', error)
      const errorMsg = error.message || 'Ошибка продажи'
      if (tg?.showAlert) {
        tg.showAlert(errorMsg)
      } else {
        alert(errorMsg)
      }
    } finally {
      setSellingGift(null)
    }
  }

  return (
    <div className="inventory-page">
      <BonusBalanceBar />
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />

      <div className="inventory-content" style={{ paddingTop: `${topPadding}px` }}>
        {loading ? (
          <div className="inventory-loading">Загрузка...</div>
        ) : inventory.length === 0 ? (
          <div className="empty-inventory-container">
            <div className="empty-icon">📦</div>
            <p className="empty-text">Ваш инвентарь пуст</p>
          </div>
        ) : (
          <div className="inventory-grid" ref={gridRef}>
            {inventory.map((gift, index) => (
              <div 
                key={`${gift.slug}-${index}`} 
                className={gift.is_regular_gift ? "gift-card-inventory-regular" : "gift-card-inventory"}
                style={!gift.is_regular_gift && gift.center_color && gift.edge_color ? {
                  background: `linear-gradient(135deg, ${gift.center_color} 0%, ${gift.edge_color} 100%)`
                } : {}}
              >
                {gift.model_path && (
                  <div className={gift.is_regular_gift ? "lottie-container-regular" : "lottie-container"}>
                    <LottieAnimation 
                      animationData={gift.model_path}
                      width={gift.is_regular_gift ? 100 : 80}
                      height={gift.is_regular_gift ? 100 : 80}
                      loop={true}
                      autoplay={true}
                    />
                  </div>
                )}
                
                <button 
                  className="gift-view-btn"
                  onClick={() => handleViewGift(gift)}
                >
                  Просмотр
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {showGiftDetails && selectedGift && (
        <GiftDetailsModal 
          gift={selectedGift}
          isInventory={true}
          onClose={() => {
            setShowGiftDetails(false)
            setSelectedGift(null)
          }}
          onSell={selectedGift.is_regular_gift ? handleSellRegular : handleSellNFT}
          onWithdraw={selectedGift.is_regular_gift ? handleWithdrawRegular : null}
        />
      )}
    </div>
  )
}

export default Inventory
