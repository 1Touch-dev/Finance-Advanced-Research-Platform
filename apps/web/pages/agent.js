/**
 * Autonomous Agent Page
 * Wired to /agent/* API endpoints
 * Auto-discover subsidiaries, investments, board connections
 */

import React, { useState } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function AutonomousAgent() {
  const [view, setView] = useState('discover');
  const [ticker, setTicker] = useState('');
  const [depth, setDepth] = useState(2);
  const [jobId, setJobId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const startDiscovery = async () => {
    if (!ticker.trim()) {
      setError('Ticker required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        ticker: ticker.toUpperCase(),
        depth: depth.toString(),
      });
      const res = await apiFetch(`/agent/discover?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to start discovery');
      const data = await res.json();
      setResult(data);
      if (data.job_id) setJobId(data.job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const checkJobStatus = async () => {
    if (!jobId.trim()) {
      setError('Job ID required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/agent/jobs/${jobId}`);
      if (!res.ok) throw new Error('Failed to get job status');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getEntities = async () => {
    if (!ticker.trim()) {
      setError('Ticker required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/agent/entities/${ticker.toUpperCase()}`);
      if (!res.ok) throw new Error('Failed to get entities');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getGraph = async () => {
    if (!ticker.trim()) {
      setError('Ticker required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ depth: depth.toString() });
      const res = await apiFetch(`/agent/graph/${ticker.toUpperCase()}?${params}`);
      if (!res.ok) throw new Error('Failed to get graph');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const discoverSubsidiaries = async () => {
    if (!ticker.trim()) {
      setError('Ticker required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/agent/subsidiaries/${ticker.toUpperCase()}`);
      if (!res.ok) throw new Error('Failed to discover subsidiaries');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const discoverInvestments = async () => {
    if (!ticker.trim()) {
      setError('Ticker required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/agent/investments/${ticker.toUpperCase()}`);
      if (!res.ok) throw new Error('Failed to discover investments');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const discoverBoardConnections = async () => {
    if (!ticker.trim()) {
      setError('Ticker required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/agent/board-connections/${ticker.toUpperCase()}`);
      if (!res.ok) throw new Error('Failed to discover board connections');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getFamilyTree = async () => {
    if (!ticker.trim()) {
      setError('Ticker required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/agent/family-tree/${ticker.toUpperCase()}`);
      if (!res.ok) throw new Error('Failed to get family tree');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      completed: 'bg-green-100 text-green-700',
      running: 'bg-blue-100 text-blue-700',
      pending: 'bg-yellow-100 text-yellow-700',
      failed: 'bg-red-100 text-red-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-600';
  };

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Autonomous Agent</h1>
        <p className="text-gray-600 mb-6">
          Auto-discover subsidiaries, investments, board connections, and entity relationships.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {[
            { key: 'discover', label: 'Start Discovery' },
            { key: 'status', label: 'Job Status' },
            { key: 'entities', label: 'View Entities' },
            { key: 'graph', label: 'Entity Graph' },
            { key: 'specific', label: 'Specific Discovery' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setView(tab.key); setResult(null); }}
              className={`px-4 py-2 rounded ${view === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Ticker Input */}
        {view !== 'status' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Ticker</label>
                <input
                  type="text"
                  placeholder="AAPL"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div className="w-32">
                <label className="block text-sm font-medium text-gray-700 mb-1">Depth</label>
                <select
                  value={depth}
                  onChange={(e) => setDepth(parseInt(e.target.value))}
                  className="w-full border rounded px-3 py-2"
                >
                  {[1, 2, 3, 4, 5].map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Alerts */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Start Discovery View */}
        {view === 'discover' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Start Discovery Job</h3>
            <p className="text-gray-600 mb-4">
              Launch an autonomous discovery job to find related entities, subsidiaries, and connections.
            </p>
            <button
              onClick={startDiscovery}
              disabled={loading}
              className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50"
            >
              {loading ? 'Starting...' : 'Start Discovery'}
            </button>

            {result?.job_id && (
              <div className="mt-4 bg-green-50 border border-green-200 p-4 rounded">
                <p className="font-medium">Discovery started!</p>
                <p className="text-sm text-gray-600">Job ID: {result.job_id}</p>
              </div>
            )}
          </div>
        )}

        {/* Job Status View */}
        {view === 'status' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Check Job Status</h3>
            <div className="flex gap-4 mb-4">
              <input
                type="text"
                placeholder="Job ID"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="flex-1 border rounded px-3 py-2"
              />
              <button
                onClick={checkJobStatus}
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50"
              >
                Check Status
              </button>
            </div>

            {result && (
              <div className="border rounded p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-medium">Status:</span>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${getStatusColor(result.status)}`}>
                    {result.status}
                  </span>
                </div>
                {result.progress !== undefined && (
                  <div className="mb-2">
                    <span className="font-medium">Progress:</span> {result.progress}%
                    <div className="w-full bg-gray-200 rounded h-2 mt-1">
                      <div className="bg-blue-600 h-2 rounded" style={{ width: `${result.progress}%` }} />
                    </div>
                  </div>
                )}
                {result.entities_found !== undefined && (
                  <p><span className="font-medium">Entities Found:</span> {result.entities_found}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* View Entities */}
        {view === 'entities' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Discovered Entities</h3>
            <button
              onClick={getEntities}
              disabled={loading}
              className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50 mb-4"
            >
              {loading ? 'Loading...' : 'Get Entities'}
            </button>

            {result?.entities && (
              <div className="space-y-2">
                {result.entities.map((e, idx) => (
                  <div key={idx} className="border rounded p-3 hover:bg-gray-50">
                    <div className="flex justify-between">
                      <span className="font-medium">{e.name}</span>
                      <span className="text-sm text-gray-500">{e.type}</span>
                    </div>
                    {e.relationship && (
                      <p className="text-sm text-gray-600">{e.relationship}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Entity Graph */}
        {view === 'graph' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Entity Graph</h3>
            <button
              onClick={getGraph}
              disabled={loading}
              className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50 mb-4"
            >
              {loading ? 'Loading...' : 'Get Graph'}
            </button>

            {result && (
              <div className="border rounded p-4">
                <p><span className="font-medium">Nodes:</span> {result.nodes?.length || 0}</p>
                <p><span className="font-medium">Edges:</span> {result.edges?.length || 0}</p>
                <pre className="mt-4 bg-gray-100 p-3 rounded text-xs overflow-x-auto max-h-96">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Specific Discovery */}
        {view === 'specific' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Specific Discovery Types</h3>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={discoverSubsidiaries}
                  disabled={loading}
                  className="bg-gray-200 hover:bg-gray-300 px-4 py-3 rounded disabled:opacity-50"
                >
                  Subsidiaries
                </button>
                <button
                  onClick={discoverInvestments}
                  disabled={loading}
                  className="bg-gray-200 hover:bg-gray-300 px-4 py-3 rounded disabled:opacity-50"
                >
                  Investments
                </button>
                <button
                  onClick={discoverBoardConnections}
                  disabled={loading}
                  className="bg-gray-200 hover:bg-gray-300 px-4 py-3 rounded disabled:opacity-50"
                >
                  Board Connections
                </button>
                <button
                  onClick={getFamilyTree}
                  disabled={loading}
                  className="bg-gray-200 hover:bg-gray-300 px-4 py-3 rounded disabled:opacity-50"
                >
                  Family Tree
                </button>
              </div>
            </div>

            {result && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="font-bold mb-4">Results</h3>
                <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto max-h-96">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
