@echo off
setlocal EnableExtensions

REM ============================================================
REM Sync changed app files from a Dropbox copy into the local
REM working copy (default: C:\MicroscopeCapture).
REM
REM Paths are NOT stored in this repo. Configure once via either:
REM   1) dropbox_sync.config.bat  (copy from dropbox_sync.config.bat.example)
REM   2) Environment variable DROPBOX_MICROSCOPE_SRC
REM ============================================================

set "SRC="
set "DST=C:\MicroscopeCapture"

if exist "%~dp0dropbox_sync.config.bat" (
    call "%~dp0dropbox_sync.config.bat"
)

if not defined SRC if defined DROPBOX_MICROSCOPE_SRC (
    set "SRC=%DROPBOX_MICROSCOPE_SRC%"
)

if not defined SRC (
    echo Dropbox source path is not configured.
    echo.
    echo   copy dropbox_sync.config.bat.example dropbox_sync.config.bat
    echo   notepad dropbox_sync.config.bat
    echo.
    echo Or set DROPBOX_MICROSCOPE_SRC to your Dropbox MicroscopeCapture folder.
    exit /b 1
)

if not defined DST set "DST=C:\MicroscopeCapture"

echo Source (Dropbox): %SRC%
echo Target (local):   %DST%
echo.

if not exist "%SRC%" (
    echo Source folder not found: %SRC%
    echo Edit dropbox_sync.config.bat or DROPBOX_MICROSCOPE_SRC.
    exit /b 1
)

if not exist "%DST%" (
    echo Target folder not found. Creating %DST%
    mkdir "%DST%"
)

REM /E      copy subdirectories including empty ones
REM /XO     do not overwrite a local file that is newer than the source
REM /XD     exclude these directories
robocopy "%SRC%" "%DST%" /E /XO ^
  /XD ".venv" ".git" "MicroscopeData" "__pycache__" ^
  /XF "*.pyc" "dropbox_sync.config.bat" ^
  /NFL /NDL /NP

set "RC=%ERRORLEVEL%"
echo.
if %RC% GEQ 8 (
    echo robocopy reported errors (code %RC%).
    exit /b %RC%
)

echo Update complete (robocopy code %RC%: 0=no change, 1=files updated).
echo If requirements.txt changed, run setup.bat
exit /b 0
