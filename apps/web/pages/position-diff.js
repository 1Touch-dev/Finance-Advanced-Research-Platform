/**
 * Institutional Position Diff Page
 * Wired to GET /market/institutional/position-diff
 *
 * Shows quarter-over-quarter position changes from 13F filings
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

// Top institutions with their CIK numbers
const TOP_INSTITUTIONS = [
  { name: 'Berkshire Hathaway', cik: '0001067983' },
  { name: 'BlackRock', cik: '0001364742' },
  { name: 'Vanguard', cik: '0000102909' },
  { name: 'State Street', cik: '0000093751' },
  { name: 'Fidelity', cik: '0000315066' },
  { name: 'Citadel', cik: '0001423053' },
  { name: 'Two Sigma', cik: '0001450144' },
  { name: 'DE Shaw', cik: '0001009207' },
  { name: 'Renaissance Technologies', cik: '0001037389' },
  { name: 'Bridgewater', cik: '0001350694' },
];

const STATUS_OPTIONS = [
  { value: 'changed', label: 'Changed Positions' },
  { value: 'new', label: 'New Positions' },
  { value: 'closed', label: 'Closed Positions' },
  { value: 'increased', label: 'Increased' },
  { value: 'decreased', label: 'Decreased' },
  { value: 'all', label: 'All Positions' },
];

export default function PositionDiff() {
  const [institutionCik, setInstitutionCik] = useState('');
  const [currentPeriod, setCurrentPeriod] = useState('');
  const [previousPeriod, setPreviousPeriod] = useState('');
  const [status, setStatus] = useState('changed');
  const [ticker, setTicker] = useState('');
  const [sortBy, setSortBy] = useState('reported_value_diff_usd');
  const [sortDir, setSortDir] = useState('desc');
  const [limit, setLimit] = useState(100);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const fetchPositionDiff = async () => {
    if (!institutionCik.trim()) {
      setError('Please select or enter an institution CIK');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const params = new URLSearchParams({
      institution_cik: institutionCik.replace(/^0+/, '').padStart(10, '0'),
      status: status,
      sort_by: sortBy,
      sort_dir: sortDir,
      limit: limit.toString(),
      offset: '0',
    });

    if (currentPeriod) params.append('current_period', currentPeriod);
    if (previousPeriod) params.append('previous_period', previousPeriod);
    if (ticker.trim()) params.append('ticker', ticker.trim().toUpperCase());

    try {
      const res = await apiFetch(`/market/institutional/position-diff?${params}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to fetch position diff');
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatMoney = (value) => {
    if (value === null || value === undefined) return '-';
    const absVal = Math.abs(value);
    if (absVal >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (absVal >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (absVal >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
    return `$${value.toLocaleString()}`;
  };

  const formatShares = (value) => {
    if (value === null || value === undefined) return '-';
    const absVal = Math.abs(value);
    if (absVal >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    if (absVal >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
    return value.toLocaleString();
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getChangeColor = (value) => {
    if (!value) return 'text-gray-600';
    return value > 0 ? 'text-green-600' : 'text-red-600';
  };

  const getStatusBadge = (posStatus) => {
    const badges = {
      new: 'bg-blue-100 text-blue-800',
      closed: 'bg-gray-100 text-gray-800',
      increased: 'bg-green-100 text-green-800',
      decreased: 'bg-red-100 text-red-800',
      unchanged: 'bg-gray-50 text-gray-600',
    };
    return badges[posStatus?.toLowerCase()] || 'bg-gray-100 text-gray-600';
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Institutional Position Diff</h1>
        <p className="text-gray-600 mb-6">
          Compare 13F quarterly filings to see position changes by major institutions.
        </p>

        {/* Controls */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Institution</label>
              <select
                value={institutionCik}
                onChange={(e) => setInstitutionCik(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                <option value="">-- Select Institution --</option>
                {TOP_INSTITUTIONS.map((inst) => (
                  <option key={inst.cik} value={inst.cik}>
                    {inst.name}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Or enter CIK..."
                value={institutionCik}
                onChange={(e) => setInstitutionCik(e.target.value)}
                className="w-full border rounded px-3 py-2 mt-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Period</label>
              <input
                type="date"
                value={currentPeriod}
                onChange={(e) => setCurrentPeriod(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
              <span className="text-xs text-gray-500">Leave blank for latest</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Previous Period</label>
              <input
                type="date"
                value={previousPeriod}
                onChange={(e) => setPreviousPeriod(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
              <span className="text-xs text-gray-500">Leave blank for prior quarter</span>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Filter Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Filter Ticker</label>
              <input
                type="text"
                placeholder="e.g., AAPL"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-full border rounded px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                <option value="reported_value_diff_usd">Value Change ($)</option>
                <option value="shares_diff">Shares Change</option>
                <option value="pct_change">Percent Change</option>
                <option value="current_value">Current Value</option>
                <option value="ticker">Ticker</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Order</label>
              <select
                value={sortDir}
                onChange={(e) => setSortDir(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>

          <button
            onClick={fetchPositionDiff}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Fetch Position Diff'}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Period Comparison</h2>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-gray-500">Institution</div>
                  <div className="text-xl font-bold">{result.institution_name || result.institution_cik}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Current Period</div>
                  <div className="text-xl font-bold">{result.current_period}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Previous Period</div>
                  <div className="text-xl font-bold">{result.previous_period}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Positions</div>
                  <div className="text-xl font-bold">{result.total_positions || result.positions?.length || 0}</div>
                </div>
              </div>
            </div>

            {/* Positions Table */}
            {result.positions && result.positions.length > 0 && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-bold">Position Changes</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left p-3">Ticker</th>
                        <th className="text-left p-3">CUSIP</th>
                        <th className="text-center p-3">Status</th>
                        <th className="text-right p-3">Prev Shares</th>
                        <th className="text-right p-3">Curr Shares</th>
                        <th className="text-right p-3">Shares Diff</th>
                        <th className="text-right p-3">Prev Value</th>
                        <th className="text-right p-3">Curr Value</th>
                        <th className="text-right p-3">Value Diff</th>
                        <th className="text-right p-3">% Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.positions.map((pos, idx) => (
                        <tr key={idx} className="border-t hover:bg-gray-50">
                          <td className="p-3 font-bold">{pos.ticker || '-'}</td>
                          <td className="p-3 text-sm text-gray-500">{pos.cusip}</td>
                          <td className="p-3 text-center">
                            <span className={`px-2 py-1 rounded text-xs font-bold ${getStatusBadge(pos.status)}`}>
                              {pos.status?.toUpperCase() || '-'}
                            </span>
                          </td>
                          <td className="p-3 text-right">{formatShares(pos.previous_shares)}</td>
                          <td className="p-3 text-right">{formatShares(pos.current_shares)}</td>
                          <td className={`p-3 text-right font-medium ${getChangeColor(pos.shares_diff)}`}>
                            {pos.shares_diff > 0 ? '+' : ''}{formatShares(pos.shares_diff)}
                          </td>
                          <td className="p-3 text-right">{formatMoney(pos.previous_value)}</td>
                          <td className="p-3 text-right">{formatMoney(pos.current_value)}</td>
                          <td className={`p-3 text-right font-bold ${getChangeColor(pos.value_diff)}`}>
                            {pos.value_diff > 0 ? '+' : ''}{formatMoney(pos.value_diff)}
                          </td>
                          <td className={`p-3 text-right font-medium ${getChangeColor(pos.pct_change)}`}>
                            {formatPercent(pos.pct_change)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* No positions */}
            {result.positions && result.positions.length === 0 && (
              <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded">
                No position changes found for the selected criteria.
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
