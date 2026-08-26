/**
 * Dashboard & Watchlist Page
 * Wired to /dashboard/* API endpoints
 * Configurable dashboards with widgets, shared watchlists
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function DashboardPage() {
  const [view, setView] = useState('dashboards');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Dashboards
  const [dashboards, setDashboards] = useState([]);
  const [selectedDashboard, setSelectedDashboard] = useState(null);
  const [dashboardName, setDashboardName] = useState('');

  // Widgets
  const [widgetTypes, setWidgetTypes] = useState([]);
  const [selectedWidgetType, setSelectedWidgetType] = useState('');

  // Watchlists
  const [sharedWatchlists, setSharedWatchlists] = useState([]);
  const [shareWatchlistId, setShareWatchlistId] = useState('');
  const [shareEmail, setShareEmail] = useState('');

  useEffect(() => {
    if (view === 'dashboards') fetchDashboards();
    if (view === 'widgets') fetchWidgetTypes();
    if (view === 'watchlists') fetchSharedWatchlists();
  }, [view]);

  const fetchDashboards = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/dashboard');
      if (!res.ok) throw new Error('Failed to fetch dashboards');
      setDashboards(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createDashboard = async () => {
    if (!dashboardName.trim()) {
      setError('Dashboard name required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch('/dashboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: dashboardName }),
      });
      if (!res.ok) throw new Error('Failed to create dashboard');
      const data = await res.json();
      setSuccess(`Dashboard created: ${data.name}`);
      setDashboardName('');
      fetchDashboards();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteDashboard = async (id) => {
    if (!confirm('Delete this dashboard?')) return;
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/dashboard/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete dashboard');
      setSuccess('Dashboard deleted');
      fetchDashboards();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchWidgetTypes = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/dashboard/widget-types');
      if (!res.ok) throw new Error('Failed to fetch widget types');
      setWidgetTypes(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addWidget = async (dashboardId) => {
    if (!selectedWidgetType) {
      setError('Select a widget type');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/dashboard/${dashboardId}/widgets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: selectedWidgetType }),
      });
      if (!res.ok) throw new Error('Failed to add widget');
      setSuccess('Widget added');
      fetchDashboards();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteWidget = async (dashboardId, widgetId) => {
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/dashboard/${dashboardId}/widgets/${widgetId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete widget');
      setSuccess('Widget deleted');
      fetchDashboards();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchSharedWatchlists = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/watchlist/shared');
      if (!res.ok) throw new Error('Failed to fetch shared watchlists');
      setSharedWatchlists(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const shareWatchlist = async () => {
    if (!shareWatchlistId || !shareEmail.trim()) {
      setError('Watchlist ID and email required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/watchlist/${shareWatchlistId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: shareEmail }),
      });
      if (!res.ok) throw new Error('Failed to share watchlist');
      setSuccess('Watchlist shared');
      setShareEmail('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const revokeShare = async (watchlistId, shareId) => {
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/watchlist/${watchlistId}/share/${shareId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to revoke share');
      setSuccess('Share revoked');
      fetchSharedWatchlists();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Dashboard</h1>
        <p className="text-gray-600 mb-6">
          Manage custom dashboards, widgets, and shared watchlists.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'dashboards', label: 'Dashboards' },
            { key: 'widgets', label: 'Widgets' },
            { key: 'watchlists', label: 'Shared Watchlists' },
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

        {/* Dashboards View */}
        {view === 'dashboards' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Create Dashboard</h3>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Dashboard name"
                  value={dashboardName}
                  onChange={(e) => setDashboardName(e.target.value)}
                  className="flex-1 border rounded px-3 py-2"
                />
                <button
                  onClick={createDashboard}
                  disabled={loading}
                  className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50"
                >
                  Create
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-bold">Your Dashboards</h2>
                <button onClick={fetchDashboards} className="text-blue-600 text-sm">Refresh</button>
              </div>
              {dashboards.length === 0 ? (
                <div className="p-6 text-center text-gray-500">No dashboards yet</div>
              ) : (
                <div className="divide-y">
                  {dashboards.map((d) => (
                    <div key={d.id} className="p-4 hover:bg-gray-50 flex justify-between items-center">
                      <div>
                        <h3 className="font-medium">{d.name}</h3>
                        <p className="text-sm text-gray-500">{d.widgets?.length || 0} widgets</p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSelectedDashboard(d)}
                          className="text-blue-600 text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => deleteDashboard(d.id)}
                          className="text-red-600 text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedDashboard && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-bold">Editing: {selectedDashboard.name}</h3>
                  <button onClick={() => setSelectedDashboard(null)} className="text-gray-500">Close</button>
                </div>

                <div className="mb-4">
                  <h4 className="font-medium mb-2">Widgets</h4>
                  {selectedDashboard.widgets?.length === 0 ? (
                    <p className="text-gray-500 text-sm">No widgets</p>
                  ) : (
                    <div className="space-y-2">
                      {selectedDashboard.widgets?.map((w) => (
                        <div key={w.id} className="flex justify-between items-center bg-gray-50 p-2 rounded">
                          <span>{w.type}</span>
                          <button
                            onClick={() => deleteWidget(selectedDashboard.id, w.id)}
                            className="text-red-600 text-sm"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <select
                    value={selectedWidgetType}
                    onChange={(e) => setSelectedWidgetType(e.target.value)}
                    className="flex-1 border rounded px-3 py-2"
                  >
                    <option value="">Select widget type...</option>
                    {widgetTypes.map((t) => (
                      <option key={t.type} value={t.type}>{t.name || t.type}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => addWidget(selectedDashboard.id)}
                    disabled={loading}
                    className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
                  >
                    Add Widget
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Widgets View */}
        {view === 'widgets' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b">
              <h2 className="text-lg font-bold">Available Widget Types</h2>
            </div>
            {loading ? (
              <div className="p-6 text-center text-gray-500">Loading...</div>
            ) : (
              <div className="grid grid-cols-2 gap-4 p-4">
                {widgetTypes.map((w) => (
                  <div key={w.type} className="border rounded p-4">
                    <h3 className="font-medium">{w.name || w.type}</h3>
                    {w.description && (
                      <p className="text-sm text-gray-600 mt-1">{w.description}</p>
                    )}
                    <span className="text-xs bg-gray-100 px-2 py-1 rounded mt-2 inline-block">
                      {w.type}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Watchlists View */}
        {view === 'watchlists' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Share Watchlist</h3>
              <div className="grid grid-cols-3 gap-4">
                <input
                  type="text"
                  placeholder="Watchlist ID"
                  value={shareWatchlistId}
                  onChange={(e) => setShareWatchlistId(e.target.value)}
                  className="border rounded px-3 py-2"
                />
                <input
                  type="email"
                  placeholder="Email to share with"
                  value={shareEmail}
                  onChange={(e) => setShareEmail(e.target.value)}
                  className="border rounded px-3 py-2"
                />
                <button
                  onClick={shareWatchlist}
                  disabled={loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
                >
                  Share
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-bold">Watchlists Shared With You</h2>
                <button onClick={fetchSharedWatchlists} className="text-blue-600 text-sm">Refresh</button>
              </div>
              {sharedWatchlists.length === 0 ? (
                <div className="p-6 text-center text-gray-500">No shared watchlists</div>
              ) : (
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3">Name</th>
                      <th className="text-left p-3">Owner</th>
                      <th className="text-left p-3">Items</th>
                      <th className="text-left p-3">Shared</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sharedWatchlists.map((w) => (
                      <tr key={w.id} className="border-t hover:bg-gray-50">
                        <td className="p-3 font-medium">{w.name}</td>
                        <td className="p-3">{w.owner_email || w.owner_id}</td>
                        <td className="p-3">{w.item_count || 0}</td>
                        <td className="p-3 text-sm text-gray-500">{w.shared_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
