const path = require('path')

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

module.exports = nextConfig
