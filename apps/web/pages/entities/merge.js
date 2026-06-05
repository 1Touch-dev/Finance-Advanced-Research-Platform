import { useEffect, useState } from 'react'
import { getApiBaseUrl } from '../../lib/api'
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
      const r = await fetch(`${API}/entities/merge/candidates`)
      if (!r.ok) throw new Error(`API ${r.status}`)
      setCandidates(await r.json())
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => { load() }, [])

  const approve = async (c) => {
    setNotice('')
    await fetch(`${API}/entities/merge/approve?primary_id=${c.a.id}&secondary_id=${c.b.id}`, { method: 'POST' })
    setNotice(`Merged ${c.b.name} into ${c.a.name}`)
    load()
  }

  const reject = async (id) => {
    await fetch(`${API}/entities/merge/reject?candidate_id=${id}`, { method: 'POST' })
    setNotice('Merge rejected')
    load()
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Entity Merge Review</h1>
        <p>Review proposed entity merges side-by-side and approve or reject.</p>
      </section>
      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <h2>Queue ({candidates.length})</h2>
          {candidates.length === 0 ? (
            <p className={styles.empty}>No pending merge candidates.</p>
          ) : (
            <ul className={styles.list}>
              {candidates.map((c) => (
                <li className={styles.listItem} key={c.id}>
                  <button className={styles.button} onClick={() => setSelected(c)}>
                    {c.a?.name} ↔ {c.b?.name} ({c.score}%)
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
        <section className={styles.panel}>
          {selected ? (
            <>
              <h2>Compare</h2>
              <div className={styles.grid2}>
                <div>
                  <h3>Entity A — {selected.a?.name}</h3>
                  <p className={styles.subtle}>ID {selected.a?.id} · {selected.a?.kind}</p>
                </div>
                <div>
                  <h3>Entity B — {selected.b?.name}</h3>
                  <p className={styles.subtle}>ID {selected.b?.id} · {selected.b?.kind}</p>
                </div>
              </div>
              <p>Reason: {selected.reason}</p>
              <div className={styles.buttonRow}>
                <button className={styles.button} onClick={() => approve(selected)}>Approve merge</button>
                <button className={styles.button} onClick={() => reject(selected.id)}>Reject</button>
              </div>
            </>
          ) : (
            <p className={styles.empty}>Select a candidate to review.</p>
          )}
          {notice && <p className={styles.subtle}>{notice}</p>}
          {err && <p className={styles.dangerText}>{err}</p>}
        </section>
      </section>
    </main>
  )
}
