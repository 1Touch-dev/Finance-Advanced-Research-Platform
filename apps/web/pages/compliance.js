/**
 * Compliance Dashboard Page
 * Wired to /compliance/* API endpoints
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function Compliance() {
  const [view, setView] = useState('policies');
  const [policies, setPolicies] = useState([]);
  const [exportRequests, setExportRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Policy form
  const [newPolicyName, setNewPolicyName] = useState('');
  const [newPolicyRules, setNewPolicyRules] = useState('{}');

  // Export request form
  const [exportReportId, setExportReportId] = useState('');

  // Bootstrap tables
  const bootstrap = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/compliance/bootstrap', { method: 'POST' });
      if (!res.ok) throw new Error('Bootstrap failed');
      setSuccess('Database tables bootstrapped successfully');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Create policy
  const createPolicy = async () => {
    if (!newPolicyName.trim()) {
      setError('Policy name is required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      let rules = {};
      try {
        rules = JSON.parse(newPolicyRules);
      } catch {
        throw new Error('Invalid JSON for rules');
      }

      const params = new URLSearchParams({
        name: newPolicyName,
      });
      const res = await apiFetch(`/compliance/policies?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rules),
      });
      if (!res.ok) throw new Error('Failed to create policy');
      const data = await res.json();
      setSuccess(`Policy created with ID: ${data.id}`);
      setNewPolicyName('');
      setNewPolicyRules('{}');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Request export approval
  const requestExport = async () => {
    if (!exportReportId.trim()) {
      setError('Report ID is required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        report_id: exportReportId,
      });
      const res = await apiFetch(`/compliance/export/request?${params}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to request export');
      const data = await res.json();
      setSuccess(`Export request created: ID ${data.id}, Status: ${data.status}`);
      setExportReportId('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Approve/reject export
  const processExport = async (eid, approve) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        approve: approve.toString(),
      });
      const res = await apiFetch(`/compliance/export/${eid}/approve?${params}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to process export');
      const data = await res.json();
      setSuccess(`Export ${eid} ${data.status}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Compliance Dashboard</h1>
        <p className="text-gray-600 mb-6">
          Manage compliance policies, export approvals, and audit controls.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'policies', label: 'Policies' },
            { key: 'exports', label: 'Export Approvals' },
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
            <button onClick={() => setSuccess(null)} className="ml-4 text-green-900">x</button>
          </div>
        )}

        {/* Policies View */}
        {view === 'policies' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Create Compliance Policy</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Policy Name</label>
                  <input
                    type="text"
                    placeholder="e.g., Data Export Policy"
                    value={newPolicyName}
                    onChange={(e) => setNewPolicyName(e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Rules (JSON)</label>
                  <textarea
                    placeholder='{"require_approval": true, "max_records": 10000}'
                    value={newPolicyRules}
                    onChange={(e) => setNewPolicyRules(e.target.value)}
                    rows={4}
                    className="w-full border rounded px-3 py-2 font-mono text-sm"
                  />
                </div>
                <button
                  onClick={createPolicy}
                  disabled={loading}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Creating...' : 'Create Policy'}
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Policy Types</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="border rounded p-4">
                  <h3 className="font-medium">Data Export</h3>
                  <p className="text-sm text-gray-600">Controls export of reports and data downloads</p>
                </div>
                <div className="border rounded p-4">
                  <h3 className="font-medium">Legal Hold</h3>
                  <p className="text-sm text-gray-600">Prevents deletion of litigation-relevant documents</p>
                </div>
                <div className="border rounded p-4">
                  <h3 className="font-medium">Data Retention</h3>
                  <p className="text-sm text-gray-600">Automatic data lifecycle management</p>
                </div>
                <div className="border rounded p-4">
                  <h3 className="font-medium">Access Control</h3>
                  <p className="text-sm text-gray-600">Role-based access to sensitive data</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Exports View */}
        {view === 'exports' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Request Export Approval</h2>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Report ID"
                  value={exportReportId}
                  onChange={(e) => setExportReportId(e.target.value)}
                  className="flex-1 border rounded px-3 py-2"
                />
                <button
                  onClick={requestExport}
                  disabled={loading}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  Request Export
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Pending Export Requests</h2>
              <p className="text-gray-500 text-sm mb-4">
                Export requests require approval before data can be downloaded or shared externally.
              </p>

              {/* Demo pending exports */}
              <div className="space-y-3">
                <div className="border rounded p-4 flex justify-between items-center">
                  <div>
                    <div className="font-medium">Export Request #1</div>
                    <div className="text-sm text-gray-500">Report ID: 42 | Status: Pending</div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => processExport(1, true)}
                      className="bg-green-600 text-white px-4 py-1 rounded text-sm"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => processExport(1, false)}
                      className="bg-red-600 text-white px-4 py-1 rounded text-sm"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Setup View */}
        {view === 'setup' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Database Setup</h2>
              <p className="text-gray-600 mb-4">
                Initialize compliance database tables. Run this once when setting up the system.
              </p>
              <button
                onClick={bootstrap}
                disabled={loading}
                className="bg-purple-600 text-white px-6 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? 'Bootstrapping...' : 'Bootstrap Compliance Tables'}
              </button>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Compliance Settings</h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b">
                  <div>
                    <div className="font-medium">Require Export Approval</div>
                    <div className="text-sm text-gray-500">All exports require manager approval</div>
                  </div>
                  <div className="bg-green-100 text-green-700 px-3 py-1 rounded text-sm">Enabled</div>
                </div>
                <div className="flex justify-between items-center py-2 border-b">
                  <div>
                    <div className="font-medium">Audit Logging</div>
                    <div className="text-sm text-gray-500">Log all data access and modifications</div>
                  </div>
                  <div className="bg-green-100 text-green-700 px-3 py-1 rounded text-sm">Enabled</div>
                </div>
                <div className="flex justify-between items-center py-2 border-b">
                  <div>
                    <div className="font-medium">Data Retention</div>
                    <div className="text-sm text-gray-500">Automatic data cleanup after retention period</div>
                  </div>
                  <div className="bg-yellow-100 text-yellow-700 px-3 py-1 rounded text-sm">7 Years</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
