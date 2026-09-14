@echo off
chcp 65001 >nul
title Đóng Gói AutoFisch Standalone EXE
echo ===================================================
echo     ĐANG ĐÓNG GÓI AUTOFISCH THÀNH FILE EXE...
echo ===================================================
echo.

echo [1/2] Đang đóng gói AutoFischCore (Nhân macro)...
python -m PyInstaller --clean --onefile --noconsole --icon="app.ico" --add-data "app.ico;." --name "AutoFischCore" --uac-admin main.py

echo.
echo [2/2] Đang đóng gói AutoFisch.exe (Giao diện khởi động & tự cập nhật)...
python -m PyInstaller --clean --onefile --noconsole --icon="app.ico" --add-data "app.ico;." --name "AutoFisch" --uac-admin launcher.py

if exist "dist\AutoFisch.exe" (
    echo.
    echo ===================================================
    echo     ĐÓNG GÓI THÀNH CÔNG!
    echo     File người dùng mở: dist\AutoFisch.exe
    echo     File nhân bot:       dist\AutoFischCore.exe
    echo ===================================================
    copy /y config.json dist\config.json >nul
    copy /y app.ico dist\app.ico >nul
    if exist "dist\Launcher.exe" del /f /q "dist\Launcher.exe" >nul
) else (
    echo.
    echo [LỖI] Quá trình đóng gói thất bại. Hãy kiểm tra lại log.
)

pause
