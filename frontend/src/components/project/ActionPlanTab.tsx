import { useState } from 'react'
import { T } from '../../styles/theme'
import { CAMPAIGN_STRATEGY, TYPE_COLOR } from './constants'
import { exportToDocx } from './exportDocx'
import type { AccountPlanPreview } from '../../api/projects'

// ─── Label mappings ────────────────────────────────────────────────────────────

const VERTICAL_LABEL: Record<string, string> = {
  city_hotel:   'Hotel Urbano',
  resort:       'Resort',
  boutique:     'Boutique Hotel',
  business:     'Business Hotel',
  agriturismo:  'Agriturismo',
}

const OBJECTIVE_LABEL: Record<string, string> = {
  direct_bookings: 'prenotazioni dirette',
  lead_gen:        'generazione di contatti',
  phone_calls:     'chiamate dirette',
  brand_awareness: 'notorietà del brand',
}

const BID_STRATEGY_LABEL: Record<string, string> = {
  maximize_conversions:       'Massimizza Conversioni',
  maximize_conversion_value:  'Massimizza Valore Conversione',
  maximize_clicks:            'Massimizza Click',
  target_impression_share:    'Quota Impressioni Target',
}

// ─── Personalized campaign description ────────────────────────────────────────

function buildCampaignDescription(
  type: string,
  brief: Record<string, unknown>,
): string {
  const client   = (brief.client          || {}) as Record<string, unknown>
  const hotel    = (brief.hotel_specifics || {}) as Record<string, unknown>
  const loc      = (hotel.location        || {}) as Record<string, unknown>
  const langs    = (brief.languages       || []) as Record<string, unknown>[]
  const firstLang = langs[0] as Record<string, unknown> | undefined

  const brand      = (client.brand_name || 'l\'hotel') as string
  const address    = (loc.address       || '') as string
  const category   = (hotel.category   || 'city_hotel') as string
  const services   = (hotel.services   || []) as string[]
  const strengths  = (hotel.strengths  || []) as string[]
  const directPct  = hotel.direct_pct as number | null | undefined
  const vertLabel  = VERTICAL_LABEL[category] || 'Hotel'
  const brandTerms = (firstLang?.brand_terms as string[] | undefined) ?? []
  const obj        = (brief.objectives || {}) as Record<string, unknown>
  const kpi        = (obj.kpi          || {}) as Record<string, unknown>
  const targetRoas = kpi.target_roas as number | null | undefined

  switch (type) {
    case 'search_brand': {
      const terms = brandTerms.slice(0, 3).join(', ')
      const directNote = directPct != null
        ? ` — attualmente solo il ${directPct}% delle prenotazioni avviene in modo diretto`
        : ''
      return (
        `Protegge le ricerche di brand di ${brand} dalle OTA competitor (Booking.com, Expedia, Hotels.com) ` +
        `che fanno bidding sul nome dell'hotel${directNote}. ` +
        (terms ? `Keyword protette: ${terms}. ` : '') +
        `Intercetta utenti con la massima intenzione d'acquisto al CPC più contenuto, ` +
        `garantendo il flusso di prenotazioni dirette e massimizzando il ROAS complessivo dell'account.`
      )
    }
    case 'search_acquisition': {
      const loc2 = address ? ` a ${address}` : ''
      const svc  = services.slice(0, 2).join(', ')
      return (
        `Acquisisce nuovi clienti intercettando viaggiatori in ricerca attiva di ${vertLabel}${loc2}. ` +
        (svc ? `Keyword di categoria, destinazione e servizi (es. ${svc}). ` : '') +
        `Posiziona ${brand} prima delle OTA sulla domanda generica, ` +
        `indirizzando il traffico verso il sito ufficiale invece che verso intermediari.`
      )
    }
    case 'retargeting': {
      const str = strengths.slice(0, 2).join(', ')
      return (
        `Re-intercetta i visitatori del sito di ${brand} che hanno esplorato le camere ` +
        `o il motore di prenotazione senza completare la prenotazione. ` +
        (str ? `Messaggi costruiti sui punti di forza dell'hotel: ${str}. ` : '') +
        `Urgency e rassicurazione per completare il funnel con un CPA inferiore rispetto all'acquisition.`
      )
    }
    case 'performance_max': {
      const roasNote = targetRoas ? ` con ROAS target ${targetRoas}:1` : ''
      return (
        `Scala automaticamente ${brand} su tutti i canali Google ` +
        `(Search, Display, YouTube, Maps, Gmail, Discover)${roasNote}. ` +
        `Smart Bidding che ottimizza la distribuzione del budget verso le conversioni più probabili, ` +
        `amplificando i risultati delle campagne Brand e Acquisition con reach incrementale.`
      )
    }
    case 'demand_gen': {
      const loc2 = address ? ` su audience in-market per ${address}` : ''
      return (
        `Genera notorietà di ${brand} su YouTube, Google Discover e Gmail ` +
        `nella fase pre-ricerca, quando i viaggiatori pianificano la prossima vacanza${loc2}. ` +
        `Alimenta il pool di remarketing e prepara il terreno per le campagne di performance.`
      )
    }
    default:
      return CAMPAIGN_STRATEGY[type]?.description ?? ''
  }
}

// ─── Component ────────────────────────────────────────────────────────────────

const btnOutline: React.CSSProperties = {
  background: 'transparent', color: T.text, border: `1px solid ${T.border}`,
  padding: '8px 18px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
}

export function ActionPlanTab({
  brief,
  plan,
}: {
  brief: Record<string, unknown>
  plan?: AccountPlanPreview | null
}) {
  const [exportingDocx, setExportingDocx] = useState(false)

  const handleExportDocx = async () => {
    setExportingDocx(true)
    try { await exportToDocx(brief) } finally { setExportingDocx(false) }
  }

  // ── Data extraction ──────────────────────────────────────────────────────────
  const client  = (brief.client           || {}) as Record<string, unknown>
  const hotel   = (brief.hotel_specifics  || {}) as Record<string, unknown>
  const loc     = (hotel.location         || {}) as Record<string, unknown>
  const budgets = (brief.budgets          || {}) as Record<string, unknown>
  const obj     = (brief.objectives       || {}) as Record<string, unknown>
  const kpi     = (obj.kpi               || {}) as Record<string, unknown>
  const byCT    = (budgets.by_campaign_type || {}) as Record<string, { total: number; by_language: Record<string, number> }>
  const seas    = (brief.seasonality      || {}) as Record<string, unknown>
  const geo     = (brief.geo_targeting    || {}) as Record<string, unknown>
  const perType = (obj.per_campaign_type  || {}) as Record<string, Record<string, unknown>>
  const creativeAssets = (brief.creative_assets || {}) as Record<string, unknown>

  const campaignTypes = (brief.campaign_types || []) as string[]
  const languages     = (brief.languages      || []) as Record<string, unknown>[]

  // Client / brand
  const brandName    = (client.brand_name      || 'Hotel') as string
  const customerId   = client.google_ads_customer_id as string | undefined

  // Hotel specifics
  const category     = (hotel.category       || 'city_hotel') as string
  const stars        = (hotel.stars          || 0) as number
  const rooms        = hotel.rooms           as number | null | undefined
  const adr          = hotel.adr             as number | null | undefined
  const occupancyRate = hotel.occupancy_rate as number | null | undefined
  const directPct    = hotel.direct_pct      as number | null | undefined
  const services     = (hotel.services       || []) as string[]
  const strengths    = (hotel.strengths      || []) as string[]
  const address      = (loc.address          || '') as string
  const landmarks    = (loc.landmarks_nearby || []) as string[]

  // Vertical label
  const vertLabel = VERTICAL_LABEL[category] || 'Hotel'

  // Objectives
  const primaryObj   = (obj.primary          || 'direct_bookings') as string
  const objLabel     = OBJECTIVE_LABEL[primaryObj] || 'prenotazioni dirette'

  // KPI targets
  const totalMonthly = (budgets.total_monthly_eur || 0) as number
  const targetCpa    = kpi.target_cpa_eur as number | null | undefined
  const targetRoas   = kpi.target_roas    as number | null | undefined

  // Geo context
  const targetCities = (geo.target_cities || []) as string[]

  // Seasonality (root-level SeasonalityInfo)
  const seasEnabled   = (seas.enabled         || false) as boolean
  const peakPeriods   = (seas.peak_periods    || []) as Record<string, unknown>[]
  const lowPeriods    = (seas.low_periods     || []) as Record<string, unknown>[]
  const hasSeasonality = seasEnabled && (peakPeriods.length > 0 || lowPeriods.length > 0)

  // AI advisor warnings from plan
  const agentIssues = (plan?.validation_warnings_structured ?? []).filter(
    w => w.level === 'warning' || w.level === 'info'
  )

  const today = new Date().toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' })

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

  // ── Dynamic next-steps ───────────────────────────────────────────────────────
  const hasPMax      = campaignTypes.includes('performance_max')
  const hasRetargeting = campaignTypes.includes('retargeting')
  const hasDemandGen = campaignTypes.includes('demand_gen')
  const needsVisualAssets = hasPMax || hasRetargeting || hasDemandGen
  const hasVideo     = Boolean(creativeAssets.youtube_video_url)

  const dynamicSteps: { step: string; title: string; desc: string }[] = [
    {
      step: '01',
      title: 'Approvazione piano',
      desc: 'Revisione e firma del preventivo da parte del cliente',
    },
    {
      step: '02',
      title: 'Setup account Google Ads',
      desc:
        `Configurazione customer ID${customerId ? ` (${customerId})` : ''}, ` +
        'conversioni, tag di tracciamento e template UTM',
    },
  ]

  if (needsVisualAssets) {
    const formats = [
      'landscape 1200×628',
      'square 1200×1200',
      hasPMax ? 'portrait 960×1200' : null,
    ].filter(Boolean).join(', ')
    dynamicSteps.push({
      step: '03',
      title: 'Caricamento asset visivi',
      desc:
        `Immagini ${brandName}: ${formats}` +
        (hasVideo ? ' — video YouTube già configurato' : ' + video YouTube consigliato per PMax/Demand Gen'),
    })
  }

  dynamicSteps.push(
    {
      step: String(dynamicSteps.length + 1).padStart(2, '0'),
      title: 'Attivazione campagne',
      desc: 'Lancio in sequenza di priorità: Brand Search → Acquisition → ' + (hasPMax ? 'PMax → ' : '') + (hasRetargeting ? 'Retargeting → ' : '') + (hasDemandGen ? 'Demand Gen' : ''),
    },
    {
      step: String(dynamicSteps.length + 2).padStart(2, '0'),
      title: 'Periodo di apprendimento',
      desc: `4–6 settimane per la calibrazione di Smart Bidding di Google` + (hasSeasonality ? ` — budget programmato sui periodi stagionali` : ''),
    },
    {
      step: String(dynamicSteps.length + 3).padStart(2, '0'),
      title: 'Primo report e ottimizzazione',
      desc:
        `Analisi ROAS${targetRoas ? ` vs target ${targetRoas}:1` : ''}, ` +
        `CPA${targetCpa ? ` vs target €${targetCpa}` : ''} ` +
        'e aggiustamenti strategici con l\'advisor AI',
    },
  )

  // ── Styles ───────────────────────────────────────────────────────────────────
  const SG = "'Space Grotesk', sans-serif"
  const docStyle: React.CSSProperties = { maxWidth: 860, margin: '0 auto', fontFamily: SG, color: '#1a1a1a' }
  const sectionStyle: React.CSSProperties = { marginBottom: 36, paddingBottom: 32, borderBottom: `1px solid #e0e0e0` }
  const h2Style: React.CSSProperties = {
    fontSize: 13, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' as const,
    color: T.primary, marginBottom: 16, fontFamily: SG,
  }
  const bodyText: React.CSSProperties = { fontSize: 14, lineHeight: 1.75, color: '#333', fontFamily: SG }
  const chipStyle: React.CSSProperties = {
    display: 'inline-block', background: '#f0f0f0', borderRadius: 12,
    fontSize: 12, padding: '3px 10px', color: '#444', fontFamily: SG,
  }

  // ── Personalized investment paragraph ─────────────────────────────────────────
  const locationStr = address || (targetCities.length ? targetCities[0] : '')
  const investmentParagraph = (() => {
    const parts: string[] = []
    parts.push(
      `${brandName} — ${vertLabel}${stars > 0 ? ` ${stars}★` : ''}${locationStr ? ` a ${locationStr}` : ''} — ` +
      `affida la gestione delle campagne Google Ads all'obiettivo di massimizzare le ${objLabel}.`
    )
    const hotelDetails: string[] = []
    if (rooms)         hotelDetails.push(`${rooms} camere`)
    if (adr)           hotelDetails.push(`ADR medio €${adr.toLocaleString('it-IT')}`)
    if (occupancyRate) hotelDetails.push(`occupazione attuale ${occupancyRate}%`)
    if (directPct)     hotelDetails.push(`prenotazioni dirette ${directPct}%`)
    if (hotelDetails.length) {
      parts.push(`Con ${hotelDetails.join(', ')}, la strategia punta a incrementare il revenue diretto riducendo la commissione alle OTA.`)
    }
    const kpiParts: string[] = []
    if (targetRoas) kpiParts.push(`ROAS target ${targetRoas}:1`)
    if (targetCpa)  kpiParts.push(`CPA target €${targetCpa}`)
    if (kpiParts.length) {
      parts.push(`Obiettivi di rendimento: ${kpiParts.join(' · ')}.`)
    }
    return parts.join(' ')
  })()

  return (
    <div style={docStyle}>

      {/* Export button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 24, gap: 10 }}>
        <button style={{ ...btnOutline, fontSize: 13 }} onClick={handleExportDocx} disabled={exportingDocx}>
          {exportingDocx ? '⏳ Generazione…' : '📄 Esporta Word'}
        </button>
      </div>

      {/* ═══ 1. INTESTAZIONE ═══ */}
      <div style={{ ...sectionStyle, textAlign: 'center', paddingBottom: 28 }}>
        <div style={{ fontSize: 11, letterSpacing: 3, textTransform: 'uppercase' as const, color: T.textGray, marginBottom: 8, fontFamily: SG }}>
          Piano Strategico Google Ads · Preventivo
        </div>
        <h1 style={{ fontSize: 32, fontWeight: 700, color: '#111', margin: '0 0 8px', letterSpacing: -0.5 }}>
          {brandName}
        </h1>
        <div style={{ fontSize: 15, color: T.textGray, marginBottom: 6, fontFamily: SG }}>
          {vertLabel}{stars > 0 ? ` · ${'★'.repeat(stars)}` : ''}{locationStr ? ` · ${locationStr}` : ''}
        </div>
        <div style={{ fontSize: 12, color: T.textGray, fontFamily: SG }}>
          Preparato il {today}
          {languages.length > 0 && ` · Mercati: ${languages.map(l => (l as Record<string,unknown>).code as string).join(', ')}`}
        </div>
        <div style={{ display: 'inline-block', marginTop: 14, padding: '4px 16px', background: '#f5f5f5', borderRadius: 20, fontSize: 11, color: T.textGray, fontFamily: SG, letterSpacing: 1 }}>
          DOCUMENTO RISERVATO — USO INTERNO E CLIENTE
        </div>
      </div>

      {/* ═══ 2. PROFILO STRUTTURA ═══ */}
      {(rooms || adr || occupancyRate || directPct || services.length > 0 || strengths.length > 0 || landmarks.length > 0) && (
        <div style={sectionStyle}>
          <div style={h2Style}>Profilo struttura</div>

          {/* Hotel metrics chips */}
          {(rooms || adr || occupancyRate || directPct) && (
            <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 8, marginBottom: 20 }}>
              {rooms         && <span style={chipStyle}>🛏 {rooms} camere</span>}
              {adr           && <span style={chipStyle}>💶 ADR €{adr.toLocaleString('it-IT')}/notte</span>}
              {occupancyRate && <span style={chipStyle}>📊 Occupazione {occupancyRate}%</span>}
              {directPct     && <span style={chipStyle}>🎯 Dirette {directPct}%</span>}
              {landmarks.length > 0 && <span style={chipStyle}>📍 {landmarks[0]}</span>}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: strengths.length && services.length ? '1fr 1fr' : '1fr', gap: 14, fontFamily: SG }}>
            {strengths.length > 0 && (
              <div style={{ background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: 8, padding: '14px 16px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' as const, color: T.textGray, marginBottom: 10 }}>
                  Punti di forza · USP
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.8, color: '#333' }}>
                  {strengths.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            )}
            {services.length > 0 && (
              <div style={{ background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: 8, padding: '14px 16px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' as const, color: T.textGray, marginBottom: 10 }}>
                  Servizi & dotazioni
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 6 }}>
                  {services.map((s, i) => (
                    <span key={i} style={{ background: '#fff', border: '1px solid #ddd', borderRadius: 4, fontSize: 12, padding: '2px 8px', color: '#444' }}>{s}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ 3. SCENARIO D'INVESTIMENTO ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Scenario d'investimento</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 20 }}>
          {[
            { label: 'Budget mensile',   value: `€${totalMonthly.toLocaleString('it-IT')}`, sub: 'investimento totale' },
            { label: 'Budget giornaliero', value: `€${Math.round(totalMonthly / 30.44).toLocaleString('it-IT')}`, sub: 'media al giorno' },
            { label: 'Campagne attive',  value: String(orderedTypes.length), sub: 'tipologie' },
            { label: 'Lingue / Mercati', value: String(languages.length), sub: languages.map(l => (l as Record<string,unknown>).code as string).join(', ') },
            ...(targetRoas ? [{ label: 'ROAS target', value: `${targetRoas}:1`, sub: 'ritorno sull\'investimento' }] : []),
            ...(targetCpa  ? [{ label: 'CPA target',  value: `€${targetCpa}`, sub: 'costo per prenotazione' }] : []),
          ].map((card, i) => (
            <div key={i} style={{ background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: 10, padding: '16px 18px', fontFamily: SG }}>
              <div style={{ fontSize: 11, color: T.textGray, letterSpacing: 0.5, textTransform: 'uppercase' as const, marginBottom: 4 }}>{card.label}</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: T.primary }}>{card.value}</div>
              <div style={{ fontSize: 11, color: T.textGray, marginTop: 2 }}>{card.sub}</div>
            </div>
          ))}
        </div>
        <p style={bodyText}>{investmentParagraph}</p>
      </div>

      {/* ═══ 4. MIX DI CAMPAGNE ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Mix di campagne consigliato</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: SG }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #111' }}>
                {['Priorità', 'Campagna', 'Funnel', 'Bid Strategy', 'Budget/mese', '% tot.', 'Budget/giorno'].map((h, i) => (
                  <th key={i} style={{ padding: '8px 12px', textAlign: i < 2 ? 'left' : 'center', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color: T.textGray }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {typeRows.map(({ type, monthlyAmt, pct }, i) => {
                const info  = CAMPAIGN_STRATEGY[type]
                const color = TYPE_COLOR[type] || T.primary
                const bidStrategy = (perType[type]?.bid_strategy as string | undefined) ?? null
                const bidLabel = bidStrategy ? (BID_STRATEGY_LABEL[bidStrategy] ?? bidStrategy) : '—'
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
                    <td style={{ padding: '12px', textAlign: 'center', fontSize: 11, color: T.textGray }}>{bidLabel}</td>
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
                <td colSpan={4} style={{ padding: '10px 12px', fontWeight: 700, fontSize: 13 }}>TOTALE</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 800, fontSize: 16, color: T.primary }}>€{Math.round(totalMonthly).toLocaleString('it-IT')}</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 700 }}>100%</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', color: T.textGray, fontWeight: 700 }}>€{Math.round(totalMonthly / 30.44).toLocaleString('it-IT')}/g</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ═══ 5. DETTAGLIO CAMPAGNE ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Dettaglio delle campagne</div>
        {orderedTypes.map((type, idx) => {
          const info      = CAMPAIGN_STRATEGY[type]
          const color     = TYPE_COLOR[type] || T.primary
          const monthly   = typeRows.find(r => r.type === type)?.monthlyAmt ?? 0
          const sampleCopy = getTypeCopy(type)
          const desc      = buildCampaignDescription(type, brief)
          const bidStrategy = (perType[type]?.bid_strategy as string | undefined) ?? null
          const bidLabel  = bidStrategy ? (BID_STRATEGY_LABEL[bidStrategy] ?? bidStrategy) : null
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
                    {bidLabel && (
                      <span style={{ fontSize: 11, color: T.textGray, background: '#f5f5f5', borderRadius: 10, padding: '2px 8px', fontFamily: SG }}>{bidLabel}</span>
                    )}
                  </div>
                </div>
              </div>
              <p style={{ ...bodyText, marginBottom: 14 }}>{desc}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14, fontFamily: SG }}>
                {[
                  { label: 'Target audience', value: info?.audience ?? '' },
                  { label: 'KPI & obiettivi',  value: info?.kpi ?? '' },
                  { label: 'Formato annunci',  value: info?.formats ?? '' },
                  { label: 'Investimento',     value: `€${Math.round(monthly).toLocaleString('it-IT')}/mese · €${Math.round(monthly/30.44).toLocaleString('it-IT')}/giorno` },
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

      {/* ═══ 6. MERCATI E LINGUE ═══ */}
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
                const l  = lang as Record<string, unknown>
                const hl = (l.headlines   as string[] | undefined) ?? []
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

      {/* ═══ 7. STAGIONALITÀ ═══ */}
      {hasSeasonality && (
        <div style={sectionStyle}>
          <div style={h2Style}>Stagionalità e pianificazione budget</div>
          <p style={{ ...bodyText, marginBottom: 20 }}>
            Il piano prevede una gestione stagionale del budget per {brandName},
            con moltiplicatori di spesa calibrati sui periodi di alta e bassa stagione.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
            {peakPeriods.map((p, i) => {
              const period = p as Record<string, unknown>
              const mult   = period.budget_multiplier as number | undefined
              return (
                <div key={`peak-${i}`} style={{ background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8, padding: '14px 16px', fontFamily: SG }}>
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' as const, color: '#b45309', marginBottom: 6 }}>
                    Alta stagione
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4, color: '#111' }}>
                    {period.label as string || `Periodo ${i + 1}`}
                  </div>
                  <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                    {period.start as string} → {period.end as string}
                  </div>
                  {mult && mult !== 1 && (
                    <div style={{ fontSize: 12, color: '#b45309', fontWeight: 600 }}>
                      Budget ×{mult} ({mult > 1 ? '+' : ''}{Math.round((mult - 1) * 100)}%)
                    </div>
                  )}
                </div>
              )
            })}
            {lowPeriods.map((p, i) => {
              const period = p as Record<string, unknown>
              const mult   = period.budget_multiplier as number | undefined
              return (
                <div key={`low-${i}`} style={{ background: '#f0f4ff', border: '1px solid #c7d2fe', borderRadius: 8, padding: '14px 16px', fontFamily: SG }}>
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' as const, color: '#3730a3', marginBottom: 6 }}>
                    Bassa stagione
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4, color: '#111' }}>
                    {period.label as string || `Periodo ${i + 1}`}
                  </div>
                  <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                    {period.start as string} → {period.end as string}
                  </div>
                  {mult && mult !== 1 && (
                    <div style={{ fontSize: 12, color: '#3730a3', fontWeight: 600 }}>
                      Budget ×{mult} ({mult > 1 ? '+' : ''}{Math.round((mult - 1) * 100)}%)
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ═══ 8. NOTE STRATEGICHE ADVISOR AI ═══ */}
      {agentIssues.length > 0 && (
        <div style={sectionStyle}>
          <div style={h2Style}>Note strategiche · Advisor AI</div>
          <p style={{ ...bodyText, marginBottom: 16 }}>
            L'analisi automatica del piano ha rilevato i seguenti punti di attenzione strategica per {brandName}:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 10 }}>
            {agentIssues.map((issue, i) => {
              const isWarning = issue.level === 'warning'
              const borderColor = isWarning ? '#f59e0b' : '#3b82f6'
              const bgColor     = isWarning ? '#fffbeb' : '#eff6ff'
              const icon        = isWarning ? '⚠️' : 'ℹ️'
              return (
                <div key={i} style={{ background: bgColor, border: `1px solid ${borderColor}`, borderLeft: `4px solid ${borderColor}`, borderRadius: 6, padding: '12px 16px', fontFamily: SG }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{ fontSize: 14, flexShrink: 0 }}>{icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color: '#666', marginBottom: 4 }}>
                        {issue.agent} · {issue.code}
                      </div>
                      <div style={{ fontSize: 13, color: '#333', lineHeight: 1.6 }}>{issue.message}</div>
                      {issue.suggested_fix && (
                        <div style={{ marginTop: 6, fontSize: 12, color: '#666', fontStyle: 'italic' as const }}>
                          Suggerimento: {issue.suggested_fix.label}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ═══ 9. PROSSIMI PASSI ═══ */}
      <div style={{ ...sectionStyle, borderBottom: 'none' }}>
        <div style={h2Style}>Prossimi passi</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10, fontFamily: SG }}>
          {dynamicSteps.map(item => (
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
