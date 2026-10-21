#!/bin/sh
# Build the site and publish it to the OVH server, where alexfrison.net is served from since 2026-10-20 (nginx:
# /etc/nginx/sites-available/alexfrison.net.conf, root /var/www/alexfrison.net; Let's Encrypt via Cloudflare DNS-01).
# GitHub Pages (.github/workflows/deploy.yml) still builds on push but no longer has the domain.
set -eu
cd "$(dirname "$0")/.."
npm run build
rsync -a --delete dist/ openvibe-ovh:alexfrison.net-dist/
ssh openvibe-ovh 'sudo rsync -a --delete ~/alexfrison.net-dist/ /var/www/alexfrison.net/ && sudo chown -R www-data:www-data /var/www/alexfrison.net'
echo "deployed: https://alexfrison.net/"
