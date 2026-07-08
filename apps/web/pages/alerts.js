import { useEffect, useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

export default function AlertsPage() {
  const API = getApiBaseUrl()
  const [events, setEvents] = useState([])
  const [err, setErr] = useState('')
  const [notice, setNotice] = useState('')

  const load = async () => {
    setErr('')
    try {
      const r = await fetch(`${API}/monitor/events?limit=50`)
      if (!r.ok) throw new Error(`API ${r.status}`)
      setEvents(await r.json())
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => {
    let cancelled = false
    const attemptLoad = async (retries = 2) => {
      setErr('')
      for (let i = 0; i <= retries; i++) {
        if (cancelled) return
        try {
          const r = await fetch(`${API}/monitor/events?limit=50`)
          if (!r.ok) throw new Error(`API ${r.status}`)
          const data = await r.json()
          if (!cancelled) setEvents(data)
          return
        } catch (e) {
          if (i === retries && !cancelled) setErr(e.message)
          else await new Promise((res) => setTimeout(res, 800))
        }
      }
    }
    attemptLoad()
    return () => { cancelled = true }
  }, [API])

  const runScan = async () => {
    setNotice('')
    try {
      await fetch(`${API}/monitor/scan`, { method: 'POST' })
      await fetch(`${API}/monitor/deliver`, { method: 'POST' })
      setNotice('Scan and delivery completed.')
      load()
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <main className="page-wrap">
      <section className="card">
        <h1>Alert Inbox</h1>
        <p>Monitor connector delta events, filings, contracts, and sanctions hits.</p>
      </section>
      <section className="card">
        <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
          <button className="btn btn-primary" onClick={runScan}>Run Scan + Deliver</button>
          <button className="btn btn-primary" onClick={load}>Refresh</button>
        </div>
        {notice && <p style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>{notice}</p>}
        {err && <p style={{color:"var(--red)",fontWeight:700}}>{err}</p>}
      </section>
      <section className="card">
        <h2>Events ({events.length})</h2>
        {events.length === 0 ? (
          <p style={{color:"var(--text-soft)",fontStyle:"italic",fontSize:"0.82rem"}}>No alert events yet. Configure rules and run a scan.</p>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:'0.5rem' }}>
            {events.map((e) => {
              const kindColor = { new_filing:'#818cf8', sanctions_hit:'#f87171', contract:'#4ade80', news:'#fbbf24' }[e.kind] || '#94a3b8'
              const norm = e.payload?.normalized || e.payload || {}
              const title = norm.title || norm.company_name || norm.description || e.kind
              const source = norm.source || e.source || ''
              const date = (norm.filed_at || norm.ingested_at || norm.date || '').slice(0,10)
              return (
                <div key={e.id} style={{ background:'rgba(8,13,26,0.85)', border:'1px solid var(--line)', borderRadius:10, padding:'0.85rem 1rem' }}>
                  <div style={{ display:'flex', gap:'0.6rem', alignItems:'center', marginBottom:'0.4rem', flexWrap:'wrap' }}>
                    <span style={{ fontSize:'0.72rem', fontWeight:700, color:kindColor, background:`${kindColor}22`, padding:'2px 8px', borderRadius:5, textTransform:'uppercase' }}>{e.kind?.replace('_',' ')}</span>
                    {e.ticker && <span style={{ fontSize:'0.72rem', color:'#fbbf24', fontWeight:600 }}>{e.ticker}</span>}
                    {source && <span style={{ fontSize:'0.72rem', color:'#64748b' }}>{source}</span>}
                    {date && <span style={{ fontSize:'0.72rem', color:'#475569', marginLeft:'auto' }}>{date}</span>}
                    <span style={{ fontSize:'0.68rem', color: e.delivered ? '#4ade80' : '#f87171', marginLeft: date ? '0' : 'auto' }}>
                      {e.delivered ? '✓ delivered' : '⏳ pending'}
                    </span>
                  </div>
                  <div style={{ fontSize:'0.88rem', color:'#e2e8f0', fontWeight:500 }}>{title}</div>
                  {norm.amount && <div style={{ fontSize:'0.75rem', color:'#94a3b8', marginTop:'0.2rem' }}>Amount: {norm.amount}</div>}
                  {norm.jurisdiction && <div style={{ fontSize:'0.75rem', color:'#94a3b8' }}>Jurisdiction: {norm.jurisdiction}</div>}
                </div>
              )
            })}
          </div>
        )}
      </section>
    </main>
  )
}
