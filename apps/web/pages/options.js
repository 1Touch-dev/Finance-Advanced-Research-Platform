/**
 * Implied Volatility Surface Page (Band B #27)
 *
 * Features:
 * - IV surface visualization
 * - Term structure analysis
 * - Skew analysis
 * - IV history and ranking
 * - Volatility screening
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── IV Snapshot Card ─────────────────────────────────────────────────────────

function IVSnapshotCard({ data }) {
  if (!data) return null;

  const ivHvColor = data.iv_hv_spread > 0 ? 'text-green-600' : 'text-red-600';
  const rankColor = data.iv_rank > 50 ? 'text-orange-600' : 'text-blue-600';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">{data.ticker}</h3>
          <p className="text-sm text-gray-500">IV Snapshot (Delayed EOD)</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-600">${data.current_price}</div>
          <div className={`text-sm font-medium ${rankColor}`}>
            IV Rank: {data.iv_rank}%
          </div>
        </div>
      </div>

      {/* IV Term Structure */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        {[
          { label: '30D IV', value: data.iv_30d },
          { label: '60D IV', value: data.iv_60d },
          { label: '90D IV', value: data.iv_90d },
        ].map((item, i) => (
          <div key={i} className="text-center p-3 bg-blue-50 rounded">
            <div className="text-xs text-blue-700">{item.label}</div>
            <div className="text-xl font-bold text-blue-600">{(item.value * 100).toFixed(1)}%</div>
          </div>
        ))}
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="p-3 bg-gray-50 rounded">
          <span className="text-gray-500">30D HV:</span>
          <span className="ml-2 font-semibold">{(data.hv_30d * 100).toFixed(1)}%</span>
        </div>
        <div className={`p-3 bg-gray-50 rounded ${ivHvColor}`}>
          <span className="text-gray-500">IV-HV Spread:</span>
          <span className="ml-2 font-semibold">
            {data.iv_hv_spread > 0 ? '+' : ''}{(data.iv_hv_spread * 100).toFixed(1)}%
          </span>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <span className="text-gray-500">Put-Call Skew:</span>
          <span className="ml-2 font-semibold">{(data.put_call_skew * 100).toFixed(1)}%</span>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <span className="text-gray-500">IV Percentile:</span>
          <span className="ml-2 font-semibold">{data.iv_percentile.toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
}

// ── Term Structure Chart ─────────────────────────────────────────────────────

function TermStructureChart({ data }) {
  if (!data?.term_structure?.length) return null;

  const terms = data.term_structure;
  const maxIV = Math.max(...terms.map(t => t.atm_iv));
  const minIV = Math.min(...terms.map(t => t.atm_iv));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">ATM IV Term Structure</h3>

      <div className="flex items-end gap-4 h-40">
        {terms.map((t, i) => {
          const height = ((t.atm_iv - minIV) / (maxIV - minIV || 1)) * 100 + 20;
          return (
            <div key={i} className="flex-1 flex flex-col items-center">
              <div className="text-xs text-gray-500 mb-1">{(t.atm_iv * 100).toFixed(1)}%</div>
              <div
                className="w-full bg-blue-500 rounded-t"
                style={{ height: `${height}%` }}
              />
              <div className="text-xs text-gray-500 mt-2">{t.expiry_months}M</div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 text-sm text-gray-600">
        {maxIV > minIV * 1.1
          ? 'Contango: Near-term IV lower than longer-term'
          : maxIV < minIV * 0.9
          ? 'Backwardation: Near-term IV elevated (event risk?)'
          : 'Flat term structure'}
      </div>
    </div>
  );
}

// ── Skew Analysis ────────────────────────────────────────────────────────────

function SkewAnalysis({ data }) {
  if (!data) return null;

  const skewColor = data.skew_25d > 0.02 ? 'text-orange-600' : data.skew_25d < -0.02 ? 'text-purple-600' : 'text-gray-600';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Skew Analysis</h3>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className={`p-4 bg-gray-50 rounded ${skewColor}`}>
          <div className="text-sm text-gray-500">25-Delta Skew</div>
          <div className="text-2xl font-bold">{(data.skew_25d * 100).toFixed(2)}%</div>
        </div>
        <div className="p-4 bg-gray-50 rounded">
          <div className="text-sm text-gray-500">10-Delta Skew</div>
          <div className="text-2xl font-bold">{(data.skew_10d * 100).toFixed(2)}%</div>
        </div>
      </div>

      <div className="p-4 bg-blue-50 rounded">
        <div className="text-sm font-medium text-blue-800">{data.interpretation}</div>
      </div>

      {/* Skew by Strike */}
      {data.skew_by_strike?.length > 0 && (
        <div className="mt-4">
          <div className="text-sm text-gray-500 mb-2">IV by Strike</div>
          <div className="flex items-end gap-1 h-24">
            {data.skew_by_strike.map((s, i) => {
              const maxDiff = Math.max(...data.skew_by_strike.map(x => Math.abs(x.iv_diff_from_atm || 0)));
              const height = 50 + (s.iv_diff_from_atm / (maxDiff || 1)) * 40;
              return (
                <div
                  key={i}
                  className={`flex-1 rounded-t ${s.moneyness < 1 ? 'bg-orange-400' : 'bg-blue-400'}`}
                  style={{ height: `${Math.max(10, height)}%` }}
                  title={`Strike: ${s.strike}, IV: ${(s.iv * 100).toFixed(1)}%`}
                />
              );
            })}
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>OTM Puts</span>
            <span>ATM</span>
            <span>OTM Calls</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── IV History Chart ─────────────────────────────────────────────────────────

function IVHistoryChart({ data }) {
  if (!data?.iv_history?.length) return null;

  const history = data.iv_history.slice(-90); // Last 90 days
  const maxIV = Math.max(...history.map(h => h.iv_30d));
  const minIV = Math.min(...history.map(h => h.iv_30d));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold">IV History (90 Days)</h3>
        <div className="text-sm text-gray-500">
          52W Range: {(data.iv_low_52w * 100).toFixed(0)}% - {(data.iv_high_52w * 100).toFixed(0)}%
        </div>
      </div>

      {/* Simple bar chart */}
      <div className="flex items-end gap-px h-32">
        {history.map((h, i) => {
          const height = ((h.iv_30d - minIV) / (maxIV - minIV || 1)) * 100;
          return (
            <div
              key={i}
              className="flex-1 bg-blue-400 hover:bg-blue-600"
              style={{ height: `${Math.max(5, height)}%` }}
              title={`${h.date}: ${(h.iv_30d * 100).toFixed(1)}%`}
            />
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div className="p-3 bg-green-50 rounded">
          <span className="text-gray-500">52W Low:</span>
          <span className="ml-2 font-semibold text-green-600">{(data.iv_low_52w * 100).toFixed(1)}%</span>
        </div>
        <div className="p-3 bg-red-50 rounded">
          <span className="text-gray-500">52W High:</span>
          <span className="ml-2 font-semibold text-red-600">{(data.iv_high_52w * 100).toFixed(1)}%</span>
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
            <th className="px-4 py-3 text-right">Price</th>
            <th className="px-4 py-3 text-right">30D IV</th>
            <th className="px-4 py-3 text-right">IV Rank</th>
            <th className="px-4 py-3 text-right">IV-HV</th>
            <th className="px-4 py-3 text-right">Skew</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {results.map((r, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-blue-600">{r.ticker}</td>
              <td className="px-4 py-3 text-right">${r.current_price}</td>
              <td className="px-4 py-3 text-right">{(r.iv_30d * 100).toFixed(1)}%</td>
              <td className={`px-4 py-3 text-right font-medium ${r.iv_rank > 50 ? 'text-orange-600' : 'text-blue-600'}`}>
                {r.iv_rank.toFixed(0)}%
              </td>
              <td className={`px-4 py-3 text-right ${r.iv_hv_spread > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {r.iv_hv_spread > 0 ? '+' : ''}{(r.iv_hv_spread * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-3 text-right">{(r.put_call_skew * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function OptionsPage() {
  const [activeTab, setActiveTab] = useState('snapshot');
  const [ticker, setTicker] = useState('NVDA');
  const [snapshot, setSnapshot] = useState(null);
  const [surface, setSurface] = useState(null);
  const [skew, setSkew] = useState(null);
  const [history, setHistory] = useState(null);
  const [screenResults, setScreenResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [snapRes, surfRes, skewRes, histRes] = await Promise.all([
        apiFetch(`/volatility/snapshot/${ticker}`),
        apiFetch(`/volatility/surface/${ticker}`),
        apiFetch(`/volatility/skew/${ticker}`),
        apiFetch(`/volatility/history/${ticker}`),
      ]);

      setSnapshot(await snapRes.json());
      setSurface(await surfRes.json());
      setSkew(await skewRes.json());
      setHistory(await histRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const runScreener = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/volatility/screen?min_iv_rank=0&max_iv_rank=100`);
      const data = await res.json();
      setScreenResults(data.results || []);
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
    if (activeTab === 'screen') {
      runScreener();
    }
  }, [activeTab]);

  return (
    <>
      <Head>
        <title>Volatility Analysis | Finance Intelligence</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Implied Volatility Analysis</h1>
            <p className="text-sm text-gray-500">IV surface, term structure, and skew (delayed EOD data)</p>
          </div>
        </header>

        {/* Tabs */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <nav className="flex space-x-8">
              {[
                { id: 'snapshot', label: 'IV Snapshot' },
                { id: 'term', label: 'Term Structure' },
                { id: 'skew', label: 'Skew' },
                { id: 'history', label: 'History' },
                { id: 'screen', label: 'Screener' },
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
        {activeTab !== 'screen' && (
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
                  {['NVDA', 'TSLA', 'AMD', 'AAPL', 'META', 'SPY'].map(t => (
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

        <main className="max-w-7xl mx-auto px-4 py-6">
          {loading && <div className="text-center py-8 text-gray-500">Loading...</div>}

          {!loading && activeTab === 'snapshot' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <IVSnapshotCard data={snapshot} />
              <TermStructureChart data={surface} />
            </div>
          )}

          {!loading && activeTab === 'term' && (
            <TermStructureChart data={surface} />
          )}

          {!loading && activeTab === 'skew' && (
            <SkewAnalysis data={skew} />
          )}

          {!loading && activeTab === 'history' && (
            <IVHistoryChart data={history} />
          )}

          {!loading && activeTab === 'screen' && (
            <ScreenerResults results={screenResults} />
          )}
        </main>
      </div>
    </>
  );
}
