import './Home.css'

function Home() {
  return (
    <div className="home-page">
      <div className="home-header">
        <h1>Главная</h1>
      </div>
      
      <div className="home-content">
        <div className="welcome-card">
          <h2>Добро пожаловать! 👋</h2>
          <p>Это главная страница приложения</p>
        </div>

        <div className="info-cards">
          <div className="info-card">
            <div className="card-icon">🎯</div>
            <h3>Возможности</h3>
            <p>Здесь будут основные функции</p>
          </div>

          <div className="info-card">
            <div className="card-icon">⚡</div>
            <h3>Быстрый доступ</h3>
            <p>Популярные действия</p>
          </div>

          <div className="info-card">
            <div className="card-icon">📊</div>
            <h3>Статистика</h3>
            <p>Ваша активность</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
