import { useEffect, useState } from 'react';
import { getApiBaseUrl , apiFetch } from '../lib/api';
import Head from 'next/head';

export default function MacroDashboardPage() {
  const API = getApiBaseUrl();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [err, setErr] = useState('');
  const [selectedSeries, setSelectedSeries] = useState('');
  const [vintageDate, setVintageDate] = useState('');
  const [vintageData, setVintageData] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    apiFetch(`/market/macro/dashboard`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        setDashboard(data);
        setLoading(false);
      })
      .catch(e => {
        setErr(e.message);
        setLoading(false);
      });
  }, [API]);

  async function fetchVintage() {
    if (!selectedSeries || !vintageDate) return;
    try {
      const res = await apiFetch(`/market/macro/vintage?series_id=${selectedSeries}&vintage_date=${vintageDate}`);
      setVintageData(await res.json());
    } catch (e) {
      console.error(e);
    }
  }

  async function searchFred() {
    if (!searchQuery) return;
    try {
      const res = await apiFetch(`/market/fred/search?query=${encodeURIComponent(searchQuery)}`);
      setSearchResults(await res.json());
    } catch (e) {
      console.error(e);
    }
  }

  const categoryColors = {
    'Growth': 'bg-green-600',
    'Inflation': 'bg-red-600',
    'Employment': 'bg-blue-600',
    'Interest Rates': 'bg-purple-600',
    'Money Supply': 'bg-yellow-600',
    'Housing': 'bg-orange-600',
    'Consumer': 'bg-pink-600',
    'Trade': 'bg-cyan-600',
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Macro Dashboard | FRED Data | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-2">Macro Economic Dashboard</h1>
      <p className="text-gray-400 mb-6">Federal Reserve Economic Data (FRED) — 23 Key Indicators + ALFRED Vintages</p>

      {loading && <div className="text-blue-400 mb-4">Loading FRED data...</div>}
      {err && <div className="text-red-400 mb-4">Error: {err}</div>}

      {/* Search Section */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Search FRED Series</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search economic indicators (e.g., unemployment, inflation)"
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
            onKeyPress={e => e.key === 'Enter' && searchFred()}
          />
          <button
            onClick={searchFred}
            className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg"
          >
            Search
          </button>
        </div>
        {searchResults?.results && (
          <div className="mt-4 max-h-48 overflow-y-auto">
            {searchResults.results.map((r, idx) => (
              <div key={idx} className="p-2 border-b border-gray-700 text-sm">
                <span className="font-semibold text-blue-400">{r.id}</span> — {r.title}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ALFRED Vintage Section */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">ALFRED Point-in-Time Data</h2>
        <p className="text-gray-400 text-sm mb-3">Get historical data as it was known on a specific date (prevents look-ahead bias)</p>
        <div className="flex gap-3 flex-wrap">
          <select
            value={selectedSeries}
            onChange={e => setSelectedSeries(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
          >
            <option value="">Select Series</option>
            {dashboard?.series && Object.keys(dashboard.series).map(key => (
              <option key={key} value={key}>{key} - {dashboard.series[key]?.name}</option>
            ))}
          </select>
          <input
            type="date"
            value={vintageDate}
            onChange={e => setVintageDate(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
          />
          <button
            onClick={fetchVintage}
            disabled={!selectedSeries || !vintageDate}
            className="bg-purple-600 hover:bg-purple-500 px-6 py-2 rounded-lg disabled:opacity-50"
          >
            Get Vintage
          </button>
        </div>
        {vintageData?.data && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-2">Date</th>
                  <th className="text-left py-2">Value</th>
                </tr>
              </thead>
              <tbody>
                {vintageData.data.map((row, idx) => (
                  <tr key={idx} className="border-b border-gray-700/50">
                    <td className="py-1">{row.date}</td>
                    <td className="py-1">{row.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Main Dashboard Grid */}
      {dashboard?.series && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Object.entries(dashboard.series).map(([id, data]) => (
            <div key={id} className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className={`px-2 py-0.5 rounded text-xs ${categoryColors[data.category] || 'bg-gray-600'}`}>
                  {data.category || 'Other'}
                </span>
                <span className="text-gray-500 text-xs">{data.frequency}</span>
              </div>
              <h3 className="font-semibold text-sm mb-1">{data.name}</h3>
              <div className="text-2xl font-bold text-blue-400">
                {data.latest_value || 'N/A'}
                <span className="text-sm text-gray-400 ml-1">{data.units?.slice(0, 10)}</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Series: {id} | {data.latest_date || ''}
              </div>
            </div>
          ))}
        </div>
      )}

      {!dashboard?.series && !loading && (
        <div className="bg-gray-800 rounded-lg p-6 text-center">
          <p className="text-gray-400">No FRED data available. Check FRED_API_KEY in .env</p>
        </div>
      )}

      <p className="text-gray-500 text-xs mt-6 text-center">
        Data source: Federal Reserve Economic Data (FRED) via St. Louis Fed | ALFRED for point-in-time vintages
      </p>
    </div>
  );
}
