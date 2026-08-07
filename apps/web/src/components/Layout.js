import Link from 'next/link'
import { useRouter } from 'next/router'
import { useMemo, useState } from 'react'
import { getAdminBaseUrl, getApiBaseUrl } from '../../lib/api'

const NAV_GROUPS = [
  {
    label: 'Intelligence',
    items: [
      { href: '/',            label: 'Dashboard',     icon: '◈' },
      { href: '/intelligence',label: 'Reports',        icon: '⬡' },
      { href: '/search',      label: 'Global Search',  icon: '⌕' },
      { href: '/saved',       label: 'Saved',          icon: '⊡' },
      { href: '/timeline',    label: 'Timeline',       icon: '⊟' },
    ],
  },
  {
    label: 'Markets',
    items: [
      { href: '/stock',           label: 'Stock',        icon: '▲' },
      { href: '/valuation',       label: 'Valuation',    icon: '◎' },
      { href: '/expert-analysis', label: 'Expert',       icon: '★' },
      { href: '/company',         label: 'Company',      icon: '⬡' },
      { href: '/compare',         label: 'Compare',      icon: '⇄' },
      { href: '/economics',       label: 'Economics',    icon: '∿' },
      { href: '/consensus',       label: 'Consensus',    icon: '◈' },
    ],
  },
  {
    label: 'Institutional',
    items: [
      { href: '/institutional',   label: 'Institutional', icon: '⊞' },
      { href: '/gov-trading',     label: 'Gov Trading',   icon: '⚖' },
      { href: '/crypto',          label: 'Crypto',        icon: '◈' },
    ],
  },
  {
    label: 'Research',
    items: [
      { href: '/filing-compare',  label: 'Filing Diff',  icon: '⊟' },
      { href: '/entity-analysis', label: 'Multi-Entity', icon: '⬡' },
      { href: '/guidance',        label: 'Guidance',     icon: '◎' },
      { href: '/analysts',        label: 'Analysts',     icon: '★' },
      { href: '/volume',          label: 'Volume',       icon: '▲' },
      { href: '/formula',         label: 'Formula',      icon: 'ƒ' },
      { href: '/options',         label: 'Volatility',   icon: '∿' },
      { href: '/leaderboard',     label: 'Leaderboard',  icon: '⚑' },
    ],
  },
  {
    label: 'Tools',
    items: [
      { href: '/registry',        label: 'Registry',     icon: '⊟' },
      { href: '/graph',           label: 'Graph',        icon: '⬡' },
      { href: '/tracking',        label: 'Tracking',     icon: '◎' },
      { href: '/tracking/alerts', label: 'Alerts',       icon: '⚑' },
      { href: '/skills',          label: 'Skills',       icon: '⚙' },
    ],
  },
  {
    label: 'Account',
    items: [
      { href: '/pricing',         label: 'Pricing',      icon: '$' },
      { href: '/billing',         label: 'Billing',      icon: '⊡' },
      { href: '/support',         label: 'Support',      icon: '?' },
      { href: '/status',          label: 'Status',       icon: '◉' },
    ],
  },
]

export default function Layout({ children }) {
  const router = useRouter()
  const path = router.pathname || '/'
  const adminUrl = useMemo(() => getAdminBaseUrl(), [])
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const isActive = (href) =>
    href === '/' ? path === '/' : path === href || path.startsWith(`${href}/`)

  // Find current page label for breadcrumb
  const currentPage = NAV_GROUPS.flatMap(g => g.items).find(i => isActive(i.href))

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)' }}>

      {/* ── Sidebar ──────────────────────────────────────────────── */}
      <aside style={{
        width: sidebarOpen ? '220px' : '56px',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-elev-1)',
        borderRight: '1px solid var(--line)',
        transition: 'width 0.2s ease',
        overflow: 'hidden',
        zIndex: 40,
      }}>
        {/* Logo */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: sidebarOpen ? '16px 16px 12px' : '16px 0 12px',
          justifyContent: sidebarOpen ? 'flex-start' : 'center',
          borderBottom: '1px solid var(--line)',
          minHeight: 56,
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: 'linear-gradient(135deg, #6366f1, #818cf8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.75rem', fontWeight: 900, color: '#fff', flexShrink: 0,
            boxShadow: '0 2px 8px rgba(99,102,241,0.5)',
          }}>EI</div>
          {sidebarOpen && (
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#e2e8f0', letterSpacing: '-0.01em', lineHeight: 1.2 }}>Enterprise</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-soft)', letterSpacing: '0.02em' }}>Intelligence</div>
            </div>
          )}
        </div>

        {/* Nav Groups */}
        <nav style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: '8px 0' }}>
          {NAV_GROUPS.map(group => (
            <div key={group.label} style={{ marginBottom: 4 }}>
              {sidebarOpen && (
                <div style={{
                  padding: '8px 16px 4px',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: 'var(--text-soft)',
                }}>
                  {group.label}
                </div>
              )}
              {group.items.map(item => {
                const active = isActive(item.href)
                return (
                  <Link href={item.href} key={item.href} legacyBehavior>
                    <a
                      title={!sidebarOpen ? item.label : undefined}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: sidebarOpen ? '7px 12px 7px 14px' : '9px 0',
                        margin: '1px 6px',
                        borderRadius: 8,
                        textDecoration: 'none',
                        fontSize: '0.82rem',
                        fontWeight: active ? 700 : 500,
                        color: active ? '#e2e8f0' : 'var(--text-muted)',
                        background: active
                          ? 'linear-gradient(90deg, rgba(99,102,241,0.22), rgba(99,102,241,0.08))'
                          : 'transparent',
                        borderLeft: active ? '2px solid var(--brand)' : '2px solid transparent',
                        transition: 'all 0.12s',
                        justifyContent: sidebarOpen ? 'flex-start' : 'center',
                        position: 'relative',
                      }}
                      onMouseEnter={e => {
                        if (!active) {
                          e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
                          e.currentTarget.style.color = '#e2e8f0'
                        }
                      }}
                      onMouseLeave={e => {
                        if (!active) {
                          e.currentTarget.style.background = 'transparent'
                          e.currentTarget.style.color = 'var(--text-muted)'
                        }
                      }}
                    >
                      <span style={{
                        fontSize: '0.9rem',
                        width: 18,
                        textAlign: 'center',
                        flexShrink: 0,
                        color: active ? 'var(--brand-hover)' : 'inherit',
                      }}>{item.icon}</span>
                      {sidebarOpen && item.label}
                    </a>
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>

        {/* Bottom actions */}
        <div style={{ padding: '8px 6px', borderTop: '1px solid var(--line)' }}>
          <a
            href={adminUrl}
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: sidebarOpen ? '7px 14px' : '9px 0',
              borderRadius: 8,
              fontSize: '0.78rem',
              fontWeight: 600,
              color: 'var(--text-soft)',
              textDecoration: 'none',
              justifyContent: sidebarOpen ? 'flex-start' : 'center',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--text)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-soft)' }}
          >
            <span style={{ fontSize: '0.9rem', width: 18, textAlign: 'center' }}>⚙</span>
            {sidebarOpen && 'Admin Panel'}
          </a>
        </div>
      </aside>

      {/* ── Main Area ─────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Top Bar */}
        <header style={{
          height: 52,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          borderBottom: '1px solid var(--line)',
          background: 'rgba(6,11,23,0.88)',
          backdropFilter: 'blur(12px)',
          flexShrink: 0,
          zIndex: 30,
          gap: '1rem',
        }}>
          {/* Left: toggle + breadcrumb */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={() => setSidebarOpen(v => !v)}
              style={{
                background: 'transparent', border: '1px solid var(--line)', borderRadius: 7,
                color: 'var(--text-muted)', cursor: 'pointer', padding: '5px 8px',
                fontSize: '0.85rem', lineHeight: 1, transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--line-strong)'; e.currentTarget.style.color = 'var(--text)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--line)'; e.currentTarget.style.color = 'var(--text-muted)' }}
            >
              ☰
            </button>
            {currentPage && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <span>Enterprise Intelligence</span>
                <span style={{ color: 'var(--line-strong)' }}>/</span>
                <span style={{ color: 'var(--text)', fontWeight: 600 }}>{currentPage.label}</span>
              </div>
            )}
          </div>

          {/* Right: live indicator + links */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              <span className="pulse-dot" />
              <span>Live</span>
            </div>
            <a
              href="http://184.72.123.188:3001/docs"
              target="_blank"
              rel="noreferrer"
              style={{
                fontSize: '0.72rem', color: 'var(--text-soft)', padding: '4px 10px',
                border: '1px solid var(--line)', borderRadius: 6, transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--line-strong)'; e.currentTarget.style.color = 'var(--text)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--line)'; e.currentTarget.style.color = 'var(--text-soft)' }}
            >
              API Docs ↗
            </a>
          </div>
        </header>

        {/* Page Content */}
        <main style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.5rem 1.75rem 2rem',
        }}>
          {children}
        </main>
      </div>
    </div>
  )
}
