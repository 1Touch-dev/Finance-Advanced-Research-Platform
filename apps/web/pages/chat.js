/**
 * RAG Chat Page
 * Wired to /chat/* API endpoints
 * Per-entity cited Q&A using intelligence report data
 */

import React, { useState, useRef, useEffect } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

export default function ChatPage() {
  const [reportId, setReportId] = useState('');
  const [entityName, setEntityName] = useState('');
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [messages, setMessages] = useState([]);
  const [summary, setSummary] = useState(null);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const askQuestion = async () => {
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }
    if (!reportId && !entityName.trim()) {
      setError('Report ID or entity name required');
      return;
    }

    const userMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion('');
    setLoading(true);
    setError(null);

    try {
      const payload = {
        question: question,
        mode: mode,
        history: messages,
      };
      if (reportId) payload.report_id = parseInt(reportId);
      if (entityName.trim()) payload.entity_name = entityName;

      const res = await apiFetch('/chat/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to get answer');
      }

      const data = await res.json();
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        context_used: data.context_used,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSummary = async () => {
    if (!reportId) {
      setError('Report ID required for summary');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/chat/summary/${reportId}`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to get summary');
      }
      const data = await res.json();
      setSummary(data.summary);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSummary(null);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  };

  return (
    <Layout>
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Research Chat</h1>
        <p className="text-gray-600 mb-6">
          Ask questions about intelligence reports with cited answers.
        </p>

        {/* Configuration */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Report ID</label>
              <input
                type="text"
                placeholder="Optional"
                value={reportId}
                onChange={(e) => setReportId(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Entity Name</label>
              <input
                type="text"
                placeholder="e.g., Apple Inc"
                value={entityName}
                onChange={(e) => setEntityName(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Search Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                <option value="hybrid">Hybrid</option>
                <option value="vector">Vector</option>
                <option value="keyword">Keyword</option>
              </select>
            </div>
            <div className="flex items-end gap-2">
              <button
                onClick={getSummary}
                disabled={loading || !reportId}
                className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded disabled:opacity-50"
              >
                Summary
              </button>
              <button
                onClick={clearChat}
                className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded"
              >
                Clear
              </button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div className="bg-blue-50 border border-blue-200 p-4 rounded mb-4">
            <h3 className="font-bold text-blue-700 mb-2">Report Summary</h3>
            <p className="text-gray-700 whitespace-pre-wrap">{summary}</p>
          </div>
        )}

        {/* Chat Messages */}
        <div className="bg-white rounded-lg shadow mb-4">
          <div className="h-96 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p>Start a conversation by asking a question about your research.</p>
                <p className="text-sm mt-2">Examples:</p>
                <ul className="text-sm mt-1 space-y-1">
                  <li>"What are the key risks mentioned in this report?"</li>
                  <li>"Summarize the competitive landscape"</li>
                  <li>"What are the main revenue drivers?"</li>
                </ul>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-3/4 rounded-lg px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-gray-300">
                          <p className="text-xs font-medium mb-1">Sources:</p>
                          <ul className="text-xs space-y-1">
                            {msg.sources.map((s, sidx) => (
                              <li key={sidx} className="text-gray-600">
                                [{sidx + 1}] {s.title || s.source || 'Unknown source'}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg px-4 py-2">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Input */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex gap-4">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question..."
              rows={2}
              className="flex-1 border rounded px-3 py-2 resize-none"
            />
            <button
              onClick={askQuestion}
              disabled={loading || !question.trim()}
              className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50 h-fit self-end"
            >
              {loading ? 'Thinking...' : 'Ask'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Press Enter to send. Shift+Enter for new line.
          </p>
        </div>
      </div>
    </Layout>
  );
}
