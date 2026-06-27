import { useState } from 'react'
import './ErrorModal.css'

function ErrorModal({ isOpen, title, message, details, onClose }) {
  const [copied, setCopied] = useState(false)

  if (!isOpen) return null

  const textToCopy = [
    title && `Ошибка: ${title}`,
    message && `Сообщение: ${message}`,
    details && `Детали:\n${details}`,
  ].filter(Boolean).join('\n')

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = textToCopy
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="errm-overlay" onClick={onClose}>
      <div className="errm-sheet glass" onClick={e => e.stopPropagation()}>
        <div className="errm-header">
          <span className="errm-icon">⚠️</span>
          <h3 className="errm-title">{title || 'Ошибка'}</h3>
          <button className="errm-close" onClick={onClose}>✕</button>
        </div>

        <div className="errm-body">
          {message && <p className="errm-message">{message}</p>}
          {details && (
            <div className="errm-details">
              <div className="errm-details-header">
                <span>Технические детали</span>
                <button className={`errm-copy-btn ${copied ? 'copied' : ''}`} onClick={handleCopy}>
                  {copied ? '✓ Скопировано' : '📋 Копировать'}
                </button>
              </div>
              <pre className="errm-code"><code>{details}</code></pre>
            </div>
          )}
        </div>

        <div className="errm-footer">
          <button className="errm-btn errm-btn-primary" onClick={onClose}>Закрыть</button>
          <button className="errm-btn errm-btn-secondary" onClick={handleCopy}>
            {copied ? '✓ Скопировано' : '📋 Скопировать ошибку'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ErrorModal
