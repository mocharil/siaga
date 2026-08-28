# ==============================================================================
# SIAGA CT Collector — Windows Scheduled Task Registration Script
# Runs daily at 06:30 WIB (SE Asia Standard Time)
# ==============================================================================

[CmdletBinding()]
param(
    [string]$TaskName = "SIAGA_CT_Collector",
    [string]$PythonExe = "C:\Program Files\Python310\python.exe",
    [string]$WorkingDir = "",
    [string]$Time = "06:30"
)

# Resolve directories
if (-not $WorkingDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $WorkingDir = (Resolve-Path "$ScriptDir\..").Path
}

$CollectorScript = Join-Path $WorkingDir "collector\ct_collector.py"

# Verify files exist
if (-not (Test-Path $PythonExe)) {
    # Fallback to python in PATH if specific path not found
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    } else {
        Write-Error "Python interpreter not found at '$PythonExe' or in PATH."
        exit 1
    }
}

if (-not (Test-Path $CollectorScript)) {
    Write-Error "Collector script not found at '$CollectorScript'."
    exit 1
}

Write-Host "Registering Scheduled Task: $TaskName"
Write-Host "  Python      : $PythonExe"
Write-Host "  Script      : $CollectorScript"
Write-Host "  Working Dir : $WorkingDir"
Write-Host "  Schedule    : Daily at $Time WIB"

# 1. Action: Execute Python with collector script in working directory
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$CollectorScript`"" -WorkingDirectory $WorkingDir

# 2. Trigger: Daily at 06:30
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

# 3. Settings:
#    - ExecutionTimeLimit: Terminate task if running longer than 1 hour (prevent hanging task blocking next schedule)
#    - MultipleInstances: IgnoreNew (default) to prevent concurrent DB writes
#    - StartWhenAvailable: Run immediately if scheduled 06:30 was missed (laptop asleep/off)
#    - WakeToRun: Wake computer to execute task
#    - AllowStartIfOnBatteries & DontStopIfGoingOnBatteries: Ensure runs on battery power
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# 4. Register Task
$RegisteredTask = Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "SIAGA CT Collector Daily Task (06:30 WIB)" -Force

if ($RegisteredTask) {
    Write-Host "Task '$TaskName' registered successfully!" -ForegroundColor Green
} else {
    Write-Error "Failed to register task '$TaskName'."
    exit 1
}
