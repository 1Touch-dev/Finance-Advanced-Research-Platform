/**
 * Sources Management Page
 * Wired to /sources/* API endpoints
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function Sources() {
  const [view, setView] = useState('health');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Health data
  const [healthData, setHealthData] = useState(null);
  const [runs, setRuns] = useState([]);
  const [records, setRecords] = useState([]);

  // Create source form
  const [sourceName, setSourceName] = useState('');
  const [sourceKind, setSourceKind] = useState('');

  // Run form
  const [runSourceId, setRunSourceId] = useState('');

  useEffect(() => {
    if (view === 'health') fetchHealth();
    if (view === 'runs') fetchRuns();
    if (view === 'records') fetchRecords();
  }, [view]);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/sources/health');
      if (!res.ok) throw new Error('Failed to fetch health');
      setHealthData(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/sources/runs?limit=50');
      if (!res.ok) throw new Error('Failed to fetch runs');
      setRuns(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecords = async (kind = '') => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: '100' });
      if (kind) params.append('kind', kind);
      const res = await apiFetch(`/sources/records?${params}`);
      if (!res.ok) throw new Error('Failed to fetch records');
      setRecords(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const bootstrap = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/sources/bootstrap', { method: 'POST' });
      if (!res.ok) throw new Error('Bootstrap failed');
      setSuccess('Sources tables bootstrapped');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createSource = async () => {
    if (!sourceName.trim() || !sourceKind.trim()) {
      setError('Name and kind are required');
      return;
    }
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      name: sourceName,
      kind: sourceKind,
    });

    try {
      const res = await apiFetch(`/sources?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to create source');
      const data = await res.json();
      setSuccess(`Source created: ID ${data.id}`);
      setSourceName('');
      setSourceKind('');
      fetchHealth();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const triggerRun = async () => {
    if (!runSourceId) {
      setError('Source ID required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/sources/${runSourceId}/runs`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to trigger run');
      const data = await res.json();
      setSuccess(`Run triggered: ID ${data.run_id}, Status: ${data.status}`);
      fetchRuns();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      success: 'bg-green-100 text-green-700',
      error: 'bg-red-100 text-red-700',
      pending: 'bg-yellow-100 text-yellow-700',
      running: 'bg-blue-100 text-blue-700',
      never_run: 'bg-gray-100 text-gray-600',
    };
    return colors[status] || 'bg-gray-100 text-gray-600';
  };

  return (
    <Layout>
      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Data Sources</h1>
        <p className="text-gray-600 mb-6">
          Manage connector sources, trigger runs, view ingested records, and monitor health.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'health', label: 'Health' },
            { key: 'runs', label: 'Runs' },
            { key: 'records', label: 'Records' },
            { key: 'create', label: 'Create Source' },
            { key: 'setup', label: 'Setup' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setView(tab.key)}
              className={`px-4 py-2 rounded ${view === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Alerts */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
            {success}
            <button onClick={() => setSuccess(null)} className="ml-4">x</button>
          </div>
        )}

        {/* Health View */}
        {view === 'health' && healthData && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Registry Overview</h2>
              <div className="grid grid-cols-5 gap-4">
                <div className="text-center">
                  <div className="text-3xl font-bold">{healthData.sources}</div>
                  <div className="text-sm text-gray-500">Sources</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold">{healthData.runs}</div>
                  <div className="text-sm text-gray-500">Total Runs</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-600">{healthData.success}</div>
                  <div className="text-sm text-gray-500">Successful</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-600">{healthData.errors}</div>
                  <div className="text-sm text-gray-500">Errors</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold">{((healthData.success_rate || 0) * 100).toFixed(0)}%</div>
                  <div className="text-sm text-gray-500">Success Rate</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b">
                <h2 className="text-lg font-bold">Source Status</h2>
              </div>
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3">ID</th>
                    <th className="text-left p-3">Name</th>
                    <th className="text-left p-3">Kind</th>
                    <th className="text-center p-3">Status</th>
                    <th className="text-right p-3">Records</th>
                    <th className="text-left p-3">Last Run</th>
                  </tr>
                </thead>
                <tbody>
                  {healthData.per_source?.map((s) => (
                    <tr key={s.id} className="border-t hover:bg-gray-50">
                      <td className="p-3">{s.id}</td>
                      <td className="p-3 font-medium">{s.name}</td>
                      <td className="p-3">{s.kind}</td>
                      <td className="p-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${getStatusColor(s.last_status)}`}>
                          {s.last_status}
                        </span>
                      </td>
                      <td className="p-3 text-right">{s.records?.toLocaleString() || 0}</td>
                      <td className="p-3 text-sm text-gray-500">{s.last_finished || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Runs View */}
        {view === 'runs' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Trigger Run</h3>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Source ID"
                  value={runSourceId}
                  onChange={(e) => setRunSourceId(e.target.value)}
                  className="flex-1 border rounded px-3 py-2"
                />
                <button onClick={triggerRun} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                  Trigger Run
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-bold">Recent Runs</h2>
                <button onClick={fetchRuns} className="text-blue-600 text-sm">Refresh</button>
              </div>
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3">Run ID</th>
                    <th className="text-left p-3">Source</th>
                    <th className="text-center p-3">Status</th>
                    <th className="text-left p-3">Started</th>
                    <th className="text-left p-3">Finished</th>
                    <th className="text-left p-3">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map?.((r) => (
                    <tr key={r.id} className="border-t hover:bg-gray-50">
                      <td className="p-3">{r.id}</td>
                      <td className="p-3">{r.source_id}</td>
                      <td className="p-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${getStatusColor(r.status)}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="p-3 text-sm">{r.started_at}</td>
                      <td className="p-3 text-sm">{r.finished_at || '-'}</td>
                      <td className="p-3 text-sm text-red-600">{r.error?.slice(0, 50) || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Records View */}
        {view === 'records' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-bold">Ingested Records ({records.total || 0})</h2>
              <button onClick={() => fetchRecords()} className="text-blue-600 text-sm">Refresh</button>
            </div>
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">External ID</th>
                  <th className="text-left p-3">Kind</th>
                  <th className="text-left p-3">Source</th>
                  <th className="text-left p-3">Last Ingested</th>
                </tr>
              </thead>
              <tbody>
                {records.records?.map?.((r, idx) => (
                  <tr key={idx} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-mono text-sm">{r.external_id}</td>
                    <td className="p-3">{r.kind}</td>
                    <td className="p-3">{r.source}</td>
                    <td className="p-3 text-sm">{r.last_ingested_at || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Create Source View */}
        {view === 'create' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Create New Source</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Name</label>
                <input
                  type="text"
                  placeholder="e.g., SEC EDGAR"
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Kind</label>
                <input
                  type="text"
                  placeholder="e.g., sec, bea, fred"
                  value={sourceKind}
                  onChange={(e) => setSourceKind(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>
            <button onClick={createSource} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
              {loading ? 'Creating...' : 'Create Source'}
            </button>
          </div>
        )}

        {/* Setup View */}
        {view === 'setup' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Bootstrap Sources Tables</h3>
            <p className="text-gray-600 mb-4">Initialize database tables for connector sources.</p>
            <button onClick={bootstrap} disabled={loading} className="bg-purple-600 text-white px-6 py-2 rounded disabled:opacity-50">
              {loading ? 'Bootstrapping...' : 'Bootstrap'}
            </button>
          </div>
        )}

        {loading && view === 'health' && !healthData && (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        )}
      </div>
    </Layout>
  );
}
