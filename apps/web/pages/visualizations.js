import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function VisualizationsPage() {
  const [chartType, setChartType] = useState('sector-breakdown');
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [noData, setNoData] = useState(null);

  const chartOptions = [
    { id: 'sector-breakdown', name: 'Sector Breakdown', endpoint: '/visualizations/sector-breakdown' },
    { id: 'performance', name: 'Performance Comparison', endpoint: '/visualizations/performance-comparison?tickers=NVDA,AAPL,MSFT,GOOGL,META' },
    { id: 'treemap', name: 'Portfolio Treemap', endpoint: '/visualizations/treemap' },
    { id: 'correlation', name: 'Correlation Matrix', endpoint: '/visualizations/correlation?tickers=NVDA,AAPL,MSFT,GOOGL,META' },
    { id: 'radar', name: 'Factor Analysis', endpoint: '/visualizations/radar/NVDA' },
    { id: 'histogram', name: 'Return Distribution', endpoint: '/visualizations/histogram' },
    { id: 'gauge', name: 'Portfolio Health', endpoint: '/visualizations/gauge' },
    { id: 'waterfall', name: 'Performance Attribution', endpoint: '/visualizations/waterfall/NVDA' },
  ];

  useEffect(() => {
    fetchChart(chartType);
  }, [chartType]);

  async function fetchChart(type) {
    setLoading(true);
    setNoData(null);
    const option = chartOptions.find(o => o.id === type);
    try {
      const res = await fetch(`${API_BASE}${option.endpoint}`);
      const data = await res.json();
      if (isNoData(data)) { setNoData(data); setChartData(null); setLoading(false); return; }
      setChartData(data);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  const formatCurrency = (val) => `$${(val || 0).toLocaleString()}`;

  const renderChart = () => {
    if (!chartData) return null;

    switch (chartData.chart_type) {
      case 'pie':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-center justify-center">
              {/* Simple pie representation */}
              <div className="relative w-64 h-64">
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-blue-500 via-green-500 to-yellow-500 animate-spin-slow" />
                <div className="absolute inset-4 rounded-full bg-gray-800 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-3xl font-bold">{chartData.total_value?.toFixed(1)}%</div>
                    <div className="text-gray-400 text-sm">Total</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {chartData.data?.map(item => (
                <div key={item.name} className="flex items-center gap-3">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: item.color }} />
                  <span className="flex-1">{item.name}</span>
                  <span className="font-semibold">{item.value}%</span>
                  <span className="text-gray-400 text-sm">({item.count} stocks)</span>
                </div>
              ))}
            </div>
          </div>
        );

      case 'bar':
        return (
          <div className="space-y-4">
            {chartData.data?.map(item => (
              <div key={item.ticker} className="flex items-center gap-4">
                <span className="w-16 font-semibold">{item.ticker}</span>
                <div className="flex-1 h-8 bg-gray-700 rounded-lg overflow-hidden">
                  <div
                    className={`h-full ${item.positive ? 'bg-green-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(Math.abs(item.return), 100)}%` }}
                  />
                </div>
                <span className={`w-20 text-right ${item.positive ? 'text-green-400' : 'text-red-400'}`}>
                  {item.return > 0 ? '+' : ''}{item.return}%
                </span>
              </div>
            ))}
            {chartData.benchmark && (
              <div className="pt-4 border-t border-gray-700 flex items-center gap-4">
                <span className="w-16 font-semibold text-gray-400">{chartData.benchmark.ticker}</span>
                <div className="flex-1 h-8 bg-gray-700 rounded-lg overflow-hidden">
                  <div
                    className="h-full bg-blue-500"
                    style={{ width: `${Math.min(chartData.benchmark.return, 100)}%` }}
                  />
                </div>
                <span className="w-20 text-right text-blue-400">
                  +{chartData.benchmark.return}%
                </span>
              </div>
            )}
          </div>
        );

      case 'heatmap':
        return (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="px-2 py-2"></th>
                  {chartData.tickers?.map(t => (
                    <th key={t} className="px-2 py-2 text-center text-sm">{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {chartData.matrix?.map((row, i) => (
                  <tr key={i}>
                    <td className="px-2 py-2 font-semibold">{chartData.tickers[i]}</td>
                    {row.map((val, j) => (
                      <td key={j} className="px-2 py-2 text-center">
                        <div
                          className="w-full py-1 rounded text-sm"
                          style={{
                            backgroundColor: `rgba(${val > 0.5 ? '34, 197, 94' : '239, 68, 68'}, ${Math.abs(val)})`,
                          }}
                        >
                          {val.toFixed(2)}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      case 'treemap':
        return (
          <div className="space-y-4">
            {chartData.data?.map(sector => (
              <div key={sector.name}>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: sector.color }} />
                  <span className="font-semibold">{sector.name}</span>
                  <span className="text-gray-400 text-sm">{formatCurrency(sector.value)}</span>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {sector.children?.map(child => (
                    <div
                      key={child.name}
                      className="px-3 py-2 rounded-lg"
                      style={{ backgroundColor: sector.color, minWidth: `${Math.max(child.value / 1000, 80)}px` }}
                    >
                      <div className="font-semibold">{child.name}</div>
                      <div className="text-sm opacity-80">{formatCurrency(child.value)}</div>
                      <div className={`text-xs ${child.change > 0 ? 'text-green-200' : 'text-red-200'}`}>
                        {child.change > 0 ? '+' : ''}{child.change}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        );

      case 'radar':
        return (
          <div className="text-center">
            <div className="text-4xl font-bold mb-4">{chartData.overall_score}/100</div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {chartData.metrics?.map(m => (
                <div key={m.name} className="bg-gray-700 p-4 rounded-lg">
                  <div className="text-gray-400 text-sm">{m.name}</div>
                  <div className="text-2xl font-bold">{m.score}</div>
                  <div className="w-full h-2 bg-gray-600 rounded-full mt-2 overflow-hidden">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${m.score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'histogram':
        return (
          <div>
            <div className="flex items-end gap-1 h-40 mb-4">
              {chartData.bins?.map((bin, i) => (
                <div
                  key={i}
                  className="flex-1 bg-blue-500 rounded-t hover:bg-blue-400 transition"
                  style={{ height: `${bin.frequency * 3}%` }}
                  title={`${bin.range}: ${bin.count} days`}
                />
              ))}
            </div>
            {chartData.statistics && (
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-gray-400 text-sm">Mean</div>
                  <div className="font-bold">{chartData.statistics.mean}%</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Std Dev</div>
                  <div className="font-bold">{chartData.statistics.std}%</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Min</div>
                  <div className="font-bold">{chartData.statistics.min}%</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Max</div>
                  <div className="font-bold">{chartData.statistics.max}%</div>
                </div>
              </div>
            )}
          </div>
        );

      case 'gauge':
        return (
          <div className="text-center">
            <div className="relative inline-block w-64 h-32 overflow-hidden">
              <div className="absolute inset-0 border-t-8 border-l-8 border-r-8 rounded-t-full" style={{ borderColor: chartData.color }} />
              <div
                className="absolute bottom-0 left-1/2 w-2 h-24 bg-white origin-bottom transform -translate-x-1/2"
                style={{ transform: `translateX(-50%) rotate(${(chartData.value - 50) * 1.8}deg)` }}
              />
            </div>
            <div className="text-4xl font-bold mt-4">{chartData.value}</div>
            <div className={`text-xl ${
              chartData.current_zone === 'Excellent' ? 'text-green-400' :
              chartData.current_zone === 'Good' || chartData.current_zone === 'Very Good' ? 'text-green-400' :
              chartData.current_zone === 'Fair' ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {chartData.current_zone}
            </div>
          </div>
        );

      case 'waterfall':
        return (
          <div className="space-y-2">
            {chartData.data?.map((item, i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="w-32 text-sm">{item.name}</span>
                <div className="flex-1 flex items-center">
                  {item.type === 'start' || item.type === 'end' ? (
                    <div className="h-8 bg-blue-500 rounded" style={{ width: `${item.value / 1000}%` }} />
                  ) : (
                    <>
                      <div style={{ width: `${(item.start) / 1000}%` }} />
                      <div
                        className={`h-8 rounded ${item.value > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.abs(item.value) / 100}%` }}
                      />
                    </>
                  )}
                </div>
                <span className={`w-24 text-right ${
                  item.type === 'positive' ? 'text-green-400' :
                  item.type === 'negative' ? 'text-red-400' : ''
                }`}>
                  {item.type !== 'start' && item.type !== 'end' ? (item.value > 0 ? '+' : '') : ''}
                  {formatCurrency(item.value)}
                </span>
              </div>
            ))}
            <div className="pt-4 border-t border-gray-700 text-center">
              <span className="text-gray-400">Total Change: </span>
              <span className={`text-xl font-bold ${chartData.total_change > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {chartData.total_change > 0 ? '+' : ''}{formatCurrency(chartData.total_change)} ({chartData.total_change_percent}%)
              </span>
            </div>
          </div>
        );

      default:
        return <pre className="text-sm overflow-x-auto">{JSON.stringify(chartData, null, 2)}</pre>;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Data Visualizations | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Data Visualizations</h1>

      {/* Chart Selector */}
      <div className="flex flex-wrap gap-2 mb-6">
        {chartOptions.map(opt => (
          <button
            key={opt.id}
            onClick={() => setChartType(opt.id)}
            className={`px-4 py-2 rounded-lg ${
              chartType === opt.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {opt.name}
          </button>
        ))}
      </div>

      {/* Chart Display */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-6">{chartData?.title || 'Loading...'}</h2>
        {loading ? (
          <div className="text-center py-10">Loading chart...</div>
        ) : noData ? (
          <NoDataCard {...noData} />
        ) : (
          renderChart()
        )}
      </div>
    </div>
  );
}
