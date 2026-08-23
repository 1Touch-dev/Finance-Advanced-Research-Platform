import { useState } from 'react'
import Link from 'next/link'
import { getApiBaseUrl , apiFetch } from '../lib/api'
import { LineChart, Line, ResponsiveContainer, Tooltip, ReferenceLine, XAxis } from 'recharts'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const fmt = (v, d = 2) => v == null ? '—' : typeof v === 'number' ? v.toFixed(d) : v
const fmtBig = v => {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (Math.abs(v) >= 1e9)  return `$${(v / 1e9).toFixed(2)}B`
  if (Math.abs(v) >= 1e6)  return `$${(v / 1e6).toFixed(2)}M`
  return `$${v.toLocaleString()}`
}
const pct = v => v == null ? '—' : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%`
const QUICK = ['AAPL','MSFT','TSLA','NVDA','AMZN','GOOGL','META','BRK-B']

const SIGNAL_COLOR = { BUY: '#10b981', SELL: '#ef4444', HOLD: '#f59e0b', STRONG_BUY: '#059669', STRONG_SELL: '#dc2626' }
const SENT_COLOR   = { bullish: '#10b981', bearish: '#ef4444', neutral: '#f59e0b', mixed: '#94a3b8' }

function PriceHero({ data, ticker }) {
  const f = data?.fundamentals || {}
  const p = data?.price || {}
  const price = p.current_price || f.currentPrice || 0
  const prev  = p.previous_close || f.previousClose || price
  const chg   = price - prev
  const chgPct= prev > 0 ? (chg / prev) * 100 : 0
  const isUp  = chg >= 0

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(99,102,241,0.1), transparent), var(--bg-elev-1)',
      border: '1px solid var(--line-md)',
      borderRadius: 'var(--radius-lg)',
      padding: '1.5rem 1.75rem',
      display: 'flex',
      gap: '2rem',
      flexWrap: 'wrap',
      alignItems: 'center',
    }}>
      {/* Price block */}
      <div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
          {ticker} · {f.longName || f.shortName || ticker}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <span style={{ fontSize: '2.4rem', fontWeight: 900, letterSpacing: '-0.04em', color: '#f1f5f9' }}>
            ${fmt(price)}
          </span>
          <span style={{ fontSize: '1rem', fontWeight: 700, color: isUp ? '#10b981' : '#ef4444' }}>
            {isUp ? '▲' : '▼'} {fmt(Math.abs(chg))} ({fmt(Math.abs(chgPct))}%)
          </span>
        </div>
        {f.exchange && (
          <div style={{ fontSize: '0.7rem', color: 'var(--text-soft)', marginTop: 2 }}>{f.exchange} · {f.currency || 'USD'}</div>
        )}
      </div>

      {/* Metric chips */}
      <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', flex: 1 }}>
        {[
          ['Mkt Cap',     fmtBig(f.marketCap)],
          ['P/E',         fmt(f.trailingPE || f.forwardPE)],
          ['Fwd P/E',     fmt(f.forwardPE)],
          ['EPS (TTM)',   fmt(f.trailingEps)],
          ['Fwd EPS',     fmt(f.forwardEps)],
          ['Beta',        fmt(f.beta)],
          ['Div Yield',   f.dividendYield != null ? `${(f.dividendYield * 100).toFixed(2)}%` : '—'],
          ['Gross Margin',f.grossMargins != null ? `${(f.grossMargins * 100).toFixed(1)}%` : '—'],
          ['Op Margin',   f.operatingMargins != null ? `${(f.operatingMargins * 100).toFixed(1)}%` : '—'],
          ['Debt/Equity', fmt(f.debtToEquity)],
          ['ROE',         f.returnOnEquity != null ? `${(f.returnOnEquity * 100).toFixed(1)}%` : '—'],
          ['Revenue',     fmtBig(f.totalRevenue)],
        ].map(([label, val]) => (
          <div key={label} style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--line)',
            borderRadius: 8,
            padding: '6px 12px',
            minWidth: 80,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#c7d2fe' }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Links */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignSelf: 'flex-start' }}>
        <Link href={`/company?ticker=${ticker}`}>
          <a className="btn btn-outline btn-sm">Deep Analysis →</a>
        </Link>
        <Link href={`/valuation?ticker=${ticker}`}>
          <a className="btn btn-outline btn-sm">DCF Valuation →</a>
        </Link>
      </div>
    </div>
  )
}

function TechPanel({ tech }) {
  if (!tech || tech.error) return null
  const ind = tech.indicators || {}
  const sig = tech.signal || {}

  // Helper: get last value from array or scalar
  const last = v => Array.isArray(v) ? v.filter(x => x != null).slice(-1)[0] : v

  const rsi   = last(ind.rsi_14 || ind.rsi)
  const macd  = last(ind.macd?.macd)
  const macdS = last(ind.macd?.signal)
  const bbU   = last(ind.bollinger?.upper)
  const bbL   = last(ind.bollinger?.lower)
  const sma20 = last(ind.sma_20 || ind.sma20)
  const sma50 = last(ind.sma_50 || ind.sma50)
  const atr   = last(ind.atr_14 || ind.atr)

  const TECH_ITEMS = [
    { label: 'RSI (14)', value: fmt(rsi), color: rsi > 70 ? '#ef4444' : rsi < 30 ? '#10b981' : '#e2e8f0' },
    { label: 'MACD',     value: fmt(macd), color: macd > 0 ? '#10b981' : '#ef4444' },
    { label: 'Signal',   value: fmt(macdS) },
    { label: 'BB Upper', value: `$${fmt(bbU)}` },
    { label: 'BB Lower', value: `$${fmt(bbL)}` },
    { label: 'SMA 20',   value: `$${fmt(sma20)}` },
    { label: 'SMA 50',   value: `$${fmt(sma50)}` },
    { label: 'ATR',      value: fmt(atr) },
  ]

  return (
    <div className="card" style={{ padding: '1rem 1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div className="section-title" style={{ margin: 0 }}>Technical Indicators</div>
        {sig.overall && (
          <span className="badge" style={{ color: SIGNAL_COLOR[sig.overall] || '#94a3b8', background: `${SIGNAL_COLOR[sig.overall] || '#94a3b8'}18`, borderColor: `${SIGNAL_COLOR[sig.overall] || '#94a3b8'}33` }}>
            {sig.overall}
          </span>
        )}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
        {TECH_ITEMS.map(({ label, value, color }) => (
          <div key={label} style={{ background: 'rgba(255,255,255,0.025)', borderRadius: 8, padding: '8px 10px', border: '1px solid var(--line)' }}>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: color || '#c7d2fe', marginTop: 2 }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AgentPanel({ intel }) {
  if (!intel) return null
  const agents = [
    { key: 'fundamentals', label: 'Fundamentals', icon: '◎', color: '#6366f1' },
    { key: 'technical',    label: 'Technical',    icon: '▲', color: '#06b6d4' },
    { key: 'sentiment',    label: 'Sentiment',    icon: '◈', color: '#10b981' },
    { key: 'risk',         label: 'Risk',         icon: '⚑', color: '#f59e0b' },
  ]

  return (
    <div className="card" style={{ padding: '1rem 1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div className="section-title" style={{ margin: 0 }}>4-Agent AI Consensus</div>
        {intel.final_verdict?.signal && (
          <span className="badge" style={{ color: SIGNAL_COLOR[intel.final_verdict.signal] || '#94a3b8', background: `${SIGNAL_COLOR[intel.final_verdict.signal] || '#94a3b8'}18`, borderColor: `${SIGNAL_COLOR[intel.final_verdict.signal] || '#94a3b8'}33`, fontSize: '0.72rem' }}>
            {intel.final_verdict.signal} · {fmt(intel.final_verdict.confidence_score * 100, 0)}% confidence
          </span>
        )}
      </div>

      {/* Summary */}
      {intel.final_verdict?.summary && (
        <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid var(--line)', borderRadius: 8, padding: '10px 12px', fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.6, marginBottom: '0.75rem' }}>
          {intel.final_verdict.summary}
        </div>
      )}

      {/* Agent cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
        {agents.map(({ key, label, icon, color }) => {
          const agent = intel[key] || {}
          const sig = agent.signal || agent.overall_signal || '—'
          const conf = agent.confidence
          return (
            <div key={key} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: 8, padding: '10px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ color, fontSize: '0.8rem' }}>{icon}</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#e2e8f0' }}>{label}</span>
                <span className="badge" style={{ marginLeft: 'auto', fontSize: '0.62rem', color: SIGNAL_COLOR[sig] || '#94a3b8', background: `${SIGNAL_COLOR[sig] || '#94a3b8'}15`, borderColor: `${SIGNAL_COLOR[sig] || '#94a3b8'}30` }}>
                  {sig}
                </span>
              </div>
              {conf != null && (
                <div style={{ height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 99, overflow: 'hidden' }}>
                  <div style={{ width: `${conf * 100}%`, height: '100%', background: color, borderRadius: 99 }} />
                </div>
              )}
              {agent.key_points?.slice(0, 2).map((pt, i) => (
                <div key={i} style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4, paddingLeft: 4, borderLeft: `2px solid ${color}44` }}>{pt}</div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AnalystPanel({ analyst }) {
  if (!analyst) return null
  const cons = analyst.consensus || {}
  const targets = analyst.price_targets || {}
  const upgrades = analyst.upgrades_downgrades || []
  const recs = analyst.recommendations_detail || []

  const GRADES = [
    { k: 'strong_buy', label: 'Strong Buy', color: '#059669' },
    { k: 'buy',        label: 'Buy',         color: '#10b981' },
    { k: 'hold',       label: 'Hold',        color: '#f59e0b' },
    { k: 'sell',       label: 'Sell',        color: '#ef4444' },
    { k: 'strong_sell',label: 'Strong Sell', color: '#dc2626' },
  ]
  const totalRecs = GRADES.reduce((s, g) => s + (recs[0]?.[g.k] || 0), 0) || 1

  return (
    <div className="card" style={{ padding: '1rem 1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div className="section-title" style={{ margin: 0 }}>Analyst Consensus</div>
        {cons.recommendation_mean && (
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Mean: <b style={{ color: '#e2e8f0' }}>{fmt(cons.recommendation_mean)}</b></span>
        )}
      </div>

      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {targets.current && (
          <div>
            <div className="stat-label">Price Target</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#10b981' }}>${fmt(targets.current)}</div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-soft)' }}>High: ${fmt(targets.high)} · Low: ${fmt(targets.low)}</div>
          </div>
        )}
        {cons.number_of_analyst_opinions && (
          <div>
            <div className="stat-label">Analysts</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#c7d2fe' }}>{cons.number_of_analyst_opinions}</div>
          </div>
        )}
      </div>

      {/* Recommendation bar */}
      {recs.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', height: 8, borderRadius: 99, overflow: 'hidden', gap: 1 }}>
            {GRADES.map(g => {
              const count = recs[0]?.[g.k] || 0
              return count > 0 ? (
                <div key={g.k} style={{ width: `${(count / totalRecs) * 100}%`, background: g.color, minWidth: 2 }} title={`${g.label}: ${count}`} />
              ) : null
            })}
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: 6, flexWrap: 'wrap' }}>
            {GRADES.map(g => {
              const count = recs[0]?.[g.k] || 0
              return count > 0 ? (
                <span key={g.k} style={{ fontSize: '0.65rem', color: g.color }}>{g.label}: {count}</span>
              ) : null
            })}
          </div>
        </div>
      )}

      {/* Recent upgrades */}
      {upgrades.length > 0 && (
        <div>
          <div className="section-title">Recent Rating Changes</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {upgrades.slice(0, 5).map((u, i) => {
              const to = u.to_grade || ''
              const color = SIGNAL_COLOR[to.replace(' ', '_').toUpperCase()] || (to.toLowerCase().includes('buy') ? '#10b981' : to.toLowerCase().includes('sell') ? '#ef4444' : '#94a3b8')
              return (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.75rem', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <span style={{ color: 'var(--text-soft)', minWidth: 80 }}>{u.date?.slice(0, 10)}</span>
                  <span style={{ color: '#e2e8f0', fontWeight: 600, flex: 1 }}>{u.firm}</span>
                  {u.from_grade && <span style={{ color: 'var(--text-soft)' }}>{u.from_grade} →</span>}
                  <span style={{ color, fontWeight: 700 }}>{u.to_grade}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function SkeletonCard({ rows = 4 }) {
  return (
    <div className="card" style={{ padding: '1rem 1.25rem' }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 14, marginBottom: 10, width: `${60 + Math.random() * 35}%` }} />
      ))}
    </div>
  )
}

export default function StockPage() {
  const [ticker, setTicker] = useState('AAPL')
  const [input, setInput] = useState('AAPL')
  const [data, setData] = useState(null)
  const [tech, setTech] = useState(null)
  const [intel, setIntel] = useState(null)
  const [analyst, setAnalyst] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const run = async (t) => {
    const sym = (t || input).toUpperCase().trim()
    if (!sym) return
    setTicker(sym)
    setLoading(true)
    setErr('')
    setData(null); setTech(null); setIntel(null); setAnalyst(null)
    try {
      const [r1, r2, r3, r4] = await Promise.allSettled([
        apiFetch(`/market/yf/snapshot?ticker=${sym}`).then(r => r.json()),
        apiFetch(`/market/technicals?ticker=${sym}`).then(r => r.json()),
        apiFetch(`/market/intelligence/report?ticker=${sym}&company=${sym}`).then(r => r.json()),
        apiFetch(`/market/company/analyst-ratings/${sym}`).then(r => r.json()),
      ])
      if (r1.status === 'fulfilled') setData(r1.value)
      if (r2.status === 'fulfilled') setTech(r2.value)
      if (r3.status === 'fulfilled') setIntel(r3.value)
      if (r4.status === 'fulfilled') setAnalyst(r4.value)
    } catch (e) { setErr(e.message) }
    setLoading(false)
  }

  return (
    <div className="page-wrap">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Stock Analysis</h1>
          <p className="page-sub">Fundamentals · Technicals · AI consensus · Analyst ratings</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            className="inp"
            value={input}
            onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="Ticker"
            style={{ width: 90, textTransform: 'uppercase', fontWeight: 700 }}
          />
          <button className="btn btn-primary" onClick={() => run()} disabled={loading}>
            {loading ? '…' : 'Analyze'}
          </button>
        </div>
      </div>

      {/* Quick picks */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {QUICK.map(t => (
          <button key={t} className="btn btn-ghost btn-sm"
            onClick={() => { setInput(t); run(t) }}
            style={{ color: ticker === t ? 'var(--brand-hover)' : undefined, borderColor: ticker === t ? 'rgba(99,102,241,0.5)' : undefined, background: ticker === t ? 'var(--brand-glow)' : undefined }}>
            {t}
          </button>
        ))}
        <Link href={`/expert-analysis?ticker=${ticker}`}>
          <a className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto', color: 'var(--cyan)' }}>Expert Analysis →</a>
        </Link>
      </div>

      {err && <div className="badge badge-red" style={{ padding: '8px 12px', borderRadius: 8 }}>{err}</div>}

      {/* Loading skeletons */}
      {loading && (
        <div style={{ display: 'grid', gap: '1rem' }}>
          <SkeletonCard rows={3} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <SkeletonCard rows={5} /><SkeletonCard rows={5} />
          </div>
        </div>
      )}

      {/* Content */}
      {!loading && data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <PriceHero data={data} ticker={ticker} />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <TechPanel tech={tech} />
            <AnalystPanel analyst={analyst} />
          </div>

          <AgentPanel intel={intel} />

          {/* Company description */}
          {data?.fundamentals?.longBusinessSummary && (
            <div className="card" style={{ padding: '1rem 1.25rem' }}>
              <div className="section-title">Company Overview</div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', lineHeight: 1.7, margin: 0 }}>
                {data.fundamentals.longBusinessSummary}
              </p>
            </div>
          )}
        </div>
      )}

      {!loading && !data && (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>▲</div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: '#94a3b8' }}>Enter a ticker to begin analysis</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-soft)', marginTop: '0.4rem' }}>Supports all NYSE, NASDAQ, and global exchange symbols</div>
        </div>
      )}
    </div>
  )
}
