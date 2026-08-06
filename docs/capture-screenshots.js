const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = 'https://8th-july-sprint.d11ri08de55gmb.amplifyapp.com';

const pages = [
  { name: 'dashboard', path: '/', description: 'Main Dashboard' },
  { name: 'intelligence', path: '/intelligence', description: 'Intelligence Reports' },
  { name: 'search', path: '/search', description: 'Global Search' },
  { name: 'stock', path: '/stock', description: 'Stock Analysis' },
  { name: 'valuation', path: '/valuation', description: 'Valuation DCF' },
  { name: 'company', path: '/company', description: 'Company Profiles' },
  { name: 'institutional', path: '/institutional', description: 'Institutional Holdings' },
  { name: 'gov-trading', path: '/gov-trading', description: 'Government Trading' },
  { name: 'crypto', path: '/crypto', description: 'Crypto Intelligence' },
  { name: 'graph', path: '/graph', description: 'Relationship Graph' },
  { name: 'tracking', path: '/tracking', description: 'Tracking & Alerts' },
];

async function captureScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 }
  });

  const screenshotDir = path.join(__dirname, 'screenshots');

  console.log('Starting screenshot capture...\n');

  for (const pageInfo of pages) {
    const page = await context.newPage();
    const url = `${BASE_URL}${pageInfo.path}`;

    try {
      console.log(`Capturing: ${pageInfo.description} (${url})`);
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

      // Wait a bit for any animations to settle
      await page.waitForTimeout(1500);

      const screenshotPath = path.join(screenshotDir, `${pageInfo.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: false });

      console.log(`  ✓ Saved: ${screenshotPath}`);
    } catch (error) {
      console.log(`  ✗ Error capturing ${pageInfo.description}: ${error.message}`);
    }

    await page.close();
  }

  await browser.close();
  console.log('\nScreenshot capture complete!');
}

captureScreenshots().catch(console.error);
