import { useState } from 'react';
import Head from 'next/head';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function EntityDiscoveryPage() {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeJob, setActiveJob] = useState(null);
  const [entities, setEntities] = useState(null);
  const [graph, setGraph] = useState(null);
  const [familyTree, setFamilyTree] = useState(null);
  const [subsidiaries, setSubsidiaries] = useState(null);
  const [investments, setInvestments] = useState(null);
  const [boardConnections, setBoardConnections] = useState(null);
  const [activeTab, setActiveTab] = useState('entities');

  async function startDiscovery() {
    if (!ticker) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/agent/discover?ticker=${ticker}&depth=2`, { method: 'POST' });
      const data = await res.json();
      setActiveJob(data);
      // Fetch all data in parallel
      await fetchAllData();
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function fetchAllData() {
    const t = ticker.toUpperCase();
    try {
      const [entitiesRes, graphRes, treeRes, subsRes, invRes, boardRes] = await Promise.all([
        fetch(`${API_BASE}/agent/entities/${t}`),
        fetch(`${API_BASE}/agent/graph/${t}?depth=2`),
        fetch(`${API_BASE}/agent/family-tree/${t}`),
        fetch(`${API_BASE}/agent/subsidiaries/${t}`),
        fetch(`${API_BASE}/agent/investments/${t}`),
        fetch(`${API_BASE}/agent/board-connections/${t}`)
      ]);
      setEntities(await entitiesRes.json());
      setGraph(await graphRes.json());
      setFamilyTree(await treeRes.json());
      setSubsidiaries(await subsRes.json());
      setInvestments(await invRes.json());
      setBoardConnections(await boardRes.json());
    } catch (err) {
      console.error('Error:', err);
    }
  }

  const tabs = [
    { id: 'entities', label: 'Discovered Entities' },
    { id: 'subsidiaries', label: 'Subsidiaries' },
    { id: 'investments', label: 'Investments' },
    { id: 'board', label: 'Board Connections' },
    { id: 'tree', label: 'Family Tree' }
  ];

  function renderTree(node, level = 0) {
    if (!node) return null;
    return (
      <div style={{ marginLeft: level * 24 }} className="py-1">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs ${
            node.type === 'parent' ? 'bg-blue-600' :
            node.type === 'holding' ? 'bg-purple-600' : 'bg-gray-600'
          }`}>
            {node.type}
          </span>
          <span className="font-medium">{node.name}</span>
        </div>
        {node.children && node.children.map((child, i) => (
          <div key={i}>{renderTree(child, level + 1)}</div>
        ))}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Entity Discovery | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Autonomous Entity Discovery</h1>

      {/* Search */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Enter ticker symbol (e.g., NVDA, AAPL)"
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
            onKeyPress={(e) => e.key === 'Enter' && startDiscovery()}
          />
          <button
            onClick={startDiscovery}
            disabled={loading || !ticker}
            className="bg-blue-600 hover:bg-blue-500 px-8 py-3 rounded-lg font-semibold disabled:opacity-50"
          >
            {loading ? 'Discovering...' : 'Start Discovery'}
          </button>
        </div>
        {activeJob && (
          <div className="mt-4 p-3 bg-gray-700 rounded-lg">
            <div className="flex items-center gap-3">
              <span className="px-2 py-1 bg-green-600 rounded text-sm">Job Started</span>
              <span className="text-gray-400">ID: {activeJob.job_id}</span>
              <span className="text-gray-400">Depth: {activeJob.depth}</span>
            </div>
          </div>
        )}
      </div>

      {entities && (
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
            {activeTab === 'entities' && entities && (
              <div>
                <h2 className="text-xl font-semibold mb-4">
                  Discovered Entities ({entities.count})
                </h2>
                {entities.entities.length === 0 ? (
                  <p className="text-gray-400">No entities discovered yet</p>
                ) : (
                  <div className="space-y-3">
                    {entities.entities.map((entity, idx) => (
                      <div key={idx} className="p-4 bg-gray-700 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-lg">{entity.name}</span>
                          <span className={`px-3 py-1 rounded text-sm ${
                            entity.type === 'subsidiary' ? 'bg-green-600' :
                            entity.type === 'investment' ? 'bg-blue-600' :
                            entity.type === 'board_connection' ? 'bg-purple-600' : 'bg-gray-600'
                          }`}>
                            {entity.type}
                          </span>
                        </div>
                        {entity.ownership && <p className="text-gray-400">Ownership: {entity.ownership}%</p>}
                        {entity.acquired && <p className="text-gray-400">Acquired: {entity.acquired}</p>}
                        {entity.person && <p className="text-gray-400">Person: {entity.person}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'subsidiaries' && subsidiaries && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Subsidiaries</h2>
                <p className="text-gray-400 text-sm mb-4">Source: {subsidiaries.source}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {subsidiaries.subsidiaries.map((sub, idx) => (
                    <div key={idx} className="p-4 bg-gray-700 rounded-lg">
                      <div className="font-semibold">{sub.name}</div>
                      <div className="text-gray-400 text-sm">
                        {sub.jurisdiction} | {sub.ownership}% owned
                      </div>
                      <span className={`inline-block mt-2 px-2 py-0.5 rounded text-xs ${
                        sub.active ? 'bg-green-600' : 'bg-red-600'
                      }`}>
                        {sub.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'investments' && investments && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Investment Holdings</h2>
                <p className="text-gray-400 mb-4">Total Value: {investments.total_value}</p>
                <div className="space-y-3">
                  {investments.investments.map((inv, idx) => (
                    <div key={idx} className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                      <div>
                        <div className="font-semibold">{inv.company}</div>
                        <div className="text-gray-400 text-sm">{inv.type}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold">{inv.value}</div>
                        <div className="text-gray-400 text-sm">{inv.stake} stake</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'board' && boardConnections && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Board Connections</h2>
                <div className="space-y-3">
                  {boardConnections.board_connections.map((conn, idx) => (
                    <div key={idx} className="p-4 bg-gray-700 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold">{conn.person}</span>
                        <span className="px-2 py-1 bg-purple-600 rounded text-sm">{conn.role}</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {conn.other_boards.map((board, i) => (
                          <span key={i} className="px-2 py-1 bg-gray-600 rounded text-sm">{board}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'tree' && familyTree && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Corporate Family Tree</h2>
                <p className="text-gray-400 mb-4">Ultimate Parent: {familyTree.ultimate_parent}</p>
                <div className="p-4 bg-gray-700 rounded-lg">
                  {renderTree(familyTree.tree)}
                </div>
              </div>
            )}
          </div>

          {/* Graph Stats */}
          {graph && (
            <div className="mt-6 bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Entity Graph Statistics</h2>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-blue-400">{graph.node_count}</div>
                  <div className="text-gray-400">Nodes</div>
                </div>
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-green-400">{graph.edge_count}</div>
                  <div className="text-gray-400">Connections</div>
                </div>
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-purple-400">{graph.depth}</div>
                  <div className="text-gray-400">Depth</div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
