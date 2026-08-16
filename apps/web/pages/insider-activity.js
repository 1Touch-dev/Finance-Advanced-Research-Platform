/**
 * Insider Activity Screener Page (Band C #41)
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function InsiderActivity() {
  const [view, setView] = useState('screen');
  const [data, setData] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ticker, setTicker] = useState('');
  const [sentiment, setSentiment] = useState(null);

  useEffect(() => {
    fetchStats();
    if (view === 'screen') fetchScreen();
    else if (view === 'cluster-buys') fetchClusterBuys();
    else if (view === 'cluster-sells') fetchClusterSells();
    else if (view === 'largest') fetchLargest();
    else if (view === 'ceo-cfo') fetchCeoCfo();
  }, [view]);

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/insider/stats`);
    if (res.ok) setStats(await res.json());
  };

  const fetchScreen = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/insider/screen?days=30&min_insiders=1`);
    if (res.ok) {
      const d = await res.json();
      setData(d.results || []);
    }
    setLoading(false);
  };

  const fetchClusterBuys = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/insider/cluster-buys?days=30&min_insiders=2`);
    if (res.ok) {
      const d = await res.json();
      setData(d.clusters || []);
    }
    setLoading(false);
  };

  const fetchClusterSells = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/insider/cluster-sells?days=30&min_insiders=2`);
    if (res.ok) {
      const d = await res.json();
      setData(d.clusters || []);
    }
    setLoading(false);
  };

  const fetchLargest = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/insider/largest?days=30&limit=20`);
    if (res.ok) {
      const d = await res.json();
      setData(d.transactions || []);
    }
    setLoading(false);
  };

  const fetchCeoCfo = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/insider/ceo-cfo?days=30`);
    if (res.ok) {
      const d = await res.json();
      setData(d.transactions || []);
    }
    setLoading(false);
  };

  const fetchSentiment = async () => {
    if (!ticker) return;
    const res = await fetch(`${API_BASE}/insider/sentiment/${ticker}`);
    if (res.ok) {
      const d = await res.json();
      setSentiment(d);
    }
  };

  const formatMoney = (value) => {
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
    return `$${value.toLocaleString()}`;
  };

  const getSignalColor = (signal) => {
    switch (signal) {
      case 'strong_buy': return 'bg-green-600 text-white';
      case 'buy': return 'bg-green-100 text-green-700';
      case 'neutral': return 'bg-gray-100 text-gray-700';
      case 'sell': return 'bg-red-100 text-red-700';
      case 'strong_sell': return 'bg-red-600 text-white';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getSignalLabel = (signal) => {
    return signal.replace('_', ' ').toUpperCase();
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Insider Activity Screener</h1>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-6 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Transactions</div>
              <div className="text-2xl font-bold">{stats.total_transactions}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Buys</div>
              <div className="text-2xl font-bold text-green-600">{stats.total_buys}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Sells</div>
              <div className="text-2xl font-bold text-red-600">{stats.total_sells}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Buy Value</div>
              <div className="text-2xl font-bold text-green-600">{formatMoney(stats.buy_value)}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Sell Value</div>
              <div className="text-2xl font-bold text-red-600">{formatMoney(stats.sell_value)}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Buy/Sell Ratio</div>
              <div className={`text-2xl font-bold ${stats.buy_sell_ratio >= 1 ? 'text-green-600' : 'text-red-600'}`}>
                {stats.buy_sell_ratio}x
              </div>
            </div>
          </div>
        )}

        {/* Ticker Lookup */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              placeholder="Enter ticker for sentiment analysis..."
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="border rounded px-3 py-2 flex-1"
            />
            <button onClick={fetchSentiment} className="bg-blue-600 text-white px-6 py-2 rounded">
              Analyze
            </button>
          </div>
          {sentiment && (
            <div className="mt-4 p-4 bg-gray-50 rounded">
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-xs text-gray-500">Ticker</div>
                  <div className="text-xl font-bold">{sentiment.ticker}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Signal</div>
                  <span className={`px-3 py-1 rounded text-sm font-bold ${getSignalColor(sentiment.signal)}`}>
                    {getSignalLabel(sentiment.signal)}
                  </span>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Buys</div>
                  <div className="font-bold text-green-600">{sentiment.total_buys} ({formatMoney(sentiment.buy_value)})</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Sells</div>
                  <div className="font-bold text-red-600">{sentiment.total_sells} ({formatMoney(sentiment.sell_value)})</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Net Value</div>
                  <div className={`font-bold text-lg ${sentiment.net_value >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {sentiment.net_value >= 0 ? '+' : ''}{formatMoney(sentiment.net_value)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'screen', label: 'Screener' },
            { key: 'cluster-buys', label: 'Cluster Buys' },
            { key: 'cluster-sells', label: 'Cluster Sells' },
            { key: 'largest', label: 'Largest Trades' },
            { key: 'ceo-cfo', label: 'CEO/CFO Only' },
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
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">Ticker</th>
                {(view === 'largest' || view === 'ceo-cfo') ? (
                  <>
                    <th className="text-left p-3">Insider</th>
                    <th className="text-left p-3">Title</th>
                    <th className="text-center p-3">Type</th>
                    <th className="text-right p-3">Shares</th>
                    <th className="text-right p-3">Price</th>
                  </>
                ) : (
                  <>
                    <th className="text-left p-3">Company</th>
                    <th className="text-right p-3">Insiders</th>
                    <th className="text-right p-3">Buy Value</th>
                    <th className="text-right p-3">Sell Value</th>
                  </>
                )}
                <th className="text-right p-3">Value</th>
                {view === 'screen' && <th className="text-center p-3">Signal</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="8" className="text-center p-8">Loading...</td></tr>
              ) : data.map((item, idx) => (
                <tr key={idx} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-bold">{item.ticker}</td>
                  {(view === 'largest' || view === 'ceo-cfo') ? (
                    <>
                      <td className="p-3">{item.insider_name}</td>
                      <td className="p-3 text-sm text-gray-500">{item.insider_title}</td>
                      <td className="p-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                          item.transaction_type === 'P' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        }`}>
                          {item.transaction_type === 'P' ? 'BUY' : 'SELL'}
                        </span>
                      </td>
                      <td className="p-3 text-right">{item.shares.toLocaleString()}</td>
                      <td className="p-3 text-right">${item.price.toFixed(2)}</td>
                    </>
                  ) : (
                    <>
                      <td className="p-3 text-sm">{item.company_name}</td>
                      <td className="p-3 text-right font-medium">{item.insider_count}</td>
                      <td className="p-3 text-right text-green-600">{formatMoney(item.buy_value || item.total_value)}</td>
                      <td className="p-3 text-right text-red-600">{formatMoney(item.sell_value || 0)}</td>
                    </>
                  )}
                  <td className={`p-3 text-right font-bold ${
                    (item.net_value || item.value) >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatMoney(Math.abs(item.net_value || item.value || item.total_value))}
                  </td>
                  {view === 'screen' && (
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${getSignalColor(item.signal)}`}>
                        {getSignalLabel(item.signal)}
                      </span>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
