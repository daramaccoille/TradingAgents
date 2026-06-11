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

# CME/commodity futures holidays (YYYY-MM-DD)
$CmeHolidays = @(
    "2024-01-01","2024-01-15","2024-02-19","2024-03-29","2024-05-27",
    "2024-06-19","2024-07-04","2024-09-02","2024-11-28","2024-12-25",
    "2025-01-01","2025-01-20","2025-02-17","2025-04-18","2025-05-26",
    "2025-06-19","2025-07-04","2025-09-01","2025-11-27","2025-12-25",
    "2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25",
    "2026-06-19","2026-07-03","2026-09-07","2026-11-26","2026-12-25"
)

# Returns the last CME trading day on or before the given date
function Get-LastTradingDay {
    param([datetime]$FromDate)
    $candidate = $FromDate
    for ($i = 0; $i -lt 10; $i++) {
        $dow = $candidate.DayOfWeek
        $ds  = $candidate.ToString("yyyy-MM-dd")
        if ($dow -ne [DayOfWeek]::Saturday -and $dow -ne [DayOfWeek]::Sunday -and $CmeHolidays -notcontains $ds) {
            return $candidate
        }
        $candidate = $candidate.AddDays(-1)
    }
    return $FromDate
}

$Yesterday = (Get-Date).AddDays(-1)
$LastTradingDay = Get-LastTradingDay -FromDate $Yesterday
$LastTradingDayStr = $LastTradingDay.ToString("yyyy-MM-dd")


# Enable UTF-8 mode for Python to prevent Windows CP-1252 encoding errors
$env:PYTHONUTF8 = 1
Write-Log "============================================="
Write-Log "DAILY TRADING AGENTS PIPELINE START"
Write-Log "============================================="
Write-Log "Last trading day: $LastTradingDayStr (today is $(Get-Date -Format 'yyyy-MM-dd'))"
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
    & $PythonExe run_all_metals_reports.py --date $LastTradingDayStr *>&1 | Out-String | ForEach-Object {
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
Write-Log "Step 2: Pushing reports matching date $LastTradingDayStr to Neon DB..."
try {
    # Run the push script and capture output
    & $PythonExe push_to_neon.py --date $LastTradingDayStr *>&1 | Out-String | ForEach-Object {
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
