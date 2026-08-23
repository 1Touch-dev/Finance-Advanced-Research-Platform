import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData , apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function GlobalMarketsPage() {
  const [markets, setMarkets] = useState([]);
  const [indices, setIndices] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [noData, setNoData] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      const [marketsRes, indicesRes] = await Promise.all([
        apiFetch('/global/markets/status'),
        apiFetch('/global/indices')
      ]);
      const marketsData = await marketsRes.json();
      if (isNoData(marketsData)) { setNoData(marketsData); setLoading(false); return; }
      const indicesData = await indicesRes.json();
      setMarkets(marketsData.markets || []);
      setIndices(indicesData.indices || []);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function searchStocks() {
    if (!searchQuery) return;
    try {
      const res = await apiFetch('/global/search?query=' + encodeURIComponent(searchQuery));
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (err) {
      console.error('Error:', err);
    }
  }

  async function selectStock(ticker) {
    try {
      const res = await apiFetch('/global/quote/' + ticker);
      const data = await res.json();
      setSelectedStock(data);
    } catch (err) {
      console.error('Error:', err);
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'open': return 'bg-green-600';
      case 'closed': return 'bg-red-600';
      case 'pre-market': return 'bg-yellow-600';
      case 'after-hours': return 'bg-purple-600';
      default: return 'bg-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Global Markets | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Global Equity Markets</h1>

      {loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : noData ? (
        <NoDataCard {...noData} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Market Status */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Market Status</h2>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {markets.map(market => (
                  <div key={market.code} className="bg-gray-700 p-3 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold">{market.code}</span>
                      <span className={'px-2 py-0.5 rounded text-xs ' + getStatusColor(market.status)}>
                        {market.status}
                      </span>
                    </div>
                    <div className="text-gray-400 text-sm">{market.name}</div>
                    <div className="text-gray-500 text-xs">{market.local_time}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Global Indices */}
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Major Indices</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {indices.map(index => (
                  <div key={index.symbol} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
                    <div>
                      <div className="font-semibold">{index.name}</div>
                      <div className="text-gray-400 text-sm">{index.country}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{index.value.toLocaleString()}</div>
                      <div className={index.change >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {index.change >= 0 ? '+' : ''}{index.change}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Search */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Search Global Stocks</h2>
              <div className="flex gap-4 mb-4">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by ticker or company name..."
                  className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  onKeyPress={(e) => e.key === 'Enter' && searchStocks()}
                />
                <button
                  onClick={searchStocks}
                  className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg"
                >
                  Search
                </button>
              </div>
              {searchResults.length > 0 && (
                <div className="space-y-2">
                  {searchResults.map(stock => (
                    <div
                      key={stock.ticker}
                      onClick={() => selectStock(stock.ticker)}
                      className="flex items-center justify-between p-3 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-650"
                    >
                      <div>
                        <span className="font-semibold">{stock.ticker}</span>
                        <span className="text-gray-400 ml-2">{stock.name}</span>
                      </div>
                      <div className="text-gray-400 text-sm">
                        {stock.exchange} · {stock.currency}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Stock Detail */}
          <div className="lg:col-span-1">
            {selectedStock ? (
              <div className="bg-gray-800 rounded-lg p-6 sticky top-6">
                <h2 className="text-xl font-semibold mb-2">{selectedStock.ticker}</h2>
                <p className="text-gray-400 mb-4">{selectedStock.name}</p>
                
                <div className="text-3xl font-bold mb-2">
                  {selectedStock.currency} {selectedStock.price.toFixed(2)}
                </div>
                <div className={selectedStock.change >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {selectedStock.change >= 0 ? '+' : ''}{selectedStock.change.toFixed(2)} 
                  ({selectedStock.change_percent.toFixed(2)}%)
                </div>

                <div className="mt-6 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Exchange</span>
                    <span>{selectedStock.exchange}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Country</span>
                    <span>{selectedStock.country}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Market Cap</span>
                    <span>{selectedStock.market_cap}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">P/E Ratio</span>
                    <span>{selectedStock.pe_ratio}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Dividend Yield</span>
                    <span>{selectedStock.dividend_yield}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Volume</span>
                    <span>{selectedStock.volume.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-800 rounded-lg p-6 text-center text-gray-400">
                Search and select a stock to view details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
