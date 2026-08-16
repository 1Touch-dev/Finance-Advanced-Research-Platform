/**
 * Price Alerts Page (Band C #35)
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const USER_ID = 'demo_user';

export default function PriceAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [alertTypes, setAlertTypes] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ticker: '', alertType: 'price_above', targetValue: '' });

  useEffect(() => {
    fetchAlerts();
    fetchAlertTypes();
    fetchNotifications();
    fetchStats();
  }, []);

  const fetchAlerts = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/alerts?user_id=${USER_ID}`);
    if (res.ok) {
      const data = await res.json();
      setAlerts(data.alerts || []);
    }
    setLoading(false);
  };

  const fetchAlertTypes = async () => {
    const res = await fetch(`${API_BASE}/alerts/types`);
    if (res.ok) {
      const data = await res.json();
      setAlertTypes(data.alert_types || []);
    }
  };

  const fetchNotifications = async () => {
    const res = await fetch(`${API_BASE}/alerts/notifications?user_id=${USER_ID}&limit=10`);
    if (res.ok) {
      const data = await res.json();
      setNotifications(data.notifications || []);
    }
  };

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/alerts/stats?user_id=${USER_ID}`);
    if (res.ok) setStats(await res.json());
  };

  const createAlert = async () => {
    const params = new URLSearchParams({
      user_id: USER_ID,
      ticker: form.ticker,
      alert_type: form.alertType,
      target_value: form.targetValue,
    });
    const res = await fetch(`${API_BASE}/alerts?${params}`, { method: 'POST' });
    if (res.ok) {
      setShowCreate(false);
      setForm({ ticker: '', alertType: 'price_above', targetValue: '' });
      fetchAlerts();
      fetchStats();
    }
  };

  const deleteAlert = async (alertId) => {
    if (!confirm('Delete this alert?')) return;
    const res = await fetch(`${API_BASE}/alerts/${alertId}?user_id=${USER_ID}`, { method: 'DELETE' });
    if (res.ok) {
      fetchAlerts();
      fetchStats();
    }
  };

  return (
    <Layout>
      <div className="p-6 max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Price Alerts</h1>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            + New Alert
          </button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Active Alerts</div>
              <div className="text-2xl font-bold">{stats.active}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Triggered Today</div>
              <div className="text-2xl font-bold text-green-600">{stats.triggered_today}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Triggered</div>
              <div className="text-2xl font-bold">{stats.triggered_total}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Unread Notifications</div>
              <div className="text-2xl font-bold text-orange-600">{stats.unread_notifications}</div>
            </div>
          </div>
        )}

        {/* Create Form */}
        {showCreate && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="font-semibold mb-4">Create Alert</h2>
            <div className="grid grid-cols-4 gap-4">
              <input
                type="text"
                placeholder="Ticker (e.g., AAPL)"
                value={form.ticker}
                onChange={(e) => setForm({ ...form, ticker: e.target.value.toUpperCase() })}
                className="border rounded px-3 py-2"
              />
              <select
                value={form.alertType}
                onChange={(e) => setForm({ ...form, alertType: e.target.value })}
                className="border rounded px-3 py-2"
              >
                {alertTypes.map((t) => (
                  <option key={t.type} value={t.type}>{t.name}</option>
                ))}
              </select>
              <input
                type="number"
                placeholder="Target Value"
                value={form.targetValue}
                onChange={(e) => setForm({ ...form, targetValue: e.target.value })}
                className="border rounded px-3 py-2"
              />
              <button onClick={createAlert} className="bg-green-600 text-white rounded hover:bg-green-700">
                Create
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-6">
          {/* Alerts List */}
          <div className="col-span-2 bg-white rounded-lg shadow">
            <div className="p-4 border-b font-semibold">Active Alerts ({alerts.length})</div>
            <div className="divide-y max-h-96 overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="p-4 text-gray-500">No alerts yet</div>
              ) : (
                alerts.map((alert) => (
                  <div key={alert.alert_id} className="p-4 flex justify-between items-center hover:bg-gray-50">
                    <div>
                      <div className="font-medium">{alert.ticker}</div>
                      <div className="text-sm text-gray-600">
                        {alert.alert_type.replace('_', ' ')} ${alert.target_value}
                      </div>
                      <div className="text-xs text-gray-400">
                        Current: ${alert.current_value?.toFixed(2)}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-1 text-xs rounded ${
                        alert.status === 'active' ? 'bg-green-100 text-green-700' : 
                        alert.status === 'triggered' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100'
                      }`}>
                        {alert.status}
                      </span>
                      <button
                        onClick={() => deleteAlert(alert.alert_id)}
                        className="text-red-500 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b font-semibold">Recent Notifications</div>
            <div className="divide-y max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-4 text-gray-500">No notifications</div>
              ) : (
                notifications.map((notif) => (
                  <div key={notif.notification_id} className={`p-3 text-sm ${notif.read ? 'bg-white' : 'bg-blue-50'}`}>
                    <div className="font-medium">{notif.ticker}</div>
                    <div className="text-gray-600">{notif.message}</div>
                    <div className="text-xs text-gray-400 mt-1">{new Date(notif.sent_at).toLocaleString()}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
