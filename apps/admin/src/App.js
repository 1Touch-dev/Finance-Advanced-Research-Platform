import React, { useEffect, useState } from 'react';
import './App.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:3001';
const WEB = process.env.REACT_APP_WEB_URL || 'http://localhost:3003';

function App() {
  const [health, setHealth] = useState(null);
  const [sourceHealth, setSourceHealth] = useState(null);
  const [runs, setRuns] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`${API}/health`).then((r) => r.json()),
      fetch(`${API}/sources/health`).then((r) => r.json()),
      fetch(`${API}/sources/runs?limit=20`).then((r) => r.json()),
    ])
      .then(([h, sh, r]) => {
        if (!cancelled) {
          setHealth(h);
          setSourceHealth(sh);
          setRuns(Array.isArray(r) ? r : []);
        }
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e.message || e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brandMark">EI</span>
          <span className="brandText">Admin</span>
        </div>
        <nav className="sideNav">
          <span className="navLabel">Apps</span>
          <a href={WEB} target="_blank" rel="noreferrer">
            Open web app
          </a>
          <a href={`${API}/docs`} target="_blank" rel="noreferrer">
            API docs (Swagger)
          </a>
          <span className="navLabel">Operations</span>
          <a href={`${API}/sources/health`} target="_blank" rel="noreferrer">
            Source health API
          </a>
        </nav>
      </aside>
      <div className="mainCol">
        <header className="top">
          <h1>Operations Dashboard</h1>
          <p className="muted">Source health, connector runs, and platform status.</p>
        </header>
        <section className="cards">
          <div className="card">
            <h2>API status</h2>
            {health && (
              <p className="statusOk">
                <span className="dot" /> {JSON.stringify(health)}
              </p>
            )}
            {err && <p className="statusErr">Unreachable: {err}</p>}
            {!health && !err && <p className="muted">Checking…</p>}
            <p className="hint">Base URL: {API}</p>
          </div>
          <div className="card">
            <h2>Source registry</h2>
            {sourceHealth && (
              <>
                <p>Sources: {sourceHealth.sources} · Runs: {sourceHealth.runs}</p>
                <p>Success rate: {((sourceHealth.success_rate || 0) * 100).toFixed(1)}%</p>
                <p>Errors: {sourceHealth.errors} · DLQ: {sourceHealth.dlq}</p>
              </>
            )}
          </div>
        </section>
        {sourceHealth?.per_source?.length > 0 && (
          <section className="cards">
            <div className="card" style={{ gridColumn: '1 / -1' }}>
              <h2>Per-source health</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                <thead>
                  <tr>
                    <th align="left">ID</th>
                    <th align="left">Name</th>
                    <th align="left">Kind</th>
                    <th align="left">Last status</th>
                    <th align="left">Records</th>
                    <th align="left">Last finished</th>
                  </tr>
                </thead>
                <tbody>
                  {sourceHealth.per_source.map((s) => (
                    <tr key={s.id}>
                      <td>{s.id}</td>
                      <td>{s.name}</td>
                      <td>{s.kind}</td>
                      <td>{s.last_status}</td>
                      <td>{s.records ?? s.last_metrics?.seen ?? '—'}</td>
                      <td>{s.last_finished || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
        {runs.length > 0 && (
          <section className="cards">
            <div className="card" style={{ gridColumn: '1 / -1' }}>
              <h2>Recent connector runs</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                <thead>
                  <tr>
                    <th align="left">Run ID</th>
                    <th align="left">Source</th>
                    <th align="left">Status</th>
                    <th align="left">Metrics</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td>{r.id}</td>
                      <td>{r.source_id}</td>
                      <td>{r.status}</td>
                      <td>{JSON.stringify(r.metrics || {})}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

export default App;
