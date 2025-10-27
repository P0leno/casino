import { useEffect, useRef } from 'react'

function LottieAnimation({ animationData, width = 80, height = 80, loop = true, autoplay = true }) {
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

        animationRef.current = lottie.default.loadAnimation({
          container: containerRef.current,
          renderer: 'svg',
          loop: loop,
          autoplay: autoplay,
          animationData: animationData
        })
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
        display: 'inline-block'
      }}
    />
  )
}

export default LottieAnimation
