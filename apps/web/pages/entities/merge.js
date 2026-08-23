import { useEffect, useState } from 'react'
import { getApiBaseUrl, apiFetch } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'

export default function EntityMergePage() {
  const API = getApiBaseUrl()
  const [candidates, setCandidates] = useState([])
  const [selected, setSelected] = useState(null)
  const [notice, setNotice] = useState('')
  const [err, setErr] = useState('')

  const load = async () => {
    setErr('')
    try {
      const r = await apiFetch(`/entities/merge/candidates`)
      if (!r.ok) throw new Error(`API ${r.status}`)
      setCandidates(await r.json())
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => { load() }, [])

  const approve = async (c) => {
    setNotice('')
    await apiFetch(`/entities/merge/approve?primary_id=${c.a.id}&secondary_id=${c.b.id}`, { method: 'POST' })
    setNotice(`Merged ${c.b.name} into ${c.a.name}`)
    load()
  }

  const reject = async (id) => {
    await apiFetch(`/entities/merge/reject?candidate_id=${id}`, { method: 'POST' })
    setNotice('Merge rejected')
    load()
  }

  return (
    <main className="page-wrap">
      <section className="card">
        <h1>Entity Merge Review</h1>
        <p>Review proposed entity merges side-by-side and approve or reject.</p>
      </section>
      <section className="grid-cols-2">
        <aside className="card">
          <h2>Queue ({candidates.length})</h2>
          {candidates.length === 0 ? (
            <p style={{color:"var(--text-soft)",fontStyle:"italic",fontSize:"0.82rem"}}>No pending merge candidates.</p>
          ) : (
            <ul style={{listStyle:"none",padding:0,margin:0,display:"flex",flexDirection:"column",gap:"0.5rem"}}>
              {candidates.map((c) => (
                <li style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:"0.5rem",padding:"8px 10px",background:"rgba(255,255,255,0.025)",borderRadius:8,border:"1px solid var(--line)"}} key={c.id}>
                  <button className="btn btn-primary" onClick={() => setSelected(c)}>
                    {c.a?.name} ↔ {c.b?.name} ({c.score}%)
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
        <section className="card">
          {selected ? (
            <>
              <h2>Compare</h2>
              <div className="grid-cols-2">
                <div>
                  <h3>Entity A — {selected.a?.name}</h3>
                  <p style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>ID {selected.a?.id} · {selected.a?.kind}</p>
                </div>
                <div>
                  <h3>Entity B — {selected.b?.name}</h3>
                  <p style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>ID {selected.b?.id} · {selected.b?.kind}</p>
                </div>
              </div>
              <p>Reason: {selected.reason}</p>
              <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
                <button className="btn btn-primary" onClick={() => approve(selected)}>Approve merge</button>
                <button className="btn btn-primary" onClick={() => reject(selected.id)}>Reject</button>
              </div>
            </>
          ) : (
            <p style={{color:"var(--text-soft)",fontStyle:"italic",fontSize:"0.82rem"}}>Select a candidate to review.</p>
          )}
          {notice && <p style={{color:"var(--text-soft)",fontSize:"0.8rem"}}>{notice}</p>}
          {err && <p style={{color:"var(--red)",fontWeight:700}}>{err}</p>}
        </section>
      </section>
    </main>
  )
}
