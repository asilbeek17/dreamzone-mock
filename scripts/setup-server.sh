#!/bin/bash
# =============================================================================
# setup-server.sh — Idempotent server bootstrap for dzmock.uz
# Run as root on a fresh Ubuntu 22.04 / 24.04 VPS.
# Safe to run multiple times.
# =============================================================================
set -euo pipefail

DOMAIN="dzmock.uz"
LOG_DOMAIN="logs.dzmock.uz"
APP_DIR="/opt/app"
STATIC_DIR="/opt/app/staticfiles"
MEDIA_DIR="/opt/app/media"
SCRIPTS_DIR="/opt/app/scripts"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }

# ── 1. System packages ────────────────────────────────────────────────────────
info "Updating system packages..."
apt-get update -q
apt-get install -y -q \
    ca-certificates curl gnupg lsb-release \
    nginx certbot python3-certbot-nginx \
    apache2-utils \
    ufw \
    jq git

# ── 2. Docker ─────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -q
    apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
    success "Docker installed."
else
    success "Docker already installed: $(docker --version)"
fi

# ── 3. UFW firewall ───────────────────────────────────────────────────────────
info "Configuring UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'
ufw --force enable
success "UFW active."

# ── 4. Application directories ────────────────────────────────────────────────
info "Creating application directories..."
mkdir -p "$APP_DIR" "$STATIC_DIR" "$MEDIA_DIR" "$SCRIPTS_DIR" /var/www/certbot
success "Directories ready."

# ── 5. Diffie-Hellman parameters ──────────────────────────────────────────────
if [ ! -f /etc/nginx/dhparam.pem ]; then
    info "Generating DH parameters (4096-bit, this takes a few minutes)..."
    openssl dhparam -out /etc/nginx/dhparam.pem 4096
    success "DH params generated."
else
    success "DH params already exist."
fi

# ── 6. Nginx configuration ────────────────────────────────────────────────────
info "Installing Nginx config..."
cp "$APP_DIR/nginx/dzmock.uz.conf" /etc/nginx/sites-available/dzmock.uz.conf
ln -sf /etc/nginx/sites-available/dzmock.uz.conf /etc/nginx/sites-enabled/dzmock.uz.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
success "Nginx configured."

# ── 7. Dozzle credentials (generate once, never overwrite) ───────────────────
DOZZLE_CREDS_FILE="$APP_DIR/.dozzle_credentials"
if [ ! -f "$DOZZLE_CREDS_FILE" ]; then
    info "Generating Dozzle credentials..."
    DOZZLE_USERNAME=$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom | head -c8)
    DOZZLE_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9!@#%^&*' </dev/urandom | head -c24)
    echo "DOZZLE_USERNAME=${DOZZLE_USERNAME}" > "$DOZZLE_CREDS_FILE"
    echo "DOZZLE_PASSWORD=${DOZZLE_PASSWORD}" >> "$DOZZLE_CREDS_FILE"
    chmod 600 "$DOZZLE_CREDS_FILE"
    success "Dozzle credentials saved to $DOZZLE_CREDS_FILE"
else
    source "$DOZZLE_CREDS_FILE"
    success "Dozzle credentials already exist."
fi

# Create/update Nginx htpasswd for Dozzle
source "$DOZZLE_CREDS_FILE"
htpasswd -cb /etc/nginx/.htpasswd_dozzle "$DOZZLE_USERNAME" "$DOZZLE_PASSWORD"
chmod 640 /etc/nginx/.htpasswd_dozzle
nginx -t && systemctl reload nginx

# ── 8. SSL certificates ───────────────────────────────────────────────────────
info "Obtaining SSL certificates..."
# Temporarily serve HTTP for ACME challenge
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    certbot certonly --nginx \
        -d "$DOMAIN" -d "www.$DOMAIN" \
        --non-interactive --agree-tos \
        --email "admin@${DOMAIN}" \
        --redirect
    success "SSL certificate issued for $DOMAIN."
else
    success "SSL certificate already exists for $DOMAIN."
fi

if [ ! -d "/etc/letsencrypt/live/$LOG_DOMAIN" ]; then
    certbot certonly --nginx \
        -d "$LOG_DOMAIN" \
        --non-interactive --agree-tos \
        --email "admin@${DOMAIN}" \
        --redirect
    success "SSL certificate issued for $LOG_DOMAIN."
else
    success "SSL certificate already exists for $LOG_DOMAIN."
fi

# Reload Nginx with full SSL config
nginx -t && systemctl reload nginx

# ── 9. Auto-renew SSL (cron) ──────────────────────────────────────────────────
RENEW_CRON="0 3 * * * certbot renew --quiet && systemctl reload nginx"
(crontab -l 2>/dev/null | grep -v 'certbot renew'; echo "$RENEW_CRON") | crontab -
success "SSL auto-renewal cron set."

# ── 10. Cleanup cron ──────────────────────────────────────────────────────────
CLEANUP_CRON="0 2 * * 0 bash $SCRIPTS_DIR/cleanup.sh >> /var/log/cleanup.log 2>&1"
(crontab -l 2>/dev/null | grep -v 'cleanup.sh'; echo "$CLEANUP_CRON") | crontab -
success "Weekly cleanup cron set."

# ── 11. SSH deploy key ────────────────────────────────────────────────────────
DEPLOY_KEY="/root/.ssh/id_deploy"
if [ ! -f "$DEPLOY_KEY" ]; then
    info "Generating SSH deploy key..."
    ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N "" -C "github-actions-deploy"
    success "Deploy key generated."
fi

# ── FINAL SUMMARY ─────────────────────────────────────────────────────────────
source "$DOZZLE_CREDS_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SETUP COMPLETE — dzmock.uz"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  App URL:     https://dzmock.uz"
echo "  Logs URL:    https://logs.dzmock.uz"
echo ""
echo "  Dozzle Username : $DOZZLE_USERNAME"
echo "  Dozzle Password : $DOZZLE_PASSWORD"
echo ""
echo "  ── GitHub Actions Secrets to add ───────────────────────────────────"
echo "  SERVER_HOST     : $(curl -s ifconfig.me 2>/dev/null || echo '109.199.110.218')"
echo "  SERVER_USER     : root"
echo "  SERVER_SSH_KEY  : (paste the private key below)"
echo ""
cat "$DEPLOY_KEY"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Add this PUBLIC key to GitHub → Settings → Deploy keys:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat "${DEPLOY_KEY}.pub"
echo ""
