# Получить все ГТД из базы за апрель 2026 (шапки + ДД активных доков)
$sid = Get-Content 'C:\CLOUDE_PR\projects\russian-transit\scripts\mcp-session.txt' -Raw
$code = @"
Зап = Новый Запрос;
Зап.УстановитьПараметр("Н", '20260401');
Зап.УстановитьПараметр("К", '20260501');
Зап.Текст =
"ВЫБРАТЬ РАЗЛИЧНЫЕ ОПП.НомерГТД КАК ГТД, ""H"" КАК Источник
|ИЗ Документ.ОперацияПоПоручительству КАК ОПП
|ГДЕ НЕ ОПП.ПометкаУдаления И ОПП.Дата >= &Н И ОПП.Дата < &К И ОПП.НомерГТД <> """"
|
|ОБЪЕДИНИТЬ ВСЕ
|
|ВЫБРАТЬ РАЗЛИЧНЫЕ ДД.НомерГТД КАК ГТД, ""D"" КАК Источник
|ИЗ Документ.ОперацияПоПоручительству.ДанныеДокументов КАК ДД
|	ВНУТРЕННЕЕ СОЕДИНЕНИЕ Документ.ОперацияПоПоручительству КАК ОПП ПО ОПП.Ссылка = ДД.Ссылка
|ГДЕ НЕ ОПП.ПометкаУдаления И ОПП.Дата >= &Н И ОПП.Дата < &К И ДД.НомерГТД <> """"";
Рез = Зап.Выполнить().Выгрузить();
Стр = "";
Для Каждого Р Из Рез Цикл
	Стр = Стр + Р.ГТД + "|" + Р.Источник + Символы.ПС;
КонецЦикла;
Результат = "TOTAL=" + Рез.Количество() + Символы.ПС + Стр;
"@
$body = @{ jsonrpc='2.0'; id=(Get-Random); method='tools/call'; params=@{ name='execute_code'; arguments=@{ code=$code } } } | ConvertTo-Json -Depth 10 -Compress
Write-Host "Sending..."
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:6010/mcp' -Method Post -Body $body -ContentType 'application/json' -Headers @{ Accept='application/json, text/event-stream'; 'Mcp-Session-Id'=$sid } -UseBasicParsing -TimeoutSec 600
$txt = ($resp.Content -split "`r?`n" | Where-Object { $_ -match '^data:\s' } | ForEach-Object { $_ -replace '^data:\s?','' }) -join "`n"
$j = $txt | ConvertFrom-Json
$inner = $j.result.content[0].text | ConvertFrom-Json
Write-Host "SUCCESS=$($inner.success)"
if ($inner.success) {
	$data = $inner.data -replace '\\n', "`n" -replace '\\"', '"'
	$data | Out-File C:/CLOUDE_PR/tmp/db_gtds_apr.txt -Encoding UTF8
	$lines = ($data -split "`n").Count
	$header = ($data -split "`n")[0]
	Write-Host "Header: $header"
	Write-Host "Lines saved: $lines"
} else {
	Write-Host "ERR: $($inner.error)"
}
