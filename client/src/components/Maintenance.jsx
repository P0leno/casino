import './Maintenance.css'

function Maintenance() {
  console.log('Maintenance component rendered!')
  
  return (
    <div className="maintenance-container">
      <div className="maintenance-content">
        <div className="maintenance-icon">
          🔧
        </div>
        <h1 className="maintenance-title">
          Технические работы
        </h1>
        <p className="maintenance-message">
          Приложение временно недоступно
        </p>
        <p className="maintenance-subtitle">
          Попробуйте позже
        </p>
      </div>
    </div>
  )
}

export default Maintenance
