# start-1c.ps1 — запуск 1С:Предприятие на InfoBase5
# Использование: powershell -NoProfile -ExecutionPolicy Bypass -File start-1c.ps1
#                [-Force]    — закрыть текущую 1С перед запуском (если открыта)

param(
    [switch]$Force
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$v8 = "C:\Program Files\1cv8\8.3.27.1719\bin\1cv8.exe"
$db = "C:\Users\Khvorostov\Documents\InfoBase5"
$user = [char]0x0410 + [char]0x0434 + [char]0x043C + [char]0x0438 + [char]0x043D + [char]0x0438 + [char]0x0441 + [char]0x0442 + [char]0x0440 + [char]0x0430 + [char]0x0442 + [char]0x043E + [char]0x0440
$pass = "123"

function Write-Step($msg, $color = "Cyan") { Write-Host "[$(Get-Date -Format HH:mm:ss)] $msg" -ForegroundColor $color }

# Pre-flight: 1C already running?
$existing = Get-Process 1cv8c -ErrorAction SilentlyContinue
if ($existing) {
    if ($Force) {
        Write-Step "Force: closing existing 1C (PID $($existing.Id))" "Yellow"
        $existing | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        Write-Step "1C already running (PID $($existing.Id)). Use -Force to restart." "Yellow"
        exit 0
    }
}

Start-Process $v8 -ArgumentList "ENTERPRISE /F `"$db`" /N `"$user`" /P `"$pass`" /DisableStartupDialogs"
Write-Step "1C launched. После загрузки запусти EPF MCP_Toolkit на порту 6010." "Green"
