import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData , apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TaxLotsPage() {
  const [lots, setLots] = useState([]);
  const [harvesting, setHarvesting] = useState([]);
  const [approaching, setApproaching] = useState([]);
  const [methodComparison, setMethodComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [noData, setNoData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    setLoading(true);
    try {
      const [lotsRes, harvestRes, approachRes] = await Promise.all([
        apiFetch(`/tax-lots/`),
        apiFetch(`/tax-lots/harvesting-opportunities`),
        apiFetch(`/tax-lots/approaching-long-term`)
      ]);
      const lotsData = await lotsRes.json();
      if (isNoData(lotsData)) { setNoData(lotsData); setLoading(false); return; }
      const harvestData = await harvestRes.json();
      const approachData = await approachRes.json();
      setLots(lotsData.lots || []);
      setHarvesting(harvestData.opportunities || []);
      setApproaching(approachData.lots || []);
    } catch (err) {
      setError('Error:', err);
    }
    setLoading(false);
  }

  async function compareMethods(ticker, shares) {
    try {
      const res = await apiFetch(`/tax-lots/compare-methods?ticker=${ticker}&shares=${shares}`);
      const data = await res.json();
      setMethodComparison(data);
    } catch (err) {
      setError('Error:', err);
    }
  }

  const formatCurrency = (val) => `$${(val || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  const formatPercent = (val) => `${(val || 0).toFixed(2)}%`;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">

      <Head>
        <title>Tax Lot Optimization | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Tax Lot Optimization</h1>

      {loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : noData ? (
        <NoDataCard {...noData} />
      ) : (
        <>
          {/* Tax Loss Harvesting Opportunities */}
          {harvesting.length > 0 && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 mb-6">
              <h2 className="text-xl font-semibold text-red-400 mb-4">🔥 Tax Loss Harvesting Opportunities</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {harvesting.map(lot => (
                  <div key={lot.lot_id} className="bg-gray-800 p-4 rounded-lg">
                    <div className="font-semibold text-lg">{lot.ticker}</div>
                    <div className="text-red-400">{formatCurrency(lot.gain_loss)} loss</div>
                    <div className="text-green-400 text-sm">Save ~{formatCurrency(lot.potential_tax_savings)} in taxes</div>
                    <div className="text-gray-400 text-xs mt-2">Wash sale ends: {lot.wash_sale_end_date}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Approaching Long-Term */}
          {approaching.length > 0 && (
            <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4 mb-6">
              <h2 className="text-xl font-semibold text-yellow-400 mb-4">⏰ Approaching Long-Term Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {approaching.map(lot => (
                  <div key={lot.lot_id} className="bg-gray-800 p-4 rounded-lg">
                    <div className="font-semibold text-lg">{lot.ticker}</div>
                    <div className="text-yellow-400">{lot.days_until_long_term} days until long-term</div>
                    {lot.tax_savings_if_wait > 0 && (
                      <div className="text-green-400 text-sm">
                        Wait to save {formatCurrency(lot.tax_savings_if_wait)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Tax Lots */}
          <div className="bg-gray-800 rounded-lg overflow-hidden mb-6">
            <h2 className="text-xl font-semibold p-4 border-b border-gray-700">All Tax Lots</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left">Ticker</th>
                    <th className="px-4 py-3 text-right">Shares</th>
                    <th className="px-4 py-3 text-right">Cost Basis</th>
                    <th className="px-4 py-3 text-right">Market Value</th>
                    <th className="px-4 py-3 text-right">Gain/Loss</th>
                    <th className="px-4 py-3 text-center">Type</th>
                    <th className="px-4 py-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {lots.map(lot => (
                    <tr key={lot.lot_id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="px-4 py-3 font-medium">{lot.ticker}</td>
                      <td className="px-4 py-3 text-right">{lot.shares}</td>
                      <td className="px-4 py-3 text-right">{formatCurrency(lot.cost_basis)}</td>
                      <td className="px-4 py-3 text-right">{formatCurrency(lot.market_value)}</td>
                      <td className={`px-4 py-3 text-right ${lot.gain_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(lot.gain_loss)} ({formatPercent(lot.gain_loss_percent)})
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${lot.is_long_term ? 'bg-green-800' : 'bg-yellow-800'}`}>
                          {lot.is_long_term ? 'Long-term' : 'Short-term'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => compareMethods(lot.ticker, lot.shares)}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          Optimize
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Method Comparison */}
          {methodComparison && methodComparison.comparisons && (
            <div className="bg-gray-800 rounded-lg p-4">
              <h2 className="text-xl font-semibold mb-4">
                Method Comparison - {methodComparison.ticker} ({methodComparison.shares_to_sell} shares)
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {methodComparison.comparisons.map(comp => (
                  <div
                    key={comp.method}
                    className={`p-4 rounded-lg ${comp.is_optimal ? 'bg-green-900 border-2 border-green-500' : 'bg-gray-700'}`}
                  >
                    <div className="font-bold uppercase">{comp.method_name || comp.method}</div>
                    {comp.is_optimal && <div className="text-green-400 text-sm mb-2">✓ Recommended</div>}
                    <div className="space-y-1 text-sm mt-2">
                      <div className="flex justify-between">
                        <span>Total Gain:</span>
                        <span className={comp.total_gain >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {formatCurrency(comp.total_gain)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Est. Tax:</span>
                        <span>{formatCurrency(comp.estimated_tax)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>After-Tax:</span>
                        <span className="font-semibold">{formatCurrency(comp.after_tax_proceeds)}</span>
                      </div>
                      {comp.tax_savings_vs_fifo > 0 && (
                        <div className="text-green-400 mt-2">
                          Save {formatCurrency(comp.tax_savings_vs_fifo)} vs FIFO
                        </div>
                      )}
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
