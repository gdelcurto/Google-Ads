import { T } from '../../styles/theme'

interface ScanEntry { ts: string; level: 'info' | 'warn' | 'error'; msg: string }

export function ScanLogTab({ projectId }: { projectId: string }) {
  const raw = localStorage.getItem(`autofill_scanlog_${projectId}`)
  const entries: ScanEntry[] = raw ? (() => { try { return JSON.parse(raw) } catch { return [] } })() : []

  if (entries.length === 0) {
    return (
      <div style={{ padding: '40px 0', textAlign: 'center', color: T.textGray, fontSize: 14 }}>
        Nessun log disponibile. Esegui l'auto-fill del sito per vedere qui il dettaglio della scansione.
      </div>
    )
  }

  const levelColor = (l: string) =>
    l === 'error' ? T.error : l === 'warn' ? T.warning : T.textGray

  const levelBg = (l: string) =>
    l === 'error' ? '#fff1f1' : l === 'warn' ? '#fffbeb' : 'transparent'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: T.textGray }}>
          {entries.length} eventi — ultima scansione:{' '}
          {entries[0]?.ts ? new Date(entries[0].ts).toLocaleString('it-IT') : '—'}
        </div>
        <button
          style={{
            background: 'transparent', border: `1px solid ${T.border}`,
            color: T.textGray, padding: '4px 12px', borderRadius: T.radiusSm,
            cursor: 'pointer', fontSize: 12,
          }}
          onClick={() => {
            localStorage.removeItem(`autofill_scanlog_${projectId}`)
            window.location.reload()
          }}
        >
          Cancella log
        </button>
      </div>

      <div style={{
        fontFamily: 'monospace', fontSize: 12.5,
        border: `1px solid ${T.borderLight}`, borderRadius: T.radius,
        overflow: 'hidden',
      }}>
        {entries.map((e, i) => {
          if (!e.msg.trim()) {
            return <div key={i} style={{ height: 6, background: '#f9f9f9', borderTop: `1px solid ${T.borderLight}` }} />
          }
          return (
            <div
              key={i}
              style={{
                display: 'flex', gap: 12, alignItems: 'flex-start',
                padding: '5px 14px',
                background: i % 2 === 0 ? '#fff' : '#fafafa',
                borderTop: i === 0 ? 'none' : `1px solid ${T.borderLight}`,
                ...(e.level !== 'info' ? { background: levelBg(e.level) } : {}),
              }}
            >
              <span style={{ color: T.textGray, flexShrink: 0, fontSize: 11, paddingTop: 1, minWidth: 75 }}>
                {new Date(e.ts).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span style={{ color: levelColor(e.level), flex: 1, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                {e.msg}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
