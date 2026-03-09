$visio = New-Object -ComObject Visio.Application
$visio.Visible = $true
$doc = $visio.Documents.Open("D:\Cloude_PR\projects\survey-automation\backend\data\projects\test_verify_a.vsdx")
$page = $doc.Pages[1]
$count = $page.Shapes.Count
Write-Host "Total shapes (test_verify_a): $count"

$s16 = $page.Shapes[16]
$w16 = [Math]::Round($s16.CellsU("Width").ResultIU, 4)
$f16 = $s16.CellsU("Width").FormulaU
$t16 = $s16.Text
Write-Host "S16: W=$w16 F=$f16 T=[$t16]"

$doc.Close()
$visio.Quit()
