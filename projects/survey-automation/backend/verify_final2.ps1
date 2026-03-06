$visio = New-Object -ComObject Visio.Application
$visio.Visible = $true
$doc = $visio.Documents.Open("D:\Cloude_PR\projects\survey-automation\backend\data\projects\6fa5881144a34dcf9ea274c5ca448e07\visio\proc_purchase.vsdx")
$page = $doc.Pages[1]
$count = $page.Shapes.Count
Write-Host "Total shapes: $count"
Write-Host ""

# Check all shapes - focus on widths
for ($i = 1; $i -le $count; $i++) {
    $s = $page.Shapes[$i]
    $w = [Math]::Round($s.CellsU("Width").ResultIU, 4)
    $h = [Math]::Round($s.CellsU("Height").ResultIU, 4)
    $t = $s.Text
    if ($t.Length -gt 50) { $t = $t.Substring(0,50) }
    Write-Host "S$i W=$w H=$h T=[$t]"
}

Write-Host ""
Write-Host "=== SUMMARY ==="
Write-Host "S16 Width (should be ~3.33):"
$s16 = $page.Shapes[16]
Write-Host ("  Value: " + [Math]::Round($s16.CellsU("Width").ResultIU, 4))
Write-Host ("  Formula: " + $s16.CellsU("Width").FormulaU)

$doc.Close()
$visio.Quit()
