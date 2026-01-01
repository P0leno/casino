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

function ShopFilterModal({ onClose, onApplyFilter, currentFilters = {}, modelsList = {} }) {
  // expandedCategory: 'gift', 'model', 'background'
  const [expandedCategory, setExpandedCategory] = useState('gift')
  const [searchQuery, setSearchQuery] = useState('')

  // Structured filters state
  const [filters, setFilters] = useState({
    gifts: currentFilters.gifts || [],
    models: currentFilters.models || [],
    backdrops: currentFilters.backdrops || []
  })

  const [backdrops, setBackdrops] = useState([])
  const [availableModels, setAvailableModels] = useState([]) // Models for selected gifts

  // Load backdrops
  useEffect(() => {
    if (expandedCategory === 'background' && backdrops.length === 0) {
      loadBackdrops()
    }
  }, [expandedCategory])

  // Load models when Model section expanded or selected gifts change
  useEffect(() => {
    if (expandedCategory === 'model' && filters.gifts.length > 0) {
      loadModelsForSelectedGifts()
    }
  }, [expandedCategory, filters.gifts])

  const loadBackdrops = async () => {
    try {
      const response = await fetch('https://shelloch.xyz/gifts/backdrops.json')
      const data = await response.json()
      setBackdrops(data)
    } catch (error) {
      console.error('Error loading backdrops:', error)
    }
  }

  const loadModelsForSelectedGifts = async () => {
    try {
      // Fetch models for ALL selected gifts
      const uniqueModels = new Set()
      const promises = filters.gifts.map(giftName =>
        fetch(`https://shelloch.xyz/gifts/models/${encodeURIComponent(giftName)}/model.json`)
          .then(r => r.json())
          .then(data => data.models || [])
          .catch(() => [])
      )

      const results = await Promise.all(promises)
      results.flat().forEach(m => uniqueModels.add(m))
      setAvailableModels(Array.from(uniqueModels).sort())
    } catch (error) {
      console.error('Error loading models:', error)
      setAvailableModels([])
    }
  }

  const getFilterItems = (category) => {
    if (category === 'gift') {
      return Object.keys(modelsList).length > 0 ? Object.keys(modelsList) : GIFT_MODELS
    } else if (category === 'background') {
      return backdrops.map(b => b.name)
    } else if (category === 'model') {
      return availableModels
    }
    return []
  }

  const getFilteredItems = (category) => {
    return getFilterItems(category).filter(item => {
      const itemName = typeof item === 'string' ? item : item
      return itemName.toLowerCase().includes(searchQuery.toLowerCase())
    })
  }

  const toggleFilter = (item, category) => {
    setFilters(prev => {
      const targetArray = category === 'gift' ? prev.gifts :
        category === 'model' ? prev.models :
          prev.backdrops

      let newArray
      if (targetArray.includes(item)) {
        newArray = targetArray.filter(f => f !== item)
      } else {
        newArray = [...targetArray, item]
      }

      // If expanding gifts, and we deselect a gift, we might need to remove models that are no longer available?
      // For simplicity, we keep selected models but they might filter nothing. 
      // But typically we should cleanup. Leaving it simple for now (user didn't request complex cleanup).

      return {
        ...prev,
        [category === 'gift' ? 'gifts' : category === 'model' ? 'models' : 'backdrops']: newArray
      }
    })
  }

  const handleApply = () => {
    onApplyFilter(filters)
    onClose()
  }

  const handleClear = () => {
    setFilters({ gifts: [], models: [], backdrops: [] })
  }

  const isModelDisabled = filters.gifts.length === 0

  const toggleCategory = (category) => {
    if (category === 'model' && isModelDisabled) return // Block if disabled

    if (expandedCategory === category) {
      setExpandedCategory(null)
      setSearchQuery('')
    } else {
      setExpandedCategory(category)
      setSearchQuery('')
    }
  }

  const getBackdropById = (name) => {
    return backdrops.find(b => b.name === name)
  }

  const renderCategoryContent = (category, placeholder) => {
    const items = getFilteredItems(category)
    const currentSelection = category === 'gift' ? filters.gifts :
      category === 'model' ? filters.models :
        filters.backdrops

    return (
      <div className="accordion-content" onClick={(e) => e.stopPropagation()}>
        <div className="accordion-search-wrap">
          <span className="search-icon-placeholder">🔍</span>
          <input
            type="text"
            className="accordion-search"
            placeholder={placeholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="accordion-list">
          {items.length === 0 && <div style={{ padding: '10px', color: '#666', textAlign: 'center' }}>Нет данных</div>}

          {items.map((item, index) => {
            const backdrop = category === 'background' ? getBackdropById(item) : null
            const isSelected = currentSelection.includes(item)
            return (
              <div
                key={index}
                className={`accordion-item ${isSelected ? 'selected' : ''}`}
                onClick={() => toggleFilter(item, category)}
              >
                {category === 'background' ? (
                  <div className="item-left">
                    <div className={`checkbox-circle ${isSelected ? 'checked' : ''}`} />
                    {backdrop && (
                      <div
                        className="backdrop-circle-small"
                        style={{
                          background: `radial-gradient(circle, ${backdrop.hex.centerColor}, ${backdrop.hex.edgeColor})`
                        }}
                      />
                    )}
                    <span className="item-name">{item}</span>
                  </div>
                ) : (
                  <div className="item-left">
                    <div className={`checkbox-circle ${isSelected ? 'checked' : ''}`} />
                    <span className="item-name">{item}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="filter-modal-overlay" onClick={onClose}>
      <div className="filter-modal" onClick={(e) => e.stopPropagation()}>
        <div className="filter-header">
          <h3>Фильтры</h3>
          <button className="filter-close" onClick={onClose}>✕</button>
        </div>

        <div className="filter-list accordion-container">
          {/* Коллекция */}
          <div className={`accordion-section ${expandedCategory === 'gift' ? 'expanded' : ''}`}>
            <div className="accordion-header" onClick={() => toggleCategory('gift')}>
              <span>Коллекция</span>
              <span className="accordion-arrow">›</span>
            </div>
            {expandedCategory === 'gift' && renderCategoryContent('gift', 'Поиск коллекции')}
          </div>

          {/* Модель */}
          <div
            className={`accordion-section ${expandedCategory === 'model' ? 'expanded' : ''}`}
            style={isModelDisabled ? { opacity: 0.5, pointerEvents: 'none' } : {}}
            onClick={isModelDisabled ? (e) => e.stopPropagation() : undefined}
          >
            <div
              className="accordion-header"
              onClick={!isModelDisabled ? () => toggleCategory('model') : undefined}
              style={isModelDisabled ? { cursor: 'not-allowed' } : {}}
            >
              <span>Модель {isModelDisabled && '(Выберите коллекцию)'}</span>
              <span className="accordion-arrow">›</span>
            </div>
            {expandedCategory === 'model' && !isModelDisabled && renderCategoryContent('model', 'Поиск модели')}
          </div>

          {/* Фон */}
          <div className={`accordion-section ${expandedCategory === 'background' ? 'expanded' : ''}`}>
            <div className="accordion-header" onClick={() => toggleCategory('background')}>
              <span>Фон</span>
              <span className="accordion-arrow">›</span>
            </div>
            {expandedCategory === 'background' && renderCategoryContent('background', 'Поиск фона')}
          </div>
        </div>

        <div className="filter-actions">
          <button className="filter-btn filter-btn-clear" onClick={handleClear}>
            Сбросить
          </button>
          <button className="filter-btn filter-btn-apply" onClick={handleApply}>
            Применить
          </button>
        </div>
      </div>
    </div>
  )
}

export default ShopFilterModal

