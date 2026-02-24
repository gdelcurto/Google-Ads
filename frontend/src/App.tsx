import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import TrashPage from './pages/TrashPage'
import UsersPage from './pages/UsersPage'
import Layout from './components/Layout'
import { AutofillJobProvider, useAutofillJobs, type AutofillNotification } from './contexts/AutofillJobContext'

// ── Global notification toasts ───────────────────────────────────────────────

function GlobalAutofillToasts() {
  const { notifications, dismissNotification } = useAutofillJobs()
  if (notifications.length === 0) return null

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        pointerEvents: 'none',
      }}
    >
      {notifications.map((n: AutofillNotification) => (
        <div
          key={n.projectId}
          style={{
            background: n.type === 'completed' ? '#f0fdf4' : '#fff0f0',
            border: `1px solid ${n.type === 'completed' ? '#86efac' : '#fca5a5'}`,
            borderRadius: 10,
            padding: '14px 16px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
            minWidth: 280,
            maxWidth: 360,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            pointerEvents: 'auto',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
            <span
              style={{
                fontWeight: 600,
                fontSize: 14,
                color: n.type === 'completed' ? '#166534' : '#991b1b',
              }}
            >
              {n.type === 'completed'
                ? <><i className="fa-solid fa-circle-check"></i> Auto-fill completato!</>
                : <><i className="fa-solid fa-circle-xmark"></i> Auto-fill fallito</>}
            </span>
            <button
              onClick={() => dismissNotification(n.projectId)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 16,
                color: '#6b7280',
                padding: 0,
                lineHeight: 1,
                flexShrink: 0,
              }}
            >
              <i className="fa-solid fa-xmark"></i>
            </button>
          </div>

          {n.type === 'completed' ? (
            <>
              <span style={{ fontSize: 13, color: '#374151' }}>
                <em>{n.brandName}</em>
                {n.projectName && n.projectName !== n.brandName ? ` (${n.projectName})` : ''}{' '}
                — il brief è pronto.
              </span>
              <Link
                to={`/projects/${n.projectId}`}
                onClick={() => dismissNotification(n.projectId)}
                style={{
                  display: 'inline-block',
                  background: '#16a34a',
                  color: '#fff',
                  borderRadius: 6,
                  padding: '6px 14px',
                  fontSize: 13,
                  fontWeight: 500,
                  textDecoration: 'none',
                  alignSelf: 'flex-start',
                }}
              >
                Vai al progetto →
              </Link>
            </>
          ) : (
            <span style={{ fontSize: 13, color: '#374151' }}>{n.errorMessage}</span>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Routes (inside BrowserRouter so Link works) ──────────────────────────────

function AppRoutes() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/projects" replace />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:id" element={<ProjectDetailPage />} />
          <Route path="trash" element={<TrashPage />} />
          <Route path="users" element={<UsersPage />} />
        </Route>
      </Routes>
      <GlobalAutofillToasts />
    </>
  )
}

// ── App root ─────────────────────────────────────────────────────────────────

function App() {
  return (
    <AutofillJobProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AutofillJobProvider>
  )
}

export default App
