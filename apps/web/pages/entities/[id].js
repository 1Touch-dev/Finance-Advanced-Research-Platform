import { useRouter } from 'next/router'
import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'
import { getApiBaseUrl } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'
import eStyles from '../../src/styles/Entity.module.css'

const API = getApiBaseUrl()
const fetcher = (url) => fetch(url).then(r => r.json()).catch(() => null)

function Badge({ label, color = '#818cf8' }) {
  return (
    <span style={{ background:`${color}22`, border:`1px solid ${color}55`, borderRadius:6,
      color, fontSize:'0.72rem', fontWeight:700, letterSpacing:'0.06em',
      padding:'0.15rem 0.5rem', textTransform:'uppercase' }}>{label}</span>
  )
}
function Stat({ label, value, sub }) {
  return (
    <div className={eStyles.stat}>
      <span className={eStyles.statVal}>{value ?? '—'}</span>
      <span className={eStyles.statLabel}>{label}</span>
      {sub && <span className={eStyles.statSub}>{sub}</span>}
    </div>
  )
}
function RelCard({ rel, entityId, onInvestigate }) {
  const srcId = rel.source_entity_id ?? rel.src
  const dstId = rel.target_entity_id ?? rel.dst
  const isSource = srcId === Number(entityId)
  const partner = isSource ? (rel.target_entity_name||rel.target_name||`Entity #${dstId}`) : (rel.source_entity_name||rel.source_name||`Entity #${srcId}`)
  const arrow = isSource ? '→' : '←'
  const colors = { employs:'#60a5fa', investor:'#a78bfa', lobbying:'#f97316', contract:'#4ade80', board_member:'#818cf8' }
  const color = colors[rel.kind] || '#94a3b8'
  return (
    <div className={eStyles.relCard}>
      <span style={{ color, fontWeight:700, fontSize:'0.72rem', textTransform:'uppercase' }}>{rel.kind?.replace(/_/g,' ')}</span>
      <span className={eStyles.relArrow}>{arrow}</span>
      <span className={eStyles.relName} onClick={() => partner && onInvestigate(partner)} title="Investigate">{partner||'—'}</span>
    </div>
  )
}
function EvidenceRow({ ev }) {
  return (
    <div className={eStyles.evRow}>
      <span className={eStyles.evSource}>{ev.source_name||ev.source_id}</span>
      <span className={eStyles.evText}>{(ev.content||ev.text||'')?.slice(0,200)}</span>
      {ev.url && <a href={ev.url} target="_blank" rel="noopener noreferrer" className={eStyles.evLink}>↗</a>}
    </div>
  )
}
function TimelineItem({ item }) {
  const colorMap = { legal:'#f87171', financial:'#60a5fa', government:'#4ade80', news:'#fbbf24' }
  const color = colorMap[item.category?.toLowerCase()] || '#818cf8'
  return (
    <div className={eStyles.tlItem}>
      <div className={eStyles.tlDot} style={{ background:color }} />
      <div className={eStyles.tlContent}>
        <span className={eStyles.tlDate}>{item.date||item.year||'—'}</span>
        <span className={eStyles.tlText}>{item.text||item.description||''}</span>
        {item.source && <span className={eStyles.tlSource}>{item.source}</span>}
      </div>
    </div>
  )
}

// ── Financial Tab ─────────────────────────────────────────────────────────────
function FinancialTab({ ticker, entityName }) {
  const { data: summary } = useSWR(ticker ? `${API}/market/financial-summary?ticker=${ticker}` : null, fetcher)
  const { data: incData } = useSWR(ticker ? `${API}/market/income-statement?ticker=${ticker}&limit=10` : null, fetcher)
  const { data: insiders } = useSWR(ticker ? `${API}/market/insider-transactions?ticker=${ticker}` : null, fetcher)
  if (!ticker) return <p style={{ color:'var(--text-muted)' }}>No ticker available. Provide a ticker to load financial data.</p>
  const chartData = (incData?.statements || []).slice().reverse().map(s => ({
    year: s.date?.slice(0,4), revenue: s.revenue ? +(s.revenue/1e9).toFixed(2) : null,
    net_income: s.net_income ? +(s.net_income/1e9).toFixed(2) : null,
    gross_margin: s.gross_margin ? +(s.gross_margin*100).toFixed(1) : null,
  }))
  const ms = summary?.beneish_mscore || {}
  const zs = summary?.altman_zscore || {}
  const q = summary?.quote || {}
  const m = summary?.metrics || {}
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>
      {/* Quote strip */}
      <div style={{ display:'flex', gap:'1rem', flexWrap:'wrap' }}>
        {[['Price', q.price ? `$${q.price}` : '—'], ['Change', q.change_pct ? `${q.change_pct?.toFixed(2)}%` : '—'],
          ['P/E', m.pe_ratio?.toFixed(1)||'—'], ['EV/EBITDA', m.ev_ebitda?.toFixed(1)||'—'],
          ['Beta', m.beta?.toFixed(2)||'—'], ['52W High', q['52w_high'] ? `$${q['52w_high']}` : '—']].map(([l,v]) => (
          <div key={l} style={{ background:'rgba(129,140,248,0.08)', border:'1px solid var(--line)', borderRadius:10, padding:'0.6rem 1rem', minWidth:90 }}>
            <div style={{ fontSize:'1.1rem', fontWeight:800, color:'#c7d2fe' }}>{v}</div>
            <div style={{ fontSize:'0.65rem', textTransform:'uppercase', color:'var(--text-muted)', letterSpacing:'0.07em' }}>{l}</div>
          </div>
        ))}
      </div>
      {/* Revenue / Net Income chart */}
      {chartData.length > 0 && (
        <div style={{ background:'rgba(8,13,26,0.8)', border:'1px solid var(--line)', borderRadius:12, padding:'1rem' }}>
          <h3 style={{ margin:'0 0 0.75rem', fontSize:'0.9rem', color:'#c7d2fe' }}>Revenue & Net Income (B USD)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <XAxis dataKey="year" tick={{ fill:'#64748b', fontSize:11 }} />
              <YAxis tick={{ fill:'#64748b', fontSize:11 }} />
              <Tooltip contentStyle={{ background:'#0f1428', border:'1px solid #334155' }} />
              <Legend />
              <Line type="monotone" dataKey="revenue" stroke="#818cf8" strokeWidth={2} dot={false} name="Revenue $B" />
              <Line type="monotone" dataKey="net_income" stroke="#4ade80" strokeWidth={2} dot={false} name="Net Income $B" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {/* Gross Margin chart */}
      {chartData.filter(d=>d.gross_margin).length > 0 && (
        <div style={{ background:'rgba(8,13,26,0.8)', border:'1px solid var(--line)', borderRadius:12, padding:'1rem' }}>
          <h3 style={{ margin:'0 0 0.75rem', fontSize:'0.9rem', color:'#c7d2fe' }}>Gross Margin %</h3>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={chartData}>
              <XAxis dataKey="year" tick={{ fill:'#64748b', fontSize:11 }} />
              <YAxis tick={{ fill:'#64748b', fontSize:11 }} unit="%" />
              <Tooltip contentStyle={{ background:'#0f1428', border:'1px solid #334155' }} />
              <Bar dataKey="gross_margin" fill="#60a5fa" name="Gross Margin %" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {/* Health scores */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1rem' }}>
        <div style={{ background:'rgba(8,13,26,0.8)', border:`2px solid ${ms.m_score > -2.22 ? '#f87171' : '#4ade80'}`, borderRadius:12, padding:'1rem' }}>
          <h3 style={{ margin:'0 0 0.5rem', fontSize:'0.88rem', color:'#c7d2fe' }}>Beneish M-Score</h3>
          {ms.error ? <p style={{ color:'var(--text-muted)', fontSize:'0.8rem' }}>{ms.error}</p> : <>
            <div style={{ fontSize:'2rem', fontWeight:900, color: ms.m_score > -2.22 ? '#f87171' : '#4ade80' }}>{ms.m_score ?? '—'}</div>
            <div style={{ fontSize:'0.78rem', color:'var(--text-muted)', marginTop:'0.25rem' }}>{ms.risk_level} · threshold: -2.22</div>
            <div style={{ fontSize:'0.72rem', color:'var(--text-soft)', marginTop:'0.25rem' }}>M &gt; -2.22 = possible earnings manipulation</div>
          </>}
        </div>
        <div style={{ background:'rgba(8,13,26,0.8)', border:`2px solid ${zs.z_score < 1.81 ? '#f87171' : zs.z_score < 2.99 ? '#fbbf24' : '#4ade80'}`, borderRadius:12, padding:'1rem' }}>
          <h3 style={{ margin:'0 0 0.5rem', fontSize:'0.88rem', color:'#c7d2fe' }}>Altman Z-Score</h3>
          {zs.error ? <p style={{ color:'var(--text-muted)', fontSize:'0.8rem' }}>{zs.error}</p> : <>
            <div style={{ fontSize:'2rem', fontWeight:900, color: zs.z_score < 1.81 ? '#f87171' : zs.z_score < 2.99 ? '#fbbf24' : '#4ade80' }}>{zs.z_score ?? '—'}</div>
            <div style={{ fontSize:'0.78rem', color:'var(--text-muted)', marginTop:'0.25rem' }}>{zs.zone}</div>
            <div style={{ fontSize:'0.72rem', color:'var(--text-soft)', marginTop:'0.25rem' }}>Distress &lt;1.81 · Grey 1.81–2.99 · Safe &gt;2.99</div>
          </>}
        </div>
      </div>
      {/* Insider transactions */}
      {(insiders?.transactions||[]).length > 0 && (
        <div style={{ background:'rgba(8,13,26,0.8)', border:'1px solid var(--line)', borderRadius:12, padding:'1rem' }}>
          <h3 style={{ margin:'0 0 0.75rem', fontSize:'0.9rem', color:'#c7d2fe' }}>Insider Transactions</h3>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'0.8rem' }}>
            <thead><tr>{['Name','Date','Shares','Price','Type'].map(h=><th key={h} style={{ textAlign:'left', padding:'0.3rem 0.5rem', color:'var(--text-muted)', fontWeight:700, borderBottom:'1px solid var(--line)' }}>{h}</th>)}</tr></thead>
            <tbody>{(insiders.transactions||[]).slice(0,10).map((t,i)=>(
              <tr key={i} style={{ borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding:'0.3rem 0.5rem', color:'#c7d2fe' }}>{t.name}</td>
                <td style={{ padding:'0.3rem 0.5rem', color:'var(--text-muted)' }}>{t.date}</td>
                <td style={{ padding:'0.3rem 0.5rem' }}>{(t.shares||0).toLocaleString()}</td>
                <td style={{ padding:'0.3rem 0.5rem' }}>${t.value}</td>
                <td style={{ padding:'0.3rem 0.5rem', color: t.transaction==='P'?'#4ade80':'#f87171' }}>{t.transaction==='P'?'Buy':'Sell'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── People & Contacts Tab ─────────────────────────────────────────────────────
function PeopleTab({ entityName, ticker }) {
  const domain = ticker ? ticker.toLowerCase()+'.com' : ''
  const { data: orgData } = useSWR(entityName ? `${API}/intelligence/apollo/org?name=${encodeURIComponent(entityName)}` : null, fetcher)
  const { data: peopleData } = useSWR(entityName ? `${API}/intelligence/apollo/people?name=${encodeURIComponent(entityName)}&domain=${domain}` : null, fetcher)
  const people = peopleData?.people || peopleData?.executives || []
  const org = orgData?.organization || orgData || {}
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>
      {org.name && (
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))', gap:'0.75rem' }}>
          {[['Headcount', org.headcount], ['Revenue', org.revenue_range], ['Founded', org.founded_year],
            ['Industry', org.industry], ['Funding', org.funding_stage], ['Location', org.city]].filter(([,v])=>v).map(([l,v])=>(
            <div key={l} style={{ background:'rgba(129,140,248,0.06)', border:'1px solid var(--line)', borderRadius:10, padding:'0.6rem' }}>
              <div style={{ fontSize:'0.88rem', fontWeight:700, color:'#c7d2fe' }}>{v}</div>
              <div style={{ fontSize:'0.65rem', textTransform:'uppercase', color:'var(--text-muted)' }}>{l}</div>
            </div>
          ))}
        </div>
      )}
      {people.length === 0 ? (
        <div style={{ background:'rgba(251,191,36,0.08)', border:'1px solid rgba(251,191,36,0.3)', borderRadius:10, padding:'1rem' }}>
          <p style={{ margin:0, color:'#fbbf24', fontSize:'0.85rem' }}>Apollo people search requires a paid Apollo plan. Org enrichment data shown above (free tier). Upgrade to Apollo paid plan to unlock executive emails, titles, and LinkedIn profiles.</p>
        </div>
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:'0.5rem' }}>
          {people.map((p,i) => (
            <div key={i} style={{ background:'rgba(8,13,26,0.8)', border:'1px solid var(--line)', borderRadius:10, padding:'0.75rem 1rem', display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'0.5rem' }}>
              <div>
                <div style={{ fontWeight:700, color:'#c7d2fe' }}>{p.name||p.first_name+' '+p.last_name}</div>
                <div style={{ fontSize:'0.78rem', color:'var(--text-muted)' }}>{p.title}</div>
              </div>
              <div style={{ display:'flex', gap:'0.5rem', flexWrap:'wrap' }}>
                {p.email && <a href={`mailto:${p.email}`} style={{ fontSize:'0.75rem', color:'#60a5fa' }}>{p.email}</a>}
                {p.linkedin_url && <a href={p.linkedin_url} target="_blank" rel="noopener noreferrer" style={{ fontSize:'0.75rem', color:'#818cf8' }}>LinkedIn ↗</a>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Social Footprint Tab ──────────────────────────────────────────────────────
function SocialTab({ entityName }) {
  const { data: newsData } = useSWR(entityName ? `${API}/market/news?entity=${encodeURIComponent(entityName)}&limit=8` : null, fetcher)
  const articles = newsData?.articles || []
  const bySrc = newsData?.by_source || {}
  const sentimentColor = (tone) => {
    if (!tone) return '#94a3b8'
    return tone > 0 ? '#4ade80' : tone < 0 ? '#f87171' : '#94a3b8'
  }
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>
      {/* Source summary cards */}
      <div style={{ display:'flex', gap:'0.75rem', flexWrap:'wrap' }}>
        {Object.entries(bySrc).filter(([,v])=>v>0).map(([src,count])=>(
          <div key={src} style={{ background:'rgba(129,140,248,0.06)', border:'1px solid var(--line)', borderRadius:10, padding:'0.6rem 1rem', minWidth:100 }}>
            <div style={{ fontSize:'1.3rem', fontWeight:900, color:'#c7d2fe' }}>{count}</div>
            <div style={{ fontSize:'0.65rem', textTransform:'uppercase', color:'var(--text-muted)' }}>{src}</div>
          </div>
        ))}
        {articles.length === 0 && <p style={{ color:'var(--text-muted)', fontSize:'0.85rem' }}>No news found. Add NEWSAPI_KEY, GUARDIAN_API_KEY, or NYT_API_KEY to .env to enable.</p>}
      </div>
      {/* Articles feed */}
      {articles.length > 0 && (
        <div style={{ display:'flex', flexDirection:'column', gap:'0.5rem' }}>
          <h3 style={{ margin:'0 0 0.5rem', fontSize:'0.9rem', color:'#c7d2fe' }}>Latest News ({articles.length})</h3>
          {articles.slice(0,20).map((a,i)=>(
            <div key={i} style={{ background:'rgba(8,13,26,0.8)', border:'1px solid var(--line)', borderRadius:10, padding:'0.75rem 1rem' }}>
              <div style={{ display:'flex', justifyContent:'space-between', gap:'0.5rem', marginBottom:'0.25rem' }}>
                <a href={a.url} target="_blank" rel="noopener noreferrer" style={{ color:'#c7d2fe', fontWeight:600, fontSize:'0.88rem', textDecoration:'none' }}>{a.title}</a>
                {a.tone !== undefined && <span style={{ fontSize:'0.72rem', color:sentimentColor(a.tone), whiteSpace:'nowrap' }}>tone: {a.tone?.toFixed(1)}</span>}
              </div>
              <div style={{ display:'flex', gap:'0.75rem', fontSize:'0.72rem', color:'var(--text-muted)' }}>
                <span>{a.source || a.domain || a.provider}</span>
                <span>{a.date?.slice(0,10)}</span>
              </div>
              {a.description && <p style={{ margin:'0.3rem 0 0', fontSize:'0.78rem', color:'var(--text-soft)', lineHeight:1.5 }}>{a.description?.slice(0,200)}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── RAG Chat Tab ──────────────────────────────────────────────────────────────
function ChatTab({ entityName, reportId }) {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const SUGGESTIONS = ['What are the main government contracts?', 'Describe lobbying activity', 'Who are the key executives?', 'What are the legal risks?', 'Summarize financial performance']
  const send = async (q) => {
    const question = q || input
    if (!question.trim()) return
    setInput('')
    setMsgs(m => [...m, { role:'user', text:question }])
    setLoading(true)
    try {
      const r = await fetch(`${API}/chat/ask`, { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ question, report_id: reportId||null, entity_name: entityName }) })
      const d = await r.json()
      setMsgs(m => [...m, { role:'assistant', text: d.answer||d.response||'No answer returned.' }])
    } catch { setMsgs(m => [...m, { role:'assistant', text:'Error contacting chat API.' }]) }
    setLoading(false)
  }
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'1rem', maxWidth:720 }}>
      <div style={{ display:'flex', gap:'0.4rem', flexWrap:'wrap' }}>
        {SUGGESTIONS.map((s,i)=>(
          <button key={i} onClick={()=>send(s)} style={{ background:'rgba(129,140,248,0.1)', border:'1px solid rgba(129,140,248,0.3)', borderRadius:8, color:'#a5b4fc', cursor:'pointer', fontSize:'0.75rem', padding:'0.3rem 0.7rem' }}>{s}</button>
        ))}
      </div>
      <div style={{ minHeight:200, display:'flex', flexDirection:'column', gap:'0.75rem' }}>
        {msgs.map((m,i)=>(
          <div key={i} style={{ display:'flex', justifyContent: m.role==='user'?'flex-end':'flex-start' }}>
            <div style={{ background: m.role==='user'?'rgba(129,140,248,0.2)':'rgba(8,13,26,0.9)', border:'1px solid var(--line)', borderRadius:10, padding:'0.6rem 1rem', maxWidth:'85%', fontSize:'0.85rem', lineHeight:1.6, color:m.role==='user'?'#c7d2fe':'#e2e8f0', whiteSpace:'pre-wrap' }}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && <div style={{ color:'var(--text-muted)', fontSize:'0.8rem' }}>Thinking…</div>}
        {msgs.length === 0 && <p style={{ color:'var(--text-muted)', fontSize:'0.85rem' }}>Ask anything about {entityName}. Use the suggestions above or type your own question.</p>}
      </div>
      <div style={{ display:'flex', gap:'0.5rem' }}>
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()}
          placeholder={`Ask about ${entityName}…`}
          style={{ flex:1, background:'rgba(8,13,26,0.9)', border:'1px solid var(--line)', borderRadius:8, color:'#e2e8f0', fontSize:'0.85rem', padding:'0.5rem 0.75rem' }} />
        <button onClick={()=>send()} disabled={loading||!input.trim()}
          style={{ background:'#6366f1', border:'none', borderRadius:8, color:'#fff', cursor:'pointer', fontWeight:700, padding:'0.5rem 1.2rem' }}>Send</button>
      </div>
    </div>
  )
}

// ── API Status Panel ──────────────────────────────────────────────────────────
function ApiStatusPanel({ ticker }) {
  const [open, setOpen] = useState(false)
  const sources = [
    { name:'Finnhub',          key:'FINNHUB_API_KEY',         url: ticker?`${API}/market/quote?ticker=${ticker}`:null },
    { name:'FMP',              key:'FMP_API_KEY',              url: ticker?`${API}/market/income-statement?ticker=${ticker}&limit=1`:null },
    { name:'Alpha Vantage',    key:'ALPHA_VANTAGE_KEY',        url: ticker?`${API}/market/metrics?ticker=${ticker}`:null },
    { name:'FRED',             key:'FRED_API_KEY',             url:`${API}/market/macro?series_id=GDP&limit=1` },
    { name:'NewsAPI',          key:'NEWSAPI_KEY',              url:`${API}/market/news/newsapi?query=test&limit=1` },
    { name:'The Guardian',     key:'GUARDIAN_API_KEY',         url:`${API}/market/news/guardian?query=test&limit=1` },
    { name:'NYT',              key:'NYT_API_KEY',              url:`${API}/market/news/nyt?query=test&limit=1` },
    { name:'UK Companies',     key:'UK_COMPANIES_HOUSE_KEY',   url:`${API}/market/uk/companies?q=test&limit=1` },
    { name:'GDELT',            key:'(no key needed)',          url:`${API}/market/news/gdelt?query=test&limit=1` },
    { name:'Apollo',           key:'APOLLO_API_KEY',           url:`${API}/intelligence/apollo/enrich` },
    { name:'Apify',            key:'APIFY_API_TOKEN',          url:null },
  ]
  return (
    <div style={{ position:'relative', display:'inline-block' }}>
      <button onClick={()=>setOpen(o=>!o)} style={{ background:'rgba(8,13,26,0.7)', border:'1px solid var(--line)', borderRadius:8, color:'var(--text-muted)', cursor:'pointer', fontSize:'0.72rem', padding:'0.3rem 0.7rem' }}>
        ⚡ API Status {open ? '▲' : '▼'}
      </button>
      {open && (
        <div style={{ position:'absolute', right:0, top:'calc(100% + 4px)', background:'#0f1428', border:'1px solid var(--line)', borderRadius:10, padding:'0.75rem', zIndex:100, minWidth:240 }}>
          {sources.map(s=>(
            <div key={s.name} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'0.25rem 0', borderBottom:'1px solid rgba(255,255,255,0.05)' }}>
              <span style={{ fontSize:'0.78rem', color:'#c7d2fe' }}>{s.name}</span>
              <span style={{ fontSize:'0.68rem', color:s.url?'#4ade80':'#94a3b8' }}>{s.url ? '● live' : '○ no key'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Add to Tracking Button ────────────────────────────────────────────────────
function AddToTrackingBtn({ entityName, entityType }) {
  const [status, setStatus] = useState('')
  const add = async () => {
    setStatus('adding…')
    try {
      const r = await fetch(`${API}/tracking/watchlist`, { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ entity_name:entityName, entity_type:entityType||'org' }) })
      const d = await r.json()
      setStatus(d.error ? '⚠ '+d.error : '✓ Added')
    } catch { setStatus('Error') }
    setTimeout(()=>setStatus(''), 3000)
  }
  return (
    <button onClick={add} style={{ background:'rgba(74,222,128,0.1)', border:'1px solid rgba(74,222,128,0.4)', borderRadius:8, color:'#4ade80', cursor:'pointer', fontSize:'0.82rem', fontWeight:700, padding:'0.4rem 1rem' }}>
      {status || '+ Track'}
    </button>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function EntityProfile() {
  const router = useRouter()
  const { id } = router.query
  const [tab, setTab] = useState('overview')

  const { data: profile } = useSWR(id ? `${API}/search/entities/${id}` : null, fetcher)
  const { data: rels }    = useSWR(id ? `${API}/search/entities/${id}/relationships` : null, fetcher)
  const { data: evidence }= useSWR(id ? `${API}/search/entities/${id}/evidence` : null, fetcher)
  const { data: timeline }= useSWR(id ? `${API}/search/entities/${id}/timeline` : null, fetcher)
  const { data: related } = useSWR(id ? `${API}/graph/related?entity_id=${id}` : null, fetcher)

  const entity      = profile?.entity || profile || {}
  const relList     = (rels?.relationships||(Array.isArray(rels)?rels:[])).slice(0,50)
  const evList      = (evidence?.evidence||(Array.isArray(evidence)?evidence:[])).slice(0,30)
  const tlList      = (timeline?.items||timeline?.timeline||(Array.isArray(timeline)?timeline:[])).slice(0,40)
  const relatedList = (related?.related||related?.entities||related?.nodes||(Array.isArray(related)?related:[])).slice(0,20)

  const entityKind = entity.entity_type||entity.kind||'entity'
  const entityName = entity.name||entity.entity_name||`Entity #${id}`
  // Check ticker field OR parse from identifiers array
  const tickerFromIdentifiers = (entity.identifiers || []).find(i => i.scheme === 'TICKER')?.value || ''
  const ticker     = entity.ticker||entity.stock_ticker||tickerFromIdentifiers||''

  const investigate = (name) => router.push(`/intelligence?entity=${encodeURIComponent(name)}`)

  const TABS = ['overview','financial','people','social','chat','relationships','evidence','timeline','related']

  if (!router.isReady) return (
    <main className={styles.page}><section className={styles.hero}><h1>Entity Profile</h1><p style={{color:'var(--text-muted)'}}>Loading…</p></section></main>
  )
  if (!id) return (
    <main className={styles.page}><section className={styles.hero}><h1>Entity Profile</h1><p>No entity ID. Go to <Link href="/search">Search</Link>.</p></section></main>
  )

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div style={{ display:'flex', alignItems:'flex-start', gap:'1rem', flexWrap:'wrap' }}>
          <div className={eStyles.avatar}>{entityName.charAt(0).toUpperCase()}</div>
          <div style={{ flex:1 }}>
            <div style={{ display:'flex', gap:'0.5rem', flexWrap:'wrap', marginBottom:'0.4rem' }}>
              <Badge label={entityKind} color="#818cf8" />
              {entity.is_us && <Badge label="US Entity" color="#4ade80" />}
              {entity.sanctions_flag && <Badge label="Sanctions Risk" color="#f87171" />}
              {entity.public_company && <Badge label="Public" color="#60a5fa" />}
              {ticker && <Badge label={ticker} color="#fbbf24" />}
            </div>
            <h1 style={{ margin:0 }}>{entityName}</h1>
            {entity.description && <p style={{ margin:'0.4rem 0 0', color:'var(--text-muted)', maxWidth:640 }}>{entity.description?.slice(0,300)}</p>}
            {entity.sec_cik && <a href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${entity.sec_cik}`} target="_blank" rel="noopener noreferrer" style={{ fontSize:'0.78rem', color:'#818cf8', marginTop:'0.3rem', display:'inline-block' }}>SEC EDGAR ↗</a>}
            <div style={{ marginTop:'0.6rem', display:'flex', gap:'0.5rem', flexWrap:'wrap' }}>
              <button className={eStyles.investigateBtn} onClick={()=>investigate(entityName)}>🔍 Generate Report</button>
              <Link href={`/graph?entity_id=${id}`} passHref><a className={eStyles.graphBtn}>🕸 Graph</a></Link>
              <AddToTrackingBtn entityName={entityName} entityType={entityKind} />
              <ApiStatusPanel ticker={ticker} />
            </div>
          </div>
        </div>
      </section>

      <div className={eStyles.statBar}>
        <Stat label="Relationships" value={relList.length} sub="mapped" />
        <Stat label="Evidence" value={evList.length} sub="cited" />
        <Stat label="Timeline" value={tlList.length} sub="events" />
        <Stat label="Related" value={relatedList.length} sub="parties" />
        {entity.total_obligated_usd>0 && <Stat label="Gov Contracts" value={`$${(entity.total_obligated_usd/1e6).toFixed(1)}M`} sub="obligated" />}
        {entity.sec_cik && <Stat label="SEC CIK" value={entity.sec_cik} sub="EDGAR" />}
      </div>

      <div className={eStyles.tabs}>
        {TABS.map(t=>(
          <button key={t} className={`${eStyles.tab} ${tab===t?eStyles.tabActive:''}`} onClick={()=>setTab(t)}>
            {t==='financial'?'📈 Financial':t==='people'?'👥 People':t==='social'?'📡 Social':t==='chat'?'💬 Chat':t.charAt(0).toUpperCase()+t.slice(1)}
          </button>
        ))}
      </div>

      {tab==='overview' && (
        <div className={styles.panel}>
          <h2>Entity Details</h2>
          <div className={eStyles.detailGrid}>
            {Object.entries(entity).filter(([k])=>!['id','created_at','updated_at','description'].includes(k)).map(([k,v])=>(
              <div key={k} className={eStyles.detailRow}>
                <span className={eStyles.detailKey}>{k.replace(/_/g,' ')}</span>
                <span className={eStyles.detailVal}>
                  {Array.isArray(v)?v.map((item,i)=><span key={i} style={{display:'inline-block',marginRight:'0.4rem',background:'rgba(255,255,255,0.08)',borderRadius:'4px',padding:'1px 6px',fontSize:'0.78rem'}}>{typeof item==='object'?Object.entries(item).map(([ik,iv])=>`${ik}: ${iv}`).join(' · '):String(item)}</span>):typeof v==='object'&&v!==null?JSON.stringify(v).slice(0,120):String(v??'—')}
                </span>
              </div>
            ))}
          </div>
          {relatedList.length>0 && (<><h3 style={{marginTop:'1.5rem'}}>Top Related Parties</h3><div className={eStyles.relGrid}>{relatedList.slice(0,8).map((r,i)=><div key={i} className={eStyles.relChip} onClick={()=>investigate(r.name||r.entity_name||'')}>{r.name||r.entity_name||`#${r.id}`}</div>)}</div></>)}
        </div>
      )}
      {tab==='financial' && <div className={styles.panel}><h2>📈 Financial Analysis</h2><FinancialTab ticker={ticker} entityName={entityName} /></div>}
      {tab==='people' && <div className={styles.panel}><h2>👥 People & Contacts</h2><PeopleTab entityName={entityName} ticker={ticker} /></div>}
      {tab==='social' && <div className={styles.panel}><h2>📡 Social & News Footprint</h2><SocialTab entityName={entityName} /></div>}
      {tab==='chat' && <div className={styles.panel}><h2>💬 Ask about {entityName}</h2><ChatTab entityName={entityName} reportId={null} /></div>}
      {tab==='relationships' && (
        <div className={styles.panel}>
          <h2>Relationships <span style={{fontSize:'0.82rem',color:'var(--text-muted)',fontWeight:400}}>({relList.length})</span></h2>
          {relList.length===0&&<p className={styles.empty}>No relationships mapped yet.</p>}
          <div className={eStyles.relList}>{relList.map((r,i)=><RelCard key={i} rel={r} entityId={id} onInvestigate={investigate}/>)}</div>
        </div>
      )}
      {tab==='evidence' && (
        <div className={styles.panel}>
          <h2>Evidence & Citations <span style={{fontSize:'0.82rem',color:'var(--text-muted)',fontWeight:400}}>({evList.length})</span></h2>
          {evList.length===0&&<p className={styles.empty}>No evidence items found.</p>}
          <div className={eStyles.evList}>{evList.map((ev,i)=><EvidenceRow key={i} ev={ev}/>)}</div>
        </div>
      )}
      {tab==='timeline' && (
        <div className={styles.panel}>
          <h2>Event Timeline <span style={{fontSize:'0.82rem',color:'var(--text-muted)',fontWeight:400}}>({tlList.length})</span></h2>
          {tlList.length===0&&<p className={styles.empty}>No timeline events found.</p>}
          <div className={eStyles.timeline}>{tlList.map((item,i)=><TimelineItem key={i} item={item}/>)}</div>
        </div>
      )}
      {tab==='related' && (
        <div className={styles.panel}>
          <h2>Related Parties <span style={{fontSize:'0.82rem',color:'var(--text-muted)',fontWeight:400}}>({relatedList.length})</span></h2>
          {relatedList.length===0&&<p className={styles.empty}>No related parties found.</p>}
          <div className={eStyles.relGrid}>{relatedList.map((r,i)=><div key={i} className={eStyles.relChipLarge} onClick={()=>investigate(r.name||r.entity_name||'')}><span className={eStyles.relChipName}>{r.name||r.entity_name||`#${r.id}`}</span>{r.entity_type&&<span className={eStyles.relChipType}>{r.entity_type}</span>}</div>)}</div>
        </div>
      )}
    </main>
  )
}
