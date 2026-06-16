import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'
import iStyles from '../src/styles/Intelligence.module.css'

const DEMO_SEEDS = [
  { label: 'Palantir Technologies', entity: 'Palantir Technologies', ticker: 'PLTR', type: 'org' },
  { label: 'Anduril Industries',    entity: 'Anduril Industries',    ticker: '',      type: 'org' },
  { label: 'Peter Thiel',           entity: 'Peter Thiel',           ticker: '',      type: 'person' },
  { label: 'Founders Fund',         entity: 'Founders Fund',         ticker: '',      type: 'fund' },
  { label: 'HawkEye 360',           entity: 'HawkEye 360',           ticker: '',      type: 'org' },
  { label: 'Redwire Corporation',   entity: 'Redwire Corporation',   ticker: 'RDW',   type: 'org' },
]

const CONFIDENCE_COLOR = {
  DOCUMENTED: '#4ade80',
  REPORTED:   '#fbbf24',
  ANALYTICAL: '#818cf8',
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

function ClaimRow({ text }) {
  const match = text.match(/^\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*(.*)$/)
  if (match) {
    return (
      <li className={iStyles.claimRow}>
        <Badge label={match[1]} />
        <span className={iStyles.claimText}>{match[2]}</span>
      </li>
    )
  }
  return <li className={iStyles.claimRow}><span className={iStyles.claimText}>{text}</span></li>
}

function Section({ section, idx }) {
  const [open, setOpen] = useState(idx < 3)
  const claims = section.claims || []
  const isNarrative = section.order === 7 || section.name.toLowerCase().includes('narrative')
  return (
    <div className={iStyles.section}>
      <button className={iStyles.sectionHeader} onClick={() => setOpen(o => !o)}>
        <span className={iStyles.sectionNum}>§{section.order || idx + 1}</span>
        <span className={iStyles.sectionName}>{section.name}</span>
        <span className={iStyles.sectionCount}>{claims.length} claim{claims.length !== 1 ? 's' : ''}</span>
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
              {claims.map((c, i) => <ClaimRow key={i} text={c.text || c} />)}
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
    { label: 'SEC CIK',      value: summary.sec_cik || '—' },
    { label: 'SEC Filings',  value: summary.sec_filings },
    { label: 'Contracts',    value: summary.contracts_found },
    { label: 'Obligated',    value: summary.total_obligated_usd ? `$${(summary.total_obligated_usd/1e6).toFixed(1)}M` : '$0' },
    { label: 'FEC PACs',     value: summary.fec_committees },
    { label: 'Lobbying',     value: summary.lobbying_filings },
    { label: 'FARA',         value: summary.fara_registrations },
    { label: 'OFAC Hits',    value: summary.sanctions_hits },
    { label: 'Court Cases',  value: summary.court_cases },
    { label: 'Graph Edges',  value: summary.relationships_written },
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

export default function IntelligencePage() {
  const API = getApiBaseUrl()
  const [entityName, setEntityName] = useState('Palantir Technologies')
  const [ticker,     setTicker]     = useState('PLTR')
  const [entityType, setEntityType] = useState('org')
  const [loading,    setLoading]    = useState(false)
  const [report,     setReport]     = useState(null)
  const [err,        setErr]        = useState('')
  const [history,    setHistory]    = useState([])

  const useSeed = (seed) => {
    setEntityName(seed.entity)
    setTicker(seed.ticker)
    setEntityType(seed.type)
    setReport(null)
    setErr('')
  }

  const generate = async () => {
    if (!entityName.trim()) return
    setLoading(true); setErr(''); setReport(null)
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
      // reconstruct sections from DB content
      const sections = (data.sections || []).map(s => ({
        ...s,
        claims: (s.content || '').split('\n').filter(Boolean).map(t => ({ text: t })),
        data: {},
      }))
      setReport({ ...data, sections, summary: null })
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
          Layer 1 — Entity Network Intelligence
        </p>
        <h1 style={{ margin: 0 }}>Intelligence Report Generator</h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', maxWidth: 72 }}>
          Enter any entity or person to generate a cited dossier: SEC filings, government contracts,
          FEC, lobbying (LDA), FARA, sanctions (OFAC), litigation — plus a GPT-4o narrative grounded
          only in the evidence retrieved.
        </p>
      </section>

      {/* Demo seeds */}
      <div className={iStyles.seedRow}>
        <span className={iStyles.seedLabel}>Thiel / Tech / AI / Defense demo:</span>
        {DEMO_SEEDS.map(s => (
          <button key={s.label} className={iStyles.seedBtn} onClick={() => useSeed(s)}>
            {s.label}
          </button>
        ))}
      </div>

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
                Runs all federal connectors live: SEC, FEC, FARA, USASpending, LDA, OFAC, CourtListener.
                Takes 10–30 seconds.
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
                Select a demo entity above or enter any name, then click Generate.
                The report will appear here with 7 cited sections.
              </p>
            </div>
          )}
          {loading && (
            <div className={styles.panel}>
              <p className={iStyles.loadingMsg}>
                Running connectors for <strong>{entityName}</strong>...
                <br/>SEC EDGAR — FEC — FARA — USASpending — LDA — OFAC — CourtListener
                <br/>Generating GPT-4o narrative...
              </p>
            </div>
          )}
          {report && !loading && (
            <div>
              <div className={iStyles.reportHeader}>
                <div>
                  <div className={iStyles.reportKind}>Layer 1 Entity Network Intelligence Report</div>
                  <h2 className={iStyles.reportTitle}>{report.entity_name || report.title}</h2>
                  <div className={iStyles.reportMeta}>
                    {report.report_id && <span>Report #{report.report_id}</span>}
                    {report.ticker && <span>Ticker: {report.ticker}</span>}
                    {report.generated_at && <span>{new Date(report.generated_at).toLocaleString()}</span>}
                  </div>
                </div>
              </div>

              <SummaryBar summary={report.summary} />

              <div className={iStyles.sectionsWrap}>
                {(report.sections || []).map((s, i) => (
                  <Section key={i} section={s} idx={i} />
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
