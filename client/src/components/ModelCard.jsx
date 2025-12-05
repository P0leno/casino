import { useEffect, useRef, useState } from 'react'
import LottieAnimation from './LottieAnimation'
import './ModelCard.css'

function ModelCard({ modelUrl, onSelect }) {
  const [isVisible, setIsVisible] = useState(false)
  const cardRef = useRef(null)
  
  // Извлекаем имя модели из URL
  const modelName = modelUrl.split('/').pop().replace('.json', '')
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        // Анимация проигрывается только когда карточка видна
        setIsVisible(entry.isIntersecting)
      },
      {
        root: null, // viewport
        rootMargin: '50px', // Начинаем загрузку за 50px до появления
        threshold: 0.1 // 10% карточки должно быть видно
      }
    )

    if (cardRef.current) {
      observer.observe(cardRef.current)
    }

    return () => {
      if (cardRef.current) {
        observer.unobserve(cardRef.current)
      }
    }
  }, [])

  return (
    <div 
      ref={cardRef}
      className="model-card"
      onClick={() => onSelect && onSelect(modelUrl, modelName)}
    >
      <div className="model-preview">
        {isVisible ? (
          <LottieAnimation 
            animationData={modelUrl}
            width="100%"
            height="100%"
            loop={true}
            autoplay={true}
          />
        ) : (
          <div className="model-placeholder">Загрузка...</div>
        )}
      </div>
      <div className="model-name">{modelName}</div>
    </div>
  )
}

export default ModelCard
