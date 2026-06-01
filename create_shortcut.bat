@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "TARGET=%~dp0run.bat"
set "ICON=%SystemRoot%\System32\imageres.dll, 174"
set "SHORTCUT=%USERPROFILE%\Desktop\Microscope Capture.lnk"

echo Creating desktop shortcut...
echo Target: %TARGET%
echo Shortcut: %SHORTCUT%

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$s = $ws.CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath = '%TARGET%';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.IconLocation = '%ICON%';" ^
  "$s.Description = 'Microscope Capture';" ^
  "$s.Save()"

if errorlevel 1 (
    echo Failed to create shortcut.
    exit /b 1
)

echo.
echo Done. A "Microscope Capture" shortcut is now on your Desktop.
echo Double-click it any time to launch the app.
exit /b 0
