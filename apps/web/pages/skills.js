import { useEffect, useState } from 'react'
import { getApiBaseUrl, apiFetch } from '../lib/api';
import styles from '../src/styles/Page.module.css'
export default function SkillsGateway(){
  const API = getApiBaseUrl()
  const [name,setName]=useState('dcf');
  const [input,setInput]=useState('{"fcf":[10,11,12,13,14],"wacc":0.1,"terminal_growth":0.02}');
  const [data,setData]=useState(null);
  const [err,setErr]=useState('');
  const [status,setStatus]=useState(null);
  useEffect(()=>{ fetch(`${API}/skills/status`).then(r=>r.json()).then(setStatus).catch(()=>{}) }, [API]);
  const run=async()=>{
    setErr('');
    try {
      const parsedInput = JSON.parse(input)
      const query = new URLSearchParams({ name, version: 'v1' }).toString()
      const r = await apiFetch(`/skills/run?${query}`, { method:'POST',
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
    <main className="page-wrap">
      <section className="card">
        <h1>Finance Skills Gateway</h1>
        <p>Execute approved skills with explicit inputs and inspect structured outputs.</p>
        {status && (
          <p style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>
            AI providers: Anthropic {status.anthropic?.configured ? `(live · ${status.anthropic.model})` : '(not configured)'}
            {' · '}OpenAI {status.openai?.configured ? '(fallback ready)' : '(not configured)'}
          </p>
        )}
      </section>
      <section className="grid-cols-2">
        <aside className="card">
          <div style={{display:"flex",flexDirection:"column",gap:"0.75rem"}}>
            <label style={{display:"flex",flexDirection:"column",gap:4,color:"var(--text-muted)",fontSize:"0.82rem",fontWeight:600}}>
              Skill Name
              <select className="inp" value={name} onChange={e=>setName(e.target.value)}>
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
            <label style={{display:"flex",flexDirection:"column",gap:4,color:"var(--text-muted)",fontSize:"0.82rem",fontWeight:600}}>
              Input JSON
              <textarea className="inp" value={input} onChange={e=>setInput(e.target.value)} />
            </label>
            <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
              <button className="btn btn-primary" onClick={run}>Run Skill</button>
            </div>
            {err ? <p style={{color:"var(--red)",fontWeight:700}}>{err}</p> : null}
          </div>
        </aside>
        <section className="card">
          <h2>Skill Run Output{data?.output?.provider ? ` · ${data.output.provider}` : ''}</h2>
          <pre className="card mono">{data?JSON.stringify(data,null,2):'No run yet.'}</pre>
        </section>
      </section>
    </main>
  )
}
