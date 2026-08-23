import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData , apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CostBasisPage() {
  const [positions, setPositions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedTicker, setSelectedTicker] = useState('');
  const [loading, setLoading] = useState(true);
  const [taxComparison, setTaxComparison] = useState(null);
  const [noData, setNoData] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    setLoading(true);
    try {
      const [posRes, sumRes] = await Promise.all([
        apiFetch(`/cost-basis/positions`),
        apiFetch(`/cost-basis/summary`)
      ]);
      const posData = await posRes.json();
      if (isNoData(posData)) { setNoData(posData); setLoading(false); return; }
      const sumData = await sumRes.json();
      setPositions(posData.positions || []);
      setSummary(sumData);
    } catch (err) {
      console.error('Error fetching cost basis data:', err);
    }
    setLoading(false);
  }

  async function compareTaxMethods(ticker, shares) {
    try {
      const res = await apiFetch(`/cost-basis/tax-lot-comparison/${ticker}?shares=${shares}`);
      const data = await res.json();
      setTaxComparison(data);
    } catch (err) {
      console.error('Error comparing tax methods:', err);
    }
  }

  const formatCurrency = (val) => `$${(val || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  const formatPercent = (val) => `${(val || 0).toFixed(2)}%`;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Cost Basis Tracking | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Cost Basis Tracking</h1>

      {loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : noData ? (
        <NoDataCard {...noData} />
      ) : (
        <>
          {/* Summary Section */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Total Cost Basis</div>
                <div className="text-2xl font-bold">{formatCurrency(summary.total_cost_basis)}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Market Value</div>
                <div className="text-2xl font-bold">{formatCurrency(summary.total_market_value)}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Unrealized Gain/Loss</div>
                <div className={`text-2xl font-bold ${summary.total_unrealized_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(summary.total_unrealized_gain)} ({formatPercent(summary.total_unrealized_gain_percent)})
                </div>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="text-gray-400 text-sm">Positions</div>
                <div className="text-2xl font-bold">{summary.positions_count} lots / {summary.tickers_count} tickers</div>
              </div>
            </div>
          )}

          {/* Holding Period Breakdown */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              <div className="bg-gray-800 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-2 text-green-400">Long-Term Gains</h3>
                <div className="text-xl">{formatCurrency(summary.long_term_gain)}</div>
                <div className="text-gray-400 text-sm">15% LTCG rate</div>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-2 text-yellow-400">Short-Term Gains</h3>
                <div className="text-xl">{formatCurrency(summary.short_term_gain)}</div>
                <div className="text-gray-400 text-sm">Ordinary income rate</div>
              </div>
            </div>
          )}

          {/* Positions Table */}
          <div className="bg-gray-800 rounded-lg overflow-hidden mb-8">
            <h2 className="text-xl font-semibold p-4 border-b border-gray-700">Tax Lots</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left">Ticker</th>
                    <th className="px-4 py-3 text-right">Shares</th>
                    <th className="px-4 py-3 text-right">Cost/Share</th>
                    <th className="px-4 py-3 text-right">Current</th>
                    <th className="px-4 py-3 text-right">Cost Basis</th>
                    <th className="px-4 py-3 text-right">Gain/Loss</th>
                    <th className="px-4 py-3 text-center">Holding</th>
                    <th className="px-4 py-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => (
                    <tr key={pos.lot_id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="px-4 py-3 font-medium">{pos.ticker}</td>
                      <td className="px-4 py-3 text-right">{pos.shares}</td>
                      <td className="px-4 py-3 text-right">{formatCurrency(pos.purchase_price)}</td>
                      <td className="px-4 py-3 text-right">{formatCurrency(pos.current_price)}</td>
                      <td className="px-4 py-3 text-right">{formatCurrency(pos.cost_basis)}</td>
                      <td className={`px-4 py-3 text-right ${pos.unrealized_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(pos.unrealized_gain)} ({formatPercent(pos.unrealized_gain_percent)})
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${pos.is_long_term ? 'bg-green-800 text-green-200' : 'bg-yellow-800 text-yellow-200'}`}>
                          {pos.is_long_term ? 'Long' : `${pos.holding_days}d`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => compareTaxMethods(pos.ticker, pos.shares)}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          Compare
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Tax Method Comparison */}
          {taxComparison && taxComparison.comparisons && (
            <div className="bg-gray-800 rounded-lg p-4">
              <h2 className="text-xl font-semibold mb-4">
                Tax Method Comparison - {taxComparison.ticker} ({taxComparison.shares_to_sell} shares)
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {taxComparison.comparisons.map((comp) => (
                  <div
                    key={comp.method}
                    className={`p-4 rounded-lg ${comp.is_optimal ? 'bg-green-900 border border-green-600' : 'bg-gray-700'}`}
                  >
                    <div className="font-semibold text-lg mb-2 uppercase">{comp.method}</div>
                    {comp.is_optimal && <span className="text-green-400 text-sm">✓ Optimal</span>}
                    <div className="mt-2 space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>Total Gain:</span>
                        <span className={comp.total_gain >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {formatCurrency(comp.total_gain)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Long-term:</span>
                        <span>{formatCurrency(comp.long_term_gain)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Short-term:</span>
                        <span>{formatCurrency(comp.short_term_gain)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
