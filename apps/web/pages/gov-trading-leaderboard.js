import { useEffect, useState } from 'react';
import Head from 'next/head';
import { getApiBaseUrl } from '../lib/api';

export default function GovTradingLeaderboardPage() {
  const API = getApiBaseUrl();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('trades');
  const [data, setData] = useState(null);
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  const tabs = [
    { id: 'trades', label: 'Top by Trades', color: 'blue' },
    { id: 'volume', label: 'Top by Volume', color: 'green' },
    { id: 'returns', label: 'Top by Returns', color: 'yellow' },
    { id: 'executive', label: 'Executive Branch', color: 'purple' },
    { id: 'notable', label: 'Notable Cases', color: 'red' },
  ];

  useEffect(() => {
    Promise.all([
      fetch(`${API}/market/gov-trading/leaderboard/${activeTab === 'notable' ? '' : activeTab}${activeTab === 'notable' ? 'notable-cases' : ''}`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/market/gov-trading/leaderboard/statistics`).then(r => r.ok ? r.json() : null),
    ])
      .then(([leaderboard, statistics]) => {
        setData(leaderboard);
        setStats(statistics);
        setLoading(false);
      })
      .catch(e => {
        setErr(e.message);
        setLoading(false);
      });
  }, [API, activeTab]);

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch(`${API}/market/gov-trading/leaderboard/rank/${encodeURIComponent(searchQuery)}`);
      setSearchResults(await res.json());
    } catch (e) {
      console.error(e);
    }
  }

  const formatCurrency = (val) => {
    if (!val) return '-';
    if (val >= 1_000_000_000) return `$${(val / 1_000_000_000).toFixed(1)}B`;
    if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
    if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
    return `$${val.toFixed(0)}`;
  };

  const formatPercent = (val) => {
    if (!val) return '-';
    return `${val > 0 ? '+' : ''}${val.toFixed(1)}%`;
  };

  const partyColor = (party) => {
    if (party === 'D') return 'text-blue-400';
    if (party === 'R') return 'text-red-400';
    return 'text-gray-400';
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Government Trading Leaderboards | Finance Platform</title>
      </Head>

      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Government Trading Leaderboards</h1>
        <p className="text-gray-400 mb-6">
          637 US Government Officials — Stock Trading Rankings (2013-2026)
        </p>

        {/* Stats Banner */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">{stats.total_politicians}</div>
              <div className="text-xs text-gray-400">Total Officials</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{stats.top_by_volume_count}</div>
              <div className="text-xs text-gray-400">By Volume</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-yellow-400">{stats.top_by_returns_count}</div>
              <div className="text-xs text-gray-400">By Returns</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-purple-400">{stats.executive_branch_count}</div>
              <div className="text-xs text-gray-400">Executive Branch</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-400">{stats.notable_cases_count}</div>
              <div className="text-xs text-gray-400">Notable Cases</div>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search politician (e.g., Pelosi, Trump, Tuberville)"
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
              onKeyPress={e => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg"
            >
              Search
            </button>
          </div>
          {searchResults && (
            <div className="mt-4 p-4 bg-gray-700 rounded-lg">
              {searchResults.found ? (
                <div>
                  <div className="font-semibold text-lg mb-2">{searchResults.name}</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {searchResults.rank_by_trades && (
                      <div className="text-sm">
                        <span className="text-gray-400">By Trades:</span>{' '}
                        <span className="text-blue-400">#{searchResults.rank_by_trades}</span>
                      </div>
                    )}
                    {searchResults.rank_by_volume && (
                      <div className="text-sm">
                        <span className="text-gray-400">By Volume:</span>{' '}
                        <span className="text-green-400">#{searchResults.rank_by_volume}</span>
                      </div>
                    )}
                    {searchResults.rank_by_returns && (
                      <div className="text-sm">
                        <span className="text-gray-400">By Returns:</span>{' '}
                        <span className="text-yellow-400">#{searchResults.rank_by_returns}</span>
                      </div>
                    )}
                    {searchResults.is_executive_branch && (
                      <div className="text-sm text-purple-400">Executive Branch</div>
                    )}
                  </div>
                  {searchResults.notable_cases_count > 0 && (
                    <div className="mt-2 text-red-400 text-sm">
                      {searchResults.notable_cases_count} notable case(s)
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-gray-400">No results found for "{searchQuery}"</div>
              )}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setLoading(true); }}
              className={`px-4 py-2 rounded-lg whitespace-nowrap text-sm font-medium ${
                activeTab === tab.id
                  ? `bg-${tab.color}-600`
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading && <div className="text-blue-400 mb-4">Loading leaderboard...</div>}
        {err && <div className="text-red-400 mb-4">Error: {err}</div>}

        {/* Leaderboard Table */}
        {!loading && data && activeTab !== 'notable' && (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-700">
                <tr>
                  <th className="text-left py-3 px-4">#</th>
                  <th className="text-left py-3 px-4">Official</th>
                  <th className="text-left py-3 px-4">Party</th>
                  <th className="text-left py-3 px-4">Chamber/Role</th>
                  <th className="text-left py-3 px-4">State</th>
                  {activeTab === 'trades' && <th className="text-right py-3 px-4">Trades</th>}
                  {activeTab === 'volume' && <th className="text-right py-3 px-4">Volume</th>}
                  {activeTab === 'returns' && <th className="text-right py-3 px-4">Return %</th>}
                  {activeTab === 'returns' && <th className="text-right py-3 px-4">vs S&P</th>}
                  {activeTab === 'executive' && <th className="text-right py-3 px-4">Trades 2025+</th>}
                  {activeTab === 'executive' && <th className="text-right py-3 px-4">Late %</th>}
                  <th className="text-right py-3 px-4">Volume</th>
                  <th className="text-right py-3 px-4">Return</th>
                </tr>
              </thead>
              <tbody>
                {(data.data || []).map((row, idx) => (
                  <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700/50">
                    <td className="py-3 px-4 text-gray-400">{row.rank || idx + 1}</td>
                    <td className="py-3 px-4 font-medium">{row.name}</td>
                    <td className={`py-3 px-4 ${partyColor(row.party)}`}>{row.party || '-'}</td>
                    <td className="py-3 px-4 text-gray-400">{row.chamber || row.role || '-'}</td>
                    <td className="py-3 px-4">{row.state || '-'}</td>
                    {activeTab === 'trades' && (
                      <td className="py-3 px-4 text-right text-blue-400 font-semibold">
                        {row.trade_count?.toLocaleString() || '-'}
                      </td>
                    )}
                    {activeTab === 'volume' && (
                      <td className="py-3 px-4 text-right text-green-400 font-semibold">
                        {formatCurrency(row.volume_usd)}
                      </td>
                    )}
                    {activeTab === 'returns' && (
                      <>
                        <td className="py-3 px-4 text-right text-yellow-400 font-semibold">
                          {formatPercent(row.return_pct)}
                        </td>
                        <td className="py-3 px-4 text-right text-green-400">
                          {formatPercent(row.vs_sp500)}
                        </td>
                      </>
                    )}
                    {activeTab === 'executive' && (
                      <>
                        <td className="py-3 px-4 text-right text-purple-400">
                          {row.trades_2025 || '-'}
                        </td>
                        <td className="py-3 px-4 text-right text-red-400">
                          {row.late_filing_pct ? `${row.late_filing_pct}%` : '-'}
                        </td>
                      </>
                    )}
                    <td className="py-3 px-4 text-right text-gray-400">
                      {formatCurrency(row.volume_usd)}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-400">
                      {formatPercent(row.return_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Notable Cases */}
        {!loading && data && activeTab === 'notable' && (
          <div className="space-y-4">
            {(data.cases || []).map((c, idx) => (
              <div key={idx} className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold text-red-400">{c.case}</div>
                    <div className="text-sm text-gray-400 mt-1">
                      {c.official} ({c.party}) — {c.position}
                    </div>
                  </div>
                  <div className="text-gray-500">{c.year}</div>
                </div>
                {c.trades_amount && (
                  <div className="mt-2 text-sm text-yellow-400">{c.trades_amount}</div>
                )}
                {c.details && (
                  <div className="mt-2 text-sm text-gray-300">{c.details}</div>
                )}
                {c.outcome && (
                  <div className="mt-2 text-sm">
                    <span className="text-gray-400">Outcome:</span> {c.outcome}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <p className="text-gray-500 text-xs mt-6 text-center">
          Data sources: Capitol Markets, Capitol Trades, Kapitol.ai, Open Cabinet, STOCK Act disclosures (2013-2026)
        </p>
      </div>
    </div>
  );
}
