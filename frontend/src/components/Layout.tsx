import { Outlet, Link, useNavigate, Navigate } from 'react-router-dom'
import { T } from '../styles/theme'

const s: Record<string, React.CSSProperties> = {
  shell: { minHeight: '100vh', display: 'flex', flexDirection: 'column' },
  nav: {
    background: T.navBg,
    color: '#fff',
    padding: '0 32px',
    display: 'flex',
    alignItems: 'center',
    gap: 32,
    height: 60,
    flexShrink: 0,
    borderBottom: '1px solid #1a1a1a',
  },
  logo: { height: 26, display: 'block' },
  navDivider: { width: 1, height: 20, background: '#2a2a2a', flexShrink: 0 },
  navLink: {
    color: T.textGray,
    textDecoration: 'none',
    fontSize: 14,
    fontWeight: 500,
    letterSpacing: 0.1,
  },
  spacer: { flex: 1 },
  logoutBtn: {
    background: 'transparent',
    border: '1px solid #2a2a2a',
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
        <button style={s.logoutBtn} onClick={logout}>Logout</button>
      </nav>
      <main style={s.main}>
        <Outlet />
      </main>
    </div>
  )
}
