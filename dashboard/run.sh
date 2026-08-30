#!/usr/bin/env bash
# ==============================================================================
# SIAGA Dashboard Runner (D4)
# Binds strictly to 127.0.0.1:8000 for local / SSH-tunneled access.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

echo "================================================================="
echo "Starting SIAGA Security Monitoring Dashboard"
echo "URL: http://127.0.0.1:8000"
echo "Security: Strictly Read-Only Mode (SQLite ?mode=ro, localhost only)"
echo "================================================================="

cd "$PROJECT_ROOT"
exec python3 -m uvicorn dashboard.api:app --host 127.0.0.1 --port 8000 --log-level info
