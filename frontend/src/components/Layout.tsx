import React, { useState, useEffect, useRef } from 'react'
import { Outlet, Link, useNavigate, Navigate } from 'react-router-dom'
import { T } from '../styles/theme'
import { useAutofillJobs, type PersistedNotification } from '../contexts/AutofillJobContext'

// ── helpers ─────────────────────────────────────────────────────────────────

function formatTime(timestamp: number): string {
  const diff = Date.now() - timestamp
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'adesso'
  if (mins < 60) return `${mins}m fa`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h fa`
  const days = Math.floor(hours / 24)
  return `${days}g fa`
}

// ── Bell SVG ─────────────────────────────────────────────────────────────────

function BellIcon({ active }: { active: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke={active ? T.primary : T.textGray}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )
}

// ── Notification Bell ────────────────────────────────────────────────────────

function NotificationBell() {
  const { allNotifications, unreadCount, markAllRead, markRead } = useAutofillJobs()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // Close on click outside.
  useEffect(() => {
    if (!open) return
    function handleOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [open])

  const sorted = [...allNotifications].sort((a, b) => b.timestamp - a.timestamp)

  const handleClick = (n: PersistedNotification) => {
    markRead(n.id)
    if (n.type === 'completed') {
      navigate(`/projects/${n.projectId}`)
    }
    setOpen(false)
  }

  return (
    <div ref={wrapperRef} style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
      {/* Bell button */}
      <button
        style={{
          background: open ? T.bgMuted : 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '6px',
          borderRadius: T.radiusSm,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
        onClick={() => setOpen(v => !v)}
        aria-label="Notifiche"
      >
        <BellIcon active={unreadCount > 0} />
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute',
            top: 1,
            right: 1,
            background: T.error,
            color: '#fff',
            borderRadius: 999,
            fontSize: 10,
            fontWeight: 700,
            minWidth: 16,
            height: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            lineHeight: 1,
            padding: '0 3px',
          }}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 8px)',
          right: 0,
          width: 360,
          background: '#fff',
          borderRadius: T.radius,
          boxShadow: T.shadowMd,
          border: `1px solid ${T.borderLight}`,
          zIndex: 1000,
          maxHeight: 480,
          overflowY: 'auto',
        }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderBottom: `1px solid ${T.borderLight}`,
            fontSize: 14,
            fontWeight: 600,
            color: T.text,
            position: 'sticky',
            top: 0,
            background: '#fff',
            zIndex: 1,
          }}>
            <span>
              Notifiche{unreadCount > 0 ? ` (${unreadCount} non lette)` : ''}
            </span>
            {unreadCount > 0 && (
              <button
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: T.blue,
                  fontSize: 12,
                  fontWeight: 500,
                  padding: 0,
                }}
                onClick={e => { e.stopPropagation(); markAllRead() }}
              >
                Segna tutte come lette
              </button>
            )}
          </div>

          {/* List */}
          {sorted.length === 0 ? (
            <div style={{
              padding: 32,
              textAlign: 'center',
              color: T.textGray,
              fontSize: 13,
            }}>
              Nessuna notifica
            </div>
          ) : (
            sorted.map(n => (
              <div
                key={n.id}
                style={{
                  padding: '12px 16px',
                  borderBottom: `1px solid ${T.borderLight}`,
                  cursor: n.type === 'completed' ? 'pointer' : 'default',
                  display: 'flex',
                  gap: 10,
                  alignItems: 'flex-start',
                  background: n.read ? '#fff' : '#f0f4ff',
                }}
                onClick={() => handleClick(n)}
                onMouseEnter={e => {
                  if (n.type === 'completed') {
                    (e.currentTarget as HTMLDivElement).style.background = n.read ? '#f7f7f7' : '#e8eeff'
                  }
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLDivElement).style.background = n.read ? '#fff' : '#f0f4ff'
                }}
              >
                {/* Icon */}
                <div style={{
                  flexShrink: 0,
                  width: 30,
                  height: 30,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 13,
                  fontWeight: 700,
                  background: n.type === 'completed' ? '#dcfce7' : '#fee2e2',
                  color: n.type === 'completed' ? T.success : T.error,
                }}>
                  {n.type === 'completed' ? '✓' : '✗'}
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 2 }}>
                    {n.brandName || n.projectName}
                  </div>
                  <div style={{ fontSize: 12, color: T.textGray, marginBottom: 3 }}>
                    {n.type === 'completed'
                      ? 'Auto-fill completato — clicca per aprire il brief'
                      : `Errore: ${n.errorMessage}`}
                  </div>
                  <div style={{ fontSize: 11, color: T.textGray }}>
                    {formatTime(n.timestamp)}
                  </div>
                </div>

                {/* Unread dot */}
                {!n.read && (
                  <div style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: T.primary,
                    flexShrink: 0,
                    marginTop: 6,
                  }} />
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── styles ───────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  shell: { minHeight: '100vh', display: 'flex', flexDirection: 'column' },
  nav: {
    background: '#fff',
    color: T.text,
    padding: '0 32px',
    display: 'flex',
    alignItems: 'center',
    gap: 32,
    height: 60,
    flexShrink: 0,
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  },
  logo: { height: 26, display: 'block' },
  navDivider: { width: 1, height: 20, background: T.borderLight, flexShrink: 0 },
  navLink: {
    color: T.textGray,
    textDecoration: 'none',
    fontSize: 14,
    fontWeight: 500,
  },
  spacer: { flex: 1 },
  logoutBtn: {
    background: 'transparent',
    border: `1px solid ${T.border}`,
    color: T.textGray,
    padding: '5px 14px',
    borderRadius: T.radiusSm,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
  },
  main: {
    flex: 1,
    padding: '40px 32px',
    maxWidth: 1280,
    margin: '0 auto',
    width: '100%',
  },
}

// ── Layout ───────────────────────────────────────────────────────────────────

export default function Layout() {
  const navigate = useNavigate()
  const token = localStorage.getItem('token')

  if (!token) {
    return <Navigate to="/login" replace />
  }

  const logout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <div style={s.shell}>
      <nav style={s.nav}>
        <Link to="/" style={{ lineHeight: 0 }}>
          <img src={T.logo} alt="Blastness" style={s.logo} />
        </Link>
        <div style={s.navDivider} />
        <Link to="/projects" style={s.navLink}>Progetti</Link>
        <div style={s.spacer} />
        <NotificationBell />
        <button style={s.logoutBtn} onClick={logout}>Logout</button>
      </nav>
      <main style={s.main}>
        <Outlet />
      </main>
    </div>
  )
}
