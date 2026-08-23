import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData , apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function BenchmarkPage() {
  const [benchmarks, setBenchmarks] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [attribution, setAttribution] = useState(null);
  const [selectedBenchmark, setSelectedBenchmark] = useState('SPY');
  const [noData, setNoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchBenchmarks();
  }, []);

  useEffect(() => {
    if (selectedBenchmark) {
      fetchComparison(selectedBenchmark);
    }
  }, [selectedBenchmark]);

  async function fetchBenchmarks() {
    try {
      const res = await apiFetch(`/benchmark/available`);
      const data = await res.json();
      if (isNoData(data)) {
        setNoData(data);
        setLoading(false);
        return;
      }
      setBenchmarks(data.benchmarks || []);
    } catch (err) {
      setError('Error fetching benchmarks:', err);
    }
    setLoading(false);
  }

  async function fetchComparison(benchmark) {
    setLoading(true);
    try {
      const [compRes, attrRes] = await Promise.all([
        apiFetch(`/benchmark/compare?benchmark=${benchmark}`),
        apiFetch(`/benchmark/sector-attribution`)
      ]);
      const compData = await compRes.json();
      const attrData = await attrRes.json();
      setComparison(compData);
      setAttribution(attrData);
    } catch (err) {
      setError('Error:', err);
    }
    setLoading(false);
  }

  const formatPercent = (val) => `${(val || 0).toFixed(2)}%`;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">

      <Head>
        <title>Benchmark Attribution | Finance Platform</title>
      </Head>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Benchmark Attribution</h1>
        <select
          value={selectedBenchmark}
          onChange={(e) => setSelectedBenchmark(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded px-4 py-2"
        >
          {benchmarks.map(b => (
            <option key={b.ticker} value={b.ticker}>{b.name} ({b.ticker})</option>
          ))}
        </select>
      </div>

      {noData ? (
        <NoDataCard {...noData} dataType="benchmark" />
      ) : loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : (
        <>
          {/* Performance Comparison */}
          {comparison && comparison.comparison && (
            <div className="bg-gray-800 rounded-lg p-4 mb-6">
              <h2 className="text-xl font-semibold mb-4">Performance vs {selectedBenchmark}</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-700">
                    <tr>
                      <th className="px-4 py-2 text-left">Period</th>
                      <th className="px-4 py-2 text-right">Portfolio</th>
                      <th className="px-4 py-2 text-right">Benchmark</th>
                      <th className="px-4 py-2 text-right">Alpha</th>
                      <th className="px-4 py-2 text-center">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.comparison.map(row => (
                      <tr key={row.period} className="border-t border-gray-700">
                        <td className="px-4 py-2 uppercase font-medium">{row.period}</td>
                        <td className="px-4 py-2 text-right">{formatPercent(row.portfolio_return)}</td>
                        <td className="px-4 py-2 text-right">{formatPercent(row.benchmark_return)}</td>
                        <td className={`px-4 py-2 text-right ${row.alpha >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {row.alpha >= 0 ? '+' : ''}{formatPercent(row.alpha)}
                        </td>
                        <td className="px-4 py-2 text-center">
                          {row.outperformed ? (
                            <span className="text-green-400">↑</span>
                          ) : (
                            <span className="text-red-400">↓</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Risk Metrics */}
          {comparison && comparison.risk_metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Sharpe Ratio</div>
                <div className="text-2xl font-bold">{comparison.risk_metrics.portfolio_sharpe}</div>
                <div className="text-gray-500 text-xs">vs {comparison.risk_metrics.benchmark_sharpe} (bench)</div>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Information Ratio</div>
                <div className="text-2xl font-bold">{comparison.risk_metrics.information_ratio}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Tracking Error</div>
                <div className="text-2xl font-bold">{formatPercent(comparison.risk_metrics.tracking_error)}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Beta</div>
                <div className="text-2xl font-bold">{comparison.risk_metrics.beta}</div>
              </div>
            </div>
          )}

          {/* Sector Attribution */}
          {attribution && attribution.sectors && (
            <div className="bg-gray-800 rounded-lg p-4">
              <h2 className="text-xl font-semibold mb-4">Sector Attribution</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-700">
                    <tr>
                      <th className="px-4 py-2 text-left">Sector</th>
                      <th className="px-4 py-2 text-right">Port Weight</th>
                      <th className="px-4 py-2 text-right">Bench Weight</th>
                      <th className="px-4 py-2 text-right">Port Return</th>
                      <th className="px-4 py-2 text-right">Allocation</th>
                      <th className="px-4 py-2 text-right">Selection</th>
                      <th className="px-4 py-2 text-right">Total Effect</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attribution.sectors.map(sector => (
                      <tr key={sector.sector} className="border-t border-gray-700">
                        <td className="px-4 py-2 font-medium">{sector.sector}</td>
                        <td className="px-4 py-2 text-right">{formatPercent(sector.portfolio_weight)}</td>
                        <td className="px-4 py-2 text-right">{formatPercent(sector.benchmark_weight)}</td>
                        <td className="px-4 py-2 text-right">{formatPercent(sector.portfolio_return)}</td>
                        <td className={`px-4 py-2 text-right ${sector.allocation_effect >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {sector.allocation_effect >= 0 ? '+' : ''}{sector.allocation_effect.toFixed(3)}
                        </td>
                        <td className={`px-4 py-2 text-right ${sector.selection_effect >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {sector.selection_effect >= 0 ? '+' : ''}{sector.selection_effect.toFixed(3)}
                        </td>
                        <td className={`px-4 py-2 text-right font-semibold ${sector.total_effect >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {sector.total_effect >= 0 ? '+' : ''}{sector.total_effect.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {attribution.summary && (
                <div className="mt-4 pt-4 border-t border-gray-700 grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-gray-400 text-sm">Total Allocation</div>
                    <div className={`text-xl font-bold ${attribution.summary.allocation_effect >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {attribution.summary.allocation_effect >= 0 ? '+' : ''}{formatPercent(attribution.summary.allocation_effect)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-400 text-sm">Total Selection</div>
                    <div className={`text-xl font-bold ${attribution.summary.selection_effect >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {attribution.summary.selection_effect >= 0 ? '+' : ''}{formatPercent(attribution.summary.selection_effect)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-400 text-sm">Active Return</div>
                    <div className={`text-xl font-bold ${attribution.summary.total_active_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {attribution.summary.total_active_return >= 0 ? '+' : ''}{formatPercent(attribution.summary.total_active_return)}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
