$visio = New-Object -ComObject Visio.Application
$visio.Visible = $true

$doc = $visio.Documents.Open("D:\Cloude_PR\projects\survey-automation\backend\data\projects\6fa5881144a34dcf9ea274c5ca448e07\visio\proc_purchase.vsdx")
$page = $doc.Pages[1]
$count = $page.Shapes.Count
$w16 = [Math]::Round($page.Shapes[16].CellsU("Width").ResultIU, 4)
$f16 = $page.Shapes[16].CellsU("Width").FormulaU
Write-Host "proc_purchase (clean): shapes=$count, S16.Width=$w16, Formula=$f16"

# Export PNG
$page.Export("D:\Cloude_PR\projects\survey-automation\backend\data\projects\6fa5881144a34dcf9ea274c5ca448e07\visio\proc_purchase.png")
Write-Host "Exported PNG"

$doc.Close()
$visio.Quit()
