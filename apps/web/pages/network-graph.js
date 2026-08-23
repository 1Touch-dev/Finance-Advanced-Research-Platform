import { useState, useEffect, useRef, useCallback } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Entity type colors
const TYPE_COLORS = {
  person: '#3B82F6',   // Blue
  org: '#10B981',      // Green
  fund: '#8B5CF6',     // Purple
  agency: '#F59E0B',   // Amber
  pac: '#EF4444',      // Red
  case: '#6B7280',     // Gray
};

const CONFIDENCE_COLORS = {
  CONFIRMED: '#10B981',
  REPORTED: '#3B82F6',
  INFERRED: '#F59E0B',
  SPECULATIVE: '#EF4444',
};

export default function NetworkGraphPage() {
  const [seedEntity, setSeedEntity] = useState('person:peter-thiel');
  const [maxDepth, setMaxDepth] = useState(2);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [connectionSource, setConnectionSource] = useState('');
  const [connectionTarget, setConnectionTarget] = useState('');
  const [pathResults, setPathResults] = useState(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [graphStats, setGraphStats] = useState(null);
  const canvasRef = useRef(null);
  const [nodePositions, setNodePositions] = useState({});

  // Fetch graph stats on load
  useEffect(() => {
    fetchGraphStats();
  }, []);

  async function fetchGraphStats() {
    try {
      const res = await fetch(`${API_BASE}/intelligence/graph/stats`);
      const data = await res.json();
      setGraphStats(data);
      setDataLoaded(data.total_entities > 0);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }

  async function loadPayPalMafia() {
    setLoading(true);
    try {
      const res = await apiFetch(`/intelligence/graph/paypal-mafia/load`, { method: 'POST' });
      const data = await res.json();
      alert(`Loaded: ${data.entities_loaded} entities, ${data.edges_loaded} edges`);
      fetchGraphStats();
    } catch (err) {
      console.error('Error:', err);
      alert('Error loading PayPal Mafia data');
    }
    setLoading(false);
  }

  async function exploreNetwork() {
    if (!seedEntity) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/intelligence/graph/explore/${encodeURIComponent(seedEntity)}?max_depth=${maxDepth}&max_nodes=200`
      );
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        setGraphData(data);
        initializeNodePositions(data.nodes);
      }
    } catch (err) {
      console.error('Error:', err);
      alert('Error exploring network');
    }
    setLoading(false);
  }

  async function explorePayPalMafia() {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/intelligence/graph/paypal-mafia/explore?seed=${encodeURIComponent(seedEntity)}&max_depth=${maxDepth}`
      );
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        setGraphData(data);
        initializeNodePositions(data.nodes);
      }
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function findConnection() {
    if (!connectionSource || !connectionTarget) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/intelligence/graph/connect?src=${encodeURIComponent(connectionSource)}&dst=${encodeURIComponent(connectionTarget)}&max_depth=4`
      );
      const data = await res.json();
      setPathResults(data);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  function initializeNodePositions(nodes) {
    const positions = {};
    const centerX = 400;
    const centerY = 300;
    const radius = 200;

    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      positions[node.id] = {
        x: centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 50,
        y: centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 50,
      };
    });
    setNodePositions(positions);
  }

  // Force-directed layout simulation
  useEffect(() => {
    if (!graphData || Object.keys(nodePositions).length === 0) return;

    const simulate = () => {
      const newPositions = { ...nodePositions };
      const nodes = graphData.nodes;
      const edges = graphData.edges;

      // Apply forces
      nodes.forEach(node => {
        if (!newPositions[node.id]) return;

        let fx = 0, fy = 0;

        // Repulsion between nodes
        nodes.forEach(other => {
          if (node.id === other.id || !newPositions[other.id]) return;
          const dx = newPositions[node.id].x - newPositions[other.id].x;
          const dy = newPositions[node.id].y - newPositions[other.id].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 2000 / (dist * dist);
          fx += (dx / dist) * force;
          fy += (dy / dist) * force;
        });

        // Attraction along edges
        edges.forEach(edge => {
          let otherId = null;
          if (edge.src === node.id) otherId = edge.dst;
          else if (edge.dst === node.id) otherId = edge.src;
          if (!otherId || !newPositions[otherId]) return;

          const dx = newPositions[otherId].x - newPositions[node.id].x;
          const dy = newPositions[otherId].y - newPositions[node.id].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (dist - 120) * 0.01;
          fx += (dx / dist) * force;
          fy += (dy / dist) * force;
        });

        // Center gravity
        fx += (400 - newPositions[node.id].x) * 0.001;
        fy += (300 - newPositions[node.id].y) * 0.001;

        // Apply forces with damping
        newPositions[node.id] = {
          x: Math.max(50, Math.min(750, newPositions[node.id].x + fx * 0.5)),
          y: Math.max(50, Math.min(550, newPositions[node.id].y + fy * 0.5)),
        };
      });

      setNodePositions(newPositions);
    };

    const interval = setInterval(simulate, 50);
    const timeout = setTimeout(() => clearInterval(interval), 3000);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [graphData]);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Head>
        <title>Network Graph | Finance Intelligence</title>
      </Head>

      <div className="p-6">
        <h1 className="text-3xl font-bold mb-2">Intelligence Network Graph</h1>
        <p className="text-gray-400 mb-6">Follow the Money - Explore entity relationships and connections</p>

        {/* Stats Banner */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold">{graphStats?.total_entities || 0}</div>
            <div className="text-sm text-gray-400">Total Entities</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold">{graphStats?.total_edges || 0}</div>
            <div className="text-sm text-gray-400">Total Edges</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold">{graphStats?.indexed_identifiers || 0}</div>
            <div className="text-sm text-gray-400">Indexed IDs</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            {!dataLoaded ? (
              <button
                onClick={loadPayPalMafia}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-medium disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Load PayPal Mafia Demo'}
              </button>
            ) : (
              <div className="text-green-500 font-medium">Data Loaded</div>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm text-gray-400 mb-1">Seed Entity ID</label>
              <input
                type="text"
                value={seedEntity}
                onChange={e => setSeedEntity(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                placeholder="person:peter-thiel"
              />
            </div>
            <div className="w-24">
              <label className="block text-sm text-gray-400 mb-1">Max Depth</label>
              <select
                value={maxDepth}
                onChange={e => setMaxDepth(parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600"
              >
                {[1, 2, 3, 4, 5].map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <button
              onClick={explorePayPalMafia}
              disabled={loading || !dataLoaded}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium disabled:opacity-50"
            >
              {loading ? 'Exploring...' : 'Explore Network'}
            </button>
          </div>
        </div>

        {/* Find Connection */}
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <h3 className="font-medium mb-3">Find Connection Between Entities</h3>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm text-gray-400 mb-1">Source Entity</label>
              <input
                type="text"
                value={connectionSource}
                onChange={e => setConnectionSource(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                placeholder="person:peter-thiel"
              />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm text-gray-400 mb-1">Target Entity</label>
              <input
                type="text"
                value={connectionTarget}
                onChange={e => setConnectionTarget(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                placeholder="person:steve-chen"
              />
            </div>
            <button
              onClick={findConnection}
              disabled={loading || !connectionSource || !connectionTarget}
              className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded font-medium disabled:opacity-50"
            >
              Find Paths
            </button>
          </div>

          {/* Path Results */}
          {pathResults && (
            <div className="mt-4">
              <div className="text-sm text-gray-400 mb-2">
                Found {pathResults.paths_found} path(s) from {pathResults.src} to {pathResults.dst}
              </div>
              {pathResults.paths?.slice(0, 3).map((path, i) => (
                <div key={i} className="bg-gray-700 rounded p-3 mb-2">
                  <div className="text-xs text-gray-400 mb-1">
                    Path {i + 1} (depth: {path.depth}, confidence: {path.confidence_floor})
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {path.nodes.map((node, j) => (
                      <span key={j} className="flex items-center">
                        <span
                          className="px-2 py-1 rounded text-sm"
                          style={{ backgroundColor: TYPE_COLORS[node.kind] || '#6B7280' }}
                        >
                          {node.name}
                        </span>
                        {j < path.edges.length && (
                          <span className="mx-2 text-gray-400 text-xs">
                            → {path.edges[j].type} →
                          </span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Graph Visualization */}
        {graphData && (
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-medium">
                Network from {graphData.seed?.name || seedEntity}
              </h3>
              <div className="text-sm text-gray-400">
                {graphData.nodes_explored} nodes, {graphData.edges?.length || 0} edges, depth {graphData.depth_reached}
              </div>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-4 mb-4 text-sm">
              {Object.entries(TYPE_COLORS).map(([type, color]) => (
                <div key={type} className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-gray-400">{type}</span>
                </div>
              ))}
            </div>

            {/* SVG Graph */}
            <svg
              viewBox="0 0 800 600"
              className="w-full bg-gray-900 rounded-lg border border-gray-700"
              style={{ minHeight: '500px' }}
            >
              {/* Edges */}
              {graphData.edges?.map((edge, i) => {
                const src = nodePositions[edge.src];
                const dst = nodePositions[edge.dst];
                if (!src || !dst) return null;
                return (
                  <g key={i}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={dst.x}
                      y2={dst.y}
                      stroke={CONFIDENCE_COLORS[edge.confidence] || '#4B5563'}
                      strokeWidth={1.5}
                      opacity={0.6}
                    />
                    <text
                      x={(src.x + dst.x) / 2}
                      y={(src.y + dst.y) / 2 - 5}
                      fill="#9CA3AF"
                      fontSize="8"
                      textAnchor="middle"
                    >
                      {edge.type}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {graphData.nodes?.map((node, i) => {
                const pos = nodePositions[node.id];
                if (!pos) return null;
                const isSelected = selectedNode?.id === node.id;
                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onClick={() => setSelectedNode(node)}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle
                      r={isSelected ? 18 : 14}
                      fill={TYPE_COLORS[node.kind] || '#6B7280'}
                      stroke={isSelected ? '#fff' : 'transparent'}
                      strokeWidth={2}
                    />
                    <text
                      y={25}
                      fill="#fff"
                      fontSize="10"
                      textAnchor="middle"
                    >
                      {node.name.length > 15 ? node.name.slice(0, 15) + '...' : node.name}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Selected Node Details */}
            {selectedNode && (
              <div className="mt-4 bg-gray-700 rounded p-4">
                <h4 className="font-medium mb-2">{selectedNode.name}</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-gray-400">ID:</div>
                  <div>{selectedNode.id}</div>
                  <div className="text-gray-400">Type:</div>
                  <div>{selectedNode.kind}</div>
                </div>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => {
                      setSeedEntity(selectedNode.id);
                      explorePayPalMafia();
                    }}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
                  >
                    Explore from here
                  </button>
                  <button
                    onClick={() => setConnectionSource(selectedNode.id)}
                    className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-sm"
                  >
                    Set as source
                  </button>
                  <button
                    onClick={() => setConnectionTarget(selectedNode.id)}
                    className="px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded text-sm"
                  >
                    Set as target
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Interesting Queries */}
        <div className="bg-gray-800 rounded-lg p-4 mt-6">
          <h3 className="font-medium mb-3">Pre-defined Queries</h3>
          <div className="grid grid-cols-2 gap-4">
            {[
              { name: 'Thiel to YouTube', src: 'person:peter-thiel', dst: 'org:youtube' },
              { name: 'Musk to Affirm', src: 'person:elon-musk', dst: 'org:affirm' },
              { name: 'Sequoia to PayPal', src: 'fund:sequoia', dst: 'org:paypal' },
              { name: 'Hoffman to Palantir', src: 'person:reid-hoffman', dst: 'org:palantir' },
            ].map(query => (
              <button
                key={query.name}
                onClick={() => {
                  setConnectionSource(query.src);
                  setConnectionTarget(query.dst);
                }}
                className="text-left px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
              >
                <div className="font-medium">{query.name}</div>
                <div className="text-xs text-gray-400">{query.src} → {query.dst}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
