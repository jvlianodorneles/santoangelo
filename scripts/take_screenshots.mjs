import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, resolve } from 'node:path';
import { chromium } from 'playwright';

const ROOT = resolve(import.meta.dirname, '..', 'site');
const TYPES = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.webp': 'image/webp', '.svg': 'image/svg+xml',
};

function serve() {
  const server = createServer(async (req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (p === '/') p = '/index.html';
    const filePath = join(ROOT, p);
    try {
      const data = await readFile(filePath);
      res.writeHead(200, { 'content-type': TYPES[extname(filePath)] || 'application/octet-stream' }).end(data);
    } catch {
      res.writeHead(404).end();
    }
  });
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(server)));
}

async function main() {
  const server = await serve();
  const port = server.address().port;
  console.log(`Serving site on http://127.0.0.1:${port}`);

  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  
  // 1. Overview screenshot
  console.log('Capturing overview screenshot...');
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.waitForTimeout(4000); // allow tiles and traffic to settle
  await page.screenshot({ path: join(ROOT, '..', 'out', 'screenshot_overview.png') });
  console.log('Saved out/screenshot_overview.png');

  // 2. Zoom in closer to Catedral Angelopolitana
  console.log('Capturing close-up of Catedral Angelopolitana...');
  for (let i = 0; i < 3; i++) {
    await page.click('#zoom-in');
    await page.waitForTimeout(600);
  }
  await page.waitForTimeout(2000);
  await page.screenshot({ path: join(ROOT, '..', 'out', 'screenshot_catedral_zoom.png') });
  console.log('Saved out/screenshot_catedral_zoom.png');

  // 3. Open Place Card for Catedral
  console.log('Clicking Catedral hotspot card...');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('#places button')).find(b => b.textContent.includes('Catedral'));
    if (btn) btn.click();
  });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: join(ROOT, '..', 'out', 'screenshot_catedral_card.png') });
  console.log('Saved out/screenshot_catedral_card.png');

  // 4. Night / Evening mode
  console.log('Capturing night mode screenshot...');
  await page.click('#evening');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: join(ROOT, '..', 'out', 'screenshot_night_mode.png') });
  console.log('Saved out/screenshot_night_mode.png');

  await browser.close();
  server.close();
  console.log('All screenshots captured successfully!');
}

main().catch(console.error);
