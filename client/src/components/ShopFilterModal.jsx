import { useState, useEffect } from 'react'
import './ShopFilterModal.css'

const GIFT_MODELS = [
  'Artisan Brick', 'Astral Shard', 'B-Day Candle', 'Berry Box', 'Big Year',
  'Bling Binky', 'Bonded Ring', 'Bow Tie', 'Bunny Muffin', 'Candy Cane',
  'Clover Pin', 'Cookie Heart', 'Crystal Ball', 'Cupid Charm', 'Desk Calendar',
  'Diamond Ring', "Durov's Cap", 'Easter Egg', 'Electric Skull', 'Eternal Candle',
  'Eternal Rose', 'Evil Eye', 'Faith Amulet', 'Flying Broom', 'Fresh Socks',
  'Gem Signet', 'Genie Lamp', 'Ginger Cookie', 'Hanging Star', 'Happy Brownie',
  'Heart Locket', 'Heroic Helmet', 'Hex Pot', 'Holiday Drink', 'Homemade Cake',
  'Hypno Lollipop', 'Ice Cream', 'Input Key', 'Instant Ramen', 'Ion Gem',
  'Ionic Dryer', 'Jack-in-the-Box', 'Jelly Bunny', 'Jester Hat', 'Jingle Bells',
  'Jolly Chimp', 'Joyful Bundle', 'Kissed Frog', 'Light Sword', 'Lol Pop',
  'Love Candle', 'Love Potion', 'Low Rider', 'Lush Bouquet', 'Lunar Snake',
  'Loot Bag', 'Mad Pumpkin', 'Magic Potion', 'Mighty Arm', 'Mini Oscar',
  'Money Pot', 'Moon Pendant', 'Mousse Cake', 'Nail Bracelet', 'Neko Helmet',
  'Party Sparkler', 'Perfume Bottle', 'Pet Snake', 'Plush Pepe', 'Precious Peach',
  'Pretty Posy', 'Record Player', 'Restless Jar', 'Sakura Flower', 'Santa Hat',
  'Scared Cat', 'Sharp Tongue', 'Signet Ring', 'Skull Flower', 'Sky Stilettos',
  'Sleigh Bell', 'Snoop Cigar', 'Snoop Dogg', 'Snow Globe', 'Snow Mittens',
  'Snake Box', 'Spiced Wine', 'Spring Basket', 'Spy Agaric', 'Star Notepad',
  'Stellar Rocket', 'Swag Bag', 'Swiss Watch', 'Tama Gadget', 'Top Hat',
  'Toy Bear', 'Trapped Heart', 'Valentine Box', 'Vintage Cigar', 'Voodoo Doll',
  'Westside Sign', 'Whip Cupcake', 'Winter Wreath', 'Witch Hat', 'Xmas Stocking'
]

function ShopFilterModal({ category, onClose, onApplyFilter, currentFilters = [] }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilters, setSelectedFilters] = useState(currentFilters) // Инициализируем текущими фильтрами
  const [backdrops, setBackdrops] = useState([])
  const [selectedGift, setSelectedGift] = useState(null) // Для двухуровневого выбора моделей
  const [giftModels, setGiftModels] = useState([]) // Модели выбранного подарка

  useEffect(() => {
    if (category === 'background') {
      loadBackdrops()
    }
  }, [category])

  const loadBackdrops = async () => {
    try {
      const response = await fetch('https://shelloch.xyz/gifts/backdrops.json')
      const data = await response.json()
      setBackdrops(data)
    } catch (error) {
      console.error('Error loading backdrops:', error)
    }
  }

  const loadGiftModels = async (giftName) => {
    try {
      // Загружаем список моделей для конкретного подарка
      const response = await fetch(`https://shelloch.xyz/gifts/models/${encodeURIComponent(giftName)}/model.json`)
      const data = await response.json()
      // Предполагаем что в model.json есть массив моделей
      setGiftModels(data.models || [])
      setSelectedGift(giftName)
    } catch (error) {
      console.error('Error loading gift models:', error)
      setGiftModels([])
    }
  }

  const getFilterItems = () => {
    if (category === 'gift') {
      return GIFT_MODELS
    } else if (category === 'background') {
      return backdrops.map(b => b.name)
    } else if (category === 'model') {
      // Для моделей показываем список подарков или модели выбранного подарка
      if (selectedGift) {
        return giftModels
      } else {
        return GIFT_MODELS
      }
    } else if (category === 'symbol') {
      return [] // Пока без сортировки
    }
    return []
  }

  const filteredItems = getFilterItems().filter(item => {
    const itemName = typeof item === 'string' ? item : item
    return itemName.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const toggleFilter = (item) => {
    // Для моделей - если выбираем подарок первый раз, загружаем его модели
    if (category === 'model' && !selectedGift && GIFT_MODELS.includes(item)) {
      loadGiftModels(item)
      return
    }
    
    // Обычная мульти-сортировка
    if (selectedFilters.includes(item)) {
      setSelectedFilters(selectedFilters.filter(f => f !== item))
    } else {
      setSelectedFilters([...selectedFilters, item])
    }
  }

  const handleBack = () => {
    if (category === 'model' && selectedGift) {
      setSelectedGift(null)
      setGiftModels([])
    }
  }

  const handleApply = () => {
    onApplyFilter(selectedFilters)
    onClose()
  }

  const handleClear = () => {
    setSelectedFilters([])
    onApplyFilter([])
    onClose()
  }

  const getBackdropById = (name) => {
    return backdrops.find(b => b.name === name)
  }

  return (
    <div className="filter-modal-overlay" onClick={onClose}>
      <div className="filter-modal" onClick={(e) => e.stopPropagation()}>
        <div className="filter-header">
          {category === 'model' && selectedGift && (
            <button className="filter-back" onClick={handleBack}>← Назад</button>
          )}
          <h3>
            {category === 'gift' ? 'Подарки' : 
             category === 'model' ? (selectedGift ? `Модели: ${selectedGift}` : 'Выберите подарок') : 
             category === 'background' ? 'Фоны' : 
             'Символы'}
          </h3>
          <button className="filter-close" onClick={onClose}>✕</button>
        </div>

        <input 
          type="text"
          className="filter-search"
          placeholder="Поиск..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        <div className="filter-list">
          {filteredItems.map((item, index) => {
            const backdrop = category === 'background' ? getBackdropById(item) : null
            return (
              <div 
                key={index}
                className={`filter-item ${selectedFilters.includes(item) ? 'selected' : ''}`}
                onClick={() => toggleFilter(item)}
              >
                {backdrop && (
                  <div 
                    className="backdrop-circle"
                    style={{
                      background: `radial-gradient(circle, ${backdrop.hex.centerColor}, ${backdrop.hex.edgeColor})`
                    }}
                  />
                )}
                <span>{item}</span>
              </div>
            )
          })}
        </div>

        <div className="filter-actions">
          <button className="filter-btn filter-btn-clear" onClick={handleClear}>
            Очистить фильтры
          </button>
          <button className="filter-btn filter-btn-apply" onClick={handleApply}>
            Готово
          </button>
        </div>
      </div>
    </div>
  )
}

export default ShopFilterModal
