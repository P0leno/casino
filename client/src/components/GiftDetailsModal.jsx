import './GiftDetailsModal.css'
import LottieAnimation from './LottieAnimation'
import { useState } from 'react'
import starIcon from '../assets/star_static.svg'

function GiftDetailsModal({ gift, onClose, onPurchase, onSell, onWithdraw, isInventory = false }) {
  if (!gift) return null

  const [purchasing, setPurchasing] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  // Determine if this is a regular gift or NFT
  const isRegularGift = gift.is_regular_gift || false

  // Withdrawal Lock Check
  const [timeLeft, setTimeLeft] = useState('')
  const [isLocked, setIsLocked] = useState(false)

  useState(() => {
    if (gift.unlock_at) {
      const updateTimer = () => {
        const now = new Date()
        const unlockDate = new Date(gift.unlock_at)
        const diff = unlockDate - now

        if (diff > 0) {
          setIsLocked(true)
          const days = Math.floor(diff / (1000 * 60 * 60 * 24))
          const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
          setTimeLeft(`${days}d ${hours}h`)
        } else {
          setIsLocked(false)
          setTimeLeft('')
        }
      }

      updateTimer()
      const interval = setInterval(updateTimer, 60000) // Update every minute
      return () => clearInterval(interval)
    }
  }, [gift.unlock_at])

  // Lottie URL for preview modal - animation for ALL gifts
  const getLottieUrl = () => {
    if (isRegularGift) {
      // Regular gift: Lottie from shelloch.xyz
      return `https://shelloch.xyz/gifts/${gift.slug}.json`
    } else {
      // NFT gift: Lottie from fragment.com
      return `https://nft.fragment.com/gift/${gift.slug}.lottie.json`
    }
  }

  const handleClose = () => {
    setIsClosing(true)
    setTimeout(() => {
      onClose()
    }, 300)
  }

  const handleBuy = async () => {
    if (purchasing) return
    setPurchasing(true)
    try {
      await onPurchase(gift)
    } finally {
      setPurchasing(false)
    }
  }

  const handleSell = () => {
    if (onSell) onSell(gift)
  }

  // Mock percentages for UI demo
  const modelPercent = '2%'
  const symbolPercent = '0.4%'
  const backdropPercent = '1.2%'

  return (
    <div
      className={`gift-modal-overlay ${isClosing ? 'gift-modal-overlay-closing' : ''}`}
      onClick={handleClose}
    >
      <div
        className={`gift-modal-content ${isClosing ? 'gift-modal-content-closing' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Gradient Spotlight */}
        <div className="gift-modal-spotlight" />

        <button className="gift-modal-close" onClick={handleClose}>✕</button>

        <div className="gift-modal-scroll-content">
          {/* Black background with Lottie animation for ALL gifts */}
          {/* Black background with Lottie animation for ALL gifts */}
          <div
            className={`gift-modal-image-container ${isRegularGift ? 'gift-modal-regular-bg' : ''}`}
            style={!isRegularGift ? { background: '#000' } : {}}
          >
            {isLocked && (
              <div style={{
                position: 'absolute',
                top: 10,
                right: 10,
                background: 'rgba(0, 0, 0, 0.6)',
                backdropFilter: 'blur(4px)',
                padding: '4px 8px',
                borderRadius: 8,
                color: '#fff',
                fontSize: 12,
                fontWeight: 'bold',
                zIndex: 10,
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                {timeLeft}
              </div>
            )}
            <LottieAnimation
              animationData={getLottieUrl()}
              width={isRegularGift ? 200 : 240}
              height={isRegularGift ? 200 : 240}
              loop={true}
              autoplay={true}
            />
          </div>

          {/* Gift title for regular gifts */}
          {isRegularGift && (
            <h2 className="gift-modal-title">{gift.title || gift.name}</h2>
          )}

          {/* Attributes only for NFT gifts */}
          {!isRegularGift && (
            <div className="gift-modal-attributes">
              <div className="gift-modal-attr-row">
                <span className="gift-modal-attr-label">Модель</span>
                <div className="gift-modal-attr-value-container">
                  <span className="gift-modal-attr-value">{gift.model_name || 'Unknown'}</span>
                  <span className="gift-modal-attr-percent">{modelPercent}</span>
                </div>
              </div>

              <div className="gift-modal-attr-row">
                <span className="gift-modal-attr-label">Символ</span>
                <div className="gift-modal-attr-value-container">
                  <span className="gift-modal-attr-value">{gift.symbol_name || 'Standard'}</span>
                  <span className="gift-modal-attr-percent">{symbolPercent}</span>
                </div>
              </div>

              <div className="gift-modal-attr-row">
                <span className="gift-modal-attr-label">Фон</span>
                <div className="gift-modal-attr-value-container">
                  <span className="gift-modal-attr-value">{gift.backdrop_name || 'Black'}</span>
                  <span className="gift-modal-attr-percent">{backdropPercent}</span>
                </div>
              </div>

              <div className="gift-modal-attr-row">
                <span className="gift-modal-attr-label">Цена флора</span>
                <div className="gift-modal-attr-value-container">
                  <span className="gift-modal-attr-value-white">
                    <img src={starIcon} alt="Star" style={{ width: 18, height: 18, marginRight: 4 }} />
                    {isInventory ? `≈ ${gift.price || '8.7'}` : `${gift.price}`}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="gift-modal-actions">
          {isInventory ? (
            <>
              <button
                className={`gift-modal-action-btn gift-modal-btn-buy ${isLocked ? 'disabled' : ''}`}
                onClick={() => !isLocked && onWithdraw && onWithdraw(gift)}
                disabled={isLocked}
                style={isLocked ? { background: '#333', color: '#888', cursor: 'not-allowed' } : {}}
              >
                {isLocked ? 'Вывод заблокирован' : 'Вывести'}
              </button>
              <button className="gift-modal-action-btn gift-modal-btn-sell" onClick={handleSell}>
                Продать
              </button>
            </>
          ) : (
            <button className="gift-modal-action-btn gift-modal-btn-buy" onClick={handleBuy}>
              {purchasing ? (
                'Покупка...'
              ) : (
                <>
                  Купить
                  <img src={starIcon} alt="Star" style={{ width: 18, height: 18, marginLeft: 8, marginRight: 4, filter: 'brightness(0) invert(1)' }} />
                  {gift.price}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div >
  )
}

export default GiftDetailsModal
