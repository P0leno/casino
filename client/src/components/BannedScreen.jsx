import './BannedScreen.css'

function BannedScreen({ botUsername }) {
  const handleAppeal = () => {
    const url = `https://t.me/${botUsername}?start=appeal`
    window.Telegram?.WebApp?.openTelegramLink(url)
  }

  return (
    <div className="banned-screen">
      <div className="banned-content">
        <div className="banned-icon">⛔</div>
        <h1 className="banned-title">Вы были забанены</h1>
        <p className="banned-description">
          Ваш аккаунт был заблокирован администрацией
        </p>
        
        <button className="banned-appeal-btn" onClick={handleAppeal}>
          Обжаловать
        </button>
      </div>
    </div>
  )
}

export default BannedScreen
