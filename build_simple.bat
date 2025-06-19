@echo off
echo AppData Cleaner - Build Script
echo ===============================

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
  echo Activating virtual environment...
  call venv\Scripts\activate.bat
  echo.
  
  REM Run the Python build script
  python build_app.py
  ) else (
  echo Error: Virtual environment not found!
  echo Please run setup.bat first to create the virtual environment.
  echo.
  pause
)

pause
