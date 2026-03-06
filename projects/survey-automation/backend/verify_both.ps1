$visio = New-Object -ComObject Visio.Application
$visio.Visible = $true

# Open test file
$doc1 = $visio.Documents.Open("D:\Cloude_PR\projects\survey-automation\backend\data\projects\test_verify_a.vsdx")
$page1 = $doc1.Pages[1]
$count1 = $page1.Shapes.Count
$w1 = [Math]::Round($page1.Shapes[16].CellsU("Width").ResultIU, 4)
Write-Host "test_verify_a: shapes=$count1, S16.Width=$w1"
$doc1.Close()

# Copy test file to real path to test path-dependent behavior
# (files are byte-identical already, but Visio might cache per-path)
$doc2 = $visio.Documents.Open("D:\Cloude_PR\projects\survey-automation\backend\data\projects\6fa5881144a34dcf9ea274c5ca448e07\visio\proc_purchase.vsdx")
$page2 = $doc2.Pages[1]
$count2 = $page2.Shapes.Count
$w2 = [Math]::Round($page2.Shapes[16].CellsU("Width").ResultIU, 4)
Write-Host "proc_purchase: shapes=$count2, S16.Width=$w2"
$doc2.Close()

# Also open test_verify_b
$doc3 = $visio.Documents.Open("D:\Cloude_PR\projects\survey-automation\backend\data\projects\test_verify_b.vsdx")
$page3 = $doc3.Pages[1]
$count3 = $page3.Shapes.Count
$w3 = [Math]::Round($page3.Shapes[16].CellsU("Width").ResultIU, 4)
Write-Host "test_verify_b: shapes=$count3, S16.Width=$w3"
$doc3.Close()

$visio.Quit()
