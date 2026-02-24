import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/projects'
import { T } from '../styles/theme'

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: T.bgPage,
  },
  card: {
    background: T.bgCard,
    width: 380,
    borderRadius: T.radiusLg,
    overflow: 'hidden',
    boxShadow: T.shadowMd,
  },
  cardTop: {
    background: T.navBg,
    padding: '28px 40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: { height: 28 },
  cardBody: { padding: '36px 40px' },
  title: {
    fontSize: 20,
    fontWeight: 700,
    marginBottom: 4,
    color: T.text,
    letterSpacing: -0.3,
  },
  subtitle: { fontSize: 13, color: T.textGray, marginBottom: 28 },
  label: {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    marginBottom: 6,
    color: T.text,
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm,
    fontSize: 14,
    marginBottom: 16,
    outline: 'none',
    background: T.bgCard,
    color: T.text,
  },
  btn: {
    width: '100%',
    padding: '12px 0',
    background: T.primary,
    color: '#fff',
    border: 'none',
    borderRadius: T.radiusSm,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    letterSpacing: 0.1,
    marginTop: 4,
  },
  error: {
    background: '#fff0f0',
    border: '1px solid #fca5a5',
    padding: '10px 12px',
    borderRadius: T.radiusSm,
    fontSize: 13,
    color: T.error,
    marginBottom: 16,
  },
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authApi.login(email, password)
      localStorage.setItem('token', data.access_token)
      navigate('/projects')
    } catch {
      setError('Email o password errati. Riprova.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.cardTop}>
          <img src={T.logoApp} alt="AdAtelier" style={s.logo} />
        </div>
        <div style={s.cardBody}>
          <div style={s.title}>Google Ads Campaigns</div>
          <div style={s.subtitle}>Piattaforma interna — Blastness / Mentefredda</div>
          {error && <div style={s.error}>{error}</div>}
          <form onSubmit={handleLogin}>
            <label style={s.label}>Email</label>
            <input
              style={s.input}
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
            />
            <label style={s.label}>Password</label>
            <input
              style={s.input}
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <button style={s.btn} type="submit" disabled={loading}>
              {loading ? 'Accesso...' : 'Accedi'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
