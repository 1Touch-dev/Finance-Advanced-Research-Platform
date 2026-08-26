/**
 * Review & Export Page
 * Wired to /review/* API endpoints
 */

import React, { useState } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function Review() {
  const [view, setView] = useState('comments');
  const [reportId, setReportId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [result, setResult] = useState(null);

  // Comment form
  const [commentText, setCommentText] = useState('');
  const [sectionId, setSectionId] = useState('');

  // Suggestion form
  const [suggestionSectionId, setSuggestionSectionId] = useState('');
  const [proposedText, setProposedText] = useState('');

  // Diff view
  const [diffSectionId, setDiffSectionId] = useState('');
  const [v1, setV1] = useState('');
  const [v2, setV2] = useState('');
  const [diffResult, setDiffResult] = useState(null);

  const bootstrap = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/review/bootstrap', { method: 'POST' });
      if (!res.ok) throw new Error('Bootstrap failed');
      setSuccess('Review tables bootstrapped');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addComment = async () => {
    if (!reportId || !commentText.trim()) {
      setError('Report ID and comment text required');
      return;
    }
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      report_id: reportId,
      text: commentText,
    });
    if (sectionId) params.append('section_id', sectionId);

    try {
      const res = await apiFetch(`/review/comments?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to add comment');
      const data = await res.json();
      setSuccess(`Comment added with ID: ${data.id}`);
      setCommentText('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addSuggestion = async () => {
    if (!reportId || !suggestionSectionId || !proposedText.trim()) {
      setError('Report ID, section ID, and proposed text required');
      return;
    }
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      report_id: reportId,
      section_id: suggestionSectionId,
      proposed: proposedText,
    });

    try {
      const res = await apiFetch(`/review/suggest?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to add suggestion');
      const data = await res.json();
      setSuccess(`Suggestion added with ID: ${data.id}`);
      setProposedText('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const processSuggestion = async (suggestionId, accept) => {
    setLoading(true);
    setError(null);
    const endpoint = accept ? 'accept' : 'reject';

    try {
      const res = await apiFetch(`/review/suggestions/${suggestionId}/${endpoint}`, { method: 'POST' });
      if (!res.ok) throw new Error(`Failed to ${endpoint} suggestion`);
      setSuccess(`Suggestion ${suggestionId} ${accept ? 'accepted' : 'rejected'}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const reverify = async () => {
    if (!reportId) {
      setError('Report ID required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ report_id: reportId });
      const res = await apiFetch(`/review/reverify?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Reverify failed');
      const data = await res.json();
      setResult(data);
      setSuccess(`Reverified ${data.results?.length || 0} claims`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSectionVersions = async () => {
    if (!diffSectionId) {
      setError('Section ID required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/review/sections/${diffSectionId}/versions`);
      if (!res.ok) throw new Error('Failed to get versions');
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getDiff = async () => {
    if (!diffSectionId || !v1 || !v2) {
      setError('Section ID and both version IDs required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ v1, v2 });
      const res = await apiFetch(`/review/sections/${diffSectionId}/diff?${params}`);
      if (!res.ok) throw new Error('Failed to get diff');
      const data = await res.json();
      setDiffResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (format) => {
    if (!reportId) {
      setError('Report ID required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/review/export/${reportId}/${format}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Export failed`);
      }
      const data = await res.json();
      setSuccess(`Exported to: ${data.path}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Review & Export</h1>
        <p className="text-gray-600 mb-6">
          Comments, suggestions, version diffs, claim verification, and report exports.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {[
            { key: 'comments', label: 'Comments' },
            { key: 'suggestions', label: 'Suggestions' },
            { key: 'versions', label: 'Versions & Diff' },
            { key: 'verify', label: 'Verify Claims' },
            { key: 'export', label: 'Export' },
            { key: 'setup', label: 'Setup' },
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

        {/* Report ID Input */}
        {view !== 'setup' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">Report ID</label>
            <input
              type="text"
              placeholder="Enter report ID"
              value={reportId}
              onChange={(e) => setReportId(e.target.value)}
              className="w-full border rounded px-3 py-2"
            />
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

        {/* Comments View */}
        {view === 'comments' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Add Comment</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Section ID (optional)</label>
                <input
                  type="text"
                  value={sectionId}
                  onChange={(e) => setSectionId(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Comment</label>
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  rows={3}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <button onClick={addComment} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                {loading ? 'Adding...' : 'Add Comment'}
              </button>
            </div>
          </div>
        )}

        {/* Suggestions View */}
        {view === 'suggestions' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Add Suggestion</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Section ID</label>
                <input
                  type="text"
                  value={suggestionSectionId}
                  onChange={(e) => setSuggestionSectionId(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Proposed Text</label>
                <textarea
                  value={proposedText}
                  onChange={(e) => setProposedText(e.target.value)}
                  rows={4}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <button onClick={addSuggestion} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                {loading ? 'Adding...' : 'Add Suggestion'}
              </button>
            </div>

            <div className="mt-6 pt-6 border-t">
              <h3 className="font-bold mb-4">Process Suggestion</h3>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Suggestion ID"
                  className="flex-1 border rounded px-3 py-2"
                  id="suggestion-id"
                />
                <button
                  onClick={() => {
                    const sid = (document.getElementById('suggestion-id')).value;
                    processSuggestion(sid, true);
                  }}
                  className="bg-green-600 text-white px-4 py-2 rounded"
                >
                  Accept
                </button>
                <button
                  onClick={() => {
                    const sid = (document.getElementById('suggestion-id')).value;
                    processSuggestion(sid, false);
                  }}
                  className="bg-red-600 text-white px-4 py-2 rounded"
                >
                  Reject
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Versions View */}
        {view === 'versions' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Get Section Versions</h3>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Section ID"
                  value={diffSectionId}
                  onChange={(e) => setDiffSectionId(e.target.value)}
                  className="flex-1 border rounded px-3 py-2"
                />
                <button onClick={getSectionVersions} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                  Get Versions
                </button>
              </div>
              {result && Array.isArray(result) && (
                <div className="mt-4">
                  <h4 className="font-medium mb-2">Versions</h4>
                  <div className="space-y-1">
                    {result.map((v) => (
                      <div key={v.id} className="text-sm bg-gray-50 p-2 rounded">
                        ID: {v.id} — {v.created_at}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-4">Compare Versions (Diff)</h3>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <input
                  type="text"
                  placeholder="Section ID"
                  value={diffSectionId}
                  onChange={(e) => setDiffSectionId(e.target.value)}
                  className="border rounded px-3 py-2"
                />
                <input
                  type="text"
                  placeholder="Version 1 ID"
                  value={v1}
                  onChange={(e) => setV1(e.target.value)}
                  className="border rounded px-3 py-2"
                />
                <input
                  type="text"
                  placeholder="Version 2 ID"
                  value={v2}
                  onChange={(e) => setV2(e.target.value)}
                  className="border rounded px-3 py-2"
                />
              </div>
              <button onClick={getDiff} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
                Get Diff
              </button>
              {diffResult && (
                <pre className="mt-4 bg-gray-900 text-green-400 p-4 rounded text-sm overflow-x-auto">
                  {diffResult.diff?.join('\n') || 'No diff'}
                </pre>
              )}
            </div>
          </div>
        )}

        {/* Verify View */}
        {view === 'verify' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Reverify All Claims</h3>
            <p className="text-gray-600 mb-4">Re-run verification on all claims in the report.</p>
            <button onClick={reverify} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">
              {loading ? 'Verifying...' : 'Reverify Claims'}
            </button>
            {result?.results && (
              <div className="mt-4">
                <h4 className="font-medium mb-2">Results</h4>
                <div className="space-y-1">
                  {result.results.map((r) => (
                    <div key={r.claim_id} className="flex justify-between bg-gray-50 p-2 rounded text-sm">
                      <span>Claim {r.claim_id}</span>
                      <span className={r.status === 'verified' ? 'text-green-600' : 'text-yellow-600'}>
                        {r.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Export View */}
        {view === 'export' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Export Report</h3>
            <p className="text-gray-600 mb-4">Export the report in various formats.</p>
            <div className="flex gap-4 flex-wrap">
              {['markdown', 'html', 'json', 'pdf', 'docx', 'evidence_csv'].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => exportReport(fmt)}
                  disabled={loading}
                  className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded disabled:opacity-50"
                >
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Setup View */}
        {view === 'setup' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold mb-4">Bootstrap Review Tables</h3>
            <p className="text-gray-600 mb-4">Initialize database tables for review functionality.</p>
            <button onClick={bootstrap} disabled={loading} className="bg-purple-600 text-white px-6 py-2 rounded disabled:opacity-50">
              {loading ? 'Bootstrapping...' : 'Bootstrap'}
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
