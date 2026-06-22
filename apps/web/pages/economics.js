import { useEffect, useState } from 'react';
import { getApiBaseUrl } from '../lib/api';
import styles from '../src/styles/Page.module.css';

export default function EconomicsPage() {
  const API = getApiBaseUrl();
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [health, setHealth] = useState(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr('');
    Promise.all([
      fetch(`${API}/sources/records?kind=bea&limit=50`).then((r) => {
        if (!r.ok) throw new Error(`records ${r.status}`);
        return r.json();
      }),
      fetch(`${API}/sources/health`).then((r) => r.json()),
    ])
      .then(([data, sh]) => {
        if (cancelled) return;
        setRecords(data.records || []);
        setTotal(data.total || 0);
        const bea = (sh.per_source || []).find((s) => s.kind === 'bea');
        setHealth(bea || null);
      })
      .catch((e) => {
        if (!cancelled) setErr(e.message || String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [API]);

  const tier = records[0]?.normalized?.source_tier || 'unknown';

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>U.S. Economic Data (BEA)</h1>
        <p>
          Bureau of Economic Analysis — GDP, national accounts, and state personal income via connector #18.
        </p>
      </section>

      <section className={styles.grid2}>
        <aside className={styles.panel}>
          <h2>Connector status</h2>
          {loading && <p className={styles.subtle}>Loading…</p>}
          {err && <p className={styles.dangerText}>{err}</p>}
          {health && (
            <ul className={styles.subtle}>
              <li>Source ID: {health.id}</li>
              <li>Last run: {health.last_status}</li>
              <li>Records in DB: {health.records}</li>
              <li>Data tier: <strong>{tier}</strong></li>
              <li>Last finished: {health.last_finished || '—'}</li>
            </ul>
          )}
          {tier === 'sample' && (
            <p className={styles.dangerText}>
              Showing sample data. Activate <code>BEA_API_USER_ID</code> at{' '}
              <a href="https://apps.bea.gov/API/signup/" target="_blank" rel="noreferrer">
                apps.bea.gov/API/signup
              </a>{' '}
              (click the email activation link), then re-run the BEA connector.
            </p>
          )}
        </aside>

        <section className={styles.panel}>
          <h2>Records ({total})</h2>
          {records.length === 0 && !loading ? (
            <p className={styles.subtle}>No BEA records yet. Run the connector from Admin or seed script.</p>
          ) : (
            <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid #334155' }}>
                  <th>Geo</th>
                  <th>Metric</th>
                  <th>Period</th>
                  <th>Value</th>
                  <th>Dataset</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => {
                  const n = r.normalized || {};
                  return (
                    <tr key={r.external_id} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td>{n.geo_name || '—'}</td>
                      <td>{n.line_description || n.description || '—'}</td>
                      <td>{n.time_period || '—'}</td>
                      <td>{n.data_value} {n.cl_unit || ''}</td>
                      <td>{n.dataset}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      </section>
    </main>
  );
}
