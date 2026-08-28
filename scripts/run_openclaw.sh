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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 1. Resolve .env file if available
if [[ -f "${REPO_DIR}/.env" ]]; then
    # shellcheck disable=SC1091
    source "${REPO_DIR}/.env"
elif [[ -f "${REPO_DIR}/../.env" ]]; then
    # shellcheck disable=SC1091
    source "${REPO_DIR}/../.env"
fi

# 2. Fail-fast validation: LLM API key MUST be set
RESOLVED_API_KEY="${OPENAI_API_KEY:-${LLM_API_KEY:?Error: LLM_API_KEY atau OPENAI_API_KEY belum di-set di environment}}"

# 3. Ensure volume exists
if ! docker volume ls -q -f name="${VOLUME}" | grep -q "${VOLUME}"; then
    echo "Creating docker volume: ${VOLUME}"
    docker volume create "${VOLUME}" > /dev/null
fi

# 4. Check if already running
if docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
    echo "Container '${CONTAINER_NAME}' is already running on http://127.0.0.1:${PORT}"
    exit 0
fi

# 5. Remove stopped container if exists
if docker ps -a -q -f name="${CONTAINER_NAME}" | grep -q .; then
    echo "Removing stopped container '${CONTAINER_NAME}'..."
    docker rm -f "${CONTAINER_NAME}" > /dev/null
fi

# 6. Start OpenClaw Gateway
echo "Starting OpenClaw Gateway (${IMAGE}) strictly on 127.0.0.1:${PORT}..."
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
    -e OPENAI_API_KEY="${RESOLVED_API_KEY}" \
    "${IMAGE}"

echo "OpenClaw Gateway started successfully on http://127.0.0.1:${PORT}"
echo "Security Notice: gateway.bind='lan' inside container, loopback protection relies on host -p 127.0.0.1:${PORT}:${PORT}."
