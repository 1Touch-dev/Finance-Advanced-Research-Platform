import { useState } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData , apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function RecursiveDiscoveryPage() {
  const [ticker, setTicker] = useState('');
  const [compareTicker, setCompareTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [graph, setGraph] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [circular, setCircular] = useState(null);
  const [chain, setChain] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [activeTab, setActiveTab] = useState('graph');
  const [noData, setNoData] = useState(null);

  async function runDiscovery() {
    if (!ticker) return;
    setLoading(true);
    setNoData(null);
    const t = ticker.toUpperCase();
    try {
      const [graphRes, clustersRes, circularRes, chainRes] = await Promise.all([
        apiFetch(`/recursive/graph/${t}?max_depth=3`),
        apiFetch(`/recursive/clusters/${t}`),
        apiFetch(`/recursive/circular/${t}`),
        apiFetch(`/recursive/chain/${t}`)
      ]);
      const graphData = await graphRes.json();
      if (isNoData(graphData)) { setNoData(graphData); setLoading(false); return; }
      setGraph(graphData);
      setClusters(await clustersRes.json());
      setCircular(await circularRes.json());
      setChain(await chainRes.json());
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function compareNetworks() {
    if (!ticker || !compareTicker) return;
    try {
      const res = await apiFetch(`/recursive/compare?ticker1=${ticker.toUpperCase()}&ticker2=${compareTicker.toUpperCase()}`);
      setComparison(await res.json());
      setActiveTab('compare');
    } catch (err) {
      console.error('Error:', err);
    }
  }

  const tabs = [
    { id: 'graph', label: 'Entity Graph' },
    { id: 'clusters', label: 'Clusters' },
    { id: 'circular', label: 'Circular Ownership' },
    { id: 'chain', label: 'Ownership Chain' },
    { id: 'compare', label: 'Compare Networks' }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Recursive Entity Discovery | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Recursive Entity Discovery</h1>

      {/* Search */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex gap-4 mb-4">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Enter ticker (e.g., NVDA)"
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
            onKeyPress={(e) => e.key === 'Enter' && runDiscovery()}
          />
          <button
            onClick={runDiscovery}
            disabled={loading || !ticker}
            className="bg-blue-600 hover:bg-blue-500 px-8 py-3 rounded-lg font-semibold disabled:opacity-50"
          >
            {loading ? 'Discovering...' : 'Discover'}
          </button>
        </div>

        {/* Compare section */}
        <div className="flex gap-4 pt-4 border-t border-gray-700">
          <input
            type="text"
            value={compareTicker}
            onChange={(e) => setCompareTicker(e.target.value.toUpperCase())}
            placeholder="Compare with (e.g., AMD)"
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
          />
          <button
            onClick={compareNetworks}
            disabled={!ticker || !compareTicker}
            className="bg-purple-600 hover:bg-purple-500 px-6 py-3 rounded-lg font-semibold disabled:opacity-50"
          >
            Compare Networks
          </button>
        </div>
      </div>

      {noData && <div className="mb-6"><NoDataCard {...noData} /></div>}

      {graph && (
        <>
          {/* Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg whitespace-nowrap ${
                  activeTab === tab.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="bg-gray-800 rounded-lg p-6">
            {activeTab === 'graph' && graph && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Entity Relationship Graph</h2>

                {/* Statistics */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-blue-400">{graph.statistics.total_nodes}</div>
                    <div className="text-gray-400 text-sm">Nodes</div>
                  </div>
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-green-400">{graph.statistics.total_edges}</div>
                    <div className="text-gray-400 text-sm">Edges</div>
                  </div>
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-purple-400">{graph.statistics.max_depth}</div>
                    <div className="text-gray-400 text-sm">Max Depth</div>
                  </div>
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-400">{graph.statistics.density}</div>
                    <div className="text-gray-400 text-sm">Density</div>
                  </div>
                </div>

                {/* Nodes list */}
                <h3 className="text-lg font-semibold mb-3">Discovered Nodes</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {graph.graph.nodes.map((node, idx) => (
                    <div key={idx} className="p-3 bg-gray-700 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">{node.label}</span>
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          node.type === 'root' ? 'bg-blue-600' :
                          node.type === 'subsidiary' ? 'bg-green-600' :
                          node.type === 'affiliate' ? 'bg-purple-600' : 'bg-gray-600'
                        }`}>
                          {node.type}
                        </span>
                      </div>
                      <div className="text-gray-400 text-sm mt-1">Depth: {node.depth}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'clusters' && clusters && (
              <div>
                <h2 className="text-xl font-semibold mb-4">
                  Entity Clusters ({clusters.total_clusters})
                </h2>
                <div className="space-y-4">
                  {clusters.clusters.map((cluster, idx) => (
                    <div key={idx} className="p-4 bg-gray-700 rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <span className="font-semibold text-lg">{cluster.name}</span>
                          <span className={`ml-3 px-2 py-1 rounded text-sm ${
                            cluster.type === 'geographic' ? 'bg-blue-600' :
                            cluster.type === 'industry' ? 'bg-green-600' : 'bg-purple-600'
                          }`}>
                            {cluster.type}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-400">Cohesion Score</div>
                          <div className="font-bold text-green-400">{(cluster.cohesion_score * 100).toFixed(0)}%</div>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {cluster.entities.map((entity, i) => (
                          <span key={i} className="px-2 py-1 bg-gray-600 rounded text-sm">{entity}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'circular' && circular && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Circular Ownership Detection</h2>
                <div className={`p-6 rounded-lg mb-4 ${
                  circular.circular_ownership_detected ? 'bg-red-900/50 border border-red-500' : 'bg-green-900/50 border border-green-500'
                }`}>
                  <div className="flex items-center gap-3">
                    <span className={`text-3xl ${circular.circular_ownership_detected ? 'text-red-400' : 'text-green-400'}`}>
                      {circular.circular_ownership_detected ? '⚠️' : '✓'}
                    </span>
                    <div>
                      <div className="font-semibold text-lg">
                        {circular.circular_ownership_detected ? 'Circular Ownership Detected' : 'No Circular Ownership'}
                      </div>
                      <div className="text-gray-400">
                        Risk Level: <span className={
                          circular.risk_level === 'high' ? 'text-red-400' :
                          circular.risk_level === 'medium' ? 'text-yellow-400' : 'text-green-400'
                        }>{circular.risk_level}</span>
                      </div>
                    </div>
                  </div>
                </div>
                {circular.cycles.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Detected Cycles</h3>
                    {circular.cycles.map((cycle, idx) => (
                      <div key={idx} className="p-4 bg-gray-700 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          {cycle.path.map((node, i) => (
                            <span key={i} className="flex items-center">
                              <span className="px-2 py-1 bg-gray-600 rounded">{node}</span>
                              {i < cycle.path.length - 1 && <span className="mx-2 text-gray-500">→</span>}
                            </span>
                          ))}
                        </div>
                        <div className="text-gray-400 text-sm">Total Stake: {cycle.total_stake}%</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'chain' && chain && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Ownership Chain</h2>
                <p className="text-gray-400 mb-4">Ultimate Parent: <span className="text-white font-semibold">{chain.ultimate_parent}</span></p>
                <div className="space-y-2">
                  {chain.chain.map((level, idx) => (
                    <div key={idx} className="flex items-center gap-4">
                      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold">
                        {level.level}
                      </div>
                      <div className="flex-1 p-4 bg-gray-700 rounded-lg flex items-center justify-between">
                        <span className="font-semibold">{level.entity}</span>
                        <span className="text-gray-400">{level.ownership}% ownership</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'compare' && comparison && (
              <div>
                <h2 className="text-xl font-semibold mb-4">
                  Network Comparison: {comparison.ticker1} vs {comparison.ticker2}
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-blue-400">{comparison.common_entities.length}</div>
                    <div className="text-gray-400 text-sm">Common Entities</div>
                  </div>
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-green-400">{comparison.common_board_members}</div>
                    <div className="text-gray-400 text-sm">Board Members</div>
                  </div>
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-purple-400">{comparison.common_investors}</div>
                    <div className="text-gray-400 text-sm">Common Investors</div>
                  </div>
                  <div className="text-center p-4 bg-gray-700 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-400">{(comparison.network_overlap_score * 100).toFixed(0)}%</div>
                    <div className="text-gray-400 text-sm">Overlap Score</div>
                  </div>
                </div>
                <div className="p-4 bg-gray-700 rounded-lg">
                  <div className="text-gray-400 mb-2">Relationship Strength</div>
                  <div className={`text-xl font-bold ${
                    comparison.relationship_strength === 'strong' ? 'text-green-400' :
                    comparison.relationship_strength === 'moderate' ? 'text-yellow-400' :
                    comparison.relationship_strength === 'weak' ? 'text-orange-400' : 'text-gray-400'
                  }`}>
                    {comparison.relationship_strength.charAt(0).toUpperCase() + comparison.relationship_strength.slice(1)}
                  </div>
                </div>
                {comparison.common_entities.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-lg font-semibold mb-3">Common Entities</h3>
                    <div className="flex flex-wrap gap-2">
                      {comparison.common_entities.map((entity, idx) => (
                        <span key={idx} className="px-3 py-1 bg-blue-600/50 border border-blue-500 rounded">{entity}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
