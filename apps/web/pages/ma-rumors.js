/**
 * M&A Rumors Page (Band C #39)
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function MARumors() {
  const [view, setView] = useState('active');
  const [rumors, setRumors] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRumor, setSelectedRumor] = useState(null);

  useEffect(() => {
    fetchStats();
    if (view === 'active') fetchActive();
    else if (view === 'high-prob') fetchHighProbability();
    else if (view === 'confirmed') fetchConfirmed();
    else if (view === 'largest') fetchLargest();
  }, [view]);

  const fetchStats = async () => {
    const res = await apiFetch(`/ma-rumors/stats`);
    if (res.ok) setStats(await res.json());
  };

  const fetchActive = async () => {
    setLoading(true);
    const res = await apiFetch(`/ma-rumors/active?days=60`);
    if (res.ok) {
      const d = await res.json();
      setRumors(d.rumors || []);
    }
    setLoading(false);
  };

  const fetchHighProbability = async () => {
    setLoading(true);
    const res = await apiFetch(`/ma-rumors/high-probability?min_score=30`);
    if (res.ok) {
      const d = await res.json();
      setRumors(d.rumors || []);
    }
    setLoading(false);
  };

  const fetchConfirmed = async () => {
    setLoading(true);
    const res = await apiFetch(`/ma-rumors/confirmed`);
    if (res.ok) {
      const d = await res.json();
      setRumors(d.deals || []);
    }
    setLoading(false);
  };

  const fetchLargest = async () => {
    setLoading(true);
    const res = await apiFetch(`/ma-rumors/largest?limit=20`);
    if (res.ok) {
      const d = await res.json();
      setRumors(d.deals || []);
    }
    setLoading(false);
  };

  const searchRumors = async () => {
    if (!searchQuery) return;
    setLoading(true);
    const res = await apiFetch(`/ma-rumors/search?q=${searchQuery}`);
    if (res.ok) {
      const d = await res.json();
      setRumors(d.results || []);
    }
    setLoading(false);
  };

  const formatMoney = (value) => {
    if (!value) return '-';
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
    return `$${value.toLocaleString()}`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed': return 'bg-green-100 text-green-700';
      case 'denied': return 'bg-red-100 text-red-700';
      case 'rumor': return 'bg-yellow-100 text-yellow-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getProbabilityColor = (prob) => {
    if (prob >= 60) return 'text-green-600';
    if (prob >= 40) return 'text-yellow-600';
    return 'text-gray-500';
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">M&A Rumors & Deal Tracker</h1>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Active Rumors</div>
              <div className="text-2xl font-bold text-yellow-600">{stats.active_rumors}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Confirmed Deals</div>
              <div className="text-2xl font-bold text-green-600">{stats.confirmed_deals}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Deal Value</div>
              <div className="text-2xl font-bold">{formatMoney(stats.total_estimated_value)}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Avg Premium</div>
              <div className="text-2xl font-bold">{stats.avg_premium_percent}%</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Hottest Target</div>
              <div className="text-2xl font-bold text-blue-600">{stats.hottest_target || '-'}</div>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              placeholder="Search by company, ticker, or headline..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="border rounded px-3 py-2 flex-1"
            />
            <button onClick={searchRumors} className="bg-blue-600 text-white px-6 py-2 rounded">
              Search
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'active', label: 'Active Rumors' },
            { key: 'high-prob', label: 'High Probability' },
            { key: 'confirmed', label: 'Confirmed Deals' },
            { key: 'largest', label: 'Largest Deals' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setView(tab.key)}
              className={`px-4 py-2 rounded ${view === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="grid grid-cols-3 gap-6">
          {/* Rumors List */}
          <div className="col-span-2 bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Target</th>
                  <th className="text-left p-3">Acquirer</th>
                  <th className="text-left p-3">Type</th>
                  <th className="text-right p-3">Value</th>
                  <th className="text-right p-3">Premium</th>
                  <th className="text-right p-3">Prob.</th>
                  <th className="text-center p-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="7" className="text-center p-8">Loading...</td></tr>
                ) : rumors.map((rumor, idx) => (
                  <tr
                    key={idx}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedRumor(rumor)}
                  >
                    <td className="p-3">
                      <div className="font-bold">{rumor.target_ticker}</div>
                      <div className="text-xs text-gray-500">{rumor.target_name}</div>
                    </td>
                    <td className="p-3">
                      <div className="font-medium">{rumor.acquirer_ticker || '-'}</div>
                      <div className="text-xs text-gray-500">{rumor.acquirer_name || 'Unknown'}</div>
                    </td>
                    <td className="p-3 text-sm capitalize">{rumor.deal_type.replace('_', ' ')}</td>
                    <td className="p-3 text-right font-medium">{formatMoney(rumor.estimated_value)}</td>
                    <td className="p-3 text-right text-green-600">
                      {rumor.premium_percent ? `+${rumor.premium_percent}%` : '-'}
                    </td>
                    <td className={`p-3 text-right font-bold ${getProbabilityColor(rumor.probability_score)}`}>
                      {rumor.probability_score}%
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 text-xs rounded ${getStatusColor(rumor.status)}`}>
                        {rumor.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Detail Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b font-semibold">Rumor Details</div>
            {selectedRumor ? (
              <div className="p-4 space-y-4">
                <div>
                  <div className="text-sm text-gray-500">Target</div>
                  <div className="font-bold text-lg">{selectedRumor.target_ticker}</div>
                  <div className="text-sm">{selectedRumor.target_name}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Acquirer</div>
                  <div className="font-bold">{selectedRumor.acquirer_name || 'Unknown'}</div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-gray-500">Deal Type</div>
                    <div className="font-medium capitalize">{selectedRumor.deal_type.replace('_', ' ')}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Sector</div>
                    <div className="font-medium">{selectedRumor.sector}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-gray-500">Estimated Value</div>
                    <div className="font-bold text-lg">{formatMoney(selectedRumor.estimated_value)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Premium</div>
                    <div className="font-bold text-lg text-green-600">
                      {selectedRumor.premium_percent ? `+${selectedRumor.premium_percent}%` : '-'}
                    </div>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Probability Score</div>
                  <div className="mt-1">
                    <div className="h-2 bg-gray-200 rounded-full">
                      <div
                        className={`h-2 rounded-full ${
                          selectedRumor.probability_score >= 60 ? 'bg-green-500' :
                          selectedRumor.probability_score >= 40 ? 'bg-yellow-500' : 'bg-gray-400'
                        }`}
                        style={{ width: `${selectedRumor.probability_score}%` }}
                      />
                    </div>
                    <div className="text-right text-sm font-bold mt-1">{selectedRumor.probability_score}%</div>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Source</div>
                  <div className="font-medium">{selectedRumor.source}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Headline</div>
                  <div className="text-sm">{selectedRumor.headline}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Summary</div>
                  <div className="text-sm text-gray-600">{selectedRumor.summary}</div>
                </div>
                <div className="text-xs text-gray-400">
                  Rumor Date: {selectedRumor.rumor_date} | Updated: {selectedRumor.last_updated}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-gray-500">
                Click a rumor to see details
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
