# Deploy обработки ЗагрузкаРееструТД через DESIGNER batch на сервер ut_rt_copy
# Версия платформы 8.3.27.1688 (как на сервере)
$ErrorActionPreference = 'Stop'

$v8 = 'C:\Program Files\1cv8\8.3.27.1688\bin\1cv8.exe'
$cfeRoot = 'C:\CLOUDE_PR\projects\russian-transit\src\cfe\Русский_Транзит'
$logFile = 'C:\CLOUDE_PR\projects\russian-transit\scripts\deploy-zagruzka-tdf.log'

if (-not (Test-Path $v8)) { Write-Error "Не найдена платформа: $v8"; exit 1 }
if (-not (Test-Path $cfeRoot)) { Write-Error "Не найден CFE: $cfeRoot"; exit 1 }

Remove-Item $logFile -ErrorAction SilentlyContinue

$bsl1 = "DataProcessors\ЗагрузкаРееструТД\Ext\ObjectModule.bsl"
$bsl2 = "DataProcessors\ЗагрузкаРееструТД\Forms\Форма\Ext\Form\Module.bsl"

Write-Host "Deploying via DESIGNER batch to is-srv1c-02:5541/ut_rt_copy..."
& $v8 DESIGNER `
	/S "is-srv1c-02:5541\ut_rt_copy" `
	/N "Администратор" /P "123" `
	/LoadConfigFromFiles $cfeRoot `
	-Extension "Русский_Транзит" `
	-files "$bsl1,$bsl2" `
	/UpdateDBCfg `
	/Out $logFile `
	/DisableStartupDialogs /DisableStartupMessages

$exitCode = $LASTEXITCODE
Write-Host "Exit code: $exitCode"
if (Test-Path $logFile) {
	$content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
	if ($content) {
		Write-Host "--- Log content ---"
		Write-Host $content
	} else {
		Write-Host "Log file empty (typical for success: 3-byte BOM)"
	}
}
if ($exitCode -eq 0) {
	Write-Host "OK. Изменения применены к ut_rt_copy. ВАЖНО: для применения runtime нужно перезапустить тонкого клиента (или дождаться рестарта рабочих процессов сервера)."
} else {
	Write-Error "Deploy failed. Check log."
	exit $exitCode
}
