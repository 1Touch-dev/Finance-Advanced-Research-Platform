import { useState } from 'react'
import Link from 'next/link'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

export default function SearchPage(){
  const [q,setQ]=useState('');
  const [res,setRes]=useState(null);
  const [err,setErr]=useState('');
  const API=getApiBaseUrl();

  const run=async(query)=>{
    const term = query ?? q
    setErr('');
    try {
      const r=await fetch(`${API}/search/?q=${encodeURIComponent(term)}`);
      if (!r.ok) throw new Error(`API returned ${r.status}`);
      setRes(await r.json());
    } catch (e) {
      setRes(null);
      setErr(`Request failed: ${e.message}`);
    }
  }

  const handleKey = e => { if (e.key === 'Enter') run() }

  const entities = res?.entities || []
  const documents = res?.documents || []
  const relationships = res?.relationships || []

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Global Search</h1>
        <p>Query entities, relationship signals, and evidence-linked records in one place.</p>
      </section>

      {/* Search Bar */}
      <section className={styles.panel} style={{ display:'flex', gap:'0.75rem', alignItems:'center', flexWrap:'wrap' }}>
        <input className={styles.input}
          value={q} onChange={e=>setQ(e.target.value)} onKeyDown={handleKey}
          placeholder="Search entities, documents…"
          style={{ flex:1, minWidth:200 }} />
        <button className={styles.button} onClick={()=>run()}>Run Search</button>
        {err && <p className={styles.dangerText} style={{ width:'100%', margin:0 }}>{err}</p>}
        <p className={styles.subtle} style={{ width:'100%', margin:0 }}>
          Quick: {['apple','palantir','spacex','microsoft','defense'].map(t=>(
            <button key={t} onClick={()=>{ setQ(t); run(t) }}
              style={{ background:'rgba(129,140,248,0.12)', border:'1px solid rgba(129,140,248,0.25)', borderRadius:6,
                color:'#818cf8', padding:'2px 8px', fontSize:'0.75rem', cursor:'pointer', marginRight:4 }}>{t}</button>
          ))}
        </p>
      </section>

      {res && (
        <>
          {/* Entities */}
          {entities.length > 0 && (
            <section className={styles.panel}>
              <h2 style={{ marginBottom:'0.75rem' }}>Entities ({entities.length})</h2>
              <div style={{ display:'flex', flexDirection:'column', gap:'0.4rem' }}>
                {entities.map(e => (
                  <Link key={e.id} href={`/entities/${e.id}`} passHref>
                    <a style={{ textDecoration:'none', display:'flex', alignItems:'center', gap:'0.75rem',
                      background:'rgba(255,255,255,0.03)', border:'1px solid var(--line)', borderRadius:8,
                      padding:'0.6rem 0.9rem', transition:'border-color 0.15s' }}
                      onMouseOver={ev=>ev.currentTarget.style.borderColor='#818cf8'}
                      onMouseOut={ev=>ev.currentTarget.style.borderColor='var(--line)'}>
                      <span style={{ background:'rgba(129,140,248,0.15)', color:'#818cf8', borderRadius:6,
                        padding:'2px 7px', fontSize:'0.68rem', fontWeight:700, textTransform:'uppercase' }}>{e.kind}</span>
                      <span style={{ fontWeight:600, color:'#e2e8f0' }}>{e.name}</span>
                      {e.ticker && <span style={{ color:'#fbbf24', fontSize:'0.8rem', fontWeight:600 }}>{e.ticker}</span>}
                      <span style={{ marginLeft:'auto', fontSize:'0.72rem', color:'#818cf8' }}>View →</span>
                    </a>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Relationships */}
          {relationships.length > 0 && (
            <section className={styles.panel}>
              <h2 style={{ marginBottom:'0.75rem' }}>Relationships ({relationships.length})</h2>
              <div style={{ display:'flex', flexDirection:'column', gap:'0.4rem' }}>
                {relationships.slice(0,10).map(r => (
                  <div key={r.id} style={{ display:'flex', alignItems:'center', gap:'0.5rem',
                    background:'rgba(255,255,255,0.02)', border:'1px solid var(--line)', borderRadius:8,
                    padding:'0.5rem 0.9rem', fontSize:'0.82rem' }}>
                    <span style={{ background:'rgba(74,222,128,0.12)', color:'#4ade80', borderRadius:5,
                      padding:'2px 7px', fontSize:'0.68rem', fontWeight:700 }}>{r.kind?.replace(/_/g,' ')}</span>
                    <span style={{ color:'#94a3b8' }}>ID {r.src} → ID {r.dst}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Documents */}
          {documents.length > 0 && (
            <section className={styles.panel}>
              <h2 style={{ marginBottom:'0.75rem' }}>Documents ({documents.length})</h2>
              <div style={{ display:'flex', flexDirection:'column', gap:'0.4rem' }}>
                {documents.slice(0,5).map((d,i) => (
                  <div key={i} style={{ background:'rgba(255,255,255,0.02)', border:'1px solid var(--line)',
                    borderRadius:8, padding:'0.5rem 0.9rem', fontSize:'0.82rem', color:'#94a3b8' }}>
                    {d.title || d.source || JSON.stringify(d).slice(0,80)}
                  </div>
                ))}
              </div>
            </section>
          )}

          {entities.length === 0 && relationships.length === 0 && documents.length === 0 && (
            <div className={styles.panel} style={{ textAlign:'center', padding:'2.5rem' }}>
              <p style={{ color:'var(--text-muted)' }}>No results found for "{q}".</p>
            </div>
          )}
        </>
      )}
    </main>
  )
}
