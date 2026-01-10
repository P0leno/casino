import { useState, useEffect } from 'react'
import './ShopFilterModal.css'



function ShopFilterModal({ onClose, onApplyFilter, currentFilters = {}, dynamicFilters = { titles: [], models: [], backdrops: [] } }) {
  // expandedCategory: 'gift', 'model', 'background'
  const [expandedCategory, setExpandedCategory] = useState('gift')
  const [searchQuery, setSearchQuery] = useState('')

  // Structured filters state
  const [filters, setFilters] = useState({
    gifts: currentFilters.gifts || [],
    models: currentFilters.models || [],
    backdrops: currentFilters.backdrops || []
  })

  // Helper to get items for the current category
  const getFilterItems = (category) => {
    if (category === 'gift') {
      return dynamicFilters.titles
    } else if (category === 'background') {
      return dynamicFilters.backdrops.map(b => b.name)
    } else if (category === 'model') {
      // Only show models for SELECTED gifts
      if (filters.gifts.length === 0) return []

      const available = new Set()
      filters.gifts.forEach(giftTitle => {
        const models = dynamicFilters.giftModels?.[giftTitle] || []
        models.forEach(m => available.add(m))
      })
      return Array.from(available).sort()
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

      // Cleanup logic: If we deselected a gift, remove its models if they are no longer valid for other selected gifts?
      // For now, simpler approach: Just filter the View. 
      // User selection remains in state, but won't match anything in Shop unless valid.
      // However, it's better UX to clear invalid models.
      let nextState = {
        ...prev,
        [category === 'gift' ? 'gifts' : category === 'model' ? 'models' : 'backdrops']: newArray
      }

      // If gifts changed, cleanup invalid models
      if (category === 'gift') {
        const selectedGifts = newArray
        if (selectedGifts.length === 0) {
          nextState.models = []
        } else {
          // Re-calculate available models
          const validModels = new Set()
          selectedGifts.forEach(g => {
            const ms = dynamicFilters.giftModels?.[g] || []
            ms.forEach(m => validModels.add(m))
          })
          // Remove models that are not in validModels
          nextState.models = prev.models.filter(m => validModels.has(m))
        }
      }

      return nextState
    })
  }

  const handleApply = () => {
    onApplyFilter(filters)
    onClose()
  }

  const handleClear = () => {
    setFilters({ gifts: [], models: [], backdrops: [] })
  }

  // Model selection is disabled if no Collection is selected
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

  const getBackdropByName = (name) => {
    return dynamicFilters.backdrops.find(b => b.name === name)
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
            const backdrop = category === 'background' ? getBackdropByName(item) : null
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
                          background: `radial-gradient(circle, ${backdrop.center_color || '#333'}, ${backdrop.edge_color || '#000'})`
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

