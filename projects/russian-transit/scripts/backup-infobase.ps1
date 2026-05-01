# backup-infobase.ps1 — Полный backup базы InfoBase5 в .dt файл
# Использование: powershell -NoProfile -ExecutionPolicy Bypass -File backup-infobase.ps1 [-Tag <suffix>]
#
# Создаёт C:\CLOUDE_PR\projects\russian-transit\backups\InfoBase5-yyyyMMdd-HHmmss[-tag].dt
# Типичный размер ~ 100-500 МБ (сжатый), время ~ 1-3 минуты для 2GB базы.

param(
    [string]$Tag = "",
    [switch]$Force,
    [int]$TimeoutSec = 600
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$v8 = "C:\Program Files\1cv8\8.3.27.1719\bin\1cv8.exe"
$db = "C:\Users\Khvorostov\Documents\InfoBase5"
$bakDir = "C:\CLOUDE_PR\projects\russian-transit\backups"

# Unicode-safe Cyrillic
$user = [char]0x0410 + [char]0x0434 + [char]0x043C + [char]0x0438 + [char]0x043D + [char]0x0438 + [char]0x0441 + [char]0x0442 + [char]0x0440 + [char]0x0430 + [char]0x0442 + [char]0x043E + [char]0x0440
$pass = "123"

function Write-Step($msg, $color = "Cyan") { Write-Host "[$(Get-Date -Format HH:mm:ss)] $msg" -ForegroundColor $color }

# Pre-flight: 1C closed
$running = Get-Process 1cv8, 1cv8c -ErrorAction SilentlyContinue
if ($running) {
    if ($Force) {
        Write-Step "Force: stopping 1C ($($running.Id -join ','))" "Yellow"
        $running | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        Write-Step "ERROR: 1C is running (PID $($running.Id -join ', ')). Close it or use -Force." "Red"
        exit 1
    }
}

# Ensure backups dir
if (-not (Test-Path $bakDir)) {
    New-Item -ItemType Directory -Path $bakDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$suffix = if ($Tag) { "-$Tag" } else { "" }
$dtFile = Join-Path $bakDir "InfoBase5-$timestamp$suffix.dt"
$logFile = Join-Path $bakDir "backup-$timestamp$suffix.log"

Write-Step "Target: $dtFile" "Gray"
Write-Step "Source: $db ($([Math]::Round((Get-ChildItem $db -File | Measure-Object Length -Sum).Sum / 1MB, 1)) MB)" "Gray"
Write-Step "Mode: full /DumpIB (timeout ${TimeoutSec}s)" "Cyan"

$argList = "DESIGNER /F `"$db`" /N `"$user`" /P `"$pass`" /DumpIB `"$dtFile`" /Out `"$logFile`" /DisableStartupDialogs /DisableStartupMessages"

$proc = Start-Process -FilePath $v8 -ArgumentList $argList -PassThru -WindowStyle Hidden
$completed = $proc.WaitForExit($TimeoutSec * 1000)

if (-not $completed) {
    Write-Step "TIMEOUT after ${TimeoutSec}s — killing DESIGNER (PID $($proc.Id))" "Red"
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    exit 124
}

$exitCode = $proc.ExitCode
if ($exitCode -eq 0 -and (Test-Path $dtFile)) {
    $sizeMB = [Math]::Round((Get-Item $dtFile).Length / 1MB, 1)
    Write-Step "SUCCESS: $dtFile ($sizeMB MB)" "Green"
} else {
    Write-Step "FAILED (exit $exitCode)" "Red"
    if (Test-Path $logFile) {
        Write-Host "=== LOG ===" -ForegroundColor Cyan
        Get-Content $logFile -Encoding UTF8
    }
}

exit $exitCode
