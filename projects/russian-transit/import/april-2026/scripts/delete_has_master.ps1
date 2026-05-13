$sid = Get-Content 'C:\CLOUDE_PR\projects\russian-transit\scripts\mcp-session.txt' -Raw
$ids = @(
	'46d4c276-4e9c-11f1-89b7-cc28aa6a0915',
	'1ba07762-4ea1-11f1-89b7-cc28aa6a0915',
	'5150a348-4e90-11f1-89b7-cc28aa6a0915'
)
$idsJson = "[" + (($ids | ForEach-Object { "`"$_`"" }) -join ',') + "]"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($idsJson)
$b64 = [Convert]::ToBase64String($bytes)
$code = @"
ДД = Base64Значение("$b64");
Текст = ПолучитьСтрокуИзДвоичныхДанных(ДД, КодировкаТекста.UTF8);
Чт = Новый ЧтениеJSON;
Чт.УстановитьСтроку(Текст);
Массив = ПрочитатьJSON(Чт, Истина);
Удалено = 0; Ошибок = 0; Лог = "";
Для Каждого ИД Из Массив Цикл
	Попытка
		Ссыл = Документы.ОперацияПоПоручительству.ПолучитьСсылку(Новый УникальныйИдентификатор(ИД));
		Об = Ссыл.ПолучитьОбъект();
		Если Об = Неопределено Тогда
			Лог = Лог + "GONE " + ИД + Символы.ПС;
			Продолжить;
		КонецЕсли;
		Лог = Лог + "DEL " + ИД + " ГТД=" + Об.НомерГТД + Символы.ПС;
		Об.Удалить();
		Удалено = Удалено + 1;
	Исключение
		Ошибок = Ошибок + 1;
		Лог = Лог + "ERR " + ИД + ": " + ОписаниеОшибки() + Символы.ПС;
	КонецПопытки;
КонецЦикла;
Результат = "Удалено=" + Удалено + " Ошибок=" + Ошибок + Символы.ПС + Лог;
"@
$body = @{ jsonrpc='2.0'; id=(Get-Random); method='tools/call'; params=@{ name='execute_code'; arguments=@{ code=$code } } } | ConvertTo-Json -Depth 10 -Compress
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:6010/mcp' -Method Post -Body $body -ContentType 'application/json' -Headers @{ Accept='application/json, text/event-stream'; 'Mcp-Session-Id'=$sid } -UseBasicParsing -TimeoutSec 120
$txt = ($resp.Content -split "`r?`n" | Where-Object { $_ -match '^data:\s' } | ForEach-Object { $_ -replace '^data:\s?','' }) -join "`n"
$j = $txt | ConvertFrom-Json
$inner = $j.result.content[0].text | ConvertFrom-Json
$data = $inner.data -replace '\\n', "`n" -replace '\\"', '"'
Write-Host "SUCCESS=$($inner.success)"
Write-Host $data
