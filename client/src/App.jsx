import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [validated, setValidated] = useState(false)

  useEffect(() => {
    const tg = window.Telegram?.WebApp

    if (!tg) {
      setError('Telegram Web App SDK не загружен')
      setLoading(false)
      return
    }

    tg.ready()
    tg.headerColor = '#000000'

    if (tg.platform === 'android' || tg.platform === 'ios') {
      tg.requestFullscreen()
    }

    const initData = tg.initData

    if (!initData) {
      return
    }

    const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
    
    fetch(`${apiUrl}/api/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData })
    })
      .then(res => res.json())
      .then(data => {
        if (data.valid) {
          setValidated(true)
        } else {
          setError('Ошибка: данные не валидны')
        }
        setLoading(false)
      })
      .catch(err => {
        setError('Ошибка соединения с сервером')
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="loader-container">
        <div className="loader-wrapper">
          <div className="preloader">
            <div className="crack"></div>
            <div className="crack crack2"></div>
            <div className="crack crack3"></div>
            <div className="crack crack4"></div>
            <div className="crack crack5"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">{error}</div>
      </div>
    )
  }

  return (
    <div className="app-container">
      <h1>Приложение запущено</h1>
      <p>Валидация прошла успешно!</p>
    </div>
  )
}

export default App
