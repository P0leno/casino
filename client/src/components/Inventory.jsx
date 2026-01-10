import { useState, useEffect, useRef } from 'react'
import './Inventory.css'
import './PromoCodeModal.css'
// LottieAnimation removed - using static images in inventory cards
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import { useBalance } from '../contexts/BalanceContext'
import GiftDetailsModal from './GiftDetailsModal'
import starStaticIcon from '../assets/star_static.svg'
import ActionStatusModal from './ActionStatusModal'
import PaymentModal from './PaymentModal'

function Inventory({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedGift, setSelectedGift] = useState(null)
  const [showGiftDetails, setShowGiftDetails] = useState(false)

  // State for ActionStatusModal (Error handling)
  const [showErrorModal, setShowErrorModal] = useState(false)
  const [errorData, setErrorData] = useState(null)

  // State for PaymentModal
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [paymentData, setPaymentData] = useState(null)

  const gridRef = useRef(null)

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

  // IntersectionObserver removed - no longer needed for static images

  const loadInventory = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) {
        setLoading(false)
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const cacheBuster = Date.now()
      console.log('Fetching inventory from:', `${apiUrl} /api/inventory / get`)

      const response = await fetch(`${apiUrl} /api/inventory / get ? _ = ${cacheBuster} `, {
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

  // --- Withdraw Logic ---

  const handleWithdrawRegular = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'

    // Confirmation
    const confirmMessage = `Вывести ${gift.title} на ваш аккаунт Telegram ? `
    const confirmed = tg?.showConfirm
      ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
      : window.confirm(confirmMessage)

    if (!confirmed) return

    try {
      // User requested: "if regular then parameter name"
      // We send 'name' key with the slug value (most reliable identifier)
      const response = await fetch(`${apiUrl} /api/withdraw - gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, name: gift.slug, index: 0 })
      })

      const data = await response.json()

      if (data.success) {
        if (tg?.showAlert) tg.showAlert('✅ Подарок успешно отправлен!')
        else alert('✅ Подарок успешно отправлен!')

        loadInventory()
        setShowGiftDetails(false)
      } else {
        // Show styled error modal
        setErrorData({
          gift: gift,
          error: data.error || data.message || 'Ошибка вывода',
          type: 'regular'
        })
        setShowErrorModal(true)
      }
    } catch (error) {
      console.error('Withdraw error:', error)
      setErrorData({
        gift: gift,
        error: 'Ошибка соединения с сервером',
        type: 'regular'
      })
      setShowErrorModal(true)
    }
  }

  const handleWithdrawNFT = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'

    const confirmMessage = `Вывести ${gift.title} на ваш аккаунт Telegram ? `
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
      console.log('NFT Withdraw Response:', data)

      if (data.success) {
        if (tg?.showAlert) tg.showAlert('✅ Подарок успешно отправлен!')
        else alert('✅ Подарок успешно отправлен!')

        loadInventory()
        setShowGiftDetails(false)
      } else if (
        data.requires_payment === true ||
        data.requires_payment === 'true' ||
        data.requires_payment ||
        (data.message && typeof data.message === 'string' && data.message.includes("Required fee:"))
      ) {
        // Show Payment Modal
        setPaymentData({
          ...data.payment_data,
          originalGift: gift // Save gift object to retry withdrawal
        })
        setShowPaymentModal(true)
        setShowGiftDetails(false) // Close details modal
      } else {
        // Show styled error modal
        const lottieUrl = `https://nft.fragment.com/gift/${gift.slug}.lottie.json`

        setErrorData({
          gift: gift,
          error: data.error || data.message || 'Ошибка вывода',
          type: 'nft',
          lottieSrc: lottieUrl
        })
        setShowErrorModal(true)
      }
    } catch (error) {
      console.error('Withdraw error:', error)
      const lottieUrl = `https://nft.fragment.com/gift/${gift.slug}.lottie.json`

      setErrorData({
        gift: gift,
        error: 'Ошибка соединения с сервером',
        type: 'nft',
        lottieSrc: lottieUrl
      })
      setShowErrorModal(true)
    }
  }

  // --- Manual Admin Withdraw Request ---
  /* New logic for Retry */
  const handleRetry = () => {
    setShowErrorModal(false)
    if (errorData?.type === 'regular') handleWithdrawRegular(errorData.gift)
    else if (errorData?.type === 'nft') handleWithdrawNFT(errorData.gift)
  }

  const handleManualAdminWithdraw = async () => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'

    if (!errorData || !errorData.gift) return

    try {
      const isNFT = errorData.type === 'nft'
      // Different endpoints for manual withdraw request
      const endpoint = isNFT
        ? `${apiUrl} /api/inventory / manual - withdraw - nft`
        : `${apiUrl} /api/inventory / manual - withdraw`

      const body = isNFT
        ? {
          initData,
          slug: errorData.gift.slug,
          giftTitle: errorData.gift.title,
          messageId: errorData.gift.message_id,
          error: errorData.error
        }
        : {
          initData,
          slug: errorData.gift.slug,
          giftTitle: errorData.gift.title,
          error: errorData.error
        }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      const data = await response.json()

      setShowErrorModal(false) // Close modal first

      if (data.success) {
        if (tg?.showAlert) tg.showAlert('✅ Заявка отправлена администрации!')
        else alert('✅ Заявка отправлена администрации!')
        loadInventory()
        setShowGiftDetails(false)
      } else {
        if (tg?.showAlert) tg.showAlert(data.message || 'Ошибка отправки заявки')
        else alert(data.message || 'Ошибка отправки заявки')
      }
    } catch (error) {
      console.error('Manual withdraw error:', error)
      const tg = window.Telegram?.WebApp
      if (tg?.showAlert) tg.showAlert('Ошибка соединения с сервером')
    }
  }

  const handleSellRegular = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'

    // Confirmation
    const price = gift.sell_price || '?'
    const confirmMessage = `Вы уверены, что хотите продать ${gift.title} за ${price} ⭐?`
    const confirmed = tg?.showConfirm
      ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
      : window.confirm(confirmMessage)

    if (!confirmed) return

    try {
      const response = await fetch(`${apiUrl} /api/sell - gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug: gift.slug })
      })
      const data = await response.json()
      if (data.success) {
        if (tg?.showAlert) tg.showAlert(msg)
        else alert(msg)
        loadInventory()
        // FIX: Map newBalance/newBonusBalance to balance/bonusBalance for context
        updateBalance({
          balance: data.newBalance,
          bonusBalance: data.newBonusBalance
        })
        setShowGiftDetails(false)
      } else {
        const msg = data.message || 'Ошибка продажи'
        if (tg?.showAlert) tg.showAlert(msg)
        else alert(msg)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleSellNFT = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
    // Confirmation for sell? Usually yes but let's skipping for brevity if not strict
    // Adding confirmation to be safe
    const confirmMessage = `Продать ${gift.title} за ${gift.sell_price || '?'} ⭐?`
    const confirmed = tg?.showConfirm
      ? await new Promise(r => tg.showConfirm(confirmMessage, r))
      : window.confirm(confirmMessage)

    if (!confirmed) return

    try {
      const response = await fetch(`${apiUrl}/api/inventory/sell-nft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug: gift.slug })
      })
      const data = await response.json()
      if (data.success) {
        const msg = `Продано! + ${data.newBalance - (data.oldBalance || 0)} ⭐`
        // logic might vary slightly depending on API response format
        if (tg?.showAlert) tg.showAlert('NFT успешно продан!')
        else alert('NFT успешно продан!')
        loadInventory()
        // FIX: Map newBalance/newBonusBalance to balance/bonusBalance for context
        updateBalance({
          balance: data.newBalance,
          bonusBalance: data.newBonusBalance
        })
        setShowGiftDetails(false)
      } else {
        if (tg?.showAlert) tg.showAlert(data.message || 'Ошибка продажи')
      }
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="inventory-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />

      <div className="inventory-content" style={{ paddingTop: `${topPadding} px` }}>
        {loading ? (
          <div className="loading-spinner"></div>
        ) : inventory.length === 0 ? (
          <div className="empty-inventory">
            {/* Empty UI */}
            <div className="empty-icon">🎁</div>
            <h3>Инвентарь пуст</h3>
            <p>У вас пока нет подарков.</p>
          </div>
        ) : (
          <div className="inventory-grid" ref={gridRef}>
            {inventory.map((gift, index) => {
              // Render card logic (same as before)
              const isRegular = gift.is_regular_gift
              const isNFT = !isRegular
              return (
                <div
                  key={`${gift.slug || gift.name} -${index} `}
                  className={isRegular ? 'gift-card-inventory-regular' : 'gift-card-inventory'}
                  onClick={() => handleViewGift(gift)}
                >
                  {/* Image rendering (already fixed to be stretched) */}
                  <div className="gift-image-wrapper" style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: isRegular ? 'relative' : 'absolute',
                    top: 0,
                    left: 0,
                    zIndex: 0
                  }}>
                    <img
                      src={isRegular
                        ? `https://shelloch.xyz/gifts/${gift.slug}.png`
                        : `https://nft.fragment.com/gift/${gift.slug || gift.name}.large.jpg`
                      }
                      alt={gift.title || gift.name}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: isRegular ? 'contain' : 'cover',
                        borderRadius: isRegular ? 0 : '20px'
                      }}
                      loading="lazy"
                    />
                  </div >

                  {isNFT && (
                    <div className="nft-badge" style={{ position: 'relative', zIndex: 1 }}>
                      <span className="nft-id">#{gift.collectible_id || '???'}</span>
                    </div>
                  )}

                  {
                    isRegular && (
                      <div className="gift-title-inventory" style={{ position: 'relative', zIndex: 1 }}>
                        {gift.title}
                      </div>
                    )
                  }

                  <button
                    className="gift-view-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleViewGift(gift)
                    }}
                    style={{ position: 'relative', zIndex: 1 }}
                  >
                    Просмотр
                  </button>
                </div >
              )
            })}
          </div >
        )}
      </div >

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

      {/* Payment Modal */}
      <PaymentModal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        invoiceUrl={paymentData?.invoice_url}
        amount={paymentData?.amount}
        giftTitle={paymentData?.gift_title}
        giftSlug={paymentData?.gift_slug}
        onCheckPayment={async () => {
          if (paymentData?.originalGift) {
            await handleWithdrawNFT(paymentData.originalGift)
          }
        }}
      />

      {/* Action Status Modal (Error / Success) */}
      <ActionStatusModal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title={errorData?.title || "Ошибка"} // Default title
        message={errorData?.error}
        isError={true}
        actionButtonText="Закрыть"
        onAction={() => setShowErrorModal(false)}
        lottieSrc={errorData?.lottieSrc}
        secondaryButtonText={errorData?.type === 'manual' ? "Написать в поддержку" : null}
        onSecondaryAction={() => {
          if (errorData?.type === 'manual') {
            window.Telegram?.WebApp?.openTelegramLink('https://t.me/shelloch_support_bot')
          }
        }}
      />
    </div >
  )
}

export default Inventory
