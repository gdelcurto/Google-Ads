import { api } from './client'

export interface Project {
  id: string
  name: string
  client_slug: string
  status: string
  preset: string
  vertical: string
  has_brief: boolean
  has_plan: boolean
  owner_id: string
  created_at: string
  updated_at: string
}

export interface CampaignPreview {
  external_key: string
  campaign_name: string
  campaign_type: string
  language_code: string
  status: string
  budget_daily_eur: number
  bid_strategy: string
  can_publish: boolean
  publish_blockers: string[]
  ad_groups_count: number
  pmax_asset_groups_count: number
  dry_run_diff: Record<string, unknown> | null
  ad_groups: AdGroupPreview[]
  pmax_asset_groups: PMaxAssetGroupPreview[]
}

export interface AdGroupPreview {
  name: string
  keywords_count: number
  ads_count: number
  audience_targeting: string[]
  rsa_headlines: string[]
  rsa_descriptions: string[]
}

export interface PMaxAssetGroupPreview {
  name: string
  headlines_count: number
  has_missing_assets: boolean
  missing_asset_notes: string[]
  audience_signals: string[]
}

export interface AccountPlanPreview {
  project_id: string
  client_name: string
  generated_at: string
  is_valid: boolean
  publish_ready: boolean
  total_campaigns: number
  validation_errors: string[]
  validation_warnings: string[]
  campaigns: CampaignPreview[]
}

export interface ValidationResult {
  is_valid: boolean
  errors: { code: string; message: string; language?: string }[]
  warnings: { code: string; message: string; language?: string }[]
  checklist: { label: string; ok: boolean; detail?: string }[]
}

export const projectsApi = {
  list: () => api.get<Project[]>('/projects').then((r) => r.data),

  create: (data: { name: string; client_slug: string; preset: string; vertical: string }) =>
    api.post<Project>('/projects', data).then((r) => r.data),

  get: (id: string) => api.get<Project>(`/projects/${id}`).then((r) => r.data),

  uploadBrief: (id: string, brief: Record<string, unknown>) =>
    api.put<{ validation: ValidationResult; status: string }>(`/projects/${id}/brief`, brief).then((r) => r.data),

  getBrief: (id: string) =>
    api.get<Record<string, unknown>>(`/projects/${id}/brief`).then((r) => r.data),

  generate: (id: string, dryRun = true) =>
    api.post<AccountPlanPreview>(`/projects/${id}/generate?dry_run=${dryRun}`).then((r) => r.data),

  getPlan: (id: string) =>
    api.get<AccountPlanPreview>(`/projects/${id}/plan`).then((r) => r.data),

  exportCsv: async (id: string): Promise<void> => {
    const token = localStorage.getItem('token')
    const resp = await fetch(`/api/projects/${id}/export/csv`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }))
      throw new Error(err.detail || `Export failed: ${resp.status}`)
    }
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const cd = resp.headers.get('Content-Disposition') || ''
    const nameMatch = cd.match(/filename="([^"]+)"/)
    const filename = nameMatch ? nameMatch[1] : `campaigns_${id}.csv`
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },

  publish: (id: string, dryRun = true) =>
    api.post<Record<string, unknown>>(`/projects/${id}/publish?dry_run=${dryRun}`).then((r) => r.data),

  getAudit: (id: string) =>
    api.get<unknown[]>(`/projects/${id}/audit`).then((r) => r.data),

  savePlan: (id: string, planData: Record<string, unknown>) =>
    api.put<{ status: string; campaigns: number }>(`/projects/${id}/plan`, planData).then((r) => r.data),
}

export interface AutofillResult {
  brand_name: string
  brand_slug: string
  domain: string
  country: string
  hotel_category: string
  stars: number
  rooms: number | null
  address: string
  services: string[]
  strengths: string[]
  booking_engine_url: string
  target_countries?: string[]
  languages: {
    code: string
    name: string
    google_language_id: number
    landing_page: string
    brand_terms: string[]
    usp_main: string
    headlines: string[]
    descriptions: string[]
    callouts: string[]
  }[]
}

export const autofillApi = {
  fromUrl: (url: string, languages: string[], content?: string) =>
    api.post<AutofillResult>('/autofill', { url, languages, content }).then((r) => r.data),

  suggestKeywords: (data: {
    brand_name: string
    hotel_category: string
    stars: number
    language_code: string
    domain?: string
    services?: string[]
    strengths?: string[]
  }) =>
    api.post<{ kw_themes_text: string; kw_negative_text: string }>('/autofill/keywords', data).then((r) => r.data),

  suggestSitelinks: (data: {
    brand_name: string
    hotel_category: string
    stars: number
    language_code: string
    landing_page: string
    domain?: string
    services?: string[]
    strengths?: string[]
    booking_engine_url?: string
  }) =>
    api.post<{ sitelinks: { text: string; description_1: string; description_2: string; final_url: string }[] }>(
      '/autofill/sitelinks', data
    ).then((r) => r.data),

  suggestTypeCopy: (data: {
    campaign_type: 'brand' | 'acquisition' | 'retargeting'
    brand_name: string
    hotel_category: string
    stars: number
    language_code: string
    domain?: string
    usp_main?: string
    services?: string[]
    strengths?: string[]
  }) =>
    api.post<{ headlines: string[]; descriptions: string[] }>('/autofill/type-copy', data).then((r) => r.data),

  suggestBudgetStrategy: (data: {
    brand_name: string
    hotel_category: string
    stars: number
    languages: string[]
    vertical?: string
    country?: string
    total_monthly_budget_eur?: number
  }) =>
    api.post<{
      recommended_types: string[]
      budget_split: Record<string, number>
      daily_by_type_lang: Record<string, Record<string, number>>
      rationale: Record<string, string>
      overall_strategy: string
      suggested_total_monthly_eur: number
      min_budget_warning: string | null
    }>('/autofill/budget-strategy', data).then((r) => r.data),
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; user: { role: string; email: string; full_name: string } }>(
      '/auth/login',
      new URLSearchParams({ username: email, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    ).then((r) => r.data),

  me: () => api.get<{ id: string; email: string; full_name: string; role: string }>('/auth/me').then((r) => r.data),
}
