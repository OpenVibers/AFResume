#!/usr/bin/env bash
# deploy.sh — Build & deploy alexfrison.net to Nginx static hosting
# Usage: ./deploy/deploy.sh [--skip-build]
# Requirements on server: git, node >=18, npm, nginx

set -euo pipefail

REPO_URL="git@github.com:HoboStreamer/AFResume.git"
SITE_DIR="/var/www/alexfrison.net"
NGINX_CONF="/etc/nginx/sites-available/alexfrison.net"
NGINX_ENABLED="/etc/nginx/sites-enabled/alexfrison.net"
DOMAIN="alexfrison.net"

# ── Helper ────────────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ── 1. Clone or pull ──────────────────────────────────────────────────────────
if [[ -d "$SITE_DIR/.git" ]]; then
    info "Pulling latest from origin/main..."
    git -C "$SITE_DIR" pull origin main
else
    info "Cloning $REPO_URL → $SITE_DIR..."
    sudo mkdir -p "$SITE_DIR"
    sudo chown "$USER":"$USER" "$SITE_DIR"
    git clone "$REPO_URL" "$SITE_DIR"
fi

# ── 2. Install deps & build ───────────────────────────────────────────────────
if [[ "${1:-}" != "--skip-build" ]]; then
    info "Installing npm dependencies..."
    npm --prefix "$SITE_DIR" ci --prefer-offline

    info "Building Astro site..."
    npm --prefix "$SITE_DIR" run build

    ok "Build complete → $SITE_DIR/dist"
fi

# ── 3. Install nginx config ───────────────────────────────────────────────────
if [[ ! -f "$NGINX_CONF" ]]; then
    info "Installing nginx config..."
    sudo cp "$SITE_DIR/deploy/nginx.conf" "$NGINX_CONF"
    sudo ln -sf "$NGINX_CONF" "$NGINX_ENABLED"
    ok "Nginx config installed."
else
    info "Nginx config already present at $NGINX_CONF — skipping copy."
    info "To update it manually: sudo cp $SITE_DIR/deploy/nginx.conf $NGINX_CONF"
fi

# ── 4. Test & reload nginx ────────────────────────────────────────────────────
info "Testing nginx config..."
sudo nginx -t

info "Reloading nginx..."
sudo systemctl reload nginx
ok "Nginx reloaded."

# ── 5. SSL reminder ───────────────────────────────────────────────────────────
if [[ ! -d "/etc/letsencrypt/live/$DOMAIN" ]]; then
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────┐"
    echo "  │  SSL cert not found. Run certbot to finish setup:       │"
    echo "  │                                                         │"
    echo "  │  sudo apt install certbot python3-certbot-nginx         │"
    echo "  │  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN  │"
    echo "  └─────────────────────────────────────────────────────────┘"
    echo ""
fi

ok "Deploy complete. Visit https://$DOMAIN"
