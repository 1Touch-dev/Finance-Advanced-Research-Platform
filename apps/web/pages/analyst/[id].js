/**
 * Public Analyst Profile Page (Band B #29)
 *
 * Features:
 * - Individual analyst track record
 * - Accuracy metrics and calibration
 * - Coverage sectors and companies
 * - Historical estimates vs actuals
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { apiFetch } from '../../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Tier Badge ───────────────────────────────────────────────────────────────

function TierBadge({ tier }) {
  const colors = {
    star: 'bg-yellow-400 text-yellow-900',
    top: 'bg-blue-500 text-white',
    above_average: 'bg-green-500 text-white',
    average: 'bg-gray-400 text-white',
    below_average: 'bg-red-400 text-white',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-bold ${colors[tier] || 'bg-gray-300'}`}>
      {tier?.replace(/_/g, ' ').toUpperCase()}
    </span>
  );
}

// ── Score Card ───────────────────────────────────────────────────────────────

function ScoreCard({ label, value, subtext, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className={`p-4 rounded-lg ${colors[color]}`}>
      <div className="text-sm text-gray-600 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
    </div>
  );
}

// ── Accuracy Chart ───────────────────────────────────────────────────────────

function AccuracyChart({ metrics }) {
  if (!metrics) return null;

  const items = [
    { label: 'Mean Abs Error', value: metrics.mean_absolute_error, max: 50 },
    { label: 'Direction Accuracy', value: metrics.direction_accuracy, max: 100 },
    { label: 'Hit Rate', value: metrics.hit_rate, max: 100 },
    { label: 'Brier Score', value: (1 - metrics.brier_score) * 100, max: 100 },
  ];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Accuracy Metrics</h3>
      <div className="space-y-4">
        {items.map((item, i) => (
          <div key={i}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">{item.label}</span>
              <span className="font-medium">{item.value?.toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full">
              <div
                className="h-2 bg-blue-500 rounded-full transition-all"
                style={{ width: `${Math.min(100, (item.value / item.max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Coverage Section ─────────────────────────────────────────────────────────

function CoverageSection({ coverage }) {
  if (!coverage) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Coverage</h3>

      <div className="grid grid-cols-2 gap-6">
        {/* Sectors */}
        <div>
          <div className="text-sm text-gray-500 mb-2">Sectors</div>
          <div className="flex flex-wrap gap-2">
            {coverage.sectors_covered?.map((sector, i) => (
              <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">
                {sector}
              </span>
            ))}
          </div>
        </div>

        {/* Companies */}
        <div>
          <div className="text-sm text-gray-500 mb-2">Top Companies</div>
          <div className="flex flex-wrap gap-2">
            {coverage.companies_covered?.slice(0, 10).map((company, i) => (
              <span key={i} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                {company}
              </span>
            ))}
            {coverage.companies_covered?.length > 10 && (
              <span className="px-3 py-1 text-gray-500 text-sm">
                +{coverage.companies_covered.length - 10} more
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mt-6 pt-4 border-t">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{coverage.total_estimates || 0}</div>
          <div className="text-xs text-gray-500">Total Estimates</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{coverage.companies_covered?.length || 0}</div>
          <div className="text-xs text-gray-500">Companies Covered</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{coverage.years_active || 0}</div>
          <div className="text-xs text-gray-500">Years Active</div>
        </div>
      </div>
    </div>
  );
}

// ── Historical Estimates ─────────────────────────────────────────────────────

function HistoricalEstimates({ estimates }) {
  if (!estimates?.length) return null;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="p-4 border-b">
        <h3 className="font-semibold">Recent Estimates</h3>
      </div>
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left">Company</th>
            <th className="px-4 py-3 text-left">Metric</th>
            <th className="px-4 py-3 text-right">Estimate</th>
            <th className="px-4 py-3 text-right">Actual</th>
            <th className="px-4 py-3 text-right">Error</th>
            <th className="px-4 py-3 text-center">Result</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {estimates.map((est, i) => {
            const error = est.actual ? ((est.estimate - est.actual) / est.actual * 100) : null;
            const isAccurate = error !== null && Math.abs(error) < 10;

            return (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-blue-600">{est.ticker}</td>
                <td className="px-4 py-3 text-gray-600">{est.metric}</td>
                <td className="px-4 py-3 text-right">${est.estimate?.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">
                  {est.actual ? `$${est.actual.toFixed(2)}` : '—'}
                </td>
                <td className={`px-4 py-3 text-right ${error > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {error !== null ? `${error > 0 ? '+' : ''}${error.toFixed(1)}%` : '—'}
                </td>
                <td className="px-4 py-3 text-center">
                  {est.actual && (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      isAccurate ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {isAccurate ? 'HIT' : 'MISS'}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Calibration Chart ────────────────────────────────────────────────────────

function CalibrationChart({ calibration }) {
  if (!calibration) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Estimate Calibration</h3>
      <p className="text-sm text-gray-500 mb-4">
        How often does this analyst hit their targets by confidence level?
      </p>

      <div className="space-y-3">
        {calibration.buckets?.map((bucket, i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="w-24 text-sm text-gray-600">{bucket.range}</div>
            <div className="flex-1 flex gap-2">
              <div className="flex-1 h-6 bg-blue-100 rounded relative">
                <div
                  className="absolute h-6 bg-blue-500 rounded flex items-center justify-end pr-2"
                  style={{ width: `${bucket.expected}%` }}
                >
                  <span className="text-xs text-white font-medium">{bucket.expected}%</span>
                </div>
              </div>
              <div className="flex-1 h-6 bg-green-100 rounded relative">
                <div
                  className="absolute h-6 bg-green-500 rounded flex items-center justify-end pr-2"
                  style={{ width: `${bucket.actual}%` }}
                >
                  <span className="text-xs text-white font-medium">{bucket.actual}%</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-6 mt-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-blue-500 rounded"></span> Expected
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-green-500 rounded"></span> Actual
        </span>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function AnalystProfilePage() {
  const router = useRouter();
  const { id } = router.query;

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;

    const fetchProfile = async () => {
      setLoading(true);
      try {
        // Mock data - in production this would call an API
        // const res = await apiFetch(`/analysts/profile/${id}`);
        // const data = await res.json();

        // Mock analyst profile data
        const mockProfile = {
          id: id,
          analyst_name: 'Sarah Chen',
          firm: 'Goldman Sachs',
          title: 'Senior Equity Analyst',
          overall_score: 87,
          tier: 'top',
          accuracy_metrics: {
            mean_absolute_error: 8.5,
            direction_accuracy: 72,
            hit_rate: 68,
            brier_score: 0.18,
          },
          coverage: {
            sectors_covered: ['Technology', 'Semiconductors', 'Software'],
            companies_covered: ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM', 'MU', 'MRVL', 'AMAT', 'LRCX', 'KLAC', 'ASML', 'TSM'],
            total_estimates: 342,
            years_active: 8,
          },
          recent_estimates: [
            { ticker: 'NVDA', metric: 'EPS Q4', estimate: 5.85, actual: 6.12, date: '2024-02-21' },
            { ticker: 'AMD', metric: 'EPS Q4', estimate: 0.77, actual: 0.69, date: '2024-01-30' },
            { ticker: 'INTC', metric: 'EPS Q4', estimate: 0.45, actual: 0.42, date: '2024-01-25' },
            { ticker: 'AVGO', metric: 'EPS Q4', estimate: 10.25, actual: 10.99, date: '2024-03-07' },
            { ticker: 'QCOM', metric: 'EPS Q1', estimate: 2.35, actual: 2.44, date: '2024-01-31' },
          ],
          calibration: {
            overall: 0.82,
            buckets: [
              { range: 'High Conf', expected: 80, actual: 75 },
              { range: 'Medium', expected: 60, actual: 62 },
              { range: 'Low Conf', expected: 40, actual: 45 },
            ],
          },
        };

        setProfile(mockProfile);
      } catch (err) {
        setError('Failed to load analyst profile');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading analyst profile...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 mb-4">{error || 'Analyst not found'}</div>
          <Link href="/analysts" legacyBehavior>
            <a className="text-blue-600 hover:underline">Back to Analysts</a>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>{profile.analyst_name} | Analyst Profile | Finance Intelligence</title>
        <meta name="description" content={`Track record and accuracy metrics for ${profile.analyst_name} at ${profile.firm}`} />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-6">
            <Link href="/analysts" legacyBehavior>
              <a className="text-sm text-blue-600 hover:underline mb-2 inline-block">
                ← Back to Analysts
              </a>
            </Link>
            <div className="flex justify-between items-start">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{profile.analyst_name}</h1>
                <p className="text-gray-500">{profile.title} at {profile.firm}</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-blue-600 mb-2">{profile.overall_score}</div>
                <TierBadge tier={profile.tier} />
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
          {/* Score Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <ScoreCard
              label="Overall Score"
              value={profile.overall_score}
              subtext="Out of 100"
              color="blue"
            />
            <ScoreCard
              label="Direction Accuracy"
              value={`${profile.accuracy_metrics?.direction_accuracy}%`}
              subtext="Beat/Miss calls"
              color="green"
            />
            <ScoreCard
              label="Mean Abs Error"
              value={`${profile.accuracy_metrics?.mean_absolute_error}%`}
              subtext="Estimate precision"
              color="purple"
            />
            <ScoreCard
              label="Estimates"
              value={profile.coverage?.total_estimates}
              subtext={`${profile.coverage?.years_active} years`}
              color="orange"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AccuracyChart metrics={profile.accuracy_metrics} />
            <CalibrationChart calibration={profile.calibration} />
          </div>

          <CoverageSection coverage={profile.coverage} />

          <HistoricalEstimates estimates={profile.recent_estimates} />
        </main>
      </div>
    </>
  );
}
