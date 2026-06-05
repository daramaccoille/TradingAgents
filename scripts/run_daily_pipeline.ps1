# run_daily_pipeline.ps1 - Automated pipeline entrypoint for Windows Task Scheduler
# Sets up environment variables, runs all 5 metal reports, and pushes them to Neon.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
# We are in trading_agents/scripts, let's move up to trading_agents root
Set-Location ..

# Configure log file paths
$TodayDate = Get-Date -Format "yyyyMMdd"
$TodayDashed = Get-Date -Format "yyyy-MM-dd"
$LogDir = Join-Path (Get-Location).Path "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$LogFile = Join-Path $LogDir "daily_pipeline_$TodayDate.log"

# Define logging wrapper
function Write-Log($Message) {
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $FullMessage = "[$Timestamp] $Message"
    Write-Host $FullMessage
    Add-Content -Path $LogFile -Value $FullMessage
}

Write-Log "============================================="
Write-Log "DAILY TRADING AGENTS PIPELINE START"
Write-Log "============================================="
Write-Log "Target Date: $TodayDashed"

# Enable UTF-8 mode for Python to prevent Windows CP-1252 encoding errors
$env:PYTHONUTF8 = 1
Write-Log "Set Environment Variable: PYTHONUTF8 = 1"

# Check virtual environment
$PythonExe = Join-Path (Get-Location).Path ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Log "ERROR: Virtual environment python not found at $PythonExe"
    exit 1
}

# Run generation for all 5 metals
Write-Log "Step 1: Running report generation for all metals..."
try {
    # Run the bulk runner python script and capture output to log file
    & $PythonExe run_all_metals_reports.py --date $TodayDashed *>&1 | Out-String | ForEach-Object {
        $line = $_.TrimEnd()
        if ($line) {
            Add-Content -Path $LogFile -Value $line
            Write-Host $line
        }
    }
    Write-Log "Generation completed successfully."
} catch {
    Write-Log "FATAL ERROR during report generation: $_"
    exit 1
}

# Push to Neon
Write-Log "Step 2: Pushing reports matching date $TodayDate to Neon DB..."
try {
    # Run the push script and capture output
    & $PythonExe push_to_neon.py --date $TodayDate *>&1 | Out-String | ForEach-Object {
        $line = $_.TrimEnd()
        if ($line) {
            Add-Content -Path $LogFile -Value $line
            Write-Host $line
        }
    }
    Write-Log "Database ingestion completed successfully."
} catch {
    Write-Log "FATAL ERROR during Neon database ingestion: $_"
    exit 1
}

Write-Log "============================================="
Write-Log "DAILY TRADING AGENTS PIPELINE COMPLETE"
Write-Log "============================================="
