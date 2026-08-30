@echo off
echo ========================================
echo   Building Threads Scraper .exe
echo ========================================
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Building executable with PyInstaller...
pyinstaller --onefile --windowed --name "ThreadsScraper" --icon=NONE threads_app.py
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Cleaning up build files...
rmdir /s /q build
del /q ThreadsScraper.spec

echo.
echo ========================================
echo   BUILD COMPLETE!
echo ========================================
echo.
echo Your executable is located at:
echo   dist\ThreadsScraper.exe
echo.
echo File size: ~15-20 MB
echo.
pause
