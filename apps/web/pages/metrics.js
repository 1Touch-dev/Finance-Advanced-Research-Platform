import { useEffect, useState, useRef } from 'react'
import { getApiBaseUrl } from '../lib/api'

const POLL_INTERVAL = 5000
const HISTORY_SIZE = 60

function StatusDot({ ok }) {
  return (
    <span style={{
      display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
      background: ok ? '#22c55e' : '#ef4444', marginRight: 8,
    }} />
  )
}

function Card({ title, children }) {
  return (
    <div style={{
      background: '#1e1e2e', borderRadius: 12, padding: '20px 24px',
      border: '1px solid #2e2e4e', flex: '1 1 320px', minWidth: 300,
    }}>
      <h3 style={{ margin: '0 0 14px', fontSize: 14, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 1 }}>{title}</h3>
      {children}
    </div>
  )
}

function Metric({ label, value, unit, color }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <span style={{ color: '#94a3b8', fontSize: 13 }}>{label}</span>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || '#e2e8f0', lineHeight: 1.2 }}>
        {value}<span style={{ fontSize: 14, fontWeight: 400, color: '#64748b', marginLeft: 4 }}>{unit}</span>
      </div>
    </div>
  )
}

function MiniBar({ label, value, max, color }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8', marginBottom: 3 }}>
        <span>{label}</span><span>{value}</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: '#2e2e4e' }}>
        <div style={{ height: 6, borderRadius: 3, background: color || '#6366f1', width: `${pct}%`, transition: 'width 0.5s' }} />
      </div>
    </div>
  )
}

function SparkLine({ data, color, height = 40, label }) {
  if (!data || data.length < 2) return <div style={{ height, color: '#475569', fontSize: 12 }}>Collecting data...</div>
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const w = 260
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - ((v - min) / range) * (height - 4)
    return `${x},${y}`
  }).join(' ')
  return (
    <div>
      {label && <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>{label}</div>}
      <svg width={w} height={height} style={{ display: 'block' }}>
        <polyline points={points} fill="none" stroke={color || '#6366f1'} strokeWidth="2" strokeLinejoin="round" />
      </svg>
    </div>
  )
}

export default function MetricsDashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const latencyHistory = useRef([])
  const requestHistory = useRef([])
  const prevCounters = useRef({})

  useEffect(() => {
    let active = true
    async function poll() {
      try {
        const resp = await fetch(`${getApiBaseUrl()}/health/rag`)
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const json = await resp.json()
        if (active) {
          setData(json)
          setError(null)
          setLastUpdate(new Date())

          const hist = json.metrics?.histograms?.retrieval_latency_ms
          if (hist) {
            latencyHistory.current = [...latencyHistory.current.slice(-(HISTORY_SIZE - 1)), hist.p50]
          }
          const total = Object.entries(json.metrics?.counters || {})
            .filter(([k]) => k.startsWith('rag_retrievals_total'))
            .reduce((s, [, v]) => s + v, 0)
          const prev = prevCounters.current.total || 0
          requestHistory.current = [...requestHistory.current.slice(-(HISTORY_SIZE - 1)), total - prev]
          prevCounters.current.total = total
        }
      } catch (e) {
        if (active) setError(e.message)
      }
    }
    poll()
    const id = setInterval(poll, POLL_INTERVAL)
    return () => { active = false; clearInterval(id) }
  }, [])

  const counters = data?.metrics?.counters || {}
  const histograms = data?.metrics?.histograms || {}
  const latency = histograms.retrieval_latency_ms || {}
  const totalRetrievals = Object.entries(counters)
    .filter(([k]) => k.startsWith('rag_retrievals_total'))
    .reduce((s, [, v]) => s + v, 0)
  const fallbacks = counters['rag_fallback_total'] || 0
  const reranks = Object.entries(counters).filter(([k]) => k.startsWith('rag_rerank_active')).reduce((s, [, v]) => s + v, 0)
  const guardrailBlocks = Object.entries(counters).filter(([k]) => k.startsWith('rag_guardrail_block')).reduce((s, [, v]) => s + v, 0)

  const modeBreakdown = {}
  Object.entries(counters).filter(([k]) => k.startsWith('rag_retrievals_total')).forEach(([k, v]) => {
    const match = k.match(/mode=(\w+)/)
    if (match) modeBreakdown[match[1]] = (modeBreakdown[match[1]] || 0) + v
  })

  return (
    <div style={{ minHeight: '100vh', background: '#0f0f1a', color: '#e2e8f0', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', padding: '32px 40px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>RAG Pipeline Metrics</h1>
          <p style={{ margin: '6px 0 0', color: '#64748b', fontSize: 13 }}>
            Live · polling every {POLL_INTERVAL / 1000}s
            {lastUpdate && <span> · updated {lastUpdate.toLocaleTimeString()}</span>}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <StatusDot ok={!error && data?.status === 'ok'} />
          <span style={{ fontSize: 13, color: error ? '#ef4444' : '#22c55e' }}>
            {error ? `Error: ${error}` : 'Connected'}
          </span>
        </div>
      </div>

      {/* Components Status */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <Card title="System Components">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 24px' }}>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Embeddings</div>
              <div style={{ fontSize: 14, color: '#e2e8f0' }}>
                {data?.components?.embeddings?.provider || '—'}
                {data?.components?.embeddings?.dim && <span style={{ color: '#6366f1' }}> ({data.components.embeddings.dim}d)</span>}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Vector Backend</div>
              <div style={{ fontSize: 14, color: '#e2e8f0' }}>{data?.components?.vector_backend || '—'}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Reranker</div>
              <div style={{ fontSize: 14, color: data?.components?.reranker?.active ? '#22c55e' : '#f59e0b' }}>
                {data?.components?.reranker?.active ? 'Active' : 'Inactive'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Prometheus</div>
              <div style={{ fontSize: 14, color: data?.metrics?.prometheus ? '#22c55e' : '#64748b' }}>
                {data?.metrics?.prometheus ? 'Exporting' : 'In-memory only'}
              </div>
            </div>
          </div>
        </Card>

        <Card title="Retrieval Counters">
          <Metric label="Total Retrievals" value={totalRetrievals} color="#6366f1" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div>
              <div style={{ fontSize: 22, fontWeight: 600, color: '#f59e0b' }}>{fallbacks}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>Fallbacks</div>
            </div>
            <div>
              <div style={{ fontSize: 22, fontWeight: 600, color: '#22c55e' }}>{reranks}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>Reranks</div>
            </div>
            <div>
              <div style={{ fontSize: 22, fontWeight: 600, color: '#ef4444' }}>{guardrailBlocks}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>Blocked</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Latency & Throughput */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <Card title="Retrieval Latency">
          <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
            <Metric label="p50" value={latency.p50?.toFixed(1) ?? '—'} unit="ms" color="#22c55e" />
            <Metric label="p95" value={latency.p95?.toFixed(1) ?? '—'} unit="ms" color="#f59e0b" />
            <Metric label="Max" value={latency.max?.toFixed(1) ?? '—'} unit="ms" color="#ef4444" />
          </div>
          <SparkLine data={latencyHistory.current} color="#6366f1" label="p50 latency over time" />
        </Card>

        <Card title="Requests / Interval">
          <SparkLine data={requestHistory.current} color="#22c55e" height={50} label="New retrievals per poll" />
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>Mode Breakdown</div>
            {Object.entries(modeBreakdown).map(([mode, count]) => (
              <MiniBar key={mode} label={mode} value={count} max={totalRetrievals || 1}
                color={mode === 'hybrid' ? '#6366f1' : mode === 'vector' ? '#22c55e' : '#f59e0b'} />
            ))}
            {Object.keys(modeBreakdown).length === 0 && <div style={{ fontSize: 12, color: '#475569' }}>No retrievals yet</div>}
          </div>
        </Card>
      </div>

      {/* Guardrails */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <Card title="Guardrail Activity">
          {Object.entries(counters).filter(([k]) => k.startsWith('rag_guardrail_block')).length > 0 ? (
            Object.entries(counters).filter(([k]) => k.startsWith('rag_guardrail_block')).map(([k, v]) => {
              const stage = k.match(/stage=(\w+)/)?.[1] || k
              return <MiniBar key={k} label={stage} value={v} max={totalRetrievals || 1} color="#ef4444" />
            })
          ) : (
            <div style={{ color: '#22c55e', fontSize: 14 }}>No blocks recorded — all retrievals clean</div>
          )}
        </Card>

        <Card title="Quality Classifier">
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 8 }}>
            Model trained on 303 samples (24 real + 280 synthetic)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <div style={{ fontSize: 11, color: '#64748b' }}>Version</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#6366f1' }}>v1-n303</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b' }}>F1 Score</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#f59e0b' }}>0.387</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b' }}>Accuracy</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#22c55e' }}>0.689</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b' }}>Synthetic %</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#94a3b8' }}>92.4%</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Raw Prometheus link */}
      <div style={{ marginTop: 16, padding: 16, background: '#1a1a2e', borderRadius: 8, border: '1px solid #2e2e4e' }}>
        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>External scrape endpoint</div>
        <code style={{ fontSize: 13, color: '#6366f1' }}>{typeof window !== 'undefined' ? `${getApiBaseUrl()}/metrics/` : '/metrics/'}</code>
        <span style={{ fontSize: 12, color: '#475569', marginLeft: 12 }}>Compatible with Prometheus / Grafana / Datadog agent</span>
      </div>
    </div>
  )
}
