import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/router'
import styles from '../src/styles/Page.module.css'
import { getApiBaseUrl , apiFetch } from '../lib/api'

const API = getApiBaseUrl()

// ── Material change severity colors ─────────────────────────────────────────────

const SEVERITY_COLORS = {
  high: { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
  medium: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
  low: { bg: '#f3f4f6', border: '#9ca3af', text: '#374151' },
  info: { bg: '#f9fafb', border: '#e5e7eb', text: '#6b7280' },
}

// ── Format helpers ─────────────────────────────────────────────────────────────

function formatValue(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
    if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(1)}K`
    return value.toFixed(2)
  }
  return String(value)
}

function formatDelta(delta, deltaPct) {
  if (delta === null || delta === undefined) return ''
  const sign = delta >= 0 ? '+' : ''
  const pct = deltaPct ? ` (${sign}${deltaPct}%)` : ''
  return `${sign}${formatValue(delta)}${pct}`
}

// ── Filing History Dropdown ─────────────────────────────────────────────────────

function FilingSelector({ ticker, formType, onSelect, label }) {
  const [filings, setFilings] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    apiFetch(`/filings/history?ticker=${ticker}&form_type=${formType}&limit=10`)
      .then(r => r.json())
      .then(data => {
        setFilings(data.filings || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [ticker, formType])

  return (
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
        {label}
      </label>
      <select
        onChange={(e) => onSelect(e.target.value)}
        disabled={loading || !filings.length}
        style={{
          width: '100%',
          padding: '0.75rem',
          borderRadius: '8px',
          border: '1px solid #e5e7eb',
          fontSize: '1rem',
          background: 'white',
        }}
      >
        <option value="">Select filing...</option>
        {filings.map((f, i) => (
          <option key={i} value={f.filing_date}>
            {f.form} — {f.filing_date} ({f.accession?.slice(0, 15)}...)
          </option>
        ))}
      </select>
    </div>
  )
}

// ── Material Changes Panel ─────────────────────────────────────────────────────

function MaterialChangesPanel({ changes }) {
  if (!changes || changes.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
        No material changes detected
      </div>
    )
  }

  return (
    <div>
      {changes.map((change, i) => {
        const colors = SEVERITY_COLORS[change.materiality] || SEVERITY_COLORS.info
        return (
          <div
            key={i}
            style={{
              padding: '1rem',
              marginBottom: '0.75rem',
              background: colors.bg,
              borderLeft: `4px solid ${colors.border}`,
              borderRadius: '4px',
            }}
          >
            <div style={{ fontWeight: 600, color: colors.text, marginBottom: '0.25rem' }}>
              {change.field.replace(/_/g, ' ').replace(/keyword /i, '')}
            </div>
            <div style={{ fontSize: '0.875rem', color: '#374151' }}>
              {change.context || `${formatValue(change.old_value)} → ${formatValue(change.new_value)}`}
            </div>
            {change.delta_pct && (
              <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: change.delta_pct > 0 ? '#059669' : '#dc2626' }}>
                {change.delta_pct > 0 ? '+' : ''}{change.delta_pct}% change
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Financial Changes Table ─────────────────────────────────────────────────────

function FinancialChangesTable({ changes }) {
  if (!changes || changes.length === 0) return null

  // Group by section
  const sections = {}
  changes.forEach(c => {
    if (!sections[c.section]) sections[c.section] = []
    sections[c.section].push(c)
  })

  return (
    <div>
      {Object.entries(sections).map(([section, items]) => (
        <div key={section} style={{ marginBottom: '2rem' }}>
          <h4 style={{
            fontSize: '0.875rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            color: '#6b7280',
            marginBottom: '0.75rem',
            letterSpacing: '0.05em',
          }}>
            {section.replace(/_/g, ' ')}
          </h4>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600 }}>Metric</th>
                <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600 }}>Prior</th>
                <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600 }}>Current</th>
                <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600 }}>Change</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c, i) => {
                const colors = SEVERITY_COLORS[c.materiality] || SEVERITY_COLORS.info
                return (
                  <tr
                    key={i}
                    style={{
                      borderBottom: '1px solid #e5e7eb',
                      background: c.materiality === 'high' ? colors.bg : 'transparent',
                    }}
                  >
                    <td style={{ padding: '0.75rem', fontWeight: c.materiality === 'high' ? 600 : 400 }}>
                      {c.field.replace(/_/g, ' ')}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace' }}>
                      {formatValue(c.old_value)}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace' }}>
                      {formatValue(c.new_value)}
                    </td>
                    <td style={{
                      padding: '0.75rem',
                      textAlign: 'right',
                      fontFamily: 'monospace',
                      color: c.delta > 0 ? '#059669' : c.delta < 0 ? '#dc2626' : '#6b7280',
                    }}>
                      {formatDelta(c.delta, c.delta_pct)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

// ── Narrative Changes Panel ─────────────────────────────────────────────────────

function NarrativeChangesPanel({ changes }) {
  if (!changes || changes.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
        No narrative changes detected
      </div>
    )
  }

  return (
    <div>
      {changes.map((change, i) => (
        <div
          key={i}
          style={{
            padding: '1rem',
            marginBottom: '1rem',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        >
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '0.75rem',
          }}>
            <h4 style={{ fontWeight: 600, margin: 0 }}>
              {change.section.replace(/_/g, ' ')}
            </h4>
            <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
              {(change.similarity_ratio * 100).toFixed(1)}% similar
            </div>
          </div>
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem' }}>
            <div style={{
              padding: '0.5rem 1rem',
              background: '#dcfce7',
              borderRadius: '4px',
              color: '#166534',
            }}>
              +{change.added_lines} lines added
            </div>
            <div style={{
              padding: '0.5rem 1rem',
              background: '#fee2e2',
              borderRadius: '4px',
              color: '#991b1b',
            }}>
              -{change.removed_lines} lines removed
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Summary Stats ─────────────────────────────────────────────────────────────

function SummaryStats({ summary }) {
  if (!summary) return null

  const stats = [
    { label: 'Financial Changes', value: summary.total_financial_changes || 0, icon: '📊' },
    { label: 'High Materiality', value: summary.high_materiality_changes || 0, icon: '🔴' },
    { label: 'Medium Materiality', value: summary.medium_materiality_changes || 0, icon: '🟡' },
    { label: 'Sections Changed', value: summary.narrative_sections_changed || 0, icon: '📝' },
    { label: 'Lines Added', value: summary.total_lines_added || 0, icon: '➕' },
    { label: 'Lines Removed', value: summary.total_lines_removed || 0, icon: '➖' },
  ]

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
      gap: '1rem',
      marginBottom: '2rem',
    }}>
      {stats.map((stat, i) => (
        <div
          key={i}
          style={{
            padding: '1rem',
            background: '#f9fafb',
            borderRadius: '8px',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>{stat.icon}</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{stat.value}</div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{stat.label}</div>
        </div>
      ))}
    </div>
  )
}

// ── Main Page Component ─────────────────────────────────────────────────────────

export default function FilingComparePage() {
  const router = useRouter()
  const { ticker: queryTicker } = router.query

  const [ticker, setTicker] = useState('')
  const [formType, setFormType] = useState('10-K')
  const [basePeriod, setBasePeriod] = useState('')
  const [comparePeriod, setComparePeriod] = useState('')
  const [diffResult, setDiffResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')

  useEffect(() => {
    if (queryTicker && !ticker) {
      setTicker(queryTicker.toUpperCase())
    }
  }, [queryTicker, ticker])

  const runComparison = useCallback(async () => {
    if (!ticker) {
      setError('Please enter a ticker symbol')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        ticker: ticker.toUpperCase(),
        form_type: formType,
      })
      if (basePeriod) params.append('base_period', basePeriod)
      if (comparePeriod) params.append('compare_period', comparePeriod)

      const res = await apiFetch(`/filings/compare?${params}`)
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate comparison')
      }

      setDiffResult(data)
    } catch (e) {
      setError(e.message)
      setDiffResult(null)
    } finally {
      setLoading(false)
    }
  }, [ticker, formType, basePeriod, comparePeriod])

  const downloadExcel = async () => {
    const params = new URLSearchParams({
      ticker: ticker.toUpperCase(),
      form_type: formType,
    })
    if (basePeriod) params.append('base_period', basePeriod)
    if (comparePeriod) params.append('compare_period', comparePeriod)

    window.open(`${API}/filings/compare/excel?${params}`, '_blank')
  }

  const viewRedline = async () => {
    const params = new URLSearchParams({
      ticker: ticker.toUpperCase(),
      form_type: formType,
    })
    if (basePeriod) params.append('base_period', basePeriod)
    if (comparePeriod) params.append('compare_period', comparePeriod)

    window.open(`${API}/filings/compare/redline?${params}`, '_blank')
  }

  return (
    <div className={styles.pageWrap}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        {/* Header */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            Filing Comparison
          </h1>
          <p style={{ color: '#6b7280' }}>
            Compare SEC filings to identify material changes between periods
          </p>
        </div>

        {/* Controls */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem',
          padding: '1.5rem',
          background: '#f9fafb',
          borderRadius: '12px',
        }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
              Ticker
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="NVDA"
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                fontSize: '1rem',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
              Form Type
            </label>
            <select
              value={formType}
              onChange={(e) => setFormType(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                fontSize: '1rem',
                background: 'white',
              }}
            >
              <option value="10-K">10-K (Annual)</option>
              <option value="10-Q">10-Q (Quarterly)</option>
              <option value="8-K">8-K (Current)</option>
              <option value="DEF 14A">DEF 14A (Proxy)</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              onClick={runComparison}
              disabled={loading || !ticker}
              style={{
                width: '100%',
                padding: '0.75rem 1.5rem',
                background: loading ? '#9ca3af' : '#4f46e5',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Comparing...' : 'Compare Filings'}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: '1rem',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            color: '#991b1b',
            marginBottom: '1rem',
          }}>
            {error}
          </div>
        )}

        {/* Results */}
        {diffResult && (
          <div>
            {/* Company Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1.5rem',
            }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {diffResult.company_name} ({diffResult.ticker})
                </h2>
                <div style={{ color: '#6b7280' }}>
                  {diffResult.form_type}: {diffResult.summary?.compare_period} → {diffResult.summary?.base_period}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  onClick={viewRedline}
                  style={{
                    padding: '0.5rem 1rem',
                    background: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    cursor: 'pointer',
                  }}
                >
                  View Redline
                </button>
                <button
                  onClick={downloadExcel}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#059669',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    cursor: 'pointer',
                  }}
                >
                  Download Excel
                </button>
              </div>
            </div>

            {/* Summary Stats */}
            <SummaryStats summary={diffResult.summary} />

            {/* Tabs */}
            <div style={{
              display: 'flex',
              gap: '0.5rem',
              marginBottom: '1.5rem',
              borderBottom: '1px solid #e5e7eb',
              paddingBottom: '0.5rem',
            }}>
              {['summary', 'financial', 'narrative', 'material'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    padding: '0.5rem 1rem',
                    background: activeTab === tab ? '#4f46e5' : 'transparent',
                    color: activeTab === tab ? 'white' : '#6b7280',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {tab === 'material' ? 'Material Changes' : tab}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div style={{
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
              padding: '1.5rem',
            }}>
              {activeTab === 'summary' && (
                <div>
                  <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
                    Largest Changes
                  </h3>
                  {diffResult.summary?.largest_changes?.map((change, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '0.75rem',
                        borderBottom: '1px solid #f3f4f6',
                      }}
                    >
                      <span>{change.field.replace(/_/g, ' ')}</span>
                      <span style={{
                        fontWeight: 600,
                        color: change.delta_pct > 0 ? '#059669' : '#dc2626',
                      }}>
                        {change.delta_pct > 0 ? '+' : ''}{change.delta_pct}%
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'financial' && (
                <FinancialChangesTable changes={diffResult.financial_changes} />
              )}

              {activeTab === 'narrative' && (
                <NarrativeChangesPanel changes={diffResult.narrative_changes} />
              )}

              {activeTab === 'material' && (
                <MaterialChangesPanel changes={diffResult.material_changes} />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
