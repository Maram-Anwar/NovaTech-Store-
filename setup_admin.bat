@echo off
cd /d "%~dp0"
title Nova Tech Store - Admin Setup
where py >nul 2>nul
if %errorlevel%==0 (
    py setup_admin.py
) else (
    python setup_admin.py
)
pause
