@echo off
echo Building AppData Cleaner...
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
  echo Activating virtual environment...
  call venv\Scripts\activate.bat
  ) else (
  echo Virtual environment not found. Please run setup.bat first.
  pause
  exit /b 1
)

REM Install PyInstaller if not present
echo Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
  echo Installing PyInstaller...
  pip install pyinstaller
)

REM Clean previous builds
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del *.spec

REM Build the application
echo Building executable...
if exist "icon.ico" (
  echo Using icon: icon.ico
  pyinstaller --onefile --windowed --name "AppDataCleaner" --icon=icon.ico appdata_cleaner.py
  ) else (
  echo No icon file found, building without icon...
  pyinstaller --onefile --windowed --name "AppDataCleaner" appdata_cleaner.py
)

REM Check if build was successful
if exist "dist\AppDataCleaner.exe" (
  echo.
  echo ========================================
  echo Build completed successfully!
  echo Executable: dist\AppDataCleaner.exe
  echo ========================================
  echo.
  
  REM Open dist folder
  explorer dist
  ) else (
  echo.
  echo ========================================
  echo Build failed! Check the output above.
  echo ========================================
  echo.
)

pause
