/**
 * Evidence Viewer Page
 * Wired to /evidence/* API endpoints
 */

import React, { useState, useRef } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function Evidence() {
  const [view, setView] = useState('upload');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Upload state
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);

  // View document state
  const [docId, setDocId] = useState('');
  const [document, setDocument] = useState(null);

  // Reference state
  const [refId, setRefId] = useState('');
  const [reference, setReference] = useState(null);

  // Create reference form
  const [refForm, setRefForm] = useState({
    raw_document_id: '',
    field_path: '',
    page_start: '',
    page_end: '',
    char_start: '',
    char_end: '',
    excerpt: '',
  });

  // Bootstrap tables
  const bootstrap = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/evidence/bootstrap', { method: 'POST' });
      if (!res.ok) throw new Error('Bootstrap failed');
      setSuccess('Evidence vault and tables initialized');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Upload file
  const uploadFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await apiFetch('/evidence/raw', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await res.json();
      setUploadResult(data);
      setSuccess(`File uploaded: ${file.name}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Get document
  const getDocument = async () => {
    if (!docId.trim()) {
      setError('Document ID is required');
      return;
    }
    setLoading(true);
    setError(null);
    setDocument(null);

    try {
      const res = await apiFetch(`/evidence/raw/${docId}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Document not found');
      }
      const data = await res.json();
      setDocument(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Download document
  const downloadDocument = () => {
    if (!docId) return;
    window.open(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/evidence/raw/${docId}?download=true`, '_blank');
  };

  // Set legal hold
  const setLegalHold = async (hold) => {
    if (!docId.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ hold: hold.toString() });
      const res = await apiFetch(`/evidence/raw/${docId}/legal_hold?${params}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to set legal hold');
      const data = await res.json();
      setSuccess(`Legal hold ${data.legal_hold ? 'enabled' : 'disabled'} for document ${data.id}`);
      getDocument(); // Refresh
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Get reference
  const getReference = async () => {
    if (!refId.trim()) {
      setError('Reference ID is required');
      return;
    }
    setLoading(true);
    setError(null);
    setReference(null);

    try {
      const res = await apiFetch(`/evidence/refs/${refId}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Reference not found');
      }
      const data = await res.json();
      setReference(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Create reference
  const createReference = async () => {
    if (!refForm.raw_document_id.trim()) {
      setError('Raw document ID is required');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('raw_document_id', refForm.raw_document_id);
      if (refForm.field_path) formData.append('field_path', refForm.field_path);
      if (refForm.page_start) formData.append('page_start', refForm.page_start);
      if (refForm.page_end) formData.append('page_end', refForm.page_end);
      if (refForm.char_start) formData.append('char_start', refForm.char_start);
      if (refForm.char_end) formData.append('char_end', refForm.char_end);
      if (refForm.excerpt) formData.append('excerpt', refForm.excerpt);

      const res = await apiFetch('/evidence/refs', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Failed to create reference');
      const data = await res.json();
      setSuccess(`Reference created with ID: ${data.id}`);
      setRefForm({
        raw_document_id: '',
        field_path: '',
        page_start: '',
        page_end: '',
        char_start: '',
        char_end: '',
        excerpt: '',
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '-';
    if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`;
    if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Evidence Vault</h1>
        <p className="text-gray-600 mb-6">
          Upload, manage, and reference raw evidence documents with legal hold and retention controls.
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'upload', label: 'Upload' },
            { key: 'view', label: 'View Document' },
            { key: 'refs', label: 'References' },
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

        {/* Upload View */}
        {view === 'upload' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Upload Evidence Document</h2>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={uploadFile}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer text-blue-600 hover:text-blue-800"
                >
                  <div className="text-4xl mb-2">📄</div>
                  <div className="font-medium">Click to upload a file</div>
                  <div className="text-sm text-gray-500">PDF, DOCX, XLSX, or any document</div>
                </label>
              </div>
              {loading && <div className="mt-4 text-center text-gray-600">Uploading...</div>}
            </div>

            {uploadResult && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4">Upload Result</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">Document ID</div>
                    <div className="font-bold text-xl">{uploadResult.id}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Size</div>
                    <div className="font-bold">{formatBytes(uploadResult.size)}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-sm text-gray-500">SHA256</div>
                    <div className="font-mono text-xs break-all">{uploadResult.sha256}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-sm text-gray-500">Storage Path</div>
                    <div className="font-mono text-sm">{uploadResult.path}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* View Document */}
        {view === 'view' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Retrieve Document</h2>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Document ID"
                  value={docId}
                  onChange={(e) => setDocId(e.target.value)}
                  className="flex-1 border rounded px-3 py-2"
                />
                <button
                  onClick={getDocument}
                  disabled={loading}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Loading...' : 'Fetch'}
                </button>
              </div>
            </div>

            {document && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-4">
                  <h2 className="text-lg font-bold">Document Details</h2>
                  <div className="flex gap-2">
                    <button
                      onClick={downloadDocument}
                      className="bg-green-600 text-white px-4 py-1 rounded text-sm"
                    >
                      Download
                    </button>
                    <button
                      onClick={() => setLegalHold(true)}
                      className="bg-red-600 text-white px-4 py-1 rounded text-sm"
                    >
                      Set Legal Hold
                    </button>
                    <button
                      onClick={() => setLegalHold(false)}
                      className="bg-gray-600 text-white px-4 py-1 rounded text-sm"
                    >
                      Release Hold
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">Document ID</div>
                    <div className="font-bold">{document.id}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Content Type</div>
                    <div className="font-medium">{document.content_type}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Size</div>
                    <div className="font-medium">{formatBytes(document.size)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Source URL</div>
                    <div className="font-medium truncate">{document.source_url || '-'}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-sm text-gray-500">SHA256</div>
                    <div className="font-mono text-xs break-all">{document.sha256}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-sm text-gray-500">Storage Path</div>
                    <div className="font-mono text-sm">{document.storage_path}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* References View */}
        {view === 'refs' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Create Evidence Reference</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Raw Document ID *</label>
                  <input
                    type="text"
                    value={refForm.raw_document_id}
                    onChange={(e) => setRefForm({ ...refForm, raw_document_id: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Field Path</label>
                  <input
                    type="text"
                    placeholder="e.g., section.2.paragraph.3"
                    value={refForm.field_path}
                    onChange={(e) => setRefForm({ ...refForm, field_path: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Page Start</label>
                  <input
                    type="number"
                    value={refForm.page_start}
                    onChange={(e) => setRefForm({ ...refForm, page_start: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Page End</label>
                  <input
                    type="number"
                    value={refForm.page_end}
                    onChange={(e) => setRefForm({ ...refForm, page_end: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Char Start</label>
                  <input
                    type="number"
                    value={refForm.char_start}
                    onChange={(e) => setRefForm({ ...refForm, char_start: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Char End</label>
                  <input
                    type="number"
                    value={refForm.char_end}
                    onChange={(e) => setRefForm({ ...refForm, char_end: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Excerpt</label>
                  <textarea
                    value={refForm.excerpt}
                    onChange={(e) => setRefForm({ ...refForm, excerpt: e.target.value })}
                    rows={3}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
              </div>
              <button
                onClick={createReference}
                disabled={loading}
                className="mt-4 bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Reference'}
              </button>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Lookup Reference</h2>
              <div className="flex gap-4">
                <input
                  type="text"
                  placeholder="Reference ID"
                  value={refId}
                  onChange={(e) => setRefId(e.target.value)}
                  className="flex-1 border rounded px-3 py-2"
                />
                <button
                  onClick={getReference}
                  disabled={loading}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  Lookup
                </button>
              </div>

              {reference && (
                <div className="mt-4 bg-gray-50 rounded p-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div><span className="text-gray-500">ID:</span> {reference.id}</div>
                    <div><span className="text-gray-500">Document ID:</span> {reference.raw_document_id}</div>
                    <div><span className="text-gray-500">Field Path:</span> {reference.field_path || '-'}</div>
                    <div><span className="text-gray-500">Pages:</span> {reference.page_start || '-'} - {reference.page_end || '-'}</div>
                    <div className="col-span-2">
                      <span className="text-gray-500">Excerpt:</span>
                      <div className="mt-1 p-2 bg-white border rounded">{reference.excerpt || 'No excerpt'}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Setup View */}
        {view === 'setup' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">Evidence Vault Setup</h2>
            <p className="text-gray-600 mb-4">
              Initialize the evidence vault storage directory and database tables. Run this once when setting up the system.
            </p>
            <button
              onClick={bootstrap}
              disabled={loading}
              className="bg-purple-600 text-white px-6 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
            >
              {loading ? 'Initializing...' : 'Bootstrap Evidence Vault'}
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
