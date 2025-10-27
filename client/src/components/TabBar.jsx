import './TabBar.css'
import homeIcon from '../assets/home.svg'
import inventoryIcon from '../assets/inventory.svg'
import spinIcon from '../assets/spin.svg'
import profileIcon from '../assets/profile.svg'

function TabBar({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'home', label: 'Главная', icon: homeIcon },
    { id: 'inventory', label: 'Инвентарь', icon: inventoryIcon },
    { id: 'spin', label: 'Спин', icon: spinIcon },
    { id: 'profile', label: 'Профиль', icon: profileIcon }
  ]

  return (
    <div className="tab-bar">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <img src={tab.icon} alt={tab.label} className="tab-icon" />
          <span className="tab-label">{tab.label}</span>
        </button>
      ))}
    </div>
  )
}

export default TabBar
