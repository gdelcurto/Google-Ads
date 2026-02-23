// ── Pure helper functions for the BriefForm wizard ───────────────────────────

import { ApiCallLogEntry } from '../../api/projects'
import {
  CAMPAIGN_TYPES, DEFAULT_LANG, LANG_IDS,
  FormState, LangState, RemarketingListState, TypeObjective,
} from './types'

// ── Text utilities ────────────────────────────────────────────────────────────

export const toLines = (s: string) => s.split('\n').map(l => l.trim()).filter(Boolean)

/**
 * Ensure text fits within max chars without cutting words mid-way.
 * Handles two cases:
 * A) text longer than max: trim to last complete word before limit.
 * B) text exactly at max and ends with a letter: LLM counted to hard limit
 *    and may have stopped mid-word — backtrack to last word boundary.
 */
export const trimToWord = (s: string, max: number): string => {
  const text = s.trimEnd()
  const cut = text.slice(0, max)

  if (text.length > max) {
    if (text[max] !== ' ') {
      const space = cut.lastIndexOf(' ')
      if (space > 0) return cut.slice(0, space)
      return cut
    }
    return cut
  }

  if (text.length === max && max >= 40 && cut.length > 0 && /[a-zA-ZÀ-ÿ]/.test(cut[cut.length - 1])) {
    const space = cut.lastIndexOf(' ')
    if (space > 0) return cut.slice(0, space)
    return cut
  }

  return cut
}

export function getUserEmail(): string {
  try {
    const token = localStorage.getItem('token')
    if (!token) return ''
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.email || payload.sub || ''
  } catch {
    return ''
  }
}

// ── Brief ↔ form conversion ───────────────────────────────────────────────────

export function briefToForm(b: Record<string, unknown>): FormState {
  const meta    = (b.meta || {}) as Record<string, unknown>
  const client  = (b.client || {}) as Record<string, unknown>
  const obj     = (b.objectives || {}) as Record<string, unknown>
  const kpi     = (obj.kpi || {}) as Record<string, unknown>
  const conv    = (obj.conversions || {}) as Record<string, unknown>
  const budgets = (b.budgets || {}) as Record<string, unknown>
  const hotel   = (b.hotel_specifics || {}) as Record<string, unknown>
  const loc     = (hotel.location || {}) as Record<string, unknown>
  const geo     = (b.geo_targeting || {}) as Record<string, unknown>
  const ca      = (b.creative_assets || {}) as Record<string, unknown>
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
    logo_url: String((ca.logo_url as string) || ''),
    image_landscape: String((ca.image_landscape as string) || ''),
    image_square: String((ca.image_square as string) || ''),
    image_portrait: String((ca.image_portrait as string) || ''),
    youtube_video_url: String((ca.youtube_video_url as string) || ''),
  }
}

export function briefToSelectedTypes(b: Record<string, unknown>): Set<string> {
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

export function briefToBudgetByTypeLang(b: Record<string, unknown>): Record<string, Record<string, string>> {
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

export function parseKwThemes(text: string): Record<string, string[]> {
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

export function briefToRemarketingLists(b: Record<string, unknown>): RemarketingListState[] {
  const audiences = (b.audiences || {}) as Record<string, unknown>
  const lists = (audiences.remarketing_lists as Record<string, unknown>[]) || []
  return lists.map(rl => ({
    name: String(rl.name || ''),
    type: String(rl.type || 'website_visitors'),
    lookback_days: String(rl.lookback_days || '30'),
    source: String(rl.source || ''),
  }))
}

export function briefToObjectivesByType(b: Record<string, unknown>): Record<string, TypeObjective> {
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

export function briefToLangs(b: Record<string, unknown>): LangState[] {
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
    const acqAssets   = l.acquisition_assets as { headlines?: string[]; descriptions?: string[] } | undefined
    const retAssets   = l.retargeting_assets as { headlines?: string[]; descriptions?: string[] } | undefined
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

// ── Brief builder ─────────────────────────────────────────────────────────────

export function buildBrief(
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
            const obj = objectivesByType[ct.key] ?? { primary_objective: 'direct_bookings', primary_conversion_action: 'purchase' }
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
    creative_assets: {
      logo_url: form.logo_url || null,
      image_landscape: form.image_landscape || null,
      image_square: form.image_square || null,
      image_portrait: form.image_portrait || null,
      youtube_video_url: form.youtube_video_url || null,
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

// ── API log helper ────────────────────────────────────────────────────────────

/** Append a single API call log entry to the project's persisted log in localStorage. */
export function appendApiLog(projectId: string, entry: ApiCallLogEntry): void {
  const key = `autofill_apilog_${projectId}`
  try {
    const raw = localStorage.getItem(key)
    const existing: unknown[] = raw ? JSON.parse(raw) : []
    existing.push(entry)
    localStorage.setItem(key, JSON.stringify(existing))
  } catch { /* ignore storage errors */ }
}
