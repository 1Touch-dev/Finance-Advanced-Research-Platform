import { useState } from 'react'
import useSWR from 'swr'
import { getApiBaseUrl, apiFetch } from '../lib/api'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''
const fetcher = url => apiFetch(url).then(r => r.json())

const fmt  = (v, d = 2) => v == null ? '—' : typeof v === 'number' ? v.toFixed(d) : v
const fmtBig = v => {
  if (v == null) return '—'
  if (v >= 1e12) return `$${(v/1e12).toFixed(2)}T`
  if (v >= 1e9)  return `$${(v/1e9).toFixed(2)}B`
  if (v >= 1e6)  return `$${(v/1e6).toFixed(2)}M`
  return `$${Number(v).toFixed(2)}`
}
const fmtPct = v => v == null ? '—' : `${v > 0 ? '+' : ''}${Number(v).toFixed(2)}%`
const chgColor = v => !v ? 'var(--text-muted)' : v > 0 ? 'var(--green)' : 'var(--red)'

const TABS = ['Dashboard', 'Coin Detail', 'Wallet Lookup']

function GlobeStats({ g }) {
  const stats = [
    { label: 'Total Mkt Cap',   value: fmtBig(g.total_market_cap_usd),   color: '#c7d2fe' },
    { label: '24h Volume',      value: fmtBig(g.total_volume_24h_usd),   color: '#c7d2fe' },
    { label: 'BTC Dominance',   value: g.btc_dominance ? `${g.btc_dominance.toFixed(1)}%` : '—', color: '#f59e0b' },
    { label: 'ETH Dominance',   value: g.eth_dominance ? `${g.eth_dominance.toFixed(1)}%` : '—', color: '#6366f1' },
    { label: 'Active Cryptos',  value: g.active_cryptos?.toLocaleString() || '—', color: '#10b981' },
    { label: 'Mkt Cap 24h Chg', value: fmtPct(g.market_cap_change_24h), color: chgColor(g.market_cap_change_24h) },
  ]
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.6rem' }}>
      {stats.map(s => (
        <div key={s.label} className="stat-card">
          <div className="stat-label">{s.label}</div>
          <div className="stat-value" style={{ fontSize: '1rem', color: s.color }}>{s.value}</div>
        </div>
      ))}
    </div>
  )
}

function DashboardTab() {
  const { data, isLoading, error } = useSWR(`${API}/market/crypto/dashboard`, fetcher, { refreshInterval: 60000 })

  if (isLoading) return (
    <div style={{ display: 'grid', gap: '0.75rem' }}>
      {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 80, borderRadius: 12 }} />)}
    </div>
  )
  if (!data || error) return <div className="badge badge-red" style={{ padding: '10px 14px', borderRadius: 10 }}>Failed to load crypto data.</div>

  const g      = data.global || {}
  const coins  = data.top_coins || []
  const trending = data.trending || []
  const whales = data.whale_alerts || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Global stats */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div className="section-title">Global Market</div>
        <GlobeStats g={g} />
      </div>

      {/* Top Coins table */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div className="section-title">Top Cryptocurrencies</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                {['#', 'Coin', 'Price', 'Mkt Cap', '24h Vol', '24h Δ', '7d Δ'].map(h => <th key={h}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {coins.map((c, i) => (
                <tr key={c.id}>
                  <td style={{ color: 'var(--text-soft)', fontWeight: 600 }}>{i + 1}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '0.82rem' }}>{c.name}</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-soft)', textTransform: 'uppercase' }}>{c.symbol}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontWeight: 700, color: '#c7d2fe' }}>${fmt(c.price_usd || c.current_price)}</td>
                  <td>{fmtBig(c.market_cap_usd || c.market_cap)}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{fmtBig(c.volume_24h_usd || c.total_volume)}</td>
                  <td style={{ color: chgColor(c.change_24h_pct ?? c.price_change_percentage_24h), fontWeight: 700 }}>
                    {fmtPct(c.change_24h_pct ?? c.price_change_percentage_24h)}
                  </td>
                  <td style={{ color: chgColor(c.change_7d_pct ?? c.price_change_percentage_7d_in_currency), fontWeight: 600 }}>
                    {fmtPct(c.change_7d_pct ?? c.price_change_percentage_7d_in_currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        {/* Trending */}
        <div className="card" style={{ padding: '1rem 1.25rem' }}>
          <div className="section-title">🔥 Trending Coins</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {trending.slice(0, 7).map((t, i) => (
              <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ color: 'var(--text-soft)', minWidth: 20, fontSize: '0.72rem' }}>{i + 1}</span>
                {t.thumb && <img src={t.thumb} width={18} height={18} style={{ borderRadius: '50%' }} alt="" />}
                <span style={{ fontWeight: 600, fontSize: '0.8rem', flex: 1 }}>{t.name}</span>
                <span className="badge badge-gray" style={{ fontSize: '0.62rem' }}>{t.symbol?.toUpperCase()}</span>
                {t.price_btc && <span style={{ fontSize: '0.7rem', color: 'var(--text-soft)' }}>{Number(t.price_btc).toExponential(2)} BTC</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Whale Alerts */}
        <div className="card" style={{ padding: '1rem 1.25rem' }}>
          <div className="section-title">🐋 Whale Alerts</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {whales.length === 0 && <div style={{ color: 'var(--text-soft)', fontSize: '0.8rem' }}>No recent whale transactions.</div>}
            {whales.slice(0, 7).map((w, i) => (
              <div key={i} style={{ padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.8rem', color: '#10b981' }}>{fmtBig(w.usd_value)}</span>
                  <span className="badge badge-cyan" style={{ fontSize: '0.6rem' }}>{w.symbol?.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 2 }}>
                  {w.from?.slice(0, 12)}… → {w.to?.slice(0, 12)}…
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function CoinTab() {
  const [coinId, setCoinId] = useState('bitcoin')
  const [input, setInput] = useState('bitcoin')
  const [query, setQuery] = useState('bitcoin')

  const { data, isLoading } = useSWR(`${API}/market/crypto/coin/${query}`, fetcher)

  const run = () => setQuery(input.toLowerCase().trim())

  if (!data && !isLoading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <input className="inp" value={input} onChange={e => setInput(e.target.value)} placeholder="e.g. bitcoin, ethereum, solana" style={{ flex: 1 }} onKeyDown={e => e.key === 'Enter' && run()} />
        <button className="btn btn-primary" onClick={run}>Fetch</button>
      </div>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <input className="inp" value={input} onChange={e => setInput(e.target.value)} placeholder="e.g. bitcoin, ethereum, solana" style={{ flex: 1 }} onKeyDown={e => e.key === 'Enter' && run()} />
        <button className="btn btn-primary" onClick={run}>Fetch</button>
      </div>

      {isLoading && <div className="skeleton" style={{ height: 200, borderRadius: 12 }} />}

      {data && !data.error && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Header */}
          <div className="card" style={{ padding: '1.25rem 1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1rem' }}>
              {data.image && <img src={data.image} width={40} height={40} style={{ borderRadius: '50%' }} alt={data.name} />}
              <div>
                <div style={{ fontWeight: 800, fontSize: '1.2rem', color: '#e2e8f0' }}>{data.name}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{data.symbol}</div>
              </div>
              {data.market_data?.price_change_percentage_24h != null && (
                <span className="badge" style={{ marginLeft: 'auto', color: chgColor(data.market_data.price_change_percentage_24h), background: chgColor(data.market_data.price_change_percentage_24h) + '18', borderColor: chgColor(data.market_data.price_change_percentage_24h) + '33', fontSize: '0.75rem' }}>
                  {fmtPct(data.market_data.price_change_percentage_24h)} (24h)
                </span>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.6rem' }}>
              {[
                ['Price (USD)', data.market_data?.current_price?.usd != null ? `$${fmt(data.market_data.current_price.usd)}` : '—', '#c7d2fe'],
                ['Market Cap', fmtBig(data.market_data?.market_cap?.usd), '#a5f3fc'],
                ['24h Volume', fmtBig(data.market_data?.total_volume?.usd), '#86efac'],
                ['ATH', data.market_data?.ath?.usd ? `$${fmt(data.market_data.ath.usd)}` : '—', '#fbbf24'],
                ['ATL', data.market_data?.atl?.usd ? `$${fmt(data.market_data.atl.usd)}` : '—', '#f87171'],
                ['Market Cap Rank', `#${data.market_cap_rank || '—'}`, '#d8b4fe'],
                ['Circulating Supply', data.market_data?.circulating_supply?.toLocaleString() ?? '—', 'var(--text-muted)'],
                ['Total Supply', data.market_data?.total_supply?.toLocaleString() ?? '—', 'var(--text-muted)'],
              ].map(([label, value, color]) => (
                <div key={label} className="stat-card">
                  <div className="stat-label">{label}</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color }}>{value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Description */}
          {data.description && (
            <div className="card" style={{ padding: '1rem 1.25rem' }}>
              <div className="section-title">About</div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', lineHeight: 1.7, margin: 0 }}>
                {data.description.replace(/<[^>]*>/g, '').slice(0, 600)}{data.description.length > 600 ? '…' : ''}
              </p>
            </div>
          )}
        </div>
      )}
      {data?.error && <div className="badge badge-red" style={{ padding: '10px', borderRadius: 10 }}>{data.error}</div>}
    </div>
  )
}

function WalletTab() {
  const [network, setNetwork] = useState('eth')
  const [addr, setAddr] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const lookup = async () => {
    if (!addr.trim()) return
    setLoading(true); setErr(''); setResult(null)
    try {
      const endpoint = network === 'eth'
        ? `${API}/market/crypto/wallet/eth/${addr.trim()}`
        : `${API}/market/crypto/wallet/btc/${addr.trim()}`
      const data = await apiFetch(endpoint).then(r => r.json())
      if (data.error) setErr(data.error)
      else setResult(data)
    } catch (e) { setErr(e.message) }
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div className="section-title">Wallet / Address Lookup</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <select className="inp" value={network} onChange={e => setNetwork(e.target.value)} style={{ width: 90 }}>
            <option value="eth">ETH</option>
            <option value="btc">BTC</option>
          </select>
          <input className="inp" value={addr} onChange={e => setAddr(e.target.value)} placeholder="Wallet address…" style={{ flex: 1, minWidth: 200 }} onKeyDown={e => e.key === 'Enter' && lookup()} />
          <button className="btn btn-primary" onClick={lookup} disabled={loading}>{loading ? '…' : 'Lookup'}</button>
        </div>
      </div>

      {err && <div className="badge badge-red" style={{ padding: '10px', borderRadius: 10 }}>{err}</div>}

      {result && (
        <div className="card" style={{ padding: '1rem 1.25rem' }}>
          <div className="section-title">Wallet Profile · {network.toUpperCase()}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.6rem', marginBottom: '1rem' }}>
            {Object.entries(result)
              .filter(([k]) => k !== 'address' && k !== 'error' && typeof result[k] !== 'object')
              .map(([k, v]) => (
                <div key={k} className="stat-card">
                  <div className="stat-label">{k.replace(/_/g, ' ')}</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#c7d2fe', wordBreak: 'break-all' }}>
                    {typeof v === 'number' ? (Math.abs(v) > 1e8 ? fmtBig(v) : fmt(v, 4)) : String(v)}
                  </div>
                </div>
              ))}
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: 'var(--text-soft)', wordBreak: 'break-all' }}>
            Address: {result.address || addr}
          </div>
        </div>
      )}
    </div>
  )
}

export default function CryptoPage() {
  const [tab, setTab] = useState(0)

  return (
    <div className="page-wrap">
      <div className="page-header">
        <div>
          <h1 className="page-title">Crypto Intelligence</h1>
          <p className="page-sub">Market overview · Coin detail · Wallet tracking · Whale alerts</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="pulse-dot" />
          <span style={{ fontSize: '0.72rem', color: 'var(--text-soft)' }}>Live CoinGecko feed</span>
        </div>
      </div>

      <div className="tabs-bar">
        {TABS.map((t, i) => (
          <button key={t} className={`tab-btn${tab === i ? ' active' : ''}`} onClick={() => setTab(i)}>{t}</button>
        ))}
      </div>

      {tab === 0 && <DashboardTab />}
      {tab === 1 && <CoinTab />}
      {tab === 2 && <WalletTab />}
    </div>
  )
}
