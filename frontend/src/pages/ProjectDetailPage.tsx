import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, type AccountPlanPreview, type CampaignPreview } from '../api/projects'
import BriefForm from '../components/BriefForm'

const s: Record<string, React.CSSProperties> = {
  header: { marginBottom: 24 },
  h1: { fontSize: 22, fontWeight: 700, color: '#1e3a5f', marginBottom: 4 },
  tabs: { display: 'flex', gap: 4, borderBottom: '2px solid #e2e8f0', marginBottom: 28 },
  tab: { padding: '10px 20px', cursor: 'pointer', fontSize: 14, fontWeight: 600, color: '#64748b', border: 'none', background: 'transparent', borderBottom: '2px solid transparent', marginBottom: -2 },
  tabActive: { color: '#1e3a5f', borderBottom: '2px solid #1e3a5f' },
  actions: { display: 'flex', gap: 12, marginBottom: 24 },
  btn: { background: '#1e3a5f', color: '#fff', border: 'none', padding: '9px 18px', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  btnGreen: { background: '#059669', color: '#fff', border: 'none', padding: '9px 18px', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  btnOrange: { background: '#d97706', color: '#fff', border: 'none', padding: '9px 18px', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  alert: { background: '#fef3c7', border: '1px solid #fcd34d', padding: '10px 14px', borderRadius: 6, fontSize: 13, marginBottom: 16 },
  error: { background: '#fef2f2', border: '1px solid #fca5a5', padding: '10px 14px', borderRadius: 6, fontSize: 13, marginBottom: 16, color: '#dc2626' },
  success: { background: '#f0fdf4', border: '1px solid #86efac', padding: '10px 14px', borderRadius: 6, fontSize: 13, marginBottom: 16, color: '#166534' },
  card: { background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', marginBottom: 16 },
  campaignName: { fontWeight: 700, fontSize: 15, color: '#1e3a5f', marginBottom: 6 },
  metaRow: { display: 'flex', gap: 16, fontSize: 13, color: '#64748b', marginBottom: 8, flexWrap: 'wrap' },
  badge: { display: 'inline-block', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, color: '#fff', background: '#64748b' },
  badgeGreen: { display: 'inline-block', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, color: '#fff', background: '#059669' },
  badgeRed: { display: 'inline-block', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, color: '#fff', background: '#dc2626' },
  blockers: { background: '#fef2f2', padding: '8px 12px', borderRadius: 6, fontSize: 12, color: '#dc2626', marginTop: 6 },
  adGroups: { marginTop: 10, paddingTop: 10, borderTop: '1px solid #f1f5f9' },
  agRow: { fontSize: 13, color: '#374151', padding: '4px 0', borderBottom: '1px dashed #f1f5f9' },
  summary: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 },
  summaryCard: { background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', textAlign: 'center' },
  summaryNum: { fontSize: 28, fontWeight: 800, color: '#1e3a5f' },
  summaryLabel: { fontSize: 12, color: '#94a3b8', marginTop: 4 },
  textarea: { width: '100%', fontFamily: 'monospace', fontSize: 12, padding: 12, border: '1px solid #cbd5e1', borderRadius: 6, minHeight: 400, resize: 'vertical' },
}

type Tab = 'overview' | 'campaigns' | 'brief' | 'audit'

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
        style={{ ...s.btn, marginTop: 10, padding: '5px 12px', fontSize: 12, background: '#f1f5f9', color: '#374151' }}
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
            <div key={`pmax-${i}`} style={{ ...s.agRow, background: '#f8fafc' }}>
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
          <div style={{ ...s.summaryNum, color: '#059669' }}>{publishable}</div>
          <div style={s.summaryLabel}>Pronte per publish</div>
        </div>
        <div style={s.summaryCard}>
          <div style={{ ...s.summaryNum, color: '#dc2626' }}>{blocked}</div>
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
        <div style={{ fontSize: 13, color: '#64748b' }}>
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
        <button style={s.btnGreen} onClick={() => projectsApi.exportCsv(id!)} disabled={!plan}>
          Esporta CSV
        </button>
        <button style={s.btnOrange} onClick={() => publishMutation.mutate()} disabled={!plan || publishMutation.isPending}>
          {publishMutation.isPending ? 'Simulando...' : 'Pubblica (Dry Run)'}
        </button>
      </div>

      <div style={s.tabs}>
        {(['overview', 'campaigns', 'brief', 'audit'] as Tab[]).map(t => (
          <button
            key={t}
            style={{ ...s.tab, ...(activeTab === t ? s.tabActive : {}) }}
            onClick={() => setActiveTab(t)}
          >
            {t === 'overview' ? 'Overview' : t === 'campaigns' ? 'Campagne' : t === 'brief' ? 'Brief' : 'Audit Log'}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div>
          {plan ? <PlanSummary plan={plan} /> : (
            <div style={s.card}>
              <p style={{ color: '#64748b' }}>
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
          ) : <p style={{ color: '#64748b' }}>Genera prima il piano.</p>}
        </div>
      )}

      {activeTab === 'brief' && (
        <div>
          {project?.has_brief && briefFetching ? (
            <p style={{ color: '#64748b' }}>Caricamento brief...</p>
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

      {activeTab === 'audit' && (
        <div>
          {(audit as any[])?.map((entry: any) => (
            <div key={entry.id} style={s.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{entry.action}</strong>
                <span style={{ fontSize: 12, color: '#94a3b8' }}>{new Date(entry.timestamp).toLocaleString('it-IT')}</span>
              </div>
              {entry.details && (
                <pre style={{ fontSize: 11, color: '#64748b', marginTop: 6, whiteSpace: 'pre-wrap' }}>
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
