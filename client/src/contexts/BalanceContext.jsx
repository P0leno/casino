import { createContext, useContext, useState, useEffect } from 'react'

const BalanceContext = createContext()

export function BalanceProvider({ children }) {
  const [balance, setBalance] = useState(0)
  const [paws, setPaws] = useState(0)
  const [bonusBalance, setBonusBalance] = useState(0)
  const [isAdmin, setIsAdmin] = useState(false)

  // Функция для обновления баланса - может принять данные или загрузить с сервера
  const updateBalance = async (data) => {
    // Если передали данные - обновляем из них
    if (data && typeof data === 'object') {
      if (data.balance !== undefined) setBalance(data.balance)
      if (data.paws !== undefined) setPaws(data.paws)
      if (data.bonusBalance !== undefined) setBonusBalance(data.bonusBalance)
      if (data.isAdmin !== undefined) setIsAdmin(data.isAdmin)
      return
    }
    
    // Если вызвали без параметров - загружаем с сервера
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return
      
      const apiUrl = import.meta.env.VITE_API_URL || 'https://api.shelloch.xyz'
      const response = await fetch(`${apiUrl}/api/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })
      
      const result = await response.json()
      if (result.valid) {
        if (result.balance !== undefined) setBalance(result.balance)
        if (result.bonusBalance !== undefined) setBonusBalance(result.bonusBalance)
        if (result.isAdmin !== undefined) setIsAdmin(result.isAdmin)
      }
    } catch (error) {
      console.error('Error fetching balance:', error)
    }
  }

  // Загрузка начального баланса
  useEffect(() => {
    // Загружаем актуальный баланс с сервера при старте
    updateBalance()
  }, [])



  return (
    <BalanceContext.Provider value={{ balance, paws, bonusBalance, isAdmin, updateBalance, setBalance, setPaws, setBonusBalance, setIsAdmin }}>
      {children}
    </BalanceContext.Provider>
  )
}

export function useBalance() {
  const context = useContext(BalanceContext)
  if (!context) {
    throw new Error('useBalance must be used within BalanceProvider')
  }
  return context
}
