import { T } from '../../styles/theme'

interface ApiLogEntry {
  ts: string
  agent: string
  reason: string
  endpoint: string
  model: string
  input_tokens: number
  output_tokens: number
  cost_usd: number
}

export function ApiLogTab({ projectId }: { projectId: string }) {
  const raw = localStorage.getItem(`autofill_apilog_${projectId}`)
  const entries: ApiLogEntry[] = raw ? (() => { try { return JSON.parse(raw) } catch { return [] } })() : []

  if (entries.length === 0) {
    return (
      <div style={{ padding: '40px 0', textAlign: 'center', color: T.textGray, fontSize: 14 }}>
        Nessuna chiamata API registrata. Esegui l'auto-fill o usa i suggerimenti AI per vedere qui il dettaglio.
      </div>
    )
  }

  const totalCost = entries.reduce((acc, e) => acc + e.cost_usd, 0)
  const totalIn   = entries.reduce((acc, e) => acc + e.input_tokens, 0)
  const totalOut  = entries.reduce((acc, e) => acc + e.output_tokens, 0)

  const modelShort = (m: string) =>
    m.replace('claude-haiku-4-5-20251001', 'Haiku 4.5').replace('claude-sonnet-4-6', 'Sonnet 4.6')

  const modelColor = (m: string) =>
    m.includes('sonnet') ? T.primary : T.textGray

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 24, fontSize: 13, color: T.textGray, flexWrap: 'wrap' as const }}>
          <span>{entries.length} chiamate totali</span>
          <span>Token in: <strong style={{ color: T.text }}>{totalIn.toLocaleString('it-IT')}</strong></span>
          <span>Token out: <strong style={{ color: T.text }}>{totalOut.toLocaleString('it-IT')}</strong></span>
          <span>Costo tot.: <strong style={{ color: T.primary }}>${totalCost.toFixed(4)}</strong></span>
        </div>
        <button
          style={{
            background: 'transparent', border: `1px solid ${T.border}`,
            color: T.textGray, padding: '4px 12px', borderRadius: T.radiusSm,
            cursor: 'pointer', fontSize: 12,
          }}
          onClick={() => {
            localStorage.removeItem(`autofill_apilog_${projectId}`)
            window.location.reload()
          }}
        >
          Cancella log
        </button>
      </div>

      <div style={{ border: `1px solid ${T.borderLight}`, borderRadius: T.radiusLg, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: T.bgMuted }}>
              {['Ora', 'Agente', 'Motivo', 'Endpoint', 'Modello', 'Token IN', 'Token OUT', 'Costo USD'].map(h => (
                <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, fontSize: 11, color: T.textGray, whiteSpace: 'nowrap' as const }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr key={i} style={{ borderTop: `1px solid ${T.borderLight}`, background: i % 2 === 0 ? '#fff' : T.bgMuted }}>
                <td style={{ padding: '6px 12px', color: T.textGray, whiteSpace: 'nowrap' as const }}>
                  {new Date(e.ts).toLocaleTimeString('it-IT')}
                </td>
                <td style={{ padding: '6px 12px', fontWeight: 600 }}>{e.agent}</td>
                <td style={{ padding: '6px 12px', color: T.textGray, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>
                  {e.reason}
                </td>
                <td style={{ padding: '6px 12px', fontFamily: 'monospace', fontSize: 11, color: T.textGray }}>
                  {e.endpoint}
                </td>
                <td style={{ padding: '6px 12px', fontWeight: 600, color: modelColor(e.model) }}>
                  {modelShort(e.model)}
                </td>
                <td style={{ padding: '6px 12px', textAlign: 'right' }}>
                  {e.input_tokens.toLocaleString('it-IT')}
                </td>
                <td style={{ padding: '6px 12px', textAlign: 'right' }}>
                  {e.output_tokens.toLocaleString('it-IT')}
                </td>
                <td style={{ padding: '6px 12px', textAlign: 'right', fontWeight: 700, color: T.primary }}>
                  ${e.cost_usd.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
