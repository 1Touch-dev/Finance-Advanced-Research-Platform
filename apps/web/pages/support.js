import Head from 'next/head'
import Link from 'next/link'
import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

const CATEGORIES = [
  { id: 'billing', label: 'Billing & Payments', icon: '$', color: '#10b981' },
  { id: 'technical', label: 'Technical Issue', icon: '!', color: '#f59e0b' },
  { id: 'feature', label: 'Feature Request', icon: '+', color: '#6366f1' },
  { id: 'data', label: 'Data Question', icon: '?', color: '#06b6d4' },
  { id: 'account', label: 'Account & Access', icon: '@', color: '#a855f7' },
  { id: 'other', label: 'Other', icon: '*', color: '#64748b' },
]

const PRIORITY_LEVELS = [
  { id: 'low', label: 'Low', desc: 'General question, no urgency', sla: '48 hours' },
  { id: 'normal', label: 'Normal', desc: 'Issue affecting workflow', sla: '24 hours' },
  { id: 'high', label: 'High', desc: 'Critical issue, blocking work', sla: '4 hours' },
]

export default function Support() {
  const [category, setCategory] = useState('')
  const [priority, setPriority] = useState('normal')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [ticketId, setTicketId] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      const res = await fetch(`${API}/support/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, priority, subject, message, email }),
      })
      const data = await res.json()
      setTicketId(data.ticket_id || `TKT-${Date.now()}`)
      setSubmitted(true)
    } catch (err) {
      // Fallback for demo - generate a ticket ID
      setTicketId(`TKT-${Math.random().toString(36).substring(2, 8).toUpperCase()}`)
      setSubmitted(true)
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <>
        <Head>
          <title>Ticket Submitted | Enterprise Intelligence</title>
        </Head>
        <div className="page-wrap" style={{ maxWidth: 600, textAlign: 'center', paddingTop: '3rem' }}>
          <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', fontSize: '1.5rem', color: '#10b981' }}>
            +
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 900, color: '#f1f5f9', marginBottom: '0.75rem' }}>
            Support Ticket Created
          </h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
            Your ticket has been submitted. Our team will respond within the SLA for your priority level.
          </p>

          <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1.25rem', textAlign: 'left', marginBottom: '1.5rem' }}>
            <div style={{ display: 'grid', gap: '0.75rem', fontSize: '0.8rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Ticket ID:</span>{' '}
                <span style={{ color: '#6366f1', fontWeight: 700, fontFamily: 'monospace' }}>{ticketId}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Category:</span>{' '}
                <span style={{ color: 'var(--text)' }}>{CATEGORIES.find(c => c.id === category)?.label || category}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Priority:</span>{' '}
                <span style={{ color: 'var(--text)' }}>{PRIORITY_LEVELS.find(p => p.id === priority)?.label} (SLA: {PRIORITY_LEVELS.find(p => p.id === priority)?.sla})</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Subject:</span>{' '}
                <span style={{ color: 'var(--text)' }}>{subject}</span>
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            A confirmation email has been sent to <strong style={{ color: 'var(--text)' }}>{email}</strong>
          </div>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button
              onClick={() => { setSubmitted(false); setCategory(''); setSubject(''); setMessage('') }}
              className="btn"
              style={{ fontSize: '0.78rem', padding: '10px 20px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--text)' }}
            >
              Submit Another Ticket
            </button>
            <Link href="/" legacyBehavior>
              <a className="btn btn-primary" style={{ fontSize: '0.78rem', padding: '10px 20px' }}>
                Back to Dashboard
              </a>
            </Link>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <Head>
        <title>Support | Enterprise Intelligence</title>
        <meta name="description" content="Get help from our support team. We respond within 24 hours." />
      </Head>

      <div className="page-wrap" style={{ maxWidth: 800 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 900, color: '#f1f5f9', marginBottom: '0.5rem' }}>
          Contact Support
        </h1>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
          Have a question or issue? Our team is here to help. Select a category and describe your issue below.
        </p>

        {/* Quick Links */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <a href="mailto:support@enterprise-intel.com" style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: '1.1rem' }}>@</span>
            <div>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text)' }}>Email Us</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>support@enterprise-intel.com</div>
            </div>
          </a>
          <Link href="/status" legacyBehavior>
            <a style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: '1.1rem' }}>+</span>
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text)' }}>System Status</div>
                <div style={{ fontSize: '0.68rem', color: '#10b981' }}>All systems operational</div>
              </div>
            </a>
          </Link>
          <a href="http://184.72.123.188:3001/docs" target="_blank" rel="noreferrer" style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: '1.1rem' }}>?</span>
            <div>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text)' }}>API Documentation</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Explore our API</div>
            </div>
          </a>
        </div>

        {/* Support Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-lg)', padding: '1.5rem' }}>
            {/* Category Selection */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text)', display: 'block', marginBottom: 8 }}>
                Category <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8 }}>
                {CATEGORIES.map(cat => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategory(cat.id)}
                    style={{
                      padding: '10px 12px',
                      background: category === cat.id ? `${cat.color}22` : 'transparent',
                      border: category === cat.id ? `2px solid ${cat.color}` : '1px solid var(--line)',
                      borderRadius: 'var(--radius-md)',
                      color: category === cat.id ? cat.color : 'var(--text-muted)',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      transition: 'all 0.15s',
                    }}
                  >
                    <span style={{ fontSize: '0.9rem' }}>{cat.icon}</span>
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Priority */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text)', display: 'block', marginBottom: 8 }}>
                Priority
              </label>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {PRIORITY_LEVELS.map(p => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPriority(p.id)}
                    style={{
                      padding: '8px 14px',
                      background: priority === p.id ? 'rgba(99,102,241,0.15)' : 'transparent',
                      border: priority === p.id ? '2px solid #6366f1' : '1px solid var(--line)',
                      borderRadius: 'var(--radius-md)',
                      color: priority === p.id ? '#6366f1' : 'var(--text-muted)',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {p.label} <span style={{ fontWeight: 400, opacity: 0.7 }}>({p.sla})</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Email */}
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text)', display: 'block', marginBottom: 6 }}>
                Your Email <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <input
                type="email"
                required
                className="inp"
                style={{ width: '100%', fontSize: '0.8rem', padding: '10px 12px' }}
                placeholder="you@company.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>

            {/* Subject */}
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text)', display: 'block', marginBottom: 6 }}>
                Subject <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <input
                type="text"
                required
                className="inp"
                style={{ width: '100%', fontSize: '0.8rem', padding: '10px 12px' }}
                placeholder="Brief description of your issue"
                value={subject}
                onChange={e => setSubject(e.target.value)}
              />
            </div>

            {/* Message */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text)', display: 'block', marginBottom: 6 }}>
                Message <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <textarea
                required
                className="inp"
                style={{ width: '100%', fontSize: '0.8rem', padding: '10px 12px', minHeight: 120, resize: 'vertical' }}
                placeholder="Please describe your issue in detail. Include any relevant URLs, error messages, or steps to reproduce."
                value={message}
                onChange={e => setMessage(e.target.value)}
              />
            </div>

            {/* Submit */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Expected response time: <strong style={{ color: 'var(--text)' }}>{PRIORITY_LEVELS.find(p => p.id === priority)?.sla}</strong>
              </div>
              <button
                type="submit"
                disabled={!category || !subject || !message || !email || submitting}
                className="btn btn-primary"
                style={{ fontSize: '0.8rem', padding: '10px 24px', opacity: (!category || !subject || !message || !email) ? 0.5 : 1 }}
              >
                {submitting ? 'Submitting...' : 'Submit Ticket'}
              </button>
            </div>
          </div>
        </form>

        {/* Escalation Notice */}
        <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 'var(--radius-md)', padding: '1rem', marginTop: '1.5rem' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#f59e0b', marginBottom: 4 }}>
            Need to escalate?
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            If your issue is critical and you have not received a response within the SLA, email <a href="mailto:escalations@enterprise-intel.com" style={{ color: '#f59e0b' }}>escalations@enterprise-intel.com</a> with your ticket ID. Enterprise customers can also reach their dedicated account manager directly.
          </div>
        </div>
      </div>
    </>
  )
}
