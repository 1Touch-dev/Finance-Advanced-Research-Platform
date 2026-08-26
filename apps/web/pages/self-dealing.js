/**
 * Self-Dealing Analysis Page
 * Wired to POST /intelligence/self-dealing
 */

import React, { useState } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function SelfDealing() {
  const [entityName, setEntityName] = useState('');
  const [ticker, setTicker] = useState('');
  const [relatedEntities, setRelatedEntities] = useState('');
  const [includeFamilyNetwork, setIncludeFamilyNetwork] = useState(true);
  const [includeInstitutional, setIncludeInstitutional] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runAnalysis = async () => {
    if (!entityName.trim()) {
      setError('Entity name is required');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    const payload = {
      entity_name: entityName.trim(),
      ticker: ticker.trim().toUpperCase(),
      related_entities: relatedEntities.split(',').map(e => e.trim()).filter(Boolean),
      include_family_network: includeFamilyNetwork,
      include_institutional_holders: includeInstitutional,
    };

    try {
      const res = await apiFetch('/intelligence/self-dealing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Analysis failed');
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score) => {
    if (score >= 80) return 'text-red-600 bg-red-100';
    if (score >= 60) return 'text-orange-600 bg-orange-100';
    if (score >= 40) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Self-Dealing Analysis</h1>
        <p className="text-gray-600 mb-6">
          Detect potential conflicts of interest, related-party transactions, and self-dealing patterns.
        </p>

        {/* Input Form */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Entity Name *</label>
              <input
                type="text"
                placeholder="e.g., Tesla, Inc."
                value={entityName}
                onChange={(e) => setEntityName(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ticker (optional)</label>
              <input
                type="text"
                placeholder="e.g., TSLA"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Related Entities (comma-separated)
            </label>
            <input
              type="text"
              placeholder="e.g., SolarCity, SpaceX, Boring Company"
              value={relatedEntities}
              onChange={(e) => setRelatedEntities(e.target.value)}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div className="flex gap-6 mb-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeFamilyNetwork}
                onChange={(e) => setIncludeFamilyNetwork(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Include family network analysis</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeInstitutional}
                onChange={(e) => setIncludeInstitutional(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Include institutional holders</span>
            </label>
          </div>

          <button
            onClick={runAnalysis}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Summary */}
            {result.summary && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4">Analysis Summary</h2>
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-sm text-gray-500">Risk Score</div>
                    <div className={`text-3xl font-bold px-4 py-2 rounded ${getRiskColor(result.summary.risk_score || 0)}`}>
                      {result.summary.risk_score || 0}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-500">Entities Analyzed</div>
                    <div className="text-3xl font-bold">{result.summary.entities_analyzed || 0}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-500">Red Flags</div>
                    <div className="text-3xl font-bold text-red-600">{result.summary.red_flags_count || 0}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-500">Related Transactions</div>
                    <div className="text-3xl font-bold">{result.summary.related_transactions || 0}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Red Flags */}
            {result.red_flags && result.red_flags.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4 text-red-600">Red Flags Detected</h2>
                <div className="space-y-3">
                  {result.red_flags.map((flag, idx) => (
                    <div key={idx} className="border-l-4 border-red-500 pl-4 py-2 bg-red-50 rounded-r">
                      <div className="font-medium">{flag.title || flag.type}</div>
                      <div className="text-sm text-gray-600">{flag.description}</div>
                      {flag.severity && (
                        <span className={`text-xs px-2 py-1 rounded mt-1 inline-block ${
                          flag.severity === 'high' ? 'bg-red-200 text-red-800' :
                          flag.severity === 'medium' ? 'bg-yellow-200 text-yellow-800' :
                          'bg-gray-200 text-gray-800'
                        }`}>
                          {flag.severity.toUpperCase()}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Related Party Transactions */}
            {result.transactions && result.transactions.length > 0 && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-bold">Related Party Transactions</h2>
                </div>
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3">Date</th>
                      <th className="text-left p-3">Parties</th>
                      <th className="text-left p-3">Description</th>
                      <th className="text-right p-3">Amount</th>
                      <th className="text-center p-3">Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.transactions.map((tx, idx) => (
                      <tr key={idx} className="border-t hover:bg-gray-50">
                        <td className="p-3 text-sm">{tx.date}</td>
                        <td className="p-3 text-sm">{tx.parties?.join(' → ') || tx.counterparty}</td>
                        <td className="p-3 text-sm">{tx.description}</td>
                        <td className="p-3 text-right font-medium">
                          {tx.amount ? `$${tx.amount.toLocaleString()}` : '-'}
                        </td>
                        <td className="p-3 text-center">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${getRiskColor(tx.risk_score || 0)}`}>
                            {tx.risk_score || 0}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Network Graph Data */}
            {result.network && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-4">Entity Network</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="font-medium mb-2">Nodes ({result.network.nodes?.length || 0})</h3>
                    <div className="max-h-64 overflow-y-auto space-y-1">
                      {result.network.nodes?.map((node, idx) => (
                        <div key={idx} className="text-sm bg-gray-50 px-2 py-1 rounded">
                          {node.name || node.id} <span className="text-gray-400">({node.type})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="font-medium mb-2">Connections ({result.network.edges?.length || 0})</h3>
                    <div className="max-h-64 overflow-y-auto space-y-1">
                      {result.network.edges?.map((edge, idx) => (
                        <div key={idx} className="text-sm bg-gray-50 px-2 py-1 rounded">
                          {edge.source} → {edge.target}
                          <span className="text-gray-400 ml-2">({edge.relationship})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* No Data Response */}
            {result.no_data && (
              <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded">
                <div className="font-medium">Limited Data Available</div>
                <div className="text-sm">{result.details || result.message}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
