@echo off
title Setup Environment - AI Face Recognition Attendance System
echo ===================================================
echo   Installing Dependencies & Setting Up Environment
echo ===================================================
echo.

if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo Setup Complete! Run start_app.bat to launch the application.
pause
