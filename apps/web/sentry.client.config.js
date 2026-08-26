import * as Sentry from '@sentry/nextjs'

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NEXT_PUBLIC_ENV || 'production',
    release: process.env.NEXT_PUBLIC_APP_VERSION,

    // Capture 10% of transactions for performance monitoring
    tracesSampleRate: 0.1,

    // Replay — capture 1% of sessions, 10% of sessions with errors
    replaysSessionSampleRate: 0.01,
    replaysOnErrorSampleRate: 0.1,

    integrations: [
      Sentry.replayIntegration({
        maskAllText: true,       // PII protection
        blockAllMedia: true,
      }),
      Sentry.browserTracingIntegration(),
    ],

    // Don't send errors from browser extensions or non-app origins
    allowUrls: [/localhost/, /amplifyapp\.com/, /financeintell\.duckdns\.org/],

    // Ignore common noise
    ignoreErrors: [
      'ResizeObserver loop limit exceeded',
      'Non-Error promise rejection captured',
      /^Network Error/,
      /^Request aborted/,
      /^timeout of \d+ms exceeded/,
    ],

    beforeSend(event) {
      // Strip auth tokens from request headers before sending
      if (event.request?.headers) {
        delete event.request.headers['Authorization']
        delete event.request.headers['authorization']
      }
      return event
    },
  })
}
