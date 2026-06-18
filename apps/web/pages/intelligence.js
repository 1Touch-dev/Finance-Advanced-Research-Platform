import { useState, useEffect, useRef } from 'react'
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

// ── Parse claim text and make capitalized names clickable ────────────────────
function SmartText({ text, onInvestigate }) {
  if (!text || !onInvestigate) return <span>{text}</span>
  // Match [CLIENT SIDE], [AS CLIENT], [REGISTRANT SIDE] tags + entity names
  const parts = text.split(/(\[(?:CLIENT|AS CLIENT|REGISTRANT|AS LOBBYING FIRM|DOCUMENTED|REPORTED|ANALYTICAL)[^\]]*\])/)
  return (
    <span>
      {parts.map((part, i) => {
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
        return <span key={i}>{part}</span>
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

function Section({ section, idx, onInvestigate }) {
  const [open, setOpen] = useState(idx < 4)
  const claims = section.claims || []
  const isNarrative = (section.order >= 11) || section.name.toLowerCase().includes('narrative')
  const isLinkedIn   = section.name.toLowerCase().includes('linkedin')
  const isNews       = section.name.toLowerCase().includes('news')
  const isPitchBook  = section.name.toLowerCase().includes('pitchbook')
  const isLobbying   = section.name.toLowerCase().includes('lobbying')

  const sectionAccentColor =
    isLinkedIn  ? '#0a66c2' :
    isNews      ? '#f59e0b' :
    isPitchBook ? '#16a34a' :
    isLobbying  ? '#f97316' :
    undefined

  return (
    <div className={iStyles.section} style={sectionAccentColor ? { borderLeft: `3px solid ${sectionAccentColor}` } : {}}>
      <button className={iStyles.sectionHeader} onClick={() => setOpen(o => !o)}>
        <span className={iStyles.sectionNum}>§{section.order || idx + 1}</span>
        <span className={iStyles.sectionName}>{section.name}</span>
        <span className={iStyles.sectionCount}>{claims.length} claim{claims.length !== 1 ? 's' : ''}</span>
        {sectionAccentColor && (
          <span style={{ fontSize: '0.65rem', color: sectionAccentColor, marginLeft: 4, fontWeight: 700 }}>
            {isLinkedIn ? 'LinkedIn' : isNews ? 'News' : isPitchBook ? 'PitchBook' : isLobbying ? 'Both Sides' : ''}
          </span>
        )}
        <span className={iStyles.chevron}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className={iStyles.sectionBody}>
          {isNarrative && claims.length > 0 ? (
            <div className={iStyles.narrative}>
              {claims[0].text.split('\n').map((line, i) => (
                <p key={i} style={{ margin: '0 0 0.65rem' }}>{line}</p>
              ))}
            </div>
          ) : (
            <ul className={iStyles.claimList}>
              {claims.map((c, i) => (
                <ClaimRow key={i} text={c.text || c} onInvestigate={onInvestigate} />
              ))}
            </ul>
          )}
          {section.data && Object.keys(section.data).length > 0 && (
            <div className={iStyles.dataRow}>
              {Object.entries(section.data).map(([k, v]) =>
                v !== null && v !== undefined && v !== '' ? (
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

  return (
    <div className={iStyles.graphEmbed}>
      <div className={iStyles.graphEmbedHeader}>
        <span>🕸 Relationship Graph — {entityName}</span>
        <span className={iStyles.graphMeta}>{nodeCount} nodes · {edgeCount} edges · click node to investigate</span>
      </div>
      {loading && <p style={{ color: 'var(--text-muted)', padding: '1rem' }}>Loading graph...</p>}
      <div
        ref={containerRef}
        style={{ width: '100%', height: 380, background: 'rgba(8,13,26,0.8)', borderRadius: 8 }}
      />
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

  const useSeed = (seed) => {
    setEntityName(seed.entity)
    setTicker(seed.ticker)
    setEntityType(seed.type)
    setReport(null)
    setErr('')
    setGraphEntityId(null)
  }

  const investigate = (name) => {
    // Click any entity name in the report → generate report for it
    setEntityName(name)
    setTicker('')
    setEntityType('org')
    setReport(null)
    setErr('')
    setGraphEntityId(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
                  </div>
                </div>
              </div>

              <SummaryBar summary={report.summary} />

              {/* Embedded relationship graph */}
              {graphEntityId && (
                <EmbeddedGraph
                  entityId={graphEntityId}
                  entityName={graphEntityName}
                  onNodeClick={(name) => investigate(name)}
                />
              )}

              <div className={iStyles.sectionsWrap}>
                {(report.sections || []).map((s, i) => (
                  <Section key={i} section={s} idx={i} onInvestigate={investigate} />
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
