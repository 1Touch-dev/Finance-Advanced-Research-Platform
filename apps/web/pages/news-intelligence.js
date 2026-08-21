import { useState } from 'react'
import useSWR from 'swr'
import Head from 'next/head'
import styles from '../src/styles/Page.module.css'
import { getApiBaseUrl } from '../lib/api'

const API = getApiBaseUrl()
const fetcher = url => fetch(url).then(r => r.json())

const FRAMING_COLOR = {
  bullish: { bg: 'rgba(74,222,128,0.12)', border: 'rgba(74,222,128,0.3)', text: '#4ade80' },
  bearish: { bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)', text: '#f87171' },
  neutral: { bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.3)', text: '#94a3b8' },
}

function StatusPill({ status }) {
  const map = {
    enriched: { bg: 'rgba(74,222,128,0.15)', text: '#4ade80', label: 'Enriched' },
    skipped_single_source: { bg: 'rgba(148,163,184,0.15)', text: '#94a3b8', label: 'Single source' },
    failed: { bg: 'rgba(248,113,113,0.15)', text: '#f87171', label: 'Failed' },
    pending: { bg: 'rgba(251,191,36,0.15)', text: '#fbbf24', label: 'Pending' },
  }
  const s = map[status] || map.pending
  return (
    <span style={{ background: s.bg, color: s.text, borderRadius: 6, padding: '0.15rem 0.5rem', fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.03em', textTransform: 'uppercase' }}>
      {s.label}
    </span>
  )
}

function EventCard({ event }) {
  const [expanded, setExpanded] = useState(false)
  const facts = event.confirmed_facts || []
  const claims = event.unconfirmed_claims || []
  const conflicts = event.conflicts || []
  const perspectives = event.perspectives || []

  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 10, background: 'rgba(14,20,37,0.86)', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem' }}>
        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', lineHeight: 1.35 }}>{event.headline}</div>
        <StatusPill status={event.enrichment_status} />
      </div>

      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
        <span>📰 {event.source_count} source{event.source_count === 1 ? '' : 's'}</span>
        {event.topic_entity && <span>· 🏷 {event.topic_entity}</span>}
        <span>· {event.updated_at ? new Date(event.updated_at.replace(' ', 'T') + 'Z').toLocaleString() : ''}</span>
      </div>

      {conflicts.length > 0 && (
        <div style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.3)', borderRadius: 8, padding: '0.6rem 0.75rem' }}>
          <div style={{ fontSize: '0.72rem', color: '#fbbf24', fontWeight: 700, marginBottom: '0.35rem' }}>⚠ {conflicts.length} CROSS-SOURCE CONFLICT{conflicts.length > 1 ? 'S' : ''}</div>
          {conflicts.map((c, i) => (
            <div key={i} style={{ fontSize: '0.8rem', color: '#e2e8f0', marginBottom: '0.3rem' }}>
              <div><span style={{ color: '#818cf8' }}>{c.source_a}:</span> {c.claim_a}</div>
              <div><span style={{ color: '#f472b6' }}>{c.source_b}:</span> {c.claim_b}</div>
              {c.note && <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>{c.note}</div>}
            </div>
          ))}
        </div>
      )}

      {perspectives.length > 0 && (
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {perspectives.map((p, i) => {
            const c = FRAMING_COLOR[p.framing] || FRAMING_COLOR.neutral
            return (
              <span key={i} title={p.notes || ''} style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text, borderRadius: 6, padding: '0.2rem 0.55rem', fontSize: '0.72rem', fontWeight: 600 }}>
                {p.source}: {p.framing}
              </span>
            )
          })}
        </div>
      )}

      <button onClick={() => setExpanded(x => !x)}
        style={{ alignSelf: 'flex-start', background: 'transparent', border: '1px solid var(--line)', borderRadius: 6, color: '#c7d2fe', padding: '0.3rem 0.6rem', fontSize: '0.75rem', cursor: 'pointer' }}>
        {expanded ? '▲ Hide details' : `▼ Facts (${facts.length}) & Claims (${claims.length})`}
      </button>

      {expanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {facts.length > 0 && (
            <div>
              <div style={{ fontSize: '0.72rem', color: '#4ade80', fontWeight: 700, marginBottom: '0.3rem' }}>✓ CONFIRMED FACTS</div>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {facts.map((f, i) => (
                  <li key={i} style={{ fontSize: '0.82rem', color: '#e2e8f0' }}>
                    {f.fact} <span style={{ color: 'var(--text-muted)' }}>— {(f.sources || []).join(', ')}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {claims.length > 0 && (
            <div>
              <div style={{ fontSize: '0.72rem', color: '#fbbf24', fontWeight: 700, marginBottom: '0.3rem' }}>? UNCONFIRMED CLAIMS</div>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {claims.map((c, i) => (
                  <li key={i} style={{ fontSize: '0.82rem', color: '#e2e8f0' }}>
                    {c.claim} <span style={{ color: 'var(--text-muted)' }}>— {c.source}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            {(event.sources || []).map((s, i) => (
              <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.78rem', color: '#818cf8', textDecoration: 'none' }}>
                [{s.source_name}] {s.title}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function NewsIntelligencePage() {
  const [hours, setHours] = useState(48)
  const [maxEvents, setMaxEvents] = useState(15)
  const [minSources, setMinSources] = useState(1)
  const [usFinanceOnly, setUsFinanceOnly] = useState(true)
  const [running, setRunning] = useState(false)
  const [jobStatus, setJobStatus] = useState(null)
  const [minSourcesFilter, setMinSourcesFilter] = useState(0)

  const { data, mutate, isLoading } = useSWR(
    `${API}/market/rss/events?limit=50${minSourcesFilter ? `&min_sources=${minSourcesFilter}` : ''}&us_finance_only=${usFinanceOnly}`,
    fetcher,
    { refreshInterval: 0 }
  )
  const events = data?.events || []

  const runPipeline = async () => {
    setRunning(true)
    setJobStatus({ status: 'started', message: 'Clustering recent RSS articles…' })
    try {
      const start = await fetch(
        `${API}/market/rss/events/run?hours=${hours}&max_events=${maxEvents}&min_sources=${minSources}&us_finance_only=${usFinanceOnly}`,
        { method: 'POST' }
      )
      const started = await start.json()
      if (!start.ok) {
        setJobStatus({ status: 'failed', error: started.detail || `HTTP ${start.status}` })
        return
      }
      const jobId = started.job_id
      const MAX_POLLS = 90 // ~7.5 min budget at 5s/poll — GPT-4o enrichment per event
      for (let i = 0; i < MAX_POLLS; i++) {
        await new Promise(r => setTimeout(r, 5000))
        let data
        try {
          const pr = await fetch(`${API}/market/rss/events/job/${jobId}`)
          data = await pr.json()
        } catch {
          continue
        }
        if (data.status === 'completed' || data.status === 'failed') {
          setJobStatus(data)
          mutate()
          setRunning(false)
          return
        }
        setJobStatus({ status: 'running', message: `Clustering + enriching… (${Math.round((i + 1) * 5 / 60)}m elapsed)` })
      }
      setJobStatus({ status: 'failed', error: 'Timed out after ~7.5 minutes — check API logs.' })
    } catch (e) {
      setJobStatus({ status: 'failed', error: e.message })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className={styles.page}>
      <Head><title>Event Intelligence — RSS Phase 2</title></Head>

      <div className={styles.hero}>
        <h1>📡 Event Intelligence</h1>
        <p>
          Clusters US stock-market news into events, then uses GPT-4o to extract confirmed
          facts vs. unconfirmed claims, flag cross-source contradictions, and label each article's
          framing — James's "500-source" deep RSS vision (F-08 Phase 2). Scoped to finance, macro,
          and government sources (stocks, earnings, Fed/Treasury/SEC policy) by default.
        </p>
      </div>

      <div className={styles.panel}>
        <h2>Generate Briefings</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label className={styles.label}>
            Lookback window
            <select className={styles.input} value={hours} onChange={e => setHours(Number(e.target.value))} disabled={running}>
              <option value={12}>12 hours</option>
              <option value={24}>24 hours</option>
              <option value={48}>48 hours</option>
              <option value={72}>72 hours</option>
            </select>
          </label>
          <label className={styles.label}>
            Max events / run
            <select className={styles.input} value={maxEvents} onChange={e => setMaxEvents(Number(e.target.value))} disabled={running}>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={25}>25</option>
            </select>
          </label>
          <label className={styles.label}>
            Enrich clusters with ≥
            <select className={styles.input} value={minSources} onChange={e => setMinSources(Number(e.target.value))} disabled={running}>
              <option value={1}>1 source (everything)</option>
              <option value={2}>2 sources (multi-source only)</option>
              <option value={3}>3 sources</option>
            </select>
          </label>
          <label className={styles.label}>
            Scope
            <select className={styles.input} value={usFinanceOnly ? '1' : '0'} onChange={e => setUsFinanceOnly(e.target.value === '1')} disabled={running}>
              <option value="1">🇺🇸 US finance/stocks only</option>
              <option value="0">🌐 All 50 sources (global)</option>
            </select>
          </label>
          <button onClick={runPipeline} disabled={running}
            style={{ background: running ? 'rgba(129,140,248,0.15)' : 'linear-gradient(135deg,#818cf8,#6366f1)',
              color: running ? '#94a3b8' : '#fff', border: 'none', borderRadius: 8,
              padding: '0.55rem 1.1rem', fontSize: '0.85rem', fontWeight: 700, cursor: running ? 'not-allowed' : 'pointer' }}>
            {running ? '⏳ Running…' : '▶ Generate Briefings'}
          </button>
        </div>

        {jobStatus && (
          <div style={{ marginTop: '0.75rem', fontSize: '0.82rem',
            color: jobStatus.status === 'failed' ? '#f87171' : jobStatus.status === 'completed' ? '#4ade80' : '#94a3b8' }}>
            {jobStatus.status === 'completed' && (
              <>✓ Done — {jobStatus.events_created ?? 0} new events, {jobStatus.events_updated ?? 0} updated
              {jobStatus.events_skipped_enrichment ? `, ${jobStatus.events_skipped_enrichment} single-source (skipped enrichment)` : ''}.</>
            )}
            {jobStatus.status === 'failed' && <>✗ {jobStatus.error || 'Job failed'}</>}
            {(jobStatus.status === 'started' || jobStatus.status === 'running') && <>⏳ {jobStatus.message}</>}
          </div>
        )}
      </div>

      <div className={styles.panel}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0 }}>Briefings ({events.length})</h2>
          <label className={styles.label} style={{ margin: 0 }}>
            <select className={styles.input} value={minSourcesFilter} onChange={e => setMinSourcesFilter(Number(e.target.value))}>
              <option value={0}>All events</option>
              <option value={2}>Multi-source only</option>
            </select>
          </label>
        </div>

        {isLoading && <div style={{ color: 'var(--text-muted)' }}>Loading…</div>}
        {!isLoading && events.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No events yet. Click "Generate Briefings" above to cluster the latest RSS articles.
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {events.map(ev => <EventCard key={ev.id} event={ev} />)}
        </div>
      </div>
    </div>
  )
}
