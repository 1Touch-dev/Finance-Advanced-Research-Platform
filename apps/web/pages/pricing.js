import Head from 'next/head'
import Link from 'next/link'
import { useState } from 'react'

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    interval: 'forever',
    description: 'For individuals exploring the platform',
    color: '#64748b',
    features: [
      '5 intelligence reports/month',
      'Basic stock analysis',
      'Public SEC filings',
      'Community support',
      '7-day data retention',
    ],
    limits: {
      reports: 5,
      alerts: 3,
      watchlists: 1,
      apiCalls: 100,
    },
    cta: 'Get Started',
    popular: false,
  },
  {
    id: 'pro',
    name: 'Professional',
    price: 49,
    interval: 'month',
    description: 'For active investors and analysts',
    color: '#6366f1',
    features: [
      '100 intelligence reports/month',
      'Full stock & valuation analysis',
      'SEC filings + insider trading',
      'Real-time alerts (email)',
      '13F institutional tracking',
      'Priority email support',
      '1-year data retention',
    ],
    limits: {
      reports: 100,
      alerts: 50,
      watchlists: 10,
      apiCalls: 5000,
    },
    cta: 'Start Free Trial',
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 299,
    interval: 'month',
    description: 'For teams and institutions',
    color: '#10b981',
    features: [
      'Unlimited intelligence reports',
      'Full platform access',
      'API access + webhooks',
      'Team collaboration (5 seats)',
      'Custom entity tracking',
      'Dedicated account manager',
      'SLA guarantee (99.9% uptime)',
      'Unlimited data retention',
    ],
    limits: {
      reports: 'Unlimited',
      alerts: 'Unlimited',
      watchlists: 'Unlimited',
      apiCalls: 100000,
    },
    cta: 'Contact Sales',
    popular: false,
  },
]

const ANNUAL_DISCOUNT = 0.20 // 20% off

function PricingCard({ plan, annual }) {
  const displayPrice = annual && plan.price > 0
    ? Math.round(plan.price * (1 - ANNUAL_DISCOUNT))
    : plan.price

  return (
    <div
      style={{
        background: 'var(--bg-elev-1)',
        border: plan.popular ? `2px solid ${plan.color}` : '1px solid var(--line)',
        borderRadius: 'var(--radius-lg)',
        padding: '1.5rem',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {plan.popular && (
        <div
          style={{
            position: 'absolute',
            top: -12,
            left: '50%',
            transform: 'translateX(-50%)',
            background: plan.color,
            color: '#fff',
            fontSize: '0.68rem',
            fontWeight: 700,
            padding: '4px 12px',
            borderRadius: 20,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          Most Popular
        </div>
      )}

      <div style={{ marginBottom: '1rem' }}>
        <div
          style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: plan.color,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: 4,
          }}
        >
          {plan.name}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
          <span style={{ fontSize: '2.2rem', fontWeight: 900, color: '#f1f5f9' }}>
            ${displayPrice}
          </span>
          {plan.price > 0 && (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              /{annual ? 'mo (billed annually)' : 'month'}
            </span>
          )}
        </div>
        {annual && plan.price > 0 && (
          <div style={{ fontSize: '0.72rem', color: '#10b981', marginTop: 4 }}>
            Save ${plan.price * 12 * ANNUAL_DISCOUNT}/year
          </div>
        )}
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 8 }}>
          {plan.description}
        </p>
      </div>

      <ul style={{ listStyle: 'none', padding: 0, margin: 0, flex: 1 }}>
        {plan.features.map((feature, i) => (
          <li
            key={i}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 8,
              fontSize: '0.78rem',
              color: 'var(--text)',
              marginBottom: 8,
            }}
          >
            <span style={{ color: plan.color, fontSize: '0.9rem' }}>+</span>
            {feature}
          </li>
        ))}
      </ul>

      <div style={{ marginTop: '1.25rem' }}>
        <button
          className="btn"
          style={{
            width: '100%',
            padding: '10px 16px',
            background: plan.popular ? plan.color : 'transparent',
            border: plan.popular ? 'none' : `1px solid ${plan.color}`,
            color: plan.popular ? '#fff' : plan.color,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          {plan.cta}
        </button>
      </div>

      {/* Usage Limits */}
      <div
        style={{
          marginTop: '1rem',
          paddingTop: '1rem',
          borderTop: '1px solid var(--line)',
        }}
      >
        <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-soft)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Usage Limits
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '0.72rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Reports:</span>{' '}
            <span style={{ color: 'var(--text)' }}>{plan.limits.reports}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Alerts:</span>{' '}
            <span style={{ color: 'var(--text)' }}>{plan.limits.alerts}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Watchlists:</span>{' '}
            <span style={{ color: 'var(--text)' }}>{plan.limits.watchlists}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>API Calls:</span>{' '}
            <span style={{ color: 'var(--text)' }}>{typeof plan.limits.apiCalls === 'number' ? plan.limits.apiCalls.toLocaleString() : plan.limits.apiCalls}/mo</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Pricing() {
  const [annual, setAnnual] = useState(false)

  return (
    <>
      <Head>
        <title>Pricing | Enterprise Intelligence</title>
        <meta name="description" content="Transparent pricing for Enterprise Intelligence platform. No hidden fees." />
      </Head>

      <div className="page-wrap" style={{ maxWidth: 1000, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 900, color: '#f1f5f9', marginBottom: 8 }}>
            Simple, Transparent Pricing
          </h1>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', maxWidth: 480, margin: '0 auto 1.5rem' }}>
            No hidden fees. No surprise charges. Cancel anytime with one click.
          </p>

          {/* Annual Toggle */}
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, background: 'var(--bg-elev-1)', padding: '6px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--line)' }}>
            <span style={{ fontSize: '0.78rem', color: annual ? 'var(--text-muted)' : 'var(--text)', fontWeight: annual ? 500 : 700 }}>Monthly</span>
            <button
              onClick={() => setAnnual(!annual)}
              style={{
                width: 44,
                height: 24,
                borderRadius: 12,
                border: 'none',
                background: annual ? '#6366f1' : 'var(--line)',
                position: 'relative',
                cursor: 'pointer',
                transition: 'background 0.2s',
              }}
            >
              <div
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: '50%',
                  background: '#fff',
                  position: 'absolute',
                  top: 3,
                  left: annual ? 23 : 3,
                  transition: 'left 0.2s',
                }}
              />
            </button>
            <span style={{ fontSize: '0.78rem', color: annual ? 'var(--text)' : 'var(--text-muted)', fontWeight: annual ? 700 : 500 }}>
              Annual <span style={{ color: '#10b981' }}>(20% off)</span>
            </span>
          </div>
        </div>

        {/* Pricing Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
          {PLANS.map(plan => (
            <PricingCard key={plan.id} plan={plan} annual={annual} />
          ))}
        </div>

        {/* FAQ / Fine Print */}
        <div style={{ background: 'var(--bg-elev-1)', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '1rem' }}>
            Frequently Asked Questions
          </div>
          <div style={{ display: 'grid', gap: '1rem', fontSize: '0.78rem' }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>Can I cancel anytime?</div>
              <div style={{ color: 'var(--text-muted)' }}>Yes. Cancel with one click from your billing page. No questions asked, no cancellation fees.</div>
            </div>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>What happens when I hit my limits?</div>
              <div style={{ color: 'var(--text-muted)' }}>You will receive a warning at 80% usage. At 100%, new requests are queued until the next billing cycle or you upgrade.</div>
            </div>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>Is there a free trial?</div>
              <div style={{ color: 'var(--text-muted)' }}>Professional plan includes a 14-day free trial. No credit card required to start.</div>
            </div>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>Do you offer refunds?</div>
              <div style={{ color: 'var(--text-muted)' }}>Yes. Full refund within 30 days if you are not satisfied. Email support@enterprise-intel.com.</div>
            </div>
          </div>
        </div>

        {/* Links */}
        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <Link href="/billing" legacyBehavior><a style={{ color: 'var(--brand-hover)', marginRight: 16 }}>Manage Billing</a></Link>
          <Link href="/support" legacyBehavior><a style={{ color: 'var(--brand-hover)', marginRight: 16 }}>Contact Support</a></Link>
          <Link href="/status" legacyBehavior><a style={{ color: 'var(--brand-hover)' }}>System Status</a></Link>
        </div>
      </div>
    </>
  )
}
