/**
 * Whisper Estimates Page (Band B #25)
 *
 * Features:
 * - Whisper vs consensus estimates
 * - Buy-side vs sell-side analysis
 * - Whisper accuracy history
 * - Estimate dispersion by analyst type
 * - Whisper screening
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Direction Badge ──────────────────────────────────────────────────────────

function DirectionBadge({ direction }) {
  const colors = {
    above: 'bg-green-500 text-white',
    below: 'bg-red-500 text-white',
    inline: 'bg-gray-400 text-white',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-bold ${colors[direction] || 'bg-gray-300'}`}>
      {direction?.toUpperCase()}
    </span>
  );
}

// ── Whisper Snapshot Card ────────────────────────────────────────────────────

function WhisperSnapshotCard({ data }) {
  if (!data) return null;

  const epsColor = data.eps_whisper_vs_consensus >= 0 ? 'text-green-600' : 'text-red-600';
  const revColor = data.revenue_whisper_vs_consensus >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">{data.ticker}</h3>
          <p className="text-sm text-gray-500">Whisper Snapshot</p>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-500">Beat Probability</div>
          <div className="text-2xl font-bold text-blue-600">{data.beat_probability}%</div>
        </div>
      </div>

      {/* EPS & Revenue */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-xs text-blue-700 mb-1">EPS Whisper</div>
          <div className="text-xl font-bold text-blue-600">${data.eps_whisper?.toFixed(2)}</div>
          <div className="text-xs text-gray-500">
            Consensus: ${data.eps_consensus?.toFixed(2)}
          </div>
          <div className={`text-sm font-medium ${epsColor}`}>
            {data.eps_whisper_vs_consensus > 0 ? '+' : ''}{data.eps_whisper_vs_consensus?.toFixed(1)}%
          </div>
        </div>
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-xs text-blue-700 mb-1">Revenue Whisper</div>
          <div className="text-xl font-bold text-blue-600">${(data.revenue_whisper / 1_000_000_000).toFixed(2)}B</div>
          <div className="text-xs text-gray-500">
            Consensus: ${(data.revenue_consensus / 1_000_000_000).toFixed(2)}B
          </div>
          <div className={`text-sm font-medium ${revColor}`}>
            {data.revenue_whisper_vs_consensus > 0 ? '+' : ''}{data.revenue_whisper_vs_consensus?.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Earnings Date */}
      <div className="p-3 bg-gray-50 rounded text-center">
        <span className="text-gray-500 text-sm">Next Earnings:</span>
        <span className="ml-2 font-semibold">{data.earnings_date}</span>
      </div>
    </div>
  );
}

// ── Side Split Analysis Card ─────────────────────────────────────────────────

function SideSplitCard({ data }) {
  if (!data) return null;

  const spreadColor = data.buy_vs_sell_spread > 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Buy-Side vs Sell-Side Analysis</h3>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Buy Side */}
        <div className="p-4 bg-green-50 rounded">
          <div className="text-sm text-green-700 font-medium mb-2">Buy-Side</div>
          <div className="text-2xl font-bold text-green-600">${data.buy_side_mean?.toFixed(2)}</div>
          <div className="text-xs text-gray-500 mt-1">
            {data.buy_side_count} estimates | Std: ${data.buy_side_std?.toFixed(2)}
          </div>
        </div>

        {/* Sell Side */}
        <div className="p-4 bg-orange-50 rounded">
          <div className="text-sm text-orange-700 font-medium mb-2">Sell-Side</div>
          <div className="text-2xl font-bold text-orange-600">${data.sell_side_mean?.toFixed(2)}</div>
          <div className="text-xs text-gray-500 mt-1">
            {data.sell_side_count} estimates | Std: ${data.sell_side_std?.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Spread */}
      <div className="p-4 bg-gray-50 rounded mb-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-500">Buy-Sell Spread:</span>
          <span className={`text-xl font-bold ${spreadColor}`}>
            {data.buy_vs_sell_spread > 0 ? '+' : ''}{data.buy_vs_sell_spread?.toFixed(1)}%
          </span>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Bullish Side: {data.bullish_side === 'buy_side' ? 'Buy-Side' : 'Sell-Side'}
        </div>
      </div>

      {/* Interpretation */}
      <div className="p-3 bg-blue-50 rounded">
        <div className="text-sm text-blue-800">{data.interpretation}</div>
      </div>
    </div>
  );
}

// ── History Chart ────────────────────────────────────────────────────────────

function HistoryChart({ data }) {
  if (!data?.periods?.length) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold">Whisper Accuracy History</h3>
        <div className="text-sm">
          <span className="text-green-600 font-medium">Whisper: {data.whisper_accuracy_rate}%</span>
          <span className="mx-2 text-gray-400">vs</span>
          <span className="text-blue-600 font-medium">Consensus: {data.consensus_accuracy_rate}%</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">Period</th>
              <th className="px-3 py-2 text-right">Actual</th>
              <th className="px-3 py-2 text-right">Whisper</th>
              <th className="px-3 py-2 text-right">Consensus</th>
              <th className="px-3 py-2 text-center">Closer</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.periods.map((p, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-3 py-2 font-medium">{p.period}</td>
                <td className="px-3 py-2 text-right">${p.actual?.toFixed(2)}</td>
                <td className="px-3 py-2 text-right text-green-600">${p.whisper?.toFixed(2)}</td>
                <td className="px-3 py-2 text-right text-blue-600">${p.consensus?.toFixed(2)}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    p.whisper_closer ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {p.whisper_closer ? 'Whisper' : 'Consensus'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Dispersion Card ──────────────────────────────────────────────────────────

function DispersionCard({ data }) {
  if (!data) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Estimate Dispersion by Side</h3>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-4 bg-gray-50 rounded">
          <div className="text-sm text-gray-500 mb-1">Buy-Side Dispersion</div>
          <div className="text-xl font-bold">{(data.buy_side_dispersion * 100).toFixed(1)}%</div>
          <div className={`text-xs ${data.buy_side_trend === 'tightening' ? 'text-green-600' : 'text-red-600'}`}>
            {data.buy_side_trend}
          </div>
        </div>
        <div className="p-4 bg-gray-50 rounded">
          <div className="text-sm text-gray-500 mb-1">Sell-Side Dispersion</div>
          <div className="text-xl font-bold">{(data.sell_side_dispersion * 100).toFixed(1)}%</div>
          <div className={`text-xs ${data.sell_side_trend === 'tightening' ? 'text-green-600' : 'text-red-600'}`}>
            {data.sell_side_trend}
          </div>
        </div>
      </div>

      <div className="p-3 bg-blue-50 rounded">
        <div className="text-sm text-blue-800">
          {data.buy_side_dispersion < data.sell_side_dispersion
            ? 'Buy-side analysts show more agreement than sell-side'
            : 'Sell-side analysts show more agreement than buy-side'}
        </div>
      </div>
    </div>
  );
}

// ── Screener Results ─────────────────────────────────────────────────────────

function ScreenerResults({ results }) {
  if (!results?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No results match your criteria
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left">Ticker</th>
            <th className="px-4 py-3 text-right">Whisper</th>
            <th className="px-4 py-3 text-right">Consensus</th>
            <th className="px-4 py-3 text-right">Spread</th>
            <th className="px-4 py-3 text-center">Direction</th>
            <th className="px-4 py-3 text-right">Confidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {results.map((r, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-blue-600">{r.ticker}</td>
              <td className="px-4 py-3 text-right">${r.whisper?.toFixed(2)}</td>
              <td className="px-4 py-3 text-right">${r.consensus?.toFixed(2)}</td>
              <td className={`px-4 py-3 text-right font-medium ${
                r.whisper_vs_consensus > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {r.whisper_vs_consensus > 0 ? '+' : ''}{r.whisper_vs_consensus?.toFixed(1)}%
              </td>
              <td className="px-4 py-3 text-center">
                <DirectionBadge direction={r.direction} />
              </td>
              <td className="px-4 py-3 text-right">{(r.confidence * 100).toFixed(0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Compare Results ──────────────────────────────────────────────────────────

function CompareResults({ data }) {
  if (!data?.comparisons?.length) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold">Whisper Comparison: {data.metric?.toUpperCase()}</h3>
        <div className="text-sm text-gray-500">
          Most bullish: <span className="text-green-600 font-medium">{data.most_bullish_whisper}</span>
        </div>
      </div>

      <div className="space-y-3">
        {data.comparisons.map((c, i) => (
          <div key={i} className="flex items-center gap-4 p-3 bg-gray-50 rounded">
            <div className="w-16 font-medium text-blue-600">{c.ticker}</div>
            <div className="flex-1">
              <div className="flex justify-between text-sm mb-1">
                <span>Whisper: ${c.whisper?.toFixed(2)}</span>
                <span className="text-gray-500">Consensus: ${c.consensus?.toFixed(2)}</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${c.whisper_vs_consensus > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                  style={{ width: `${Math.min(Math.abs(c.whisper_vs_consensus) * 10, 100)}%` }}
                />
              </div>
            </div>
            <div className={`w-20 text-right font-medium ${
              c.whisper_vs_consensus > 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {c.whisper_vs_consensus > 0 ? '+' : ''}{c.whisper_vs_consensus?.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function WhisperPage() {
  const [activeTab, setActiveTab] = useState('snapshot');
  const [ticker, setTicker] = useState('NVDA');
  const [snapshot, setSnapshot] = useState(null);
  const [sideSplit, setSideSplit] = useState(null);
  const [history, setHistory] = useState(null);
  const [dispersion, setDispersion] = useState(null);
  const [screenResults, setScreenResults] = useState([]);
  const [compareData, setCompareData] = useState(null);
  const [compareTickers, setCompareTickers] = useState('NVDA,AAPL,MSFT,GOOGL');
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [snapRes, sideRes, histRes, dispRes] = await Promise.all([
        apiFetch(`/whisper/${ticker}/snapshot`),
        apiFetch(`/whisper/${ticker}/side-split`),
        apiFetch(`/whisper/${ticker}/history`),
        apiFetch(`/whisper/${ticker}/dispersion`),
      ]);

      setSnapshot(await snapRes.json());
      setSideSplit(await sideRes.json());
      setHistory(await histRes.json());
      setDispersion(await dispRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const runScreener = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/whisper/screen`);
      const data = await res.json();
      setScreenResults(data.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const runCompare = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/whisper/compare?tickers=${compareTickers}`);
      const data = await res.json();
      setCompareData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [ticker]);

  useEffect(() => {
    if (activeTab === 'screen') runScreener();
    if (activeTab === 'compare') runCompare();
  }, [activeTab]);

  return (
    <>
      <Head>
        <title>Whisper Estimates | Finance Intelligence</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Whisper Estimates</h1>
            <p className="text-sm text-gray-500">Unofficial street expectations &amp; buy/sell-side analysis</p>
          </div>
        </header>

        {/* Tabs */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <nav className="flex space-x-8">
              {[
                { id: 'snapshot', label: 'Snapshot' },
                { id: 'side-split', label: 'Side Split' },
                { id: 'history', label: 'History' },
                { id: 'dispersion', label: 'Dispersion' },
                { id: 'screen', label: 'Screener' },
                { id: 'compare', label: 'Compare' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Ticker Selector */}
        {!['screen', 'compare'].includes(activeTab) && (
          <div className="bg-white border-b">
            <div className="max-w-7xl mx-auto px-4 py-4">
              <div className="flex gap-4 items-center">
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="px-4 py-2 border rounded-lg w-32"
                  placeholder="Ticker"
                />
                <button
                  onClick={fetchData}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Analyze
                </button>
                <div className="flex gap-2 ml-4">
                  {['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA'].map(t => (
                    <button
                      key={t}
                      onClick={() => setTicker(t)}
                      className={`px-3 py-1 text-sm rounded-full border ${
                        ticker === t ? 'bg-blue-100 border-blue-500' : 'border-gray-300'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Compare Input */}
        {activeTab === 'compare' && (
          <div className="bg-white border-b">
            <div className="max-w-7xl mx-auto px-4 py-4">
              <div className="flex gap-4 items-center">
                <input
                  type="text"
                  value={compareTickers}
                  onChange={(e) => setCompareTickers(e.target.value.toUpperCase())}
                  className="px-4 py-2 border rounded-lg flex-1"
                  placeholder="NVDA,AAPL,MSFT,GOOGL"
                />
                <button
                  onClick={runCompare}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Compare
                </button>
              </div>
            </div>
          </div>
        )}

        <main className="max-w-7xl mx-auto px-4 py-6">
          {loading && <div className="text-center py-8 text-gray-500">Loading...</div>}

          {!loading && activeTab === 'snapshot' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <WhisperSnapshotCard data={snapshot} />
              <SideSplitCard data={sideSplit} />
            </div>
          )}

          {!loading && activeTab === 'side-split' && (
            <SideSplitCard data={sideSplit} />
          )}

          {!loading && activeTab === 'history' && (
            <HistoryChart data={history} />
          )}

          {!loading && activeTab === 'dispersion' && (
            <DispersionCard data={dispersion} />
          )}

          {!loading && activeTab === 'screen' && (
            <ScreenerResults results={screenResults} />
          )}

          {!loading && activeTab === 'compare' && (
            <CompareResults data={compareData} />
          )}
        </main>
      </div>
    </>
  );
}
