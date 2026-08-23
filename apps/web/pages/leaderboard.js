/**
 * Model & Idea Leaderboards Page (Band B #30)
 *
 * Features:
 * - Prediction leaderboard with Brier scoring
 * - Idea leaderboard by P&L
 * - User profiles and calibration
 * - Submit predictions and ideas
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Tier Badge ───────────────────────────────────────────────────────────────

function TierBadge({ tier }) {
  const colors = {
    elite: 'bg-yellow-400 text-yellow-900',
    expert: 'bg-blue-500 text-white',
    proficient: 'bg-green-500 text-white',
    novice: 'bg-gray-400 text-white',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-bold ${colors[tier] || 'bg-gray-300'}`}>

      {tier?.toUpperCase()}
    </span>
  );
}

// ── Trend Indicator ──────────────────────────────────────────────────────────

function TrendIndicator({ trend, change }) {
  if (trend === 'stable') return <span className="text-gray-400">→</span>;

  const color = trend === 'up' ? 'text-green-600' : 'text-red-600';
  const arrow = trend === 'up' ? '↑' : '↓';

  return (
    <span className={`${color} font-medium`}>
      {arrow} {Math.abs(change)}
    </span>
  );
}

// ── Prediction Leaderboard ───────────────────────────────────────────────────

function PredictionLeaderboard({ leaderboard, onSelectUser }) {
  if (!leaderboard?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No predictions yet
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left">Rank</th>
            <th className="px-4 py-3 text-left">User</th>
            <th className="px-4 py-3 text-right">Score</th>
            <th className="px-4 py-3 text-right">Accuracy</th>
            <th className="px-4 py-3 text-center">Tier</th>
            <th className="px-4 py-3 text-right">Predictions</th>
            <th className="px-4 py-3 text-center">Trend</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {leaderboard.map((entry, i) => (
            <tr
              key={i}
              className="hover:bg-gray-50 cursor-pointer"
              onClick={() => onSelectUser(entry.user_id)}
            >
              <td className="px-4 py-3">
                {entry.rank <= 3 ? (
                  <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-white text-xs font-bold ${
                    entry.rank === 1 ? 'bg-yellow-400' : entry.rank === 2 ? 'bg-gray-400' : 'bg-orange-400'
                  }`}>
                    {entry.rank}
                  </span>
                ) : (
                  <span className="text-gray-600">#{entry.rank}</span>
                )}
              </td>
              <td className="px-4 py-3 font-medium">{entry.display_name}</td>
              <td className="px-4 py-3 text-right font-bold text-blue-600">
                {(entry.score * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-3 text-right">
                {(entry.accuracy_rate * 100).toFixed(0)}%
              </td>
              <td className="px-4 py-3 text-center">
                <TierBadge tier={entry.tier} />
              </td>
              <td className="px-4 py-3 text-right text-gray-500">
                {entry.total_predictions}
              </td>
              <td className="px-4 py-3 text-center">
                <TrendIndicator trend={entry.trend} change={entry.trend_change} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Idea Leaderboard ─────────────────────────────────────────────────────────

function IdeaLeaderboard({ ideas }) {
  if (!ideas?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No ideas submitted yet
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {ideas.map((idea, i) => (
        <div key={i} className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-start mb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-blue-600">{idea.ticker}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  idea.direction === 'long' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {idea.direction.toUpperCase()}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  idea.status === 'hit_target' ? 'bg-green-100 text-green-700' :
                  idea.status === 'stopped_out' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {idea.status.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1">{idea.thesis}</p>
            </div>
            <div className={`text-2xl font-bold ${idea.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {idea.pnl_pct >= 0 ? '+' : ''}{idea.pnl_pct}%
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 text-sm">
            <div className="p-2 bg-gray-50 rounded">
              <div className="text-gray-500 text-xs">Entry</div>
              <div className="font-medium">${idea.entry_price}</div>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <div className="text-gray-500 text-xs">Target</div>
              <div className="font-medium">${idea.target_price}</div>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <div className="text-gray-500 text-xs">Current</div>
              <div className="font-medium">${idea.current_price}</div>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <div className="text-gray-500 text-xs">Submitted</div>
              <div className="font-medium">{idea.submitted_date}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── User Profile Modal ───────────────────────────────────────────────────────

function UserProfileModal({ userId, onClose }) {
  const [profile, setProfile] = useState(null);
  const [calibration, setCalibration] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const [profileRes, calibRes] = await Promise.all([
          apiFetch(`/leaderboard/user/${userId}`),
          apiFetch(`/leaderboard/calibration/${userId}`),
        ]);
        setProfile(await profileRes.json());
        setCalibration(await calibRes.json());
      } catch (err) {
        setError(err.message || "Something went wrong");
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [userId]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">Loading...</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-xl font-bold">{profile?.display_name}</h2>
              <div className="flex items-center gap-2 mt-1">
                <TierBadge tier={profile?.tier} />
                {profile?.badges?.map((badge, i) => (
                  <span key={i} className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">
                    {badge}
                  </span>
                ))}
              </div>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
          </div>
        </div>

        <div className="p-6">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="text-center p-3 bg-blue-50 rounded">
              <div className="text-2xl font-bold text-blue-600">{profile?.total_predictions}</div>
              <div className="text-xs text-gray-500">Predictions</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded">
              <div className="text-2xl font-bold text-green-600">{(profile?.accuracy_rate * 100).toFixed(0)}%</div>
              <div className="text-xs text-gray-500">Accuracy</div>
            </div>
            <div className="text-center p-3 bg-purple-50 rounded">
              <div className="text-2xl font-bold text-purple-600">{profile?.avg_brier_score?.toFixed(3)}</div>
              <div className="text-xs text-gray-500">Brier Score</div>
            </div>
            <div className="text-center p-3 bg-orange-50 rounded">
              <div className="text-2xl font-bold text-orange-600">{profile?.streak_current}</div>
              <div className="text-xs text-gray-500">Current Streak</div>
            </div>
          </div>

          {/* Calibration */}
          <h3 className="font-semibold mb-3">Calibration Analysis</h3>
          <div className="p-4 bg-gray-50 rounded mb-4">
            <div className="flex justify-between mb-2">
              <span>Overall Calibration</span>
              <span className="font-bold">{(calibration?.overall_calibration * 100).toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full">
              <div
                className="h-2 bg-blue-500 rounded-full"
                style={{ width: `${calibration?.overall_calibration * 100}%` }}
              />
            </div>
          </div>

          {/* Calibration Buckets */}
          {calibration?.calibration_buckets?.length > 0 && (
            <div className="space-y-2">
              {calibration.calibration_buckets.map((bucket, i) => (
                <div key={i} className="flex items-center gap-4 text-sm">
                  <div className="w-20 text-gray-500">{bucket.confidence_range}</div>
                  <div className="flex-1">
                    <div className="flex gap-2">
                      <div className="flex-1 h-4 bg-blue-100 rounded relative">
                        <div
                          className="absolute h-4 bg-blue-500 rounded"
                          style={{ width: `${bucket.predicted_rate * 100}%` }}
                        />
                      </div>
                      <div className="flex-1 h-4 bg-green-100 rounded relative">
                        <div
                          className="absolute h-4 bg-green-500 rounded"
                          style={{ width: `${bucket.actual_rate * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="w-16 text-right text-xs">
                    <span className="text-blue-600">{(bucket.predicted_rate * 100).toFixed(0)}%</span>
                    {' / '}
                    <span className="text-green-600">{(bucket.actual_rate * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
              <div className="flex gap-4 text-xs text-gray-500 mt-2">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-blue-500 rounded"></span> Predicted
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-green-500 rounded"></span> Actual
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function LeaderboardPage() {
  const [activeTab, setActiveTab] = useState('predictions');
  const [metric, setMetric] = useState('brier');
  const [leaderboard, setLeaderboard] = useState([]);
  const [ideas, setIdeas] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLeaderboard = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/leaderboard/predictions?metric=${metric}&limit=20`);
      const data = await res.json();
      setLeaderboard(data.leaderboard || []);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const fetchIdeas = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/leaderboard/ideas?limit=20`);
      const data = await res.json();
      setIdeas(data.ideas || []);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'predictions') {
      fetchLeaderboard();
    } else if (activeTab === 'ideas') {
      fetchIdeas();
    }
  }, [activeTab, metric]);

  return (
    <>
      <Head>
        <title>Leaderboards | Finance Intelligence</title>
      </Head>

      <div className="research-dark min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Prediction Leaderboards</h1>
            <p className="text-sm text-gray-500">Track forecaster accuracy with Brier scoring</p>
          </div>
        </header>

        {/* Tabs */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <nav className="flex space-x-8">
              {[
                { id: 'predictions', label: 'Predictions' },
                { id: 'ideas', label: 'Trading Ideas' },
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
          {/* Metric Selector for Predictions */}
          {activeTab === 'predictions' && (
            <div className="mb-6 flex gap-2">
              {[
                { id: 'brier', label: 'Brier Score' },
                { id: 'accuracy', label: 'Accuracy' },
                { id: 'calibration', label: 'Calibration' },
              ].map(m => (
                <button
                  key={m.id}
                  onClick={() => setMetric(m.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    metric === m.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 border'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          )}

          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : activeTab === 'predictions' ? (
            <PredictionLeaderboard leaderboard={leaderboard} onSelectUser={setSelectedUser} />
          ) : (
            <IdeaLeaderboard ideas={ideas} />
          )}
        </main>
      </div>

      {/* User Profile Modal */}
      {selectedUser && (
        <UserProfileModal userId={selectedUser} onClose={() => setSelectedUser(null)} />
      )}
    </>
  );
}
