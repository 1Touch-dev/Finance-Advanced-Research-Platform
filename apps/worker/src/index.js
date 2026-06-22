const Queue = require('bull');
const axios = require('axios');

const redisUrl = process.env.REDIS_URL || 'redis://127.0.0.1:6379';
const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

const connectorQueue = new Queue('connector-runs', redisUrl);
const alertQueue = new Queue('alert-scan', redisUrl);

const CONNECTOR_MAP = {
  sec_edgar: 'sec',
  fec: 'fec',
  congress_gov: 'congress',
  sam_gov: 'sam',
  courtlistener: 'courtlistener',
  usaspending: 'usaspending',
  ofac: 'ofac',
  gleif: 'gleif',
  lda_gov: 'lda',
  fara: 'fara',
  govinfo: 'govinfo',
  federal_register: 'federal_register',
  regulations_gov: 'regulations',
  ecfr: 'ecfr',
  reginfo_oira: 'reginfo_oira',
  irs_990: 'irs990',
  opencorporates: 'opencorporates',
};

connectorQueue.process(async (job) => {
  const { sourceId, runId, connectorKind } = job.data;
  console.log(`Running connector ${connectorKind} source=${sourceId} run=${runId}`);
  try {
    const { spawn } = require('child_process');
    return new Promise((resolve, reject) => {
      const proc = spawn('python', [
        '-m', 'runner.cli',
        '--connector', connectorKind,
        '--source-id', String(sourceId),
        '--run-id', String(runId),
      ], { cwd: process.env.CONNECTORS_DIR || '../../packages/connectors', env: process.env });
      proc.on('close', (code) => (code === 0 ? resolve({ ok: true }) : reject(new Error(`exit ${code}`))));
    });
  } catch (e) {
    await axios.post(`${apiUrl}/sources/runs/${runId}/status`, { status: 'error', error: String(e) });
    throw e;
  }
});

alertQueue.process(async () => {
  console.log('Running alert scan');
  const scan = await axios.post(`${apiUrl}/monitor/scan`);
  const deliver = await axios.post(`${apiUrl}/monitor/deliver`);
  return { scan: scan.data, deliver: deliver.data };
});

connectorQueue.add(
  { sourceId: 1, runId: 1, connectorKind: 'sec_edgar' },
  { repeat: { cron: '0 */6 * * *' }, removeOnComplete: true }
).catch(() => {});

alertQueue.add(
  {},
  { repeat: { cron: '0 * * * *' }, removeOnComplete: true }
).catch(() => {});

console.log('Worker running — connector-runs + alert-scan queues active');
