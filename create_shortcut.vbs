Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

desktopPath = WshShell.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\Survey Automation.lnk"

Set shortcut = WshShell.CreateShortcut(shortcutPath)
shortcut.TargetPath = "C:\CLOUDE_PR\projects\survey-automation\start.bat"
shortcut.WorkingDirectory = "C:\CLOUDE_PR\projects\survey-automation"
shortcut.Description = "Survey Automation - Backend + Frontend"
shortcut.WindowStyle = 1
shortcut.Save

WScript.Echo "Shortcut created: " & shortcutPath
