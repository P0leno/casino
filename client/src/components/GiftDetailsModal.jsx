import './GiftDetailsModal.css'
import LottieAnimation from './LottieAnimation'
import { useState, useEffect } from 'react'
import starAnim from '../assets/star.json'

const MODELS_LIST_URL = 'https://shelloch.xyz/gifts/models_list.json'
const BACKDROPS_URL = 'https://shelloch.xyz/gifts/backdrops.json'

function GiftDetailsModal({ gift, onClose, onPurchase, onSell, onWithdraw, isInventory = false }) {
  if (!gift) return null

  const [purchasing, setPurchasing] = useState(false)
  const [selling, setSelling] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)
  const [modelsExpanded, setModelsExpanded] = useState(false)
  const [availableModels, setAvailableModels] = useState([])
  const [showBackdropModal, setShowBackdropModal] = useState(false)
  const [backdrops, setBackdrops] = useState([])

  // Загрузка списка моделей для этого подарка
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch(MODELS_LIST_URL)
        if (response.ok) {
          const data = await response.json()
          // Находим модели для текущего подарка
          const models = data[gift.title]?.models || []
          setAvailableModels(models)
        }
      } catch (error) {
        console.error('Error loading models:', error)
      }
    }

    if (gift.title) {
      loadModels()
    }
  }, [gift.title])

  // Загрузка списка фонов
  useEffect(() => {
    const loadBackdrops = async () => {
      try {
        const response = await fetch(BACKDROPS_URL)
        if (response.ok) {
          const data = await response.json()
          setBackdrops(data)
        }
      } catch (error) {
        console.error('Error loading backdrops:', error)
      }
    }

    loadBackdrops()
  }, [])

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
                : 'radial-gradient(circle, #363738, #0e0f0f)'
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

          {/* Атрибуты подарка */}
          {!gift.is_regular_gift && (
            <div className="info-section">
              {/* Модели - expandable полоса */}
              {availableModels.length > 0 && (
                <div className="attribute-expandable">
                  <div
                    className="attribute-header"
                    onClick={() => setModelsExpanded(!modelsExpanded)}
                  >
                    <div className="attribute-main">
                      <span className="attribute-label">Модель</span>
                      {gift.model_name && (
                        <span className="attribute-value">
                          {gift.model_name}
                          {gift.rarity_model && (
                            <span className="rarity-percent">{(gift.rarity_model / 10).toFixed(1)}%</span>
                          )}
                        </span>
                      )}
                    </div>
                    <span className={`attribute-arrow ${modelsExpanded ? 'expanded' : ''}`}>›</span>
                  </div>
                  {modelsExpanded && (
                    <div className="attribute-list">
                      {availableModels.map((model, index) => (
                        <div
                          key={index}
                          className={`attribute-item ${gift.model_name === model ? 'current' : ''}`}
                        >
                          {model}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Фон - кнопка открывающая модальное окно */}
              {gift.backdrop_name && (
                <div
                  className="attribute-button"
                  onClick={() => setShowBackdropModal(true)}
                >
                  <div className="attribute-main">
                    <span className="attribute-label">Фон</span>
                    <span className="attribute-value">
                      {gift.backdrop_name}
                      {gift.rarity_backdrop && (
                        <span className="rarity-percent">{(gift.rarity_backdrop / 10).toFixed(1)}%</span>
                      )}
                    </span>
                  </div>
                  <span className="attribute-arrow">›</span>
                </div>
              )}
            </div>
          )}

          {/* Кнопки */}
          {isInventory ? (
            // Кнопки для инвентаря
            <div className="modal-buttons-column">
              {gift.is_regular_gift ? (
                // Обычный подарок - только Продать с текстом о выводе
                <>
                  <div className="withdraw-info-text">
                    <span className="withdraw-info-regular">Этот подарок можно </span>
                    <span
                      className="withdraw-info-link"
                      onClick={handleWithdraw}
                    >
                      вывести
                    </span>
                  </div>
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

      {/* Модальное окно с фонами */}
      {showBackdropModal && (
        <div className="backdrop-modal-overlay" onClick={() => setShowBackdropModal(false)}>
          <div className="backdrop-modal" onClick={(e) => e.stopPropagation()}>
            <div className="backdrop-modal-header">
              <h3>Фоны</h3>
              <button className="backdrop-modal-close" onClick={() => setShowBackdropModal(false)}>✕</button>
            </div>
            <div className="backdrop-modal-grid">
              {backdrops.map((backdrop, index) => (
                <div
                  key={index}
                  className={`backdrop-modal-item ${gift.backdrop_name === backdrop.name ? 'current' : ''}`}
                >
                  <div
                    className="backdrop-circle-large"
                    style={{
                      background: `radial-gradient(circle, ${backdrop.hex.centerColor}, ${backdrop.hex.edgeColor})`
                    }}
                  />
                  <span className="backdrop-name">{backdrop.name}</span>
                  {backdrop.rarity && (
                    <span className="backdrop-rarity">{(backdrop.rarity / 10).toFixed(1)}%</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default GiftDetailsModal
