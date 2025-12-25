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

        const anim = lottie.default.loadAnimation(config)
        animationRef.current = anim

        if (!autoplay) {
          // Агрессивная остановка анимации
          const freeze = () => {
            try {
              anim.goToAndStop(0, true)
              anim.pause() // На всякий случай
            } catch (e) {
              // Игнорируем ошибки если анимация еще не готова
            }
          }

          anim.addEventListener('DOMLoaded', freeze)
          anim.addEventListener('data_ready', freeze)
          anim.addEventListener('config_ready', freeze)
          anim.addEventListener('segmentStart', freeze) // Если вдруг начала играть

          // И по таймеру для надежности
          setTimeout(freeze, 50)
          setTimeout(freeze, 200)
          setTimeout(freeze, 500)

          // И сразу
          freeze()
        }
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
