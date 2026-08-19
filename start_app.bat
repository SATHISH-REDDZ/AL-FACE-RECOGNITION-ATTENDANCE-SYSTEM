@echo off
title AI Face Recognition Attendance System Launcher
echo ===================================================
echo   AI Face Recognition Attendance System
echo ===================================================
echo.
if exist venv\Scripts\activate.bat (
    echo Activating Virtual Environment...
    call venv\Scripts\activate.bat
)

echo Starting Flask Application Server...
python run.py
pause
