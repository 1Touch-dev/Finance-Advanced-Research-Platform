import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const fmt = (v, d = 2) => v == null ? '—' : typeof v === 'number' ? v.toFixed(d) : v
const fmtBig = v => {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e12) return `$${(v/1e12).toFixed(2)}T`
  if (Math.abs(v) >= 1e9) return `$${(v/1e9).toFixed(2)}B`
  if (Math.abs(v) >= 1e6) return `$${(v/1e6).toFixed(2)}M`
  return `$${v.toLocaleString()}`
}
const pct = v => v == null ? '—' : `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%`

function PricePanel({ data, t }) {
  const fundamentals = data?.fundamentals || {}
  const price = data?.price || {}
  const currentPrice = price.current_price || fundamentals.currentPrice
  return (
    <section className="card">
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Price — {t}</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#e2e8f0' }}>${fmt(currentPrice)}</div>
        </div>
        {[
          ['Market Cap', fundamentals.marketCap ? fmtBig(fundamentals.marketCap) : '—'],
          ['P/E Ratio', fmt(fundamentals.trailingPE || fundamentals.forwardPE)],
          ['EPS', fmt(fundamentals.trailingEps)],
          ['Beta', fmt(fundamentals.beta)],
          ['52W High', `$${fmt(fundamentals['52WeekHigh'] || fundamentals.fiftyTwoWeekHigh)}`],
          ['52W Low', `$${fmt(fundamentals['52WeekLow'] || fundamentals.fiftyTwoWeekLow)}`],
          ['Div Yield', fundamentals.dividendYield != null ? `${(fundamentals.dividendYield * 100).toFixed(2)}%` : '—'],
        ].map(([label, val]) => (
          <div key={label} style={{ textAlign: 'center', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.5rem 0.75rem', minWidth: 80 }}>
            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#c7d2fe' }}>{val}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function AnalystPanel({ data }) {
  if (!data) return null
  const upColor = data.upside_potential_pct > 10 ? '#4ade80' : data.upside_potential_pct < -10 ? '#f87171' : '#fbbf24'
  const recColors = { BUY: '#4ade80', STRONG_BUY: '#4ade80', HOLD: '#fbbf24', SELL: '#f87171', STRONG_SELL: '#f87171', UNDERPERFORM: '#f87171' }
  return (
    <section className="card">
      <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Analyst Consensus</h2>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 900, color: recColors[data.recommendation] || '#94a3b8' }}>{data.recommendation || '—'}</div>
          <div style={{ fontSize: '0.68rem', color: '#64748b' }}>{data.analyst_count} analysts</div>
        </div>
        {[
          ['Mean Target', data.price_target_mean ? `$${fmt(data.price_target_mean)}` : '—'],
          ['High Target', data.price_target_high ? `$${fmt(data.price_target_high)}` : '—'],
          ['Low Target', data.price_target_low ? `$${fmt(data.price_target_low)}` : '—'],
          ['Upside', data.upside_potential_pct != null ? `${data.upside_potential_pct > 0 ? '+' : ''}${data.upside_potential_pct.toFixed(1)}%` : '—'],
        ].map(([label, val]) => (
          <div key={label} style={{ textAlign: 'center', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.5rem 0.75rem', minWidth: 90 }}>
            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: label === 'Upside' ? upColor : '#c7d2fe' }}>{val}</div>
          </div>
        ))}
      </div>
      {data.recent_ratings?.length > 0 && (
        <div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Recent Ratings</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            {data.recent_ratings.slice(0, 8).map((r, i) => (
              <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.78rem', padding: '0.25rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ color: '#e2e8f0', fontWeight: 600, minWidth: 130 }}>{r.firm}</span>
                <span style={{ color: recColors[r.to_grade?.toUpperCase()] || '#94a3b8' }}>{r.to_grade}</span>
                {r.from_grade && <span style={{ color: '#64748b', fontSize: '0.7rem' }}>from {r.from_grade}</span>}
                <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: '0.68rem' }}>{String(r.date).slice(0, 10)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function EarningsPanel({ data }) {
  if (!data || (!data.earnings_history?.length && !data.calendar)) return null
  return (
    <section className="card">
      <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Earnings History</h2>
      {data.calendar && Object.keys(data.calendar).length > 0 && (
        <div style={{ marginBottom: '0.75rem', background: 'rgba(129,140,248,0.08)', border: '1px solid rgba(129,140,248,0.2)', borderRadius: 8, padding: '0.6rem 0.9rem' }}>
          <div style={{ fontSize: '0.72rem', color: '#818cf8', textTransform: 'uppercase', fontWeight: 700, marginBottom: '0.3rem' }}>Next Earnings</div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.82rem' }}>
            {Object.entries(data.calendar).slice(0, 4).map(([k, v]) => (
              <span key={k} style={{ color: '#e2e8f0' }}><span style={{ color: '#64748b' }}>{k}:</span> {v}</span>
            ))}
          </div>
        </div>
      )}
      {data.earnings_history?.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
          <thead>
            <tr style={{ color: '#64748b' }}>
              <th style={{ padding: '0.35rem 0.5rem', textAlign: 'left', borderBottom: '1px solid var(--line)' }}>Quarter</th>
              <th style={{ padding: '0.35rem 0.5rem', textAlign: 'right', borderBottom: '1px solid var(--line)' }}>Actual EPS</th>
              <th style={{ padding: '0.35rem 0.5rem', textAlign: 'right', borderBottom: '1px solid var(--line)' }}>Estimated EPS</th>
              <th style={{ padding: '0.35rem 0.5rem', textAlign: 'right', borderBottom: '1px solid var(--line)' }}>Surprise</th>
            </tr>
          </thead>
          <tbody>
            {data.earnings_history.slice(0, 8).map((e, i) => {
              const quarter = e.quarter || e.Quarter || e.period
              const actual = e.epsActual || e['Reported EPS'] || e.actual
              const est = e.epsEstimate || e['EPS Estimate'] || e.estimate
              const surp = e.epsDifference || e.Surprise
              return (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '0.35rem 0.5rem', color: '#e2e8f0' }}>{String(quarter).slice(0, 10)}</td>
                  <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right', color: '#c7d2fe', fontWeight: 600 }}>{fmt(actual)}</td>
                  <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right', color: '#94a3b8' }}>{fmt(est)}</td>
                  <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right', color: surp > 0 ? '#4ade80' : surp < 0 ? '#f87171' : '#94a3b8', fontWeight: 600 }}>
                    {surp != null ? `${surp > 0 ? '+' : ''}${fmt(surp)}` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </section>
  )
}

function CapTablePanel({ data }) {
  if (!data || data.error) return null
  const inst = data.top_institutional_holders || []
  const mf = data.top_mutual_fund_holders || []
  return (
    <section className="card">
      <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Cap Table & Ownership</h2>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        {[
          ['Shares Outstanding', data.shares_outstanding ? `${(data.shares_outstanding/1e9).toFixed(2)}B` : '—'],
          ['Float Shares', data.float_shares ? `${(data.float_shares/1e9).toFixed(2)}B` : '—'],
          ['Insider %', data.insider_ownership_pct != null ? `${(data.insider_ownership_pct*100).toFixed(1)}%` : '—'],
          ['Institutional %', data.institutional_ownership_pct != null ? `${(data.institutional_ownership_pct*100).toFixed(1)}%` : '—'],
        ].map(([label, val]) => (
          <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.5rem 0.75rem', minWidth: 130 }}>
            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#c7d2fe' }}>{val}</div>
          </div>
        ))}
      </div>
      {inst.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Top Institutional Holders</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            {inst.slice(0, 10).map((h, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', padding: '0.25rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ color: '#e2e8f0', fontWeight: 600, flex: 1 }}>{h.holder}</span>
                <span style={{ color: '#94a3b8' }}>{h.pct_held ? `${(h.pct_held*100).toFixed(2)}%` : '—'}</span>
                <span style={{ color: '#c7d2fe' }}>{h.value_usd ? fmtBig(h.value_usd) : '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function FilingsPanel({ data, ticker }) {
  if (!data || !data.filings?.length) return null
  const formColors = { '10-K': '#818cf8', '10-Q': '#4ade80', '8-K': '#fbbf24', 'DEF 14A': '#94a3b8', '4': '#f87171' }
  return (
    <section className="card">
      <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Recent SEC Filings</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        {data.filings.map((f, i) => (
          <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.35rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: formColors[f.form_type] || '#94a3b8', background: `${formColors[f.form_type] || '#94a3b8'}22`, padding: '1px 6px', borderRadius: 4, minWidth: 50, textAlign: 'center' }}>
              {f.form_type}
            </span>
            <span style={{ fontSize: '0.83rem', color: '#e2e8f0', flex: 1 }}>{f.description || f.form_type + ' Filing'}</span>
            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>{f.filing_date}</span>
            <a href={f.viewer_url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: '0.68rem', color: '#818cf8', textDecoration: 'none' }}>View →</a>
          </div>
        ))}
      </div>
    </section>
  )
}

function QuarterlyPanel({ data }) {
  if (!data || data.error) return null
  const quarters = data.revenue || []
  if (!quarters.length) return null
  return (
    <section className="card">
      <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Quarterly Financials (SEC EDGAR)</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        {[
          ['Revenue', data.revenue],
          ['Net Income', data.net_income],
          ['EPS (Diluted)', data.eps_diluted],
          ['Gross Profit', data.gross_profit],
        ].map(([metric, rows]) => rows?.length ? (
          <div key={metric}>
            <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem', fontWeight: 600 }}>{metric}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              {rows.slice(0, 5).map((r, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', padding: '0.2rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <span style={{ color: '#94a3b8' }}>{r.period_end?.slice(0, 7)} {r.form && <span style={{ fontSize: '0.65rem' }}>({r.form})</span>}</span>
                  <span style={{ color: '#c7d2fe', fontWeight: 600 }}>
                    {metric.includes('EPS') ? `$${fmt(r.value)}` : fmtBig(r.value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : null)}
      </div>
    </section>
  )
}

export default function CompanyDeepPage() {
  const [ticker, setTicker] = useState('AAPL')
  const [query, setQuery] = useState('AAPL')
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  const run = async () => {
    setErr(''); setLoading(true); setData(null)
    try {
      const r = await fetch(`${API}/market/company/deep-report/${encodeURIComponent(query.toUpperCase())}`)
      const d = await r.json()
      if (d.error && !d.quarterly_financials && !d.analyst_ratings) {
        setErr(`Error: ${d.error}`)
        return
      }
      setData(d)
      setTicker(query.toUpperCase())
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  const POPULAR = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'PLTR', 'JPM', 'BAC']
  const TABS = ['overview', 'filings', 'cap-table', 'analyst', 'earnings']

  return (
    <main className="page-wrap">
      <div className="card">
        <h1 >Deep Company Analysis</h1>
        <p >SEC quarterly reports (10-K/10-Q), XBRL financials, cap table, analyst ratings, insider trades, and earnings history.</p>
      </div>

      <section className="card" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="inp" value={query} onChange={e => setQuery(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && run()}
          placeholder="e.g. AAPL" style={{ maxWidth: 160, fontWeight: 700, fontSize: '1rem' }} />
        <button className="btn btn-primary" onClick={run} disabled={loading}>
          {loading ? 'Analyzing…' : 'Deep Analyze'}
        </button>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {POPULAR.map(t => (
            <button key={t} onClick={() => { setQuery(t); setTimeout(run, 0) }}
              style={{ background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.2)', borderRadius: 5, color: '#818cf8', padding: '2px 8px', fontSize: '0.72rem', cursor: 'pointer' }}>
              {t}
            </button>
          ))}
        </div>
        {err && <p style={{color:"var(--red)",fontWeight:700}} style={{ width: '100%', margin: 0 }}>{err}</p>}
      </section>

      {data && (
        <>
          {/* Company Header */}
          {data.company_info && !data.company_info.error && (
            <section className="card" style={{ padding: '0.75rem 1rem' }}>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#e2e8f0' }}>{data.company_info.name}</div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    {data.company_info.sic_description} · {data.company_info.state_of_incorporation} · CIK {data.company_info.cik}
                  </div>
                </div>
                {data.company_info.website && (
                  <a href={data.company_info.website} target="_blank" rel="noopener noreferrer"
                    style={{ marginLeft: 'auto', fontSize: '0.8rem', color: '#818cf8', textDecoration: 'none' }}>
                    {data.company_info.website} →
                  </a>
                )}
              </div>
            </section>
          )}

          {/* Tab Nav */}
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            {TABS.map(t => (
              <button key={t} onClick={() => setActiveTab(t)}
                style={{
                  padding: '0.4rem 0.9rem', borderRadius: 6, border: '1px solid', cursor: 'pointer',
                  borderColor: activeTab === t ? '#818cf8' : 'var(--line)',
                  background: activeTab === t ? 'rgba(129,140,248,0.15)' : 'rgba(255,255,255,0.03)',
                  color: activeTab === t ? '#818cf8' : '#94a3b8', fontWeight: 600, fontSize: '0.78rem',
                  textTransform: 'capitalize',
                }}>
                {t.replace('-', ' ')}
              </button>
            ))}
          </div>

          {activeTab === 'overview' && (
            <>
              {data.analyst_ratings && <PricePanel data={{ fundamentals: {} }} t={ticker} />}
              <QuarterlyPanel data={data.quarterly_financials} />
              <AnalystPanel data={data.analyst_ratings} />
            </>
          )}
          {activeTab === 'filings' && <FilingsPanel data={data.recent_filings} ticker={ticker} />}
          {activeTab === 'cap-table' && <CapTablePanel data={data.cap_table} />}
          {activeTab === 'analyst' && <AnalystPanel data={data.analyst_ratings} />}
          {activeTab === 'earnings' && <EarningsPanel data={data.earnings_history} />}
        </>
      )}

      {!data && !loading && (
        <section className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: '#64748b' }}>Enter a ticker and click <strong style={{ color: '#818cf8' }}>Deep Analyze</strong> to get full SEC financials, cap table, analyst ratings, and earnings data.</p>
        </section>
      )}
    </main>
  )
}
