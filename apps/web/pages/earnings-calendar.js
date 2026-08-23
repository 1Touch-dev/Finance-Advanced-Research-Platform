import { useState, useEffect } from 'react';
import Head from 'next/head';
import { getApiBaseUrl , apiFetch } from '../lib/api';

export default function EarningsCalendarPage() {
  const API = getApiBaseUrl();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('upcoming');
  const [data, setData] = useState([]);
  const [weekCalendar, setWeekCalendar] = useState({});
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState('');
  const [searchTicker, setSearchTicker] = useState('');
  const [tickerData, setTickerData] = useState(null);

  const tabs = [
    { id: 'upcoming', label: 'Upcoming (7 Days)' },
    { id: 'week', label: 'Weekly Calendar' },
    { id: 'surprises', label: 'Recent Surprises' },
  ];

  useEffect(() => {
    fetchStats();
    if (activeTab === 'upcoming') fetchUpcoming();
    else if (activeTab === 'week') fetchWeekCalendar();
    else if (activeTab === 'surprises') fetchSurprises();
  }, [activeTab]);

  async function fetchStats() {
    try {
      const res = await apiFetch(`/earnings/stats`);
      if (res.ok) setStats(await res.json());
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchUpcoming() {
    setLoading(true);
    try {
      const res = await apiFetch(`/earnings/upcoming?days=7`);
      if (res.ok) {
        const d = await res.json();
        setData(d.events || []);
      }
    } catch (e) {
      setErr(e.message);
    }
    setLoading(false);
  }

  async function fetchWeekCalendar() {
    setLoading(true);
    try {
      const res = await apiFetch(`/earnings/week`);
      if (res.ok) {
        const d = await res.json();
        setWeekCalendar(d.calendar || {});
      }
    } catch (e) {
      setErr(e.message);
    }
    setLoading(false);
  }

  async function fetchSurprises() {
    setLoading(true);
    try {
      const res = await apiFetch(`/earnings/surprises?min_surprise=5&days_back=30`);
      if (res.ok) {
        const d = await res.json();
        setData(d.surprises || []);
      }
    } catch (e) {
      setErr(e.message);
    }
    setLoading(false);
  }

  async function searchByTicker() {
    if (!searchTicker) return;
    try {
      const res = await apiFetch(`/earnings/ticker/${searchTicker}?quarters=8`);
      if (res.ok) {
        const d = await res.json();
        setTickerData(d);
      }
    } catch (e) {
      console.error(e);
    }
  }

  const importanceColor = (imp) => {
    if (imp === 'high') return 'bg-red-600';
    if (imp === 'medium') return 'bg-yellow-600';
    return 'bg-gray-600';
  };

  const sessionLabel = (session) => {
    if (session === 'pre_market') return 'BMO';
    if (session === 'after_hours') return 'AMC';
    return 'TBD';
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Earnings Calendar | Finance Platform</title>
      </Head>

      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Earnings Calendar</h1>
        <p className="text-gray-400 mb-6">Finnhub Earnings Data — Upcoming, Surprises, EPS Estimates</p>

        {/* Stats Banner */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">{stats.this_week}</div>
              <div className="text-xs text-gray-400">This Week</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-purple-400">{stats.next_week}</div>
              <div className="text-xs text-gray-400">Next Week</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{stats.beats_this_week}</div>
              <div className="text-xs text-gray-400">Beats</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-400">{stats.misses_this_week}</div>
              <div className="text-xs text-gray-400">Misses</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-yellow-400">+{stats.avg_surprise_percent}%</div>
              <div className="text-xs text-gray-400">Avg Surprise</div>
            </div>
          </div>
        )}

        {/* Ticker Search */}
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={searchTicker}
              onChange={e => setSearchTicker(e.target.value.toUpperCase())}
              placeholder="Search ticker (e.g., AAPL, MSFT, NVDA)"
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
              onKeyPress={e => e.key === 'Enter' && searchByTicker()}
            />
            <button
              onClick={searchByTicker}
              className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg"
            >
              Search
            </button>
          </div>
          {tickerData && (
            <div className="mt-4">
              <div className="font-semibold mb-2">{tickerData.ticker} — {tickerData.quarters} Quarters</div>
              <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
                {tickerData.history.map((q, idx) => (
                  <div key={idx} className="p-2 bg-gray-700 rounded text-center text-sm">
                    <div className="text-gray-400 text-xs">{q.fiscal_quarter} {q.fiscal_year}</div>
                    <div className={`font-semibold ${q.surprise_percent > 0 ? 'text-green-400' : q.surprise_percent < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                      {q.eps_actual !== null ? `$${q.eps_actual}` : '-'}
                    </div>
                    {q.surprise_percent !== null && (
                      <div className={`text-xs ${q.surprise_percent > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {q.surprise_percent > 0 ? '+' : ''}{q.surprise_percent}%
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg whitespace-nowrap text-sm font-medium ${
                activeTab === tab.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading && <div className="text-blue-400 mb-4">Loading earnings...</div>}
        {err && <div className="text-red-400 mb-4">Error: {err}</div>}

        {/* Upcoming & Surprises Table */}
        {!loading && activeTab !== 'week' && (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-700">
                <tr>
                  <th className="text-left py-3 px-4">Ticker</th>
                  <th className="text-left py-3 px-4">Date</th>
                  <th className="text-center py-3 px-4">Session</th>
                  <th className="text-left py-3 px-4">Quarter</th>
                  <th className="text-right py-3 px-4">EPS Est</th>
                  {activeTab === 'surprises' && <th className="text-right py-3 px-4">EPS Act</th>}
                  {activeTab === 'surprises' && <th className="text-right py-3 px-4">Surprise</th>}
                  <th className="text-center py-3 px-4">Importance</th>
                </tr>
              </thead>
              <tbody>
                {data.map((event, idx) => (
                  <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700/50">
                    <td className="py-3 px-4 font-semibold">{event.ticker}</td>
                    <td className="py-3 px-4">{event.earnings_date}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-1 rounded text-xs ${
                        event.session === 'pre_market' ? 'bg-yellow-600' :
                        event.session === 'after_hours' ? 'bg-purple-600' : 'bg-gray-600'
                      }`}>
                        {sessionLabel(event.session)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400">{event.fiscal_quarter} {event.fiscal_year}</td>
                    <td className="py-3 px-4 text-right">{event.eps_estimate !== null ? `$${event.eps_estimate}` : '-'}</td>
                    {activeTab === 'surprises' && (
                      <td className="py-3 px-4 text-right">{event.eps_actual !== null ? `$${event.eps_actual}` : '-'}</td>
                    )}
                    {activeTab === 'surprises' && (
                      <td className={`py-3 px-4 text-right font-semibold ${
                        event.surprise_percent > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {event.surprise_percent !== null ? `${event.surprise_percent > 0 ? '+' : ''}${event.surprise_percent}%` : '-'}
                      </td>
                    )}
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-1 rounded text-xs ${importanceColor(event.importance)}`}>
                        {event.importance || 'medium'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Weekly Calendar View */}
        {!loading && activeTab === 'week' && (
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(weekCalendar).map(([date, events]) => (
              <div key={date} className="bg-gray-800 rounded-lg p-3 min-h-40">
                <div className="font-semibold text-sm border-b border-gray-700 pb-2 mb-2">
                  {new Date(date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                </div>
                <div className="space-y-2">
                  {events.length === 0 ? (
                    <div className="text-gray-500 text-xs">No earnings</div>
                  ) : (
                    events.slice(0, 8).map((e, idx) => (
                      <div key={idx} className="p-2 bg-gray-700 rounded text-xs">
                        <div className="flex justify-between items-center">
                          <span className="font-semibold">{e.ticker}</span>
                          <span className={`px-1 rounded text-xs ${
                            e.session === 'pre_market' ? 'bg-yellow-600' : 'bg-purple-600'
                          }`}>
                            {sessionLabel(e.session)}
                          </span>
                        </div>
                        {e.eps_estimate && (
                          <div className="text-gray-400 mt-1">Est: ${e.eps_estimate}</div>
                        )}
                      </div>
                    ))
                  )}
                  {events.length > 8 && (
                    <div className="text-gray-400 text-xs text-center">+{events.length - 8} more</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <p className="text-gray-500 text-xs mt-6 text-center">
          Data source: Finnhub Earnings Calendar (FREE tier) | Updated in real-time
        </p>
      </div>
    </div>
  );
}
