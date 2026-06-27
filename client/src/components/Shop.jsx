import { useState, useEffect } from 'react'
import './Shop.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import LottieAnimation from './LottieAnimation'
import GiftDetailsModal from './GiftDetailsModal'
import ShopSortModal from './ShopSortModal'
import ShopFilterModal from './ShopFilterModal'
import { useBalance } from '../contexts/BalanceContext'
import { useError } from './ErrorContext'
import starStaticBlackIcon from '../assets/starstatic_black.svg'

const API_URL = import.meta.env.VITE_API_URL || ''
const MODELS_LIST_URL = 'https://shelloch.xyz/gifts/models_list.json'

const hexToRgba = (hex, alpha) => {
  if (!hex) return `rgba(0, 0, 0, ${alpha})`;
  let r = 0, g = 0, b = 0;
  if (hex.length === 4) {
    r = parseInt(hex[1] + hex[1], 16);
    g = parseInt(hex[2] + hex[2], 16);
    b = parseInt(hex[3] + hex[3], 16);
  } else if (hex.length === 7) {
    r = parseInt(hex.substring(1, 3), 16);
    g = parseInt(hex.substring(3, 5), 16);
    b = parseInt(hex.substring(5, 7), 16);
  }
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function Shop({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const { showError } = useError()
  const [activeCategory, setActiveCategory] = useState('gift')
  const [gifts, setGifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedGift, setSelectedGift] = useState(null)
  const [showGiftDetails, setShowGiftDetails] = useState(false)
  const [showFilterModal, setShowFilterModal] = useState(false)
  const [showSortModal, setShowSortModal] = useState(false)
  const [sortOrder, setSortOrder] = useState('price_asc')
  const [appliedFilters, setAppliedFilters] = useState({ gifts: [], models: [], backdrops: [] })
  // const [filterCategory, setFilterCategory] = useState(null) // Removed
  const [modelsList, setModelsList] = useState({})


  const isMobile = window.Telegram?.WebApp?.platform === 'android' ||
    window.Telegram?.WebApp?.platform === 'ios'

  const tg = window.Telegram?.WebApp
  const safeAreaTop = tg?.safeAreaInset?.top || tg?.contentSafeAreaInset?.top || 0
  // Отступ = safe area + 20px (отступ баланс баров) + 50px (высота баланс бара) + 10px (gap)
  // Adjusted for "5px from status bar" request
  const contentPadding = isMobile ? (safeAreaTop + 60) : 60

  console.log('Shop - safeAreaTop:', safeAreaTop, 'contentPadding:', contentPadding, 'isMobile:', isMobile)

  const categories = [
    { id: 'gift', label: 'Подарок' },
    { id: 'background', label: 'Фон' }
  ]

  // Загрузка подарков с сервера и списка моделей
  useEffect(() => {
    loadGifts()
    loadModelsList()
  }, [])

  const loadModelsList = async () => {
    try {
      const response = await fetch(MODELS_LIST_URL)
      if (response.ok) {
        const data = await response.json()
        setModelsList(data)
      }
    } catch (error) {
      console.error('Error loading models list:', error)
    }
  }

  const loadGifts = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData || ''

      const cacheBuster = Date.now()
      console.log('Fetching gifts from:', `${API_URL}/api/shop/gifts`)

      const response = await fetch(`${API_URL}/api/shop/gifts?_=${cacheBuster}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      if (response.ok) {
        const data = await response.json()
        setGifts(data)
      }
    } catch (error) {
      console.error('Error loading gifts:', error)
    } finally {
      setLoading(false)
    }
  }

  // Фильтрация и сортировка подарков
  const getDisplayedGifts = () => {
    let result = gifts

    // 1. Фильтрация
    if (appliedFilters) {
      if (appliedFilters.gifts && appliedFilters.gifts.length > 0) {
        result = result.filter(gift => appliedFilters.gifts.includes(gift.title))
      }
      if (appliedFilters.models && appliedFilters.models.length > 0) {
        result = result.filter(gift => appliedFilters.models.includes(gift.model_name))
      }
      if (appliedFilters.backdrops && appliedFilters.backdrops.length > 0) {
        result = result.filter(gift => appliedFilters.backdrops.includes(gift.backdrop_name))
      }
    }

    // 2. Сортировка
    if (sortOrder === 'price_asc') {
      result = [...result].sort((a, b) => a.price - b.price)
    } else if (sortOrder === 'price_desc') {
      result = [...result].sort((a, b) => b.price - a.price)
    }

    return result
  }

  const handleGiftClick = (gift) => {
    setSelectedGift(gift)
    setShowGiftDetails(true)
  }

  const handlePurchase = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData || ''

    try {
      const response = await fetch(`${API_URL}/api/shop/buy-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          slug: gift.slug
        })
      })

      const data = await response.json()

      if (!response.ok) {
        const errorMsg = data.detail || data.error || 'Ошибка покупки'
        showError('Ошибка покупки', errorMsg, `Статус: ${response.status}\nОтвет: ${JSON.stringify(data)}`)
        return
      }

      // Успешная покупка
      const successMsg = `Подарок "${gift.title}" куплен! 🎁`
      if (tg?.showAlert) {
        tg.showAlert(successMsg)
      } else {
        alert(successMsg)
      }

      // Закрываем модальное окно
      setShowGiftDetails(false)
      setSelectedGift(null)

      // Обновляем баланс на фронтенде
      updateBalance()

      // Обновляем список подарков (может измениться availability)
      loadGifts()

    } catch (error) {
      console.error('Purchase error:', error)
      showError('Ошибка сети', error.message || 'Ошибка сети', error.stack || '')
    }
  }

  return (
    <div className="shop-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="shop-content" style={{ paddingTop: contentPadding }}>


        {/* Панель управления (Фильтр и Сортировка) */}
        <div className="shop-controls">
          <button
            className="shop-control-btn"
            onClick={() => setShowFilterModal(true)}
          >
            <span className="control-icon">🌪️</span> {/* Placeholder icon */}
            Фильтр
          </button>
          <button
            className="shop-control-btn"
            onClick={() => setShowSortModal(true)}
          >
            <span className="control-icon">⇅</span> {/* Placeholder icon */}
            Сортировка
          </button>

          {showSortModal && (
            <ShopSortModal
              currentSort={sortOrder}
              onClose={() => setShowSortModal(false)}
              onApplySort={(sort) => {
                setSortOrder(sort)
                setShowSortModal(false)
              }}
            />
          )}
        </div>

        {/* Сетка товаров */}
        <div className="shop-grid">
          {loading ? (
            <div className="shop-loading">Загрузка...</div>
          ) : getDisplayedGifts().length === 0 ? (
            <div className="shop-empty">Подарки не найдены</div>
          ) : (
            getDisplayedGifts().map(gift => (
              <div
                key={gift.gift_id}
                className="shop-item-card"
                onClick={() => handleGiftClick(gift)}
                style={{
                  background: gift.center_color
                    ? `radial-gradient(100% 80% at 50% 30%, ${hexToRgba(gift.center_color, 0.8)} 0%, ${hexToRgba(gift.center_color, 0.2)} 50%, ${hexToRgba(gift.center_color, 0)} 100%)`
                    : 'radial-gradient(circle, #363738, #0e0f0f)'
                }}
              >
                <div className="shop-item-image">
                  {gift.slug ? (
                    <img
                      src={`https://nft.fragment.com/gift/${gift.slug}.large.jpg`}
                      alt={gift.title}
                      style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                      loading="lazy"
                    />
                  ) : (
                    gift.model_path && (
                      <LottieAnimation
                        animationData={gift.model_path}
                        width="30%"
                        height="30%"
                        loop={true}
                        autoplay={true}
                      />
                    )
                  )}
                </div>
                <button className="shop-item-price">
                  {gift.price}
                  <img src={starStaticBlackIcon} alt="star" className="price-star-icon" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {showGiftDetails && selectedGift && (
        <GiftDetailsModal
          gift={selectedGift}
          onClose={() => {
            setShowGiftDetails(false)
            setSelectedGift(null)
          }}
          onPurchase={handlePurchase}
        />
      )}

      {showFilterModal && (
        <ShopFilterModal
          category={activeCategory}
          currentFilters={appliedFilters}
          dynamicFilters={{
            titles: [...new Set(gifts.map(g => g.title))].sort(),
            models: [...new Set(gifts.map(g => g.model_name).filter(Boolean))].sort(),
            backdrops: (() => {
              const unique = new Map();
              gifts.forEach(g => {
                if (g.backdrop_name && !unique.has(g.backdrop_name)) {
                  unique.set(g.backdrop_name, {
                    name: g.backdrop_name,
                    center_color: g.center_color,
                    edge_color: g.edge_color
                  });
                }
              });
              return Array.from(unique.values()).sort((a, b) => a.name.localeCompare(b.name));
            })(),
            giftModels: (() => {
              const map = {};
              gifts.forEach(g => {
                if (!map[g.title]) map[g.title] = new Set();
                if (g.model_name) map[g.title].add(g.model_name);
              });
              // Convert Sets to Arrays
              Object.keys(map).forEach(k => map[k] = Array.from(map[k]).sort());
              return map;
            })()
          }}
          onClose={() => setShowFilterModal(false)}
          onApplyFilter={(filters) => {
            setAppliedFilters(filters)
          }}
        />
      )}

    </div>
  )
}

export default Shop
