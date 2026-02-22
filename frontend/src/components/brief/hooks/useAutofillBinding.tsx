// ── useAutofillBinding ────────────────────────────────────────────────────────
// Applies an enriched autofill result from a completed background job to form state.

import React, { useEffect } from 'react'
import { EnrichedAutofillResult } from '../../../api/projects'
import { FormState, LangState } from '../types'

interface UseAutofillBindingParams {
  pendingAutofill: EnrichedAutofillResult | null | undefined
  setForm: React.Dispatch<React.SetStateAction<FormState>>
  setLangs: React.Dispatch<React.SetStateAction<LangState[]>>
  setAutofillSuccess: (v: boolean) => void
}

export function useAutofillBinding({
  pendingAutofill,
  setForm,
  setLangs,
  setAutofillSuccess,
}: UseAutofillBindingParams) {
  useEffect(() => {
    if (!pendingAutofill) return

    setForm(prev => ({
      ...prev,
      brand_name:          pendingAutofill.brand_name || prev.brand_name,
      brand_slug:          pendingAutofill.brand_slug || prev.brand_slug,
      domain:              pendingAutofill.domain || prev.domain,
      country:             pendingAutofill.country || prev.country,
      hotel_category:      pendingAutofill.hotel_category || prev.hotel_category,
      stars:               pendingAutofill.stars != null ? String(pendingAutofill.stars) : prev.stars,
      rooms:               pendingAutofill.rooms != null ? String(pendingAutofill.rooms) : prev.rooms,
      address:             pendingAutofill.address || prev.address,
      services:            (pendingAutofill.services || []).join('\n'),
      strengths:           (pendingAutofill.strengths || []).join('\n'),
      booking_engine_url:  pendingAutofill.booking_engine_url || prev.booking_engine_url,
      target_countries:    (pendingAutofill.target_countries || []).join('\n') || prev.target_countries,
      project_name:        prev.project_name || `${pendingAutofill.brand_name} — Google Ads`,
    }))

    if (pendingAutofill.languages && pendingAutofill.languages.length > 0) {
      setLangs(pendingAutofill.languages.map(l => ({
        code:                     l.code,
        name:                     l.name,
        google_language_id:       String(l.google_language_id || ''),
        landing_page:             l.landing_page || '',
        brand_terms:              (l.brand_terms || []).join('\n'),
        usp_main:                 l.usp_main || '',
        headlines:                (l.headlines || []).join('\n'),
        descriptions:             (l.descriptions || []).join('\n'),
        callouts:                 (l.callouts || []).join('\n'),
        sitelinks:                l.sitelinks || [],
        kw_themes:                '',
        kw_negative:              '',
        brand_headlines:          (l.brand_headlines || []).join('\n'),
        brand_descriptions:       (l.brand_descriptions || []).join('\n'),
        acquisition_headlines:    (l.acquisition_headlines || []).join('\n'),
        acquisition_descriptions: (l.acquisition_descriptions || []).join('\n'),
        retargeting_headlines:    (l.retargeting_headlines || []).join('\n'),
        retargeting_descriptions: (l.retargeting_descriptions || []).join('\n'),
      })))
    }

    setAutofillSuccess(true)
  }, [pendingAutofill])
}
