import { Outlet, Link, useNavigate, Navigate } from 'react-router-dom'

const s: Record<string, React.CSSProperties> = {
  shell: { minHeight: '100vh', display: 'flex', flexDirection: 'column' },
  nav: {
    background: '#1e3a5f', color: '#fff', padding: '0 24px',
    display: 'flex', alignItems: 'center', gap: 24, height: 56,
  },
  brand: { fontWeight: 700, fontSize: 18, color: '#fff', textDecoration: 'none' },
  navLink: { color: '#94b8d8', textDecoration: 'none', fontSize: 14 },
  spacer: { flex: 1 },
  logoutBtn: {
    background: 'transparent', border: '1px solid #94b8d8', color: '#94b8d8',
    padding: '4px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 13,
  },
  main: { flex: 1, padding: '32px 24px', maxWidth: 1200, margin: '0 auto', width: '100%' },
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
        <Link to="/" style={s.brand}>Google Ads Campaigns</Link>
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
