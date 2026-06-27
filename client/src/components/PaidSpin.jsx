import { useState, useEffect, useRef, useMemo } from 'react'
import './Spin.css'
import LottieAnimation from './LottieAnimation'
import BalanceBar from './BalanceBar'
import BonusBalanceBar from './BonusBalanceBar'
import { useBalance } from '../contexts/BalanceContext'
import pawAnim from '../assets/paw.json'
import starAnim from '../assets/star.json'
import secretIcon from '../assets/secret.svg'

const gifts = [
  { name: 'bear', animation: '/gifts/bear.json' },
  { name: 'gift', animation: '/gifts/gift.json' },
  { name: 'heart', animation: '/gifts/heart.json' },
  { name: 'rose', animation: '/gifts/rose.json' },
  { name: 'paw', animation: pawAnim },
  { name: 'star', animation: starAnim },
  { name: 'secret', animation: null, icon: secretIcon }
]

const ITEM_WIDTH = 120
const GIFTS_COUNT = 7

import DemoSpinMenu from './DemoSpinMenu'

function PaidSpin({ onNavigateToTopUp }) {
  const { updateBalance } = useBalance()
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState(null)

  // Secret Result State
  const [secretResult, setSecretResult] = useState(null)

  const [pawAmount, setPawAmount] = useState(0)
  const [starAmount, setStarAmount] = useState(0)
  const [offset, setOffset] = useState(0)
  const [visibleCount, setVisibleCount] = useState(5)
  const [isProcessing, setIsProcessing] = useState(false)
  const [fastSpin, setFastSpin] = useState(false)

  // Demo Mode State
  const [isDemoMenuOpen, setDemoMenuOpen] = useState(false)
  const [isDemoMode, setDemoMode] = useState(false)
  const [demoSelectedGift, setDemoSelectedGift] = useState('')

  // Promik Logic
  const [promikCode, setPromikCode] = useState('')
  const [slug, setSlug] = useState('bazmin') // default

  // Fetch case info state
  const [caseInfo, setCaseInfo] = useState({ price: 0, currency: 'star' })

  // ... refs ...
  const viewportRef = useRef(null)
  const animationFrameRef = useRef(null)
  const targetOffsetRef = useRef(0)
  const startTimeRef = useRef(0)
  const durationRef = useRef(5000)
  const fastSpinRef = useRef(false)

  // Sync ref with state
  useEffect(() => {
    fastSpinRef.current = fastSpin
  }, [fastSpin])

  // Fetch Case Info
  useEffect(() => {
    const fetchCaseInfo = async () => {
      try {
        const tg = window.Telegram?.WebApp
        const initData = tg?.initData || ''
        const apiUrl = import.meta.env.VITE_API_URL || ''

        const res = await fetch(`${apiUrl}/api/game/case-info`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData, slug })
        })
        const data = await res.json()
        if (data.success) {
          setCaseInfo({
            price: data.price,
            currency: data.currency,
            secret_limit: data.secret_limit // Dynamic limit
          })
        }
      } catch (e) {
        console.error("Failed to fetch case info", e)
      }
    }

    if (slug) fetchCaseInfo()
  }, [slug])

  // -- SPIN LOGIC --
  const handleSpin = async () => {
    if (spinning || isProcessing) return

    // DEMO MODE CHECK
    if (isDemoMode) {
      if (!demoSelectedGift) {
        alert("Select a gift in Demo Menu first!")
        return
      }

      setSpinning(true)
      setResult(null)
      setSecretResult(null)
      setPawAmount(0)
      setStarAmount(0)
      setIsProcessing(true)

      // Simulate API success with selected gift
      const demoResult = {
        success: true,
        gift: demoSelectedGift,
        // Mock amounts for currencies if selected
        paw_count: demoSelectedGift === 'paw' ? 999 : 0,
        star_count: demoSelectedGift === 'star' ? 999 : 0,
        // Mock secret logic (RANDOM)
        is_secret: demoSelectedGift === 'secret',
        secret_slug: null,
        secret_name: null,
        balance: 999, // Fake balance
        bonus_balance: 999
      }

      if (demoSelectedGift === 'secret') {
        const mockSecrets = [
          { slug: 'blue-potion', name: 'Blue Potion' },
          { slug: 'red-energy', name: 'Red Energy' },
          { slug: 'nft-sword', name: 'NFT Sword' },
          { slug: 'gold-coin', name: 'Gold Coin' }
        ]
        const randomSecret = mockSecrets[Math.floor(Math.random() * mockSecrets.length)]
        demoResult.secret_slug = randomSecret.slug
        demoResult.secret_name = randomSecret.name
      }

      startSpinAnimation(demoResult)
      return
    }

    // REAL SPIN
    setSpinning(true)
    setResult(null)
    setSecretResult(null)
    setPawAmount(0)
    setStarAmount(0)
    setIsProcessing(true)

    try {
      const tg = window.Telegram?.WebApp
      const initData = tg?.initData || ''

      const res = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/game/spin-paid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          slug,
          promikCode: slug === 'promik' ? promikCode : undefined
        })
      })

      const data = await res.json()

      if (data.success) {
        if (data.balance !== undefined) {
          updateBalance(data.balance, data.bonus_balance)
        }
        startSpinAnimation(data)
      } else {
        alert(data.message || 'Error')
        setSpinning(false)
        setIsProcessing(false)
        if (data.needTopUp && onNavigateToTopUp) {
          onNavigateToTopUp()
        }
      }
    } catch (e) {
      console.error(e)
      setSpinning(false)
      setIsProcessing(false)
      alert('Network error')
    }
  }

  const startSpinAnimation = (data) => {
    // Determine target gift index
    const targetGiftName = data.gift
    let targetIndex = gifts.findIndex(g => g.name === targetGiftName)

    if (targetIndex === -1) {
      targetIndex = 0
    }

    const itemWidth = ITEM_WIDTH
    const giftsCount = GIFTS_COUNT
    const extraRounds = fastSpinRef.current ? 2 : 5 // Fast spin adjustment
    const totalDistance = (extraRounds * giftsCount * itemWidth) + (targetIndex * itemWidth)

    // Normalize current offset
    const currentOffset = offset % (giftsCount * itemWidth)
    const startOffset = currentOffset

    const finalOffset = startOffset + totalDistance

    // Randomize landing position within the item (center +/- jitter)
    const jitter = Math.random() * (itemWidth * 0.4) * (Math.random() > 0.5 ? 1 : -1)

    targetOffsetRef.current = finalOffset + jitter
    startTimeRef.current = 0 // Reset time
    durationRef.current = fastSpinRef.current ? 1500 : 5000 // Fast spin duration

    // Animation Loop
    const animate = (time) => {
      if (!startTimeRef.current) startTimeRef.current = time
      const elapsed = time - startTimeRef.current
      const progress = Math.min(elapsed / durationRef.current, 1)

      // Easing: easeOutCubic
      const ease = 1 - Math.pow(1 - progress, 3)

      const currentPos = startOffset + (targetOffsetRef.current - startOffset) * ease
      setOffset(currentPos)

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate)
      } else {
        // Finished
        // Handle Result Modal Logic
        if (data.paw_count) setPawAmount(data.paw_count)
        if (data.star_count) setStarAmount(data.star_count)
        // If promik, clear code
        if (slug === 'promik') setPromikCode('')

        // Handle Secret Result
        if (data.gift === 'secret' && data.secret_slug) {
          setSecretResult({
            slug: data.secret_slug,
            name: data.secret_name,
            is_secret: true
          })
        } else if (data.is_secret && data.secret_slug) { // support legacy/demo field names
          setSecretResult({
            slug: data.secret_slug,
            name: data.secret_name,
            is_secret: true
          })
        }

        // Show result (NAME string)
        setResult(data.gift)

        setSpinning(false)
        setIsProcessing(false)
      }
    }

    animationFrameRef.current = requestAnimationFrame(animate)
  }

  const visibleItems = useMemo(() => {
    const items = []
    const startIndex = Math.floor(offset / ITEM_WIDTH)
    for (let i = 0; i < visibleCount; i++) {
      const index = (startIndex + i) % GIFTS_COUNT
      items.push({ gift: gifts[index], position: (startIndex + i) * ITEM_WIDTH - offset, key: startIndex + i })
    }
    return items
  }, [offset, visibleCount])

  return (
    <div className="spin-container">
      {/* RENDER DEMO MENU */}
      <DemoSpinMenu
        isOpen={isDemoMenuOpen}
        onClose={() => setDemoMenuOpen(false)}
        isDemo={isDemoMode}
        onToggleDemo={setDemoMode}
        selectedGiftName={demoSelectedGift}
        onSelectGift={setDemoSelectedGift}
        availableGifts={gifts}
      />

      <div className="balance-container">
        <BalanceBar />
        {/* ATTACH CLICK HANDLER */}
        <BonusBalanceBar onClick={() => setDemoMenuOpen(true)} />
      </div>

      <div className="spin-content">
        <div className="roulette-container">
          <div className="roulette-viewport" ref={viewportRef}>
            <div className="roulette-pointer">▼</div>
            <div className="roulette-strip-virtual">
              {visibleItems.map((item) => (
                <div key={item.key} className="roulette-item" style={{ position: 'absolute', left: `${item.position}px`, width: `${ITEM_WIDTH}px` }}>
                  {item.gift.name === 'secret' ? (
                    <div className="secret-item-preview">
                      <img src={item.gift.icon} alt="Secret" className="secret-icon" style={{ width: '60px', height: '60px', marginBottom: '5px' }} />
                      <span className="secret-label">Secret</span>
                      <span className="secret-sublabel" style={{ fontSize: '10px', color: '#aaa' }}>
                        {caseInfo.secret_limit ? `Up to ${caseInfo.secret_limit} ⭐` : 'Up to ? ⭐'}
                      </span>
                    </div>
                  ) : (
                    <LottieAnimation animationData={item.gift.animation} width={80} height={80} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {result && (
          <div className="spin-result">
            <p>Вы выиграли:</p>
            <div className="result-gift-large" style={{ position: 'relative' }}>
              {result === 'secret' && secretResult ? (
                // Show REAL gift for Secret Win
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <img
                    src={`https://nft.fragment.com/gift/${secretResult.slug}.large.jpg`}
                    alt={secretResult.name}
                    style={{ width: '120px', borderRadius: '12px' }}
                  />
                  <div style={{ marginTop: '10px', fontSize: '18px', fontWeight: 'bold' }}>{secretResult.name}</div>
                </div>
              ) : (
                <>
                  <LottieAnimation animationData={gifts.find(g => g.name === result).animation} width={120} height={120} />
                  {result === 'paw' && pawAmount > 0 && <div className="result-amount">×{pawAmount}</div>}
                  {result === 'star' && starAmount > 0 && <div className="result-amount">×{starAmount}</div>}
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="spin-controls">
        {slug === 'promik' && (
          <div className="promik-input-container" style={{ marginBottom: '10px', width: '100%', maxWidth: '280px' }}>
            <input
              type="text"
              placeholder="Введите промокод..."
              value={promikCode}
              onChange={e => setPromikCode(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.1)',
                background: 'rgba(0,0,0,0.3)',
                color: 'white',
                textAlign: 'center',
                fontSize: '16px',
                outline: 'none'
              }}
            />
          </div>
        )}

        <button
          className={`spin-button-fixed ${spinning ? 'disabled' : ''}`}
          onClick={handleSpin}
          disabled={spinning}
        >
          {spinning ? 'Вращение...' : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="button-main-text">
                {slug === 'promik' ? 'Активировать' : `Крутить за ${caseInfo.price}`}
              </span>
              <LottieAnimation animationData={slug === 'lapik' ? pawAnim : starAnim} width={24} height={24} />
            </div>
          )}
        </button>

        {!spinning && (
          <div className="fast-spin-toggle">
            <span className="toggle-label">Быстрый запуск</span>
            <label className="switch">
              <input type="checkbox" className="toggle" checked={fastSpin} onChange={(e) => setFastSpin(e.target.checked)} />
              <span className="slider"></span>
            </label>
          </div>
        )}
      </div>
    </div>
  )
}

export default PaidSpin
