import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

export default function SearchPage(){
  const [q,setQ]=useState('');
  const [res,setRes]=useState(null);
  const [err,setErr]=useState('');
  const API=getApiBaseUrl();
  const run=async()=>{
    setErr('');
    try {
      // Use trailing slash to avoid cross-origin redirect from /search -> /search/
      const r=await fetch(`${API}/search/?q=${encodeURIComponent(q)}`);
      if (!r.ok) throw new Error(`API returned ${r.status}`);
      setRes(await r.json());
    } catch (e) {
      setRes(null);
      setErr(`Request failed: ${e.message}`);
    }
  }
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Global Search</h1>
        <p>
          Query entities, relationship signals, and evidence-linked records in one place.
        </p>
      </section>
      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <div className={styles.controls}>
            <label className={styles.label}>
              Search query
              <input
                className={styles.input}
                value={q}
                onChange={e=>setQ(e.target.value)}
                placeholder="Search entities, documents..."
              />
            </label>
            <div className={styles.buttonRow}>
              <button className={styles.button} onClick={run}>Run Search</button>
            </div>
            {err ? <p className={styles.dangerText}>{err}</p> : null}
            <p className={styles.subtle}>Tip: try queries like `apple`, `microsoft`, or `defense`.</p>
          </div>
        </aside>
        <section className={styles.panel}>
          <h2>Search Result JSON</h2>
          <pre className={styles.mono}>{res?JSON.stringify(res,null,2):'No results yet. Run a query to inspect output.'}</pre>
        </section>
      </section>
    </main>
  )
}
