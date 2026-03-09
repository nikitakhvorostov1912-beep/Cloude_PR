$visio = New-Object -ComObject Visio.Application
$visio.Visible = $true
$doc = $visio.Documents.Open("D:\Cloude_PR\projects\survey-automation\backend\data\projects\6fa5881144a34dcf9ea274c5ca448e07\visio\proc_purchase.vsdx")
$page = $doc.Pages[1]
$count = $page.Shapes.Count
Write-Host "Total shapes: $count"
Write-Host ""

# Check start event label (should be S16, W~3.33) and end event label
# Focus on shapes 14-18 (around start event area)
Write-Host "=== Start event area ==="
for ($i = 14; $i -le [Math]::Min(18, $count); $i++) {
    $s = $page.Shapes[$i]
    $w = [Math]::Round($s.CellsU("Width").ResultIU, 4)
    $h = [Math]::Round($s.CellsU("Height").ResultIU, 4)
    $t = $s.Text
    if ($t.Length -gt 50) { $t = $t.Substring(0,50) }
    Write-Host "S$i W=$w H=$h T=[$t]"
}

Write-Host ""
Write-Host "=== End event area ==="
for ($i = [Math]::Max(1, $count - 12); $i -le $count; $i++) {
    $s = $page.Shapes[$i]
    $w = [Math]::Round($s.CellsU("Width").ResultIU, 4)
    $h = [Math]::Round($s.CellsU("Height").ResultIU, 4)
    $t = $s.Text
    if ($t.Length -gt 50) { $t = $t.Substring(0,50) }
    Write-Host "S$i W=$w H=$h T=[$t]"
}

# Export PNG
$page.Export("D:\Cloude_PR\projects\survey-automation\backend\data\projects\6fa5881144a34dcf9ea274c5ca448e07\visio\proc_purchase.png")
Write-Host ""
Write-Host "DONE - Exported PNG"

$doc.Close()
$visio.Quit()
