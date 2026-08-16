/**
 * Portfolio Tracking Page (Band C #32)
 *
 * Features:
 * - List all portfolios with performance summary
 * - Create new portfolios
 * - View holdings with market values and P&L
 * - Sector allocation breakdown
 * - Add/remove positions
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── P&L Badge ────────────────────────────────────────────────────────────────

function PnLBadge({ value, percent }) {
  const isPositive = value >= 0;
  const color = isPositive ? 'text-green-600' : 'text-red-600';
  const bgColor = isPositive ? 'bg-green-50' : 'bg-red-50';

  return (
    <span className={`px-2 py-1 rounded text-sm font-medium ${color} ${bgColor}`}>
      {isPositive ? '+' : ''}{value?.toLocaleString(undefined, { style: 'currency', currency: 'USD' })}
      <span className="text-xs ml-1">({isPositive ? '+' : ''}{percent?.toFixed(1)}%)</span>
    </span>
  );
}

// ── Portfolio Card ───────────────────────────────────────────────────────────

function PortfolioCard({ portfolio, onClick }) {
  const pnlColor = portfolio.total_unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow p-6 hover:shadow-md cursor-pointer transition-shadow"
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{portfolio.name}</h3>
          <p className="text-sm text-gray-500">{portfolio.holdings_count} holdings</p>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold">
            ${portfolio.total_market_value?.toLocaleString()}
          </div>
          <div className={`text-sm font-medium ${pnlColor}`}>
            {portfolio.total_unrealized_pnl >= 0 ? '+' : ''}
            ${portfolio.total_unrealized_pnl?.toLocaleString()}
            <span className="text-xs ml-1">
              ({portfolio.total_unrealized_pnl_pct >= 0 ? '+' : ''}{portfolio.total_unrealized_pnl_pct?.toFixed(1)}%)
            </span>
          </div>
        </div>
      </div>

      {portfolio.thesis && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">{portfolio.thesis}</p>
      )}

      <div className="flex justify-between text-sm text-gray-500">
        <span>Day: <span className={portfolio.day_change >= 0 ? 'text-green-600' : 'text-red-600'}>
          {portfolio.day_change >= 0 ? '+' : ''}${portfolio.day_change?.toFixed(2)}
        </span></span>
        <span>{portfolio.base_currency}</span>
      </div>
    </div>
  );
}

// ── Holdings Table ───────────────────────────────────────────────────────────

function HoldingsTable({ holdings, pnlData }) {
  const [showPeriodReturns, setShowPeriodReturns] = useState(false);

  if (!holdings?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No holdings in this portfolio
      </div>
    );
  }

  // Get period returns for each holding from pnlData if available
  const getPeriodReturn = (ticker, period) => {
    if (!pnlData?.positions) return null;
    const pos = pnlData.positions.find(p => p.ticker === ticker);
    return pos?.period_returns?.[period];
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">Holdings</span>
        <button
          onClick={() => setShowPeriodReturns(!showPeriodReturns)}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          {showPeriodReturns ? 'Hide Period Returns' : 'Show Period Returns'}
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">Ticker</th>
              <th className="px-4 py-3 text-right">Shares</th>
              <th className="px-4 py-3 text-right">Cost Basis</th>
              <th className="px-4 py-3 text-right">Price</th>
              <th className="px-4 py-3 text-right">Market Value</th>
              <th className="px-4 py-3 text-right">P&L</th>
              {showPeriodReturns && (
                <>
                  <th className="px-4 py-3 text-right">Day</th>
                  <th className="px-4 py-3 text-right">Week</th>
                  <th className="px-4 py-3 text-right">Month</th>
                  <th className="px-4 py-3 text-right">YTD</th>
                </>
              )}
              <th className="px-4 py-3 text-right">Weight</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {holdings.map((h, i) => {
              const dayReturn = getPeriodReturn(h.ticker, 'day');
              const weekReturn = getPeriodReturn(h.ticker, 'week');
              const monthReturn = getPeriodReturn(h.ticker, 'month');
              const ytdReturn = getPeriodReturn(h.ticker, 'ytd');

              return (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-blue-600">{h.ticker}</div>
                    <div className="text-xs text-gray-500">{h.sector}</div>
                  </td>
                  <td className="px-4 py-3 text-right">{h.quantity}</td>
                  <td className="px-4 py-3 text-right">${h.cost_basis?.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">${h.current_price?.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-medium">${h.market_value?.toLocaleString()}</td>
                  <td className={`px-4 py-3 text-right font-medium ${h.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {h.unrealized_pnl >= 0 ? '+' : ''}${h.unrealized_pnl?.toFixed(2)}
                    <span className="text-xs ml-1">({h.unrealized_pnl_pct >= 0 ? '+' : ''}{h.unrealized_pnl_pct?.toFixed(1)}%)</span>
                  </td>
                  {showPeriodReturns && (
                    <>
                      <td className={`px-4 py-3 text-right text-xs ${dayReturn?.pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {dayReturn ? `${dayReturn.pct >= 0 ? '+' : ''}${dayReturn.pct?.toFixed(1)}%` : '-'}
                      </td>
                      <td className={`px-4 py-3 text-right text-xs ${weekReturn?.pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {weekReturn ? `${weekReturn.pct >= 0 ? '+' : ''}${weekReturn.pct?.toFixed(1)}%` : '-'}
                      </td>
                      <td className={`px-4 py-3 text-right text-xs ${monthReturn?.pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {monthReturn ? `${monthReturn.pct >= 0 ? '+' : ''}${monthReturn.pct?.toFixed(1)}%` : '-'}
                      </td>
                      <td className={`px-4 py-3 text-right text-xs ${ytdReturn?.pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {ytdReturn ? `${ytdReturn.pct >= 0 ? '+' : ''}${ytdReturn.pct?.toFixed(1)}%` : '-'}
                      </td>
                    </>
                  )}
                  <td className="px-4 py-3 text-right">{h.weight?.toFixed(1)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Sector Allocation ────────────────────────────────────────────────────────

function SectorAllocation({ sectors }) {
  if (!sectors?.length) return null;

  const colors = [
    'bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500',
    'bg-pink-500', 'bg-cyan-500', 'bg-yellow-500', 'bg-red-500',
  ];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Sector Allocation</h3>

      {/* Bar Chart */}
      <div className="h-8 flex rounded overflow-hidden mb-4">
        {sectors.map((s, i) => (
          <div
            key={i}
            className={`${colors[i % colors.length]}`}
            style={{ width: `${s.weight}%` }}
            title={`${s.sector}: ${s.weight.toFixed(1)}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        {sectors.map((s, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded ${colors[i % colors.length]}`} />
            <span className="text-gray-600">{s.sector}</span>
            <span className="text-gray-900 font-medium ml-auto">{s.weight?.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Performance Summary ──────────────────────────────────────────────────────

function PerformanceSummary({ performance }) {
  if (!performance) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="font-semibold mb-4">Performance</h3>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-sm text-blue-700">Total Value</div>
          <div className="text-2xl font-bold text-blue-600">
            ${performance.total_market_value?.toLocaleString()}
          </div>
        </div>
        <div className={`p-4 rounded ${performance.total_unrealized_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className={`text-sm ${performance.total_unrealized_pnl >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            Unrealized P&L
          </div>
          <div className={`text-2xl font-bold ${performance.total_unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {performance.total_unrealized_pnl >= 0 ? '+' : ''}${performance.total_unrealized_pnl?.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
        <div className="p-3 bg-gray-50 rounded text-center">
          <div className="text-gray-500">Holdings</div>
          <div className="font-semibold">{performance.holdings_count}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded text-center">
          <div className="text-gray-500">Winners</div>
          <div className="font-semibold text-green-600">{performance.positive_positions}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded text-center">
          <div className="text-gray-500">Losers</div>
          <div className="font-semibold text-red-600">{performance.negative_positions}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded text-center">
          <div className="text-gray-500">Top Weight</div>
          <div className="font-semibold">{performance.largest_position_weight?.toFixed(1)}%</div>
        </div>
      </div>

      {(performance.top_gainer || performance.top_loser) && (
        <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
          {performance.top_gainer && (
            <div className="p-3 bg-green-50 rounded">
              <div className="text-green-700">Top Gainer</div>
              <div className="font-semibold text-green-600">
                {performance.top_gainer} (+{performance.top_gainer_pct?.toFixed(1)}%)
              </div>
            </div>
          )}
          {performance.top_loser && (
            <div className="p-3 bg-red-50 rounded">
              <div className="text-red-700">Top Loser</div>
              <div className="font-semibold text-red-600">
                {performance.top_loser} ({performance.top_loser_pct?.toFixed(1)}%)
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Add Position Modal ───────────────────────────────────────────────────────

function AddPositionModal({ portfolioId, onClose, onAdded }) {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [costBasis, setCostBasis] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch(
        `${API_BASE}/portfolio/${portfolioId}/positions?ticker=${ticker}&quantity=${quantity}&cost_basis=${costBasis}`,
        { method: 'POST' }
      );
      if (res.ok) {
        onAdded();
        onClose();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-96">
        <h3 className="text-lg font-semibold mb-4">Add Position</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ticker</label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="AAPL"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="100"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cost Basis (per share)</label>
            <input
              type="number"
              step="0.01"
              value={costBasis}
              onChange={(e) => setCostBasis(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="150.00"
              required
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Adding...' : 'Add Position'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Create Portfolio Modal ───────────────────────────────────────────────────

function CreatePortfolioModal({ onClose, onCreated }) {
  const [name, setName] = useState('');
  const [thesis, setThesis] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const params = new URLSearchParams({ name });
      if (thesis) params.append('thesis', thesis);

      const res = await fetch(`${API_BASE}/portfolio?${params}`, { method: 'POST' });
      if (res.ok) {
        onCreated();
        onClose();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-96">
        <h3 className="text-lg font-semibold mb-4">Create Portfolio</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="My Portfolio"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Investment Thesis (optional)</label>
            <textarea
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="Growth-focused tech portfolio..."
              rows={3}
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Portfolio'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [portfolioDetail, setPortfolioDetail] = useState(null);
  const [portfolioPnL, setPortfolioPnL] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddPosition, setShowAddPosition] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchPortfolios = async () => {
    try {
      const res = await fetch(`${API_BASE}/portfolio`);
      const data = await res.json();
      setPortfolios(data.portfolios || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPortfolioDetail = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/portfolio/${id}`);
      const data = await res.json();
      setPortfolioDetail(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchPortfolioPnL = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/portfolio/${id}/pnl`);
      const data = await res.json();
      setPortfolioPnL(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchPortfolios();
  }, []);

  useEffect(() => {
    if (selectedPortfolio) {
      fetchPortfolioDetail(selectedPortfolio);
      fetchPortfolioPnL(selectedPortfolio);
    } else {
      setPortfolioPnL(null);
    }
  }, [selectedPortfolio]);

  return (
    <>
      <Head>
        <title>Portfolio Tracking | Finance Intelligence</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Portfolio Tracking</h1>
                <p className="text-sm text-gray-500">Track your holdings with P&L and performance metrics</p>
              </div>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                + New Portfolio
              </button>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 py-6">
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading portfolios...</div>
          ) : !selectedPortfolio ? (
            <>
              {portfolios.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-12 text-center">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Portfolios Yet</h3>
                  <p className="text-gray-500 mb-4">Create your first portfolio to start tracking</p>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Create Portfolio
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {portfolios.map((p) => (
                    <PortfolioCard
                      key={p.id}
                      portfolio={p}
                      onClick={() => setSelectedPortfolio(p.id)}
                    />
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              {/* Back Button */}
              <button
                onClick={() => {
                  setSelectedPortfolio(null);
                  setPortfolioDetail(null);
                }}
                className="mb-4 text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                &larr; Back to Portfolios
              </button>

              {portfolioDetail && (
                <div className="space-y-6">
                  {/* Header */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <h2 className="text-xl font-bold text-gray-900">{portfolioDetail.name}</h2>
                        {portfolioDetail.thesis && (
                          <p className="text-gray-600 mt-1">{portfolioDetail.thesis}</p>
                        )}
                      </div>
                      <button
                        onClick={() => setShowAddPosition(true)}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        + Add Position
                      </button>
                    </div>
                  </div>

                  {/* Performance & Allocation */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <PerformanceSummary performance={portfolioDetail.performance} />
                    <SectorAllocation sectors={portfolioDetail.sector_allocation} />
                  </div>

                  {/* Period P&L Summary */}
                  {portfolioPnL && (
                    <div className="bg-white rounded-lg shadow p-6">
                      <h3 className="font-semibold mb-4">Period Returns</h3>
                      <div className="grid grid-cols-4 gap-4">
                        <div className={`p-4 rounded ${portfolioPnL.period_totals?.day >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                          <div className="text-sm text-gray-600">Today</div>
                          <div className={`text-xl font-bold ${portfolioPnL.period_totals?.day >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {portfolioPnL.period_totals?.day >= 0 ? '+' : ''}${portfolioPnL.period_totals?.day?.toFixed(2)}
                          </div>
                        </div>
                        <div className={`p-4 rounded ${portfolioPnL.period_totals?.week >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                          <div className="text-sm text-gray-600">This Week</div>
                          <div className={`text-xl font-bold ${portfolioPnL.period_totals?.week >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {portfolioPnL.period_totals?.week >= 0 ? '+' : ''}${portfolioPnL.period_totals?.week?.toFixed(2)}
                          </div>
                        </div>
                        <div className={`p-4 rounded ${portfolioPnL.period_totals?.month >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                          <div className="text-sm text-gray-600">This Month</div>
                          <div className={`text-xl font-bold ${portfolioPnL.period_totals?.month >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {portfolioPnL.period_totals?.month >= 0 ? '+' : ''}${portfolioPnL.period_totals?.month?.toFixed(2)}
                          </div>
                        </div>
                        <div className={`p-4 rounded ${portfolioPnL.period_totals?.ytd >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                          <div className="text-sm text-gray-600">YTD</div>
                          <div className={`text-xl font-bold ${portfolioPnL.period_totals?.ytd >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {portfolioPnL.period_totals?.ytd >= 0 ? '+' : ''}${portfolioPnL.period_totals?.ytd?.toFixed(2)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Holdings */}
                  <div>
                    <HoldingsTable holdings={portfolioDetail.holdings} pnlData={portfolioPnL} />
                  </div>
                </div>
              )}
            </>
          )}
        </main>

        {/* Modals */}
        {showCreateModal && (
          <CreatePortfolioModal
            onClose={() => setShowCreateModal(false)}
            onCreated={fetchPortfolios}
          />
        )}
        {showAddPosition && selectedPortfolio && (
          <AddPositionModal
            portfolioId={selectedPortfolio}
            onClose={() => setShowAddPosition(false)}
            onAdded={() => fetchPortfolioDetail(selectedPortfolio)}
          />
        )}
      </div>
    </>
  );
}
