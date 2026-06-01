@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist ".git" (
    echo This folder is not a git repository.
    echo Clone the repo first, for example:
    echo   git clone https://github.com/YOUR_USER/MicroscopeCapture.git C:\MicroscopeCapture
    exit /b 1
)

echo Pulling latest changes from Git...
git pull
if errorlevel 1 (
    echo git pull failed.
    exit /b 1
)

echo.
echo Update complete.
echo If requirements.txt changed, run setup.bat again.
echo Then launch with run.bat or the Desktop shortcut.
exit /b 0
