import { useState, useRef, useEffect, useMemo } from 'react'
import useSWR from 'swr'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''
const fetcher = url => fetch(url).then(r => r.json())

const PARTY_COLORS = { D: '#60a5fa', R: '#f87171', I: '#a78bfa' }
const PARTY_NAMES = { D: 'Democrat', R: 'Republican', I: 'Independent' }

const BILL_TYPE_SLUGS = {
  hr: 'house-bill', s: 'senate-bill',
  hres: 'house-resolution', sres: 'senate-resolution',
  hjres: 'house-joint-resolution', sjres: 'senate-joint-resolution',
  hconres: 'house-concurrent-resolution', sconres: 'senate-concurrent-resolution',
}
const congressGovUrl = (bill) => {
  const slug = BILL_TYPE_SLUGS[(bill.type || '').toLowerCase()]
  if (!slug || !bill.congress || !bill.number) return null
  return `https://www.congress.gov/bill/${bill.congress}th-congress/${slug}/${bill.number}`
}

function Modal({ open, onClose, children, maxWidth = 640 }) {
  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (open) {
      setMounted(true)
      const raf1 = requestAnimationFrame(() => {
        const raf2 = requestAnimationFrame(() => setVisible(true))
        return () => cancelAnimationFrame(raf2)
      })
      const onKey = (e) => e.key === 'Escape' && onClose()
      document.addEventListener('keydown', onKey)
      const prevOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      return () => {
        cancelAnimationFrame(raf1)
        document.removeEventListener('keydown', onKey)
        document.body.style.overflow = prevOverflow
      }
    }
    setVisible(false)
    const t = setTimeout(() => setMounted(false), 200)
    return () => clearTimeout(t)
  }, [open])

  if (!mounted) return null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1.5rem', overflowY: 'auto',
        background: visible ? 'rgba(2,6,15,0.72)' : 'rgba(2,6,15,0)',
        backdropFilter: visible ? 'blur(4px)' : 'blur(0px)',
        transition: 'background 0.22s ease, backdrop-filter 0.22s ease',
      }}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%', maxWidth, maxHeight: '85vh', overflowY: 'auto',
          background: '#0b1120', border: '1px solid rgba(129,140,248,0.4)',
          borderRadius: 16, boxShadow: '0 24px 64px rgba(0,0,0,0.6), 0 0 0 1px rgba(129,140,248,0.08)',
          padding: '1.5rem', margin: 'auto',
          opacity: visible ? 1 : 0,
          transform: visible ? 'translateY(0) scale(1)' : 'translateY(16px) scale(0.96)',
          transition: 'opacity 0.22s cubic-bezier(.22,1,.36,1), transform 0.22s cubic-bezier(.22,1,.36,1)',
        }}>
        {children}
      </div>
    </div>
  )
}

function PoliticianDropdown({ politicians, selected, onSelect }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [highlight, setHighlight] = useState(0)
  const rootRef = useRef(null)
  const inputRef = useRef(null)

  const selectedPol = politicians.find(p => p.id === selected)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return politicians
    return politicians.filter(p =>
      p.name?.toLowerCase().includes(q) ||
      p.state?.toLowerCase().includes(q) ||
      p.chamber?.toLowerCase().includes(q) ||
      p.party?.toLowerCase().includes(q)
    )
  }, [politicians, query])

  useEffect(() => {
    function onClickOutside(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  useEffect(() => { if (open) { setHighlight(0); setTimeout(() => inputRef.current?.focus(), 0) } }, [open])

  const choose = (p) => {
    onSelect(p.id)
    setOpen(false)
    setQuery('')
  }

  const onKeyDown = (e) => {
    if (e.key === 'Escape') { setOpen(false); setQuery('') }
    else if (e.key === 'ArrowDown') { e.preventDefault(); setHighlight(h => Math.min(h + 1, filtered.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHighlight(h => Math.max(h - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); if (filtered[highlight]) choose(filtered[highlight]) }
  }

  return (
    <div ref={rootRef} style={{ position: 'relative', flex: 1, minWidth: 260, maxWidth: 380 }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '0.6rem',
          background: 'rgba(255,255,255,0.06)', border: `1px solid ${open ? '#818cf8' : 'var(--line-md)'}`,
          borderRadius: 8, color: '#e2e8f0', padding: '9px 14px', fontSize: '0.85rem',
          cursor: 'pointer', textAlign: 'left', transition: 'border-color 0.15s',
        }}>
        {selectedPol ? (
          <>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: PARTY_COLORS[selectedPol.party] || '#94a3b8', flexShrink: 0 }} />
            <span style={{ fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedPol.name}</span>
            <span style={{ color: '#64748b', fontSize: '0.72rem', flexShrink: 0 }}>{selectedPol.party} · {selectedPol.state?.toUpperCase()} · {selectedPol.chamber}</span>
          </>
        ) : (
          <span style={{ color: '#64748b', flex: 1 }}>🔍 Select a politician to view trading profile…</span>
        )}
        <span style={{ color: '#64748b', fontSize: '0.7rem', flexShrink: 0, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>▼</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 50,
          background: '#0b1120', border: '1px solid #818cf8', borderRadius: 10,
          boxShadow: '0 12px 32px rgba(0,0,0,0.5)', overflow: 'hidden',
        }}>
          <div style={{ padding: '0.5rem', borderBottom: '1px solid var(--line)' }}>
            <input
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Type a name, state, or party…"
              style={{
                width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid var(--line-md)',
                borderRadius: 6, color: '#e2e8f0', padding: '7px 10px', fontSize: '0.82rem', outline: 'none',
              }}
            />
          </div>
          <div role="listbox" style={{ maxHeight: 320, overflowY: 'auto' }}>
            {filtered.length === 0 && (
              <div style={{ padding: '0.9rem', color: '#64748b', fontSize: '0.82rem', textAlign: 'center' }}>No politicians match "{query}"</div>
            )}
            {filtered.map((p, i) => (
              <div
                key={p.id}
                role="option"
                aria-selected={p.id === selected}
                tabIndex={0}
                onClick={() => choose(p)}
                onMouseEnter={() => setHighlight(i)}
                onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && choose(p)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0.55rem 0.9rem', cursor: 'pointer',
                  background: i === highlight ? 'rgba(129,140,248,0.15)' : (p.id === selected ? 'rgba(129,140,248,0.06)' : 'transparent'),
                  borderLeft: p.id === selected ? '3px solid #818cf8' : '3px solid transparent',
                }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: PARTY_COLORS[p.party] || '#94a3b8', flexShrink: 0 }} />
                <span style={{ fontWeight: 600, color: '#e2e8f0', fontSize: '0.85rem', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
                <span style={{
                  fontSize: '0.65rem', fontWeight: 700, color: PARTY_COLORS[p.party] || '#94a3b8',
                  background: `${PARTY_COLORS[p.party] || '#94a3b8'}1a`, borderRadius: 4, padding: '1px 6px', flexShrink: 0,
                }} title={PARTY_NAMES[p.party] || p.party}>{p.party}</span>
                <span style={{ color: '#64748b', fontSize: '0.72rem', flexShrink: 0, minWidth: 70, textAlign: 'right' }}>{p.state?.toUpperCase()} · {p.chamber}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function LegislationSearchTab() {
  const [query, setQuery] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedBill, setSelectedBill] = useState(null)
  const [hoveredIdx, setHoveredIdx] = useState(null)
  const { data: searchData, isLoading } = useSWR(
    searchTerm ? `${API}/market/gov-trading/legislation/search?query=${encodeURIComponent(searchTerm)}&limit=25` : null,
    fetcher
  )
  const { data: billDetail, isLoading: billLoading } = useSWR(
    selectedBill ? `${API}/market/gov-trading/legislation/bill/${selectedBill.congress}/${selectedBill.type}/${selectedBill.number}` : null,
    fetcher
  )

  const isSameBill = (a, b) => a && b && a.congress === b.congress && a.type === b.type && a.number === b.number

  const handleSelectBill = (bill) => setSelectedBill(bill)

  const POPULAR_SEARCHES = ['AI regulation', 'banking', 'crypto', 'defense', 'semiconductor', 'drug pricing', 'energy']

  const statusBadge = (latestAction) => {
    const text = (latestAction || '').toLowerCase()
    if (text.includes('became public law') || text.includes('signed by president')) return { label: 'Law', color: '#4ade80' }
    if (text.includes('passed')) return { label: 'Passed', color: '#818cf8' }
    if (text.includes('committee')) return { label: 'Committee', color: '#fbbf24' }
    return { label: 'Introduced', color: '#94a3b8' }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <section className="card" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="inp" value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && setSearchTerm(query)}
          placeholder="Search bills — e.g. 'AI regulation', 'banking', 'crypto'" style={{ flex: 1, minWidth: 260 }} />
        <button className="btn btn-primary" onClick={() => setSearchTerm(query)}>🔍 Search</button>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {POPULAR_SEARCHES.map(t => (
            <button key={t} onClick={() => { setQuery(t); setSearchTerm(t) }}
              style={{ background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.2)', borderRadius: 5, color: '#818cf8', padding: '2px 8px', fontSize: '0.72rem', cursor: 'pointer' }}>
              {t}
            </button>
          ))}
        </div>
      </section>

      {isLoading && <p style={{ color: '#94a3b8' }}>Searching Congress.gov…</p>}

      {searchData && !isLoading && (
        <section className="card">
          <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>
            Results for "{searchData.query}" ({searchData.bills?.length || 0} bills)
          </h2>
          {(searchData.bills || []).length === 0 && (
            <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No bills found. Try a different search term.</p>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {(searchData.bills || []).map((bill, i) => {
              const badge = statusBadge(bill.latest_action)
              const isSelected = isSameBill(selectedBill, bill)
              const isHovered = hoveredIdx === i
              return (
                <div key={i} onClick={() => handleSelectBill(bill)}
                  onMouseEnter={() => setHoveredIdx(i)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && handleSelectBill(bill)}
                  style={{
                    padding: '0.6rem 0.9rem',
                    border: `1px solid ${isSelected ? '#818cf8' : (isHovered ? 'rgba(129,140,248,0.5)' : 'var(--line)')}`,
                    borderRadius: 8, cursor: 'pointer',
                    background: isSelected ? 'rgba(129,140,248,0.08)' : (isHovered ? 'rgba(255,255,255,0.03)' : 'transparent'),
                    transform: isHovered ? 'translateY(-1px)' : 'none',
                    boxShadow: isHovered ? '0 4px 12px rgba(0,0,0,0.25)' : 'none',
                    transition: 'border-color 0.15s, background 0.15s, transform 0.15s, box-shadow 0.15s',
                  }}>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ background: '#6366f122', color: '#818cf8', borderRadius: 5, padding: '2px 8px', fontSize: '0.65rem', fontWeight: 700 }}>
                      {bill.type?.toUpperCase()} {bill.number}
                    </span>
                    <span style={{ background: `${badge.color}22`, color: badge.color, borderRadius: 5, padding: '2px 8px', fontSize: '0.65rem', fontWeight: 700 }}>
                      {badge.label}
                    </span>
                    <span style={{ color: '#64748b', fontSize: '0.7rem', marginLeft: 'auto' }}>Congress {bill.congress}</span>
                  </div>
                  <div style={{ color: '#e2e8f0', fontSize: '0.85rem', marginTop: '0.35rem', fontWeight: 500 }}>{bill.title}</div>
                  {bill.latest_action && <div style={{ color: '#64748b', fontSize: '0.72rem', marginTop: '0.2rem' }}>{bill.latest_action} {bill.latest_action_date && `· ${bill.latest_action_date}`}</div>}
                  <div style={{ color: isHovered ? '#818cf8' : '#475569', fontSize: '0.68rem', marginTop: '0.3rem', fontWeight: 600 }}>
                    👆 Click to view full details
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Bill detail modal */}
      <Modal open={!!selectedBill} onClose={() => setSelectedBill(null)} maxWidth={620}>
        {billLoading && (
          <div style={{ padding: '2rem 0', textAlign: 'center', color: '#94a3b8', fontSize: '0.9rem' }}>
            ⏳ Loading bill details…
          </div>
        )}
        {!billLoading && billDetail?.error && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setSelectedBill(null)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1.2rem' }}>✕</button>
            </div>
            <p style={{ color: '#f87171', fontSize: '0.85rem' }}>Could not load details for this bill: {billDetail.error}</p>
          </div>
        )}
        {!billLoading && billDetail && !billDetail.error && (() => {
          const badge = statusBadge(billDetail.latest_action)
          const url = congressGovUrl(billDetail)
          return (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.9rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ background: '#6366f122', color: '#818cf8', borderRadius: 5, padding: '3px 9px', fontSize: '0.7rem', fontWeight: 700 }}>
                    {billDetail.type?.toUpperCase()} {billDetail.number}
                  </span>
                  <span style={{ background: `${badge.color}22`, color: badge.color, borderRadius: 5, padding: '3px 9px', fontSize: '0.7rem', fontWeight: 700 }}>
                    {badge.label}
                  </span>
                  <span style={{ color: '#64748b', fontSize: '0.72rem' }}>Congress {billDetail.congress}</span>
                </div>
                <button onClick={() => setSelectedBill(null)}
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--line)', color: '#94a3b8', cursor: 'pointer', fontSize: '1rem', borderRadius: 6, width: 28, height: 28, flexShrink: 0, lineHeight: 1 }}>✕</button>
              </div>

              <h2 style={{ fontSize: '1.15rem', lineHeight: 1.4, marginBottom: '1rem', color: '#f1f5f9' }}>{billDetail.title}</h2>

              <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                {[
                  ['Introduced', billDetail.introduced_date],
                  ['Policy Area', billDetail.policy_area || '—'],
                  ['Cosponsors', billDetail.cosponsors_count],
                  ['Summaries', billDetail.summaries_count],
                ].map(([label, val]) => (
                  <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.5rem 0.9rem', minWidth: 110, flex: '1 1 110px' }}>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#c7d2fe' }}>{val ?? '—'}</div>
                  </div>
                ))}
              </div>

              {billDetail.latest_action && (
                <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.7rem 0.9rem', marginBottom: '0.75rem' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 3 }}>Latest Action</div>
                  <div style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>{billDetail.latest_action} <span style={{ color: '#64748b' }}>({billDetail.latest_action_date})</span></div>
                </div>
              )}

              {billDetail.sponsors?.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: PARTY_COLORS[billDetail.sponsors[0].party] || '#94a3b8' }} />
                  <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                    <strong style={{ color: '#e2e8f0' }}>Sponsor:</strong> {billDetail.sponsors[0].name} ({billDetail.sponsors[0].party}-{billDetail.sponsors[0].state})
                  </span>
                </div>
              )}

              {url && (
                <a href={url} target="_blank" rel="noopener noreferrer"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: '#818cf8', fontSize: '0.8rem', fontWeight: 600, textDecoration: 'none' }}>
                  📄 View full bill on Congress.gov ↗
                </a>
              )}
            </div>
          )
        })()}
      </Modal>
    </div>
  )
}

function CRSReportsPanel() {
  const [expanded, setExpanded] = useState(false)
  const { data } = useSWR(expanded ? `${API}/market/gov-trading/legislation/crs-reports?limit=15` : null, fetcher)

  return (
    <section className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: expanded ? '0.75rem' : 0 }}>
        <h2 style={{ fontSize: '1rem' }}>📄 CRS Policy Research Reports</h2>
        <button onClick={() => setExpanded(!expanded)}
          style={{ padding: '6px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--line)', color: '#94a3b8', borderRadius: 6, cursor: 'pointer', fontSize: '0.75rem' }}>
          {expanded ? '▲ Hide' : '▼ Show reports'}
        </button>
      </div>
      {expanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {(data?.reports || []).map((r, i) => (
            <div key={r.id || i} style={{ padding: '0.5rem 0.8rem', border: '1px solid var(--line)', borderRadius: 8 }}>
              <div style={{ color: '#e2e8f0', fontSize: '0.82rem', fontWeight: 600 }}>{r.title}</div>
              <div style={{ color: '#64748b', fontSize: '0.7rem', marginTop: 2 }}>{r.type} · {r.status} · {r.publish_date}</div>
            </div>
          ))}
          {data && (data.reports || []).length === 0 && <p style={{ color: '#64748b', fontSize: '0.8rem' }}>No reports available.</p>}
          {!data && <p style={{ color: '#64748b', fontSize: '0.8rem' }}>Loading…</p>}
        </div>
      )}
    </section>
  )
}

function PoliticianTab() {
  const [selected, setSelected] = useState('')
  const [profileData, setProfileData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [summaryExpanded, setSummaryExpanded] = useState(false)
  const [votesExpanded, setVotesExpanded] = useState(false)
  const { data: listData } = useSWR(`${API}/market/gov-trading/politicians/list`, fetcher)
  const { data: summaryData } = useSWR(summaryExpanded ? `${API}/market/gov-trading/politicians/summary` : null, fetcher)
  const { data: votesData, isLoading: votesLoading } = useSWR(
    votesExpanded && selected ? `${API}/market/gov-trading/politician/${selected}/votes` : null,
    fetcher
  )

  const loadProfile = async (id) => {
    if (!id) return
    setSelected(id)
    setLoading(true)
    setProfileData(null)
    setVotesExpanded(false)
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
        <PoliticianDropdown politicians={politicians} selected={selected} onSelect={loadProfile} />
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
                  <td style={{ padding: '7px 12px', color: '#64748b', fontSize: '0.75rem' }}>
                    {p.data_note ? (
                      <span title={p.data_note} style={{ color: '#34d399', cursor: 'help', fontSize: '0.7rem' }}>Senate eFD data</span>
                    ) : (p.latest_filing || '—')}
                  </td>
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

          {/* Vote / Legislative Activity Record */}
          <div style={{ marginTop: '1rem' }}>
            <button onClick={() => setVotesExpanded(!votesExpanded)}
              style={{ padding: '6px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--line)', color: '#94a3b8', borderRadius: 6, cursor: 'pointer', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
              {votesExpanded ? '▲ Hide Voting/Sponsorship Record' : '▼ Show Full Voting/Sponsorship Record'}
            </button>
            {votesExpanded && (
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: 10, padding: '0.75rem' }}>
                {votesLoading && <p style={{ color: '#94a3b8', fontSize: '0.82rem' }}>Loading legislative record…</p>}
                {votesData?.error && <p style={{ color: '#f87171', fontSize: '0.82rem' }}>{votesData.error}</p>}
                {votesData?.votes?.length === 0 && !votesLoading && (
                  <p style={{ color: '#64748b', fontSize: '0.82rem' }}>{votesData.note || 'No legislative record found.'}</p>
                )}
                {(votesData?.votes || []).map((v, i) => (
                  <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)', flexWrap: 'wrap' }}>
                    <span style={{ background: v.role === 'sponsor' ? '#4ade8022' : '#818cf822', color: v.role === 'sponsor' ? '#4ade80' : '#818cf8',
                      borderRadius: 5, padding: '1px 7px', fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase' }}>
                      {v.role}
                    </span>
                    <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>{v.type?.toUpperCase()} {v.number}</span>
                    <span style={{ color: '#e2e8f0', fontSize: '0.8rem' }}>{v.title}</span>
                    <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: '0.7rem' }}>{v.introduced}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

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
      <section className="card">
        <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Congressional STOCK Act Disclosures ({days}d)</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
          {[
            ['PTR Filings', data.total_ptr_disclosures],
            ['House PTR', data.house_ptr_filers],
            ['Senate PTR', data.senate_ptr_filers],
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
        <section className="card">
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

        <section className="card">
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
      <section className="card">
        <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Recent PTR Filers (House + Senate)</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.5rem' }}>
          {recent.map((m, i) => (
            <div key={i} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.6rem 0.9rem' }}>
              <div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: '0.85rem' }}>{m.name || (m.first && m.last ? `${m.first} ${m.last}` : '—')}</div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: 2 }}>
                {m.chamber ? <span style={{ textTransform: 'capitalize', color: m.chamber === 'senate' ? '#818cf8' : '#64748b' }}>{m.chamber}</span> : null}
                {m.state_dst ? ` ${m.state_dst}` : ''} • Filed {m.filing_date}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* SEC Form 4 Insider Trades */}
      {form4.length > 0 && (
        <section className="card">
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
      <section className="card" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="inp" value={query} onChange={e => setQuery(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && setTicker(query)}
          placeholder="Ticker e.g. AAPL" style={{ maxWidth: 140, fontWeight: 700 }} />
        <button className="btn btn-primary" onClick={() => setTicker(query)}>Look Up</button>
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
        <section className="card">
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
    { id: 'legislation', label: '📜 Legislation Search' },
  ]

  return (
    <main className="page-wrap">
      <div className="card">
        <h1 >Government & Insider Trading</h1>
        <p >Congressional STOCK Act disclosures, corporate insider trades via SEC Form 4, and government financial intelligence.</p>
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
            <option value={3650}>Historical (10 yr)</option>
          </select>
        )}
      </div>

      {tab === 'summary' && <SummaryTab days={days} setDays={setDays} />}
      {tab === 'insider' && <InsiderTab />}
      {tab === 'politicians' && <PoliticianTab />}
      {tab === 'legislation' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <LegislationSearchTab />
          <CRSReportsPanel />
        </div>
      )}
    </main>
  )
}
