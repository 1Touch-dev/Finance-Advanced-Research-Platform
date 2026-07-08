import { useRouter } from 'next/router'
import useSWR from 'swr'
import { useState } from 'react'
import { getApiBaseUrl } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'

const API=getApiBaseUrl()
const fetcher=(u)=>fetch(u).then(r=>r.json())

export default function Review(){
  const router=useRouter(); const {id}=router.query
  const {data:rep, mutate}=useSWR(id?`${API}/reports/${id}`:null, fetcher)
  const [sectionText,setSectionText]=useState('')
  const [sectionId,setSectionId]=useState('')
  const [comment,setComment]=useState('')
  const [err,setErr]=useState('')
  const [notice,setNotice]=useState('')
  const addComment=async()=>{ await fetch(`${API}/review/comments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({report_id:Number(id),section_id:sectionId?Number(sectionId):null,text:comment})}); setComment(''); }
  const suggest=async()=>{ await fetch(`${API}/review/suggest`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({report_id:Number(id),section_id:Number(sectionId),proposed:sectionText})}); setSectionText('') }
  const exportMd=async()=>{ const r=await fetch(`${API}/review/export/${id}/markdown`); setNotice(`Exported: ${(await r.json()).path}`)}
  const exportPdf=async()=>{ const r=await fetch(`${API}/review/export/${id}/pdf`); setNotice(`Exported PDF: ${(await r.json()).path}`)}
  const exportDocx=async()=>{ const r=await fetch(`${API}/review/export/${id}/docx`); setNotice(`Exported Word: ${(await r.json()).path}`)}
  const safeAddComment = async () => {
    setErr(''); setNotice('')
    try { await addComment(); setNotice('Comment added.'); }
    catch (e) { setErr(`Could not add comment: ${e.message}`) }
  }
  const safeSuggest = async () => {
    setErr(''); setNotice('')
    try { await suggest(); setNotice(`Suggestion submitted for section #${sectionId}.`) }
    catch (e) { setErr(`Could not submit suggestion: ${e.message}`) }
  }
  const safeExport = async () => {
    setErr(''); setNotice('')
    try { await exportMd() } catch (e) { setErr(`Could not export markdown: ${e.message}`) }
  }
  return (
    <main className="page-wrap">
      <section className="card">
        <h1>Review Workspace</h1>
        <p>Review report sections, submit edits, leave comments, and export reviewer-ready markdown.</p>
      </section>
      {!rep? 'Loading...' : (
        <>
          <section className="card">
            <h2>{rep.title} <span style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>({rep.kind})</span></h2>
            <ul style={{listStyle:"none",padding:0,margin:0,display:"flex",flexDirection:"column",gap:"0.5rem"}}>
              {rep.sections.map(s=> (
                <li style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:"0.5rem",padding:"8px 10px",background:"rgba(255,255,255,0.025)",borderRadius:8,border:"1px solid var(--line)"}} key={s.id}>
                  <span>{s.order}. {s.name}</span>
                  <button className="btn btn-primary" onClick={()=>setSectionId(s.id)}>Select</button>
                </li>
              ))}
            </ul>
          </section>
          <section className="grid-cols-2">
            <div className="card">
            <h3>Suggest Edit</h3>
              <label style={{display:"flex",flexDirection:"column",gap:4,color:"var(--text-muted)",fontSize:"0.82rem",fontWeight:600}}>
                Proposed content
                <textarea className="inp" value={sectionText} onChange={e=>setSectionText(e.target.value)} />
              </label>
              <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
                <button className="btn btn-primary" onClick={safeSuggest} disabled={!sectionId}>
                  Propose for Section #{sectionId || '...'}
                </button>
              </div>
            </div>
            <div className="card">
            <h3>Add Comment</h3>
              <label style={{display:"flex",flexDirection:"column",gap:4,color:"var(--text-muted)",fontSize:"0.82rem",fontWeight:600}}>
                Comment text
                <textarea className="inp" value={comment} onChange={e=>setComment(e.target.value)} />
              </label>
              <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
                <button className="btn btn-primary" onClick={safeAddComment}>Post Comment</button>
              </div>
            </div>
          </section>
          <section className="card">
            <h3>Exports</h3>
            <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
              <button className="btn btn-primary" onClick={safeExport}>Export Markdown</button>
              <button className="btn btn-primary" onClick={async()=>{ try{await exportPdf()}catch(e){setErr(e.message)}}}>Export PDF</button>
              <button className="btn btn-primary" onClick={async()=>{ try{await exportDocx()}catch(e){setErr(e.message)}}}>Export Word</button>
            </div>
            {notice ? <p style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>{notice}</p> : null}
            {err ? <p style={{color:"var(--red)",fontWeight:700}}>{err}</p> : null}
          </section>
        </>
      )}
    </main>
  )
}
