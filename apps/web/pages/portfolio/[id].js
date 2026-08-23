import { useRouter } from 'next/router'
import useSWR from 'swr'
import { useRef, useState } from 'react'
import { getApiBaseUrl, authHeaders } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'

const API=getApiBaseUrl()
const fetcher=(u)=>fetch(u).then(r=>r.json())

export default function Portfolio(){
  const router=useRouter(); const {id}=router.query
  const {data}=useSWR(id?`${API}/monitor/portfolios/${id}/exposure`:null, fetcher)
  const fileRef=useRef(null)
  const [status, setStatus] = useState('')
  const importCsv=async()=>{
    setStatus('')
    const f=fileRef.current.files[0]
    if (!f) { setStatus('Select a CSV file first.'); return }
    const fd=new FormData(); fd.append('file', f)
    await fetch(`${API}/monitor/portfolios/${id}/import_csv`,{method:'POST', body:fd})
    setStatus('CSV imported successfully.')
  }
  return (
    <main className="page-wrap">
      <section className="card">
        <h1>Portfolio Exposure</h1>
        <p>Inspect weighted position concentration and import additional positions via CSV.</p>
      </section>
      <section className="grid-cols-2">
        <aside className="card">
          <div style={{display:"flex",flexDirection:"column",gap:"0.75rem"}}>
            <label style={{display:"flex",flexDirection:"column",gap:4,color:"var(--text-muted)",fontSize:"0.82rem",fontWeight:600}}>
              Upload positions CSV
              <input className="inp" ref={fileRef} type="file" accept=".csv" />
            </label>
            <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
              <button className="btn btn-primary" onClick={importCsv}>Import CSV</button>
            </div>
            {status ? <p style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>{status}</p> : null}
          </div>
        </aside>
        <section className="card">
          <h2>Exposure Output</h2>
          <pre className="card mono">{data?JSON.stringify(data,null,2):'Loading...'}</pre>
        </section>
      </section>
    </main>
  )
}
