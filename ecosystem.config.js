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
  ],
};
