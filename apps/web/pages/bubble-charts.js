import { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function BubbleChartsPage() {
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [xMetric, setXMetric] = useState('market_cap');
  const [yMetric, setYMetric] = useState('pe_ratio');
  const [sizeMetric, setSizeMetric] = useState('revenue');
  const [colorBy, setColorBy] = useState('sector');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  async function fetchInitialData() {
    try {
      const [presetsRes, metricsRes] = await Promise.all([
        apiFetch(`/bubble-charts/presets`),
        apiFetch(`/bubble-charts/metrics`)
      ]);
      const presetsData = await presetsRes.json();
      const metricsData = await metricsRes.json();
      setPresets(presetsData.presets || []);
      setMetrics(metricsData.metrics || []);
      fetchChart();
    } catch (err) {
      setError('Error:', err);
    }
    setLoading(false);
  }

  async function fetchChart() {
    setLoading(true);
    try {
      const res = await apiFetch(`/bubble-charts/?x_metric=${xMetric}&y_metric=${yMetric}&size_metric=${sizeMetric}&color_by=${colorBy}`);
      const data = await res.json();
      setChartData(data);
    } catch (err) {
      setError('Error:', err);
    }
    setLoading(false);
  }

  function applyPreset(preset) {
    setSelectedPreset(preset.name);
    setXMetric(preset.x_metric);
    setYMetric(preset.y_metric);
    setSizeMetric(preset.size_metric);
    setColorBy(preset.color_by);
    setTimeout(fetchChart, 100);
  }

  useEffect(() => {
    if (!loading) fetchChart();
  }, [xMetric, yMetric, sizeMetric, colorBy]);

  const formatValue = (val, type) => {
    if (type === 'size' || val > 100) return `$${val.toFixed(0)}B`;
    if (type === 'percent') return `${val.toFixed(1)}%`;
    return val.toFixed(1);
  };

  // Simple bubble visualization
  const renderBubbles = () => {
    if (!chartData?.data) return null;

    const maxSize = Math.max(...chartData.data.map(d => d.size));
    const minSize = Math.min(...chartData.data.map(d => d.size));
    const xMin = chartData.x_axis?.min || 0;
    const xMax = chartData.x_axis?.max || 100;
    const yMin = chartData.y_axis?.min || 0;
    const yMax = chartData.y_axis?.max || 100;

    return (
      <div className="relative h-96 border border-gray-700 rounded-lg overflow-hidden">

        {/* Y-axis label */}
        <div className="absolute left-0 top-1/2 transform -rotate-90 -translate-y-1/2 -translate-x-8 text-gray-400 text-sm">
          {chartData.y_axis?.label}
        </div>
        {/* X-axis label */}
        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-6 text-gray-400 text-sm">
          {chartData.x_axis?.label}
        </div>
        {/* Bubbles */}
        {chartData.data.map((bubble, i) => {
          const xPos = ((bubble.x - xMin) / (xMax - xMin)) * 80 + 10;
          const yPos = 90 - ((bubble.y - yMin) / (yMax - yMin)) * 80;
          const size = ((bubble.size - minSize) / (maxSize - minSize)) * 40 + 20;

          return (
            <div
              key={bubble.ticker}
              className="absolute transform -translate-x-1/2 -translate-y-1/2 rounded-full flex items-center justify-center cursor-pointer hover:scale-110 transition-transform"
              style={{
                left: `${xPos}%`,
                top: `${yPos}%`,
                width: `${size}px`,
                height: `${size}px`,
                backgroundColor: bubble.color,
                opacity: 0.8,
              }}
              title={`${bubble.name}\nX: ${bubble.x}\nY: ${bubble.y}\nSize: ${bubble.size}`}
            >
              <span className="text-white text-xs font-bold">{bubble.ticker}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Interactive Bubble Charts | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Interactive Bubble Charts</h1>

      {/* Presets */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Quick Presets</h2>
        <div className="flex flex-wrap gap-2">
          {presets.map(preset => (
            <button
              key={preset.name}
              onClick={() => applyPreset(preset)}
              className={`px-4 py-2 rounded-lg ${
                selectedPreset === preset.name ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div>
          <label className="block text-gray-400 text-sm mb-1">X-Axis</label>
          <select
            value={xMetric}
            onChange={(e) => setXMetric(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2"
          >
            {metrics.map(m => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-gray-400 text-sm mb-1">Y-Axis</label>
          <select
            value={yMetric}
            onChange={(e) => setYMetric(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2"
          >
            {metrics.map(m => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-gray-400 text-sm mb-1">Bubble Size</label>
          <select
            value={sizeMetric}
            onChange={(e) => setSizeMetric(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2"
          >
            {metrics.map(m => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-gray-400 text-sm mb-1">Color By</label>
          <select
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2"
          >
            <option value="sector">Sector</option>
            <option value="performance">Performance</option>
          </select>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        {loading ? (
          <div className="text-center py-10">Loading chart...</div>
        ) : (
          renderBubbles()
        )}
      </div>

      {/* Legend */}
      {chartData?.legend && (
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold mb-3">Legend</h3>
          <div className="flex flex-wrap gap-4">
            {chartData.legend.map(item => (
              <div key={item.label} className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: item.color }} />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Table */}
      {chartData?.data && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3">Data Table</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left">Ticker</th>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-right">{chartData.x_axis?.label}</th>
                  <th className="px-4 py-2 text-right">{chartData.y_axis?.label}</th>
                  <th className="px-4 py-2 text-right">{chartData.size?.label}</th>
                  <th className="px-4 py-2 text-center">Sector</th>
                </tr>
              </thead>
              <tbody>
                {chartData.data.map(item => (
                  <tr key={item.ticker} className="border-t border-gray-700">
                    <td className="px-4 py-2 font-semibold">{item.ticker}</td>
                    <td className="px-4 py-2">{item.name}</td>
                    <td className="px-4 py-2 text-right">{item.x.toFixed(1)}</td>
                    <td className="px-4 py-2 text-right">{item.y.toFixed(1)}</td>
                    <td className="px-4 py-2 text-right">{item.size.toFixed(1)}</td>
                    <td className="px-4 py-2 text-center">
                      <span
                        className="px-2 py-1 rounded text-xs"
                        style={{ backgroundColor: item.color }}
                      >
                        {item.sector}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
