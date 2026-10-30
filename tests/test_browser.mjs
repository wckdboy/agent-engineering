// Run with playwright-core installed, or set PLAYWRIGHT_MODULE to its index.mjs.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : 'playwright-core');
const root = fileURLToPath(new URL('../site/', import.meta.url));
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
const server = createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
    assert(file.startsWith(root));
    res.setHeader('Content-Type', types[extname(file)] || 'application/octet-stream');
    res.end(await readFile(file));
  } catch { res.writeHead(404); res.end('Not found'); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const failures = [];
function check(ok, name, detail = '') {
  if (!ok) failures.push(`${name}: ${detail}`);
}
async function contrast(locator, backgroundLocator = locator) {
  const color = await locator.evaluate(el => getComputedStyle(el).color);
  const background = await backgroundLocator.evaluate(el => getComputedStyle(el).backgroundColor);
  function luminance(value) {
    const rgb = value.match(/[\d.]+/g).slice(0, 3).map(v => {
      const n = Number(v) / 255;
      return n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4;
    });
    return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2];
  }
  const a = luminance(color), b = luminance(background);
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
}
try {
  if (process.env.QA_SHOTS) await mkdir(process.env.QA_SHOTS, { recursive: true });
  for (const theme of ['light', 'dark']) {
    for (const width of [1440, 1100, 1000, 861, 860, 390, 320]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, reducedMotion: 'reduce' });
      const page = await context.newPage();
      page.on('pageerror', error => failures.push(error.message));
      await page.goto(origin);
      await page.evaluate(t => {
        localStorage.setItem('agenteng-theme', t);
        document.documentElement.dataset.theme = t;
      }, theme);
      await page.waitForSelector('.skill-card');
      const id = `${theme}/${width}`;
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${id} overflow`);
      const skip = page.locator('.skip-link');
      await skip.focus();
      const skipRatio = await contrast(skip);
      check(skipRatio >= 4.5, `${id} skip-link contrast`, skipRatio);
      const inline = page.locator('.section-intro a[href="./creed.md"]');
      check((await inline.evaluate(el => getComputedStyle(el).textDecorationLine)).includes('underline'), `${id} inline-link cue`);
      const sidebar = page.locator('.sidebar');
      const menu = page.locator('#menu-toggle');
      check(await sidebar.isVisible() || await menu.isVisible(), `${id} section navigation`);
      if (!(await sidebar.isVisible()) && await menu.isVisible()) await menu.click();
      check(await page.locator('.side-nav a[href="#principles"]').isVisible(), `${id} principles reachable`);
      check(await page.locator('.side-nav a[href="#repos"]').isVisible(), `${id} repositories reachable`);
      if (await menu.isVisible() && await sidebar.isVisible()) await menu.click();
      if (width === 1440 || width === 320) {
        await page.locator('.skill-card').first().click();
        await page.waitForSelector('#skill-drawer:not([hidden])');
        await page.keyboard.press('Escape');
        check(!(await page.locator('.drawer').isVisible()), `${id} skill dismiss`);
      }
      if (process.env.QA_SHOTS && [1440, 1000, 320].includes(width)) await page.screenshot({ path: `${process.env.QA_SHOTS}/creed-${theme}-${width}.png` });
      await page.goto(`${origin}/docs/README.agents.html`);
      await page.evaluate(t => { document.documentElement.dataset.theme = t; }, theme);
      const codeRatio = await contrast(page.locator('.doc pre code').first(), page.locator('.doc pre').first());
      check(codeRatio >= 4.5, `${id} documentation code contrast`, codeRatio);
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${id} documentation overflow`);
      await context.close();
    }
  }
} finally {
  await browser.close();
  await new Promise(r => server.close(r));
}
assert.deepEqual(failures, [], failures.join('\n'));
console.log('PASS: 14 theme/viewport profiles, contrast, inline links, navigation, documentation and skill dismissal');
