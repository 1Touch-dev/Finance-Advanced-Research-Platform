const path = require('path')
const { withSentryConfig } = require('@sentry/nextjs')

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  webpack: (config) => {
    // Force all React imports (including hoisted deps like swr living in the
    // monorepo root node_modules) to resolve to this app's own React copy.
    // Prevents "Invalid hook call" errors caused by duplicate React copies
    // in an npm workspaces monorepo (apps/admin pins react@17, apps/web needs react@18).
    config.resolve.alias = {
      ...config.resolve.alias,
      react: path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
    }
    return config
  },
}

// Only wrap with Sentry when a DSN is configured — keeps local builds clean
const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN
if (SENTRY_DSN) {
  module.exports = withSentryConfig(nextConfig, {
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    // Upload source maps silently; don't block the build on Sentry failures
    silent: true,
    // Disable Sentry CLI auto-instrumentation (we do it manually in sentry.*.config.js)
    autoInstrumentServerFunctions: false,
    // Static export doesn't support server-side Sentry tunnel
    tunnelRoute: undefined,
    // Don't tree-shake Sentry in dev (faster builds)
    disableLogger: process.env.NODE_ENV === 'production',
  })
} else {
  module.exports = nextConfig
}
