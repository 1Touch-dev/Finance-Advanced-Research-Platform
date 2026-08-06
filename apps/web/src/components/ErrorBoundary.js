import React from 'react'

/**
 * Error Boundary - Catches React render errors
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          background: 'var(--bg-elev-1)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--line)',
          margin: '2rem auto',
          maxWidth: 500,
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
          <h2 style={{ color: '#f1f5f9', fontSize: '1.1rem', marginBottom: '0.5rem' }}>
            Something went wrong
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: 'var(--brand)',
              color: '#fff',
              border: 'none',
              padding: '0.5rem 1.25rem',
              borderRadius: 8,
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            Reload Page
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * API Error Display - For failed API calls
 */
export function ApiError({ message, onRetry }) {
  return (
    <div style={{
      padding: '2rem',
      textAlign: 'center',
      background: 'rgba(239, 68, 68, 0.08)',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid rgba(239, 68, 68, 0.2)',
      margin: '1rem 0',
    }}>
      <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🔌</div>
      <h3 style={{ color: '#fca5a5', fontSize: '0.95rem', marginBottom: '0.4rem', fontWeight: 700 }}>
        Connection Error
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '1rem' }}>
        {message || 'Unable to connect to the server. Please check if the backend is running.'}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            background: 'transparent',
            color: '#fca5a5',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            padding: '0.4rem 1rem',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: '0.8rem',
            fontWeight: 600,
          }}
        >
          Try Again
        </button>
      )}
    </div>
  )
}

/**
 * Loading Skeleton
 */
export function LoadingSkeleton({ rows = 3 }) {
  return (
    <div style={{ padding: '1rem 0' }}>
      {[...Array(rows)].map((_, i) => (
        <div
          key={i}
          style={{
            height: 20,
            background: 'linear-gradient(90deg, var(--bg-elev-1) 25%, var(--bg-elev-2) 50%, var(--bg-elev-1) 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s infinite',
            borderRadius: 6,
            marginBottom: '0.75rem',
            width: i === rows - 1 ? '60%' : '100%',
          }}
        />
      ))}
      <style jsx>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  )
}

/**
 * Empty State
 */
export function EmptyState({ icon = '📭', title, message }) {
  return (
    <div style={{
      padding: '3rem 2rem',
      textAlign: 'center',
      color: 'var(--text-muted)',
    }}>
      <div style={{ fontSize: '2.5rem', marginBottom: '1rem', opacity: 0.6 }}>{icon}</div>
      <h3 style={{ color: 'var(--text-soft)', fontSize: '1rem', marginBottom: '0.4rem' }}>
        {title || 'No data'}
      </h3>
      <p style={{ fontSize: '0.85rem' }}>{message}</p>
    </div>
  )
}

export default ErrorBoundary
