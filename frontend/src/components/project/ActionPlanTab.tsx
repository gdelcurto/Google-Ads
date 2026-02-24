import { useState } from 'react'
import { T } from '../../styles/theme'
import { CAMPAIGN_STRATEGY, TYPE_COLOR } from './constants'
import { exportToDocx } from './exportDocx'

const btnOutline: React.CSSProperties = {
  background: 'transparent', color: T.text, border: `1px solid ${T.border}`,
  padding: '8px 18px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
}

export function ActionPlanTab({ brief }: { brief: Record<string, unknown> }) {
  const [exportingDocx, setExportingDocx] = useState(false)

  const handleExportDocx = async () => {
    setExportingDocx(true)
    try { await exportToDocx(brief) } finally { setExportingDocx(false) }
  }

  const client  = (brief.client           || {}) as Record<string, unknown>
  const hotel   = (brief.hotel_specifics  || {}) as Record<string, unknown>
  const loc     = (hotel.location         || {}) as Record<string, unknown>
  const budgets = (brief.budgets          || {}) as Record<string, unknown>
  const obj     = (brief.objectives       || {}) as Record<string, unknown>
  const kpi     = (obj.kpi               || {}) as Record<string, unknown>
  const byCT    = (budgets.by_campaign_type || {}) as Record<string, { total: number; by_language: Record<string, number> }>
  const campaignTypes = (brief.campaign_types || []) as string[]
  const languages     = (brief.languages      || []) as Record<string, unknown>[]

  const brandName    = (client.brand_name      || 'Hotel') as string
  const category     = (hotel.category         || 'Hotel') as string
  const stars        = (hotel.stars            || 0) as number
  const address      = (loc.address            || '') as string
  const totalMonthly = (budgets.total_monthly_eur || 0) as number
  const targetCpa    = kpi.target_cpa_eur as number | null
  const targetRoas   = kpi.target_roas    as number | null
  const today        = new Date().toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' })

  const orderedTypes = [...campaignTypes].sort((a, b) =>
    ((CAMPAIGN_STRATEGY[a]?.priority ?? 99) - (CAMPAIGN_STRATEGY[b]?.priority ?? 99))
  )

  const typeRows = orderedTypes.map(t => {
    const monthlyAmt = byCT[t]?.total ?? 0
    const pct = totalMonthly > 0 ? (monthlyAmt / totalMonthly) * 100 : 0
    return { type: t, monthlyAmt, pct }
  })

  const firstLang = languages[0] as Record<string, unknown> | undefined
  const getTypeCopy = (t: string): string[] => {
    if (!firstLang) return []
    const assetMap: Record<string, string> = {
      search_brand:       'brand_assets',
      search_acquisition: 'acquisition_assets',
      retargeting:        'retargeting_assets',
    }
    const assetKey = assetMap[t]
    const typeAssets = assetKey ? (firstLang[assetKey] as Record<string, unknown> | undefined) : undefined
    const typeHl = typeAssets?.headlines as string[] | undefined
    if (typeHl?.length) return typeHl.slice(0, 4)
    return (firstLang.headlines as string[] | undefined)?.slice(0, 4) ?? []
  }

  const SG = "'Space Grotesk', sans-serif"
  const docStyle: React.CSSProperties = { maxWidth: 860, margin: '0 auto', fontFamily: SG, color: '#1a1a1a' }
  const sectionStyle: React.CSSProperties = { marginBottom: 36, paddingBottom: 32, borderBottom: `1px solid #e0e0e0` }
  const h2Style: React.CSSProperties = {
    fontSize: 13, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' as const,
    color: T.primary, marginBottom: 16, fontFamily: SG,
  }
  const bodyText: React.CSSProperties = { fontSize: 14, lineHeight: 1.75, color: '#333', fontFamily: SG }

  return (
    <div style={docStyle}>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 24, gap: 10 }}>
        <button style={{ ...btnOutline, fontSize: 13 }} onClick={handleExportDocx} disabled={exportingDocx}>
          {exportingDocx ? '⏳ Generazione…' : '📄 Esporta Word'}
        </button>
      </div>

      {/* ═══ 1. INTESTAZIONE ═══ */}
      <div style={{ ...sectionStyle, textAlign: 'center', paddingBottom: 28 }}>
        <div style={{ fontSize: 11, letterSpacing: 3, textTransform: 'uppercase' as const, color: T.textGray, marginBottom: 8, fontFamily: SG }}>
          Piano Strategico Google Ads
        </div>
        <h1 style={{ fontSize: 32, fontWeight: 700, color: '#111', margin: '0 0 8px', letterSpacing: -0.5 }}>
          {brandName}
        </h1>
        <div style={{ fontSize: 15, color: T.textGray, marginBottom: 6, fontFamily: SG }}>
          {category}{stars > 0 ? ` · ${'★'.repeat(stars)}` : ''}{address ? ` · ${address}` : ''}
        </div>
        <div style={{ fontSize: 12, color: T.textGray, fontFamily: SG }}>
          Preparato il {today}
          {languages.length > 0 && ` · Mercati: ${languages.map(l => (l as Record<string,unknown>).code as string).join(', ')}`}
        </div>
        <div style={{ display: 'inline-block', marginTop: 14, padding: '4px 16px', background: '#f5f5f5', borderRadius: 20, fontSize: 11, color: T.textGray, fontFamily: SG, letterSpacing: 1 }}>
          DOCUMENTO RISERVATO — USO INTERNO E CLIENTE
        </div>
      </div>

      {/* ═══ 2. SCENARIO D'INVESTIMENTO ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Scenario d'investimento</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 20 }}>
          {[
            { label: 'Budget mensile', value: `€${totalMonthly.toLocaleString('it-IT')}`, sub: 'investimento totale' },
            { label: 'Budget giornaliero', value: `€${Math.round(totalMonthly / 30.44).toLocaleString('it-IT')}`, sub: 'media al giorno' },
            { label: 'Campagne attive', value: String(orderedTypes.length), sub: 'tipologie' },
            { label: 'Lingue / Mercati', value: String(languages.length), sub: languages.map(l => (l as Record<string,unknown>).code as string).join(', ') },
            ...(targetRoas ? [{ label: 'ROAS target', value: `${targetRoas}:1`, sub: 'ritorno sull\'investimento' }] : []),
            ...(targetCpa  ? [{ label: 'CPA target', value: `€${targetCpa}`, sub: 'costo per prenotazione' }] : []),
          ].map((card, i) => (
            <div key={i} style={{ background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: 10, padding: '16px 18px', fontFamily: SG }}>
              <div style={{ fontSize: 11, color: T.textGray, letterSpacing: 0.5, textTransform: 'uppercase' as const, marginBottom: 4 }}>{card.label}</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: T.primary }}>{card.value}</div>
              <div style={{ fontSize: 11, color: T.textGray, marginTop: 2 }}>{card.sub}</div>
            </div>
          ))}
        </div>
        <p style={bodyText}>
          Il piano prevede un approccio <strong>full-funnel</strong> con {orderedTypes.length} tipologie di campagna Google Ads,
          attivate in ordine di priorità d'intento: dalla protezione del brand fino alla generazione di domanda.
          L'obiettivo primario è incrementare le prenotazioni dirette riducendo la dipendenza dalle OTA (Booking.com, Expedia)
          e migliorare il ritorno sull'investimento pubblicitario.
        </p>
      </div>

      {/* ═══ 3. MIX DI CAMPAGNE ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Mix di campagne consigliato</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: SG }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #111' }}>
                {['Priorità', 'Campagna', 'Funnel', 'Budget/mese', '% tot.', 'Budget/giorno'].map((h, i) => (
                  <th key={i} style={{ padding: '8px 12px', textAlign: i < 2 ? 'left' : 'center', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color: T.textGray }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {typeRows.map(({ type, monthlyAmt, pct }, i) => {
                const info = CAMPAIGN_STRATEGY[type]
                const color = TYPE_COLOR[type] || T.primary
                return (
                  <tr key={type} style={{ borderBottom: '1px solid #e8e8e8', background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                    <td style={{ padding: '12px', textAlign: 'center', color: T.textGray, fontSize: 12, fontWeight: 700 }}>{info?.priority ?? i + 1}</td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
                        <strong style={{ color: '#111' }}>{info?.label ?? type}</strong>
                      </div>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <span style={{ background: info?.funnelColor ?? color, color: '#fff', borderRadius: 12, fontSize: 10, padding: '2px 10px', fontWeight: 700, whiteSpace: 'nowrap' as const }}>
                        {info?.funnel ?? '—'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center', fontWeight: 700, fontSize: 15 }}>€{Math.round(monthlyAmt).toLocaleString('it-IT')}</td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' }}>
                        <div style={{ width: 60, height: 6, background: '#e8e8e8', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
                        </div>
                        <span style={{ fontSize: 12, color: T.textGray, minWidth: 32 }}>{pct.toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center', color: T.textGray, fontSize: 13 }}>€{Math.round(monthlyAmt / 30.44).toLocaleString('it-IT')}/g</td>
                  </tr>
                )
              })}
              <tr style={{ borderTop: '2px solid #111', background: '#f5f5f5' }}>
                <td colSpan={3} style={{ padding: '10px 12px', fontWeight: 700, fontSize: 13 }}>TOTALE</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 800, fontSize: 16, color: T.primary }}>€{Math.round(totalMonthly).toLocaleString('it-IT')}</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 700 }}>100%</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', color: T.textGray, fontWeight: 700 }}>€{Math.round(totalMonthly / 30.44).toLocaleString('it-IT')}/g</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ═══ 4. DETTAGLIO CAMPAGNE ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Dettaglio delle campagne</div>
        {orderedTypes.map((type, idx) => {
          const info = CAMPAIGN_STRATEGY[type]
          const color = TYPE_COLOR[type] || T.primary
          const monthly = typeRows.find(r => r.type === type)?.monthlyAmt ?? 0
          const sampleCopy = getTypeCopy(type)
          return (
            <div key={type} style={{ marginBottom: 28, paddingBottom: 28, borderBottom: idx < orderedTypes.length - 1 ? '1px dashed #e0e0e0' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
                <div style={{ width: 40, height: 40, borderRadius: 8, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 12, flexShrink: 0, fontFamily: SG }}>
                  {info?.priority ?? idx + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' as const, marginBottom: 4 }}>
                    <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#111', fontFamily: SG }}>{info?.label ?? type}</h3>
                    <span style={{ background: info?.funnelColor ?? color, color: '#fff', borderRadius: 12, fontSize: 10, padding: '2px 10px', fontWeight: 700, fontFamily: SG }}>{info?.funnel ?? '—'}</span>
                    <span style={{ fontSize: 13, color: T.primary, fontWeight: 700, fontFamily: SG }}>€{Math.round(monthly).toLocaleString('it-IT')}/mese</span>
                  </div>
                </div>
              </div>
              <p style={{ ...bodyText, marginBottom: 14 }}>{info?.description ?? ''}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14, fontFamily: SG }}>
                {[
                  { label: 'Target audience', value: info?.audience ?? '' },
                  { label: 'KPI & obiettivi', value: info?.kpi ?? '' },
                  { label: 'Formato annunci', value: info?.formats ?? '' },
                  { label: 'Investimento', value: `€${Math.round(monthly).toLocaleString('it-IT')}/mese · €${Math.round(monthly/30.44).toLocaleString('it-IT')}/giorno` },
                ].map((item, i) => (
                  <div key={i} style={{ background: '#fafafa', border: '1px solid #ebebeb', borderRadius: 6, padding: '10px 14px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color: T.textGray, marginBottom: 4 }}>{item.label}</div>
                    <div style={{ fontSize: 13, color: '#333', lineHeight: 1.5 }}>{item.value}</div>
                  </div>
                ))}
              </div>
              {sampleCopy.length > 0 && (
                <div style={{ background: `${color}0d`, border: `1px solid ${color}33`, borderRadius: 8, padding: '12px 16px', fontFamily: SG }}>
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color, marginBottom: 8 }}>
                    Messaggi chiave — {(firstLang?.code as string) || 'IT'}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 6 }}>
                    {sampleCopy.map((h, i) => (
                      <span key={i} style={{ background: '#fff', border: `1px solid ${color}44`, borderRadius: 4, fontSize: 12, padding: '3px 10px', color: '#222' }}>{h}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* ═══ 5. MERCATI E LINGUE ═══ */}
      {languages.length > 0 && (
        <div style={sectionStyle}>
          <div style={h2Style}>Mercati e lingue</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: SG }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #111' }}>
                {['Lingua', 'Landing page', 'Headline campionatura', 'Brand terms'].map((h, i) => (
                  <th key={i} style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color: T.textGray }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {languages.map((lang, i) => {
                const l = lang as Record<string, unknown>
                const hl = (l.headlines as string[] | undefined) ?? []
                const bt = (l.brand_terms as string[] | undefined) ?? []
                return (
                  <tr key={i} style={{ borderBottom: '1px solid #e8e8e8', background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 700 }}>{l.code as string} — {l.name as string}</td>
                    <td style={{ padding: '10px 12px', color: T.textGray, fontSize: 12 }}>{(l.landing_page as string | undefined) || '—'}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#444' }}>{hl.slice(0, 2).join(' · ') || '—'}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#444' }}>{bt.slice(0, 3).join(', ') || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ═══ 6. PROSSIMI PASSI ═══ */}
      <div style={{ ...sectionStyle, borderBottom: 'none' }}>
        <div style={h2Style}>Prossimi passi</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10, fontFamily: SG }}>
          {[
            { step: '01', title: 'Approvazione piano', desc: 'Revisione e firma del preventivo da parte del cliente' },
            { step: '02', title: 'Setup account Google Ads', desc: 'Configurazione customer ID, conversioni, tag, FLOODLIGHT' },
            { step: '03', title: 'Caricamento asset visivi', desc: 'Immagini per Performance Max e Retargeting (se attivi)' },
            { step: '04', title: 'Attivazione Brand + Acquisition', desc: 'Prima le campagne ad alto intento, poi le altre' },
            { step: '05', title: 'Periodo di apprendimento', desc: '4–6 settimane per ottimizzazione automatica Google' },
            { step: '06', title: 'Primo report risultati', desc: 'Analisi KPI, ROAS e aggiustamenti strategici' },
          ].map(item => (
            <div key={item.step} style={{ background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: 8, padding: '14px 16px', display: 'flex', gap: 12 }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: T.primary, flexShrink: 0 }}>{item.step}</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{item.title}</div>
                <div style={{ fontSize: 12, color: T.textGray, lineHeight: 1.5 }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 36, paddingTop: 20, borderTop: '1px solid #e8e8e8', textAlign: 'center', fontSize: 11, color: '#aaa', fontFamily: SG, letterSpacing: 0.5 }}>
          Documento generato da Google Ads Planner · {brandName} · {today}
        </div>
      </div>
    </div>
  )
}
