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
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Review Workspace</h1>
        <p>Review report sections, submit edits, leave comments, and export reviewer-ready markdown.</p>
      </section>
      {!rep? 'Loading...' : (
        <>
          <section className={styles.panel}>
            <h2>{rep.title} <span className={styles.subtle}>({rep.kind})</span></h2>
            <ul className={styles.list}>
              {rep.sections.map(s=> (
                <li className={styles.listItem} key={s.id}>
                  <span>{s.order}. {s.name}</span>
                  <button className={styles.button} onClick={()=>setSectionId(s.id)}>Select</button>
                </li>
              ))}
            </ul>
          </section>
          <section className={styles.grid2}>
            <div className={styles.panel}>
            <h3>Suggest Edit</h3>
              <label className={styles.label}>
                Proposed content
                <textarea className={styles.textarea} value={sectionText} onChange={e=>setSectionText(e.target.value)} />
              </label>
              <div className={styles.buttonRow}>
                <button className={styles.button} onClick={safeSuggest} disabled={!sectionId}>
                  Propose for Section #{sectionId || '...'}
                </button>
              </div>
            </div>
            <div className={styles.panel}>
            <h3>Add Comment</h3>
              <label className={styles.label}>
                Comment text
                <textarea className={styles.textarea} value={comment} onChange={e=>setComment(e.target.value)} />
              </label>
              <div className={styles.buttonRow}>
                <button className={styles.button} onClick={safeAddComment}>Post Comment</button>
              </div>
            </div>
          </section>
          <section className={styles.panel}>
            <h3>Exports</h3>
            <div className={styles.buttonRow}>
              <button className={styles.button} onClick={safeExport}>Export Markdown</button>
              <button className={styles.button} onClick={async()=>{ try{await exportPdf()}catch(e){setErr(e.message)}}}>Export PDF</button>
              <button className={styles.button} onClick={async()=>{ try{await exportDocx()}catch(e){setErr(e.message)}}}>Export Word</button>
            </div>
            {notice ? <p className={styles.subtle}>{notice}</p> : null}
            {err ? <p className={styles.dangerText}>{err}</p> : null}
          </section>
        </>
      )}
    </main>
  )
}
