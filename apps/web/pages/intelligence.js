import { useState, useEffect, useRef, useMemo } from 'react'
import { useRouter } from 'next/router'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'
import iStyles from '../src/styles/Intelligence.module.css'

const DEMO_SEEDS = {
  paypal_mafia: {
    label: '🕶 PayPal Mafia',
    seeds: [
      { label: 'Peter Thiel',     entity: 'Peter Thiel',     ticker: '',      type: 'person' },
      { label: 'Elon Musk',       entity: 'Elon Musk',       ticker: 'TSLA',  type: 'person' },
      { label: 'Reid Hoffman',    entity: 'Reid Hoffman',    ticker: '',      type: 'person' },
      { label: 'Max Levchin',     entity: 'Max Levchin',     ticker: 'AFRM',  type: 'person' },
      { label: 'David Sacks',     entity: 'David Sacks',     ticker: '',      type: 'person' },
    ],
  },
  thiel_portfolio: {
    label: '🛡 Thiel / AI / Defense',
    seeds: [
      { label: 'Palantir Technologies', entity: 'Palantir Technologies', ticker: 'PLTR', type: 'org' },
      { label: 'Anduril Industries',    entity: 'Anduril Industries',    ticker: '',      type: 'org' },
      { label: 'Founders Fund',         entity: 'Founders Fund',         ticker: '',      type: 'fund' },
      { label: 'HawkEye 360',           entity: 'HawkEye 360',           ticker: '',      type: 'org' },
      { label: 'Redwire Corporation',   entity: 'Redwire Corporation',   ticker: 'RDW',   type: 'org' },
    ],
  },
}

const CONFIDENCE_COLOR = {
  DOCUMENTED: '#4ade80',
  REPORTED:   '#fbbf24',
  ANALYTICAL: '#818cf8',
}

// ── Entity name chip — clickable to generate a new report ────────────────────
function EntityChip({ name, onInvestigate }) {
  if (!name || name.length < 3) return <span>{name}</span>
  return (
    <span
      className={iStyles.entityChip}
      title={`Investigate: ${name}`}
      onClick={() => onInvestigate && onInvestigate(name)}
    >
      {name}
    </span>
  )
}

// ── Parse claim text: highlight tags + make capitalized names clickable ───────
function SmartText({ text, onInvestigate }) {
  if (!text || !onInvestigate) return <span>{text}</span>

  // Step 1 — split on bracket tags first
  const tagParts = text.split(/(\[(?:CLIENT|AS CLIENT|REGISTRANT|AS LOBBYING FIRM|DOCUMENTED|REPORTED|ANALYTICAL)[^\]]*\])/)

  return (
    <span>
      {tagParts.map((part, i) => {
        if (part.match(/^\[/)) {
          const tag = part.replace(/^\[|\]$/g, '')
          const color =
            tag.startsWith('CLIENT') || tag.startsWith('AS CLIENT') ? '#4ade80' :
            tag.startsWith('REGISTRANT') || tag.startsWith('AS LOBBYING') ? '#f97316' :
            CONFIDENCE_COLOR[tag] || '#94a3b8'
          return (
            <span key={i} style={{
              color, border: `1px solid ${color}44`, borderRadius: 4,
              padding: '1px 6px', fontSize: '0.72rem', fontWeight: 700,
              marginRight: 4, whiteSpace: 'nowrap',
            }}>
              {tag}
            </span>
          )
        }

        // Step 2 — within plain text, find capitalized multi-word entity names
        // Match: 2+ consecutive words starting with uppercase (e.g. "Peter Thiel", "Palantir Technologies")
        const nameParts = part.split(/(\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+\b)/)
        if (nameParts.length === 1) return <span key={i}>{part}</span>

        return (
          <span key={i}>
            {nameParts.map((chunk, j) => {
              if (/^[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+$/.test(chunk) && chunk.length > 4) {
                return (
                  <EntityChip key={j} name={chunk} onInvestigate={onInvestigate} />
                )
              }
              return <span key={j}>{chunk}</span>
            })}
          </span>
        )
      })}
    </span>
  )
}

function Badge({ label }) {
  const color = CONFIDENCE_COLOR[label] || '#94a3b8'
  return (
    <span style={{ color, border: `1px solid ${color}44`, borderRadius: 4,
                   padding: '1px 6px', fontSize: '0.72rem', fontWeight: 700,
                   marginRight: 4, whiteSpace: 'nowrap' }}>
      {label}
    </span>
  )
}

function ClaimRow({ text, onInvestigate }) {
  const match = text.match(/^\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*(.*)$/)
  if (match) {
    return (
      <li className={iStyles.claimRow}>
        <Badge label={match[1]} />
        <span className={iStyles.claimText}>
          <SmartText text={match[2]} onInvestigate={onInvestigate} />
        </span>
      </li>
    )
  }
  return (
    <li className={iStyles.claimRow}>
      <span className={iStyles.claimText}>
        <SmartText text={text} onInvestigate={onInvestigate} />
      </span>
    </li>
  )
}

function Section({ section, idx, onInvestigate, filters }) {
  const [open, setOpen] = useState(idx < 4)
  const claims = section.claims || []
  const isNarrative = (section.order >= 11) || section.name.toLowerCase().includes('narrative')
  const isLinkedIn   = section.name.toLowerCase().includes('linkedin')
  const isNews       = section.name.toLowerCase().includes('news')
  const isPitchBook  = section.name.toLowerCase().includes('pitchbook')
  const isLobbying   = section.name.toLowerCase().includes('lobbying')

  const category = SECTION_CATEGORY[section.name] || 'Intelligence'
  const catColor = CATEGORY_COLOR[category] || '#94a3b8'

  const sectionAccentColor =
    isLinkedIn  ? '#0a66c2' :
    isNews      ? '#f59e0b' :
    isPitchBook ? '#16a34a' :
    isLobbying  ? '#f97316' :
    catColor

  // Apply filters to claims
  const filteredClaims = useMemo(() => {
    if (!filters) return claims
    return claims.filter(c => {
      const text = (c.text || c || '').toLowerCase()
      const conf = c.confidence || ''
      const src  = (c.source || '').toLowerCase()
      if (filters.confidence !== 'All' && conf !== filters.confidence) return false
      if (filters.source !== 'All' && !src.includes(filters.source.toLowerCase())) return false
      if (filters.search && !text.includes(filters.search.toLowerCase())) return false
      return true
    })
  }, [claims, filters])

  // Apply category filter at section level
  if (filters && filters.category !== 'All' && category !== filters.category) return null

  return (
    <div className={iStyles.section} style={{ borderLeft: `3px solid ${sectionAccentColor}` }}>
      <button className={iStyles.sectionHeader} onClick={() => setOpen(o => !o)}>
        <span className={iStyles.sectionNum}>§{section.order || idx + 1}</span>
        <span className={iStyles.sectionName}>{section.name}</span>
        <span
          className={iStyles.sectionCatBadge}
          style={{ background: `${catColor}22`, color: catColor, border: `1px solid ${catColor}44` }}
        >{category}</span>
        <span className={iStyles.sectionCount}>{filteredClaims.length}/{claims.length}</span>
        {sectionAccentColor && (isLinkedIn || isNews || isPitchBook || isLobbying) && (
          <span style={{ fontSize: '0.65rem', color: sectionAccentColor, marginLeft: 4, fontWeight: 700 }}>
            {isLinkedIn ? 'LinkedIn' : isNews ? 'News' : isPitchBook ? 'PitchBook' : 'Both Sides'}
          </span>
        )}
        <span className={iStyles.chevron}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className={iStyles.sectionBody}>
          {isNarrative && filteredClaims.length > 0 ? (
            <div className={iStyles.narrative}>
              {filteredClaims[0].text.split('\n').map((line, i) => (
                <p key={i} style={{ margin: '0 0 0.65rem' }}>{line}</p>
              ))}
            </div>
          ) : (
            <SortableTable
              claims={filteredClaims}
              sectionName={section.name}
              onInvestigate={onInvestigate}
            />
          )}
          {section.data && Object.keys(section.data).length > 0 && (
            <div className={iStyles.dataRow}>
              {Object.entries(section.data).map(([k, v]) =>
                v !== null && v !== undefined && v !== '' && !Array.isArray(v) ? (
                  <span key={k} className={iStyles.dataChip}>
                    {k.replace(/_/g, ' ')}: <strong>{typeof v === 'number' ? v.toLocaleString() : String(v)}</strong>
                  </span>
                ) : null
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── KPI strip ─────────────────────────────────────────────────────────────────
function KpiStrip({ summary }) {
  if (!summary) return null
  const contractsVal = summary.kpi_contracts_value_usd
    ? `$${(summary.kpi_contracts_value_usd / 1e6).toFixed(1)}M`
    : '$0'
  const lobbySpend = summary.kpi_lobbying_spend
    ? `$${(summary.kpi_lobbying_spend / 1e3).toFixed(0)}K`
    : '$0'
  const courtRisk = summary.kpi_court_risk || 'LOW'
  const sanctionsRisk = summary.kpi_sanctions_risk || 'CLEAR'
  const confidence = summary.kpi_data_confidence ?? 0
  const sourcesActive = summary.kpi_sources_active ?? 0

  const riskColor = r => r === 'HIGH' ? '#f87171' : r === 'MEDIUM' ? '#fbbf24' : r === 'CLEAR' ? '#4ade80' : '#4ade80'

  const kpis = [
    { label: 'Gov Contracts', value: contractsVal, sub: `${summary.contracts_found || 0} awards`, color: '#60a5fa' },
    { label: 'Lobbying Spend', value: lobbySpend, sub: `${summary.lobbying_filings || 0} filings`, color: '#f97316' },
    { label: 'Court Risk', value: courtRisk, sub: `${summary.court_cases || 0} cases`, color: riskColor(courtRisk) },
    { label: 'Sanctions', value: sanctionsRisk, sub: `${summary.sanctions_hits || 0} hits`, color: riskColor(sanctionsRisk) },
    { label: 'News Coverage', value: summary.news_articles || 0, sub: 'articles found', color: '#fbbf24' },
    { label: 'Data Confidence', value: `${confidence}%`, sub: `${sourcesActive}/8 sources`, color: '#a78bfa' },
  ]

  return (
    <div className={iStyles.kpiStrip}>
      {kpis.map(k => (
        <div key={k.label} className={iStyles.kpiCard}>
          <span className={iStyles.kpiValue} style={{ color: k.color }}>{k.value}</span>
          <span className={iStyles.kpiLabel}>{k.label}</span>
          <span className={iStyles.kpiSub}>{k.sub}</span>
        </div>
      ))}
    </div>
  )
}

// ── Filter bar ────────────────────────────────────────────────────────────────
function FilterBar({ sections, filters, setFilters }) {
  const categories = ['All', 'Financial', 'Government', 'Legal', 'Intelligence', 'Social']
  const sources    = ['All', 'SEC', 'LDA', 'FEC', 'FARA', 'USASpending', 'CourtListener', 'LinkedIn', 'PitchBook', 'News', 'Wikipedia']

  return (
    <div className={iStyles.filterBar}>
      <div className={iStyles.filterGroup}>
        <span className={iStyles.filterLabel}>Category</span>
        <div className={iStyles.filterChips}>
          {categories.map(c => (
            <button
              key={c}
              className={`${iStyles.filterChip} ${filters.category === c ? iStyles.filterChipActive : ''}`}
              onClick={() => setFilters(f => ({ ...f, category: c }))}
            >{c}</button>
          ))}
        </div>
      </div>
      <div className={iStyles.filterGroup}>
        <span className={iStyles.filterLabel}>Source</span>
        <select
          className={iStyles.filterSelect}
          value={filters.source}
          onChange={e => setFilters(f => ({ ...f, source: e.target.value }))}
        >
          {sources.map(s => <option key={s}>{s}</option>)}
        </select>
      </div>
      <div className={iStyles.filterGroup}>
        <span className={iStyles.filterLabel}>Confidence</span>
        <div className={iStyles.filterChips}>
          {['All', 'DOCUMENTED', 'REPORTED', 'ANALYTICAL'].map(c => (
            <button
              key={c}
              className={`${iStyles.filterChip} ${filters.confidence === c ? iStyles.filterChipActive : ''}`}
              onClick={() => setFilters(f => ({ ...f, confidence: c }))}
            >{c}</button>
          ))}
        </div>
      </div>
      <div className={iStyles.filterGroup}>
        <span className={iStyles.filterLabel}>Search</span>
        <input
          className={iStyles.filterSearch}
          placeholder="Filter claims..."
          value={filters.search}
          onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
        />
      </div>
      {(filters.category !== 'All' || filters.source !== 'All' || filters.confidence !== 'All' || filters.search) && (
        <button
          className={iStyles.filterReset}
          onClick={() => setFilters({ category: 'All', source: 'All', confidence: 'All', search: '' })}
        >✕ Clear</button>
      )}
    </div>
  )
}

// ── Section category map ──────────────────────────────────────────────────────
const SECTION_CATEGORY = {
  'Entity Profile': 'Intelligence',
  'Investors & Capital Structure': 'Financial',
  'Government Contracts & Procurement': 'Government',
  'Lobbying Activity (Both Sides)': 'Government',
  'Political & Foreign Exposure': 'Government',
  'People & Education (LinkedIn)': 'Social',
  'Sanctions & Compliance': 'Legal',
  'Litigation & Legal Exposure': 'Legal',
  'PitchBook & Investor Intelligence': 'Financial',
  'News & Media Timeline': 'Intelligence',
  'Data Sources & Enrichment': 'Intelligence',
  'Deep Intelligence Narrative (AI-Generated)': 'Intelligence',
}

const CATEGORY_COLOR = {
  Financial:     '#34d399',
  Government:    '#60a5fa',
  Legal:         '#f87171',
  Intelligence:  '#a78bfa',
  Social:        '#f59e0b',
}

// ── Sortable table ─────────────────────────────────────────────────────────────
function SortableTable({ claims, sectionName, onInvestigate }) {
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(0)
  const PAGE = 10

  // Try to detect if claims look like tabular data (lobbying, contracts)
  const isLobbying   = sectionName?.toLowerCase().includes('lobbying')
  const isContracts  = sectionName?.toLowerCase().includes('contract')
  const isNews       = sectionName?.toLowerCase().includes('news')
  const isInvestors  = sectionName?.toLowerCase().includes('investor') || sectionName?.toLowerCase().includes('capital')

  const exportCsv = () => {
    const rows = [['#', 'Confidence', 'Text', 'Source']]
    claims.forEach((c, i) => {
      const m = (c.text || '').match(/^\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*(.*)$/)
      rows.push([i + 1, m ? m[1] : '', m ? m[2] : (c.text || ''), c.source || ''])
    })
    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
    const a = document.createElement('a')
    a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv)
    a.download = `${sectionName?.replace(/[^a-z0-9]/gi, '_')}.csv`
    a.click()
  }

  const paginated = claims.slice(page * PAGE, (page + 1) * PAGE)
  const totalPages = Math.ceil(claims.length / PAGE)

  return (
    <div>
      <div className={iStyles.tableToolbar}>
        <span className={iStyles.tableCount}>{claims.length} item{claims.length !== 1 ? 's' : ''}</span>
        <button className={iStyles.csvBtn} onClick={exportCsv} title="Export CSV">⬇ CSV</button>
      </div>
      <ul className={iStyles.claimList}>
        {paginated.map((c, i) => (
          <ClaimRow key={i} text={c.text || c} onInvestigate={onInvestigate} />
        ))}
      </ul>
      {totalPages > 1 && (
        <div className={iStyles.pagination}>
          <button className={iStyles.pageBtn} disabled={page === 0} onClick={() => setPage(p => p - 1)}>‹ Prev</button>
          <span className={iStyles.pageInfo}>{page + 1} / {totalPages}</span>
          <button className={iStyles.pageBtn} disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next ›</button>
        </div>
      )}
    </div>
  )
}

function SummaryBar({ summary }) {
  if (!summary) return null
  const items = [
    { label: 'SEC CIK',          value: summary.sec_cik || '—' },
    { label: 'Filings',          value: summary.sec_filings },
    { label: 'Contracts',        value: summary.contracts_found },
    { label: 'Obligated',        value: summary.total_obligated_usd ? `$${(summary.total_obligated_usd/1e6).toFixed(1)}M` : '$0' },
    { label: 'Lobbying (client)',value: summary.lobbying_filings },
    { label: 'Lobbying (firm)',  value: summary.lobbying_as_registrant || 0 },
    { label: 'Investors',        value: summary.investor_filings },
    { label: 'FEC PACs',         value: summary.fec_committees },
    { label: 'FARA',             value: summary.fara_registrations },
    { label: 'OFAC Hits',        value: summary.sanctions_hits },
    { label: 'Court Cases',      value: summary.court_cases },
    { label: 'News Articles',    value: summary.news_articles || 0 },
    { label: 'LinkedIn Edu',     value: summary.linkedin_education || 0 },
    { label: 'Graph Edges',      value: summary.relationships_written },
  ]
  return (
    <div className={iStyles.summaryBar}>
      {items.map(it => (
        <div key={it.label} className={iStyles.summaryCell}>
          <span className={iStyles.summaryCellVal}>{it.value ?? 0}</span>
          <span className={iStyles.summaryCellLabel}>{it.label}</span>
        </div>
      ))}
    </div>
  )
}

// ── Embedded Cytoscape graph ──────────────────────────────────────────────────
function EmbeddedGraph({ entityId, entityName, onNodeClick }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)
  const API = getApiBaseUrl()

  useEffect(() => {
    if (!entityId) return
    setLoading(true)

    fetch(`${API}/graph/export?entity_id=${entityId}&depth=2`)
      .then(r => r.json())
      .then(data => {
        if (!containerRef.current) return
        setNodeCount((data.nodes || []).length)
        setEdgeCount((data.edges || []).length)

        const initCy = () => {
          if (cyRef.current) cyRef.current.destroy()
          const elements = []
          ;(data.nodes || []).forEach(n => {
            const isMain = n.id === entityId
            elements.push({
              data: {
                id: String(n.id),
                label: n.name || String(n.id),
                kind: n.kind || 'org',
              },
              classes: isMain ? 'main-node' : '',
            })
          })
          ;(data.edges || []).forEach((e, i) => {
            elements.push({
              data: { id: `e${i}`, source: String(e.src), target: String(e.dst), label: e.kind || '' },
            })
          })
          cyRef.current = window.cytoscape({
            container: containerRef.current,
            elements,
            style: [
              {
                selector: 'node',
                style: {
                  'background-color': '#3b5998',
                  label: 'data(label)',
                  color: '#dbeafe',
                  'font-size': 9,
                  'text-wrap': 'wrap',
                  'text-max-width': 80,
                  'width': 36,
                  'height': 36,
                },
              },
              {
                selector: 'node.main-node',
                style: {
                  'background-color': '#818cf8',
                  'width': 48,
                  'height': 48,
                  'font-size': 11,
                  'font-weight': 'bold',
                  'border-width': 2,
                  'border-color': '#fff',
                },
              },
              {
                selector: 'edge',
                style: {
                  width: 1.5,
                  'line-color': '#475569',
                  'target-arrow-color': '#475569',
                  'target-arrow-shape': 'triangle',
                  label: 'data(label)',
                  'font-size': 7,
                  color: '#94a3b8',
                  'curve-style': 'bezier',
                },
              },
              {
                selector: 'node:selected',
                style: { 'background-color': '#f59e0b', 'border-width': 2, 'border-color': '#fff' },
              },
            ],
            layout: { name: 'cose', animate: false, padding: 20 },
            wheelSensitivity: 0.3,
          })
          cyRef.current.on('tap', 'node', evt => {
            const nodeName = evt.target.data('label')
            if (onNodeClick && nodeName) onNodeClick(nodeName)
          })
        }

        if (window.cytoscape) {
          initCy()
        } else {
          const script = document.createElement('script')
          script.src = 'https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js'
          script.onload = initCy
          document.body.appendChild(script)
        }
        setLoading(false)
      })
      .catch(() => setLoading(false))
    return () => { if (cyRef.current) cyRef.current.destroy() }
  }, [entityId])

  if (!entityId) return null

  const exportGraphPng = () => {
    if (!cyRef.current) return
    try {
      const png64 = cyRef.current.png({ full: true, scale: 2, bg: '#080d1a' })
      const a = document.createElement('a')
      a.href = png64
      a.download = `graph_${entityName?.replace(/[^a-z0-9]/gi,'_')}.png`
      a.click()
    } catch(e) { console.error('PNG export failed', e) }
  }

  const exportGraphJson = () => {
    if (!cyRef.current) return
    const json = {
      nodes: cyRef.current.nodes().map(n => ({ id: n.id(), label: n.data('label'), kind: n.data('kind') })),
      edges: cyRef.current.edges().map(e => ({ source: e.data('source'), target: e.data('target'), kind: e.data('label') })),
      entity: entityName,
      exported_at: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `graph_${entityName?.replace(/[^a-z0-9]/gi,'_')}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div className={iStyles.graphEmbed}>
      <div className={iStyles.graphEmbedHeader}>
        <span>🕸 Relationship Graph — {entityName}</span>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span className={iStyles.graphMeta}>{nodeCount} nodes · {edgeCount} edges · click node to investigate</span>
          <button className={iStyles.graphExportBtn} onClick={exportGraphPng} title="Export PNG">⬇ PNG</button>
          <button className={iStyles.graphExportBtn} onClick={exportGraphJson} title="Export JSON">⬇ JSON</button>
        </div>
      </div>
      {loading && <p style={{ color: 'var(--text-muted)', padding: '1rem' }}>Loading graph...</p>}
      <div
        ref={containerRef}
        style={{ width: '100%', height: 380, background: 'rgba(8,13,26,0.8)', borderRadius: 8 }}
      />
    </div>
  )
}

// ── KPI Dashboard View ────────────────────────────────────────────────────────
function KpiDashboardView({ report, onInvestigate }) {
  const s = report.summary || {}
  const sections = report.sections || []

  // Extract structured data from sections
  const contractSection = sections.find(sec => sec.name?.toLowerCase().includes('contract'))
  const lobbySection    = sections.find(sec => sec.name?.toLowerCase().includes('lobbying'))
  const legalSection    = sections.find(sec => sec.name?.toLowerCase().includes('litigation'))
  const newsSection     = sections.find(sec => sec.name?.toLowerCase().includes('news'))
  const investorSection = sections.find(sec => sec.name?.toLowerCase().includes('investor') || sec.name?.toLowerCase().includes('capital'))
  const pbSection       = sections.find(sec => sec.name?.toLowerCase().includes('pitchbook'))
  const linkedInSection = sections.find(sec => sec.name?.toLowerCase().includes('linkedin'))

  const metric = (label, value, sub, color = '#c7d2fe') => (
    <div className={iStyles.dashMetric}>
      <span className={iStyles.dashMetricVal} style={{ color }}>{value}</span>
      <span className={iStyles.dashMetricLabel}>{label}</span>
      {sub && <span className={iStyles.dashMetricSub}>{sub}</span>}
    </div>
  )

  const riskBadge = (val) => {
    const color = val === 'HIGH' ? '#f87171' : val === 'MEDIUM' ? '#fbbf24' : val === 'CLEAR' ? '#4ade80' : '#4ade80'
    return <span style={{ color, fontWeight: 800 }}>{val}</span>
  }

  const topClaims = (section, n = 4) =>
    (section?.claims || []).slice(0, n).map((c, i) => (
      <div key={i} className={iStyles.dashClaimRow}>
        <SmartText text={(c.text || c || '').replace(/^\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*/, '')} onInvestigate={onInvestigate} />
      </div>
    ))

  return (
    <div className={iStyles.dashView}>
      {/* Row 1 — headline numbers */}
      <div className={iStyles.dashRow}>
        <div className={iStyles.dashCard}>
          <div className={iStyles.dashCardTitle}>💰 Government Contracts</div>
          <div className={iStyles.dashMetricGrid}>
            {metric('Total Obligated', s.total_obligated_usd ? `$${(s.total_obligated_usd/1e6).toFixed(1)}M` : '$0', `${s.contracts_found||0} awards`, '#60a5fa')}
            {metric('Lobbying Spend', s.kpi_lobbying_spend ? `$${(s.kpi_lobbying_spend/1e3).toFixed(0)}K` : '$0', `${s.lobbying_filings||0} filings`, '#f97316')}
            {metric('Lobbying Firms', s.lobbying_firms || 0, 'as client', '#fb923c')}
            {metric('As Registrant', s.lobbying_as_registrant || 0, 'filings', '#fdba74')}
          </div>
          <div className={iStyles.dashClaimList}>{topClaims(contractSection)}</div>
        </div>

        <div className={iStyles.dashCard}>
          <div className={iStyles.dashCardTitle}>⚖️ Legal & Compliance</div>
          <div className={iStyles.dashMetricGrid}>
            {metric('Court Cases', s.court_cases || 0, 'CourtListener', '#f87171')}
            {metric('Court Risk', riskBadge(s.kpi_court_risk || 'LOW'), '', '#f87171')}
            {metric('OFAC/Sanctions', riskBadge(s.kpi_sanctions_risk || 'CLEAR'), `${s.sanctions_hits||0} hits`, '#4ade80')}
            {metric('FARA Regs', s.fara_registrations || 0, 'foreign agent', '#fb7185')}
          </div>
          <div className={iStyles.dashClaimList}>{topClaims(legalSection)}</div>
        </div>
      </div>

      {/* Row 2 — financial + media */}
      <div className={iStyles.dashRow}>
        <div className={iStyles.dashCard}>
          <div className={iStyles.dashCardTitle}>📈 Investors & Capital</div>
          <div className={iStyles.dashMetricGrid}>
            {metric('SEC Filings', s.sec_filings || 0, 'EDGAR', '#818cf8')}
            {metric('Investor Filings', s.investor_filings || 0, '13G/13D/D', '#a78bfa')}
            {metric('FEC PACs', s.fec_committees || 0, 'committees', '#c084fc')}
            {metric('Graph Edges', s.relationships_written || 0, 'mapped', '#e879f9')}
          </div>
          {pbSection && (
            <div className={iStyles.dashClaimList}>{topClaims(pbSection, 3)}</div>
          )}
          {!pbSection && <div className={iStyles.dashClaimList}>{topClaims(investorSection, 3)}</div>}
        </div>

        <div className={iStyles.dashCard}>
          <div className={iStyles.dashCardTitle}>📰 News & Intelligence</div>
          <div className={iStyles.dashMetricGrid}>
            {metric('News Articles', s.news_articles || 0, 'Google News', '#fbbf24')}
            {metric('Data Confidence', `${s.kpi_data_confidence||0}%`, `${s.kpi_sources_active||0}/8 sources`, '#34d399')}
            {linkedInSection && metric('LinkedIn Edu', s.linkedin_education || 0, 'entries', '#0a66c2')}
            {metric('SEC CIK', s.sec_cik || '—', 'EDGAR ID', '#94a3b8')}
          </div>
          <div className={iStyles.dashClaimList}>{topClaims(newsSection, 4)}</div>
        </div>
      </div>

      {/* Row 3 — lobbying issue areas */}
      {(s.lobbying_issue_areas || []).length > 0 && (
        <div className={iStyles.dashCard} style={{ gridColumn: '1/-1' }}>
          <div className={iStyles.dashCardTitle}>🏛 Lobbying Issue Areas</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.5rem' }}>
            {(s.lobbying_issue_areas || []).map((area, i) => (
              <span key={i} className={iStyles.issueTag}>{area}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function IntelligencePage() {
  const API = getApiBaseUrl()
  const router = useRouter()
  const [entityName, setEntityName] = useState('Palantir Technologies')
  const [ticker,     setTicker]     = useState('PLTR')
  const [entityType, setEntityType] = useState('org')
  const [loading,    setLoading]    = useState(false)
  const [report,     setReport]     = useState(null)
  const [err,        setErr]        = useState('')
  const [history,    setHistory]    = useState([])
  const [graphEntityId, setGraphEntityId] = useState(null)
  const [graphEntityName, setGraphEntityName] = useState('')
  const [filters, setFilters] = useState({ category: 'All', source: 'All', confidence: 'All', search: '' })
  const [viewMode, setViewMode] = useState('report') // 'report' | 'dashboard'
  const [chatOpen, setChatOpen]   = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [chatInput, setChatInput]   = useState('')
  const [chatLoading, setChatLoading] = useState(false)

  const useSeed = (seed) => {
    setEntityName(seed.entity)
    setTicker(seed.ticker)
    setEntityType(seed.type)
    setReport(null)
    setErr('')
    setGraphEntityId(null)
  }

  const investigate = (name) => {
    // Click any entity name in the report → immediately generate a new report
    setEntityName(name)
    setTicker('')
    setEntityType('org')
    setReport(null)
    setErr('')
    setGraphEntityId(null)
    setFilters({ category: 'All', source: 'All', confidence: 'All', search: '' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
    // Auto-trigger generation
    setTimeout(() => {
      const params = new URLSearchParams({ entity_name: name, entity_type: 'org' })
      setLoading(true)
      fetch(`${API}/intelligence/generate?${params}`, { method: 'POST' })
        .then(r => r.ok ? r.json() : r.text().then(t => { throw new Error(`API ${r.status}: ${t.slice(0, 200)}`) }))
        .then(data => {
          setReport(data)
          setHistory(h => [{ id: data.report_id, entity: name, ts: new Date().toLocaleTimeString() }, ...h.slice(0, 9)])
          if (data.entity_id) { setGraphEntityId(data.entity_id); setGraphEntityName(name) }
        })
        .catch(e => setErr(e.message))
        .finally(() => setLoading(false))
    }, 50)
  }

  const generate = async () => {
    if (!entityName.trim()) return
    setLoading(true); setErr(''); setReport(null); setGraphEntityId(null)
    try {
      const params = new URLSearchParams({ entity_name: entityName, entity_type: entityType })
      if (ticker) params.set('ticker', ticker)
      const r = await fetch(`${API}/intelligence/generate?${params}`, { method: 'POST' })
      if (!r.ok) {
        const txt = await r.text()
        throw new Error(`API ${r.status}: ${txt.slice(0, 200)}`)
      }
      const data = await r.json()
      setReport(data)
      setHistory(h => [{ id: data.report_id, entity: entityName, ts: new Date().toLocaleTimeString() }, ...h.slice(0, 9)])
      // Wire graph
      if (data.entity_id) {
        setGraphEntityId(data.entity_id)
        setGraphEntityName(entityName)
      }
    } catch(e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  const loadHistoric = async (id) => {
    setLoading(true); setErr('')
    try {
      const r = await fetch(`${API}/intelligence/${id}`)
      if (!r.ok) throw new Error(`API ${r.status}`)
      const data = await r.json()
      const sections = (data.sections || []).map(s => ({
        ...s,
        claims: (s.content || '').split('\n').filter(Boolean).map(t => ({ text: t })),
        data: {},
      }))
      setReport({ ...data, sections, summary: null })
      setGraphEntityId(null)
    } catch(e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  const askChat = async () => {
    if (!chatInput.trim() || !report?.report_id) return
    const question = chatInput.trim()
    setChatInput('')
    setChatHistory(h => [...h, { role: 'user', content: question }])
    setChatLoading(true)
    try {
      const r = await fetch(`${API}/chat/ask`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          report_id: report.report_id,
          question,
          history: chatHistory.slice(-6),
        }),
      })
      const data = r.ok ? await r.json() : { answer: `Error ${r.status}`, sources: [] }
      setChatHistory(h => [...h, {
        role:    'assistant',
        content: data.answer || 'No answer returned.',
        sources: (data.sources || []).slice(0, 3),
      }])
    } catch(e) {
      setChatHistory(h => [...h, { role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p style={{ margin: '0 0 0.4rem', fontSize: '0.75rem', fontWeight: 700,
                    letterSpacing: '0.08em', textTransform: 'uppercase', color: '#818cf8' }}>
          Layer 1 v1.2 — Entity Network Intelligence
        </p>
        <h1 style={{ margin: 0 }}>Intelligence Report Generator</h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', maxWidth: 640 }}>
          Enter any entity or person — runs SEC, FEC, FARA, USASpending, LDA (both sides), OFAC,
          CourtListener, Wikipedia, FundedAPI, Apify LinkedIn, Apify PitchBook, Google News —
          then builds a deep cited dossier + relationship graph + AI narrative.
        </p>
      </section>

      {/* Demo seeds */}
      {Object.values(DEMO_SEEDS).map(group => (
        <div key={group.label} className={iStyles.seedRow}>
          <span className={iStyles.seedLabel}>{group.label}:</span>
          {group.seeds.map(s => (
            <button key={s.label} className={iStyles.seedBtn} onClick={() => useSeed(s)}>
              {s.label}
            </button>
          ))}
        </div>
      ))}

      <div className={styles.grid2}>
        {/* LEFT: controls + history */}
        <aside>
          <div className={styles.panel}>
            <h2>Generate Report</h2>
            <div className={styles.controls}>
              <label className={styles.label}>
                Entity / Person Name
                <input className={styles.input} value={entityName}
                       onChange={e => setEntityName(e.target.value)}
                       placeholder="e.g. Palantir Technologies" />
              </label>
              <label className={styles.label}>
                Ticker (optional)
                <input className={styles.input} value={ticker}
                       onChange={e => setTicker(e.target.value)}
                       placeholder="e.g. PLTR" />
              </label>
              <label className={styles.label}>
                Entity Type
                <select className={styles.select} value={entityType}
                        onChange={e => setEntityType(e.target.value)}>
                  <option value="org">Organization</option>
                  <option value="person">Person</option>
                  <option value="fund">Fund / Investment Vehicle</option>
                  <option value="agency">Government Agency</option>
                </select>
              </label>
              <div className={styles.buttonRow}>
                <button className={styles.button} onClick={generate} disabled={loading}>
                  {loading ? 'Generating...' : 'Generate Intelligence Report'}
                </button>
              </div>
              {err && <p className={styles.dangerText}>{err}</p>}
              <p className={styles.subtle}>
                Runs 9–12 sections: SEC · FEC · FARA · USASpending · LDA (both sides) · OFAC ·
                CourtListener · Wikipedia · FundedAPI · LinkedIn (Apify) · PitchBook (Apify) ·
                Google News (Apify) · GPT narrative. Takes 30–90 seconds.
              </p>
            </div>
          </div>

          {history.length > 0 && (
            <div className={styles.panel} style={{ marginTop: '0.75rem' }}>
              <h3 style={{ margin: '0 0 0.6rem', fontSize: '0.9rem' }}>Recent Reports</h3>
              <ul className={styles.list}>
                {history.map((h, i) => (
                  <li key={i} className={styles.listItem}
                      style={{ cursor: 'pointer' }}
                      onClick={() => h.id && loadHistoric(h.id)}>
                    <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>{h.entity}</span>
                    <span style={{ color: 'var(--text-soft)', fontSize: '0.78rem' }}>{h.ts}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        {/* RIGHT: report viewer */}
        <section>
          {!report && !loading && (
            <div className={styles.panel}>
              <p className={styles.empty}>
                Select a demo entity above — try the <strong>PayPal Mafia</strong> group (Peter Thiel,
                Elon Musk, Reid Hoffman…) or the <strong>Thiel / AI / Defense</strong> group (Palantir, Anduril…).
                <br/><br/>
                <strong>New in v1.2:</strong> Click any highlighted entity name in the report to investigate it.
                LinkedIn education, PitchBook funding, and live news are included via Apify.
                Lobbying now shows <em>both sides</em> (as client + as lobbying firm).
              </p>
            </div>
          )}
          {loading && (
            <div className={styles.panel}>
              <p className={iStyles.loadingMsg}>
                Running connectors for <strong>{entityName}</strong>...
                <br/>SEC EDGAR · FEC · FARA · USASpending · LDA (both sides) · OFAC · CourtListener
                <br/>Wikipedia · FundedAPI · Apify LinkedIn · Apify PitchBook · Google News...
                <br/>Generating deep GPT-4o intelligence narrative (5-section format)...
                <br/><span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>~30–90 seconds</span>
              </p>
            </div>
          )}
          {report && !loading && (
            <div>
              <div className={iStyles.reportHeader}>
                <div>
                  <div className={iStyles.reportKind}>Layer 1 v1.2 — Entity Network Intelligence Report</div>
                  <h2 className={iStyles.reportTitle}>{report.entity_name || report.title}</h2>
                  <div className={iStyles.reportMeta}>
                    {report.report_id && <span>Report #{report.report_id}</span>}
                    {report.ticker && <span>Ticker: {report.ticker}</span>}
                    {report.generated_at && <span>{new Date(report.generated_at).toLocaleString()}</span>}
                    {report.data_sources && (
                      <>
                        {report.data_sources.apify_linkedin && <span className={iStyles.apifyBadge}>LinkedIn ✓</span>}
                        {report.data_sources.apify_pitchbook && <span className={iStyles.apifyBadge}>PitchBook ✓</span>}
                        {report.data_sources.apify_news > 0 && <span className={iStyles.apifyBadge}>News ({report.data_sources.apify_news}) ✓</span>}
                      </>
                    )}
                    {report.report_id && (
                      <a
                        href={`${API}/intelligence/${report.report_id}/pdf`}
                        target="_blank" rel="noopener noreferrer"
                        className={iStyles.pdfDownloadBtn}
                        title="Download PDF"
                      >⬇ PDF</a>
                    )}
                  </div>
                </div>
              </div>

              <div className={iStyles.viewToggleBar}>
                <button
                  className={`${iStyles.viewToggleBtn} ${viewMode === 'report' ? iStyles.viewToggleActive : ''}`}
                  onClick={() => setViewMode('report')}
                >📄 Full Report</button>
                <button
                  className={`${iStyles.viewToggleBtn} ${viewMode === 'dashboard' ? iStyles.viewToggleActive : ''}`}
                  onClick={() => setViewMode('dashboard')}
                >📊 KPI Dashboard</button>
              </div>

              <SummaryBar summary={report.summary} />

              {/* KPI strip */}
              <KpiStrip summary={report.summary} />

              {/* Filter bar — only in report mode */}
              {viewMode === 'report' && (
                <FilterBar
                  sections={report.sections || []}
                  filters={filters}
                  setFilters={setFilters}
                />
              )}

              {/* Embedded relationship graph */}
              {graphEntityId && (
                <EmbeddedGraph
                  entityId={graphEntityId}
                  entityName={graphEntityName}
                  onNodeClick={(name) => investigate(name)}
                />
              )}

              {/* KPI Dashboard view */}
              {viewMode === 'dashboard' && (
                <KpiDashboardView report={report} onInvestigate={investigate} />
              )}

              {viewMode === 'report' && (
              <div className={iStyles.sectionsWrap}>
                {(report.sections || []).map((s, i) => (
                  <Section key={i} section={s} idx={i} onInvestigate={investigate} filters={filters} />
                ))}
              </div>
              )}
            </div>
          )}
        </section>
      </div>

      {/* ── Floating RAG Chat Panel ─────────────────────────────────────── */}
      {report && (
        <div className={iStyles.chatFab} onClick={() => setChatOpen(o => !o)} title="Ask AI about this report">
          {chatOpen ? '✕' : '💬'}
        </div>
      )}
      {report && chatOpen && (
        <div className={iStyles.chatPanel}>
          <div className={iStyles.chatHeader}>
            <span>🤖 Ask about {report.entity_name}</span>
            <button className={iStyles.chatClose} onClick={() => setChatOpen(false)}>✕</button>
          </div>
          <div className={iStyles.chatMessages}>
            {chatHistory.length === 0 && (
              <div className={iStyles.chatEmpty}>
                Ask anything about this entity — contracts, court cases, lobbying, people, financials...
              </div>
            )}
            {chatHistory.map((msg, i) => (
              <div key={i} className={`${iStyles.chatMsg} ${msg.role === 'user' ? iStyles.chatUser : iStyles.chatBot}`}>
                <div className={iStyles.chatMsgText}>{msg.content}</div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className={iStyles.chatSources}>
                    {msg.sources.slice(0,2).map((s, j) => (
                      <span key={j} className={iStyles.chatSource}>
                        {(s.source || '')} · {(s.text || '').slice(0, 60)}…
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {chatLoading && <div className={iStyles.chatLoading}>Thinking…</div>}
          </div>
          <div className={iStyles.chatInputRow}>
            <input
              className={iStyles.chatInput}
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && askChat()}
              placeholder="Ask a question…"
              disabled={chatLoading}
            />
            <button className={iStyles.chatSend} onClick={askChat} disabled={chatLoading || !chatInput.trim()}>→</button>
          </div>
        </div>
      )}
    </main>
  )
}
