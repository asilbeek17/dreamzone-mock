#!/bin/bash
# =============================================================================
# cleanup.sh — Weekly deep cleanup of Docker images, containers, and logs
# Scheduled via cron every Sunday at 02:00
# =============================================================================
set -euo pipefail

echo "=== [cleanup] Started at $(date) ==="

# Remove stopped containers
CONTAINERS=$(docker ps -aq --filter status=exited --filter status=created 2>/dev/null || true)
if [ -n "$CONTAINERS" ]; then
    echo "[cleanup] Removing $(echo "$CONTAINERS" | wc -w) stopped container(s)..."
    docker rm $CONTAINERS
else
    echo "[cleanup] No stopped containers."
fi

# Remove dangling images (<none>:<none>)
docker image prune -f
echo "[cleanup] Dangling images pruned."

# Remove images older than 7 days that are not currently used
docker image prune -a --force --filter "until=168h"
echo "[cleanup] Old unused images pruned."

# Remove unused volumes (be conservative — only anonymous ones)
docker volume prune -f
echo "[cleanup] Unused anonymous volumes pruned."

# Remove unused networks
docker network prune -f
echo "[cleanup] Unused networks pruned."

# Truncate Docker daemon logs (keep last 100MB)
DOCKER_LOG="/var/lib/docker/containers"
if [ -d "$DOCKER_LOG" ]; then
    find "$DOCKER_LOG" -name "*.log" -size +100M -exec truncate --size=50M {} \;
    echo "[cleanup] Large container logs truncated."
fi

echo "=== [cleanup] Finished at $(date) ==="
