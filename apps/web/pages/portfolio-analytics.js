import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData, apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PortfolioAnalyticsPage() {
  const [activeTab, setActiveTab] = useState('factors');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({});
  const [noData, setNoData] = useState(null);
  // user_id derived from JWT token server-side
  const userId = '';

  const tabs = [
    { id: 'factors', label: 'Factor Decomposition', endpoint: 'factor-decomposition' },
    { id: 'rebalancing', label: 'Rebalancing', endpoint: 'rebalancing', method: 'POST' },
    { id: 'models', label: 'Model Portfolios', endpoint: 'model-portfolios' },
    { id: 'risk-parity', label: 'Risk Parity', endpoint: 'risk-parity' },
    { id: 'scenarios', label: 'Scenario Analysis', endpoint: 'scenario-analysis', method: 'POST' },
    { id: 'drawdown', label: 'Drawdown', endpoint: 'drawdown' },
    { id: 'correlation', label: 'Correlation Matrix', endpoint: 'correlation-matrix' },
    { id: 'sector', label: 'Sector Rotation', endpoint: 'sector-rotation' },
    { id: 'factor-timing', label: 'Factor Timing', endpoint: 'factor-timing' },
    { id: 'attribution', label: 'Performance Attribution', endpoint: 'performance-attribution' }
  ];

  useEffect(() => {
    loadTabData(activeTab);
  }, [activeTab]);

  async function loadTabData(tabId) {
    const tab = tabs.find(t => t.id === tabId);
    if (!tab) return;
    setLoading(true);
    setNoData(null);
    try {
      const needsUser = !['models', 'factor-timing'].includes(tabId);
      const url = `${API_BASE}/portfolio-analytics/${tab.endpoint}${needsUser ? `?user_id=${userId}` : ''}`;
      const res = await fetch(url, { method: tab.method || 'GET' });
      const result = await res.json();
      if (isNoData(result)) { setNoData(result); setLoading(false); return; }
      setData(prev => ({ ...prev, [tabId]: result }));
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  const currentData = data[activeTab];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Portfolio Analytics | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Portfolio Analytics</h1>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap text-sm ${
              activeTab === tab.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-gray-800 rounded-lg p-6">
        {loading ? (
          <div className="text-center py-10">Loading...</div>
        ) : noData ? (
          <NoDataCard {...noData} />
        ) : !currentData ? (
          <div className="text-center py-10 text-gray-400">Select a tab to view analytics</div>
        ) : (
          <>
            {/* D1: Factor Decomposition */}
            {activeTab === 'factors' && currentData.factors && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Factor Decomposition</h2>
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-blue-400">{currentData.r_squared}</div>
                    <div className="text-gray-400 text-sm">R-Squared</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-green-400">{currentData.residual_risk}%</div>
                    <div className="text-gray-400 text-sm">Residual Risk</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-purple-400">{currentData.tracking_error}%</div>
                    <div className="text-gray-400 text-sm">Tracking Error</div>
                  </div>
                </div>
                <table className="w-full">
                  <thead><tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-2">Factor</th><th className="pb-2">Exposure</th><th className="pb-2">Contribution</th><th className="pb-2">T-Stat</th>
                  </tr></thead>
                  <tbody>
                    {currentData.factors.map((f, i) => (
                      <tr key={i} className="border-b border-gray-700">
                        <td className="py-2 font-semibold">{f.name}</td>
                        <td className="py-2">{f.exposure}</td>
                        <td className={`py-2 ${f.contribution >= 0 ? 'text-green-400' : 'text-red-400'}`}>{f.contribution}%</td>
                        <td className="py-2">{f.t_stat}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* D2: Rebalancing */}
            {activeTab === 'rebalancing' && currentData.suggested_trades && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Rebalancing Suggestions</h2>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <div className="text-sm text-gray-400 mb-2">Drift Score</div>
                    <div className="text-2xl font-bold text-yellow-400">{currentData.drift_score}%</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <div className="text-sm text-gray-400 mb-2">Est. Tax Impact</div>
                    <div className="text-2xl font-bold text-red-400">${currentData.estimated_tax_impact}</div>
                  </div>
                </div>
                <div className="space-y-3">
                  {currentData.suggested_trades.map((t, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                      <div>
                        <span className={`px-2 py-1 rounded text-sm mr-2 ${t.action === 'buy' ? 'bg-green-600' : 'bg-red-600'}`}>
                          {t.action.toUpperCase()}
                        </span>
                        <span className="font-semibold">{t.sector}</span>
                      </div>
                      <div className="text-right">
                        <div>{t.current_weight}% → {t.target_weight}%</div>
                        <div className="text-gray-400 text-sm">${t.estimated_value}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* D3: Model Portfolios */}
            {activeTab === 'models' && currentData.models && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Model Portfolios</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {currentData.models.map((m, i) => (
                    <div key={i} className="p-4 bg-gray-700 rounded-lg">
                      <div className="font-semibold text-lg mb-2">{m.name}</div>
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-gray-400">Risk Level:</span>
                        <div className="flex gap-1">
                          {[...Array(10)].map((_, j) => (
                            <div key={j} className={`w-2 h-4 rounded ${j < m.risk_level ? 'bg-blue-500' : 'bg-gray-600'}`} />
                          ))}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div><span className="text-gray-400">Return:</span> <span className="text-green-400">{m.expected_return}%</span></div>
                        <div><span className="text-gray-400">Volatility:</span> <span className="text-yellow-400">{m.volatility}%</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* D4: Risk Parity */}
            {activeTab === 'risk-parity' && currentData.allocations && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Risk Parity Allocation</h2>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-blue-400">{currentData.portfolio_volatility}%</div>
                    <div className="text-gray-400 text-sm">Portfolio Volatility</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-green-400">{currentData.sharpe_ratio}</div>
                    <div className="text-gray-400 text-sm">Sharpe Ratio</div>
                  </div>
                </div>
                <div className="space-y-3">
                  {currentData.allocations.map((a, i) => (
                    <div key={i} className="p-4 bg-gray-700 rounded-lg">
                      <div className="flex justify-between mb-2">
                        <span className="font-semibold">{a.asset}</span>
                        <span>{a.weight}%</span>
                      </div>
                      <div className="w-full bg-gray-600 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${a.weight}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* D5: Scenario Analysis */}
            {activeTab === 'scenarios' && currentData.scenarios && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Scenario Analysis</h2>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-red-400">{currentData.var_95}%</div>
                    <div className="text-gray-400 text-sm">VaR (95%)</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-red-400">{currentData.cvar_95}%</div>
                    <div className="text-gray-400 text-sm">CVaR (95%)</div>
                  </div>
                </div>
                <div className="space-y-3">
                  {currentData.scenarios.map((s, i) => (
                    <div key={i} className="p-4 bg-gray-700 rounded-lg">
                      <div className="flex justify-between mb-2">
                        <span className="font-semibold capitalize">{s.name.replace('_', ' ')}</span>
                        <span className={s.portfolio_impact >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {s.portfolio_impact > 0 ? '+' : ''}{s.portfolio_impact}%
                        </span>
                      </div>
                      <div className="text-gray-400 text-sm">Probability: {s.probability}%</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* D6: Drawdown */}
            {activeTab === 'drawdown' && currentData.max_drawdown && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Drawdown Analytics</h2>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-red-400">{currentData.max_drawdown.value}%</div>
                    <div className="text-gray-400 text-sm">Max Drawdown</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-yellow-400">{currentData.current_drawdown}%</div>
                    <div className="text-gray-400 text-sm">Current Drawdown</div>
                  </div>
                </div>
                <div className="p-4 bg-gray-700 rounded-lg mb-4">
                  <h3 className="font-semibold mb-2">Max Drawdown Details</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div><span className="text-gray-400">Start:</span> {currentData.max_drawdown.start_date}</div>
                    <div><span className="text-gray-400">Bottom:</span> {currentData.max_drawdown.bottom_date}</div>
                    <div><span className="text-gray-400">Recovery:</span> {currentData.max_drawdown.recovery_date}</div>
                    <div><span className="text-gray-400">Duration:</span> {currentData.max_drawdown.duration_days} days</div>
                  </div>
                </div>
              </div>
            )}

            {/* D7: Correlation Matrix */}
            {activeTab === 'correlation' && currentData.matrix && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Correlation Matrix</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr><th></th>{currentData.tickers.map((t, i) => <th key={i} className="p-2">{t}</th>)}</tr>
                    </thead>
                    <tbody>
                      {currentData.matrix.map((row, i) => (
                        <tr key={i}>
                          <td className="p-2 font-semibold">{currentData.tickers[i]}</td>
                          {row.map((val, j) => (
                            <td key={j} className="p-2 text-center" style={{
                              backgroundColor: `rgba(59, 130, 246, ${val * 0.5})`
                            }}>{val}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* D8: Sector Rotation */}
            {activeTab === 'sector' && currentData.signals && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Sector Rotation Signals</h2>
                <div className="space-y-3">
                  {currentData.signals.map((s, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                      <div>
                        <span className="font-semibold">{s.sector}</span>
                        <span className={`ml-2 px-2 py-1 rounded text-xs ${
                          s.signal === 'overweight' ? 'bg-green-600' : s.signal === 'underweight' ? 'bg-red-600' : 'bg-gray-600'
                        }`}>{s.signal}</span>
                      </div>
                      <div className="text-right">
                        <div className={s.momentum_score >= 0 ? 'text-green-400' : 'text-red-400'}>{s.momentum_score}</div>
                        <div className="text-gray-400 text-sm">Trend: {s.trend}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* D9: Factor Timing */}
            {activeTab === 'factor-timing' && currentData.factors && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Factor Timing Signals</h2>
                <div className="p-4 bg-gray-700 rounded-lg mb-4">
                  <span className="text-gray-400">Market Regime:</span>
                  <span className="ml-2 font-semibold capitalize">{currentData.market_regime?.replace('_', ' ')}</span>
                  <span className="ml-2 text-gray-400">({(currentData.regime_probability * 100).toFixed(0)}% confidence)</span>
                </div>
                <div className="space-y-3">
                  {currentData.factors.map((f, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                      <div>
                        <span className="font-semibold">{f.name}</span>
                        <span className={`ml-2 px-2 py-1 rounded text-xs ${
                          f.current_signal === 'bullish' ? 'bg-green-600' : f.current_signal === 'bearish' ? 'bg-red-600' : 'bg-gray-600'
                        }`}>{f.current_signal}</span>
                      </div>
                      <div className="text-right">
                        <div className="capitalize">{f.recommended_exposure}</div>
                        <div className="text-gray-400 text-sm">Conviction: {(f.conviction * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* D11: Performance Attribution */}
            {activeTab === 'attribution' && currentData.attribution && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Performance Attribution (Brinson)</h2>
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-green-400">{currentData.total_return}%</div>
                    <div className="text-gray-400 text-sm">Portfolio Return</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-blue-400">{currentData.benchmark_return}%</div>
                    <div className="text-gray-400 text-sm">Benchmark Return</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-2xl font-bold text-purple-400">{currentData.excess_return}%</div>
                    <div className="text-gray-400 text-sm">Excess Return</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-xl font-bold">{currentData.attribution.allocation_effect}%</div>
                    <div className="text-gray-400 text-sm">Allocation Effect</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-xl font-bold">{currentData.attribution.selection_effect}%</div>
                    <div className="text-gray-400 text-sm">Selection Effect</div>
                  </div>
                  <div className="p-4 bg-gray-700 rounded-lg text-center">
                    <div className="text-xl font-bold">{currentData.attribution.interaction_effect}%</div>
                    <div className="text-gray-400 text-sm">Interaction Effect</div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
