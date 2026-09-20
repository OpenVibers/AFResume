#!/usr/bin/env node
// Downloads pinned, license-clean copies of frontend libraries into
// public/assets/vendor/. Re-run with `npm run vendor:fetch` after editing.

import { mkdir, writeFile, access } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', 'public', 'assets', 'vendor');

const FILES = [
  // Inter font (OFL)
  ['https://cdn.jsdelivr.net/npm/@fontsource/inter@5.1.0/files/inter-latin-400-normal.woff2', 'fonts/inter-400.woff2'],
  ['https://cdn.jsdelivr.net/npm/@fontsource/inter@5.1.0/files/inter-latin-600-normal.woff2', 'fonts/inter-600.woff2'],
  ['https://cdn.jsdelivr.net/npm/@fontsource/inter@5.1.0/files/inter-latin-800-normal.woff2', 'fonts/inter-800.woff2'],
  // jsPDF (MIT) — client-side themed résumé export
  ['https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', 'jspdf/jspdf.umd.min.js'],
  // Space Grotesk (OFL)
  ['https://cdn.jsdelivr.net/npm/@fontsource/space-grotesk@5.1.0/files/space-grotesk-latin-500-normal.woff2', 'fonts/space-grotesk-500.woff2'],
  ['https://cdn.jsdelivr.net/npm/@fontsource/space-grotesk@5.1.0/files/space-grotesk-latin-700-normal.woff2', 'fonts/space-grotesk-700.woff2'],
];

async function exists(p) {
  try { await access(p); return true; } catch { return false; }
}

async function fetchOne(url, rel) {
  const dest = join(ROOT, rel);
  if (await exists(dest)) {
    console.log(`= ${rel}`);
    return;
  }
  await mkdir(dirname(dest), { recursive: true });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await writeFile(dest, buf);
  console.log(`+ ${rel} (${(buf.length / 1024).toFixed(1)} KB)`);
}

async function main() {
  await mkdir(ROOT, { recursive: true });
  for (const [url, rel] of FILES) {
    try { await fetchOne(url, rel); }
    catch (e) { console.error(`! ${rel}: ${e.message}`); }
  }
  await writeFile(join(ROOT, 'README.md'),
`# Vendored Libraries

All libraries here are downloaded locally so the site ships with **zero CDN
dependencies**. Re-fetch with \`npm run vendor:fetch\`.

| Library | Version | License |
|---|---|---|
| Lenis | 1.1.13 | MIT |
| Font Awesome Free (CSS + webfonts) | 6.x | CC BY 4.0 / SIL OFL 1.1 / MIT |
| Inter | 5.1.0 | SIL OFL 1.1 |
| Space Grotesk | 5.1.0 | SIL OFL 1.1 |
`);
  console.log('done.');
}

main().catch(e => { console.error(e); process.exit(1); });
