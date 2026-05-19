# Точечный deploy изменённых файлов расширения Русский_Транзит через DESIGNER -files
# Берёт изменённые файлы из git (HEAD~N..HEAD + unstaged) и применяет на сервер.
#
# Использование:
#   deploy-changed.ps1                              — последний коммит на ut_rt_copy
#   deploy-changed.ps1 -SinceCommits 3              — последние 3 коммита
#   deploy-changed.ps1 -Server local                — на локальную InfoBase5
#   deploy-changed.ps1 -Files "Path1.bsl,Path2.xml" — явный список (без git)
#   deploy-changed.ps1 -DryRun                      — показать что бы залилось, без запуска
#
# Фикс из памяти 2026-05-03: -files требует ОТНОСИТЕЛЬНЫЕ пути для XML (для BSL ок и абсолютные).
# Server modes:
#   ut_rt_copy (default) — продакшен-клон на is-srv1c-02:5541
#   local                — локальная InfoBase5

param(
	[int]$SinceCommits = 1,
	[ValidateSet('ut_rt_copy','local')]
	[string]$Server = 'ut_rt_copy',
	[string]$Files = '',
	[switch]$IncludeUnstaged,
	[switch]$DryRun,
	[switch]$NoUpdateDB,
	[int]$BatchSize = 30
)

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$v8 = 'C:\Program Files\1cv8\8.3.27.1989\bin\1cv8.exe'
$repoRoot = 'C:\CLOUDE_PR'
$extName = [char]0x0420 + [char]0x0443 + [char]0x0441 + [char]0x0441 + [char]0x043A + [char]0x0438 + [char]0x0439 + '_' + [char]0x0422 + [char]0x0440 + [char]0x0430 + [char]0x043D + [char]0x0437 + [char]0x0438 + [char]0x0442
$user = [char]0x0410 + [char]0x0434 + [char]0x043C + [char]0x0438 + [char]0x043D + [char]0x0438 + [char]0x0441 + [char]0x0442 + [char]0x0440 + [char]0x0430 + [char]0x0442 + [char]0x043E + [char]0x0440
$srcCfeRoot = "$repoRoot\projects\russian-transit\src\cfe\$extName"
$logFile = "$repoRoot\projects\russian-transit\scripts\deploy-changed.log"

function Write-Step($msg, $color = 'Cyan') {
	Write-Host "[$(Get-Date -Format HH:mm:ss)] $msg" -ForegroundColor $color
}

# === 1. Получить список изменённых файлов ===
$cfePrefix = "projects/russian-transit/src/cfe/$extName/"
$changedFiles = @()

if ($Files) {
	$changedFiles = $Files -split ','
	Write-Step "Files mode: explicit list ($($changedFiles.Count) files)" 'Cyan'
} else {
	Push-Location $repoRoot
	try {
		$gitArgs = @('-c','core.quotepath=false','diff','--name-only',"HEAD~${SinceCommits}..HEAD",'--',$cfePrefix)
		$committed = & git @gitArgs 2>$null
		if ($IncludeUnstaged) {
			$unstaged = & git -c core.quotepath=false diff --name-only -- $cfePrefix 2>$null
			$staged = & git -c core.quotepath=false diff --name-only --cached -- $cfePrefix 2>$null
			$committed = @($committed) + @($unstaged) + @($staged) | Where-Object { $_ } | Select-Object -Unique
		}
		# git возвращает пути с / и octal-escaped кириллицей — нормализуем
		$changedFiles = $committed | Where-Object { $_ -and $_.EndsWith('.bsl') -or $_.EndsWith('.xml') } | ForEach-Object {
			# octal-escape (\320\240...) → строка
			if ($_ -match '\\') {
				# Использовать git с -z для бинарной выдачи (без escape)
				$_
			} else {
				$_
			}
		}
		Write-Step "Git mode: $($changedFiles.Count) files in last $SinceCommits commit(s)$(if($IncludeUnstaged){' + unstaged/staged'})" 'Cyan'
	} finally {
		Pop-Location
	}
}

if (-not $changedFiles -or $changedFiles.Count -eq 0) {
	Write-Step "No changed files found in $cfePrefix. Nothing to deploy." 'Yellow'
	exit 0
}

# === 2. Конвертировать в относительные пути от srcCfeRoot ===
$srcCfeFull = [System.IO.Path]::GetFullPath($srcCfeRoot).TrimEnd('\','/')
$cfePrefixWin = $cfePrefix.Replace('/','\').TrimEnd('\')

$filesRel = @()
foreach ($f in $changedFiles) {
	# git выдаёт с прямым слешем, путь относительно repoRoot
	$relFromRepo = $f.Replace('/','\')
	# Убираем prefix "projects\russian-transit\src\cfe\Русский_Транзит\"
	if ($relFromRepo.StartsWith($cfePrefixWin, [StringComparison]::OrdinalIgnoreCase)) {
		$relFromCfe = $relFromRepo.Substring($cfePrefixWin.Length + 1)
		$filesRel += $relFromCfe
	} else {
		Write-Step "  skip (not in cfe root): $f" 'DarkGray'
	}
}

if ($filesRel.Count -eq 0) {
	Write-Step "No files in extension after filtering. Nothing to deploy." 'Yellow'
	exit 0
}

Write-Step "Files to deploy:" 'Green'
$filesRel | ForEach-Object { Write-Host "  $_" -ForegroundColor White }

# === 3. Сервер ===
if ($Server -eq 'ut_rt_copy') {
	$serverArgs = @('/S', 'is-srv1c-02:5541\ut_rt_copy')
	$serverDesc = 'is-srv1c-02:5541/ut_rt_copy'
} else {
	$serverArgs = @('/F', 'C:\Users\Khvorostov\Documents\InfoBase5')
	$serverDesc = 'InfoBase5 (local)'
}

# === 4. Разбивка на батчи ===
$batches = @()
if ($filesRel.Count -le $BatchSize) {
	$batches += ,@($filesRel)
} else {
	for ($i = 0; $i -lt $filesRel.Count; $i += $BatchSize) {
		$end = [Math]::Min($i + $BatchSize - 1, $filesRel.Count - 1)
		$batches += ,@($filesRel[$i..$end])
	}
}

Write-Host ''
Write-Step "Target: $serverDesc" 'Cyan'
Write-Step "Mode: $(if ($NoUpdateDB){'load only (no UpdateDBCfg)'}else{'load + UpdateDBCfg on last batch'})" 'Cyan'
Write-Step "Batches: $($batches.Count) (size $BatchSize)" 'Cyan'

if ($DryRun) {
	Write-Host ''
	Write-Step "DRY RUN — would deploy $($filesRel.Count) files in $($batches.Count) batches" 'Yellow'
	exit 0
}

# === 5. Запуск ===
$totalStart = Get-Date
$batchIdx = 0
$lastExitCode = 0
foreach ($batch in $batches) {
	$batchIdx++
	$isLast = ($batchIdx -eq $batches.Count)
	$filesArg = ($batch -join ',')
	$updateDBArg = if ($NoUpdateDB -or -not $isLast) { @() } else { @('/UpdateDBCfg') }
	$batchLog = "$repoRoot\projects\russian-transit\scripts\deploy-changed-batch-$batchIdx.log"

	$arguments = @(
		'DESIGNER'
	) + $serverArgs + @(
		'/N', $user,
		'/P', '123',
		'/LoadConfigFromFiles', $srcCfeRoot,
		'-Extension', $extName,
		'-files', $filesArg
	) + $updateDBArg + @(
		'/Out', $batchLog,
		'/DisableStartupDialogs',
		'/DisableStartupMessages'
	)

	Remove-Item $batchLog -ErrorAction SilentlyContinue
	Write-Host ''
	Write-Step "Batch $batchIdx/$($batches.Count): $($batch.Count) files$(if ($isLast -and -not $NoUpdateDB){' + UpdateDBCfg'})" 'Cyan'
	$start = Get-Date
	$proc = Start-Process -FilePath $v8 -ArgumentList $arguments -NoNewWindow -Wait -PassThru
	$elapsed = ((Get-Date) - $start).TotalSeconds
	$lastExitCode = $proc.ExitCode

	Write-Step "  Exit: $($proc.ExitCode), elapsed: $([math]::Round($elapsed, 1))s" $(if ($proc.ExitCode -eq 0) { 'Green' } else { 'Red' })

	if ((Test-Path $batchLog) -and ((Get-Item $batchLog).Length -gt 3)) {
		Write-Step "  --- LOG batch $batchIdx ---" 'DarkYellow'
		Get-Content $batchLog -Raw -Encoding utf8
		Write-Step "  --- END ---" 'DarkYellow'
	}

	if ($proc.ExitCode -ne 0) {
		Write-Step "Batch $batchIdx failed. Aborting." 'Red'
		break
	}
}

$totalElapsed = ((Get-Date) - $totalStart).TotalSeconds
Write-Host ''
if ($lastExitCode -eq 0) {
	Write-Step "OK: deploy of $($filesRel.Count) file(s) in $batchIdx batch(es), total $([math]::Round($totalElapsed, 1))s." 'Green'
} else {
	Write-Step "FAIL after $batchIdx batch(es), total $([math]::Round($totalElapsed, 1))s." 'Red'
}

exit $lastExitCode
