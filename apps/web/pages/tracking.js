import { useState, useEffect } from 'react'
import useSWR from 'swr'
import styles from '../src/styles/Page.module.css'
import { getApiBaseUrl } from '../lib/api'
import Link from 'next/link'

const API = getApiBaseUrl()
const fetcher = url => fetch(url).then(r => r.json())

// ── Entity Watchlist Row ──────────────────────────────────────────────────────

function WatchRow({ entity, onRemove, onInvestigate }) {
  const lastChecked = entity.last_checked
    ? new Date(entity.last_checked).toLocaleString()
    : 'Never'

  return (
    <div style={{
      display:       'grid',
      gridTemplateColumns: '1fr 90px 120px 90px 90px',
      alignItems:    'center',
      gap:           '0.5rem',
      padding:       '0.5rem 0.75rem',
      background:    'rgba(129,140,248,0.04)',
      border:        '1px solid var(--line)',
      borderRadius:  8,
      marginBottom:  '0.35rem',
    }}>
      <span style={{ fontWeight: 700, color: '#c7d2fe', fontSize: '0.88rem' }}>
        {entity.entity_name}
      </span>
      <span style={{
        background:  entity.entity_type === 'person' ? 'rgba(248,113,113,0.15)' : 'rgba(96,165,250,0.15)',
        border:      `1px solid ${entity.entity_type === 'person' ? 'rgba(248,113,113,0.4)' : 'rgba(96,165,250,0.4)'}`,
        borderRadius: 5,
        color:       entity.entity_type === 'person' ? '#f87171' : '#60a5fa',
        fontSize:    '0.68rem',
        fontWeight:  700,
        padding:     '0.1rem 0.4rem',
        textAlign:   'center',
        textTransform: 'uppercase',
      }}>{entity.entity_type}</span>
      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{lastChecked}</span>
      <button
        onClick={() => onInvestigate(entity.entity_name)}
        style={{
          background:  'rgba(129,140,248,0.12)',
          border:      '1px solid rgba(129,140,248,0.3)',
          borderRadius: 6,
          color:       '#c7d2fe',
          cursor:      'pointer',
          fontSize:    '0.72rem',
          fontWeight:  700,
          padding:     '0.2rem 0.5rem',
        }}
      >Investigate</button>
      <button
        onClick={() => onRemove(entity.entity_name)}
        style={{
          background:  'rgba(248,113,113,0.1)',
          border:      '1px solid rgba(248,113,113,0.3)',
          borderRadius: 6,
          color:       '#f87171',
          cursor:      'pointer',
          fontSize:    '0.72rem',
          fontWeight:  700,
          padding:     '0.2rem 0.5rem',
        }}
      >Remove</button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TrackingPage() {
  const [addName,    setAddName]    = useState('')
  const [addType,    setAddType]    = useState('org')
  const [digestRunning, setDigestRunning] = useState(false)
  const [digestResult,  setDigestResult]  = useState(null)
  const [dryRun,     setDryRun]     = useState(true)

  const { data: watchlist, mutate: mutateList } = useSWR(`${API}/tracking/watchlist`, fetcher, { refreshInterval: 30000 })
  const { data: digestLogs } = useSWR(`${API}/tracking/digest/logs`, fetcher, { refreshInterval: 60000 })

  const entities = watchlist || []
  const logs     = digestLogs || []

  const addEntity = async () => {
    if (!addName.trim()) return
    await fetch(`${API}/tracking/watchlist`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ entity_name: addName.trim(), entity_type: addType }),
    })
    setAddName('')
    mutateList()
  }

  const removeEntity = async (name) => {
    await fetch(`${API}/tracking/watchlist/${encodeURIComponent(name)}`, { method: 'DELETE' })
    mutateList()
  }

  const runDigest = async () => {
    setDigestRunning(true)
    setDigestResult(null)
    try {
      const r = await fetch(`${API}/tracking/digest/run?dry_run=${dryRun}`, { method: 'POST' })
      const data = await r.json()
      setDigestResult(data)
    } catch(e) {
      setDigestResult({ error: e.message })
    } finally {
      setDigestRunning(false)
    }
  }

  const investigate = (name) => {
    window.open(`/intelligence?entity=${encodeURIComponent(name)}`, '_blank')
  }

  const QUICK_ENTITIES = [
    { name: 'Palantir Technologies', type: 'org' },
    { name: 'Peter Thiel',           type: 'person' },
    { name: 'Anduril Industries',    type: 'org' },
    { name: 'SpaceX',                type: 'org' },
    { name: 'Elon Musk',             type: 'person' },
  ]

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p style={{ margin: '0 0 0.4rem', fontSize: '0.75rem', fontWeight: 700,
                    letterSpacing: '0.08em', textTransform: 'uppercase', color: '#818cf8' }}>
          v2.0 — Entity Monitoring
        </p>
        <h1 style={{ margin: 0 }}>Tracking Dashboard</h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', maxWidth: 640 }}>
          Add entities to your watchlist. Run a daily digest to detect changes in contracts,
          lobbying, court cases, and more. Alerts delivered via email and SMS.
        </p>
      </section>

      {/* Stats */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Entities Watched',   value: entities.length },
          { label: 'Digest Runs',        value: logs.length },
          { label: 'Last Digest',        value: logs[0] ? new Date(logs[0].sent_at).toLocaleDateString() : '—' },
          { label: 'Digest Status',      value: logs[0]?.status || '—' },
        ].map((s, i) => (
          <div key={i} style={{
            background: 'rgba(8,13,26,0.85)',
            border:     '1px solid var(--line)',
            borderRadius: 10,
            padding:    '0.6rem 1rem',
            minWidth:   130,
          }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#c7d2fe' }}>{s.value}</div>
            <div style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
                          letterSpacing: '0.07em', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* Add to watchlist */}
      <div className={styles.panel}>
        <h2>Add to Watchlist</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label className={styles.label} style={{ flex: '1 1 220px' }}>
            Entity Name
            <input
              className={styles.input}
              value={addName}
              onChange={e => setAddName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addEntity()}
              placeholder="e.g. Palantir Technologies"
            />
          </label>
          <label className={styles.label} style={{ minWidth: 120 }}>
            Type
            <select className={styles.input} value={addType} onChange={e => setAddType(e.target.value)}>
              <option value="org">Organization</option>
              <option value="person">Person</option>
            </select>
          </label>
          <button className={styles.btn} onClick={addEntity} style={{ alignSelf: 'flex-end' }}>
            + Add to Watchlist
          </button>
        </div>

        {/* Quick adds */}
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.6rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', alignSelf: 'center' }}>
            Quick add:
          </span>
          {QUICK_ENTITIES.map(e => (
            <button
              key={e.name}
              onClick={() => { setAddName(e.name); setAddType(e.type) }}
              style={{
                background:  'rgba(129,140,248,0.08)',
                border:      '1px solid rgba(129,140,248,0.2)',
                borderRadius: 6,
                color:       '#c7d2fe',
                cursor:      'pointer',
                fontSize:    '0.73rem',
                fontWeight:  600,
                padding:     '0.2rem 0.5rem',
              }}
            >{e.name}</button>
          ))}
        </div>
      </div>

      {/* Watchlist */}
      <div className={styles.panel}>
        <h2>Watchlist ({entities.length})</h2>
        {entities.length === 0 && (
          <p className={styles.empty}>No entities being tracked. Add some above.</p>
        )}
        {entities.map((e, i) => (
          <WatchRow key={i} entity={e} onRemove={removeEntity} onInvestigate={investigate} />
        ))}
      </div>

      {/* Digest controls */}
      <div className={styles.panel}>
        <h2>Daily Digest</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: '0 0 0.75rem' }}>
          Runs automatically at 6:00 AM UTC. Re-generates all watched entity reports,
          detects changes, and sends email + SMS alerts. You can also run it manually below.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer',
                          fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
            Dry run (no emails/SMS)
          </label>
          <button
            className={styles.btn}
            onClick={runDigest}
            disabled={digestRunning || entities.length === 0}
          >
            {digestRunning ? '⏳ Running digest…' : '▶ Run Digest Now'}
          </button>
        </div>

        {digestResult && (
          <div style={{ marginTop: '0.75rem', background: 'rgba(8,13,26,0.9)', border: '1px solid var(--line)',
                        borderRadius: 8, padding: '0.75rem', fontSize: '0.82rem' }}>
            <div style={{ fontWeight: 700, color: digestResult.error ? '#f87171' : '#4ade80', marginBottom: '0.4rem' }}>
              {digestResult.error ? `Error: ${digestResult.error}` :
               `${digestResult.status?.toUpperCase()} — ${digestResult.entities_checked} entities checked, ${digestResult.total_changes || 0} changes`}
            </div>
            {digestResult.changes && Object.entries(digestResult.changes).map(([name, changes], i) => (
              <div key={i} style={{ marginBottom: '0.4rem' }}>
                <span style={{ color: '#818cf8', fontWeight: 700 }}>{name}:</span>
                <ul style={{ margin: '0.2rem 0 0 1rem', padding: 0, color: 'var(--text-soft)' }}>
                  {(changes || []).map((c, j) => <li key={j}>{c}</li>)}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Digest logs */}
      {logs.length > 0 && (
        <div className={styles.panel}>
          <h2>Digest History</h2>
          <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'rgba(129,140,248,0.1)', color: '#818cf8' }}>
                {['Sent At', 'Status', 'Entities', 'Channel', 'Detail'].map(h => (
                  <th key={h} style={{ padding: '0.4rem 0.6rem', textAlign: 'left', fontWeight: 700, fontSize: '0.72rem' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 10).map((log, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '0.4rem 0.6rem', color: 'var(--text-muted)' }}>
                    {new Date(log.sent_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '0.4rem 0.6rem',
                                color: log.status === 'sent' ? '#4ade80' : log.status === 'dry_run' ? '#fbbf24' : '#f87171',
                                fontWeight: 700 }}>
                    {log.status}
                  </td>
                  <td style={{ padding: '0.4rem 0.6rem' }}>{log.entity_count}</td>
                  <td style={{ padding: '0.4rem 0.6rem', color: 'var(--text-muted)' }}>{log.channel}</td>
                  <td style={{ padding: '0.4rem 0.6rem', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                    {typeof log.detail === 'object' ? JSON.stringify(log.detail) : (log.detail || '—')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Configure notifications note */}
      <div className={styles.panel} style={{ borderLeft: '3px solid #fbbf24' }}>
        <h3 style={{ margin: '0 0 0.4rem', color: '#fbbf24' }}>Notification Configuration</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: 0 }}>
          Set <code>DIGEST_RECIPIENT_EMAIL</code> and <code>DIGEST_RECIPIENT_PHONE</code> in <code>.env</code> to
          receive daily digests. SendGrid (email) and Twilio (SMS) are already configured.
          A cron job or PM2 scheduler can be set up to auto-trigger <code>POST /tracking/digest/run</code> at 6 AM UTC daily.
        </p>
      </div>
    </main>
  )
}
