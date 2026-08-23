/**
 * Consensus & Earnings Analysis Page (Band B #19-#21, #23)
 *
 * Features:
 * - Point-in-time consensus snapshots
 * - Consensus momentum and revisions
 * - Estimate dispersion analysis
 * - Earnings surprise history
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Consensus Snapshot Card ───────────────────────────────────────────────────

function ConsensusCard({ data }) {
  if (!data) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">

      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">{data.ticker} Consensus</h3>
          <p className="text-sm text-gray-500">
            {data.estimate_type.toUpperCase()} - FY{data.fiscal_year}
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-blue-600">
            ${data.consensus?.mean?.toFixed(2)}
          </div>
          <div className="text-sm text-gray-500">Mean Estimate</div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="text-center p-3 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">High</div>
          <div className="font-semibold">${data.consensus?.high?.toFixed(2)}</div>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">Low</div>
          <div className="font-semibold">${data.consensus?.low?.toFixed(2)}</div>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">Median</div>
          <div className="font-semibold">${data.consensus?.median?.toFixed(2)}</div>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">Analysts</div>
          <div className="font-semibold">{data.num_analysts}</div>
        </div>
      </div>

      <div className="text-xs text-gray-400">
        As of: {new Date(data.as_of_date).toLocaleDateString()}
      </div>
    </div>
  );
}

// ── Momentum Panel ────────────────────────────────────────────────────────────

function MomentumPanel({ data }) {
  if (!data) return null;

  const getTrendColor = (trend) => {
    if (trend?.includes('up')) return 'text-green-600';
    if (trend?.includes('down')) return 'text-red-600';
    return 'text-gray-600';
  };

  const getTrendIcon = (trend) => {
    if (trend?.includes('accelerating_up')) return '⬆️⬆️';
    if (trend?.includes('up')) return '⬆️';
    if (trend?.includes('accelerating_down')) return '⬇️⬇️';
    if (trend?.includes('down')) return '⬇️';
    return '➡️';
  };

  const getMomentumColor = (val) => {
    if (val > 0) return 'text-green-600 bg-green-50';
    if (val < 0) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Consensus Momentum</h3>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{getTrendIcon(data.trend)}</span>
          <span className={`text-xl font-semibold ${getTrendColor(data.trend)}`}>
            {data.trend?.replace(/_/g, ' ')}
          </span>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-500">Signal Strength</div>
          <div className="flex items-center gap-2">
            <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500"
                style={{ width: `${data.signal_strength}%` }}
              />
            </div>
            <span className="text-sm font-medium">{data.signal_strength?.toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className={`p-4 rounded-lg ${getMomentumColor(data.momentum?.['7d'])}`}>
          <div className="text-sm opacity-75">7-Day</div>
          <div className="text-xl font-bold">
            {data.momentum?.['7d'] > 0 ? '+' : ''}{data.momentum?.['7d']?.toFixed(2)}%
          </div>
        </div>
        <div className={`p-4 rounded-lg ${getMomentumColor(data.momentum?.['30d'])}`}>
          <div className="text-sm opacity-75">30-Day</div>
          <div className="text-xl font-bold">
            {data.momentum?.['30d'] > 0 ? '+' : ''}{data.momentum?.['30d']?.toFixed(2)}%
          </div>
        </div>
        <div className={`p-4 rounded-lg ${getMomentumColor(data.momentum?.['90d'])}`}>
          <div className="text-sm opacity-75">90-Day</div>
          <div className="text-xl font-bold">
            {data.momentum?.['90d'] > 0 ? '+' : ''}{data.momentum?.['90d']?.toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Revisions Up (30d):</span>
            <span className="ml-2 text-green-600 font-medium">{data.revisions?.up_30d}</span>
          </div>
          <div>
            <span className="text-gray-500">Revisions Down (30d):</span>
            <span className="ml-2 text-red-600 font-medium">{data.revisions?.down_30d}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Dispersion Panel ──────────────────────────────────────────────────────────

function DispersionPanel({ data }) {
  if (!data) return null;

  const getDispersionColor = (level) => {
    switch (level) {
      case 'low': return 'bg-green-100 text-green-700';
      case 'moderate': return 'bg-yellow-100 text-yellow-700';
      case 'high': return 'bg-orange-100 text-orange-700';
      case 'extreme': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold">Estimate Dispersion</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getDispersionColor(data.dispersion_level)}`}>
          {data.dispersion_level}
        </span>
      </div>

      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-500">Uncertainty Score</span>
          <span className="font-medium">{data.uncertainty_score?.toFixed(0)}/100</span>
        </div>
        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${
              data.uncertainty_score > 60 ? 'bg-red-500' :
              data.uncertainty_score > 30 ? 'bg-yellow-500' :
              'bg-green-500'
            }`}
            style={{ width: `${data.uncertainty_score}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Range</div>
          <div className="font-semibold">${data.metrics?.range?.toFixed(2)}</div>
          <div className="text-xs text-gray-400">{data.metrics?.range_pct?.toFixed(1)}% of mean</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Std Dev</div>
          <div className="font-semibold">${data.metrics?.std_dev?.toFixed(3)}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">IQR</div>
          <div className="font-semibold">${data.metrics?.interquartile_range?.toFixed(2)}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">CV</div>
          <div className="font-semibold">{(data.metrics?.coefficient_of_variation * 100)?.toFixed(2)}%</div>
        </div>
      </div>

      {data.outliers?.length > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
          <div className="text-sm text-yellow-800">
            <strong>Outliers:</strong> {data.outliers.join(', ')}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Surprise History Panel ────────────────────────────────────────────────────

function SurpriseHistoryPanel({ data }) {
  if (!data) return null;

  const getSurpriseColor = (type) => {
    switch (type) {
      case 'beat': return 'bg-green-100 text-green-700';
      case 'miss': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold">Earnings Surprise History</h3>
          <p className="text-sm text-gray-500">{data.company_name}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-600">{data.summary?.beat_rate}%</div>
          <div className="text-sm text-gray-500">Beat Rate</div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="text-center p-3 bg-green-50 rounded">
          <div className="text-2xl font-bold text-green-600">{data.summary?.beats}</div>
          <div className="text-xs text-green-700">Beats</div>
        </div>
        <div className="text-center p-3 bg-red-50 rounded">
          <div className="text-2xl font-bold text-red-600">{data.summary?.misses}</div>
          <div className="text-xs text-red-700">Misses</div>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded">
          <div className="text-2xl font-bold text-gray-600">{data.summary?.inline}</div>
          <div className="text-xs text-gray-700">Inline</div>
        </div>
        <div className="text-center p-3 bg-blue-50 rounded">
          <div className="text-2xl font-bold text-blue-600">{data.streaks?.current_beat_streak}</div>
          <div className="text-xs text-blue-700">Current Streak</div>
        </div>
      </div>

      {/* Average Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Avg Surprise</div>
          <div className="font-semibold">{data.metrics?.avg_surprise_pct > 0 ? '+' : ''}{data.metrics?.avg_surprise_pct}%</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Avg Beat Magnitude</div>
          <div className="font-semibold text-green-600">+{data.metrics?.avg_beat_magnitude}%</div>
        </div>
      </div>

      {/* History Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">Period</th>
              <th className="px-3 py-2 text-right">Actual</th>
              <th className="px-3 py-2 text-right">Estimate</th>
              <th className="px-3 py-2 text-right">Surprise</th>
              <th className="px-3 py-2 text-center">Result</th>
              <th className="px-3 py-2 text-right">1D Move</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.history?.slice(0, 8).map((s, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-3 py-2">
                  {s.fiscal_period} {s.fiscal_year}
                </td>
                <td className="px-3 py-2 text-right font-medium">
                  ${s.actual_eps?.toFixed(2)}
                </td>
                <td className="px-3 py-2 text-right text-gray-600">
                  ${s.consensus_eps?.toFixed(2)}
                </td>
                <td className={`px-3 py-2 text-right font-medium ${
                  s.surprise_pct > 0 ? 'text-green-600' : s.surprise_pct < 0 ? 'text-red-600' : ''
                }`}>
                  {s.surprise_pct > 0 ? '+' : ''}{s.surprise_pct?.toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSurpriseColor(s.surprise_type)}`}>
                    {s.surprise_type}
                  </span>
                </td>
                <td className={`px-3 py-2 text-right ${
                  s.market_reaction?.['1d'] > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {s.market_reaction?.['1d'] > 0 ? '+' : ''}{s.market_reaction?.['1d']?.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main Page Component ───────────────────────────────────────────────────────

export default function ConsensusPage() {
  const [ticker, setTicker] = useState('NVDA');
  const [fiscalYear, setFiscalYear] = useState(new Date().getFullYear());

  const [consensusData, setConsensusData] = useState(null);
  const [momentumData, setMomentumData] = useState(null);
  const [dispersionData, setDispersionData] = useState(null);
  const [surpriseData, setSurpriseData] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);

    try {
      const [consensus, momentum, dispersion, surprise] = await Promise.all([
        apiFetch(`/consensus/snapshot?ticker=${ticker}&fiscal_year=${fiscalYear}`).then(r => r.json()),
        apiFetch(`/consensus/momentum?ticker=${ticker}&fiscal_year=${fiscalYear}`).then(r => r.json()),
        apiFetch(`/consensus/dispersion?ticker=${ticker}&fiscal_year=${fiscalYear}`).then(r => r.json()),
        apiFetch(`/consensus/surprise-history?ticker=${ticker}&quarters=12`).then(r => r.json()),
      ]);

      setConsensusData(consensus);
      setMomentumData(momentum);
      setDispersionData(dispersion);
      setSurpriseData(surprise);
    } catch (err) {
      setError('Failed to fetch consensus data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchAll();
  };

  return (
    <>
      <Head>
        <title>Consensus & Earnings Analysis | Finance Intelligence</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Consensus & Earnings Analysis</h1>
            <p className="text-sm text-gray-500">Point-in-time consensus, momentum, dispersion, and surprise history</p>
          </div>
        </header>

        {/* Search Bar */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <form onSubmit={handleSearch} className="flex gap-4 items-center">
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="Ticker (e.g., NVDA)"
                className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-32"
              />
              <select
                value={fiscalYear}
                onChange={(e) => setFiscalYear(parseInt(e.target.value))}
                className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {[2024, 2025, 2026].map(year => (
                  <option key={year} value={year}>FY {year}</option>
                ))}
              </select>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>

              {/* Quick tickers */}
              <div className="ml-4 flex gap-2">
                {['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN'].map(t => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => { setTicker(t); }}
                    className={`px-3 py-1 text-sm rounded-full border ${
                      ticker === t
                        ? 'bg-blue-100 border-blue-500 text-blue-700'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </form>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 py-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading consensus data...</div>
          ) : (
            <div className="space-y-6">
              {/* Top Row: Consensus + Momentum */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ConsensusCard data={consensusData} />
                <MomentumPanel data={momentumData} />
              </div>

              {/* Middle Row: Dispersion */}
              <DispersionPanel data={dispersionData} />

              {/* Bottom Row: Surprise History */}
              <SurpriseHistoryPanel data={surpriseData} />
            </div>
          )}
        </main>
      </div>
    </>
  );
}
