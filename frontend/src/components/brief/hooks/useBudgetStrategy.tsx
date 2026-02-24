// ── useBudgetStrategy ─────────────────────────────────────────────────────────
// Budget strategy suggestion mutation + state for the BriefForm wizard.

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { autofillApi } from '../../../api/projects'
import { FormState, LangState } from '../types'
import { appendApiLog } from '../utils'

export interface StrategyResult {
  recommended_types: string[]
  budget_split: Record<string, number>
  daily_by_type_lang: Record<string, Record<string, number>>
  rationale: Record<string, string>
  overall_strategy: string
  suggested_total_monthly_eur: number
  min_budget_warning: string | null
  ai_raw_response?: string | null
  ai_prompt_used?: string | null
  reasoning_steps?: Array<{ step: number; label: string; detail: string; value: string }>
}

interface UseBudgetStrategyParams {
  form: FormState
  langs: LangState[]
  projectId: string
  setField: (key: keyof FormState, val: string) => void
  setSelectedTypes: React.Dispatch<React.SetStateAction<Set<string>>>
  setBudgetByTypeLang: React.Dispatch<React.SetStateAction<Record<string, Record<string, string>>>>
  setErrors: (errs: string[]) => void
}

const backendToFrontend: Record<string, string> = {
  search_brand: 'brand',
  search_acquisition: 'acquisition',
  performance_max: 'pmax',
  retargeting: 'retargeting',
  demand_gen: 'demand_gen',
}

export function useBudgetStrategy({
  form, langs, projectId, setField, setSelectedTypes, setBudgetByTypeLang, setErrors,
}: UseBudgetStrategyParams) {
  const [strategyResult, setStrategyResult] = useState<StrategyResult | null>(null)
  const [strategyPanelOpen, setStrategyPanelOpen] = useState(false)

  const budgetStrategyMutation = useMutation({
    mutationFn: () => {
      if (!form.brand_name) throw new Error('Inserisci il nome del brand (Step 0) prima di richiedere la strategia.')
      const existingBudget = parseFloat(form.total_monthly_eur) || 0
      return autofillApi.suggestBudgetStrategy({
        brand_name:     form.brand_name,
        hotel_category: form.hotel_category || 'city_hotel',
        stars:          parseInt(form.stars) || 3,
        languages:      langs.map(l => l.code.toUpperCase()).filter(Boolean),
        vertical:       form.vertical || 'hotel',
        country:        form.country || 'IT',
        ...(existingBudget > 0 ? { total_monthly_budget_eur: existingBudget } : {}),
      })
    },
    onSuccess: (data) => {
      setStrategyResult(data)
      setStrategyPanelOpen(true)
      setSelectedTypes(new Set(data.recommended_types.map((t: string) => backendToFrontend[t] || t)))
      setField('total_monthly_eur', String(data.suggested_total_monthly_eur))
      const newBudget: Record<string, Record<string, string>> = {}
      for (const [feKey, byLang] of Object.entries(data.daily_by_type_lang)) {
        newBudget[feKey] = Object.fromEntries(
          Object.entries(byLang as Record<string, number>).map(([lang, val]) => [lang, String(val)])
        )
      }
      setBudgetByTypeLang(newBudget)
      if (data.api_call_log) appendApiLog(projectId, data.api_call_log)
      // Save full strategy result to budget log for the Budget Log tab
      const key = `budget_strategy_log_${projectId}`
      const existing = (() => { try { return JSON.parse(localStorage.getItem(key) || '[]') } catch { return [] } })()
      existing.unshift({
        ts: new Date().toISOString(),
        overall_strategy: data.overall_strategy || '',
        suggested_total_monthly_eur: data.suggested_total_monthly_eur,
        min_budget_warning: data.min_budget_warning ?? null,
        recommended_types: data.recommended_types,
        budget_split: data.budget_split,
        daily_by_type_lang: data.daily_by_type_lang,
        rationale: data.rationale || {},
        ai_raw_response: data.ai_raw_response ?? null,
        ai_prompt_used: data.ai_prompt_used ?? null,
        reasoning_steps: data.reasoning_steps ?? [],
      })
      localStorage.setItem(key, JSON.stringify(existing.slice(0, 10)))
    },
    onError: (e: Error) => setErrors([`Strategia budget: ${e.message}`]),
  })

  return {
    strategyResult,
    setStrategyResult,
    strategyPanelOpen,
    setStrategyPanelOpen,
    budgetStrategyMutation,
    backendToFrontend,
  }
}
