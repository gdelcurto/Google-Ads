// ── useSitelinkSuggest ────────────────────────────────────────────────────────
// Sitelink suggestion mutation for the BriefForm wizard.

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { autofillApi } from '../../../api/projects'
import { FormState, LangState } from '../types'
import { toLines, appendApiLog } from '../utils'

interface UseSitelinkSuggestParams {
  form: FormState
  setLangs: React.Dispatch<React.SetStateAction<LangState[]>>
  setErrors: (errs: string[]) => void
  projectId: string
}

export function useSitelinkSuggest({ form, setLangs, setErrors, projectId }: UseSitelinkSuggestParams) {
  const [slSuggestingLang, setSlSuggestingLang] = useState<number | null>(null)

  const slSuggestMutation = useMutation({
    mutationFn: ({ lang }: { langIdx: number; lang: LangState }) =>
      autofillApi.suggestSitelinks({
        brand_name:          form.brand_name,
        hotel_category:      form.hotel_category,
        stars:               parseInt(form.stars) || 3,
        language_code:       lang.code,
        landing_page:        lang.landing_page || `https://${form.domain}`,
        domain:              form.domain || undefined,
        services:            toLines(form.services),
        strengths:           toLines(form.strengths),
        booking_engine_url:  form.booking_engine_url || undefined,
      }),
    onSuccess: (data, { langIdx }) => {
      setLangs(prev => prev.map((l, i) => i === langIdx
        ? { ...l, sitelinks: data.sitelinks }
        : l
      ))
      setSlSuggestingLang(null)
      if (data.api_call_log) appendApiLog(projectId, data.api_call_log)
    },
    onError: (e: Error) => {
      setErrors([`Suggerimento sitelink: ${e.message}`])
      setSlSuggestingLang(null)
    },
  })

  return { slSuggestMutation, slSuggestingLang, setSlSuggestingLang }
}
