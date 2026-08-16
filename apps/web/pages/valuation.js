import { useState, useEffect } from 'react';
import Head from 'next/head';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ValuationPage() {
  const [selectedTicker, setSelectedTicker] = useState('NVDA');
  const [valuation, setValuation] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);

  const tickers = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA'];

  useEffect(() => {
    fetchData(selectedTicker);
  }, [selectedTicker]);

  async function fetchData(ticker) {
    setLoading(true);
    try {
      const [valRes, compRes] = await Promise.all([
        fetch(API_BASE + '/valuation/' + ticker),
        fetch(API_BASE + '/valuation/comparison?tickers=' + tickers.join(','))
      ]);
      const valData = await valRes.json();
      const compData = await compRes.json();
      setValuation(valData);
      setComparison(compData);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  const getZScoreColor = (zscore) => {
    if (zscore <= -2) return 'text-green-400';
    if (zscore <= -1) return 'text-green-300';
    if (zscore <= 1) return 'text-yellow-400';
    if (zscore <= 2) return 'text-orange-400';
    return 'text-red-400';
  };

  const getSignalColor = (signal) => {
    const s = signal?.toLowerCase();
    if (s === 'undervalued') return 'bg-green-600';
    if (s === 'fairly valued') return 'bg-yellow-600';
    if (s === 'overvalued') return 'bg-red-600';
    return 'bg-gray-600';
  };

  const formatMultiple = (val) => val?.toFixed(1) || '-';

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Valuation Analysis | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Valuation Timeline Analysis</h1>

      <div className="flex gap-2 mb-6">
        {tickers.map(ticker => (
          <button
            key={ticker}
            onClick={() => setSelectedTicker(ticker)}
            className={'px-4 py-2 rounded-lg ' + (selectedTicker === ticker ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600')}
          >
            {ticker}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-10">Loading valuation data...</div>
      ) : valuation ? (
        <>
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">{valuation.ticker} Valuation</h2>
                <p className="text-gray-400">{valuation.company_name}</p>
              </div>
              <div className="text-right">
                <div className={'text-4xl font-bold ' + getZScoreColor(valuation.composite_zscore)}>
                  {valuation.composite_zscore?.toFixed(2)}
                </div>
                <div className="text-gray-400">Composite Z-Score</div>
                <span className={'inline-block mt-2 px-3 py-1 rounded-full text-sm ' + getSignalColor(valuation.signal)}>
                  {valuation.signal}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {valuation.multiples?.map(metric => (
              <div key={metric.name} className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">{metric.name}</div>
                <div className="text-2xl font-bold">{formatMultiple(metric.current)}</div>
                <div className="flex items-center gap-2 text-sm mt-2">
                  <span className="text-gray-400">5Y Avg:</span>
                  <span>{formatMultiple(metric.historical_avg)}</span>
                </div>
                <div className={'text-sm ' + getZScoreColor(metric.zscore)}>
                  Z-Score: {metric.zscore?.toFixed(2)}
                </div>
              </div>
            ))}
          </div>

          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Historical Valuation Bands</h3>
            <div className="space-y-4">
              {valuation.bands?.map(band => (
                <div key={band.metric}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{band.metric}</span>
                    <span className="text-gray-400">
                      Min: {formatMultiple(band.min)} | Avg: {formatMultiple(band.avg)} | Max: {formatMultiple(band.max)}
                    </span>
                  </div>
                  <div className="relative h-6 bg-gray-700 rounded-full overflow-hidden">
                    <div className="absolute h-full bg-blue-900/50" style={{ left: '0%', width: '100%' }} />
                    <div className="absolute top-0 h-full w-1 bg-yellow-400" style={{ left: band.percentile + '%' }} />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs">
                      {band.percentile}th percentile
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {comparison?.comparisons && (
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4">Cross-Company Comparison</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-700">
                    <tr>
                      <th className="px-4 py-2 text-left">Ticker</th>
                      <th className="px-4 py-2 text-right">P/E</th>
                      <th className="px-4 py-2 text-right">P/S</th>
                      <th className="px-4 py-2 text-right">P/B</th>
                      <th className="px-4 py-2 text-right">EV/EBITDA</th>
                      <th className="px-4 py-2 text-right">Z-Score</th>
                      <th className="px-4 py-2 text-center">Signal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.comparisons.map(item => (
                      <tr
                        key={item.ticker}
                        className={'border-t border-gray-700 ' + (item.ticker === selectedTicker ? 'bg-blue-900/30' : '')}
                      >
                        <td className="px-4 py-3 font-semibold">{item.ticker}</td>
                        <td className="px-4 py-3 text-right">{formatMultiple(item.pe_ratio)}</td>
                        <td className="px-4 py-3 text-right">{formatMultiple(item.ps_ratio)}</td>
                        <td className="px-4 py-3 text-right">{formatMultiple(item.pb_ratio)}</td>
                        <td className="px-4 py-3 text-right">{formatMultiple(item.ev_ebitda)}</td>
                        <td className={'px-4 py-3 text-right font-semibold ' + getZScoreColor(item.composite_zscore)}>
                          {item.composite_zscore?.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={'px-2 py-1 rounded text-xs ' + getSignalColor(item.signal)}>
                            {item.signal}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center text-gray-400 py-10">
          No valuation data available
        </div>
      )}
    </div>
  );
}
