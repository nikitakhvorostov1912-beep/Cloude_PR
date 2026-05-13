# Один SQL-запрос: для каждого doc_id из missing_full.json — статус (GONE / HAS_MASTER / ORPHAN)
$sid = Get-Content 'C:\CLOUDE_PR\projects\russian-transit\scripts\mcp-session.txt' -Raw
$ops = @(Get-Content C:\CLOUDE_PR\tmp\missing_full.json -Raw | ConvertFrom-Json)
$pairs = $ops | ForEach-Object { "{`"i`":`"$($_.doc_id)`",`"g`":`"$($_.gtd)`"}" }
$json = "[" + ($pairs -join ',') + "]"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
$b64 = [Convert]::ToBase64String($bytes)
Write-Host "Total ids: $($ops.Count), b64 length: $($b64.Length)"

$code = @"
ДД = Base64Значение("$b64");
Текст = ПолучитьСтрокуИзДвоичныхДанных(ДД, КодировкаТекста.UTF8);
Чт = Новый ЧтениеJSON;
Чт.УстановитьСтроку(Текст);
Массив = ПрочитатьJSON(Чт, Истина);

// ТЗ исходного списка
ВхТЗ = Новый ТаблицаЗначений;
ВхТЗ.Колонки.Добавить("ВИД", Новый ОписаниеТипов("Строка", , Новый КвалификаторыСтроки(50)));
ВхТЗ.Колонки.Добавить("ГТД", Новый ОписаниеТипов("Строка", , Новый КвалификаторыСтроки(50)));
Для Каждого Эл Из Массив Цикл
	Нов = ВхТЗ.Добавить();
	Нов.ВИД = Эл["i"];
	Нов.ГТД = Эл["g"];
КонецЦикла;

// Запрос: для каждого ВИД получим Мой документ (если есть активный), для каждой ГТД — кол-во активных мастеров (ОПП.ДД.ГТД совпадает, не мой)
Зап = Новый Запрос;
Зап.МенеджерВременныхТаблиц = Новый МенеджерВременныхТаблиц;
Зап.УстановитьПараметр("ВхТЗ", ВхТЗ);
Зап.Текст =
"ВЫБРАТЬ
|	ВхТЗ.ВИД КАК ВИД,
|	ВхТЗ.ГТД КАК ГТД
|ПОМЕСТИТЬ ВТ_Список
|ИЗ
|	&ВхТЗ КАК ВхТЗ;
|
|////////////////////////////////////////////////////////////////////////////////
|ВЫБРАТЬ
|	ВТ.ВИД КАК ВИД,
|	ВТ.ГТД КАК ГТД,
|	МАКСИМУМ(ОПП.Ссылка) КАК МояСсылка,
|	КОЛИЧЕСТВО(РАЗЛИЧНЫЕ ОПП.Ссылка) КАК МоиАктивные
|ПОМЕСТИТЬ ВТ_МоиАктивные
|ИЗ
|	ВТ_Список КАК ВТ
|		ЛЕВОЕ СОЕДИНЕНИЕ Документ.ОперацияПоПоручительству КАК ОПП
|		ПО ОПП.ВнешнийИдентификатор = ВТ.ВИД
|		И НЕ ОПП.ПометкаУдаления
|СГРУППИРОВАТЬ ПО ВТ.ВИД, ВТ.ГТД;
|
|////////////////////////////////////////////////////////////////////////////////
|ВЫБРАТЬ
|	ВТ.ВИД КАК ВИД,
|	ВТ.ГТД КАК ГТД,
|	ВТ.МояСсылка КАК МояСсылка,
|	ВТ.МоиАктивные КАК МоиАктивные,
|	КОЛИЧЕСТВО(РАЗЛИЧНЫЕ ОППМ.Ссылка) КАК КолМастеров
|ИЗ
|	ВТ_МоиАктивные КАК ВТ
|		ЛЕВОЕ СОЕДИНЕНИЕ Документ.ОперацияПоПоручительству.ДанныеДокументов КАК ДД
|		ПО ДД.НомерГТД = ВТ.ГТД
|		ЛЕВОЕ СОЕДИНЕНИЕ Документ.ОперацияПоПоручительству КАК ОППМ
|		ПО ОППМ.Ссылка = ДД.Ссылка
|		И НЕ ОППМ.ПометкаУдаления
|		И ОППМ.Ссылка <> ЕСТЬNULL(ВТ.МояСсылка, НЕОПРЕДЕЛЕНО)
|СГРУППИРОВАТЬ ПО ВТ.ВИД, ВТ.ГТД, ВТ.МояСсылка, ВТ.МоиАктивные";
Рез = Зап.Выполнить().Выгрузить();

CntGone = 0; CntHas = 0; CntOrphan = 0;
Стр = "";
Для Каждого Р Из Рез Цикл
	Если Р.МоиАктивные = 0 Тогда
		CntGone = CntGone + 1;
		Стр = Стр + "GONE|" + Р.ВИД + "|" + Р.ГТД + Символы.ПС;
	ИначеЕсли Р.КолМастеров > 0 Тогда
		CntHas = CntHas + 1;
		Стр = Стр + "HAS_MASTER|" + Р.ВИД + "|" + Р.ГТД + "|" + Р.МояСсылка.УникальныйИдентификатор() + Символы.ПС;
	Иначе
		CntOrphan = CntOrphan + 1;
		Стр = Стр + "ORPHAN|" + Р.ВИД + "|" + Р.ГТД + "|" + Р.МояСсылка.УникальныйИдентификатор() + Символы.ПС;
	КонецЕсли;
КонецЦикла;
Результат = "ИТОГО: GONE=" + CntGone + " HAS_MASTER=" + CntHas + " ORPHAN=" + CntOrphan + " Всего=" + Рез.Количество() + Символы.ПС + Стр;
"@

$body = @{ jsonrpc='2.0'; id=(Get-Random); method='tools/call'; params=@{ name='execute_code'; arguments=@{ code=$code } } } | ConvertTo-Json -Depth 10 -Compress
Write-Host "Sending request..."
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:6010/mcp' -Method Post -Body $body -ContentType 'application/json' -Headers @{ Accept='application/json, text/event-stream'; 'Mcp-Session-Id'=$sid } -UseBasicParsing -TimeoutSec 600
$txt = ($resp.Content -split "`r?`n" | Where-Object { $_ -match '^data:\s' } | ForEach-Object { $_ -replace '^data:\s?','' }) -join "`n"
$j = $txt | ConvertFrom-Json
$inner = $j.result.content[0].text | ConvertFrom-Json
Write-Host "SUCCESS=$($inner.success)"
if ($inner.success) {
	$data = $inner.data -replace '\\n', "`n" -replace '\\"', '"'
	$data | Out-File C:/CLOUDE_PR/tmp/orphan_status_raw.txt -Encoding UTF8
	Write-Host ($data -split "`n" | Select-Object -First 1)
	$data -split "`n" | Where-Object { $_ -match '^GONE\|' } | Out-File C:/CLOUDE_PR/tmp/gone.txt -Encoding UTF8
	$data -split "`n" | Where-Object { $_ -match '^HAS_MASTER\|' } | Out-File C:/CLOUDE_PR/tmp/active_with_master.txt -Encoding UTF8
	$data -split "`n" | Where-Object { $_ -match '^ORPHAN\|' } | Out-File C:/CLOUDE_PR/tmp/orphans.txt -Encoding UTF8
	Write-Host "Files written: gone.txt, active_with_master.txt, orphans.txt"
} else {
	Write-Host "ERROR: $($inner.error)"
}
