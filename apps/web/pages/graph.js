import { useEffect, useRef, useState } from 'react'
import { getApiBaseUrl } from '../lib/api'
import styles from '../src/styles/Page.module.css'

export default function GraphPage() {
  const API = getApiBaseUrl()
  const cyRef = useRef(null)
  const containerRef = useRef(null)
  const [entityId, setEntityId] = useState('1')
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')

  const run = async () => {
    setErr('')
    try {
      const r = await fetch(`${API}/graph/export?entity_id=${encodeURIComponent(entityId)}&depth=2`)
      if (!r.ok) throw new Error(`API returned ${r.status}`)
      setData(await r.json())
    } catch (e) {
      setData(null)
      setErr(`Request failed: ${e.message}`)
    }
  }

  useEffect(() => {
    if (!data || !containerRef.current) return
    const script = document.createElement('script')
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js'
    script.onload = () => {
      if (cyRef.current) cyRef.current.destroy()
      const elements = []
      ;(data.nodes || []).forEach((n) => {
        elements.push({ data: { id: String(n.id), label: n.name || String(n.id) } })
      })
      ;(data.edges || []).forEach((e, i) => {
        elements.push({ data: { id: `e${i}`, source: String(e.src), target: String(e.dst), label: e.kind || '' } })
      })
      cyRef.current = window.cytoscape({
        container: containerRef.current,
        elements,
        style: [
          { selector: 'node', style: { 'background-color': '#6ea8fe', label: 'data(label)', color: '#dbeafe', 'font-size': 10 } },
          { selector: 'edge', style: { width: 2, 'line-color': '#94a3b8', 'target-arrow-color': '#94a3b8', 'target-arrow-shape': 'triangle', label: 'data(label)', 'font-size': 8, color: '#cbd5e1' } },
        ],
        layout: { name: 'cose', animate: false },
        wheelSensitivity: 0.2,
      })
      cyRef.current.on('tap', 'node', (evt) => {
        const id = evt.target.id()
        setEntityId(id)
      })
    }
    document.body.appendChild(script)
    return () => { if (cyRef.current) cyRef.current.destroy() }
  }, [data])

  const exportJson = () => {
    if (!data) return
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `graph-${entityId}.json`
    a.click()
  }

  const exportPng = () => {
    if (!cyRef.current) return
    const png = cyRef.current.png({ scale: 2 })
    const a = document.createElement('a')
    a.href = png
    a.download = `graph-${entityId}.png`
    a.click()
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Intelligence Graph</h1>
        <p>Interactive Cytoscape graph with expand-on-click, zoom/pan, and export.</p>
      </section>
      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <div className={styles.controls}>
            <label className={styles.label}>
              Entity ID
              <input className={styles.input} value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="Entity ID (example: 1)" />
            </label>
            <div className={styles.buttonRow}>
              <button className={styles.button} onClick={run}>Expand Graph</button>
              <button className={styles.button} onClick={exportJson} disabled={!data}>Export JSON</button>
              <button className={styles.button} onClick={exportPng} disabled={!data}>Export PNG</button>
            </div>
            {err ? <p className={styles.dangerText}>{err}</p> : null}
            <div className={styles.metaRow}>
              <span className={styles.chip}>Nodes: {data?.nodes?.length ?? 0}</span>
              <span className={styles.chip}>Edges: {data?.edges?.length ?? 0}</span>
            </div>
          </div>
        </aside>
        <section className={styles.panel}>
          <h2>Graph Canvas</h2>
          <div ref={containerRef} style={{ width: '100%', height: 560, border: '1px solid var(--line)', borderRadius: 12, background: 'rgba(8,13,26,0.75)' }} />
          {!data && <p className={styles.empty}>Run expansion to render the graph.</p>}
        </section>
      </section>
    </main>
  )
}
