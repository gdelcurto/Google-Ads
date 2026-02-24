/**
 * Word (DOCX) export for the Action Plan / Preventivo.
 *
 * Produces a clean A4 document with:
 *   1. Cover — hotel name, category, date
 *   2. Scenario d'investimento — KPI table + intro paragraph
 *   3. Mix di campagne — full budget allocation table
 *   4. Dettaglio campagne — one section per campaign type
 *   5. Mercati e lingue — languages table
 *   6. Prossimi passi — numbered action items
 */

import {
  AlignmentType,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  VerticalAlign,
  WidthType,
} from 'docx'
import { CAMPAIGN_STRATEGY } from './constants'

// ─── helpers ──────────────────────────────────────────────────────────────────

const PINK   = 'E10098'
const DARK   = '111111'
const GRAY   = '666666'
const LGRAY  = 'AAAAAA'
const TBGRAY = 'F2F2F2'

function para(
  text: string,
  opts: {
    bold?: boolean
    size?: number      // half-points (22 = 11pt, 28 = 14pt)
    color?: string
    italic?: boolean
    align?: (typeof AlignmentType)[keyof typeof AlignmentType]
    spaceBefore?: number
    spaceAfter?: number
    allCaps?: boolean
    heading?: (typeof HeadingLevel)[keyof typeof HeadingLevel]
  } = {},
): Paragraph {
  return new Paragraph({
    heading: opts.heading,
    alignment: opts.align,
    spacing: { before: opts.spaceBefore ?? 0, after: opts.spaceAfter ?? 80 },
    children: [
      new TextRun({
        text,
        bold: opts.bold,
        size: opts.size ?? 22,
        color: opts.color,
        italics: opts.italic,
        allCaps: opts.allCaps,
      }),
    ],
  })
}

function hCell(text: string, pct?: number): TableCell {
  return new TableCell({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, bold: true, size: 18, color: GRAY, allCaps: true })],
    })],
    width: pct != null ? { size: pct, type: WidthType.PERCENTAGE } : undefined,
    shading: { fill: TBGRAY, type: 'solid' },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
  })
}

function dCell(
  text: string,
  opts: { bold?: boolean; center?: boolean; color?: string; colSpan?: number; bg?: string } = {},
): TableCell {
  return new TableCell({
    children: [new Paragraph({
      alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text, bold: opts.bold, size: 20, color: opts.color })],
    })],
    columnSpan: opts.colSpan,
    shading: opts.bg ? { fill: opts.bg, type: 'solid' } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
  })
}

function sectionHeading(title: string): Paragraph {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 180 },
    children: [new TextRun({ text: title, bold: true, size: 30, color: DARK })],
  })
}

function divider(): Paragraph {
  return new Paragraph({ spacing: { before: 0, after: 200 }, children: [] })
}

// ─── main export ──────────────────────────────────────────────────────────────

export async function exportToDocx(brief: Record<string, unknown>): Promise<void> {
  // ── data extraction (mirrors ActionPlanTab.tsx) ────────────────────────────
  const client  = (brief.client           || {}) as Record<string, unknown>
  const hotel   = (brief.hotel_specifics  || {}) as Record<string, unknown>
  const loc     = (hotel.location         || {}) as Record<string, unknown>
  const budgets = (brief.budgets          || {}) as Record<string, unknown>
  const obj     = (brief.objectives       || {}) as Record<string, unknown>
  const kpi     = (obj.kpi               || {}) as Record<string, unknown>
  const byCT    = (budgets.by_campaign_type || {}) as Record<string, { total: number }>
  const campaignTypes = (brief.campaign_types || []) as string[]
  const languages     = (brief.languages      || []) as Record<string, unknown>[]

  const brandName    = (client.brand_name      || 'Hotel') as string
  const category     = (hotel.category         || 'Hotel') as string
  const stars        = (hotel.stars            || 0) as number
  const address      = (loc.address            || '') as string
  const totalMonthly = (budgets.total_monthly_eur || 0) as number
  const targetCpa    = kpi.target_cpa_eur as number | null
  const targetRoas   = kpi.target_roas    as number | null
  const today        = new Date().toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' })

  const orderedTypes = [...campaignTypes].sort((a, b) =>
    ((CAMPAIGN_STRATEGY[a]?.priority ?? 99) - (CAMPAIGN_STRATEGY[b]?.priority ?? 99))
  )
  const typeRows = orderedTypes.map(t => {
    const monthlyAmt = byCT[t]?.total ?? 0
    const pct = totalMonthly > 0 ? (monthlyAmt / totalMonthly) * 100 : 0
    return { type: t, monthlyAmt, pct }
  })

  const firstLang = languages[0] as Record<string, unknown> | undefined
  const getTypeCopy = (t: string): string[] => {
    if (!firstLang) return []
    const assetMap: Record<string, string> = {
      search_brand:       'brand_assets',
      search_acquisition: 'acquisition_assets',
      retargeting:        'retargeting_assets',
    }
    const assetKey = assetMap[t]
    const typeAssets = assetKey ? (firstLang[assetKey] as Record<string, unknown> | undefined) : undefined
    const typeHl = typeAssets?.headlines as string[] | undefined
    if (typeHl?.length) return typeHl.slice(0, 4)
    return (firstLang.headlines as string[] | undefined)?.slice(0, 4) ?? []
  }

  // ── document children ─────────────────────────────────────────────────────
  const children: (Paragraph | Table)[] = []

  // ─── 1. COVER ───────────────────────────────────────────────────────────────
  children.push(
    para('Piano Strategico Google Ads', {
      size: 22, color: PINK, allCaps: true, align: AlignmentType.CENTER, spaceAfter: 160,
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 100 },
      children: [new TextRun({ text: brandName, bold: true, size: 72, color: DARK })],
    }),
  )

  const subtitle = [category, stars > 0 ? '★'.repeat(stars) : '', address].filter(Boolean).join(' · ')
  if (subtitle) {
    children.push(para(subtitle, { size: 26, color: GRAY, align: AlignmentType.CENTER, spaceAfter: 80 }))
  }
  children.push(
    para(
      `Preparato il ${today}` +
      (languages.length > 0 ? ` · Mercati: ${languages.map(l => l.code as string).join(', ')}` : ''),
      { size: 20, color: GRAY, align: AlignmentType.CENTER, spaceAfter: 60 },
    ),
    para('DOCUMENTO RISERVATO — USO INTERNO E CLIENTE', {
      size: 18, color: LGRAY, allCaps: true, align: AlignmentType.CENTER, spaceAfter: 400,
    }),
  )

  // ─── 2. SCENARIO D'INVESTIMENTO ─────────────────────────────────────────────
  children.push(sectionHeading('1. Scenario d\'investimento'))

  // KPI table: 2 rows × (4 or 6) columns
  const kpiLabels = ['Budget mensile', 'Budget giornaliero', 'Campagne attive', 'Lingue / Mercati']
  const kpiValues = [
    `€${Math.round(totalMonthly).toLocaleString('it-IT')}`,
    `€${Math.round(totalMonthly / 30.44).toLocaleString('it-IT')}/g`,
    String(orderedTypes.length),
    `${languages.length} (${languages.map(l => l.code as string).join(', ')})`,
  ]
  if (targetRoas) { kpiLabels.push('ROAS target'); kpiValues.push(`${targetRoas}:1`) }
  if (targetCpa)  { kpiLabels.push('CPA target');  kpiValues.push(`€${targetCpa}`) }
  const colW = Math.floor(100 / kpiLabels.length)

  children.push(
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({ children: kpiLabels.map(l => hCell(l, colW)) }),
        new TableRow({ children: kpiValues.map(v => dCell(v, { bold: true, center: true })) }),
      ],
    }),
    divider(),
    para(
      `Il piano prevede un approccio full-funnel con ${orderedTypes.length} tipologie di campagna Google Ads, ` +
      `attivate in ordine di priorità d'intento: dalla protezione del brand fino alla generazione di domanda. ` +
      `L'obiettivo primario è incrementare le prenotazioni dirette riducendo la dipendenza dalle OTA ` +
      `(Booking.com, Expedia) e migliorare il ritorno sull'investimento pubblicitario.`,
      { size: 22, spaceAfter: 0 },
    ),
  )

  // ─── 3. MIX DI CAMPAGNE ─────────────────────────────────────────────────────
  children.push(sectionHeading('2. Mix di campagne consigliato'))
  children.push(
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({
          tableHeader: true,
          children: ['#', 'Campagna', 'Funnel', 'Budget/mese', '% tot.', 'Budget/giorno']
            .map(h => hCell(h)),
        }),
        ...typeRows.map(({ type, monthlyAmt, pct }) => {
          const info = CAMPAIGN_STRATEGY[type]
          return new TableRow({ children: [
            dCell(String(info?.priority ?? '—'), { center: true }),
            dCell(info?.label ?? type, { bold: true }),
            dCell(info?.funnel ?? '—', { center: true }),
            dCell(`€${Math.round(monthlyAmt).toLocaleString('it-IT')}`, { bold: true, center: true }),
            dCell(`${pct.toFixed(0)}%`, { center: true }),
            dCell(`€${Math.round(monthlyAmt / 30.44).toLocaleString('it-IT')}/g`, { center: true }),
          ]})
        }),
        new TableRow({ children: [
          dCell('TOTALE', { bold: true, colSpan: 3, bg: TBGRAY }),
          dCell(`€${Math.round(totalMonthly).toLocaleString('it-IT')}`, { bold: true, center: true, color: PINK, bg: TBGRAY }),
          dCell('100%', { bold: true, center: true, bg: TBGRAY }),
          dCell(`€${Math.round(totalMonthly / 30.44).toLocaleString('it-IT')}/g`, { center: true, bg: TBGRAY }),
        ]}),
      ],
    }),
  )

  // ─── 4. DETTAGLIO CAMPAGNE ───────────────────────────────────────────────────
  children.push(sectionHeading('3. Dettaglio delle campagne'))

  orderedTypes.forEach((type, idx) => {
    const info    = CAMPAIGN_STRATEGY[type]
    const monthly = typeRows.find(r => r.type === type)?.monthlyAmt ?? 0
    const copy    = getTypeCopy(type)

    children.push(
      new Paragraph({
        spacing: { before: idx === 0 ? 0 : 280, after: 100 },
        children: [
          new TextRun({ text: `${idx + 1}. ${info?.label ?? type}`, bold: true, size: 26, color: DARK }),
          new TextRun({ text: `   ${info?.funnel ?? ''}`, size: 20, color: GRAY }),
          new TextRun({ text: `   €${Math.round(monthly).toLocaleString('it-IT')}/mese`, bold: true, size: 22, color: PINK }),
        ],
      }),
    )

    if (info?.description) {
      children.push(para(info.description, { size: 21, spaceAfter: 120 }))
    }

    const detailRows: [string, string][] = [
      ['Target audience', info?.audience ?? ''],
      ['KPI & obiettivi',  info?.kpi ?? ''],
      ['Formato annunci',  info?.formats ?? ''],
      ['Investimento',     `€${Math.round(monthly).toLocaleString('it-IT')}/mese · €${Math.round(monthly / 30.44).toLocaleString('it-IT')}/giorno`],
    ]
    children.push(
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: detailRows.map(([label, value]) =>
          new TableRow({ children: [
            new TableCell({
              children: [new Paragraph({ children: [new TextRun({ text: label, bold: true, size: 18, color: GRAY, allCaps: true })] })],
              width: { size: 22, type: WidthType.PERCENTAGE },
              shading: { fill: 'F8F8F8', type: 'solid' },
              verticalAlign: VerticalAlign.CENTER,
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
            }),
            new TableCell({
              children: [new Paragraph({ children: [new TextRun({ text: value, size: 20 })] })],
              width: { size: 78, type: WidthType.PERCENTAGE },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
            }),
          ]})
        ),
      }),
    )

    if (copy.length > 0) {
      children.push(new Paragraph({
        spacing: { before: 120, after: 0 },
        children: [
          new TextRun({ text: 'Messaggi chiave: ', bold: true, size: 19, color: GRAY, allCaps: true }),
          new TextRun({ text: copy.map(h => `"${h}"`).join(' · '), size: 19, italics: true }),
        ],
      }))
    }
  })

  // ─── 5. MERCATI E LINGUE ────────────────────────────────────────────────────
  if (languages.length > 0) {
    children.push(sectionHeading('4. Mercati e lingue'))
    children.push(
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            tableHeader: true,
            children: ['Lingua', 'Landing page', 'Headline campionatura', 'Brand terms'].map(h => hCell(h)),
          }),
          ...languages.map(lang => {
            const l  = lang as Record<string, unknown>
            const hl = (l.headlines   as string[] | undefined) ?? []
            const bt = (l.brand_terms as string[] | undefined) ?? []
            return new TableRow({ children: [
              dCell(`${l.code} — ${l.name}`, { bold: true }),
              dCell((l.landing_page as string | undefined) || '—'),
              dCell(hl.slice(0, 2).join(' · ') || '—'),
              dCell(bt.slice(0, 3).join(', ')  || '—'),
            ]})
          }),
        ],
      }),
    )
  }

  // ─── 6. PROSSIMI PASSI ──────────────────────────────────────────────────────
  children.push(sectionHeading('5. Prossimi passi'))
  ;[
    { n: '01', title: 'Approvazione piano',         desc: 'Revisione e firma del preventivo da parte del cliente' },
    { n: '02', title: 'Setup account Google Ads',   desc: 'Configurazione customer ID, conversioni, tag, FLOODLIGHT' },
    { n: '03', title: 'Caricamento asset visivi',   desc: 'Immagini per Performance Max e Retargeting (se attivi)' },
    { n: '04', title: 'Attivazione Brand + Acquisition', desc: 'Prima le campagne ad alto intento, poi le altre' },
    { n: '05', title: 'Periodo di apprendimento',   desc: '4–6 settimane per ottimizzazione automatica Google' },
    { n: '06', title: 'Primo report risultati',     desc: 'Analisi KPI, ROAS e aggiustamenti strategici' },
  ].forEach(item => {
    children.push(new Paragraph({
      spacing: { before: 80, after: 80 },
      children: [
        new TextRun({ text: `${item.n}. `, bold: true, color: PINK, size: 24 }),
        new TextRun({ text: `${item.title} — `, bold: true, size: 22 }),
        new TextRun({ text: item.desc, size: 22, color: GRAY }),
      ],
    }))
  })

  children.push(
    divider(),
    para(
      `Documento generato da Google Ads Planner · ${brandName} · ${today}`,
      { size: 18, color: LGRAY, align: AlignmentType.CENTER, spaceBefore: 400, spaceAfter: 0 },
    ),
  )

  // ─── build & download ─────────────────────────────────────────────────────
  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: 'Calibri', size: 22, color: '1A1A1A' },
        },
      },
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4 in twips
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      children,
    }],
  })

  const blob = await Packer.toBlob(doc)
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `${brandName.replace(/[^a-zA-Z0-9À-ÖØ-öø-ÿ]/g, '_')}_PianoStrategico.docx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
