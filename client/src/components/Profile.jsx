import { useEffect, useState, useRef } from 'react'
import './Profile.css'
import LottieAnimation from './LottieAnimation'
import Settings from './Settings'
import GiftDetailsModal from './GiftDetailsModal'
import PromoCodeModal from './PromoCodeModal'
import ActionStatusModal from './ActionStatusModal'
import PaymentModal from './PaymentModal'
import starStaticIcon from '../assets/star_static.svg'
import giftIcon from '../assets/gift.svg'
import supIcon from '../assets/sup.svg'
import pawAnim from '../assets/paw.json'
import starAnim from '../assets/star.json'
import secretIcon from '../assets/secret.svg'
import { useBalance } from '../contexts/BalanceContext'

const giftAnimations = {
  bear: '/gifts/bear.json',
  bottle: '/gifts/bottle.json',
  cake: '/gifts/cake.json',
  cup: '/gifts/cup.json',
  diamond: '/gifts/diamond.json',
  flowers: '/gifts/flowers.json',
  gift: '/gifts/gift.json',
  heart: '/gifts/heart.json',
  ring: '/gifts/ring.json',
  rocket: '/gifts/rocket.json',
  rose: '/gifts/rose.json',
  paw: pawAnim,
  star: starAnim,
  secret: secretIcon
}

function Profile() {
  const { isAdmin } = useBalance()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showAdminPanel, setShowAdminPanel] = useState(false)
  const [targetUserId, setTargetUserId] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [showChancesPanel, setShowChancesPanel] = useState(false)
  const [chances, setChances] = useState([])
  const [editingGift, setEditingGift] = useState(null)
  const [selectedSpinMode, setSelectedSpinMode] = useState('free_spin') // free_spin, bazmin, lapik, nistart, promik
  const [refundUserId, setRefundUserId] = useState('')
  const [refundTransactionId, setRefundTransactionId] = useState('')
  const [showSettingsPanel, setShowSettingsPanel] = useState(false)
  const [refundLoading, setRefundLoading] = useState(false)
  const [showRefundPanel, setShowRefundPanel] = useState(false)
  const [deductFromBalance, setDeductFromBalance] = useState(false)
  const [showCrashPanel, setShowCrashPanel] = useState(false)
  const [crashMaxMultiplier, setCrashMaxMultiplier] = useState(1000)
  const [crashAlwaysProfit, setCrashAlwaysProfit] = useState(false)
  const [crashMaxDebt, setCrashMaxDebt] = useState(300)
  const [crashBigBetThreshold, setCrashBigBetThreshold] = useState(100)
  const [crashBigBetLoseChance, setCrashBigBetLoseChance] = useState(30)
  const [crashState, setCrashState] = useState(null)
  const [exploding, setExploding] = useState(false)
  const adminWsRef = useRef(null)
  const [showSafeArea, setShowSafeArea] = useState(false)
  const [safeAreaInset, setSafeAreaInset] = useState({ top: 0, bottom: 0, left: 0, right: 0 })
  const [showTasksPanel, setShowTasksPanel] = useState(false)
  const [tasks, setTasks] = useState([])
  const [showAddTaskForm, setShowAddTaskForm] = useState(false)
  const [taskTarget, setTaskTarget] = useState('')
  const [taskType, setTaskType] = useState('subscribe')
  const [taskAward, setTaskAward] = useState('')
  const [taskCurrency, setTaskCurrency] = useState('paws')
  const [taskLimit, setTaskLimit] = useState('') // New limitation state
  const [botPermissionStatus, setBotPermissionStatus] = useState('')
  const [checkingPermissions, setCheckingPermissions] = useState(false)
  const [tasksLoading, setTasksLoading] = useState(false)
  const [useCustomInvite, setUseCustomInvite] = useState(false)
  const [customInviteLink, setCustomInviteLink] = useState('')
  const [inventory, setInventory] = useState([])
  const [inventoryLoading, setInventoryLoading] = useState(true)
  const [selectedGift, setSelectedGift] = useState(null)
  const [showGiftDetails, setShowGiftDetails] = useState(false)
  const gridRef = useRef(null)
  const observerRef = useRef(null)
  const [activeProfileTab, setActiveProfileTab] = useState('inventory')
  const [showPromoCodeModal, setShowPromoCodeModal] = useState(false)
  const [showErrorModal, setShowErrorModal] = useState(false)
  const [errorData, setErrorData] = useState(null)
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [paymentData, setPaymentData] = useState(null)
  const [cases, setCases] = useState([])
  const [adminView, setAdminView] = useState('list') // list, chances, gifts
  const [caseGifts, setCaseGifts] = useState([])

  // Add Case functionality
  const [isAddingCase, setIsAddingCase] = useState(false)
  const [newCaseData, setNewCaseData] = useState({ slug: '', title: '', price: '0', currency: 'star', spinLimit: '-1' })
  const [newCaseIcon, setNewCaseIcon] = useState(null) // For toggling gifts logic

  useEffect(() => {
    const tg = window.Telegram?.WebApp

    // Получаем safe area insets
    if (tg) {
      const safeArea = {
        top: tg.safeAreaInset?.top || 0,
        bottom: tg.safeAreaInset?.bottom || 0,
        left: tg.safeAreaInset?.left || 0,
        right: tg.safeAreaInset?.right || 0
      }
      setSafeAreaInset(safeArea)
      console.log('Safe Area Inset:', safeArea)
    }
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
      setUser(tg.initDataUnsafe.user)
    }

    loadInventory().finally(() => setLoading(false))
    loadInventory().finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (showChancesPanel) {
      loadCases()
      setAdminView('list')
    }
  }, [showChancesPanel])



  // IntersectionObserver removed - no longer needed for static images

  const getAvatarUrl = () => {
    if (user?.photo_url) {
      return user.photo_url
    }
    return null
  }

  const getInitials = () => {
    if (!user) return '?'
    const first = user.first_name?.[0] || ''
    const last = user.last_name?.[0] || ''
    return (first + last).toUpperCase() || '?'
  }

  const handleBanUser = async () => {
    if (!targetUserId.trim()) {
      alert('Введите User ID')
      return
    }

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/ban-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, targetUserId: parseInt(targetUserId) })
      })

      const data = await response.json()
      if (data.success) {
        alert('Пользователь забанен')
        setTargetUserId('')
      } else {
        alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'))
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }

  const loadChances = async (mode = 'free_spin') => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/get-chances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, mode })
      })

      const data = await response.json()
      if (data.valid) {
        setChances(data.chances)
      }
    } catch (error) {
      console.error('Error loading chances:', error)
    }
  }

  const handleUpdateChance = async (giftName, visibleChance, realChance, mode, pawMin = 0, pawMax = 0, starMin = 1, starMax = 5) => {
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/update-chances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, giftName, visibleChance, realChance, mode, pawMin, pawMax, starMin, starMax })
      })

      const data = await response.json()
      if (data.success) {
        alert('Шансы обновлены')
        loadChances(mode)
        setEditingGift(null)
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }

  const handleUnbanUser = async () => {
    if (!targetUserId.trim()) {
      alert('Введите User ID')
      return
    }

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/unban-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, targetUserId: parseInt(targetUserId) })
      })

      const data = await response.json()
      if (data.success) {
        alert('Пользователь разбанен')
        setTargetUserId('')
      } else {
        alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'))
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }

  const loadCrashSettings = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/crash/get-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid) {
        setCrashMaxMultiplier(data.maxMultiplier)
        setCrashAlwaysProfit(data.alwaysProfit || false)
        setCrashMaxDebt(data.maxDebt || 300)
        setCrashBigBetThreshold(data.bigBetThreshold || 100)
        setCrashBigBetLoseChance(data.bigBetLoseChance || 30)
      }
    } catch (error) {
      console.error('Error loading crash settings:', error)
    }
  }

  const loadCases = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/cases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.success) {
        setCases(data.cases)
      }
    } catch (error) {
      console.error('Error loading cases:', error)
    }
  }

  const handleUpdateCase = async (slug, title, price, spinLimit) => {
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/cases/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug, title, price: parseInt(price), spinLimit: parseInt(spinLimit) })
      })

      const data = await response.json()
      if (data.success) {
        alert('Кейс обновлен')
        loadCases()
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (error) {
      alert('Ошибка соединения')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCreateCase = async () => {
    if (!newCaseIcon || !newCaseData.slug || !newCaseData.title) {
      alert('Заполните все поля и выберите иконку')
      return
    }
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const formData = new FormData()
      formData.append('initData', initData)
      formData.append('slug', newCaseData.slug)
      formData.append('title', newCaseData.title)
      formData.append('price', newCaseData.price)
      formData.append('currency', newCaseData.currency)
      formData.append('spinLimit', newCaseData.spinLimit)
      formData.append('icon', newCaseIcon)

      const response = await fetch(`${apiUrl}/api/admin/cases/create`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()
      if (data.success) {
        alert('Кейс создан')
        setIsAddingCase(false)
        setNewCaseData({ slug: '', title: '', price: 0, currency: 'star', spinLimit: -1 })
        // Assuming data.cases contains the updated list, otherwise loadCases() is needed
        setCases(data.cases) // Changed from updated.data.cases to data.cases, assuming data contains the new list
        setNewCaseIcon(null)

        // Auto-redirect to Chances configuration
        setSelectedSpinMode(newCaseData.slug);
        setAdminView('chances');
        loadChances(newCaseData.slug); // Should load default seeded chances

      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (e) {
      alert('Error creating case: ' + e.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteCase = async (slug) => {
    if (!window.confirm(`Удалить кейс ${slug}? Это действие необратимо.`)) return
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/cases/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug })
      })
      const data = await response.json()
      if (data.success) {
        alert('Кейс удален')
        loadCases()
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (e) {
      alert('Ошибка соединения')
    } finally {
      setActionLoading(false)
    }
  }

  // Helper to toggle active status
  const handleToggleCaseActive = async (item) => {
    // Toggle logic
    const newStatus = !item.isActive;
    // Use existing update logic but passing isActive
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/cases/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          slug: item.slug,
          title: item.title,
          price: item.price,
          spinLimit: item.spinLimit,
          isActive: newStatus
        })
      })

      const data = await response.json()
      if (data.success) {
        loadCases()
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (error) {
      alert('Ошибка соединения')
    } finally {
      setActionLoading(false)
    }
  }

  const loadCaseGifts = async (mode) => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/cases/gifts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, mode })
      })

      const data = await response.json()
      if (data.success) {
        setCaseGifts(data.gifts)
      }
    } catch (error) {
      console.error('Error loading case gifts:', error)
    }
  }

  const handleToggleCaseGift = async (slug, giftName, enabled) => {
    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/cases/toggle-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug, giftName, enabled })
      })

      const data = await response.json()
      if (data.success) {
        loadCaseGifts(slug) // Reload status
      }
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  const handleUpdateCrashSettings = async () => {
    if (!crashMaxMultiplier || crashMaxMultiplier < 2 || crashMaxMultiplier > 100000) {
      alert('Максимальный коэффициент должен быть от 2 до 100000')
      return
    }

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/crash/update-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          maxMultiplier: parseFloat(crashMaxMultiplier),
          alwaysProfit: crashAlwaysProfit,
          maxDebt: parseInt(crashMaxDebt),
          bigBetThreshold: parseInt(crashBigBetThreshold),
          bigBetLoseChance: parseInt(crashBigBetLoseChance)
        })
      })

      const data = await response.json()
      if (data.success) {
        alert('Настройки краш-игры обновлены')
        setShowCrashPanel(false)
      } else {
        alert('Ошибка: ' + data.message)
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setActionLoading(false)
    }
  }



  const handleExplode = async () => {
    if (!window.confirm('Взорвать ракету сейчас?')) return

    setExploding(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) return

      const apiUrl = import.meta.env.VITE_API_URL || ''
      const response = await fetch(`${apiUrl}/api/admin/crash/explode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (!data.success) {
        alert(data.message || 'Ошибка взрыва')
      }
    } catch (error) {
      console.error('Error exploding:', error)
      alert('Ошибка соединения с сервером')
    } finally {
      setExploding(false)
    }
  }

  const handleRefund = async () => {
    if (!refundUserId.trim() || !refundTransactionId.trim()) {
      alert('Заполните все поля')
      return
    }

    const confirmText = deductFromBalance
      ? `Вернуть платеж для пользователя ${refundUserId}?\nTransaction: ${refundTransactionId}\n\n⚠️ Баланс пользователя будет уменьшен (может уйти в минус)`
      : `Вернуть платеж для пользователя ${refundUserId}?\nTransaction: ${refundTransactionId}`

    const confirmed = confirm(confirmText)
    if (!confirmed) return

    setRefundLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/refund-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          userId: parseInt(refundUserId),
          transactionId: refundTransactionId,
          deductFromBalance: deductFromBalance
        })
      })

      const data = await response.json()
      if (data.success) {
        let message = '✅ Платеж успешно возвращен'
        if (data.deductedAmount !== undefined && data.deductedAmount > 0) {
          message += `\nСписано со счета: ${data.deductedAmount} ⭐`
        }
        if (data.newBalance !== undefined) {
          message += `\nНовый баланс: ${data.newBalance} ⭐`
        }
        alert(message)
        setRefundUserId('')
        setRefundTransactionId('')
        setDeductFromBalance(false)
      } else {
        alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'))
      }
    } catch (error) {
      alert('Ошибка соединения с сервером')
    } finally {
      setRefundLoading(false)
    }
  }

  const loadTasks = async () => {
    setTasksLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/tasks/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.valid && data.tasks) {
        console.log('Loaded tasks:', data.tasks)
        setTasks(data.tasks)
      }
    } catch (error) {
      console.error('Error loading tasks:', error)
    } finally {
      setTasksLoading(false)
    }
  }

  const checkBotPermissions = async () => {
    if (taskType === 'open_url' || !taskTarget.trim()) {
      setBotPermissionStatus('')
      return
    }

    setCheckingPermissions(true)
    setBotPermissionStatus('Проверка...')

    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/tasks/check-bot-permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, channelUsername: taskTarget })
      })

      const data = await response.json()
      if (data.valid && data.hasPermissions) {
        setBotPermissionStatus('✅ Бот имеет права админа')
      } else {
        setBotPermissionStatus('❌ Бот не имеет прав админа в канале')
      }
    } catch (error) {
      console.error('Error checking permissions:', error)
      setBotPermissionStatus('❌ Ошибка проверки')
    } finally {
      setCheckingPermissions(false)
    }
  }

  const handleTaskTypeChange = (newType) => {
    setTaskType(newType)
    // Сбрасываем custom invite при смене типа
    if (newType !== 'private_channel') {
      setUseCustomInvite(false)
      setCustomInviteLink('')
    }
    if (newType === 'open_url') {
      setBotPermissionStatus('')
    } else if (taskTarget.trim()) {
      checkBotPermissions()
    }
  }

  const handleTaskTargetChange = (value) => {
    setTaskTarget(value)
    setBotPermissionStatus('')
  }

  const handleCreateTask = async () => {
    if (!taskTarget.trim() || !taskAward || parseInt(taskAward) < 1) {
      alert('Заполните все поля корректно')
      return
    }

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/tasks/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          target: taskTarget,
          type: taskType,
          award: parseInt(taskAward),
          currency: taskCurrency,
          customInvite: useCustomInvite ? customInviteLink : null,
          limit: taskLimit ? parseInt(taskLimit) : null
        })
      })

      const data = await response.json()
      if (data.success) {
        tg.showAlert('Задание успешно создано!')
        setShowAddTaskForm(false)
        setTaskTarget('')
        setTaskAward('')
        setTaskLimit('')
        loadTasks()
      } else {
        tg.showAlert(data.message || 'Ошибка создания задания')
      }
    } catch (error) {
      console.error('Error creating task:', error)
      alert('Ошибка соединения')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteTask = async (taskId) => {
    if (!confirm('Удалить задание?')) return

    setActionLoading(true)
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const response = await fetch(`${apiUrl}/api/admin/tasks/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, taskId })
      })

      const data = await response.json()
      if (data.success) {
        alert('Задание удалено')
        loadTasks()
      } else {
        alert(data.message || 'Ошибка удаления')
      }
    } catch (error) {
      console.error('Error deleting task:', error)
      alert('Ошибка соединения')
    } finally {
      setActionLoading(false)
    }
  }

  const getTaskTypeLabel = (type) => {
    const labels = {
      'subscribe': 'Подписка на канал',
      'private_channel': 'Подписка на частный канал',
      'open_url': 'Открыть ссылку'
    }
    return labels[type] || type
  }

  const loadInventory = async () => {
    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData
      if (!initData) {
        setInventoryLoading(false)
        return
      }

      const apiUrl = import.meta.env.VITE_API_URL || ''
      const response = await fetch(`${apiUrl}/api/inventory/get`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      })

      const data = await response.json()
      if (data.inventory) {
        setInventory(data.inventory)
      }
    } catch (error) {
      console.error('Error loading inventory:', error)
    } finally {
      setInventoryLoading(false)
    }
  }

  const handleViewGift = (gift) => {
    setSelectedGift(gift)
    setShowGiftDetails(true)
  }

  const handleWithdrawRegular = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || ''

    const confirmMessage = `Вывести ${gift.title} на ваш аккаунт Telegram?`
    const confirmed = tg?.showConfirm
      ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
      : window.confirm(confirmMessage)

    if (!confirmed) return

    try {
      const response = await fetch(`${apiUrl}/api/withdraw-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, name: gift.slug, index: 0 })
      })

      const data = await response.json()

      if (data.success) {
        if (tg?.showAlert) tg.showAlert('✅ Подарок успешно отправлен!')
        else alert('✅ Подарок успешно отправлен!')

        loadInventory()
        setShowGiftDetails(false)
      } else {
        setErrorData({
          gift: gift,
          error: data.error || data.message || 'Ошибка вывода',
          type: 'regular'
        })
        setShowErrorModal(true)
      }
    } catch (error) {
      console.error('Withdraw error:', error)
      setErrorData({
        gift: gift,
        error: 'Ошибка соединения с сервером',
        type: 'regular'
      })
      setShowErrorModal(true)
    }
  }

  const handleWithdrawNFT = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || ''

    const confirmMessage = `Вывести ${gift.title} на ваш аккаунт Telegram?`
    const confirmed = tg?.showConfirm
      ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
      : window.confirm(confirmMessage)

    if (!confirmed) return

    try {
      const response = await fetch(`${apiUrl}/api/withdraw-nft-gift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          slug: gift.slug,
          messageId: gift.message_id
        })
      })

      const data = await response.json()

      if (data.success) {
        if (tg?.showAlert) tg.showAlert('✅ Подарок успешно отправлен!')
        else alert('✅ Подарок успешно отправлен!')

        loadInventory()
        setShowGiftDetails(false)
      } else if (
        data.requires_payment === true ||
        data.requires_payment === 'true' ||
        data.requires_payment ||
        (data.message && typeof data.message === 'string' && data.message.includes("Required fee:"))
      ) {
        // Show Payment Modal
        setPaymentData({
          ...data.payment_data,
          originalGift: gift // Save gift object to retry withdrawal
        })
        setShowPaymentModal(true)
        setShowGiftDetails(false) // Close details modal
      } else {
        setErrorData({
          gift: gift,
          error: data.error || data.message || 'Ошибка вывода NFT',
          type: 'nft',
          lottieSrc: `https://nft.fragment.com/gift/${gift.slug}.lottie.json`,
          title: 'Ошибка отправки'
        })
        setShowErrorModal(true)
      }
    } catch (error) {
      setErrorData({
        gift: gift,
        error: 'Ошибка соединения с сервером',
        type: 'nft'
      })
      setShowErrorModal(true)
    }
  }

  /* New logic for Retry */
  const handleRetry = () => {
    setShowErrorModal(false)
    if (errorData?.type === 'regular') handleWithdrawRegular(errorData.gift)
    else if (errorData?.type === 'nft') handleWithdrawNFT(errorData.gift)
  }

  const handleManualAdminWithdraw = async () => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || ''

    if (!errorData || !errorData.gift) return

    try {
      const isNFT = errorData.type === 'nft'
      const endpoint = isNFT
        ? `${apiUrl}/api/inventory/manual-withdraw-nft`
        : `${apiUrl}/api/inventory/manual-withdraw`

      const body = isNFT
        ? {
          initData,
          slug: errorData.gift.slug,
          giftTitle: errorData.gift.title,
          messageId: errorData.gift.message_id,
          error: errorData.error
        }
        : {
          initData,
          slug: errorData.gift.slug,
          giftTitle: errorData.gift.title,
          error: errorData.error
        }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      const data = await response.json()

      setShowErrorModal(false)

      if (data.success) {
        if (tg?.showAlert) tg.showAlert('✅ Заявка отправлена администрации!')
        else alert('✅ Заявка отправлена администрации!')
        loadInventory()
        setShowGiftDetails(false)
      } else {
        if (tg?.showAlert) tg.showAlert(data.message || 'Ошибка отправки заявки')
        else alert(data.message || 'Ошибка отправки заявки')
      }
    } catch (error) {
      console.error('Manual withdraw error:', error)
      const tg = window.Telegram?.WebApp
      if (tg?.showAlert) tg.showAlert('Ошибка соединения с сервером')
    }
  }

  const handleSellRegular = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || ''

    try {
      // sell_price уже есть в gift из inventory
      const sellPrice = gift.sell_price
      if (!sellPrice || sellPrice <= 0) {
        tg?.showAlert('Цена продажи не установлена')
        return
      }

      const confirmMessage = `Продать ${gift.title} за ${sellPrice} ⭐?`
      const confirmed = tg?.showConfirm
        ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
        : window.confirm(confirmMessage)

      if (!confirmed) return

      const sellResponse = await fetch(`${apiUrl}/api/inventory/sell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug: gift.slug })
      })

      const sellData = await sellResponse.json()

      if (sellData.success) {
        tg?.showAlert(`✅ Подарок продан!`)
        loadInventory()
        setShowGiftDetails(false)
      } else {
        tg?.showAlert(sellData.message || sellData.detail || 'Не удалось продать подарок')
      }
    } catch (error) {
      console.error('Sell error:', error)
      tg?.showAlert('Ошибка соединения с сервером')
    }
  }

  const handleSellNFT = async (gift) => {
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData
    const apiUrl = import.meta.env.VITE_API_URL || ''

    // Confirmation
    const price = gift.sell_price || '?'
    const confirmMessage = `Вы уверены, что хотите продать NFT ${gift.title} за ${price} ⭐?`
    const confirmed = tg?.showConfirm
      ? await new Promise(resolve => tg.showConfirm(confirmMessage, resolve))
      : window.confirm(confirmMessage)

    if (!confirmed) return

    try {
      const response = await fetch(`${apiUrl}/api/inventory/sell-nft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, slug: gift.slug })
      })

      const data = await response.json()

      if (data.success) {
        if (tg?.showAlert) {
          tg.showAlert(`✅ NFT продан за ${data.sellPrice} ⭐`)
        } else {
          alert(`✅ NFT продан за ${data.sellPrice} ⭐`)
        }
        loadInventory()
        setShowGiftDetails(false)
      } else {
        if (tg?.showAlert) {
          tg.showAlert(data.message || 'Не удалось продать NFT')
        } else {
          alert(data.message || 'Не удалось продать NFT')
        }
      }
    } catch (error) {
      console.error('Sell NFT error:', error)
      if (tg?.showAlert) {
        tg.showAlert('Ошибка соединения с сервером')
      } else {
        alert('Ошибка соединения с сервером')
      }
    }
  }

  const isMobile = window.Telegram?.WebApp?.platform === 'android' ||
    window.Telegram?.WebApp?.platform === 'ios'

  const tg = window.Telegram?.WebApp
  const safeAreaTopValue = tg?.safeAreaInset?.top || tg?.contentSafeAreaInset?.top || 0
  const contentPadding = isMobile ? (safeAreaTopValue + 20) : 5

  const handleCopyId = async () => {
    const userId = user?.id
    if (userId) {
      try {
        await navigator.clipboard.writeText(userId.toString())
        const tg = window.Telegram?.WebApp
        if (tg?.showPopup) {
          tg.showPopup({
            message: 'ID скопирован в буфер обмена'
          })
        } else {
          alert('ID скопирован в буфер обмена')
        }
      } catch (err) {
        console.error('Ошибка копирования:', err)
        alert('Не удалось скопировать ID')
      }
    }
  }

  return (
    <div className="profile-page">
      {/* Header Card */}
      <div className="profile-header-card">
        {getAvatarUrl() ? (
          <img src={getAvatarUrl()} alt="Avatar" className="profile-header-avatar" />
        ) : (
          <div className="profile-header-avatar-placeholder">
            {getInitials()}
          </div>
        )}
        <div className="profile-header-info">
          <h2 className="profile-header-name">
            {user?.first_name} {user?.last_name}
          </h2>
          <p className="profile-header-id" onClick={handleCopyId}>
            ID: {user?.id || 'N/A'}
          </p>
        </div>
      </div>

      {/* Profile Tabs */}
      <div className="profile-tabs-container">
        <div className="profile-tabs">
          <div
            className="profile-tab-indicator"
            style={{
              left: activeProfileTab === 'inventory' ? '3px' : 'calc(50%)',
              width: 'calc(50% - 3px)'
            }}
          />
          <label className="profile-tab-label">
            <input
              type="radio"
              name="profile-tab"
              value="inventory"
              checked={activeProfileTab === 'inventory'}
              onChange={(e) => setActiveProfileTab(e.target.value)}
            />
            <span>Инвентарь</span>
          </label>

          <label className="profile-tab-label">
            <input
              type="radio"
              name="profile-tab"
              value="admin"
              checked={activeProfileTab === 'admin'}
              onChange={(e) => setActiveProfileTab(e.target.value)}
            />
            <span>Прочее</span>
          </label>
        </div>
      </div>

      <div className="profile-content">
        {/* Прочее */}
        <div className="profile-other-section" style={{ display: activeProfileTab === 'admin' ? 'block' : 'none' }}>
          <div className="profile-actions">
            <button className="action-button" onClick={() => setShowPromoCodeModal(true)}>
              <img src={giftIcon} alt="promo" className="button-icon-img" />
              <span className="button-text">Промокод</span>
            </button>

            <button className="action-button" onClick={() => {
              const tg = window.Telegram?.WebApp
              if (tg && tg.openTelegramLink) {
                tg.openTelegramLink('https://t.me/helpshellbot')
              } else {
                window.open('https://t.me/helpshellbot', '_blank')
              }
            }}>
              <img src={supIcon} alt="support" className="button-icon-img" />
              <span className="button-text">Поддержка</span>
            </button>

            {!loading && isAdmin && (
              <>
                <button className="action-button admin-button" onClick={() => setShowAdminPanel(true)}>
                  <span className="button-icon">👑</span>
                  <span className="button-text">Админ панель</span>
                </button>
                <button className="action-button admin-button" onClick={() => setShowSafeArea(!showSafeArea)}>
                  <span className="button-icon">📐</span>
                  <span className="button-text">{showSafeArea ? 'Скрыть' : 'Показать'} Safe Area</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Инвентарь */}
        <div className="profile-inventory-section" style={{ display: activeProfileTab === 'inventory' ? 'block' : 'none' }}>
          {inventoryLoading ? (
            <div className="inventory-loading">Загрузка...</div>
          ) : inventory.length === 0 ? (
            <div className="inventory-empty">Ваш инвентарь пуст</div>
          ) : (
            <div className="inventory-grid" ref={gridRef}>
              {inventory.map((gift, index) => {
                const isNFT = gift.collectible_id !== undefined
                const isRegular = gift.is_regular_gift === true

                return (
                  <div
                    key={index}
                    className={isRegular ? "gift-card-inventory-regular" : "gift-card-inventory"}
                    style={{
                      background: gift.center_color && gift.edge_color
                        ? `linear-gradient(135deg, ${gift.center_color} 0%, ${gift.edge_color} 100%)`
                        : 'radial-gradient(circle, #363738, #0e0f0f)'
                    }}
                    onClick={() => handleViewGift(gift)}
                  >
                    {/* Static images only - NO Lottie */}
                    <div className="gift-image-wrapper" style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      position: isRegular ? 'relative' : 'absolute',
                      top: 0,
                      left: 0,
                      zIndex: 0
                    }}>
                      <img
                        src={isRegular
                          ? `https://shelloch.xyz/gifts/${gift.slug}.png`
                          : `https://nft.fragment.com/gift/${gift.slug || gift.name}.large.jpg`
                        }
                        alt={gift.title || gift.name}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: isRegular ? 'contain' : 'cover',
                          borderRadius: isRegular ? 0 : '20px'
                        }}
                        loading="lazy"
                      />
                    </div>

                    {isNFT && !isRegular && (
                      <div className="nft-badge" style={{ position: 'relative', zIndex: 1 }}>
                        <span className="nft-id">#{gift.collectible_id}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {showAdminPanel && isAdmin && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowAdminPanel(false)} />
          <div className="overlay-sheet admin-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowAdminPanel(false)}>✕</button>

            <div className="sheet-content">
              <h2 className="admin-panel-title">Админ панель</h2>

              <div className="admin-input-group">
                <label className="admin-label">User ID</label>
                <input
                  type="number"
                  className="admin-input"
                  placeholder="Введите ID пользователя"
                  value={targetUserId}
                  onChange={(e) => setTargetUserId(e.target.value)}
                  disabled={actionLoading}
                />
              </div>

              <div className="admin-buttons">
                <button
                  className="admin-action-button ban-button"
                  onClick={handleBanUser}
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Загрузка...' : 'Забанить'}
                </button>
                <button
                  className="admin-action-button unban-button"
                  onClick={handleUnbanUser}
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Загрузка...' : 'Разбанить'}
                </button>
              </div>

              <div className="admin-divider"></div>

              <button
                className="admin-chances-button"
                onClick={() => {
                  loadChances(selectedSpinMode);
                  setShowChancesPanel(true);
                }}
                disabled={actionLoading}
              >
                <span className="button-icon">🎲</span>
                <span className="button-text">Шансы</span>
              </button>

              <div className="admin-divider"></div>

              <button
                className="admin-chances-button refund-panel-button"
                onClick={() => setShowRefundPanel(true)}
                disabled={actionLoading}
              >
                <span className="button-icon">💰</span>
                <span className="button-text">Возврат</span>
              </button>

              <div className="admin-divider"></div>

              <div className="admin-button-row">
                <button
                  className="admin-chances-button crash-panel-button half-width"
                  onClick={() => {
                    loadCrashSettings();
                    setShowCrashPanel(true);
                  }}
                  disabled={actionLoading}
                >
                  <span className="button-icon">🚀</span>
                  <span className="button-text">Краш</span>
                </button>

                <button
                  className="admin-chances-button crash-panel-button half-width"
                  onClick={() => {
                    loadTasks();
                    setShowTasksPanel(true);
                  }}
                  disabled={actionLoading}
                >
                  <span className="button-icon">📋</span>
                  <span className="button-text">Задания</span>
                </button>
              </div>

              <div className="admin-divider"></div>

              <button
                className="admin-chances-button settings-panel-button"
                onClick={() => setShowSettingsPanel(true)}
                disabled={actionLoading}
              >
                <span className="button-icon">⚙️</span>
                <span className="button-text">Настройки</span>
              </button>
            </div>
          </div>
        </>
      )}

      {showChancesPanel && isAdmin && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowChancesPanel(false)} />
          <div className="overlay-sheet admin-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowChancesPanel(false)}>✕</button>

            <div className="sheet-content">

              {adminView === 'list' && (
                <>
                  <h2 className="admin-panel-title">Управление кейсами</h2>
                  <div className="admin-actions-header">
                    <button className="admin-action-button add-case-button" onClick={() => setIsAddingCase(true)}>+ Новый кейс</button>
                  </div>

                  {isAddingCase && (
                    <div className="modal-overlay">
                      <div className="modal-content add-case-modal">
                        <div className="modal-header">
                          <h3>Создание Кейса</h3>
                          <button className="modal-close" onClick={() => setIsAddingCase(false)}>✕</button>
                        </div>
                        <div className="add-case-form-body">
                          <div className="input-group">
                            <label>Slug (уникальный ID)</label>
                            <input className="admin-input" placeholder="mega_case_1" value={newCaseData.slug} onChange={e => setNewCaseData({ ...newCaseData, slug: e.target.value })} />
                          </div>
                          <div className="input-group">
                            <label>Название (для пользователей)</label>
                            <input className="admin-input" placeholder="Мега Кейс" value={newCaseData.title} onChange={e => setNewCaseData({ ...newCaseData, title: e.target.value })} />
                          </div>
                          <div className="inputs-row-2">
                            <div className="input-group">
                              <label>Цена</label>
                              <input className="admin-input" type="number" placeholder="0" value={newCaseData.price} onChange={e => setNewCaseData({ ...newCaseData, price: e.target.value })} />
                            </div>
                            <div className="input-group">
                              <label>Валюта</label>
                              <select className="admin-input" value={newCaseData.currency} onChange={e => setNewCaseData({ ...newCaseData, currency: e.target.value })}>
                                <option value="star">Stars ⭐️</option>
                                <option value="paw">Paws 🐾</option>
                              </select>
                            </div>
                          </div>
                          <div className="inputs-row-2">
                            <div className="input-group">
                              <label>Лимит прокрутов (-1 = ∞)</label>
                              <input className="admin-input" type="number" placeholder="-1" value={newCaseData.spinLimit} onChange={e => setNewCaseData({ ...newCaseData, spinLimit: e.target.value })} />
                            </div>
                            <div className="input-group">
                              <label>Иконка (.svg)</label>
                              <input type="file" className="admin-input" accept=".svg" onChange={e => setNewCaseIcon(e.target.files[0])} />
                            </div>
                          </div>
                          <div className="modal-actions">
                            <button className="admin-action-button" onClick={handleCreateCase} disabled={actionLoading}>Создать Кейс</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="cases-list-admin">
                    {cases.map(item => (
                      <div key={item.slug} className="case-item-admin">
                        <div className="case-header">
                          <div className="case-header-left">
                            <span className="case-slug-badge">{item.slug}</span>
                            {item.spinLimit > -1 && (
                              <span className="case-limit-badge">
                                {item.spinsCount || 0} / {item.spinLimit}
                              </span>
                            )}
                          </div>
                          <div className="case-header-right">
                            <label className="toggle-switch small">
                              <input
                                type="checkbox"
                                checked={item.isActive}
                                onChange={() => handleToggleCaseActive(item)}
                              />
                              <span className="toggle-slider"></span>
                            </label>

                            <span className="case-currency-badge">{item.currency}</span>
                            {!item.isDefault && (
                              <button className="delete-case-btn" onClick={() => handleDeleteCase(item.slug)}>🗑️</button>
                            )}
                          </div>
                        </div>
                        <div className="case-inputs-row">
                          <div className="admin-input-group compact" style={{ flex: 2 }}>
                            <label>Название</label>
                            <input
                              className="admin-input"
                              defaultValue={item.title}
                              onBlur={(e) => handleUpdateCase(item.slug, e.target.value, item.price, item.spinLimit)}
                            />
                          </div>
                          <div className="admin-input-group compact" style={{ flex: 1 }}>
                            <label>Цена</label>
                            <input
                              className="admin-input"
                              type="number"
                              defaultValue={item.price}
                              onBlur={(e) => handleUpdateCase(item.slug, item.title, e.target.value, item.spinLimit)}
                            />
                          </div>
                          <div className="admin-input-group compact" style={{ flex: 1 }}>
                            <label>Лимит</label>
                            <input
                              className="admin-input"
                              type="number"
                              defaultValue={item.spinLimit}
                              onBlur={(e) => handleUpdateCase(item.slug, item.title, item.price, e.target.value)}
                            />
                          </div>

                          {/* Moved Actions Here */}
                          <div className="case-actions-inline" style={{ display: 'flex', gap: '5px', alignItems: 'flex-end' }}>
                            <button
                              className="admin-action-button secondary-btn small-btn"
                              title="Шансы"
                              onClick={() => {
                                setSelectedSpinMode(item.slug);
                                setAdminView('chances');
                                loadChances(item.slug);
                              }}>
                              🎲
                            </button>
                            <button
                              className="admin-action-button secondary-btn small-btn"
                              title="Наполнение"
                              onClick={() => {
                                setSelectedSpinMode(item.slug);
                                setAdminView('gifts');
                                loadCaseGifts(item.slug);
                              }}>
                              🎁
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {adminView === 'chances' && (
                <>
                  <div className="panel-header-row">
                    <button className="back-btn" onClick={() => setAdminView('list')}>← Назад</button>
                    <h2 className="admin-panel-title">Шансы: {cases.find(c => c.slug === selectedSpinMode)?.title}</h2>
                  </div>

                  <div className="chances-list">
                    {chances.map(chance => (
                      <div key={chance.name} className="chance-item">
                        <div className="chance-info">
                          <div className="gift-icon-preview">
                            <img
                              src={chance.name === 'secret' ? secretIcon : `/gifts/${chance.name}.png`}
                              onError={(e) => e.target.src = giftIcon}
                              alt={chance.name}
                            />
                          </div>
                          <div className="chance-details">
                            <span className="chance-name">{chance.name}</span>
                            <div className="chance-values">
                              {editingGift === chance.name ? (
                                <>
                                  <input
                                    id={`visible-${chance.name}`}
                                    className="chance-input"
                                    type="number"
                                    defaultValue={chance.visible} // Отображаемый %
                                    step="0.01"
                                    placeholder="Vis%"
                                  />
                                  <input
                                    id={`real-${chance.name}`}
                                    className="chance-input"
                                    type="number"
                                    defaultValue={chance.real} // Реальный %
                                    step="0.001"
                                    placeholder="Real%"
                                  />
                                </>
                              ) : (
                                <span>Vis: {chance.visible}% | Real: {chance.real}%</span>
                              )}
                            </div>

                            {/* Диапазоны для валют */}
                            {chance.name === 'paw' && (
                              <div className="chance-row">
                                <span className="chance-label">Лапок (диапазон):</span>
                                {editingGift === chance.name ? (
                                  <div className="paw-range-inputs">
                                    <input
                                      type="number"
                                      className="chance-input paw-range-input"
                                      defaultValue={chance.pawMin || 0}
                                      id={`pawMin-${chance.name}`}
                                      min="0"
                                      max="100"
                                      placeholder="От"
                                      disabled={actionLoading}
                                    />
                                    <span className="range-separator">-</span>
                                    <input
                                      type="number"
                                      className="chance-input paw-range-input"
                                      defaultValue={chance.pawMax || 5}
                                      id={`pawMax-${chance.name}`}
                                      min="0"
                                      max="100"
                                      placeholder="До"
                                      disabled={actionLoading}
                                    />
                                  </div>
                                ) : (
                                  <span className="chance-value">{chance.pawMin || 0}-{chance.pawMax || 0}</span>
                                )}
                              </div>
                            )}
                            {chance.name === 'star' && (
                              <div className="chance-row">
                                <span className="chance-label">Звезд (диапазон):</span>
                                {editingGift === chance.name ? (
                                  <div className="paw-range-inputs">
                                    <input
                                      type="number"
                                      className="chance-input paw-range-input"
                                      defaultValue={chance.starMin || 1}
                                      id={`starMin-${chance.name}`}
                                      min="1"
                                      max="100"
                                      placeholder="От"
                                      disabled={actionLoading}
                                    />
                                    <span className="range-separator">-</span>
                                    <input
                                      type="number"
                                      className="chance-input paw-range-input"
                                      defaultValue={chance.starMax || 5}
                                      id={`starMax-${chance.name}`}
                                      min="1"
                                      max="100"
                                      placeholder="До"
                                      disabled={actionLoading}
                                    />
                                  </div>
                                ) : (
                                  <span className="chance-value">{chance.starMin || 1}-{chance.starMax || 5}</span>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="chance-actions">
                            {editingGift === chance.name ? (
                              <>
                                <button
                                  className="chance-btn save-btn"
                                  onClick={() => {
                                    const visible = parseFloat(document.getElementById(`visible-${chance.name}`).value)
                                    const real = parseFloat(document.getElementById(`real-${chance.name}`).value)
                                    let pawMin = 0, pawMax = 0, starMin = 1, starMax = 5
                                    if (chance.name === 'paw') {
                                      pawMin = parseInt(document.getElementById(`pawMin-${chance.name}`).value) || 0
                                      pawMax = parseInt(document.getElementById(`pawMax-${chance.name}`).value) || 0
                                    }
                                    if (chance.name === 'star') {
                                      starMin = parseInt(document.getElementById(`starMin-${chance.name}`).value) || 1
                                      starMax = parseInt(document.getElementById(`starMax-${chance.name}`).value) || 5
                                    }
                                    handleUpdateChance(chance.name, visible, real, selectedSpinMode, pawMin, pawMax, starMin, starMax)
                                  }}
                                  disabled={actionLoading}
                                >
                                  ✓
                                </button>
                                <button
                                  className="chance-btn cancel-btn"
                                  onClick={() => setEditingGift(null)}
                                  disabled={actionLoading}
                                >
                                  ✕
                                </button>
                              </>
                            ) : (
                              <button
                                className="chance-btn edit-btn"
                                onClick={() => setEditingGift(chance.name)}
                              >
                                ✎
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {adminView === 'gifts' && (
                <>
                  <div className="panel-header-row">
                    <button className="back-btn" onClick={() => setAdminView('list')}>← Назад</button>
                    <h2 className="admin-panel-title">Наполнение: {cases.find(c => c.slug === selectedSpinMode)?.title}</h2>
                  </div>

                  <div className="gifts-toggle-list">
                    {caseGifts.map(gift => (
                      <div key={gift.name} className="gift-toggle-item">
                        <div className="gift-toggle-info">
                          <img src={`/gifts/${gift.name}.png`} onError={(e) => e.target.src = giftIcon} alt={gift.name} className="mini-gift-icon" />
                          <span className="gift-name">{gift.name}</span>
                          {gift.type === 'currency' && <span className="currency-badge">Val</span>}
                        </div>
                        <label className="toggle-switch small">
                          <input
                            type="checkbox"
                            checked={gift.enabled}
                            onChange={(e) => handleToggleCaseGift(selectedSpinMode, gift.name, e.target.checked)}
                          />
                          <span className="toggle-slider"></span>
                        </label>
                      </div>
                    ))}
                  </div>
                </>
              )}

            </div>
          </div>
        </>
      )}

      {showRefundPanel && isAdmin && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowRefundPanel(false)} />
          <div className="overlay-sheet refund-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowRefundPanel(false)}>✕</button>

            <div className="sheet-content">
              <h2 className="admin-panel-title">Возврат платежа</h2>

              <div className="admin-input-group">
                <label className="admin-label">User ID</label>
                <input
                  type="number"
                  className="admin-input"
                  placeholder="ID пользователя"
                  value={refundUserId}
                  onChange={(e) => setRefundUserId(e.target.value)}
                  disabled={refundLoading}
                />
              </div>

              <div className="admin-input-group">
                <label className="admin-label">Transaction ID</label>
                <input
                  type="text"
                  className="admin-input"
                  placeholder="Telegram Payment Charge ID"
                  value={refundTransactionId}
                  onChange={(e) => setRefundTransactionId(e.target.value)}
                  disabled={refundLoading}
                />
              </div>

              <div className="admin-toggle-group">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    className="toggle-checkbox"
                    checked={deductFromBalance}
                    onChange={(e) => setDeductFromBalance(e.target.checked)}
                    disabled={refundLoading}
                  />
                  <span className="toggle-slider"></span>
                  <span className="toggle-text">Списать с баланса</span>
                </label>
                {deductFromBalance && (
                  <p className="toggle-hint">⚠️ Баланс может уйти в минус</p>
                )}
              </div>

              <button
                className="admin-action-button refund-button"
                onClick={handleRefund}
                disabled={refundLoading || !refundUserId || !refundTransactionId}
              >
                {refundLoading ? 'Загрузка...' : 'Вернуть'}
              </button>
            </div>
          </div>
        </>
      )}

      {showCrashPanel && isAdmin && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowCrashPanel(false)} />
          <div className="overlay-sheet crash-settings-panel">
            <button className="close-panel-btn" onClick={() => setShowCrashPanel(false)}>✕</button>

            <div className="sheet-content">
              <h2 className="admin-panel-title">Настройки краш-игры</h2>

              {crashState && (
                <div className="crash-game-info">
                  <div className="crash-info-card">
                    <div className="crash-info-label">Статус игры</div>
                    <div className="crash-info-value">
                      {crashState.crashed && '💥 CRASHED!'}
                      {!crashState.crashed && !crashState.isRunning && '⏳ Ожидание'}
                      {!crashState.crashed && crashState.isRunning && '🚀 В полете'}
                    </div>
                  </div>

                  {crashState.isRunning && !crashState.crashed && (
                    <div className="crash-info-card highlight">
                      <div className="crash-info-label">Текущий коэффициент</div>
                      <div className="crash-info-value multiplier">
                        {crashState.currentMultiplier.toFixed(2)}x
                      </div>
                    </div>
                  )}

                  {crashState.crashed && crashState.crashedAt && (
                    <div className="crash-info-card crashed">
                      <div className="crash-info-label">Взорвалась на</div>
                      <div className="crash-info-value multiplier crashed-mult">
                        {crashState.crashedAt.toFixed(2)}x
                      </div>
                    </div>
                  )}

                  <div className="crash-info-card">
                    <div className="crash-info-label">Активных ставок</div>
                    <div className="crash-info-value">
                      {crashState.betsCount || 0}
                    </div>
                  </div>
                </div>
              )}

              {crashState?.isRunning && !crashState?.crashed && (
                <button
                  className="admin-action-button explode-button"
                  onClick={handleExplode}
                  disabled={exploding}
                >
                  {exploding ? 'Взрываем...' : '💥 Взорвать сейчас'}
                </button>
              )}

              <div className="admin-divider"></div>

              <div className="admin-toggle-group">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    className="toggle-checkbox"
                    checked={crashAlwaysProfit}
                    onChange={(e) => setCrashAlwaysProfit(e.target.checked)}
                    disabled={actionLoading}
                  />
                  <span className="toggle-slider"></span>
                  <span className="toggle-text">💰 Всегда в плюсе</span>
                </label>
                {crashAlwaysProfit && (
                  <>
                    <p className="toggle-hint">Система будет компенсировать выигрыши низкими крашами</p>
                    <div className="admin-input-group" style={{ marginTop: '10px' }}>
                      <label className="admin-label">Порог долга (⭐)</label>
                      <input
                        type="number"
                        className="admin-input"
                        placeholder="300"
                        value={crashMaxDebt}
                        onChange={(e) => setCrashMaxDebt(e.target.value)}
                        disabled={actionLoading}
                        min="50"
                        max="10000"
                      />
                    </div>
                    <div className="admin-input-group" style={{ marginTop: '10px' }}>
                      <label className="admin-label">Порог большой ставки (⭐)</label>
                      <input
                        type="number"
                        className="admin-input"
                        placeholder="100"
                        value={crashBigBetThreshold}
                        onChange={(e) => setCrashBigBetThreshold(e.target.value)}
                        disabled={actionLoading}
                        min="10"
                        max="10000"
                      />
                    </div>
                    <div className="admin-input-group" style={{ marginTop: '10px' }}>
                      <label className="admin-label">Шанс проигрыша на большой ставке (%)</label>
                      <input
                        type="number"
                        className="admin-input"
                        placeholder="30"
                        value={crashBigBetLoseChance}
                        onChange={(e) => setCrashBigBetLoseChance(e.target.value)}
                        disabled={actionLoading}
                        min="0"
                        max="100"
                      />
                      <p className="input-hint">
                        При ставках ≥{crashBigBetThreshold}⭐ - {crashBigBetLoseChance}% шанс раннего краша
                      </p>
                    </div>
                  </>
                )}
              </div>

              <div className="admin-divider"></div>

              <div className="admin-input-group">
                <label className="admin-label">Максимальный коэффициент</label>
                <input
                  type="number"
                  className="admin-input"
                  placeholder="От 2 до 100000"
                  value={crashMaxMultiplier}
                  onChange={(e) => setCrashMaxMultiplier(e.target.value)}
                  disabled={actionLoading}
                  min="2"
                  max="100000"
                  step="0.1"
                />
                <p className="input-hint">
                  Определяет максимальный множитель, который может выпасть в краш-игре (1% шанс на диапазон 50x - max)
                </p>
              </div>

              <button
                className="admin-action-button save-button"
                onClick={handleUpdateCrashSettings}
                disabled={actionLoading}
              >
                {actionLoading ? 'Загрузка...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </>
      )}

      {showTasksPanel && isAdmin && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowTasksPanel(false)} />
          <div className="overlay-sheet tasks-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowTasksPanel(false)}>✕</button>

            <div className="sheet-content">
              <h2 className="admin-panel-title">Управление заданиями</h2>

              {!showAddTaskForm ? (
                <>
                  <button
                    className="admin-action-button add-task-button"
                    onClick={() => setShowAddTaskForm(true)}
                    disabled={actionLoading || tasksLoading}
                  >
                    + Добавить задание
                  </button>

                  {tasksLoading ? (
                    <div className="tasks-loading">Загрузка...</div>
                  ) : tasks.length === 0 ? (
                    <div className="tasks-empty">Нет заданий</div>
                  ) : (
                    <div className="tasks-list-admin">
                      {tasks.map(task => (
                        <div key={task.id} className="task-item-admin">
                          <div className="task-item-header">
                            <span className="task-type-badge">{getTaskTypeLabel(task.type)}</span>
                            <button
                              className="task-delete-btn"
                              onClick={() => handleDeleteTask(task.id)}
                              disabled={actionLoading}
                            >
                              Удалить
                            </button>
                          </div>
                          <div className="task-item-target">{task.target}</div>
                          {task.execution_limit && (
                            <div className="task-item-limit" style={{ fontSize: '12px', color: '#aaa', marginTop: '4px' }}>
                              Лимит: {task.completions_count || 0} / {task.execution_limit}
                            </div>
                          )}
                          <div className="task-item-reward">
                            Награда: {task.award} {task.currency === 'paws' ? (
                              <>
                                <span style={{ display: 'inline-flex', alignItems: 'center', width: '20px', height: '20px' }}>
                                  <LottieAnimation animationData={pawAnim} width={20} height={20} />
                                </span>
                                <span>Paws</span>
                              </>
                            ) : task.currency === 'star' ? (
                              <>
                                <span style={{ display: 'inline-flex', alignItems: 'center', width: '20px', height: '20px' }}>
                                  <LottieAnimation animationData={starAnim} width={20} height={20} />
                                </span>
                                <span>Stars</span>
                              </>
                            ) : (
                              <span>{task.currency}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="add-task-form">
                  <div className="admin-input-group">
                    <label className="admin-label">Тип задания</label>
                    <select
                      className="admin-input admin-select"
                      value={taskType}
                      onChange={(e) => handleTaskTypeChange(e.target.value)}
                      disabled={actionLoading}
                    >
                      <option value="subscribe">Подписка на публичный канал</option>
                      <option value="private_channel">Подписка на частный канал</option>
                      <option value="open_url">Открыть ссылку</option>
                    </select>
                  </div>

                  <div className="admin-input-group">
                    <label className="admin-label">
                      {taskType === 'private_channel' ? 'ID канала (например: -1002531573202)' : 'Цель (ссылка/username канала)'}
                    </label>
                    <input
                      type="text"
                      className="admin-input"
                      placeholder={taskType === 'private_channel' ? '-1002531573202' : '@channel или https://t.me/channel'}
                      value={taskTarget}
                      onChange={(e) => handleTaskTargetChange(e.target.value)}
                      onBlur={checkBotPermissions}
                      disabled={actionLoading}
                    />
                    {botPermissionStatus && (
                      <p className={`bot-permission-status ${botPermissionStatus.includes('❌') ? 'error' : 'success'}`}>
                        {botPermissionStatus}
                      </p>
                    )}
                  </div>

                  <div className="admin-input-group">
                    <label className="admin-label">Награда</label>
                    <input
                      type="number"
                      className="admin-input"
                      placeholder="Количество"
                      value={taskAward}
                      onChange={(e) => setTaskAward(e.target.value)}
                      disabled={actionLoading}
                      min="1"
                    />
                  </div>

                  <div className="admin-input-group">
                    <label className="admin-label">Валюта</label>
                    <select
                      className="admin-input admin-select"
                      value={taskCurrency}
                      onChange={(e) => setTaskCurrency(e.target.value)}
                      disabled={actionLoading}
                    >
                      <option value="paws">🐾 Paws</option>
                      <option value="star">⭐ Stars</option>
                    </select>
                  </div>

                  <div className="admin-input-group">
                    <label className="admin-label">Лимит выполнений (необязательно)</label>
                    <input
                      type="number"
                      className="admin-input"
                      placeholder="Без лимита"
                      value={taskLimit}
                      onChange={(e) => setTaskLimit(e.target.value)}
                      disabled={actionLoading}
                      min="1"
                    />
                  </div>

                  {taskType === 'private_channel' && (
                    <>
                      <div className="admin-input-group">
                        <label className="admin-label checkbox-label">
                          <input
                            type="checkbox"
                            checked={useCustomInvite}
                            onChange={(e) => setUseCustomInvite(e.target.checked)}
                            disabled={actionLoading}
                          />
                          <span>Своя invite ссылка</span>
                        </label>
                      </div>

                      {useCustomInvite && (
                        <div className="admin-input-group">
                          <label className="admin-label">Invite ссылка</label>
                          <input
                            type="text"
                            className="admin-input"
                            placeholder="https://t.me/+xxxxx"
                            value={customInviteLink}
                            onChange={(e) => setCustomInviteLink(e.target.value)}
                            disabled={actionLoading}
                          />
                        </div>
                      )}
                    </>
                  )}

                  <div className="form-actions-row">
                    <button
                      className="admin-action-button cancel-button"
                      onClick={() => {
                        setShowAddTaskForm(false)
                        setTaskTarget('')
                        setTaskType('subscribe')
                        setTaskAward('')
                        setTaskCurrency('paws')
                        setBotPermissionStatus('')
                        setUseCustomInvite(false)
                        setCustomInviteLink('')
                        setTaskLimit('')
                      }}
                      disabled={actionLoading}
                    >
                      Отмена
                    </button>
                    <button
                      className="admin-action-button save-button"
                      onClick={handleCreateTask}
                      disabled={actionLoading || checkingPermissions}
                    >
                      {actionLoading ? 'Создание...' : 'Создать'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {showSettingsPanel && isAdmin && (
        <>
          <div className="overlay-backdrop" onClick={() => setShowSettingsPanel(false)} />
          <div className="overlay-sheet settings-panel-sheet">
            <button className="close-panel-btn" onClick={() => setShowSettingsPanel(false)}>✕</button>

            <div className="sheet-content">
              <Settings />
            </div>
          </div>
        </>
      )}

      {/* Safe Area Визуализация */}
      {showSafeArea && (
        <div
          style={{
            position: 'fixed',
            top: `${safeAreaInset.top}px`,
            left: `${safeAreaInset.left}px`,
            right: `${safeAreaInset.right}px`,
            bottom: `${safeAreaInset.bottom}px`,
            border: '3px solid red',
            pointerEvents: 'none',
            zIndex: 9999,
            boxShadow: 'inset 0 0 0 1px yellow'
          }}
        >
          <div style={{
            position: 'absolute',
            top: '10px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(255, 0, 0, 0.8)',
            color: 'white',
            padding: '8px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            fontWeight: 'bold',
            pointerEvents: 'auto'
          }}>
            Safe Area: T:{safeAreaInset.top} B:{safeAreaInset.bottom} L:{safeAreaInset.left} R:{safeAreaInset.right}
          </div>
        </div>
      )}

      {/* Gift Details Modal */}
      {showGiftDetails && selectedGift && (
        <GiftDetailsModal
          gift={selectedGift}
          onClose={() => {
            setShowGiftDetails(false)
            setSelectedGift(null)
          }}
          onSell={selectedGift.is_regular_gift ? handleSellRegular : handleSellNFT}
          onWithdraw={selectedGift.is_regular_gift ? handleWithdrawRegular : handleWithdrawNFT}
          isInventory={true}
        />
      )}

      {/* Payment Modal */}
      <PaymentModal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        invoiceUrl={paymentData?.invoice_url}
        amount={paymentData?.amount}
        giftTitle={paymentData?.gift_title}
        giftSlug={paymentData?.gift_slug}
        onCheckPayment={async () => {
          if (paymentData?.originalGift) {
            await handleWithdrawNFT(paymentData.originalGift)
          }
        }}
        lottieSrc={paymentData?.originalGift ? `https://nft.fragment.com/gift/${paymentData.originalGift.slug}.lottie.json` : null}
      />

      {/* Action Status Modal for Errors */}
      <ActionStatusModal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title="Ошибка отправки"
        message={errorData?.error || 'Произошла ошибка'}
        actionButtonText="Повторить"
        onAction={handleRetry}
        secondaryButtonText="Вывод администрацией"
        onSecondaryAction={handleManualAdminWithdraw}
        helpText="Убедитесь что вы написали боту"
        helpLink="https://t.me/shellrelayer"
        isError={true}
      />

      {/* Модальное окно промокода */}
      <PromoCodeModal
        isOpen={showPromoCodeModal}
        onClose={() => setShowPromoCodeModal(false)}
      />
    </div>
  )
}

export default Profile
