/**
 * Word (DOCX) export for the Action Plan / Preventivo.
 *
 * Design goals:
 *  - A4, 2.5 cm margins, Calibri 11 pt body
 *  - Table headers: dark background (#1F2937) + white text  — high contrast
 *  - Alternating data rows: white / very light gray (#F9FAFB)
 *  - Totale/highlight row: light pink (#FDF4F9), dark text
 *  - Explicit column widths in DXA (twips) — avoids "incomplete table" in Word
 *  - All borders defined explicitly — no missing cell borders
 */

import {
  AlignmentType,
  Document,
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

// ─── palette ──────────────────────────────────────────────────────────────────
const C = {
  dark:       '1F2937',   // section headings, body text
  white:      'FFFFFF',
  accent:     'E10098',   // pink — key numbers, step bullets
  body:       '374151',   // paragraph text
  muted:      '6B7280',   // captions
  thBg:       'E10098',   // table header background (primary pink)
  thText:     'FFFFFF',   // table header text
  rowAlt:     'F9FAFB',   // alternating row tint
  totBg:      'FDF4F9',   // totale row — light pink
  totText:    '111827',
  border:     'D1D5DB',   // table border
  labelBg:    'F3F4F6',   // label cell in detail table
  accentLight:'F9E8F4',   // section heading bar
} as const

// A4 content width at 2.5 cm margins:
// (11906 twips page − 2 × 1440 twips) = 9026 twips usable
const PAGE_W = 9026

// ─── border helpers ───────────────────────────────────────────────────────────
const BORDER = { style: 'single' as const, size: 4, color: C.border }

const tableBorders = {
  top:            BORDER,
  bottom:         BORDER,
  left:           BORDER,
  right:          BORDER,
  insideHorizontal: BORDER,
  insideVertical:   BORDER,
}

// ─── cell factories ───────────────────────────────────────────────────────────

/** Table header cell: dark bg, white bold text, centred. */
function th(
  text: string,
  widthDxa: number,
  opts: { left?: boolean } = {},
): TableCell {
  return new TableCell({
    width:         { size: widthDxa, type: WidthType.DXA },
    shading:       { fill: C.thBg, type: 'clear' },
    verticalAlign: VerticalAlign.CENTER,
    margins:       { top: 80, bottom: 80, left: 140, right: 140 },
    children: [new Paragraph({
      alignment: opts.left ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: [new TextRun({
        text, bold: true, size: 18, color: C.thText, allCaps: true,
      })],
    })],
  })
}

/** Standard data cell. */
function td(
  text: string,
  widthDxa: number,
  opts: {
    bold?:   boolean
    center?: boolean
    color?:  string
    bg?:     string
    size?:   number
    italic?: boolean
    span?:   number
  } = {},
): TableCell {
  const cell = new TableCell({
    width:         opts.span ? undefined : { size: widthDxa, type: WidthType.DXA },
    columnSpan:    opts.span,
    shading:       opts.bg ? { fill: opts.bg, type: 'solid' } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins:       { top: 80, bottom: 80, left: 140, right: 140 },
    children: [new Paragraph({
      alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({
        text,
        bold:    opts.bold,
        size:    opts.size ?? 20,
        color:   opts.color,
        italics: opts.italic,
      })],
    })],
  })
  return cell
}

// ─── paragraph helpers ────────────────────────────────────────────────────────

function p(
  text: string,
  opts: {
    bold?:        boolean
    size?:        number
    color?:       string
    italic?:      boolean
    align?:       (typeof AlignmentType)[keyof typeof AlignmentType]
    before?:      number
    after?:       number
    allCaps?:     boolean
  } = {},
): Paragraph {
  return new Paragraph({
    alignment: opts.align,
    spacing:   { before: opts.before ?? 0, after: opts.after ?? 80 },
    children: [new TextRun({
      text,
      bold:    opts.bold,
      size:    opts.size ?? 22,
      color:   opts.color,
      italics: opts.italic,
      allCaps: opts.allCaps,
    })],
  })
}

function gap(pts = 160): Paragraph {
  return new Paragraph({ spacing: { before: 0, after: pts }, children: [] })
}

/** Section heading with left pink bar (via paragraph border trick). */
function h1(title: string): Paragraph {
  return new Paragraph({
    spacing: { before: 360, after: 180 },
    border: {
      left: { style: 'single', size: 16, color: C.accent, space: 8 },
    },
    children: [new TextRun({
      text: title, bold: true, size: 28, color: C.dark,
    })],
  })
}

// ─── main export ──────────────────────────────────────────────────────────────

export async function exportToDocx(brief: Record<string, unknown>): Promise<void> {
  // ── data extraction ────────────────────────────────────────────────────────
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
    const ta = assetKey ? (firstLang[assetKey] as Record<string, unknown> | undefined) : undefined
    const hl = ta?.headlines as string[] | undefined
    if (hl?.length) return hl.slice(0, 4)
    return (firstLang.headlines as string[] | undefined)?.slice(0, 4) ?? []
  }

  const children: (Paragraph | Table)[] = []

  // ─── COVER ────────────────────────────────────────────────────────────────
  children.push(
    gap(400),
    p('Piano Strategico Google Ads', {
      size: 20, color: C.accent, allCaps: true,
      align: AlignmentType.CENTER, after: 200,
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 120 },
      children:  [new TextRun({ text: brandName, bold: true, size: 52, color: C.dark, font: 'Space Grotesk' })],
    }),
  )

  const subtitle = [category, stars > 0 ? '★'.repeat(stars) : '', address].filter(Boolean).join(' · ')
  if (subtitle) {
    children.push(p(subtitle, { size: 22, color: C.muted, align: AlignmentType.CENTER, after: 100 }))
  }
  children.push(
    p(
      `Preparato il ${today}` +
      (languages.length > 0 ? ` · Mercati: ${languages.map(l => l.code as string).join(', ')}` : ''),
      { size: 20, color: C.muted, align: AlignmentType.CENTER, after: 80 },
    ),
    p('DOCUMENTO RISERVATO — USO INTERNO E CLIENTE', {
      size: 20, color: 'AAAAAA', allCaps: true,
      align: AlignmentType.CENTER, after: 600,
    }),
  )

  // ─── 1. SCENARIO D'INVESTIMENTO ───────────────────────────────────────────
  children.push(h1('1. Scenario d\'investimento'))

  // KPI table: 2 rows × N columns (4 base + optional ROAS/CPA)
  const kpiCols: { label: string; value: string }[] = [
    { label: 'Budget mensile',    value: `€ ${Math.round(totalMonthly).toLocaleString('it-IT')}` },
    { label: 'Budget giornaliero', value: `€ ${Math.round(totalMonthly / 30.44).toLocaleString('it-IT')} / g` },
    { label: 'Campagne attive',   value: String(orderedTypes.length) },
    { label: `Lingue / Mercati`,  value: `${languages.length} (${languages.map(l => l.code as string).join(', ')})` },
  ]
  if (targetRoas) kpiCols.push({ label: 'ROAS target', value: `${targetRoas}:1` })
  if (targetCpa)  kpiCols.push({ label: 'CPA target',  value: `€ ${targetCpa}` })

  const kpiW = Math.floor(PAGE_W / kpiCols.length)
  children.push(
    new Table({
      width:   { size: PAGE_W, type: WidthType.DXA },
      borders: tableBorders,
      rows: [
        new TableRow({ children: kpiCols.map(c => th(c.label, kpiW)) }),
        new TableRow({ children: kpiCols.map(c =>
          td(c.value, kpiW, { bold: true, center: true, size: 24, color: C.accent })
        )}),
      ],
    }),
    gap(160),
    p(
      `Il piano prevede un approccio full-funnel con ${orderedTypes.length} tipologie di campagna Google Ads, ` +
      `attivate in ordine di priorità d'intento: dalla protezione del brand fino alla generazione di domanda. ` +
      `L'obiettivo primario è incrementare le prenotazioni dirette riducendo la dipendenza dalle OTA ` +
      `(Booking.com, Expedia) e migliorare il ritorno sull'investimento pubblicitario.`,
      { color: C.body, after: 0 },
    ),
  )

  // ─── 2. MIX DI CAMPAGNE ───────────────────────────────────────────────────
  children.push(h1('2. Mix di campagne consigliato'))

  // Column widths for 6-col table: #(600) | Campagna(2400) | Funnel(1200) | Budget/mese(1500) | %(1000) | Budget/g(1500) = 8200 — slightly under 9026, padded by table margins
  const MIX = { n: 600, name: 2626, funnel: 1400, budget: 1500, pct: 900, daily: 1500 }

  children.push(
    new Table({
      width:   { size: PAGE_W, type: WidthType.DXA },
      borders: tableBorders,
      rows: [
        new TableRow({
          tableHeader: true,
          children: [
            th('#',             MIX.n),
            th('Campagna',      MIX.name, { left: true }),
            th('Funnel',        MIX.funnel),
            th('Budget / mese', MIX.budget),
            th('% tot.',        MIX.pct),
            th('Budget / g',    MIX.daily),
          ],
        }),
        ...typeRows.map(({ type, monthlyAmt, pct }) => {
          const info = CAMPAIGN_STRATEGY[type]
          return new TableRow({ children: [
            td(String(info?.priority ?? '—'), MIX.n,      { center: true }),
            td(info?.label ?? type,           MIX.name,   { bold: true }),
            td(info?.funnel ?? '—',           MIX.funnel, { center: true }),
            td(`€ ${Math.round(monthlyAmt).toLocaleString('it-IT')}`, MIX.budget, { bold: true, center: true }),
            td(`${pct.toFixed(0)} %`,         MIX.pct,    { center: true }),
            td(`€ ${Math.round(monthlyAmt / 30.44).toLocaleString('it-IT')}`, MIX.daily, { center: true }),
          ]})
        }),
        // TOTALE row — colSpan 3 for first 3 cols, then 3 individual cells
        new TableRow({ children: [
          td('TOTALE', 0, { bold: true, color: C.totText, size: 22, span: 3 }),
          td(`€ ${Math.round(totalMonthly).toLocaleString('it-IT')}`, MIX.budget,
             { bold: true, center: true, color: C.accent, size: 24 }),
          td('100 %', MIX.pct,  { bold: true, center: true, color: C.totText }),
          td(`€ ${Math.round(totalMonthly / 30.44).toLocaleString('it-IT')}`, MIX.daily,
             { center: true, color: C.totText }),
        ]}),
      ],
    }),
  )

  // ─── 3. DETTAGLIO CAMPAGNE ────────────────────────────────────────────────
  children.push(h1('3. Dettaglio delle campagne'))

  const DET = { label: Math.floor(PAGE_W * 0.24), value: Math.floor(PAGE_W * 0.76) }

  orderedTypes.forEach((type, idx) => {
    const info    = CAMPAIGN_STRATEGY[type]
    const monthly = typeRows.find(r => r.type === type)?.monthlyAmt ?? 0
    const copy    = getTypeCopy(type)

    children.push(
      new Paragraph({
        spacing: { before: idx === 0 ? 0 : 280, after: 100 },
        children: [
          new TextRun({ text: `${idx + 1}. ${info?.label ?? type}`, bold: true, size: 26, color: C.dark }),
          new TextRun({ text: `   ${info?.funnel ?? ''}`, size: 20, color: C.muted }),
          new TextRun({ text: `   € ${Math.round(monthly).toLocaleString('it-IT')} / mese`, bold: true, size: 22, color: C.accent }),
        ],
      }),
    )

    if (info?.description) {
      children.push(p(info.description, { size: 21, color: C.body, after: 120 }))
    }

    children.push(
      new Table({
        width:   { size: PAGE_W, type: WidthType.DXA },
        borders: tableBorders,
        rows: [
          ['Target audience', info?.audience ?? ''],
          ['KPI & obiettivi',  info?.kpi ?? ''],
          ['Formato annunci',  info?.formats ?? ''],
          ['Investimento',     `€ ${Math.round(monthly).toLocaleString('it-IT')} / mese  ·  € ${Math.round(monthly / 30.44).toLocaleString('it-IT')} / giorno`],
        ].map(([label, value]) =>
          new TableRow({ children: [
            new TableCell({
              width:         { size: DET.label, type: WidthType.DXA },
              verticalAlign: VerticalAlign.CENTER,
              margins:       { top: 80, bottom: 80, left: 140, right: 140 },
              children: [new Paragraph({
                children: [new TextRun({ text: label, bold: true, size: 18, color: C.muted, allCaps: true })],
              })],
            }),
            new TableCell({
              width:         { size: DET.value, type: WidthType.DXA },
              verticalAlign: VerticalAlign.CENTER,
              margins:       { top: 80, bottom: 80, left: 140, right: 140 },
              children: [new Paragraph({
                children: [new TextRun({ text: value, size: 20, color: C.body })],
              })],
            }),
          ]})
        ),
      }),
    )

    if (copy.length > 0) {
      children.push(new Paragraph({
        spacing: { before: 100, after: 0 },
        children: [
          new TextRun({ text: 'Messaggi chiave:  ', bold: true, size: 19, color: C.muted, allCaps: true }),
          new TextRun({ text: copy.map(h => `"${h}"`).join('  ·  '), size: 19, italics: true, color: C.dark }),
        ],
      }))
    }
  })

  // ─── 4. MERCATI E LINGUE ──────────────────────────────────────────────────
  if (languages.length > 0) {
    children.push(h1('4. Mercati e lingue'))

    const LANG = {
      lang:  Math.floor(PAGE_W * 0.16),
      url:   Math.floor(PAGE_W * 0.24),
      hl:    Math.floor(PAGE_W * 0.34),
      bt:    Math.floor(PAGE_W * 0.26),
    }

    children.push(
      new Table({
        width:   { size: PAGE_W, type: WidthType.DXA },
        borders: tableBorders,
        rows: [
          new TableRow({
            tableHeader: true,
            children: [
              th('Lingua',               LANG.lang, { left: true }),
              th('Landing page',         LANG.url,  { left: true }),
              th('Headline campionatura', LANG.hl,  { left: true }),
              th('Brand terms',          LANG.bt,   { left: true }),
            ],
          }),
          ...languages.map((lang) => {
            const l  = lang as Record<string, unknown>
            const hl = (l.headlines   as string[] | undefined) ?? []
            const bt = (l.brand_terms as string[] | undefined) ?? []
            return new TableRow({ children: [
              td(`${l.code} — ${l.name}`, LANG.lang, { bold: true }),
              td((l.landing_page as string | undefined) || '—', LANG.url, { size: 18 }),
              td(hl.slice(0, 2).join(' · ') || '—', LANG.hl, { size: 18 }),
              td(bt.slice(0, 3).join(', ')  || '—', LANG.bt, { size: 18 }),
            ]})
          }),
        ],
      }),
    )
  }

  // ─── build & download ─────────────────────────────────────────────────────
  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: 'Space Grotesk', size: 22, color: C.dark },
        },
      },
    },
    sections: [{
      properties: {
        page: {
          size:   { width: 11906, height: 16838 }, // A4 twips
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
