/**
 * Guidance vs Actual Tracking Page (Band B #22)
 *
 * Features:
 * - Management guidance lookup
 * - Guidance vs actual comparison
 * - Credibility scoring
 * - Revision history
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Credibility Card ──────────────────────────────────────────────────────────

function CredibilityCard({ data }) {
  if (!data) return null;

  const getTierColor = (tier) => {
    switch (tier) {
      case 'excellent': return 'badge-green';
      case 'good': return 'badge-brand';
      case 'average': return 'badge-amber';
      case 'poor': return 'badge-amber';
      case 'unreliable': return 'badge-red';
      default: return 'badge-gray';
    }
  };

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h3 style={{ color: 'var(--text)', fontSize: '1.05rem', fontWeight: 800, margin: 0 }}>{data.company_name}</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '0.25rem 0 0' }}>Management Credibility Score</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: 'var(--brand)', fontSize: '2rem', fontWeight: 900, lineHeight: 1 }}>{data.overall_score}</div>
          <span className={`badge ${getTierColor(data.tier)}`}>
            {data.tier?.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Component Scores */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
        {Object.entries(data.component_scores || {}).map(([key, value]) => (
          <div key={key} style={{ textAlign: 'center', padding: '0.8rem', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--line)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '0.25rem', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</div>
            <div style={{ color: 'var(--text)', fontSize: '1rem', fontWeight: 800 }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Historical Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(16,185,129,0.10)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ color: '#22c55e', fontSize: '1.5rem', fontWeight: 900 }}>{data.historical_stats?.beats || 0}</div>
          <div style={{ color: '#86efac', fontSize: '0.75rem' }}>Beats</div>
        </div>
        <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.28)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ color: '#818cf8', fontSize: '1.5rem', fontWeight: 900 }}>{data.historical_stats?.meets || 0}</div>
          <div style={{ color: '#c4b5fd', fontSize: '0.75rem' }}>Meets</div>
        </div>
        <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(239,68,68,0.10)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ color: '#f87171', fontSize: '1.5rem', fontWeight: 900 }}>{data.historical_stats?.misses || 0}</div>
          <div style={{ color: '#fca5a5', fontSize: '0.75rem' }}>Misses</div>
        </div>
      </div>

      {/* Rates */}
      <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Beat Rate:</span>
          <span style={{ color: 'var(--text)', marginLeft: 8, fontWeight: 800 }}>{data.historical_stats?.beat_rate}%</span>
        </div>
        <div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Meet or Beat:</span>
          <span style={{ color: '#22c55e', marginLeft: 8, fontWeight: 800 }}>{data.historical_stats?.meet_or_beat_rate}%</span>
        </div>
      </div>

      {/* Flags */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
        {data.flags?.green?.length > 0 && (
          <div style={{ padding: '0.9rem', background: 'rgba(16,185,129,0.10)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ color: '#86efac', fontSize: '0.85rem', fontWeight: 800, marginBottom: '0.5rem' }}>Positives</div>
            {data.flags.green.map((flag, i) => (
              <div key={i} style={{ color: '#bbf7d0', fontSize: '0.8rem' }}>+ {flag}</div>
            ))}
          </div>
        )}
        {data.flags?.red?.length > 0 && (
          <div style={{ padding: '0.9rem', background: 'rgba(239,68,68,0.10)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ color: '#fca5a5', fontSize: '0.85rem', fontWeight: 800, marginBottom: '0.5rem' }}>Concerns</div>
            {data.flags.red.map((flag, i) => (
              <div key={i} style={{ color: '#fecaca', fontSize: '0.8rem' }}>- {flag}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── History Table ─────────────────────────────────────────────────────────────

function HistoryTable({ data }) {
  if (!data?.history?.length) return null;

  const getOutcomeColor = (outcome) => {
    if (outcome === 'beat' || outcome === 'significantly_beat') return 'badge-green';
    if (outcome === 'missed' || outcome === 'significantly_missed') return 'badge-red';
    return 'badge-gray';
  };

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--line)' }}>
        <h3 style={{ color: 'var(--text)', fontSize: '0.95rem', fontWeight: 800, margin: 0 }}>Guidance History</h3>
      </div>
      <table style={{ width: '100%', fontSize: '0.78rem', borderCollapse: 'collapse' }}>
        <thead style={{ background: 'rgba(255,255,255,0.03)' }}>
          <tr>
            <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 700 }}>Period</th>
            <th style={{ padding: '0.75rem 1rem', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 700 }}>Guidance Low</th>
            <th style={{ padding: '0.75rem 1rem', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 700 }}>Guidance High</th>
            <th style={{ padding: '0.75rem 1rem', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 700 }}>Actual</th>
            <th style={{ padding: '0.75rem 1rem', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 700 }}>vs Mid</th>
            <th style={{ padding: '0.75rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontWeight: 700 }}>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {data.history.map((row, i) => (
            <tr key={i} style={{ borderTop: '1px solid var(--line)' }}>
              <td style={{ padding: '0.75rem 1rem', color: 'var(--text)' }}>{row.fiscal_period} {row.fiscal_year}</td>
              <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)', textAlign: 'right' }}>${row.guidance?.low?.toFixed(2)}</td>
              <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)', textAlign: 'right' }}>${row.guidance?.high?.toFixed(2)}</td>
              <td style={{ padding: '0.75rem 1rem', color: 'var(--text)', textAlign: 'right', fontWeight: 700 }}>${row.actual?.toFixed(2)}</td>
              <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: row.vs_midpoint_pct > 0 ? '#22c55e' : '#f87171' }}>
                {row.vs_midpoint_pct > 0 ? '+' : ''}{row.vs_midpoint_pct}%
              </td>
              <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                <span className={`badge ${getOutcomeColor(row.outcome)}`}>
                  {row.outcome}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function GuidancePage() {
  const [ticker, setTicker] = useState('NVDA');
  const [credibilityData, setCredibilityData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [cred, hist] = await Promise.all([
        fetch(`${API_BASE}/guidance/credibility?ticker=${ticker}`).then(r => r.json()),
        fetch(`${API_BASE}/guidance/history?ticker=${ticker}&quarters=12`).then(r => r.json()),
      ]);
      setCredibilityData(cred);
      setHistoryData(hist);
    } catch (err) {
      setError('Failed to fetch guidance data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <>
      <Head>
        <title>Guidance Tracking | Finance Intelligence</title>
      </Head>

      <div className="page-wrap">
        <header className="page-header">
          <div>
            <h1 className="page-title">Guidance vs Actual Tracking</h1>
            <p className="page-sub">Management credibility scoring and guidance history</p>
          </div>
        </header>

        <div className="card" style={{ padding: '1rem 1.25rem' }}>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="inp"
                placeholder="Ticker"
                style={{ width: 140 }}
              />
              <button
                onClick={fetchData}
                disabled={loading}
                className="btn btn-primary"
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {['NVDA', 'AAPL', 'MSFT', 'TSLA', 'META', 'INTC'].map(t => (
                  <button
                    key={t}
                    onClick={() => setTicker(t)}
                    className={`btn ${ticker === t ? 'btn-primary' : 'btn-ghost'} btn-xs`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
        </div>

        <main style={{ display: 'grid', gap: '1rem' }}>
          {error && <div className="badge badge-red" style={{ padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)' }}>{error}</div>}
          {loading ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading...</div>
          ) : (
            <>
              <CredibilityCard data={credibilityData} />
              <HistoryTable data={historyData} />
            </>
          )}
        </main>
      </div>
    </>
  );
}
