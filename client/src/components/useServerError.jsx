import { useCallback } from 'react'
import { useError } from './ErrorContext'

export function useServerError() {
  const { showError } = useError()

  const handleError = useCallback((err, context = '') => {
    if (err instanceof Response) {
      // Fetch Response — пытаемся прочитать тело
      err.clone().text().then(body => {
        let details = body
        try {
          const json = JSON.parse(body)
          details = json.detail || json.message || JSON.stringify(json, null, 2)
        } catch {}
        showError(
          `Ошибка сервера (${err.status})`,
          context || 'Запрос к серверу не удался',
          details
        )
      }).catch(() => {
        showError(
          `Ошибка сервера (${err.status})`,
          context || 'Запрос к серверу не удался',
          err.statusText
        )
      })
    } else if (err instanceof TypeError) {
      // Network error
      showError(
        'Ошибка соединения',
        'Не удалось连接到 серверу. Проверьте интернет.',
        `${err.message}\n\n${err.stack || ''}`
      )
    } else if (typeof err === 'string') {
      showError('Ошибка', context || '', err)
    } else if (err?.message) {
      showError(
        'Ошибка',
        context || '',
        `${err.message}\n${err.stack || ''}`
      )
    } else {
      showError('Ошибка', context || '', String(err))
    }
  }, [showError])

  const showApiError = useCallback(async (res, context = '') => {
    let body = ''
    try { body = await res.clone().text() } catch {}
    let details = body
    try {
      const json = JSON.parse(body)
      details = json.detail || json.message || JSON.stringify(json, null, 2)
    } catch {}

    const title = `Ошибка ${res.status}`
    let message = context || 'Запрос не выполнен'
    if (res.status === 400) message = 'Неверный запрос'
    else if (res.status === 403) message = 'Нет доступа'
    else if (res.status === 404) message = 'Ресурс не найден'
    else if (res.status === 429) message = 'Слишком много запросов'
    else if (res.status >= 500) message = 'Ошибка сервера'

    showError(title, message, details)
  }, [showError])

  return { handleError, showApiError }
}
