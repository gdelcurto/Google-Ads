import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, autofillApi, EnrichedAutofillResult } from '../api/projects'
import { T } from '../styles/theme'

import {
  FormState, LangState, SitelinkState, RemarketingListState, TypeObjective,
  LANG_IDS, STEPS, CAMPAIGN_TYPES, DEFAULT_FORM, DEFAULT_LANG,
  VERTICAL_DEFAULT_STARS,
} from './brief/types'
import {
  toLines, getUserEmail, buildBrief,
  briefToForm, briefToSelectedTypes, briefToBudgetByTypeLang, briefToLangs,
  briefToRemarketingLists, briefToObjectivesByType, appendApiLog,
} from './brief/utils'
import { css } from './brief/styles'
import { StrategyResult } from './brief/hooks/useBudgetStrategy'

import { Step0InfoBase } from './brief/steps/Step0InfoBase'
import { Step1Obiettivi } from './brief/steps/Step1Obiettivi'
import { Step2Lingue } from './brief/steps/Step2Lingue'
import { Step3Hotel } from './brief/steps/Step3Hotel'
import { Step4Anteprima } from './brief/steps/Step4Anteprima'
import { Step5Revisione } from './brief/steps/Step5Revisione'

interface BriefFormProps {
  projectId: string
  /** Project metadata used to seed form defaults when no brief exists yet. */
  project?: { preset?: string; vertical?: string; name?: string; client_slug?: string } | null
  existingBrief?: Record<string, unknown> | null
  onSaved: () => void
  /** Enriched autofill result from a completed background job — applied automatically on mount/change. */
  pendingAutofill?: EnrichedAutofillResult | null
  /** Called when a background job is successfully started, with the job ID. */
  onJobStarted?: (jobId: string) => void
}

export default function BriefForm({ projectId, project, existingBrief, onSaved, pendingAutofill, onJobStarted }: BriefFormProps) {
  const qc = useQueryClient()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<FormState>(() => {
    if (existingBrief) return briefToForm(existingBrief)
    const base = { ...DEFAULT_FORM, created_by: getUserEmail() }
    if (project) {
      if (project.preset)      base.preset        = project.preset
      if (project.vertical) {
        base.vertical       = project.vertical
        base.hotel_category = project.vertical
        base.stars          = VERTICAL_DEFAULT_STARS[project.vertical] ?? '4'
      }
      if (project.name)        base.project_name  = project.name
      if (project.client_slug) base.brand_slug    = project.client_slug
    }
    return base
  })
  const [langs, setLangs] = useState<LangState[]>(() =>
    existingBrief ? briefToLangs(existingBrief) : [{ ...DEFAULT_LANG }]
  )
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(() =>
    existingBrief ? briefToSelectedTypes(existingBrief) : new Set(['brand', 'acquisition', 'pmax'])
  )
  const [budgetByTypeLang, setBudgetByTypeLang] = useState<Record<string, Record<string, string>>>(() =>
    existingBrief ? briefToBudgetByTypeLang(existingBrief) : {}
  )
  const [objectivesByType, setObjectivesByType] = useState<Record<string, TypeObjective>>(() =>
    existingBrief ? briefToObjectivesByType(existingBrief) : {}
  )
  const [remarketingLists, setRemarketingLists] = useState<RemarketingListState[]>(() =>
    existingBrief ? briefToRemarketingLists(existingBrief) : []
  )
  const [errors, setErrors] = useState<string[]>([])
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveHadWarnings, setSaveHadWarnings] = useState(false)
  const [kwSuggestingLang, setKwSuggestingLang] = useState<number | null>(null)
  const [slSuggestingLang, setSlSuggestingLang] = useState<number | null>(null)
  const [previewLangIdx, setPreviewLangIdx] = useState(0)

  // ── Budget Strategy state ──────────────────────────────────────────────────
  const [strategyResult, setStrategyResult] = useState<StrategyResult | null>(null)
  const [strategyPanelOpen, setStrategyPanelOpen] = useState(false)

  // ── Auto-fill state ────────────────────────────────────────────────────────
  const [autofillUrl, setAutofillUrl] = useState('')
  const [autofillLangs, setAutofillLangs] = useState<string[]>(['IT', 'EN'])
  const [autofillSuccess, setAutofillSuccess] = useState(false)
  const [autofillManual, setAutofillManual] = useState(false)
  const [autofillContent, setAutofillContent] = useState('')

  // Apply an enriched autofill result from a completed background job
  useEffect(() => {
    if (!pendingAutofill) return
    setForm(prev => ({
      ...prev,
      brand_name: pendingAutofill.brand_name || prev.brand_name,
      brand_slug: pendingAutofill.brand_slug || prev.brand_slug,
      domain: pendingAutofill.domain || prev.domain,
      country: pendingAutofill.country || prev.country,
      hotel_category: pendingAutofill.hotel_category || prev.hotel_category,
      stars: pendingAutofill.stars != null ? String(pendingAutofill.stars) : prev.stars,
      rooms: pendingAutofill.rooms != null ? String(pendingAutofill.rooms) : prev.rooms,
      address: pendingAutofill.address || prev.address,
      services: (pendingAutofill.services || []).join('\n'),
      strengths: (pendingAutofill.strengths || []).join('\n'),
      booking_engine_url: pendingAutofill.booking_engine_url || prev.booking_engine_url,
      target_countries: (pendingAutofill.target_countries || []).join('\n') || prev.target_countries,
      project_name: prev.project_name || `${pendingAutofill.brand_name} — Google Ads`,
    }))
    if (pendingAutofill.languages && pendingAutofill.languages.length > 0) {
      setLangs(pendingAutofill.languages.map(l => ({
        code: l.code,
        name: l.name,
        google_language_id: String(l.google_language_id || ''),
        landing_page: l.landing_page || '',
        brand_terms: (l.brand_terms || []).join('\n'),
        usp_main: l.usp_main || '',
        headlines: (l.headlines || []).join('\n'),
        descriptions: (l.descriptions || []).join('\n'),
        callouts: (l.callouts || []).join('\n'),
        sitelinks: l.sitelinks || [],
        kw_themes: '',
        kw_negative: '',
        brand_headlines: (l.brand_headlines || []).join('\n'),
        brand_descriptions: (l.brand_descriptions || []).join('\n'),
        acquisition_headlines: (l.acquisition_headlines || []).join('\n'),
        acquisition_descriptions: (l.acquisition_descriptions || []).join('\n'),
        retargeting_headlines: (l.retargeting_headlines || []).join('\n'),
        retargeting_descriptions: (l.retargeting_descriptions || []).join('\n'),
      })))
    }
    setAutofillSuccess(true)
  }, [pendingAutofill])

  // Start a background auto-fill job
  const startJobMutation = useMutation({
    mutationFn: () => autofillApi.startJob(
      autofillUrl.trim(),
      autofillLangs,
      projectId,
      autofillManual && autofillContent.trim() ? autofillContent.trim() : undefined,
    ),
    onSuccess: (data) => {
      if (onJobStarted) onJobStarted(data.job_id)
    },
    onError: (e: Error) => {
      setErrors([`Auto-fill: ${e.message}`])
      if (!autofillManual) setAutofillManual(true)
    },
  })

  const budgetStrategyMutation = useMutation({
    mutationFn: () => {
      if (!form.brand_name) throw new Error('Inserisci il nome del brand (Step 0) prima di richiedere la strategia.')
      const existingBudget = parseFloat(form.total_monthly_eur) || 0
      return autofillApi.suggestBudgetStrategy({
        brand_name: form.brand_name,
        hotel_category: form.hotel_category || 'city_hotel',
        stars: parseInt(form.stars) || 3,
        languages: langs.map(l => l.code.toUpperCase()).filter(Boolean),
        vertical: form.vertical || 'hotel',
        country: form.country || 'IT',
        ...(existingBudget > 0 ? { total_monthly_budget_eur: existingBudget } : {}),
      })
    },
    onSuccess: (data) => {
      setStrategyResult(data)
      setStrategyPanelOpen(true)
      const backendToFrontend: Record<string, string> = {
        search_brand: 'brand', search_acquisition: 'acquisition',
        performance_max: 'pmax', retargeting: 'retargeting', demand_gen: 'demand_gen',
      }
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
    },
    onError: (e: Error) => setErrors([`Strategia budget: ${e.message}`]),
  })

  // Recalculate budget using AI ratios after user deselects campaign types
  const frontendToBackendMap: Record<string, string> = {
    brand: 'search_brand', acquisition: 'search_acquisition',
    pmax: 'performance_max', retargeting: 'retargeting', demand_gen: 'demand_gen',
  }
  const aiSuggestedKeys = strategyResult
    ? new Set(strategyResult.recommended_types.map(t => ({
        search_brand: 'brand', search_acquisition: 'acquisition',
        performance_max: 'pmax', retargeting: 'retargeting', demand_gen: 'demand_gen',
      }[t] || t)))
    : null
  const canRecalculate = aiSuggestedKeys !== null && [...aiSuggestedKeys].some(k => !selectedTypes.has(k))

  const handleRecalculateBudget = () => {
    const total = parseFloat(form.total_monthly_eur) || (strategyResult?.suggested_total_monthly_eur ?? 0)
    if (!total || !strategyResult) return
    let totalRatio = 0
    const ratios: Record<string, number> = {}
    for (const ct of CAMPAIGN_TYPES) {
      if (!selectedTypes.has(ct.key)) continue
      const bk = frontendToBackendMap[ct.key] || ct.key
      const r = strategyResult.budget_split[bk] ?? 0
      ratios[ct.key] = r
      totalRatio += r
    }
    const activeLangs = langs.map(l => l.code.toUpperCase()).filter(Boolean)
    const nLangs = Math.max(activeLangs.length, 1)
    const newBudget: Record<string, Record<string, string>> = {}
    for (const ct of CAMPAIGN_TYPES) {
      if (!selectedTypes.has(ct.key)) continue
      const ratio = totalRatio > 0 ? (ratios[ct.key] / totalRatio) : (1 / selectedTypes.size)
      const dailyPerLang = (total * ratio) / nLangs / 30.44
      newBudget[ct.key] = Object.fromEntries(
        activeLangs.map(c => [c, String(Math.round(dailyPerLang * 100) / 100)])
      )
    }
    setBudgetByTypeLang(prev => ({ ...prev, ...newBudget }))
  }

  const toggleAutofillLang = (code: string) =>
    setAutofillLangs(prev => prev.includes(code) ? prev.filter(l => l !== code) : [...prev, code])

  const kwSuggestMutation = useMutation({
    mutationFn: ({ lang }: { langIdx: number; lang: LangState }) =>
      autofillApi.suggestKeywords({
        brand_name: form.brand_name,
        hotel_category: form.hotel_category,
        stars: parseInt(form.stars) || 3,
        language_code: lang.code,
        domain: form.domain || undefined,
        services: toLines(form.services),
        strengths: toLines(form.strengths),
      }),
    onSuccess: (data, { langIdx }) => {
      setLangs(prev => prev.map((l, i) => i === langIdx
        ? { ...l, kw_themes: data.kw_themes_text, kw_negative: data.kw_negative_text }
        : l
      ))
      setKwSuggestingLang(null)
      if (data.api_call_log) appendApiLog(projectId, data.api_call_log)
    },
    onError: (e: Error) => {
      setErrors([`Suggerimento keyword: ${e.message}`])
      setKwSuggestingLang(null)
    },
  })

  const slSuggestMutation = useMutation({
    mutationFn: ({ lang }: { langIdx: number; lang: LangState }) =>
      autofillApi.suggestSitelinks({
        brand_name: form.brand_name,
        hotel_category: form.hotel_category,
        stars: parseInt(form.stars) || 3,
        language_code: lang.code,
        landing_page: lang.landing_page || `https://${form.domain}`,
        domain: form.domain || undefined,
        services: toLines(form.services),
        strengths: toLines(form.strengths),
        booking_engine_url: form.booking_engine_url || undefined,
      }),
    onSuccess: (data, { langIdx }) => {
      setLangs(prev => prev.map((l, i) => i === langIdx ? { ...l, sitelinks: data.sitelinks } : l))
      setSlSuggestingLang(null)
      if (data.api_call_log) appendApiLog(projectId, data.api_call_log)
    },
    onError: (e: Error) => {
      setErrors([`Suggerimento sitelink: ${e.message}`])
      setSlSuggestingLang(null)
    },
  })

  const saveMutation = useMutation({
    mutationFn: (brief: Record<string, unknown>) => projectsApi.uploadBrief(projectId, brief),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['brief', projectId] })
      qc.invalidateQueries({ queryKey: ['project', projectId] })
      setSaveSuccess(true)
      if (result.validation.errors.length > 0) {
        setErrors(result.validation.errors.map((e: { message: string }) => e.message))
        setSaveHadWarnings(true)
      }
      setTimeout(onSaved, 1800)
    },
    onError: (e: Error) => setErrors([e.message]),
  })

  const setField = (key: keyof FormState, val: string) =>
    setForm(prev => ({ ...prev, [key]: val }))

  const redistributeBudget = (nextTypes: Set<string>) => {
    const totalMonthly = parseFloat(form.total_monthly_eur) || 0
    if (!totalMonthly || nextTypes.size === 0) return
    const backendWeights: Record<string, number> = {
      brand: 0.12, acquisition: 0.28, pmax: 0.38, retargeting: 0.10, demand_gen: 0.12,
    }
    const active = CAMPAIGN_TYPES.filter(ct => nextTypes.has(ct.key))
    const rawWeights = Object.fromEntries(active.map(ct => [ct.key, backendWeights[ct.key] ?? 0.15]))
    const totalW = Object.values(rawWeights).reduce((s, v) => s + v, 0)
    const activeLangs = langs.map(l => l.code.toUpperCase()).filter(Boolean)
    const nLangs = Math.max(activeLangs.length, 1)
    setBudgetByTypeLang(prev => {
      const next = { ...prev }
      for (const ct of active) {
        const monthlyForType = totalMonthly * (rawWeights[ct.key] / totalW)
        const dailyPerLang = monthlyForType / nLangs / 30.44
        next[ct.key] = Object.fromEntries(activeLangs.map(c => [c, String(Math.round(dailyPerLang * 100) / 100)]))
      }
      return next
    })
  }

  const setLangField = (i: number, key: keyof LangState, val: string) =>
    setLangs(prev => prev.map((l, idx) => idx === i ? { ...l, [key]: val } : l))

  const handleLangCode = (i: number, code: string) => {
    const upper = code.toUpperCase()
    const id = LANG_IDS[upper] ? String(LANG_IDS[upper]) : langs[i].google_language_id
    setLangs(prev => prev.map((l, idx) => idx === i ? { ...l, code: upper, google_language_id: id } : l))
  }

  const addLang = () =>
    setLangs(prev => [...prev, { ...DEFAULT_LANG, code: '', name: '', google_language_id: '' }])

  const addSitelink = (langIdx: number) =>
    setLangs(prev => prev.map((l, i) => i === langIdx
      ? { ...l, sitelinks: [...l.sitelinks, { text: '', description_1: '', description_2: '', final_url: '' }] }
      : l
    ))

  const removeSitelink = (langIdx: number, slIdx: number) =>
    setLangs(prev => prev.map((l, i) => i === langIdx
      ? { ...l, sitelinks: l.sitelinks.filter((_, j) => j !== slIdx) }
      : l
    ))

  const setSitelinkField = (langIdx: number, slIdx: number, key: keyof SitelinkState, val: string) =>
    setLangs(prev => prev.map((l, i) => i === langIdx
      ? { ...l, sitelinks: l.sitelinks.map((sl, j) => j === slIdx ? { ...sl, [key]: val } : sl) }
      : l
    ))

  const addRemarketingList = () =>
    setRemarketingLists(prev => [...prev, { name: '', type: 'website_visitors', lookback_days: '30', source: '' }])

  const removeRemarketingList = (idx: number) =>
    setRemarketingLists(prev => prev.filter((_, i) => i !== idx))

  const setRemarketingListField = (idx: number, key: keyof RemarketingListState, val: string) =>
    setRemarketingLists(prev => prev.map((rl, i) => i === idx ? { ...rl, [key]: val } : rl))

  const removeLang = (i: number) => setLangs(prev => prev.filter((_, idx) => idx !== i))

  const validate = (): boolean => {
    const errs: string[] = []
    if (!form.project_name) errs.push('Nome progetto obbligatorio')
    if (!form.brand_name) errs.push('Nome brand obbligatorio')
    if (!form.brand_slug) errs.push('Slug brand obbligatorio')
    if (!form.domain) errs.push('Dominio obbligatorio')
    if (selectedTypes.size === 0) {
      errs.push('Seleziona almeno un tipo di campagna')
    } else {
      for (const ct of CAMPAIGN_TYPES) {
        if (!selectedTypes.has(ct.key)) continue
        const hasAny = langs.some(l => {
          const v = budgetByTypeLang[ct.key]?.[l.code.toUpperCase()]
          return v && parseFloat(v) > 0
        })
        if (!hasAny) errs.push(`Budget obbligatorio per "${ct.label}" (almeno una lingua)`)
      }
    }
    if (langs.length === 0) errs.push('Almeno una lingua richiesta')
    langs.forEach((l, i) => {
      const n = i + 1
      if (!l.code) errs.push(`Lingua ${n}: codice obbligatorio`)
      if (!l.landing_page) errs.push(`Lingua ${n}: landing page obbligatoria`)
      if (!l.brand_terms) errs.push(`Lingua ${n}: brand terms obbligatori`)
      const hl = toLines(l.headlines)
      if (hl.length < 3) errs.push(`Lingua ${n}: almeno 3 headline (trovate ${hl.length})`)
      hl.forEach(h => { if (h.length > 30) errs.push(`Lingua ${n}: headline troppo lunga (max 30): "${h.slice(0, 20)}..."`) })
      const dl = toLines(l.descriptions)
      if (dl.length < 2) errs.push(`Lingua ${n}: almeno 2 descrizioni (trovate ${dl.length})`)
      dl.forEach(d => { if (d.length > 90) errs.push(`Lingua ${n}: descrizione troppo lunga (max 90): "${d.slice(0, 30)}..."`) })
    })
    if (!form.address) errs.push('Indirizzo hotel obbligatorio')
    if (!form.booking_engine_url) errs.push('URL booking engine obbligatorio')
    setErrors(errs)
    if (errs.length > 0) setStep(0)
    return errs.length === 0
  }

  const handleSubmit = () => {
    if (validate()) {
      saveMutation.mutate(buildBrief(form, langs, selectedTypes, budgetByTypeLang, remarketingLists, objectivesByType))
    }
  }

  const goNext = () => { setStep(prev => prev + 1); setErrors([]) }
  const goPrev = () => { setStep(prev => prev - 1); setErrors([]) }

  return (
    <div>
      {/* ── Stepper ── */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 32 }}>
        {STEPS.map((label, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div
                style={{
                  ...css.stepBubble,
                  background: i < step ? T.success : i === step ? T.primary : T.borderLight,
                  color: i <= step ? '#fff' : T.textGray,
                  cursor: i < step ? 'pointer' : 'default',
                }}
                onClick={() => { if (i < step) { setStep(i); setErrors([]) } }}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <div style={{ ...css.stepLabel, color: i === step ? T.primary : T.textGray, fontWeight: i === step ? 700 : 400 }}>
                {label}
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ ...css.stepLine, background: i < step ? T.success : T.borderLight }} />
            )}
          </div>
        ))}
      </div>

      {/* ── Messages ── */}
      {saveSuccess && (
        <div style={css.successBox}>
          {saveHadWarnings
            ? 'Brief salvato (con avvertimenti). Reindirizzamento verso overview...'
            : 'Brief salvato con successo! Reindirizzamento...'}
        </div>
      )}
      {errors.length > 0 && !saveSuccess && (
        <div style={css.errBox}>
          <strong>Errori da correggere:</strong>
          <ul style={{ marginLeft: 16, marginTop: 4 }}>
            {errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
          <button
            onClick={() => setErrors([])}
            style={{ marginTop: 6, background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', fontWeight: 700 }}
          >
            <i className="fa-solid fa-xmark"></i> Chiudi
          </button>
        </div>
      )}
      {errors.length > 0 && saveSuccess && (
        <div style={{ ...css.errBox, borderColor: T.yellow, background: '#fffbeb', color: '#92400e' }}>
          <strong>Avvertimenti (brief salvato):</strong>
          <ul style={{ marginLeft: 16, marginTop: 4 }}>
            {errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      {/* ── Steps ── */}
      {step === 0 && (
        <Step0InfoBase
          form={form} setField={setField}
          autofillUrl={autofillUrl} setAutofillUrl={setAutofillUrl}
          autofillLangs={autofillLangs} toggleAutofillLang={toggleAutofillLang}
          autofillManual={autofillManual} setAutofillManual={setAutofillManual}
          autofillContent={autofillContent} setAutofillContent={setAutofillContent}
          autofillSuccess={autofillSuccess}
          startJobMutation={startJobMutation}
          setErrors={setErrors}
        />
      )}
      {step === 1 && (
        <Step1Obiettivi
          form={form} setField={setField} langs={langs}
          selectedTypes={selectedTypes} setSelectedTypes={setSelectedTypes}
          objectivesByType={objectivesByType} setObjectivesByType={setObjectivesByType}
          budgetByTypeLang={budgetByTypeLang} setBudgetByTypeLang={setBudgetByTypeLang}
          strategyResult={strategyResult} setStrategyResult={setStrategyResult}
          strategyPanelOpen={strategyPanelOpen} setStrategyPanelOpen={setStrategyPanelOpen}
          budgetStrategyMutation={budgetStrategyMutation}
          canRecalculate={canRecalculate} handleRecalculateBudget={handleRecalculateBudget}
          redistributeBudget={redistributeBudget}
        />
      )}
      {step === 2 && (
        <Step2Lingue
          brandName={form.brand_name}
          langs={langs} setLangField={setLangField} handleLangCode={handleLangCode}
          addLang={addLang} removeLang={removeLang}
          addSitelink={addSitelink} removeSitelink={removeSitelink} setSitelinkField={setSitelinkField}
          slSuggestMutation={slSuggestMutation} kwSuggestMutation={kwSuggestMutation}
          slSuggestingLang={slSuggestingLang} kwSuggestingLang={kwSuggestingLang}
          setSlSuggestingLang={setSlSuggestingLang} setKwSuggestingLang={setKwSuggestingLang}
          setErrors={setErrors}
        />
      )}
      {step === 3 && (
        <Step3Hotel
          form={form} setField={setField}
          remarketingLists={remarketingLists}
          addRemarketingList={addRemarketingList}
          removeRemarketingList={removeRemarketingList}
          setRemarketingListField={setRemarketingListField}
          selectedTypes={selectedTypes}
        />
      )}
      {step === 4 && (
        <Step4Anteprima
          form={form} langs={langs}
          previewLangIdx={previewLangIdx} setPreviewLangIdx={setPreviewLangIdx}
        />
      )}
      {step === 5 && (
        <Step5Revisione
          form={form} langs={langs} selectedTypes={selectedTypes}
          budgetByTypeLang={budgetByTypeLang} remarketingLists={remarketingLists}
          objectivesByType={objectivesByType}
        />
      )}

      {/* ── Navigation ── */}
      <div style={css.nav}>
        {step > 0 ? (
          <button style={css.btnGhost} onClick={goPrev}>← Indietro</button>
        ) : <div />}

        {step < STEPS.length - 1 ? (
          <button style={css.btn} onClick={goNext}>Avanti →</button>
        ) : (
          <button style={css.btnGreen} onClick={handleSubmit} disabled={saveMutation.isPending || saveSuccess}>
            {saveMutation.isPending ? 'Salvataggio...' : 'Salva Brief'}
          </button>
        )}
      </div>
    </div>
  )
}
