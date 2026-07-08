/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './src/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#080d1a',
          1: '#0e1425',
          2: '#131c33',
          soft: '#1a2744',
        },
        brand: {
          DEFAULT: '#6ea8fe',
          strong: '#8db7ff',
          dim: 'rgba(110,168,254,0.18)',
        },
        line: 'rgba(148,163,184,0.22)',
        ok: '#34d399',
        warn: '#fbbf24',
        danger: '#f87171',
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      backdropBlur: { nav: '14px' },
      boxShadow: {
        soft: '0 14px 42px rgba(0,0,0,0.28)',
        glow: '0 0 24px rgba(110,168,254,0.18)',
        card: '0 4px 16px rgba(0,0,0,0.4)',
      },
      borderRadius: {
        sm: '10px', md: '14px', lg: '18px', xl: '22px',
      },
    },
  },
  plugins: [],
}
