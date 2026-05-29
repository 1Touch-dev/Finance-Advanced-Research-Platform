const Queue = require('bull');
const redisUrl = process.env.REDIS_URL || 'redis://127.0.0.1:6379';
const myQueue = new Queue('myQueue', redisUrl);

myQueue.process(async (job) => {
  console.log(`Processing job ${job.id}`);
  return Promise.resolve();
});

console.log('Worker is running...');