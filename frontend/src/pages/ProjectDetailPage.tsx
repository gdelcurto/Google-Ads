import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, type AccountPlanPreview, type CampaignPreview } from '../api/projects'
import BriefForm from '../components/BriefForm'
import { GoogleAdPreview } from '../components/GoogleAdPreview'
import { T } from '../styles/theme'

const s: Record<string, React.CSSProperties> = {
  header: { marginBottom: 28 },
  h1: { fontSize: 24, fontWeight: 700, color: T.text, marginBottom: 4, letterSpacing: -0.4 },
  tabs: { display: 'flex', gap: 0, borderBottom: `2px solid ${T.borderLight}`, marginBottom: 28 },
  tab: {
    padding: '10px 20px', cursor: 'pointer', fontSize: 14, fontWeight: 600,
    color: T.textGray, border: 'none', background: 'transparent',
    borderBottom: '2px solid transparent', marginBottom: -2,
  },
  tabActive: { color: T.primary, borderBottom: `2px solid ${T.primary}` },
  actions: { display: 'flex', gap: 10, marginBottom: 24 },
  btn: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '9px 18px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnGreen: {
    background: T.success, color: '#fff', border: 'none',
    padding: '9px 18px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnOutline: {
    background: 'transparent', color: T.text, border: `1px solid ${T.border}`,
    padding: '8px 18px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  alert: {
    background: '#fffbeb', border: `1px solid ${T.yellow}`,
    padding: '10px 14px', borderRadius: T.radiusSm, fontSize: 13, marginBottom: 16, color: '#713f12',
  },
  error: {
    background: '#fff0f0', border: '1px solid #fca5a5',
    padding: '10px 14px', borderRadius: T.radiusSm, fontSize: 13, marginBottom: 16, color: T.error,
  },
  success: {
    background: '#f0fdf4', border: '1px solid #86efac',
    padding: '10px 14px', borderRadius: T.radiusSm, fontSize: 13, marginBottom: 16, color: '#166534',
  },
  card: {
    background: T.bgCard, borderRadius: T.radiusLg, padding: 20,
    boxShadow: T.shadow, marginBottom: 12, border: `1px solid ${T.borderLight}`,
  },
  campaignName: { fontWeight: 700, fontSize: 15, color: T.text, marginBottom: 6 },
  metaRow: { display: 'flex', gap: 16, fontSize: 13, color: T.textGray, marginBottom: 8, flexWrap: 'wrap' },
  badge: {
    display: 'inline-block', padding: '2px 10px', borderRadius: 20,
    fontSize: 11, fontWeight: 700, color: '#fff', background: T.textGray,
  },
  badgeGreen: {
    display: 'inline-block', padding: '2px 10px', borderRadius: 20,
    fontSize: 11, fontWeight: 700, color: '#fff', background: T.success,
  },
  badgeRed: {
    display: 'inline-block', padding: '2px 10px', borderRadius: 20,
    fontSize: 11, fontWeight: 700, color: '#fff', background: T.error,
  },
  blockers: {
    background: '#fff0f0', padding: '8px 12px',
    borderRadius: T.radiusSm, fontSize: 12, color: T.error, marginTop: 8,
  },
  adGroups: { marginTop: 10, paddingTop: 10, borderTop: `1px solid ${T.borderLight}` },
  agRow: {
    fontSize: 13, color: T.text, padding: '6px 0',
    borderBottom: `1px solid ${T.borderLight}`,
  },
  summary: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 },
  summaryCard: {
    background: T.bgCard, borderRadius: T.radiusLg, padding: 20,
    boxShadow: T.shadow, textAlign: 'center', border: `1px solid ${T.borderLight}`,
  },
  summaryNum: { fontSize: 30, fontWeight: 800, color: T.primary },
  summaryLabel: { fontSize: 12, color: T.textGray, marginTop: 4 },
  textarea: {
    width: '100%', fontFamily: 'monospace', fontSize: 12, padding: 12,
    border: `1px solid ${T.border}`, borderRadius: T.radiusSm, minHeight: 400, resize: 'vertical',
  },
}

type Tab = 'overview' | 'campaigns' | 'preview' | 'brief' | 'action_plan' | 'plan_json' | 'audit'

function CampaignCard({ campaign }: { campaign: CampaignPreview }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={s.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={s.campaignName}>{campaign.campaign_name}</div>
          <div style={s.metaRow}>
            <span>{campaign.campaign_type}</span>
            <span>Lang: {campaign.language_code}</span>
            <span>Budget: €{campaign.budget_daily_eur.toFixed(2)}/d</span>
            <span>Bid: {campaign.bid_strategy}</span>
            <span>Ad Groups: {campaign.ad_groups_count}</span>
          </div>
        </div>
        <span style={campaign.can_publish ? s.badgeGreen : s.badgeRed}>
          {campaign.can_publish ? 'Publishable' : 'Blocked'}
        </span>
      </div>

      {campaign.publish_blockers.length > 0 && (
        <div style={s.blockers}>
          <strong>Blockers:</strong>
          <ul style={{ marginLeft: 16, marginTop: 4 }}>
            {campaign.publish_blockers.map((b, i) => <li key={i}>{b}</li>)}
          </ul>
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        style={{ marginTop: 10, padding: '5px 12px', fontSize: 12, background: T.bgPage, color: T.text, border: `1px solid ${T.border}`, borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 500 }}
      >
        {expanded ? '▲ Nascondi' : '▼ Ad Groups'} ({campaign.ad_groups_count})
      </button>

      {expanded && (
        <div style={s.adGroups}>
          {campaign.ad_groups.map((ag, i) => (
            <div key={i} style={s.agRow}>
              <strong>{ag.name}</strong>
              {' · '}KW: {ag.keywords_count}
              {' · '}Ads: {ag.ads_count}
              {ag.audience_targeting.length > 0 && ` · Audience: ${ag.audience_targeting.join(', ')}`}
            </div>
          ))}
          {campaign.pmax_asset_groups.map((ag, i) => (
            <div key={`pmax-${i}`} style={{ ...s.agRow, background: T.secondary }}>
              <strong>Asset Group:</strong> {ag.name}
              {ag.has_missing_assets && <span style={{ color: '#dc2626' }}> ⚠ Asset mancanti</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function PlanSummary({ plan }: { plan: AccountPlanPreview }) {
  const publishable = plan.campaigns.filter(c => c.can_publish).length
  const blocked = plan.campaigns.filter(c => !c.can_publish).length
  const totalBudget = plan.campaigns.reduce((sum, c) => sum + c.budget_daily_eur, 0)

  return (
    <div>
      <div style={s.summary}>
        <div style={s.summaryCard}>
          <div style={s.summaryNum}>{plan.total_campaigns}</div>
          <div style={s.summaryLabel}>Campagne totali</div>
        </div>
        <div style={s.summaryCard}>
          <div style={{ ...s.summaryNum, color: T.success }}>{publishable}</div>
          <div style={s.summaryLabel}>Pronte per publish</div>
        </div>
        <div style={s.summaryCard}>
          <div style={{ ...s.summaryNum, color: T.error }}>{blocked}</div>
          <div style={s.summaryLabel}>Bloccate</div>
        </div>
        <div style={s.summaryCard}>
          <div style={s.summaryNum}>€{totalBudget.toFixed(0)}</div>
          <div style={s.summaryLabel}>Budget/giorno totale</div>
        </div>
      </div>

      {plan.validation_errors.length > 0 && (
        <div style={s.error}>
          <strong>Errori validazione:</strong>
          <ul style={{ marginLeft: 16 }}>{plan.validation_errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
      )}
      {plan.validation_warnings.length > 0 && (
        <div style={s.alert}>
          <strong>Warning:</strong>
          <ul style={{ marginLeft: 16 }}>{plan.validation_warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}
    </div>
  )
}

const TYPE_COLOR: Record<string, string> = {
  search_brand:       '#1a73e8',
  search_acquisition: '#ea8600',
  retargeting:        '#7c3aed',
  performance_max:    '#059669',
  demand_gen:         '#e10098',
}

// ─── Piano d'azione ───────────────────────────────────────────────────────────

const CAMPAIGN_STRATEGY: Record<string, {
  label: string; funnel: string; funnelColor: string; priority: number
  description: string; audience: string; kpi: string; formats: string
}> = {
  search_brand: {
    label: 'Brand Search', funnel: 'Bottom', funnelColor: '#dc2626', priority: 1,
    description:
      'Protegge il traffico di brand dalle OTA (Booking.com, Expedia) che fanno bidding sul nome dell\'hotel. ' +
      'Intercetta utenti con la più alta intenzione d\'acquisto al CPC più contenuto. ' +
      'Fondamentale per garantire il flusso di prenotazioni dirette e massimizzare il ROAS complessivo dell\'account.',
    audience: 'Utenti che cercano direttamente il nome dell\'hotel o varianti brand',
    kpi: 'ROAS atteso 5:1–10:1 · CPC basso · CTR alto · Priorità massima',
    formats: 'RSA (Responsive Search Ads) con brand name in posizione 1',
  },
  search_acquisition: {
    label: 'Acquisition Search', funnel: 'Mid → Bottom', funnelColor: '#d97706', priority: 2,
    description:
      'Intercetta viaggiatori in fase di ricerca attiva su keyword di destinazione, categoria e servizi ' +
      '(es. "hotel 4 stelle Roma centro", "hotel con spa lago di Garda"). ' +
      'È il principale motore di acquisizione di nuovi clienti diretti, indirizzando il traffico verso il sito ufficiale invece che verso le OTA.',
    audience: 'Viaggiatori in fase di ricerca attiva che non conoscono ancora il brand',
    kpi: 'ROAS atteso 3:1–5:1 · Volume elevato · CPA target per conversione diretta',
    formats: 'RSA con copy differenziato per tema (location, servizi, categoria, occasione)',
  },
  performance_max: {
    label: 'Performance Max', funnel: 'Full-Funnel', funnelColor: '#059669', priority: 3,
    description:
      'Campagna automatizzata di Google che scala su tutti i touchpoint: Search, Display, YouTube, Maps, Gmail e Discover. ' +
      'Ottimizza autonomamente la distribuzione del budget verso le conversioni più probabili, ' +
      'amplificando i risultati delle campagne brand e acquisition con reach incrementale su tutti i canali.',
    audience: 'Audience automatica basata su segnali di remarketing, liste in-market e customer match',
    kpi: 'ROAS target configurabile · Apprendimento: 4–6 settimane · Richiede asset visivi',
    formats: 'Asset group con headline, descrizioni lunghe, immagini landscape/square e video YouTube',
  },
  retargeting: {
    label: 'Retargeting Display', funnel: 'Mid → Bottom', funnelColor: '#7c3aed', priority: 4,
    description:
      'Re-intercetta i visitatori del sito che hanno esplorato le camere o il motore di prenotazione senza completare la prenotazione. ' +
      'Utilizza messaggi di urgency e rassicurazione per spingere alla conversione diretta, ' +
      'con costi di acquisizione inferiori rispetto alle campagne di prospecting.',
    audience: 'Visitatori del sito negli ultimi 14–30 giorni, esclusi i clienti già prenotati',
    kpi: 'CPA inferiore all\'acquisition · Alta probabilità di conversione · Reach limitato ma qualificato',
    formats: 'Display ads adattivi con immagini hotel (300×250, 728×90, 160×600)',
  },
  demand_gen: {
    label: 'Demand Gen', funnel: 'Top', funnelColor: '#e10098', priority: 5,
    description:
      'Campagna di ispirazione su YouTube, Google Discover e Gmail che raggiunge i viaggiatori nella fase pre-ricerca, ' +
      'quando ancora stanno pianificando la prossima vacanza. ' +
      'Genera notorietà del brand, alimenta le audience di remarketing e prepara il terreno per le campagne di performance.',
    audience: 'Audience in-market per hotel e viaggi, similar audiences e prospecting su YouTube',
    kpi: 'Focus su reach e consideration · Risultati a 4–8 settimane · Richiede video e creatività visive',
    formats: 'Video 16:9 su YouTube, immagini landscape e square su Discover e Gmail',
  },
}

function ActionPlanTab({ brief }: {
  brief: Record<string, unknown>
}) {
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

  // ── Campaign selection & budget recalculation ─────────────────────────────
  const [selectedTypes, setSelectedTypes] = useState<string[]>(() => [...campaignTypes])
  const [recalcBudgets, setRecalcBudgets] = useState<Record<string, number> | null>(null)

  const typesKey = campaignTypes.join(',')
  useEffect(() => {
    setSelectedTypes([...campaignTypes])
    setRecalcBudgets(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typesKey])

  // True when user has deselected at least one AI-suggested type
  const isDirty = campaignTypes.some(t => !selectedTypes.includes(t))

  function toggleType(type: string) {
    setSelectedTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    )
    setRecalcBudgets(null) // reset recalculation on each toggle
  }

  function handleRecalculate() {
    const origSelectedSum = selectedTypes.reduce((sum, t) => sum + (byCT[t]?.total ?? 0), 0)
    const newBudgets: Record<string, number> = {}
    for (const t of selectedTypes) {
      newBudgets[t] = origSelectedSum > 0
        ? ((byCT[t]?.total ?? 0) / origSelectedSum) * totalMonthly
        : selectedTypes.length > 0 ? totalMonthly / selectedTypes.length : 0
    }
    setRecalcBudgets(newBudgets)
  }

  function effectiveBudget(type: string): number {
    if (recalcBudgets && selectedTypes.includes(type)) return recalcBudgets[type] ?? 0
    return byCT[type]?.total ?? 0
  }

  // Total for selected types only (used in summary cards and table total row)
  const effectiveTotalMonthly = recalcBudgets
    ? selectedTypes.reduce((sum, t) => sum + (recalcBudgets[t] ?? 0), 0)
    : selectedTypes.reduce((sum, t) => sum + (byCT[t]?.total ?? 0), 0)

  // All AI types sorted by priority — shown in the mix table (incl. deselected)
  const allOrderedTypes = [...campaignTypes].sort((a, b) =>
    ((CAMPAIGN_STRATEGY[a]?.priority ?? 99) - (CAMPAIGN_STRATEGY[b]?.priority ?? 99))
  )

  // Only selected types sorted — used for the detail section
  const orderedSelectedTypes = [...selectedTypes].sort((a, b) =>
    ((CAMPAIGN_STRATEGY[a]?.priority ?? 99) - (CAMPAIGN_STRATEGY[b]?.priority ?? 99))
  )

  // Budget rows: all types, with isSelected flag and effective amounts
  const typeRows = allOrderedTypes.map(t => {
    const isSelected = selectedTypes.includes(t)
    const monthlyAmt = isSelected ? effectiveBudget(t) : (byCT[t]?.total ?? 0)
    const pct = isSelected && effectiveTotalMonthly > 0 ? (monthlyAmt / effectiveTotalMonthly) * 100 : 0
    return { type: t, monthlyAmt, pct, isSelected }
  })

  // First language for sample copy
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

  const docStyle: React.CSSProperties = {
    maxWidth: 860, margin: '0 auto', fontFamily: '"Georgia", "Times New Roman", serif', color: '#1a1a1a',
  }
  const sectionStyle: React.CSSProperties = {
    marginBottom: 36, paddingBottom: 32, borderBottom: `1px solid #e0e0e0`,
  }
  const h2Style: React.CSSProperties = {
    fontSize: 13, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' as const,
    color: T.primary, marginBottom: 16, fontFamily: 'system-ui, sans-serif',
  }
  const bodyText: React.CSSProperties = {
    fontSize: 14, lineHeight: 1.75, color: '#333', fontFamily: '"Georgia", serif',
  }

  return (
    <div style={docStyle}>

      {/* ── Print button ── */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 24, gap: 10 }}>
        <button
          style={{ ...s.btnOutline, fontSize: 13 }}
          onClick={() => window.print()}
        >
          🖨 Stampa / Salva PDF
        </button>
      </div>

      {/* ═══ 1. INTESTAZIONE ═══ */}
      <div style={{ ...sectionStyle, textAlign: 'center', paddingBottom: 28 }}>
        <div style={{ fontSize: 11, letterSpacing: 3, textTransform: 'uppercase' as const, color: T.textGray, marginBottom: 8, fontFamily: 'system-ui, sans-serif' }}>
          Piano Strategico Google Ads
        </div>
        <h1 style={{ fontSize: 32, fontWeight: 700, color: '#111', margin: '0 0 8px', letterSpacing: -0.5 }}>
          {brandName}
        </h1>
        <div style={{ fontSize: 15, color: T.textGray, marginBottom: 6, fontFamily: 'system-ui, sans-serif' }}>
          {category}{stars > 0 ? ` · ${'★'.repeat(stars)}` : ''}
          {address ? ` · ${address}` : ''}
        </div>
        <div style={{ fontSize: 12, color: T.textGray, fontFamily: 'system-ui, sans-serif' }}>
          Preparato il {today}
          {languages.length > 0 && ` · Mercati: ${languages.map(l => (l as Record<string,unknown>).code as string).join(', ')}`}
        </div>
        <div style={{ display: 'inline-block', marginTop: 14, padding: '4px 16px', background: '#f5f5f5', borderRadius: 20, fontSize: 11, color: T.textGray, fontFamily: 'system-ui, sans-serif', letterSpacing: 1 }}>
          DOCUMENTO RISERVATO — USO INTERNO E CLIENTE
        </div>
      </div>

      {/* ═══ 2. SCENARIO D'INVESTIMENTO ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Scenario d'investimento</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 20 }}>
          {[
            { label: 'Budget mensile', value: `€${Math.round(effectiveTotalMonthly).toLocaleString('it-IT')}`, sub: 'investimento totale' },
            { label: 'Budget giornaliero', value: `€${Math.round(effectiveTotalMonthly / 30.44).toLocaleString('it-IT')}`, sub: 'media al giorno' },
            { label: 'Campagne attive', value: String(selectedTypes.length), sub: 'tipologie' },
            { label: 'Lingue / Mercati', value: String(languages.length), sub: languages.map(l => (l as Record<string,unknown>).code as string).join(', ') },
            ...(targetRoas ? [{ label: 'ROAS target', value: `${targetRoas}:1`, sub: 'ritorno sull\'investimento' }] : []),
            ...(targetCpa  ? [{ label: 'CPA target', value: `€${targetCpa}`, sub: 'costo per prenotazione' }] : []),
          ].map((card, i) => (
            <div key={i} style={{ background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: 10, padding: '16px 18px', fontFamily: 'system-ui, sans-serif' }}>
              <div style={{ fontSize: 11, color: T.textGray, letterSpacing: 0.5, textTransform: 'uppercase' as const, marginBottom: 4 }}>{card.label}</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: T.primary }}>{card.value}</div>
              <div style={{ fontSize: 11, color: T.textGray, marginTop: 2 }}>{card.sub}</div>
            </div>
          ))}
        </div>
        <p style={bodyText}>
          Il piano prevede un approccio <strong>full-funnel</strong> con {selectedTypes.length} tipologie di campagna Google Ads,
          attivate in ordine di priorità d'intento: dalla protezione del brand fino alla generazione di domanda.
          L'obiettivo primario è incrementare le prenotazioni dirette riducendo la dipendenza dalle OTA (Booking.com, Expedia)
          e migliorare il ritorno sull'investimento pubblicitario.
        </p>
      </div>

      {/* ═══ 3. MIX DI CAMPAGNE ═══ */}
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap' as const, gap: 10 }}>
          <div style={h2Style}>Mix di campagne consigliato</div>
          {isDirty && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {!recalcBudgets && (
                <span style={{ fontSize: 12, color: T.textGray, fontFamily: 'system-ui, sans-serif' }}>
                  {campaignTypes.length - selectedTypes.length} campagna/e esclusa/e
                </span>
              )}
              <button
                onClick={handleRecalculate}
                style={{
                  background: recalcBudgets ? '#f0fdf4' : T.primary,
                  color: recalcBudgets ? '#15803d' : '#fff',
                  border: recalcBudgets ? '1px solid #bbf7d0' : 'none',
                  borderRadius: 6, padding: '6px 14px', fontSize: 12,
                  fontWeight: 700, cursor: 'pointer', fontFamily: 'system-ui, sans-serif',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}
              >
                {recalcBudgets ? '✓ Budget ricalcolato' : '⟳ Ricalcola budget'}
              </button>
              <button
                onClick={() => { setSelectedTypes([...campaignTypes]); setRecalcBudgets(null) }}
                style={{
                  background: 'transparent', color: T.textGray, border: `1px solid ${T.borderLight}`,
                  borderRadius: 6, padding: '6px 12px', fontSize: 12,
                  fontWeight: 600, cursor: 'pointer', fontFamily: 'system-ui, sans-serif',
                }}
                title="Ripristina la selezione suggerita dall'AI"
              >
                Ripristina AI
              </button>
            </div>
          )}
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'system-ui, sans-serif' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #111' }}>
                <th style={{ padding: '8px 8px', width: 32 }} />
                {['Priorità', 'Campagna', 'Funnel', 'Budget/mese', '% tot.', 'Budget/giorno'].map((h, i) => (
                  <th key={i} style={{ padding: '8px 12px', textAlign: i < 2 ? 'left' : 'center', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color: T.textGray }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {typeRows.map(({ type, monthlyAmt, pct, isSelected }, i) => {
                const info = CAMPAIGN_STRATEGY[type]
                const color = TYPE_COLOR[type] || T.primary
                const rowOpacity = isSelected ? 1 : 0.4
                return (
                  <tr
                    key={type}
                    style={{ borderBottom: '1px solid #e8e8e8', background: i % 2 === 0 ? '#fff' : '#fafafa', opacity: rowOpacity, transition: 'opacity 0.15s' }}
                  >
                    <td style={{ padding: '8px 8px', textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleType(type)}
                        style={{ cursor: 'pointer', width: 15, height: 15, accentColor: T.primary }}
                        title={isSelected ? 'Deseleziona campagna' : 'Seleziona campagna'}
                      />
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center', color: T.textGray, fontSize: 12, fontWeight: 700 }}>
                      {info?.priority ?? i + 1}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
                        <strong style={{ color: '#111', textDecoration: isSelected ? 'none' : 'line-through' }}>{info?.label ?? type}</strong>
                      </div>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <span style={{ background: info?.funnelColor ?? color, color: '#fff', borderRadius: 12, fontSize: 10, padding: '2px 10px', fontWeight: 700, whiteSpace: 'nowrap' as const }}>
                        {info?.funnel ?? '—'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center', fontWeight: 700, fontSize: 15 }}>
                      {isSelected ? `€${Math.round(monthlyAmt).toLocaleString('it-IT')}` : '—'}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      {isSelected ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' }}>
                          <div style={{ width: 60, height: 6, background: '#e8e8e8', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
                          </div>
                          <span style={{ fontSize: 12, color: T.textGray, minWidth: 32 }}>{pct.toFixed(0)}%</span>
                        </div>
                      ) : <span style={{ color: T.textGray, fontSize: 12 }}>—</span>}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center', color: T.textGray, fontSize: 13 }}>
                      {isSelected ? `€${Math.round(monthlyAmt / 30.44).toLocaleString('it-IT')}/g` : '—'}
                    </td>
                  </tr>
                )
              })}
              <tr style={{ borderTop: '2px solid #111', background: '#f5f5f5' }}>
                <td colSpan={4} style={{ padding: '10px 12px', fontWeight: 700, fontSize: 13 }}>
                  TOTALE{isDirty ? ` (${selectedTypes.length}/${campaignTypes.length} campagne)` : ''}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 800, fontSize: 16, color: T.primary }}>
                  €{Math.round(effectiveTotalMonthly).toLocaleString('it-IT')}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 700 }}>100%</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', color: T.textGray, fontWeight: 700 }}>
                  €{Math.round(effectiveTotalMonthly / 30.44).toLocaleString('it-IT')}/g
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        {isDirty && !recalcBudgets && (
          <div style={{ marginTop: 14, padding: '10px 14px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8, fontSize: 12, color: '#92400e', fontFamily: 'system-ui, sans-serif' }}>
            Hai deselezionato {campaignTypes.length - selectedTypes.length} tipologia/e. Clicca <strong>Ricalcola budget</strong> per redistribuire il budget totale (€{Math.round(totalMonthly).toLocaleString('it-IT')}/mese) proporzionalmente tra le campagne selezionate.
          </div>
        )}
        {recalcBudgets && (
          <div style={{ marginTop: 14, padding: '10px 14px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, fontSize: 12, color: '#15803d', fontFamily: 'system-ui, sans-serif' }}>
            Budget redistribuito proporzionalmente tra {selectedTypes.length} campagne selezionate · Budget totale invariato: €{Math.round(totalMonthly).toLocaleString('it-IT')}/mese
          </div>
        )}
      </div>

      {/* ═══ 4. DETTAGLIO CAMPAGNE ═══ */}
      <div style={sectionStyle}>
        <div style={h2Style}>Dettaglio delle campagne</div>
        {orderedSelectedTypes.map((type, idx) => {
          const info = CAMPAIGN_STRATEGY[type]
          const color = TYPE_COLOR[type] || T.primary
          const monthly = effectiveBudget(type)
          const sampleCopy = getTypeCopy(type)

          return (
            <div key={type} style={{ marginBottom: 28, paddingBottom: 28, borderBottom: idx < orderedSelectedTypes.length - 1 ? '1px dashed #e0e0e0' : 'none' }}>
              {/* Campaign header */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
                <div style={{ width: 40, height: 40, borderRadius: 8, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 12, flexShrink: 0, fontFamily: 'system-ui, sans-serif' }}>
                  {info?.priority ?? idx + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' as const, marginBottom: 4 }}>
                    <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#111', fontFamily: 'system-ui, sans-serif' }}>
                      {info?.label ?? type}
                    </h3>
                    <span style={{ background: info?.funnelColor ?? color, color: '#fff', borderRadius: 12, fontSize: 10, padding: '2px 10px', fontWeight: 700, fontFamily: 'system-ui, sans-serif' }}>
                      {info?.funnel ?? '—'}
                    </span>
                    <span style={{ fontSize: 13, color: T.primary, fontWeight: 700, fontFamily: 'system-ui, sans-serif' }}>
                      €{Math.round(monthly).toLocaleString('it-IT')}/mese
                    </span>
                  </div>
                </div>
              </div>

              {/* Description */}
              <p style={{ ...bodyText, marginBottom: 14 }}>{info?.description ?? ''}</p>

              {/* Detail grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14, fontFamily: 'system-ui, sans-serif' }}>
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

              {/* Sample headlines */}
              {sampleCopy.length > 0 && (
                <div style={{ background: `${color}0d`, border: `1px solid ${color}33`, borderRadius: 8, padding: '12px 16px', fontFamily: 'system-ui, sans-serif' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' as const, color, marginBottom: 8 }}>
                    Messaggi chiave — {(firstLang?.code as string) || 'IT'}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 6 }}>
                    {sampleCopy.map((h, i) => (
                      <span key={i} style={{ background: '#fff', border: `1px solid ${color}44`, borderRadius: 4, fontSize: 12, padding: '3px 10px', color: '#222' }}>
                        {h}
                      </span>
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
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'system-ui, sans-serif' }}>
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
                    <td style={{ padding: '10px 12px', fontWeight: 700 }}>
                      {l.code as string} — {l.name as string}
                    </td>
                    <td style={{ padding: '10px 12px', color: T.textGray, fontSize: 12 }}>
                      {(l.landing_page as string | undefined) || '—'}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#444' }}>
                      {hl.slice(0, 2).join(' · ') || '—'}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#444' }}>
                      {bt.slice(0, 3).join(', ') || '—'}
                    </td>
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10, fontFamily: 'system-ui, sans-serif' }}>
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

        {/* Footer */}
        <div style={{ marginTop: 36, paddingTop: 20, borderTop: '1px solid #e8e8e8', textAlign: 'center', fontSize: 11, color: '#aaa', fontFamily: 'system-ui, sans-serif', letterSpacing: 0.5 }}>
          Documento generato da Google Ads Planner · {brandName} · {today}
        </div>
      </div>
    </div>
  )
}

const TYPE_LABEL: Record<string, string> = {
  search_brand:       'Brand',
  search_acquisition: 'Acquisition',
  retargeting:        'Retargeting',
  performance_max:    'Performance Max',
  demand_gen:         'Demand Gen',
}

function CampaignPreviewCard({
  campaign, briefLang, domain,
}: {
  campaign: CampaignPreview
  briefLang: Record<string, unknown> | undefined
  domain: string
}) {
  const [open, setOpen] = useState(false)
  const isPMax = campaign.campaign_type === 'performance_max'
  const color = TYPE_COLOR[campaign.campaign_type] || T.primary
  const label = TYPE_LABEL[campaign.campaign_type] || campaign.campaign_type

  return (
    <div style={{ border: `1px solid ${T.borderLight}`, borderRadius: T.radiusLg, marginBottom: 12, overflow: 'hidden' }}>

      {/* ── Header row (always visible) ── */}
      <div
        style={{
          padding: '12px 16px', background: T.bgMuted, cursor: 'pointer',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderBottom: open ? `1px solid ${T.borderLight}` : 'none',
        }}
        onClick={() => setOpen(o => !o)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' as const }}>
          <span style={{ background: color, color: '#fff', borderRadius: 4, fontSize: 11, padding: '2px 8px', fontWeight: 700 }}>
            {label}
          </span>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{campaign.campaign_name}</span>
          <span style={{ fontSize: 12, color: T.textGray }}>
            {campaign.language_code} · €{campaign.budget_daily_eur.toFixed(2)}/d · {campaign.bid_strategy}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          {campaign.publish_blockers.length > 0 && (
            <span style={{ fontSize: 11, color: T.error, fontWeight: 700 }}>
              {campaign.publish_blockers.length} {campaign.publish_blockers.length === 1 ? 'blocco' : 'blocchi'}
            </span>
          )}
          <span style={{ fontSize: 11, fontWeight: 700, color: campaign.can_publish ? T.success : T.error }}>
            {campaign.can_publish ? '✓ Pronta' : '✗ Bloccata'}
          </span>
          <span style={{ fontSize: 12, color: T.textGray }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* ── Expanded body ── */}
      {open && (
        <div style={{ padding: 20 }}>

          {/* Publish blockers */}
          {campaign.publish_blockers.length > 0 && (
            <div style={{ background: '#fff0f0', border: '1px solid #fca5a5', borderRadius: T.radiusSm, padding: '10px 14px', marginBottom: 16, fontSize: 13, color: T.error }}>
              <strong>Blocchi:</strong>
              <ul style={{ marginLeft: 16, marginTop: 4 }}>
                {campaign.publish_blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          )}

          {/* ── Performance Max ── */}
          {isPMax ? (
            <div>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>Asset Groups</div>
              {campaign.pmax_asset_groups.length === 0
                ? <p style={{ color: T.textGray, fontSize: 13 }}>Nessun asset group trovato.</p>
                : campaign.pmax_asset_groups.map((ag, i) => (
                  <div key={i} style={{ border: `1px solid ${T.borderLight}`, borderRadius: T.radiusSm, padding: '10px 14px', marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <strong style={{ fontSize: 13 }}>📦 {ag.name}</strong>
                      <span style={{ fontSize: 11, fontWeight: 700, color: ag.has_missing_assets ? T.error : T.success }}>
                        {ag.has_missing_assets ? '⚠ Asset mancanti' : '✓ Completo'}
                      </span>
                    </div>
                    {ag.missing_asset_notes.length > 0 && (
                      <ul style={{ fontSize: 12, color: T.error, marginLeft: 16 }}>
                        {ag.missing_asset_notes.map((n, j) => <li key={j}>{n}</li>)}
                      </ul>
                    )}
                    {ag.audience_signals.length > 0 && (
                      <div style={{ fontSize: 12, color: T.textGray, marginTop: 4 }}>
                        Audience signals: {ag.audience_signals.join(', ')}
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: T.textGray, marginTop: 2 }}>
                      Headline asset: {ag.headlines_count}
                    </div>
                  </div>
                ))
              }
              {/* Brief assets recap */}
              {briefLang && (
                <div style={{ marginTop: 16, padding: '12px 14px', background: T.bgMuted, borderRadius: T.radiusSm, fontSize: 13 }}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>Asset testo da brief ({campaign.language_code})</div>
                  <div style={{ marginBottom: 4 }}>
                    <strong>Headline:</strong>{' '}
                    {(briefLang.headlines as string[] || []).slice(0, 3).join(' | ')}
                    {(briefLang.headlines as string[] || []).length > 3
                      ? ` +${(briefLang.headlines as string[] || []).length - 3} altri` : ''}
                  </div>
                  <div>
                    <strong>Description:</strong>{' '}
                    {(briefLang.descriptions as string[] || []).slice(0, 1).join('')}
                  </div>
                </div>
              )}
            </div>

          ) : (
            /* ── Search / Retargeting / Demand Gen — one RSA preview per ad group ── */
            <div>
              {campaign.ad_groups.length === 0 ? (
                <div style={{ padding: 16, background: T.bgMuted, borderRadius: T.radiusSm, color: T.textGray, fontSize: 13 }}>
                  Nessun ad group trovato per questa campagna.
                </div>
              ) : (
                campaign.ad_groups.map((ag, i) => {
                  const agH = ag.rsa_headlines?.length > 0 ? ag.rsa_headlines : (briefLang?.headlines as string[] || [])
                  const agD = ag.rsa_descriptions?.length > 0 ? ag.rsa_descriptions : (briefLang?.descriptions as string[] || [])
                  const hasRsa = agH.length > 0

                  return (
                    <div key={i} style={{ marginBottom: 20 }}>
                      {/* Ad group header */}
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' as const,
                        marginBottom: 10, paddingBottom: 8, borderBottom: `1px solid ${T.borderLight}`,
                      }}>
                        <span style={{ fontWeight: 700, fontSize: 13 }}>📁 {ag.name}</span>
                        <span style={{ fontSize: 11, color: T.textGray, background: T.bgMuted, padding: '2px 8px', borderRadius: 10 }}>
                          {ag.keywords_count} keyword
                        </span>
                        <span style={{ fontSize: 11, color: T.textGray, background: T.bgMuted, padding: '2px 8px', borderRadius: 10 }}>
                          {ag.ads_count} {ag.ads_count === 1 ? 'annuncio' : 'annunci'}
                        </span>
                        {ag.audience_targeting.length > 0 && (
                          <span style={{ fontSize: 11, color: T.textGray }}>
                            Audience: {ag.audience_targeting.join(', ')}
                          </span>
                        )}
                      </div>

                      {/* RSA preview */}
                      {hasRsa ? (
                        <GoogleAdPreview
                          lang={{
                            headlines:    agH,
                            descriptions: agD,
                            callouts:     briefLang?.callouts as string[] || [],
                            sitelinks:    briefLang?.sitelinks as { text: string; description_1: string; description_2: string; final_url: string }[] || [],
                          }}
                          domain={domain}
                        />
                      ) : (
                        <div style={{ padding: '10px 14px', background: T.bgMuted, borderRadius: T.radiusSm, color: T.textGray, fontSize: 12 }}>
                          Nessun annuncio RSA per questo ad group.
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [planJsonText, setPlanJsonText] = useState('')
  const qc = useQueryClient()

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id!),
  })

  const { data: plan } = useQuery({
    queryKey: ['plan', id],
    queryFn: () => projectsApi.getPlan(id!),
    enabled: activeTab === 'campaigns' || activeTab === 'overview' || activeTab === 'preview' || activeTab === 'action_plan',
    retry: false,
  })

  const { data: brief, isFetching: briefFetching } = useQuery({
    queryKey: ['brief', id],
    queryFn: () => projectsApi.getBrief(id!),
    enabled: (activeTab === 'brief' || activeTab === 'preview' || activeTab === 'action_plan') && (project?.has_brief ?? false),
    retry: false,
  })

  const { data: audit } = useQuery({
    queryKey: ['audit', id],
    queryFn: () => projectsApi.getAudit(id!),
    enabled: activeTab === 'audit',
  })

  // Sync plan JSON editor when plan changes
  useEffect(() => {
    if (plan) setPlanJsonText(JSON.stringify(plan, null, 2))
  }, [plan])

  const savePlanMutation = useMutation({
    mutationFn: (planData: Record<string, unknown>) => projectsApi.savePlan(id!, planData),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan', id] })
      setMessage({ type: 'success', text: 'Piano salvato con successo.' })
    },
    onError: (e: Error) => setMessage({ type: 'error', text: e.message }),
  })

  const generateMutation = useMutation({
    mutationFn: () => projectsApi.generate(id!, true),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan', id] })
      qc.invalidateQueries({ queryKey: ['project', id] })
      setMessage({ type: 'success', text: 'Piano generato con successo (dry run).' })
      setActiveTab('campaigns')
    },
    onError: (e: Error) => setMessage({ type: 'error', text: e.message }),
  })

  const publishMutation = useMutation({
    mutationFn: () => projectsApi.publish(id!, true),
    onSuccess: () => setMessage({ type: 'success', text: 'Dry run completato. Controlla i risultati.' }),
    onError: (e: Error) => setMessage({ type: 'error', text: e.message }),
  })

  if (!project) return <p>Caricamento...</p>

  return (
    <div>
      <div style={s.header}>
        <h1 style={s.h1}>{project.name}</h1>
        <div style={{ fontSize: 13, color: T.textGray }}>
          {project.client_slug} · {project.preset} · {project.vertical} · <strong>{project.status}</strong>
        </div>
      </div>

      {message && (
        <div style={message.type === 'success' ? s.success : s.error}>
          {message.text}
          <button onClick={() => setMessage(null)} style={{ marginLeft: 12, cursor: 'pointer', background: 'none', border: 'none', fontWeight: 700 }}>✕</button>
        </div>
      )}

      <div style={s.actions}>
        <button style={s.btn} onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending || !project.has_brief}>
          {generateMutation.isPending ? 'Generando...' : 'Genera Piano (Dry Run)'}
        </button>
        <button
          style={s.btnGreen}
          onClick={async () => {
            try {
              await projectsApi.exportCsv(id!)
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : 'Errore export'
              setMessage({ type: 'error', text: `Export CSV: ${msg}` })
            }
          }}
          disabled={!plan}
        >
          Esporta CSV
        </button>
        <button style={s.btnOutline} onClick={() => publishMutation.mutate()} disabled={!plan || publishMutation.isPending}>
          {publishMutation.isPending ? 'Simulando...' : 'Pubblica (Dry Run)'}
        </button>
      </div>

      <div style={s.tabs}>
        {(['overview', 'campaigns', 'preview', 'brief', 'action_plan', 'plan_json', 'audit'] as Tab[]).map(t => (
          <button
            key={t}
            style={{ ...s.tab, ...(activeTab === t ? s.tabActive : {}) }}
            onClick={() => setActiveTab(t)}
          >
            {t === 'overview'     ? 'Overview'
              : t === 'campaigns'  ? 'Campagne'
              : t === 'preview'    ? 'Anteprima'
              : t === 'brief'      ? 'Brief'
              : t === 'action_plan'? 'Piano d\'azione'
              : t === 'plan_json'  ? 'Modifica Piano'
              : 'Audit Log'}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div>
          {plan ? <PlanSummary plan={plan} /> : (
            <div style={s.card}>
              <p style={{ color: T.textGray }}>
                {project.has_brief
                  ? 'Brief caricato. Clicca "Genera Piano" per vedere il preview.'
                  : 'Carica il brief per iniziare.'}
              </p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'campaigns' && (
        <div>
          {plan ? (
            <>
              <PlanSummary plan={plan} />
              {plan.campaigns.map(c => <CampaignCard key={c.external_key} campaign={c} />)}
            </>
          ) : <p style={{ color: T.textGray }}>Genera prima il piano.</p>}
        </div>
      )}

      {activeTab === 'preview' && (() => {
        const briefLangs = (brief as any)?.languages as Record<string, unknown>[] | undefined
        const briefDomain = (brief as any)?.client?.domain || (brief as any)?.hotel?.domain || ''

        const ready   = plan?.campaigns.filter(c => c.can_publish).length ?? 0
        const blocked = plan?.campaigns.filter(c => !c.can_publish).length ?? 0

        return (
          <div>
            {/* Summary bar */}
            {plan && (
              <div style={{ display: 'flex', gap: 24, marginBottom: 20, fontSize: 13, flexWrap: 'wrap' as const }}>
                <span>Campagne totali: <strong>{plan.total_campaigns}</strong></span>
                <span style={{ color: T.success }}>Pronte: <strong>{ready}</strong></span>
                <span style={{ color: blocked > 0 ? T.error : T.textGray }}>Bloccate: <strong>{blocked}</strong></span>
                <span style={{ color: T.textGray, fontSize: 12 }}>
                  Clicca su una campagna per vedere l'anteprima dell'annuncio
                </span>
              </div>
            )}

            {!plan ? (
              <div style={s.card}>
                <p style={{ color: T.textGray, marginBottom: 12 }}>
                  Genera prima il piano per vedere l'anteprima di tutte le campagne.
                </p>
                <button style={s.btn} onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending || !project.has_brief}>
                  {generateMutation.isPending ? 'Generando...' : 'Genera Piano'}
                </button>
              </div>
            ) : (
              plan.campaigns.map(campaign => {
                const briefLang = briefLangs?.find(l => l.code === campaign.language_code)
                let domain = briefDomain
                if (!domain && briefLang?.landing_page) {
                  try { domain = new URL(briefLang.landing_page as string).hostname } catch { /* ok */ }
                }
                return (
                  <CampaignPreviewCard
                    key={campaign.external_key}
                    campaign={campaign}
                    briefLang={briefLang}
                    domain={domain}
                  />
                )
              })
            )}
          </div>
        )
      })()}

      {activeTab === 'brief' && (
        <div>
          {project?.has_brief && briefFetching ? (
            <p style={{ color: T.textGray }}>Caricamento brief...</p>
          ) : (
            <BriefForm
              key={brief ? 'loaded' : 'new'}
              projectId={id!}
              existingBrief={brief ?? null}
              onSaved={() => {
                qc.invalidateQueries({ queryKey: ['project', id] })
                qc.invalidateQueries({ queryKey: ['brief', id] })
                setMessage({ type: 'success', text: 'Brief salvato con successo!' })
                setActiveTab('overview')
              }}
            />
          )}
        </div>
      )}

      {activeTab === 'action_plan' && (
        <div>
          {!project?.has_brief ? (
            <div style={s.card}>
              <p style={{ color: T.textGray }}>Carica prima il brief per generare il Piano d'azione.</p>
            </div>
          ) : briefFetching ? (
            <p style={{ color: T.textGray }}>Caricamento brief...</p>
          ) : brief ? (
            <ActionPlanTab brief={brief} />
          ) : (
            <div style={s.card}><p style={{ color: T.textGray }}>Brief non disponibile.</p></div>
          )}
        </div>
      )}

      {activeTab === 'plan_json' && (
        <div>
          <p style={{ fontSize: 13, color: T.textGray, marginBottom: 12 }}>
            Modifica manualmente il JSON del piano campagne. Utile per aggiustamenti rapidi senza rigenerare.
            {!plan && ' Genera prima il piano con il pulsante "Genera Piano".'}
          </p>
          {plan ? (
            <>
              <textarea
                style={s.textarea}
                value={planJsonText}
                onChange={e => setPlanJsonText(e.target.value)}
                rows={30}
              />
              <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
                <button
                  style={s.btnGreen}
                  onClick={() => {
                    try {
                      const parsed = JSON.parse(planJsonText)
                      savePlanMutation.mutate(parsed)
                    } catch {
                      setMessage({ type: 'error', text: 'JSON non valido — controlla la sintassi.' })
                    }
                  }}
                  disabled={savePlanMutation.isPending}
                >
                  {savePlanMutation.isPending ? 'Salvataggio...' : 'Salva Piano Modificato'}
                </button>
                <button
                  style={s.btnOutline}
                  onClick={() => plan && setPlanJsonText(JSON.stringify(plan, null, 2))}
                >
                  Ripristina
                </button>
              </div>
            </>
          ) : (
            <p style={{ color: T.textGray }}>Genera prima il piano.</p>
          )}
        </div>
      )}

      {activeTab === 'audit' && (
        <div>
          {(audit as any[])?.map((entry: any) => (
            <div key={entry.id} style={s.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{entry.action}</strong>
                <span style={{ fontSize: 12, color: T.textGray }}>{new Date(entry.timestamp).toLocaleString('it-IT')}</span>
              </div>
              {entry.details && (
                <pre style={{ fontSize: 11, color: T.textGray, marginTop: 6, whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(entry.details, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
