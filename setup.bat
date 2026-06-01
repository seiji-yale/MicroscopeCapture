@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo Microscope Capture - setup
echo.

for %%I in ("%~dp0.") do set "PROJECT_DIR=%%~sI"
echo Project path: %PROJECT_DIR%
echo If setup fails with "No such file or directory" during PySide6 install,
echo move this folder to a shorter path such as C:\MicroscopeCapture and retry.
echo.

set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON if exist "C:\ProgramData\miniforge3\python.exe" set "PYTHON=C:\ProgramData\miniforge3\python.exe"
if not defined PYTHON if exist "C:\ProgramData\miniforge3\Python.exe" set "PYTHON=C:\ProgramData\miniforge3\Python.exe"

if not defined PYTHON (
    echo Python was not found on PATH.
    echo Install Python or Miniforge, then run this script again.
    exit /b 1
)

echo Using Python: %PYTHON%
"%PYTHON%" --version
if errorlevel 1 exit /b 1

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    "%PYTHON%" -m venv .venv
    if errorlevel 1 exit /b 1
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Setup complete.
echo Run the app with: run.bat
echo Or manually: .venv\Scripts\python.exe app.py
exit /b 0
