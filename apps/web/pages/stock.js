import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'
export default function Stock(){
  const API = getApiBaseUrl()
  const [t,setT]=useState('AAPL');
  const [data,setData]=useState(null);
  const [err,setErr]=useState('');
  const run=async()=>{
    setErr('');
    try {
      const r=await fetch(`${API}/finance/analyze_stock?ticker=${encodeURIComponent(t)}`)
      if (!r.ok) throw new Error(`API returned ${r.status}`)
      setData(await r.json())
    } catch (e) {
      setData(null)
      setErr(`Request failed: ${e.message}`)
    }
  }
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Stock Analysis</h1>
        <p>Run a quick fundamentals + technical + DCF snapshot for a given ticker.</p>
      </section>
      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <div className={styles.controls}>
            <label className={styles.label}>
              Ticker
              <input className={styles.input} value={t} onChange={e=>setT(e.target.value)} />
            </label>
            <div className={styles.buttonRow}>
              <button className={styles.button} onClick={run}>Analyze</button>
            </div>
            {err ? <p className={styles.dangerText}>{err}</p> : null}
          </div>
        </aside>
        <section className={styles.panel}>
          <h2>Analysis Output</h2>
          <pre className={styles.mono}>{data?JSON.stringify(data,null,2):'Enter a ticker and run analysis.'}</pre>
        </section>
      </section>
    </main>
  )
}
