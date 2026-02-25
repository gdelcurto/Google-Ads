import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clientsApi, type ClientCreate } from '../api/clients'
import { T } from '../styles/theme'

const s: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 },
  h1: { fontSize: 26, fontWeight: 700, color: T.text, letterSpacing: -0.5 },
  btn: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '10px 20px', borderRadius: T.radiusSm,
    cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnOutline: {
    background: '#fff', color: T.primary,
    border: `1.5px solid ${T.primary}`,
    padding: '7px 16px', borderRadius: T.radiusSm,
    cursor: 'pointer', fontWeight: 600, fontSize: 13,
  },
  card: {
    background: '#fff', borderRadius: T.radius,
    border: `1px solid ${T.borderLight}`,
    padding: '20px 24px',
    display: 'flex', alignItems: 'center', gap: 16,
    boxShadow: T.shadow,
    textDecoration: 'none', color: 'inherit',
    transition: 'box-shadow 0.15s',
  },
  grid: { display: 'flex', flexDirection: 'column', gap: 12 },
  meta: { fontSize: 13, color: T.textGray },
  badge: {
    background: T.bgMuted, color: T.textGray,
    borderRadius: 99, padding: '2px 10px',
    fontSize: 12, fontWeight: 600,
  },
  emptyBox: {
    textAlign: 'center', padding: '64px 24px',
    color: T.textGray, fontSize: 15,
  },
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 3000,
  },
  modal: {
    background: '#fff', borderRadius: T.radiusLg, padding: 32,
    width: 480, maxWidth: '95vw', boxShadow: T.shadowMd,
  },
  field: { marginBottom: 16 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 5 },
  input: {
    width: '100%', boxSizing: 'border-box' as const,
    padding: '9px 12px', borderRadius: T.radiusSm,
    border: `1.5px solid ${T.borderLight}`, fontSize: 14,
    outline: 'none', color: T.text,
  },
  modalActions: { display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 24 },
}

function CreateClientModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<ClientCreate>({
    name: '', bb_client_id: '', agency: '', contact_email: '', contact_phone: '', notes: '',
  })
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => clientsApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] })
      onClose()
    },
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div style={s.overlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={s.modal}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24, color: T.text }}>
          Nuovo cliente
        </h2>

        {error && (
          <div style={{ background: '#fee2e2', color: '#991b1b', padding: '10px 14px', borderRadius: T.radiusSm, marginBottom: 16, fontSize: 13 }}>
            {error}
          </div>
        )}

        <div style={s.field}>
          <label style={s.label}>Nome brand *</label>
          <input style={s.input} value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="es. Hotel Bella Vista" autoFocus />
        </div>
        <div style={s.field}>
          <label style={s.label}>ID Cliente BB</label>
          <input style={s.input} value={form.bb_client_id ?? ''}
            onChange={e => setForm(f => ({ ...f, bb_client_id: e.target.value }))}
            placeholder="es. BL-12345" />
        </div>
        <div style={s.field}>
          <label style={s.label}>Agenzia</label>
          <input style={s.input} value={form.agency ?? ''}
            onChange={e => setForm(f => ({ ...f, agency: e.target.value }))}
            placeholder="es. Blastness" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div style={s.field}>
            <label style={s.label}>Email contatto</label>
            <input style={s.input} type="email" value={form.contact_email ?? ''}
              onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))}
              placeholder="contatto@hotel.it" />
          </div>
          <div style={s.field}>
            <label style={s.label}>Telefono</label>
            <input style={s.input} type="tel" value={form.contact_phone ?? ''}
              onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))}
              placeholder="+39 02 1234567" />
          </div>
        </div>

        <div style={s.modalActions}>
          <button style={s.btnOutline} onClick={onClose}>Annulla</button>
          <button
            style={{ ...s.btn, opacity: !form.name.trim() || mutation.isPending ? 0.6 : 1 }}
            disabled={!form.name.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? 'Creazione...' : 'Crea cliente'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ClientsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const { data: clients = [], isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: clientsApi.list,
  })

  return (
    <div>
      <div style={s.header}>
        <h1 style={s.h1}>Clienti</h1>
        <button style={s.btn} onClick={() => setShowCreate(true)}>
          + Nuovo cliente
        </button>
      </div>

      {isLoading ? (
        <div style={s.emptyBox}>Caricamento...</div>
      ) : clients.length === 0 ? (
        <div style={s.emptyBox}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🏨</div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Nessun cliente ancora</div>
          <div>Crea il primo cliente per iniziare.</div>
        </div>
      ) : (
        <div style={s.grid}>
          {clients.map(c => (
            <Link key={c.id} to={`/clients/${c.id}`} style={s.card}
              onMouseEnter={e => (e.currentTarget.style.boxShadow = T.shadowMd)}
              onMouseLeave={e => (e.currentTarget.style.boxShadow = T.shadow)}
            >
              <div style={{
                width: 42, height: 42, borderRadius: T.radiusSm,
                background: T.bgMuted, display: 'flex', alignItems: 'center',
                justifyContent: 'center', flexShrink: 0,
              }}>
                <i className="fa-solid fa-building" style={{ fontSize: 18, color: T.primary }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: T.text, marginBottom: 3 }}>
                  {c.name}
                </div>
                <div style={s.meta}>
                  {c.agency && <span>{c.agency} · </span>}
                  {c.contact_email && <span>{c.contact_email} · </span>}
                  {c.bb_client_id && <span>BB: {c.bb_client_id}</span>}
                </div>
              </div>
              <span style={s.badge}>
                {c.hotels_count} {c.hotels_count === 1 ? 'hotel' : 'hotel'}
              </span>
            </Link>
          ))}
        </div>
      )}

      {showCreate && <CreateClientModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
