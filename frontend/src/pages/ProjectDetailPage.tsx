import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, type AccountPlanPreview, type CampaignPreview } from '../api/projects'
import BriefForm from '../components/BriefForm'
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

type Tab = 'overview' | 'campaigns' | 'brief' | 'audit' | 'plan_json'

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
    enabled: activeTab === 'campaigns' || activeTab === 'overview',
    retry: false,
  })

  const { data: brief, isFetching: briefFetching } = useQuery({
    queryKey: ['brief', id],
    queryFn: () => projectsApi.getBrief(id!),
    enabled: activeTab === 'brief' && (project?.has_brief ?? false),
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
        {(['overview', 'campaigns', 'brief', 'plan_json', 'audit'] as Tab[]).map(t => (
          <button
            key={t}
            style={{ ...s.tab, ...(activeTab === t ? s.tabActive : {}) }}
            onClick={() => setActiveTab(t)}
          >
            {t === 'overview' ? 'Overview'
              : t === 'campaigns' ? 'Campagne'
              : t === 'brief' ? 'Brief'
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
