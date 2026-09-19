# alexfrison.net

Personal site, portfolio and resume for Alex Frison. Built with [Astro](https://astro.build/),
fully static, **zero CDN dependencies** in production (fonts, icons and the one JS library are
vendored under `public/assets/vendor/`). Deployed to GitHub Pages on every push to `main`
(`.github/workflows/deploy.yml`), served at https://alexfrison.net via the `public/CNAME` file.

## Quick start

```bash
npm install
npm run dev             # http://localhost:4321
npm run build           # outputs dist/
npm run preview         # preview the built site
npm run vendor:fetch    # re-download pinned vendor libraries (only needed after editing the list)
npm run resume:pdf      # regenerate public/Alex_Frison_Resume_Sep_2026.pdf (needs python3 + reportlab)
```

## Where the content lives

Everything the site and the PDF say comes from one set of files, so they never drift:

| What | Where |
|---|---|
| Name, pitch, contact, metrics, network tiles, "open to" | `src/data/profile.json` |
| Roles / experience | `src/content/experience/*.json` (sorted by `order`) |
| Skill groups | `src/content/skills/*.json` |
| Projects and case notes | `src/content/projects/*.mdx` (frontmatter + body) |
| Site screenshots for the network section | `public/assets/img/sites/*.webp` |
| Portrait | `public/assets/img/me-cut1.png`, `me-cut2.png` |

Edit JSON or MDX, run `npm run build`, and push. To refresh the PDF after a content change run
`npm run resume:pdf` and commit the regenerated file (the filename is read from
`profile.resumePdf`, so bump it there when you want a new dated version).

## Structure

- `src/layouts/Base.astro`: head, SEO and JSON-LD, theme boot, smooth scroll (Lenis), reveal
  animations, custom cursor, spotlight and tilt cards, magnetic buttons.
- `src/components/`: `Hero` (aurora canvas, kinetic name, scramble rotator), `Metrics` (count-up),
  `Marquee`, `Now`, `Network` (bento + architecture diagram), `ProjectGrid` (filterable),
  `Timeline`, `Skills`, `Contact`, `Nav`, `Footer`.
- `src/pages/`: `index`, `resume`, `portfolio`, `portfolio/[slug]`, `404`.
- `resume/build_resume.py`: reportlab PDF builder driven by the same content files.
- `scripts/fetch-vendor.mjs`: downloads the pinned vendor files.

## Deploy

Push to `main`. The workflow builds with Node 20 and publishes `dist/` to GitHub Pages. The custom
domain is configured in the repository's Pages settings and pinned by `public/CNAME`.

## License

Code: MIT. Vendored libraries retain their own licenses, see `public/assets/vendor/README.md`.
Content, copy and images are © Alex Frison.
