import { useEffect, useRef } from 'react'

function LottieAnimation({ animationData, width = 80, height = 80, loop = true, autoplay = true, rotation = 0 }) {
  const containerRef = useRef(null)
  const animationRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !animationData) return

    const loadLottie = async () => {
      try {
        const lottie = await import('https://cdn.skypack.dev/lottie-web')
        
        if (animationRef.current) {
          animationRef.current.destroy()
        }

        // Если animationData это строка (URL), то загружаем по path
        // Если объект - используем напрямую как animationData
        const config = {
          container: containerRef.current,
          renderer: 'svg',
          loop: loop,
          autoplay: autoplay
        }

        if (typeof animationData === 'string') {
          // Это путь к файлу
          config.path = animationData
        } else {
          // Это уже загруженный JSON объект
          config.animationData = animationData
        }

        animationRef.current = lottie.default.loadAnimation(config)
      } catch (error) {
        console.error('Failed to load lottie:', error)
      }
    }

    loadLottie()

    return () => {
      if (animationRef.current) {
        animationRef.current.destroy()
      }
    }
  }, [animationData, loop, autoplay])

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: `${width}px`, 
        height: `${height}px`,
        display: 'inline-block',
        transform: rotation !== 0 ? `rotate(${rotation}deg)` : 'none'
      }}
    />
  )
}

export default LottieAnimation
