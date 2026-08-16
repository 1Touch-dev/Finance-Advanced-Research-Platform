/**
 * Earnings Calendar Page (Band C #36)
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function EarningsCalendar() {
  const [view, setView] = useState('upcoming');
  const [events, setEvents] = useState([]);
  const [weekCalendar, setWeekCalendar] = useState({});
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState('');

  useEffect(() => {
    fetchStats();
    if (view === 'upcoming') fetchUpcoming();
    else if (view === 'week') fetchWeek();
    else if (view === 'surprises') fetchSurprises();
  }, [view]);

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/earnings/stats`);
    if (res.ok) setStats(await res.json());
  };

  const fetchUpcoming = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/earnings/upcoming?days=14`);
    if (res.ok) {
      const data = await res.json();
      setEvents(data.events || []);
    }
    setLoading(false);
  };

  const fetchWeek = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/earnings/week`);
    if (res.ok) {
      const data = await res.json();
      setWeekCalendar(data.calendar || {});
    }
    setLoading(false);
  };

  const fetchSurprises = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/earnings/surprises?min_surprise=5`);
    if (res.ok) {
      const data = await res.json();
      setEvents(data.surprises || []);
    }
    setLoading(false);
  };

  const fetchTickerHistory = async () => {
    if (!selectedTicker) return;
    setLoading(true);
    const res = await fetch(`${API_BASE}/earnings/ticker/${selectedTicker}`);
    if (res.ok) {
      const data = await res.json();
      setEvents(data.history || []);
      setView('ticker');
    }
    setLoading(false);
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Earnings Calendar</h1>

        {/* Stats Summary */}
        {stats && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">This Week</div>
              <div className="text-2xl font-bold">{stats.this_week}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Next Week</div>
              <div className="text-2xl font-bold">{stats.next_week}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Beats This Week</div>
              <div className="text-2xl font-bold text-green-600">{stats.beats_this_week}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Avg Surprise</div>
              <div className="text-2xl font-bold">{stats.avg_surprise_percent}%</div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setView('upcoming')}
            className={`px-4 py-2 rounded ${view === 'upcoming' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Upcoming
          </button>
          <button
            onClick={() => setView('week')}
            className={`px-4 py-2 rounded ${view === 'week' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Week View
          </button>
          <button
            onClick={() => setView('surprises')}
            className={`px-4 py-2 rounded ${view === 'surprises' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Surprises
          </button>
          <div className="flex gap-2 ml-auto">
            <input
              type="text"
              placeholder="Ticker..."
              value={selectedTicker}
              onChange={(e) => setSelectedTicker(e.target.value.toUpperCase())}
              className="border rounded px-3 py-2"
            />
            <button onClick={fetchTickerHistory} className="bg-gray-600 text-white px-4 py-2 rounded">
              Search
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center py-8">Loading...</div>
        ) : view === 'week' ? (
          <div className="grid grid-cols-5 gap-4">
            {Object.entries(weekCalendar).map(([date, dayEvents]) => (
              <div key={date} className="bg-white rounded-lg shadow p-4">
                <div className="font-semibold border-b pb-2 mb-2">{date}</div>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {dayEvents.map((event, idx) => (
                    <div key={idx} className="text-sm p-2 bg-gray-50 rounded">
                      <div className="font-medium">{event.ticker}</div>
                      <div className="text-xs text-gray-500">{event.session}</div>
                      <div className="text-xs">Est: ${event.eps_estimate}</div>
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
                  <th className="text-left p-3">Session</th>
                  <th className="text-right p-3">EPS Est</th>
                  <th className="text-right p-3">EPS Act</th>
                  <th className="text-right p-3">Surprise</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event, idx) => (
                  <tr key={idx} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{event.ticker}</td>
                    <td className="p-3">{event.company_name}</td>
                    <td className="p-3">{event.earnings_date}</td>
                    <td className="p-3 text-sm">{event.session}</td>
                    <td className="p-3 text-right">${event.eps_estimate?.toFixed(2) || '-'}</td>
                    <td className="p-3 text-right">${event.eps_actual?.toFixed(2) || '-'}</td>
                    <td className={`p-3 text-right ${event.surprise_percent > 0 ? 'text-green-600' : event.surprise_percent < 0 ? 'text-red-600' : ''}`}>
                      {event.surprise_percent ? `${event.surprise_percent > 0 ? '+' : ''}${event.surprise_percent}%` : '-'}
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
