import { useState } from 'react'
import { type CampaignPreview } from '../../api/projects'
import { T } from '../../styles/theme'

const s: Record<string, React.CSSProperties> = {
  card: {
    background: T.bgCard, borderRadius: T.radiusLg, padding: 20,
    boxShadow: T.shadow, marginBottom: 12, border: `1px solid ${T.borderLight}`,
  },
  campaignName: { fontWeight: 700, fontSize: 15, color: T.text, marginBottom: 6 },
  metaRow: { display: 'flex', gap: 16, fontSize: 13, color: T.textGray, marginBottom: 8, flexWrap: 'wrap' },
  badgeGreen: {
    display: 'inline-block', padding: '2px 10px', borderRadius: 20,
    fontSize: 11, fontWeight: 700, color: '#fff', background: T.success,
  },
  badgeRed: {
    display: 'inline-block', padding: '2px 10px', borderRadius: 20,
    fontSize: 11, fontWeight: 700, color: '#fff', background: T.error,
  },
  blockers: {
    background: '#fff0f0', padding: '8px 12px',
    borderRadius: T.radiusSm, fontSize: 12, color: T.error, marginTop: 8,
  },
  adGroups: { marginTop: 10, paddingTop: 10, borderTop: `1px solid ${T.borderLight}` },
  agRow: {
    fontSize: 13, color: T.text, padding: '6px 0',
    borderBottom: `1px solid ${T.borderLight}`,
  },
}

export function CampaignCard({ campaign }: { campaign: CampaignPreview }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={s.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={s.campaignName}>{campaign.campaign_name}</div>
          <div style={s.metaRow}>
            <span>{campaign.campaign_type}</span>
            <span>Lang: {campaign.language_code}</span>
            <span>Budget: €{campaign.budget_daily_eur.toFixed(2)}/d</span>
            <span>Bid: {campaign.bid_strategy}</span>
            <span>Ad Groups: {campaign.ad_groups_count}</span>
          </div>
        </div>
        <span style={campaign.can_publish ? s.badgeGreen : s.badgeRed}>
          {campaign.can_publish ? 'Publishable' : 'Blocked'}
        </span>
      </div>

      {campaign.publish_blockers.length > 0 && (
        <div style={s.blockers}>
          <strong>Blockers:</strong>
          <ul style={{ marginLeft: 16, marginTop: 4 }}>
            {campaign.publish_blockers.map((b, i) => <li key={i}>{b}</li>)}
          </ul>
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        style={{ marginTop: 10, padding: '5px 12px', fontSize: 12, background: T.bgPage, color: T.text, border: `1px solid ${T.border}`, borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 500 }}
      >
        {expanded ? '▲ Nascondi' : '▼ Ad Groups'} ({campaign.ad_groups_count})
      </button>

      {expanded && (
        <div style={s.adGroups}>
          {campaign.ad_groups.map((ag, i) => (
            <div key={i} style={s.agRow}>
              <strong>{ag.name}</strong>
              {' · '}KW: {ag.keywords_count}
              {' · '}Ads: {ag.ads_count}
              {ag.audience_targeting.length > 0 && ` · Audience: ${ag.audience_targeting.join(', ')}`}
            </div>
          ))}
          {campaign.pmax_asset_groups.map((ag, i) => (
            <div key={`pmax-${i}`} style={{ ...s.agRow, background: T.secondary }}>
              <strong>Asset Group:</strong> {ag.name}
              {ag.has_missing_assets && <span style={{ color: '#dc2626' }}> ⚠ Asset mancanti</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
