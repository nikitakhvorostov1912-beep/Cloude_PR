; Кастомные страницы NSIS инсталлера для Survey Automation

!macro customHeader
  !system "echo Сборка Survey Automation installer..."
!macroend

!macro customInit
  ; Проверить Windows версию (нужен Windows 10+)
  ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentMajorVersionNumber"
  ${If} $R0 < 10
    MessageBox MB_OK|MB_ICONSTOP "Survey Automation требует Windows 10 или новее."
    Quit
  ${EndIf}
!macroend

!macro customInstall
  ; Установить Visual C++ Redistributable если нужно
  ; (обычно уже есть на современных Windows)
!macroend

!macro customUnInstall
  ; Удаление не трогает AppData (данные пользователя)
  MessageBox MB_YESNO "Удалить данные проектов в AppData?\n(Это удалит все ваши проекты)" IDNO +2
    RMDir /r "$APPDATA\SurveyAutomation"
!macroend
