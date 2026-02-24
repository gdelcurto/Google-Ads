import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '../api/projects'
import BriefForm from '../components/BriefForm'
import { T } from '../styles/theme'
import { useAutofillJobs } from '../contexts/AutofillJobContext'
import { CampaignCard } from '../components/project/CampaignCard'
import { PlanSummary } from '../components/project/PlanSummary'
import { ActionPlanTab } from '../components/project/ActionPlanTab'
import { CampaignPreviewCard } from '../components/project/CampaignPreviewCard'
import { ScanLogTab } from '../components/project/ScanLogTab'
import { ApiLogTab } from '../components/project/ApiLogTab'

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

type Tab = 'overview' | 'campaigns' | 'preview' | 'brief' | 'action_plan' | 'plan_json' | 'audit' | 'scan_log' | 'api_log'


export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [planJsonText, setPlanJsonText] = useState('')
  const qc = useQueryClient()

  // ── Background auto-fill job tracking (global context) ───────────────────────
  const { runningJobIds, completedResults, registerJob, clearResult } = useAutofillJobs()
  const hasRunningJob = id ? runningJobIds.has(id) : false
  const pendingAutofill = id ? (completedResults[id] ?? null) : null

  const handleJobStarted = (jobId: string) => {
    if (!id) return
    registerJob(id, jobId, project?.name)
  }

  const handleApplyAutofill = () => {
    setActiveTab('brief')
    // pendingAutofill stays in context — BriefForm consumes it via prop
  }

  const handleDismissAutofill = () => {
    if (id) clearResult(id)
  }

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id!),
  })

  const { data: plan } = useQuery({
    queryKey: ['plan', id],
    queryFn: () => projectsApi.getPlan(id!),
    enabled: (project?.has_plan ?? false) || activeTab === 'campaigns' || activeTab === 'overview' || activeTab === 'preview' || activeTab === 'action_plan',
    retry: false,
  })

  const { data: brief, isLoading: briefFetching } = useQuery({
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

  /**
   * Apply a suggested_fix from an AI advisor warning to the brief,
   * then automatically re-generate the plan so the user sees the effect.
   */
  const handleApplyFix = async (fix: NonNullable<import('../api/projects').ValidationWarning['suggested_fix']>) => {
    if (!id) return
    try {
      await projectsApi.applyBriefFix(id, fix.brief_path, fix.value, fix.action)
      qc.invalidateQueries({ queryKey: ['brief', id] })
      setMessage({ type: 'success', text: `Fix applicato: ${fix.label}. Rigenerazione piano in corso…` })
      // Re-generate the plan so the user immediately sees the effect
      generateMutation.mutate()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Errore applicazione fix'
      setMessage({ type: 'error', text: `Impossibile applicare il fix: ${msg}` })
    }
  }

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
          <button onClick={() => setMessage(null)} style={{ marginLeft: 12, cursor: 'pointer', background: 'none', border: 'none', fontWeight: 700 }}><i className="fa-solid fa-xmark"></i></button>
        </div>
      )}

      {/* Auto-fill job in progress */}
      {hasRunningJob && !pendingAutofill && (
        <div style={{ ...s.alert, display: 'flex', alignItems: 'center', gap: 10 }}>
          <i className="fa-solid fa-hourglass-half"></i>
          <span style={{ flex: 1 }}>
            Auto-fill in elaborazione in background — puoi cambiare scheda o pagina liberamente.
            Riceverai una notifica in basso a destra quando il brief è pronto.
          </span>
        </div>
      )}

      {/* Auto-fill result ready banner */}
      {pendingAutofill && (
        <div style={{ ...s.success, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span style={{ flex: 1 }}>
            <i className="fa-solid fa-circle-check"></i> <strong>Auto-fill completato!</strong> Il brief per <em>{pendingAutofill.brand_name}</em> è pronto.
          </span>
          <button
            style={{ ...s.btn, fontSize: 13, padding: '6px 14px' }}
            onClick={handleApplyAutofill}
          >
            Applica al progetto
          </button>
          <button
            onClick={handleDismissAutofill}
            style={{ cursor: 'pointer', background: 'none', border: 'none', fontWeight: 700, fontSize: 16 }}
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>
      )}

      <div style={s.actions}>
        <button style={s.btn} onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending || !project.has_brief}>
          {generateMutation.isPending ? 'Generando...' : plan ? 'Rigenera Piano' : 'Genera Piano'}
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
          {publishMutation.isPending ? 'Pubblicando...' : project.status === 'published' ? 'Ripubblica' : 'Pubblica'}
        </button>
      </div>

      <div style={s.tabs}>
        {(['overview', 'campaigns', 'preview', 'brief', 'action_plan', 'plan_json', 'audit', 'scan_log', 'api_log'] as Tab[]).map(t => (
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
              : t === 'audit'      ? 'Audit Log'
              : t === 'scan_log'   ? 'Scan Log'
              : 'API Log'}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div>
          {plan ? <PlanSummary plan={plan} onApplyFix={handleApplyFix} /> : (
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
              <PlanSummary plan={plan} onApplyFix={handleApplyFix} />
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
              project={project}
              existingBrief={brief ?? null}
              pendingAutofill={pendingAutofill}
              onJobStarted={handleJobStarted}
              onSaved={() => {
                qc.invalidateQueries({ queryKey: ['project', id] })
                qc.invalidateQueries({ queryKey: ['brief', id] })
                if (id) clearResult(id)
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

      {activeTab === 'scan_log' && (
        <ScanLogTab projectId={id!} />
      )}

      {activeTab === 'api_log' && (
        <ApiLogTab projectId={id!} />
      )}
    </div>
  )
}
