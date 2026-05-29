import { useRouter } from 'next/router'
import useSWR from 'swr'
import { useRef } from 'react'
const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:3001'
const fetcher=(u)=>fetch(u).then(r=>r.json())

export default function Portfolio(){
  const router=useRouter(); const {id}=router.query
  const {data}=useSWR(id?`${API}/monitor/portfolios/${id}/exposure`:null, fetcher)
  const fileRef=useRef(null)
  const importCsv=async()=>{ const f=fileRef.current.files[0]; const fd=new FormData(); fd.append('file', f); await fetch(`${API}/monitor/portfolios/${id}/import_csv`,{method:'POST', body:fd}); alert('Imported'); }
  return (
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Portfolio Exposure</h1>
      <div>
        <input ref={fileRef} type="file" accept=".csv" />
        <button onClick={importCsv}>Import CSV</button>
      </div>
      <pre>{data?JSON.stringify(data,null,2):'Loading...'}</pre>
    </main>
  )
}
