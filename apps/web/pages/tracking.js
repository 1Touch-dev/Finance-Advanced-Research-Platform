import { useState } from 'react'
import useSWR from 'swr'
import styles from '../src/styles/Page.module.css'
import { getApiBaseUrl } from '../lib/api'

const API = getApiBaseUrl()
const fetcher = url => fetch(url).then(r => r.json())

// ── F-04: Inline investment threshold panel ───────────────────────────────────

function ThresholdPanel({ ticker, onSaved }) {
  const [open, setOpen]           = useState(false)
  const [threshold, setThreshold] = useState('')
  const [email, setEmail]         = useState('')
  const [phone, setPhone]         = useState('')
  const [onBuy, setOnBuy]         = useState(true)
  const [onSell, setOnSell]       = useState(false)
  const [saving, setSaving]       = useState(false)
  const [msg, setMsg]             = useState(null)

  // pre-fill when opening
  const handleOpen = async () => {
    setOpen(o => !o)
    if (!open && ticker) {
      try {
        const r = await fetch(`${API}/tracking/watchlist/${encodeURIComponent(ticker)}/threshold`)
        if (r.ok) {
          const d = await r.json()
          setThreshold(d.threshold || '')
          setEmail(d.notify_email || '')
          setPhone(d.notify_phone || '')
          setOnBuy(d.alert_on_buy ?? true)
          setOnSell(d.alert_on_sell ?? false)
        }
      } catch (_) {}
    }
  }

  const save = async () => {
    if (!threshold || Number(threshold) < 1000) {
      setMsg({ ok: false, text: 'Threshold must be ≥ $1,000' }); return
    }
    if (!email && !phone) {
      setMsg({ ok: false, text: 'Enter at least an email or phone' }); return
    }
    setSaving(true); setMsg(null)
    try {
      const body = {
        threshold: Number(threshold),
        notify_email: email || null,
        notify_phone: phone || null,
        alert_on_buy: onBuy,
        alert_on_sell: onSell,
      }
      const r = await fetch(`${API}/tracking/watchlist/${encodeURIComponent(ticker)}/threshold`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const d = await r.json()
      if (r.ok) {
        setMsg({ ok: true, text: `Alert saved — notifying at ≥$${Number(threshold).toLocaleString()}` })
        if (onSaved) onSaved()
      } else {
        setMsg({ ok: false, text: d.detail || JSON.stringify(d) })
      }
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally {
      setSaving(false)
    }
  }

  const hasSaved = !!threshold && Number(threshold) >= 1000

  return (
    <div style={{ marginTop: '0.35rem' }}>
      <button
        onClick={handleOpen}
        title={hasSaved ? `Alert set at ≥$${Number(threshold).toLocaleString()}` : 'Set investment alert'}
        style={{
          background:   hasSaved ? 'rgba(34,197,94,0.12)' : 'rgba(251,191,36,0.1)',
          border:       `1px solid ${hasSaved ? 'rgba(34,197,94,0.35)' : 'rgba(251,191,36,0.3)'}`,
          borderRadius: 6,
          color:        hasSaved ? '#4ade80' : '#fbbf24',
          cursor:       'pointer',
          fontSize:     '0.7rem',
          fontWeight:   700,
          padding:      '0.18rem 0.5rem',
          whiteSpace:   'nowrap',
        }}
      >
        {hasSaved ? `📬 Alert ≥$${Number(threshold).toLocaleString()}` : '📬 Set Alert'}
      </button>

      {open && (
        <div style={{
          marginTop:    '0.5rem',
          background:   'rgba(8,13,26,0.95)',
          border:       '1px solid rgba(251,191,36,0.25)',
          borderRadius: 8,
          padding:      '0.75rem',
        }}>
          <p style={{ margin: '0 0 0.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#fbbf24' }}>
            📬 Investment Alert — {ticker}
          </p>
          <p style={{ margin: '0 0 0.6rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Alert me when someone invests ≥ this amount
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: '1 1 120px' }}>
              <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Threshold ($)
              </span>
              <input
                className="inp"
                type="number"
                min="1000"
                placeholder="5000"
                value={threshold}
                onChange={e => setThreshold(e.target.value)}
                style={{ fontSize: '0.82rem' }}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: '2 1 200px' }}>
              <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Email
              </span>
              <input
                className="inp"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                style={{ fontSize: '0.82rem' }}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: '1 1 150px' }}>
              <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Phone (optional)
              </span>
              <input
                className="inp"
                type="tel"
                placeholder="+14155551234"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                style={{ fontSize: '0.82rem' }}
              />
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>Alert on:</span>
            <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', fontSize: '0.75rem', color: '#c7d2fe' }}>
              <input type="checkbox" checked={onBuy} onChange={e => setOnBuy(e.target.checked)} />
              BUY
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', fontSize: '0.75rem', color: '#c7d2fe' }}>
              <input type="checkbox" checked={onSell} onChange={e => setOnSell(e.target.checked)} />
              SELL
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button onClick={save} disabled={saving} style={{ fontSize: '0.78rem', padding: '0.3rem 0.9rem' }}>
              {saving ? '⏳ Saving…' : '💾 Save Alert'}
            </button>
            <button
              onClick={() => { setOpen(false); setMsg(null) }}
              style={{
                background: 'transparent', border: '1px solid var(--line)', borderRadius: 6,
                color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.75rem', padding: '0.3rem 0.7rem',
              }}
            >Cancel</button>
          </div>
          {msg && (
            <p style={{ margin: '0.4rem 0 0', fontSize: '0.75rem', color: msg.ok ? '#4ade80' : '#f87171' }}>
              {msg.ok ? '✓' : '✗'} {msg.text}
            </p>
          )}
          {Number(threshold) > 0 && Number(threshold) < 5000 && (
            <p style={{ margin: '0.3rem 0 0', fontSize: '0.68rem', color: '#fbbf24' }}>
              ⚠ Low threshold may cause frequent alerts. Consider $5,000+.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Entity Watchlist Row ──────────────────────────────────────────────────────

function WatchRow({ entity, onRemove, onInvestigate }) {
  const lastChecked = entity.last_checked
    ? new Date(entity.last_checked).toLocaleString()
    : 'Never'

  // Derive a ticker guess from entity_name for F-04 (e.g. "Apple" → no ticker unless API returns one)
  const ticker = entity.ticker || null

  return (
    <div style={{
      padding:      '0.6rem 0.75rem',
      background:   'rgba(129,140,248,0.04)',
      border:       '1px solid var(--line)',
      borderRadius: 8,
      marginBottom: '0.35rem',
    }}>
      <div style={{
        display:             'grid',
        gridTemplateColumns: '1fr 90px 120px 90px 90px',
        alignItems:          'center',
        gap:                 '0.5rem',
      }}>
        <span style={{ fontWeight: 700, color: '#c7d2fe', fontSize: '0.88rem' }}>
          {entity.entity_name}
          {ticker && (
            <span style={{ marginLeft: 6, fontSize: '0.68rem', color: '#818cf8',
                           background: 'rgba(129,140,248,0.12)', borderRadius: 4, padding: '0 4px' }}>
              {ticker}
            </span>
          )}
        </span>
        <span style={{
          background:    entity.entity_type === 'person' ? 'rgba(248,113,113,0.15)' : 'rgba(96,165,250,0.15)',
          border:        `1px solid ${entity.entity_type === 'person' ? 'rgba(248,113,113,0.4)' : 'rgba(96,165,250,0.4)'}`,
          borderRadius:  5,
          color:         entity.entity_type === 'person' ? '#f87171' : '#60a5fa',
          fontSize:      '0.68rem',
          fontWeight:    700,
          padding:       '0.1rem 0.4rem',
          textAlign:     'center',
          textTransform: 'uppercase',
        }}>{entity.entity_type}</span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{lastChecked}</span>
        <button
          onClick={() => onInvestigate(entity.entity_name)}
          style={{
            background:  'rgba(129,140,248,0.12)',
            border:      '1px solid rgba(129,140,248,0.3)',
            borderRadius: 6, color: '#c7d2fe', cursor: 'pointer',
            fontSize: '0.72rem', fontWeight: 700, padding: '0.2rem 0.5rem',
          }}
        >Investigate</button>
        <button
          onClick={() => onRemove(entity.entity_name)}
          style={{
            background:  'rgba(248,113,113,0.1)',
            border:      '1px solid rgba(248,113,113,0.3)',
            borderRadius: 6, color: '#f87171', cursor: 'pointer',
            fontSize: '0.72rem', fontWeight: 700, padding: '0.2rem 0.5rem',
          }}
        >Remove</button>
      </div>

      {/* F-04 investment alert panel — shown only when a ticker is available */}
      {ticker && <ThresholdPanel ticker={ticker} />}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TrackingPage() {
  const [addName,    setAddName]    = useState('')
  const [addType,    setAddType]    = useState('org')
  const [addTicker,  setAddTicker]  = useState('')
  const [digestRunning, setDigestRunning] = useState(false)
  const [digestResult,  setDigestResult]  = useState(null)
  const [dryRun,     setDryRun]     = useState(true)

  // F-03 scan state
  const [scanRunning, setScanRunning] = useState(false)
  const [scanResult,  setScanResult]  = useState(null)
  const [scanDryRun,  setScanDryRun]  = useState(true)

  const { data: watchlist, mutate: mutateList } = useSWR(`${API}/tracking/watchlist`, fetcher, { refreshInterval: 30000 })
  const { data: digestLogs } = useSWR(`${API}/tracking/digest/logs`, fetcher, { refreshInterval: 60000 })

  const entities = watchlist || []
  const logs     = digestLogs || []

  const addEntity = async () => {
    if (!addName.trim()) return
    await fetch(`${API}/tracking/watchlist`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        entity_name: addName.trim(),
        entity_type: addType,
        notes: addTicker.trim() ? `ticker:${addTicker.trim().toUpperCase()}` : '',
      }),
    })
    setAddName(''); setAddTicker('')
    mutateList()
  }

  const removeEntity = async (name) => {
    await fetch(`${API}/tracking/watchlist/${encodeURIComponent(name)}`, { method: 'DELETE' })
    mutateList()
  }

  const runDigest = async () => {
    setDigestRunning(true); setDigestResult(null)
    try {
      const r = await fetch(`${API}/tracking/digest/run?dry_run=${dryRun}`, { method: 'POST' })
      setDigestResult(await r.json())
    } catch(e) {
      setDigestResult({ error: e.message })
    } finally {
      setDigestRunning(false)
    }
  }

  const runBigTradeScan = async () => {
    setScanRunning(true); setScanResult(null)
    try {
      const r = await fetch(`${API}/tracking/scan/insider-trades?dry_run=${scanDryRun}`, { method: 'POST' })
      setScanResult(await r.json())
    } catch(e) {
      setScanResult({ error: e.message })
    } finally {
      setScanRunning(false)
    }
  }

  const investigate = (name) => {
    window.open(`/intelligence?entity=${encodeURIComponent(name)}`, '_blank')
  }

  // Enrich entities with ticker from notes field (notes: "ticker:AAPL")
  const enrichedEntities = entities.map(e => {
    const tickerMatch = (e.notes || '').match(/ticker:([A-Z]{1,6})/i)
    return { ...e, ticker: tickerMatch ? tickerMatch[1].toUpperCase() : null }
  })

  const QUICK_ENTITIES = [
    { name: 'Apple Inc.',            type: 'org',    ticker: 'AAPL' },
    { name: 'Palantir Technologies', type: 'org',    ticker: 'PLTR' },
    { name: 'Peter Thiel',           type: 'person', ticker: null   },
    { name: 'Tesla Inc.',            type: 'org',    ticker: 'TSLA' },
    { name: 'Elon Musk',             type: 'person', ticker: null   },
    { name: 'NVIDIA Corporation',    type: 'org',    ticker: 'NVDA' },
  ]

  return (
    <main className="page-wrap">
      <section className="card">
        <p style={{ margin: '0 0 0.4rem', fontSize: '0.75rem', fontWeight: 700,
                    letterSpacing: '0.08em', textTransform: 'uppercase', color: '#818cf8' }}>
          v2.0 — Entity Monitoring + Trade Alerts
        </p>
        <h1 style={{ margin: 0 }}>Tracking Dashboard</h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', maxWidth: 640 }}>
          Add entities to your watchlist. Set personal investment thresholds per company (F-04).
          Platform auto-scans SEC Form 4 insider trades every 4 hours for big trade alerts (F-03).
        </p>
      </section>

      {/* Stats */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Entities Watched',  value: entities.length },
          { label: 'Digest Runs',       value: logs.length },
          { label: 'Last Digest',       value: logs[0] ? new Date(logs[0].sent_at).toLocaleDateString() : '—' },
          { label: 'Digest Status',     value: logs[0]?.status || '—' },
        ].map((s, i) => (
          <div key={i} style={{
            background: 'rgba(8,13,26,0.85)', border: '1px solid var(--line)',
            borderRadius: 10, padding: '0.6rem 1rem', minWidth: 130,
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
      <div className="card">
        <h2>Add to Watchlist</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4,
                          color: 'var(--text-muted)', fontSize: '0.82rem', fontWeight: 600, flex: '2 1 200px' }}>
            Entity Name
            <input className="inp" value={addName} onChange={e => setAddName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addEntity()} placeholder="e.g. Apple Inc." />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4,
                          color: 'var(--text-muted)', fontSize: '0.82rem', fontWeight: 600, flex: '0 1 110px' }}>
            Ticker (opt.)
            <input className="inp" value={addTicker} onChange={e => setAddTicker(e.target.value.toUpperCase())}
              placeholder="AAPL" maxLength={6} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4,
                          color: 'var(--text-muted)', fontSize: '0.82rem', fontWeight: 600, minWidth: 120 }}>
            Type
            <select className="inp" value={addType} onChange={e => setAddType(e.target.value)}>
              <option value="org">Organization</option>
              <option value="person">Person</option>
            </select>
          </label>
          <button onClick={addEntity} style={{ alignSelf: 'flex-end' }}>+ Add to Watchlist</button>
        </div>

        {/* Quick adds */}
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.6rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', alignSelf: 'center' }}>
            Quick add:
          </span>
          {QUICK_ENTITIES.map(e => (
            <button key={e.name}
              onClick={() => { setAddName(e.name); setAddType(e.type); setAddTicker(e.ticker || '') }}
              style={{
                background: 'rgba(129,140,248,0.08)', border: '1px solid rgba(129,140,248,0.2)',
                borderRadius: 6, color: '#c7d2fe', cursor: 'pointer',
                fontSize: '0.73rem', fontWeight: 600, padding: '0.2rem 0.5rem',
              }}
            >{e.name}{e.ticker ? ` (${e.ticker})` : ''}</button>
          ))}
        </div>
      </div>

      {/* Watchlist */}
      <div className="card">
        <h2>Watchlist ({enrichedEntities.length})</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', margin: '0 0 0.6rem' }}>
          Entities with a ticker show a <strong style={{color:'#fbbf24'}}>📬 Set Alert</strong> button — 
          click it to configure your personal investment threshold for F-04 alerts.
        </p>
        {enrichedEntities.length === 0 && (
          <p style={{ color: 'var(--text-soft)', fontStyle: 'italic', fontSize: '0.82rem' }}>
            No entities being tracked. Add some above.
          </p>
        )}
        {enrichedEntities.map((e, i) => (
          <WatchRow key={i} entity={e} onRemove={removeEntity} onInvestigate={investigate} />
        ))}
      </div>

      {/* F-03: Big Trade Scan */}
      <div className="card" style={{ borderLeft: '3px solid #f87171' }}>
        <h2 style={{ color: '#f87171' }}>🚨 F-03 — Big Trade Scanner</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: '0 0 0.75rem' }}>
          Scans SEC Form 4 insider trades automatically every 4 hours via PM2.
          Fires an alert when any insider buys/sells above the configured threshold ($500k default).
          Use the button below to run a manual scan now.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer',
                          fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            <input type="checkbox" checked={scanDryRun} onChange={e => setScanDryRun(e.target.checked)} />
            Dry run (no emails/SMS)
          </label>
          <button
            onClick={runBigTradeScan}
            disabled={scanRunning}
            style={{
              background: scanRunning ? undefined : 'rgba(248,113,113,0.12)',
              border: '1px solid rgba(248,113,113,0.35)',
              color: '#f87171',
            }}
          >
            {scanRunning ? '⏳ Scanning…' : '▶ Run Big-Trade Scan'}
          </button>
        </div>

        {scanResult && (
          <div style={{ marginTop: '0.75rem', background: 'rgba(8,13,26,0.9)', border: '1px solid var(--line)',
                        borderRadius: 8, padding: '0.75rem', fontSize: '0.82rem' }}>
            {scanResult.error ? (
              <p style={{ color: '#f87171', margin: 0 }}>Error: {scanResult.error}</p>
            ) : (
              <>
                <p style={{ color: '#4ade80', fontWeight: 700, margin: '0 0 0.4rem' }}>
                  ✓ {scanResult.rules_run} rule(s) run
                  {scanResult.dry_run && <span style={{ color: '#fbbf24', marginLeft: 8 }}>(dry run)</span>}
                </p>
                {(scanResult.results || []).map((r, i) => (
                  <div key={i} style={{ marginBottom: '0.5rem', paddingLeft: '0.5rem',
                                        borderLeft: '2px solid rgba(248,113,113,0.3)' }}>
                    <p style={{ margin: '0 0 0.2rem', fontWeight: 700, color: '#c7d2fe' }}>
                      {r.rule_name} — threshold ${(r.threshold_used||0).toLocaleString()}
                    </p>
                    <p style={{ margin: '0 0 0.2rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Scanned {r.scanned_tickers} tickers · {r.above_threshold} above threshold ·
                      {r.already_alerted} already alerted · <strong style={{color:'#4ade80'}}>{r.new_alerts_created} new alerts</strong>
                    </p>
                    {(r.alerts || []).slice(0,3).map((a, j) => (
                      <div key={j} style={{ fontSize: '0.73rem', color: 'var(--text-soft)', paddingLeft: '0.5rem' }}>
                        {a.ticker} — {a.insider} ({a.transaction}) ${(a.value_usd||0).toLocaleString()} on {a.date}
                      </div>
                    ))}
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>

      {/* Digest controls */}
      <div className="card">
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
          <button onClick={runDigest} disabled={digestRunning || entities.length === 0}>
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
        <div className="card">
          <h2>Digest History</h2>
          <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'rgba(129,140,248,0.1)', color: '#818cf8' }}>
                {['Sent At','Status','Entities','Channel','Detail'].map(h => (
                  <th key={h} style={{ padding: '0.4rem 0.6rem', textAlign: 'left',
                                       fontWeight: 700, fontSize: '0.72rem' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 10).map((log, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '0.4rem 0.6rem', color: 'var(--text-muted)' }}>
                    {new Date(log.sent_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '0.4rem 0.6rem', fontWeight: 700,
                                color: log.status === 'sent' ? '#4ade80' : log.status === 'dry_run' ? '#fbbf24' : '#f87171' }}>
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

      {/* Config note */}
      <div className="card" style={{ borderLeft: '3px solid #fbbf24' }}>
        <h3 style={{ margin: '0 0 0.4rem', color: '#fbbf24' }}>Notification Configuration</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: 0 }}>
          <strong>F-03 (Big Trade):</strong> Set <code>ALERT_RECIPIENT_EMAIL</code> and
          <code>ALERT_RECIPIENT_PHONE</code> in <code>.env</code>.<br/>
          <strong>F-04 (Investment Alert):</strong> Each watchlist item stores its own email/phone —
          set them via the <span style={{color:'#fbbf24'}}>📬 Set Alert</span> button on each row.<br/>
          SendGrid and Twilio are already configured. PM2 runs both scanners every 4 hours automatically.
        </p>
      </div>
    </main>
  )
}

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
    <main className="page-wrap">
      <section className="card">
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
      <div className="card">
        <h2>Add to Watchlist</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label style={{display:"flex",flexDirection:"column",gap:4,color:"var(--text-muted)",fontSize:"0.82rem",fontWeight:600}} style={{ flex: '1 1 220px' }}>
            Entity Name
            <input
              className="inp"
              value={addName}
              onChange={e => setAddName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addEntity()}
              placeholder="e.g. Palantir Technologies"
            />
          </label>
          <label style={{display:"flex",flexDirection:"column",gap:4,color:"var(--text-muted)",fontSize:"0.82rem",fontWeight:600}} style={{ minWidth: 120 }}>
            Type
            <select className="inp" value={addType} onChange={e => setAddType(e.target.value)}>
              <option value="org">Organization</option>
              <option value="person">Person</option>
            </select>
          </label>
          <button  onClick={addEntity} style={{ alignSelf: 'flex-end' }}>
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
      <div className="card">
        <h2>Watchlist ({entities.length})</h2>
        {entities.length === 0 && (
          <p style={{color:"var(--text-soft)",fontStyle:"italic",fontSize:"0.82rem"}}>No entities being tracked. Add some above.</p>
        )}
        {entities.map((e, i) => (
          <WatchRow key={i} entity={e} onRemove={removeEntity} onInvestigate={investigate} />
        ))}
      </div>

      {/* Digest controls */}
      <div className="card">
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
        <div className="card">
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
      <div className="card" style={{ borderLeft: '3px solid #fbbf24' }}>
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
