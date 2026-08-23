import { useState } from 'react';
import Head from 'next/head';
import { getApiBaseUrl , apiFetch } from '../lib/api';

export default function PrivateCompanyPage() {
  const API = getApiBaseUrl();
  const [companyName, setCompanyName] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('full');
  const [results, setResults] = useState(null);
  const [err, setErr] = useState('');

  async function searchFull() {
    if (!companyName) return;
    setLoading(true);
    setErr('');
    try {
      const res = await apiFetch(`/intelligence/private-co/full?name=${encodeURIComponent(companyName)}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setResults(await res.json());
      setActiveTab('full');
    } catch (e) {
      setErr(e.message);
    }
    setLoading(false);
  }

  async function searchUK() {
    if (!companyName) return;
    setLoading(true);
    setErr('');
    try {
      const res = await apiFetch(`/intelligence/private-co/uk?name=${encodeURIComponent(companyName)}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setResults({ uk_results: await res.json() });
      setActiveTab('uk');
    } catch (e) {
      setErr(e.message);
    }
    setLoading(false);
  }

  async function searchFormD() {
    if (!companyName) return;
    setLoading(true);
    setErr('');
    try {
      const res = await apiFetch(`/intelligence/private-co/form-d?name=${encodeURIComponent(companyName)}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setResults({ form_d_results: await res.json() });
      setActiveTab('formd');
    } catch (e) {
      setErr(e.message);
    }
    setLoading(false);
  }

  async function searchFunding() {
    if (!companyName) return;
    setLoading(true);
    setErr('');
    try {
      const res = await apiFetch(`/intelligence/private-co/funding?name=${encodeURIComponent(companyName)}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setResults({ funding_results: await res.json() });
      setActiveTab('funding');
    } catch (e) {
      setErr(e.message);
    }
    setLoading(false);
  }

  const tabs = [
    { id: 'full', label: 'Full Search (All Sources)' },
    { id: 'uk', label: 'UK Companies House' },
    { id: 'formd', label: 'SEC Form D' },
    { id: 'funding', label: 'Funding History' },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Private Company Intelligence | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-2">Private Company Intelligence</h1>
      <p className="text-gray-400 mb-6">
        OpenCorporates + GLEIF + FinCEN + UK Companies House + SEC Form D
      </p>

      {/* Search */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex gap-4 mb-4">
          <input
            type="text"
            value={companyName}
            onChange={e => setCompanyName(e.target.value)}
            placeholder="Enter company name (e.g., Stripe, SpaceX)"
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
            onKeyPress={e => e.key === 'Enter' && searchFull()}
          />
          <button
            onClick={searchFull}
            disabled={loading || !companyName}
            className="bg-blue-600 hover:bg-blue-500 px-8 py-3 rounded-lg font-semibold disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Full Search'}
          </button>
        </div>

        <div className="flex gap-2 flex-wrap">
          <button onClick={searchUK} disabled={loading || !companyName}
            className="bg-purple-600 hover:bg-purple-500 px-4 py-2 rounded-lg text-sm disabled:opacity-50">
            UK Companies House
          </button>
          <button onClick={searchFormD} disabled={loading || !companyName}
            className="bg-green-600 hover:bg-green-500 px-4 py-2 rounded-lg text-sm disabled:opacity-50">
            SEC Form D
          </button>
          <button onClick={searchFunding} disabled={loading || !companyName}
            className="bg-yellow-600 hover:bg-yellow-500 px-4 py-2 rounded-lg text-sm disabled:opacity-50">
            Funding History
          </button>
        </div>
      </div>

      {err && <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-6 text-red-400">{err}</div>}

      {results && (
        <>
          {/* Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg whitespace-nowrap text-sm ${
                  activeTab === tab.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Results */}
          <div className="bg-gray-800 rounded-lg p-6">
            {/* Full Results */}
            {activeTab === 'full' && results.opencorporates_matches && (
              <div className="space-y-6">
                {/* OpenCorporates */}
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-blue-400">OpenCorporates Matches</h3>
                  {results.opencorporates_matches?.length > 0 ? (
                    <div className="grid gap-3">
                      {results.opencorporates_matches.map((m, i) => (
                        <div key={i} className="p-3 bg-gray-700 rounded-lg">
                          <div className="font-semibold">{m.name}</div>
                          <div className="text-sm text-gray-400">
                            {m.jurisdiction} | {m.company_type} | {m.status}
                          </div>
                          {m.registered_address && <div className="text-xs text-gray-500 mt-1">{m.registered_address}</div>}
                        </div>
                      ))}
                    </div>
                  ) : <p className="text-gray-400">No matches found</p>}
                </div>

                {/* GLEIF */}
                {results.gleif_matches?.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-3 text-green-400">GLEIF (LEI Records)</h3>
                    <div className="grid gap-3">
                      {results.gleif_matches.map((m, i) => (
                        <div key={i} className="p-3 bg-gray-700 rounded-lg">
                          <div className="font-semibold">{m.name}</div>
                          <div className="text-sm text-blue-400">LEI: {m.lei}</div>
                          <div className="text-xs text-gray-400">{m.jurisdiction} | {m.status}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* UK Companies House */}
                {results.uk_companies_house_matches?.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-3 text-purple-400">UK Companies House</h3>
                    <div className="grid gap-3">
                      {results.uk_companies_house_matches.map((m, i) => (
                        <div key={i} className="p-3 bg-gray-700 rounded-lg">
                          <div className="font-semibold">{m.name}</div>
                          <div className="text-sm text-gray-400">
                            #{m.company_number} | {m.company_type} | {m.status}
                          </div>
                          {m.incorporation_date && <div className="text-xs text-gray-500">Inc: {m.incorporation_date}</div>}
                        </div>
                      ))}
                    </div>

                    {/* UK Detail */}
                    {results.uk_companies_house_detail?.officers && (
                      <div className="mt-4">
                        <h4 className="font-semibold mb-2">Officers</h4>
                        <div className="flex flex-wrap gap-2">
                          {results.uk_companies_house_detail.officers.map((o, i) => (
                            <span key={i} className="px-2 py-1 bg-purple-600/30 border border-purple-500 rounded text-sm">
                              {o.name} ({o.role})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* SEC Form D */}
                {results.sec_form_d_filings?.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-3 text-yellow-400">SEC Form D Filings</h3>
                    <div className="grid gap-3">
                      {results.sec_form_d_filings.map((f, i) => (
                        <div key={i} className="p-3 bg-gray-700 rounded-lg">
                          <div className="font-semibold">{f.company_name}</div>
                          <div className="text-sm text-gray-400">
                            {f.form_type} | Filed: {f.filed_at}
                          </div>
                          <a href={f.sec_url} target="_blank" rel="noreferrer" className="text-xs text-blue-400 hover:underline">
                            View on SEC
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* UK Only */}
            {activeTab === 'uk' && results.uk_results && (
              <div>
                <h3 className="text-lg font-semibold mb-3">UK Companies House Results</h3>
                {Array.isArray(results.uk_results) && results.uk_results.length > 0 ? (
                  <div className="grid gap-3">
                    {results.uk_results.map((m, i) => (
                      <div key={i} className="p-4 bg-gray-700 rounded-lg">
                        <div className="font-semibold text-lg">{m.name}</div>
                        <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
                          <div><span className="text-gray-400">Company #:</span> {m.company_number}</div>
                          <div><span className="text-gray-400">Type:</span> {m.company_type}</div>
                          <div><span className="text-gray-400">Status:</span> {m.status}</div>
                          <div><span className="text-gray-400">Incorporated:</span> {m.incorporation_date}</div>
                        </div>
                        {m.registered_address && (
                          <div className="mt-2 text-gray-400 text-sm">{m.registered_address}</div>
                        )}
                        <a href={m.companies_house_url} target="_blank" rel="noreferrer"
                           className="text-blue-400 text-sm hover:underline mt-2 inline-block">
                          View on Companies House
                        </a>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-gray-400">No UK companies found</p>}
              </div>
            )}

            {/* Form D Only */}
            {activeTab === 'formd' && results.form_d_results && (
              <div>
                <h3 className="text-lg font-semibold mb-3">SEC Form D (Private Placements)</h3>
                {Array.isArray(results.form_d_results) && results.form_d_results.length > 0 ? (
                  <div className="grid gap-3">
                    {results.form_d_results.map((f, i) => (
                      <div key={i} className="p-4 bg-gray-700 rounded-lg">
                        <div className="font-semibold">{f.company_name}</div>
                        <div className="text-sm text-gray-400 mt-1">
                          Form: {f.form_type} | Filed: {f.filed_at} | CIK: {f.cik}
                        </div>
                        <a href={f.sec_url} target="_blank" rel="noreferrer"
                           className="text-blue-400 text-sm hover:underline mt-2 inline-block">
                          View Filing
                        </a>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-gray-400">No Form D filings found</p>}
              </div>
            )}

            {/* Funding History */}
            {activeTab === 'funding' && results.funding_results && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Startup Funding History</h3>
                <div className="p-4 bg-gray-700 rounded-lg mb-4">
                  <div className="text-xl font-bold text-green-400">
                    {results.funding_results.total_filings || 0} Form D Filings
                  </div>
                  <p className="text-gray-400 text-sm mt-2">{results.funding_results.data_note}</p>
                </div>
                {results.funding_results.form_d_filings?.length > 0 && (
                  <div className="space-y-2">
                    {results.funding_results.form_d_filings.map((f, i) => (
                      <div key={i} className="p-3 bg-gray-700/50 rounded flex justify-between items-center">
                        <span>{f.filed_at}</span>
                        <span className="text-blue-400">{f.form_type}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      <p className="text-gray-500 text-xs mt-6 text-center">
        Data sources: OpenCorporates, GLEIF, FinCEN, FDIC, UK Companies House, SEC EDGAR
      </p>
    </div>
  );
}
