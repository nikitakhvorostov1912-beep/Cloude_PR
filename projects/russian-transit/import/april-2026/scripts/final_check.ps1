# Финальная проверка: найти все ГТД с >1 активным документом
$sid = Get-Content 'C:\CLOUDE_PR\projects\russian-transit\scripts\mcp-session.txt' -Raw
$code = @"
Зап = Новый Запрос;
Зап.Текст =
"ВЫБРАТЬ
|	ОПП.НомерГТД КАК НомерГТД,
|	КОЛИЧЕСТВО(РАЗЛИЧНЫЕ ОПП.Ссылка) КАК Кол
|ИЗ
|	Документ.ОперацияПоПоручительству КАК ОПП
|ГДЕ
|	НЕ ОПП.ПометкаУдаления
|	И ОПП.НомерГТД <> """"
|	И ОПП.Дата >= ДАТАВРЕМЯ(2026, 4, 1) И ОПП.Дата < ДАТАВРЕМЯ(2026, 5, 1)
|СГРУППИРОВАТЬ ПО ОПП.НомерГТД
|ИМЕЮЩИЕ КОЛИЧЕСТВО(РАЗЛИЧНЫЕ ОПП.Ссылка) > 1
|УПОРЯДОЧИТЬ ПО Кол УБЫВ";
Рез = Зап.Выполнить().Выгрузить();
Стр = "Дубликатов ГТД среди активных док-в апреля 2026: " + Рез.Количество() + Символы.ПС;
Для Каждого Р Из Рез Цикл
	Стр = Стр + Р.НомерГТД + " => " + Р.Кол + Символы.ПС;
КонецЦикла;

// Также общая статистика
ЗапС = Новый Запрос("ВЫБРАТЬ КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Ссылка) КАК К ИЗ Документ.ОперацияПоПоручительству ГДЕ НЕ ПометкаУдаления И Дата >= &Н И Дата < &К");
ЗапС.УстановитьПараметр("Н", '20260401');
ЗапС.УстановитьПараметр("К", '20260501');
РезС = ЗапС.Выполнить().Выгрузить();
Стр = Стр + Символы.ПС + "Всего активных ОПП за апрель 2026: " + РезС[0].К;

Результат = Стр;
"@
$body = @{ jsonrpc='2.0'; id=(Get-Random); method='tools/call'; params=@{ name='execute_code'; arguments=@{ code=$code } } } | ConvertTo-Json -Depth 10 -Compress
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:6010/mcp' -Method Post -Body $body -ContentType 'application/json' -Headers @{ Accept='application/json, text/event-stream'; 'Mcp-Session-Id'=$sid } -UseBasicParsing -TimeoutSec 120
$txt = ($resp.Content -split "`r?`n" | Where-Object { $_ -match '^data:\s' } | ForEach-Object { $_ -replace '^data:\s?','' }) -join "`n"
$j = $txt | ConvertFrom-Json
$inner = $j.result.content[0].text | ConvertFrom-Json
$data = $inner.data -replace '\\n', "`n" -replace '\\"', '"'
Write-Host "SUCCESS=$($inner.success)"
Write-Host $data
$data | Out-File C:/CLOUDE_PR/tmp/final_check_result.txt -Encoding UTF8
