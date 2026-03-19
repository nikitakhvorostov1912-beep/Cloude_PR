# Delete old VSDX and SVG cache, then regenerate
$projectDir = "C:\CLOUDE_PR\projects\survey-automation\backend\data\projects"
$vsdxFiles = Get-ChildItem -Path $projectDir -Recurse -Filter "*.vsdx" -ErrorAction SilentlyContinue
$svgFiles  = Get-ChildItem -Path $projectDir -Recurse -Filter "*.svg"  -ErrorAction SilentlyContinue

Write-Host "Deleting $($vsdxFiles.Count) VSDX and $($svgFiles.Count) SVG files..."
foreach ($f in $vsdxFiles) { Remove-Item $f.FullName -Force; Write-Host "  del $($f.Name)" }
foreach ($f in $svgFiles)  { Remove-Item $f.FullName -Force }

# Find all projects
$projects = Get-ChildItem -Path $projectDir -Directory -ErrorAction SilentlyContinue
Write-Host "Projects found: $($projects.Count)"

foreach ($proj in $projects) {
    $projId = $proj.Name
    Write-Host "Project: $projId"

    $procFile = "$($proj.FullName)\processes\processes.json"
    if (-not (Test-Path $procFile)) { Write-Host "  no processes.json, skip"; continue }

    $data = Get-Content $procFile -Raw | ConvertFrom-Json
    foreach ($proc in $data.processes) {
        $procId = $proc.id
        Write-Host "  Generating Visio for $procId..."
        $url = "http://localhost:8000/api/projects/$projId/export/visio/$procId"
        try {
            $resp = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 30 -ErrorAction Stop
            Write-Host "    OK $($resp.StatusCode)"
        } catch {
            Write-Host "    FAIL $url : $($_.Exception.Message)"
        }
        Start-Sleep -Milliseconds 500
    }
}

Write-Host "Done"
