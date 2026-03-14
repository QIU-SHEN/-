@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo   WeChat AI Publisher - 取消开机启动
echo ==========================================
echo.

set "STARTUP_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_PATH%\WeChatAI_Publisher.lnk"

if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo 已删除开机启动快捷方式
    echo.
    echo 程序将不再随系统启动
) else (
    echo 未找到开机启动项，可能已经取消过了
)

pause
