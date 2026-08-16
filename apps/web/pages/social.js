import { useState, useEffect } from 'react';
import Head from 'next/head';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function SocialPage() {
  const [trending, setTrending] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [whales, setWhales] = useState(null);
  const [momentum, setMomentum] = useState(null);
  const [institutional, setInstitutional] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrending();
  }, []);

  async function fetchTrending() {
    try {
      const res = await fetch(`${API_BASE}/social/reddit/trending`);
      const data = await res.json();
      setTrending(data.trending || []);
      if (data.trending?.length > 0) {
        selectTicker(data.trending[0].ticker);
      }
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function selectTicker(ticker) {
    setSelectedTicker(ticker);
    setLoading(true);
    try {
      const [sentRes, whaleRes, momRes, instRes] = await Promise.all([
        fetch(`${API_BASE}/social/reddit/sentiment?ticker=${ticker}`),
        fetch(`${API_BASE}/social/whales/flow/${ticker}`),
        fetch(`${API_BASE}/social/momentum/${ticker}`),
        fetch(`${API_BASE}/social/institutional/${ticker}`)
      ]);
      const sentData = await sentRes.json();
      const whaleData = await whaleRes.json();
      const momData = await momRes.json();
      const instData = await instRes.json();
      setSentiment(sentData);
      setWhales(whaleData);
      setMomentum(momData);
      setInstitutional(instData);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  const sentimentColors = {
    bullish: 'text-green-400',
    bearish: 'text-red-400',
    neutral: 'text-yellow-400'
  };

  const formatCurrency = (val) => {
    if (val >= 1000000000) return `$${(val / 1000000000).toFixed(1)}B`;
    if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
    return `$${val.toLocaleString()}`;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Social & Whale Tracking | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Social Sentiment & Whale Tracking</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Trending Tickers */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">🔥 Trending on Reddit</h2>
            <div className="space-y-2">
              {trending.map((item, i) => (
                <div
                  key={item.ticker}
                  onClick={() => selectTicker(item.ticker)}
                  className={`p-3 rounded-lg cursor-pointer transition ${
                    selectedTicker === item.ticker
                      ? 'bg-blue-900 border border-blue-600'
                      : 'bg-gray-700 hover:bg-gray-650'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">#{i + 1} {item.ticker}</span>
                    <span className={sentimentColors[item.sentiment] || 'text-gray-400'}>
                      {item.sentiment}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-400 mt-1">
                    <span>{item.mentions} mentions</span>
                    <span className={item.change_24h > 0 ? 'text-green-400' : 'text-red-400'}>
                      {item.change_24h > 0 ? '+' : ''}{item.change_24h}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Details */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="text-center py-10">Loading...</div>
          ) : selectedTicker ? (
            <>
              {/* Momentum Score */}
              {momentum && (
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">{selectedTicker} Social Momentum</h2>
                    <div className={`text-3xl font-bold ${
                      momentum.overall_score > 60 ? 'text-green-400' :
                      momentum.overall_score < 40 ? 'text-red-400' : 'text-yellow-400'
                    }`}>
                      {momentum.overall_score}/100
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    {['reddit', 'twitter', 'stocktwits'].map(platform => {
                      const data = momentum[platform];
                      return (
                        <div key={platform} className="bg-gray-700 p-4 rounded-lg">
                          <div className="text-gray-400 capitalize">{platform}</div>
                          <div className="text-2xl font-bold">{data?.score}</div>
                          <div className={`text-sm ${sentimentColors[data?.sentiment]}`}>
                            {data?.sentiment} • {data?.mentions_24h} mentions
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="text-center mt-4 text-gray-400">
                    Momentum Trend: <span className={
                      momentum.momentum_trend === 'accelerating' ? 'text-green-400' :
                      momentum.momentum_trend === 'decelerating' ? 'text-red-400' : 'text-yellow-400'
                    }>{momentum.momentum_trend}</span>
                  </div>
                </div>
              )}

              {/* Whale Flow & Institutional */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {/* Whale Flow */}
                {whales && (
                  <div className="bg-gray-800 rounded-lg p-4">
                    <h3 className="text-lg font-semibold mb-4">🐋 Whale Flow (30 Days)</h3>
                    <div className={`text-3xl font-bold mb-2 ${
                      whales.total_net_flow > 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {formatCurrency(Math.abs(whales.total_net_flow))}
                      <span className="text-sm ml-2">
                        {whales.total_net_flow > 0 ? 'Net Inflow' : 'Net Outflow'}
                      </span>
                    </div>
                    <div className={`inline-block px-3 py-1 rounded-full text-sm ${
                      whales.signal === 'accumulation' ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'
                    }`}>
                      {whales.signal?.toUpperCase()}
                    </div>
                  </div>
                )}

                {/* Institutional Ownership */}
                {institutional && (
                  <div className="bg-gray-800 rounded-lg p-4">
                    <h3 className="text-lg font-semibold mb-4">🏛️ Institutional Ownership</h3>
                    <div className="text-3xl font-bold mb-2">
                      {institutional.total_institutional}%
                      <span className={`text-sm ml-2 ${
                        institutional.qoq_change > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {institutional.qoq_change > 0 ? '+' : ''}{institutional.qoq_change}% QoQ
                      </span>
                    </div>
                    <div className="space-y-2 mt-4">
                      {institutional.top_holders?.slice(0, 3).map(holder => (
                        <div key={holder.name} className="flex justify-between text-sm">
                          <span>{holder.name}</span>
                          <span className="text-gray-400">{holder.percent}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Reddit Posts */}
              {sentiment && sentiment.posts && (
                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">Recent Reddit Posts</h3>
                  <div className="space-y-3">
                    {sentiment.posts.slice(0, 5).map(post => (
                      <div key={post.post_id} className="p-4 bg-gray-700 rounded-lg">
                        <div className="font-medium">{post.title}</div>
                        <div className="text-gray-400 text-sm mt-1 line-clamp-2">{post.content}</div>
                        <div className="flex gap-4 mt-2 text-sm text-gray-400">
                          <span>r/{post.subreddit}</span>
                          <span>⬆️ {post.score}</span>
                          <span>💬 {post.comments}</span>
                          <span className={sentimentColors[post.sentiment]}>
                            {post.sentiment} ({(post.sentiment_score * 100).toFixed(0)}%)
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  {sentiment.sentiment_summary && (
                    <div className="mt-4 p-4 bg-gray-700 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">Overall Sentiment</span>
                        <span className={`text-xl font-bold ${sentimentColors[sentiment.sentiment_summary.signal]}`}>
                          {sentiment.sentiment_summary.signal?.toUpperCase()} ({(sentiment.sentiment_summary.average_score * 100).toFixed(0)}%)
                        </span>
                      </div>
                      <div className="flex gap-4 mt-2 text-sm">
                        <span className="text-green-400">🟢 {sentiment.sentiment_summary.bullish_posts} bullish</span>
                        <span className="text-red-400">🔴 {sentiment.sentiment_summary.bearish_posts} bearish</span>
                        <span className="text-yellow-400">🟡 {sentiment.sentiment_summary.neutral_posts} neutral</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="text-center text-gray-400 py-10">
              Select a ticker to view social and whale data
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
