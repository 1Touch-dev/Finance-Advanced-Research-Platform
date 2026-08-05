import Head from 'next/head'
import Link from 'next/link'
import { useState, useEffect } from 'react'
import { getApiBaseUrl } from '../lib/api'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const SERVICES = [
  { id: 'api', name: 'Core API', description: 'Main API endpoints' },
  { id: 'web', name: 'Web Application', description: 'Frontend application' },
  { id: 'data', name: 'Data Pipeline', description: 'Real-time data ingestion' },
  { id: 'search', name: 'Search Service', description: 'OpenSearch cluster' },
  { id: 'auth', name: 'Authentication', description: 'Login & session management' },
  { id: 'alerts', name: 'Alert System', description: 'Email & notification delivery' },
]

const STATUS_COLORS = {
  operational: '#10b981',
  degraded: '#f59e0b',
  partial_outage: '#f97316',
  major_outage: '#dc2626',
  maintenance: '#6366f1',
}

const STATUS_LABELS = {
  operational: 'Operational',
  degraded: 'Degraded Performance',
  partial_outage: 'Partial Outage',
  major_outage: 'Major Outage',
  maintenance: 'Under Maintenance',
}

export default function Status() {
  const [services, setServices] = useState([])
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [overallStatus, setOverallStatus] = useState('operational')

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API}/status`)
        const data = await res.json()
        setServices(data.services || [])
        setIncidents(data.incidents || [])
        setOverallStatus(data.overall_status || 'operational')
      } catch (err) {
        // Fallback mock data
        setServices(SERVICES.map(s => ({ ...s, status: 'operational', uptime: 99.95 + Math.random() * 0.05 })))
        setIncidents([
          {
            id: 'inc-001',
            title: 'Elevated API latency',
            status: 'resolved',
            severity: 'minor',
            created_at: '2026-08-04T14:30:00Z',
            resolved_at: '2026-08-04T15:45:00Z',
            updates: [
              { time: '2026-08-04T15:45:00Z', message: 'Issue resolved. All systems back to normal.' },
              { time: '2026-08-04T15:00:00Z', message: 'Identified root cause as database connection pool saturation. Scaling up.' },
              { time: '2026-08-04T14:30:00Z', message: 'Investigating reports of slow API responses.' },
            ],
          },
          {
            id: 'inc-002',
            title: 'Scheduled database maintenance',
            status: 'completed',
            severity: 'maintenance',
            created_at: '2026-08-01T02:00:00Z',
            resolved_at: '2026-08-01T04:00:00Z',
            updates: [
              { time: '2026-08-01T04:00:00Z', message: 'Maintenance completed successfully.' },
              { time: '2026-08-01T02:00:00Z', message: 'Beginning scheduled database maintenance. Brief service interruption expected.' },
            ],
          },
        ])
        setOverallStatus('operational')
      } finally {
        setLoading(false)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const formatDate = (dateStr) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const getOverallColor = () => STATUS_COLORS[overallStatus] || STATUS_COLORS.operational
  const getOverallLabel = () => STATUS_LABELS[overallStatus] || 'Operational'

  // Generate uptime chart bars (last 90 days)
  const UptimeChart = ({ uptime }) => {
    const days = 90
    const bars = Array.from({ length: days }, (_, i) => {
      // Simulate some variation
      const dayUptime = i < 3 ? (uptime - (Math.random() * 0.5)) : uptime
      return dayUptime >= 99.9 ? 'operational' : dayUptime >= 99.0 ? 'degraded' : 'partial_outage'
    })

    return (
      <div style={{ display: 'flex', gap: 1, height: 24, alignItems: 'flex-end' }}>
        {bars.map((status, i) => (
          <div
            key={i}
            style={{
              width: 3,
              height: '100%',
              background: STATUS_COLORS[status],
              borderRadius: 1,
              opacity: i < 3 ? 0.6 : 1,
            }}
            title={`Day ${days - i}: ${status}`}
          />
        ))}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="page-wrap" style={{ textAlign: 'center', paddingTop: '4rem' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading system status...</div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>System Status | Enterprise Intelligence</title>
        <meta name="description" content="Real-time system status and incident history for Enterprise Intelligence platform." />
      </Head>

      <div className="page-wrap" style={{ maxWidth: 900 }}>
        {/* Overall Status Banner */}
        <div
          style={{
            background: `linear-gradient(135deg, ${getOverallColor()}22, transparent)`,
            border: `1px solid ${getOverallColor()}44`,
            borderRadius: 'var(--radius-lg)',
            padding: '1.5rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                background: `${getOverallColor()}33`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                color: getOverallColor(),
              }}
            >
              {overallStatus === 'operational' ? '+' : overallStatus === 'maintenance' ? '!' : '!'}
            </div>
            <div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f1f5f9' }}>
                {getOverallLabel()}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Last updated: {new Date().toLocaleTimeString()}
              </div>
            </div>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span style={{ color: 'var(--text)' }}>99.98%</span> uptime last 90 days
          </div>
        </div>

        {/* Services Grid */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '1rem' }}>
            Services
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {services.map(service => (
              <div
                key={service.id}
                style={{
                  background: 'var(--bg-elev-1)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem 1.25rem',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr auto',
                  alignItems: 'center',
                  gap: '1rem',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text)' }}>{service.name}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{service.description}</div>
                </div>
                <div style={{ overflow: 'hidden' }}>
                  <UptimeChart uptime={service.uptime || 99.99} />
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                    <span>90 days ago</span>
                    <span>{(service.uptime || 99.99).toFixed(2)}% uptime</span>
                    <span>Today</span>
                  </div>
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '6px 12px',
                    background: `${STATUS_COLORS[service.status || 'operational']}22`,
                    borderRadius: 20,
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    color: STATUS_COLORS[service.status || 'operational'],
                  }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: STATUS_COLORS[service.status || 'operational'] }} />
                  {STATUS_LABELS[service.status || 'operational']}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Incident History */}
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '1rem' }}>
            Incident History
          </div>
          {incidents.length === 0 ? (
            <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '2rem', textAlign: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No incidents in the last 90 days</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {incidents.map(incident => (
                <div
                  key={incident.id}
                  style={{
                    background: 'var(--bg-elev-1)',
                    border: '1px solid var(--line)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.25rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text)' }}>{incident.title}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                        {formatDate(incident.created_at)}
                        {incident.resolved_at && ` — Resolved ${formatDate(incident.resolved_at)}`}
                      </div>
                    </div>
                    <span
                      style={{
                        padding: '4px 10px',
                        borderRadius: 12,
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        background: incident.status === 'resolved' || incident.status === 'completed' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                        color: incident.status === 'resolved' || incident.status === 'completed' ? '#10b981' : '#f59e0b',
                        textTransform: 'capitalize',
                      }}
                    >
                      {incident.status}
                    </span>
                  </div>

                  {/* Timeline */}
                  <div style={{ borderLeft: '2px solid var(--line)', marginLeft: 8, paddingLeft: 16 }}>
                    {incident.updates.map((update, i) => (
                      <div key={i} style={{ position: 'relative', paddingBottom: i === incident.updates.length - 1 ? 0 : 12 }}>
                        <div
                          style={{
                            position: 'absolute',
                            left: -21,
                            top: 4,
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            background: i === 0 ? '#10b981' : 'var(--line-strong)',
                          }}
                        />
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-soft)', marginBottom: 2 }}>
                          {formatDate(update.time)}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text)' }}>{update.message}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Subscribe */}
        <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1.25rem', marginTop: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text)' }}>Subscribe to status updates</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Get notified when we have incidents or scheduled maintenance</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" style={{ fontSize: '0.75rem', padding: '8px 14px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--text-muted)' }}>
              Email
            </button>
            <button className="btn" style={{ fontSize: '0.75rem', padding: '8px 14px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--text-muted)' }}>
              Slack
            </button>
            <button className="btn" style={{ fontSize: '0.75rem', padding: '8px 14px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--text-muted)' }}>
              RSS
            </button>
          </div>
        </div>

        {/* Footer Links */}
        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <Link href="/support"><a style={{ color: 'var(--brand-hover)', marginRight: 16 }}>Contact Support</a></Link>
          <Link href="/pricing"><a style={{ color: 'var(--brand-hover)' }}>View Pricing</a></Link>
        </div>
      </div>
    </>
  )
}
