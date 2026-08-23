import Head from 'next/head'
import Link from 'next/link'
import { useState, useEffect } from 'react'
import { getApiBaseUrl, apiFetch, isNoData } from '../lib/api';

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

export default function Billing() {
  const [subscription, setSubscription] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cancelling, setCancelling] = useState(false)
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [cancelReason, setCancelReason] = useState('')

  useEffect(() => {
    apiFetch('/billing/subscription')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && !isNoData(data)) {
          setSubscription(data)
        } else {
          setError('no_billing')
        }
      })
      .catch(() => setError('no_billing'))
      .finally(() => setLoading(false))
  }, [])

  const handleCancel = async () => {
    setCancelling(true)
    try {
      const res = await apiFetch(`/billing/cancel`, { method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: cancelReason }),
      })
      if (res.ok) {
        setSubscription(prev => ({ ...prev, status: 'cancelled', cancelledAt: new Date().toISOString() }))
        setShowCancelModal(false)
      }
    } catch (err) {
      console.error('Cancel failed:', err)
    } finally {
      setCancelling(false)
    }
  }

  if (loading) {
    return (
      <div className="page-wrap" style={{ textAlign: 'center', paddingTop: '4rem' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading billing information...</div>
      </div>
    )
  }

  if (error || !subscription) {
    return (
      <>
        <Head><title>Billing | Enterprise Intelligence</title></Head>
        <div className="page-wrap" style={{ maxWidth: 600, textAlign: 'center', paddingTop: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>💳</div>
          <h1 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#f1f5f9', marginBottom: '0.75rem' }}>
            Billing Not Configured
          </h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.5rem', lineHeight: 1.6 }}>
            Payment processing is not yet active. Stripe integration is required to enable subscriptions, invoices, and payment management.
          </p>
          <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1rem', fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'left' }}>
            <strong style={{ color: 'var(--text)' }}>Required:</strong> Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in environment variables to enable billing.
          </div>
          <Link href="/" legacyBehavior>
            <a className="btn btn-primary" style={{ marginTop: '1.5rem', fontSize: '0.8rem', padding: '10px 20px' }}>Back to Dashboard</a>
          </Link>
        </div>
      </>
    )
  }

  const UsageBar = ({ label, used, limit }) => {
    const pct = typeof limit === 'number' ? Math.min((used / limit) * 100, 100) : 0
    const isWarning = pct >= 80
    const color = isWarning ? '#f59e0b' : '#6366f1'

    return (
      <div style={{ marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
          <span style={{ color: 'var(--text)' }}>{label}</span>
          <span style={{ color: isWarning ? color : 'var(--text-muted)' }}>
            {used.toLocaleString()} / {typeof limit === 'number' ? limit.toLocaleString() : limit}
          </span>
        </div>
        <div style={{ height: 6, background: 'var(--line)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.3s' }} />
        </div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>Billing | Enterprise Intelligence</title>
      </Head>

      <div className="page-wrap" style={{ maxWidth: 800 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 900, color: '#f1f5f9', marginBottom: '1.5rem' }}>
          Billing & Subscription
        </h1>

        {/* Current Plan */}
        <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', marginBottom: '1.5rem' }}>
          {/* Plan Details */}
          <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
              Current Plan
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1rem' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#6366f1' }}>{subscription.plan}</div>
              <span className={`badge ${subscription.status === 'active' ? 'badge-brand' : 'badge-gray'}`}>
                {subscription.status === 'active' ? 'Active' : subscription.status === 'cancelled' ? 'Cancelled' : subscription.status}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              <strong style={{ color: 'var(--text)' }}>${subscription.price}</strong>/{subscription.interval}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Current period: {subscription.currentPeriodStart} to {subscription.currentPeriodEnd}
            </div>
            {subscription.status === 'active' && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                Next billing: <strong style={{ color: 'var(--text)' }}>{subscription.nextBillingDate}</strong>
              </div>
            )}
            {subscription.status === 'cancelled' && (
              <div style={{ fontSize: '0.75rem', color: '#f59e0b', marginTop: 8 }}>
                Your subscription will end on {subscription.currentPeriodEnd}. You retain access until then.
              </div>
            )}

            <div style={{ marginTop: '1rem', display: 'flex', gap: 8 }}>
              <Link href="/pricing" legacyBehavior>
                <a className="btn btn-primary" style={{ fontSize: '0.75rem', padding: '8px 14px' }}>
                  {subscription.status === 'cancelled' ? 'Resubscribe' : 'Change Plan'}
                </a>
              </Link>
              {subscription.status === 'active' && (
                <button
                  onClick={() => setShowCancelModal(true)}
                  className="btn"
                  style={{ fontSize: '0.75rem', padding: '8px 14px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--text-muted)' }}
                >
                  Cancel Subscription
                </button>
              )}
            </div>
          </div>

          {/* Usage This Period */}
          <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
              Usage This Period
            </div>
            <UsageBar label="Intelligence Reports" used={subscription.usage.reports.used} limit={subscription.usage.reports.limit} />
            <UsageBar label="Active Alerts" used={subscription.usage.alerts.used} limit={subscription.usage.alerts.limit} />
            <UsageBar label="API Calls" used={subscription.usage.apiCalls.used} limit={subscription.usage.apiCalls.limit} />
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              Resets on {subscription.nextBillingDate}
            </div>
          </div>
        </div>

        {/* Payment Method */}
        <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1.25rem', marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
            Payment Method
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 40, height: 26, background: 'linear-gradient(135deg, #1a1f36, #2d3748)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.6rem', color: '#f1f5f9' }}>
                VISA
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text)' }}>**** **** **** 4242</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Expires 12/2028</div>
              </div>
            </div>
            <button className="btn" style={{ fontSize: '0.72rem', padding: '6px 12px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--text-muted)' }}>
              Update
            </button>
          </div>
        </div>

        {/* Billing History */}
        <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
            Billing History
          </div>
          <table style={{ width: '100%', fontSize: '0.78rem', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                <th style={{ textAlign: 'left', padding: '8px 0', color: 'var(--text-muted)', fontWeight: 600 }}>Date</th>
                <th style={{ textAlign: 'left', padding: '8px 0', color: 'var(--text-muted)', fontWeight: 600 }}>Description</th>
                <th style={{ textAlign: 'right', padding: '8px 0', color: 'var(--text-muted)', fontWeight: 600 }}>Amount</th>
                <th style={{ textAlign: 'right', padding: '8px 0', color: 'var(--text-muted)', fontWeight: 600 }}>Invoice</th>
              </tr>
            </thead>
            <tbody>
              {BILLING_HISTORY.map((inv) => (
                <tr key={inv.id} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '10px 0', color: 'var(--text)' }}>{inv.date}</td>
                  <td style={{ padding: '10px 0', color: 'var(--text-muted)' }}>{inv.desc}</td>
                  <td style={{ padding: '10px 0', color: 'var(--text)', textAlign: 'right' }}>${inv.amount}</td>
                  <td style={{ padding: '10px 0', textAlign: 'right' }}>
                    <a
                      href={`${API}/billing/invoices/${inv.id}/pdf`}
                      download={`${inv.id}.pdf`}
                      style={{ color: 'var(--brand-hover)', fontSize: '0.72rem' }}
                    >
                      Download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Support Link */}
        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Questions about billing? <Link href="/support" legacyBehavior><a style={{ color: 'var(--brand-hover)' }}>Contact Support</a></Link>
        </div>
      </div>

      {/* Cancel Modal */}
      {showCancelModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-lg)', padding: '1.5rem', maxWidth: 440, width: '90%' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f1f5f9', marginBottom: '0.75rem' }}>
              Cancel Subscription
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              We are sorry to see you go. Your subscription will remain active until <strong style={{ color: 'var(--text)' }}>{subscription.currentPeriodEnd}</strong>. You can resubscribe anytime.
            </p>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Help us improve (optional)
              </label>
              <select
                value={cancelReason}
                onChange={e => setCancelReason(e.target.value)}
                className="inp"
                style={{ width: '100%', fontSize: '0.8rem', padding: '8px 10px' }}
              >
                <option value="">Select a reason...</option>
                <option value="too_expensive">Too expensive</option>
                <option value="not_using">Not using it enough</option>
                <option value="missing_features">Missing features I need</option>
                <option value="found_alternative">Found an alternative</option>
                <option value="technical_issues">Technical issues</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowCancelModal(false)}
                className="btn"
                style={{ fontSize: '0.78rem', padding: '8px 16px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--text)' }}
              >
                Keep Subscription
              </button>
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="btn"
                style={{ fontSize: '0.78rem', padding: '8px 16px', background: '#dc2626', border: 'none', color: '#fff' }}
              >
                {cancelling ? 'Cancelling...' : 'Confirm Cancellation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
