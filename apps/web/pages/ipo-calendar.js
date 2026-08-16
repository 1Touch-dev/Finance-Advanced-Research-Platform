/**
 * IPO Calendar Page (Band C #38)
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function IPOCalendar() {
  const [view, setView] = useState('upcoming');
  const [data, setData] = useState([]);
  const [weekCalendar, setWeekCalendar] = useState({});
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchTicker, setSearchTicker] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    fetchStats();
    if (view === 'upcoming') fetchUpcoming();
    else if (view === 'recent') fetchRecent();
    else if (view === 'lockups') fetchLockups();
    else if (view === 'week') fetchWeek();
    else if (view === 'performance') fetchPerformance();
  }, [view]);

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/ipo/stats`);
    if (res.ok) setStats(await res.json());
  };

  const fetchUpcoming = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/ipo/upcoming?days=30`);
    if (res.ok) {
      const d = await res.json();
      setData(d.upcoming || []);
    }
    setLoading(false);
  };

  const fetchRecent = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/ipo/recent?days=90`);
    if (res.ok) {
      const d = await res.json();
      setData(d.recent || []);
    }
    setLoading(false);
  };

  const fetchLockups = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/ipo/lockups?days=90`);
    if (res.ok) {
      const d = await res.json();
      setData(d.lockup_expirations || []);
    }
    setLoading(false);
  };

  const fetchWeek = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/ipo/week`);
    if (res.ok) {
      const d = await res.json();
      setWeekCalendar(d.calendar || {});
    }
    setLoading(false);
  };

  const fetchPerformance = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/ipo/performance?days=90`);
    if (res.ok) {
      const d = await res.json();
      setData(d.performance || []);
    }
    setLoading(false);
  };

  const searchIPO = async () => {
    if (!searchTicker) return;
    const res = await fetch(`${API_BASE}/ipo/ticker/${searchTicker}`);
    if (res.ok) {
      const d = await res.json();
      setSearchResults(d.ipo);
    } else {
      setSearchResults(null);
    }
  };

  const formatMoney = (value) => {
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
    return `$${value.toLocaleString()}`;
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">IPO Calendar</h1>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Upcoming IPOs</div>
              <div className="text-2xl font-bold text-blue-600">{stats.upcoming_count}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Recently Priced</div>
              <div className="text-2xl font-bold">{stats.priced_count}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Deal Pipeline</div>
              <div className="text-2xl font-bold">{formatMoney(stats.total_deal_size_upcoming)}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Avg First Day Return</div>
              <div className="text-2xl font-bold text-green-600">+{stats.avg_first_day_return}%</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Next IPO</div>
              <div className="text-lg font-bold">{stats.next_ipo?.ticker || '-'}</div>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              placeholder="Search by ticker..."
              value={searchTicker}
              onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
              className="border rounded px-3 py-2 flex-1"
            />
            <button onClick={searchIPO} className="bg-blue-600 text-white px-6 py-2 rounded">
              Search
            </button>
          </div>
          {searchResults && (
            <div className="mt-4 p-4 bg-gray-50 rounded grid grid-cols-6 gap-4">
              <div>
                <div className="text-xs text-gray-500">Ticker</div>
                <div className="font-bold">{searchResults.ticker}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Company</div>
                <div className="font-medium text-sm">{searchResults.company_name}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">IPO Date</div>
                <div className="font-medium">{searchResults.ipo_date}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Price Range</div>
                <div className="font-medium">${searchResults.price_range_low}-${searchResults.price_range_high}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Deal Size</div>
                <div className="font-medium">{formatMoney(searchResults.deal_size)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Status</div>
                <span className={`px-2 py-1 text-xs rounded ${
                  searchResults.status === 'priced' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {searchResults.status}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {['upcoming', 'recent', 'lockups', 'week', 'performance'].map((tab) => (
            <button
              key={tab}
              onClick={() => setView(tab)}
              className={`px-4 py-2 rounded capitalize ${view === tab ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            >
              {tab === 'lockups' ? 'Lockup Expirations' : tab}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center py-8">Loading...</div>
        ) : view === 'week' ? (
          <div className="grid grid-cols-7 gap-2">
            {Object.entries(weekCalendar).map(([day, ipos]) => (
              <div key={day} className="bg-white rounded-lg shadow p-3 min-h-32">
                <div className="font-semibold text-sm border-b pb-2 mb-2">{day.split(' ')[0]}</div>
                <div className="space-y-2">
                  {ipos.map((ipo, idx) => (
                    <div key={idx} className="text-xs p-2 bg-blue-50 rounded">
                      <div className="font-medium">{ipo.ticker}</div>
                      <div className="text-gray-500">${ipo.price_range_low}-${ipo.price_range_high}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Ticker</th>
                  <th className="text-left p-3">Company</th>
                  <th className="text-left p-3">Date</th>
                  <th className="text-left p-3">Exchange</th>
                  <th className="text-right p-3">Price Range</th>
                  <th className="text-right p-3">Deal Size</th>
                  {view === 'performance' && <th className="text-right p-3">Return</th>}
                  {view === 'lockups' && <th className="text-right p-3">Days Until</th>}
                  <th className="text-center p-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.map((ipo, idx) => (
                  <tr key={idx} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-bold">{ipo.ticker}</td>
                    <td className="p-3 text-sm">{ipo.company_name}</td>
                    <td className="p-3">{ipo.ipo_date}</td>
                    <td className="p-3">{ipo.exchange}</td>
                    <td className="p-3 text-right">
                      ${ipo.price_range_low}-${ipo.price_range_high}
                      {ipo.offer_price && <span className="text-green-600 ml-2">(${ipo.offer_price})</span>}
                    </td>
                    <td className="p-3 text-right">{formatMoney(ipo.deal_size)}</td>
                    {view === 'performance' && (
                      <td className={`p-3 text-right font-bold ${ipo.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {ipo.total_return >= 0 ? '+' : ''}{ipo.total_return}%
                      </td>
                    )}
                    {view === 'lockups' && (
                      <td className="p-3 text-right font-medium text-orange-600">
                        {ipo.days_until_lockup_expiry} days
                      </td>
                    )}
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 text-xs rounded ${
                        ipo.status === 'priced' ? 'bg-green-100 text-green-700' :
                        ipo.status === 'expected' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {ipo.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}
