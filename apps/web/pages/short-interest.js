/**
 * Short Interest Page (Band C #40)
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ShortInterest() {
  const [view, setView] = useState('most-shorted');
  const [data, setData] = useState([]);
  const [stats, setStats] = useState(null);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ticker, setTicker] = useState('');
  const [tickerData, setTickerData] = useState(null);

  useEffect(() => {
    fetchStats();
    fetchSectors();
    if (view === 'most-shorted') fetchMostShorted();
    else if (view === 'squeeze') fetchSqueezeCandidates();
    else if (view === 'changes') fetchChanges();
  }, [view]);

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/short-interest/stats`);
    if (res.ok) setStats(await res.json());
  };

  const fetchSectors = async () => {
    const res = await fetch(`${API_BASE}/short-interest/sectors`);
    if (res.ok) {
      const d = await res.json();
      setSectors(d.sectors || []);
    }
  };

  const fetchMostShorted = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/short-interest/most-shorted?min_short_percent=5`);
    if (res.ok) {
      const d = await res.json();
      setData(d.stocks || []);
    }
    setLoading(false);
  };

  const fetchSqueezeCandidates = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/short-interest/squeeze-candidates?min_score=40`);
    if (res.ok) {
      const d = await res.json();
      setData(d.candidates || []);
    }
    setLoading(false);
  };

  const fetchChanges = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/short-interest/changes?min_change=5`);
    if (res.ok) {
      const d = await res.json();
      setData(d.stocks || []);
    }
    setLoading(false);
  };

  const fetchTicker = async () => {
    if (!ticker) return;
    setLoading(true);
    const res = await fetch(`${API_BASE}/short-interest/ticker/${ticker}`);
    if (res.ok) {
      const d = await res.json();
      setTickerData(d.data);
    }
    setLoading(false);
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Short Interest Data</h1>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Tracked</div>
              <div className="text-2xl font-bold">{stats.total_tracked}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Highly Shorted (20%+)</div>
              <div className="text-2xl font-bold text-red-600">{stats.highly_shorted_count}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Avg Short %</div>
              <div className="text-2xl font-bold">{stats.avg_short_percent}%</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Most Shorted</div>
              <div className="text-2xl font-bold">{stats.most_shorted}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Biggest Increase</div>
              <div className="text-2xl font-bold text-orange-600">{stats.biggest_increase}</div>
            </div>
          </div>
        )}

        {/* Ticker Search */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              placeholder="Enter ticker..."
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="border rounded px-3 py-2 flex-1"
            />
            <button onClick={fetchTicker} className="bg-blue-600 text-white px-6 py-2 rounded">
              Search
            </button>
          </div>
          {tickerData && (
            <div className="mt-4 grid grid-cols-5 gap-4 p-4 bg-gray-50 rounded">
              <div>
                <div className="text-xs text-gray-500">Ticker</div>
                <div className="font-bold">{tickerData.ticker}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Short % Float</div>
                <div className="font-bold text-red-600">{tickerData.short_percent_float}%</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Days to Cover</div>
                <div className="font-bold">{tickerData.days_to_cover}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Short Interest</div>
                <div className="font-bold">{(tickerData.short_interest / 1e6).toFixed(1)}M</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Change</div>
                <div className={`font-bold ${tickerData.short_change_percent > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {tickerData.short_change_percent > 0 ? '+' : ''}{tickerData.short_change_percent}%
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setView('most-shorted')}
            className={`px-4 py-2 rounded ${view === 'most-shorted' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Most Shorted
          </button>
          <button
            onClick={() => setView('squeeze')}
            className={`px-4 py-2 rounded ${view === 'squeeze' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Squeeze Candidates
          </button>
          <button
            onClick={() => setView('changes')}
            className={`px-4 py-2 rounded ${view === 'changes' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Recent Changes
          </button>
        </div>

        <div className="grid grid-cols-4 gap-6">
          {/* Main Table */}
          <div className="col-span-3 bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Ticker</th>
                  <th className="text-left p-3">Company</th>
                  <th className="text-right p-3">Short %</th>
                  <th className="text-right p-3">Days Cover</th>
                  {view === 'squeeze' && <th className="text-right p-3">Squeeze Score</th>}
                  {view === 'changes' && <th className="text-right p-3">Change %</th>}
                  {view === 'squeeze' && <th className="text-center p-3">Risk</th>}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="6" className="text-center p-8">Loading...</td></tr>
                ) : data.map((item, idx) => (
                  <tr key={idx} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{item.ticker}</td>
                    <td className="p-3">{item.company_name}</td>
                    <td className="p-3 text-right text-red-600">{item.short_percent_float}%</td>
                    <td className="p-3 text-right">{item.days_to_cover}</td>
                    {view === 'squeeze' && (
                      <td className="p-3 text-right font-bold">{item.squeeze_score}</td>
                    )}
                    {view === 'changes' && (
                      <td className={`p-3 text-right ${item.short_change_percent > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {item.short_change_percent > 0 ? '+' : ''}{item.short_change_percent}%
                      </td>
                    )}
                    {view === 'squeeze' && (
                      <td className="p-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${
                          item.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                          item.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {item.risk_level}
                        </span>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Sector Summary */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b font-semibold">By Sector</div>
            <div className="divide-y">
              {sectors.map((sector, idx) => (
                <div key={idx} className="p-3">
                  <div className="font-medium text-sm">{sector.sector}</div>
                  <div className="text-xs text-gray-500">{sector.stock_count} stocks</div>
                  <div className="flex justify-between mt-1">
                    <span className="text-xs">Avg Short:</span>
                    <span className="text-xs font-medium text-red-600">{sector.avg_short_percent_float}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs">Most Shorted:</span>
                    <span className="text-xs font-medium">{sector.most_shorted}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
