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
  ...(profile.networkPlanned || []).map((n) => n.url),
  'https://powerchat.live',
  'https://github.com/OpenVibers',
  'https://alexfrison.net',
];
const internal = ['/', '/resume/', '/portfolio/', ...readdirSync(`${ROOT}dist/portfolio`).filter((d) => existsSync(`${ROOT}dist/portfolio/${d}/index.html`)).map((d) => `/portfolio/${d}/`)];

// Every in-page anchor the built site links to (nav items, "See the network", skip links...) gets
// its own shot, scrolled to that section, so hovering /#experience previews the Experience
// section rather than the top of the home page.
const hashTargets = new Map(); // "path#hash" -> { path, hash }
const walk = (dir) => readdirSync(dir, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(`${dir}/${e.name}`) : e.name.endsWith('.html') ? [`${dir}/${e.name}`] : []);
for (const file of walk(`${ROOT}dist`)) {
  const pagePath = file.replace(`${ROOT}dist`, '').replace(/index\.html$/, '') || '/';
  const html = readFileSync(file, 'utf8');
  for (const m of html.matchAll(/href="((?:\/[a-z0-9\-\/]*)?)#([a-z0-9\-]+)"/gi)) {
    const path = m[1] ? (m[1].endsWith('/') ? m[1] : m[1] + '/') : pagePath;
    if (m[2] === 'main' || !existsSync(`${ROOT}dist${path}index.html`)) continue; // #main is the skip link
    hashTargets.set(`${path}#${m[2]}`, { path, hash: m[2] });
  }
}

const server = spawn('python3', ['-m', 'http.server', '4399'], { cwd: `${ROOT}dist`, stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 800));

const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', args: ['--no-sandbox'] });
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: SCALE, colorScheme: 'dark',
  userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' });
const map = {};
const shoot = async (url, key, label, file, hash) => {
  const page = await ctx.newPage();
  try {
    await page.addInitScript(() => { try { localStorage.setItem('ov_theme_asked', '1'); } catch {} });
    await page.goto(url, { waitUntil: 'networkidle', timeout: 25000 }).catch(() => {});
    await page.waitForTimeout(url.startsWith('http://localhost') ? 2500 : 1500);
    if (hash) {
      const found = await page.evaluate((id) => {
        const el = document.getElementById(id); if (!el) return false;
        const y = el.getBoundingClientRect().top + scrollY - 84;
        if (window.__lenis) window.__lenis.scrollTo(y, { immediate: true }); else scrollTo(0, y);
        return true;
      }, hash);
      if (!found) throw new Error('no #' + hash);
      await page.waitForTimeout(1600); // let reveal animations finish
    }
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
for (const { path, hash } of hashTargets.values()) {
  const short = path.replace(/\/$/, '') || '/';
  await shoot(`http://localhost:4399${path}`, `path:${short}#${hash}`, `alexfrison.net${short === '/' ? '' : short}#${hash}`, 'local' + (short === '/' ? '/home' : short).replace(/\//g, '_') + '__' + hash, hash);
}
await browser.close();
server.kill();
writeFileSync(`${ROOT}src/data/link-previews.json`, JSON.stringify(map, null, 2) + '\n');
console.log('wrote', Object.keys(map).length, 'previews');
