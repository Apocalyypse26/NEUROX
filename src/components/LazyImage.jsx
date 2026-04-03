import React, { useState, useEffect, useRef } from 'react'

export default function LazyImage({
  src,
  alt,
  className = '',
  style = {},
  onLoad,
  onError,
  placeholder = null,
  fallbackSrc = null,
  rootMargin = '200px',
  threshold = 0.1,
  ...props
}) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [isInView, setIsInView] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [currentSrc, setCurrentSrc] = useState(null)
  const imgRef = useRef(null)
  const observerRef = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true)
          observer.disconnect()
        }
      },
      {
        rootMargin: rootMargin,
        threshold: threshold
      }
    )

    observerRef.current = observer

    if (imgRef.current) {
      observer.observe(imgRef.current)
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [rootMargin, threshold])

  useEffect(() => {
    if (isInView && src) {
      const img = new Image()
      img.src = src
      img.onload = () => {
        setCurrentSrc(src)
        setIsLoaded(true)
        setHasError(false)
        onLoad?.()
      }
      img.onerror = () => {
        setHasError(true)
        if (fallbackSrc) {
          setCurrentSrc(fallbackSrc)
        }
        onError?.()
      }
    }
  }, [isInView, src, fallbackSrc, onLoad, onError])

  const containerStyle = {
    position: 'relative',
    overflow: 'hidden',
    background: 'rgba(255, 255, 255, 0.05)',
    ...style
  }

  const imageStyle = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transition: 'opacity 0.3s ease-in-out, transform 0.3s ease-in-out',
    opacity: isLoaded ? 1 : 0,
    transform: isLoaded ? 'scale(1)' : 'scale(1.02)'
  }

  return (
    <div ref={imgRef} style={containerStyle} className={`lazy-image-container ${className}`}>
      {!isLoaded && !hasError && (
        <div className="lazy-image-placeholder">
          {placeholder || <div className="lazy-image-shimmer" />}
        </div>
      )}
      
      {currentSrc && (
        <img
          src={currentSrc}
          alt={alt}
          style={imageStyle}
          className="lazy-image"
          {...props}
        />
      )}

      <style>{`
        .lazy-image-container {
          display: block;
        }

        .lazy-image-placeholder {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .lazy-image-shimmer {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0.03) 0%,
            rgba(255, 255, 255, 0.08) 50%,
            rgba(255, 255, 255, 0.03) 100%
          );
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }

        @keyframes shimmer {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }

        .lazy-image {
          display: block;
        }
      `}</style>
    </div>
  )
}
