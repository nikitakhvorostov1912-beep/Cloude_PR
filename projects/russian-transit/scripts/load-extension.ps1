# load-extension.ps1 — Загрузка расширения Русский_Транзит в базу 1С
# Использование: powershell -NoProfile -ExecutionPolicy Bypass -File load-extension.ps1
#                [-DumpOnly]      — выгрузить текущее расширение из базы в dump-check
#                [-NoDB]          — без UpdateDBCfg (только применить к конфигурации)
#                [-Force]         — убить запущенную 1С автоматически (без подтверждения)
#                [-TimeoutSec N]  — таймаут DESIGNER (default 180)
#
# ВАЖНО: bash искажает кириллицу в аргументах — всегда через PowerShell.

param(
    [switch]$DumpOnly,
    [switch]$NoDB,
    [switch]$Force,
    [int]$TimeoutSec = 180
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$v8 = "C:\Program Files\1cv8\8.3.27.1719\bin\1cv8.exe"
$db = "C:\Users\Khvorostov\Documents\InfoBase5"

# Unicode-safe strings for Cyrillic paths (bash arg passing)
$extName = [char]0x0420 + [char]0x0443 + [char]0x0441 + [char]0x0441 + [char]0x043A + [char]0x0438 + [char]0x0439 + "_" + [char]0x0422 + [char]0x0440 + [char]0x0430 + [char]0x043D + [char]0x0437 + [char]0x0438 + [char]0x0442
$user = [char]0x0410 + [char]0x0434 + [char]0x043C + [char]0x0438 + [char]0x043D + [char]0x0438 + [char]0x0441 + [char]0x0442 + [char]0x0440 + [char]0x0430 + [char]0x0442 + [char]0x043E + [char]0x0440

$srcDir = "C:\CLOUDE_PR\projects\russian-transit\src\cfe\" + $extName
$logFile = "C:\CLOUDE_PR\projects\russian-transit\scripts\load-result.log"
$pass = "123"

function Write-Step($msg, $color = "Cyan") { Write-Host "[$(Get-Date -Format HH:mm:ss)] $msg" -ForegroundColor $color }

# === PRE-FLIGHT 1: Source exists ===
if (-not (Test-Path $srcDir)) {
    Write-Step "ERROR: Source not found: $srcDir" "Red"
    exit 1
}

# === PRE-FLIGHT 2: 1C must be closed (DESIGNER blocks on running 1cv8c) ===
$running1c = Get-Process 1cv8c, 1cv8s -ErrorAction SilentlyContinue
if ($running1c) {
    if ($Force) {
        Write-Step "Force: stopping 1C ($($running1c.Id -join ','))" "Yellow"
        $running1c | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        Write-Step "ERROR: 1C is running (PID $($running1c.Id -join ', ')). Close it or use -Force." "Red"
        Write-Step "  Tip: Файл -> Завершить работу, или Stop-Process -Id $($running1c.Id[0]) -Force" "Gray"
        exit 1
    }
}

# === PRE-FLIGHT 3: kill orphan PowerShell holding the log ===
if (Test-Path $logFile) {
    try {
        # Try to remove — if locked, the file handle is held by orphan process
        Remove-Item $logFile -Force -ErrorAction Stop
    } catch {
        Write-Step "Log file locked, killing orphan PowerShell holders..." "Yellow"
        $myPid = $PID
        Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {
            $_.Id -ne $myPid -and $_.Modules.FileName -contains $logFile
        } | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        Remove-Item $logFile -Force -ErrorAction SilentlyContinue
    }
}

# === PRE-FLIGHT 4: stale ConfigDumpInfo.xml ===
$dumpInfo = Join-Path $srcDir "ConfigDumpInfo.xml"
if (Test-Path $dumpInfo) {
    Remove-Item $dumpInfo -Force
    Write-Step "Removed stale ConfigDumpInfo.xml (force full reload)" "Yellow"
}

# === MODE selection ===
if ($DumpOnly) {
    $dumpDir = "C:\CLOUDE_PR\projects\russian-transit\dump-check"
    if (Test-Path $dumpDir) { Remove-Item $dumpDir -Recurse -Force -ErrorAction SilentlyContinue }
    New-Item -ItemType Directory -Path $dumpDir -Force | Out-Null
    $argList = "DESIGNER /F `"$db`" /N `"$user`" /P `"$pass`" /DumpConfigToFiles `"$dumpDir`" -Extension `"$extName`" /Out `"$logFile`" /DisableStartupDialogs"
    Write-Step "Mode: dump (export from DB to dump-check/)" "Cyan"
} else {
    $updateFlag = if ($NoDB) { "" } else { "/UpdateDBCfg" }
    $argList = "DESIGNER /F `"$db`" /N `"$user`" /P `"$pass`" /LoadConfigFromFiles `"$srcDir`" -Extension `"$extName`" $updateFlag /Out `"$logFile`" /DisableStartupDialogs"
    Write-Step "Mode: load + UpdateDBCfg (timeout ${TimeoutSec}s)" "Cyan"
}

Write-Step "Source: $srcDir" "Gray"

# === EXECUTE with timeout ===
$proc = Start-Process -FilePath $v8 -ArgumentList $argList -PassThru -WindowStyle Hidden
$completed = $proc.WaitForExit($TimeoutSec * 1000)

if (-not $completed) {
    Write-Step "TIMEOUT after ${TimeoutSec}s — killing DESIGNER (PID $($proc.Id))" "Red"
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Write-Step "If you have huge unstaged changes, commit them in smaller chunks first." "Yellow"
    exit 124
}

$exitCode = $proc.ExitCode
Write-Host ""
if ($exitCode -eq 0) {
    Write-Step "SUCCESS (exit 0)" "Green"
} else {
    Write-Step "FAILED (exit $exitCode)" "Red"
}

if (Test-Path $logFile) {
    Write-Host ""
    Write-Host "=== LOG ===" -ForegroundColor Cyan
    Get-Content $logFile -Encoding UTF8
    Write-Host "=== END ===" -ForegroundColor Cyan
}

exit $exitCode
