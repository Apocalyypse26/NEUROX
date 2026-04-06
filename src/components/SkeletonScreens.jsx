import React from 'react'

export const SkeletonCard = ({ delay = 0 }) => (
  <div className={`skeleton skeleton-card ${delay ? `skeleton-delay-${delay}` : ''}`}>
    <div className="skeleton skeleton-icon" />
    <div className="skeleton skeleton-text-md" style={{ width: '70%' }} />
    <div className="skeleton skeleton-text-sm" style={{ width: '50%' }} />
  </div>
)

export const SkeletonMediaCard = ({ delay = 0, aspectRatio = '16/9' }) => (
  <div 
    className={`skeleton skeleton-media-card ${delay ? `skeleton-delay-${delay}` : ''}`}
    style={{ aspectRatio }}
  />
)

export const SkeletonScoreCard = ({ delay = 0, size = 'medium' }) => (
  <div 
    className={`skeleton skeleton-score ${delay ? `skeleton-delay-${delay}` : ''}`}
    style={{ 
      height: size === 'large' ? '180px' : size === 'small' ? '80px' : '120px',
      borderRadius: size === 'large' ? '24px' : '20px'
    }}
  />
)

export const SkeletonProgressBar = ({ delay = 0 }) => (
  <div className={`skeleton skeleton-progress-bar ${delay ? `skeleton-delay-${delay}` : ''}`} />
)

export const SkeletonText = ({ lines = 3, delay = 0 }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
    {[...Array(lines)].map((_, i) => (
      <div 
        key={i} 
        className={`skeleton skeleton-text-md ${delay ? `skeleton-delay-${delay}` : ''}`}
        style={{ width: `${60 + Math.random() * 30}%` }}
      />
    ))}
  </div>
)

export const SkeletonAvatar = ({ delay = 0, size = 48 }) => (
  <div 
    className={`skeleton skeleton-avatar ${delay ? `skeleton-delay-${delay}` : ''}`}
    style={{ width: size, height: size }}
  />
)

export const SkeletonButton = ({ delay = 0, width = '120px' }) => (
  <div 
    className={`skeleton skeleton-button ${delay ? `skeleton-delay-${delay}` : ''}`}
    style={{ width }}
  />
)

export const SkeletonGallery = ({ count = 4 }) => (
  <div className="media-gallery" style={{ 
    display: 'grid', 
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', 
    gap: '1rem' 
  }}>
    {[...Array(count)].map((_, i) => (
      <SkeletonMediaCard key={i} delay={(i % 5) + 1} />
    ))}
  </div>
)

export const SkeletonDashboardCards = ({ count = 3 }) => (
  <div style={{ 
    display: 'grid', 
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', 
    gap: '1rem' 
  }}>
    {[...Array(count)].map((_, i) => (
      <SkeletonCard key={i} delay={(i % 5) + 1} />
    ))}
  </div>
)

export const SkeletonStats = ({ count = 3 }) => (
  <div style={{ 
    display: 'grid', 
    gridTemplateColumns: `repeat(${count}, 1fr)`, 
    gap: '1rem' 
  }}>
    {[...Array(count)].map((_, i) => (
      <div key={i} className={`skeleton ${i === 0 ? 'skeleton-delay-1' : ''}`} style={{ height: '80px', borderRadius: '16px' }} />
    ))}
  </div>
)

export const SkeletonForm = ({ fields = 3 }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
    {[...Array(fields)].map((_, i) => (
      <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div className={`skeleton skeleton-text-sm`} style={{ width: '100px' }} />
        <div className={`skeleton`} style={{ height: '44px', borderRadius: '8px' }} />
      </div>
    ))}
  </div>
)