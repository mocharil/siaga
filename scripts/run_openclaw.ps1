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
    [string]$Volume = "openclaw-state",
    [string]$EnvFile = ""
)

# 1. Resolve .env file if not explicitly specified
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoDir = (Resolve-Path "$ScriptDir\..").Path

if (-not $EnvFile) {
    if (Test-Path "$RepoDir\.env") {
        $EnvFile = "$RepoDir\.env"
    } elseif (Test-Path "$RepoDir\..\.env") {
        $EnvFile = (Resolve-Path "$RepoDir\..\.env").Path
    }
}

# 2. Parse .env file into environment if found
if ($EnvFile -and (Test-Path $EnvFile)) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $name = $parts[0].Trim()
            $val = $parts[1].Trim().Trim('"').Trim("'")
            if (-not [System.Environment]::GetEnvironmentVariable($name)) {
                [System.Environment]::SetEnvironmentVariable($name, $val, "Process")
            }
        }
    }
}

# 3. Fail-fast validation: LLM API key MUST be set
$ResolvedApiKey = $env:OPENAI_API_KEY
if (-not $ResolvedApiKey) {
    $ResolvedApiKey = $env:LLM_API_KEY
}
if (-not $ResolvedApiKey) {
    Write-Error "Error: LLM_API_KEY atau OPENAI_API_KEY belum di-set di environment. Set variabel sebelum menjalankan skrip."
    exit 1
}

# 4. Ensure volume exists
$volCheck = docker volume ls -q -f name=$Volume
if (-not $volCheck) {
    Write-Host "Creating docker volume: $Volume"
    docker volume create $Volume | Out-Null
}

# 5. Check if container is already running
$running = docker ps -q -f name=$ContainerName
if ($running) {
    Write-Host "Container '$ContainerName' is already running on http://127.0.0.1:$Port" -ForegroundColor Yellow
    exit 0
}

# 6. Remove existing stopped container
$exists = docker ps -a -q -f name=$ContainerName
if ($exists) {
    Write-Host "Removing stopped container '$ContainerName'..."
    docker rm -f $ContainerName | Out-Null
}

# 7. Start OpenClaw Gateway container
Write-Host "Starting OpenClaw Gateway ($Image) strictly on 127.0.0.1:$Port..."
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
    -e OPENAI_API_KEY="${ResolvedApiKey}" `
    $Image

if ($LASTEXITCODE -eq 0) {
    Write-Host "OpenClaw Gateway started successfully on http://127.0.0.1:$Port" -ForegroundColor Green
    Write-Host "Security Notice: gateway.bind='lan' inside container, loopback protection relies on host -p 127.0.0.1:${Port}:${Port}." -ForegroundColor Cyan
} else {
    Write-Error "Failed to start OpenClaw Gateway container."
    exit 1
}
