import { useState, useEffect, useRef } from 'react'
import './Inventory.css'
import './PromoCodeModal.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import { useBalance } from '../contexts/BalanceContext'
import GiftDetailsModal from './GiftDetailsModal'
import starStaticIcon from '../assets/star_static.svg'

function Inventory({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedGift, setSelectedGift] = useState(null)
  const [showGiftDetails, setShowGiftDetails] = useState(false)
  const [sellingGift, setSellingGift] = useState(null)
  const [showErrorModal, setShowErrorModal] = useState(false)
  const [errorData, setErrorData] = useState(null)
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
        // Проверяем нужна ли ручная отправка (PeerIdInvalid)
        if (data.needsManual || (data.error && data.error.includes('PeerIdInvalid'))) {
          setErrorData({
            gift: gift,
            error: data.error || data.message,
            type: 'withdraw'
          })
          setShowErrorModal(true)
          setShowGiftDetails(false)
        } else {
          const errorMsg = data.message || 'Не удалось отправить подарок'
          if (tg?.showAlert) {
            tg.showAlert(errorMsg)
          } else {
            alert(errorMsg)
          }
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
        body: JSON.stringify({ initData, slug: gift.slug })
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

  // Вывод NFT подарков
  const handleWithdrawNFT = async (gift) => {
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
      const response = await fetch(`${apiUrl}/api/withdraw-nft-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          initData, 
          slug: gift.slug,
          messageId: gift.message_id
        })
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
        // Проверяем нужна ли ручная отправка (PeerIdInvalid)
        if (data.needsManual || (data.error && data.error.includes('PeerIdInvalid'))) {
          setErrorData({
            gift: gift,
            error: data.error || data.message,
            type: 'withdrawNFT'
          })
          setShowErrorModal(true)
          setShowGiftDetails(false)
        } else {
          const errorMsg = data.message || 'Не удалось отправить подарок'
          if (tg?.showAlert) {
            tg.showAlert(errorMsg)
          } else {
            alert(errorMsg)
          }
        }
      }
    } catch (error) {
      console.error('Withdraw NFT error:', error)
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
      // Проверяем что есть sell_price
      if (!gift.sell_price || gift.sell_price <= 0) {
        throw new Error('Цена продажи не установлена')
      }

      // Диалоговое окно подтверждения (sell_price уже рассчитан с комиссией)
      const confirmMessage = `Продать "${gift.title}"?\n\nВы получите: ${gift.sell_price}⭐`
      
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

      // Обновляем баланс
      updateBalance(sellData)

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
          onWithdraw={selectedGift.is_regular_gift ? handleWithdrawRegular : handleWithdrawNFT}
        />
      )}

      {showErrorModal && errorData && (
        <>
          <div className="promo-modal-backdrop" onClick={() => setShowErrorModal(false)} />
          <div className="promo-modal-sheet" style={{ paddingBottom: `${20}px` }}>
            <button className="promo-close-btn" onClick={() => setShowErrorModal(false)}>×</button>
            
            <div className="promo-modal-content">
              <h2 className="promo-modal-title">Ошибка отправки</h2>
              
              <div className="error-message-section">
                <div className="error-label">Произошла ошибка:</div>
                <div className="error-value">{errorData.error}</div>
              </div>

              <div className="error-instruction">
                <p>Убедитесь, что вы начали чат с ботом</p>
                <a 
                  href="https://t.me/shellrelayer"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bot-link"
                  onClick={(e) => {
                    e.preventDefault()
                    const tg = window.Telegram?.WebApp
                    tg?.openTelegramLink('https://t.me/shellrelayer')
                  }}
                >
                  @shellrelayer
                </a>
              </div>

              <div className="error-buttons">
                <button 
                  className="error-btn retry-btn"
                  onClick={async () => {
                    setShowErrorModal(false)
                    if (errorData.type === 'withdraw') {
                      await handleWithdrawRegular(errorData.gift)
                    } else if (errorData.type === 'withdrawNFT') {
                      await handleWithdrawNFT(errorData.gift)
                    }
                  }}
                >
                  Повторить
                </button>
                <button 
                  className="error-btn help-btn"
                  onClick={() => {
                    const tg = window.Telegram?.WebApp
                    tg?.openTelegramLink('https://t.me/ShellSupport_bot')
                    setShowErrorModal(false)
                  }}
                >
                  Помощь
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Inventory
