import { useState, useEffect } from 'react';
import Head from 'next/head';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function BrokeragePage() {
  const [brokers, setBrokers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [syncStatus, setSyncStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const userId = 'demo_user';

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      const [brokersRes, accountsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/brokerage/brokers`),
        fetch(`${API_BASE}/brokerage/accounts?user_id=${userId}`),
        fetch(`${API_BASE}/brokerage/sync-status?user_id=${userId}`)
      ]);
      const brokersData = await brokersRes.json();
      const accountsData = await accountsRes.json();
      const statusData = await statusRes.json();
      setBrokers(brokersData.brokers || []);
      setAccounts(accountsData.accounts || []);
      setSyncStatus(statusData);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function linkBroker(brokerId) {
    setLinking(true);
    try {
      const initRes = await fetch(
        `${API_BASE}/brokerage/link/initiate?user_id=${userId}&broker_id=${brokerId}`,
        { method: 'POST' }
      );
      const initData = await initRes.json();
      if (initData.link_token) {
        // Simulate OAuth completion
        const completeRes = await fetch(
          `${API_BASE}/brokerage/link/complete?user_id=${userId}&link_token=${initData.link_token}&access_token=simulated_token`,
          { method: 'POST' }
        );
        const completeData = await completeRes.json();
        if (completeData.status === 'linked') {
          fetchData();
        }
      }
    } catch (err) {
      console.error('Error:', err);
    }
    setLinking(false);
  }

  async function selectAccount(account) {
    setSelectedAccount(account);
    try {
      const [posRes, txRes] = await Promise.all([
        fetch(`${API_BASE}/brokerage/accounts/${account.account_id}/positions?user_id=${userId}`),
        fetch(`${API_BASE}/brokerage/accounts/${account.account_id}/transactions?user_id=${userId}`)
      ]);
      const posData = await posRes.json();
      const txData = await txRes.json();
      setPositions(posData.positions || []);
      setTransactions(txData.transactions || []);
    } catch (err) {
      console.error('Error:', err);
    }
  }

  async function syncAccount(accountId) {
    try {
      await fetch(`${API_BASE}/brokerage/accounts/${accountId}/sync?user_id=${userId}`, { method: 'POST' });
      fetchData();
    } catch (err) {
      console.error('Error:', err);
    }
  }

  async function unlinkAccount(accountId) {
    if (!confirm('Are you sure you want to unlink this account?')) return;
    try {
      await fetch(`${API_BASE}/brokerage/accounts/${accountId}?user_id=${userId}`, { method: 'DELETE' });
      setSelectedAccount(null);
      setPositions([]);
      setTransactions([]);
      fetchData();
    } catch (err) {
      console.error('Error:', err);
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Brokerage Sync | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Brokerage Sync</h1>

      {loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Brokers & Accounts */}
          <div className="lg:col-span-1">
            {/* Supported Brokers */}
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Link a Broker</h2>
              <div className="space-y-3">
                {brokers.map(broker => (
                  <div key={broker.id} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
                    <div>
                      <div className="font-semibold">{broker.name}</div>
                      <div className="text-gray-400 text-sm">
                        {broker.oauth ? 'OAuth' : 'API Key'}
                      </div>
                    </div>
                    <button
                      onClick={() => linkBroker(broker.id)}
                      disabled={linking}
                      className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                    >
                      {linking ? 'Linking...' : 'Link'}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Linked Accounts */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Linked Accounts ({accounts.length})</h2>
              {accounts.length === 0 ? (
                <p className="text-gray-400">No accounts linked yet</p>
              ) : (
                <div className="space-y-3">
                  {accounts.map(account => (
                    <div
                      key={account.account_id}
                      onClick={() => selectAccount(account)}
                      className={`p-3 rounded-lg cursor-pointer ${
                        selectedAccount?.account_id === account.account_id
                          ? 'bg-blue-900 border border-blue-500'
                          : 'bg-gray-700 hover:bg-gray-650'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-semibold">{account.broker}</div>
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          account.status === 'active' ? 'bg-green-600' : 'bg-yellow-600'
                        }`}>
                          {account.status}
                        </span>
                      </div>
                      <div className="text-gray-400 text-sm">{account.account_type}</div>
                      <div className="text-gray-500 text-xs mt-1">
                        Last sync: {account.last_sync || 'Never'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Account Details */}
          <div className="lg:col-span-2">
            {selectedAccount ? (
              <>
                {/* Account Header */}
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-semibold">{selectedAccount.broker}</h2>
                      <p className="text-gray-400">{selectedAccount.account_type} Account</p>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => syncAccount(selectedAccount.account_id)}
                        className="bg-green-600 hover:bg-green-500 px-4 py-2 rounded-lg"
                      >
                        Sync Now
                      </button>
                      <button
                        onClick={() => unlinkAccount(selectedAccount.account_id)}
                        className="bg-red-600 hover:bg-red-500 px-4 py-2 rounded-lg"
                      >
                        Unlink
                      </button>
                    </div>
                  </div>
                </div>

                {/* Positions */}
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h3 className="text-lg font-semibold mb-4">Positions</h3>
                  {positions.length === 0 ? (
                    <p className="text-gray-400">No positions found</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="text-left text-gray-400 border-b border-gray-700">
                            <th className="pb-3">Symbol</th>
                            <th className="pb-3">Shares</th>
                            <th className="pb-3">Avg Cost</th>
                            <th className="pb-3">Current</th>
                            <th className="pb-3">Value</th>
                            <th className="pb-3">P/L</th>
                          </tr>
                        </thead>
                        <tbody>
                          {positions.map(pos => (
                            <tr key={pos.symbol} className="border-b border-gray-700">
                              <td className="py-3 font-semibold">{pos.symbol}</td>
                              <td className="py-3">{pos.shares}</td>
                              <td className="py-3">${pos.avg_cost?.toFixed(2) || '0.00'}</td>
                              <td className="py-3">${pos.current_price?.toFixed(2) || '0.00'}</td>
                              <td className="py-3">${pos.market_value?.toFixed(2) || '0.00'}</td>
                              <td className={`py-3 ${(pos.unrealized_pl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                ${pos.unrealized_pl?.toFixed(2) || '0.00'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Transactions */}
                <div className="bg-gray-800 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Recent Transactions</h3>
                  {transactions.length === 0 ? (
                    <p className="text-gray-400">No transactions found</p>
                  ) : (
                    <div className="space-y-3">
                      {transactions.map((tx, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
                          <div>
                            <div className="font-semibold">
                              <span className={tx.type === 'BUY' ? 'text-green-400' : 'text-red-400'}>
                                {tx.type}
                              </span>
                              {' '}{tx.symbol}
                            </div>
                            <div className="text-gray-400 text-sm">{tx.date}</div>
                          </div>
                          <div className="text-right">
                            <div>{tx.shares} shares</div>
                            <div className="text-gray-400 text-sm">@ ${tx.price?.toFixed(2) || '0.00'}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="bg-gray-800 rounded-lg p-6 text-center text-gray-400">
                Select a linked account to view details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
