import { useState } from 'react'
import useSWR from 'swr'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''
const fetcher = url => fetch(url).then(r => r.json())

const fmt = (v, d = 2) => v == null ? '—' : typeof v === 'number' ? v.toFixed(d) : v
const fmtBig = v => {
  if (v == null) return '—'
  if (v >= 1e12) return `$${(v/1e12).toFixed(2)}T`
  if (v >= 1e9) return `$${(v/1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v/1e6).toFixed(2)}M`
  return `$${v.toFixed(2)}`
}
const fmtPct = v => v == null ? '—' : `${v > 0 ? '+' : ''}${Number(v).toFixed(2)}%`
const changeColor = v => !v ? '#94a3b8' : v > 0 ? '#4ade80' : '#f87171'

function DashboardTab() {
  const { data, isLoading } = useSWR(`${API}/market/crypto/dashboard`, fetcher, { refreshInterval: 60000 })
  if (isLoading) return <p style={{ color: '#94a3b8' }}>Loading market data…</p>
  if (!data) return <p style={{ color: '#f87171' }}>Failed to load data.</p>

  const g = data.global || {}
  const coins = data.top_coins || []
  const trending = data.trending || []
  const whales = data.whale_alerts || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Global Market */}
      <section className={styles.panel}>
        <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Global Market Overview</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {[
            ['Total Market Cap', fmtBig(g.total_market_cap_usd)],
            ['24h Volume', fmtBig(g.total_volume_24h_usd)],
            ['BTC Dominance', g.btc_dominance ? `${g.btc_dominance.toFixed(1)}%` : '—'],
            ['ETH Dominance', g.eth_dominance ? `${g.eth_dominance.toFixed(1)}%` : '—'],
            ['Active Cryptos', g.active_cryptos?.toLocaleString() || '—'],
            ['24h Change', fmtPct(g.market_cap_change_24h)],
          ].map(([label, val]) => (
            <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.6rem 0.9rem', minWidth: 120 }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#c7d2fe', marginTop: 2 }}>{val}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Top Coins */}
      <section className={styles.panel}>
        <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Top Cryptocurrencies</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.83rem' }}>
            <thead>
              <tr style={{ color: '#64748b', textAlign: 'left' }}>
                {['Coin', 'Price', 'Market Cap', '24h Volume', '24h Change'].map(h => (
                  <th key={h} style={{ padding: '0.4rem 0.6rem', borderBottom: '1px solid var(--line)', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {coins.slice(0, 15).map(c => (
                <tr key={c.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '0.45rem 0.6rem', color: '#e2e8f0', fontWeight: 600 }}>{c.id?.charAt(0).toUpperCase() + c.id?.slice(1)}</td>
                  <td style={{ padding: '0.45rem 0.6rem', color: '#c7d2fe', fontWeight: 600 }}>{c.price_usd ? `$${Number(c.price_usd).toLocaleString(undefined, {maximumFractionDigits: 4})}` : '—'}</td>
                  <td style={{ padding: '0.45rem 0.6rem', color: '#94a3b8' }}>{fmtBig(c.market_cap_usd)}</td>
                  <td style={{ padding: '0.45rem 0.6rem', color: '#94a3b8' }}>{fmtBig(c.volume_24h_usd)}</td>
                  <td style={{ padding: '0.45rem 0.6rem', color: changeColor(c.change_24h_pct), fontWeight: 600 }}>{fmtPct(c.change_24h_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Trending + Whale Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <section className={styles.panel}>
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>🔥 Trending (24h)</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {trending.map((c, i) => (
              <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ fontSize: '0.72rem', color: '#818cf8', fontWeight: 700, minWidth: 20 }}>#{i + 1}</span>
                <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '0.85rem' }}>{c.name}</span>
                <span style={{ color: '#fbbf24', fontSize: '0.75rem' }}>{c.symbol}</span>
                {c.rank && <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: '#64748b' }}>Rank #{c.rank}</span>}
              </div>
            ))}
          </div>
        </section>

        <section className={styles.panel}>
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>🐋 Whale Alerts</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {whales.length === 0 && <p style={{ color: '#64748b', fontSize: '0.8rem' }}>No significant whale movements.</p>}
            {whales.map(w => (
              <div key={w.symbol} style={{ padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: '0.85rem' }}>{w.symbol}</span>
                  <span style={{ fontSize: '0.68rem', background: 'rgba(251,191,36,0.15)', color: '#fbbf24', padding: '1px 6px', borderRadius: 4 }}>{w.alert_reason?.replace(/_/g, ' ')}</span>
                  <span style={{ marginLeft: 'auto', color: changeColor(w.change_1h_pct), fontWeight: 600, fontSize: '0.8rem' }}>{fmtPct(w.change_1h_pct)} 1h</span>
                </div>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: 2 }}>Vol: {fmtBig(w.volume_24h)} | 24h: {fmtPct(w.change_24h_pct)}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

function CoinDetailTab() {
  const [coinId, setCoinId] = useState('bitcoin')
  const [query, setQuery] = useState('bitcoin')
  const { data, isLoading } = useSWR(coinId ? `${API}/market/crypto/coin/${coinId}` : null, fetcher)
  const { data: flowData } = useSWR(coinId ? `${API}/market/crypto/flow/${coinId}` : null, fetcher)

  const POPULAR = ['bitcoin', 'ethereum', 'solana', 'binancecoin', 'ripple', 'dogecoin', 'cardano', 'avalanche-2']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <section className={styles.panel} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input className={styles.input} value={query} onChange={e => setQuery(e.target.value.toLowerCase())}
          onKeyDown={e => e.key === 'Enter' && setCoinId(query)}
          placeholder="CoinGecko ID e.g. bitcoin, ethereum"
          style={{ flex: 1, minWidth: 200 }} />
        <button className={styles.button} onClick={() => setCoinId(query)}>Fetch Coin</button>
        <div style={{ width: '100%', display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {POPULAR.map(id => (
            <button key={id} onClick={() => { setQuery(id); setCoinId(id) }}
              style={{ background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.2)', borderRadius: 5, color: '#818cf8', padding: '2px 8px', fontSize: '0.72rem', cursor: 'pointer' }}>
              {id}
            </button>
          ))}
        </div>
      </section>

      {isLoading && <p style={{ color: '#94a3b8' }}>Loading coin data…</p>}
      {data && !data.error && (
        <>
          <section className={styles.panel}>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '1rem' }}>
              {data.image && <img src={data.image} alt={data.name} style={{ width: 48, height: 48, borderRadius: 8 }} />}
              <div>
                <h2 style={{ margin: 0 }}>{data.name} <span style={{ color: '#fbbf24', fontSize: '0.8rem' }}>{data.symbol}</span></h2>
                <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Rank #{data.rank}</div>
              </div>
              <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#e2e8f0' }}>${data.price_usd?.toLocaleString(undefined, {maximumFractionDigits:4})}</div>
                <div style={{ color: changeColor(data.change_24h), fontWeight: 600 }}>{fmtPct(data.change_24h)} (24h)</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              {[
                ['Market Cap', fmtBig(data.market_cap)],
                ['24h Volume', fmtBig(data.volume_24h)],
                ['7d Change', fmtPct(data.change_7d)],
                ['30d Change', fmtPct(data.change_30d)],
                ['ATH', data.ath ? `$${data.ath.toLocaleString()}` : '—'],
                ['Supply', data.circulating_supply ? `${(data.circulating_supply/1e6).toFixed(2)}M` : '—'],
              ].map(([label, val]) => (
                <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.5rem 0.75rem', minWidth: 100 }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#c7d2fe' }}>{val}</div>
                </div>
              ))}
            </div>
            {data.description && (
              <p style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5 }}>{data.description}</p>
            )}
          </section>

          {flowData && !flowData.error && (
            <section className={styles.panel}>
              <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Exchange Flow Signal</h2>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: flowData.flow_signal?.includes('INFLOW') ? '#4ade80' : flowData.flow_signal?.includes('OUTFLOW') ? '#f87171' : '#fbbf24', marginBottom: '0.5rem' }}>
                {flowData.flow_signal}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                Vol/Cap Ratio: {flowData.vol_to_cap_ratio} | 24h: {fmtPct(flowData.change_24h_pct)}
              </div>
              {(flowData.top_exchanges || []).length > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '0.3rem', textTransform: 'uppercase' }}>Top Exchanges</div>
                  {flowData.top_exchanges.map(ex => (
                    <div key={ex.name} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.25rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <span style={{ color: '#e2e8f0' }}>{ex.name}</span>
                      <span style={{ color: '#c7d2fe' }}>{fmtBig(ex.volume_usd)}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  )
}

function WalletTab() {
  const [chain, setChain] = useState('eth')
  const [address, setAddress] = useState('')
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  const lookup = async () => {
    if (!query.trim()) return
    setLoading(true); setErr(''); setResult(null)
    try {
      const endpoint = chain === 'btc'
        ? `${API}/market/crypto/wallet/btc/${encodeURIComponent(query.trim())}`
        : `${API}/market/crypto/wallet/eth/${encodeURIComponent(query.trim())}`
      const r = await fetch(endpoint)
      const d = await r.json()
      if (d.error) { setErr(d.error); return }
      setResult(d)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <section className={styles.panel} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={chain} onChange={e => setChain(e.target.value)}
          style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid var(--line)', borderRadius: 6, color: '#e2e8f0', padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}>
          <option value="eth">Ethereum (ETH)</option>
          <option value="btc">Bitcoin (BTC)</option>
        </select>
        <input className={styles.input} value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && lookup()}
          placeholder={chain === 'btc' ? 'Bitcoin address (bc1q…)' : 'Ethereum address (0x…)'}
          style={{ flex: 1, minWidth: 200, fontFamily: 'monospace', fontSize: '0.82rem' }} />
        <button className={styles.button} onClick={lookup} disabled={loading}>{loading ? 'Looking up…' : 'Lookup'}</button>
        {err && <p className={styles.dangerText} style={{ width: '100%', margin: 0 }}>{err}</p>}
      </section>

      {result && (
        <section className={styles.panel}>
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Wallet Profile — {result.chain?.toUpperCase()}</h2>
          <p style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#818cf8', marginBottom: '1rem', wordBreak: 'break-all' }}>{result.address}</p>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            {result.chain === 'bitcoin' ? [
              ['Balance', `${result.balance_btc} BTC`],
              ['Total Received', `${result.total_received_btc} BTC`],
              ['Total Sent', `${result.total_sent_btc} BTC`],
              ['Transactions', result.n_tx],
            ] : [
              ['ETH Balance', `${result.balance_eth} ETH`],
              ['Token Count', result.token_count],
              ['Transactions', result.tx_count],
            ].map(([label, val]) => (
              <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.5rem 0.75rem', minWidth: 130 }}>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#c7d2fe' }}>{val}</div>
              </div>
            ))}
          </div>

          {result.tokens?.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>ERC-20 Tokens Held</div>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {result.tokens.map(t => (
                  <span key={t.symbol} style={{ background: 'rgba(129,140,248,0.1)', color: '#818cf8', borderRadius: 5, padding: '2px 8px', fontSize: '0.72rem', fontWeight: 600 }}>{t.symbol}</span>
                ))}
              </div>
            </div>
          )}

          <div>
            <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Recent Transactions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              {(result.recent_transactions || []).slice(0, 8).map((tx, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: '0.78rem' }}>
                  <span style={{ fontFamily: 'monospace', color: '#818cf8', fontSize: '0.7rem' }}>{tx.hash}</span>
                  <span style={{ color: '#fbbf24', marginLeft: 'auto', fontWeight: 600 }}>
                    {result.chain === 'bitcoin' ? `${tx.value_out_btc} BTC` : `${tx.value_eth} ETH`}
                  </span>
                  {tx.is_error && <span style={{ color: '#f87171', fontSize: '0.68rem' }}>FAILED</span>}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default function CryptoPage() {
  const [tab, setTab] = useState('dashboard')
  const TABS = [
    { id: 'dashboard', label: 'Market Dashboard' },
    { id: 'coin', label: 'Coin Detail' },
    { id: 'wallet', label: 'Wallet Lookup' },
  ]

  return (
    <main className={styles.page}>
      <div className={styles.hero}>
        <h1 className={styles.heroTitle}>Crypto Intelligence</h1>
        <p className={styles.heroSub}>Real-time market data, on-chain wallet analysis, and whale tracking across BTC, ETH and top altcoins.</p>
      </div>

      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
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

      {tab === 'dashboard' && <DashboardTab />}
      {tab === 'coin' && <CoinDetailTab />}
      {tab === 'wallet' && <WalletTab />}
    </main>
  )
}
