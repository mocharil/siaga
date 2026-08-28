#!/usr/bin/env bash
# ==============================================================================
# SIAGA — OpenClaw Gateway Run Script (Bash / Linux / VPS)
# Image: ghcr.io/openclaw/openclaw:2026.7.1-2
# Digest: sha256:8789721d2e9b24b780a1504b56deb4c6bd5c7dbf96a1dd117e7c45c2ed72c8ac
# ==============================================================================

set -euo pipefail

IMAGE="ghcr.io/openclaw/openclaw:2026.7.1-2"
CONTAINER_NAME="openclaw-gateway"
PORT="18789"
VOLUME="openclaw-state"

# 1. Ensure volume exists
if ! docker volume ls -q -f name="${VOLUME}" | grep -q "${VOLUME}"; then
    echo "Creating docker volume: ${VOLUME}"
    docker volume create "${VOLUME}"
fi

# 2. Check if already running
if docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
    echo "Container '${CONTAINER_NAME}' is already running."
    exit 0
fi

# 3. Remove stopped container if exists
if docker ps -a -q -f name="${CONTAINER_NAME}" | grep -q .; then
    echo "Removing stopped container '${CONTAINER_NAME}'..."
    docker rm -f "${CONTAINER_NAME}" > /dev/null
fi

# 4. Start OpenClaw Gateway
echo "Starting OpenClaw Gateway (${IMAGE}) on 127.0.0.1:${PORT}..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "127.0.0.1:${PORT}:${PORT}" \
    -v "${VOLUME}:/home/node/.openclaw" \
    -e HOME=/home/node \
    -e OPENCLAW_HOME=/home/node \
    -e OPENCLAW_STATE_DIR=/home/node/.openclaw \
    -e OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json \
    -e OPENCLAW_CONFIG_DIR=/home/node/.openclaw \
    -e OPENCLAW_WORKSPACE_DIR=/home/node/.openclaw/workspace \
    "${IMAGE}"

echo "OpenClaw Gateway started successfully on http://127.0.0.1:${PORT}"
