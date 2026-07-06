import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const fmtBig = v => {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e12) return `$${(v/1e12).toFixed(2)}T`
  if (Math.abs(v) >= 1e9)  return `$${(v/1e9).toFixed(2)}B`
  if (Math.abs(v) >= 1e6)  return `$${(v/1e6).toFixed(2)}M`
  if (Math.abs(v) >= 1e3)  return `$${(v/1e3).toFixed(0)}K`
  return `$${v?.toLocaleString()}`
}
const pct = v => v == null ? '—' : `${(v * 100).toFixed(2)}%`

const INSTITUTIONS = [
  'Berkshire Hathaway','BlackRock','Vanguard','State Street','Fidelity',
  'T. Rowe Price','JP Morgan','Goldman Sachs','Morgan Stanley','Cathie Wood / ARK',
  'Pershing Square',
]

function HolderRow({ h, rank }) {
  return (
    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <td style={{ padding: '7px 12px', textAlign: 'right', color: '#475569', fontSize: '0.75rem' }}>{rank}</td>
      <td style={{ padding: '7px 12px', fontWeight: 600, color: '#e2e8f0', fontSize: '0.82rem' }}>{h.holder || h.issuer || '—'}</td>
      <td style={{ padding: '7px 12px', textAlign: 'right', color: '#86efac' }}>{h.shares?.toLocaleString() || '—'}</td>
      <td style={{ padding: '7px 12px', textAlign: 'right', color: '#a5f3fc' }}>
        {h.value_usd ? fmtBig(h.value_usd) : h.value_thousands ? fmtBig(h.value_thousands * 1000) : '—'}
      </td>
      <td style={{ padding: '7px 12px', textAlign: 'right', color: '#818cf8' }}>{h.pct_held != null ? pct(h.pct_held) : '—'}</td>
      <td style={{ padding: '7px 12px', textAlign: 'right', color: '#64748b', fontSize: '0.75rem' }}>{h.date_reported?.slice(0, 10) || '—'}</td>
    </tr>
  )
}

function FilersTable({ filers }) {
  if (!filers?.length) return <p style={{ color: '#64748b', fontSize: '0.82rem' }}>No recent 13F filers found</p>
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--line)' }}>
          {['Institution', 'Filing Date', 'Period', 'CIK'].map(h =>
            <th key={h} style={{ padding: '6px 12px', textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
        </tr>
      </thead>
      <tbody>
        {filers.map((f, i) => (
          <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
            <td style={{ padding: '7px 12px', fontWeight: 600, color: '#e2e8f0' }}>{f.filer}</td>
            <td style={{ padding: '7px 12px', color: '#86efac' }}>{f.filing_date}</td>
            <td style={{ padding: '7px 12px', color: '#94a3b8' }}>{f.period}</td>
            <td style={{ padding: '7px 12px', color: '#475569', fontSize: '0.75rem' }}>{f.cik}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function InstitutionHoldings({ data }) {
  if (!data) return null
  if (data.error) return <p style={{ color: '#f87171' }}>{data.error}</p>

  const holdings = data.top_holdings || []
  return (
    <div>
      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Filing Date</div>
          <div style={{ fontWeight: 700, color: '#86efac' }}>{data.latest_13f_date || '—'}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Holdings</div>
          <div style={{ fontWeight: 700, color: '#c7d2fe' }}>{data.holdings_count || 0}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Value</div>
          <div style={{ fontWeight: 700, color: '#a5f3fc' }}>{data.top_holdings_value_b ? `$${data.top_holdings_value_b}B` : '—'}</div>
        </div>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--line)' }}>
              {['#', 'Issuer', 'Shares', 'Value ($K)', 'Type'].map(h =>
                <th key={h} style={{ padding: '6px 12px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {holdings.slice(0, 30).map((h, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '7px 12px', textAlign: 'right', color: '#475569', fontSize: '0.75rem' }}>{i+1}</td>
                <td style={{ padding: '7px 12px', fontWeight: 600, color: '#e2e8f0' }}>{h.issuer}</td>
                <td style={{ padding: '7px 12px', textAlign: 'right', color: '#86efac' }}>{h.shares?.toLocaleString()}</td>
                <td style={{ padding: '7px 12px', textAlign: 'right', color: '#a5f3fc' }}>{fmtBig((h.value_thousands || 0) * 1000)}</td>
                <td style={{ padding: '7px 12px', textAlign: 'right', color: '#94a3b8', fontSize: '0.75rem' }}>{h.type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function InstitutionalPage() {
  const [ticker, setTicker] = useState('AAPL')
  const [input, setInput] = useState('AAPL')
  const [institution, setInstitution] = useState('')
  const [tab, setTab] = useState('holders')
  const [holderData, setHolderData] = useState(null)
  const [instData, setInstData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [instLoading, setInstLoading] = useState(false)
  const [error, setError] = useState('')

  const runTicker = async (t) => {
    const sym = (t || input).toUpperCase().trim()
    if (!sym) return
    setTicker(sym)
    setLoading(true)
    setError('')
    setHolderData(null)
    try {
      const res = await fetch(`${API}/market/company/institutional-changes/${sym}`)
      setHolderData(await res.json())
    } catch(e) { setError('Failed: ' + e.message) }
    setLoading(false)
  }

  const runInstitution = async (name) => {
    const n = name || institution
    if (!n) return
    setInstLoading(true)
    try {
      const res = await fetch(`${API}/market/institution/holdings/${encodeURIComponent(n)}`)
      setInstData(await res.json())
      setTab('institution')
    } catch(e) { setError('Failed: ' + e.message) }
    setInstLoading(false)
  }

  const d = holderData || {}
  const TABS = [
    { id: 'holders', label: '🏛️ Institutional Holders' },
    { id: 'mutual', label: '📈 Mutual Funds' },
    { id: 'mega', label: '💎 Mega Positions' },
    { id: 'filers', label: '📋 13F Filers' },
    { id: 'institution', label: '🔍 Institution Lookup' },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Institutional Intelligence</h1>
          <p className={styles.subtitle}>13F holders · Big money positions · Institution portfolios</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <input value={input} onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && runTicker()}
            placeholder="Ticker" style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--card)', color: '#e2e8f0', width: 100 }} />
          <button onClick={() => runTicker()} disabled={loading}
            style={{ padding: '8px 18px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 700 }}>
            {loading ? '…' : 'Search'}
          </button>
          {['AAPL','MSFT','TSLA','NVDA','AMZN'].map(t => (
            <button key={t} onClick={() => { setInput(t); runTicker(t) }}
              style={{ padding: '4px 10px', background: ticker === t ? '#6366f1' : 'rgba(255,255,255,0.05)',
                color: ticker === t ? '#fff' : '#94a3b8', border: '1px solid var(--line)', borderRadius: 6, cursor: 'pointer', fontSize: '0.75rem' }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {error && <div style={{ background: '#ef444420', border: '1px solid #ef444444', borderRadius: 8, padding: '0.75rem', color: '#fca5a5', marginBottom: '1rem' }}>{error}</div>}

      {/* Summary stats */}
      {holderData && (
        <div className={styles.panel} style={{ padding: '0.75rem 1.5rem', marginBottom: '1rem', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          {[
            ['Inst. Holders', d.total_institutional_holders],
            ['Mega Positions (>$1B)', d.mega_positions_over_1b?.length],
            ['Large Positions ($100M+)', d.large_positions_100m_to_1b?.length],
            ['Recent 13F Filers', d.recent_13f_filers?.length],
          ].map(([label, val]) => (
            <div key={label}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
              <div style={{ fontWeight: 700, color: '#c7d2fe', fontSize: '1rem' }}>{val ?? '—'}</div>
            </div>
          ))}
          {Object.entries(d.ownership_summary || {}).slice(0, 3).map(([k, v]) => (
            <div key={k}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k}</div>
              <div style={{ fontWeight: 700, color: '#a5f3fc', fontSize: '0.9rem' }}>{v}</div>
            </div>
          ))}
        </div>
      )}

      {/* Institution Lookup Bar */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <select value={institution} onChange={e => setInstitution(e.target.value)}
          style={{ padding: '7px 12px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--card)', color: '#e2e8f0', flex: 1 }}>
          <option value="">Select Institution for Portfolio Lookup…</option>
          {INSTITUTIONS.map(i => <option key={i} value={i}>{i}</option>)}
        </select>
        <button onClick={() => runInstitution()} disabled={instLoading}
          style={{ padding: '7px 18px', background: '#0f172a', border: '1px solid #6366f1', color: '#818cf8', borderRadius: 8, cursor: 'pointer', fontWeight: 700 }}>
          {instLoading ? '…' : 'View Portfolio'}
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: '1.25rem', borderBottom: '1px solid var(--line)' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ padding: '8px 14px', background: 'transparent', border: 'none',
              borderBottom: tab === t.id ? '2px solid #6366f1' : '2px solid transparent',
              color: tab === t.id ? '#818cf8' : '#64748b', cursor: 'pointer', fontWeight: tab === t.id ? 700 : 400, fontSize: '0.8rem' }}>
            {t.label}
          </button>
        ))}
      </div>

      <div className={styles.panel}>
        {tab === 'holders' && (
          holderData ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--line)' }}>
                    {['#', 'Holder', 'Shares', 'Value', '% Held', 'Date'].map(h =>
                      <th key={h} style={{ padding: '6px 12px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {(d.institutional_holders || []).map((h, i) => <HolderRow key={i} h={h} rank={i+1} />)}
                </tbody>
              </table>
            </div>
          ) : <p style={{ color: '#64748b' }}>Enter a ticker to load institutional holders</p>
        )}
        {tab === 'mutual' && (
          holderData ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--line)' }}>
                    {['#', 'Fund', 'Shares', 'Value', '% Held', 'Date'].map(h =>
                      <th key={h} style={{ padding: '6px 12px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {(d.mutual_fund_holders || []).map((h, i) => <HolderRow key={i} h={h} rank={i+1} />)}
                </tbody>
              </table>
            </div>
          ) : <p style={{ color: '#64748b' }}>Enter a ticker first</p>
        )}
        {tab === 'mega' && (
          holderData ? (
            <>
              <h4 style={{ color: '#fbbf24', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Mega Positions (&gt;$1B)</h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      {['#', 'Holder', 'Shares', 'Value', '% Held'].map(h =>
                        <th key={h} style={{ padding: '6px 12px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {(d.mega_positions_over_1b || []).map((h, i) => <HolderRow key={i} h={h} rank={i+1} />)}
                  </tbody>
                </table>
              </div>
              <h4 style={{ color: '#a5f3fc', fontSize: '0.72rem', textTransform: 'uppercase', margin: '1.5rem 0 0.75rem' }}>Notable Institutions</h4>
              {Object.entries(d.notable_institution_positions || {}).map(([name, info]) => (
                <div key={name} style={{ display: 'flex', gap: '1rem', padding: '0.5rem 0.75rem', border: '1px solid var(--line)', borderRadius: 8, marginBottom: '0.4rem' }}>
                  <span style={{ fontWeight: 700, color: '#c7d2fe', flex: 1 }}>{name}</span>
                  <span style={{ color: '#86efac' }}>{info.shares?.toLocaleString()} shares</span>
                  <span style={{ color: '#a5f3fc' }}>{fmtBig(info.value_usd)}</span>
                  <span style={{ color: '#818cf8' }}>{info.pct_held != null ? pct(info.pct_held) : '—'}</span>
                </div>
              ))}
            </>
          ) : <p style={{ color: '#64748b' }}>Enter a ticker first</p>
        )}
        {tab === 'filers' && <FilersTable filers={d.recent_13f_filers} />}
        {tab === 'institution' && <InstitutionHoldings data={instData} />}
      </div>
    </div>
  )
}
