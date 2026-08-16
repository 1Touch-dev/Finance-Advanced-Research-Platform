import { useState, useEffect } from 'react';
import Head from 'next/head';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PWASettingsPage() {
  const [preferences, setPreferences] = useState(null);
  const [compatibility, setCompatibility] = useState(null);
  const [installPrompt, setInstallPrompt] = useState(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pushSupported, setPushSupported] = useState(false);

  useEffect(() => {
    fetchData();
    checkInstallState();
    checkPushSupport();
  }, []);

  async function fetchData() {
    try {
      const [prefsRes, compatRes, promptRes] = await Promise.all([
        fetch(API_BASE + '/pwa/notifications/preferences?user_id=user_1'),
        fetch(API_BASE + '/pwa/compatibility'),
        fetch(API_BASE + '/pwa/install-prompt')
      ]);
      const prefsData = await prefsRes.json();
      const compatData = await compatRes.json();
      const promptData = await promptRes.json();
      setPreferences(prefsData.preferences || {});
      setCompatibility(compatData);
      setInstallPrompt(promptData);
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  function checkInstallState() {
    if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
    }
  }

  function checkPushSupport() {
    setPushSupported('Notification' in window && 'serviceWorker' in navigator);
  }

  async function updatePreference(key, value) {
    const newPrefs = { ...preferences, [key]: value };
    setPreferences(newPrefs);
    try {
      await fetch(API_BASE + '/pwa/notifications/preferences?user_id=user_1', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPrefs)
      });
    } catch (err) {
      console.error('Error:', err);
    }
  }

  async function requestNotificationPermission() {
    if (!('Notification' in window)) {
      alert('Notifications not supported');
      return;
    }
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      alert('Notifications enabled!');
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>PWA Settings | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">App Settings</h1>

      {loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Install Status */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Installation</h2>
            <div className={'p-4 rounded-lg mb-4 ' + (isInstalled ? 'bg-green-900' : 'bg-blue-900')}>
              <div className="flex items-center gap-3">
                <span className="text-2xl">{isInstalled ? '✓' : '📱'}</span>
                <div>
                  <div className="font-semibold">
                    {isInstalled ? 'App Installed' : 'Install App'}
                  </div>
                  <div className="text-sm text-gray-400">
                    {isInstalled 
                      ? 'Running in standalone mode' 
                      : 'Add to home screen for quick access'}
                  </div>
                </div>
              </div>
            </div>
            {!isInstalled && (
              <p className="text-sm text-gray-400">
                Use your browser menu to &quot;Add to Home Screen&quot; or &quot;Install App&quot;
              </p>
            )}
          </div>

          {/* Push Notifications */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Push Notifications</h2>
            {pushSupported ? (
              <>
                <button
                  onClick={requestNotificationPermission}
                  className="w-full bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg mb-4"
                >
                  Enable Notifications
                </button>
                <p className="text-sm text-gray-400">
                  Get real-time alerts for price movements, earnings, and more
                </p>
              </>
            ) : (
              <p className="text-yellow-400">
                Push notifications not supported in this browser
              </p>
            )}
          </div>

          {/* Notification Preferences */}
          {preferences && (
            <div className="bg-gray-800 rounded-lg p-6 lg:col-span-2">
              <h2 className="text-xl font-semibold mb-4">Notification Preferences</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(preferences).map(([key, value]) => (
                  <label key={key} className="flex items-center gap-3 p-3 bg-gray-700 rounded-lg cursor-pointer">
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={(e) => updatePreference(key, e.target.checked)}
                      className="w-5 h-5 rounded"
                    />
                    <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Compatibility */}
          {compatibility && (
            <div className="bg-gray-800 rounded-lg p-6 lg:col-span-2">
              <h2 className="text-xl font-semibold mb-4">Feature Compatibility</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(compatibility.features || {}).map(([feature, supported]) => (
                  <div key={feature} className="flex items-center gap-2">
                    <span className={supported ? 'text-green-400' : 'text-red-400'}>
                      {supported ? '✓' : '✗'}
                    </span>
                    <span className="capitalize">{feature.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Offline Info */}
          <div className="bg-gray-800 rounded-lg p-6 lg:col-span-2">
            <h2 className="text-xl font-semibold mb-4">Offline Mode</h2>
            <p className="text-gray-400 mb-4">
              When offline, you can still view your cached portfolio, watchlist, and recent data.
            </p>
            <div className="flex gap-4">
              <div className="flex-1 p-4 bg-gray-700 rounded-lg">
                <div className="text-lg font-semibold">Cached Data</div>
                <div className="text-gray-400 text-sm">Portfolio, Watchlist, Alerts</div>
              </div>
              <div className="flex-1 p-4 bg-gray-700 rounded-lg">
                <div className="text-lg font-semibold">Auto Sync</div>
                <div className="text-gray-400 text-sm">Changes sync when back online</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
