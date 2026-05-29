import React, { useEffect, useState } from 'react';
import './App.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:3001';

function App() {
  const [health, setHealth] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled) setHealth(d);
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
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">
            Open web app
          </a>
          <a href={`${API}/docs`} target="_blank" rel="noreferrer">
            API docs (Swagger)
          </a>
          <span className="navLabel">API</span>
          <a href={`${API}/health`} target="_blank" rel="noreferrer">
            GET /health
          </a>
        </nav>
      </aside>
      <div className="mainCol">
        <header className="top">
          <h1>Operations</h1>
          <p className="muted">
            Local admin shell — extend with orgs, users, and source runs.
          </p>
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
            <h2>Bootstrap</h2>
            <p className="muted">
              First-time DB setup: <code>POST {API}/bootstrap</code>
            </p>
            <p className="hint">Run from terminal or use API docs when auth is off.</p>
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;
