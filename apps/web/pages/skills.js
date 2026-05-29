import { useState } from 'react'
const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:3001'
export default function SkillsGateway(){
  const [name,setName]=useState('dcf');
  const [input,setInput]=useState('{"fcf":[10,11,12,13,14],"wacc":0.1,"terminal_growth":0.02}');
  const [data,setData]=useState(null);
  const run=async()=>{
    const body = { name, version:'v1', input: JSON.parse(input) }
    const r = await fetch(`${API}/skills/run`,{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})
    setData(await r.json())
  }
  return (
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Finance Skills Gateway</h1>
      <div>
        <label>Skill Name </label>
        <select value={name} onChange={e=>setName(e.target.value)}>
          <option value="dcf">dcf</option>
          <option value="comps">comps</option>
          <option value="earnings">earnings</option>
          <option value="one_pager">one_pager</option>
          <option value="ic_memo">ic_memo</option>
          <option value="due_diligence">due_diligence</option>
          <option value="model_review">model_review</option>
          <option value="market_research">market_research</option>
        </select>
      </div>
      <div>
        <label>Input JSON</label>
        <textarea value={input} onChange={e=>setInput(e.target.value)} rows={8} cols={80}></textarea>
      </div>
      <button onClick={run}>Run Skill</button>
      <pre>{data?JSON.stringify(data,null,2):'No run yet'}</pre>
    </main>
  )
}
