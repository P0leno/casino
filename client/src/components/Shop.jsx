import { useState, useEffect } from 'react'
import './Shop.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import LottieAnimation from './LottieAnimation'
import GiftDetailsModal from './GiftDetailsModal'
import ShopFilterModal from './ShopFilterModal'
import { useBalance } from '../contexts/BalanceContext'
import starStaticBlackIcon from '../assets/starstatic_black.svg'

const API_URL = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
const MODELS_LIST_URL = 'https://shelloch.xyz/gifts/models_list.json'

function Shop({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const [activeCategory, setActiveCategory] = useState('gift')
  const [gifts, setGifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedGift, setSelectedGift] = useState(null)
  const [showGiftDetails, setShowGiftDetails] = useState(false)
  const [showFilterModal, setShowFilterModal] = useState(false)
  const [appliedFilters, setAppliedFilters] = useState([])
  const [filterCategory, setFilterCategory] = useState(null) // Категория для которой применены фильтры
  const [modelsList, setModelsList] = useState({}) // Список всех моделей из models_list.json

  const isMobile = window.Telegram?.WebApp?.platform === 'android' ||
    window.Telegram?.WebApp?.platform === 'ios'

  const tg = window.Telegram?.WebApp
  const safeAreaTop = tg?.safeAreaInset?.top || tg?.contentSafeAreaInset?.top || 0
  // Отступ = safe area + 20px (отступ баланс баров) + 50px (высота баланс бара) + 10px (gap)
  const contentPadding = isMobile ? (safeAreaTop + 80) : 50

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

  // Фильтрация подарков по выбранным фильтрам
  const getFilteredGifts = () => {
    if (appliedFilters.length === 0 || !filterCategory) {
      return gifts
    }

    // Применяем фильтры в зависимости от категории
    return gifts.filter(gift => {
      if (filterCategory === 'gift') {
        // Фильтруем по названию подарка (title должно быть в списке)
        return gift.title && appliedFilters.includes(gift.title)
      } else if (filterCategory === 'model') {
        // Фильтруем по модели (model_name должно быть в списке)
        return gift.model_name && appliedFilters.includes(gift.model_name)
      } else if (filterCategory === 'background') {
        // Фильтруем по фону (backdrop_name должно быть в списке)
        return gift.backdrop_name && appliedFilters.includes(gift.backdrop_name)
      }
      return true
    })
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
        // Показываем ошибку (FastAPI возвращает detail)
        const errorMsg = data.detail || data.error || 'Ошибка покупки'
        if (tg?.showAlert) {
          tg.showAlert(errorMsg)
        } else {
          alert(errorMsg)
        }
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
      const errorMsg = 'Ошибка сети'
      if (tg?.showAlert) {
        tg.showAlert(errorMsg)
      } else {
        alert(errorMsg)
      }
    }
  }

  return (
    <div className="shop-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="shop-content">
        <div style={{ paddingTop: `${contentPadding}px` }}>
          <h1 className="shop-title">Магазин 🛒</h1>
        </div>

        {/* Категории */}
        <div className="shop-categories">
          {categories.map(category => (
            <button
              key={category.id}
              className={`category-btn ${activeCategory === category.id ? 'active' : ''}`}
              onClick={() => {
                setActiveCategory(category.id)
                // Открываем фильтр при нажатии на категорию
                setShowFilterModal(true)
              }}
            >
              {category.label}
            </button>
          ))}
        </div>

        {/* Сетка товаров */}
        <div className="shop-grid">
          {loading ? (
            <div className="shop-loading">Загрузка...</div>
          ) : getFilteredGifts().length === 0 ? (
            <div className="shop-empty">Подарки не найдены</div>
          ) : (
            getFilteredGifts().map(gift => (
              <div
                key={gift.gift_id}
                className="shop-item-card"
                onClick={() => handleGiftClick(gift)}
              >
                <div
                  className="shop-item-image"
                  style={{
                    background: gift.center_color && gift.edge_color
                      ? `linear-gradient(135deg, ${gift.center_color} 0%, ${gift.edge_color} 100%)`
                      : 'radial-gradient(circle, #363738, #0e0f0f)'
                  }}
                >
                  {gift.model_path && (
                    <LottieAnimation
                      animationData={gift.model_path}
                      width="30%"
                      height="30%"
                      loop={true}
                      autoplay={true}
                    />
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
          currentFilters={filterCategory === activeCategory ? appliedFilters : []} // Передаем фильтры только если категория совпадает
          modelsList={modelsList} // Передаем список моделей
          onClose={() => setShowFilterModal(false)}
          onApplyFilter={(filters) => {
            setAppliedFilters(filters)
            setFilterCategory(activeCategory) // Сохраняем категорию для которой применены фильтры
          }}
        />
      )}
    </div>
  )
}

export default Shop
