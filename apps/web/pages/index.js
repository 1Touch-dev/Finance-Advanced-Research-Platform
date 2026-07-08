import Head from 'next/head'
import Link from 'next/link'
import { useState, useEffect } from 'react'
import { getApiBaseUrl } from '../lib/api'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const FEATURE_CARDS = [
  {
    group: 'Markets',
    color: '#6366f1',
    items: [
      { href: '/stock',           label: 'Stock Analysis',      desc: 'Price, technicals, AI consensus',      icon: '▲' },
      { href: '/valuation',       label: 'DCF Valuation',       desc: 'Intrinsic value vs market price',       icon: '◎' },
      { href: '/expert-analysis', label: 'Expert Analysis',     desc: 'Analyst ratings & sentiment trend',     icon: '★' },
      { href: '/company',         label: 'Deep Company',        desc: 'SEC filings, cap table, earnings',      icon: '⬡' },
      { href: '/institutional',   label: 'Institutional (13F)', desc: 'BlackRock, Vanguard, Berkshire flows',  icon: '⊞' },
      { href: '/compare',         label: 'Compare',             desc: 'Side-by-side entity analysis',         icon: '⇄' },
    ]
  },
  {
    group: 'Intelligence',
    color: '#10b981',
    items: [
      { href: '/intelligence',  label: 'Intelligence Reports',  desc: 'Multi-source entity dossiers',          icon: '⬡' },
      { href: '/search',        label: 'Global Search',         desc: 'Search all articles & reports',         icon: '⌕' },
      { href: '/timeline',      label: 'Event Timeline',        desc: 'Chronological signal history',          icon: '⊟' },
      { href: '/saved',         label: 'Saved Reports',         desc: 'Archived intelligence reports',         icon: '⊡' },
      { href: '/tracking',      label: 'Tracking',              desc: 'Monitor entities & events',             icon: '◎' },
      { href: '/tracking/alerts', label: 'Alerts',              desc: 'Event-triggered notifications',         icon: '⚑' },
    ]
  },
  {
    group: 'Government & Crypto',
    color: '#f59e0b',
    items: [
      { href: '/gov-trading',   label: 'Gov Trading',           desc: 'STOCK Act PTRs + Politician tracker',   icon: '⚖' },
      { href: '/crypto',        label: 'Crypto Intelligence',   desc: 'Market, wallets, whale alerts',          icon: '◈' },
      { href: '/economics',     label: 'Economics',             desc: 'GDP, CPI, rates, FRED data',             icon: '∿' },
      { href: '/registry',      label: 'Entity Registry',       desc: 'OSINT enrichment + private intel',       icon: '⊟' },
      { href: '/graph',         label: 'Relationship Graph',    desc: 'Network of entity connections',          icon: '⬡' },
      { href: '/skills',        label: 'Skills & Agents',       desc: 'AI agent skill library',                icon: '⚙' },
    ]
  },
]

function QuickSearch() {
  const [q, setQ] = useState('')
  const router = typeof window !== 'undefined' ? require('next/router').useRouter() : null

  const go = () => {
    if (q.trim() && router) router.push(`/search?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <div style={{ display: 'flex', gap: 8, maxWidth: 520 }}>
      <input
        className="inp"
        style={{ flex: 1, fontSize: '0.9rem', padding: '10px 14px' }}
        placeholder="Search entities, tickers, companies…"
        value={q}
        onChange={e => setQ(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && go()}
      />
      <button className="btn btn-primary" onClick={go} style={{ padding: '10px 18px' }}>
        Search
      </button>
    </div>
  )
}

function StatBar() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    if (!API) return
    fetch(`${API}/market/rss/stats`).then(r => r.json()).then(setStats).catch(() => {})
  }, [])

  const items = [
    { label: 'Articles Ingested', value: stats?.total_articles?.toLocaleString() ?? '—', color: 'var(--brand-hover)' },
    { label: 'RSS Sources', value: stats?.active_sources?.toLocaleString() ?? '50+', color: '#06b6d4' },
    { label: 'Entities Tracked', value: stats?.entities_count?.toLocaleString() ?? '15+', color: '#10b981' },
    { label: 'API Endpoints', value: '60+', color: '#a855f7' },
    { label: 'Data Sources', value: '20+', color: '#f59e0b' },
  ]

  return (
    <div style={{
      display: 'flex', gap: '1.5rem', flexWrap: 'wrap',
      padding: '12px 20px',
      background: 'var(--bg-elev-1)',
      border: '1px solid var(--line)',
      borderRadius: 'var(--radius-md)',
    }}>
      {items.map(item => (
        <div key={item.label} style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 800, color: item.color, letterSpacing: '-0.02em' }}>{item.value}</div>
          <div className="stat-label" style={{ marginBottom: 0 }}>{item.label}</div>
        </div>
      ))}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="pulse-dot" />
        <span style={{ fontSize: '0.72rem', color: 'var(--text-soft)' }}>Live data feeds active</span>
      </div>
    </div>
  )
}

export default function Home() {
  return (
    <>
      <Head>
        <title>Enterprise Intelligence Platform</title>
        <meta name="description" content="Financial intelligence, market research, and public-record analysis." />
      </Head>

      <div className="page-wrap">
        {/* Hero */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(6,11,23,0) 60%), var(--bg-elev-1)',
          border: '1px solid var(--line-md)',
          borderRadius: 'var(--radius-lg)',
          padding: '2rem 2rem 1.75rem',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Background glow */}
          <div style={{
            position: 'absolute', top: -60, right: -60,
            width: 280, height: 280,
            background: 'radial-gradient(circle, rgba(99,102,241,0.12), transparent 70%)',
            pointerEvents: 'none',
          }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '0.75rem' }}>
            <span className="badge badge-brand">
              <span className="pulse-dot" style={{ width: 5, height: 5 }} />
              All Systems Live
            </span>
            <span className="badge badge-gray">8th July 2026</span>
          </div>

          <h1 style={{
            fontSize: 'clamp(1.6rem, 3vw, 2.4rem)',
            fontWeight: 900,
            letterSpacing: '-0.035em',
            color: '#f1f5f9',
            margin: '0 0 0.5rem',
            lineHeight: 1.15,
          }}>
            Enterprise Intelligence<br />
            <span style={{ color: 'var(--brand-hover)' }}>Platform</span>
          </h1>
          <p style={{
            color: 'var(--text-muted)',
            fontSize: '0.92rem',
            margin: '0 0 1.5rem',
            maxWidth: 540,
            lineHeight: 1.6,
          }}>
            Financial markets, intelligence reports, institutional flows, government trading,
            crypto analytics, and OSINT — unified in one research platform.
          </p>

          <QuickSearch />
        </div>

        {/* Stats Bar */}
        <StatBar />

        {/* Feature Groups */}
        {FEATURE_CARDS.map(group => (
          <div key={group.group}>
            <div className="section-title" style={{ color: group.color, marginBottom: '0.75rem' }}>
              ── {group.group}
            </div>
            <div style={{ display: 'grid', gap: '0.6rem', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
              {group.items.map(item => (
                <Link href={item.href} key={item.href}>
                  <a className="card card-hover" style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 12,
                    padding: '14px 16px',
                    textDecoration: 'none',
                  }}>
                    <div style={{
                      width: 34, height: 34, borderRadius: 9, flexShrink: 0,
                      background: `${group.color}1a`,
                      border: `1px solid ${group.color}33`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.85rem', color: group.color,
                    }}>
                      {item.icon}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#e2e8f0', marginBottom: 2 }}>{item.label}</div>
                      <div style={{ fontSize: '0.73rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{item.desc}</div>
                    </div>
                    <span style={{ marginLeft: 'auto', color: 'var(--text-soft)', fontSize: '0.7rem', paddingTop: 2 }}>→</span>
                  </a>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
