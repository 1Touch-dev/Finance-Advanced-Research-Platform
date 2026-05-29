import { useEffect, useState } from 'react'

export default function SearchPage(){
  const [q,setQ]=useState('');
  const [res,setRes]=useState(null);
  const [err,setErr]=useState('');
  const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:3001';
  const run=async()=>{
    setErr('');
    try {
      const r=await fetch(`${API}/search?q=${encodeURIComponent(q)}`);
      if (!r.ok) throw new Error(`API returned ${r.status}`);
      setRes(await r.json());
    } catch (e) {
      setRes(null);
      setErr(`Request failed: ${e.message}`);
    }
  }
  return (
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Global Search</h1>
      <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search entities, documents..."/>
      <button onClick={run}>Search</button>
      {err ? <p style={{color:'#b91c1c'}}>{err}</p> : null}
      <pre>{res?JSON.stringify(res,null,2):'No results'}</pre>
    </main>
  )
}
