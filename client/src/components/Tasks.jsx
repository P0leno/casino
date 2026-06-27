import { useState, useEffect } from 'react'
import './Home.css'
import './Tasks.css'
import './PromoCodeModal.css'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import { useBalance } from '../contexts/BalanceContext'
import LottieAnimation from './LottieAnimation'
import starAnim from '../assets/star.json'
import pawAnim from '../assets/paw.json'

function Tasks({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [completingTask, setCompletingTask] = useState(null)
  const [removingTaskId, setRemovingTaskId] = useState(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [selectedTask, setSelectedTask] = useState(null)

  const isMobile = window.Telegram?.WebApp?.platform === 'android' ||
    window.Telegram?.WebApp?.platform === 'ios'

  const tg = window.Telegram?.WebApp
  const safeAreaTop = tg?.safeAreaInset?.top || tg?.contentSafeAreaInset?.top || 0
  // Отступ = safe area + 20px (отступ баланс баров) + 36px (высота баланс бара с padding) + 10px (gap)
  const contentPadding = isMobile ? (safeAreaTop + 66) : 50

  useEffect(() => {
    loadAvailableTasks()
  }, [])

  const loadAvailableTasks = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) {
        setLoading(false)
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || ''
      const cacheBuster = Date.now()
      const response = await fetch(`${apiUrl}/api/tasks/list?_=${cacheBuster}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid && data.tasks) {
        setTasks(data.tasks)
      }
      setLoading(false)
    } catch (error) {
      console.error('Error loading tasks:', error)
      setLoading(false)
    }
  }

  const getTaskTitle = (task) => {
    if (task.type === 'subscribe' || task.type === 'private_channel') {
      return 'Подписаться'
    } else if (task.type === 'open_url') {
      return 'Перейти по ссылке'
    }
    return 'Задание'
  }

  const getTaskDescription = (task) => {
    return task.target
  }

  const handleStartTask = async (task) => {
    const tg = window.Telegram?.WebApp
    if (!tg) return

    setCompletingTask(task.id)

    // Для subscribe - открываем публичный канал
    if (task.type === 'subscribe') {
      // Извлекаем username канала
      let channelUsername = task.target
      if (channelUsername.startsWith('@')) {
        channelUsername = channelUsername.substring(1)
      } else if (channelUsername.includes('t.me/')) {
        channelUsername = channelUsername.split('t.me/')[1]
      }

      // Открываем канал
      tg.openTelegramLink(`https://t.me/${channelUsername}`)

      // Ждем 5 секунд чтобы пользователь успел подписаться
      setTimeout(() => {
        completeTask(task.id)
      }, 5000)
    } else if (task.type === 'private_channel') {
      // Для частного канала получаем invite link с сервера
      try {
        const initData = tg?.initData
        const apiUrl = import.meta.env.VITE_API_URL || ''
        const response = await fetch(`${apiUrl}/api/tasks/get-invite-link`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData, taskId: task.id })
        })

        const data = await response.json()
        if (data.success && data.inviteLink) {
          // Открываем invite link
          tg.openTelegramLink(data.inviteLink)

          // Ждем 5 секунд чтобы пользователь успел подписаться
          setTimeout(() => {
            completeTask(task.id)
          }, 5000)
        } else {
          setCompletingTask(null)
          return
        }
      } catch (error) {
        console.error('Error getting invite link:', error)
        setCompletingTask(null)
        return
      }
    } else if (task.type === 'open_url') {
      // Для open_url открываем ссылку и сразу засчитываем
      let url = task.target
      // Добавляем протокол если его нет
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url
      }
      tg.openLink(url)

      // Для open_url сразу засчитываем без проверки
      completeTask(task.id)
    }
  }

  const completeTask = async (taskId) => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || ''
      const response = await fetch(`${apiUrl}/api/tasks/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, taskId })
      })

      const data = await response.json()

      if (data.success) {
        updateBalance(data)
        // Запускаем анимацию удаления без уведомлений
        setRemovingTaskId(taskId)

        // Через 0.5 секунды убираем задание из списка
        setTimeout(() => {
          setTasks(tasks.filter(t => t.id !== taskId))
          setRemovingTaskId(null)
        }, 500)
      }
      // Если не success - просто ничего не делаем, никаких уведомлений

      setCompletingTask(null)
    } catch (error) {
      console.error('Error completing task:', error)
      const tg = window.Telegram?.WebApp
      tg?.showAlert('Ошибка соединения')
      setCompletingTask(null)
    }
  }

  return (
    <div className="home-page">
      <BalanceBar onNavigateToTopUp={onNavigateToTopUp} />
      <BonusBalanceBar />
      <div className="home-content" style={{ paddingTop: `${contentPadding}px` }}>
        <div className="tasks-header">
          <h2>Задания 📋</h2>
          <p>Выполняй задания и получай награды</p>
        </div>

        {loading ? (
          <div className="tasks-loading">Загрузка...</div>
        ) : tasks.length === 0 ? (
          <div className="tasks-empty">
            <p>Нет доступных заданий</p>
          </div>
        ) : (
          <div className="tasks-list">
            {tasks.map(task => (
              <div key={task.id} className={`task-card ${removingTaskId === task.id ? 'removing' : ''}`}>
                <div className="task-info">
                  <div className="task-title">{getTaskTitle(task)}</div>
                </div>
                <div className="task-right">
                  <div className="task-reward">
                    <LottieAnimation
                      animationData={task.currency === 'paws' ? pawAnim : starAnim}
                      width={24}
                      height={24}
                    />
                    <span className="task-reward-amount">{task.award}</span>
                  </div>
                  <div className="task-actions">
                    {(task.type === 'subscribe' || task.type === 'open_url' || task.type === 'private_channel') && (
                      <button
                        className="task-details-btn"
                        onClick={() => {
                          setSelectedTask(task)
                          setShowDetailsModal(true)
                        }}
                      >
                        Подробнее
                      </button>
                    )}
                    <button
                      className={`task-start-btn ${completingTask === task.id ? 'disabled' : ''}`}
                      onClick={() => handleStartTask(task)}
                      disabled={completingTask === task.id}
                    >
                      {completingTask === task.id ? 'Проверка...' : 'Начать'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showDetailsModal && selectedTask && (
        <>
          <div className="promo-modal-backdrop" onClick={() => setShowDetailsModal(false)} />
          <div className="promo-modal-sheet task-details-modal">
            <button className="promo-close-btn" onClick={() => setShowDetailsModal(false)}>×</button>

            <div className="promo-modal-content">
              <h2 className="promo-modal-title">Подробности задания</h2>

              <div className="task-detail-section">
                <div className="task-detail-label">
                  {selectedTask.type === 'open_url' ? 'Ссылка:' : 'Канал/Группа:'}
                </div>
                <div className="task-detail-value">{selectedTask.target}</div>
              </div>

              <div className="task-detail-section">
                <div className="task-detail-label">Награда:</div>
                <div className="task-detail-reward">
                  <LottieAnimation
                    animationData={selectedTask.currency === 'paws' ? pawAnim : starAnim}
                    width={24}
                    height={24}
                  />
                  <span>{selectedTask.award} {selectedTask.currency === 'paws' ? '🐾' : '⭐'}</span>
                </div>
              </div>

              <button
                className="promo-modal-action-btn"
                onClick={() => setShowDetailsModal(false)}
              >
                Закрыть
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Tasks
