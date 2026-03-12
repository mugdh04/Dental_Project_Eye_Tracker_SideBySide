@echo off
setlocal enabledelayedexpansion

:: Check for Python installation
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

:: Run the build script
echo Starting Eye Tracker build...
python build_exe.py

if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build complete! Executable is in the dist folder.
pause
echo.
echo To distribute:
echo   1. Create a folder named "EyeTracker"
echo   2. Copy these into the folder:
echo        - EyeTracker.exe
echo        - images folder
echo        - aoi_config.json
echo        - run.bat
echo   3. Zip the EyeTracker folder
pause