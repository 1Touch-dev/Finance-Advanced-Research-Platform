import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { getApiBaseUrl } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'

const API = getApiBaseUrl()
const fetcher = url => fetch(url).then(r => r.json()).catch(() => ({ alerts: [] }))
const SEV_COLOR = { info:'#60a5fa', warn:'#fbbf24', critical:'#f87171', page:'#ef4444' }

export default function AlertsPage() {
  const [severity, setSeverity] = useState('all')
  const [status, setStatus] = useState('all')
  const url = `${API}/tracking/alerts?limit=100${severity!=='all'?`&severity=${severity}`:''}${status!=='all'?`&status=${status}`:''}`
  const { data, mutate } = useSWR(url, fetcher, { refreshInterval: 30000 })
  const alerts = data?.alerts || []
  const ack = async (id) => { await fetch(`${API}/tracking/alerts/${id}/acknowledge`, { method:'POST' }); mutate() }
  const snooze = async (id) => { await fetch(`${API}/tracking/alerts/${id}/snooze?hours=24`, { method:'POST' }); mutate() }
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Alert Inbox</h1>
        <p style={{ color:'var(--text-muted)', margin:'0.3rem 0 0' }}>Triggered alerts from entity monitoring. <Link href="/tracking">Back to Tracking</Link></p>
      </section>
      <div style={{ display:'flex', gap:'0.5rem', flexWrap:'wrap', marginBottom:'1rem' }}>
        {['all','info','warn','critical'].map(s => (
          <button key={s} onClick={() => setSeverity(s)} style={{ background:severity===s?'rgba(129,140,248,0.2)':'rgba(8,13,26,0.7)', border:'1px solid '+(severity===s?'#818cf8':'var(--line)'), borderRadius:8, color:severity===s?'#c7d2fe':'var(--text-muted)', cursor:'pointer', fontSize:'0.78rem', fontWeight:600, padding:'0.3rem 0.8rem' }}>{s}</button>
        ))}
        <span style={{ borderLeft:'1px solid var(--line)', margin:'0 0.25rem' }} />
        {['all','new','acknowledged','snoozed','resolved'].map(s => (
          <button key={s} onClick={() => setStatus(s)} style={{ background:status===s?'rgba(74,222,128,0.1)':'rgba(8,13,26,0.7)', border:'1px solid '+(status===s?'#4ade80':'var(--line)'), borderRadius:8, color:status===s?'#4ade80':'var(--text-muted)', cursor:'pointer', fontSize:'0.78rem', fontWeight:600, padding:'0.3rem 0.8rem' }}>{s}</button>
        ))}
      </div>
      {alerts.length === 0 ? (
        <div className={styles.panel} style={{ textAlign:'center', padding:'3rem' }}>
          <div style={{ fontSize:'2.5rem' }}>✅</div>
          <h2 style={{ color:'#4ade80' }}>No alerts</h2>
          <p style={{ color:'var(--text-muted)' }}>All clear. Add entities to <Link href="/tracking">tracking</Link> to monitor.</p>
        </div>
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:'0.5rem' }}>
          {alerts.map((a, i) => {
            const c = SEV_COLOR[a.severity||'info'] || '#94a3b8'
            return (
              <div key={i} style={{ background:'rgba(8,13,26,0.85)', border:`1px solid ${c}44`, borderLeft:`3px solid ${c}`, borderRadius:10, padding:'0.75rem 1rem', display:'flex', gap:'1rem', alignItems:'flex-start' }}>
                <div style={{ flex:1 }}>
                  <div style={{ display:'flex', gap:'0.5rem', alignItems:'center', marginBottom:'0.25rem' }}>
                    <span style={{ background:`${c}22`, border:`1px solid ${c}44`, borderRadius:4, color:c, fontSize:'0.65rem', fontWeight:800, padding:'1px 6px', textTransform:'uppercase' }}>{a.severity||'info'}</span>
                    <span style={{ fontWeight:700, color:'#c7d2fe' }}>{a.entity_name||'System'}</span>
                    <span style={{ fontSize:'0.72rem', color:'var(--text-muted)' }}>{a.alert_type}</span>
                  </div>
                  <div style={{ fontSize:'0.85rem', color:'var(--text)', lineHeight:1.5 }}>{a.message}</div>
                  <div style={{ fontSize:'0.72rem', color:'var(--text-muted)', marginTop:'0.25rem' }}>{a.created_at?.slice(0,19).replace('T',' ')} · {a.status||'new'}</div>
                </div>
                <div style={{ display:'flex', gap:'0.4rem' }}>
                  <button onClick={() => ack(a.id)} style={{ background:'rgba(74,222,128,0.1)', border:'1px solid rgba(74,222,128,0.3)', borderRadius:6, color:'#4ade80', cursor:'pointer', fontSize:'0.72rem', padding:'0.25rem 0.6rem' }}>Ack</button>
                  <button onClick={() => snooze(a.id)} style={{ background:'rgba(251,191,36,0.08)', border:'1px solid rgba(251,191,36,0.3)', borderRadius:6, color:'#fbbf24', cursor:'pointer', fontSize:'0.72rem', padding:'0.25rem 0.6rem' }}>Snooze</button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </main>
  )
}
