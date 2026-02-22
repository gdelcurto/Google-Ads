import { useState } from 'react'
import { type CampaignPreview } from '../../api/projects'
import { GoogleAdPreview } from '../GoogleAdPreview'
import { T } from '../../styles/theme'
import { TYPE_COLOR, TYPE_LABEL } from './constants'

export function CampaignPreviewCard({
  campaign, briefLang, domain,
}: {
  campaign: CampaignPreview
  briefLang: Record<string, unknown> | undefined
  domain: string
}) {
  const [open, setOpen] = useState(false)
  const isPMax = campaign.campaign_type === 'performance_max'
  const color = TYPE_COLOR[campaign.campaign_type] || T.primary
  const label = TYPE_LABEL[campaign.campaign_type] || campaign.campaign_type

  return (
    <div style={{ border: `1px solid ${T.borderLight}`, borderRadius: T.radiusLg, marginBottom: 12, overflow: 'hidden' }}>

      {/* ── Header row (always visible) ── */}
      <div
        style={{
          padding: '12px 16px', background: T.bgMuted, cursor: 'pointer',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderBottom: open ? `1px solid ${T.borderLight}` : 'none',
        }}
        onClick={() => setOpen(o => !o)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' as const }}>
          <span style={{ background: color, color: '#fff', borderRadius: 4, fontSize: 11, padding: '2px 8px', fontWeight: 700 }}>
            {label}
          </span>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{campaign.campaign_name}</span>
          <span style={{ fontSize: 12, color: T.textGray }}>
            {campaign.language_code} · €{campaign.budget_daily_eur.toFixed(2)}/d · {campaign.bid_strategy}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          {campaign.publish_blockers.length > 0 && (
            <span style={{ fontSize: 11, color: T.error, fontWeight: 700 }}>
              {campaign.publish_blockers.length} {campaign.publish_blockers.length === 1 ? 'blocco' : 'blocchi'}
            </span>
          )}
          <span style={{ fontSize: 11, fontWeight: 700, color: campaign.can_publish ? T.success : T.error }}>
            {campaign.can_publish ? '✓ Pronta' : '✗ Bloccata'}
          </span>
          <span style={{ fontSize: 12, color: T.textGray }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* ── Expanded body ── */}
      {open && (
        <div style={{ padding: 20 }}>
          {campaign.publish_blockers.length > 0 && (
            <div style={{ background: '#fff0f0', border: '1px solid #fca5a5', borderRadius: T.radiusSm, padding: '10px 14px', marginBottom: 16, fontSize: 13, color: T.error }}>
              <strong>Blocchi:</strong>
              <ul style={{ marginLeft: 16, marginTop: 4 }}>
                {campaign.publish_blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          )}

          {isPMax ? (
            <div>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>Asset Groups</div>
              {campaign.pmax_asset_groups.length === 0
                ? <p style={{ color: T.textGray, fontSize: 13 }}>Nessun asset group trovato.</p>
                : campaign.pmax_asset_groups.map((ag, i) => (
                  <div key={i} style={{ border: `1px solid ${T.borderLight}`, borderRadius: T.radiusSm, padding: '10px 14px', marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <strong style={{ fontSize: 13 }}>📦 {ag.name}</strong>
                      <span style={{ fontSize: 11, fontWeight: 700, color: ag.has_missing_assets ? T.error : T.success }}>
                        {ag.has_missing_assets ? '⚠ Asset mancanti' : '✓ Completo'}
                      </span>
                    </div>
                    {ag.missing_asset_notes.length > 0 && (
                      <ul style={{ fontSize: 12, color: T.error, marginLeft: 16 }}>
                        {ag.missing_asset_notes.map((n, j) => <li key={j}>{n}</li>)}
                      </ul>
                    )}
                    {ag.audience_signals.length > 0 && (
                      <div style={{ fontSize: 12, color: T.textGray, marginTop: 4 }}>
                        Audience signals: {ag.audience_signals.join(', ')}
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: T.textGray, marginTop: 2 }}>
                      Headline asset: {ag.headlines_count}
                    </div>
                  </div>
                ))
              }
              {briefLang && (
                <div style={{ marginTop: 16, padding: '12px 14px', background: T.bgMuted, borderRadius: T.radiusSm, fontSize: 13 }}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>Asset testo da brief ({campaign.language_code})</div>
                  <div style={{ marginBottom: 4 }}>
                    <strong>Headline:</strong>{' '}
                    {(briefLang.headlines as string[] || []).slice(0, 3).join(' | ')}
                    {(briefLang.headlines as string[] || []).length > 3
                      ? ` +${(briefLang.headlines as string[] || []).length - 3} altri` : ''}
                  </div>
                  <div>
                    <strong>Description:</strong>{' '}
                    {(briefLang.descriptions as string[] || []).slice(0, 1).join('')}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div>
              {campaign.ad_groups.length === 0 ? (
                <div style={{ padding: 16, background: T.bgMuted, borderRadius: T.radiusSm, color: T.textGray, fontSize: 13 }}>
                  Nessun ad group trovato per questa campagna.
                </div>
              ) : (
                campaign.ad_groups.map((ag, i) => {
                  const agH = ag.rsa_headlines?.length > 0 ? ag.rsa_headlines : (briefLang?.headlines as string[] || [])
                  const agD = ag.rsa_descriptions?.length > 0 ? ag.rsa_descriptions : (briefLang?.descriptions as string[] || [])
                  const hasRsa = agH.length > 0
                  return (
                    <div key={i} style={{ marginBottom: 20 }}>
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' as const,
                        marginBottom: 10, paddingBottom: 8, borderBottom: `1px solid ${T.borderLight}`,
                      }}>
                        <span style={{ fontWeight: 700, fontSize: 13 }}>📁 {ag.name}</span>
                        <span style={{ fontSize: 11, color: T.textGray, background: T.bgMuted, padding: '2px 8px', borderRadius: 10 }}>
                          {ag.keywords_count} keyword
                        </span>
                        <span style={{ fontSize: 11, color: T.textGray, background: T.bgMuted, padding: '2px 8px', borderRadius: 10 }}>
                          {ag.ads_count} {ag.ads_count === 1 ? 'annuncio' : 'annunci'}
                        </span>
                        {ag.audience_targeting.length > 0 && (
                          <span style={{ fontSize: 11, color: T.textGray }}>Audience: {ag.audience_targeting.join(', ')}</span>
                        )}
                      </div>
                      {hasRsa ? (
                        <GoogleAdPreview
                          lang={{
                            headlines:    agH,
                            descriptions: agD,
                            callouts:     briefLang?.callouts as string[] || [],
                            sitelinks:    briefLang?.sitelinks as { text: string; description_1: string; description_2: string; final_url: string }[] || [],
                          }}
                          domain={domain}
                        />
                      ) : (
                        <div style={{ padding: '10px 14px', background: T.bgMuted, borderRadius: T.radiusSm, color: T.textGray, fontSize: 12 }}>
                          Nessun annuncio RSA per questo ad group.
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
