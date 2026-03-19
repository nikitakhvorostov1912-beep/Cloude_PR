' Interview-to-BPMN — запуск без окна консоли
' Двойной клик по этому файлу запустит приложение и откроет браузер

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Запустить Ollama если не запущена
WshShell.Run "cmd /c tasklist /FI ""IMAGENAME eq ollama.exe"" | find /I ""ollama.exe"" >nul || start """" ollama serve", 0, False

' Подождать 2 секунды для старта Ollama
WScript.Sleep 2000

' Запустить Streamlit (скрыть консольное окно)
WshShell.Run "cmd /c python -m streamlit run src/web/app.py --server.headless=false --browser.gatherUsageStats=false", 0, False

' Подождать 3 секунды и открыть браузер
WScript.Sleep 3000
WshShell.Run "http://localhost:8501", 1, False
