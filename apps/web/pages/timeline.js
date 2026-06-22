import { useState, useMemo } from 'react'
import { useRouter } from 'next/router'
import styles from '../src/styles/Page.module.css'
import eStyles from '../src/styles/Entity.module.css'
import tStyles from '../src/styles/Timeline.module.css'
import { getApiBaseUrl } from '../lib/api'
import Link from 'next/link'

const API = getApiBaseUrl()

// ── Category config ───────────────────────────────────────────────────────────

const CATEGORIES = [
  { id: 'all',        label: 'All',       color: '#c7d2fe' },
  { id: 'career',     label: 'Career',    color: '#60a5fa' },
  { id: 'financial',  label: 'Financial', color: '#4ade80' },
  { id: 'legal',      label: 'Legal',     color: '#f87171' },
  { id: 'government', label: 'Government',color: '#fbbf24' },
  { id: 'news',       label: 'News',      color: '#a78bfa' },
  { id: 'education',  label: 'Education', color: '#34d399' },
]

const CAT_COLOR = Object.fromEntries(CATEGORIES.map(c => [c.id, c.color]))

// ── Demo seeded timeline events (for Palantir / Peter Thiel / Elon Musk) ─────

const DEMO_TIMELINES = {
  'Peter Thiel': [
    { date: '1968', category: 'education', text: 'Born in Frankfurt, Germany. Moved to US as a child.', source: 'Wikipedia' },
    { date: '1989', category: 'education', text: 'Graduated from Stanford University (BA in Philosophy).', source: 'Wikipedia' },
    { date: '1992', category: 'education', text: 'Graduated Stanford Law School (JD).', source: 'Wikipedia' },
    { date: '1998', category: 'career',    text: 'Co-founded PayPal with Max Levchin and others.', source: 'Wikipedia' },
    { date: '2002', category: 'financial', text: 'PayPal acquired by eBay for $1.5B. Thiel receives ~$55M.', source: 'SEC/M&A records' },
    { date: '2003', category: 'career',    text: 'Founded Palantir Technologies with Alex Karp.', source: 'Palantir S-1' },
    { date: '2004', category: 'financial', text: 'Invested $500K in Facebook as first outside investor.', source: 'SEC' },
    { date: '2005', category: 'career',    text: 'Founded Founders Fund VC firm.', source: 'Founders Fund' },
    { date: '2011', category: 'career',    text: 'Launched Thiel Fellowship — $100K grants for 20-Under-20.', source: 'Thiel Foundation' },
    { date: '2016', category: 'government', text: 'Spoke at Republican National Convention; donated to Trump campaign.', source: 'FEC OpenData' },
    { date: '2016', category: 'legal',     text: 'Funded Hulk Hogan lawsuit against Gawker Media ($140M verdict).', source: 'Court records' },
    { date: '2020', category: 'financial', text: 'Palantir Technologies IPO (NYSE: PLTR) — direct listing at $9.50/share.', source: 'SEC S-1' },
    { date: '2022', category: 'government', text: 'Retired from Palantir board. Focused on political donations.', source: 'SEC Form 4' },
    { date: '2022', category: 'financial', text: 'Net worth estimated at ~$7.5B (Forbes).', source: 'Forbes' },
  ],
  'Elon Musk': [
    { date: '1971', category: 'education',  text: 'Born in Pretoria, South Africa.', source: 'Wikipedia' },
    { date: '1995', category: 'career',     text: 'Co-founded Zip2 with brother Kimbal Musk.', source: 'Wikipedia' },
    { date: '1999', category: 'financial',  text: 'Zip2 acquired by Compaq for $307M.', source: 'SEC' },
    { date: '1999', category: 'career',     text: 'Founded X.com (became PayPal after merger with Confinity).', source: 'Wikipedia' },
    { date: '2002', category: 'financial',  text: 'PayPal acquired by eBay for $1.5B; Musk earns ~$180M.', source: 'SEC' },
    { date: '2002', category: 'career',     text: 'Founded SpaceX.', source: 'SpaceX' },
    { date: '2004', category: 'career',     text: 'Joined Tesla Motors as chairman and lead investor.', source: 'SEC' },
    { date: '2008', category: 'legal',      text: 'Near-bankruptcy for Tesla and SpaceX. Diverted funds.', source: 'WSJ' },
    { date: '2018', category: 'legal',      text: 'SEC charged Musk over "funding secured" tweet. Settled $20M.', source: 'SEC' },
    { date: '2022', category: 'financial',  text: 'Acquired Twitter for $44B.', source: 'SEC 13D' },
    { date: '2024', category: 'government', text: 'Donated $250M+ to Trump PAC; appointed to DOGE advisory role.', source: 'FEC OpenData' },
  ],
  'Palantir Technologies': [
    { date: '2003', category: 'career',     text: 'Founded by Peter Thiel, Alex Karp, Joe Lonsdale, and others in Palo Alto.', source: 'Palantir S-1' },
    { date: '2004', category: 'financial',  text: 'First VC funding — $2M seed from Founders Fund and Thiel.', source: 'PitchBook' },
    { date: '2006', category: 'government', text: 'CIA-funded through In-Q-Tel. First government contract.', source: 'SEC' },
    { date: '2010', category: 'government', text: 'NSA, FBI, and DHS contracts; Palantir Gotham deployed in counterterrorism.', source: 'Media' },
    { date: '2014', category: 'legal',      text: 'Sued for gender discrimination; settled out of court.', source: 'Court records' },
    { date: '2015', category: 'legal',      text: 'OFCCP lawsuit over hiring discrimination at US DoL.', source: 'Court records' },
    { date: '2016', category: 'government', text: 'Won $876M US Army contract for intelligence systems.', source: 'USASpending' },
    { date: '2020', category: 'financial',  text: 'IPO via direct listing (NYSE: PLTR) at $9.50. Market cap $16B.', source: 'SEC S-1' },
    { date: '2021', category: 'government', text: 'Awarded $823M TITAN contract for US Army battlefield AI.', source: 'USASpending' },
    { date: '2023', category: 'financial',  text: 'Added to S&P 500 index.', source: 'S&P' },
    { date: '2024', category: 'financial',  text: 'Revenue $2.87B; first year of GAAP profitability.', source: 'SEC 10-K' },
  ],
}

function getDemo(name) {
  const key = Object.keys(DEMO_TIMELINES).find(k => k.toLowerCase() === name.toLowerCase())
  return key ? DEMO_TIMELINES[key] : null
}

// ── Timeline Event Card ───────────────────────────────────────────────────────

function EventCard({ ev, isLast }) {
  const color  = CAT_COLOR[ev.category] || '#818cf8'
  const catCfg = CATEGORIES.find(c => c.id === ev.category) || CATEGORIES[0]
  return (
    <div className={tStyles.event}>
      <div className={tStyles.eventLeft}>
        <div className={tStyles.dot} style={{ background: color }} />
        {!isLast && <div className={tStyles.line} />}
      </div>
      <div className={tStyles.eventCard}>
        <div className={tStyles.eventHeader}>
          <span className={tStyles.eventDate}>{ev.date}</span>
          <span className={tStyles.eventCat} style={{ background: `${color}22`, color, borderColor: `${color}55` }}>
            {catCfg.label}
          </span>
          {ev.source && <span className={tStyles.eventSrc}>{ev.source}</span>}
        </div>
        <p className={tStyles.eventText}>{ev.text}</p>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TimelinePage() {
  const router = useRouter()
  const [entityName, setEntityName]   = useState('Peter Thiel')
  const [loading,    setLoading]      = useState(false)
  const [events,     setEvents]       = useState(DEMO_TIMELINES['Peter Thiel'])
  const [loaded,     setLoaded]       = useState('Peter Thiel')
  const [filterCat,  setFilterCat]    = useState('all')
  const [search,     setSearch]       = useState('')
  const [viewMode,   setViewMode]     = useState('vertical') // 'vertical' | 'cards'

  const load = async () => {
    // Check demo first
    const demo = getDemo(entityName)
    if (demo) {
      setEvents(demo)
      setLoaded(entityName)
      return
    }

    setLoading(true)
    try {
      // Try to get timeline from entities API
      const r = await fetch(`${API}/intelligence/generate?entity_name=${encodeURIComponent(entityName)}&entity_type=org`, {
        method: 'POST',
      })
      if (r.ok) {
        const data = await r.json()
        // Build timeline from sections
        const built = []
        for (const sec of (data.sections || [])) {
          const cat = guessCategory(sec.name)
          for (const claim of (sec.claims || []).slice(0, 5)) {
            const text = (claim.text || claim || '').replace(/^\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*/, '')
            if (text) {
              built.push({
                date:     new Date().getFullYear().toString(),
                category: cat,
                text:     text.slice(0, 300),
                source:   claim.source || sec.name,
              })
            }
          }
        }
        setEvents(built.slice(0, 40))
        setLoaded(entityName)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  function guessCategory(sectionName) {
    const n = (sectionName || '').toLowerCase()
    if (n.includes('linkedin') || n.includes('people') || n.includes('career')) return 'career'
    if (n.includes('sec') || n.includes('fund') || n.includes('contract')) return 'financial'
    if (n.includes('court') || n.includes('litigation') || n.includes('sanction')) return 'legal'
    if (n.includes('fec') || n.includes('fara') || n.includes('government') || n.includes('lda')) return 'government'
    if (n.includes('news')) return 'news'
    return 'career'
  }

  const filtered = useMemo(() => {
    let evs = [...events].sort((a, b) => {
      const ya = parseInt(a.date) || 0
      const yb = parseInt(b.date) || 0
      return ya - yb
    })
    if (filterCat !== 'all') evs = evs.filter(e => e.category === filterCat)
    if (search)              evs = evs.filter(e =>
      (e.text || '').toLowerCase().includes(search.toLowerCase()) ||
      (e.source || '').toLowerCase().includes(search.toLowerCase())
    )
    return evs
  }, [events, filterCat, search])

  const SEEDS = [
    { label: 'Peter Thiel', type: 'person' },
    { label: 'Elon Musk',   type: 'person' },
    { label: 'Palantir Technologies', type: 'org' },
  ]

  return (
    <main className={styles.page}>
      {/* Header */}
      <section className={styles.hero}>
        <p style={{ margin: '0 0 0.4rem', fontSize: '0.75rem', fontWeight: 700,
                    letterSpacing: '0.08em', textTransform: 'uppercase', color: '#818cf8' }}>
          Layer 1 v1.2 — Person &amp; Entity Timeline
        </p>
        <h1 style={{ margin: 0 }}>Intelligence Timeline</h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', maxWidth: 640 }}>
          Chronological event timeline — career moves, filings, contracts, legal events,
          and news for any person or organization.
        </p>
      </section>

      {/* Quick seeds */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)' }}>Quick:</span>
        {SEEDS.map(s => (
          <button
            key={s.label}
            onClick={() => { setEntityName(s.label); setEvents(DEMO_TIMELINES[s.label] || []); setLoaded(s.label) }}
            style={{
              background: 'rgba(129,140,248,0.1)',
              border: '1px solid rgba(129,140,248,0.3)',
              borderRadius: 7,
              color: '#c7d2fe',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 600,
              padding: '0.25rem 0.6rem',
            }}
          >{s.label}</button>
        ))}
      </div>

      {/* Controls */}
      <div className={styles.panel}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label className={styles.label} style={{ flex: '1 1 240px' }}>
            Entity / Person Name
            <input
              className={styles.input}
              value={entityName}
              onChange={e => setEntityName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && load()}
              placeholder="e.g. Peter Thiel"
            />
          </label>
          <button className={styles.btn} onClick={load} disabled={loading} style={{ marginBottom: 0, alignSelf: 'flex-end' }}>
            {loading ? 'Loading...' : 'Load Timeline'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {CATEGORIES.map(c => (
          <button
            key={c.id}
            onClick={() => setFilterCat(c.id)}
            style={{
              background:  filterCat === c.id ? `${c.color}22` : 'transparent',
              border:      `1px solid ${filterCat === c.id ? c.color : 'var(--line)'}`,
              borderRadius: 7,
              color:       filterCat === c.id ? c.color : 'var(--text-muted)',
              cursor:      'pointer',
              fontSize:    '0.76rem',
              fontWeight:  700,
              padding:     '0.25rem 0.65rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >{c.label}</button>
        ))}
        <input
          placeholder="Search events…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            background: 'rgba(8,13,26,0.9)',
            border:    '1px solid var(--line)',
            borderRadius: 7,
            color:     'var(--text)',
            font:      'inherit',
            fontSize:  '0.8rem',
            padding:   '0.25rem 0.6rem',
            marginLeft: 'auto',
          }}
        />
        <button
          onClick={() => setViewMode(v => v === 'vertical' ? 'cards' : 'vertical')}
          style={{
            background:  'rgba(15,20,40,0.7)',
            border:      '1px solid var(--line)',
            borderRadius: 7,
            color:       'var(--text-muted)',
            cursor:      'pointer',
            fontSize:    '0.78rem',
            fontWeight:  600,
            padding:     '0.25rem 0.65rem',
          }}
        >{viewMode === 'vertical' ? '⊞ Cards' : '↕ Timeline'}</button>
      </div>

      {/* Stats bar */}
      {loaded && (
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {CATEGORIES.filter(c => c.id !== 'all').map(c => {
            const count = events.filter(e => e.category === c.id).length
            if (!count) return null
            return (
              <span key={c.id} style={{ fontSize: '0.75rem', fontWeight: 700, color: c.color }}>
                {c.label}: {count}
              </span>
            )
          })}
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
            Showing {filtered.length} of {events.length} events for <strong>{loaded}</strong>
          </span>
        </div>
      )}

      {/* Timeline */}
      {filtered.length === 0 && !loading && (
        <div className={styles.panel}>
          <p className={styles.empty}>
            No events to display. Try one of the demo seeds above or load any entity.
          </p>
        </div>
      )}

      {viewMode === 'vertical' && filtered.length > 0 && (
        <div className={styles.panel} style={{ padding: '1rem 1.25rem' }}>
          <div className={tStyles.timelineWrap}>
            {filtered.map((ev, i) => (
              <EventCard key={i} ev={ev} isLast={i === filtered.length - 1} />
            ))}
          </div>
        </div>
      )}

      {viewMode === 'cards' && filtered.length > 0 && (
        <div className={tStyles.cardGrid}>
          {filtered.map((ev, i) => {
            const color = CAT_COLOR[ev.category] || '#818cf8'
            return (
              <div key={i} className={tStyles.card} style={{ borderTopColor: color }}>
                <div className={tStyles.cardDate}>{ev.date}</div>
                <span className={tStyles.cardCat} style={{ color, background: `${color}15` }}>
                  {ev.category}
                </span>
                <p className={tStyles.cardText}>{ev.text}</p>
                <span className={tStyles.cardSrc}>{ev.source}</span>
              </div>
            )
          })}
        </div>
      )}
    </main>
  )
}
