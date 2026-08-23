import { useState, useEffect } from 'react';
import Head from 'next/head';
import { apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PersonsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [news, setNews] = useState([]);
  const [trades, setTrades] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function searchPersons(query) {
    if (!query) return;
    try {
      const res = await apiFetch(`/persons/search?query=${encodeURIComponent(query)}`);
      const data = await res.json();
      setSearchResults(data.persons || []);
    } catch (err) {
      setError('Error:', err);
    }
  }

  async function selectPerson(personId) {
    setLoading(true);
    try {
      const [personRes, timelineRes, newsRes, tradesRes] = await Promise.all([
        apiFetch(`/persons/${personId}`),
        apiFetch(`/persons/${personId}/timeline-with-prices`),
        apiFetch(`/persons/${personId}/news`),
        apiFetch(`/persons/${personId}/trades`)
      ]);
      const personData = await personRes.json();
      const timelineData = await timelineRes.json();
      const newsData = await newsRes.json();
      const tradesData = await tradesRes.json();
      setSelectedPerson(personData);
      setTimeline(timelineData);
      setNews(newsData.news || []);
      setTrades(tradesData);
    } catch (err) {
      setError('Error:', err);
    }
    setLoading(false);
  }

  const eventTypeColors = {
    appointment: 'bg-blue-600',
    departure: 'bg-red-600',
    trade: 'bg-green-600',
    filing: 'bg-yellow-600',
    news: 'bg-purple-600',
    company_event: 'bg-pink-600'
  };

  const formatCurrency = (val) => val ? `$${(val / 1000000).toFixed(1)}M` : '-';

  // Default persons to show
  const defaultPersons = [
    { person_id: 'jensen_huang', name: 'Jensen Huang', title: 'CEO', company: 'NVIDIA' },
    { person_id: 'elon_musk', name: 'Elon Musk', title: 'CEO', company: 'Tesla' },
    { person_id: 'satya_nadella', name: 'Satya Nadella', title: 'CEO', company: 'Microsoft' },
    { person_id: 'tim_cook', name: 'Tim Cook', title: 'CEO', company: 'Apple' }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">

      <Head>
        <title>Executive Timelines | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Executive Timelines</h1>

      {/* Search */}
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search executives by name or company..."
          className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-2"
          onKeyPress={(e) => e.key === 'Enter' && searchPersons(searchQuery)}
        />
        <button
          onClick={() => searchPersons(searchQuery)}
          className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg"
        >
          Search
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Person List */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">
              {searchResults.length > 0 ? 'Search Results' : 'Featured Executives'}
            </h2>
            <div className="space-y-2">
              {(searchResults.length > 0 ? searchResults : defaultPersons).map(person => (
                <div
                  key={person.person_id}
                  onClick={() => selectPerson(person.person_id)}
                  className={`p-3 rounded-lg cursor-pointer transition ${
                    selectedPerson?.person_id === person.person_id
                      ? 'bg-blue-900 border border-blue-600'
                      : 'bg-gray-700 hover:bg-gray-650'
                  }`}
                >
                  <div className="font-medium">{person.name}</div>
                  <div className="text-gray-400 text-sm">{person.title} at {person.company}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Timeline & Details */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="text-center py-10">Loading...</div>
          ) : selectedPerson ? (
            <>
              {/* Person Header */}
              <div className="bg-gray-800 rounded-lg p-6 mb-6">
                <h2 className="text-2xl font-bold">{selectedPerson.name}</h2>
                <div className="text-gray-400">{selectedPerson.title} at {selectedPerson.company}</div>
                {selectedPerson.ticker && (
                  <span className="inline-block mt-2 px-3 py-1 bg-blue-900 rounded-full text-sm">
                    ${selectedPerson.ticker}
                  </span>
                )}
              </div>

              {/* Trades Summary */}
              {trades && trades.trades?.length > 0 && (
                <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 mb-6">
                  <h3 className="text-lg font-semibold text-green-400 mb-2">Insider Trades</h3>
                  <div className="flex gap-4">
                    <div>
                      <div className="text-gray-400 text-sm">Total Transactions</div>
                      <div className="text-xl font-bold">{trades.trade_count}</div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-sm">Total Value</div>
                      <div className="text-xl font-bold">{formatCurrency(trades.total_value)}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Timeline Events */}
              <div className="bg-gray-800 rounded-lg p-4 mb-6">
                <h3 className="text-lg font-semibold mb-4">Timeline</h3>
                <div className="space-y-4">
                  {timeline?.events?.map(event => (
                    <div key={event.event_id} className="flex gap-4 p-4 bg-gray-700 rounded-lg">
                      <div className={`w-3 h-3 rounded-full mt-1.5 ${eventTypeColors[event.event_type] || 'bg-gray-500'}`} />
                      <div className="flex-1">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="font-semibold">{event.title}</div>
                            <div className="text-gray-400 text-sm">{event.description}</div>
                          </div>
                          <div className="text-gray-400 text-sm whitespace-nowrap">{event.date}</div>
                        </div>
                        <div className="flex gap-2 mt-2">
                          <span className={`px-2 py-0.5 rounded text-xs ${eventTypeColors[event.event_type] || 'bg-gray-600'}`}>
                            {event.event_type.replace('_', ' ')}
                          </span>
                          {event.value && (
                            <span className="px-2 py-0.5 bg-green-800 rounded text-xs">
                              {formatCurrency(event.value)}
                            </span>
                          )}
                          {event.source && (
                            <span className="text-gray-500 text-xs">via {event.source}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* News */}
              {news.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">Recent News</h3>
                  <div className="space-y-3">
                    {news.map((item, i) => (
                      <div key={i} className="p-3 bg-gray-700 rounded-lg">
                        <div className="font-medium">{item.headline}</div>
                        <div className="flex gap-2 mt-1 text-sm text-gray-400">
                          <span>{item.source}</span>
                          <span>•</span>
                          <span>{item.date}</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            item.sentiment === 'positive' ? 'bg-green-800' :
                            item.sentiment === 'negative' ? 'bg-red-800' : 'bg-gray-600'
                          }`}>
                            {item.sentiment}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center text-gray-400 py-10">
              Select an executive to view their timeline
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
