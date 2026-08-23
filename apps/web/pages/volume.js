/**
 * Volume Screening Page (Band B #28)
 *
 * Features:
 * - Unusual volume alerts
 * - Volume profile analysis
 * - Sector volume flow
 * - Historical volume patterns
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Signal Badge ──────────────────────────────────────────────────────────────

function SignalBadge({ signal }) {
  const colors = {
    extreme_spike: 'bg-red-500 text-white',
    high_volume: 'bg-orange-500 text-white',
    elevated: 'bg-yellow-500 text-yellow-900',
    normal: 'bg-gray-300 text-gray-700',
    low: 'bg-blue-300 text-blue-900',
    extreme_low: 'bg-blue-500 text-white',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-bold ${colors[signal] || 'bg-gray-300'}`}>

      {signal?.replace(/_/g, ' ').toUpperCase()}
    </span>
  );
}

// ── Alert Card ────────────────────────────────────────────────────────────────

function AlertCard({ alert }) {
  const priceColor = alert.price_change_pct >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-blue-600">{alert.ticker}</span>
            <SignalBadge signal={alert.signal} />
          </div>
          <p className="text-sm text-gray-500">{alert.company_name}</p>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold">{alert.volume_ratio}x</div>
          <div className="text-xs text-gray-500">vs avg</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="text-center p-2 bg-gray-50 rounded">
          <div className="text-gray-500 text-xs">Volume</div>
          <div className="font-medium">{(alert.volume / 1_000_000).toFixed(1)}M</div>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded">
          <div className="text-gray-500 text-xs">Price</div>
          <div className="font-medium">${alert.price?.toFixed(2)}</div>
        </div>
        <div className={`text-center p-2 bg-gray-50 rounded ${priceColor}`}>
          <div className="text-gray-500 text-xs">Change</div>
          <div className="font-medium">{alert.price_change_pct > 0 ? '+' : ''}{alert.price_change_pct}%</div>
        </div>
      </div>

      {alert.pattern && (
        <div className="mt-3">
          <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
            {alert.pattern?.replace(/_/g, ' ')}
          </span>
        </div>
      )}
    </div>
  );
}

// ── Volume Profile Card ───────────────────────────────────────────────────────

function VolumeProfileCard({ data }) {
  if (!data) return null;

  const getTrendIcon = (trend) => {
    if (trend === 'increasing') return '↑';
    if (trend === 'decreasing') return '↓';
    return '→';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">{data.ticker} Volume Profile</h3>
          <p className="text-sm text-gray-500">{data.company_name}</p>
        </div>
        <SignalBadge signal={data.latest?.signal} />
      </div>

      {/* Averages */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {['10d', '20d', '50d', '90d'].map(period => (
          <div key={period} className="text-center p-3 bg-gray-50 rounded">
            <div className="text-xs text-gray-500">Avg {period}</div>
            <div className="font-semibold">{(data.averages?.[period] / 1_000_000).toFixed(1)}M</div>
          </div>
        ))}
      </div>

      {/* Latest */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-sm text-blue-700">Latest Volume</div>
          <div className="text-xl font-bold text-blue-600">{(data.latest?.volume / 1_000_000).toFixed(1)}M</div>
        </div>
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-sm text-blue-700">Ratio</div>
          <div className="text-xl font-bold text-blue-600">{data.latest?.ratio}x</div>
        </div>
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-sm text-blue-700">Trend {getTrendIcon(data.patterns?.trend)}</div>
          <div className="text-xl font-bold text-blue-600 capitalize">{data.patterns?.trend}</div>
        </div>
      </div>

      {/* Patterns */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="p-3 bg-gray-50 rounded">
          <span className="text-gray-500">Spikes (30d):</span>
          <span className="ml-2 font-semibold">{data.patterns?.spikes_30d}</span>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <span className="text-gray-500">Volatility:</span>
          <span className="ml-2 font-semibold">{(data.patterns?.volatility * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function VolumePage() {
  const [activeTab, setActiveTab] = useState('alerts');
  const [alerts, setAlerts] = useState([]);
  const [ticker, setTicker] = useState('NVDA');
  const [profile, setProfile] = useState(null);
  const [minRatio, setMinRatio] = useState(2.0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/volume/screen?min_ratio=${minRatio}`);
      const data = await res.json();
      setAlerts(data.alerts || []);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/volume/profile/${ticker}`);
      const data = await res.json();
      setProfile(data);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  useEffect(() => {
    if (activeTab === 'profile') {
      fetchProfile();
    }
  }, [activeTab, ticker]);

  return (
    <>
      <Head>
        <title>Volume Screening | Finance Intelligence</title>
      </Head>

      <div className="research-dark min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Volume Screening</h1>
            <p className="text-sm text-gray-500">Unusual volume detection and analysis (delayed EOD data)</p>
          </div>
        </header>

        {/* Tabs */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <nav className="flex space-x-8">
              {[
                { id: 'alerts', label: 'Volume Alerts' },
                { id: 'profile', label: 'Ticker Profile' },
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

        <main className="max-w-7xl mx-auto px-4 py-6">
          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="space-y-4">
              <div className="flex gap-4 items-center">
                <label className="text-sm text-gray-600">Min Ratio:</label>
                <input
                  type="number"
                  value={minRatio}
                  onChange={(e) => setMinRatio(parseFloat(e.target.value))}
                  step="0.5"
                  min="1"
                  className="w-20 px-3 py-2 border rounded-lg"
                />
                <button
                  onClick={fetchAlerts}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Screen
                </button>
                <span className="text-sm text-gray-500">{alerts.length} alerts found</span>
              </div>

              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {alerts.map((alert, i) => (
                    <AlertCard key={i} alert={alert} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="space-y-4">
              <div className="flex gap-4 items-center">
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="Ticker"
                  className="w-32 px-4 py-2 border rounded-lg"
                />
                <button
                  onClick={fetchProfile}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Analyze
                </button>
                <div className="flex gap-2 ml-4">
                  {['NVDA', 'TSLA', 'AMD', 'AAPL', 'META'].map(t => (
                    <button
                      key={t}
                      onClick={() => setTicker(t)}
                      className={`px-3 py-1 text-sm rounded-full border ${ticker === t ? 'bg-blue-100 border-blue-500' : 'border-gray-300'}`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : (
                <VolumeProfileCard data={profile} />
              )}
            </div>
          )}
        </main>
      </div>
    </>
  );
}
