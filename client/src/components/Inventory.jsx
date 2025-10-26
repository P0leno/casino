import { useState } from 'react'
import './Inventory.css'

function Inventory() {
  const [showOverlay, setShowOverlay] = useState(false)

  const handleOpenBot = () => {
    window.open('https://t.me/shellrelayer', '_blank')
    setShowOverlay(false)
  }

  return (
    <div className="inventory-page">
      <div className="inventory-header">
        <h1>Инвентарь</h1>
      </div>

      <div className="inventory-content">
        <div className="inventory-grid">
          <div className="empty-inventory">
            <div className="empty-icon">🎁</div>
            <p className="empty-text">Ваш инвентарь пуст</p>
          </div>
        </div>
      </div>

      <div className="add-gifts-text" onClick={() => setShowOverlay(true)}>
        Добавить подарки
      </div>

      {showOverlay && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowOverlay(false)} />
          <div className="overlay-sheet">
            <div className="sheet-handle"></div>
            
            <div className="sheet-content">
              <div className="overlay-icon">🎁</div>
              <h2 className="overlay-title">Добавить подарки</h2>
              <p className="overlay-text">
                Чтобы подарки появились в вашем инвентаре, отправьте их боту
              </p>

              <div className="warning-block">
                <div className="warning-icon">⚠️</div>
                <p className="warning-text">
                  Не отправляйте не улучшенные подарки и не покупайте с ТГ маркета
                </p>
              </div>

              <button className="overlay-button" onClick={handleOpenBot}>
                Отправить
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Inventory
