@echo off
setlocal
cd /d "%~dp0"
title Nova Tech Store - Gmail OTP Setup

echo ==========================================================
echo             NOVA TECH STORE - GMAIL OTP
echo ==========================================================
echo.
echo Use a Gmail APP PASSWORD, not your normal Gmail password.
echo If you do not configure Gmail, registration still works and
 echo the OTP will be printed in the Nova server window.
echo.
set /p NOVA_EMAIL=Gmail address: 
set /p NOVA_PASS=16-character Gmail App Password: 

if "%NOVA_EMAIL%"=="" goto :missing
if "%NOVA_PASS%"=="" goto :missing

setx NOVA_STORE_EMAIL "%NOVA_EMAIL%" >nul
setx NOVA_STORE_EMAIL_PASSWORD "%NOVA_PASS%" >nul

echo.
echo Saved successfully for future terminal sessions.
echo IMPORTANT: Close any Nova server window and start it again.
echo Then launch START_NOVA_STORE.bat.
pause
exit /b 0

:missing
echo.
echo Email and App Password are required.
pause
exit /b 1
