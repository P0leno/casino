import './GiftDetailsModal.css'
import LottieAnimation from './LottieAnimation'
import { useState } from 'react'
import starAnim from '../assets/star.json'

function GiftDetailsModal({ gift, onClose, onPurchase, onSell, onWithdraw, isInventory = false }) {
  if (!gift) return null
  
  const [purchasing, setPurchasing] = useState(false)
  const [selling, setSelling] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)

  // Определяем тип подарка: NFT или Shop
  const isNFTGift = gift.collectible_id !== undefined
  const isShopGift = gift.gift_id !== undefined && gift.price !== undefined

  // Формируем ссылку на NFT
  const nftUrl = isNFTGift 
    ? `https://t.me/nft/${gift.name}`
    : `https://t.me/nft/${gift.slug || gift.gift_id}`

  const handleOpenLink = (e) => {
    e.preventDefault()
    // Используем Telegram WebApp API если доступен
    const tg = window.Telegram?.WebApp
    
    // openTelegramLink открывает внутри Telegram (для t.me ссылок)
    if (tg && tg.openTelegramLink) {
      tg.openTelegramLink(nftUrl)
    } else if (tg && tg.openLink) {
      tg.openLink(nftUrl)
    } else {
      window.open(nftUrl, '_blank')
    }
  }

  const getInitials = (user) => {
    if (!user) return '?'
    const first = user.first_name?.[0] || ''
    const last = user.last_name?.[0] || ''
    return (first + last).toUpperCase() || '?'
  }

  const getFullName = (user) => {
    if (!user) return 'Unknown'
    const parts = [user.first_name, user.last_name].filter(Boolean)
    return parts.join(' ') || user.username || 'Unknown'
  }

  const handlePurchase = async () => {
    if (purchasing) return
    
    const tg = window.Telegram?.WebApp
    
    // Подтверждение покупки
    const confirmMessage = `Купить "${gift.title}" за ${gift.price} ⭐?`
    const confirmed = tg?.showConfirm 
      ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
      : window.confirm(confirmMessage)
    
    if (!confirmed) return
    
    setPurchasing(true)
    
    try {
      if (onPurchase) {
        await onPurchase(gift)
      }
    } catch (error) {
      console.error('Purchase error:', error)
    } finally {
      setPurchasing(false)
    }
  }

  const handleSell = async () => {
    if (selling) return
    
    setSelling(true)
    
    try {
      if (onSell) {
        await onSell(gift)
      }
    } catch (error) {
      console.error('Sell error:', error)
    } finally {
      setSelling(false)
    }
  }

  const handleWithdraw = async () => {
    if (withdrawing) return
    
    setWithdrawing(true)
    
    try {
      if (onWithdraw) {
        await onWithdraw(gift)
      }
    } catch (error) {
      console.error('Withdraw error:', error)
    } finally {
      setWithdrawing(false)
    }
  }

  return (
    <>
      <div className="overlay-backdrop" onClick={onClose} />
      <div className="overlay-sheet gift-details-modal">
        <div className="sheet-content">
          {/* Карточка подарка с фоном */}
          <div 
            className="gift-card-preview"
            style={{
              background: gift.center_color && gift.edge_color 
                ? `linear-gradient(135deg, ${gift.center_color} 0%, ${gift.edge_color} 100%)`
                : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            }}
          >
            <button className="modal-close-btn-on-card" onClick={onClose}>✕</button>
            
            <a 
              href={nftUrl} 
              onClick={handleOpenLink}
              className="modal-open-link"
            >
              Открыть
            </a>
            
            {gift.model_path && (
              <div className="gift-animation">
                <LottieAnimation 
                  animationData={gift.model_path}
                  width={80}
                  height={80}
                  loop={true}
                  autoplay={true}
                />
              </div>
            )}
          </div>

          {isNFTGift && (
            <>
              <h2 className="gift-details-title">{gift.title}</h2>
              <p className="gift-details-subtitle">
                коллекционный предмет #{gift.collectible_id}
              </p>
            </>
          )}

          {/* Владелец (только для NFT подарков) */}
          {isNFTGift && gift.owner && (
            <div className="info-section">
              <div className="info-row">
                <span className="info-label">Владелец</span>
              </div>
              <div className="owner-card-compact">
                {gift.owner.photo_url ? (
                  <img src={gift.owner.photo_url} alt="Avatar" className="owner-avatar-small" />
                ) : (
                  <div className="owner-avatar-small placeholder">
                    {getInitials(gift.owner)}
                  </div>
                )}
                <span className="owner-name-compact">{getFullName(gift.owner)}</span>
              </div>
            </div>
          )}

          {/* Атрибуты подарка (только для NFT) */}
          {!gift.is_regular_gift && (
            <div className="info-section">
              {gift.model_name && (
                <div className="info-row">
                  <span className="info-label">Модель</span>
                  <span className="info-value">
                    {gift.model_name}
                    {gift.rarity_model && (
                      <span className="rarity-percent">{(gift.rarity_model / 10).toFixed(1)}%</span>
                    )}
                  </span>
                </div>
              )}

              {gift.symbol_name && (
                <div className="info-row">
                  <span className="info-label">Узор</span>
                  <span className="info-value">
                    {gift.symbol_name}
                    {gift.rarity_symbol && (
                      <span className="rarity-percent">{(gift.rarity_symbol / 10).toFixed(1)}%</span>
                    )}
                  </span>
                </div>
              )}

              {gift.backdrop_name && (
                <div className="info-row">
                  <span className="info-label">Фон</span>
                  <span className="info-value">
                    {gift.backdrop_name}
                    {gift.rarity_backdrop && (
                      <span className="rarity-percent">{(gift.rarity_backdrop / 10).toFixed(1)}%</span>
                    )}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Кнопки */}
          {isInventory ? (
            // Кнопки для инвентаря
            <div className="modal-buttons-column">
              {gift.is_regular_gift ? (
                // Обычный подарок - Вывести и Продать
                <>
                  <button 
                    className="modal-withdraw-button" 
                    onClick={handleWithdraw}
                    disabled={withdrawing}
                  >
                    {withdrawing ? 'Вывод...' : 'Вывести'}
                  </button>
                  <button 
                    className="spin-button-fixed modal-sell-button" 
                    onClick={handleSell}
                    disabled={selling}
                  >
                    {selling ? (
                      'Продажа...'
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="button-main-text">Продать за {gift.sell_price || 0}</span>
                        <LottieAnimation animationData={starAnim} width={24} height={24} />
                      </div>
                    )}
                  </button>
                </>
              ) : (
                // NFT подарок - только Продать
                <button 
                  className="spin-button-fixed modal-sell-button-full" 
                  onClick={handleSell}
                  disabled={selling}
                >
                  {selling ? (
                    'Продажа...'
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="button-main-text">Продать за {gift.sell_price || 0}</span>
                      <LottieAnimation animationData={starAnim} width={24} height={24} />
                    </div>
                  )}
                </button>
              )}
            </div>
          ) : (
            // Кнопки для магазина
            isShopGift && gift.price > 0 && (
              <button 
                className="spin-button-fixed modal-buy-button" 
                onClick={handlePurchase}
                disabled={purchasing}
              >
                {purchasing ? (
                  'Покупка...'
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="button-main-text">Купить за {gift.price}</span>
                    <LottieAnimation animationData={starAnim} width={24} height={24} />
                  </div>
                )}
              </button>
            )
          )}
        </div>
      </div>
    </>
  )
}

export default GiftDetailsModal
