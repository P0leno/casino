import { createContext, useContext, useState, useEffect } from 'react'

const BalanceContext = createContext()

export function BalanceProvider({ children }) {
  const [balance, setBalance] = useState(0)
  const [paws, setPaws] = useState(0)
  const [bonusBalance, setBonusBalance] = useState(0)

  // Функция для обновления баланса из ответа API
  const updateBalance = (data) => {
    if (data.balance !== undefined) setBalance(data.balance)
    if (data.paws !== undefined) setPaws(data.paws)
    if (data.bonusBalance !== undefined) setBonusBalance(data.bonusBalance)
  }

  // Загрузка начального баланса (опционально, если нужно)
  useEffect(() => {
    // Можно загрузить из localStorage если сохраняли
    const savedBalance = localStorage.getItem('userBalance')
    const savedPaws = localStorage.getItem('userPaws')
    if (savedBalance) setBalance(parseInt(savedBalance) || 0)
    if (savedPaws) setPaws(parseInt(savedPaws) || 0)
  }, [])

  // Сохранение в localStorage при изменении
  useEffect(() => {
    localStorage.setItem('userBalance', balance.toString())
    localStorage.setItem('userPaws', paws.toString())
  }, [balance, paws])

  return (
    <BalanceContext.Provider value={{ balance, paws, bonusBalance, updateBalance, setBalance, setPaws, setBonusBalance }}>
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
