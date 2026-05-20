# Прямой вызов MCP Toolkit native на 6005 через HttpClient.
# Стандартный MCP-клиент Claude Code на этом сервере падает с 404,
# потому что нарушает регистр заголовка Mcp-Session-Id.
#
# Использование:
#   .\mcp6005-call.ps1 -ToolName execute_query -Args '{"query":"ВЫБРАТЬ 1"}'
#   .\mcp6005-call.ps1 -ToolName execute_code  -Args '{"code":"Результат = ИмяПользователя();"}'

param(
    [Parameter(Mandatory)] [string]$ToolName,
    [Parameter(Mandatory)] [string]$Args,
    [int]$Port = 6005,
    [int]$TimeoutSec = 60
)

Add-Type -AssemblyName System.Net.Http

$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
$client.DefaultRequestHeaders.Accept.Add('application/json')
$client.DefaultRequestHeaders.Accept.Add('text/event-stream')

try {
    # 1. initialize
    $init = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"claude-helper","version":"1"}}}'
    $c1 = New-Object System.Net.Http.StringContent($init, [System.Text.Encoding]::UTF8, 'application/json')
    $r1 = $client.PostAsync("http://127.0.0.1:$Port/mcp", $c1).Result
    if (-not $r1.IsSuccessStatusCode) {
        Write-Error "Init failed: $($r1.StatusCode)"
        return
    }
    $sid = ($r1.Headers | Where-Object { $_.Key -ieq 'mcp-session-id' }).Value | Select-Object -First 1

    # 2. tools/call
    $reqObj = @{
        jsonrpc = '2.0'
        id      = 2
        method  = 'tools/call'
        params  = @{
            name      = $ToolName
            arguments = ConvertFrom-Json $Args
        }
    }
    $reqJson = ConvertTo-Json $reqObj -Depth 20 -Compress
    $c2 = New-Object System.Net.Http.StringContent($reqJson, [System.Text.Encoding]::UTF8, 'application/json')
    $c2.Headers.Add('Mcp-Session-Id', $sid)
    $r2 = $client.PostAsync("http://127.0.0.1:$Port/mcp", $c2).Result
    $raw = $r2.Content.ReadAsStringAsync().Result

    # SSE → собираем data-строки в один JSON
    $dataLines = $raw -split "`n" | Where-Object { $_ -match '^data:' } | ForEach-Object { $_ -replace '^data:\s?', '' }
    $combined = ($dataLines -join '')
    Write-Output $combined
} finally {
    $client.Dispose()
}
