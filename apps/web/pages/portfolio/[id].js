import { useRouter } from 'next/router'
import useSWR from 'swr'
import { useRef, useState } from 'react'
import { getApiBaseUrl } from '../../lib/api'
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
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Portfolio Exposure</h1>
        <p>Inspect weighted position concentration and import additional positions via CSV.</p>
      </section>
      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <div className={styles.controls}>
            <label className={styles.label}>
              Upload positions CSV
              <input className={styles.input} ref={fileRef} type="file" accept=".csv" />
            </label>
            <div className={styles.buttonRow}>
              <button className={styles.button} onClick={importCsv}>Import CSV</button>
            </div>
            {status ? <p className={styles.subtle}>{status}</p> : null}
          </div>
        </aside>
        <section className={styles.panel}>
          <h2>Exposure Output</h2>
          <pre className={styles.mono}>{data?JSON.stringify(data,null,2):'Loading...'}</pre>
        </section>
      </section>
    </main>
  )
}
