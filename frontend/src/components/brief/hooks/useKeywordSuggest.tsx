// ── useKeywordSuggest ─────────────────────────────────────────────────────────
// Keyword suggestion mutation for the BriefForm wizard.

import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { autofillApi } from '../../../api/projects'
import { FormState, LangState } from '../types'
import { toLines, appendApiLog } from '../utils'

interface UseKeywordSuggestParams {
  form: FormState
  setLangs: React.Dispatch<React.SetStateAction<LangState[]>>
  setErrors: (errs: string[]) => void
  projectId: string
}

export function useKeywordSuggest({ form, setLangs, setErrors, projectId }: UseKeywordSuggestParams) {
  const [kwSuggestingLang, setKwSuggestingLang] = useState<number | null>(null)

  const kwSuggestMutation = useMutation({
    mutationFn: ({ lang }: { langIdx: number; lang: LangState }) =>
      autofillApi.suggestKeywords({
        brand_name:     form.brand_name,
        hotel_category: form.hotel_category,
        stars:          parseInt(form.stars) || 3,
        language_code:  lang.code,
        domain:         form.domain || undefined,
        services:       toLines(form.services),
        strengths:      toLines(form.strengths),
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

  return { kwSuggestMutation, kwSuggestingLang, setKwSuggestingLang }
}
