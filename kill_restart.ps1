# Kill port 8000
$conn = netstat -aon | Where-Object { $_ -match ':8000 ' -and $_ -match 'LISTENING' }
if ($conn) {
    $pidStr = ($conn.Trim() -split '\s+')[-1]
    if ($pidStr -match '^\d+$') {
        Stop-Process -Id ([int]$pidStr) -Force -ErrorAction SilentlyContinue
        Write-Host "Killed PID $pidStr on port 8000"
        Start-Sleep -Seconds 1
    }
} else {
    Write-Host "Port 8000 is already free"
}

# Start new backend
$backendDir = "C:\CLOUDE_PR\projects\survey-automation\backend"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$backendDir`" && python -m uvicorn main:app --host 0.0.0.0 --port 8000" -WindowStyle Minimized
Write-Host "Backend started"
Start-Sleep -Seconds 4

# Check it's up
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "Health check: $($resp.StatusCode) OK"
} catch {
    Write-Host "Health check failed: $_"
}
