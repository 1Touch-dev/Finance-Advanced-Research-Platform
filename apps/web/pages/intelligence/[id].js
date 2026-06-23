import { useRouter } from 'next/router'
import Link from 'next/link'
import useSWR from 'swr'
import { getApiBaseUrl } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'

const API = getApiBaseUrl()
const fetcher = url => fetch(url).then(r => r.json()).catch(() => null)

const CONF_COLOR = { DOCUMENTED:'#4ade80', REPORTED:'#fbbf24', ANALYTICAL:'#94a3b8' }

export default function ReportPage() {
  const router = useRouter()
  const { id } = router.query
  const { data: report, error } = useSWR(id ? `${API}/intelligence/${id}` : null, fetcher)

  if (!router.isReady) return <main className={styles.page}><section className={styles.hero}><p>Loading…</p></section></main>
  if (error || (report && report.detail)) return <main className={styles.page}><section className={styles.hero}><h1>Report Not Found</h1><p><Link href="/saved">← Saved Reports</Link></p></section></main>
  if (!report) return <main className={styles.page}><section className={styles.hero}><p>Loading report {id}…</p></section></main>

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'1rem' }}>
          <div>
            <div style={{ fontSize:'0.72rem', color:'var(--text-muted)', marginBottom:'0.25rem' }}>
              <Link href="/saved">← Saved Reports</Link>
            </div>
            <h1 style={{ margin:0 }}>{report.entity_name || `Report #${id}`}</h1>
            <p style={{ margin:'0.3rem 0 0', color:'var(--text-muted)' }}>
              {report.entity_type} {report.ticker && <span style={{ color:'#fbbf24' }}>({report.ticker})</span>} · Generated {report.created_at?.slice(0,10)}
            </p>
          </div>
          <div style={{ display:'flex', gap:'0.5rem', flexWrap:'wrap' }}>
            <a href={`${API}/intelligence/${id}/pdf`} target="_blank" rel="noopener noreferrer" style={{ background:'rgba(129,140,248,0.15)', border:'1px solid #818cf8', borderRadius:8, color:'#c7d2fe', fontSize:'0.82rem', fontWeight:700, padding:'0.4rem 1rem', textDecoration:'none' }}>⬇ PDF</a>
            <a href={`${API}/intelligence/${id}/word`} target="_blank" rel="noopener noreferrer" style={{ background:'rgba(129,140,248,0.1)', border:'1px solid var(--line)', borderRadius:8, color:'#c7d2fe', fontSize:'0.82rem', padding:'0.4rem 1rem', textDecoration:'none' }}>Word</a>
            <a href={`${API}/intelligence/${id}/excel`} target="_blank" rel="noopener noreferrer" style={{ background:'rgba(129,140,248,0.1)', border:'1px solid var(--line)', borderRadius:8, color:'#c7d2fe', fontSize:'0.82rem', padding:'0.4rem 1rem', textDecoration:'none' }}>Excel</a>
            <a href={`${API}/intelligence/${id}/powerpoint`} target="_blank" rel="noopener noreferrer" style={{ background:'rgba(129,140,248,0.1)', border:'1px solid var(--line)', borderRadius:8, color:'#c7d2fe', fontSize:'0.82rem', padding:'0.4rem 1rem', textDecoration:'none' }}>PPT</a>
            <Link href={`/intelligence?entity=${encodeURIComponent(report.entity_name||'')}`} passHref>
              <a style={{ background:'rgba(74,222,128,0.1)', border:'1px solid rgba(74,222,128,0.4)', borderRadius:8, color:'#4ade80', fontSize:'0.82rem', padding:'0.4rem 1rem', textDecoration:'none' }}>↻ Regenerate</a>
            </Link>
          </div>
        </div>
      </section>

      {/* Sections */}
      {(report.sections || []).map((s, i) => (
        <div key={i} className={styles.panel} style={{ marginBottom:'0.75rem' }}>
          <h2 style={{ margin:'0 0 0.75rem', display:'flex', gap:'0.5rem', alignItems:'center' }}>
            <span style={{ color:'var(--text-muted)', fontSize:'0.82rem', fontWeight:400 }}>§{s.order||i+1}</span>
            {s.title || s.name}
          </h2>
          {s.summary && <p style={{ margin:'0 0 0.75rem', color:'var(--text-soft)', fontSize:'0.88rem', lineHeight:1.6 }}>{s.summary}</p>}
          <ul style={{ margin:0, padding:0, listStyle:'none', display:'flex', flexDirection:'column', gap:'0.35rem' }}>
            {(s.claims||[]).map((c, j) => {
              const txt = typeof c === 'string' ? c : c.text || ''
              const conf = typeof c === 'object' ? c.confidence : (txt.match(/^\[(DOCUMENTED|REPORTED|ANALYTICAL)\]/)||[])[1]
              const color = CONF_COLOR[conf] || '#94a3b8'
              return (
                <li key={j} style={{ display:'flex', gap:'0.5rem', alignItems:'flex-start', padding:'0.35rem 0.5rem', borderBottom:'1px solid rgba(255,255,255,0.04)', fontSize:'0.85rem', lineHeight:1.6 }}>
                  {conf && <span style={{ background:`${color}22`, border:`1px solid ${color}44`, borderRadius:4, color, fontSize:'0.65rem', fontWeight:800, padding:'1px 5px', whiteSpace:'nowrap', marginTop:'0.15rem' }}>{conf}</span>}
                  <span style={{ color:'var(--text)' }}>{conf ? txt.replace(/^\[(?:DOCUMENTED|REPORTED|ANALYTICAL)\]\s*/,'') : txt}</span>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </main>
  )
}
