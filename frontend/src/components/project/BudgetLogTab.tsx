import { useState } from 'react'
import { T } from '../../styles/theme'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BudgetStrategyLog {
  ts: string
  overall_strategy: string
  suggested_total_monthly_eur: number
  min_budget_warning: string | null
  recommended_types: string[]
  budget_split: Record<string, number>
  daily_by_type_lang: Record<string, Record<string, number>>
  rationale: Record<string, string>
}

export interface BudgetValidationIssue {
  ts: string
  code: string
  message: string
  level: 'error' | 'warning' | 'info'
  agent: string
  suggested_fix?: string | null
}

const STORAGE_STRATEGY = (id: string) => `budget_strategy_log_${id}`
const STORAGE_VALIDATION = (id: string) => `budget_validation_log_${id}`

// ── Helpers ───────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  search_brand:       'Search Brand',
  search_acquisition: 'Search Acquisition',
  performance_max:    'Performance Max',
  retargeting:        'Retargeting',
  demand_gen:         'Demand Gen',
}

const levelColor = (l: string) =>
  l === 'error' ? T.error : l === 'warning' ? T.warning : T.textGray

const levelBg = (l: string) =>
  l === 'error' ? '#fff1f1' : l === 'warning' ? '#fffbeb' : '#f8f8f8'

const levelIcon = (l: string) =>
  l === 'error' ? 'fa-circle-xmark' : l === 'warning' ? 'fa-triangle-exclamation' : 'fa-circle-info'

// ── Component ─────────────────────────────────────────────────────────────────

export function BudgetLogTab({ projectId }: { projectId: string }) {
  const [, forceRender] = useState(0)

  const rawStrategy   = localStorage.getItem(STORAGE_STRATEGY(projectId))
  const rawValidation = localStorage.getItem(STORAGE_VALIDATION(projectId))

  const strategies: BudgetStrategyLog[] = rawStrategy
    ? (() => { try { return JSON.parse(rawStrategy) } catch { return [] } })()
    : []

  const validations: BudgetValidationIssue[] = rawValidation
    ? (() => { try { return JSON.parse(rawValidation) } catch { return [] } })()
    : []

  const clearAll = () => {
    localStorage.removeItem(STORAGE_STRATEGY(projectId))
    localStorage.removeItem(STORAGE_VALIDATION(projectId))
    forceRender(n => n + 1)
  }

  if (strategies.length === 0 && validations.length === 0) {
    return (
      <div style={{ padding: '40px 0', textAlign: 'center', color: T.textGray, fontSize: 14 }}>
        Nessun log disponibile. Usa il suggeritore budget nel Brief o genera un piano per vedere i passaggi.
      </div>
    )
  }

  return (
    <div>
      {/* Header ─────────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ fontSize: 13, color: T.textGray }}>
          {strategies.length > 0 && <span>{strategies.length} strateg{strategies.length === 1 ? 'ia AI' : 'ie AI'}</span>}
          {strategies.length > 0 && validations.length > 0 && <span style={{ margin: '0 8px' }}>·</span>}
          {validations.length > 0 && <span>{validations.length} issue{validations.length !== 1 ? 's' : ''} di validazione</span>}
        </div>
        <button
          style={{
            background: 'transparent', border: `1px solid ${T.border}`,
            color: T.textGray, padding: '4px 12px', borderRadius: T.radiusSm,
            cursor: 'pointer', fontSize: 12,
          }}
          onClick={clearAll}
        >
          Cancella log
        </button>
      </div>

      {/* ── AI Strategy entries ──────────────────────────────────────────────── */}
      {strategies.map((s, idx) => (
        <div
          key={idx}
          style={{
            border: `1px solid ${T.borderLight}`, borderRadius: T.radiusLg,
            marginBottom: 20, overflow: 'hidden',
          }}
        >
          {/* Strategy header */}
          <div style={{
            background: T.bgMuted, padding: '10px 16px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            borderBottom: `1px solid ${T.borderLight}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <i className="fa-solid fa-chart-pie" style={{ color: T.primary, fontSize: 13 }} />
              <span style={{ fontWeight: 700, fontSize: 13, color: T.text }}>
                Strategia Budget AI
              </span>
              <span style={{
                background: T.primary, color: '#fff', fontSize: 11, fontWeight: 700,
                padding: '2px 8px', borderRadius: 99,
              }}>
                €{s.suggested_total_monthly_eur.toLocaleString('it-IT')}/mese
              </span>
            </div>
            <span style={{ fontSize: 11, color: T.textGray }}>
              {new Date(s.ts).toLocaleString('it-IT')}
            </span>
          </div>

          {/* Overall strategy text */}
          {s.overall_strategy && (
            <div style={{ padding: '12px 16px', fontSize: 13, color: T.text, lineHeight: 1.6, borderBottom: `1px solid ${T.borderLight}` }}>
              {s.overall_strategy}
            </div>
          )}

          {/* Min budget warning */}
          {s.min_budget_warning && (
            <div style={{
              padding: '8px 16px', fontSize: 12.5, color: '#713f12',
              background: '#fffbeb', borderBottom: `1px solid #fef08a`,
              display: 'flex', gap: 8, alignItems: 'flex-start',
            }}>
              <i className="fa-solid fa-triangle-exclamation" style={{ color: T.warning, marginTop: 2 }} />
              {s.min_budget_warning}
            </div>
          )}

          {/* Budget split table */}
          {Object.keys(s.budget_split).length > 0 && (
            <div style={{ padding: '12px 16px', borderBottom: `1px solid ${T.borderLight}` }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: T.textGray, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Distribuzione budget
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {Object.entries(s.budget_split).map(([type, pct]) => (
                  <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 160, fontSize: 12.5, color: T.text, fontWeight: 600 }}>
                      {TYPE_LABELS[type] || type}
                    </div>
                    <div style={{ flex: 1, height: 6, background: T.borderLight, borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: T.primary, borderRadius: 3 }} />
                    </div>
                    <div style={{ width: 40, textAlign: 'right', fontSize: 12.5, color: T.text, fontWeight: 700 }}>
                      {pct}%
                    </div>
                    {s.daily_by_type_lang[type] && (
                      <div style={{ fontSize: 11, color: T.textGray, minWidth: 90, textAlign: 'right' }}>
                        {Object.entries(s.daily_by_type_lang[type]).map(([lang, daily]) =>
                          `${lang}: €${daily}/g`
                        ).join(' · ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rationale per type */}
          {Object.keys(s.rationale).length > 0 && (
            <div style={{ padding: '12px 16px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: T.textGray, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Ragionamento per tipo
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Object.entries(s.rationale).map(([type, reason]) => (
                  <div key={type} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{
                      fontSize: 11, fontWeight: 700, color: T.primary,
                      background: '#f0f4ff', padding: '2px 8px', borderRadius: 99,
                      whiteSpace: 'nowrap',
                    }}>
                      {TYPE_LABELS[type] || type}
                    </span>
                    <span style={{ fontSize: 12.5, color: T.textGray, lineHeight: 1.5 }}>{reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}

      {/* ── Validation issues from BudgetStrategistAgent ─────────────────────── */}
      {validations.length > 0 && (
        <div style={{ border: `1px solid ${T.borderLight}`, borderRadius: T.radiusLg, overflow: 'hidden' }}>
          <div style={{
            background: T.bgMuted, padding: '10px 16px',
            borderBottom: `1px solid ${T.borderLight}`,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <i className="fa-solid fa-shield-halved" style={{ color: T.textGray, fontSize: 13 }} />
            <span style={{ fontWeight: 700, fontSize: 13, color: T.text }}>
              Validazione BudgetStrategistAgent
            </span>
          </div>
          {validations.map((v, i) => (
            <div
              key={i}
              style={{
                padding: '10px 16px',
                borderTop: i === 0 ? 'none' : `1px solid ${T.borderLight}`,
                background: levelBg(v.level),
                display: 'flex', gap: 10, alignItems: 'flex-start',
              }}
            >
              <i
                className={`fa-solid ${levelIcon(v.level)}`}
                style={{ color: levelColor(v.level), marginTop: 2, flexShrink: 0 }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 11, color: T.textGray }}>{v.code}</span>
                  <span style={{ fontSize: 11, color: T.textGray }}>·</span>
                  <span style={{ fontSize: 11, color: T.textGray }}>{new Date(v.ts).toLocaleString('it-IT')}</span>
                </div>
                <div style={{ fontSize: 13, color: T.text, lineHeight: 1.5 }}>{v.message}</div>
                {v.suggested_fix && (
                  <div style={{ fontSize: 12, color: T.textGray, marginTop: 4, fontStyle: 'italic' }}>
                    💡 {v.suggested_fix}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
