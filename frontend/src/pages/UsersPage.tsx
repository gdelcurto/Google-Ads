import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi, type UserItem, type PermissionItem, type PermissionCreate } from '../api/users'
import { projectsApi } from '../api/projects'
import { T } from '../styles/theme'
import { useHeaderActions } from '../contexts/HeaderActionsContext'

// ── Styles ────────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  page: { display: 'grid', gridTemplateColumns: '280px 1fr', gap: 24, alignItems: 'start' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 },
  h1: { fontSize: 26, fontWeight: 700, color: T.text, letterSpacing: -0.5 },
  h2: { fontSize: 16, fontWeight: 700, color: T.text, marginBottom: 16 },
  btn: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '8px 16px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 13,
  },
  btnOutline: {
    background: 'transparent', color: T.text, border: `1px solid ${T.border}`,
    padding: '7px 14px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 13,
  },
  btnDanger: {
    background: 'transparent', color: T.error, border: `1px solid ${T.error}`,
    padding: '6px 12px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 12,
  },
  btnSm: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '5px 12px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 12,
  },
  card: {
    background: T.bgCard, borderRadius: T.radiusLg, padding: 20,
    boxShadow: T.shadow, border: `1px solid ${T.borderLight}`,
  },
  userRow: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 12px', borderRadius: T.radiusSm, cursor: 'pointer',
    border: `1px solid transparent`, marginBottom: 6,
  },
  userRowActive: {
    background: '#fdf0f8', border: `1px solid ${T.primary}`,
  },
  avatar: {
    width: 36, height: 36, borderRadius: '50%',
    background: T.primary, color: '#fff',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 14, fontWeight: 700, flexShrink: 0,
  },
  roleBadge: {
    display: 'inline-block', padding: '2px 8px', borderRadius: 20,
    fontSize: 11, fontWeight: 700,
  },
  permRow: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 12px', background: T.bgMuted,
    borderRadius: T.radiusSm, marginBottom: 8,
  },
  tag: {
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '2px 8px', borderRadius: 20,
    fontSize: 11, fontWeight: 700, background: '#e0f2fe', color: '#0369a1',
  },
  tagWrite: { background: '#dcfce7', color: '#166534' },
  tagAllProj: { background: '#f3e8ff', color: '#7c3aed' },
  overlay: {
    position: 'fixed' as const, inset: 0, background: 'rgba(0,0,0,0.4)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
  },
  modal: {
    background: '#fff', borderRadius: T.radiusLg, padding: 28,
    width: 560, maxWidth: '95vw', maxHeight: '90vh',
    overflowY: 'auto' as const, boxShadow: T.shadowMd,
  },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: T.textGray, marginBottom: 4 },
  input: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 14, boxSizing: 'border-box' as const,
  },
  select: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 14, background: '#fff',
  },
  formRow: { marginBottom: 14 },
  error: {
    background: '#fff0f0', border: '1px solid #fca5a5',
    padding: '8px 12px', borderRadius: T.radiusSm, fontSize: 13, color: T.error, marginBottom: 12,
  },
  tabGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginTop: 6,
  },
  checkRow: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 },
  divider: { height: 1, background: T.borderLight, margin: '16px 0' },
}

const ROLE_COLORS: Record<string, { bg: string; color: string }> = {
  admin:      { bg: '#fce7f3', color: '#be185d' },
  strategist: { bg: '#dbeafe', color: '#1d4ed8' },
  operator:   { bg: '#d1fae5', color: '#065f46' },
}

const TAB_LABELS: Record<string, string> = {
  tab_overview:    'Overview',
  tab_campaigns:   'Campagne',
  tab_preview:     'Anteprima',
  tab_brief:       'Brief',
  tab_action_plan: "Piano d'azione",
  tab_plan_json:   'Modifica Piano',
  tab_audit:       'Audit Log',
  tab_scan_log:    'Scan Log',
  tab_api_log:     'API Log',
}

const ALL_TABS = Object.keys(TAB_LABELS) as (keyof PermissionCreate)[]

// ── Helpers ───────────────────────────────────────────────────────────────────

function initPermForm(overrides?: Partial<PermissionCreate>): PermissionCreate {
  return {
    all_projects: false,
    project_id: null,
    can_read: true,
    can_write: false,
    tab_overview: true,
    tab_campaigns: true,
    tab_preview: true,
    tab_brief: true,
    tab_action_plan: true,
    tab_plan_json: true,
    tab_audit: true,
    tab_scan_log: true,
    tab_api_log: true,
    ...overrides,
  }
}

function permFromItem(p: PermissionItem): PermissionCreate {
  return {
    all_projects: p.all_projects,
    project_id: p.project_id,
    can_read: p.can_read,
    can_write: p.can_write,
    tab_overview: p.tab_overview,
    tab_campaigns: p.tab_campaigns,
    tab_preview: p.tab_preview,
    tab_brief: p.tab_brief,
    tab_action_plan: p.tab_action_plan,
    tab_plan_json: p.tab_plan_json,
    tab_audit: p.tab_audit,
    tab_scan_log: p.tab_scan_log,
    tab_api_log: p.tab_api_log,
  }
}

// ── Permission Form Modal ─────────────────────────────────────────────────────

function PermissionModal({
  userId,
  editing,
  onClose,
}: {
  userId: string
  editing: PermissionItem | null
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState<PermissionCreate>(
    editing ? permFromItem(editing) : initPermForm()
  )
  const [err, setErr] = useState('')

  const { data: projects = [] } = useQuery({
    queryKey: ['projects-list'],
    queryFn: () => projectsApi.list(),
  })

  const saveMutation = useMutation({
    mutationFn: () =>
      editing
        ? usersApi.updatePermission(userId, editing.id, form)
        : usersApi.addPermission(userId, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-permissions', userId] })
      onClose()
    },
    onError: (e: Error) => setErr(e.message),
  })

  const setTab = (key: keyof PermissionCreate, val: boolean) =>
    setForm(f => ({ ...f, [key]: val }))

  const setAllTabs = (val: boolean) => {
    const updates: Partial<PermissionCreate> = {}
    ALL_TABS.forEach(k => { updates[k] = val as never })
    setForm(f => ({ ...f, ...updates }))
  }

  return (
    <div style={s.overlay} onClick={onClose}>
      <div style={s.modal} onClick={e => e.stopPropagation()}>
        <h2 style={{ ...s.h2, marginBottom: 20 }}>
          {editing ? 'Modifica permesso' : 'Aggiungi permesso'}
        </h2>

        {err && <div style={s.error}>{err}</div>}

        {/* Scope */}
        {!editing && (
          <div style={s.formRow}>
            <label style={s.label}>Scope</label>
            <div style={{ display: 'flex', gap: 16 }}>
              <label style={s.checkRow}>
                <input
                  type="radio"
                  checked={!form.all_projects}
                  onChange={() => setForm(f => ({ ...f, all_projects: false }))}
                />
                Progetto specifico
              </label>
              <label style={s.checkRow}>
                <input
                  type="radio"
                  checked={form.all_projects}
                  onChange={() => setForm(f => ({ ...f, all_projects: true, project_id: null }))}
                />
                Tutti i progetti
              </label>
            </div>
          </div>
        )}

        {!form.all_projects && !editing && (
          <div style={s.formRow}>
            <label style={s.label}>Progetto</label>
            <select
              style={s.select}
              value={form.project_id ?? ''}
              onChange={e => setForm(f => ({ ...f, project_id: e.target.value || null }))}
            >
              <option value="">— seleziona —</option>
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.client_slug})</option>
              ))}
            </select>
          </div>
        )}

        {/* Access */}
        <div style={s.divider} />
        <div style={{ ...s.formRow, display: 'flex', gap: 24 }}>
          <label style={s.checkRow}>
            <input
              type="checkbox"
              checked={form.can_read}
              onChange={e => setForm(f => ({ ...f, can_read: e.target.checked }))}
            />
            <strong>Lettura</strong> (accesso al progetto)
          </label>
          <label style={s.checkRow}>
            <input
              type="checkbox"
              checked={form.can_write}
              onChange={e => setForm(f => ({ ...f, can_write: e.target.checked }))}
            />
            <strong>Scrittura</strong> (modifica brief, genera, pubblica)
          </label>
        </div>

        {/* Tabs */}
        <div style={s.divider} />
        <div style={{ ...s.formRow }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <label style={{ ...s.label, marginBottom: 0 }}>Tab visibili</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button style={{ ...s.btnSm, background: T.textGray, fontSize: 11 }} onClick={() => setAllTabs(true)}>
                Tutte
              </button>
              <button style={{ ...s.btnSm, background: T.textGray, fontSize: 11 }} onClick={() => setAllTabs(false)}>
                Nessuna
              </button>
            </div>
          </div>
          <div style={s.tabGrid}>
            {ALL_TABS.map(key => (
              <label key={key} style={s.checkRow}>
                <input
                  type="checkbox"
                  checked={!!form[key]}
                  onChange={e => setTab(key, e.target.checked)}
                />
                {TAB_LABELS[key]}
              </label>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 20 }}>
          <button style={s.btnOutline} onClick={onClose}>Annulla</button>
          <button style={s.btn} onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? 'Salvataggio...' : 'Salva'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── User Form Modal ───────────────────────────────────────────────────────────

function UserModal({
  editing,
  onClose,
}: {
  editing: UserItem | null
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    email: editing?.email ?? '',
    full_name: editing?.full_name ?? '',
    password: '',
    role: editing?.role ?? 'strategist',
    is_active: editing?.is_active ?? true,
  })
  const [err, setErr] = useState('')

  const saveMutation = useMutation({
    mutationFn: () =>
      editing
        ? usersApi.update(editing.id, {
            full_name: form.full_name,
            role: form.role,
            is_active: form.is_active,
            ...(form.password ? { password: form.password } : {}),
          })
        : usersApi.create({
            email: form.email,
            full_name: form.full_name,
            password: form.password,
            role: form.role,
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      onClose()
    },
    onError: (e: Error) => setErr(e.message),
  })

  return (
    <div style={s.overlay} onClick={onClose}>
      <div style={{ ...s.modal, width: 440 }} onClick={e => e.stopPropagation()}>
        <h2 style={{ ...s.h2, marginBottom: 20 }}>
          {editing ? 'Modifica utente' : 'Nuovo utente'}
        </h2>

        {err && <div style={s.error}>{err}</div>}

        {!editing && (
          <div style={s.formRow}>
            <label style={s.label}>Email</label>
            <input style={s.input} type="email" value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
          </div>
        )}

        <div style={s.formRow}>
          <label style={s.label}>Nome completo</label>
          <input style={s.input} value={form.full_name}
            onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
        </div>

        <div style={s.formRow}>
          <label style={s.label}>{editing ? 'Nuova password (lascia vuoto per non cambiare)' : 'Password'}</label>
          <input style={s.input} type="password" value={form.password}
            onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        </div>

        <div style={s.formRow}>
          <label style={s.label}>Ruolo</label>
          <select style={s.select} value={form.role}
            onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
            <option value="admin">Admin</option>
            <option value="strategist">Strategist</option>
            <option value="operator">Operator</option>
          </select>
        </div>

        {editing && (
          <div style={s.formRow}>
            <label style={s.checkRow}>
              <input type="checkbox" checked={form.is_active}
                onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
              Account attivo
            </label>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 20 }}>
          <button style={s.btnOutline} onClick={onClose}>Annulla</button>
          <button style={s.btn} onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? 'Salvataggio...' : 'Salva'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function UsersPage() {
  const qc = useQueryClient()
  const [selectedUser, setSelectedUser] = useState<UserItem | null>(null)
  const [showUserModal, setShowUserModal] = useState(false)
  const [editingUser, setEditingUser] = useState<UserItem | null>(null)
  const [showPermModal, setShowPermModal] = useState(false)
  const [editingPerm, setEditingPerm] = useState<PermissionItem | null>(null)

  useHeaderActions(
    <button style={s.btn} onClick={() => { setEditingUser(null); setShowUserModal(true) }}>
      + Nuovo utente
    </button>,
    [],
  )

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const { data: permissions = [] } = useQuery({
    queryKey: ['user-permissions', selectedUser?.id],
    queryFn: () => usersApi.listPermissions(selectedUser!.id),
    enabled: !!selectedUser,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => usersApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setSelectedUser(null)
    },
  })

  const deletePermMutation = useMutation({
    mutationFn: ({ permId }: { permId: string }) =>
      usersApi.deletePermission(selectedUser!.id, permId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-permissions', selectedUser?.id] }),
  })

  return (
    <div>
      <div style={s.header}>
        <h1 style={s.h1}>Gestione Utenti</h1>
      </div>

      {isLoading ? (
        <p style={{ color: T.textGray }}>Caricamento...</p>
      ) : (
        <div style={s.page}>
          {/* ── User list ─────────────────────────────────────────────── */}
          <div style={s.card}>
            <div style={s.h2}>Utenti ({users.length})</div>
            {users.map(u => {
              const rc = ROLE_COLORS[u.role] ?? ROLE_COLORS.operator
              const isSelected = selectedUser?.id === u.id
              return (
                <div
                  key={u.id}
                  style={{ ...s.userRow, ...(isSelected ? s.userRowActive : {}) }}
                  onClick={() => setSelectedUser(isSelected ? null : u)}
                >
                  <div style={s.avatar}>{u.full_name.charAt(0).toUpperCase()}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: T.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {u.full_name}
                      {!u.is_active && <span style={{ marginLeft: 6, fontSize: 11, color: T.error }}>(disabilitato)</span>}
                    </div>
                    <div style={{ fontSize: 11, color: T.textGray, marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{u.email}</div>
                  </div>
                  <span style={{ ...s.roleBadge, background: rc.bg, color: rc.color }}>{u.role}</span>
                </div>
              )
            })}
          </div>

          {/* ── User detail + permissions ──────────────────────────────── */}
          {selectedUser ? (
            <div>
              {/* User info card */}
              <div style={{ ...s.card, marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: T.text }}>{selectedUser.full_name}</div>
                    <div style={{ fontSize: 13, color: T.textGray, marginTop: 2 }}>{selectedUser.email}</div>
                    <div style={{ marginTop: 6 }}>
                      {(() => {
                        const rc = ROLE_COLORS[selectedUser.role] ?? ROLE_COLORS.operator
                        return <span style={{ ...s.roleBadge, background: rc.bg, color: rc.color }}>{selectedUser.role}</span>
                      })()}
                      {!selectedUser.is_active && (
                        <span style={{ marginLeft: 8, fontSize: 12, color: T.error, fontWeight: 600 }}>Account disabilitato</span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button style={s.btnOutline}
                      onClick={() => { setEditingUser(selectedUser); setShowUserModal(true) }}>
                      Modifica
                    </button>
                    <button style={s.btnDanger}
                      onClick={() => {
                        if (confirm(`Eliminare l'utente ${selectedUser.full_name}?`)) {
                          deleteMutation.mutate(selectedUser.id)
                        }
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      Elimina
                    </button>
                  </div>
                </div>
              </div>

              {/* Permissions card */}
              <div style={s.card}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div style={{ ...s.h2, marginBottom: 0 }}>Permessi progetto</div>
                  <button style={s.btnSm}
                    onClick={() => { setEditingPerm(null); setShowPermModal(true) }}>
                    + Aggiungi
                  </button>
                </div>

                {selectedUser.role === 'admin' && (
                  <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: T.radiusSm, padding: '8px 12px', fontSize: 13, color: '#166534', marginBottom: 12 }}>
                    Gli admin hanno accesso completo a tutti i progetti per impostazione predefinita.
                  </div>
                )}

                {permissions.length === 0 && selectedUser.role !== 'admin' && (
                  <div style={{ color: T.textGray, fontSize: 13, fontStyle: 'italic' }}>
                    Nessun permesso configurato — l'utente non può accedere a nessun progetto.
                  </div>
                )}

                {permissions.map(p => {
                  const enabledTabs = ALL_TABS.filter(k => p[k as keyof PermissionItem])
                  return (
                    <div key={p.id} style={s.permRow}>
                      <div style={{ flex: 1 }}>
                        {/* Scope */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 6 }}>
                          {p.all_projects ? (
                            <span style={{ ...s.tag, ...s.tagAllProj }}>Tutti i progetti</span>
                          ) : (
                            <span style={s.tag}>{p.project_name ?? p.project_id}</span>
                          )}
                          {p.can_read && <span style={{ ...s.tag, background: '#e0f2fe', color: '#0369a1' }}>Lettura</span>}
                          {p.can_write && <span style={{ ...s.tag, ...s.tagWrite }}>Scrittura</span>}
                        </div>
                        {/* Tabs */}
                        <div style={{ fontSize: 11, color: T.textGray }}>
                          Tab:{' '}
                          {enabledTabs.length === ALL_TABS.length
                            ? 'tutte'
                            : enabledTabs.length === 0
                              ? 'nessuna'
                              : enabledTabs.map(k => TAB_LABELS[k]).join(', ')}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                        <button style={s.btnSm}
                          onClick={() => { setEditingPerm(p); setShowPermModal(true) }}>
                          Modifica
                        </button>
                        <button style={{ ...s.btnDanger, padding: '5px 10px' }}
                          onClick={() => {
                            if (confirm('Eliminare questo permesso?')) {
                              deletePermMutation.mutate({ permId: p.id })
                            }
                          }}>
                          ×
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div style={{ ...s.card, color: T.textGray, fontSize: 14, fontStyle: 'italic' }}>
              Seleziona un utente per visualizzare e gestire i permessi.
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {showUserModal && (
        <UserModal
          editing={editingUser}
          onClose={() => setShowUserModal(false)}
        />
      )}
      {showPermModal && selectedUser && (
        <PermissionModal
          userId={selectedUser.id}
          editing={editingPerm}
          onClose={() => setShowPermModal(false)}
        />
      )}
    </div>
  )
}
