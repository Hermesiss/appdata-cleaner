@echo off
cd /d "%~dp0"
echo AppData Cleaner Launcher
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
  echo Running with administrator privileges...
  echo.
  ) else (
  echo This program requires administrator privileges.
  echo Please run this batch file as Administrator.
  echo.
  pause
  exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if %errorLevel% == 0 (
  echo Python found.
  ) else (
  echo Python is not installed or not in PATH.
  echo Please install Python first.
  pause
  exit /b 1
)

REM Install requirements if needed
if exist requirements.txt (
  echo Installing/updating requirements...
  python -m pip install -r requirements.txt
  echo.
)

REM Run the application
echo Starting AppData Cleaner...
python appdata_cleaner.py

echo.
echo Application closed.
pause
