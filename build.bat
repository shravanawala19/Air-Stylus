@echo off
setlocal

echo ============================================
echo   AIRstylus - Air Mouse  build script
echo ============================================

cd /d "%~dp0"

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Building executable...
python -m PyInstaller --clean --noconfirm build.spec
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo Executable: dist\AIRstylus.exe
echo.
pause
endlocal