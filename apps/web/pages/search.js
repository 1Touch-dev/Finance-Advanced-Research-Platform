import { useState } from 'react'
import Link from 'next/link'
import { getApiBaseUrl } from '../lib/api'

const QUICK_TERMS = ['apple', 'palantir', 'spacex', 'microsoft', 'defense', 'blackrock', 'tesla']

export default function SearchPage() {
  const [q, setQ] = useState('')
  const [res, setRes] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const API = getApiBaseUrl()

  const run = async (query) => {
    const term = query ?? q
    if (!term.trim()) return
    setErr(''); setLoading(true); setRes(null)
    try {
      const r = await fetch(`${API}/search/?q=${encodeURIComponent(term)}`)
      if (!r.ok) throw new Error(`API returned ${r.status}`)
      setRes(await r.json())
    } catch (e) {
      setErr(`Request failed: ${e.message}`)
    }
    setLoading(false)
  }

  const entities      = res?.entities      || []
  const documents     = res?.documents     || []
  const relationships = res?.relationships || []

  return (
    <div className="page-wrap">
      <div className="page-header">
        <div>
          <h1 className="page-title">Global Search</h1>
          <p className="page-sub">Query entities, relationships, and evidence-linked records</p>
        </div>
      </div>

      {/* Search bar */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: '0.75rem' }}>
          <input
            className="inp"
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="Search entities, documents, tickers…"
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={() => run()} disabled={loading}>
            {loading ? '…' : 'Search'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.68rem', color: 'var(--text-soft)' }}>Quick:</span>
          {QUICK_TERMS.map(t => (
            <button
              key={t}
              className="btn btn-ghost btn-xs"
              onClick={() => { setQ(t); run(t) }}
            >{t}</button>
          ))}
        </div>
      </div>

      {err && <div className="badge badge-red" style={{ padding: '8px 14px', borderRadius: 10 }}>{err}</div>}

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 56, borderRadius: 12 }} />)}
        </div>
      )}

      {res && !loading && (
        <>
          {/* Entities */}
          {entities.length > 0 && (
            <div className="card" style={{ padding: '1rem 1.25rem' }}>
              <div className="section-title">Entities ({entities.length})</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {entities.map(e => (
                  <Link key={e.id} href={`/entities/${e.id}`} passHref>
                    <a className="card card-hover" style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '8px 12px', textDecoration: 'none',
                    }}>
                      <span className="badge badge-brand">{e.kind}</span>
                      <span style={{ fontWeight: 600, color: '#e2e8f0', fontSize: '0.85rem' }}>{e.name}</span>
                      {e.ticker && <span className="badge badge-amber">{e.ticker}</span>}
                      <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--text-soft)' }}>View →</span>
                    </a>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Relationships */}
          {relationships.length > 0 && (
            <div className="card" style={{ padding: '1rem 1.25rem' }}>
              <div className="section-title">Relationships ({relationships.length})</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {relationships.slice(0, 10).map(r => (
                  <div key={r.id} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)',
                    borderRadius: 8, padding: '7px 12px', fontSize: '0.8rem',
                  }}>
                    <span className="badge badge-green">{r.kind?.replace(/_/g, ' ')}</span>
                    <span style={{ color: 'var(--text-muted)' }}>ID {r.src} → ID {r.dst}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Documents */}
          {documents.length > 0 && (
            <div className="card" style={{ padding: '1rem 1.25rem' }}>
              <div className="section-title">Documents ({documents.length})</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {documents.slice(0, 5).map((d, i) => (
                  <div key={i} style={{
                    background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)',
                    borderRadius: 8, padding: '7px 12px', fontSize: '0.8rem', color: 'var(--text-muted)',
                  }}>
                    {d.title || d.source || JSON.stringify(d).slice(0, 80)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {entities.length === 0 && relationships.length === 0 && documents.length === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: '2.5rem' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>⌕</div>
              <div style={{ color: 'var(--text-muted)', fontWeight: 600 }}>No results found for "{q}"</div>
            </div>
          )}
        </>
      )}

      {!res && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem', color: 'var(--text-soft)' }}>⌕</div>
          <div style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Enter a term to search the intelligence database</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-soft)', marginTop: '0.4rem' }}>
            Supports entity names, tickers, keywords, and document terms
          </div>
        </div>
      )}
    </div>
  )
}
