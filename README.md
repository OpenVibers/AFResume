# alexfrison.net

Personal site & portfolio for Alex Frison. Built with [Astro](https://astro.build/),
fully static, **zero CDN dependencies** in production (every JS/CSS/font is
vendored under `public/assets/vendor/`).

## Quick start

```bash
npm install
npm run vendor:fetch    # downloads pinned libraries into public/assets/vendor/
npm run dev             # http://localhost:4321
npm run build           # outputs dist/
npm run preview         # preview the built site
```

## Customizing

- **Portrait:** drop a transparent PNG at `public/assets/img/alex-cutout.png`
  (~700×900). The hero will use it automatically; until then a styled
  placeholder is shown.
- **Resume PDF:** place at `public/Alex_Frison_Resume.pdf`.
- **Content:** all resume entries, projects, and skills are content
  collections under `src/content/`. Edit JSON / MDX, rebuild.
- **OG image:** `public/assets/img/og.png` (1200×630 recommended).

## Deploy (self-hosted Nginx)

```nginx
server {
  listen 443 ssl http2;
  server_name alexfrison.net www.alexfrison.net;

  root /var/www/alexfrison.net/dist;
  index index.html;

  # gzip + brotli
  gzip on;
  gzip_types text/plain text/css application/javascript application/json image/svg+xml;
  brotli on;
  brotli_types text/plain text/css application/javascript application/json image/svg+xml;

  # immutable cache for vendored assets
  location /assets/vendor/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
  }
  location /_astro/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
  }

  # HTML: no cache
  location / {
    add_header Cache-Control "no-cache";
    try_files $uri $uri/ $uri.html /404.html;
  }
}
```

Build, then sync `dist/` to the server:

```bash
npm run build
rsync -avz --delete dist/ user@host:/var/www/alexfrison.net/dist/
```

## License

Code: MIT. Vendored libraries retain their own licenses — see
`public/assets/vendor/README.md`.
