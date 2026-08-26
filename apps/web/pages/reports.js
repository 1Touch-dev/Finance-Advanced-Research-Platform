/**
 * Reports Management Page
 * Wired to /reports/* API endpoints
 */

import React, { useState } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

const REPORT_KINDS = ['due_diligence', 'ic_memo', 'one_pager', 'earnings', 'research', 'custom'];

export default function Reports() {
  const [view, setView] = useState('create');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [report, setReport] = useState(null);

  // Create report form
  const [reportTitle, setReportTitle] = useState('');
  const [reportKind, setReportKind] = useState('research');

  // Report ID for operations
  const [reportId, setReportId] = useState('');

  // Section form
  const [sectionName, setSectionName] = useState('');
  const [sectionContent, setSectionContent] = useState('');
  const [sectionOrder, setSectionOrder] = useState('0');

  // Claim form
  const [claimText, setClaimText] = useState('');
  const [claimId, setClaimId] = useState('');
  const [evidenceRefId, setEvidenceRefId] = useState('');

  const bootstrap = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/reports/bootstrap', { method: 'POST' });
      if (!res.ok) throw new Error('Bootstrap failed');
      setSuccess('Reports tables bootstrapped');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createReport = async () => {
    if (!reportTitle.trim()) {
      setError('Title is required');
      return;
    }
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      title: reportTitle,
      kind: reportKind,
    });

    try {
      const res = await apiFetch(`/reports?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to create report');
      const data = await res.json();
      setSuccess(`Report created: ID ${data.id}`);
      setReportId(data.id.toString());
      setReportTitle('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getReport = async () => {
    if (!reportId) {
      setError('Report ID required');
      return;
    }
    setLoading(true);
    setError(null);
    setReport(null);

    try {
      const res = await apiFetch(`/reports/${reportId}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Report not found');
      }
      setReport(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addSection = async () => {
    if (!reportId || !sectionName.trim()) {
      setError('Report ID and section name required');
      return;
    }
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      name: sectionName,
      content: sectionContent,
      order: sectionOrder,
    });

    try {
      const res = await apiFetch(`/reports/${reportId}/sections?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to add section');
      const data = await res.json();
      setSuccess(`Section added: ID ${data.id}`);
      setSectionName('');
      setSectionContent('');
      getReport(); // Refresh
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addClaim = async () => {
    if (!reportId || !claimText.trim()) {
      setError('Report ID and claim text required');
      return;
    }
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      text: claimText,
    });

    try {
      const res = await apiFetch(`/reports/${reportId}/claims?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to add claim');
      const data = await res.json();
      setSuccess(`Claim added: ID ${data.id}`);
      setClaimText('');
      getReport(); // Refresh
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const verifyClaim = async () => {
    if (!claimId) {
      setError('Claim ID required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/reports/claims/${claimId}/verify`, { method: 'POST' });
      if (!res.ok) throw new Error('Verification failed');
      const data = await res.json();
      setSuccess(`Claim ${claimId}: ${data.status} (${data.flags?.join(', ') || 'no flags'})`);
      getReport(); // Refresh
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const attachEvidence = async () => {
    if (!claimId || !evidenceRefId) {
      setError('Claim ID and evidence ref ID required');
      return;
    }
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      evidence_ref_id: evidenceRefId,
    });

    try {
      const res = await apiFetch(`/reports/claims/${claimId}/evidence?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to attach evidence');
      const data = await res.json();
      setSuccess(`Evidence attached: ID ${data.id}`);
      setEvidenceRefId('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const checkExportReady = async () => {
    if (!reportId) {
      setError('Report ID required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/reports/${reportId}/export_ready`);
      if (!res.ok) throw new Error('Check failed');
      const data = await res.json();
      if (data.ready) {
        setSuccess('Report is ready for export!');
      } else {
        setError(`Export blocked: ${data.blocked?.length || 0} claims need attention`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      verified: 'bg-green-100 text-green-700',
      needs_review: 'bg-yellow-100 text-yellow-700',
      contradicted: 'bg-red-100 text-red-700',
      draft: 'bg-gray-100 text-gray-600',
    };
    return colors[status] || 'bg-gray-100 text-gray-600';
  };

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Reports</h1>
        <p className="text-gray-600 mb-6">
          Create reports, add sections and claims, verify evidence, and export.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {[
            { key: 'create', label: 'Create' },
            { key: 'view', label: 'View Report' },
            { key: 'sections', label: 'Sections' },
            { key: 'claims', label: 'Claims' },
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

        {/* Report ID (for most views) */}
        {view !== 'create' && view !== 'setup' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Report ID"
                value={reportId}
                onChange={(e) => setReportId(e.target.value)}
                className="flex-1 border rounded px-3 py-2"
              />
              <button onClick={getReport} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                Load Report
              </button>
            </div>
          </div>
        )}

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

        {/* Create View */}
        {view === 'create' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Create New Report</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Title</label>
                <input
                  type="text"
                  placeholder="e.g., Apple Inc. Due Diligence Report"
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Kind</label>
                <select
                  value={reportKind}
                  onChange={(e) => setReportKind(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                >
                  {REPORT_KINDS.map((k) => (
                    <option key={k} value={k}>{k.replace('_', ' ').toUpperCase()}</option>
                  ))}
                </select>
              </div>
              <button onClick={createReport} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                {loading ? 'Creating...' : 'Create Report'}
              </button>
            </div>
          </div>
        )}

        {/* View Report */}
        {view === 'view' && report && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-bold">{report.title}</h2>
                  <p className="text-gray-500">{report.kind} | Status: {report.status}</p>
                </div>
                <button onClick={checkExportReady} className="bg-green-600 text-white px-4 py-2 rounded text-sm">
                  Check Export Ready
                </button>
              </div>

              {/* Sections */}
              <div className="mb-6">
                <h3 className="font-bold mb-2">Sections ({report.sections?.length || 0})</h3>
                {report.sections?.map((s) => (
                  <div key={s.id} className="border rounded p-3 mb-2">
                    <div className="font-medium">{s.order}. {s.name}</div>
                    <div className="text-sm text-gray-600 mt-1">{s.content?.slice(0, 200) || 'No content'}</div>
                  </div>
                ))}
              </div>

              {/* Claims */}
              <div className="mb-6">
                <h3 className="font-bold mb-2">Claims ({report.claims?.length || 0})</h3>
                {report.claims?.map((c) => (
                  <div key={c.id} className="border rounded p-3 mb-2 flex justify-between items-center">
                    <div>
                      <div className="text-sm">{c.text}</div>
                      {c.note && <div className="text-xs text-red-600 mt-1">Note: {c.note}</div>}
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${getStatusColor(c.status)}`}>
                      {c.status || 'pending'}
                    </span>
                  </div>
                ))}
              </div>

              {/* Evidence Bundles */}
              {report.bundles?.length > 0 && (
                <div>
                  <h3 className="font-bold mb-2">Evidence Bundles</h3>
                  {report.bundles.map((b) => (
                    <div key={b.id} className="text-sm bg-gray-50 p-2 rounded mb-1">
                      {b.name}: {b.items?.length || 0} items
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Sections View */}
        {view === 'sections' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Add Section</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Section Name</label>
                  <input
                    type="text"
                    placeholder="e.g., Executive Summary"
                    value={sectionName}
                    onChange={(e) => setSectionName(e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Order</label>
                  <input
                    type="number"
                    value={sectionOrder}
                    onChange={(e) => setSectionOrder(e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Content</label>
                <textarea
                  value={sectionContent}
                  onChange={(e) => setSectionContent(e.target.value)}
                  rows={4}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <button onClick={addSection} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                {loading ? 'Adding...' : 'Add Section'}
              </button>
            </div>
          </div>
        )}

        {/* Claims View */}
        {view === 'claims' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Add Claim</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Claim Text</label>
                  <textarea
                    placeholder="e.g., Revenue grew 15% YoY in Q3 2024"
                    value={claimText}
                    onChange={(e) => setClaimText(e.target.value)}
                    rows={2}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <button onClick={addClaim} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                  Add Claim
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Verify Claim</h3>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Claim ID"
                  value={claimId}
                  onChange={(e) => setClaimId(e.target.value)}
                  className="flex-1 border rounded px-3 py-2"
                />
                <button onClick={verifyClaim} disabled={loading} className="bg-green-600 text-white px-6 py-2 rounded disabled:opacity-50">
                  Verify
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Attach Evidence</h3>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <input
                  type="text"
                  placeholder="Claim ID"
                  value={claimId}
                  onChange={(e) => setClaimId(e.target.value)}
                  className="border rounded px-3 py-2"
                />
                <input
                  type="text"
                  placeholder="Evidence Ref ID"
                  value={evidenceRefId}
                  onChange={(e) => setEvidenceRefId(e.target.value)}
                  className="border rounded px-3 py-2"
                />
              </div>
              <button onClick={attachEvidence} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                Attach Evidence
              </button>
            </div>
          </div>
        )}

        {/* Setup View */}
        {view === 'setup' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Bootstrap Reports Tables</h3>
            <p className="text-gray-600 mb-4">Initialize database tables for reports, sections, claims, and evidence.</p>
            <button onClick={bootstrap} disabled={loading} className="bg-purple-600 text-white px-6 py-2 rounded disabled:opacity-50">
              {loading ? 'Bootstrapping...' : 'Bootstrap'}
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
