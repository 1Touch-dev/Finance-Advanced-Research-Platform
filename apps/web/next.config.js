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
  // Single React instance for the whole monorepo (root node_modules).
  // Nested copies under apps/web cause "Invalid hook call" even at the
  // same version — swr at root + react-dom nested = two React dispatchers.
  experimental: {
    esmExternals: false,
  },
  webpack: (config) => {
    const reactPath = path.resolve(__dirname, '../../node_modules/react')
    const reactDomPath = path.resolve(__dirname, '../../node_modules/react-dom')
    config.resolve.alias = {
      ...config.resolve.alias,
      react: reactPath,
      'react-dom': reactDomPath,
    }
    return config
  },
}

module.exports = nextConfig
