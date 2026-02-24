import React from 'react'
import { FormState, LangState, TypeObjective, BidStrategyChoice, CAMPAIGN_TYPES, DEFAULT_TYPE_OBJECTIVE, DEFAULT_BID_STRATEGY_BY_TYPE, OBJECTIVE_OPTIONS, BID_STRATEGY_OPTIONS } from '../types'
import { css } from '../styles'
import { T } from '../../../styles/theme'
import { StrategyResult } from '../hooks/useBudgetStrategy'

interface Props {
  form: FormState
  setField: (key: keyof FormState, val: string) => void
  langs: LangState[]
  selectedTypes: Set<string>
  setSelectedTypes: (next: Set<string>) => void
  objectivesByType: Record<string, TypeObjective>
  setObjectivesByType: React.Dispatch<React.SetStateAction<Record<string, TypeObjective>>>
  budgetByTypeLang: Record<string, Record<string, string>>
  setBudgetByTypeLang: React.Dispatch<React.SetStateAction<Record<string, Record<string, string>>>>
  strategyResult: StrategyResult | null
  setStrategyResult: (v: StrategyResult | null) => void
  strategyPanelOpen: boolean
  setStrategyPanelOpen: (v: boolean) => void
  budgetStrategyMutation: { mutate: () => void; isPending: boolean }
  canRecalculate: boolean
  handleRecalculateBudget: () => void
  redistributeBudget: (nextTypes: Set<string>) => void
}

export function Step1Obiettivi({
  form, setField, langs, selectedTypes, setSelectedTypes,
  objectivesByType, setObjectivesByType, budgetByTypeLang, setBudgetByTypeLang,
  strategyResult, setStrategyResult, strategyPanelOpen, setStrategyPanelOpen,
  budgetStrategyMutation, canRecalculate, handleRecalculateBudget, redistributeBudget,
}: Props) {
  return (
    <>
      <div style={css.section}>
        <div style={css.sectionTitle}>Obiettivi per tipologia di campagna</div>
        <div style={{ fontSize: 12, color: T.textGray, marginBottom: 12 }}>
          Definisci obiettivo primario e azione di conversione per ogni tipo attivo.
          Le campagne non selezionate nella tabella budget non vengono mostrate.
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', paddingBottom: 10, paddingRight: 16, color: T.textGray, fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                  Tipo campagna
                </th>
                <th style={{ textAlign: 'left', paddingBottom: 10, paddingLeft: 8, paddingRight: 8, color: T.textGray, fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                  Obiettivo primario *
                </th>
                <th style={{ textAlign: 'left', paddingBottom: 10, paddingLeft: 8, color: T.textGray, fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                  Azione di conversione primaria
                </th>
              </tr>
            </thead>
            <tbody>
              {CAMPAIGN_TYPES.map(ct => {
                const isSel = selectedTypes.has(ct.key)
                if (!isSel) return null
                const obj: TypeObjective = objectivesByType[ct.key] ?? DEFAULT_TYPE_OBJECTIVE
                return (
                  <tr key={ct.key} style={{ borderTop: `1px solid ${T.borderLight}` }}>
                    <td style={{ padding: '10px 16px 10px 0', verticalAlign: 'middle', whiteSpace: 'nowrap', fontWeight: 600, fontSize: 13 }}>
                      {ct.label}
                    </td>
                    <td style={{ padding: '8px 8px', verticalAlign: 'middle' }}>
                      <select
                        style={{ ...css.select, marginBottom: 0 }}
                        value={obj.primary_objective}
                        onChange={e => setObjectivesByType(prev => ({
                          ...prev,
                          [ct.key]: { ...obj, primary_objective: e.target.value },
                        }))}
                      >
                        {OBJECTIVE_OPTIONS.map(o => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </td>
                    <td style={{ padding: '8px 8px', verticalAlign: 'middle' }}>
                      <input
                        style={{ ...css.input, marginBottom: 0 }}
                        value={obj.primary_conversion_action}
                        onChange={e => setObjectivesByType(prev => ({
                          ...prev,
                          [ct.key]: { ...obj, primary_conversion_action: e.target.value },
                        }))}
                        placeholder="purchase"
                      />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {[...selectedTypes].length === 0 && (
            <div style={{ padding: '12px 0', color: T.textGray, fontSize: 13 }}>
              Seleziona almeno un tipo di campagna nella sezione Budget qui sotto.
            </div>
          )}
        </div>
      </div>

      <div style={css.section}>
        <div style={css.sectionTitle}>Strategia di offerta per tipologia di campagna</div>
        <div style={{ fontSize: 12, color: T.textGray, marginBottom: 12 }}>
          Definisci la strategia di offerta da applicare su Google Ads per ogni tipo di campagna attivo.
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', paddingBottom: 10, paddingRight: 16, color: T.textGray, fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                  Tipo campagna
                </th>
                <th style={{ textAlign: 'left', paddingBottom: 10, paddingLeft: 8, color: T.textGray, fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                  Strategia di offerta *
                </th>
              </tr>
            </thead>
            <tbody>
              {CAMPAIGN_TYPES.map(ct => {
                const isSel = selectedTypes.has(ct.key)
                if (!isSel) return null
                const obj: TypeObjective = objectivesByType[ct.key] ?? {
                  ...DEFAULT_TYPE_OBJECTIVE,
                  bid_strategy: DEFAULT_BID_STRATEGY_BY_TYPE[ct.key] as BidStrategyChoice,
                }
                return (
                  <tr key={ct.key} style={{ borderTop: `1px solid ${T.borderLight}` }}>
                    <td style={{ padding: '10px 16px 10px 0', verticalAlign: 'middle', whiteSpace: 'nowrap', fontWeight: 600, fontSize: 13 }}>
                      {ct.label}
                    </td>
                    <td style={{ padding: '8px 8px', verticalAlign: 'middle' }}>
                      <select
                        style={{ ...css.select, marginBottom: 0 }}
                        value={obj.bid_strategy ?? DEFAULT_BID_STRATEGY_BY_TYPE[ct.key]}
                        onChange={e => setObjectivesByType(prev => ({
                          ...prev,
                          [ct.key]: { ...obj, bid_strategy: e.target.value as BidStrategyChoice },
                        }))}
                      >
                        {BID_STRATEGY_OPTIONS.map(o => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {[...selectedTypes].length === 0 && (
            <div style={{ padding: '12px 0', color: T.textGray, fontSize: 13 }}>
              Seleziona almeno un tipo di campagna nella sezione Budget qui sotto.
            </div>
          )}
        </div>
      </div>

      <div style={css.section}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', ...css.sectionTitle }}>
          <span>Budget campagne (€/giorno per lingua)</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
            {canRecalculate && (
              <button
                style={{ ...css.btnAdd, fontSize: 12, padding: '5px 14px', background: T.primary }}
                onClick={handleRecalculateBudget}
                title="Ridistribuisce il budget totale tra le campagne selezionate mantenendo le proporzioni AI"
              >
                ⟳ Ricalcola budget
              </button>
            )}
            <button
              style={{ ...css.btnAdd, fontSize: 12, padding: '5px 14px' }}
              onClick={() => budgetStrategyMutation.mutate()}
              disabled={budgetStrategyMutation.isPending}
            >
              {budgetStrategyMutation.isPending
                ? <><i className="fa-solid fa-hourglass-half"></i> Analisi in corso...</>
                : <><i className="fa-solid fa-wand-magic-sparkles"></i> Suggerisci Strategia AI</>}
            </button>
          </div>
        </div>
        {/* Optional total budget hint — shown only if already populated */}
        {form.total_monthly_eur && parseFloat(form.total_monthly_eur) > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, fontSize: 12, color: T.textGray }}>
            <span>Budget mensile:</span>
            <strong style={{ color: T.text }}>€{parseFloat(form.total_monthly_eur).toLocaleString('it-IT')}/mese</strong>
            <button
              style={{ ...css.btnRed, padding: '2px 8px', fontSize: 11 }}
              onClick={() => { setField('total_monthly_eur', ''); setBudgetByTypeLang({}); setStrategyResult(null); setStrategyPanelOpen(false) }}
            >
              <i className="fa-solid fa-xmark"></i> Azzera
            </button>
          </div>
        )}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', paddingBottom: 10, paddingRight: 16, color: T.textGray, fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                  Tipo campagna
                </th>
                {langs.map(l => (
                  <th key={l.code} style={{ textAlign: 'center', paddingBottom: 10, paddingLeft: 8, paddingRight: 8, color: T.textGray, fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                    {l.code || '—'} (€/giorno)
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {CAMPAIGN_TYPES.map(ct => {
                const isSel = selectedTypes.has(ct.key)
                return (
                  <tr key={ct.key} style={{ borderTop: `1px solid ${T.borderLight}` }}>
                    <td style={{ padding: '8px 16px 8px 0', verticalAlign: 'middle' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={isSel}
                          onChange={e => {
                            const next = new Set(selectedTypes)
                            if (e.target.checked) next.add(ct.key); else next.delete(ct.key)
                            setSelectedTypes(next)
                            if (!strategyResult) redistributeBudget(next)
                          }}
                          style={{ width: 15, height: 15, accentColor: T.primary, cursor: 'pointer', flexShrink: 0 }}
                        />
                        <span style={{ fontWeight: isSel ? 600 : 400, color: isSel ? T.text : T.textGray, whiteSpace: 'nowrap' }}>
                          {ct.label}
                        </span>
                      </label>
                    </td>
                    {langs.map(l => {
                      const code = l.code.toUpperCase()
                      const val = budgetByTypeLang[ct.key]?.[code] ?? ''
                      return (
                        <td key={code} style={{ padding: '8px', verticalAlign: 'middle', textAlign: 'center' }}>
                          <input
                            type="number"
                            min="0"
                            step="1"
                            disabled={!isSel}
                            value={val}
                            onChange={e => setBudgetByTypeLang(prev => ({
                              ...prev,
                              [ct.key]: { ...(prev[ct.key] ?? {}), [code]: e.target.value },
                            }))}
                            placeholder="0"
                            style={{
                              ...css.input,
                              width: 90,
                              textAlign: 'right',
                              opacity: isSel ? 1 : 0.35,
                              background: isSel ? T.bgCard : T.bgMuted,
                              cursor: isSel ? 'text' : 'not-allowed',
                            }}
                          />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {/* Totals row */}
        {selectedTypes.size > 0 && (() => {
          const langTotals: Record<string, number> = {}
          let grandDaily = 0
          for (const ct of CAMPAIGN_TYPES) {
            if (!selectedTypes.has(ct.key)) continue
            for (const l of langs) {
              const code = l.code.toUpperCase()
              const d = parseFloat(budgetByTypeLang[ct.key]?.[code] ?? '0') || 0
              langTotals[code] = (langTotals[code] || 0) + d
              grandDaily += d
            }
          }
          const grandMonthly = Math.round(grandDaily * 30.44)
          return (
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: `2px solid ${T.borderLight}`, display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'center' }}>
              {langs.map(l => {
                const code = l.code.toUpperCase()
                return (
                  <div key={code} style={{ fontSize: 13, color: T.textGray }}>
                    {code} tot.: <strong style={{ color: T.text }}>€{(langTotals[code] || 0).toFixed(0)}/g</strong>
                  </div>
                )
              })}
              <div style={{ marginLeft: 'auto', fontSize: 13, color: T.textGray }}>
                Mensile stimato: <strong style={{ color: T.primary, fontSize: 15 }}>€{grandMonthly.toLocaleString('it-IT')}</strong>
              </div>
            </div>
          )
        })()}

        {/* ── Budget Strategy Rationale Panel ── */}
        {strategyPanelOpen && strategyResult && (
          <div style={{ marginTop: 20, background: T.bgCard, border: `1px solid ${T.primary}33`, borderRadius: T.radiusLg, padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14, color: T.primary, marginBottom: 4 }}>Strategia consigliata dall'AI</div>
                <div style={{ fontSize: 13, color: T.textGray }}>
                  Budget mensile consigliato:{' '}
                  <strong style={{ color: T.text, fontSize: 15 }}>
                    €{strategyResult.suggested_total_monthly_eur.toLocaleString('it-IT')}/mese
                  </strong>
                  {' '}— {strategyResult.recommended_types.length} campagne attive
                </div>
              </div>
              <button style={css.btnRed} onClick={() => setStrategyPanelOpen(false)}><i className="fa-solid fa-xmark"></i></button>
            </div>
            {strategyResult.min_budget_warning && (
              <div style={{ background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#92400e' }}>
                <i className="fa-solid fa-triangle-exclamation"></i> {strategyResult.min_budget_warning}
              </div>
            )}
            {strategyResult.overall_strategy && (
              <div style={{ fontSize: 13, color: T.textGray, marginBottom: 14, lineHeight: 1.6, borderBottom: `1px solid ${T.borderLight}`, paddingBottom: 12 }}>
                {strategyResult.overall_strategy}
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 10 }}>
              {strategyResult.recommended_types.map(backendKey => {
                const labelMap: Record<string, string> = {
                  search_brand: 'Brand Search',
                  search_acquisition: 'Acquisition Search',
                  performance_max: 'Performance Max',
                  retargeting: 'Retargeting',
                  demand_gen: 'Demand Gen',
                }
                const pct = strategyResult.budget_split[backendKey]
                return (
                  <div key={backendKey} style={{ background: T.bgPage, border: `1px solid ${T.borderLight}`, borderRadius: 8, padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <strong style={{ fontSize: 13, color: T.text }}>{labelMap[backendKey] || backendKey}</strong>
                      {pct != null && <span style={{ fontSize: 12, color: T.primary, fontWeight: 700 }}>{pct}%</span>}
                    </div>
                    <div style={{ fontSize: 12, color: T.textGray, lineHeight: 1.5 }}>
                      {strategyResult.rationale[backendKey] || ''}
                    </div>
                  </div>
                )
              })}
            </div>
            <div style={{ marginTop: 12, fontSize: 12, color: T.textGray }}>
              Le campagne selezionate e i budget sono stati applicati automaticamente alla tabella sopra. Puoi modificarli liberamente.
            </div>
          </div>
        )}
      </div>
    </>
  )
}
