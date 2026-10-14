@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)
%PY% --version
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found. Install Python and enable Add Python to PATH.
  pause
  exit /b 1
)
if not exist .venv (
  %PY% -m venv .venv
  if errorlevel 1 goto :failed
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :network
python -m pip install --retries 5 --timeout 30 -r requirements.txt
if errorlevel 1 goto :network
if not exist .env copy .env.example .env >nul
echo.
echo Setup complete. Edit .env and change SECRET_KEY and ADMIN_TEMP_PASSWORD before use.
echo Starting Campus Complaint System...
python run.py
goto :eof
:network
echo.
echo ERROR: Python packages could not be downloaded.
echo Check your internet connection, VPN/proxy, DNS, or firewall, then run setup_windows.bat again.
echo This is a package-download/network error if pip reports temporary failure in name resolution.
pause
exit /b 1
:failed
echo ERROR: Could not create the Python virtual environment.
pause
exit /b 1
