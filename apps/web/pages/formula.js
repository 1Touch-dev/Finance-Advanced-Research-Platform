/**
 * Custom Formula & Expression Charting Page (Band B #26)
 *
 * Features:
 * - Formula builder with syntax highlighting
 * - Real-time validation
 * - Chart visualization
 * - Save/load formulas
 */

import React, { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Formula Input ────────────────────────────────────────────────────────────

function FormulaInput({ value, onChange, validation, onEvaluate }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex gap-4 items-start">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Formula
          </label>
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="e.g., NVDA.price / AAPL.price or rolling_avg(TSLA.price, 20)"
            className={`w-full px-4 py-3 border rounded-lg font-mono text-sm ${
              validation?.valid === false
                ? 'border-red-300 bg-red-50'
                : validation?.valid === true
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300'
            }`}
            rows={3}
          />
          {validation?.errors?.length > 0 && (
            <div className="mt-2 text-sm text-red-600">
              {validation.errors.map((e, i) => (
                <div key={i}>• {e}</div>
              ))}
            </div>
          )}
          {validation?.warnings?.length > 0 && (
            <div className="mt-2 text-sm text-yellow-600">
              {validation.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={onEvaluate}
          disabled={!value || validation?.valid === false}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Evaluate
        </button>
      </div>
    </div>
  );
}

// ── Chart Display ────────────────────────────────────────────────────────────

function ChartDisplay({ data }) {
  if (!data?.computed?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Enter a formula and click Evaluate to see results
      </div>
    );
  }

  // Filter out null values and get min/max
  const validPoints = data.computed.filter(p => p.value !== null);
  if (validPoints.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No valid data points to display
      </div>
    );
  }

  const values = validPoints.map(p => p.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  // Simple SVG line chart
  const width = 800;
  const height = 300;
  const padding = 40;

  const xScale = (i) => padding + (i / (validPoints.length - 1)) * (width - 2 * padding);
  const yScale = (v) => height - padding - ((v - minVal) / range) * (height - 2 * padding);

  const pathD = validPoints
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.value)}`)
    .join(' ');

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-gray-900">
          {data.formula}
        </h3>
        <div className="text-sm text-gray-500">
          {validPoints.length} data points
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-64">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map(pct => (
          <g key={pct}>
            <line
              x1={padding}
              y1={padding + pct * (height - 2 * padding)}
              x2={width - padding}
              y2={padding + pct * (height - 2 * padding)}
              stroke="#e5e7eb"
              strokeDasharray="4"
            />
            <text
              x={padding - 5}
              y={padding + pct * (height - 2 * padding)}
              textAnchor="end"
              fontSize="10"
              fill="#9ca3af"
            >
              {(maxVal - pct * range).toFixed(2)}
            </text>
          </g>
        ))}

        {/* Data line */}
        <path
          d={pathD}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
        />

        {/* Axes */}
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#9ca3af" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#9ca3af" />
      </svg>

      {/* Stats */}
      <div className="mt-4 grid grid-cols-4 gap-4 text-sm">
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Latest</div>
          <div className="font-semibold">{validPoints[validPoints.length - 1]?.value.toFixed(4)}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Min</div>
          <div className="font-semibold">{minVal.toFixed(4)}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Max</div>
          <div className="font-semibold">{maxVal.toFixed(4)}</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-gray-500">Range</div>
          <div className="font-semibold">{range.toFixed(4)}</div>
        </div>
      </div>
    </div>
  );
}

// ── Preset Formulas ──────────────────────────────────────────────────────────

function PresetFormulas({ onSelect }) {
  const presets = [
    { label: 'Price Ratio', formula: 'NVDA.price / AAPL.price' },
    { label: '20D MA', formula: 'rolling_avg(NVDA.price, 20)' },
    { label: 'Momentum', formula: 'pct_change(TSLA.price, 20)' },
    { label: 'Volatility', formula: 'rolling_std(AMD.price, 20)' },
    { label: 'Relative Strength', formula: 'NVDA.price / SPY.price' },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {presets.map((p, i) => (
        <button
          key={i}
          onClick={() => onSelect(p.formula)}
          className="px-3 py-1 text-sm bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100"
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

// ── Reference Panel ──────────────────────────────────────────────────────────

function ReferencePanel({ metrics, functions }) {
  const [activeTab, setActiveTab] = useState('metrics');

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="border-b">
        <nav className="flex">
          <button
            onClick={() => setActiveTab('metrics')}
            className={`px-4 py-3 text-sm font-medium ${
              activeTab === 'metrics' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
            }`}
          >
            Metrics
          </button>
          <button
            onClick={() => setActiveTab('functions')}
            className={`px-4 py-3 text-sm font-medium ${
              activeTab === 'functions' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
            }`}
          >
            Functions
          </button>
          <button
            onClick={() => setActiveTab('syntax')}
            className={`px-4 py-3 text-sm font-medium ${
              activeTab === 'syntax' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
            }`}
          >
            Syntax
          </button>
        </nav>
      </div>

      <div className="p-4 max-h-64 overflow-y-auto">
        {activeTab === 'metrics' && (
          <div className="grid grid-cols-2 gap-2 text-sm">
            {metrics?.map((m, i) => (
              <div key={i} className="p-2 bg-gray-50 rounded">
                <code className="text-blue-600">TICKER.{m.name}</code>
                <div className="text-xs text-gray-500">{m.description}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'functions' && (
          <div className="space-y-2 text-sm">
            {functions?.map((f, i) => (
              <div key={i} className="p-2 bg-gray-50 rounded">
                <code className="text-purple-600">{f.name}()</code>
                <div className="text-xs text-gray-500">{f.description}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'syntax' && (
          <div className="text-sm space-y-3">
            <div>
              <div className="font-medium">Basic Reference</div>
              <code className="text-blue-600">TICKER.metric</code>
              <div className="text-xs text-gray-500">e.g., NVDA.price, AAPL.pe</div>
            </div>
            <div>
              <div className="font-medium">Arithmetic</div>
              <code className="text-blue-600">+ - * / ^</code>
              <div className="text-xs text-gray-500">e.g., NVDA.price / AAPL.price</div>
            </div>
            <div>
              <div className="font-medium">Functions</div>
              <code className="text-purple-600">func(TICKER.metric, args)</code>
              <div className="text-xs text-gray-500">e.g., rolling_avg(NVDA.price, 20)</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function FormulaPage() {
  const [formula, setFormula] = useState('');
  const [validation, setValidation] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [functions, setFunctions] = useState([]);
  const [loading, setLoading] = useState(false);

  // Fetch reference data
  useEffect(() => {
    const fetchRef = async () => {
      try {
        const [metricsRes, funcsRes] = await Promise.all([
          fetch(`${API_BASE}/formula/reference/metrics`),
          fetch(`${API_BASE}/formula/reference/functions`),
        ]);
        const metricsData = await metricsRes.json();
        const funcsData = await funcsRes.json();
        setMetrics(metricsData.metrics || []);
        setFunctions(funcsData.functions || []);
      } catch (err) {
        console.error('Failed to fetch reference data:', err);
      }
    };
    fetchRef();
  }, []);

  // Validate formula on change
  const validateFormula = useCallback(async (f) => {
    if (!f.trim()) {
      setValidation(null);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/formula/validate?formula=${encodeURIComponent(f)}`);
      const data = await res.json();
      setValidation(data);
    } catch (err) {
      console.error('Validation error:', err);
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => validateFormula(formula), 500);
    return () => clearTimeout(timeout);
  }, [formula, validateFormula]);

  // Evaluate formula
  const evaluateFormula = async () => {
    if (!formula || validation?.valid === false) return;

    setLoading(true);
    try {
      const res = await apiFetch(`/formula/evaluate`, { method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ formula, days: 252 }),
      });
      const data = await res.json();
      setChartData(data);
    } catch (err) {
      console.error('Evaluation error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Formula Builder | Finance Intelligence</title>
      </Head>

      <div className="research-dark min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Custom Formula Builder</h1>
            <p className="text-sm text-gray-500">Create custom financial metrics and visualizations</p>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
          {/* Presets */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm font-medium text-gray-700 mb-2">Quick Start</div>
            <PresetFormulas onSelect={setFormula} />
          </div>

          {/* Formula Input */}
          <FormulaInput
            value={formula}
            onChange={setFormula}
            validation={validation}
            onEvaluate={evaluateFormula}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart */}
            <div className="lg:col-span-2">
              {loading ? (
                <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                  Evaluating formula...
                </div>
              ) : (
                <ChartDisplay data={chartData} />
              )}
            </div>

            {/* Reference */}
            <div>
              <ReferencePanel metrics={metrics} functions={functions} />
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
