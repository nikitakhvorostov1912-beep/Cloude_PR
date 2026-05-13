# Сравнить API список ГТД (7813) с DB списком (14012 строк = шапки+ДД)
$api = (Get-Content C:/CLOUDE_PR/tmp/april_operations.json -Raw | ConvertFrom-Json) | ForEach-Object { $_.gtd }
$apiSet = [System.Collections.Generic.HashSet[string]]::new()
$api | ForEach-Object { [void]$apiSet.Add($_) }
Write-Host "API уникальных ГТД: $($apiSet.Count)"

$dbLines = Get-Content C:/CLOUDE_PR/tmp/db_gtds_apr.txt
$dbHeaders = [System.Collections.Generic.HashSet[string]]::new()
$dbDD = [System.Collections.Generic.HashSet[string]]::new()
$dbAny = [System.Collections.Generic.HashSet[string]]::new()
foreach ($l in $dbLines) {
	$t = $l.Trim().Trim('"')
	if ($t -match '^(\S+)\|([HD])$') {
		$gtd = $matches[1]
		$src = $matches[2]
		[void]$dbAny.Add($gtd)
		if ($src -eq 'H') { [void]$dbHeaders.Add($gtd) }
		else { [void]$dbDD.Add($gtd) }
	}
}
Write-Host "DB ГТД в шапках: $($dbHeaders.Count)"
Write-Host "DB ГТД в ДД: $($dbDD.Count)"
Write-Host "DB ГТД (шапки ∪ ДД): $($dbAny.Count)"

# Что в API, но не в базе:
$missing = [System.Collections.Generic.HashSet[string]]::new($apiSet)
$missing.ExceptWith($dbAny)
Write-Host ""
Write-Host "=== API но НЕ в базе: $($missing.Count) ==="
if ($missing.Count -gt 0) {
	$missing | Select-Object -First 30 | ForEach-Object { Write-Host "  $_" }
	$missing | Out-File C:/CLOUDE_PR/tmp/api_not_in_db.txt -Encoding UTF8
}

# Что в базе, но не в API (лишнее или из других дат API):
$extra = [System.Collections.Generic.HashSet[string]]::new($dbAny)
$extra.ExceptWith($apiSet)
Write-Host ""
Write-Host "=== В базе но НЕ в API: $($extra.Count) ==="
if ($extra.Count -gt 0) {
	$extra | Select-Object -First 30 | ForEach-Object { Write-Host "  $_" }
	$extra | Out-File C:/CLOUDE_PR/tmp/db_not_in_api.txt -Encoding UTF8
}
