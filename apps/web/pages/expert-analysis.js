import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const SENTIMENT_COLORS = { bullish: '#22c55e', bearish: '#ef4444', neutral: '#94a3b8', BULLISH: '#22c55e', BEARISH: '#ef4444', NEUTRAL: '#94a3b8' }

function SentimentBar({ bullish, bearish, neutral }) {
  const total = (bullish || 0) + (bearish || 0) + (neutral || 0) || 1
  return (
    <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', marginTop: 4 }}>
      <div style={{ width: `${(bullish/total)*100}%`, background: '#22c55e' }} />
      <div style={{ width: `${(neutral/total)*100}%`, background: '#64748b' }} />
      <div style={{ width: `${(bearish/total)*100}%`, background: '#ef4444' }} />
    </div>
  )
}

function TrendChart({ weeks }) {
  if (!weeks?.length) return null
  const maxScore = 1
  const w = 680, h = 120, pad = 20
  const pts = weeks.slice(0, 12).reverse()
  const xStep = (w - 2*pad) / Math.max(pts.length - 1, 1)
  const yMid = h / 2
  const yScale = (h/2 - pad) / maxScore

  const points = pts.map((p, i) => ({
    x: pad + i * xStep,
    y: yMid - (p.net_sentiment_score || 0) * yScale,
    score: p.net_sentiment_score,
    week: p.week,
    total: p.total_articles,
  }))

  const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 120, overflow: 'visible' }}>
      <line x1={pad} y1={yMid} x2={w-pad} y2={yMid} stroke="rgba(255,255,255,0.1)" strokeDasharray="4,4" />
      <path d={pathData} fill="none" stroke="#6366f1" strokeWidth={2} />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r={4} fill={p.score > 0.1 ? '#22c55e' : p.score < -0.1 ? '#ef4444' : '#facc15'} />
          <text x={p.x} y={h - 4} fontSize={8} fill="#64748b" textAnchor="middle">
            {p.week?.slice(5) || ''}
          </text>
        </g>
      ))}
    </svg>
  )
}

function AnalystTimeline({ events }) {
  if (!events?.length) return <p style={{ color: '#64748b', fontSize: '0.82rem' }}>No analyst events found</p>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {events.slice(0, 20).map((e, i) => {
        const color = SENTIMENT_COLORS[e.sentiment] || '#94a3b8'
        return (
          <div key={i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', padding: '0.5rem 0.75rem',
            background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: 8 }}>
            <span style={{ color: '#64748b', fontSize: '0.75rem', minWidth: 85 }}>{e.date}</span>
            <span style={{ background: color + '22', color, border: `1px solid ${color}44`, borderRadius: 5,
              padding: '2px 8px', fontSize: '0.7rem', fontWeight: 700, minWidth: 70, textAlign: 'center' }}>{e.action || e.sentiment}</span>
            <span style={{ color: '#cbd5e1', fontWeight: 600, fontSize: '0.82rem' }}>{e.firm || 'Unknown'}</span>
            {e.from_grade && <span style={{ color: '#64748b', fontSize: '0.75rem' }}>{e.from_grade} →</span>}
            <span style={{ color, fontSize: '0.82rem', fontWeight: 700 }}>{e.to_grade}</span>
          </div>
        )
      })}
    </div>
  )
}

function ThemeCloud({ themes }) {
  if (!themes?.length) return null
  const max = themes[0]?.mentions || 1
  return (
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
      {themes.map(t => {
        const size = 0.7 + (t.mentions / max) * 0.5
        const opacity = 0.4 + (t.mentions / max) * 0.6
        return (
          <span key={t.theme} style={{ background: `rgba(99,102,241,${opacity * 0.2})`,
            color: `rgba(165,180,252,${opacity})`, border: `1px solid rgba(99,102,241,${opacity * 0.4})`,
            borderRadius: 20, padding: `${4 * size}px ${10 * size}px`, fontSize: `${size * 0.8}rem`, fontWeight: 600 }}>
            {t.theme} <span style={{ opacity: 0.7, fontSize: '0.65em' }}>({t.mentions})</span>
          </span>
        )
      })}
    </div>
  )
}

function ArticleCard({ a }) {
  const color = SENTIMENT_COLORS[a.sentiment] || '#94a3b8'
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '0.75rem 1rem',
      marginBottom: '0.6rem', borderLeft: `3px solid ${color}` }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
        <span style={{ background: color + '22', color, border: `1px solid ${color}44`, borderRadius: 5,
          padding: '1px 7px', fontSize: '0.65rem', fontWeight: 700 }}>{a.sentiment}</span>
        {a.is_analyst_report && <span style={{ background: '#fbbf2422', color: '#fbbf24', border: '1px solid #fbbf2444', borderRadius: 5, padding: '1px 7px', fontSize: '0.65rem', fontWeight: 700 }}>Analyst</span>}
        <span style={{ color: '#64748b', fontSize: '0.7rem' }}>{a.source}</span>
        <span style={{ color: '#475569', fontSize: '0.7rem', marginLeft: 'auto' }}>{a.published?.slice(0, 10)}</span>
      </div>
      <a href={a.url} target="_blank" rel="noreferrer"
        style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '0.85rem', textDecoration: 'none', lineHeight: 1.4, display: 'block' }}>
        {a.title}
      </a>
      {a.summary && <p style={{ color: '#94a3b8', fontSize: '0.77rem', marginTop: '0.3rem', lineHeight: 1.5 }}>{a.summary?.slice(0, 200)}</p>}
    </div>
  )
}

export default function ExpertAnalysisPage() {
  const [ticker, setTicker] = useState('AAPL')
  const [input, setInput] = useState('AAPL')
  const [companyInput, setCompanyInput] = useState('')
  const [tab, setTab] = useState('overview')
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
      const res = await fetch(`${API}/market/company/expert-analysis/${sym}?company=${encodeURIComponent(companyInput)}`)
      const d = await res.json()
      setData(d)
    } catch(e) {
      setError('Failed to load: ' + e.message)
    }
    setLoading(false)
  }

  const s = data?.summary || {}
  const netColor = s.net_sentiment_score > 0.1 ? '#22c55e' : s.net_sentiment_score < -0.1 ? '#ef4444' : '#facc15'

  const TABS = [
    { id: 'overview', label: '📊 Overview' },
    { id: 'trend', label: '📈 Sentiment Trend' },
    { id: 'themes', label: '🔍 Key Themes' },
    { id: 'analyst', label: '🏦 Analyst Timeline' },
    { id: 'articles', label: '📰 Articles' },
  ]

  return (
    <div >
      <div >
        <div>
          <h1 >Expert Analysis Tracker</h1>
          <p >Analyst ratings · News sentiment · Themes · Weekly trend</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <input value={input} onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="Ticker" style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--card)', color: '#e2e8f0', width: 100 }} />
          <input value={companyInput} onChange={e => setCompanyInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="Company name (optional)" style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--card)', color: '#e2e8f0', width: 200, fontSize: '0.85rem' }} />
          <button onClick={() => run()} disabled={loading}
            style={{ padding: '8px 18px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 700 }}>
            {loading ? '…' : 'Analyze'}
          </button>
          {['AAPL','MSFT','TSLA','NVDA','GOOGL'].map(t => (
            <button key={t} onClick={() => { setInput(t); run(t) }}
              style={{ padding: '4px 10px', background: ticker === t ? '#6366f1' : 'rgba(255,255,255,0.05)',
                color: ticker === t ? '#fff' : '#94a3b8', border: '1px solid var(--line)', borderRadius: 6, cursor: 'pointer', fontSize: '0.75rem' }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {error && <div style={{ background: '#ef444420', border: '1px solid #ef444444', borderRadius: 8, padding: '0.75rem', color: '#fca5a5', marginBottom: '1rem' }}>{error}</div>}

      {data && (
        <>
          {/* Summary Bar */}
          <div className="card" style={{ padding: '1rem 1.5rem', marginBottom: '1rem', display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Overall Sentiment</div>
              <span style={{ background: SENTIMENT_COLORS[s.overall_sentiment] + '22', color: SENTIMENT_COLORS[s.overall_sentiment],
                border: `1px solid ${SENTIMENT_COLORS[s.overall_sentiment]}44`, borderRadius: 8, padding: '4px 14px', fontWeight: 700, fontSize: '0.85rem' }}>
                {s.overall_sentiment}
              </span>
            </div>
            {[
              ['Articles', s.total_articles],
              ['Bullish', s.bullish],
              ['Bearish', s.bearish],
              ['Analyst Reports', s.analyst_reports],
              ['Net Score', s.net_sentiment_score?.toFixed(3)],
            ].map(([label, val]) => (
              <div key={label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: label === 'Bullish' ? '#22c55e' : label === 'Bearish' ? '#ef4444' : label === 'Net Score' ? netColor : '#c7d2fe' }}>{val ?? '—'}</div>
              </div>
            ))}
            <div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Recent Trend</div>
              <span style={{ color: s.recent_trend === 'IMPROVING' ? '#22c55e' : s.recent_trend === 'DETERIORATING' ? '#ef4444' : '#facc15', fontWeight: 700, fontSize: '0.85rem' }}>
                {s.recent_trend === 'IMPROVING' ? '↑ IMPROVING' : s.recent_trend === 'DETERIORATING' ? '↓ DETERIORATING' : '→ STABLE'}
              </span>
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 0, marginBottom: '1.25rem', borderBottom: '1px solid var(--line)' }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                style={{ padding: '8px 16px', background: 'transparent', border: 'none',
                  borderBottom: tab === t.id ? '2px solid #6366f1' : '2px solid transparent',
                  color: tab === t.id ? '#818cf8' : '#64748b', cursor: 'pointer', fontWeight: tab === t.id ? 700 : 400, fontSize: '0.82rem' }}>
                {t.label}
              </button>
            ))}
          </div>

          <div className="card">
            {tab === 'overview' && (
              <div>
                <SentimentBar bullish={s.bullish} bearish={s.bearish} neutral={s.neutral} />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#64748b', marginTop: 4 }}>
                  <span style={{ color: '#22c55e' }}>Bullish {s.bullish}</span>
                  <span>Neutral {s.neutral}</span>
                  <span style={{ color: '#ef4444' }}>Bearish {s.bearish}</span>
                </div>
                <div style={{ marginTop: '1.5rem' }}>
                  <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Top Analyst Articles</h4>
                  {(data.top_analyst_articles || []).slice(0, 5).map((a, i) => <ArticleCard key={i} a={a} />)}
                  {!data.top_analyst_articles?.length && <p style={{ color: '#64748b', fontSize: '0.82rem' }}>No analyst articles found</p>}
                </div>
              </div>
            )}
            {tab === 'trend' && (
              <div>
                <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Weekly Sentiment Score</h4>
                <TrendChart weeks={data.weekly_sentiment_trend} />
                <div style={{ marginTop: '1rem', overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--line)' }}>
                        {['Week', 'Total', '🟢 Bullish', '🔴 Bearish', 'Neutral', 'Analyst', 'Net Score'].map(h =>
                          <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {(data.weekly_sentiment_trend || []).map((w, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                          <td style={{ padding: '6px 10px', textAlign: 'right', color: '#94a3b8' }}>{w.week}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right' }}>{w.total_articles}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', color: '#22c55e' }}>{w.bullish}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', color: '#ef4444' }}>{w.bearish}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', color: '#94a3b8' }}>{w.neutral}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', color: '#fbbf24' }}>{w.analyst_reports}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', color: w.net_sentiment_score > 0.1 ? '#22c55e' : w.net_sentiment_score < -0.1 ? '#ef4444' : '#94a3b8', fontWeight: 700 }}>
                            {w.net_sentiment_score?.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {tab === 'themes' && (
              <div>
                <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '1rem' }}>Key Topics & Themes</h4>
                <ThemeCloud themes={data.key_themes} />
                <div style={{ marginTop: '1.5rem', overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--line)' }}>
                        {['Theme', 'Mentions'].map(h =>
                          <th key={h} style={{ padding: '6px 12px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {(data.key_themes || []).map((t, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                          <td style={{ padding: '6px 12px', textAlign: 'right', fontWeight: 600 }}>{t.theme}</td>
                          <td style={{ padding: '6px 12px', textAlign: 'right', color: '#818cf8' }}>{t.mentions}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {tab === 'analyst' && <AnalystTimeline events={data.analyst_timeline} />}
            {tab === 'articles' && (
              <div>
                <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Recent Articles</h4>
                {(data.recent_articles || []).map((a, i) => <ArticleCard key={i} a={a} />)}
              </div>
            )}
          </div>
        </>
      )}

      {!data && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🏦</div>
          <div style={{ fontSize: '1rem', fontWeight: 600, color: '#94a3b8' }}>Enter a ticker to track expert analysis</div>
          <div style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>Aggregates analyst upgrades/downgrades · News sentiment · Weekly trend · Key themes</div>
        </div>
      )}
    </div>
  )
}
