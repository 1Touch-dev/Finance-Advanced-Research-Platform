/**
 * Docket-to-Disclosure Reconciliation Page (Band B #31)
 *
 * Features:
 * - Reconcile court dockets against SEC disclosures
 * - Identify undisclosed or misrepresented litigation
 * - View findings by divergence type and materiality
 * - Browse court cases and disclosure history
 */

import React, { useState, useEffect } from 'react';
import Head from 'next/head';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Risk Score Badge ─────────────────────────────────────────────────────────

function RiskBadge({ score }) {
  let color = 'bg-gray-400';
  let label = 'Unknown';

  if (score >= 80) {
    color = 'bg-red-500';
    label = 'Critical';
  } else if (score >= 60) {
    color = 'bg-orange-500';
    label = 'High';
  } else if (score >= 40) {
    color = 'bg-yellow-500';
    label = 'Medium';
  } else if (score >= 0) {
    color = 'bg-green-500';
    label = 'Low';
  }

  return (
    <span className={`px-2 py-1 rounded text-xs font-bold text-white ${color}`}>
      {label} ({score})
    </span>
  );
}

// ── Materiality Badge ────────────────────────────────────────────────────────

function MaterialityBadge({ level }) {
  const colors = {
    critical: 'bg-red-500 text-white',
    high: 'bg-orange-500 text-white',
    medium: 'bg-yellow-500 text-yellow-900',
    low: 'bg-green-500 text-white',
    unknown: 'bg-gray-400 text-white',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-bold ${colors[level] || 'bg-gray-300'}`}>
      {level?.toUpperCase()}
    </span>
  );
}

// ── Divergence Type Badge ────────────────────────────────────────────────────

function DivergenceBadge({ type }) {
  const colors = {
    missing_disclosure: 'bg-red-100 text-red-700',
    amount_mismatch: 'bg-orange-100 text-orange-700',
    timing_gap: 'bg-yellow-100 text-yellow-700',
    status_mismatch: 'bg-blue-100 text-blue-700',
    party_mismatch: 'bg-purple-100 text-purple-700',
    minimization: 'bg-pink-100 text-pink-700',
    outcome_not_updated: 'bg-gray-100 text-gray-700',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[type] || 'bg-gray-100'}`}>
      {type?.replace(/_/g, ' ')}
    </span>
  );
}

// ── Summary Card ─────────────────────────────────────────────────────────────

function SummaryCard({ data }) {
  if (!data) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">{data.ticker}</h3>
          <p className="text-sm text-gray-500">{data.company_name}</p>
        </div>
        <RiskBadge score={data.risk_score} />
      </div>

      <div className="p-4 bg-gray-50 rounded mb-4">
        <div className="text-sm text-gray-700">{data.summary}</div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="p-3 bg-blue-50 rounded">
          <span className="text-gray-500">CIK:</span>
          <span className="ml-2 font-medium">{data.cik}</span>
        </div>
        <div className="p-3 bg-blue-50 rounded">
          <span className="text-gray-500">Analysis Date:</span>
          <span className="ml-2 font-medium">{data.analysis_date}</span>
        </div>
      </div>
    </div>
  );
}

// ── Findings List ────────────────────────────────────────────────────────────

function FindingsList({ data, onSelectFinding }) {
  if (!data?.findings?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No findings match your criteria
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="p-4 border-b bg-gray-50">
        <span className="text-sm text-gray-500">
          Showing {data.filtered_count} of {data.total_findings} findings
        </span>
      </div>
      <div className="divide-y divide-gray-100">
        {data.findings.map((f, i) => (
          <div
            key={i}
            className="p-4 hover:bg-gray-50 cursor-pointer"
            onClick={() => onSelectFinding(f.id)}
          >
            <div className="flex justify-between items-start mb-2">
              <h4 className="font-medium text-gray-900">{f.title}</h4>
              <RiskBadge score={f.risk_score} />
            </div>
            <p className="text-sm text-gray-600 mb-3">{f.description?.slice(0, 200)}...</p>
            <div className="flex gap-2 flex-wrap">
              <DivergenceBadge type={f.divergence_type} />
              <MaterialityBadge level={f.materiality} />
              <span className="px-2 py-1 rounded text-xs bg-gray-100 text-gray-600">
                {f.disclosure_status?.replace(/_/g, ' ')}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Cases List ───────────────────────────────────────────────────────────────

function CasesList({ data }) {
  if (!data?.cases?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No cases found
      </div>
    );
  }

  const formatAmount = (amount) => {
    if (!amount) return 'N/A';
    if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="p-4 border-b bg-gray-50">
        <span className="text-sm text-gray-500">
          Showing {data.filtered_count} of {data.total_cases} cases
        </span>
      </div>
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left">Case</th>
            <th className="px-4 py-3 text-left">Court</th>
            <th className="px-4 py-3 text-left">Filed</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-right">Amount</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.cases.map((c, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <div className="font-medium text-blue-600">{c.case_name?.slice(0, 50)}</div>
                <div className="text-xs text-gray-500">{c.docket_number}</div>
              </td>
              <td className="px-4 py-3 text-gray-600">{c.court}</td>
              <td className="px-4 py-3 text-gray-600">{c.filed_date}</td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs ${
                  c.status === 'open' ? 'bg-yellow-100 text-yellow-700' :
                  c.status === 'closed' ? 'bg-green-100 text-green-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  {c.status}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-medium">{formatAmount(c.amount_claimed)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Disclosures List ─────────────────────────────────────────────────────────

function DisclosuresList({ data }) {
  if (!data?.disclosures?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No disclosures found
      </div>
    );
  }

  const formatAmount = (amount) => {
    if (!amount) return 'N/A';
    if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="p-4 border-b bg-gray-50">
        <span className="text-sm text-gray-500">
          Showing {data.filtered_count} of {data.total_disclosures} disclosures
        </span>
      </div>
      <div className="divide-y divide-gray-100">
        {data.disclosures.map((d, i) => (
          <div key={i} className="p-4 hover:bg-gray-50">
            <div className="flex justify-between items-start mb-2">
              <div className="flex gap-2">
                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                  {d.filing_type}
                </span>
                <span className="text-sm text-gray-500">{d.filing_date}</span>
              </div>
              <span className="font-medium">{formatAmount(d.amount_disclosed)}</span>
            </div>
            <p className="text-sm text-gray-600 mb-2">{d.description}</p>
            <div className="text-xs text-gray-500">
              Section: {d.section} | Assessment: {d.management_assessment}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Finding Detail Modal ─────────────────────────────────────────────────────

function FindingDetail({ findingId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (findingId) {
      setLoading(true);
      fetch(`${API_BASE}/docket/finding/${findingId}`)
        .then(res => res.json())
        .then(setData)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [findingId]);

  if (!findingId) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div className="p-4 border-b flex justify-between items-center sticky top-0 bg-white">
          <h3 className="font-semibold">Finding Details</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">&times;</button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : data?.finding ? (
          <div className="p-4 space-y-4">
            <h4 className="font-medium text-lg">{data.finding.title}</h4>

            <div className="flex gap-2 flex-wrap">
              <DivergenceBadge type={data.finding.divergence_type} />
              <MaterialityBadge level={data.finding.materiality} />
              <RiskBadge score={data.finding.risk_score} />
            </div>

            <div className="p-4 bg-gray-50 rounded">
              <div className="text-sm text-gray-700">{data.finding.description}</div>
            </div>

            {data.finding.evidence && (
              <div>
                <h5 className="font-medium text-sm text-gray-500 mb-2">Evidence</h5>
                <div className="p-3 bg-yellow-50 rounded text-sm">{data.finding.evidence}</div>
              </div>
            )}

            {data.finding.recommendations?.length > 0 && (
              <div>
                <h5 className="font-medium text-sm text-gray-500 mb-2">Recommendations</h5>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {data.finding.recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {data.finding.docket_case && (
              <div className="p-4 bg-blue-50 rounded">
                <h5 className="font-medium text-sm text-blue-700 mb-2">Related Court Case</h5>
                <div className="text-sm">
                  <div><strong>Case:</strong> {data.finding.docket_case.case_name}</div>
                  <div><strong>Court:</strong> {data.finding.docket_case.court}</div>
                  <div><strong>Filed:</strong> {data.finding.docket_case.filed_date}</div>
                  <div><strong>Status:</strong> {data.finding.docket_case.status}</div>
                </div>
              </div>
            )}

            {data.finding.disclosed_litigation && (
              <div className="p-4 bg-green-50 rounded">
                <h5 className="font-medium text-sm text-green-700 mb-2">SEC Disclosure</h5>
                <div className="text-sm">
                  <div><strong>Filing:</strong> {data.finding.disclosed_litigation.filing_type}</div>
                  <div><strong>Date:</strong> {data.finding.disclosed_litigation.filing_date}</div>
                  <div className="mt-2">{data.finding.disclosed_litigation.description}</div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-gray-500">Finding not found</div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function DocketPage() {
  const [activeTab, setActiveTab] = useState('summary');
  const [ticker, setTicker] = useState('NVDA');
  const [summary, setSummary] = useState(null);
  const [findings, setFindings] = useState(null);
  const [cases, setCases] = useState(null);
  const [disclosures, setDisclosures] = useState(null);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Run reconciliation first
      await fetch(`${API_BASE}/docket/${ticker}/reconcile`);

      // Then fetch all data
      const [sumRes, findRes, caseRes, discRes] = await Promise.all([
        fetch(`${API_BASE}/docket/${ticker}/summary`),
        fetch(`${API_BASE}/docket/${ticker}/findings`),
        fetch(`${API_BASE}/docket/${ticker}/cases`),
        fetch(`${API_BASE}/docket/${ticker}/disclosures`),
      ]);

      setSummary(await sumRes.json());
      setFindings(await findRes.json());
      setCases(await caseRes.json());
      setDisclosures(await discRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [ticker]);

  return (
    <>
      <Head>
        <title>Docket Reconciliation | Finance Intelligence</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Docket-to-Disclosure Reconciliation</h1>
            <p className="text-sm text-gray-500">Compare court dockets against SEC disclosure filings</p>
          </div>
        </header>

        {/* Tabs */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <nav className="flex space-x-8">
              {[
                { id: 'summary', label: 'Summary' },
                { id: 'findings', label: 'Findings' },
                { id: 'cases', label: 'Court Cases' },
                { id: 'disclosures', label: 'SEC Disclosures' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.label}
                  {tab.id === 'findings' && findings?.total_findings > 0 && (
                    <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">
                      {findings.total_findings}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Ticker Selector */}
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex gap-4 items-center">
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="px-4 py-2 border rounded-lg w-32"
                placeholder="Ticker"
              />
              <button
                onClick={fetchData}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Reconcile
              </button>
              <div className="flex gap-2 ml-4">
                {['NVDA', 'AAPL', 'MSFT', 'META', 'GOOGL', 'TSLA'].map(t => (
                  <button
                    key={t}
                    onClick={() => setTicker(t)}
                    className={`px-3 py-1 text-sm rounded-full border ${
                      ticker === t ? 'bg-blue-100 border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <main className="max-w-7xl mx-auto px-4 py-6">
          {loading && <div className="text-center py-8 text-gray-500">Running reconciliation...</div>}

          {!loading && activeTab === 'summary' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SummaryCard data={summary} />
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="font-semibold mb-4">Quick Stats</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-red-50 rounded text-center">
                    <div className="text-3xl font-bold text-red-600">{findings?.total_findings || 0}</div>
                    <div className="text-sm text-gray-500">Findings</div>
                  </div>
                  <div className="p-4 bg-blue-50 rounded text-center">
                    <div className="text-3xl font-bold text-blue-600">{cases?.total_cases || 0}</div>
                    <div className="text-sm text-gray-500">Court Cases</div>
                  </div>
                  <div className="p-4 bg-green-50 rounded text-center">
                    <div className="text-3xl font-bold text-green-600">{disclosures?.total_disclosures || 0}</div>
                    <div className="text-sm text-gray-500">Disclosures</div>
                  </div>
                  <div className="p-4 bg-orange-50 rounded text-center">
                    <div className="text-3xl font-bold text-orange-600">{summary?.risk_score || 0}</div>
                    <div className="text-sm text-gray-500">Risk Score</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!loading && activeTab === 'findings' && (
            <FindingsList data={findings} onSelectFinding={setSelectedFinding} />
          )}

          {!loading && activeTab === 'cases' && (
            <CasesList data={cases} />
          )}

          {!loading && activeTab === 'disclosures' && (
            <DisclosuresList data={disclosures} />
          )}
        </main>

        {/* Finding Detail Modal */}
        <FindingDetail
          findingId={selectedFinding}
          onClose={() => setSelectedFinding(null)}
        />
      </div>
    </>
  );
}
