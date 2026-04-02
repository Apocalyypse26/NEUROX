export function exportToJSON(data, filename = 'neurox-analysis') {
  const exportData = {
    exportedAt: new Date().toISOString(),
    platform: 'NEUROX',
    version: '2.5',
    ...data
  }
  
  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}-${Date.now()}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function shareToTwitter({ score, fileName, bestPlatform }) {
  const text = `🚀 My meme just scored ${score}/100 on NEUROX virality analysis!\n\n📊 Best platform: ${bestPlatform}\n🎯 File: ${fileName}\n\n#NEUROX #ViralScore #MemeAnalysis`
  const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`
  window.open(url, '_blank', 'width=600,height=400')
}

export function shareToTelegram({ score, fileName, bestPlatform }) {
  const text = `🚀 My meme scored ${score}/100 on NEUROX!\n\n📊 Best platform: ${bestPlatform}\n🎯 File: ${fileName}\n\n#NEUROX #ViralScore`
  const url = `https://t.me/share/url?url=${encodeURIComponent('https://neurox.ai')}&text=${encodeURIComponent(text)}`
  window.open(url, '_blank', 'width=600,height=400')
}

export function copyToClipboard(text) {
  return navigator.clipboard.writeText(text)
}

export function generateShareableImage({ score, fileName, bestPlatform, confidence, thumbnailUrl }) {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 600
    canvas.height = 400
    
    // Background gradient
    const gradient = ctx.createLinearGradient(0, 0, 600, 400)
    gradient.addColorStop(0, '#0a0015')
    gradient.addColorStop(0.5, '#150a25')
    gradient.addColorStop(1, '#0a0015')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 600, 400)
    
    // Border glow
    ctx.strokeStyle = score > 85 ? '#FF6F37' : score > 70 ? '#f59e0b' : '#ef4444'
    ctx.lineWidth = 3
    ctx.strokeRect(10, 10, 580, 380)
    
    // Header
    ctx.fillStyle = '#FF6F37'
    ctx.font = 'bold 18px monospace'
    ctx.fillText('NEUROX VIRALITY ANALYSIS', 30, 45)
    
    // Divider
    ctx.strokeStyle = 'rgba(255,111,55,0.3)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(30, 60)
    ctx.lineTo(570, 60)
    ctx.stroke()
    
    // Score section
    const scoreColor = score > 85 ? '#FF6F37' : score > 70 ? '#f59e0b' : '#ef4444'
    ctx.fillStyle = scoreColor
    ctx.font = 'bold 72px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(score.toString(), 300, 180)
    
    ctx.fillStyle = '#666'
    ctx.font = '24px monospace'
    ctx.fillText('/100', 360, 180)
    
    // Progress bar
    ctx.fillStyle = 'rgba(255,255,255,0.1)'
    ctx.fillRect(100, 200, 400, 12)
    
    ctx.fillStyle = scoreColor
    ctx.shadowColor = scoreColor
    ctx.shadowBlur = 10
    ctx.fillRect(100, 200, (score / 100) * 400, 12)
    ctx.shadowBlur = 0
    
    // Details
    ctx.textAlign = 'left'
    ctx.fillStyle = '#888'
    ctx.font = '14px monospace'
    ctx.fillText(`FILE: ${fileName?.substring(0, 30) || 'Unknown'}`, 30, 260)
    ctx.fillText(`BEST PLATFORM: ${bestPlatform || 'N/A'}`, 30, 285)
    ctx.fillText(`CONFIDENCE: ${confidence || 'N/A'}`, 30, 310)
    
    // Footer
    ctx.fillStyle = '#FF6F37'
    ctx.font = 'bold 12px monospace'
    ctx.textAlign = 'center'
    ctx.fillText('neurox.ai | #NEUROX', 300, 365)
    
    // Recording indicator
    ctx.fillStyle = '#ef4444'
    ctx.beginPath()
    ctx.arc(560, 45, 5, 0, Math.PI * 2)
    ctx.fill()
    
    canvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `neurox-viral-${score}-${Date.now()}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      resolve()
    }, 'image/png')
  })
}
