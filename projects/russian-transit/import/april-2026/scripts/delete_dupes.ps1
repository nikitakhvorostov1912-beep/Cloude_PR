param([int]$StartFrom = 0, [int]$BatchSize = 100)
$sid = Get-Content 'C:\CLOUDE_PR\projects\russian-transit\scripts\mcp-session.txt' -Raw
$lines = Get-Content C:\CLOUDE_PR\tmp\dupe_pairs.txt
$total = $lines.Count
Write-Host "Total pairs: $total, starting from $StartFrom, batch=$BatchSize"

$deleted = 0; $skipped = 0; $errors = 0; $totalDone = 0
$start = $StartFrom
$logFile = "C:\CLOUDE_PR\tmp\delete_dupes_log.txt"
"=== DELETE DUPES START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') from=$StartFrom batch=$BatchSize ===" | Out-File $logFile -Append -Encoding UTF8

while ($start -lt $total) {
	$end = [Math]::Min($start + $BatchSize, $total) - 1
	$batch = $lines[$start..$end]
	$pairsJson = ($batch | ForEach-Object { $p = $_.Split('|'); "{`"m`":`"$($p[0])`",`"M`":`"$($p[1])`"}" }) -join ','
	$pairsJson = "[$pairsJson]"
	$bytes = [System.Text.Encoding]::UTF8.GetBytes($pairsJson)
	$b64 = [Convert]::ToBase64String($bytes)
	$code = @"
ДД = Base64Значение("$b64");
Текст = ПолучитьСтрокуИзДвоичныхДанных(ДД, КодировкаТекста.UTF8);
Чт = Новый ЧтениеJSON;
Чт.УстановитьСтроку(Текст);
Массив = ПрочитатьJSON(Чт, Истина);
Удалено = 0; Пропущено = 0; Ошибок = 0;
Подробно = "";
Для Каждого Эл Из Массив Цикл
	Попытка
		МойСсыл = Документы.ОперацияПоПоручительству.ПолучитьСсылку(Новый УникальныйИдентификатор(Эл["m"]));
		МастерСсыл = Документы.ОперацияПоПоручительству.ПолучитьСсылку(Новый УникальныйИдентификатор(Эл["M"]));
		МойД = МойСсыл.ПолучитьОбъект();
		МастерД = МастерСсыл.ПолучитьОбъект();
		Если МойД = Неопределено Тогда
			Пропущено = Пропущено + 1;
			Подробно = Подробно + "SKIP_MY_GONE " + Эл["m"] + Символы.ПС;
			Продолжить;
		КонецЕсли;
		Если МастерД = Неопределено Тогда
			Пропущено = Пропущено + 1;
			Подробно = Подробно + "SKIP_M_GONE " + Эл["m"] + "->" + Эл["M"] + Символы.ПС;
			Продолжить;
		КонецЕсли;
		НайденоВДД = Ложь;
		Для Каждого Стр Из МастерД.ДанныеДокументов Цикл
			Если СокрЛП(Стр.НомерГТД) = СокрЛП(МойД.НомерГТД) Тогда
				НайденоВДД = Истина;
				Прервать;
			КонецЕсли;
		КонецЦикла;
		Если НЕ НайденоВДД Тогда
			Пропущено = Пропущено + 1;
			Подробно = Подробно + "SKIP_NOT_IN_DD " + МойД.НомерГТД + "->" + МастерД.НомерГТД + Символы.ПС;
			Продолжить;
		КонецЕсли;
		МойД.Удалить();
		Удалено = Удалено + 1;
	Исключение
		Ошибок = Ошибок + 1;
		Подробно = Подробно + "ERR " + Эл["m"] + ": " + ОписаниеОшибки() + Символы.ПС;
	КонецПопытки;
КонецЦикла;
Результат = "Удалено=" + Удалено + " Пропущено=" + Пропущено + " Ошибок=" + Ошибок + Символы.ПС + Подробно;
"@
	$id = Get-Random -Minimum 100 -Maximum 999999
	$body = @{ jsonrpc='2.0'; id=$id; method='tools/call'; params=@{ name='execute_code'; arguments=@{ code=$code } } } | ConvertTo-Json -Depth 10 -Compress
	try {
		$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:6010/mcp' -Method Post -Body $body -ContentType 'application/json' -Headers @{ Accept='application/json, text/event-stream'; 'Mcp-Session-Id'=$sid } -UseBasicParsing -TimeoutSec 600
		$txt = ($resp.Content -split "`r?`n" | Where-Object { $_ -match '^data:\s' } | ForEach-Object { $_ -replace '^data:\s?','' }) -join "`n"
		$j = $txt | ConvertFrom-Json
		$inner = $j.result.content[0].text | ConvertFrom-Json
		if ($inner.success) {
			$data = $inner.data -replace '\\n', "`n" -replace '\\"', '"'
			$m = [regex]::Match($data, 'Удалено=(\d+)\s+Пропущено=(\d+)\s+Ошибок=(\d+)')
			if ($m.Success) {
				$d = [int]$m.Groups[1].Value
				$sk = [int]$m.Groups[2].Value
				$e = [int]$m.Groups[3].Value
				$deleted += $d; $skipped += $sk; $errors += $e
				$totalDone = $end + 1
				Write-Host ("Batch {0,4}-{1,4}: удалено={2,3} пропущ={3,2} ош={4,2} | сумм_удал={5}" -f $start, $end, $d, $sk, $e, $deleted)
				if ($sk -gt 0 -or $e -gt 0) {
					"BATCH $start-$end" | Out-File $logFile -Append -Encoding UTF8
					$data | Out-File $logFile -Append -Encoding UTF8
				}
			} else {
				Write-Host "Batch $start unparsed: $($data.Substring(0,[Math]::Min(300,$data.Length)))"
				"BATCH $start UNPARSED: $data" | Out-File $logFile -Append -Encoding UTF8
				break
			}
		} else {
			Write-Host "Batch $start FAILED: $($inner.error)"
			"BATCH $start FAILED: $($inner.error)" | Out-File $logFile -Append -Encoding UTF8
			break
		}
	} catch {
		Write-Host "Batch $start EXC: $($_.Exception.Message)"
		"BATCH $start EXC: $($_.Exception.Message)" | Out-File $logFile -Append -Encoding UTF8
		break
	}
	$start = $start + $BatchSize
}

Write-Host ""
Write-Host ("ИТОГО: удалено=$deleted пропущено=$skipped ошибок=$errors из $totalDone")
"ИТОГО: удалено=$deleted пропущено=$skipped ошибок=$errors из $totalDone" | Out-File $logFile -Append -Encoding UTF8
