import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { getApiBaseUrl } from '../lib/api'

const API = getApiBaseUrl()
const fetcher = url => fetch(url).then(r => r.json()).catch(() => ({ reports: [] }))

export default function SavedReports() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = useSWR(`${API}/intelligence/?limit=100`, fetcher, { refreshInterval: 60000 })
  const raw = (data?.reports || data || [])
  const reports = raw
    .map(r => ({
      ...r,
      id: r.report_id ?? r.id,
      entity_name: r.entity_name || (r.title?.split(': ').slice(1).join(': ')) || r.title || `Report #${r.report_id ?? r.id}`,
    }))
    .filter(r => !search || r.entity_name.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="page-wrap">
      <div className="page-header">
        <div>
          <h1 className="page-title">Saved Reports</h1>
          <p className="page-sub">All generated intelligence dossiers — click to view, download PDF/Word/Excel</p>
        </div>
        <Link href="/intelligence">
          <a className="btn btn-primary">+ New Report</a>
        </Link>
      </div>

      <input
        className="inp"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search by entity name…"
        style={{ maxWidth: 400 }}
      />

      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 64, borderRadius: 12 }} />)}
        </div>
      )}

      {!isLoading && reports.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⬡</div>
          <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.75rem' }}>No reports yet</div>
          <Link href="/intelligence">
            <a className="btn btn-primary">Generate your first report →</a>
          </Link>
        </div>
      )}

      {!isLoading && reports.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {reports.map((r, i) => (
            <Link key={i} href={`/intelligence/${r.id}`} passHref>
              <a style={{ textDecoration: 'none' }}>
                <div className="card card-hover" style={{
                  padding: '0.85rem 1.1rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: 'pointer',
                  gap: '1rem',
                }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, color: '#c7d2fe', fontSize: '0.9rem', marginBottom: 3 }}>
                      {r.entity_name || `Report #${r.id}`}
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                      {r.entity_type && <span className="badge badge-gray">{r.entity_type}</span>}
                      {r.ticker && <span className="badge badge-amber">{r.ticker}</span>}
                      {r.created_at && <span style={{ fontSize: '0.68rem', color: 'var(--text-soft)' }}>{r.created_at.slice(0, 10)}</span>}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
                    {r.id && (
                      <>
                        {[['PDF', 'pdf'], ['Word', 'word'], ['Excel', 'excel']].map(([label, ext]) => (
                          <a
                            key={ext}
                            href={`${API}/intelligence/${r.id}/${ext}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={e => e.stopPropagation()}
                            className="btn btn-ghost btn-xs"
                          >{label}</a>
                        ))}
                      </>
                    )}
                    <span style={{ color: 'var(--text-soft)', fontSize: '0.8rem' }}>→</span>
                  </div>
                </div>
              </a>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
