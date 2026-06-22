import { useState, useMemo } from 'react'
import styles from '../src/styles/Page.module.css'
import cStyles from '../src/styles/Compare.module.css'
import { getApiBaseUrl } from '../lib/api'

const API = getApiBaseUrl()

// ── KPI configuration ─────────────────────────────────────────────────────────

const KPIS = [
  { id: 'contracts',  label: 'Gov\'t Contracts ($M)', key: 'total_obligated_usd', fmt: v => v > 0 ? `$${(v/1e6).toFixed(1)}M` : '$0', higher: 'more' },
  { id: 'lobbying',   label: 'Lobbying Spend ($K)',   key: 'kpi_lobbying_spend',  fmt: v => v > 0 ? `$${(v/1e3).toFixed(0)}K` : '$0',  higher: 'more' },
  { id: 'court',      label: 'Court Risk',            key: 'kpi_court_risk',      fmt: v => v || 'LOW', higher: 'less' },
  { id: 'sanctions',  label: 'Sanctions',             key: 'kpi_sanctions_risk',  fmt: v => v || 'CLEAR', higher: 'less' },
  { id: 'confidence', label: 'Data Confidence',       key: 'kpi_data_confidence', fmt: v => `${v||0}%`, higher: 'more' },
  { id: 'sources',    label: 'Sources Active',        key: 'kpi_sources_active',  fmt: v => `${v||0}/8`, higher: 'more' },
  { id: 'sec',        label: 'SEC Filings',           key: 'sec_filings',         fmt: v => v||0, higher: 'more' },
  { id: 'news',       label: 'News Articles',         key: 'news_articles',       fmt: v => v||0, higher: 'more' },
  { id: 'lobbying_f', label: 'Lobbying Filings',      key: 'lobbying_filings',    fmt: v => v||0, higher: 'more' },
  { id: 'fec',        label: 'FEC Committees',        key: 'fec_committees',      fmt: v => v||0, higher: 'more' },
  { id: 'fara',       label: 'FARA Registrations',    key: 'fara_registrations',  fmt: v => v||0, higher: 'more' },
  { id: 'graph',      label: 'Relationships Mapped',  key: 'relationships_written',fmt: v => v||0, higher: 'more' },
]

const RISK_VALS = { CLEAR: 0, LOW: 1, MEDIUM: 2, HIGH: 3, VERY_HIGH: 4 }

const DEMO_ENTITIES = [
  { name: 'Palantir Technologies', ticker: 'PLTR', type: 'org' },
  { name: 'Peter Thiel',           ticker: '',     type: 'person' },
  { name: 'Elon Musk',             ticker: '',     type: 'person' },
]

// ── Radar chart (pure SVG) ─────────────────────────────────────────────────────

function RadarChart({ entities, summaries }) {
  const N = 6
  const AXES = ['contracts', 'lobbying', 'court', 'confidence', 'sources', 'news']
    .map(id => KPIS.find(k => k.id === id))
    .filter(Boolean)

  const cx = 160, cy = 160, r = 110
  const pts = (idx) => (angle) => {
    const x = cx + r * Math.sin(angle)
    const y = cy - r * Math.cos(angle)
    return [x, y]
  }

  const axisPoints = AXES.map((_, i) => {
    const a = (2 * Math.PI * i) / AXES.length
    const x = cx + r * Math.sin(a)
    const y = cy - r * Math.cos(a)
    return [x, y, a]
  })

  const normalize = (entity, summary, kpi) => {
    const val = summary?.[kpi.key]
    if (!val) return 0
    if (kpi.id === 'court' || kpi.id === 'sanctions') {
      const rv = RISK_VALS[String(val).toUpperCase()] || 0
      return Math.min(1, rv / 3)
    }
    if (kpi.id === 'confidence' || kpi.id === 'sources') return Math.min(1, Number(val) / 100)
    const nums = entities
      .map((e, i) => Number(summaries[i]?.[kpi.key] || 0))
      .filter(Boolean)
    const mx = Math.max(...nums, 1)
    return Math.min(1, Number(val) / mx)
  }

  const COLORS = ['#818cf8', '#f97316', '#4ade80', '#fbbf24', '#f43f5e']

  const entityPolygon = (entity, summary, colorIdx) => {
    if (!summary) return null
    const points = AXES.map((kpi, i) => {
      const a = (2 * Math.PI * i) / AXES.length
      const n = normalize(entity, summary, kpi)
      const dist = n * r
      const x = cx + dist * Math.sin(a)
      const y = cy - dist * Math.cos(a)
      return `${x},${y}`
    }).join(' ')
    const color = COLORS[colorIdx % COLORS.length]
    return (
      <g key={colorIdx}>
        <polygon points={points} fill={`${color}22`} stroke={color} strokeWidth={2} strokeOpacity={0.9} />
        {AXES.map((kpi, i) => {
          const a = (2 * Math.PI * i) / AXES.length
          const n = normalize(entity, summary, kpi)
          const dist = n * r
          const x = cx + dist * Math.sin(a)
          const y = cy - dist * Math.cos(a)
          return <circle key={i} cx={x} cy={y} r={4} fill={color} />
        })}
      </g>
    )
  }

  return (
    <div className={cStyles.radarWrap}>
      <svg width={320} height={320} style={{ overflow: 'visible' }}>
        {/* Background rings */}
        {[0.25, 0.5, 0.75, 1].map(f => (
          <polygon key={f}
            points={AXES.map((_, i) => {
              const a = (2 * Math.PI * i) / AXES.length
              return `${cx + r * f * Math.sin(a)},${cy - r * f * Math.cos(a)}`
            }).join(' ')}
            fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={1}
          />
        ))}
        {/* Axis lines */}
        {axisPoints.map(([x, y], i) => (
          <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        ))}
        {/* Axis labels */}
        {axisPoints.map(([x, y, a], i) => {
          const lx = cx + (r + 22) * Math.sin(a)
          const ly = cy - (r + 22) * Math.cos(a)
          return (
            <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
              fill="#94a3b8" fontSize={9} fontWeight={700}>
              {AXES[i].label.slice(0, 12)}
            </text>
          )
        })}
        {/* Entity polygons */}
        {entities.map((e, i) => entityPolygon(e, summaries[i], i))}
      </svg>
      {/* Legend */}
      <div className={cStyles.radarLegend}>
        {entities.map((e, i) => (
          <span key={i} style={{ color: COLORS[i % COLORS.length], fontSize: '0.75rem', fontWeight: 700 }}>
            ■ {e.name}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── KPI Table ─────────────────────────────────────────────────────────────────

function KpiTable({ entities, summaries }) {
  return (
    <div className={cStyles.tableWrap}>
      <table className={cStyles.table}>
        <thead>
          <tr>
            <th>Metric</th>
            {entities.map((e, i) => <th key={i}>{e.name}</th>)}
          </tr>
        </thead>
        <tbody>
          {KPIS.map(kpi => {
            const vals = entities.map((_, i) => summaries[i]?.[kpi.key] ?? null)
            // Find best
            let bestIdx = -1
            if (kpi.higher === 'more') {
              const nums = vals.map(v => typeof v === 'number' ? v : RISK_VALS[String(v||'').toUpperCase()] || 0)
              const mx = Math.max(...nums)
              if (mx > 0) bestIdx = nums.indexOf(mx)
            } else {
              const nums = vals.map(v => typeof v === 'number' ? v : RISK_VALS[String(v||'').toUpperCase()] || 0)
              const mn = Math.min(...nums.filter(n => n >= 0))
              if (mn < Infinity) bestIdx = nums.indexOf(mn)
            }
            return (
              <tr key={kpi.id}>
                <td className={cStyles.metricLabel}>{kpi.label}</td>
                {vals.map((v, i) => (
                  <td key={i} className={`${cStyles.metricVal} ${i === bestIdx ? cStyles.metricBest : ''}`}>
                    {v !== null ? kpi.fmt(v) : '—'}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Board overlap (shared relationships) ─────────────────────────────────────

function BoardOverlap({ reports }) {
  if (reports.length < 2) return null

  // Extract all entity names from sections
  const namesets = reports.map(r =>
    new Set((r.sections || []).flatMap(s =>
      (s.claims || []).map(c => (c.text || c || '').match(/[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+/g) || [])
    ).flat().filter(n => n.length > 3))
  )

  const overlaps = []
  for (let i = 0; i < reports.length; i++) {
    for (let j = i + 1; j < reports.length; j++) {
      const shared = [...namesets[i]].filter(n => namesets[j].has(n)).slice(0, 15)
      if (shared.length) {
        overlaps.push({ a: reports[i].entity_name, b: reports[j].entity_name, shared })
      }
    }
  }

  if (!overlaps.length) return null

  return (
    <div className={styles.panel}>
      <h2>Shared Entity References</h2>
      {overlaps.map((ov, i) => (
        <div key={i} className={cStyles.overlapRow}>
          <span className={cStyles.overlapPair}>{ov.a} ↔ {ov.b}</span>
          <div className={cStyles.overlapNames}>
            {ov.shared.map((n, j) => <span key={j} className={cStyles.overlapChip}>{n}</span>)}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ComparePage() {
  const [slots,    setSlots]    = useState([
    { name: 'Palantir Technologies', type: 'org',    ticker: 'PLTR' },
    { name: 'Anduril Industries',    type: 'org',    ticker: '' },
    { name: '',                      type: 'org',    ticker: '' },
  ])
  const [reports,  setReports]  = useState([])
  const [loading,  setLoading]  = useState([])
  const [activeTab, setActiveTab] = useState('radar')

  const summaries = reports.map(r => r?.summary || {})
  const loadedEntities = reports.map((r, i) => slots[i]).filter((_, i) => reports[i])

  const generate = async (idx) => {
    const slot = slots[idx]
    if (!slot.name.trim()) return
    setLoading(prev => { const a = [...prev]; a[idx] = true; return a })
    try {
      const params = new URLSearchParams({ entity_name: slot.name, entity_type: slot.type })
      if (slot.ticker) params.set('ticker', slot.ticker)
      const r = await fetch(`${API}/intelligence/generate?${params}`, { method: 'POST' })
      const data = r.ok ? await r.json() : null
      setReports(prev => {
        const a = [...prev]
        a[idx] = data
        return a
      })
    } catch(e) {
      console.error(e)
    } finally {
      setLoading(prev => { const a = [...prev]; a[idx] = false; return a })
    }
  }

  const generateAll = () => {
    slots.forEach((s, i) => { if (s.name.trim()) generate(i) })
  }

  const addSlot = () => {
    if (slots.length < 5) setSlots(s => [...s, { name: '', type: 'org', ticker: '' }])
  }

  const removeSlot = (idx) => {
    setSlots(s => s.filter((_, i) => i !== idx))
    setReports(r => r.filter((_, i) => i !== idx))
  }

  const COLORS = ['#818cf8', '#f97316', '#4ade80', '#fbbf24', '#f43f5e']

  const tabs = ['radar', 'table', 'overlap']

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p style={{ margin: '0 0 0.4rem', fontSize: '0.75rem', fontWeight: 700,
                    letterSpacing: '0.08em', textTransform: 'uppercase', color: '#818cf8' }}>
          Layer 1 v1.2 — Entity Comparison
        </p>
        <h1 style={{ margin: 0 }}>Compare Entities</h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', maxWidth: 640 }}>
          Side-by-side KPI comparison, radar chart, and shared-entity overlap for up to 5 entities.
        </p>
      </section>

      {/* Entity slots */}
      <div className={styles.panel}>
        <div className={cStyles.slotGrid}>
          {slots.map((slot, i) => (
            <div key={i} className={cStyles.slot} style={{ borderTopColor: COLORS[i % COLORS.length] }}>
              <div className={cStyles.slotHeader}>
                <span style={{ color: COLORS[i % COLORS.length], fontWeight: 800, fontSize: '0.8rem' }}>Entity {i + 1}</span>
                {i > 1 && <button className={cStyles.removeBtn} onClick={() => removeSlot(i)}>✕</button>}
              </div>
              <input
                className={styles.input}
                value={slot.name}
                onChange={e => {
                  const s = [...slots]; s[i] = { ...s[i], name: e.target.value }; setSlots(s)
                }}
                placeholder="Entity name…"
                onKeyDown={e => e.key === 'Enter' && generate(i)}
              />
              <input
                className={styles.input}
                value={slot.ticker}
                onChange={e => {
                  const s = [...slots]; s[i] = { ...s[i], ticker: e.target.value }; setSlots(s)
                }}
                placeholder="Ticker (optional)"
                style={{ marginTop: '0.4rem' }}
              />
              <select
                value={slot.type}
                onChange={e => {
                  const s = [...slots]; s[i] = { ...s[i], type: e.target.value }; setSlots(s)
                }}
                className={styles.input}
                style={{ marginTop: '0.4rem' }}
              >
                <option value="org">Organization</option>
                <option value="person">Person</option>
              </select>
              <button
                className={styles.btn}
                onClick={() => generate(i)}
                disabled={loading[i] || !slot.name.trim()}
                style={{ marginTop: '0.5rem', width: '100%' }}
              >
                {loading[i] ? 'Generating…' : reports[i] ? '✓ Reload' : 'Generate Report'}
              </button>
              {reports[i] && (
                <div style={{ marginTop: '0.4rem', fontSize: '0.72rem', color: '#4ade80', fontWeight: 700 }}>
                  ✓ {Object.keys(reports[i].summary || {}).length} KPIs loaded
                </div>
              )}
            </div>
          ))}
          {slots.length < 5 && (
            <button className={cStyles.addSlot} onClick={addSlot}>+ Add Entity</button>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem' }}>
          <button className={styles.btn} onClick={generateAll} disabled={loading.some(Boolean)}>
            {loading.some(Boolean) ? 'Generating…' : '⚡ Generate All'}
          </button>
          {loadedEntities.length > 0 && (
            <span style={{ fontSize: '0.8rem', color: '#4ade80', fontWeight: 700, alignSelf: 'center' }}>
              {loadedEntities.length} entities loaded
            </span>
          )}
        </div>
      </div>

      {/* Comparison views — only show when ≥2 reports loaded */}
      {loadedEntities.length >= 2 && (
        <>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: '0.35rem' }}>
            {tabs.map(t => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                style={{
                  background:   activeTab === t ? 'rgba(129,140,248,0.15)' : 'rgba(15,20,40,0.7)',
                  border:       `1px solid ${activeTab === t ? '#818cf8' : 'var(--line)'}`,
                  borderRadius: 8,
                  color:        activeTab === t ? '#c7d2fe' : 'var(--text-muted)',
                  cursor:       'pointer',
                  font:         'inherit',
                  fontSize:     '0.82rem',
                  fontWeight:   600,
                  padding:      '0.35rem 1rem',
                  textTransform: 'capitalize',
                }}
              >{t === 'radar' ? '📡 Radar' : t === 'table' ? '📊 KPI Table' : '🔗 Overlap'}</button>
            ))}
          </div>

          {activeTab === 'radar' && (
            <div className={styles.panel}>
              <h2>Radar Comparison</h2>
              <RadarChart entities={loadedEntities} summaries={summaries} />
            </div>
          )}

          {activeTab === 'table' && (
            <div className={styles.panel}>
              <h2>KPI Comparison Table</h2>
              <KpiTable entities={loadedEntities} summaries={summaries} />
            </div>
          )}

          {activeTab === 'overlap' && (
            <BoardOverlap reports={reports.filter(Boolean)} />
          )}
        </>
      )}

      {loadedEntities.length < 2 && loadedEntities.length > 0 && (
        <div className={styles.panel}>
          <p className={styles.empty}>
            Generate reports for at least 2 entities to see comparisons.
          </p>
        </div>
      )}
    </main>
  )
}
