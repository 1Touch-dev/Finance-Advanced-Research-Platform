import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'
export default function SkillsGateway(){
  const API = getApiBaseUrl()
  const [name,setName]=useState('dcf');
  const [input,setInput]=useState('{"fcf":[10,11,12,13,14],"wacc":0.1,"terminal_growth":0.02}');
  const [data,setData]=useState(null);
  const [err,setErr]=useState('');
  const run=async()=>{
    setErr('');
    try {
      const parsedInput = JSON.parse(input)
      const query = new URLSearchParams({ name, version: 'v1' }).toString()
      const r = await fetch(`${API}/skills/run?${query}`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ input: parsedInput })
      })
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
        <h1>Finance Skills Gateway</h1>
        <p>Execute approved skills with explicit inputs and inspect structured outputs.</p>
      </section>
      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <div className={styles.controls}>
            <label className={styles.label}>
              Skill Name
              <select className={styles.select} value={name} onChange={e=>setName(e.target.value)}>
          <option value="dcf">dcf</option>
          <option value="comps">comps</option>
          <option value="earnings">earnings</option>
          <option value="one_pager">one_pager</option>
          <option value="ic_memo">ic_memo</option>
          <option value="due_diligence">due_diligence</option>
          <option value="model_review">model_review</option>
          <option value="market_research">market_research</option>
              </select>
            </label>
            <label className={styles.label}>
              Input JSON
              <textarea className={styles.textarea} value={input} onChange={e=>setInput(e.target.value)} />
            </label>
            <div className={styles.buttonRow}>
              <button className={styles.button} onClick={run}>Run Skill</button>
            </div>
            {err ? <p className={styles.dangerText}>{err}</p> : null}
          </div>
        </aside>
        <section className={styles.panel}>
          <h2>Skill Run Output</h2>
          <pre className={styles.mono}>{data?JSON.stringify(data,null,2):'No run yet.'}</pre>
        </section>
      </section>
    </main>
  )
}
