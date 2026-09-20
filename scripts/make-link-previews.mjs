// Pre-renders the hover-preview thumbnails for every external site and internal page the site
// links to, so hovering a link never fetches a live page. Run after `npm run build` (internal
// pages are shot from dist/ served locally). Output: public/assets/img/previews/*.jpg and
// src/data/link-previews.json (key → { img, label }).
import { chromium } from '/home/workstation/OpenVibers/OpenVibe.Games/node_modules/playwright/index.mjs';
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { spawn } from 'node:child_process';

const ROOT = new URL('..', import.meta.url).pathname;
const profile = JSON.parse(readFileSync(`${ROOT}src/data/profile.json`, 'utf8'));
const OUT = `${ROOT}public/assets/img/previews`;
const W = 1280, H = 800, SCALE = 0.5; // 640x400 output

const external = [
  ...profile.network.map((n) => n.url),
  'https://powerchat.live',
  'https://github.com/OpenVibers',
  'https://alexfrison.net',
];
const internal = ['/', '/resume/', '/portfolio/', ...readdirSync(`${ROOT}dist/portfolio`).filter((d) => existsSync(`${ROOT}dist/portfolio/${d}/index.html`)).map((d) => `/portfolio/${d}/`)];

const server = spawn('python3', ['-m', 'http.server', '4399'], { cwd: `${ROOT}dist`, stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 800));

const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', args: ['--no-sandbox'] });
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: SCALE, colorScheme: 'dark',
  userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' });
const map = {};
const shoot = async (url, key, label, file) => {
  const page = await ctx.newPage();
  try {
    await page.addInitScript(() => { try { localStorage.setItem('ov_theme_asked', '1'); } catch {} });
    await page.goto(url, { waitUntil: 'networkidle', timeout: 25000 }).catch(() => {});
    await page.waitForTimeout(url.startsWith('http://localhost') ? 2500 : 1500);
    await page.screenshot({ path: `${OUT}/${file}.jpg`, type: 'jpeg', quality: 74, clip: { x: 0, y: 0, width: W, height: H } });
    map[key] = { img: `/assets/img/previews/${file}.jpg`, label };
    console.log('ok', key);
  } catch (e) { console.log('FAIL', key, e.message); }
  await page.close();
};
for (const u of external) {
  const host = new URL(u).host.replace(/^www\./, '');
  await shoot(u, host, host, host.replace(/[^a-z0-9.-]/gi, '_'));
}
for (const p of internal) {
  const label = p === '/' ? 'alexfrison.net' : `alexfrison.net${p.replace(/\/$/, '')}`;
  await shoot(`http://localhost:4399${p}`, `path:${p.replace(/\/$/, '') || '/'}`, label, 'local' + (p.replace(/\/$/, '') || '/home').replace(/\//g, '_'));
}
await browser.close();
server.kill();
writeFileSync(`${ROOT}src/data/link-previews.json`, JSON.stringify(map, null, 2) + '\n');
console.log('wrote', Object.keys(map).length, 'previews');
