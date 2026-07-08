import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const fmt = (v, d = 2) => v == null ? '—' : typeof v === 'number' ? v.toFixed(d) : v
const fmtBig = v => {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e12) return `$${(v/1e12).toFixed(2)}T`
  if (Math.abs(v) >= 1e9)  return `$${(v/1e9).toFixed(2)}B`
  if (Math.abs(v) >= 1e6)  return `$${(v/1e6).toFixed(2)}M`
  return `$${v.toLocaleString()}`
}

const ASSESSMENT_COLORS = {
  'SIGNIFICANTLY UNDERVALUED': '#22c55e',
  'MODERATELY UNDERVALUED':    '#86efac',
  'FAIRLY VALUED':             '#facc15',
  'MODERATELY OVERVALUED':     '#fb923c',
  'SIGNIFICANTLY OVERVALUED':  '#ef4444',
  'UNKNOWN':                   '#94a3b8',
}

function AssessmentBadge({ value }) {
  const color = ASSESSMENT_COLORS[value] || '#94a3b8'
  return (
    <span style={{ background: color + '22', color, border: `1px solid ${color}55`,
      borderRadius: 8, padding: '4px 12px', fontWeight: 700, fontSize: '0.78rem', letterSpacing: '0.05em' }}>
      {value || 'UNKNOWN'}
    </span>
  )
}

function MetricCard({ label, value, sub, color }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)',
      borderRadius: 10, padding: '0.75rem 1rem', minWidth: 110, textAlign: 'center' }}>
      <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: color || '#c7d2fe' }}>{value}</div>
      {sub && <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function DCFSection({ dcf }) {
  if (!dcf || dcf.error) return <p style={{ color: '#94a3b8' }}>{dcf?.error || 'No DCF data'}</p>
  const inputs = dcf.inputs || {}
  const upside = dcf.upside_downside_pct
  const upsideColor = upside == null ? '#94a3b8' : upside > 0 ? '#22c55e' : '#ef4444'

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        <MetricCard label="Intrinsic Value" value={dcf.intrinsic_price_per_share ? `$${fmt(dcf.intrinsic_price_per_share)}` : '—'} color="#818cf8" />
        <MetricCard label="Market Price" value={dcf.current_market_price ? `$${fmt(dcf.current_market_price)}` : '—'} color="#e2e8f0" />
        <MetricCard label="Upside / Downside" value={upside != null ? `${upside > 0 ? '+' : ''}${fmt(upside)}%` : '—'} color={upsideColor} />
        <MetricCard label="Enterprise Value" value={fmtBig(dcf.enterprise_value)} color="#a5f3fc" />
        <MetricCard label="Equity Value" value={fmtBig(dcf.equity_value)} color="#86efac" />
        <MetricCard label="Net Debt" value={fmtBig(dcf.net_debt)} color="#fb923c" />
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <MetricCard label="WACC" value={`${fmt(inputs.wacc_pct)}%`} color="#f9a8d4" />
        <MetricCard label="Cost of Equity" value={`${fmt(inputs.cost_of_equity_pct)}%`} />
        <MetricCard label="FCF Growth (5yr)" value={`${fmt(inputs.fcf_growth_5y_assumed)}%`} color="#fbbf24" />
        <MetricCard label="Historical CAGR" value={`${fmt(inputs.historical_cagr_pct)}%`} />
        <MetricCard label="Terminal Growth" value={`${fmt(inputs.terminal_growth_pct)}%`} />
        <MetricCard label="Beta" value={fmt(inputs.beta)} />
        <MetricCard label="Risk-Free Rate" value={`${fmt(inputs.risk_free_rate_pct)}%`} />
      </div>

      {/* Scenarios */}
      <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Scenarios</h4>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        {['bear', 'base', 'bull'].map(s => {
          const sc = dcf.scenarios?.[s] || {}
          const color = s === 'bull' ? '#22c55e' : s === 'bear' ? '#ef4444' : '#facc15'
          return (
            <div key={s} style={{ background: color + '11', border: `1px solid ${color}33`,
              borderRadius: 10, padding: '0.75rem 1.25rem', textAlign: 'center', minWidth: 130 }}>
              <div style={{ fontSize: '0.62rem', color, textTransform: 'uppercase', fontWeight: 700 }}>{s} Case</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color, marginTop: 4 }}>
                {sc.intrinsic_price ? `$${sc.intrinsic_price}` : '—'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 2 }}>{sc.description}</div>
            </div>
          )
        })}
      </div>

      {/* FCF History */}
      {dcf.fcf_history?.length > 0 && (
        <>
          <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>FCF History</h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--line)' }}>
                  {['FY', 'Period End', 'Op Cash Flow', 'CapEx', 'Free Cash Flow'].map(h =>
                    <th key={h} style={{ textAlign: 'right', padding: '6px 12px', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {dcf.fcf_history.map((r, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '6px 12px', textAlign: 'right' }}>{r.fy}</td>
                    <td style={{ padding: '6px 12px', textAlign: 'right', color: '#94a3b8' }}>{r.period_end}</td>
                    <td style={{ padding: '6px 12px', textAlign: 'right', color: '#86efac' }}>{fmtBig(r.ocf)}</td>
                    <td style={{ padding: '6px 12px', textAlign: 'right', color: '#fb923c' }}>{fmtBig(r.capex)}</td>
                    <td style={{ padding: '6px 12px', textAlign: 'right', fontWeight: 700, color: r.fcf >= 0 ? '#22c55e' : '#ef4444' }}>{fmtBig(r.fcf)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* 5-Year Projections */}
      {dcf.projected_fcfs?.length > 0 && (
        <>
          <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', margin: '1rem 0 0.5rem' }}>5-Year FCF Projections</h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--line)' }}>
                  {['Year', 'Projected FCF', 'Present Value'].map(h =>
                    <th key={h} style={{ textAlign: 'right', padding: '6px 12px', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {dcf.projected_fcfs.map(r => (
                  <tr key={r.year} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '6px 12px', textAlign: 'right' }}>Year {r.year}</td>
                    <td style={{ padding: '6px 12px', textAlign: 'right', color: '#86efac' }}>{fmtBig(r.projected_fcf)}</td>
                    <td style={{ padding: '6px 12px', textAlign: 'right', color: '#a5f3fc' }}>{fmtBig(r.present_value)}</td>
                  </tr>
                ))}
                <tr style={{ borderTop: '2px solid var(--line)', fontWeight: 700 }}>
                  <td style={{ padding: '6px 12px', textAlign: 'right', color: '#94a3b8' }}>Terminal Value (PV)</td>
                  <td></td>
                  <td style={{ padding: '6px 12px', textAlign: 'right', color: '#c7d2fe' }}>{fmtBig(dcf.pv_terminal_value)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function FilingAnalysisSection({ fa }) {
  const [expanded, setExpanded] = useState(null)
  if (!fa || fa.error) return <p style={{ color: '#94a3b8' }}>{fa?.error || 'No filing data'}</p>
  return (
    <div>
      <p style={{ color: '#94a3b8', fontSize: '0.82rem', marginBottom: '1rem' }}>
        {fa.filings_analyzed || 0} filing(s) analyzed
      </p>
      {(fa.analyses || []).map((a, i) => (
        <div key={i} style={{ border: '1px solid var(--line)', borderRadius: 10, marginBottom: '1rem', overflow: 'hidden' }}>
          <div style={{ padding: '0.75rem 1rem', background: 'rgba(255,255,255,0.03)', display: 'flex', gap: '1rem', alignItems: 'center', cursor: 'pointer' }}
               onClick={() => setExpanded(expanded === i ? null : i)}>
            <span style={{ background: '#6366f122', color: '#818cf8', border: '1px solid #6366f144', borderRadius: 6, padding: '2px 8px', fontSize: '0.72rem', fontWeight: 700 }}>{a.form_type}</span>
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{a.filing_date}</span>
            {a.forward_guidance?.length > 0 && (
              <span style={{ color: '#fbbf24', fontSize: '0.72rem' }}>⚡ {a.forward_guidance.length} guidance signals</span>
            )}
            <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: '0.75rem' }}>{expanded === i ? '▲' : '▼'}</span>
          </div>
          {expanded === i && (
            <div style={{ padding: '1rem' }}>
              {a.forward_guidance?.length > 0 && (
                <>
                  <h5 style={{ color: '#fbbf24', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Forward Guidance</h5>
                  {a.forward_guidance.map((g, j) => (
                    <div key={j} style={{ background: 'rgba(251,191,36,0.07)', border: '1px solid rgba(251,191,36,0.2)',
                      borderRadius: 8, padding: '0.5rem 0.75rem', marginBottom: '0.4rem', fontSize: '0.82rem', color: '#fef3c7' }}>
                      <span style={{ fontSize: '0.62rem', color: '#fbbf24', textTransform: 'uppercase', marginRight: 8 }}>{g.type?.replace('_', ' ')}</span>
                      {g.text}
                    </div>
                  ))}
                </>
              )}
              {a.key_risks?.length > 0 && (
                <>
                  <h5 style={{ color: '#f87171', fontSize: '0.72rem', textTransform: 'uppercase', margin: '1rem 0 0.5rem' }}>Key Risks</h5>
                  {a.key_risks.map((r, j) => (
                    <div key={j} style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)',
                      borderRadius: 8, padding: '0.5rem 0.75rem', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#fecaca' }}>
                      {r}
                    </div>
                  ))}
                </>
              )}
              {a.mda_excerpt && (
                <>
                  <h5 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', margin: '1rem 0 0.5rem' }}>MD&A Excerpt</h5>
                  <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: 8,
                    padding: '0.75rem', fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.7, maxHeight: 300, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                    {a.mda_excerpt?.slice(0, 2000)}
                  </div>
                </>
              )}
              <a href={a.doc_url} target="_blank" rel="noreferrer"
                 style={{ color: '#6366f1', fontSize: '0.72rem', marginTop: '0.5rem', display: 'inline-block' }}>
                View full filing ↗
              </a>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function ValuationPage() {
  const [ticker, setTicker] = useState('AAPL')
  const [input, setInput] = useState('AAPL')
  const [tab, setTab] = useState('dcf')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async (t) => {
    const sym = (t || input).toUpperCase().trim()
    if (!sym) return
    setTicker(sym)
    setLoading(true)
    setError('')
    setData(null)
    try {
      const [dcfRes, faRes] = await Promise.all([
        fetch(`${API}/market/company/dcf-valuation/${sym}`),
        fetch(`${API}/market/company/filing-analysis/${sym}`),
      ])
      const [dcf, fa] = await Promise.all([dcfRes.json(), faRes.json()])
      setData({ dcf, fa })
    } catch(e) {
      setError('Failed to load: ' + e.message)
    }
    setLoading(false)
  }

  const TABS = [
    { id: 'dcf', label: '📊 DCF Valuation' },
    { id: 'filing', label: '📄 Filing Analysis' },
  ]

  return (
    <div >
      <div >
        <div>
          <h1 >Financial Valuation Engine</h1>
          <p >DCF intrinsic value · 10-K/10-Q analysis · Bull/Bear scenarios</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <input value={input} onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="Ticker (e.g. AAPL)" style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid var(--line)',
              background: 'var(--card)', color: '#e2e8f0', width: 150, fontSize: '0.9rem' }} />
          <button onClick={() => run()} disabled={loading}
            style={{ padding: '8px 18px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 700 }}>
            {loading ? '…' : 'Analyze'}
          </button>
          {['AAPL','MSFT','TSLA','NVDA','AMZN','GOOGL'].map(t => (
            <button key={t} onClick={() => { setInput(t); run(t) }}
              style={{ padding: '4px 10px', background: ticker === t ? '#6366f1' : 'rgba(255,255,255,0.05)',
                color: ticker === t ? '#fff' : '#94a3b8', border: '1px solid var(--line)', borderRadius: 6, cursor: 'pointer', fontSize: '0.75rem' }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {error && <div style={{ background: '#ef444420', border: '1px solid #ef444444', borderRadius: 8, padding: '0.75rem 1rem', color: '#fca5a5', marginBottom: '1rem' }}>{error}</div>}

      {data && (
        <>
          {/* Assessment Banner */}
          <div className="card" style={{ padding: '1rem 1.5rem', marginBottom: '1rem', display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Overall Assessment</div>
              <AssessmentBadge value={data.dcf?.assessment} />
            </div>
            {data.dcf?.synthesis?.narrative && (
              <p style={{ color: '#cbd5e1', fontSize: '0.85rem', lineHeight: 1.6, flex: 1, margin: 0 }}>
                {data.dcf.synthesis?.narrative || data.dcf?.inputs && `WACC: ${data.dcf.inputs.wacc_pct}% | FCF Growth: ${data.dcf.inputs.fcf_growth_5y_assumed}%`}
              </p>
            )}
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 0, marginBottom: '1.25rem', borderBottom: '1px solid var(--line)' }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                style={{ padding: '8px 18px', background: 'transparent', border: 'none', borderBottom: tab === t.id ? '2px solid #6366f1' : '2px solid transparent',
                  color: tab === t.id ? '#818cf8' : '#64748b', cursor: 'pointer', fontWeight: tab === t.id ? 700 : 400, fontSize: '0.85rem' }}>
                {t.label}
              </button>
            ))}
          </div>

          <div className="card">
            {tab === 'dcf' && <DCFSection dcf={data.dcf} />}
            {tab === 'filing' && <FilingAnalysisSection fa={data.fa} />}
          </div>
        </>
      )}

      {!data && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>📊</div>
          <div style={{ fontSize: '1rem', fontWeight: 600, color: '#94a3b8' }}>Enter a ticker to run DCF valuation</div>
          <div style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>Analyzes SEC EDGAR XBRL financials · 10-K/10-Q management guidance · Intrinsic vs market price</div>
        </div>
      )}
    </div>
  )
}
