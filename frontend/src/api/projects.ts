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

  exportCsv: (id: string) => {
    window.open(`/api/projects/${id}/export/csv`, '_blank')
  },

  publish: (id: string, dryRun = true) =>
    api.post<Record<string, unknown>>(`/projects/${id}/publish?dry_run=${dryRun}`).then((r) => r.data),

  getAudit: (id: string) =>
    api.get<unknown[]>(`/projects/${id}/audit`).then((r) => r.data),
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
  fromUrl: (url: string, languages: string[]) =>
    api.post<AutofillResult>('/autofill', { url, languages }).then((r) => r.data),
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
