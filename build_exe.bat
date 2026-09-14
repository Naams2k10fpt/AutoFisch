@echo off
chcp 65001 >nul
title Đóng Gói AutoFisch Standalone EXE (Single File)
echo ===================================================
echo     ĐANG ĐÓNG GÓI AUTOFISCH THÀNH 1 FILE EXE DUY NHẤT...
echo ===================================================
echo.

python -m PyInstaller --clean --onefile --noconsole --icon="app.ico" --add-data "app.ico;." --name "AutoFisch" main.py

if exist "dist\AutoFisch.exe" (
    echo.
    echo ===================================================
    echo     ĐÓNG GÓI THÀNH CÔNG!
    echo     File duy nhất xuất xưởng: dist\AutoFisch.exe
    echo ===================================================
    copy /y config.json dist\config.json >nul
    copy /y app.ico dist\app.ico >nul
    if exist "dist\AutoFischCore.exe" del /f /q "dist\AutoFischCore.exe" >nul
    if exist "dist\Launcher.exe" del /f /q "dist\Launcher.exe" >nul
) else (
    echo.
    echo [LỖI] Quá trình đóng gói thất bại. Hãy kiểm tra lại log.
)

pause

