/**
 * Analyst Accuracy Scoring Page (Band B #24)
 *
 * Features:
 * - Analyst search and profiles
 * - Accuracy scoring leaderboard
 * - Firm rankings
 * - Historical estimate accuracy
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Tier Badge ────────────────────────────────────────────────────────────────

function TierBadge({ tier }) {
  const colors = {
    star: 'bg-yellow-400 text-yellow-900',
    top: 'bg-blue-500 text-white',
    above_average: 'bg-green-500 text-white',
    average: 'bg-gray-400 text-white',
    below_average: 'bg-red-400 text-white',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-bold ${colors[tier] || 'bg-gray-300'}`}>
      {tier?.replace(/_/g, ' ').toUpperCase()}
    </span>
  );
}

// ── Analyst Card ──────────────────────────────────────────────────────────────

function AnalystCard({ data, onClick }) {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{data.analyst_name}</h3>
          <p className="text-sm text-gray-500">{data.firm}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-600">{data.overall_score}</div>
          <TierBadge tier={data.tier} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="text-center p-2 bg-gray-50 rounded">
          <div className="text-gray-500 text-xs">MAE</div>
          <div className="font-medium">{data.accuracy_metrics?.mean_absolute_error}%</div>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded">
          <div className="text-gray-500 text-xs">Direction</div>
          <div className="font-medium">{data.accuracy_metrics?.direction_accuracy}%</div>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded">
          <div className="text-gray-500 text-xs">Hit Rate</div>
          <div className="font-medium">{data.accuracy_metrics?.hit_rate}%</div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1">
        {data.coverage?.sectors_covered?.slice(0, 2).map((sector, i) => (
          <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded">
            {sector}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Firm Ranking Table ────────────────────────────────────────────────────────

function FirmRankingTable({ data }) {
  if (!data?.ranking?.length) return null;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="p-4 border-b">
        <h3 className="font-semibold">Firm Rankings</h3>
        <p className="text-sm text-gray-500">By average analyst accuracy</p>
      </div>
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left">Rank</th>
            <th className="px-4 py-3 text-left">Firm</th>
            <th className="px-4 py-3 text-right">Avg Score</th>
            <th className="px-4 py-3 text-right">Analysts</th>
            <th className="px-4 py-3 text-right">Top Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.ranking.map((firm, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium">#{firm.rank}</td>
              <td className="px-4 py-3">{firm.firm}</td>
              <td className="px-4 py-3 text-right font-semibold text-blue-600">{firm.avg_score}</td>
              <td className="px-4 py-3 text-right">{firm.analyst_count}</td>
              <td className="px-4 py-3 text-right text-green-600">{firm.top_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AnalystsPage() {
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [ranking, setRanking] = useState([]);
  const [firmRanking, setFirmRanking] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchLeaderboard = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/analysts/ranking?limit=20`);
      const data = await res.json();
      setRanking(data.ranking || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFirmRanking = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/analysts/ranking/firms`);
      const data = await res.json();
      setFirmRanking(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const searchAnalysts = async () => {
    if (!searchQuery) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/analysts/search?name=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      setSearchResults(data.analysts || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
    fetchFirmRanking();
  }, []);

  return (
    <>
      <Head>
        <title>Analyst Scoring | Finance Intelligence</title>
      </Head>

      <div className="research-dark min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Analyst Accuracy Scoring</h1>
            <p className="text-sm text-gray-500">Track analyst estimate accuracy and calibration</p>
          </div>
        </header>

        {/* Tabs */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <nav className="flex space-x-8">
              {[
                { id: 'leaderboard', label: 'Leaderboard' },
                { id: 'firms', label: 'Firm Rankings' },
                { id: 'search', label: 'Search' },
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
          {loading && <div className="text-center py-8 text-gray-500">Loading...</div>}

          {/* Leaderboard */}
          {activeTab === 'leaderboard' && !loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {ranking.map((analyst, i) => (
                <div key={i} className="relative">
                  {i < 3 && (
                    <div className="absolute -top-2 -left-2 w-8 h-8 bg-yellow-400 rounded-full flex items-center justify-center text-white font-bold shadow-lg">
                      {i + 1}
                    </div>
                  )}
                  <AnalystCard data={analyst} />
                </div>
              ))}
            </div>
          )}

          {/* Firm Rankings */}
          {activeTab === 'firms' && !loading && (
            <FirmRankingTable data={firmRanking} />
          )}

          {/* Search */}
          {activeTab === 'search' && (
            <div className="space-y-4">
              <div className="flex gap-4">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchAnalysts()}
                  placeholder="Search by analyst name..."
                  className="flex-1 px-4 py-2 border rounded-lg"
                />
                <button
                  onClick={searchAnalysts}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Search
                </button>
              </div>

              {!loading && searchResults.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {searchResults.map((analyst, i) => (
                    <div key={i} className="bg-white rounded-lg shadow p-4">
                      <h3 className="font-semibold">{analyst.name}</h3>
                      <p className="text-sm text-gray-500">{analyst.firm}</p>
                      <p className="text-sm text-gray-500">{analyst.title}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {analyst.sectors_covered?.map((s, j) => (
                          <span key={j} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </>
  );
}
