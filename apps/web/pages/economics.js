import { useEffect, useState } from 'react';
import { getApiBaseUrl , apiFetch } from '../lib/api';
import Head from 'next/head';

export default function EconomicsPage() {
  const API = getApiBaseUrl();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [activeTab, setActiveTab] = useState('gdp');

  // Data states
  const [gdpData, setGdpData] = useState(null);
  const [stateIncome, setStateIncome] = useState(null);
  const [samOpps, setSamOpps] = useState(null);
  const [regulations, setRegulations] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr('');

    Promise.all([
      apiFetch(`/market/macro/dashboard`).then(r => r.ok ? r.json() : null).catch(() => null),
      apiFetch(`/government/bea/gdp`).then(r => r.ok ? r.json() : null).catch(() => null),
      apiFetch(`/government/bea/state-income`).then(r => r.ok ? r.json() : null).catch(() => null),
      apiFetch(`/government/sam/opportunities?limit=10`).then(r => r.ok ? r.json() : null).catch(() => null),
      apiFetch(`/government/regulations/search?limit=10`).then(r => r.ok ? r.json() : null).catch(() => null),
    ])
      .then(([fredDashboard, beaGdp, state, sam, regs]) => {
        if (cancelled) return;
        // FRED is primary, BEA is fallback
        if (fredDashboard && fredDashboard.gdp) {
          setGdpData({ source: 'FRED', data: fredDashboard.gdp, indicators: fredDashboard });
        } else if (beaGdp && !beaGdp.error) {
          setGdpData({ source: 'BEA', data: beaGdp.data, fallback: true });
        } else {
          setGdpData(null);
        }
        setStateIncome(state);
        setSamOpps(sam);
        setRegulations(regs);
      })
      .catch(e => {
        if (!cancelled) setErr(e.message || String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [API]);

  const tabs = [
    { id: 'gdp', label: 'GDP Data' },
    { id: 'state', label: 'State Income' },
    { id: 'contracts', label: 'Federal Contracts' },
    { id: 'regulations', label: 'Regulations' },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Government & Economic Data | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-2">Government & Economic Data</h1>
      <p className="text-gray-400 mb-6">BEA, SAM.gov, Regulations.gov — Real-time government data feeds</p>

      {loading && <div className="text-blue-400 mb-4">Loading data...</div>}
      {err && <div className="text-red-400 mb-4">Error: {err}</div>}

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap ${
              activeTab === tab.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-gray-800 rounded-lg p-6">
        {activeTab === 'gdp' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">U.S. Economic Indicators</h2>
              {gdpData?.source && (
                <span className={`text-xs px-2 py-1 rounded ${gdpData.source === 'FRED' ? 'bg-green-700' : 'bg-blue-700'}`}>
                  Source: {gdpData.source} {gdpData.fallback && '(fallback)'}
                </span>
              )}
            </div>

            {/* FRED-style indicators dashboard */}
            {gdpData?.indicators && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {gdpData.indicators.gdp && (
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <div className="text-sm text-gray-400">GDP</div>
                    <div className="text-2xl font-bold">${gdpData.indicators.gdp.value?.toLocaleString() || 'N/A'}</div>
                    <div className="text-xs text-gray-500">{gdpData.indicators.gdp.date || 'Latest'}</div>
                  </div>
                )}
                {gdpData.indicators.cpi && (
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <div className="text-sm text-gray-400">CPI (Inflation)</div>
                    <div className="text-2xl font-bold">{gdpData.indicators.cpi.value || 'N/A'}</div>
                    <div className="text-xs text-gray-500">{gdpData.indicators.cpi.date || 'Latest'}</div>
                  </div>
                )}
                {gdpData.indicators.unemployment && (
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <div className="text-sm text-gray-400">Unemployment</div>
                    <div className="text-2xl font-bold">{gdpData.indicators.unemployment.value}%</div>
                    <div className="text-xs text-gray-500">{gdpData.indicators.unemployment.date || 'Latest'}</div>
                  </div>
                )}
                {gdpData.indicators.fed_funds && (
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <div className="text-sm text-gray-400">Fed Funds Rate</div>
                    <div className="text-2xl font-bold">{gdpData.indicators.fed_funds.value}%</div>
                    <div className="text-xs text-gray-500">{gdpData.indicators.fed_funds.date || 'Latest'}</div>
                  </div>
                )}
              </div>
            )}

            {gdpData?.data ? (
              <div className="overflow-x-auto">
                <h3 className="text-lg font-semibold mb-2">Historical GDP</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left py-2">Period</th>
                      <th className="text-left py-2">GDP (Billions)</th>
                      <th className="text-left py-2">Growth</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(Array.isArray(gdpData.data) ? gdpData.data : [gdpData.data]).slice(0, 10).map((row, idx) => (
                      <tr key={idx} className="border-b border-gray-700/50">
                        <td className="py-2">{row.year || row.TimePeriod || row.date || '-'}</td>
                        <td className="py-2">${row.value?.toLocaleString() || row.DataValue || '-'}</td>
                        <td className="py-2 text-green-400">{row.growth || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-400">No GDP data available. Check FRED_API_KEY or BEA_API_USER_ID in .env</p>
            )}
            <p className="text-gray-500 text-xs mt-4">
              Source: {gdpData?.source === 'FRED' ? 'Federal Reserve Economic Data (fred.stlouisfed.org)' : 'Bureau of Economic Analysis (api.bea.gov)'}
            </p>
          </div>
        )}

        {activeTab === 'state' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">State Personal Income</h2>
            {stateIncome?.data ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {(stateIncome.data || []).slice(0, 20).map((row, idx) => (
                  <div key={idx} className="p-3 bg-gray-700 rounded-lg">
                    <div className="font-semibold">{row.state || row.GeoName}</div>
                    <div className="text-green-400">${row.income || row.DataValue}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No state income data available.</p>
            )}
          </div>
        )}

        {activeTab === 'contracts' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Federal Contract Opportunities (SAM.gov)</h2>
            {samOpps?.opportunities?.length > 0 ? (
              <div className="space-y-3">
                {samOpps.opportunities.map((opp, idx) => (
                  <div key={idx} className="p-4 bg-gray-700 rounded-lg">
                    <div className="font-semibold text-blue-400">{opp.title}</div>
                    <div className="text-sm text-gray-400 mt-1">
                      {opp.agency} | {opp.type} | Posted: {opp.postedDate}
                    </div>
                    {opp.responseDeadline && (
                      <div className="text-sm text-yellow-400 mt-1">
                        Deadline: {opp.responseDeadline}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No contract opportunities found. Check SAM_GOV_API_KEY in .env</p>
            )}
          </div>
        )}

        {activeTab === 'regulations' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Federal Regulations (Regulations.gov)</h2>
            {regulations?.documents?.length > 0 ? (
              <div className="space-y-3">
                {regulations.documents.map((doc, idx) => (
                  <div key={idx} className="p-4 bg-gray-700 rounded-lg">
                    <div className="font-semibold">{doc.title}</div>
                    <div className="text-sm text-gray-400 mt-1">
                      {doc.agency} | {doc.documentType} | {doc.postedDate}
                    </div>
                    {doc.commentEndDate && (
                      <div className="text-sm text-yellow-400 mt-1">
                        Comments due: {doc.commentEndDate}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No regulations found. Check REGULATIONS_GOV_API_KEY in .env</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
