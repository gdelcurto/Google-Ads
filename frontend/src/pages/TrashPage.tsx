import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, type Project } from '../api/projects'
import { T } from '../styles/theme'

const STATUS_LABELS: Record<string, string> = {
  draft:     'Bozza',
  validated: 'Validato',
  preview:   'Preview',
  published: 'Pubblicato',
  archived:  'Archiviato',
}

const s: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 32,
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  h1: { fontSize: 26, fontWeight: 700, color: T.text, letterSpacing: -0.5 },
  backLink: {
    color: T.textGray,
    textDecoration: 'none',
    fontSize: 13,
    fontWeight: 500,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    background: T.bgCard,
    borderRadius: T.radiusLg,
    overflow: 'hidden',
    boxShadow: T.shadow,
  },
  th: {
    textAlign: 'left' as const,
    padding: '14px 16px',
    fontSize: 12,
    fontWeight: 700,
    color: T.textGray,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    borderBottom: `2px solid ${T.borderLight}`,
    background: T.bgMuted,
  },
  td: {
    padding: '14px 16px',
    fontSize: 14,
    color: T.text,
    borderBottom: `1px solid ${T.borderLight}`,
  },
  name: {
    fontWeight: 600,
  },
  slug: {
    fontSize: 12,
    color: T.textGray,
  },
  badge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 600,
    color: T.textGray,
    background: T.bgMuted,
    border: `1px solid ${T.borderLight}`,
  },
  actionBtn: {
    background: 'transparent',
    border: `1px solid ${T.borderLight}`,
    padding: '6px 14px',
    borderRadius: T.radiusSm,
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 500,
    color: T.text,
  },
  restoreBtn: {
    background: 'transparent',
    border: `1px solid ${T.success}`,
    padding: '6px 14px',
    borderRadius: T.radiusSm,
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 500,
    color: T.success,
  },
  deleteBtn: {
    background: 'transparent',
    border: `1px solid ${T.error}`,
    padding: '6px 14px',
    borderRadius: T.radiusSm,
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 500,
    color: T.error,
  },
  actions: {
    display: 'flex',
    gap: 8,
  },
  emptyState: {
    textAlign: 'center' as const,
    padding: '60px 0',
    color: T.textGray,
    fontSize: 14,
  },
  modal: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
    backdropFilter: 'blur(3px)',
  },
  modalBox: {
    background: T.bgCard,
    borderRadius: T.radiusLg,
    padding: 36,
    width: 440,
    boxShadow: T.shadowMd,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 700,
    marginBottom: 16,
    color: T.text,
    letterSpacing: -0.3,
  },
  row: { display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 8 },
  cancelBtn: {
    background: 'transparent',
    color: T.text,
    border: `1px solid ${T.border}`,
    padding: '10px 18px',
    borderRadius: T.radiusSm,
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 500,
  },
  btn: {
    background: T.error,
    color: '#fff',
    border: 'none',
    padding: '10px 20px',
    borderRadius: T.radiusSm,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 14,
  },
}

export default function TrashPage() {
  const [confirmPermanent, setConfirmPermanent] = useState<Project | null>(null)
  const qc = useQueryClient()

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['trash'],
    queryFn: projectsApi.listTrash,
  })

  const restoreMutation = useMutation({
    mutationFn: (id: string) => projectsApi.restore(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trash'] })
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const permanentDeleteMutation = useMutation({
    mutationFn: (id: string) => projectsApi.permanentDelete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trash'] })
      setConfirmPermanent(null)
    },
  })

  return (
    <div>
      <div style={s.header}>
        <div style={s.titleRow}>
          <Link to="/projects" style={s.backLink}>
            <i className="fa-solid fa-arrow-left"></i> Progetti
          </Link>
          <h1 style={s.h1}>Cestino</h1>
        </div>
      </div>

      {isLoading && <p style={{ color: T.textGray }}>Caricamento...</p>}

      {!isLoading && projects.length === 0 ? (
        <div style={s.emptyState}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>
            <i className="fa-regular fa-trash-can" style={{ color: T.borderLight }}></i>
          </div>
          <div>Il cestino è vuoto</div>
        </div>
      ) : (
        <table style={s.table}>
          <thead>
            <tr>
              <th style={s.th}>Progetto</th>
              <th style={s.th}>Slug</th>
              <th style={s.th}>Stato</th>
              <th style={s.th}>Preset</th>
              <th style={s.th}>Verticale</th>
              <th style={{ ...s.th, textAlign: 'right' }}>Azioni</th>
            </tr>
          </thead>
          <tbody>
            {projects.map(p => (
              <tr
                key={p.id}
                onMouseEnter={e => { (e.currentTarget as HTMLTableRowElement).style.background = T.bgMuted }}
                onMouseLeave={e => { (e.currentTarget as HTMLTableRowElement).style.background = '' }}
              >
                <td style={s.td}>
                  <div style={s.name}>{p.name}</div>
                </td>
                <td style={s.td}>
                  <span style={s.slug}>{p.client_slug}</span>
                </td>
                <td style={s.td}>
                  <span style={s.badge}>{STATUS_LABELS[p.status] || p.status}</span>
                </td>
                <td style={s.td}>
                  <span style={{ fontSize: 13, color: T.textGray }}>{p.preset}</span>
                </td>
                <td style={s.td}>
                  <span style={{ fontSize: 13, color: T.textGray }}>{p.vertical}</span>
                </td>
                <td style={{ ...s.td, textAlign: 'right' }}>
                  <div style={{ ...s.actions, justifyContent: 'flex-end' }}>
                    <button
                      style={s.restoreBtn}
                      onClick={() => restoreMutation.mutate(p.id)}
                      disabled={restoreMutation.isPending}
                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = T.success; (e.currentTarget as HTMLButtonElement).style.color = '#fff' }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; (e.currentTarget as HTMLButtonElement).style.color = T.success }}
                    >
                      <i className="fa-solid fa-rotate-left"></i> Ripristina
                    </button>
                    <button
                      style={s.deleteBtn}
                      onClick={() => setConfirmPermanent(p)}
                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = T.error; (e.currentTarget as HTMLButtonElement).style.color = '#fff' }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; (e.currentTarget as HTMLButtonElement).style.color = T.error }}
                    >
                      <i className="fa-solid fa-xmark"></i> Elimina
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {confirmPermanent && (
        <div style={s.modal} onClick={() => setConfirmPermanent(null)}>
          <div style={s.modalBox} onClick={e => e.stopPropagation()}>
            <div style={s.modalTitle}>Eliminare definitivamente?</div>
            <p style={{ fontSize: 14, color: T.textGray, marginBottom: 20, lineHeight: 1.5 }}>
              Il progetto <strong style={{ color: T.text }}>{confirmPermanent.name}</strong> verrà
              eliminato in modo permanente. Questa azione non può essere annullata.
            </p>
            <div style={s.row}>
              <button style={s.cancelBtn} onClick={() => setConfirmPermanent(null)}>Annulla</button>
              <button
                style={s.btn}
                onClick={() => permanentDeleteMutation.mutate(confirmPermanent.id)}
                disabled={permanentDeleteMutation.isPending}
              >
                {permanentDeleteMutation.isPending ? 'Eliminando...' : 'Elimina definitivamente'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
