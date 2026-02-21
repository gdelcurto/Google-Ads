import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '../api/projects'

const STATUS_COLORS: Record<string, string> = {
  draft: '#94a3b8',
  validated: '#3b82f6',
  preview: '#f59e0b',
  published: '#10b981',
  archived: '#6b7280',
}

const s: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 },
  h1: { fontSize: 24, fontWeight: 700, color: '#1e3a5f' },
  btn: { background: '#1e3a5f', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: 6, cursor: 'pointer', fontWeight: 600 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 20 },
  card: { background: '#fff', borderRadius: 8, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', textDecoration: 'none', color: 'inherit', display: 'block' },
  cardTitle: { fontSize: 16, fontWeight: 700, marginBottom: 6, color: '#1e3a5f' },
  cardSlug: { fontSize: 12, color: '#64748b', marginBottom: 12 },
  badge: { display: 'inline-block', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, color: '#fff' },
  cardMeta: { fontSize: 12, color: '#94a3b8', marginTop: 12 },
  modal: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  modalBox: { background: '#fff', borderRadius: 8, padding: 32, width: 420, boxShadow: '0 4px 32px rgba(0,0,0,0.18)' },
  modalTitle: { fontSize: 18, fontWeight: 700, marginBottom: 20, color: '#1e3a5f' },
  label: { display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4, color: '#374151' },
  input: { width: '100%', padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 14, marginBottom: 16 },
  select: { width: '100%', padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 14, marginBottom: 16 },
  row: { display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 8 },
  cancelBtn: { background: '#f1f5f9', color: '#374151', border: 'none', padding: '9px 18px', borderRadius: 6, cursor: 'pointer' },
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
        <input style={s.input} value={name} onChange={e => setName(e.target.value)} placeholder="Grand Hotel Roma – Setup Q2 2024" />
        <label style={s.label}>Slug cliente (URL-safe)</label>
        <input style={s.input} value={slug} onChange={e => setSlug(e.target.value)} placeholder="grand-hotel-roma" />
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

      {isLoading && <p>Caricamento...</p>}

      <div style={s.grid}>
        {projects.map(p => (
          <Link key={p.id} to={`/projects/${p.id}`} style={s.card}>
            <div style={s.cardTitle}>{p.name}</div>
            <div style={s.cardSlug}>{p.client_slug} · {p.preset} · {p.vertical}</div>
            <span style={{ ...s.badge, background: STATUS_COLORS[p.status] || '#94a3b8' }}>
              {p.status}
            </span>
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
          <p style={{ color: '#64748b' }}>Nessun progetto. Crea il primo!</p>
        )}
      </div>

      {showCreate && <CreateProjectModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
