import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { projectsApi, autofillApi, EnrichedAutofillResult } from '../api/projects'
import { clientsApi, type Hotel } from '../api/clients'
import { T } from '../styles/theme'

import {
  FormState, LangState, SitelinkState, RemarketingListState, TypeObjective,
  LANG_IDS, STEPS, CAMPAIGN_TYPES, DEFAULT_FORM, DEFAULT_LANG,
  VERTICAL_DEFAULT_STARS,
} from './brief/types'
import {
  toLines, getUserEmail, buildBrief,
  briefToForm, briefToSelectedTypes, briefToBudgetByTypeLang, briefToLangs,
  briefToRemarketingLists, briefToObjectivesByType,
} from './brief/utils'
import { css } from './brief/styles'

import { useAutofillBinding }  from './brief/hooks/useAutofillBinding'
import { useKeywordSuggest }   from './brief/hooks/useKeywordSuggest'
import { useSitelinkSuggest }  from './brief/hooks/useSitelinkSuggest'
import { useBudgetStrategy }   from './brief/hooks/useBudgetStrategy'
import { useCopySuggest }      from './brief/hooks/useCopySuggest'

import { Step0InfoBase }  from './brief/steps/Step0InfoBase'
import { Step1Obiettivi } from './brief/steps/Step1Obiettivi'
import { Step2Lingue }    from './brief/steps/Step2Lingue'
import { Step3Hotel }     from './brief/steps/Step3Hotel'
import { Step4Anteprima } from './brief/steps/Step4Anteprima'
import { Step5Revisione } from './brief/steps/Step5Revisione'
import { LoadingOverlay } from './LoadingOverlay'

interface BriefFormProps {
  projectId: string
  project?: { preset?: string; vertical?: string; name?: string; client_slug?: string; client_id?: string | null; hotel_id?: string | null } | null
  existingBrief?: Record<string, unknown> | null
  onSaved: () => void
  pendingAutofill?: EnrichedAutofillResult | null
  onJobStarted?: (jobId: string) => void
}

export default function BriefForm({ projectId, project, existingBrief, onSaved, pendingAutofill, onJobStarted }: BriefFormProps) {
  const qc = useQueryClient()

  // ── Client / Hotel link ────────────────────────────────────────────────────
  const [linkedClientId, setLinkedClientId] = useState<string>(project?.client_id ?? '')
  const [linkedHotelId,  setLinkedHotelId]  = useState<string>(project?.hotel_id ?? '')

  const { data: clientsList = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: clientsApi.list,
  })

  // Fetch full client with hotels when client is selected
  const { data: fullClient } = useQuery({
    queryKey: ['client', linkedClientId],
    queryFn: () => clientsApi.get(linkedClientId),
    enabled: !!linkedClientId,
  })

  const hotelsForClientFull: Hotel[] = fullClient?.hotels ?? []

  const linkMutation = useMutation({
    mutationFn: ({ cid, hid }: { cid: string | null; hid: string | null }) =>
      projectsApi.link(projectId, cid, hid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })

  const handleSelectClient = (clientId: string) => {
    setLinkedClientId(clientId)
    setLinkedHotelId('')
    linkMutation.mutate({ cid: clientId || null, hid: null })
  }

  const handleSelectHotel = (hotelId: string) => {
    setLinkedHotelId(hotelId)
    linkMutation.mutate({ cid: linkedClientId || null, hid: hotelId || null })
  }

  const prefillFromHotel = (hotel: Hotel) => {
    const domain = hotel.website_url
      ? hotel.website_url.replace(/^https?:\/\//, '').replace(/\/$/, '')
      : ''
    const seasons = hotel.seasonality ?? []
    const avgOf = (key: 'avg_occupancy_pct' | 'direct_booking_pct') => {
      const vals = seasons.map(s => s[key]).filter((v): v is number => v != null)
      if (!vals.length) return null
      return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)
    }
    const derivedOccupancy = avgOf('avg_occupancy_pct')
    const derivedDirectPct = avgOf('direct_booking_pct')

    const allChannels = Array.from(
      new Set(seasons.flatMap(s => s.booking_channels ?? []).filter(Boolean))
    )

    const MONTH_SHORT = ['gen','feb','mar','apr','mag','giu','lug','ago','set','ott','nov','dic']
    const fmtDate = (mm_dd: string) => {
      const [m] = mm_dd.split('-')
      return MONTH_SHORT[parseInt(m, 10) - 1] ?? mm_dd
    }
    const seasonalityLines = seasons.map(s => {
      const parts: string[] = []
      if (s.date_from && s.date_to) parts.push(`${fmtDate(s.date_from)}-${fmtDate(s.date_to)}`)
      if (s.avg_occupancy_pct != null) parts.push(`occ. ${Math.round(s.avg_occupancy_pct)}%`)
      if (s.direct_booking_pct != null) parts.push(`dirette ${Math.round(s.direct_booking_pct)}%`)
      if (s.booking_channels?.length) parts.push(`canali: ${s.booking_channels.join(', ')}`)
      return `${s.name || 'Periodo'}: ${parts.join(', ')}`
    })

    setForm(prev => ({
      ...prev,
      brand_name:     prev.brand_name     || fullClient?.name || hotel.name,
      brand_slug:     prev.brand_slug     || hotel.name.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-'),
      domain:         prev.domain         || domain,
      country:        prev.country        || hotel.country_code || '',
      hotel_category: hotel.category      || prev.hotel_category,
      vertical:       hotel.category      || prev.vertical,
      stars:          hotel.stars != null ? String(hotel.stars) : prev.stars,
      rooms:          hotel.rooms != null ? String(hotel.rooms) : prev.rooms,
      city:           hotel.city          || prev.city,
      address:        prev.address        || [hotel.address, hotel.city, hotel.country].filter(Boolean).join(', '),
      booking_engine_url: prev.booking_engine_url || hotel.booking_engine || '',
      adr:            hotel.adr != null   ? String(hotel.adr)          : prev.adr,
      occupancy_rate: derivedOccupancy != null ? String(derivedOccupancy) : prev.occupancy_rate,
      direct_pct:     derivedDirectPct != null  ? String(derivedDirectPct)  : prev.direct_pct,
      booking_channels:    allChannels.length      ? allChannels.join(', ')       : prev.booking_channels,
      seasonality_summary: seasonalityLines.length ? seasonalityLines.join('\n')  : prev.seasonality_summary,
    }))
    if (!autofillUrl && hotel.website_url) setAutofillUrl(hotel.website_url)
  }

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
  const [errors, setErrors]           = useState<string[]>([])
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveHadWarnings, setSaveHadWarnings] = useState(false)
  const [previewLangIdx, setPreviewLangIdx]   = useState(0)
  const [autofillUrl, setAutofillUrl]         = useState<string>(() => {
    const domain = String((existingBrief as Record<string, unknown> | null)?.domain ?? '')
    return domain ? `https://${domain}` : ''
  })
  const [autofillLangs, setAutofillLangs]     = useState<string[]>(['IT', 'EN'])
  const [autofillSuccess, setAutofillSuccess] = useState(false)
  const [autofillManual, setAutofillManual]   = useState(false)
  const [autofillContent, setAutofillContent] = useState('')

  // helpers that hooks depend on
  const setField = (key: keyof FormState, val: string) =>
    setForm(prev => ({ ...prev, [key]: val }))

  // ── Hooks ──────────────────────────────────────────────────────────────────
  useAutofillBinding({ pendingAutofill, setForm, setLangs, setAutofillSuccess })

  const {
    strategyResult, setStrategyResult,
    strategyPanelOpen, setStrategyPanelOpen,
    budgetStrategyMutation, backendToFrontend,
  } = useBudgetStrategy({ form, langs, projectId, setField, setSelectedTypes, setBudgetByTypeLang, setErrors })

  const { kwSuggestMutation, kwSuggestingLang, setKwSuggestingLang } =
    useKeywordSuggest({ form, setLangs, setErrors, projectId })

  const { slSuggestMutation, slSuggestingLang, setSlSuggestingLang } =
    useSitelinkSuggest({ form, setLangs, setErrors, projectId })

  const { triggerCopy, isGenerating: copySuggestIsGenerating, hasError: copySuggestHasError } =
    useCopySuggest({ form, setLangs, setErrors, projectId })

  // ── Budget recalculation (uses strategyResult from hook) ───────────────────
  const frontendToBackend: Record<string, string> = {
    brand: 'search_brand', acquisition: 'search_acquisition',
    pmax: 'performance_max', retargeting: 'retargeting', demand_gen: 'demand_gen',
  }
  const aiSuggestedKeys = strategyResult
    ? new Set(strategyResult.recommended_types.map(t => backendToFrontend[t] || t))
    : null
  const canRecalculate = aiSuggestedKeys !== null && [...aiSuggestedKeys].some(k => !selectedTypes.has(k))

  const handleRecalculateBudget = () => {
    const total = parseFloat(form.total_monthly_eur) || (strategyResult?.suggested_total_monthly_eur ?? 0)
    if (!total || !strategyResult) return
    let totalRatio = 0
    const ratios: Record<string, number> = {}
    for (const ct of CAMPAIGN_TYPES) {
      if (!selectedTypes.has(ct.key)) continue
      const bk = frontendToBackend[ct.key] || ct.key
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

  // ── Other handlers ─────────────────────────────────────────────────────────
  const toggleAutofillLang = (code: string) =>
    setAutofillLangs(prev => prev.includes(code) ? prev.filter(l => l !== code) : [...prev, code])

  const startJobMutation = useMutation({
    mutationFn: () => autofillApi.startJob(
      autofillUrl.trim(), autofillLangs, projectId,
      autofillManual && autofillContent.trim() ? autofillContent.trim() : undefined,
    ),
    onSuccess: (data) => { if (onJobStarted) onJobStarted(data.job_id) },
    onError: (e: Error) => {
      setErrors([`Auto-fill: ${e.message}`])
      if (!autofillManual) setAutofillManual(true)
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

  const redistributeBudget = (nextTypes: Set<string>) => {
    const totalMonthly = parseFloat(form.total_monthly_eur) || 0
    if (!totalMonthly || nextTypes.size === 0) return
    const weights: Record<string, number> = {
      brand: 0.12, acquisition: 0.28, pmax: 0.38, retargeting: 0.10, demand_gen: 0.12,
    }
    const active = CAMPAIGN_TYPES.filter(ct => nextTypes.has(ct.key))
    const rawW = Object.fromEntries(active.map(ct => [ct.key, weights[ct.key] ?? 0.15]))
    const totalW = Object.values(rawW).reduce((s, v) => s + v, 0)
    const activeLangs = langs.map(l => l.code.toUpperCase()).filter(Boolean)
    const nLangs = Math.max(activeLangs.length, 1)
    setBudgetByTypeLang(prev => {
      const next = { ...prev }
      for (const ct of active) {
        const dailyPerLang = (totalMonthly * (rawW[ct.key] / totalW)) / nLangs / 30.44
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
    if (!form.project_name)   errs.push('Nome progetto obbligatorio')
    if (!form.brand_name)     errs.push('Nome brand obbligatorio')
    if (!form.brand_slug)     errs.push('Slug brand obbligatorio')
    if (!form.domain)         errs.push('Dominio obbligatorio')
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
      if (!l.code)         errs.push(`Lingua ${n}: codice obbligatorio`)
      if (!l.landing_page) errs.push(`Lingua ${n}: landing page obbligatoria`)
      if (!l.brand_terms)  errs.push(`Lingua ${n}: brand terms obbligatori`)
      const hl = toLines(l.headlines)
      if (hl.length < 3) errs.push(`Lingua ${n}: almeno 3 headline (trovate ${hl.length})`)
      hl.forEach(h => { if (h.length > 30) errs.push(`Lingua ${n}: headline troppo lunga (max 30): "${h.slice(0, 20)}..."`) })
      const dl = toLines(l.descriptions)
      if (dl.length < 2) errs.push(`Lingua ${n}: almeno 2 descrizioni (trovate ${dl.length})`)
      dl.forEach(d => { if (d.length > 90) errs.push(`Lingua ${n}: descrizione troppo lunga (max 90): "${d.slice(0, 30)}..."`) })
    })
    if (!form.address)           errs.push('Indirizzo hotel obbligatorio')
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
      <LoadingOverlay
        visible={budgetStrategyMutation.isPending}
        message="L'AI sta costruendo la tua strategia."
        submessage="Analisi del profilo hotel, obiettivi e distribuzione ottimale del budget"
      />
      <LoadingOverlay
        visible={saveMutation.isPending}
        message="Brief salvato. Tutto a posto."
        submessage="Validazione e salvataggio della configurazione in corso"
      />
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

      {/* ── Client / Hotel selector (step 0 only) ── */}
      {step === 0 && (
        <div style={{
          background: '#f0f4ff',
          border: `1.5px solid ${T.blue}`,
          borderRadius: T.radiusLg,
          padding: '16px 20px',
          marginBottom: 24,
        }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: T.blue, marginBottom: 12 }}>
            <i className="fa-solid fa-building" /> Collega cliente e hotel
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, alignItems: 'flex-end' }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: T.textGray, display: 'block', marginBottom: 4, textTransform: 'uppercase' as const, letterSpacing: 0.5 }}>
                Cliente
              </label>
              <select
                style={{ width: '100%', padding: '8px 11px', borderRadius: T.radiusSm, border: `1.5px solid ${T.borderLight}`, fontSize: 13, color: T.text }}
                value={linkedClientId}
                onChange={e => handleSelectClient(e.target.value)}
              >
                <option value="">— Nessun cliente —</option>
                {clientsList.map(c => (
                  <option key={c.id} value={c.id}>{c.name}{c.agency ? ` (${c.agency})` : ''}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: T.textGray, display: 'block', marginBottom: 4, textTransform: 'uppercase' as const, letterSpacing: 0.5 }}>
                Hotel
              </label>
              <select
                style={{ width: '100%', padding: '8px 11px', borderRadius: T.radiusSm, border: `1.5px solid ${T.borderLight}`, fontSize: 13, color: T.text }}
                value={linkedHotelId}
                onChange={e => handleSelectHotel(e.target.value)}
                disabled={!linkedClientId}
              >
                <option value="">— Seleziona hotel —</option>
                {hotelsForClientFull.map(h => (
                  <option key={h.id} value={h.id}>{h.name}{h.stars ? ` ${'★'.repeat(h.stars)}` : ''}</option>
                ))}
              </select>
            </div>
            {linkedHotelId && (() => {
              const hotel = hotelsForClientFull.find(h => h.id === linkedHotelId)
              return hotel ? (
                <button
                  style={{ padding: '8px 14px', background: T.blue, color: '#fff', border: 'none', borderRadius: T.radiusSm, cursor: 'pointer', fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap' as const }}
                  onClick={() => prefillFromHotel(hotel)}
                  title="Pre-compila i campi del brief con i dati salvati dell'hotel"
                >
                  <i className="fa-solid fa-wand-sparkles" /> Pre-compila
                </button>
              ) : null
            })()}
          </div>
          {linkedHotelId && (() => {
            const hotel = hotelsForClientFull.find(h => h.id === linkedHotelId)
            return hotel?.has_scraped_data ? (
              <div style={{ marginTop: 10, fontSize: 12, color: T.success }}>
                <i className="fa-solid fa-circle-check" /> Dati scansionati disponibili per questo hotel
                {hotel.scraped_at && <span style={{ color: T.textGray }}> · {new Date(hotel.scraped_at).toLocaleDateString('it-IT')}</span>}
              </div>
            ) : null
          })()}
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
          hasExistingBrief={!!existingBrief}
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
          copySuggestTrigger={triggerCopy} copySuggestIsGenerating={copySuggestIsGenerating} copySuggestHasError={copySuggestHasError}
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
