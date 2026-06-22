import { useState, useEffect } from 'react';
import { getApiBaseUrl } from '../lib/api';
const STATES = [
  { code: '', name: 'All States' },
  { code: 'us_al', name: 'Alabama' }, { code: 'us_ak', name: 'Alaska' },
  { code: 'us_az', name: 'Arizona' }, { code: 'us_ar', name: 'Arkansas' },
  { code: 'us_ca', name: 'California' }, { code: 'us_co', name: 'Colorado' },
  { code: 'us_ct', name: 'Connecticut' }, { code: 'us_de', name: 'Delaware' },
  { code: 'us_dc', name: 'DC' }, { code: 'us_fl', name: 'Florida' },
  { code: 'us_ga', name: 'Georgia' }, { code: 'us_hi', name: 'Hawaii' },
  { code: 'us_id', name: 'Idaho' }, { code: 'us_il', name: 'Illinois' },
  { code: 'us_in', name: 'Indiana' }, { code: 'us_ia', name: 'Iowa' },
  { code: 'us_ks', name: 'Kansas' }, { code: 'us_ky', name: 'Kentucky' },
  { code: 'us_la', name: 'Louisiana' }, { code: 'us_me', name: 'Maine' },
  { code: 'us_md', name: 'Maryland' }, { code: 'us_ma', name: 'Massachusetts' },
  { code: 'us_mi', name: 'Michigan' }, { code: 'us_mn', name: 'Minnesota' },
  { code: 'us_ms', name: 'Mississippi' }, { code: 'us_mo', name: 'Missouri' },
  { code: 'us_mt', name: 'Montana' }, { code: 'us_ne', name: 'Nebraska' },
  { code: 'us_nv', name: 'Nevada' }, { code: 'us_nh', name: 'New Hampshire' },
  { code: 'us_nj', name: 'New Jersey' }, { code: 'us_nm', name: 'New Mexico' },
  { code: 'us_ny', name: 'New York' }, { code: 'us_nc', name: 'North Carolina' },
  { code: 'us_nd', name: 'North Dakota' }, { code: 'us_oh', name: 'Ohio' },
  { code: 'us_ok', name: 'Oklahoma' }, { code: 'us_or', name: 'Oregon' },
  { code: 'us_pa', name: 'Pennsylvania' }, { code: 'us_ri', name: 'Rhode Island' },
  { code: 'us_sc', name: 'South Carolina' }, { code: 'us_sd', name: 'South Dakota' },
  { code: 'us_tn', name: 'Tennessee' }, { code: 'us_tx', name: 'Texas' },
  { code: 'us_ut', name: 'Utah' }, { code: 'us_vt', name: 'Vermont' },
  { code: 'us_va', name: 'Virginia' }, { code: 'us_wa', name: 'Washington' },
  { code: 'us_wv', name: 'West Virginia' }, { code: 'us_wi', name: 'Wisconsin' },
  { code: 'us_wy', name: 'Wyoming' },
];

const TIER_COLORS = { bulk: '#22c55e', api: '#3b82f6', scrape: '#f59e0b', cobalt: '#a855f7', pending: '#6b7280' };
const STATUS_COLORS = { success: '#22c55e', partial: '#f59e0b', pending: '#6b7280', error: '#ef4444' };

export default function RegistryPage() {
  const [query, setQuery] = useState('');
  const [state, setState] = useState('');
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const [jurisdictions, setJurisdictions] = useState([]);
  const [showJurisdictions, setShowJurisdictions] = useState(false);
  const [searched, setSearched] = useState(false);

  const apiBase = getApiBaseUrl();

  useEffect(() => {
    fetch(`${apiBase}/registry/health`)
      .then(r => r.json())
      .then(d => setHealth(d))
      .catch(() => {});
    fetch(`${apiBase}/registry/jurisdictions`)
      .then(r => r.json())
      .then(d => setJurisdictions(d.jurisdictions || []))
      .catch(() => {});
  }, [apiBase]);

  const handleSearch = async (e) => {
    e?.preventDefault();
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (state) params.set('state', state);
      params.set('limit', '20');
      const resp = await fetch(`${apiBase}/registry/search?${params}`);
      const data = await resp.json();
      setResults(data.results || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 1rem' }}>
        {/* Header */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0 }}>
            U.S. State Company Registry
          </h1>
          <p style={{ color: '#6b7280', marginTop: '0.5rem' }}>
            Search across 51 jurisdictions (50 states + DC) — normalized schema, free-first data.
          </p>
          {health && (
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
              <Stat label="Jurisdictions Registered" value={health.total_jurisdictions_registered} />
              <Stat label="With Live Data" value={health.live_jurisdictions_with_data} />
              <Stat label="Total Records" value={health.total_registry_records?.toLocaleString()} />
              {Object.entries(health.tier_distribution || {}).map(([tier, count]) => (
                <Stat key={tier} label={`Tier: ${tier}`} value={count} color={TIER_COLORS[tier]} />
              ))}
            </div>
          )}
        </div>

        {/* Search form */}
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Search by company name..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            style={{
              flex: 1, minWidth: 220, padding: '0.625rem 0.875rem',
              border: '1px solid #d1d5db', borderRadius: 8, fontSize: '0.9rem',
            }}
          />
          <select
            value={state}
            onChange={e => setState(e.target.value)}
            style={{
              padding: '0.625rem 0.875rem', border: '1px solid #d1d5db',
              borderRadius: 8, fontSize: '0.9rem', minWidth: 160,
            }}
          >
            {STATES.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
          </select>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '0.625rem 1.5rem', background: '#1d4ed8', color: '#fff',
              border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600,
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {/* Results */}
        {searched && (
          <div>
            <div style={{ marginBottom: '0.75rem', color: '#6b7280', fontSize: '0.875rem' }}>
              {loading ? 'Loading...' : `${total.toLocaleString()} result${total !== 1 ? 's' : ''} found`}
            </div>
            {results.length > 0 ? (
              <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                  <thead>
                    <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                      <th style={thStyle}>Legal Name</th>
                      <th style={thStyle}>State</th>
                      <th style={thStyle}>Type</th>
                      <th style={thStyle}>Status</th>
                      <th style={thStyle}>Formed</th>
                      <th style={thStyle}>Source Tier</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={tdStyle}><strong>{r.legal_name || '—'}</strong></td>
                        <td style={tdStyle}>{r.jurisdiction_code || '—'}</td>
                        <td style={tdStyle}>{r.entity_type || '—'}</td>
                        <td style={tdStyle}>
                          <span style={{
                            padding: '2px 8px', borderRadius: 12, fontSize: '0.8rem',
                            background: r.status === 'active' ? '#dcfce7' : '#f3f4f6',
                            color: r.status === 'active' ? '#166534' : '#374151',
                          }}>
                            {r.status || '—'}
                          </span>
                        </td>
                        <td style={tdStyle}>{r.formation_date || '—'}</td>
                        <td style={tdStyle}>
                          <span style={{
                            padding: '2px 8px', borderRadius: 12, fontSize: '0.75rem',
                            background: '#eff6ff', color: '#1d4ed8',
                          }}>
                            {r.source_tier || '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : !loading && (
              <div style={{ textAlign: 'center', padding: '3rem', color: '#6b7280' }}>
                No results found. Try seeding data: <code>bash scripts/seed-state-registry.sh</code>
              </div>
            )}
          </div>
        )}

        {/* Jurisdictions coverage */}
        <div style={{ marginTop: '2.5rem' }}>
          <button
            onClick={() => setShowJurisdictions(v => !v)}
            style={{
              background: 'none', border: '1px solid #d1d5db', borderRadius: 8,
              padding: '0.5rem 1rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.875rem',
            }}
          >
            {showJurisdictions ? '▲' : '▼'} All 51 Jurisdictions ({jurisdictions.length} loaded)
          </button>

          {showJurisdictions && jurisdictions.length > 0 && (
            <div style={{ marginTop: '1rem', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                    <th style={thStyle}>Code</th>
                    <th style={thStyle}>State</th>
                    <th style={thStyle}>Tier</th>
                    <th style={thStyle}>Records</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>SOS Portal</th>
                  </tr>
                </thead>
                <tbody>
                  {jurisdictions.map(j => (
                    <tr key={j.jurisdiction_code} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={tdStyle}><code>{j.jurisdiction_code}</code></td>
                      <td style={tdStyle}>{j.name}</td>
                      <td style={tdStyle}>
                        <span style={{
                          padding: '2px 7px', borderRadius: 10, fontSize: '0.75rem',
                          background: TIER_COLORS[j.tier] + '22',
                          color: TIER_COLORS[j.tier],
                          fontWeight: 600,
                        }}>
                          {j.tier}
                        </span>
                      </td>
                      <td style={tdStyle}>{j.record_count || 0}</td>
                      <td style={tdStyle}>
                        <span style={{
                          padding: '2px 7px', borderRadius: 10, fontSize: '0.75rem',
                          background: STATUS_COLORS[j.last_status] + '22',
                          color: STATUS_COLORS[j.last_status],
                        }}>
                          {j.last_status}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <a href={j.sos_url} target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>
                          Portal ↗
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
  );
}

const thStyle = { padding: '0.625rem 0.75rem', textAlign: 'left', fontWeight: 600, color: '#374151' };
const tdStyle = { padding: '0.625rem 0.75rem', verticalAlign: 'top' };

function Stat({ label, value, color = '#1d4ed8' }) {
  return (
    <div style={{
      background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8,
      padding: '0.5rem 0.875rem', minWidth: 100,
    }}>
      <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ fontSize: '1.25rem', fontWeight: 700, color }}>{value ?? '—'}</div>
    </div>
  );
}
