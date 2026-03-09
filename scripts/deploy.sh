#!/bin/bash
# =============================================================================
# deploy.sh — Zero-downtime deployment with automatic rollback
# Called by GitHub Actions CD after a new image is pushed to GHCR.
# =============================================================================
set -euo pipefail

APP_DIR="/opt/app"
COMPOSE="docker compose"
HEALTH_URL="http://127.0.0.1:8000/"
HEALTH_RETRIES=12
HEALTH_INTERVAL=10
IMAGE="ghcr.io/asilbeek17/dreamzone-mock"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[deploy]${NC} $*"; }
error() { echo -e "${RED}[deploy]${NC} $*"; }
warn()  { echo -e "${YELLOW}[deploy]${NC} $*"; }

cd "$APP_DIR"

# ── 1. Record current image digest for rollback ───────────────────────────────
PREVIOUS_IMAGE=$(docker inspect --format='{{.Image}}' "$(docker compose ps -q web 2>/dev/null)" 2>/dev/null || echo "none")
info "Previous image digest: $PREVIOUS_IMAGE"

# ── 2. Pull latest image ──────────────────────────────────────────────────────
info "Pulling latest image from GHCR..."
docker pull "${IMAGE}:latest"

# ── 3. Recreate web container only (db stays up) ─────────────────────────────
info "Recreating web container..."
$COMPOSE up -d --no-deps --force-recreate web

# ── 4. Health check ───────────────────────────────────────────────────────────
info "Running health checks ($HEALTH_RETRIES attempts, ${HEALTH_INTERVAL}s interval)..."
attempt=0
healthy=false

while [ $attempt -lt $HEALTH_RETRIES ]; do
    attempt=$((attempt + 1))
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" || echo "000")

    if [[ "$HTTP_CODE" =~ ^(200|301|302|303)$ ]]; then
        info "Health check passed (HTTP $HTTP_CODE) on attempt $attempt."
        healthy=true
        break
    fi

    warn "Attempt $attempt/$HEALTH_RETRIES: HTTP $HTTP_CODE — waiting ${HEALTH_INTERVAL}s..."
    sleep $HEALTH_INTERVAL
done

# ── 5. Rollback on failure ────────────────────────────────────────────────────
if [ "$healthy" = false ]; then
    error "Health check FAILED after $HEALTH_RETRIES attempts. Rolling back..."

    if [ "$PREVIOUS_IMAGE" != "none" ] && [ -n "$PREVIOUS_IMAGE" ]; then
        docker tag "$PREVIOUS_IMAGE" "${IMAGE}:rollback"
        # Update compose to use the rollback tag temporarily
        IMAGE_OVERRIDE="${IMAGE}:rollback" $COMPOSE up -d --no-deps --force-recreate web || true
        error "Rolled back to previous image: $PREVIOUS_IMAGE"
    else
        error "No previous image found. Manual intervention required."
    fi

    # Show last 50 lines of web logs for diagnosis
    error "=== Last 50 lines of web container logs ==="
    docker compose logs --tail=50 web
    exit 1
fi

# ── 6. Start all services (db + dozzle) if not running ───────────────────────
info "Ensuring all services are up..."
$COMPOSE up -d

# ── 7. Clean up dangling images ───────────────────────────────────────────────
info "Pruning dangling images..."
docker image prune -f

info "Deployment complete."
echo ""
echo "  App:  https://dzmock.uz"
echo "  Logs: https://logs.dzmock.uz"
echo ""
