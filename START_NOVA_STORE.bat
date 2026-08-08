@echo off
setlocal
cd /d "%~dp0"
title Nova Tech Store v4 - Backend Server

echo ==========================================================
echo               NOVA TECH STORE v4
echo ==========================================================
echo.
echo IMPORTANT: Keep this window OPEN while using the website.
echo This version uses http://127.0.0.1:5055 to avoid old servers.
echo.

for %%F in (api_server.py users.json admins.json products.json carts.json index.html app.js styles.css) do (
  if not exist "%%F" (
    echo ERROR: Required file %%F is missing.
    echo Extract this ZIP into a NEW EMPTY folder.
    pause
    exit /b 1
  )
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 (
    py -3 -c "import json; [json.load(open(f, encoding='utf-8')) for f in ['users.json','admins.json','products.json','carts.json']]; print('JSON data check: OK')"
    if errorlevel 1 goto :json_error
    echo Starting Nova Backend v6 on port 5055...
    py -3 api_server.py
    goto :server_end
  )
)

where python >nul 2>nul
if %errorlevel%==0 (
  python -c "import json; [json.load(open(f, encoding='utf-8')) for f in ['users.json','admins.json','products.json','carts.json']]; print('JSON data check: OK')"
  if errorlevel 1 goto :json_error
  echo Starting Nova Backend v6 on port 5055...
  python api_server.py
  goto :server_end
)

echo ERROR: Python 3 is not installed or not available in PATH.
echo Install Python 3 and enable Add Python to PATH.
pause
exit /b 1

:json_error
echo.
echo ERROR: One of the JSON data files is invalid.
pause
exit /b 1

:server_end
echo.
echo Nova server stopped.
pause
