import { useState } from 'react'
const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:3001'
export default function Stock(){
  const [t,setT]=useState('AAPL');
  const [data,setData]=useState(null);
  const run=async()=>{
    const r=await fetch(`${API}/finance/analyze_stock?ticker=${encodeURIComponent(t)}`)
    setData(await r.json())
  }
  return (
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Analyze Stock</h1>
      <input value={t} onChange={e=>setT(e.target.value)} />
      <button onClick={run}>Analyze</button>
      <pre>{data?JSON.stringify(data,null,2):'Enter a ticker and analyze'}</pre>
    </main>
  )
}
