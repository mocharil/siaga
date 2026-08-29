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

# 2b. Telegram token is a soft requirement — needed for T24/T25 heartbeat
# delivery, but the gateway itself should still start without it.
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    echo "WARNING: TELEGRAM_BOT_TOKEN kosong — channel Telegram tidak akan berfungsi."
fi

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
    -v "${REPO_DIR}:/workspace/siaga" \
    -e HOME=/home/node \
    -e OPENCLAW_HOME=/home/node \
    -e OPENCLAW_STATE_DIR=/home/node/.openclaw \
    -e OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json \
    -e OPENCLAW_CONFIG_DIR=/home/node/.openclaw \
    -e OPENCLAW_WORKSPACE_DIR=/home/node/.openclaw/workspace \
    -e OPENAI_API_KEY="${RESOLVED_API_KEY}" \
    -e TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}" \
    "${IMAGE}"

echo "OpenClaw Gateway started successfully on http://127.0.0.1:${PORT}"
echo "Security Notice: gateway.bind='lan' inside container, loopback protection relies on host -p 127.0.0.1:${PORT}:${PORT}."

# 7. Bootstrap Python deps for the mounted SIAGA repo, every start.
# NOT a one-time step: /home/node/.local is NOT on any persistent volume,
# so anything installed there vanishes on every container recreation
# (including the future VPS migration). This image ships Python but no
# pip and no ensurepip (venv module cannot bootstrap itself), so pip is
# fetched fresh via get-pip.py each time — no apt, no root, ~5 seconds.
echo "Bootstrapping pip + SIAGA Python dependencies inside the container..."
for i in 1 2 3 4 5; do
    if docker exec "${CONTAINER_NAME}" bash -c "
        curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py &&
        python3 /tmp/get-pip.py --user --quiet --break-system-packages &&
        ~/.local/bin/pip3 install --quiet --break-system-packages -r /workspace/siaga/requirements.txt
    "; then
        echo "SIAGA dependencies installed."
        break
    fi
    echo "Container not ready yet, retrying (${i}/5)..."
    sleep 2
done
