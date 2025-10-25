import './TabBar.css'

function TabBar({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'home', label: 'Главная', icon: '🏠' },
    { id: 'inventory', label: 'Инвентарь', icon: '🎁' },
    { id: 'profile', label: 'Профиль', icon: '👤' }
  ]

  return (
    <div className="tab-bar">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className="tab-icon">{tab.icon}</span>
          <span className="tab-label">{tab.label}</span>
        </button>
      ))}
    </div>
  )
}

export default TabBar
