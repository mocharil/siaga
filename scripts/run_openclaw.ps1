# ==============================================================================
# SIAGA — OpenClaw Gateway Run Script (PowerShell / Windows)
# Image: ghcr.io/openclaw/openclaw:2026.7.1-2
# Digest: sha256:8789721d2e9b24b780a1504b56deb4c6bd5c7dbf96a1dd117e7c45c2ed72c8ac
# ==============================================================================

[CmdletBinding()]
param(
    [string]$Image = "ghcr.io/openclaw/openclaw:2026.7.1-2",
    [string]$ContainerName = "openclaw-gateway",
    [int]$Port = 18789,
    [string]$Volume = "openclaw-state"
)

# 1. Ensure volume exists
$volCheck = docker volume ls -q -f name=$Volume
if (-not $volCheck) {
    Write-Host "Creating docker volume: $Volume"
    docker volume create $Volume
}

# 2. Check if container is already running
$running = docker ps -q -f name=$ContainerName
if ($running) {
    Write-Host "Container '$ContainerName' is already running."
    exit 0
}

# 3. Remove existing stopped container
$exists = docker ps -a -q -f name=$ContainerName
if ($exists) {
    Write-Host "Removing stopped container '$ContainerName'..."
    docker rm -f $ContainerName | Out-Null
}

# 4. Start OpenClaw Gateway container
Write-Host "Starting OpenClaw Gateway ($Image) on 127.0.0.1:$Port..."
docker run -d `
    --name $ContainerName `
    --restart unless-stopped `
    -p "127.0.0.1:${Port}:${Port}" `
    -v "${Volume}:/home/node/.openclaw" `
    -e HOME=/home/node `
    -e OPENCLAW_HOME=/home/node `
    -e OPENCLAW_STATE_DIR=/home/node/.openclaw `
    -e OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json `
    -e OPENCLAW_CONFIG_DIR=/home/node/.openclaw `
    -e OPENCLAW_WORKSPACE_DIR=/home/node/.openclaw/workspace `
    $Image

if ($LASTEXITCODE -eq 0) {
    Write-Host "OpenClaw Gateway started successfully on http://127.0.0.1:$Port" -ForegroundColor Green
} else {
    Write-Error "Failed to start OpenClaw Gateway container."
}
