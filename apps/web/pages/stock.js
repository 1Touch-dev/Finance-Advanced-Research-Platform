import { useState } from 'react'
import Link from 'next/link'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

export default function Stock(){
  const API = getApiBaseUrl()
  const [t,setT]=useState('AAPL')
  const [data,setData]=useState(null)
  const [tech,setTech]=useState(null)
  const [intel,setIntel]=useState(null)
  const [analyst,setAnalyst]=useState(null)
  const [err,setErr]=useState('')
  const [loading,setLoading]=useState(false)

  const run=async()=>{
    setErr(''); setLoading(true); setData(null); setTech(null); setIntel(null); setAnalyst(null)
    try {
      const [r1, r2, r3, r4] = await Promise.allSettled([
        fetch(`${API}/market/yf/snapshot?ticker=${encodeURIComponent(t)}`).then(r=>r.json()),
        fetch(`${API}/market/technicals?ticker=${encodeURIComponent(t)}`).then(r=>r.json()),
        fetch(`${API}/market/intelligence/report?ticker=${encodeURIComponent(t)}&company=${encodeURIComponent(t)}`).then(r=>r.json()),
        fetch(`${API}/market/company/analyst-ratings/${encodeURIComponent(t)}`).then(r=>r.json()),
      ])
      if (r1.status==='fulfilled') setData(r1.value)
      if (r2.status==='fulfilled') setTech(r2.value)
      if (r3.status==='fulfilled') setIntel(r3.value)
      if (r4.status==='fulfilled') setAnalyst(r4.value)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  const fmt=(v,d=2)=>v==null?'—':typeof v==='number'?v.toFixed(d):v
  const pct=(v)=>v==null?'—':`${v>0?'+':''}${(v*100).toFixed(1)}%`

  const fundamentals = data?.fundamentals || {}
  const price = data?.price || {}
  const signals = tech?.summary?.signals || []
  const trend = tech?.summary?.trend || ''
  const recColors = { BUY: '#4ade80', STRONG_BUY: '#4ade80', HOLD: '#fbbf24', SELL: '#f87171', STRONG_SELL: '#f87171', UNDERPERFORM: '#f87171' }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Stock Analysis</h1>
        <p>Real-time quote · 15 technical indicators · multi-agent intelligence score · analyst consensus</p>
      </section>

      {/* Ticker input */}
      <section className={styles.panel} style={{ display:'flex', gap:'0.75rem', alignItems:'center', flexWrap:'wrap' }}>
        <input className={styles.input} value={t} onChange={e=>setT(e.target.value.toUpperCase())}
          onKeyDown={e=>e.key==='Enter'&&run()} placeholder="e.g. AAPL"
          style={{ maxWidth:180, fontSize:'1rem', fontWeight:700 }} />
        <button className={styles.button} onClick={run} disabled={loading}>
          {loading ? 'Loading…' : 'Analyze'}
        </button>
        <span style={{ fontSize:'0.75rem', color:'var(--text-muted)' }}>
          {['AAPL','TSLA','NVDA','MSFT','GOOGL','META','AMZN','PLTR'].map(tk=>(
            <button key={tk} onClick={()=>{setT(tk);setTimeout(run,0)}}
              style={{ background:'rgba(129,140,248,0.1)', border:'1px solid rgba(129,140,248,0.2)', borderRadius:5,
                color:'#818cf8', padding:'2px 8px', fontSize:'0.72rem', cursor:'pointer', marginRight:4 }}>{tk}</button>
          ))}
        </span>
        {data && (
          <Link href={`/company?t=${t}`} passHref>
            <a style={{ marginLeft:'auto', fontSize:'0.75rem', color:'#818cf8', textDecoration:'none', border:'1px solid rgba(129,140,248,0.3)', borderRadius:6, padding:'0.35rem 0.75rem' }}>
              Deep Company Analysis →
            </a>
          </Link>
        )}
        {err && <p className={styles.dangerText} style={{ width:'100%', margin:0 }}>{err}</p>}
      </section>

      {data && (
        <>
          {/* Price Row */}
          <section className={styles.panel}>
            <div style={{ display:'flex', gap:'1rem', flexWrap:'wrap', alignItems:'flex-end' }}>
              <div>
                <div style={{ fontSize:'0.68rem', color:'var(--text-muted)', textTransform:'uppercase', letterSpacing:'0.05em' }}>Price — {t}</div>
                <div style={{ fontSize:'2rem', fontWeight:800, color:'#e2e8f0' }}>${fmt(price.current_price||fundamentals.currentPrice)}</div>
              </div>
              {[['Market Cap', fundamentals.marketCap ? `$${(fundamentals.marketCap/1e9).toFixed(1)}B` : '—'],
                ['P/E', fmt(fundamentals.trailingPE||fundamentals.forwardPE)],
                ['EPS', fmt(fundamentals.trailingEps)],
                ['Beta', fmt(fundamentals.beta)],
                ['52W High', `$${fmt(fundamentals['52WeekHigh']||fundamentals.fiftyTwoWeekHigh)}`],
                ['52W Low', `$${fmt(fundamentals['52WeekLow']||fundamentals.fiftyTwoWeekLow)}`],
                ['Div Yield', fundamentals.dividendYield != null ? `${(fundamentals.dividendYield * 100).toFixed(2)}%` : '—'],
              ].map(([label, val]) => (
                <div key={label} style={{ textAlign:'center', background:'rgba(255,255,255,0.03)',
                  border:'1px solid var(--line)', borderRadius:8, padding:'0.5rem 0.75rem', minWidth:80 }}>
                  <div style={{ fontSize:'0.65rem', color:'var(--text-muted)', textTransform:'uppercase' }}>{label}</div>
                  <div style={{ fontSize:'1rem', fontWeight:700, color:'#c7d2fe' }}>{val}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Fundamentals + Technicals */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1rem' }}>
            <section className={styles.panel}>
              <h2 style={{ marginBottom:'0.75rem', fontSize:'1rem' }}>Fundamentals</h2>
              {[['Net Margin', pct(fundamentals.profitMargins)],
                ['Gross Margin', pct(fundamentals.grossMargins)],
                ['ROE', pct(fundamentals.returnOnEquity)],
                ['Revenue (TTM)', fundamentals.totalRevenue ? `$${(fundamentals.totalRevenue/1e9).toFixed(1)}B` : '—'],
                ['Total Debt', fundamentals.totalDebt ? `$${(fundamentals.totalDebt/1e9).toFixed(1)}B` : '—'],
                ['Free Cash Flow', fundamentals.freeCashflow ? `$${(fundamentals.freeCashflow/1e9).toFixed(1)}B` : '—'],
                ['Employees', fundamentals.fullTimeEmployees?.toLocaleString() || '—'],
              ].map(([k,v])=>(
                <div key={k} style={{ display:'flex', justifyContent:'space-between', padding:'0.3rem 0',
                  borderBottom:'1px solid rgba(255,255,255,0.05)', fontSize:'0.85rem' }}>
                  <span style={{ color:'#94a3b8' }}>{k}</span>
                  <span style={{ color:'#e2e8f0', fontWeight:600 }}>{v}</span>
                </div>
              ))}
            </section>

            {tech && (
              <section className={styles.panel}>
                <h2 style={{ marginBottom:'0.75rem', fontSize:'1rem' }}>
                  Technical Signals
                  {trend && <span style={{ marginLeft:'0.5rem', fontSize:'0.75rem', color: trend.includes('up')?'#4ade80':'#f87171',
                    background: trend.includes('up')?'rgba(74,222,128,0.1)':'rgba(248,113,113,0.1)',
                    padding:'2px 7px', borderRadius:5 }}>{trend}</span>}
                </h2>
                {[['SMA 50', `$${fmt(tech.summary?.sma50)}`],
                  ['SMA 200', `$${fmt(tech.summary?.sma200)}`],
                  ['RSI (14)', fmt(tech.summary?.rsi)],
                  ['MACD Hist', fmt(tech.summary?.macd_hist)],
                  ['Bollinger Upper', `$${fmt(tech.summary?.bb_upper)}`],
                  ['Bollinger Lower', `$${fmt(tech.summary?.bb_lower)}`],
                  ['ATR (14)', fmt(tech.summary?.atr)],
                ].map(([k,v])=>(
                  <div key={k} style={{ display:'flex', justifyContent:'space-between', padding:'0.3rem 0',
                    borderBottom:'1px solid rgba(255,255,255,0.05)', fontSize:'0.85rem' }}>
                    <span style={{ color:'#94a3b8' }}>{k}</span>
                    <span style={{ color:'#e2e8f0', fontWeight:600 }}>{v}</span>
                  </div>
                ))}
                {signals.length > 0 && (
                  <div style={{ marginTop:'0.5rem' }}>
                    {signals.slice(0,4).map((s,i)=>(
                      <div key={i} style={{ fontSize:'0.75rem', color:'#fbbf24', marginTop:'0.2rem' }}>• {s}</div>
                    ))}
                  </div>
                )}
              </section>
            )}
          </div>

          {/* Analyst Consensus + Intelligence Score side by side */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1rem' }}>
            {analyst && !analyst.error && (
              <section className={styles.panel}>
                <h2 style={{ marginBottom:'0.75rem', fontSize:'1rem' }}>Analyst Consensus</h2>
                <div style={{ display:'flex', gap:'1rem', alignItems:'center', marginBottom:'0.5rem' }}>
                  <div style={{ fontSize:'1.8rem', fontWeight:900, color: recColors[analyst.recommendation] || '#94a3b8' }}>
                    {analyst.recommendation || '—'}
                  </div>
                  <div>
                    <div style={{ fontSize:'0.8rem', color:'#e2e8f0' }}>{analyst.analyst_count} analysts</div>
                    <div style={{ fontSize:'0.75rem', color:'#64748b' }}>Mean target: ${fmt(analyst.price_target_mean)}</div>
                  </div>
                  {analyst.upside_potential_pct != null && (
                    <div style={{ marginLeft:'auto', textAlign:'right' }}>
                      <div style={{ fontSize:'1.2rem', fontWeight:800, color: analyst.upside_potential_pct > 0 ? '#4ade80' : '#f87171' }}>
                        {analyst.upside_potential_pct > 0 ? '+' : ''}{analyst.upside_potential_pct?.toFixed(1)}%
                      </div>
                      <div style={{ fontSize:'0.68rem', color:'#64748b' }}>upside</div>
                    </div>
                  )}
                </div>
                {analyst.recent_ratings?.slice(0,5).map((r,i)=>(
                  <div key={i} style={{ display:'flex', gap:'0.5rem', fontSize:'0.75rem', padding:'0.25rem 0', borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
                    <span style={{ color:'#e2e8f0', flex:1 }}>{r.firm}</span>
                    <span style={{ color: recColors[r.to_grade?.toUpperCase()] || '#94a3b8' }}>{r.to_grade}</span>
                    <span style={{ color:'#64748b' }}>{String(r.date).slice(0,10)}</span>
                  </div>
                ))}
              </section>
            )}

            {intel && (
              <section className={styles.panel}>
                <h2 style={{ marginBottom:'0.75rem', fontSize:'1rem' }}>Multi-Agent Intelligence</h2>
                <div style={{ display:'flex', gap:'0.75rem', flexWrap:'wrap', marginBottom:'0.5rem' }}>
                  {[['Composite', intel.composite_score, '#818cf8'],
                    ['Fundamental', intel.fundamentals_score, '#4ade80'],
                    ['Technical', intel.technical_score, '#4ade80'],
                    ['Sentiment', intel.sentiment_score, '#fbbf24'],
                    ['Risk', intel.risk_score, '#fbbf24'],
                  ].map(([label, val, color])=>(
                    <div key={label} style={{ textAlign:'center', background:'rgba(255,255,255,0.03)',
                      border:'1px solid var(--line)', borderRadius:8, padding:'0.4rem 0.6rem', minWidth:70 }}>
                      <div style={{ fontSize:'0.6rem', color:'var(--text-muted)', textTransform:'uppercase' }}>{label}</div>
                      <div style={{ fontSize:'1.2rem', fontWeight:800, color }}>{val ?? '—'}</div>
                    </div>
                  ))}
                </div>
                <div style={{ display:'flex', alignItems:'center', gap:'0.75rem' }}>
                  <span style={{ fontSize:'1.4rem', fontWeight:900,
                    color: intel.recommendation==='BUY'?'#4ade80': intel.recommendation==='SELL'?'#f87171':'#fbbf24' }}>
                    {intel.recommendation || '—'}
                  </span>
                  <span style={{ fontSize:'0.75rem', color:'var(--text-muted)' }}>{intel.conviction}</span>
                </div>
                {intel.thesis && <p style={{ marginTop:'0.5rem', fontSize:'0.78rem', color:'#94a3b8', lineHeight:1.5 }}>{intel.thesis.slice(0,200)}…</p>}
              </section>
            )}
          </div>

          {/* Company Profile */}
          {fundamentals.longBusinessSummary && (
            <section className={styles.panel}>
              <h2 style={{ marginBottom:'0.5rem', fontSize:'1rem' }}>Company Profile</h2>
              <p style={{ fontSize:'0.82rem', color:'#94a3b8', lineHeight:1.6 }}>
                {fundamentals.longBusinessSummary.slice(0,400)}{fundamentals.longBusinessSummary.length>400?'…':''}
              </p>
              {fundamentals.sector && <p style={{ marginTop:'0.4rem', fontSize:'0.75rem', color:'#64748b' }}>
                {fundamentals.sector} · {fundamentals.industry} · {fundamentals.country}
              </p>}
              <Link href={`/company?t=${t}`} passHref>
                <a style={{ display:'inline-block', marginTop:'0.75rem', fontSize:'0.78rem', color:'#818cf8', textDecoration:'none', border:'1px solid rgba(129,140,248,0.3)', borderRadius:6, padding:'0.35rem 0.75rem' }}>
                  View Full Company Report (SEC Filings, Cap Table, Earnings) →
                </a>
              </Link>
            </section>
          )}
        </>
      )}

      {!data && !loading && (
        <div className={styles.panel} style={{ textAlign:'center', padding:'3rem' }}>
          <p style={{ color:'var(--text-muted)' }}>Enter a ticker above and click Analyze to see real-time data.</p>
        </div>
      )}
    </main>
  )
}
