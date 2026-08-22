import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PWAAdvancedPage() {
  const [activeTab, setActiveTab] = useState('offline');
  const [loading, setLoading] = useState(false);
  const [noData, setNoData] = useState(null);
  const userId = 'demo_user';

  // E2: Offline Caching State
  const [offlineConfig, setOfflineConfig] = useState(null);
  const [swConfig, setSwConfig] = useState(null);
  const [cachedRoutes, setCachedRoutes] = useState([]);
  const [cacheRoute, setCacheRoute] = useState('/portfolio');

  // E3: WebAuthn State
  const [biometricStatus, setBiometricStatus] = useState(null);
  const [registrationChallenge, setRegistrationChallenge] = useState(null);
  const [loginChallenge, setLoginChallenge] = useState(null);
  const [authMessage, setAuthMessage] = useState('');

  // E5: Screen Sharing State
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [sessionName, setSessionName] = useState('');
  const [joinSessionId, setJoinSessionId] = useState('');

  useEffect(() => {
    fetchOfflineData();
    fetchBiometricStatus();
    fetchActiveSessions();
  }, []);

  // E2: Offline Caching Functions
  async function fetchOfflineData() {
    try {
      const [configRes, swRes, routesRes] = await Promise.all([
        fetch(`${API_BASE}/pwa-advanced/offline/config`),
        fetch(`${API_BASE}/pwa-advanced/offline/sw-config`),
        fetch(`${API_BASE}/pwa-advanced/offline/cached?user_id=${userId}`)
      ]);
      const configData = await configRes.json();
      if (isNoData(configData)) { setNoData(configData); return; }
      setOfflineConfig(configData);
      setSwConfig(await swRes.json());
      const routesData = await routesRes.json();
      setCachedRoutes(routesData.cached_routes || []);
    } catch (err) {
      console.error('Error fetching offline data:', err);
    }
  }

  async function addCachedRoute() {
    if (!cacheRoute) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/pwa-advanced/offline/cache?user_id=${userId}&route=${encodeURIComponent(cacheRoute)}`, {
        method: 'POST'
      });
      await fetchOfflineData();
      setCacheRoute('');
    } catch (err) {
      console.error('Error caching route:', err);
    }
    setLoading(false);
  }

  async function clearAllCache() {
    if (!confirm('Clear all cached routes?')) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/pwa-advanced/offline/cache?user_id=${userId}`, { method: 'DELETE' });
      await fetchOfflineData();
    } catch (err) {
      console.error('Error clearing cache:', err);
    }
    setLoading(false);
  }

  // E3: WebAuthn Functions
  async function fetchBiometricStatus() {
    try {
      const res = await fetch(`${API_BASE}/pwa-advanced/biometric/status?user_id=${userId}`);
      setBiometricStatus(await res.json());
    } catch (err) {
      console.error('Error fetching biometric status:', err);
    }
  }

  async function startRegistration() {
    setLoading(true);
    setAuthMessage('');
    try {
      const res = await fetch(`${API_BASE}/pwa-advanced/biometric/register/start?user_id=${userId}&username=demo_user`, {
        method: 'POST'
      });
      const data = await res.json();
      setRegistrationChallenge(data);
      setAuthMessage('Registration challenge created. Click "Complete Registration" to simulate biometric enrollment.');
    } catch (err) {
      setAuthMessage('Error starting registration');
    }
    setLoading(false);
  }

  async function completeRegistration() {
    if (!registrationChallenge) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/pwa-advanced/biometric/register/complete?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credential_id: 'simulated_cred_' + Date.now(),
          public_key: 'simulated_public_key_' + Date.now()
        })
      });
      const data = await res.json();
      if (data.biometric_enabled) {
        setAuthMessage('Biometric registration successful!');
        setRegistrationChallenge(null);
        await fetchBiometricStatus();
      }
    } catch (err) {
      setAuthMessage('Error completing registration');
    }
    setLoading(false);
  }

  async function startLogin() {
    setLoading(true);
    setAuthMessage('');
    try {
      const res = await fetch(`${API_BASE}/pwa-advanced/biometric/login/start?user_id=${userId}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.error) {
        setAuthMessage(data.error);
      } else {
        setLoginChallenge(data);
        setAuthMessage('Login challenge created. Click "Verify Login" to authenticate.');
      }
    } catch (err) {
      setAuthMessage('Error starting login');
    }
    setLoading(false);
  }

  async function verifyLogin() {
    if (!loginChallenge) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/pwa-advanced/biometric/login/verify?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credential_id: loginChallenge.allowCredentials[0].id,
          signature: 'simulated_signature_' + Date.now()
        })
      });
      const data = await res.json();
      if (data.authenticated) {
        setAuthMessage('Login successful! Authenticated via biometrics.');
        setLoginChallenge(null);
      } else {
        setAuthMessage(data.error || 'Authentication failed');
      }
    } catch (err) {
      setAuthMessage('Error verifying login');
    }
    setLoading(false);
  }

  // E5: Screen Sharing Functions
  async function fetchActiveSessions() {
    try {
      const res = await fetch(`${API_BASE}/pwa-advanced/screen/active?user_id=${userId}`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('Error fetching sessions:', err);
    }
  }

  async function createSession() {
    setLoading(true);
    try {
      const url = sessionName
        ? `${API_BASE}/pwa-advanced/screen/create?user_id=${userId}&session_name=${encodeURIComponent(sessionName)}`
        : `${API_BASE}/pwa-advanced/screen/create?user_id=${userId}`;
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      setCurrentSession(data);
      setSessionName('');
      await fetchActiveSessions();
    } catch (err) {
      console.error('Error creating session:', err);
    }
    setLoading(false);
  }

  async function joinSession() {
    if (!joinSessionId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/pwa-advanced/screen/${joinSessionId}/join?user_id=${userId}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        setCurrentSession(data);
        setJoinSessionId('');
        await fetchActiveSessions();
      }
    } catch (err) {
      console.error('Error joining session:', err);
    }
    setLoading(false);
  }

  async function leaveSession(sessionId) {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/pwa-advanced/screen/${sessionId}/leave?user_id=${userId}`, {
        method: 'POST'
      });
      setCurrentSession(null);
      await fetchActiveSessions();
    } catch (err) {
      console.error('Error leaving session:', err);
    }
    setLoading(false);
  }

  async function endSession(sessionId) {
    if (!confirm('End this screen sharing session?')) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/pwa-advanced/screen/${sessionId}/end?user_id=${userId}`, {
        method: 'POST'
      });
      setCurrentSession(null);
      await fetchActiveSessions();
    } catch (err) {
      console.error('Error ending session:', err);
    }
    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>PWA Advanced | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">PWA Advanced Features</h1>

      {noData ? (
        <NoDataCard {...noData} />
      ) : (
      <>
      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-gray-700 pb-4">
        <button
          onClick={() => setActiveTab('offline')}
          className={`px-4 py-2 rounded-lg ${activeTab === 'offline' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
        >
          E2: Offline Caching
        </button>
        <button
          onClick={() => setActiveTab('biometric')}
          className={`px-4 py-2 rounded-lg ${activeTab === 'biometric' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
        >
          E3: Biometric Auth
        </button>
        <button
          onClick={() => setActiveTab('screen')}
          className={`px-4 py-2 rounded-lg ${activeTab === 'screen' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
        >
          E5: Screen Sharing
        </button>
      </div>

      {/* E2: Offline Caching Tab */}
      {activeTab === 'offline' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Config */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Offline Configuration</h2>
            {offlineConfig && (
              <div className="space-y-4">
                <div>
                  <span className="text-gray-400">Cache Version:</span>
                  <span className="ml-2 font-mono">{offlineConfig.cache_version}</span>
                </div>
                <div>
                  <span className="text-gray-400">Max Cache Size:</span>
                  <span className="ml-2">{offlineConfig.max_cache_size_mb} MB</span>
                </div>
                <div>
                  <h3 className="text-gray-400 mb-2">Caching Strategies:</h3>
                  <div className="space-y-2">
                    {Object.entries(offlineConfig.strategies || {}).map(([key, value]) => (
                      <div key={key} className="flex justify-between bg-gray-700 p-2 rounded">
                        <span>{key}</span>
                        <span className="text-blue-400">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-gray-400 mb-2">Cacheable Routes:</h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {(offlineConfig.cacheable_routes || []).map((route, idx) => (
                      <div key={idx} className="bg-gray-700 p-2 rounded text-sm">
                        <div className="font-mono">{route.path}</div>
                        <div className="text-gray-400 text-xs">
                          {route.strategy} | TTL: {route.ttl}s
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Service Worker */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Service Worker Config</h2>
            {swConfig && (
              <div className="space-y-4">
                <div>
                  <span className="text-gray-400">SW Version:</span>
                  <span className="ml-2 font-mono">{swConfig.sw_version}</span>
                </div>
                <div className="flex gap-4">
                  <div className={`px-3 py-1 rounded text-sm ${swConfig.skip_waiting ? 'bg-green-600' : 'bg-gray-600'}`}>
                    Skip Waiting: {swConfig.skip_waiting ? 'On' : 'Off'}
                  </div>
                  <div className={`px-3 py-1 rounded text-sm ${swConfig.clients_claim ? 'bg-green-600' : 'bg-gray-600'}`}>
                    Clients Claim: {swConfig.clients_claim ? 'On' : 'Off'}
                  </div>
                </div>
                <div>
                  <h3 className="text-gray-400 mb-2">Precache URLs:</h3>
                  <div className="flex flex-wrap gap-2">
                    {(swConfig.precache_urls || []).map((url, idx) => (
                      <span key={idx} className="bg-gray-700 px-2 py-1 rounded text-sm font-mono">{url}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* User Cached Routes */}
          <div className="bg-gray-800 rounded-lg p-6 lg:col-span-2">
            <h2 className="text-xl font-semibold mb-4">Your Cached Routes</h2>
            <div className="flex gap-4 mb-4">
              <input
                type="text"
                value={cacheRoute}
                onChange={(e) => setCacheRoute(e.target.value)}
                placeholder="/route/to/cache"
                className="flex-1 bg-gray-700 rounded-lg px-4 py-2"
              />
              <button
                onClick={addCachedRoute}
                disabled={loading || !cacheRoute}
                className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg disabled:opacity-50"
              >
                Cache Route
              </button>
              <button
                onClick={clearAllCache}
                disabled={loading}
                className="bg-red-600 hover:bg-red-500 px-6 py-2 rounded-lg disabled:opacity-50"
              >
                Clear All
              </button>
            </div>
            {cachedRoutes.length === 0 ? (
              <p className="text-gray-400">No routes cached yet</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {cachedRoutes.map((route, idx) => (
                  <div key={idx} className="bg-gray-700 p-3 rounded-lg">
                    <div className="font-mono text-blue-400">{route.route}</div>
                    <div className="text-gray-400 text-xs mt-1">Cached: {route.cached_at}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* E3: Biometric Auth Tab */}
      {activeTab === 'biometric' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Status */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Biometric Status</h2>
            {biometricStatus && (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className={`w-4 h-4 rounded-full ${biometricStatus.biometric_enabled ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="text-lg">
                    {biometricStatus.biometric_enabled ? 'Biometrics Enabled' : 'Biometrics Not Set Up'}
                  </span>
                </div>
                {biometricStatus.biometric_enabled && (
                  <>
                    <div>
                      <span className="text-gray-400">Registered:</span>
                      <span className="ml-2">{biometricStatus.registered_at}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Last Used:</span>
                      <span className="ml-2">{biometricStatus.last_used || 'Never'}</span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Registration */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Register Biometrics</h2>
            <p className="text-gray-400 mb-4">
              Set up fingerprint or Face ID for quick, secure login.
            </p>
            <div className="flex gap-4">
              <button
                onClick={startRegistration}
                disabled={loading || biometricStatus?.biometric_enabled}
                className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg disabled:opacity-50"
              >
                Start Registration
              </button>
              {registrationChallenge && (
                <button
                  onClick={completeRegistration}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-500 px-6 py-2 rounded-lg disabled:opacity-50"
                >
                  Complete Registration
                </button>
              )}
            </div>
          </div>

          {/* Login */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Biometric Login</h2>
            <p className="text-gray-400 mb-4">
              Authenticate using your registered biometric credentials.
            </p>
            <div className="flex gap-4">
              <button
                onClick={startLogin}
                disabled={loading || !biometricStatus?.biometric_enabled}
                className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg disabled:opacity-50"
              >
                Start Login
              </button>
              {loginChallenge && (
                <button
                  onClick={verifyLogin}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-500 px-6 py-2 rounded-lg disabled:opacity-50"
                >
                  Verify Login
                </button>
              )}
            </div>
          </div>

          {/* Message */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Authentication Status</h2>
            {authMessage ? (
              <div className={`p-4 rounded-lg ${authMessage.includes('successful') ? 'bg-green-900' : 'bg-gray-700'}`}>
                {authMessage}
              </div>
            ) : (
              <p className="text-gray-400">No recent authentication activity</p>
            )}
          </div>
        </div>
      )}

      {/* E5: Screen Sharing Tab */}
      {activeTab === 'screen' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Create Session */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Create Screen Sharing Session</h2>
            <div className="space-y-4">
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="Session name (optional)"
                className="w-full bg-gray-700 rounded-lg px-4 py-2"
              />
              <button
                onClick={createSession}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg disabled:opacity-50"
              >
                Create Session
              </button>
            </div>
          </div>

          {/* Join Session */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Join Screen Sharing Session</h2>
            <div className="space-y-4">
              <input
                type="text"
                value={joinSessionId}
                onChange={(e) => setJoinSessionId(e.target.value)}
                placeholder="Enter Session ID"
                className="w-full bg-gray-700 rounded-lg px-4 py-2"
              />
              <button
                onClick={joinSession}
                disabled={loading || !joinSessionId}
                className="w-full bg-green-600 hover:bg-green-500 px-6 py-3 rounded-lg disabled:opacity-50"
              >
                Join Session
              </button>
            </div>
          </div>

          {/* Current Session */}
          {currentSession && (
            <div className="bg-gray-800 rounded-lg p-6 lg:col-span-2">
              <h2 className="text-xl font-semibold mb-4">Current Session</h2>
              <div className="bg-gray-700 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <span className="text-gray-400">Session ID:</span>
                    <span className="ml-2 font-mono">{currentSession.session_id}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Status:</span>
                    <span className={`ml-2 px-2 py-0.5 rounded text-sm ${
                      currentSession.status === 'active' ? 'bg-green-600' : 'bg-yellow-600'
                    }`}>
                      {currentSession.status}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Host:</span>
                    <span className="ml-2">{currentSession.host_user_id || currentSession.host}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Participants:</span>
                    <span className="ml-2">{(currentSession.participants || []).length}</span>
                  </div>
                </div>
                <div className="mb-4">
                  <span className="text-gray-400">ICE Servers:</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {(currentSession.ice_servers || []).map((server, idx) => (
                      <span key={idx} className="bg-gray-600 px-2 py-1 rounded text-xs font-mono">{server.urls}</span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-4">
                  <button
                    onClick={() => leaveSession(currentSession.session_id)}
                    disabled={loading}
                    className="bg-yellow-600 hover:bg-yellow-500 px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    Leave Session
                  </button>
                  {currentSession.host_user_id === userId && (
                    <button
                      onClick={() => endSession(currentSession.session_id)}
                      disabled={loading}
                      className="bg-red-600 hover:bg-red-500 px-4 py-2 rounded-lg disabled:opacity-50"
                    >
                      End Session
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Active Sessions */}
          <div className="bg-gray-800 rounded-lg p-6 lg:col-span-2">
            <h2 className="text-xl font-semibold mb-4">Your Active Sessions ({sessions.length})</h2>
            {sessions.length === 0 ? (
              <p className="text-gray-400">No active sessions</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sessions.map(session => (
                  <div key={session.session_id} className="bg-gray-700 p-4 rounded-lg">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-semibold">{session.session_name}</div>
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        session.status === 'active' ? 'bg-green-600' : 'bg-yellow-600'
                      }`}>
                        {session.status}
                      </span>
                    </div>
                    <div className="text-gray-400 text-sm">ID: {session.session_id}</div>
                    <div className="text-gray-400 text-sm">
                      {session.participants?.length || 0} participant(s)
                    </div>
                    <div className="text-gray-500 text-xs mt-2">Created: {session.created_at}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      </>
      )}
    </div>
  );
}
