import Link from 'next/link'
import { useState } from 'react'
import useSWR from 'swr'
import { getApiBaseUrl, apiFetch } from '../lib/api'

const API = getApiBaseUrl()
const fetcher = (url) => apiFetch(url).then((response) => response.json()).catch(() => ({ reports: [] }))

export default function SavedReports() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = useSWR(`${API}/intelligence/?limit=100`, fetcher, { refreshInterval: 60000 })
  const raw = (data?.reports || data || [])
  const reports = raw
    .map((report) => ({
      ...report,
      id: report.report_id ?? report.id,
      interactiveSupported: report.interactive_report?.supported === true || report.has_interactive_report_payload === true,
      entity_name: report.entity_name || (report.title?.split(': ').slice(1).join(': ')) || report.title || `Report #${report.report_id ?? report.id}`,
    }))
    .filter((report) => !search || report.entity_name.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="page-wrap">
      <div className="page-header">
        <div>
          <h1 className="page-title">Saved Reports</h1>
          <p className="page-sub">All generated intelligence dossiers. Open the base report, downloads, or the interactive viewer when available.</p>
        </div>
        <Link href="/intelligence" className="btn btn-primary">+ New Report</Link>
      </div>

      <input
        className="inp"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search by entity name..."
        style={{ maxWidth: 400 }}
      />

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {[1, 2, 3, 4].map((index) => <div key={index} className="skeleton" style={{ height: 64, borderRadius: 12 }} />)}
        </div>
      ) : null}

      {!isLoading && reports.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>[]</div>
          <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.75rem' }}>No reports yet</div>
          <Link href="/intelligence" className="btn btn-primary">Generate your first report</Link>
        </div>
      ) : null}

      {!isLoading && reports.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {reports.map((report, index) => (
            <Link key={`${report.id}-${index}`} href={`/intelligence/${report.id}`} style={{ textDecoration: 'none' }}>
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
                    {report.entity_name || `Report #${report.id}`}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                    {report.entity_type ? <span className="badge badge-gray">{report.entity_type}</span> : null}
                    {report.ticker ? <span className="badge badge-amber">{report.ticker}</span> : null}
                    {report.created_at ? <span style={{ fontSize: '0.68rem', color: 'var(--text-soft)' }}>{report.created_at.slice(0, 10)}</span> : null}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
                  {report.id ? (
                    <>
                      <a
                        href={`${API}/intelligence/${report.id}/pdf-beautiful`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(event) => event.stopPropagation()}
                        title="Beautiful PDF"
                        className="btn btn-primary btn-xs"
                      >PDF</a>
                      {report.interactiveSupported ? (
                        <Link
                          href={`/intelligence/interactive/${report.id}`}
                          onClick={(event) => event.stopPropagation()}
                          className="btn btn-ghost btn-xs"
                        >Interactive</Link>
                      ) : null}
                      {[['Word', 'word'], ['Excel', 'excel-detailed'], ['MD', 'markdown']].map(([label, ext]) => (
                        <a
                          key={ext}
                          href={`${API}/intelligence/${report.id}/${ext}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(event) => event.stopPropagation()}
                          className="btn btn-ghost btn-xs"
                        >{label}</a>
                      ))}
                    </>
                  ) : null}
                  <span style={{ color: 'var(--text-soft)', fontSize: '0.8rem' }}>&gt;</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  )
}
