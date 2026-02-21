import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, autofillApi, AutofillResult } from '../api/projects'
import { T } from '../styles/theme'
import { GoogleAdPreview } from './GoogleAdPreview'

// ── types ─────────────────────────────────────────────────────────────────────

interface FormState {
  project_name: string
  preset: string
  vertical: string
  created_by: string
  brand_name: string
  brand_slug: string
  domain: string
  country: string
  currency: string
  timezone: string
  google_ads_customer_id: string
  primary_objective: string
  target_cpa_eur: string
  target_roas: string
  max_cpc_brand: string
  max_cpc_acquisition: string
  primary_conversion_action: string
  total_monthly_eur: string
  hotel_category: string
  stars: string
  rooms: string
  address: string
  services: string
  strengths: string
  booking_engine_url: string
  target_countries: string
  target_cities: string
}

interface SitelinkState {
  text: string
  description_1: string
  description_2: string
  final_url: string
}

interface RemarketingListState {
  name: string
  type: string
  lookback_days: string
  source: string
}

interface LangState {
  code: string
  name: string
  google_language_id: string
  landing_page: string
  brand_terms: string
  usp_main: string
  headlines: string
  descriptions: string
  callouts: string
  sitelinks: SitelinkState[]
  kw_themes: string
  kw_negative: string
  // Per-type RSA copy overrides (optional)
  brand_headlines: string
  brand_descriptions: string
  acquisition_headlines: string
  acquisition_descriptions: string
  retargeting_headlines: string
  retargeting_descriptions: string
}

// ── constants ─────────────────────────────────────────────────────────────────

const LANG_IDS: Record<string, number> = {
  IT: 1004, EN: 1000, DE: 1001, FR: 1002, ES: 1003,
  NL: 1010, PT: 1014, RU: 1031, ZH: 1017, JA: 1005,
  PL: 1030, SV: 1040, NO: 1013, DA: 1009, FI: 1011,
}

const STEPS = ['Info Base', 'Obiettivi & Budget', 'Lingue & Asset', 'Hotel & Geo', 'Anteprima', 'Revisione']

const CAMPAIGN_TYPES = [
  { key: 'brand',       label: 'Brand',           backendKey: 'search_brand' },
  { key: 'acquisition', label: 'Acquisition',      backendKey: 'search_acquisition' },
  { key: 'retargeting', label: 'Retargeting',       backendKey: 'retargeting' },
  { key: 'pmax',        label: 'Performance Max',  backendKey: 'performance_max' },
  { key: 'demand_gen',  label: 'Demand Gen',        backendKey: 'demand_gen' },
] as const

const DEFAULT_FORM: FormState = {
  project_name: '',
  preset: 'blastness',
  vertical: 'city_hotel',
  created_by: '',
  brand_name: '',
  brand_slug: '',
  domain: '',
  country: 'IT',
  currency: 'EUR',
  timezone: 'Europe/Rome',
  google_ads_customer_id: '',
  primary_objective: 'direct_bookings',
  target_cpa_eur: '',
  target_roas: '',
  max_cpc_brand: '',
  max_cpc_acquisition: '',
  primary_conversion_action: 'purchase',
  total_monthly_eur: '',
  hotel_category: 'city_hotel',
  stars: '3',
  rooms: '',
  address: '',
  services: '',
  strengths: '',
  booking_engine_url: '',
  target_countries: 'IT',
  target_cities: '',
}

const DEFAULT_LANG: LangState = {
  code: 'IT',
  name: 'Italiano',
  google_language_id: '1004',
  landing_page: '',
  brand_terms: '',
  usp_main: '',
  headlines: '',
  descriptions: '',
  callouts: '',
  sitelinks: [],
  kw_themes: '',
  kw_negative: '',
  brand_headlines: '',
  brand_descriptions: '',
  acquisition_headlines: '',
  acquisition_descriptions: '',
  retargeting_headlines: '',
  retargeting_descriptions: '',
}

// ── helpers ───────────────────────────────────────────────────────────────────

const toLines = (s: string) => s.split('\n').map(l => l.trim()).filter(Boolean)

/** Trim text to max chars without cutting mid-word. Drops the last partial word. */
const trimToWord = (s: string, max: number): string => {
  if (s.length <= max) return s
  const cut = s.slice(0, max)
  // If the character immediately after max is not a space, we're mid-word
  if (max < s.length && s[max] !== ' ') {
    const space = cut.lastIndexOf(' ')
    if (space > 0) return cut.slice(0, space)
    return cut // single very long word — no choice but to trim
  }
  return cut.trimEnd()
}

function getUserEmail(): string {
  try {
    const token = localStorage.getItem('token')
    if (!token) return ''
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.email || payload.sub || ''
  } catch {
    return ''
  }
}

function briefToForm(b: Record<string, unknown>): FormState {
  const meta = (b.meta || {}) as Record<string, unknown>
  const client = (b.client || {}) as Record<string, unknown>
  const obj = (b.objectives || {}) as Record<string, unknown>
  const kpi = (obj.kpi || {}) as Record<string, unknown>
  const conv = (obj.conversions || {}) as Record<string, unknown>
  const budgets = (b.budgets || {}) as Record<string, unknown>
  const hotel = (b.hotel_specifics || {}) as Record<string, unknown>
  const loc = (hotel.location || {}) as Record<string, unknown>
  const geo = (b.geo_targeting || {}) as Record<string, unknown>
  return {
    project_name: String(meta.project_name || ''),
    preset: String(meta.preset || 'blastness'),
    vertical: String(meta.vertical || 'city_hotel'),
    created_by: String(meta.created_by || ''),
    brand_name: String(client.brand_name || ''),
    brand_slug: String(client.brand_slug || ''),
    domain: String(client.domain || ''),
    country: String(client.country || 'IT'),
    currency: String(client.currency || 'EUR'),
    timezone: String(client.timezone || 'Europe/Rome'),
    google_ads_customer_id: String(client.google_ads_customer_id || ''),
    primary_objective: String(obj.primary || 'direct_bookings'),
    target_cpa_eur: kpi.target_cpa_eur != null ? String(kpi.target_cpa_eur) : '',
    target_roas: kpi.target_roas != null ? String(kpi.target_roas) : '',
    max_cpc_brand: kpi.max_cpc_brand != null ? String(kpi.max_cpc_brand) : '',
    max_cpc_acquisition: kpi.max_cpc_acquisition != null ? String(kpi.max_cpc_acquisition) : '',
    primary_conversion_action: String(conv.primary_conversion_action || 'purchase'),
    total_monthly_eur: budgets.total_monthly_eur != null ? String(budgets.total_monthly_eur) : '',
    hotel_category: String(hotel.category || 'city_hotel'),
    stars: String(hotel.stars || '3'),
    rooms: hotel.rooms != null ? String(hotel.rooms) : '',
    address: String(loc.address || ''),
    services: ((hotel.services as string[]) || []).join('\n'),
    strengths: ((hotel.strengths as string[]) || []).join('\n'),
    booking_engine_url: String(hotel.booking_engine_url || ''),
    target_countries: ((geo.target_countries as string[]) || []).join('\n'),
    target_cities: ((geo.target_cities as string[]) || []).join('\n'),
  }
}

function briefToSelectedTypes(b: Record<string, unknown>): Set<string> {
  const byCT = ((b.budgets as Record<string, unknown>)?.by_campaign_type || {}) as Record<string, unknown>
  if (Object.keys(byCT).length === 0) return new Set(['brand', 'acquisition', 'pmax'])
  const found = new Set<string>()
  for (const ct of CAMPAIGN_TYPES) {
    const entry = byCT[ct.backendKey] as Record<string, unknown> | undefined
    const byLang = (entry?.by_language || {}) as Record<string, number>
    if (Object.values(byLang).some(v => v > 0)) found.add(ct.key)
  }
  return found.size > 0 ? found : new Set(['brand', 'acquisition', 'pmax'])
}

function briefToBudgetByTypeLang(b: Record<string, unknown>): Record<string, Record<string, string>> {
  const byCT = ((b.budgets as Record<string, unknown>)?.by_campaign_type || {}) as Record<string, unknown>
  const result: Record<string, Record<string, string>> = {}
  for (const ct of CAMPAIGN_TYPES) {
    const entry = byCT[ct.backendKey] as Record<string, unknown> | undefined
    if (!entry) continue
    const byLang = (entry.by_language || {}) as Record<string, number>
    result[ct.key] = {}
    for (const [code, monthly] of Object.entries(byLang)) {
      result[ct.key][code] = String(Math.round((monthly / 30.44) * 100) / 100)
    }
  }
  return result
}

function parseKwThemes(text: string): Record<string, string[]> {
  const themes: Record<string, string[]> = {}
  for (const line of text.split('\n')) {
    const colonIdx = line.indexOf(':')
    if (colonIdx === -1 || !line.trim()) continue
    const theme = line.slice(0, colonIdx).trim()
    const keywords = line.slice(colonIdx + 1).split(',').map(k => k.trim()).filter(Boolean)
    if (theme && keywords.length > 0) themes[theme] = keywords
  }
  return themes
}

function briefToRemarketingLists(b: Record<string, unknown>): RemarketingListState[] {
  const audiences = (b.audiences || {}) as Record<string, unknown>
  const lists = (audiences.remarketing_lists as Record<string, unknown>[]) || []
  return lists.map(rl => ({
    name: String(rl.name || ''),
    type: String(rl.type || 'website_visitors'),
    lookback_days: String(rl.lookback_days || '30'),
    source: String(rl.source || ''),
  }))
}

type TypeObjective = { primary_objective: string; primary_conversion_action: string }

const DEFAULT_TYPE_OBJECTIVE: TypeObjective = {
  primary_objective: 'direct_bookings',
  primary_conversion_action: 'purchase',
}

const OBJECTIVE_OPTIONS = [
  { value: 'direct_bookings', label: 'Prenotazioni dirette' },
  { value: 'lead_gen',        label: 'Lead generation' },
  { value: 'phone_calls',     label: 'Telefonate' },
  { value: 'brand_awareness', label: 'Brand awareness' },
]

function briefToObjectivesByType(b: Record<string, unknown>): Record<string, TypeObjective> {
  const perType = ((b.objectives as Record<string, unknown>)?.per_campaign_type || {}) as Record<string, Record<string, unknown>>
  const result: Record<string, TypeObjective> = {}
  for (const ct of CAMPAIGN_TYPES) {
    const entry = perType[ct.backendKey]
    if (entry) {
      result[ct.key] = {
        primary_objective: String(entry.primary || 'direct_bookings'),
        primary_conversion_action: String(entry.primary_conversion_action || 'purchase'),
      }
    }
  }
  return result
}

function briefToLangs(b: Record<string, unknown>): LangState[] {
  const langs = (b.languages as Record<string, unknown>[]) || []
  if (!langs.length) return [{ ...DEFAULT_LANG }]
  const akw = (b.acquisition_keywords || {}) as Record<string, unknown>
  return langs.map(l => {
    const code = String(l.code || '').toUpperCase()
    const sitelinks = ((l.sitelinks as Record<string, unknown>[]) || []).map(sl => ({
      text: String(sl.text || ''),
      description_1: String(sl.description_1 || ''),
      description_2: String(sl.description_2 || ''),
      final_url: String(sl.final_url || ''),
    }))
    const kwPlan = akw[code] as Record<string, unknown> | undefined
    let kw_themes = ''
    let kw_negative = ''
    if (kwPlan) {
      const themes = (kwPlan.themes || {}) as Record<string, string[]>
      kw_themes = Object.entries(themes).map(([t, kws]) => `${t}: ${kws.join(', ')}`).join('\n')
      kw_negative = ((kwPlan.negative_keywords as string[]) || []).join('\n')
    }
    const brandAssets = l.brand_assets as { headlines?: string[]; descriptions?: string[] } | undefined
    const acqAssets = l.acquisition_assets as { headlines?: string[]; descriptions?: string[] } | undefined
    const retAssets = l.retargeting_assets as { headlines?: string[]; descriptions?: string[] } | undefined
    return {
      code,
      name: String(l.name || ''),
      google_language_id: String(l.google_language_id || ''),
      landing_page: String(l.landing_page || ''),
      brand_terms: ((l.brand_terms as string[]) || []).join('\n'),
      usp_main: String(((l.usp as Record<string, unknown>)?.main) || ''),
      headlines: ((l.headlines as string[]) || []).join('\n'),
      descriptions: ((l.descriptions as string[]) || []).join('\n'),
      callouts: ((l.callouts as string[]) || []).join('\n'),
      sitelinks,
      kw_themes,
      kw_negative,
      brand_headlines: (brandAssets?.headlines || []).join('\n'),
      brand_descriptions: (brandAssets?.descriptions || []).join('\n'),
      acquisition_headlines: (acqAssets?.headlines || []).join('\n'),
      acquisition_descriptions: (acqAssets?.descriptions || []).join('\n'),
      retargeting_headlines: (retAssets?.headlines || []).join('\n'),
      retargeting_descriptions: (retAssets?.descriptions || []).join('\n'),
    }
  })
}

function buildBrief(
  form: FormState,
  langs: LangState[],
  selectedTypes: Set<string>,
  budgetByTypeLang: Record<string, Record<string, string>>,
  remarketingLists: RemarketingListState[],
  objectivesByType: Record<string, TypeObjective>,
): Record<string, unknown> {
  const activeLangCodes = langs.map(l => l.code.toUpperCase())
  const byCampaignType: Record<string, unknown> = {}
  let totalMonthly = 0
  for (const ct of CAMPAIGN_TYPES) {
    if (!selectedTypes.has(ct.key)) continue
    const byLanguage: Record<string, number> = {}
    let typeMonthly = 0
    for (const code of activeLangCodes) {
      const daily = parseFloat(budgetByTypeLang[ct.key]?.[code] ?? '0') || 0
      const monthly = Math.round(daily * 30.44 * 100) / 100
      byLanguage[code] = monthly
      typeMonthly += monthly
    }
    byCampaignType[ct.backendKey] = { total: Math.round(typeMonthly * 100) / 100, by_language: byLanguage }
    totalMonthly += typeMonthly
  }
  return {
    version: '1.0',
    meta: {
      project_name: form.project_name,
      created_by: form.created_by || getUserEmail() || 'admin@blastness.com',
      preset: form.preset,
      vertical: form.vertical,
    },
    client: {
      brand_name: form.brand_name,
      brand_slug: form.brand_slug,
      domain: form.domain,
      country: form.country.toUpperCase().slice(0, 2),
      currency: form.currency.toUpperCase().slice(0, 3),
      timezone: form.timezone,
      google_ads_customer_id: form.google_ads_customer_id || null,
    },
    objectives: {
      // Global fallback: use the first selected type's objective, or the default.
      primary: (() => {
        const firstType = CAMPAIGN_TYPES.find(ct => selectedTypes.has(ct.key))
        return (firstType && objectivesByType[firstType.key]?.primary_objective) || 'direct_bookings'
      })(),
      secondary: [],
      kpi: {
        target_cpa_eur: form.target_cpa_eur ? parseFloat(form.target_cpa_eur) : null,
        target_roas: form.target_roas ? parseFloat(form.target_roas) : null,
        max_cpc_brand: form.max_cpc_brand ? parseFloat(form.max_cpc_brand) : null,
        max_cpc_acquisition: form.max_cpc_acquisition ? parseFloat(form.max_cpc_acquisition) : null,
      },
      conversions: {
        // Global fallback: first selected type's conversion action.
        primary_conversion_action: (() => {
          const firstType = CAMPAIGN_TYPES.find(ct => selectedTypes.has(ct.key))
          return (firstType && objectivesByType[firstType.key]?.primary_conversion_action) || 'purchase'
        })(),
        conversion_action_ids: [],
        secondary_conversion_actions: [],
        value_per_conversion: null,
      },
      per_campaign_type: Object.fromEntries(
        CAMPAIGN_TYPES
          .filter(ct => selectedTypes.has(ct.key))
          .map(ct => {
            const obj = objectivesByType[ct.key] ?? DEFAULT_TYPE_OBJECTIVE
            return [ct.backendKey, {
              primary: obj.primary_objective,
              primary_conversion_action: obj.primary_conversion_action || 'purchase',
            }]
          })
      ),
    },
    campaign_types: CAMPAIGN_TYPES
      .filter(ct => selectedTypes.has(ct.key))
      .map(ct => ct.backendKey),
    budgets: {
      total_monthly_eur: Math.round(totalMonthly * 100) / 100,
      by_campaign_type: byCampaignType,
    },
    languages: langs.map(l => ({
      code: l.code.toUpperCase(),
      name: l.name,
      google_language_id: parseInt(l.google_language_id) || LANG_IDS[l.code.toUpperCase()] || 0,
      landing_page: l.landing_page,
      brand_terms: toLines(l.brand_terms),
      brand_variants: [],
      brand_exclusions: [],
      usp: { main: l.usp_main || '', bullets: [] },
      headlines: toLines(l.headlines),
      descriptions: toLines(l.descriptions),
      sitelinks: l.sitelinks
        .filter(sl => sl.text.trim())
        .map(sl => ({
          text: trimToWord(sl.text, 25),
          description_1: trimToWord(sl.description_1, 35),
          description_2: trimToWord(sl.description_2, 35),
          final_url: sl.final_url || l.landing_page,
        })),
      callouts: toLines(l.callouts),
      structured_snippets: [],
      brand_assets: toLines(l.brand_headlines).length > 0 ? {
        headlines: toLines(l.brand_headlines).map(h => trimToWord(h, 30)),
        descriptions: toLines(l.brand_descriptions).map(d => trimToWord(d, 90)),
      } : null,
      acquisition_assets: toLines(l.acquisition_headlines).length > 0 ? {
        headlines: toLines(l.acquisition_headlines).map(h => trimToWord(h, 30)),
        descriptions: toLines(l.acquisition_descriptions).map(d => trimToWord(d, 90)),
      } : null,
      retargeting_assets: toLines(l.retargeting_headlines).length > 0 ? {
        headlines: toLines(l.retargeting_headlines).map(h => trimToWord(h, 30)),
        descriptions: toLines(l.retargeting_descriptions).map(d => trimToWord(d, 90)),
      } : null,
    })),
    geo_targeting: {
      target_countries: toLines(form.target_countries),
      target_regions: [],
      target_cities: toLines(form.target_cities),
      exclusions: {},
      radius_targets: [],
    },
    acquisition_keywords: (() => {
      const akw: Record<string, unknown> = {}
      for (const l of langs) {
        const themes = parseKwThemes(l.kw_themes)
        const negatives = toLines(l.kw_negative)
        if (Object.keys(themes).length > 0 || negatives.length > 0) {
          akw[l.code.toUpperCase()] = { themes, negative_keywords: negatives }
        }
      }
      return Object.keys(akw).length > 0 ? akw : null
    })(),
    audiences: {
      remarketing_lists: remarketingLists
        .filter(rl => rl.name.trim())
        .map(rl => ({
          name: rl.name.trim(),
          type: rl.type || 'website_visitors',
          lookback_days: parseInt(rl.lookback_days) || 30,
          source: rl.source.trim() || 'website',
        })),
      customer_match: { enabled: false },
      in_market_segments: [],
      custom_intent: [],
    },
    hotel_specifics: {
      category: form.hotel_category,
      stars: parseInt(form.stars) || 3,
      rooms: form.rooms ? parseInt(form.rooms) : null,
      location: {
        address: form.address,
        coordinates: null,
        landmarks_nearby: [],
        distance_to_landmarks: {},
      },
      room_categories: [],
      services: toLines(form.services),
      strengths: toLines(form.strengths),
      booking_engine_url: form.booking_engine_url,
      hotel_id_google: null,
    },
    utm_config: {
      source: 'google',
      medium: '{network}',
      campaign: '{campaignid}',
      content: '{adgroupid}',
      term: '{keyword}',
      custom_params: {},
      preset_tag: null,
    },
  }
}

// ── styles ────────────────────────────────────────────────────────────────────

const css: Record<string, React.CSSProperties> = {
  stepBubble: {
    width: 28, height: 28, borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 13, fontWeight: 700, flexShrink: 0,
  },
  stepLine: { flex: 1, height: 2, marginBottom: 16, marginLeft: 4, marginRight: 4 },
  stepLabel: { fontSize: 11, marginTop: 4, textAlign: 'center' },
  section: {
    background: T.bgCard, borderRadius: T.radiusLg, padding: 24,
    boxShadow: T.shadow, marginBottom: 16, border: `1px solid ${T.borderLight}`,
  },
  sectionTitle: {
    fontWeight: 700, fontSize: 15, color: T.text,
    marginBottom: 16, paddingBottom: 8, borderBottom: `1px solid ${T.borderLight}`,
  },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  field: { marginBottom: 16 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 4 },
  hint: { display: 'block', fontSize: 11, color: T.textGray, marginBottom: 4 },
  input: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 14, boxSizing: 'border-box',
    background: T.bgCard, color: T.text,
  },
  inputErr: { borderColor: '#fca5a5' },
  select: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 14, background: T.bgCard, boxSizing: 'border-box',
    color: T.text,
  },
  textarea: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 13, fontFamily: 'inherit',
    resize: 'vertical', boxSizing: 'border-box', color: T.text,
  },
  charCount: { fontSize: 11, color: T.textGray, textAlign: 'right', marginTop: 2 },
  langCard: {
    border: `1px solid ${T.borderLight}`, borderRadius: T.radiusLg,
    padding: 16, marginBottom: 16, background: T.bgMuted,
  },
  langHeader: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: 12,
  },
  nav: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginTop: 24,
  },
  btn: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '10px 24px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnGhost: {
    background: T.bgPage, color: T.text, border: `1px solid ${T.border}`,
    padding: '10px 24px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnGreen: {
    background: T.success, color: '#fff', border: 'none',
    padding: '10px 24px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnRed: {
    background: 'transparent', color: T.error, border: '1px solid #fca5a5',
    padding: '4px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
  },
  btnAdd: {
    background: 'transparent', color: T.primary, border: `1px solid ${T.primary}`,
    padding: '8px 16px', borderRadius: T.radiusSm, cursor: 'pointer', fontSize: 13, fontWeight: 600,
  },
  errBox: {
    background: '#fff0f0', border: '1px solid #fca5a5', padding: '12px 14px',
    borderRadius: T.radiusSm, fontSize: 13, color: T.error, marginBottom: 16,
  },
  successBox: {
    background: '#f0fdf4', border: '1px solid #86efac', padding: '12px 14px',
    borderRadius: T.radiusSm, fontSize: 13, color: '#166534', marginBottom: 16,
  },
  reviewCode: {
    background: T.bgPage, border: `1px solid ${T.border}`, borderRadius: T.radiusSm,
    padding: 16, fontSize: 12, fontFamily: 'monospace',
    overflowX: 'auto', whiteSpace: 'pre-wrap', maxHeight: 500, overflowY: 'auto',
  },
  autofillPanel: {
    background: T.bgCard,
    border: `1px solid ${T.primary}33`, borderRadius: T.radiusLg,
    padding: 20, marginBottom: 24,
  },
  autofillTitle: {
    fontWeight: 700, fontSize: 15, color: T.primary,
    marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8,
  },
  autofillSubtitle: { fontSize: 12, color: T.textGray, marginBottom: 14 },
  autofillRow: { display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' as const },
  autofillUrlInput: {
    flex: 1, minWidth: 220, padding: '9px 12px',
    border: `1px solid ${T.border}`, borderRadius: T.radiusSm, fontSize: 14,
    boxSizing: 'border-box' as const, background: T.bgPage,
  },
  autofillLangPills: { display: 'flex', gap: 6, flexWrap: 'wrap' as const, marginTop: 10 },
  btnAutofill: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '9px 20px', borderRadius: T.radiusSm, cursor: 'pointer',
    fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap' as const,
  },
  autofillSuccessBox: {
    background: '#f0fdf4', border: '1px solid #86efac', padding: '10px 14px',
    borderRadius: T.radiusSm, fontSize: 13, color: '#166534', marginTop: 10,
  },
}

const langPillStyle = (active: boolean): React.CSSProperties => ({
  padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
  cursor: 'pointer', border: active ? `2px solid ${T.primary}` : `1px solid ${T.border}`,
  background: active ? T.primary : T.bgCard, color: active ? '#fff' : T.textGray,
})

// ── PerTypeCopySection ────────────────────────────────────────────────────────

function PerTypeCopySection({
  label, description,
  headlinesValue, descriptionsValue,
  headlinesPlaceholder, descriptionsPlaceholder,
  onHeadlinesChange, onDescriptionsChange,
}: {
  label: string
  description: string
  headlinesValue: string
  descriptionsValue: string
  headlinesPlaceholder: string
  descriptionsPlaceholder: string
  onHeadlinesChange: (v: string) => void
  onDescriptionsChange: (v: string) => void
}) {
  const [open, setOpen] = useState(false)
  const hasContent = headlinesValue.trim().length > 0 || descriptionsValue.trim().length > 0

  return (
    <div style={{ border: `1px solid ${hasContent ? T.primary : T.borderLight}`, borderRadius: T.radiusSm, marginBottom: 10 }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', padding: '10px 14px',
          background: hasContent ? '#eff6ff' : T.bgPage,
          border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderRadius: T.radiusSm,
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 13, color: hasContent ? T.primary : T.textGray }}>
          {hasContent ? '✓ ' : ''}{label}
          {!hasContent && <span style={{ fontWeight: 400, fontSize: 11, marginLeft: 8, color: T.textGray }}>(opzionale)</span>}
        </span>
        <span style={{ fontSize: 11, color: T.textGray }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={{ padding: '14px 14px 10px', borderTop: `1px solid ${T.borderLight}` }}>
          <p style={{ fontSize: 12, color: T.textGray, marginBottom: 12, marginTop: 0 }}>{description}</p>

          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: T.text, display: 'block', marginBottom: 4 }}>
              Headline dedicate (una per riga — max 30 car.)
            </label>
            <textarea
              style={{ width: '100%', fontFamily: 'inherit', fontSize: 13, padding: '8px 10px', border: `1px solid ${T.border}`, borderRadius: T.radiusSm, minHeight: 90, resize: 'vertical', boxSizing: 'border-box' as const }}
              value={headlinesValue}
              onChange={e => onHeadlinesChange(e.target.value)}
              placeholder={headlinesPlaceholder}
            />
            {toLines(headlinesValue).map((h, j) => h.length > 30 && (
              <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                Riga {j + 1} troppo lunga ({h.length}/30)
              </div>
            ))}
            <div style={{ fontSize: 11, color: T.textGray, textAlign: 'right', marginTop: 2 }}>
              {toLines(headlinesValue).length} headline
            </div>
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: T.text, display: 'block', marginBottom: 4 }}>
              Descrizioni dedicate (una per riga — max 90 car.)
            </label>
            <textarea
              style={{ width: '100%', fontFamily: 'inherit', fontSize: 13, padding: '8px 10px', border: `1px solid ${T.border}`, borderRadius: T.radiusSm, minHeight: 70, resize: 'vertical', boxSizing: 'border-box' as const }}
              value={descriptionsValue}
              onChange={e => onDescriptionsChange(e.target.value)}
              placeholder={descriptionsPlaceholder}
            />
            {toLines(descriptionsValue).map((d, j) => d.length > 90 && (
              <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                Riga {j + 1} troppo lunga ({d.length}/90)
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── component ─────────────────────────────────────────────────────────────────

interface BriefFormProps {
  projectId: string
  existingBrief?: Record<string, unknown> | null
  onSaved: () => void
}

export default function BriefForm({ projectId, existingBrief, onSaved }: BriefFormProps) {
  const qc = useQueryClient()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<FormState>(() =>
    existingBrief ? briefToForm(existingBrief) : { ...DEFAULT_FORM, created_by: getUserEmail() }
  )
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
  const [autoSlPending, setAutoSlPending] = useState(false)

  // ── Auto-fill state ────────────────────────────────────────────────────────
  const [autofillUrl, setAutofillUrl] = useState('')
  const [autofillLangs, setAutofillLangs] = useState<string[]>(['IT', 'EN'])
  const [autofillSuccess, setAutofillSuccess] = useState(false)
  const [autofillManual, setAutofillManual] = useState(false)
  const [autofillContent, setAutofillContent] = useState('')

  const autofillMutation = useMutation({
    mutationFn: () => autofillApi.fromUrl(
      autofillUrl.trim(),
      autofillLangs,
      autofillManual && autofillContent.trim() ? autofillContent.trim() : undefined,
    ),
    onSuccess: (data: AutofillResult) => {
      // Populate form fields with AI-extracted data
      setForm(prev => ({
        ...prev,
        brand_name: data.brand_name || prev.brand_name,
        brand_slug: data.brand_slug || prev.brand_slug,
        domain: data.domain || prev.domain,
        country: data.country || prev.country,
        hotel_category: data.hotel_category || prev.hotel_category,
        stars: data.stars != null ? String(data.stars) : prev.stars,
        rooms: data.rooms != null ? String(data.rooms) : prev.rooms,
        address: data.address || prev.address,
        services: (data.services || []).join('\n'),
        strengths: (data.strengths || []).join('\n'),
        booking_engine_url: data.booking_engine_url || prev.booking_engine_url,
        target_countries: (data.target_countries || []).join('\n') || prev.target_countries,
        project_name: prev.project_name || `${data.brand_name} — Google Ads`,
      }))
      // Populate language assets
      if (data.languages && data.languages.length > 0) {
        setLangs(data.languages.map(l => ({
          code: l.code,
          name: l.name,
          google_language_id: String(l.google_language_id || ''),
          landing_page: l.landing_page || '',
          brand_terms: (l.brand_terms || []).join('\n'),
          usp_main: l.usp_main || '',
          headlines: (l.headlines || []).join('\n'),
          descriptions: (l.descriptions || []).join('\n'),
          callouts: (l.callouts || []).join('\n'),
          sitelinks: [],
          kw_themes: '',
          kw_negative: '',
          brand_headlines: '',
          brand_descriptions: '',
          acquisition_headlines: '',
          acquisition_descriptions: '',
          retargeting_headlines: '',
          retargeting_descriptions: '',
        })))
        // Auto-generate sitelinks + per-type RSA copy for each language in parallel
        setAutoSlPending(true)
        const commonArgs = {
          brand_name: data.brand_name,
          hotel_category: data.hotel_category || 'city_hotel',
          stars: data.stars || 3,
          domain: data.domain || undefined,
          services: data.services || [],
          strengths: data.strengths || [],
        }
        Promise.allSettled(data.languages.flatMap((l, idx) => {
          const langArgs = { ...commonArgs, language_code: l.code, usp_main: l.usp_main || undefined }
          return [
            // Sitelinks
            autofillApi.suggestSitelinks({
              ...langArgs,
              landing_page: l.landing_page || `https://${data.domain}`,
              booking_engine_url: data.booking_engine_url || undefined,
            }).then(slData => {
              setLangs(prev => prev.map((lang, i) => i === idx
                ? { ...lang, sitelinks: slData.sitelinks }
                : lang
              ))
            }),
            // Brand copy
            autofillApi.suggestTypeCopy({ ...langArgs, campaign_type: 'brand' }).then(copyData => {
              setLangs(prev => prev.map((lang, i) => i === idx
                ? { ...lang, brand_headlines: copyData.headlines.join('\n'), brand_descriptions: copyData.descriptions.join('\n') }
                : lang
              ))
            }),
            // Acquisition copy
            autofillApi.suggestTypeCopy({ ...langArgs, campaign_type: 'acquisition' }).then(copyData => {
              setLangs(prev => prev.map((lang, i) => i === idx
                ? { ...lang, acquisition_headlines: copyData.headlines.join('\n'), acquisition_descriptions: copyData.descriptions.join('\n') }
                : lang
              ))
            }),
            // Retargeting copy
            autofillApi.suggestTypeCopy({ ...langArgs, campaign_type: 'retargeting' }).then(copyData => {
              setLangs(prev => prev.map((lang, i) => i === idx
                ? { ...lang, retargeting_headlines: copyData.headlines.join('\n'), retargeting_descriptions: copyData.descriptions.join('\n') }
                : lang
              ))
            }),
          ]
        })).finally(() => setAutoSlPending(false))
      }
      setAutofillSuccess(true)
    },
    onError: (e: Error) => {
      setErrors([`Auto-fill: ${e.message}`])
      // Se il fetch automatico fallisce, apri la modalità manuale
      if (!autofillManual) setAutofillManual(true)
    },
  })

  const toggleAutofillLang = (code: string) => {
    setAutofillLangs(prev =>
      prev.includes(code) ? prev.filter(l => l !== code) : [...prev, code]
    )
  }

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
      setLangs(prev => prev.map((l, i) => i === langIdx
        ? { ...l, sitelinks: data.sitelinks }
        : l
      ))
      setSlSuggestingLang(null)
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
      // Brief is always saved by backend — always navigate after save
      setSaveSuccess(true)
      if (result.validation.errors.length > 0) {
        setErrors(result.validation.errors.map(e => e.message))
        setSaveHadWarnings(true)
      }
      setTimeout(onSaved, 1800)
    },
    onError: (e: Error) => setErrors([e.message]),
  })

  const setField = (key: keyof FormState, val: string) =>
    setForm(prev => ({ ...prev, [key]: val }))

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
            ✕ Chiudi
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

      {/* ── STEP 0 — Info Base ── */}
      {step === 0 && (
        <>
          {/* ── Auto-fill Panel ── */}
          <div style={css.autofillPanel}>
            <div style={css.autofillTitle}>
              <span>✨</span> Auto-compila dal sito dell'hotel
            </div>
            <div style={css.autofillSubtitle}>
              Inserisci l'URL del sito dell'hotel: l'AI analizzerà il sito e compilerà automaticamente
              tutti i campi del brief (testi, headline, descrizioni, callout per ogni lingua).
            </div>
            <div style={css.autofillRow}>
              <input
                style={css.autofillUrlInput}
                type="url"
                value={autofillUrl}
                onChange={e => { setAutofillUrl(e.target.value); setAutofillSuccess(false) }}
                placeholder="https://www.nomedelhotel.it"
                disabled={autofillMutation.isPending}
              />
              <button
                style={{ ...css.btnAutofill, opacity: autofillMutation.isPending || !autofillUrl.trim() ? 0.6 : 1 }}
                onClick={() => { setErrors([]); setAutofillSuccess(false); autofillMutation.mutate() }}
                disabled={autofillMutation.isPending || !autofillUrl.trim()}
              >
                {autofillMutation.isPending ? '⏳ Analisi in corso...' : '🔍 Analizza e compila'}
              </button>
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: T.text, fontWeight: 600 }}>
              Lingue da generare:
            </div>
            <div style={css.autofillLangPills}>
              {['IT', 'EN', 'DE', 'FR', 'ES', 'NL', 'PT'].map(code => (
                <span
                  key={code}
                  style={langPillStyle(autofillLangs.includes(code))}
                  onClick={() => !autofillMutation.isPending && toggleAutofillLang(code)}
                >
                  {code}
                </span>
              ))}
            </div>
            {/* Modalità manuale: incolla il testo del sito */}
            <div style={{ marginTop: 10 }}>
              <button
                style={{ background: 'none', border: 'none', color: '#6366f1', fontSize: 12, cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
                onClick={() => setAutofillManual(v => !v)}
              >
                {autofillManual ? '▲ Nascondi modalità manuale' : '▼ Il server non riesce a raggiungere il sito? Incolla il testo manualmente'}
              </button>
            </div>
            {autofillManual && (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 12, color: T.textGray, marginBottom: 4 }}>
                  Vai sul sito dell'hotel, seleziona tutto il testo (Ctrl+A → Ctrl+C) e incollalo qui sotto.
                  Oppure copia il testo della homepage e delle pagine camere/servizi.
                </div>
                <textarea
                  style={{ width: '100%', minHeight: 120, fontSize: 12, padding: 8, border: '1px solid #d1d5db', borderRadius: 6, resize: 'vertical', boxSizing: 'border-box' }}
                  placeholder="Incolla qui il contenuto del sito web dell'hotel..."
                  value={autofillContent}
                  onChange={e => setAutofillContent(e.target.value)}
                  disabled={autofillMutation.isPending}
                />
              </div>
            )}
            {autofillMutation.isPending && (
              <div style={{ marginTop: 10, fontSize: 12, color: T.blue }}>
                Sto analizzando il sito e generando i contenuti con AI... può richiedere 20–40 secondi.
              </div>
            )}
            {autofillSuccess && (
              <div style={css.autofillSuccessBox}>
                ✅ Campi compilati con successo! Scorri il form per rivedere e correggere i dati generati.
              </div>
            )}
          </div>

          <div style={css.section}>
            <div style={css.sectionTitle}>Informazioni Progetto</div>
            <div style={css.grid2}>
              <div style={css.field}>
                <label style={css.label}>Nome progetto *</label>
                <input
                  style={css.input}
                  value={form.project_name}
                  onChange={e => setField('project_name', e.target.value)}
                  placeholder="es. Hotel Bella Vista — Search 2024"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Email strategist</label>
                <input
                  style={css.input}
                  value={form.created_by}
                  onChange={e => setField('created_by', e.target.value)}
                  placeholder="nome@agenzia.com"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Preset</label>
                <select style={css.select} value={form.preset} onChange={e => setField('preset', e.target.value)}>
                  <option value="blastness">Blastness</option>
                  <option value="mentefredda">Mentefredda</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div style={css.field}>
                <label style={css.label}>Tipologia struttura</label>
                <select style={css.select} value={form.vertical} onChange={e => setField('vertical', e.target.value)}>
                  <option value="city_hotel">City Hotel</option>
                  <option value="resort">Resort</option>
                  <option value="boutique">Boutique</option>
                  <option value="business">Business</option>
                  <option value="agriturismo">Agriturismo</option>
                </select>
              </div>
            </div>
          </div>

          <div style={css.section}>
            <div style={css.sectionTitle}>Dati Cliente</div>
            <div style={css.grid2}>
              <div style={css.field}>
                <label style={css.label}>Nome brand *</label>
                <input
                  style={css.input}
                  value={form.brand_name}
                  onChange={e => setField('brand_name', e.target.value)}
                  placeholder="es. Hotel Bella Vista"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Brand slug *</label>
                <span style={css.hint}>Solo lettere minuscole, numeri e trattini</span>
                <input
                  style={css.input}
                  value={form.brand_slug}
                  onChange={e => setField('brand_slug', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
                  placeholder="hotel-bella-vista"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Dominio *</label>
                <span style={css.hint}>Senza https://</span>
                <input
                  style={css.input}
                  value={form.domain}
                  onChange={e => setField('domain', e.target.value)}
                  placeholder="www.hotelbella.it"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Timezone</label>
                <input
                  style={css.input}
                  value={form.timezone}
                  onChange={e => setField('timezone', e.target.value)}
                  placeholder="Europe/Rome"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Paese (ISO 2) *</label>
                <input
                  style={css.input}
                  value={form.country}
                  onChange={e => setField('country', e.target.value.toUpperCase().slice(0, 2))}
                  placeholder="IT"
                  maxLength={2}
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Valuta (ISO 3)</label>
                <input
                  style={css.input}
                  value={form.currency}
                  onChange={e => setField('currency', e.target.value.toUpperCase().slice(0, 3))}
                  placeholder="EUR"
                  maxLength={3}
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Google Ads Customer ID</label>
                <span style={css.hint}>Formato: 123-456-7890</span>
                <input
                  style={css.input}
                  value={form.google_ads_customer_id}
                  onChange={e => setField('google_ads_customer_id', e.target.value)}
                  placeholder="123-456-7890"
                />
              </div>
            </div>
          </div>
        </>
      )}

      {/* ── STEP 1 — Obiettivi & Budget ── */}
      {step === 1 && (
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
            <div style={css.sectionTitle}>KPI Target (opzionali)</div>
            <div style={css.grid2}>
              <div style={css.field}>
                <label style={css.label}>Target CPA (€)</label>
                <input
                  style={css.input}
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.target_cpa_eur}
                  onChange={e => setField('target_cpa_eur', e.target.value)}
                  placeholder="es. 25.00"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Target ROAS</label>
                <input
                  style={css.input}
                  type="number"
                  min="0"
                  step="0.1"
                  value={form.target_roas}
                  onChange={e => setField('target_roas', e.target.value)}
                  placeholder="es. 4.0"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Max CPC Brand (€)</label>
                <input
                  style={css.input}
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.max_cpc_brand}
                  onChange={e => setField('max_cpc_brand', e.target.value)}
                  placeholder="es. 1.50"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Max CPC Acquisition (€)</label>
                <input
                  style={css.input}
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.max_cpc_acquisition}
                  onChange={e => setField('max_cpc_acquisition', e.target.value)}
                  placeholder="es. 2.00"
                />
              </div>
            </div>
          </div>

          <div style={css.section}>
            <div style={css.sectionTitle}>Budget campagne (€/giorno per lingua)</div>
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
                              onChange={e => setSelectedTypes(prev => {
                                const next = new Set(prev)
                                if (e.target.checked) next.add(ct.key); else next.delete(ct.key)
                                return next
                              })}
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
          </div>
        </>
      )}

      {/* ── STEP 2 — Lingue & Asset ── */}
      {step === 2 && (
        <div>
          {langs.map((lang, i) => (
            <div key={i} style={css.langCard}>
              <div style={css.langHeader}>
                <strong style={{ fontSize: 15 }}>
                  Lingua {i + 1}{lang.code ? ` — ${lang.code}` : ''}
                  {lang.name ? ` (${lang.name})` : ''}
                </strong>
                {langs.length > 1 && (
                  <button style={css.btnRed} onClick={() => removeLang(i)}>✕ Rimuovi</button>
                )}
              </div>

              <div style={css.grid2}>
                <div style={css.field}>
                  <label style={css.label}>Codice lingua *</label>
                  <span style={css.hint}>IT, EN, DE, FR, ES, NL, PT…</span>
                  <input
                    style={css.input}
                    value={lang.code}
                    onChange={e => handleLangCode(i, e.target.value)}
                    placeholder="IT"
                    maxLength={5}
                  />
                </div>
                <div style={css.field}>
                  <label style={css.label}>Nome lingua *</label>
                  <input
                    style={css.input}
                    value={lang.name}
                    onChange={e => setLangField(i, 'name', e.target.value)}
                    placeholder="Italiano"
                  />
                </div>
                <div style={css.field}>
                  <label style={css.label}>Google Language ID *</label>
                  <span style={css.hint}>IT=1004, EN=1000, DE=1001, FR=1002, ES=1003</span>
                  <input
                    style={css.input}
                    type="number"
                    value={lang.google_language_id}
                    onChange={e => setLangField(i, 'google_language_id', e.target.value)}
                    placeholder="1004"
                  />
                </div>
                <div style={css.field}>
                  <label style={css.label}>Landing Page URL *</label>
                  <input
                    style={css.input}
                    value={lang.landing_page}
                    onChange={e => setLangField(i, 'landing_page', e.target.value)}
                    placeholder="https://www.hotel.it/"
                  />
                </div>
              </div>

              <div style={css.field}>
                <label style={css.label}>Brand Terms * (uno per riga)</label>
                <span style={css.hint}>Varianti del nome brand da targettizzare nelle campagne brand</span>
                <textarea
                  style={{ ...css.textarea, minHeight: 80 }}
                  value={lang.brand_terms}
                  onChange={e => setLangField(i, 'brand_terms', e.target.value)}
                  placeholder={'Hotel Bella Vista\nBella Vista Hotel\nHBV'}
                />
              </div>

              <div style={css.field}>
                <label style={css.label}>USP principale (opzionale)</label>
                <span style={css.hint}>Proposta di valore unica — max 90 caratteri</span>
                <input
                  style={{ ...css.input, ...(lang.usp_main.length > 90 ? css.inputErr : {}) }}
                  value={lang.usp_main}
                  onChange={e => setLangField(i, 'usp_main', e.target.value)}
                  placeholder="es. Prenota diretto e risparmia fino al 20%"
                />
                <div style={css.charCount}>{lang.usp_main.length} / 90</div>
              </div>

              <div style={css.field}>
                <label style={css.label}>Headline RSA * (una per riga — min 3, max 30 caratteri ciascuna)</label>
                <textarea
                  style={{ ...css.textarea, minHeight: 130 }}
                  value={lang.headlines}
                  onChange={e => setLangField(i, 'headlines', e.target.value)}
                  placeholder={'Hotel Bella Vista\nPrenota Diretto Online\nMiglior Tariffa Garantita\nVista Mare Panoramica\nPiscina Esterna Riscaldata'}
                />
                {toLines(lang.headlines).map((h, j) => h.length > 30 && (
                  <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                    Riga {j + 1} troppo lunga ({h.length}/30): "{h.slice(0, 25)}..."
                  </div>
                ))}
                <div style={css.charCount}>{toLines(lang.headlines).length} headline</div>
              </div>

              <div style={css.field}>
                <label style={css.label}>Descrizioni RSA * (una per riga — min 2, max 90 caratteri ciascuna)</label>
                <textarea
                  style={{ ...css.textarea, minHeight: 100 }}
                  value={lang.descriptions}
                  onChange={e => setLangField(i, 'descriptions', e.target.value)}
                  placeholder={'Prenota sul sito ufficiale per la migliore tariffa garantita e disdici gratis.\nCamera Superior con vista mare e colazione inclusa, posizione centrale.'}
                />
                {toLines(lang.descriptions).map((d, j) => d.length > 90 && (
                  <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                    Riga {j + 1} troppo lunga ({d.length}/90)
                  </div>
                ))}
                <div style={css.charCount}>{toLines(lang.descriptions).length} descrizioni</div>
              </div>

              <div style={css.field}>
                <label style={css.label}>Callout (uno per riga — opzionale)</label>
                <textarea
                  style={{ ...css.textarea, minHeight: 80 }}
                  value={lang.callouts}
                  onChange={e => setLangField(i, 'callouts', e.target.value)}
                  placeholder={'Cancellazione gratuita\nWi-Fi incluso\nParcheggio gratuito\nCheck-in anticipato'}
                />
              </div>

              {/* ── Sitelinks ── */}
              <div style={css.field}>
                <label style={css.label}>Sitelink (consigliati min. 2)</label>
                <span style={css.hint}>Testo max 25 car. · Descrizioni max 35 car. ciascuna</span>
                <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'center', flexWrap: 'wrap' as const }}>
                  <button
                    style={{ ...css.btnAdd, fontSize: 12, padding: '6px 14px', opacity: slSuggestingLang === i ? 0.6 : 1 }}
                    onClick={() => {
                      if (!form.brand_name) { setErrors(['Inserisci prima il nome del brand (Step 0)']); return }
                      setSlSuggestingLang(i)
                      slSuggestMutation.mutate({ langIdx: i, lang })
                    }}
                    disabled={slSuggestingLang === i}
                  >
                    {slSuggestingLang === i ? '⏳ Generando sitelink...' : '✨ Genera sitelink con AI'}
                  </button>
                  <span style={{ fontSize: 11, color: T.textGray }}>oppure aggiungili manualmente →</span>
                </div>
                {lang.sitelinks.map((sl, j) => (
                  <div key={j} style={{ border: `1px solid ${T.borderLight}`, borderRadius: 6, padding: 10, marginBottom: 8, background: T.bgPage }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <strong style={{ fontSize: 12, color: T.textGray }}>Sitelink {j + 1}</strong>
                      <button style={css.btnRed} onClick={() => removeSitelink(i, j)}>✕</button>
                    </div>
                    <div style={css.grid2}>
                      <div>
                        <label style={{ ...css.label, fontSize: 11 }}>Testo *</label>
                        <input style={css.input} value={sl.text} onChange={e => setSitelinkField(i, j, 'text', e.target.value)} maxLength={25} placeholder="Prenota Ora" />
                        <div style={css.charCount}>{sl.text.length}/25</div>
                      </div>
                      <div>
                        <label style={{ ...css.label, fontSize: 11 }}>URL finale *</label>
                        <input style={css.input} value={sl.final_url} onChange={e => setSitelinkField(i, j, 'final_url', e.target.value)} placeholder="https://..." />
                      </div>
                      <div>
                        <label style={{ ...css.label, fontSize: 11 }}>Descrizione 1</label>
                        <input style={css.input} value={sl.description_1} onChange={e => setSitelinkField(i, j, 'description_1', e.target.value)} maxLength={35} placeholder="Miglior tariffa garantita" />
                        <div style={css.charCount}>{sl.description_1.length}/35</div>
                      </div>
                      <div>
                        <label style={{ ...css.label, fontSize: 11 }}>Descrizione 2</label>
                        <input style={css.input} value={sl.description_2} onChange={e => setSitelinkField(i, j, 'description_2', e.target.value)} maxLength={35} placeholder="Cancellazione gratuita" />
                        <div style={css.charCount}>{sl.description_2.length}/35</div>
                      </div>
                    </div>
                  </div>
                ))}
                <button style={css.btnAdd} onClick={() => addSitelink(i)}>+ Aggiungi sitelink</button>
              </div>

              {/* ── Acquisition Keywords ── */}
              <div style={css.field}>
                <label style={css.label}>Keyword Acquisition — opzionale</label>
                <span style={css.hint}>Formato: "tema: kw1, kw2, kw3" — una riga per tema. Usate nelle campagne Search Acquisition.</span>
                <div style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'center', flexWrap: 'wrap' as const }}>
                  <button
                    style={{ ...css.btnAdd, fontSize: 12, padding: '6px 14px', opacity: kwSuggestingLang === i ? 0.6 : 1 }}
                    onClick={() => {
                      if (!form.brand_name) { setErrors(['Inserisci prima il nome del brand (Step 0)']); return }
                      setKwSuggestingLang(i)
                      kwSuggestMutation.mutate({ langIdx: i, lang })
                    }}
                    disabled={kwSuggestingLang === i}
                  >
                    {kwSuggestingLang === i ? '⏳ Generando keyword...' : '✨ Genera keyword con AI'}
                  </button>
                  <span style={{ fontSize: 11, color: T.textGray }}>oppure inseriscile manualmente ↓</span>
                </div>
                <textarea
                  style={{ ...css.textarea, minHeight: 100 }}
                  value={lang.kw_themes}
                  onChange={e => setLangField(i, 'kw_themes', e.target.value)}
                  placeholder={'prenotazione: prenota hotel X, hotel X booking\ncategoria: hotel 4 stelle Roma\nposizione: hotel centro storico Roma'}
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Keyword Negative — opzionale</label>
                <span style={css.hint}>Una per riga</span>
                <textarea
                  style={{ ...css.textarea, minHeight: 70 }}
                  value={lang.kw_negative}
                  onChange={e => setLangField(i, 'kw_negative', e.target.value)}
                  placeholder={'gratis\nreview\nopinioni\nfoto'}
                />
              </div>

              {/* ── Per-type RSA copy (optional) ── */}
              <PerTypeCopySection
                label="Copy Brand Search"
                description="Copy dedicata alle campagne Brand. Deve contenere il nome dell'hotel. Sostituisce gli headline generici per questo tipo di campagna."
                headlinesValue={lang.brand_headlines}
                descriptionsValue={lang.brand_descriptions}
                headlinesPlaceholder={'Hotel Bella Vista\nSito Ufficiale\nMiglior Tariffa Garantita\nPrenota Direttamente'}
                descriptionsPlaceholder={'Prenota sul sito ufficiale di Hotel Bella Vista e ottieni la miglior tariffa garantita.'}
                onHeadlinesChange={v => setLangField(i, 'brand_headlines', v)}
                onDescriptionsChange={v => setLangField(i, 'brand_descriptions', v)}
              />

              <PerTypeCopySection
                label="Copy Acquisition Search"
                description="Copy per campagne di acquisizione. NON deve contenere il brand — usa termini di categoria, posizione e USP generici."
                headlinesValue={lang.acquisition_headlines}
                descriptionsValue={lang.acquisition_descriptions}
                headlinesPlaceholder={'Hotel 4 Stelle Roma Centro\nColazione Inclusa\nPiscina Panoramica\nCancellazione Gratuita'}
                descriptionsPlaceholder={'Hotel 4 stelle nel cuore di Roma. Prenota online e risparmia fino al 20% sulla tariffa ufficiale.'}
                onHeadlinesChange={v => setLangField(i, 'acquisition_headlines', v)}
                onDescriptionsChange={v => setLangField(i, 'acquisition_descriptions', v)}
              />

              <PerTypeCopySection
                label="Copy Retargeting / Display"
                description="Copy urgency/personalizzata per visitatori che hanno già visto il sito. Usa messaggi di ritorno e offerte riservate."
                headlinesValue={lang.retargeting_headlines}
                descriptionsValue={lang.retargeting_descriptions}
                headlinesPlaceholder={'Completa la Prenotazione\nOfferta Riservata a Te\nUltimi Posti Disponibili\nTorna e Risparmia'}
                descriptionsPlaceholder={'Hai visitato il nostro sito? Completa la prenotazione oggi e approfitta di una tariffa esclusiva.'}
                onHeadlinesChange={v => setLangField(i, 'retargeting_headlines', v)}
                onDescriptionsChange={v => setLangField(i, 'retargeting_descriptions', v)}
              />
            </div>
          ))}
          <button style={css.btnAdd} onClick={addLang}>+ Aggiungi lingua</button>
        </div>
      )}

      {/* ── STEP 3 — Hotel & Geo ── */}
      {step === 3 && (
        <>
          <div style={css.section}>
            <div style={css.sectionTitle}>Specifiche Hotel</div>
            <div style={css.grid2}>
              <div style={css.field}>
                <label style={css.label}>Categoria struttura *</label>
                <select style={css.select} value={form.hotel_category} onChange={e => setField('hotel_category', e.target.value)}>
                  <option value="city_hotel">City Hotel</option>
                  <option value="resort">Resort</option>
                  <option value="boutique">Boutique</option>
                  <option value="business">Business</option>
                  <option value="agriturismo">Agriturismo</option>
                </select>
              </div>
              <div style={css.field}>
                <label style={css.label}>Stelle (1–5) *</label>
                <input
                  style={css.input}
                  type="number"
                  min="1"
                  max="5"
                  value={form.stars}
                  onChange={e => setField('stars', e.target.value)}
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Numero camere</label>
                <input
                  style={css.input}
                  type="number"
                  min="1"
                  value={form.rooms}
                  onChange={e => setField('rooms', e.target.value)}
                  placeholder="es. 80"
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>URL Booking Engine *</label>
                <input
                  style={css.input}
                  value={form.booking_engine_url}
                  onChange={e => setField('booking_engine_url', e.target.value)}
                  placeholder="https://booking.hotel.it/it"
                />
              </div>
            </div>
            <div style={css.field}>
              <label style={css.label}>Indirizzo completo *</label>
              <input
                style={css.input}
                value={form.address}
                onChange={e => setField('address', e.target.value)}
                placeholder="Via Roma 1, 00100 Roma, Italia"
              />
            </div>
            <div style={css.grid2}>
              <div style={css.field}>
                <label style={css.label}>Servizi offerti (uno per riga)</label>
                <textarea
                  style={{ ...css.textarea, minHeight: 110 }}
                  value={form.services}
                  onChange={e => setField('services', e.target.value)}
                  placeholder={'Piscina esterna\nSPA e centro benessere\nRistorante gourmet\nSala conferenze\nBar'}
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Punti di forza (uno per riga)</label>
                <textarea
                  style={{ ...css.textarea, minHeight: 110 }}
                  value={form.strengths}
                  onChange={e => setField('strengths', e.target.value)}
                  placeholder={'Vista panoramica sul mare\nPosizione centrale\nPersonale multilingue\nFamiglie benvenute'}
                />
              </div>
            </div>
          </div>

          <div style={css.section}>
            <div style={css.sectionTitle}>Targeting Geografico</div>
            <div style={css.grid2}>
              <div style={css.field}>
                <label style={css.label}>Paesi target (codice ISO 2, uno per riga)</label>
                <textarea
                  style={{ ...css.textarea, minHeight: 90 }}
                  value={form.target_countries}
                  onChange={e => setField('target_countries', e.target.value)}
                  placeholder={'IT\nDE\nFR\nGB'}
                />
              </div>
              <div style={css.field}>
                <label style={css.label}>Città target (una per riga — opzionale)</label>
                <textarea
                  style={{ ...css.textarea, minHeight: 90 }}
                  value={form.target_cities}
                  onChange={e => setField('target_cities', e.target.value)}
                  placeholder={'Milano\nRoma\nTorino'}
                />
              </div>
            </div>
          </div>

          <div style={css.section}>
            <div style={css.sectionTitle}>Audience & Remarketing</div>
            <p style={{ fontSize: 12, color: T.textGray, marginBottom: 12 }}>
              Obbligatorio se hai selezionato campagne <strong>Retargeting</strong> o <strong>Demand Gen</strong>.
              Inserisci le audience list già create in Google Ads.
            </p>
            {remarketingLists.map((rl, idx) => (
              <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1fr 160px 70px 1fr auto', gap: 8, marginBottom: 8, alignItems: 'flex-end' }}>
                <div>
                  <label style={{ ...css.label, fontSize: 11 }}>Nome lista *</label>
                  <input style={css.input} value={rl.name} onChange={e => setRemarketingListField(idx, 'name', e.target.value)} placeholder="All Website Visitors" />
                </div>
                <div>
                  <label style={{ ...css.label, fontSize: 11 }}>Tipo</label>
                  <select style={css.select} value={rl.type} onChange={e => setRemarketingListField(idx, 'type', e.target.value)}>
                    <option value="website_visitors">Visitatori sito</option>
                    <option value="customer_list">Customer list</option>
                    <option value="youtube">YouTube</option>
                  </select>
                </div>
                <div>
                  <label style={{ ...css.label, fontSize: 11 }}>Giorni</label>
                  <input style={css.input} type="number" min="1" max="540" value={rl.lookback_days} onChange={e => setRemarketingListField(idx, 'lookback_days', e.target.value)} placeholder="30" />
                </div>
                <div>
                  <label style={{ ...css.label, fontSize: 11 }}>Sorgente (URL o nome)</label>
                  <input style={css.input} value={rl.source} onChange={e => setRemarketingListField(idx, 'source', e.target.value)} placeholder="https://www.hotel.it" />
                </div>
                <button style={{ ...css.btnRed, alignSelf: 'flex-end', marginBottom: 0 }} onClick={() => removeRemarketingList(idx)}>✕</button>
              </div>
            ))}
            <button style={css.btnAdd} onClick={addRemarketingList}>+ Aggiungi audience list</button>
          </div>
        </>
      )}

      {/* ── STEP 4 — Anteprima Google Ads ── */}
      {step === 4 && (
        <div style={css.section}>
          <div style={css.sectionTitle}>Anteprima Google Ads</div>
          <p style={{ fontSize: 13, color: T.textGray, marginBottom: 16 }}>
            Simulazione di come apparirà il tuo annuncio su Google. Google seleziona automaticamente
            la combinazione di headline e descrizioni più performante.
          </p>
          {autoSlPending && (
            <div style={{ fontSize: 12, color: T.blue, marginBottom: 12 }}>
              ⏳ Generazione automatica sitelink e copy per tipo in corso...
            </div>
          )}
          {/* Language tabs */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' as const }}>
            {langs.map((lang, i) => (
              <button
                key={i}
                style={{
                  padding: '6px 16px', border: 'none', borderRadius: 20, cursor: 'pointer',
                  fontSize: 13, fontWeight: previewLangIdx === i ? 600 : 400,
                  background: previewLangIdx === i ? T.primary : T.bgPage,
                  color: previewLangIdx === i ? '#fff' : T.textGray,
                  transition: 'all .15s',
                }}
                onClick={() => setPreviewLangIdx(i)}
              >
                {lang.code || `Lingua ${i + 1}`}
                {lang.name ? ` — ${lang.name}` : ''}
              </button>
            ))}
          </div>
          {langs[previewLangIdx] && (() => {
            const l = langs[previewLangIdx]
            return (
              <GoogleAdPreview
                lang={{
                  headlines: toLines(l.headlines),
                  descriptions: toLines(l.descriptions),
                  callouts: toLines(l.callouts),
                  sitelinks: l.sitelinks,
                }}
                domain={form.domain || (l.landing_page ? (() => { try { return new URL(l.landing_page).hostname } catch { return '' } })() : '')}
              />
            )
          })()}
        </div>
      )}

      {/* ── STEP 5 — Revisione ── */}
      {step === 5 && (
        <div style={css.section}>
          <div style={css.sectionTitle}>Revisione Brief</div>
          <p style={{ fontSize: 13, color: T.textGray, marginBottom: 12 }}>
            Controlla il JSON prima di salvare. Puoi tornare indietro per modificare i dati.
          </p>
          <div style={css.reviewCode}>
            {JSON.stringify(buildBrief(form, langs, selectedTypes, budgetByTypeLang, remarketingLists, objectivesByType), null, 2)}
          </div>
        </div>
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
