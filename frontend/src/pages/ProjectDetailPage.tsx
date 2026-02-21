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

type Tab = 'overview' | 'campaigns' | 'preview' | 'brief' | 'plan_json' | 'audit'

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
            /* ── Search / Retargeting / Demand Gen — RSA preview ── */
            /* Priority: actual RSA from plan ad_group[0] → brief lang fallback */
            (() => {
              const firstAg = campaign.ad_groups[0]
              const planH = firstAg?.rsa_headlines?.length > 0 ? firstAg.rsa_headlines : null
              const planD = firstAg?.rsa_descriptions?.length > 0 ? firstAg.rsa_descriptions : null
              const previewH = planH || (briefLang?.headlines as string[] || [])
              const previewD = planD || (briefLang?.descriptions as string[] || [])

              if (!previewH.length) {
                return (
                  <div style={{ padding: 16, background: T.bgMuted, borderRadius: T.radiusSm, color: T.textGray, fontSize: 13 }}>
                    Asset non trovati per la lingua <strong>{campaign.language_code}</strong> nel brief.
                  </div>
                )
              }
              return (
                <GoogleAdPreview
                  lang={{
                    headlines:    previewH,
                    descriptions: previewD,
                    callouts:     briefLang?.callouts  as string[] || [],
                    sitelinks:    briefLang?.sitelinks as { text: string; description_1: string; description_2: string; final_url: string }[] || [],
                  }}
                  domain={domain}
                />
              )
            })()
          )}

          {/* ── Ad Groups table ── */}
          {campaign.ad_groups.length > 0 && (
            <div style={{ marginTop: 20, borderTop: `1px solid ${T.borderLight}`, paddingTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: T.textGray, marginBottom: 8 }}>
                Ad Groups ({campaign.ad_groups_count})
              </div>
              {campaign.ad_groups.map((ag, i) => (
                <div key={i} style={{ fontSize: 12, padding: '5px 0', borderBottom: `1px solid ${T.borderLight}`, display: 'flex', gap: 16, flexWrap: 'wrap' as const }}>
                  <span style={{ fontWeight: 600 }}>📁 {ag.name}</span>
                  <span style={{ color: T.textGray }}>KW: {ag.keywords_count}</span>
                  <span style={{ color: T.textGray }}>Annunci: {ag.ads_count}</span>
                  {ag.audience_targeting.length > 0 && (
                    <span style={{ color: T.textGray }}>Audience: {ag.audience_targeting.join(', ')}</span>
                  )}
                </div>
              ))}
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
    enabled: activeTab === 'campaigns' || activeTab === 'overview' || activeTab === 'preview',
    retry: false,
  })

  const { data: brief, isFetching: briefFetching } = useQuery({
    queryKey: ['brief', id],
    queryFn: () => projectsApi.getBrief(id!),
    enabled: (activeTab === 'brief' || activeTab === 'preview') && (project?.has_brief ?? false),
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
        {(['overview', 'campaigns', 'preview', 'brief', 'plan_json', 'audit'] as Tab[]).map(t => (
          <button
            key={t}
            style={{ ...s.tab, ...(activeTab === t ? s.tabActive : {}) }}
            onClick={() => setActiveTab(t)}
          >
            {t === 'overview'   ? 'Overview'
              : t === 'campaigns' ? 'Campagne'
              : t === 'preview'   ? 'Anteprima'
              : t === 'brief'     ? 'Brief'
              : t === 'plan_json' ? 'Modifica Piano'
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
