' Создаёт ярлык "Interview-to-BPMN" на рабочем столе
' Запустите этот файл один раз двойным кликом

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strDesktop = WshShell.SpecialFolders("Desktop")
strProjectDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Создать ярлык
Set oShortcut = WshShell.CreateShortcut(strDesktop & "\Interview-to-BPMN.lnk")
oShortcut.TargetPath = strProjectDir & "\start.bat"
oShortcut.WorkingDirectory = strProjectDir
oShortcut.WindowStyle = 1
oShortcut.Description = "Interview-to-BPMN: Аудио интервью → BPMN-схемы и документация"
oShortcut.IconLocation = "shell32.dll,137"
oShortcut.Save

MsgBox "Ярлык создан на рабочем столе!" & vbCrLf & vbCrLf & _
       "Двойной клик по ярлыку запустит приложение." & vbCrLf & _
       "Браузер откроется автоматически на http://localhost:8501", _
       vbInformation, "Interview-to-BPMN"
