// ── useCopySuggest ─────────────────────────────────────────────────────────────
// RSA copy generation hook — fills headlines and/or descriptions via Claude API.

import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { autofillApi } from '../../../api/projects'
import { FormState, LangState } from '../types'
import { toLines, appendApiLog } from '../utils'

// 'generic' uses acquisition-type copy (non-brand) for the shared RSA pool
export type CopyTarget = 'generic' | 'brand' | 'acquisition' | 'retargeting'

interface UseCopySuggestParams {
  form: FormState
  setLangs: React.Dispatch<React.SetStateAction<LangState[]>>
  setErrors: (errs: string[]) => void
  projectId: string
}

export function useCopySuggest({ form, setLangs, setErrors, projectId }: UseCopySuggestParams) {
  // Key format: "${langIdx}-${target}"
  const [generatingKey, setGeneratingKey] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: ({ lang, target }: { langIdx: number; lang: LangState; target: CopyTarget }) => {
      const apiType = target === 'generic' ? 'acquisition' : target
      return autofillApi.suggestTypeCopy({
        campaign_type:  apiType as 'brand' | 'acquisition' | 'retargeting',
        brand_name:     form.brand_name,
        hotel_category: form.hotel_category,
        stars:          parseInt(form.stars) || 3,
        language_code:  lang.code,
        domain:         form.domain || undefined,
        usp_main:       lang.usp_main || undefined,
        services:       toLines(form.services),
        strengths:      toLines(form.strengths),
      })
    },
    onSuccess: (data, { langIdx, lang, target }) => {
      const descriptions = data.descriptions.join('\n')
      const headlines    = data.headlines.join('\n')

      setLangs(prev => prev.map((l, i) => {
        if (i !== langIdx) return l
        switch (target) {
          case 'generic':
            return {
              ...l,
              descriptions,
              // Fill headlines only if they're also empty
              headlines: l.headlines.trim() === '' ? headlines : l.headlines,
            }
          case 'brand':
            return { ...l, brand_headlines: headlines, brand_descriptions: descriptions }
          case 'acquisition':
            return { ...l, acquisition_headlines: headlines, acquisition_descriptions: descriptions }
          case 'retargeting':
            return { ...l, retargeting_headlines: headlines, retargeting_descriptions: descriptions }
          default:
            return l
        }
      }))

      setGeneratingKey(null)
      if (data.api_call_log) appendApiLog(projectId, data.api_call_log)
    },
    onError: (e: Error) => {
      setErrors([`Generazione copy AI: ${e.message}`])
      setGeneratingKey(null)
    },
  })

  const triggerCopy = (langIdx: number, lang: LangState, target: CopyTarget) => {
    setGeneratingKey(`${langIdx}-${target}`)
    mutation.mutate({ langIdx, lang, target })
  }

  const isGenerating = (langIdx: number, target: CopyTarget) =>
    generatingKey === `${langIdx}-${target}`

  return { triggerCopy, isGenerating }
}
