import { type AccountPlanPreview, type CampaignPreview, type ValidationWarning } from '../../api/projects'
import { T } from '../../styles/theme'
import { TYPE_COLOR, TYPE_LABEL, CAMPAIGN_STRATEGY } from './constants'

const s: Record<string, React.CSSProperties> = {
  summary: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 },
  summaryCard: {
    background: T.bgCard, borderRadius: T.radiusLg, padding: 20,
    boxShadow: T.shadow, textAlign: 'center', border: `1px solid ${T.borderLight}`,
  },
  summaryNum: { fontSize: 30, fontWeight: 800, color: T.primary },
  summaryLabel: { fontSize: 12, color: T.textGray, marginTop: 4 },
  section: { marginBottom: 20 },
  sectionTitle: { fontSize: 14, fontWeight: 700, color: T.text, marginBottom: 10 },
  table: {
    width: '100%', borderCollapse: 'collapse' as const, fontSize: 13,
  },
  th: {
    textAlign: 'left' as const, padding: '8px 12px', borderBottom: `2px solid ${T.borderLight}`,
    fontSize: 11, fontWeight: 700, color: T.textGray, textTransform: 'uppercase' as const, letterSpacing: 0.5,
  },
  td: {
    padding: '8px 12px', borderBottom: `1px solid ${T.borderLight}`, color: T.text,
  },
  error: {
    background: '#fff0f0', border: '1px solid #fca5a5',
    padding: '10px 14px', borderRadius: T.radiusSm, fontSize: 13, marginBottom: 16, color: T.error,
  },
  alert: {
    background: '#fffbeb', border: `1px solid ${T.yellow}`,
    padding: '10px 14px', borderRadius: T.radiusSm, fontSize: 13, marginBottom: 16, color: '#713f12',
  },
  typeBadge: {
    display: 'inline-block', padding: '2px 8px', borderRadius: 4,
    fontSize: 11, fontWeight: 700, color: '#fff',
  },
  bar: {
    height: 8, borderRadius: 4, minWidth: 4,
  },
  langChip: {
    display: 'inline-block', padding: '3px 10px', borderRadius: 12,
    fontSize: 12, fontWeight: 600, background: T.bgMuted, color: T.text,
    border: `1px solid ${T.borderLight}`,
  },
}

/** Group campaigns by a key and return sorted array */
function groupBy<K extends string>(campaigns: CampaignPreview[], keyFn: (c: CampaignPreview) => K) {
  const map = new Map<K, CampaignPreview[]>()
  for (const c of campaigns) {
    const k = keyFn(c)
    if (!map.has(k)) map.set(k, [])
    map.get(k)!.push(c)
  }
  return Array.from(map.entries())
}

export function PlanSummary({
  plan,
  onApplyFix,
}: {
  plan: AccountPlanPreview
  onApplyFix?: (fix: NonNullable<ValidationWarning['suggested_fix']>) => Promise<void>
}) {
  const publishable = plan.campaigns.filter(c => c.can_publish).length
  const blocked = plan.campaigns.filter(c => !c.can_publish).length
  const totalBudget = plan.campaigns.reduce((sum, c) => sum + c.budget_daily_eur, 0)

  // Group by type
  const byType = groupBy(plan.campaigns, c => c.campaign_type)
    .sort((a, b) => (CAMPAIGN_STRATEGY[a[0]]?.priority ?? 99) - (CAMPAIGN_STRATEGY[b[0]]?.priority ?? 99))

  // Group by language
  const byLang = groupBy(plan.campaigns, c => c.language_code)
    .sort((a, b) => a[0].localeCompare(b[0]))

  // Total ad groups & keywords
  const totalAdGroups = plan.campaigns.reduce((sum, c) => sum + c.ad_groups.length + c.pmax_asset_groups.length, 0)
  const totalKeywords = plan.campaigns.reduce((sum, c) => sum + c.ad_groups.reduce((s2, ag) => s2 + ag.keywords_count, 0), 0)

  return (
    <div>
      {/* ── KPI cards ── */}
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
          <div style={{ ...s.summaryNum, color: blocked > 0 ? T.error : T.textGray }}>{blocked}</div>
          <div style={s.summaryLabel}>Bloccate</div>
        </div>
        <div style={s.summaryCard}>
          <div style={s.summaryNum}>&euro;{totalBudget.toFixed(0)}</div>
          <div style={s.summaryLabel}>Budget/giorno totale</div>
        </div>
      </div>

      {/* ── Validation errors / warnings ── */}
      {plan.validation_errors.length > 0 && (
        <div style={s.error}>
          <strong>Errori validazione:</strong>
          <ul style={{ marginLeft: 16 }}>{plan.validation_errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
      )}

      {/* Structured AI advisor warnings with optional 'Applica' CTA */}
      {(plan.validation_warnings_structured?.length > 0) ? (
        <div style={s.alert}>
          <strong>Warning AI:</strong>
          <ul style={{ marginLeft: 16, marginTop: 6 }}>
            {plan.validation_warnings_structured.map((w, i) => (
              <li key={i} style={{ marginBottom: 8, lineHeight: 1.5 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: T.textGray, marginRight: 6, textTransform: 'uppercase' }}>
                  [{w.code}]
                </span>
                {w.message}
                {w.suggested_fix && onApplyFix && (
                  <button
                    onClick={() => onApplyFix(w.suggested_fix!)}
                    style={{
                      marginLeft: 10, padding: '2px 10px',
                      fontSize: 11, fontWeight: 700, cursor: 'pointer',
                      background: T.primary, color: '#fff', border: 'none',
                      borderRadius: 4,
                    }}
                    title={`Applica al brief: ${w.suggested_fix.brief_path}`}
                  >
                    {w.suggested_fix.label}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : plan.validation_warnings.length > 0 && (
        <div style={s.alert}>
          <strong>Warning:</strong>
          <ul style={{ marginLeft: 16 }}>{plan.validation_warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}

      {/* ── Two-column layout: Type breakdown + Language breakdown ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>

        {/* ── Campaign types breakdown ── */}
        <div style={{ background: T.bgCard, borderRadius: T.radiusLg, padding: 20, boxShadow: T.shadow, border: `1px solid ${T.borderLight}` }}>
          <div style={s.sectionTitle}>Campagne per tipo</div>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Tipo</th>
                <th style={{ ...s.th, textAlign: 'center' as const }}>N.</th>
                <th style={{ ...s.th, textAlign: 'right' as const }}>Budget/g</th>
                <th style={{ ...s.th, width: 120 }}>Distribuzione</th>
              </tr>
            </thead>
            <tbody>
              {byType.map(([type, campaigns]) => {
                const typeBudget = campaigns.reduce((sum, c) => sum + c.budget_daily_eur, 0)
                const pct = totalBudget > 0 ? (typeBudget / totalBudget) * 100 : 0
                const color = TYPE_COLOR[type] || T.textGray
                return (
                  <tr key={type}>
                    <td style={s.td}>
                      <span style={{ ...s.typeBadge, background: color }}>
                        {TYPE_LABEL[type] || type}
                      </span>
                    </td>
                    <td style={{ ...s.td, textAlign: 'center' }}>{campaigns.length}</td>
                    <td style={{ ...s.td, textAlign: 'right', fontWeight: 600 }}>
                      &euro;{typeBudget.toFixed(0)}
                    </td>
                    <td style={s.td}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ flex: 1, background: T.bgMuted, borderRadius: 4, height: 8 }}>
                          <div style={{ ...s.bar, width: `${pct}%`, background: color }} />
                        </div>
                        <span style={{ fontSize: 11, color: T.textGray, minWidth: 32, textAlign: 'right' }}>
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* ── Language breakdown ── */}
        <div style={{ background: T.bgCard, borderRadius: T.radiusLg, padding: 20, boxShadow: T.shadow, border: `1px solid ${T.borderLight}` }}>
          <div style={s.sectionTitle}>Mercati / Lingue</div>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Lingua</th>
                <th style={{ ...s.th, textAlign: 'center' as const }}>Campagne</th>
                <th style={{ ...s.th, textAlign: 'right' as const }}>Budget/g</th>
                <th style={{ ...s.th, textAlign: 'center' as const }}>Stato</th>
              </tr>
            </thead>
            <tbody>
              {byLang.map(([lang, campaigns]) => {
                const langBudget = campaigns.reduce((sum, c) => sum + c.budget_daily_eur, 0)
                const allReady = campaigns.every(c => c.can_publish)
                const someBlocked = campaigns.some(c => !c.can_publish)
                return (
                  <tr key={lang}>
                    <td style={s.td}>
                      <span style={s.langChip}>{lang.toUpperCase()}</span>
                    </td>
                    <td style={{ ...s.td, textAlign: 'center' }}>{campaigns.length}</td>
                    <td style={{ ...s.td, textAlign: 'right', fontWeight: 600 }}>
                      &euro;{langBudget.toFixed(0)}
                    </td>
                    <td style={{ ...s.td, textAlign: 'center' }}>
                      {allReady ? (
                        <span style={{ color: T.success, fontWeight: 700, fontSize: 12 }}>Pronte</span>
                      ) : someBlocked ? (
                        <span style={{ color: T.error, fontWeight: 700, fontSize: 12 }}>
                          {campaigns.filter(c => !c.can_publish).length} bloccate
                        </span>
                      ) : (
                        <span style={{ color: T.textGray, fontSize: 12 }}>—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Bottom row: stats + campaign list ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 20 }}>

        {/* ── Quick stats ── */}
        <div style={{ background: T.bgCard, borderRadius: T.radiusLg, padding: 20, boxShadow: T.shadow, border: `1px solid ${T.borderLight}` }}>
          <div style={s.sectionTitle}>Riepilogo contenuti</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { label: 'Ad Group / Asset Group', value: totalAdGroups },
              { label: 'Keyword totali', value: totalKeywords },
              { label: 'Lingue', value: byLang.length },
              { label: 'Budget mensile stimato', value: `\u20AC${(totalBudget * 30).toFixed(0)}` },
            ].map(({ label, value }) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: `1px solid ${T.borderLight}` }}>
                <span style={{ fontSize: 13, color: T.textGray }}>{label}</span>
                <span style={{ fontSize: 15, fontWeight: 700, color: T.text }}>{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Campaign list mini ── */}
        <div style={{ background: T.bgCard, borderRadius: T.radiusLg, padding: 20, boxShadow: T.shadow, border: `1px solid ${T.borderLight}` }}>
          <div style={s.sectionTitle}>Tutte le campagne</div>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Campagna</th>
                <th style={s.th}>Tipo</th>
                <th style={s.th}>Lingua</th>
                <th style={{ ...s.th, textAlign: 'right' as const }}>Budget/g</th>
                <th style={{ ...s.th, textAlign: 'center' as const }}>Stato</th>
              </tr>
            </thead>
            <tbody>
              {plan.campaigns.map(c => {
                const color = TYPE_COLOR[c.campaign_type] || T.textGray
                return (
                  <tr key={c.external_key}>
                    <td style={{ ...s.td, fontWeight: 600, fontSize: 12 }}>{c.campaign_name}</td>
                    <td style={s.td}>
                      <span style={{ ...s.typeBadge, background: color, fontSize: 10, padding: '1px 6px' }}>
                        {TYPE_LABEL[c.campaign_type] || c.campaign_type}
                      </span>
                    </td>
                    <td style={{ ...s.td, fontSize: 12 }}>{c.language_code.toUpperCase()}</td>
                    <td style={{ ...s.td, textAlign: 'right', fontSize: 12 }}>
                      &euro;{c.budget_daily_eur.toFixed(2)}
                    </td>
                    <td style={{ ...s.td, textAlign: 'center' }}>
                      {c.can_publish ? (
                        <span style={{ color: T.success, fontWeight: 700, fontSize: 11 }}>Pronta</span>
                      ) : (
                        <span style={{ color: T.error, fontWeight: 700, fontSize: 11 }}>
                          {c.publish_blockers.length} {c.publish_blockers.length === 1 ? 'blocco' : 'blocchi'}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
