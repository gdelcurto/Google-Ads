import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '../api/projects'
import { T } from '../styles/theme'

const STATUS_COLORS: Record<string, string> = {
  draft:     T.textGray,
  validated: T.blue,
  preview:   T.warning,
  published: T.success,
  archived:  '#888',
}

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
  h1: { fontSize: 26, fontWeight: 700, color: T.text, letterSpacing: -0.5 },
  btn: {
    background: T.primary,
    color: '#fff',
    border: 'none',
    padding: '10px 20px',
    borderRadius: T.radiusSm,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 14,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: 16,
  },
  card: {
    background: T.bgCard,
    borderRadius: T.radiusLg,
    padding: 24,
    boxShadow: T.shadow,
    textDecoration: 'none',
    color: 'inherit',
    display: 'block',
    border: `1px solid ${T.borderLight}`,
  },
  cardTitle: { fontSize: 15, fontWeight: 700, marginBottom: 4, color: T.text },
  cardSlug: { fontSize: 12, color: T.textGray, marginBottom: 14, letterSpacing: 0.1 },
  badge: {
    display: 'inline-block',
    padding: '3px 10px',
    borderRadius: 20,
    fontSize: 11,
    fontWeight: 700,
    color: '#fff',
    letterSpacing: 0.4,
    textTransform: 'uppercase' as const,
  },
  cardMeta: { fontSize: 12, color: T.textGray, marginTop: 14 },
  cardDivider: {
    height: 1,
    background: T.borderLight,
    margin: '14px 0',
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
    marginBottom: 24,
    color: T.text,
    letterSpacing: -0.3,
  },
  label: { display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: T.text },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm,
    fontSize: 14,
    marginBottom: 16,
    outline: 'none',
    background: T.bgCard,
  },
  select: {
    width: '100%',
    padding: '10px 12px',
    border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm,
    fontSize: 14,
    marginBottom: 16,
    background: T.bgCard,
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
  emptyState: {
    textAlign: 'center' as const,
    padding: '60px 0',
    color: T.textGray,
    fontSize: 14,
  },
}

function CreateProjectModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [preset, setPreset] = useState('blastness')
  const [vertical, setVertical] = useState('city_hotel')
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => projectsApi.create({ name, client_slug: slug, preset, vertical }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['projects'] }); onClose() },
  })

  return (
    <div style={s.modal} onClick={onClose}>
      <div style={s.modalBox} onClick={e => e.stopPropagation()}>
        <div style={s.modalTitle}>Nuovo Progetto</div>
        <label style={s.label}>Nome progetto</label>
        <input
          style={s.input}
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="Grand Hotel Roma – Setup Q2 2024"
          autoFocus
        />
        <label style={s.label}>Slug cliente (URL-safe)</label>
        <input
          style={s.input}
          value={slug}
          onChange={e => setSlug(e.target.value)}
          placeholder="grand-hotel-roma"
        />
        <label style={s.label}>Preset</label>
        <select style={s.select} value={preset} onChange={e => setPreset(e.target.value)}>
          <option value="blastness">Blastness</option>
          <option value="mentefredda">Mentefredda</option>
          <option value="custom">Custom</option>
        </select>
        <label style={s.label}>Verticale</label>
        <select style={s.select} value={vertical} onChange={e => setVertical(e.target.value)}>
          <option value="city_hotel">City Hotel</option>
          <option value="resort">Resort</option>
          <option value="boutique">Boutique</option>
          <option value="business">Business</option>
          <option value="agriturismo">Agriturismo</option>
        </select>
        <div style={s.row}>
          <button style={s.cancelBtn} onClick={onClose}>Annulla</button>
          <button style={s.btn} onClick={() => mutation.mutate()} disabled={!name || !slug}>
            {mutation.isPending ? 'Creando...' : 'Crea progetto'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ProjectsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  return (
    <div>
      <div style={s.header}>
        <h1 style={s.h1}>Progetti Campagne</h1>
        <button style={s.btn} onClick={() => setShowCreate(true)}>+ Nuovo Progetto</button>
      </div>

      {isLoading && <p style={{ color: T.textGray }}>Caricamento...</p>}

      <div style={s.grid}>
        {projects.map(p => (
          <Link key={p.id} to={`/projects/${p.id}`} style={s.card}>
            <div style={s.cardTitle}>{p.name}</div>
            <div style={s.cardSlug}>{p.client_slug} · {p.preset} · {p.vertical}</div>
            <span style={{ ...s.badge, background: STATUS_COLORS[p.status] || T.textGray }}>
              {STATUS_LABELS[p.status] || p.status}
            </span>
            <div style={s.cardDivider} />
            <div style={s.cardMeta}>
              {p.has_brief ? '✓ Brief caricato' : '○ Brief mancante'}
              {' · '}
              {p.has_plan ? '✓ Piano generato' : '○ Piano non generato'}
            </div>
            <div style={{ ...s.cardMeta, marginTop: 4 }}>
              Aggiornato: {new Date(p.updated_at).toLocaleDateString('it-IT')}
            </div>
          </Link>
        ))}
        {!isLoading && projects.length === 0 && (
          <div style={{ ...s.emptyState, gridColumn: '1 / -1' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>○</div>
            <div>Nessun progetto. Crea il primo!</div>
          </div>
        )}
      </div>

      {showCreate && <CreateProjectModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
