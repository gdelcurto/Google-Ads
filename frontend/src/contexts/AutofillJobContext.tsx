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
 */
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { autofillApi, type EnrichedAutofillResult } from '../api/projects'

// ── localStorage helpers ────────────────────────────────────────────────────

const JOB_KEY    = (p: string) => `autofill_job_${p}`
const META_KEY   = (p: string) => `autofill_job_meta_${p}`
const RESULT_KEY = (p: string) => `autofill_result_${p}`

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

// ── types ───────────────────────────────────────────────────────────────────

export interface AutofillNotification {
  projectId: string
  projectName: string
  brandName: string
  type: 'completed' | 'failed'
  errorMessage?: string
}

interface AutofillJobContextValue {
  /** Set of projectIds that currently have a running background job. */
  runningJobIds: Set<string>
  /** Map of projectId → completed result (available until clearResult is called). */
  completedResults: Record<string, EnrichedAutofillResult>
  /** Pending toast notifications. */
  notifications: AutofillNotification[]
  /** Register a newly started job so the global poller picks it up. */
  registerJob(projectId: string, jobId: string, projectName?: string): void
  /** Remove a completed result (call after the user saves the brief). */
  clearResult(projectId: string): void
  /** Dismiss a notification toast. */
  dismissNotification(projectId: string): void
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
            setNotifications((prev: AutofillNotification[]) => [
              ...prev.filter((n: AutofillNotification) => n.projectId !== projectId),
              {
                projectId,
                projectName,
                brandName: status.result!.brand_name || projectName,
                type: 'completed' as const,
              },
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
            setNotifications((prev: AutofillNotification[]) => [
              ...prev.filter((n: AutofillNotification) => n.projectId !== projectId),
              {
                projectId,
                projectName,
                brandName: projectName,
                type: 'failed' as const,
                errorMessage: status.error_message ?? 'errore sconosciuto',
              },
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
  }, []) // Empty deps: runs once. Uses runningRef for current state.

  return (
    <AutofillJobContext.Provider
      value={{ runningJobIds, completedResults, notifications, registerJob, clearResult, dismissNotification }}
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
