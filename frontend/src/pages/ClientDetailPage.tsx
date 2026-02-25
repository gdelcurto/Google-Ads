import { useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clientsApi, type Hotel, type HotelCreate, type SeasonalityPeriod } from '../api/clients'
import { T } from '../styles/theme'
import { useHeaderActions } from '../contexts/HeaderActionsContext'

// ── styles ───────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 },
  h1: { fontSize: 24, fontWeight: 700, color: T.text, letterSpacing: -0.5 },
  sub: { fontSize: 13, color: T.textGray, marginTop: 3 },
  btn: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '9px 18px', borderRadius: T.radiusSm,
    cursor: 'pointer', fontWeight: 600, fontSize: 13,
  },
  btnOutline: {
    background: '#fff', color: T.primary, border: `1.5px solid ${T.primary}`,
    padding: '7px 14px', borderRadius: T.radiusSm,
    cursor: 'pointer', fontWeight: 600, fontSize: 13,
  },
  btnGhost: {
    background: 'transparent', color: T.textGray, border: `1px solid ${T.borderLight}`,
    padding: '5px 12px', borderRadius: T.radiusSm,
    cursor: 'pointer', fontWeight: 500, fontSize: 12,
  },
  btnDanger: {
    background: '#fff', color: T.error, border: `1px solid ${T.error}`,
    padding: '5px 12px', borderRadius: T.radiusSm,
    cursor: 'pointer', fontWeight: 500, fontSize: 12,
  },
  section: {
    background: '#fff', borderRadius: T.radius,
    border: `1px solid ${T.borderLight}`, padding: '20px 24px',
    marginBottom: 20, boxShadow: T.shadow,
  },
  sectionTitle: { fontSize: 16, fontWeight: 700, color: T.text, marginBottom: 16 },
  hotelCard: {
    border: `1px solid ${T.borderLight}`, borderRadius: T.radiusSm,
    padding: '16px 20px', marginBottom: 12,
    background: T.bgMuted,
  },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 },
  grid3: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 },
  field: { marginBottom: 0 },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: T.textGray, marginBottom: 4, textTransform: 'uppercase' as const, letterSpacing: 0.5 },
  input: {
    width: '100%', boxSizing: 'border-box' as const,
    padding: '8px 11px', borderRadius: T.radiusSm,
    border: `1.5px solid ${T.borderLight}`, fontSize: 13,
    color: T.text, outline: 'none',
  },
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.38)',
    display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
    zIndex: 3000, padding: '40px 24px', overflowY: 'auto',
  },
  modal: {
    background: '#fff', borderRadius: T.radiusLg, padding: 32,
    width: 680, maxWidth: '100%', boxShadow: T.shadowMd,
    marginBottom: 40,
  },
  periodCard: {
    border: `1px solid ${T.borderLight}`, borderRadius: T.radiusSm,
    padding: '14px 16px', marginBottom: 10, background: '#fafafa',
  },
  tagInput: {
    display: 'flex', flexWrap: 'wrap' as const, gap: 6,
    border: `1.5px solid ${T.borderLight}`, borderRadius: T.radiusSm,
    padding: '6px 10px', minHeight: 38,
    background: '#fff', cursor: 'text',
  },
  tag: {
    background: T.bgMuted, border: `1px solid ${T.borderLight}`,
    borderRadius: 4, padding: '2px 8px', fontSize: 12,
    display: 'flex', alignItems: 'center', gap: 4,
  },
}

// ── TagInput (for multi-value list fields) ────────────────────────────────────

function TagInput({ values, onChange, placeholder }: {
  values: string[]
  onChange: (v: string[]) => void
  placeholder?: string
}) {
  const [inputVal, setInputVal] = useState('')
  return (
    <div style={s.tagInput} onClick={() => document.getElementById('_tag_input')?.focus()}>
      {values.map((v, i) => (
        <span key={i} style={s.tag}>
          {v}
          <button
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: 11, color: T.textGray }}
            onClick={e => { e.stopPropagation(); onChange(values.filter((_, j) => j !== i)) }}
          >✕</button>
        </span>
      ))}
      <input
        id="_tag_input"
        style={{ border: 'none', outline: 'none', fontSize: 13, flex: 1, minWidth: 80, padding: '2px 0' }}
        value={inputVal}
        placeholder={values.length === 0 ? placeholder : ''}
        onChange={e => setInputVal(e.target.value)}
        onKeyDown={e => {
          if ((e.key === 'Enter' || e.key === ',') && inputVal.trim()) {
            e.preventDefault()
            onChange([...values, inputVal.trim().toUpperCase()])
            setInputVal('')
          }
          if (e.key === 'Backspace' && !inputVal && values.length > 0) {
            onChange(values.slice(0, -1))
          }
        }}
      />
    </div>
  )
}

// ── Seasonality period editor ─────────────────────────────────────────────────

function emptyPeriod(): SeasonalityPeriod {
  return {
    name: '', date_from: '', date_to: '',
    avg_occupancy_pct: null, target_markets: [],
    booking_channels: [], direct_booking_pct: null,
  }
}

function SeasonalityEditor({ periods, onChange }: {
  periods: SeasonalityPeriod[]
  onChange: (p: SeasonalityPeriod[]) => void
}) {
  const update = (i: number, patch: Partial<SeasonalityPeriod>) =>
    onChange(periods.map((p, j) => j === i ? { ...p, ...patch } : p))

  return (
    <div>
      {periods.map((p, i) => (
        <div key={i} style={s.periodCard}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: T.text }}>
              Periodo {i + 1}
            </span>
            <button style={s.btnDanger} onClick={() => onChange(periods.filter((_, j) => j !== i))}>
              Rimuovi
            </button>
          </div>
          <div style={{ ...s.grid3, marginBottom: 10 }}>
            <div style={s.field}>
              <label style={s.label}>Nome periodo</label>
              <input style={s.input} value={p.name}
                onChange={e => update(i, { name: e.target.value })}
                placeholder="es. Alta stagione" />
            </div>
            <div style={s.field}>
              <label style={s.label}>Dal (MM-GG)</label>
              <input style={s.input} value={p.date_from}
                onChange={e => update(i, { date_from: e.target.value })}
                placeholder="06-01" maxLength={5} />
            </div>
            <div style={s.field}>
              <label style={s.label}>Al (MM-GG)</label>
              <input style={s.input} value={p.date_to}
                onChange={e => update(i, { date_to: e.target.value })}
                placeholder="08-31" maxLength={5} />
            </div>
          </div>
          <div style={{ ...s.grid2, marginBottom: 10 }}>
            <div style={s.field}>
              <label style={s.label}>Tasso occupazione medio (%)</label>
              <input style={s.input} type="number" min={0} max={100}
                value={p.avg_occupancy_pct ?? ''}
                onChange={e => update(i, { avg_occupancy_pct: e.target.value ? Number(e.target.value) : null })}
                placeholder="es. 82" />
            </div>
            <div style={s.field}>
              <label style={s.label}>% prenotazioni dirette</label>
              <input style={s.input} type="number" min={0} max={100}
                value={p.direct_booking_pct ?? ''}
                onChange={e => update(i, { direct_booking_pct: e.target.value ? Number(e.target.value) : null })}
                placeholder="es. 25" />
            </div>
          </div>
          <div style={{ marginBottom: 10 }}>
            <label style={s.label}>Mercati target (Paesi ISO-2 — premi Invio per aggiungere)</label>
            <TagInput
              values={p.target_markets}
              onChange={v => update(i, { target_markets: v })}
              placeholder="IT, DE, GB..."
            />
          </div>
          <div>
            <label style={s.label}>Canali di prenotazione (premi Invio per aggiungere)</label>
            <TagInput
              values={p.booking_channels}
              onChange={v => update(i, { booking_channels: v })}
              placeholder="booking.com, expedia, direct..."
            />
          </div>
        </div>
      ))}
      <button style={s.btnGhost} onClick={() => onChange([...periods, emptyPeriod()])}>
        + Aggiungi periodo stagionale
      </button>
    </div>
  )
}

// ── Hotel form modal ──────────────────────────────────────────────────────────

function HotelModal({
  clientId,
  hotel,
  onClose,
}: {
  clientId: string
  hotel?: Hotel
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState<HotelCreate>({
    name:          hotel?.name ?? '',
    bb_hotel_id:   hotel?.bb_hotel_id ?? '',
    category:      hotel?.category ?? 'city_hotel',
    stars:         hotel?.stars ?? 0,
    address:       hotel?.address ?? '',
    city:          hotel?.city ?? '',
    country:       hotel?.country ?? '',
    country_code:  hotel?.country_code ?? '',
    website_url:   hotel?.website_url ?? '',
    booking_engine: hotel?.booking_engine ?? '',
    property_type: hotel?.property_type ?? '',
    adr:           hotel?.adr ?? null,
    seasonality:   hotel?.seasonality ?? [],
  })
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: () => clientsApi.createHotel(clientId, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['client', clientId] }); onClose() },
    onError: (e: Error) => setError(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: () => clientsApi.updateHotel(hotel!.id, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['client', clientId] }); onClose() },
    onError: (e: Error) => setError(e.message),
  })

  const isPending = createMutation.isPending || updateMutation.isPending
  const save = () => hotel ? updateMutation.mutate() : createMutation.mutate()

  const set = (k: keyof HotelCreate, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div style={s.overlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={s.modal}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24, color: T.text }}>
          {hotel ? 'Modifica hotel' : 'Nuovo hotel'}
        </h2>

        {error && (
          <div style={{ background: '#fee2e2', color: '#991b1b', padding: '10px 14px', borderRadius: T.radiusSm, marginBottom: 16, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* ── Base info ── */}
        <div style={{ ...s.grid2, marginBottom: 12 }}>
          <div style={s.field}>
            <label style={s.label}>Nome hotel *</label>
            <input style={s.input} value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="Hotel Bella Vista" autoFocus />
          </div>
          <div style={s.field}>
            <label style={s.label}>ID Hotel BB</label>
            <input style={s.input} value={form.bb_hotel_id ?? ''}
              onChange={e => set('bb_hotel_id', e.target.value)}
              placeholder="BL-HTL-001" />
          </div>
        </div>

        <div style={{ ...s.grid3, marginBottom: 12 }}>
          <div style={s.field}>
            <label style={s.label}>Categoria</label>
            <select style={{ ...s.input, cursor: 'pointer' }} value={form.category ?? ''}
              onChange={e => set('category', e.target.value)}>
              <option value="city_hotel">City Hotel</option>
              <option value="resort">Resort</option>
              <option value="boutique">Boutique</option>
              <option value="business">Business</option>
              <option value="agriturismo">Agriturismo</option>
            </select>
          </div>
          <div style={s.field}>
            <label style={s.label}>Stelle</label>
            <input style={s.input} type="number" min={0} max={5}
              value={form.stars ?? ''}
              onChange={e => set('stars', Number(e.target.value))}
              placeholder="4" />
          </div>
          <div style={s.field}>
            <label style={s.label}>ADR (€/notte)</label>
            <input style={s.input} type="number" min={0}
              value={form.adr ?? ''}
              onChange={e => set('adr', e.target.value ? Number(e.target.value) : null)}
              placeholder="180" />
          </div>
        </div>

        <div style={{ ...s.grid2, marginBottom: 12 }}>
          <div style={s.field}>
            <label style={s.label}>Indirizzo</label>
            <input style={s.input} value={form.address ?? ''}
              onChange={e => set('address', e.target.value)}
              placeholder="Via Roma 1" />
          </div>
          <div style={s.field}>
            <label style={s.label}>Città</label>
            <input style={s.input} value={form.city ?? ''}
              onChange={e => set('city', e.target.value)}
              placeholder="Milano" />
          </div>
          <div style={s.field}>
            <label style={s.label}>Paese</label>
            <input style={s.input} value={form.country ?? ''}
              onChange={e => set('country', e.target.value)}
              placeholder="Italia" />
          </div>
          <div style={s.field}>
            <label style={s.label}>Codice paese (ISO-2)</label>
            <input style={s.input} value={form.country_code ?? ''}
              onChange={e => set('country_code', e.target.value.toUpperCase().slice(0, 2))}
              maxLength={2} placeholder="IT" />
          </div>
        </div>

        <div style={{ ...s.grid2, marginBottom: 20 }}>
          <div style={s.field}>
            <label style={s.label}>Website URL</label>
            <input style={s.input} value={form.website_url ?? ''}
              onChange={e => set('website_url', e.target.value)}
              placeholder="https://www.hotelbella.it" />
          </div>
          <div style={s.field}>
            <label style={s.label}>Booking engine</label>
            <input style={s.input} value={form.booking_engine ?? ''}
              onChange={e => set('booking_engine', e.target.value)}
              placeholder="Booking Suite, Siteminder..." />
          </div>
        </div>

        {/* ── Seasonality ── */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: T.text, marginBottom: 12, borderTop: `1px solid ${T.borderLight}`, paddingTop: 16 }}>
            Stagionalità
          </div>
          <SeasonalityEditor
            periods={form.seasonality ?? []}
            onChange={v => set('seasonality', v)}
          />
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button style={s.btnOutline} onClick={onClose}>Annulla</button>
          <button
            style={{ ...s.btn, opacity: !form.name.trim() || isPending ? 0.6 : 1 }}
            disabled={!form.name.trim() || isPending}
            onClick={save}
          >
            {isPending ? 'Salvataggio...' : hotel ? 'Salva modifiche' : 'Crea hotel'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [hotelModal, setHotelModal] = useState<'new' | Hotel | null>(null)
  const [editClient, setEditClient] = useState(false)
  const [clientForm, setClientForm] = useState<{ name: string; bb_client_id: string; agency: string; contact_email: string; contact_phone: string; notes: string } | null>(null)
  const [saveMsg, setSaveMsg] = useState('')

  const { data: client, isLoading } = useQuery({
    queryKey: ['client', id],
    queryFn: () => clientsApi.get(id!),
    enabled: !!id,
  })

  const deleteHotelMutation = useMutation({
    mutationFn: (hotelId: string) => clientsApi.deleteHotel(hotelId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['client', id] }),
  })

  const updateClientMutation = useMutation({
    mutationFn: () => clientsApi.update(id!, clientForm!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client', id] })
      qc.invalidateQueries({ queryKey: ['clients'] })
      setEditClient(false)
      setSaveMsg('Salvato')
      setTimeout(() => setSaveMsg(''), 2500)
    },
  })

  const startEditClient = useCallback(() => {
    if (!client) return
    setClientForm({
      name: client.name,
      bb_client_id: client.bb_client_id ?? '',
      agency: client.agency ?? '',
      contact_email: client.contact_email ?? '',
      contact_phone: client.contact_phone ?? '',
      notes: client.notes ?? '',
    })
    setEditClient(true)
  }, [client])

  useHeaderActions(
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      {saveMsg && <span style={{ fontSize: 13, color: T.success }}>{saveMsg}</span>}
      <button style={s.btnGhost} onClick={startEditClient}>
        <i className="fa-solid fa-pen" /> Modifica
      </button>
      <button style={s.btn} onClick={() => setHotelModal('new')}>
        + Nuovo hotel
      </button>
    </div>,
    [saveMsg, startEditClient],
  )

  if (isLoading) return <div style={{ padding: 40, color: T.textGray }}>Caricamento...</div>
  if (!client) return <div style={{ padding: 40, color: T.error }}>Cliente non trovato</div>

  return (
    <div style={{ maxWidth: 860 }}>
      {/* ── Header ── */}
      <div style={s.header}>
        <div>
          <div style={{ fontSize: 13, color: T.textGray, marginBottom: 4 }}>
            <Link to="/clients" style={{ color: T.textGray, textDecoration: 'none' }}>
              ← Clienti
            </Link>
          </div>
          <h1 style={s.h1}>{client.name}</h1>
          <div style={s.sub}>
            {client.agency && <span>{client.agency} · </span>}
            {client.bb_client_id && <span>BB: {client.bb_client_id} · </span>}
            {client.contact_email}
          </div>
        </div>
      </div>

      {/* ── Client edit inline ── */}
      {editClient && clientForm && (
        <div style={{ ...s.section, borderColor: T.primary }}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 16 }}>Modifica cliente</div>
          <div style={{ ...s.grid2, marginBottom: 12 }}>
            <div>
              <label style={s.label}>Nome brand *</label>
              <input style={s.input} value={clientForm.name}
                onChange={e => setClientForm(f => ({ ...f!, name: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>ID Cliente BB</label>
              <input style={s.input} value={clientForm.bb_client_id}
                onChange={e => setClientForm(f => ({ ...f!, bb_client_id: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>Agenzia</label>
              <input style={s.input} value={clientForm.agency}
                onChange={e => setClientForm(f => ({ ...f!, agency: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>Email contatto</label>
              <input style={s.input} value={clientForm.contact_email}
                onChange={e => setClientForm(f => ({ ...f!, contact_email: e.target.value }))} />
            </div>
            <div>
              <label style={s.label}>Telefono</label>
              <input style={s.input} value={clientForm.contact_phone}
                onChange={e => setClientForm(f => ({ ...f!, contact_phone: e.target.value }))} />
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={s.label}>Note</label>
            <textarea style={{ ...s.input, minHeight: 60, resize: 'vertical' }}
              value={clientForm.notes}
              onChange={e => setClientForm(f => ({ ...f!, notes: e.target.value }))} />
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button style={s.btnGhost} onClick={() => setEditClient(false)}>Annulla</button>
            <button style={s.btn}
              disabled={!clientForm.name.trim() || updateClientMutation.isPending}
              onClick={() => updateClientMutation.mutate()}>
              {updateClientMutation.isPending ? 'Salvataggio...' : 'Salva'}
            </button>
          </div>
        </div>
      )}

      {/* ── Hotels ── */}
      <div style={s.section}>
        <div style={s.sectionTitle}>Hotel ({client.hotels.length})</div>

        {client.hotels.length === 0 ? (
          <div style={{ color: T.textGray, fontSize: 14, padding: '16px 0' }}>
            Nessun hotel. Clicca "+ Nuovo hotel" per aggiungerne uno.
          </div>
        ) : (
          client.hotels.map(h => (
            <div key={h.id} style={s.hotelCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: T.text, marginBottom: 4 }}>
                    {h.name}
                    {h.stars ? <span style={{ marginLeft: 6, fontSize: 12, color: T.warning }}>{'★'.repeat(h.stars)}</span> : null}
                  </div>
                  <div style={{ fontSize: 13, color: T.textGray, marginBottom: 6 }}>
                    {[h.city, h.country].filter(Boolean).join(', ')}
                    {h.bb_hotel_id && <span> · BB: {h.bb_hotel_id}</span>}
                    {h.adr && <span> · ADR: €{h.adr}/notte</span>}
                    {h.website_url && <span> · <a href={h.website_url} target="_blank" rel="noopener noreferrer" style={{ color: T.blue }}>{h.website_url}</a></span>}
                  </div>
                  {h.seasonality.length > 0 && (
                    <div style={{ fontSize: 12, color: T.textGray }}>
                      {h.seasonality.length} {h.seasonality.length === 1 ? 'periodo stagionale' : 'periodi stagionali'}
                    </div>
                  )}
                  {h.has_scraped_data && (
                    <div style={{ fontSize: 12, color: T.success, marginTop: 2 }}>
                      <i className="fa-solid fa-circle-check" /> Dati scansionati disponibili
                      {h.scraped_at && <span style={{ color: T.textGray }}> · {new Date(h.scraped_at).toLocaleDateString('it-IT')}</span>}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <button style={s.btnGhost} onClick={() => setHotelModal(h)}>
                    <i className="fa-solid fa-pen" /> Modifica
                  </button>
                  <button
                    style={s.btnDanger}
                    onClick={() => {
                      if (confirm(`Eliminare "${h.name}"? L'azione non è reversibile.`))
                        deleteHotelMutation.mutate(h.id)
                    }}
                  >
                    <i className="fa-solid fa-trash" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* ── Modals ── */}
      {hotelModal === 'new' && (
        <HotelModal clientId={id!} onClose={() => setHotelModal(null)} />
      )}
      {hotelModal && hotelModal !== 'new' && (
        <HotelModal clientId={id!} hotel={hotelModal as Hotel} onClose={() => setHotelModal(null)} />
      )}
    </div>
  )
}
