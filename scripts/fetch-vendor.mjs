#!/usr/bin/env node
// Downloads pinned, license-clean copies of frontend libraries into
// public/assets/vendor/. Re-run with `npm run vendor:fetch` after editing.

import { mkdir, writeFile, access } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', 'public', 'assets', 'vendor');

const FILES = [
  // GSAP 3.12.5 + ScrollTrigger (MIT-equivalent free for non-Club uses)
  ['https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js', 'gsap/gsap.min.js'],
  ['https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js', 'gsap/ScrollTrigger.min.js'],
  // Lenis 1.1.13 (MIT)
  ['https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js', 'lenis/lenis.min.js'],
  ['https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.css', 'lenis/lenis.css'],
  // Splitting 1.0.6 (MIT)
  ['https://cdn.jsdelivr.net/npm/splitting@1.0.6/dist/splitting.min.js', 'splitting/splitting.min.js'],
  ['https://cdn.jsdelivr.net/npm/splitting@1.0.6/dist/splitting.css', 'splitting/splitting.css'],
  ['https://cdn.jsdelivr.net/npm/splitting@1.0.6/dist/splitting-cells.css', 'splitting/splitting-cells.css'],
  // tsparticles slim 3.5.0 (MIT)
  ['https://cdn.jsdelivr.net/npm/@tsparticles/slim@3.5.0/tsparticles.slim.bundle.min.js', 'tsparticles/tsparticles.slim.bundle.min.js'],
  // Swiper 11.1.14 (MIT)
  ['https://cdn.jsdelivr.net/npm/swiper@11.1.14/swiper-bundle.min.js', 'swiper/swiper-bundle.min.js'],
  ['https://cdn.jsdelivr.net/npm/swiper@11.1.14/swiper-bundle.min.css', 'swiper/swiper-bundle.min.css'],
  // Lottie-web 5.12.2 (MIT)
  ['https://cdn.jsdelivr.net/npm/lottie-web@5.12.2/build/player/lottie_light.min.js', 'lottie/lottie_light.min.js'],
  // Inter font (OFL)
  ['https://cdn.jsdelivr.net/npm/@fontsource/inter@5.1.0/files/inter-latin-400-normal.woff2', 'fonts/inter-400.woff2'],
  ['https://cdn.jsdelivr.net/npm/@fontsource/inter@5.1.0/files/inter-latin-600-normal.woff2', 'fonts/inter-600.woff2'],
  ['https://cdn.jsdelivr.net/npm/@fontsource/inter@5.1.0/files/inter-latin-800-normal.woff2', 'fonts/inter-800.woff2'],
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
| GSAP + ScrollTrigger | 3.12.5 | GreenSock Standard "No Charge" License (free for non-commercial; see https://gsap.com/standard-license/) |
| Lenis | 1.1.13 | MIT |
| Splitting.js | 1.0.6 | MIT |
| tsparticles (slim) | 3.5.0 | MIT |
| Swiper | 11.1.14 | MIT |
| Lottie-web (light) | 5.12.2 | MIT |
| Inter | 5.1.0 | SIL OFL 1.1 |
| Space Grotesk | 5.1.0 | SIL OFL 1.1 |
`);
  console.log('done.');
}

main().catch(e => { console.error(e); process.exit(1); });
