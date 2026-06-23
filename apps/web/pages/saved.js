import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

const API = getApiBaseUrl()
const fetcher = url => fetch(url).then(r => r.json()).catch(() => ({ reports:[] }))

export default function SavedReports() {
  const [search, setSearch] = useState('')
  const { data } = useSWR(`${API}/intelligence/?limit=100`, fetcher, { refreshInterval: 60000 })
  const reports = (data?.reports || data || []).filter(r =>
    !search || (r.entity_name||'').toLowerCase().includes(search.toLowerCase())
  )
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Saved Reports</h1>
        <p style={{ color:'var(--text-muted)', margin:'0.3rem 0 0' }}>All generated intelligence reports. Click to view.</p>
      </section>
      <div style={{ marginBottom:'1rem' }}>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by entity name…"
          style={{ background:'rgba(8,13,26,0.9)', border:'1px solid var(--line)', borderRadius:8, color:'#e2e8f0', fontSize:'0.85rem', padding:'0.5rem 0.75rem', width:'100%', maxWidth:400 }} />
      </div>
      {reports.length === 0 ? (
        <div className={styles.panel} style={{ textAlign:'center', padding:'3rem' }}>
          <p style={{ color:'var(--text-muted)' }}>No reports yet. <Link href="/intelligence">Generate your first report →</Link></p>
        </div>
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:'0.5rem' }}>
          {reports.map((r, i) => (
            <Link key={i} href={`/intelligence/${r.id}`} passHref>
              <a style={{ textDecoration:'none' }}>
                <div style={{ background:'rgba(8,13,26,0.85)', border:'1px solid var(--line)', borderRadius:10, padding:'0.75rem 1rem', display:'flex', justifyContent:'space-between', alignItems:'center', cursor:'pointer', transition:'border-color 0.12s' }}
                  onMouseOver={e => e.currentTarget.style.borderColor='#818cf8'}
                  onMouseOut={e => e.currentTarget.style.borderColor='var(--line)'}>
                  <div>
                    <div style={{ fontWeight:700, color:'#c7d2fe', fontSize:'0.95rem' }}>{r.entity_name || `Report #${r.id}`}</div>
                    <div style={{ fontSize:'0.75rem', color:'var(--text-muted)', marginTop:'0.15rem' }}>
                      {r.entity_type && <span style={{ marginRight:'0.5rem' }}>{r.entity_type}</span>}
                      {r.ticker && <span style={{ marginRight:'0.5rem', color:'#fbbf24' }}>{r.ticker}</span>}
                      {r.created_at?.slice(0,10)}
                    </div>
                  </div>
                  <div style={{ display:'flex', gap:'0.5rem', alignItems:'center' }}>
                    {r.id && (
                      <>
                        <a href={`${API}/intelligence/${r.id}/pdf`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} style={{ fontSize:'0.72rem', color:'#818cf8', padding:'0.2rem 0.5rem', border:'1px solid var(--line)', borderRadius:5 }}>PDF</a>
                        <a href={`${API}/intelligence/${r.id}/word`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} style={{ fontSize:'0.72rem', color:'#818cf8', padding:'0.2rem 0.5rem', border:'1px solid var(--line)', borderRadius:5 }}>Word</a>
                        <a href={`${API}/intelligence/${r.id}/excel`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} style={{ fontSize:'0.72rem', color:'#818cf8', padding:'0.2rem 0.5rem', border:'1px solid var(--line)', borderRadius:5 }}>Excel</a>
                      </>
                    )}
                    <span style={{ color:'var(--text-muted)', fontSize:'0.8rem' }}>→</span>
                  </div>
                </div>
              </a>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}
