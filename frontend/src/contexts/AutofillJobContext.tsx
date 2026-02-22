/**
 * Global context for background auto-fill job tracking.
 *
 * Why global?
 * The backend runs the job regardless of whether the user stays on the page.
 * This context polls all active jobs every 5 s from any page, saves results
 * to localStorage when they complete, and exposes toast notifications.
 *
 * localStorage keys:
 *   autofill_job_{projectId}        → active job ID (string)
 *   autofill_job_meta_{projectId}   → { projectName: string } (JSON)
 *   autofill_result_{projectId}     → completed EnrichedAutofillResult (JSON)
 *   notifications_history           → PersistedNotification[] (JSON, max 100)
 */
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { autofillApi, type EnrichedAutofillResult } from '../api/projects'

// ── localStorage helpers ────────────────────────────────────────────────────

const JOB_KEY           = (p: string) => `autofill_job_${p}`
const META_KEY          = (p: string) => `autofill_job_meta_${p}`
const RESULT_KEY        = (p: string) => `autofill_result_${p}`
const SCANLOG_KEY       = (p: string) => `autofill_scanlog_${p}`
const NOTIF_HISTORY_KEY = 'notifications_history'

function scanRunningProjectIds(): string[] {
  const ids: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('autofill_job_') && !key.startsWith('autofill_job_meta_')) {
      ids.push(key.replace('autofill_job_', ''))
    }
  }
  return ids
}

function loadStoredResults(): Record<string, EnrichedAutofillResult> {
  const out: Record<string, EnrichedAutofillResult> = {}
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('autofill_result_')) {
      const projectId = key.replace('autofill_result_', '')
      try {
        const raw = localStorage.getItem(key)
        if (raw) out[projectId] = JSON.parse(raw)
      } catch { /* ignore corrupt entries */ }
    }
  }
  return out
}

function loadPersistedNotifications(): PersistedNotification[] {
  try {
    const raw = localStorage.getItem(NOTIF_HISTORY_KEY)
    if (raw) return JSON.parse(raw) as PersistedNotification[]
  } catch { /* ignore */ }
  return []
}

function savePersistedNotifications(notifs: PersistedNotification[]) {
  // Keep at most last 100 notifications to avoid bloating localStorage.
  localStorage.setItem(NOTIF_HISTORY_KEY, JSON.stringify(notifs.slice(-100)))
}

// ── types ───────────────────────────────────────────────────────────────────

export interface AutofillNotification {
  projectId: string
  projectName: string
  brandName: string
  type: 'completed' | 'failed'
  errorMessage?: string
}

/** Persistent notification stored in localStorage history. */
export interface PersistedNotification extends AutofillNotification {
  /** Unique id: `{projectId}_{timestamp}` */
  id: string
  timestamp: number
  read: boolean
}

interface AutofillJobContextValue {
  /** Set of projectIds that currently have a running background job. */
  runningJobIds: Set<string>
  /** Map of projectId → completed result (available until clearResult is called). */
  completedResults: Record<string, EnrichedAutofillResult>
  /** Pending toast notifications (dismissed when the user closes the toast). */
  notifications: AutofillNotification[]
  /** Full notification history, persisted across sessions. */
  allNotifications: PersistedNotification[]
  /** Number of unread notifications. */
  unreadCount: number
  /** Register a newly started job so the global poller picks it up. */
  registerJob(projectId: string, jobId: string, projectName?: string): void
  /** Remove a completed result (call after the user saves the brief). */
  clearResult(projectId: string): void
  /** Dismiss a notification toast. */
  dismissNotification(projectId: string): void
  /** Mark all notifications as read. */
  markAllRead(): void
  /** Mark a single notification as read by id. */
  markRead(id: string): void
}

const AutofillJobContext = createContext<AutofillJobContextValue | null>(null)

// ── provider ────────────────────────────────────────────────────────────────

export function AutofillJobProvider({ children }: { children: React.ReactNode }) {
  const [runningJobIds, setRunningJobIds] = useState<Set<string>>(
    () => new Set(scanRunningProjectIds()),
  )
  const [completedResults, setCompletedResults] = useState<Record<string, EnrichedAutofillResult>>(
    () => loadStoredResults(),
  )
  const [notifications, setNotifications] = useState<AutofillNotification[]>([])
  const [allNotifications, setAllNotifications] = useState<PersistedNotification[]>(
    () => loadPersistedNotifications(),
  )

  // Keep a ref so the polling interval closure always sees current state.
  const runningRef = useRef(runningJobIds)
  runningRef.current = runningJobIds

  // ── public actions ─────────────────────────────────────────────────────

  const registerJob = useCallback((projectId: string, jobId: string, projectName = '') => {
    localStorage.setItem(JOB_KEY(projectId), jobId)
    if (projectName) {
      localStorage.setItem(META_KEY(projectId), JSON.stringify({ projectName }))
    }
    setRunningJobIds((prev: Set<string>) => new Set([...prev, projectId]))
  }, [])

  const clearResult = useCallback((projectId: string) => {
    localStorage.removeItem(RESULT_KEY(projectId))
    setCompletedResults((prev: Record<string, EnrichedAutofillResult>) => {
      const next = { ...prev }
      delete next[projectId]
      return next
    })
  }, [])

  const dismissNotification = useCallback((projectId: string) => {
    setNotifications((prev: AutofillNotification[]) =>
      prev.filter((n: AutofillNotification) => n.projectId !== projectId),
    )
  }, [])

  const markAllRead = useCallback(() => {
    setAllNotifications(prev => {
      const next = prev.map(n => ({ ...n, read: true }))
      savePersistedNotifications(next)
      return next
    })
  }, [])

  const markRead = useCallback((id: string) => {
    setAllNotifications(prev => {
      const next = prev.map(n => n.id === id ? { ...n, read: true } : n)
      savePersistedNotifications(next)
      return next
    })
  }, [])

  const unreadCount = allNotifications.filter(n => !n.read).length

  // ── global poller ──────────────────────────────────────────────────────

  useEffect(() => {
    const poll = async () => {
      const projectIds = Array.from(runningRef.current)
      if (projectIds.length === 0) return

      for (const projectId of projectIds) {
        const jobId = localStorage.getItem(JOB_KEY(projectId))
        if (!jobId) {
          // Key removed externally — stop tracking this project.
          setRunningJobIds((prev: Set<string>) => {
            const next = new Set(prev)
            next.delete(projectId)
            return next
          })
          continue
        }

        try {
          const status = await autofillApi.getJob(jobId)

          if (status.status === 'completed' && status.result) {
            // Persist result so it survives page navigation.
            localStorage.setItem(RESULT_KEY(projectId), JSON.stringify(status.result))
            // Persist scan log separately so it stays visible even after clearResult()
            if (status.result._scan_log) {
              localStorage.setItem(SCANLOG_KEY(projectId), JSON.stringify(status.result._scan_log))
            }
            localStorage.removeItem(JOB_KEY(projectId))

            const raw = localStorage.getItem(META_KEY(projectId))
            const meta = raw ? (JSON.parse(raw) as { projectName?: string }) : null
            const projectName = meta?.projectName ?? ''

            setCompletedResults((prev: Record<string, EnrichedAutofillResult>) => ({
              ...prev,
              [projectId]: status.result!,
            }))
            setRunningJobIds((prev: Set<string>) => {
              const next = new Set(prev)
              next.delete(projectId)
              return next
            })

            const notif: AutofillNotification = {
              projectId,
              projectName,
              brandName: status.result!.brand_name || projectName,
              type: 'completed',
            }
            // Add to persistent history.
            const persisted: PersistedNotification = {
              ...notif,
              id: `${projectId}_${Date.now()}`,
              timestamp: Date.now(),
              read: false,
            }
            setAllNotifications(prev => {
              const next = [...prev, persisted]
              savePersistedNotifications(next)
              return next
            })
            setNotifications((prev: AutofillNotification[]) => [
              ...prev.filter((n: AutofillNotification) => n.projectId !== projectId),
              notif,
            ])
          } else if (status.status === 'failed') {
            localStorage.removeItem(JOB_KEY(projectId))

            const raw = localStorage.getItem(META_KEY(projectId))
            const meta = raw ? (JSON.parse(raw) as { projectName?: string }) : null
            const projectName = meta?.projectName ?? ''

            setRunningJobIds((prev: Set<string>) => {
              const next = new Set(prev)
              next.delete(projectId)
              return next
            })

            const notif: AutofillNotification = {
              projectId,
              projectName,
              brandName: projectName,
              type: 'failed',
              errorMessage: status.error_message ?? 'errore sconosciuto',
            }
            // Add to persistent history.
            const persisted: PersistedNotification = {
              ...notif,
              id: `${projectId}_${Date.now()}`,
              timestamp: Date.now(),
              read: false,
            }
            setAllNotifications(prev => {
              const next = [...prev, persisted]
              savePersistedNotifications(next)
              return next
            })
            setNotifications((prev: AutofillNotification[]) => [
              ...prev.filter((n: AutofillNotification) => n.projectId !== projectId),
              notif,
            ])
          }
        } catch {
          // Network error — skip this cycle, retry on next tick.
        }
      }
    }

    // Poll immediately on mount, then every 5 s.
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, []) // Empty deps: runs once. Uses runningRef for current state; setters are stable.

  return (
    <AutofillJobContext.Provider
      value={{
        runningJobIds,
        completedResults,
        notifications,
        allNotifications,
        unreadCount,
        registerJob,
        clearResult,
        dismissNotification,
        markAllRead,
        markRead,
      }}
    >
      {children}
    </AutofillJobContext.Provider>
  )
}

// ── hook ────────────────────────────────────────────────────────────────────

export function useAutofillJobs() {
  const ctx = useContext(AutofillJobContext)
  if (!ctx) throw new Error('useAutofillJobs must be used within AutofillJobProvider')
  return ctx
}
