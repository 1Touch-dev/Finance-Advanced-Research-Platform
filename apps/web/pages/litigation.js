/**
 * Litigation Intelligence Page
 * Wired to /litigation/* API endpoints
 */

import React, { useState } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

const ENFORCEMENT_TYPES = ['sec', 'doj', 'ftc', 'ofac', 'state', 'international'];
const RISK_LEVELS = ['critical', 'high', 'medium', 'low', 'minimal'];

export default function Litigation() {
  const [ticker, setTicker] = useState('');
  const [view, setView] = useState('enforcement');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Screener state
  const [screenerTickers, setScreenerTickers] = useState('');
  const [screenerFilters, setScreenerFilters] = useState({
    minRiskScore: '',
    maxRiskScore: '',
    riskLevel: '',
    hasSecEnforcement: null,
    hasClassAction: null,
  });

  const fetchData = async (endpoint) => {
    if (!ticker.trim()) {
      setError('Please enter a ticker');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await apiFetch(`/litigation/${ticker.toUpperCase()}/${endpoint}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Failed to fetch ${endpoint}`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runScreener = async () => {
    const tickers = screenerTickers.split(',').map(t => t.trim().toUpperCase()).filter(Boolean);
    if (tickers.length === 0) {
      setError('Please enter at least one ticker');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    const params = new URLSearchParams();
    tickers.forEach(t => params.append('tickers', t));
    if (screenerFilters.minRiskScore) params.append('min_risk_score', screenerFilters.minRiskScore);
    if (screenerFilters.maxRiskScore) params.append('max_risk_score', screenerFilters.maxRiskScore);
    if (screenerFilters.riskLevel) params.append('risk_level', screenerFilters.riskLevel);
    if (screenerFilters.hasSecEnforcement !== null) params.append('has_sec_enforcement', screenerFilters.hasSecEnforcement);

    try {
      const res = await apiFetch(`/litigation/screen?${params}`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Screener failed');
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level) => {
    const colors = {
      critical: 'bg-red-600 text-white',
      high: 'bg-red-400 text-white',
      medium: 'bg-yellow-400 text-black',
      low: 'bg-green-400 text-black',
      minimal: 'bg-green-200 text-black',
    };
    return colors[level?.toLowerCase()] || 'bg-gray-200';
  };

  const formatMoney = (value) => {
    if (!value) return '-';
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    return `$${value.toLocaleString()}`;
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Litigation Intelligence</h1>
        <p className="text-gray-600 mb-6">
          Enforcement events, docket velocity, exposure analysis, and litigation screening.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {[
            { key: 'enforcement', label: 'Enforcement' },
            { key: 'event-study', label: 'Event Study' },
            { key: 'velocity', label: 'Docket Velocity' },
            { key: 'exposure', label: 'Exposure' },
            { key: 'snapshot', label: 'Snapshot' },
            { key: 'screener', label: 'Screener' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setView(tab.key); setResult(null); }}
              className={`px-4 py-2 rounded ${view === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Ticker Input (for non-screener views) */}
        {view !== 'screener' && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Enter ticker (e.g., AAPL)"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="flex-1 border rounded px-3 py-2"
              />
              <button
                onClick={() => fetchData(view)}
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>
            </div>
          </div>
        )}

        {/* Screener Form */}
        {view === 'screener' && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="font-bold mb-4">Screen Companies by Litigation Risk</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tickers (comma-separated)</label>
                <input
                  type="text"
                  placeholder="AAPL, MSFT, GOOG, META"
                  value={screenerTickers}
                  onChange={(e) => setScreenerTickers(e.target.value.toUpperCase())}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Min Risk Score</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={screenerFilters.minRiskScore}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, minRiskScore: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Max Risk Score</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={screenerFilters.maxRiskScore}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, maxRiskScore: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Risk Level</label>
                  <select
                    value={screenerFilters.riskLevel}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, riskLevel: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">Any</option>
                    {RISK_LEVELS.map((l) => (
                      <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">SEC Enforcement</label>
                  <select
                    value={screenerFilters.hasSecEnforcement === null ? '' : screenerFilters.hasSecEnforcement}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, hasSecEnforcement: e.target.value === '' ? null : e.target.value === 'true' })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">Any</option>
                    <option value="true">Has SEC</option>
                    <option value="false">No SEC</option>
                  </select>
                </div>
              </div>
              <button
                onClick={runScreener}
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Screening...' : 'Run Screener'}
              </button>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Enforcement Events */}
            {result.events && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-bold">Enforcement Events ({result.event_count || result.events.length})</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left p-3">Date</th>
                        <th className="text-left p-3">Type</th>
                        <th className="text-left p-3">Agency</th>
                        <th className="text-left p-3">Description</th>
                        <th className="text-right p-3">Penalty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.events.map((evt, idx) => (
                        <tr key={idx} className="border-t hover:bg-gray-50">
                          <td className="p-3">{evt.date || evt.event_date}</td>
                          <td className="p-3">
                            <span className="px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-bold">
                              {evt.event_type || evt.type}
                            </span>
                          </td>
                          <td className="p-3">{evt.agency || '-'}</td>
                          <td className="p-3 text-sm">{evt.description?.slice(0, 100)}</td>
                          <td className="p-3 text-right font-bold">{formatMoney(evt.penalty_amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Event Study Results */}
            {result.results && view === 'event-study' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4">Event Study: Market Reactions</h2>
                {result.summary && (
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="text-center p-4 bg-red-50 rounded">
                      <div className="text-3xl font-bold text-red-600">{result.summary.negative_reactions}</div>
                      <div className="text-sm text-gray-600">Negative</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded">
                      <div className="text-3xl font-bold text-gray-600">{result.summary.neutral_reactions}</div>
                      <div className="text-sm text-gray-600">Neutral</div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded">
                      <div className="text-3xl font-bold text-green-600">{result.summary.positive_reactions}</div>
                      <div className="text-sm text-gray-600">Positive</div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Velocity Indicator */}
            {result.velocity_score !== undefined && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4">Docket Velocity</h2>
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold">{result.velocity_score?.toFixed(1) || 0}</div>
                    <div className="text-sm text-gray-500">Velocity Score</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold">{result.filings_count || 0}</div>
                    <div className="text-sm text-gray-500">New Filings</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold">{result.trend || '-'}</div>
                    <div className="text-sm text-gray-500">Trend</div>
                  </div>
                  <div className="text-center">
                    <span className={`px-3 py-1 rounded text-sm font-bold ${getRiskColor(result.risk_level)}`}>
                      {result.risk_level?.toUpperCase() || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Exposure Analysis */}
            {result.exposure_metrics && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4">Normalized Exposure</h2>
                <div className="grid grid-cols-5 gap-4">
                  {Object.entries(result.exposure_metrics).map(([key, value]) => (
                    <div key={key} className="text-center p-3 bg-gray-50 rounded">
                      <div className="text-2xl font-bold">{typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : value}</div>
                      <div className="text-xs text-gray-500">{key.replace(/_/g, ' ')}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Screener Results */}
            {result.results && view === 'screener' && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-bold">
                    Screener Results: {result.screened_count} / {result.total_input} companies
                  </h2>
                </div>
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3">Ticker</th>
                      <th className="text-center p-3">Risk Score</th>
                      <th className="text-center p-3">Risk Level</th>
                      <th className="text-center p-3">SEC</th>
                      <th className="text-center p-3">Class Action</th>
                      <th className="text-right p-3">Exposure %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.results.map((r, idx) => (
                      <tr key={idx} className="border-t hover:bg-gray-50">
                        <td className="p-3 font-bold">{r.ticker}</td>
                        <td className="p-3 text-center">{r.risk_score?.toFixed(0) || '-'}</td>
                        <td className="p-3 text-center">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${getRiskColor(r.risk_level)}`}>
                            {r.risk_level?.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-3 text-center">{r.has_sec_enforcement ? '✓' : '-'}</td>
                        <td className="p-3 text-center">{r.has_class_action ? '✓' : '-'}</td>
                        <td className="p-3 text-right">{r.exposure_pct ? `${(r.exposure_pct * 100).toFixed(2)}%` : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Snapshot */}
            {result.as_of_date && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4">Litigation Snapshot: {result.as_of_date}</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">Active Cases</div>
                    <div className="text-2xl font-bold">{result.active_cases || 0}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Total Exposure</div>
                    <div className="text-2xl font-bold">{formatMoney(result.total_exposure)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Risk Level</div>
                    <span className={`px-3 py-1 rounded text-sm font-bold ${getRiskColor(result.risk_level)}`}>
                      {result.risk_level?.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Score</div>
                    <div className="text-2xl font-bold">{result.risk_score?.toFixed(0) || 0}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
