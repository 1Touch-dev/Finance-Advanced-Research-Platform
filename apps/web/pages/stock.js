import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
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
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Analyze Stock</h1>
      <input value={t} onChange={e=>setT(e.target.value)} />
      <button onClick={run}>Analyze</button>
      {err ? <p style={{color:'#b91c1c'}}>{err}</p> : null}
      <pre>{data?JSON.stringify(data,null,2):'Enter a ticker and analyze'}</pre>
    </main>
  )
}
