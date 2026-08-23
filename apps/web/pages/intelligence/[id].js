import Link from 'next/link'
import { useRouter } from 'next/router'
import useSWR from 'swr'
import { getApiBaseUrl, authHeaders } from '../../lib/api'

const API = getApiBaseUrl()
const fetcher = (url) => fetch(url, { headers: authHeaders() }).then((response) => response.json()).catch(() => null)

const CONFIDENCE_COLOR = {
  DOCUMENTED: '#4ade80',
  REPORTED: '#fbbf24',
  ANALYTICAL: '#94a3b8',
}

const GROUNDED_SECTION_NAMES = [
  'Grounded Founder & Executive Network',
  'Grounded Co-Investment Network',
  'Correlation & Event Studies',
  'Deep Comparative Analysis',
]

function exportLinkStyle() {
  return {
    background: 'rgba(129,140,248,0.1)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: '#c7d2fe',
    fontSize: '0.82rem',
    padding: '0.4rem 1rem',
    textDecoration: 'none',
  }
}

export default function ReportPage() {
  const router = useRouter()
  const { id } = router.query
  const { data: report, error } = useSWR(id ? `${API}/intelligence/${id}` : null, fetcher)

  if (!router.isReady) {
    return <main className="page-wrap"><section className="card"><p>Loading...</p></section></main>
  }

  if (error || (report && report.detail)) {
    return (
      <main className="page-wrap">
        <section className="card">
          <h1>Report Not Found</h1>
          <p><Link href="/saved">Back to saved reports</Link></p>
        </section>
      </main>
    )
  }

  if (!report) {
    return <main className="page-wrap"><section className="card"><p>Loading report {id}...</p></section></main>
  }

  const groundedSections = (report.sections || []).filter((section) => GROUNDED_SECTION_NAMES.includes(section?.name || section?.title))

  return (
    <main className="page-wrap">
      <section className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
              <Link href="/saved">Back to saved reports</Link>
            </div>
            <h1 style={{ margin: 0 }}>{report.entity_name || `Report #${id}`}</h1>
            <p style={{ margin: '0.3rem 0 0', color: 'var(--text-muted)' }}>
              {report.entity_type || 'org'} {report.ticker ? <span style={{ color: '#fbbf24' }}>({report.ticker})</span> : null} {' '}Generated {report.created_at?.slice(0, 10) || '-'}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <a href={`${API}/intelligence/${id}/pdf-premium`} target="_blank" rel="noopener noreferrer" title="Premium Intelligence Report" style={{ background: 'linear-gradient(135deg,#c9a227,#b8860b)', border: '1px solid #d4a843', borderRadius: 8, color: '#1a1a2e', fontSize: '0.82rem', fontWeight: 800, padding: '0.4rem 1.2rem', textDecoration: 'none', boxShadow: '0 2px 8px rgba(201,162,39,0.3)' }}>Premium Report</a>
            <a href={`${API}/intelligence/${id}/pdf-beautiful`} target="_blank" rel="noopener noreferrer" title="Beautifully styled PDF" style={{ background: 'linear-gradient(135deg,#6366f1,#4f46e5)', border: '1px solid #818cf8', borderRadius: 8, color: '#fff', fontSize: '0.82rem', fontWeight: 700, padding: '0.4rem 1rem', textDecoration: 'none' }}>Beautiful PDF</a>
            <a href={`${API}/intelligence/${id}/pdf-professional`} target="_blank" rel="noopener noreferrer" title="Professional PDF with charts" style={{ background: 'rgba(129,140,248,0.15)', border: '1px solid #818cf8', borderRadius: 8, color: '#c7d2fe', fontSize: '0.82rem', fontWeight: 700, padding: '0.4rem 1rem', textDecoration: 'none' }}>Pro PDF</a>
            <a href={`${API}/intelligence/${id}/pdf`} target="_blank" rel="noopener noreferrer" style={exportLinkStyle()}>PDF</a>
            <a href={`${API}/intelligence/${id}/word`} target="_blank" rel="noopener noreferrer" style={exportLinkStyle()}>Word</a>
            <a href={`${API}/intelligence/${id}/excel-detailed`} target="_blank" rel="noopener noreferrer" style={exportLinkStyle()}>Excel</a>
            <a href={`${API}/intelligence/${id}/powerpoint-detailed`} target="_blank" rel="noopener noreferrer" style={exportLinkStyle()}>PPT</a>
            <a href={`${API}/intelligence/${id}/markdown`} target="_blank" rel="noopener noreferrer" style={exportLinkStyle()}>MD</a>
            {report.interactive_report?.supported === true ? (
              <Link href={`/intelligence/interactive/${id}`} style={{ background: 'rgba(110,168,254,0.12)', border: '1px solid rgba(110,168,254,0.4)', borderRadius: 8, color: '#dbeafe', fontSize: '0.82rem', padding: '0.4rem 1rem', textDecoration: 'none' }}>
                Open Interactive
              </Link>
            ) : null}
            <Link href={`/intelligence?entity=${encodeURIComponent(report.entity_name || '')}`} style={{ background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.4)', borderRadius: 8, color: '#4ade80', fontSize: '0.82rem', padding: '0.4rem 1rem', textDecoration: 'none' }}>
              Regenerate
            </Link>
          </div>
        </div>
      </section>

      {(groundedSections.length || report.interactive_report || report.network_analysis || report.correlation_analysis) ? (
        <section className="card">
          <h2 style={{ margin: '0 0 0.75rem' }}>Grounded Intelligence Additions</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
            {groundedSections.map((section, index) => (
              <span key={`${section.name || section.title}-${index}`} style={{ background: 'rgba(129,140,248,0.12)', border: '1px solid rgba(129,140,248,0.28)', borderRadius: 999, color: '#c7d2fe', fontSize: '0.78rem', fontWeight: 700, padding: '0.28rem 0.7rem' }}>
                {section.name || section.title}
              </span>
            ))}
            {report.interactive_report?.supported ? (
              <span style={{ background: 'rgba(74,222,128,0.12)', border: '1px solid rgba(74,222,128,0.28)', borderRadius: 999, color: '#4ade80', fontSize: '0.78rem', fontWeight: 700, padding: '0.28rem 0.7rem' }}>
                Interactive payload available
              </span>
            ) : null}
          </div>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.86rem', lineHeight: 1.6 }}>
            Older reports still render normally. Newly persisted grounded sections and interactive payload support appear here additively when the backend has stored them.
          </p>
        </section>
      ) : null}

      {(report.sections || []).map((section, index) => (
        <div key={`${section.name || section.title || 'section'}-${index}`} className="card" style={{ marginBottom: '0.75rem' }}>
          <h2 style={{ margin: '0 0 0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', fontWeight: 400 }}>Section {section.order || index + 1}</span>
            {section.title || section.name}
          </h2>
          {section.summary ? <p style={{ margin: '0 0 0.75rem', color: 'var(--text-soft)', fontSize: '0.88rem', lineHeight: 1.6 }}>{section.summary}</p> : null}
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {(section.claims || []).map((claim, claimIndex) => {
              const text = typeof claim === 'string' ? claim : claim.text || ''
              const confidence = typeof claim === 'object' ? claim.confidence : (text.match(/^\[(DOCUMENTED|REPORTED|ANALYTICAL)\]/) || [])[1]
              const color = CONFIDENCE_COLOR[confidence] || '#94a3b8'
              return (
                <li key={`${section.name || section.title || 'section'}-${claimIndex}`} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', padding: '0.35rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: '0.85rem', lineHeight: 1.6 }}>
                  {confidence ? (
                    <span style={{ background: `${color}22`, border: `1px solid ${color}44`, borderRadius: 4, color, fontSize: '0.65rem', fontWeight: 800, padding: '1px 5px', whiteSpace: 'nowrap', marginTop: '0.15rem' }}>
                      {confidence}
                    </span>
                  ) : null}
                  <span style={{ color: 'var(--text)' }}>{confidence ? text.replace(/^\[(?:DOCUMENTED|REPORTED|ANALYTICAL)\]\s*/, '') : text}</span>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </main>
  )
}
