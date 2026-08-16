module.exports = {
  apps: [
    {
      name: 'finance-api',
      cwd: './apps/api',
      script: '../../venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 3001',
      interpreter: '../../venv/bin/python3',
      env_file: '../../.env',
      autorestart: true,
    },
    {
      name: 'finance-web',
      cwd: './apps/web',
      script: 'npm',
      args: 'run dev -- -p 3003',
      env: {
        NEXT_PUBLIC_API_URL: 'http://184.72.123.188:3001',
      },
      autorestart: true,
    },
    {
      name: 'finance-admin',
      cwd: './apps/admin',
      script: 'npx',
      args: 'serve -s build -l 3002',
      env: {
        REACT_APP_API_URL: 'http://184.72.123.188:3001',
        REACT_APP_WEB_URL: 'http://184.72.123.188:3003',
      },
      autorestart: true,
    },
    {
      name: 'finance-worker',
      cwd: './apps/worker',
      script: 'src/index.js',
      env_file: '../../.env',
      autorestart: true,
    },
    {
      name: 'rss-poller',
      cwd: './apps/api',
      script: '../../venv/bin/python3',
      args: '-m app.connectors.rss_worker --loop',
      interpreter: 'none',
      env_file: '../../.env',
      autorestart: true,
      watch: false,
    },
    // ── F-03: Big Trade Scanner ──────────────────────────────────────────────
    {
      name: 'big-trade-scanner',
      cwd: './apps/api',
      script: '../../venv/bin/python3',
      args: '-m app.scripts.run_big_trade_scan',
      interpreter: 'none',
      env_file: '../../.env',
      autorestart: true,
      watch: false,
      // Runs at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
      cron_restart: '0 */4 * * *',
      log_file: './logs/big-trade-scanner.log',
      error_file: './logs/big-trade-scanner-error.log',
    },
    // ── F-04: Investment Alert Scanner ──────────────────────────────────────
    {
      name: 'investment-alert-scanner',
      cwd: './apps/api',
      script: '../../venv/bin/python3',
      args: '-m app.scripts.run_investment_alert_scan',
      interpreter: 'none',
      env_file: '../../.env',
      autorestart: true,
      watch: false,
      // Offset 30 min from big-trade-scanner to avoid overlap
      // Runs at 00:30, 04:30, 08:30, 12:30, 16:30, 20:30 UTC
      cron_restart: '30 */4 * * *',
      log_file: './logs/investment-alert-scanner.log',
      error_file: './logs/investment-alert-scanner-error.log',
    },
    // ── #7: Freshness Engine Scanner ──────────────────────────────────────────
    {
      name: 'freshness-scanner',
      cwd: './apps/api',
      script: '../../venv/bin/python3',
      args: '-m app.scripts.run_freshness_scan --max-jobs 20',
      interpreter: 'none',
      env_file: '../../.env',
      autorestart: true,
      watch: false,
      // Runs every hour at minute 15 to avoid overlap with other scanners
      // 00:15, 01:15, 02:15, ... 23:15 UTC
      cron_restart: '15 * * * *',
      log_file: './logs/freshness-scanner.log',
      error_file: './logs/freshness-scanner-error.log',
    },
  ],
};
