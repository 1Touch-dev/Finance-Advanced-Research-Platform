import { useEffect, useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

export default function AlertsPage() {
  const API = getApiBaseUrl()
  const [events, setEvents] = useState([])
  const [err, setErr] = useState('')
  const [notice, setNotice] = useState('')

  const load = async () => {
    setErr('')
    try {
      const r = await fetch(`${API}/monitor/events?limit=50`)
      if (!r.ok) throw new Error(`API ${r.status}`)
      setEvents(await r.json())
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => {
    let cancelled = false
    const attemptLoad = async (retries = 2) => {
      setErr('')
      for (let i = 0; i <= retries; i++) {
        if (cancelled) return
        try {
          const r = await fetch(`${API}/monitor/events?limit=50`)
          if (!r.ok) throw new Error(`API ${r.status}`)
          const data = await r.json()
          if (!cancelled) setEvents(data)
          return
        } catch (e) {
          if (i === retries && !cancelled) setErr(e.message)
          else await new Promise((res) => setTimeout(res, 800))
        }
      }
    }
    attemptLoad()
    return () => { cancelled = true }
  }, [API])

  const runScan = async () => {
    setNotice('')
    try {
      await fetch(`${API}/monitor/scan`, { method: 'POST' })
      await fetch(`${API}/monitor/deliver`, { method: 'POST' })
      setNotice('Scan and delivery completed.')
      load()
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Alert Inbox</h1>
        <p>Monitor connector delta events, filings, contracts, and sanctions hits.</p>
      </section>
      <section className={styles.panel}>
        <div className={styles.buttonRow}>
          <button className={styles.button} onClick={runScan}>Run Scan + Deliver</button>
          <button className={styles.button} onClick={load}>Refresh</button>
        </div>
        {notice && <p className={styles.subtle}>{notice}</p>}
        {err && <p className={styles.dangerText}>{err}</p>}
      </section>
      <section className={styles.panel}>
        <h2>Events ({events.length})</h2>
        {events.length === 0 ? (
          <p className={styles.empty}>No alert events yet. Configure rules and run a scan.</p>
        ) : (
          <ul className={styles.list}>
            {events.map((e) => (
              <li className={styles.listItem} key={e.id}>
                <strong>{e.kind}</strong>
                {e.ticker ? ` · ${e.ticker}` : ''}
                <span className={styles.subtle}> · delivered: {String(e.delivered)}</span>
                <pre className={styles.codeBlock}>{JSON.stringify(e.payload, null, 2)}</pre>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
