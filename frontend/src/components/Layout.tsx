import { useState, useEffect, useRef } from 'react'
import { Outlet, Link, useNavigate, useLocation, Navigate } from 'react-router-dom'
import { T } from '../styles/theme'
import { useAutofillJobs, type PersistedNotification } from '../contexts/AutofillJobContext'

const SIDEBAR_W = 56

// ── helpers ──────────────────────────────────────────────────────────────────

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

function getTokenRole(): string | null {
  try {
    const token = localStorage.getItem('token')
    if (!token) return null
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.role ?? null
  } catch {
    return null
  }
}

// ── Tooltip label ─────────────────────────────────────────────────────────────

function Tooltip({ label }: { label: string }) {
  return (
    <div style={{
      position: 'absolute',
      left: SIDEBAR_W + 8,
      top: '50%',
      transform: 'translateY(-50%)',
      background: 'rgba(17,17,17,0.92)',
      color: '#fff',
      padding: '5px 11px',
      borderRadius: 6,
      fontSize: 12,
      fontWeight: 600,
      whiteSpace: 'nowrap',
      pointerEvents: 'none',
      zIndex: 10000,
      boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
    }}>
      {label}
      <div style={{
        position: 'absolute',
        right: '100%',
        top: '50%',
        transform: 'translateY(-50%)',
        width: 0, height: 0,
        borderTop: '5px solid transparent',
        borderBottom: '5px solid transparent',
        borderRight: '5px solid rgba(17,17,17,0.92)',
      }} />
    </div>
  )
}

// ── Nav item (link) ───────────────────────────────────────────────────────────

function NavLink({ to, icon, label, active }: {
  to: string
  icon: string
  label: string
  active: boolean
}) {
  const [hovered, setHovered] = useState(false)
  return (
    <Link
      to={to}
      style={{ textDecoration: 'none', display: 'block', position: 'relative' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{
        width: SIDEBAR_W,
        height: 48,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: active
          ? 'rgba(255,255,255,0.18)'
          : hovered ? 'rgba(255,255,255,0.10)' : 'transparent',
        transition: 'background 0.15s',
        position: 'relative',
      }}>
        {active && (
          <div style={{
            position: 'absolute',
            left: 0, top: '50%',
            transform: 'translateY(-50%)',
            width: 3, height: 28,
            background: '#fff',
            borderRadius: '0 3px 3px 0',
          }} />
        )}
        <i className={icon} style={{ fontSize: 18, color: 'rgba(255,255,255,0.95)' }} />
        {hovered && <Tooltip label={label} />}
      </div>
    </Link>
  )
}

// ── Notification Bell ─────────────────────────────────────────────────────────

function NotificationBell() {
  const { allNotifications, unreadCount, markAllRead, markRead } = useAutofillJobs()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [hovered, setHovered] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

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
    if (n.type === 'completed') navigate(`/projects/${n.projectId}`)
    setOpen(false)
  }

  return (
    <div ref={wrapperRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(v => !v)}
        aria-label="Notifiche"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          width: SIDEBAR_W,
          height: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: open || hovered ? 'rgba(255,255,255,0.10)' : 'transparent',
          border: 'none',
          cursor: 'pointer',
          position: 'relative',
          transition: 'background 0.15s',
        }}
      >
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none"
          stroke="rgba(255,255,255,0.95)" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: 8, right: 8,
            background: '#fff', color: T.primary,
            borderRadius: 999, fontSize: 9, fontWeight: 800,
            minWidth: 15, height: 15,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '0 3px', lineHeight: 1,
          }}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
        {hovered && !open && (
          <Tooltip label={`Notifiche${unreadCount > 0 ? ` (${unreadCount})` : ''}`} />
        )}
      </button>

      {/* Dropdown — opens to the right of the sidebar */}
      {open && (
        <div style={{
          position: 'fixed',
          left: SIDEBAR_W + 8,
          bottom: 56,
          width: 360,
          background: '#fff',
          borderRadius: T.radius,
          boxShadow: T.shadowMd,
          border: `1px solid ${T.borderLight}`,
          zIndex: 2000,
          maxHeight: 480,
          overflowY: 'auto',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px', borderBottom: `1px solid ${T.borderLight}`,
            fontSize: 14, fontWeight: 600, color: T.text,
            position: 'sticky', top: 0, background: '#fff', zIndex: 1,
          }}>
            <span>Notifiche{unreadCount > 0 ? ` (${unreadCount})` : ''}</span>
            {unreadCount > 0 && (
              <button
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: T.blue, fontSize: 12, fontWeight: 500, padding: 0 }}
                onClick={e => { e.stopPropagation(); markAllRead() }}
              >
                Segna tutte come lette
              </button>
            )}
          </div>

          {sorted.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: T.textGray, fontSize: 13 }}>
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
                  display: 'flex', gap: 10, alignItems: 'flex-start',
                  background: n.read ? '#fff' : '#f0f4ff',
                }}
                onClick={() => handleClick(n)}
                onMouseEnter={e => { if (n.type === 'completed') (e.currentTarget as HTMLDivElement).style.background = n.read ? '#f7f7f7' : '#e8eeff' }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = n.read ? '#fff' : '#f0f4ff' }}
              >
                <div style={{
                  flexShrink: 0, width: 30, height: 30, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, fontWeight: 700,
                  background: n.type === 'completed' ? '#dcfce7' : '#fee2e2',
                  color: n.type === 'completed' ? T.success : T.error,
                }}>
                  {n.type === 'completed' ? '✓' : '✗'}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 2 }}>
                    {n.brandName || n.projectName}
                  </div>
                  <div style={{ fontSize: 12, color: T.textGray, marginBottom: 3 }}>
                    {n.type === 'completed' ? 'Auto-fill completato — clicca per aprire il brief' : `Errore: ${n.errorMessage}`}
                  </div>
                  <div style={{ fontSize: 11, color: T.textGray }}>{formatTime(n.timestamp)}</div>
                </div>
                {!n.read && (
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: T.primary, flexShrink: 0, marginTop: 6 }} />
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Logout button ────────────────────────────────────────────────────────────

function LogoutButton({ onLogout }: { onLogout: () => void }) {
  const [hov, setHov] = useState(false)
  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={onLogout}
        onMouseEnter={() => setHov(true)}
        onMouseLeave={() => setHov(false)}
        style={{
          width: SIDEBAR_W, height: 48,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: hov ? 'rgba(255,255,255,0.10)' : 'transparent',
          border: 'none', cursor: 'pointer',
          transition: 'background 0.15s',
        }}
      >
        <i className="fa-solid fa-right-from-bracket" style={{ fontSize: 17, color: 'rgba(255,255,255,0.85)' }} />
        {hov && <Tooltip label="Logout" />}
      </button>
    </div>
  )
}

// ── Layout ────────────────────────────────────────────────────────────────────

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const token = localStorage.getItem('token')
  const role = getTokenRole()

  if (!token) return <Navigate to="/login" replace />

  const logout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  const isActive = (path: string) => location.pathname.startsWith(path)

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <nav style={{
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
        width: SIDEBAR_W,
        background: T.primary,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        zIndex: 1000,
        boxShadow: '2px 0 16px rgba(225,0,152,0.22)',
      }}>
        {/* Logo */}
        <Link to="/" style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: SIDEBAR_W, height: 56, flexShrink: 0,
          background: '#fff',
        }}>
          <img
            src="https://www.blastness.com/loghi/2342/logofooter.png"
            alt="Blastness"
            style={{ width: 34, objectFit: 'contain' }}
          />
        </Link>

        {/* Divider */}
        <div style={{ width: 28, height: 1, background: 'rgba(255,255,255,0.25)', marginBottom: 6 }} />

        {/* Nav links */}
        <NavLink
          to="/projects"
          icon="fa-solid fa-folder-open"
          label="Progetti"
          active={isActive('/projects')}
        />
        {role === 'admin' && (
          <NavLink
            to="/users"
            icon="fa-solid fa-users"
            label="Utenti"
            active={isActive('/users')}
          />
        )}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Bottom: notifications + logout */}
        <NotificationBell />

        {/* Logout */}
        <LogoutButton onLogout={logout} />

        <div style={{ height: 8 }} />
      </nav>

      {/* ── Main content ────────────────────────────────────────── */}
      <main style={{
        flex: 1,
        marginLeft: SIDEBAR_W,
        padding: '0 36px 40px',
        boxSizing: 'border-box',
        minHeight: '100vh',
        width: `calc(100% - ${SIDEBAR_W}px)`,
      }}>
        {/* App header */}
        <div style={{
          paddingTop: 28,
          paddingBottom: 20,
          marginBottom: 28,
          borderBottom: `1px solid ${T.borderLight}`,
        }}>
          <img
            src="https://www.mentefredda.it/AdAtelier.svg"
            alt="AdAtelier"
            style={{ height: 28, display: 'block' }}
          />
        </div>

        <Outlet />
      </main>
    </div>
  )
}
