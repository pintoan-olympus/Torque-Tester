@echo off
REM ============================================================
REM  Torque Tester & Calibration System - Build Script
REM  Produces dist\TorqueTester\TorqueTester.exe
REM ============================================================

echo.
echo =============================================
echo  Building Torque Tester Executable
echo =============================================
echo.

REM Clean previous builds
if exist "dist\TorqueTester" (
    echo Cleaning previous build...
    rmdir /s /q "dist\TorqueTester"
)
if exist "build\TorqueTester" (
    rmdir /s /q "build\TorqueTester"
)

REM Run PyInstaller
echo Running PyInstaller...
python -m PyInstaller torque_tester.spec --clean --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed! Check the output above for details.
    pause
    exit /b 1
)

echo.
echo =============================================
echo  Build complete!
echo  Executable: dist\TorqueTester\TorqueTester.exe
echo =============================================
echo.

REM Copy runtime data files next to the exe (db_config.json only; DB is created on first run)
if exist "db_config.json" (
    echo Copying db_config.json to dist\TorqueTester\...
    copy /Y "db_config.json" "dist\TorqueTester\db_config.json"
)

echo Done. You can now distribute the dist\TorqueTester\ folder.
echo.
pause
