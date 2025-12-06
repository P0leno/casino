import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useBalance } from '../contexts/BalanceContext'

function ProtectedRoute({ children }) {
  const { updateBalance } = useBalance()
  const [loading, setLoading] = useState(true)
  const [authorized, setAuthorized] = useState(false)
  const [banned, setBanned] = useState(false)

  useEffect(() => {
    const validateUser = async () => {
      const tg = window.Telegram?.WebApp

      if (!tg) {
        setLoading(false)
        return
      }

      tg.ready()
      const initData = tg.initData

      if (!initData) {
        // Нет initData - оставляем бесконечный лоадер
        return
      }

      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
        const response = await fetch(`${apiUrl}/api/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData })
        })

        const data = await response.json()

        if (data.valid && data.isBanned) {
          setBanned(true)
          setLoading(false)
          return
        }

        if (data.valid && !data.isBanned) {
          // Обновляем баланс если пришел в ответе
          if (data.balance !== undefined || data.bonusBalance !== undefined) {
            updateBalance({
              balance: data.balance || 0,
              bonus_balance: data.bonusBalance || 0
            })
          }
          
          setAuthorized(true)
          setLoading(false)
        } else {
          setLoading(false)
        }
      } catch (error) {
        console.error('Validation error:', error)
        setLoading(false)
      }
    }

    validateUser()
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

  if (banned) {
    // Забаненные пользователи видят бесконечный лоадер
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

  if (!authorized) {
    return (
      <div className="error-container">
        <div className="error-message">Ошибка авторизации</div>
      </div>
    )
  }

  return children
}

export default ProtectedRoute
