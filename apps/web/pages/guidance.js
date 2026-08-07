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
      case 'excellent': return 'bg-green-500';
      case 'good': return 'bg-blue-500';
      case 'average': return 'bg-yellow-500';
      case 'poor': return 'bg-orange-500';
      case 'unreliable': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold">{data.company_name}</h3>
          <p className="text-sm text-gray-500">Management Credibility Score</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-blue-600">{data.overall_score}</div>
          <span className={`inline-block px-3 py-1 rounded-full text-white text-sm font-medium ${getTierColor(data.tier)}`}>
            {data.tier?.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Component Scores */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {Object.entries(data.component_scores || {}).map(([key, value]) => (
          <div key={key} className="text-center p-3 bg-gray-50 rounded">
            <div className="text-xs text-gray-500 mb-1">{key.replace(/_/g, ' ')}</div>
            <div className="text-lg font-semibold">{value}</div>
          </div>
        ))}
      </div>

      {/* Historical Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-4 bg-green-50 rounded">
          <div className="text-2xl font-bold text-green-600">{data.historical_stats?.beats || 0}</div>
          <div className="text-xs text-green-700">Beats</div>
        </div>
        <div className="text-center p-4 bg-blue-50 rounded">
          <div className="text-2xl font-bold text-blue-600">{data.historical_stats?.meets || 0}</div>
          <div className="text-xs text-blue-700">Meets</div>
        </div>
        <div className="text-center p-4 bg-red-50 rounded">
          <div className="text-2xl font-bold text-red-600">{data.historical_stats?.misses || 0}</div>
          <div className="text-xs text-red-700">Misses</div>
        </div>
      </div>

      {/* Rates */}
      <div className="flex gap-8 mb-6">
        <div>
          <span className="text-sm text-gray-500">Beat Rate:</span>
          <span className="ml-2 font-semibold">{data.historical_stats?.beat_rate}%</span>
        </div>
        <div>
          <span className="text-sm text-gray-500">Meet or Beat:</span>
          <span className="ml-2 font-semibold text-green-600">{data.historical_stats?.meet_or_beat_rate}%</span>
        </div>
      </div>

      {/* Flags */}
      <div className="grid grid-cols-2 gap-4">
        {data.flags?.green?.length > 0 && (
          <div className="p-3 bg-green-50 rounded">
            <div className="text-sm font-medium text-green-800 mb-2">Positives</div>
            {data.flags.green.map((flag, i) => (
              <div key={i} className="text-sm text-green-700">+ {flag}</div>
            ))}
          </div>
        )}
        {data.flags?.red?.length > 0 && (
          <div className="p-3 bg-red-50 rounded">
            <div className="text-sm font-medium text-red-800 mb-2">Concerns</div>
            {data.flags.red.map((flag, i) => (
              <div key={i} className="text-sm text-red-700">- {flag}</div>
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
    if (outcome === 'beat' || outcome === 'significantly_beat') return 'bg-green-100 text-green-700';
    if (outcome === 'missed' || outcome === 'significantly_missed') return 'bg-red-100 text-red-700';
    return 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="p-4 border-b">
        <h3 className="font-semibold">Guidance History</h3>
      </div>
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left">Period</th>
            <th className="px-4 py-3 text-right">Guidance Low</th>
            <th className="px-4 py-3 text-right">Guidance High</th>
            <th className="px-4 py-3 text-right">Actual</th>
            <th className="px-4 py-3 text-right">vs Mid</th>
            <th className="px-4 py-3 text-center">Outcome</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.history.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3">{row.fiscal_period} {row.fiscal_year}</td>
              <td className="px-4 py-3 text-right">${row.guidance?.low?.toFixed(2)}</td>
              <td className="px-4 py-3 text-right">${row.guidance?.high?.toFixed(2)}</td>
              <td className="px-4 py-3 text-right font-medium">${row.actual?.toFixed(2)}</td>
              <td className={`px-4 py-3 text-right ${row.vs_midpoint_pct > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {row.vs_midpoint_pct > 0 ? '+' : ''}{row.vs_midpoint_pct}%
              </td>
              <td className="px-4 py-3 text-center">
                <span className={`px-2 py-1 rounded text-xs font-medium ${getOutcomeColor(row.outcome)}`}>
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

      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Guidance vs Actual Tracking</h1>
            <p className="text-sm text-gray-500">Management credibility scoring and guidance history</p>
          </div>
        </header>

        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex gap-4 items-center">
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="px-4 py-2 border rounded-lg w-32"
                placeholder="Ticker"
              />
              <button
                onClick={fetchData}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>
              <div className="flex gap-2 ml-4">
                {['NVDA', 'AAPL', 'MSFT', 'TSLA', 'META', 'INTC'].map(t => (
                  <button
                    key={t}
                    onClick={() => setTicker(t)}
                    className={`px-3 py-1 text-sm rounded-full border ${ticker === t ? 'bg-blue-100 border-blue-500' : 'border-gray-300'}`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
          {error && <div className="p-4 bg-red-50 text-red-700 rounded-lg">{error}</div>}
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading...</div>
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
