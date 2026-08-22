import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function NarrativeModelPage() {
  const [models, setModels] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [activeTab, setActiveTab] = useState('models');
  const [noData, setNoData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Training state
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [trainingJob, setTrainingJob] = useState(null);

  // Generation state
  const [ticker, setTicker] = useState('');
  const [reportType, setReportType] = useState('analysis');
  const [narrative, setNarrative] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      const [modelsRes, datasetsRes, perfRes] = await Promise.all([
        fetch(`${API_BASE}/narrative-model/models`),
        fetch(`${API_BASE}/narrative-model/datasets`),
        fetch(`${API_BASE}/narrative-model/performance`)
      ]);
      const modelsData = await modelsRes.json();
      if (isNoData(modelsData)) {
        setNoData(modelsData);
        setLoading(false);
        return;
      }
      const datasetsData = await datasetsRes.json();
      const perfData = await perfRes.json();
      setModels(modelsData.models || []);
      setDatasets(datasetsData.datasets || []);
      setPerformance(perfData);
      if (modelsData.recommended) setSelectedModel(modelsData.recommended);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function startTraining() {
    if (!selectedModel || !selectedDataset) return;
    try {
      const res = await fetch(
        `${API_BASE}/narrative-model/train?base_model=${selectedModel}&dataset_id=${selectedDataset}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setTrainingJob(data);
    } catch (err) {
      console.error('Error:', err);
    }
  }

  async function generateNarrative() {
    if (!ticker) return;
    setGenerating(true);
    try {
      const res = await fetch(
        `${API_BASE}/narrative-model/generate?ticker=${ticker}&report_type=${reportType}`,
        { method: 'POST' }
      );
      setNarrative(await res.json());
    } catch (err) {
      console.error('Error:', err);
    }
    setGenerating(false);
  }

  const tabs = [
    { id: 'models', label: 'Models' },
    { id: 'training', label: 'Training' },
    { id: 'generate', label: 'Generate' },
    { id: 'performance', label: 'Performance' }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Narrative Model | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Narrative Model Training & Deployment</h1>

      {noData ? (
        <NoDataCard {...noData} dataType="narrative_model" />
      ) : loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : (
        <>
          {/* Tabs */}
          <div className="flex gap-2 mb-6">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg ${
                  activeTab === tab.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Models Tab */}
          {activeTab === 'models' && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Available Models</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {models.map(model => (
                  <div key={model.id} className="p-4 bg-gray-700 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{model.name}</span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        model.status === 'deployed' ? 'bg-green-600' :
                        model.status === 'available' ? 'bg-blue-600' : 'bg-gray-600'
                      }`}>
                        {model.status}
                      </span>
                    </div>
                    <div className="text-gray-400 text-sm">
                      Size: {model.size} | Type: {model.type}
                    </div>
                  </div>
                ))}
              </div>

              <h2 className="text-xl font-semibold mt-8 mb-4">Training Datasets</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {datasets.map(ds => (
                  <div key={ds.id} className="p-4 bg-gray-700 rounded-lg flex justify-between items-center">
                    <div>
                      <div className="font-semibold">{ds.id}</div>
                      <div className="text-gray-400 text-sm">{ds.type}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-blue-400">{ds.samples.toLocaleString()}</div>
                      <div className="text-gray-400 text-sm">samples</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Training Tab */}
          {activeTab === 'training' && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Start Training Job</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-gray-400 mb-2">Base Model</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
                  >
                    <option value="">Select model...</option>
                    {models.filter(m => m.type === 'base').map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-gray-400 mb-2">Dataset</label>
                  <select
                    value={selectedDataset}
                    onChange={(e) => setSelectedDataset(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
                  >
                    <option value="">Select dataset...</option>
                    {datasets.map(ds => (
                      <option key={ds.id} value={ds.id}>{ds.id} ({ds.samples.toLocaleString()} samples)</option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                onClick={startTraining}
                disabled={!selectedModel || !selectedDataset}
                className="bg-green-600 hover:bg-green-500 px-6 py-3 rounded-lg font-semibold disabled:opacity-50"
              >
                Start Training (GPU Required)
              </button>

              {trainingJob && (
                <div className="mt-6 p-4 bg-gray-700 rounded-lg">
                  <h3 className="font-semibold mb-2">Training Job Started</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div><span className="text-gray-400">Job ID:</span> {trainingJob.job_id}</div>
                    <div><span className="text-gray-400">Status:</span> {trainingJob.status}</div>
                    <div><span className="text-gray-400">Base Model:</span> {trainingJob.base_model}</div>
                    <div><span className="text-gray-400">Est. Time:</span> {trainingJob.estimated_time}</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Generate Tab */}
          {activeTab === 'generate' && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Generate Narrative</h2>
              <div className="flex gap-4 mb-6">
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="Enter ticker (e.g., NVDA)"
                  className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
                />
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-3"
                >
                  <option value="analysis">Analysis</option>
                  <option value="summary">Summary</option>
                  <option value="risk">Risk Assessment</option>
                </select>
                <button
                  onClick={generateNarrative}
                  disabled={generating || !ticker}
                  className="bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg font-semibold disabled:opacity-50"
                >
                  {generating ? 'Generating...' : 'Generate'}
                </button>
              </div>

              {narrative && (
                <div className="p-6 bg-gray-700 rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <span className="text-2xl font-bold">{narrative.ticker}</span>
                      <span className="ml-3 px-2 py-1 bg-blue-600 rounded text-sm">{narrative.report_type}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-400">Confidence</div>
                      <div className="text-xl font-bold text-green-400">{(narrative.confidence * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                  <div className="prose prose-invert max-w-none">
                    <p className="text-lg leading-relaxed">{narrative.narrative}</p>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-600 text-sm text-gray-400">
                    Model: {narrative.model_version} | Generated: {new Date(narrative.generated_at).toLocaleString()}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Performance Tab */}
          {activeTab === 'performance' && performance && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Model Performance</h2>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-2xl font-bold text-blue-400">{performance.metrics.bleu_score}</div>
                  <div className="text-gray-400 text-sm">BLEU Score</div>
                </div>
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-2xl font-bold text-green-400">{performance.metrics.rouge_l}</div>
                  <div className="text-gray-400 text-sm">ROUGE-L</div>
                </div>
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-2xl font-bold text-purple-400">{performance.metrics.human_eval_score}</div>
                  <div className="text-gray-400 text-sm">Human Eval</div>
                </div>
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-400">{(performance.metrics.factual_accuracy * 100).toFixed(0)}%</div>
                  <div className="text-gray-400 text-sm">Factual Accuracy</div>
                </div>
                <div className="text-center p-4 bg-gray-700 rounded-lg">
                  <div className="text-2xl font-bold text-pink-400">{(performance.metrics.coherence * 100).toFixed(0)}%</div>
                  <div className="text-gray-400 text-sm">Coherence</div>
                </div>
              </div>

              <h3 className="text-lg font-semibold mb-4">Improvement vs Base Model</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-gray-700 rounded-lg">
                  <div className="text-xl font-bold text-green-400">{performance.comparison_to_base.improvement}</div>
                  <div className="text-gray-400 text-sm">Overall Improvement</div>
                </div>
                <div className="p-4 bg-gray-700 rounded-lg">
                  <div className="text-xl font-bold text-green-400">{performance.comparison_to_base.finance_terminology}</div>
                  <div className="text-gray-400 text-sm">Finance Terminology</div>
                </div>
                <div className="p-4 bg-gray-700 rounded-lg">
                  <div className="text-xl font-bold text-green-400">{performance.comparison_to_base.factual_grounding}</div>
                  <div className="text-gray-400 text-sm">Factual Grounding</div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
