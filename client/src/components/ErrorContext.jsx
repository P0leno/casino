import { createContext, useContext, useState, useCallback } from 'react'
import ErrorModal from './ErrorModal'

const ErrorContext = createContext(null)

export function ErrorProvider({ children }) {
  const [error, setError] = useState(null)

  const showError = useCallback((title, message, details) => {
    setError({ title, message, details })
  }, [])

  const hideError = useCallback(() => {
    setError(null)
  }, [])

  return (
    <ErrorContext.Provider value={{ showError, hideError }}>
      {children}
      <ErrorModal
        isOpen={!!error}
        title={error?.title}
        message={error?.message}
        details={error?.details}
        onClose={hideError}
      />
    </ErrorContext.Provider>
  )
}

export function useError() {
  const ctx = useContext(ErrorContext)
  if (!ctx) throw new Error('useError must be used within ErrorProvider')
  return ctx
}
