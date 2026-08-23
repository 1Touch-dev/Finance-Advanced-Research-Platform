/**
 * Multi-Entity & Thematic Analysis Page (Band B #18)
 *
 * Features:
 * - Sector/industry entity browsing
 * - Supply chain visualization
 * - Thematic corpus analysis
 * - Cross-entity comparison
 */

import React, { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Sector Card Component ─────────────────────────────────────────────────────

function SectorCard({ sector, onClick, isActive }) {
  const sectorIcons = {
    technology: '💻',
    healthcare: '🏥',
    financials: '🏦',
    consumer_discretionary: '🛍️',
    consumer_staples: '🛒',
    industrials: '🏭',
    energy: '⚡',
    materials: '🧱',
    utilities: '💡',
    real_estate: '🏠',
    communication_services: '📡',
  };

  return (
    <button
      onClick={() =>
 onClick(sector.value)}
      className={`p-4 rounded-lg border transition-all ${
        isActive
          ? 'bg-blue-50 border-blue-500 shadow-md'
          : 'bg-white border-gray-200 hover:border-blue-300 hover:shadow'
      }`}
    >
      <div className="text-2xl mb-2">{sectorIcons[sector.value] || '📊'}</div>
      <div className="text-sm font-medium text-gray-800">{sector.name}</div>
    </button>
  );
}

// ── Entity Table Component ────────────────────────────────────────────────────

function EntityTable({ entities, onEntityClick, selectedTickers }) {
  const formatMarketCap = (cap) => {
    if (!cap) return 'N/A';
    if (cap >= 1_000_000_000_000) return `$${(cap / 1_000_000_000_000).toFixed(1)}T`;
    if (cap >= 1_000_000_000) return `$${(cap / 1_000_000_000).toFixed(1)}B`;
    return `$${(cap / 1_000_000).toFixed(0)}M`;
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Select</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Industry</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Market Cap</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Themes</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {entities.map((entity) => (
            <tr
              key={entity.ticker}
              className={`hover:bg-gray-50 cursor-pointer ${
                selectedTickers.includes(entity.ticker) ? 'bg-blue-50' : ''
              }`}
              onClick={() => onEntityClick(entity.ticker)}
            >
              <td className="px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedTickers.includes(entity.ticker)}
                  onChange={() => {}}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
              </td>
              <td className="px-4 py-3 text-sm font-medium text-blue-600">{entity.ticker}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{entity.name}</td>
              <td className="px-4 py-3 text-sm text-gray-500">{entity.industry?.replace(/_/g, ' ')}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{formatMarketCap(entity.market_cap)}</td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-1">
                  {entity.themes?.slice(0, 3).map((theme, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full"
                    >
                      {theme}
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Supply Chain Visualization ────────────────────────────────────────────────

function SupplyChainView({ data }) {
  if (!data) return null;

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      default: return 'bg-green-500';
    }
  };

  const suppliers = data.nodes?.filter(n => n.relationship_type === 'supplier') || [];
  const customers = data.nodes?.filter(n => n.relationship_type === 'customer') || [];
  const others = data.nodes?.filter(n => !['supplier', 'customer'].includes(n.relationship_type)) || [];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold">Supply Chain: {data.focal_name}</h3>
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1">
            <span className="text-gray-500">Risk Score:</span>
            <span className={`px-2 py-0.5 rounded ${
              data.supply_chain_risk_score >= 60 ? 'bg-red-100 text-red-700' :
              data.supply_chain_risk_score >= 40 ? 'bg-yellow-100 text-yellow-700' :
              'bg-green-100 text-green-700'
            }`}>
              {data.supply_chain_risk_score?.toFixed(0)}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Suppliers */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">
            Suppliers ({suppliers.length})
          </h4>
          <div className="space-y-2">
            {suppliers.map((node, i) => (
              <div
                key={i}
                className="p-3 border rounded-lg hover:shadow-sm transition-shadow"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium text-blue-600">{node.ticker}</div>
                    <div className="text-sm text-gray-600">{node.name}</div>
                  </div>
                  <div className={`w-3 h-3 rounded-full ${getRiskColor(node.concentration_risk)}`} title={node.concentration_risk} />
                </div>
                {node.revenue_at_risk && (
                  <div className="mt-2 text-xs text-gray-500">
                    Revenue exposure: {node.revenue_at_risk}%
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Focal Company */}
        <div className="flex flex-col items-center justify-center">
          <div className="p-6 bg-blue-600 text-white rounded-xl shadow-lg">
            <div className="text-xl font-bold">{data.focal_ticker}</div>
            <div className="text-sm opacity-90">{data.focal_name}</div>
          </div>
          <div className="mt-4 text-center text-sm text-gray-500">
            <div>Suppliers: {data.total_suppliers}</div>
            <div>Customers: {data.total_customers}</div>
          </div>
        </div>

        {/* Customers */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">
            Customers ({customers.length})
          </h4>
          <div className="space-y-2">
            {customers.map((node, i) => (
              <div
                key={i}
                className="p-3 border rounded-lg hover:shadow-sm transition-shadow"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium text-blue-600">{node.ticker}</div>
                    <div className="text-sm text-gray-600">{node.name}</div>
                  </div>
                </div>
                {node.revenue_at_risk && (
                  <div className="mt-2 text-xs text-gray-500">
                    Revenue share: {node.revenue_at_risk}%
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Risk Flags */}
      {data.key_risks?.length > 0 && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg">
          <h4 className="text-sm font-medium text-red-800 mb-2">Key Risks</h4>
          <ul className="list-disc list-inside text-sm text-red-700">
            {data.key_risks.map((risk, i) => (
              <li key={i}>{risk}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Thematic Analysis Panel ───────────────────────────────────────────────────

function ThematicAnalysisPanel({ data }) {
  if (!data) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-semibold">Theme: {data.theme}</h3>
          <p className="text-sm text-gray-500">{data.theme_description}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-600">
            {data.avg_exposure_score?.toFixed(0)}
          </div>
          <div className="text-sm text-gray-500">Avg Exposure</div>
        </div>
      </div>

      {/* Exposure Rankings */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Exposure Rankings</h4>
        <div className="space-y-2">
          {data.exposure_rankings?.map((ticker, i) => {
            const score = data.exposure_scores?.[ticker] || 0;
            const sentiment = data.sentiment_by_entity?.[ticker];

            return (
              <div key={ticker} className="flex items-center gap-3">
                <div className="w-6 text-sm text-gray-500">#{i + 1}</div>
                <div className="w-16 font-medium text-blue-600">{ticker}</div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${score}%` }}
                    />
                  </div>
                </div>
                <div className="w-12 text-sm text-gray-600">{score.toFixed(0)}%</div>
                <div className={`px-2 py-0.5 text-xs rounded ${
                  sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                  sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {sentiment}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Opportunity & Risk Flags */}
      <div className="grid grid-cols-2 gap-4">
        {data.opportunity_flags?.length > 0 && (
          <div className="p-4 bg-green-50 rounded-lg">
            <h4 className="text-sm font-medium text-green-800 mb-2">Opportunities</h4>
            <ul className="text-sm text-green-700 space-y-1">
              {data.opportunity_flags.map((flag, i) => (
                <li key={i}>• {flag}</li>
              ))}
            </ul>
          </div>
        )}
        {data.risk_flags?.length > 0 && (
          <div className="p-4 bg-red-50 rounded-lg">
            <h4 className="text-sm font-medium text-red-800 mb-2">Risks</h4>
            <ul className="text-sm text-red-700 space-y-1">
              {data.risk_flags.map((flag, i) => (
                <li key={i}>• {flag}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Trend */}
      <div className="mt-4 flex items-center gap-2 text-sm">
        <span className="text-gray-500">Trend:</span>
        <span className={`px-2 py-0.5 rounded ${
          data.trend_direction === 'increasing' ? 'bg-green-100 text-green-700' :
          data.trend_direction === 'decreasing' ? 'bg-red-100 text-red-700' :
          'bg-gray-100 text-gray-700'
        }`}>
          {data.trend_direction === 'increasing' ? '↑' : data.trend_direction === 'decreasing' ? '↓' : '→'} {data.trend_direction}
        </span>
      </div>
    </div>
  );
}

// ── Comparison Table ──────────────────────────────────────────────────────────

function ComparisonTable({ data }) {
  if (!data?.metrics?.length) return null;

  const formatValue = (value, unit) => {
    if (value === null || value === undefined) return 'N/A';
    if (unit === 'USD') {
      if (value >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
      if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
      return `$${(value / 1_000_000).toFixed(0)}M`;
    }
    if (unit === 'count') return value.toLocaleString();
    return value.toFixed(2);
  };

  const tickers = data.tickers || [];

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Metric</th>
            {tickers.map(ticker => (
              <th key={ticker} className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                {ticker}
              </th>
            ))}
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Leader</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.metrics.map((metric, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              <td className="px-4 py-3">
                <div className="text-sm font-medium text-gray-900">{metric.metric_description}</div>
                <div className="text-xs text-gray-500">{metric.unit}</div>
              </td>
              {tickers.map(ticker => (
                <td
                  key={ticker}
                  className={`px-4 py-3 text-center text-sm ${
                    metric.leader === ticker ? 'font-bold text-blue-600' : 'text-gray-900'
                  }`}
                >
                  {formatValue(metric.values?.[ticker], metric.unit)}
                </td>
              ))}
              <td className="px-4 py-3 text-center">
                <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                  {metric.leader}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page Component ───────────────────────────────────────────────────────

export default function EntityAnalysisPage() {
  // State
  const [sectors, setSectors] = useState([]);
  const [activeSector, setActiveSector] = useState(null);
  const [entities, setEntities] = useState([]);
  const [selectedTickers, setSelectedTickers] = useState([]);
  const [activeTab, setActiveTab] = useState('browse'); // browse, supply-chain, thematic, compare

  // Analysis data
  const [supplyChainData, setSupplyChainData] = useState(null);
  const [thematicData, setThematicData] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);

  // Input states
  const [themeInput, setThemeInput] = useState('AI');
  const [supplyChainTicker, setSupplyChainTicker] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load sectors on mount
  useEffect(() => {
    fetchSectors();
  }, []);

  const fetchSectors = async () => {
    try {
      const res = await apiFetch(`/entities/multi/sectors`);
      const data = await res.json();
      setSectors(data.sectors || []);
    } catch (err) {
      setError('Failed to load sectors');
    }
  };

  const fetchSectorEntities = async (sector) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/entities/multi/by-sector/${sector}`);
      const data = await res.json();
      setEntities(data.entities || []);
    } catch (err) {
      setError('Failed to load entities');
    } finally {
      setLoading(false);
    }
  };

  const handleSectorClick = (sector) => {
    setActiveSector(sector);
    fetchSectorEntities(sector);
  };

  const handleEntityClick = (ticker) => {
    setSelectedTickers(prev =>
      prev.includes(ticker)
        ? prev.filter(t => t !== ticker)
        : [...prev, ticker]
    );
  };

  const fetchSupplyChain = async () => {
    if (!supplyChainTicker) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/entities/multi/supply-chain/${supplyChainTicker}`);
      const data = await res.json();
      setSupplyChainData(data);
    } catch (err) {
      setError('Failed to load supply chain');
    } finally {
      setLoading(false);
    }
  };

  const analyzeTheme = async () => {
    if (!themeInput || selectedTickers.length === 0) return;
    setLoading(true);
    try {
      const tickerStr = selectedTickers.join(',');
      const res = await apiFetch(`/entities/multi/analyze/theme?theme=${encodeURIComponent(themeInput)}&tickers=${tickerStr}`);
      const data = await res.json();
      setThematicData(data);
    } catch (err) {
      setError('Failed to analyze theme');
    } finally {
      setLoading(false);
    }
  };

  const compareEntities = async () => {
    if (selectedTickers.length < 2) return;
    setLoading(true);
    try {
      const tickerStr = selectedTickers.join(',');
      const res = await apiFetch(`/entities/multi/compare?tickers=${tickerStr}`);
      const data = await res.json();
      setComparisonData(data);
    } catch (err) {
      setError('Failed to compare entities');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Multi-Entity Analysis | Finance Intelligence</title>
      </Head>

      <div className="research-dark min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Multi-Entity Analysis</h1>
            <p className="text-sm text-gray-500">Sector analysis, supply chains, and thematic research</p>
          </div>
        </header>

        {/* Tab Navigation */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <nav className="flex space-x-8">
              {[
                { id: 'browse', label: 'Browse Entities' },
                { id: 'supply-chain', label: 'Supply Chain' },
                { id: 'thematic', label: 'Thematic Analysis' },
                { id: 'compare', label: 'Compare' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 py-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">
              {error}
              <button onClick={() => setError(null)} className="ml-4 underline">Dismiss</button>
            </div>
          )}

          {/* Browse Tab */}
          {activeTab === 'browse' && (
            <div className="space-y-6">
              {/* Sector Grid */}
              <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-11 gap-3">
                {sectors.map(sector => (
                  <SectorCard
                    key={sector.value}
                    sector={sector}
                    onClick={handleSectorClick}
                    isActive={activeSector === sector.value}
                  />
                ))}
              </div>

              {/* Selected Tickers */}
              {selectedTickers.length > 0 && (
                <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
                  <span className="text-sm text-blue-700">Selected:</span>
                  {selectedTickers.map(ticker => (
                    <span key={ticker} className="px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded">
                      {ticker}
                      <button
                        onClick={() => handleEntityClick(ticker)}
                        className="ml-1 text-blue-500 hover:text-blue-700"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <button
                    onClick={() => setSelectedTickers([])}
                    className="ml-auto text-sm text-blue-600 hover:underline"
                  >
                    Clear all
                  </button>
                </div>
              )}

              {/* Entity Table */}
              {loading ? (
                <div className="text-center py-12 text-gray-500">Loading entities...</div>
              ) : entities.length > 0 ? (
                <div className="bg-white rounded-lg shadow">
                  <EntityTable
                    entities={entities}
                    onEntityClick={handleEntityClick}
                    selectedTickers={selectedTickers}
                  />
                </div>
              ) : activeSector ? (
                <div className="text-center py-12 text-gray-500">No entities found in this sector</div>
              ) : (
                <div className="text-center py-12 text-gray-500">Select a sector to view entities</div>
              )}
            </div>
          )}

          {/* Supply Chain Tab */}
          {activeTab === 'supply-chain' && (
            <div className="space-y-6">
              <div className="flex gap-4 items-center">
                <input
                  type="text"
                  value={supplyChainTicker}
                  onChange={(e) => setSupplyChainTicker(e.target.value.toUpperCase())}
                  placeholder="Enter ticker (e.g., NVDA)"
                  className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  onClick={fetchSupplyChain}
                  disabled={!supplyChainTicker || loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Analyze Supply Chain
                </button>
              </div>

              {loading ? (
                <div className="text-center py-12 text-gray-500">Loading supply chain...</div>
              ) : supplyChainData ? (
                <SupplyChainView data={supplyChainData} />
              ) : (
                <div className="text-center py-12 text-gray-500">
                  Enter a ticker to analyze its supply chain relationships
                </div>
              )}
            </div>
          )}

          {/* Thematic Analysis Tab */}
          {activeTab === 'thematic' && (
            <div className="space-y-6">
              <div className="flex gap-4 items-center">
                <input
                  type="text"
                  value={themeInput}
                  onChange={(e) => setThemeInput(e.target.value)}
                  placeholder="Theme (e.g., AI, cloud, EV)"
                  className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  onClick={analyzeTheme}
                  disabled={!themeInput || selectedTickers.length === 0 || loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Analyze Theme
                </button>
                {selectedTickers.length === 0 && (
                  <span className="text-sm text-gray-500">
                    Select entities from the Browse tab first
                  </span>
                )}
              </div>

              {/* Quick Theme Buttons */}
              <div className="flex flex-wrap gap-2">
                {['AI', 'Cloud', 'EV', '5G', 'Data Center', 'Gaming', 'Autonomous'].map(theme => (
                  <button
                    key={theme}
                    onClick={() => setThemeInput(theme)}
                    className={`px-3 py-1 text-sm rounded-full border ${
                      themeInput === theme
                        ? 'bg-blue-100 border-blue-500 text-blue-700'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {theme}
                  </button>
                ))}
              </div>

              {loading ? (
                <div className="text-center py-12 text-gray-500">Analyzing theme...</div>
              ) : thematicData ? (
                <ThematicAnalysisPanel data={thematicData} />
              ) : (
                <div className="text-center py-12 text-gray-500">
                  Select entities and enter a theme to analyze exposure
                </div>
              )}
            </div>
          )}

          {/* Compare Tab */}
          {activeTab === 'compare' && (
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <button
                  onClick={compareEntities}
                  disabled={selectedTickers.length < 2 || loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Compare Selected ({selectedTickers.length})
                </button>
                {selectedTickers.length < 2 && (
                  <span className="text-sm text-gray-500">
                    Select at least 2 entities from the Browse tab
                  </span>
                )}
              </div>

              {loading ? (
                <div className="text-center py-12 text-gray-500">Comparing entities...</div>
              ) : comparisonData ? (
                <ComparisonTable data={comparisonData} />
              ) : (
                <div className="text-center py-12 text-gray-500">
                  Select entities and click Compare to see metric comparison
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </>
  );
}
