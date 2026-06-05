@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist ".git" (
    echo This folder is not a git repository.
    echo Clone the repo first, for example:
    echo   git clone https://github.com/YOUR_USER/MicroscopeCapture.git C:\MicroscopeCapture
    exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
    echo Git was not found on PATH.
    echo Install Git for Windows, then open a new Command Prompt and retry.
    exit /b 1
)

echo Pulling latest changes from Git...
git fetch origin
if errorlevel 1 (
    echo git fetch failed. Check your network and remote URL: git remote -v
    exit /b 1
)

git pull origin main
if errorlevel 1 (
    echo git pull failed.
    echo Try: git branch --set-upstream-to=origin/main main
    exit /b 1
)

echo.
echo Update complete.
echo If requirements.txt changed, run setup.bat again.
echo Then launch with run.bat or the Desktop shortcut.
exit /b 0
