import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/projects'

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' },
  card: { background: '#fff', padding: 40, borderRadius: 8, boxShadow: '0 2px 16px rgba(0,0,0,0.10)', width: 360 },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 8, color: '#1e3a5f' },
  subtitle: { fontSize: 13, color: '#64748b', marginBottom: 28 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4, color: '#374151' },
  input: {
    width: '100%', padding: '10px 12px', border: '1px solid #cbd5e1',
    borderRadius: 6, fontSize: 14, marginBottom: 16, outline: 'none',
  },
  btn: {
    width: '100%', padding: '11px 0', background: '#1e3a5f', color: '#fff',
    border: 'none', borderRadius: 6, fontSize: 15, fontWeight: 600, cursor: 'pointer',
  },
  error: { background: '#fef2f2', border: '1px solid #fca5a5', padding: 10, borderRadius: 6, fontSize: 13, color: '#dc2626', marginBottom: 16 },
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
        <div style={s.title}>Google Ads Campaigns</div>
        <div style={s.subtitle}>Piattaforma interna — Blastness / Mentefredda</div>
        {error && <div style={s.error}>{error}</div>}
        <form onSubmit={handleLogin}>
          <label style={s.label}>Email</label>
          <input style={s.input} type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
          <label style={s.label}>Password</label>
          <input style={s.input} type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          <button style={s.btn} type="submit" disabled={loading}>
            {loading ? 'Accesso...' : 'Accedi'}
          </button>
        </form>
      </div>
    </div>
  )
}
