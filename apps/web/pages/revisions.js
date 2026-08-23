/**
 * Estimate Revision Screener Page (Band C #37)
 *
 * Features:
 * - Screen companies by revision criteria
 * - Top upward/downward revisions
 * - Accelerating revisions
 * - Revision alerts
 * - Summary statistics
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Revision Result Row ───────────────────────────────────────────────────────

function RevisionRow({ result, onClick }) {
  const getMomentumColor = (val) => {
    if (val > 2) return 'text-green-600 bg-green-50';
    if (val > 0) return 'text-green-500 bg-green-50';
    if (val < -2) return 'text-red-600 bg-red-50';
    if (val < 0) return 'text-red-500 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getTrendBadge = (trend) => {
    const colors = {
      strong_up: 'bg-green-600 text-white',
      moderate_up: 'bg-green-400 text-white',
      stable: 'bg-gray-400 text-white',
      moderate_down: 'bg-red-400 text-white',
      strong_down: 'bg-red-600 text-white',
    };
    return colors[trend] || 'bg-gray-400 text-white';
  };

  return (
    <tr
      className="hover:bg-gray-50 cursor-pointer border-b"
      onClick={() =>
 onClick && onClick(result)}
    >
      <td className="px-4 py-3">
        <div className="font-semibold text-blue-600">{result.ticker}</div>
        <div className="text-xs text-gray-500">{result.company_name}</div>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`inline-block px-2 py-1 rounded text-sm font-medium ${getMomentumColor(result.momentum?.['7d'])}`}>
          {result.momentum?.['7d'] > 0 ? '+' : ''}{result.momentum?.['7d']?.toFixed(2)}%
        </span>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`inline-block px-2 py-1 rounded text-sm font-medium ${getMomentumColor(result.momentum?.['30d'])}`}>
          {result.momentum?.['30d'] > 0 ? '+' : ''}{result.momentum?.['30d']?.toFixed(2)}%
        </span>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`inline-block px-2 py-1 rounded text-sm font-medium ${getMomentumColor(result.momentum?.['90d'])}`}>
          {result.momentum?.['90d'] > 0 ? '+' : ''}{result.momentum?.['90d']?.toFixed(2)}%
        </span>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`inline-block px-2 py-1 rounded text-xs ${getTrendBadge(result.trend_classification)}`}>
          {result.trend_classification?.replace(/_/g, ' ')}
        </span>
      </td>
      <td className="px-4 py-3 text-center">
        <div className="text-sm">
          <span className="text-green-600">{result.revisions?.up_30d || 0}</span>
          <span className="text-gray-400 mx-1">/</span>
          <span className="text-red-600">{result.revisions?.down_30d || 0}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-center">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full"
            style={{ width: `${result.signal_strength || 0}%` }}
          ></div>
        </div>
        <div className="text-xs text-gray-500 mt-1">{result.signal_strength?.toFixed(0)}%</div>
      </td>
    </tr>
  );
}

// ── Alert Card ────────────────────────────────────────────────────────────────

function AlertCard({ alert }) {
  const getSeverityColor = (severity) => {
    const colors = {
      high: 'border-red-500 bg-red-50',
      medium: 'border-yellow-500 bg-yellow-50',
      low: 'border-blue-500 bg-blue-50',
    };
    return colors[severity] || 'border-gray-500 bg-gray-50';
  };

  const getAlertIcon = (type) => {
    const icons = {
      momentum_spike: '📈',
      trend_reversal: '🔄',
      high_dispersion: '⚠️',
    };
    return icons[type] || '📊';
  };

  return (
    <div className={`border-l-4 rounded p-4 mb-3 ${getSeverityColor(alert.severity)}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{getAlertIcon(alert.alert_type)}</span>
          <div>
            <div className="font-semibold">{alert.ticker}</div>
            <div className="text-sm text-gray-600">{alert.company_name}</div>
          </div>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          alert.severity === 'high' ? 'bg-red-600 text-white' :
          alert.severity === 'medium' ? 'bg-yellow-600 text-white' :
          'bg-blue-600 text-white'
        }`}>
          {alert.severity}
        </span>
      </div>
      <p className="text-sm mt-2 text-gray-700">{alert.description}</p>
      <div className="text-xs text-gray-400 mt-2">
        {new Date(alert.triggered_at).toLocaleString()}
      </div>
    </div>
  );
}

// ── Summary Stats Card ────────────────────────────────────────────────────────

function SummaryCard({ summary }) {
  if (!summary) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Market Revision Summary</h3>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-4 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {summary.direction_breakdown?.upward_revisions || 0}
          </div>
          <div className="text-sm text-gray-600">Upward</div>
          <div className="text-xs text-gray-400">
            {summary.direction_breakdown?.upward_pct?.toFixed(1)}%
          </div>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-600">
            {summary.direction_breakdown?.stable || 0}
          </div>
          <div className="text-sm text-gray-600">Stable</div>
        </div>
        <div className="text-center p-4 bg-red-50 rounded-lg">
          <div className="text-2xl font-bold text-red-600">
            {summary.direction_breakdown?.downward_revisions || 0}
          </div>
          <div className="text-sm text-gray-600">Downward</div>
          <div className="text-xs text-gray-400">
            {summary.direction_breakdown?.downward_pct?.toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="border-t pt-4">
        <div className="text-sm text-gray-600 mb-2">Average 30-Day Momentum</div>
        <div className={`text-xl font-bold ${
          summary.momentum_stats?.average_30d_momentum > 0 ? 'text-green-600' : 'text-red-600'
        }`}>
          {summary.momentum_stats?.average_30d_momentum > 0 ? '+' : ''}
          {summary.momentum_stats?.average_30d_momentum?.toFixed(2)}%
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
        <div>
          <span className="text-gray-500">Max Momentum:</span>
          <span className="ml-2 font-medium text-green-600">
            +{summary.momentum_stats?.max_30d_momentum?.toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="text-gray-500">Min Momentum:</span>
          <span className="ml-2 font-medium text-red-600">
            {summary.momentum_stats?.min_30d_momentum?.toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Main Page Component ───────────────────────────────────────────────────────

export default function RevisionsPage() {
  const [activeTab, setActiveTab] = useState('screen');
  const [screenResults, setScreenResults] = useState(null);
  const [topUpward, setTopUpward] = useState(null);
  const [topDownward, setTopDownward] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [estimateType, setEstimateType] = useState('eps');
  const [fiscalPeriod, setFiscalPeriod] = useState('FY');
  const [minMomentum, setMinMomentum] = useState('');
  const [trendFilter, setTrendFilter] = useState('');

  const fetchScreenResults = async () => {
    setLoading(true);
    setError(null);
    try {
      let url = `${API_BASE}/revisions/screen?estimate_type=${estimateType}&fiscal_period=${fiscalPeriod}&limit=50`;
      if (minMomentum) url += `&min_momentum_30d=${minMomentum}`;
      if (trendFilter) url += `&trend_classification=${trendFilter}`;

      const res = await apiFetch(url, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to fetch screen results');
      const data = await res.json();
      setScreenResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchTopRevisions = async () => {
    setLoading(true);
    try {
      const [upRes, downRes] = await Promise.all([
        apiFetch(`/revisions/top-upward?estimate_type=${estimateType}&limit=10`),
        apiFetch(`/revisions/top-downward?estimate_type=${estimateType}&limit=10`),
      ]);

      if (upRes.ok) setTopUpward(await upRes.json());
      if (downRes.ok) setTopDownward(await downRes.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/revisions/alerts?estimate_type=${estimateType}`);
      if (res.ok) setAlerts(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/revisions/summary?estimate_type=${estimateType}`);
      if (res.ok) setSummary(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScreenResults();
    fetchSummary();
  }, []);

  useEffect(() => {
    if (activeTab === 'leaders') fetchTopRevisions();
    if (activeTab === 'alerts') fetchAlerts();
  }, [activeTab, estimateType]);

  return (
    <>
      <Head>
        <title>Estimate Revisions | Finance Research Platform</title>
      </Head>

      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <div className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 py-6">
            <h1 className="text-2xl font-bold text-gray-900">Estimate Revision Screener</h1>
            <p className="text-gray-600">Screen companies by analyst estimate momentum and revisions</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-4 mt-4">
          <div className="bg-white rounded-lg shadow">
            <div className="border-b flex">
              {[
                { id: 'screen', label: 'Screener' },
                { id: 'leaders', label: 'Leaderboard' },
                { id: 'alerts', label: 'Alerts' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-3 font-medium ${
                    activeTab === tab.id
                      ? 'border-b-2 border-blue-600 text-blue-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Filters */}
            <div className="p-4 border-b bg-gray-50 flex items-center gap-4">
              <div>
                <label className="text-sm text-gray-600 block mb-1">Estimate Type</label>
                <select
                  value={estimateType}
                  onChange={(e) => setEstimateType(e.target.value)}
                  className="border rounded px-3 py-2 text-sm"
                >
                  <option value="eps">EPS</option>
                  <option value="revenue">Revenue</option>
                  <option value="ebitda">EBITDA</option>
                </select>
              </div>

              <div>
                <label className="text-sm text-gray-600 block mb-1">Period</label>
                <select
                  value={fiscalPeriod}
                  onChange={(e) => setFiscalPeriod(e.target.value)}
                  className="border rounded px-3 py-2 text-sm"
                >
                  <option value="FY">Full Year</option>
                  <option value="Q1">Q1</option>
                  <option value="Q2">Q2</option>
                  <option value="Q3">Q3</option>
                  <option value="Q4">Q4</option>
                </select>
              </div>

              {activeTab === 'screen' && (
                <>
                  <div>
                    <label className="text-sm text-gray-600 block mb-1">Min 30d Momentum</label>
                    <input
                      type="number"
                      value={minMomentum}
                      onChange={(e) => setMinMomentum(e.target.value)}
                      placeholder="e.g., 2"
                      className="border rounded px-3 py-2 text-sm w-24"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-gray-600 block mb-1">Trend</label>
                    <select
                      value={trendFilter}
                      onChange={(e) => setTrendFilter(e.target.value)}
                      className="border rounded px-3 py-2 text-sm"
                    >
                      <option value="">All</option>
                      <option value="strong_up">Strong Up</option>
                      <option value="moderate_up">Moderate Up</option>
                      <option value="stable">Stable</option>
                      <option value="moderate_down">Moderate Down</option>
                      <option value="strong_down">Strong Down</option>
                    </select>
                  </div>

                  <button
                    onClick={fetchScreenResults}
                    disabled={loading}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 mt-5"
                  >
                    {loading ? 'Loading...' : 'Apply Filters'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="max-w-7xl mx-auto px-4 py-4">
          {error && (
            <div className="bg-red-100 text-red-700 p-4 rounded mb-4">
              {error}
            </div>
          )}

          {activeTab === 'screen' && (
            <div className="grid grid-cols-4 gap-4">
              {/* Results Table */}
              <div className="col-span-3 bg-white rounded-lg shadow">
                <div className="p-4 border-b">
                  <h2 className="font-semibold">
                    Screener Results
                    {screenResults && (
                      <span className="text-sm font-normal text-gray-500 ml-2">
                        ({screenResults.total_matched} of {screenResults.total_screened})
                      </span>
                    )}
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">7D</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">30D</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">90D</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Trend</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Up/Down</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Signal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {screenResults?.results?.map((result) => (
                        <RevisionRow key={result.ticker} result={result} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Summary Sidebar */}
              <div className="col-span-1">
                <SummaryCard summary={summary} />
              </div>
            </div>
          )}

          {activeTab === 'leaders' && (
            <div className="grid grid-cols-2 gap-4">
              {/* Top Upward */}
              <div className="bg-white rounded-lg shadow">
                <div className="p-4 border-b bg-green-50">
                  <h2 className="font-semibold text-green-800">Top Upward Revisions</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs">Company</th>
                        <th className="px-4 py-2 text-center text-xs">30D</th>
                        <th className="px-4 py-2 text-center text-xs">Trend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topUpward?.results?.map((r) => (
                        <tr key={r.ticker} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-2">
                            <div className="font-medium text-blue-600">{r.ticker}</div>
                          </td>
                          <td className="px-4 py-2 text-center text-green-600 font-medium">
                            +{r.momentum?.['30d']?.toFixed(2)}%
                          </td>
                          <td className="px-4 py-2 text-center text-sm">
                            {r.trend_classification?.replace(/_/g, ' ')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Top Downward */}
              <div className="bg-white rounded-lg shadow">
                <div className="p-4 border-b bg-red-50">
                  <h2 className="font-semibold text-red-800">Top Downward Revisions</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs">Company</th>
                        <th className="px-4 py-2 text-center text-xs">30D</th>
                        <th className="px-4 py-2 text-center text-xs">Trend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topDownward?.results?.map((r) => (
                        <tr key={r.ticker} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-2">
                            <div className="font-medium text-blue-600">{r.ticker}</div>
                          </td>
                          <td className="px-4 py-2 text-center text-red-600 font-medium">
                            {r.momentum?.['30d']?.toFixed(2)}%
                          </td>
                          <td className="px-4 py-2 text-center text-sm">
                            {r.trend_classification?.replace(/_/g, ' ')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'alerts' && (
            <div className="max-w-3xl mx-auto">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="font-semibold mb-4">
                  Revision Alerts
                  {alerts && (
                    <span className="text-sm font-normal text-gray-500 ml-2">
                      ({alerts.alert_count} alerts)
                    </span>
                  )}
                </h2>
                {alerts?.alerts?.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No alerts at this time</p>
                ) : (
                  alerts?.alerts?.map((alert, i) => (
                    <AlertCard key={i} alert={alert} />
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
