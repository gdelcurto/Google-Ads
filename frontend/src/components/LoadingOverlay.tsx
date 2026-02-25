import { useEffect, useState } from 'react'
import '../styles/loading.css'

interface LoadingOverlayProps {
  visible: boolean
  message?: string
  submessage?: string
}

export function LoadingOverlay({
  visible,
  message    = 'Elaborazione in corso…',
  submessage,
}: LoadingOverlayProps) {
  // Keep the DOM mounted during the fade-out transition
  const [mounted, setMounted] = useState(visible)

  useEffect(() => {
    if (visible) {
      setMounted(true)
    } else {
      const t = setTimeout(() => setMounted(false), 350)
      return () => clearTimeout(t)
    }
  }, [visible])

  if (!mounted) return null

  return (
    <div
      className="lo-overlay"
      style={{ opacity: visible ? 1 : 0, pointerEvents: visible ? 'all' : 'none' }}
      aria-live="assertive"
      aria-label={message}
    >
      <div className="lo-logo-area">
        {/* Concentric spinning rings */}
        <div className="lo-ring lo-ring-outer" />
        <div className="lo-ring lo-ring-inner" />

        {/* Logo with shimmer + glow */}
        <div className="lo-logo-wrap">
          <img
            src="/AdAtelier.svg"
            className="lo-logo"
            alt="AdAtelier"
            draggable={false}
          />
        </div>
      </div>

      <p className="lo-message">{message}</p>
      {submessage && <p className="lo-submessage">{submessage}</p>}

      <div className="lo-dots">
        <span /><span /><span />
      </div>
    </div>
  )
}
