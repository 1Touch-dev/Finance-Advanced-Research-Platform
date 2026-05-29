import { useRouter } from 'next/router'
import useSWR from 'swr'
import { useState } from 'react'
const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:3001'
const fetcher=(u)=>fetch(u).then(r=>r.json())

export default function Review(){
  const router=useRouter(); const {id}=router.query
  const {data:rep, mutate}=useSWR(id?`${API}/reports/${id}`:null, fetcher)
  const [sectionText,setSectionText]=useState('')
  const [sectionId,setSectionId]=useState('')
  const [comment,setComment]=useState('')
  const addComment=async()=>{ await fetch(`${API}/review/comments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({report_id:Number(id),section_id:sectionId?Number(sectionId):null,text:comment})}); setComment(''); }
  const suggest=async()=>{ await fetch(`${API}/review/suggest`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({report_id:Number(id),section_id:Number(sectionId),proposed:sectionText})}); setSectionText('') }
  const exportMd=async()=>{ const r=await fetch(`${API}/review/export/${id}/markdown`); alert(`Exported: ${(await r.json()).path}`)}
  return (
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Review Workspace</h1>
      {!rep? 'Loading...' : (
        <>
          <h2>{rep.title} <small>({rep.kind})</small></h2>
          <h3>Sections</h3>
          <ul>
            {rep.sections.map(s=> <li key={s.id}>{s.order}. {s.name} <button onClick={()=>setSectionId(s.id)}>Edit</button></li> )}
          </ul>
          <div>
            <h3>Suggest Edit</h3>
            <textarea rows={6} cols={80} value={sectionText} onChange={e=>setSectionText(e.target.value)} />
            <div><button onClick={suggest} disabled={!sectionId}>Propose for Section #{sectionId}</button></div>
          </div>
          <div>
            <h3>Add Comment</h3>
            <textarea rows={4} cols={80} value={comment} onChange={e=>setComment(e.target.value)} />
            <div><button onClick={addComment}>Comment</button></div>
          </div>
          <div>
            <h3>Exports</h3>
            <button onClick={exportMd}>Export Markdown</button>
          </div>
        </>
      )}
    </main>
  )
}
