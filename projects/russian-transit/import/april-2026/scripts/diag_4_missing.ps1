$sid = Get-Content 'C:\CLOUDE_PR\projects\russian-transit\scripts\mcp-session.txt' -Raw
$gtds = @(
	'10000000/040426/0203901',
	'10000000/160426/0233671',
	'10000000/300426/0270094',
	'10000000/300426/0270260'
)
$ids = '["' + ($gtds -join '","') + '"]'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($ids)
$b64 = [Convert]::ToBase64String($bytes)
$code = @"
ДД = Base64Значение("$b64");
Текст = ПолучитьСтрокуИзДвоичныхДанных(ДД, КодировкаТекста.UTF8);
Чт = Новый ЧтениеJSON;
Чт.УстановитьСтроку(Текст);
Массив = ПрочитатьJSON(Чт, Истина);
Стр = "";
Для Каждого Г Из Массив Цикл
	Зап = Новый Запрос("ВЫБРАТЬ Ссылка, ПометкаУдаления, Дата ИЗ Документ.ОперацияПоПоручительству ГДЕ НомерГТД = &Г");
	Зап.УстановитьПараметр("Г", Г);
	Рез = Зап.Выполнить().Выгрузить();
	Стр = Стр + "ГТД=" + Г + " шапок=" + Рез.Количество();
	Для Каждого Р Из Рез Цикл
		Стр = Стр + " [" + Р.Ссылка + " дата=" + Формат(Р.Дата, "ДФ=dd.MM.yyyy") + " удал=" + Р.ПометкаУдаления + "]";
	КонецЦикла;
	Зап2 = Новый Запрос("ВЫБРАТЬ ДД.Ссылка КАК Ссылка, ОПП.ПометкаУдаления КАК Удал ИЗ Документ.ОперацияПоПоручительству.ДанныеДокументов КАК ДД ВНУТРЕННЕЕ СОЕДИНЕНИЕ Документ.ОперацияПоПоручительству КАК ОПП ПО ОПП.Ссылка = ДД.Ссылка ГДЕ ДД.НомерГТД = &Г");
	Зап2.УстановитьПараметр("Г", Г);
	Рез2 = Зап2.Выполнить().Выгрузить();
	Стр = Стр + " ВД_ДД=" + Рез2.Количество();
	Для Каждого Р Из Рез2 Цикл
		Стр = Стр + " {" + Р.Ссылка + " удал=" + Р.Удал + "}";
	КонецЦикла;
	Стр = Стр + Символы.ПС;
КонецЦикла;
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
