import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

function GraphView({data}){
  // simple radial layout
  if(!data) return null
  const nodes = data.nodes||[]
  const edges = data.edges||[]
  const W=880,H=560, cx=W/2, cy=H/2
  const positions = {}
  const R = Math.min(W,H)/2 - 60
  nodes.forEach((n,i)=>{
    const a = (i/nodes.length)*Math.PI*2
    positions[n.id] = {x: cx + R*Math.cos(a), y: cy + R*Math.sin(a)}
  })
  return (
    <svg width={W} height={H} style={{border:'1px solid var(--line)', borderRadius: 12, background:'rgba(8,13,26,0.75)'}}>
      {edges.map((e,i)=>{
        const s = positions[e.src]||{x:cx,y:cy}
        const d = positions[e.dst]||{x:cx,y:cy}
        return <g key={i}>
          <line x1={s.x} y1={s.y} x2={d.x} y2={d.y} stroke="rgba(148,163,184,0.65)" strokeWidth={1.1}/>
        </g>
      })}
      {nodes.map((n,i)=>{
        const p = positions[n.id]
        return <g key={n.id}>
          <circle cx={p.x} cy={p.y} r={12} fill="#6ea8fe"/>
          <text x={p.x+14} y={p.y+4} fontSize={12} fill="#dbeafe">{n.name}</text>
        </g>
      })}
    </svg>
  )
}

export default function GraphPage(){
  const API = getApiBaseUrl()
  const [entityId,setEntityId]=useState('');
  const [data,setData]=useState(null);
  const [err,setErr]=useState('');
  const run=async()=>{
    setErr('');
    try {
      const r=await fetch(`${API}/graph/export?entity_id=${encodeURIComponent(entityId)}&depth=2`)
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
        <h1>Intelligence Graph</h1>
        <p>Expand relationship edges for a target entity and visually inspect linked nodes.</p>
      </section>
      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <div className={styles.controls}>
            <label className={styles.label}>
              Entity ID
              <input
                className={styles.input}
                value={entityId}
                onChange={e=>setEntityId(e.target.value)}
                placeholder="Entity ID (example: 1)"
              />
            </label>
            <div className={styles.buttonRow}>
              <button className={styles.button} onClick={run}>Expand Graph</button>
            </div>
            {err ? <p className={styles.dangerText}>{err}</p> : null}
            <div className={styles.metaRow}>
              <span className={styles.chip}>Nodes: {data?.nodes?.length ?? 0}</span>
              <span className={styles.chip}>Edges: {data?.edges?.length ?? 0}</span>
            </div>
          </div>
        </aside>
        <section className={styles.panel}>
          <h2>Graph Canvas</h2>
          {data ? <GraphView data={data}/> : <p className={styles.empty}>Run expansion to render the graph.</p>}
        </section>
      </section>
    </main>
  )
}
