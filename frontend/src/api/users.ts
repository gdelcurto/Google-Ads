import { api } from './client'

export interface UserItem {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  email: string
  full_name: string
  password: string
  role: string
}

export interface UserUpdate {
  full_name?: string
  role?: string
  is_active?: boolean
  password?: string
}

export interface PermissionTabs {
  overview: boolean
  campaigns: boolean
  preview: boolean
  brief: boolean
  action_plan: boolean
  plan_json: boolean
  audit: boolean
  scan_log: boolean
  api_log: boolean
  budget_log: boolean
}

export interface PermissionItem {
  id: string
  user_id: string
  all_projects: boolean
  project_id: string | null
  project_name: string | null
  can_read: boolean
  can_write: boolean
  tab_overview: boolean
  tab_campaigns: boolean
  tab_preview: boolean
  tab_brief: boolean
  tab_action_plan: boolean
  tab_plan_json: boolean
  tab_audit: boolean
  tab_scan_log: boolean
  tab_api_log: boolean
  tab_budget_log: boolean
  created_at: string
  created_by: string
}

export interface PermissionCreate {
  all_projects: boolean
  project_id?: string | null
  can_read: boolean
  can_write: boolean
  tab_overview: boolean
  tab_campaigns: boolean
  tab_preview: boolean
  tab_brief: boolean
  tab_action_plan: boolean
  tab_plan_json: boolean
  tab_audit: boolean
  tab_scan_log: boolean
  tab_api_log: boolean
  tab_budget_log: boolean
}

export interface MyPermissions {
  can_read: boolean
  can_write: boolean
  tabs: PermissionTabs
}

export const DEFAULT_ALL_TABS: PermissionTabs = {
  overview: true, campaigns: true, preview: true,
  brief: true, action_plan: true, plan_json: true,
  audit: true, scan_log: true, api_log: true, budget_log: true,
}

export const usersApi = {
  list: (): Promise<UserItem[]> =>
    api.get('/users').then(r => r.data),

  create: (data: UserCreate): Promise<UserItem> =>
    api.post('/users', data).then(r => r.data),

  update: (id: string, data: UserUpdate): Promise<UserItem> =>
    api.put(`/users/${id}`, data).then(r => r.data),

  remove: (id: string): Promise<void> =>
    api.delete(`/users/${id}`).then(r => r.data),

  listPermissions: (userId: string): Promise<PermissionItem[]> =>
    api.get(`/users/${userId}/permissions`).then(r => r.data),

  addPermission: (userId: string, data: PermissionCreate): Promise<PermissionItem> =>
    api.post(`/users/${userId}/permissions`, data).then(r => r.data),

  updatePermission: (userId: string, permId: string, data: PermissionCreate): Promise<PermissionItem> =>
    api.put(`/users/${userId}/permissions/${permId}`, data).then(r => r.data),

  deletePermission: (userId: string, permId: string): Promise<void> =>
    api.delete(`/users/${userId}/permissions/${permId}`).then(r => r.data),
}

export const getMyPermissions = (projectId: string): Promise<MyPermissions> =>
  api.get(`/projects/${projectId}/my-permissions`).then(r => r.data)
