// ── Type definitions and constants for the BriefForm wizard ──────────────────

export interface FormState {
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
  // Visual creative assets (PMax / Retargeting Display / Demand Gen)
  logo_url: string
  image_landscape: string
  image_square: string
  image_portrait: string
  youtube_video_url: string
}

export interface SitelinkState {
  text: string
  description_1: string
  description_2: string
  final_url: string
}

export interface RemarketingListState {
  name: string
  type: string
  lookback_days: string
  source: string
}

export interface LangState {
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

export type TypeObjective = { primary_objective: string; primary_conversion_action: string }

// ── Constants ─────────────────────────────────────────────────────────────────

export const LANG_IDS: Record<string, number> = {
  IT: 1004, EN: 1000, DE: 1001, FR: 1002, ES: 1003,
  NL: 1010, PT: 1014, RU: 1031, ZH: 1017, JA: 1005,
  PL: 1030, SV: 1040, NO: 1013, DA: 1009, FI: 1011,
}

export const STEPS = ['Info Base', 'Obiettivi & Budget', 'Lingue & Asset', 'Hotel & Geo', 'Anteprima', 'Revisione']

export const CAMPAIGN_TYPES = [
  { key: 'brand',       label: 'Brand',           backendKey: 'search_brand' },
  { key: 'acquisition', label: 'Acquisition',      backendKey: 'search_acquisition' },
  { key: 'retargeting', label: 'Retargeting',       backendKey: 'retargeting' },
  { key: 'pmax',        label: 'Performance Max',  backendKey: 'performance_max' },
  { key: 'demand_gen',  label: 'Demand Gen',        backendKey: 'demand_gen' },
] as const

export const DEFAULT_FORM: FormState = {
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
  logo_url: '',
  image_landscape: '',
  image_square: '',
  image_portrait: '',
  youtube_video_url: '',
}

export const DEFAULT_LANG: LangState = {
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

export const DEFAULT_TYPE_OBJECTIVE: TypeObjective = {
  primary_objective: 'direct_bookings',
  primary_conversion_action: 'purchase',
}

export const OBJECTIVE_OPTIONS = [
  { value: 'direct_bookings', label: 'Prenotazioni dirette' },
  { value: 'lead_gen',        label: 'Lead generation' },
  { value: 'phone_calls',     label: 'Telefonate' },
  { value: 'brand_awareness', label: 'Brand awareness' },
]

export const VERTICAL_DEFAULT_STARS: Record<string, string> = {
  city_hotel: '4',
  resort:     '4',
  boutique:   '4',
  business:   '4',
  agriturismo:'3',
}
