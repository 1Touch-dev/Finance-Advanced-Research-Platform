import { useState } from 'react'
import useSWR from 'swr'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''
const fetcher = url => fetch(url).then(r => r.json())

const PARTY_COLORS = { D: '#60a5fa', R: '#f87171', I: '#a78bfa' }

function PoliticianTab() {
  const [selected, setSelected] = useState('')
  const [profileData, setProfileData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [summaryExpanded, setSummaryExpanded] = useState(false)
  const { data: listData } = useSWR(`${API}/market/gov-trading/politicians/list`, fetcher)
  const { data: summaryData } = useSWR(summaryExpanded ? `${API}/market/gov-trading/politicians/summary` : null, fetcher)

  const loadProfile = async (id) => {
    if (!id) return
    setSelected(id)
    setLoading(true)
    setProfileData(null)
    try {
      const res = await fetch(`${API}/market/gov-trading/politician/${id}`)
      setProfileData(await res.json())
    } catch(e) { console.error(e) }
    setLoading(false)
  }

  const politicians = listData?.politicians || []
  const p = profileData?.politician || {}
  const partyColor = PARTY_COLORS[p.party] || '#94a3b8'

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={selected} onChange={e => loadProfile(e.target.value)}
          style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid var(--line)', borderRadius: 8,
            color: '#e2e8f0', padding: '8px 14px', fontSize: '0.85rem', flex: 1, maxWidth: 360 }}>
          <option value="">Select a politician to view trading profile…</option>
          {politicians.map(p => (
            <option key={p.id} value={p.id}>{p.name} ({p.party} – {p.state?.toUpperCase()}, {p.chamber})</option>
          ))}
        </select>
        <button onClick={() => setSummaryExpanded(!summaryExpanded)}
          style={{ padding: '8px 14px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--line)',
            color: '#94a3b8', borderRadius: 8, cursor: 'pointer', fontSize: '0.8rem' }}>
          {summaryExpanded ? '▲ Hide Summary' : '▼ All Politicians Summary'}
        </button>
      </div>

      {/* All politicians summary */}
      {summaryExpanded && summaryData && (
        <div style={{ marginBottom: '1.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', background: 'rgba(255,255,255,0.03)' }}>
                {['Name', 'Party', 'Chamber', 'State', 'PTR Filings', 'Latest Filing'].map(h =>
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {(summaryData.politicians || []).map(p => (
                <tr key={p.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', cursor: 'pointer' }}
                    onClick={() => loadProfile(p.id)}>
                  <td style={{ padding: '7px 12px', fontWeight: 600, color: '#e2e8f0' }}>{p.name}</td>
                  <td style={{ padding: '7px 12px' }}><span style={{ color: PARTY_COLORS[p.party] || '#94a3b8', fontWeight: 700 }}>{p.party}</span></td>
                  <td style={{ padding: '7px 12px', color: '#94a3b8', textTransform: 'capitalize' }}>{p.chamber}</td>
                  <td style={{ padding: '7px 12px', color: '#94a3b8' }}>{p.state}</td>
                  <td style={{ padding: '7px 12px', color: '#818cf8', fontWeight: 700 }}>{p.ptr_count || 0}</td>
                  <td style={{ padding: '7px 12px', color: '#64748b', fontSize: '0.75rem' }}>{p.latest_filing || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <p style={{ color: '#94a3b8' }}>Loading profile…</p>}

      {profileData && !profileData.error && (
        <div>
          {/* Politician Header */}
          <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', padding: '1rem 1.25rem',
            background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 10, marginBottom: '1.25rem', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#e2e8f0' }}>{p.name}</div>
              <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: 4 }}>
                <span style={{ color: partyColor, fontWeight: 700 }}>{p.party}</span>
                {' · '}{p.chamber?.toUpperCase()}{' · '}{p.state}
              </div>
            </div>
            {[
              ['PTR Filings', profileData.ptr_filings_count],
              ['Legislation Tracked', profileData.recent_legislation_sponsored?.length || 0],
              ['Financial Legislation', profileData.financially_relevant_legislation?.length || 0],
            ].map(([label, val]) => (
              <div key={label} style={{ textAlign: 'center', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.5rem 1rem' }}>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#c7d2fe' }}>{val}</div>
              </div>
            ))}
          </div>

          {/* PTR Filings */}
          {profileData.recent_ptr_filings?.length > 0 && (
            <>
              <h4 style={{ color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Recent PTR Filings (STOCK Act)</h4>
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: 10, overflow: 'hidden', marginBottom: '1.25rem' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)', background: 'rgba(255,255,255,0.03)' }}>
                      {['Filing Date', 'District', 'Filing Type', 'Year', 'Doc ID'].map(h =>
                        <th key={h} style={{ padding: '6px 12px', textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {profileData.recent_ptr_filings.slice(0, 15).map((f, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <td style={{ padding: '6px 12px', color: '#86efac' }}>{f.filing_date}</td>
                        <td style={{ padding: '6px 12px', color: '#94a3b8' }}>{f.state_dst || '—'}</td>
                        <td style={{ padding: '6px 12px' }}>
                          <span style={{ background: '#818cf822', color: '#818cf8', borderRadius: 4, padding: '1px 7px', fontSize: '0.65rem', fontWeight: 700 }}>PTR</span>
                        </td>
                        <td style={{ padding: '6px 12px', color: '#64748b' }}>{f.year}</td>
                        <td style={{ padding: '6px 12px', color: '#475569', fontSize: '0.72rem' }}>{f.doc_id}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Legislation */}
          {profileData.recent_legislation_sponsored?.length > 0 && (
            <>
              <h4 style={{ color: '#fbbf24', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Sponsored Legislation</h4>
              {profileData.recent_legislation_sponsored.slice(0, 8).map((bill, i) => (
                <div key={i} style={{ padding: '0.6rem 0.9rem', border: '1px solid var(--line)', borderRadius: 8, marginBottom: '0.4rem' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ background: '#6366f122', color: '#818cf8', borderRadius: 5, padding: '2px 8px', fontSize: '0.65rem', fontWeight: 700 }}>
                      {bill.type} {bill.number}
                    </span>
                    {bill.policy_area && <span style={{ background: '#fbbf2422', color: '#fbbf24', borderRadius: 5, padding: '2px 8px', fontSize: '0.65rem' }}>{bill.policy_area}</span>}
                    <span style={{ color: '#64748b', fontSize: '0.7rem', marginLeft: 'auto' }}>{bill.introduced}</span>
                  </div>
                  <div style={{ color: '#e2e8f0', fontSize: '0.82rem', marginTop: '0.3rem', fontWeight: 500 }}>{bill.title}</div>
                  {bill.latest_action && <div style={{ color: '#64748b', fontSize: '0.72rem', marginTop: '0.2rem' }}>{bill.latest_action}</div>}
                </div>
              ))}
            </>
          )}

          <div style={{ background: 'rgba(251,191,36,0.07)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 8, padding: '0.75rem 1rem', marginTop: '1rem', fontSize: '0.78rem', color: '#fef3c7' }}>
            ⚠️ {profileData.note}
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryTab({ days, setDays }) {
  const { data, isLoading } = useSWR(`${API}/market/gov-trading/summary?days=${days}`, fetcher, { refreshInterval: 300000 })

  if (isLoading) return <p style={{ color: '#94a3b8' }}>Loading congressional data…</p>
  if (!data) return <p style={{ color: '#f87171' }}>Could not load government trading data.</p>

  const members = data.most_active_members || []
  const recent = data.recent_ptr_filers || []
  const states = data.top_states_by_ptr || []
  const form4 = data.recent_sec_form4_insiders || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Stats Row */}
      <section className={styles.panel}>
        <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Congressional STOCK Act Disclosures ({days}d)</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
          {[
            ['PTR Filings', data.total_ptr_disclosures],
            ['House PTR', data.house_ptr_filers],
            ['Active Members', members.length],
          ].map(([label, val]) => (
            <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.6rem 0.9rem', minWidth: 130 }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#818cf8' }}>{val ?? '—'}</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#64748b' }}>{data.note}</p>
      </section>

      {/* Most Active + Top States */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <section className={styles.panel}>
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Most Active Traders (PTR Count)</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {members.slice(0, 12).map((m, i) => (
              <div key={m.name} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.3rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ fontSize: '0.68rem', color: '#818cf8', fontWeight: 700, minWidth: 20 }}>#{i+1}</span>
                <span style={{ fontSize: '0.83rem', color: '#e2e8f0', fontWeight: 600 }}>{m.name}</span>
                <span style={{ fontSize: '0.72rem', color: '#64748b' }}>{m.state_dst}</span>
                <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#fbbf24', fontWeight: 600 }}>{m.ptr_filings} PTR</span>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.panel}>
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>States by PTR Activity</h2>
          {states.slice(0, 12).map(s => (
            <div key={s.state} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.3rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: '0.83rem' }}>
              <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{s.state || 'Unknown'}</span>
              <span style={{ color: '#c7d2fe' }}>{s.count} filings</span>
            </div>
          ))}
        </section>
      </div>

      {/* Recent PTR Filers */}
      <section className={styles.panel}>
        <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Recent PTR Filers (House)</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.5rem' }}>
          {recent.map((m, i) => (
            <div key={i} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.6rem 0.9rem' }}>
              <div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: '0.85rem' }}>{m.name}</div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: 2 }}>{m.state_dst} • Filed {m.filing_date}</div>
            </div>
          ))}
        </div>
      </section>

      {/* SEC Form 4 Insider Trades */}
      {form4.length > 0 && (
        <section className={styles.panel}>
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Recent SEC Form 4 — Corporate Insider Trades</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {form4.slice(0, 15).map((t, i) => (
              <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.35rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.72rem', background: 'rgba(129,140,248,0.1)', color: '#818cf8', padding: '1px 6px', borderRadius: 4, fontWeight: 600 }}>FORM 4</span>
                <span style={{ fontSize: '0.83rem', color: '#e2e8f0', fontWeight: 600 }}>{t.insider}</span>
                {t.company && <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>@ {t.company}</span>}
                <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: '#64748b' }}>{t.filing_date}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function InsiderTab() {
  const [ticker, setTicker] = useState('AAPL')
  const [query, setQuery] = useState('AAPL')
  const { data: insiderData, isLoading } = useSWR(
    ticker ? `${API}/market/company/insider-trades/${ticker}?limit=30` : null,
    fetcher
  )

  const POPULAR = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'PLTR', 'BABA']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <section className={styles.panel} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input className={styles.input} value={query} onChange={e => setQuery(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && setTicker(query)}
          placeholder="Ticker e.g. AAPL" style={{ maxWidth: 140, fontWeight: 700 }} />
        <button className={styles.button} onClick={() => setTicker(query)}>Look Up</button>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {POPULAR.map(t => (
            <button key={t} onClick={() => { setQuery(t); setTicker(t) }}
              style={{ background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.2)', borderRadius: 5, color: '#818cf8', padding: '2px 8px', fontSize: '0.72rem', cursor: 'pointer' }}>
              {t}
            </button>
          ))}
        </div>
      </section>

      {isLoading && <p style={{ color: '#94a3b8' }}>Loading insider trades…</p>}
      {insiderData && (
        <section className={styles.panel}>
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Insider Trades — {ticker} ({insiderData.count || 0} records)</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {(insiderData.trades || []).map((t, i) => {
              const isBuy = (t.transaction || '').toLowerCase().includes('purchase') || (t.transaction || '').toLowerCase().includes('buy')
              const isSell = (t.transaction || '').toLowerCase().includes('sale') || (t.transaction || '').toLowerCase().includes('sell')
              return (
                <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: isBuy ? '#4ade80' : isSell ? '#f87171' : '#fbbf24',
                    background: isBuy ? 'rgba(74,222,128,0.1)' : isSell ? 'rgba(248,113,113,0.1)' : 'rgba(251,191,36,0.1)',
                    padding: '1px 6px', borderRadius: 4, textTransform: 'uppercase' }}>
                    {t.transaction?.slice(0, 8)}
                  </span>
                  <span style={{ fontSize: '0.83rem', color: '#e2e8f0', fontWeight: 600 }}>{t.insider}</span>
                  <span style={{ fontSize: '0.72rem', color: '#64748b' }}>{t.title}</span>
                  <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: '#c7d2fe', fontWeight: 600 }}>
                    {t.shares?.toLocaleString()} sh {t.value_usd ? `/ $${(t.value_usd/1e6).toFixed(2)}M` : ''}
                  </span>
                  <span style={{ fontSize: '0.68rem', color: '#64748b' }}>{t.date}</span>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}

export default function GovTradingPage() {
  const [tab, setTab] = useState('summary')
  const [days, setDays] = useState(90)

  const TABS = [
    { id: 'summary', label: '🏛️ Congressional Summary' },
    { id: 'insider', label: '📊 Corporate Insider Trades' },
    { id: 'politicians', label: '👤 Politician Tracker' },
  ]

  return (
    <main className={styles.page}>
      <div className={styles.hero}>
        <h1 className={styles.heroTitle}>Government & Insider Trading</h1>
        <p className={styles.heroSub}>Congressional STOCK Act disclosures, corporate insider trades via SEC Form 4, and government financial intelligence.</p>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                padding: '0.45rem 1rem', borderRadius: 6, border: '1px solid',
                borderColor: tab === t.id ? '#818cf8' : 'var(--line)',
                background: tab === t.id ? 'rgba(129,140,248,0.15)' : 'rgba(255,255,255,0.03)',
                color: tab === t.id ? '#818cf8' : '#94a3b8',
                fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer',
              }}>
              {t.label}
            </button>
          ))}
        </div>
        {tab === 'summary' && (
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid var(--line)', borderRadius: 6, color: '#e2e8f0', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}>
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 6 months</option>
          </select>
        )}
      </div>

      {tab === 'summary' && <SummaryTab days={days} setDays={setDays} />}
      {tab === 'insider' && <InsiderTab />}
      {tab === 'politicians' && <PoliticianTab />}
    </main>
  )
}
