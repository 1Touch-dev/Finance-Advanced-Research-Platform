import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'

function GraphView({data}){
  // simple radial layout
  if(!data) return null
  const nodes = data.nodes||[]
  const edges = data.edges||[]
  const W=900,H=600, cx=W/2, cy=H/2
  const byId = Object.fromEntries(nodes.map(n=>[n.id,n]))
  const positions = {}
  const R = Math.min(W,H)/2 - 60
  nodes.forEach((n,i)=>{
    const a = (i/nodes.length)*Math.PI*2
    positions[n.id] = {x: cx + R*Math.cos(a), y: cy + R*Math.sin(a)}
  })
  return (
    <svg width={W} height={H} style={{border:'1px solid #ddd'}}>
      {edges.map((e,i)=>{
        const s = positions[e.src]||{x:cx,y:cy}
        const d = positions[e.dst]||{x:cx,y:cy}
        return <g key={i}>
          <line x1={s.x} y1={s.y} x2={d.x} y2={d.y} stroke="#999" strokeWidth={1}/>
        </g>
      })}
      {nodes.map((n,i)=>{
        const p = positions[n.id]
        return <g key={n.id}>
          <circle cx={p.x} cy={p.y} r={12} fill="#1976d2"/>
          <text x={p.x+14} y={p.y+4} fontSize={12}>{n.name}</text>
        </g>
      })}
    </svg>
  )
}

export default function GraphPage(){
  const [entityId,setEntityId]=useState('');
  const [data,setData]=useState(null);
  const run=async()=>{
    const r=await fetch(`${API}/graph/export?entity_id=${encodeURIComponent(entityId)}&depth=2`)
    setData(await r.json())
  }
  return (
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Intelligence Graph</h1>
      <input value={entityId} onChange={e=>setEntityId(e.target.value)} placeholder="Entity ID"/>
      <button onClick={run}>Expand</button>
      <GraphView data={data}/>
    </main>
  )
}
